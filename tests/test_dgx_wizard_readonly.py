"""Guard actual-DGX wizard audit before it can query the installed host."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/diagnostics/check-wizard-dgx-readonly.sh"


class DgxWizardReadonlyTests(unittest.TestCase):
    def run_with_sha(self, sha: str | None) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        env.pop("QWEN38_WIZARD_AUDIT_TARGET_SHA", None)
        if sha is not None:
            env["QWEN38_WIZARD_AUDIT_TARGET_SHA"] = sha
        return subprocess.run(
            ["bash", str(SCRIPT)], cwd=ROOT, env=env,
            text=True, capture_output=True, check=False, timeout=10,
        )

    def test_missing_target_aborts_before_host_checks(self) -> None:
        run = self.run_with_sha(None)
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertIn("exact_sha_required", run.stderr)
        self.assertNotIn("WIZARD_DGX_READONLY=BEGIN", run.stdout)

    def test_malformed_sha_is_rejected(self) -> None:
        run = self.run_with_sha("HEAD")
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertIn("exact_sha_required", run.stderr)

    def test_wrong_sha_is_rejected(self) -> None:
        run = self.run_with_sha("0" * 40)
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertIn("sha_mismatch", run.stderr)
        self.assertNotIn("WIZARD_DGX_READONLY=BEGIN", run.stdout)

    def test_only_dry_run_preview_host_operations(self) -> None:
        content = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("--yes --no-start --dry-run", content)
        self.assertIn("--yes --dry-run --purge-all", content)
        self.assertIn("STATE_DRIFT_DETECTED", content)
        self.assertIn("checkout_dirty_after", content)
        self.assertIn("PYTHONDONTWRITEBYTECODE=1", content)
        for forbidden in ("systemctl restart", "docker start", "docker rm ",
                          "sudo ", "git reset --hard"):
            self.assertNotIn(forbidden, content)


if __name__ == "__main__":
    unittest.main()
