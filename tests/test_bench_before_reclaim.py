"""No-host refusal and no-delete guarantees for storage audit."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/diagnostics/inspect-bench-before-reclaim.sh"


class BeforeReclaimAuditTests(unittest.TestCase):
    def run_sha(self, sha: str | None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.pop("QWEN38_RECLAIM_AUDIT_SHA", None)
        if sha is not None:
            env["QWEN38_RECLAIM_AUDIT_SHA"] = sha
        return subprocess.run(
            ["bash", str(SCRIPT)], cwd=ROOT, env=env,
            capture_output=True, text=True, check=False, timeout=10,
        )

    def test_missing_sha_rejected_before_inventory(self) -> None:
        result = self.run_sha(None)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("exact_checkout_sha_required", result.stderr)
        self.assertNotIn("RECLAIM_READONLY=BEGIN", result.stdout)

    def test_short_sha_rejected(self) -> None:
        result = self.run_sha("abc")
        self.assertEqual(result.returncode, 2, result.stderr)

    def test_wrong_sha_rejected(self) -> None:
        result = self.run_sha("0" * 40)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("checkout_sha_mismatch", result.stderr)

    def test_existing_managers_readonly_only(self) -> None:
        data = SCRIPT.read_text(encoding="utf-8")
        for command in (
            'manage-storage.sh" status', 'manage-storage.sh" recommend',
            'manage-storage.sh" plan', 'manage-models.sh" assets',
            'docker system df -v', 'docker image ls', 'docker ps -a',
            'BLOCKED_PENDING_MODEL_EVIDENCE_AND_ASSET_REVIEW',
        ):
            self.assertIn(command, data)
        for command in (
            "docker rmi", "docker rm", "docker image prune",
            "docker system prune", "docker builder prune", "docker start",
            "systemctl restart", "systemctl start", "swapoff ",
            'manage-models.sh" retire', 'manage-models.sh" remove',
            'manage-storage.sh" prune', "rm -rf", "sudo ",
        ):
            self.assertNotIn(command, data)


if __name__ == "__main__":
    unittest.main()
