"""Read-only per-model benchmark archive integrity and reclaim boundaries."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "scripts/diagnostics/benchmark-reclaim-readiness.py"
SPEC = importlib.util.spec_from_file_location("benchmark_reclaim_readiness", SOURCE)
assert SPEC and SPEC.loader
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class BenchReclaimReadiness(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.reports = self.root / "docs/model-reports"
        self.reports.mkdir(parents=True)
        for profile in CHECK.PROFILES:
            (self.reports / (profile + ".md")).write_text(
                "**BENCHMARK_STATUS: NOT_MEASURED**\n", encoding="utf-8"
            )

    def archive(self, content=b"real captured results"):
        (self.reports / "mazinb.md").write_text(
            "**BENCHMARK_STATUS: MEASURED**\n", encoding="utf-8"
        )
        folder = self.reports / "evidence/mazinb/20261014T015805Z"
        folder.mkdir(parents=True)
        contents = {"mazinb.json": content, "mazinb-report.md": b"report"}
        for name, body in contents.items():
            (folder / name).write_bytes(body)
        (folder / "SHA256SUMS").write_text(
            "".join(f"{hashlib.sha256(body).hexdigest()}  {name}\n"
                    for name, body in contents.items()), encoding="utf-8"
        )
        return folder

    def test_unmeasured_never_counts_as_zero_or_cleanup_permission(self):
        lines, rc = CHECK.inspect(self.root)
        self.assertEqual(rc, 0)
        self.assertIn("BENCHMARK_PROFILE=mazinb RESULT=NOT_MEASURED HOLD", lines)
        self.assertIn("RECLAIM_ACTUAL_DELETION=NOT_PERFORMED", lines)

    def test_verified_benchmark_digests_still_not_approval(self):
        self.archive()
        lines, rc = CHECK.inspect(self.root)
        self.assertEqual(rc, 0)
        self.assertTrue(any("MEASURED_ARCHIVE_VERIFIED" in x for x in lines))
        self.assertTrue(any("SHA256_OK" in x for x in lines))
        self.assertTrue(any("RECLAIM=NOT_AUTHORIZED" in x for x in lines))

    def test_tampered_payload_is_blocked(self):
        folder = self.archive()
        (folder / "mazinb.json").write_bytes(b"changed!")
        lines, rc = CHECK.inspect(self.root)
        self.assertEqual(rc, 2)
        self.assertTrue(any("artifact_sha256_mismatch" in x for x in lines))

    def test_absolute_path_manifest_is_rejected(self):
        folder = self.archive()
        original = (folder / "SHA256SUMS").read_text()
        (folder / "SHA256SUMS").write_text(original.replace(
            "  mazinb.json", "  /tmp/mazinb.json"
        ))
        self.assertEqual(CHECK.inspect(self.root)[1], 2)

    def test_symlink_payload_is_rejected(self):
        folder = self.archive()
        target = folder / "mazinb.json"
        target.unlink()
        target.symlink_to("/etc/hosts")
        self.assertEqual(CHECK.inspect(self.root)[1], 2)

    def test_missing_archive_prevents_falsely_measured_certification(self):
        (self.reports / "mazinb.md").write_text(
            "**BENCHMARK_STATUS: MEASURED**\n"
        )
        self.assertEqual(CHECK.inspect(self.root)[1], 2)

    def test_duplicate_manifest_entry_is_blocked(self):
        folder = self.archive()
        p = folder / "SHA256SUMS"
        p.write_text(p.read_text() + p.read_text().splitlines()[0] + "\n")
        self.assertEqual(CHECK.inspect(self.root)[1], 2)


if __name__ == "__main__":
    unittest.main()
