from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
PARSER = ROOT / "scripts" / "lib" / "qualification_marker.py"


class QualificationMarkerTests(unittest.TestCase):
    def run_parser(self, text: str, *args: str) -> subprocess.CompletedProcess[bytes]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "qualification.env"
            path.write_text(text, encoding="utf-8")
            return subprocess.run(
                ["python3", str(PARSER), str(path), *args],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

    def test_schema2_bound_marker_is_accepted(self) -> None:
        release = "a" * 40
        digest = "b" * 64
        result = self.run_parser(
            "\n".join([
                "QUALIFICATION_SCHEMA_VERSION=2",
                f"QUALIFIED_RELEASE={release}",
                f"RELEASE_MANIFEST_SHA256={digest}",
                "QUALIFIED_AT=2026-09-18T00:00:00Z",
                "",
            ]),
            "--require-bound",
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        fields = result.stdout.split(b"\0")
        self.assertIn(b"RELEASE_MANIFEST_SHA256", fields)
        self.assertIn(digest.encode(), fields)

    def test_schema1_is_readable_but_rejected_for_cutover(self) -> None:
        release = "a" * 40
        text = (
            "QUALIFICATION_SCHEMA_VERSION=1\n"
            f"QUALIFIED_RELEASE={release}\n"
            "QUALIFIED_AT=2026-09-18T00:00:00Z\n"
        )
        observed = self.run_parser(text)
        self.assertEqual(observed.returncode, 0, observed.stderr.decode())
        cutover = self.run_parser(text, "--require-bound")
        self.assertNotEqual(cutover.returncode, 0)
        self.assertIn(b"legacy and not manifest-bound", cutover.stderr)

    def test_schema2_rejects_invalid_digest(self) -> None:
        result = self.run_parser(
            "QUALIFICATION_SCHEMA_VERSION=2\n"
            f"QUALIFIED_RELEASE={'a' * 40}\n"
            "RELEASE_MANIFEST_SHA256=not-a-digest\n"
            "QUALIFIED_AT=2026-09-18T00:00:00Z\n"
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"invalid RELEASE_MANIFEST_SHA256", result.stderr)

    def test_rejects_unknown_duplicate_and_shell_like_values(self) -> None:
        release = "a" * 40
        base = (
            "QUALIFICATION_SCHEMA_VERSION=2\n"
            f"QUALIFIED_RELEASE={release}\n"
            f"RELEASE_MANIFEST_SHA256={'b' * 64}\n"
            "QUALIFIED_AT=2026-09-18T00:00:00Z\n"
        )
        unknown = self.run_parser(base + "EXTRA=1\n")
        self.assertNotEqual(unknown.returncode, 0)
        self.assertIn(b"unknown qualification key", unknown.stderr)

        duplicate = self.run_parser(base + f"QUALIFIED_RELEASE={release}\n")
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertIn(b"duplicate key", duplicate.stderr)

        shell_like = self.run_parser(base.replace(release, "$(touch-pwned)"))
        self.assertNotEqual(shell_like.returncode, 0)
        self.assertIn(b"unsafe value", shell_like.stderr)


if __name__ == "__main__":
    unittest.main()
