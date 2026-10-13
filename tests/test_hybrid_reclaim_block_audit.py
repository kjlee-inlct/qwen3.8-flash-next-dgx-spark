"""Guard tests for physical accounting, without inspecting model files."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/diagnostics/inspect-hybrid-reclaim-blocks.sh"


class HybridReclaimBlockAuditTests(unittest.TestCase):
    def execute(self, variables: dict[str, str]) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env.pop("QWEN38_RECLAIM_AUDIT_SHA", None)
        env.pop("QWEN38_RECLAIM_MODELS_ROOT", None)
        env.update(variables)
        return subprocess.run(
            ["bash", str(SCRIPT)], cwd=ROOT, env=env,
            text=True, capture_output=True, check=False, timeout=10,
        )

    def test_missing_sha_is_rejected_before_inspection(self) -> None:
        r = self.execute({})
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("exact_checkout_sha_required", r.stderr)
        self.assertNotIn("RECLAIM_BLOCK_ACCOUNTING=BEGIN", r.stdout)

    def test_explicit_existing_models_root_required(self) -> None:
        r = self.execute({"QWEN38_RECLAIM_AUDIT_SHA": "f" * 40})
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("explicit_real_models_root_required", r.stderr)

    def test_bad_checkout_refused(self) -> None:
        r = self.execute({
            "QWEN38_RECLAIM_AUDIT_SHA": "0" * 40,
            "QWEN38_RECLAIM_MODELS_ROOT": str(ROOT),
        })
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("checkout_sha_mismatch", r.stderr)

    def test_no_destructive_or_runtime_operations(self) -> None:
        text = SCRIPT.read_text(encoding="utf-8")
        for expected in ("du -scxB1", "find \"$path\" -xdev", "BENCHMARK_EVIDENCE=NOT_VERIFIED",
                         "MODEL_DELETION=BLOCKED_PENDING_DEPENDENCY_AND_EVIDENCE_REVIEW"):
            self.assertIn(expected, text)
        for forbidden in ("rm -rf", "docker run", "docker rm", "docker rmi",
                          "systemctl start", "systemctl restart", "sudo ",
                          "manage-models.sh\" remove", "manage-storage.sh\" prune",
                          "swapoff", "git clean", "git reset"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
