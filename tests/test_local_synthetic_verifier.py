"""Guard the exact-SHA, host-denying synthetic DGX test entry point."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "lifecycle" / "verify-synthetic.sh"


class LocalSyntheticVerifierTests(unittest.TestCase):
    def invoke(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(SCRIPT), *args],
            cwd=ROOT,
            env={**os.environ, "GITHUB_ACTIONS": "false"},
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )

    def test_script_has_valid_bash_syntax(self) -> None:
        result = subprocess.run(
            ["bash", "-n", str(SCRIPT)],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_sha_is_rejected_before_any_tests(self) -> None:
        result = self.invoke()
        self.assertEqual(result.returncode, 2)
        self.assertIn("exact_sha", result.stderr)
        self.assertNotIn("SYNTHETIC_TEST=", result.stdout)

    def test_wrong_sha_is_rejected_before_any_tests(self) -> None:
        result = self.invoke("0" * 40)
        self.assertEqual(result.returncode, 2)
        self.assertIn("checkout_sha_mismatch", result.stderr)
        self.assertNotIn("SYNTHETIC_TEST=", result.stdout)

    def test_ci_override_is_rejected_for_operator(self) -> None:
        sha = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True
        ).strip()
        result = self.invoke(sha, "--ci")
        self.assertEqual(result.returncode, 2)
        self.assertIn("ci_flag_requires_github_actions", result.stderr)

    def test_runtime_mutators_are_denied_and_only_synthetic_tests_selected(self) -> None:
        body = SCRIPT.read_text(encoding="utf-8")
        for required in (
            "checkout_sha_mismatch",
            "remote_tracking_sha_mismatch",
            "dirty_checkout",
            "dirty_checkout_after_test",
            "XDG_STATE_HOME",
            "XDG_DATA_HOME",
            "PYTHONDONTWRITEBYTECODE",
            "DENIED_HOST_COMMAND",
            "test_uninstall_wizard_preview.py",
            "test_asset_ownership.py",
            "test_operation_lock.py",
            "test_lifecycle_integration.py",
            "test_managed_lifecycle_readonly_snapshot.py",
            "LOCAL_SYNTHETIC_HOST_COMMANDS=PATH_DENY_STUBS",
            "LOCAL_SYNTHETIC_RESULT=PASS",
            "MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED",
        ):
            self.assertIn(required, body)
        for forbidden in (
            "git pull ", "git fetch ", "git merge ", "git reset ",
            "systemctl start ", "systemctl restart ", "docker run ",
            "docker rm -f ", "uninstall.sh --purge",
            "unittest discover -s tests -v",
        ):
            self.assertNotIn(forbidden, body)


if __name__ == "__main__":
    unittest.main()
