"""Guardrails for the non-mutating on-host managed-lifecycle status snapshot."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/lifecycle/inspect-readonly-lifecycle.sh"


class ManagedLifecycleReadonlySnapshotTests(unittest.TestCase):
    def test_bash_syntax(self) -> None:
        result = subprocess.run(
            ["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_operator_requires_exact_commit(self) -> None:
        env = os.environ.copy()
        env.pop("QWEN38_LIFECYCLE_AUDIT_TARGET_SHA", None)
        result = subprocess.run(
            ["bash", str(SCRIPT)], env=env, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("exact_checkout_sha_required", result.stderr)

    def test_readonly_scope_is_bounded_to_inventory_status_doctor(self) -> None:
        body = SCRIPT.read_text(encoding="utf-8")
        for required in (
            "QWEN38_LIFECYCLE_AUDIT_TARGET_SHA",
            "checkout_sha_mismatch",
            "dirty_checkout",
            "git -C",
            "install.sh\" --list-models",
            "install.sh\" --list-backends",
            "profile-switch-transition.sh\" status",
            "runtime-transition.sh\" status",
            "update-transition.sh\" status",
            "release-profile-refresh-transition.sh\" status",
            "doctor.sh\"",
            "MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED",
            "MANAGED_LIFECYCLE_READONLY=PARTIAL_CHECK_FAILURE",
        ):
            self.assertIn(required, body)
        for unsafe in (
            "docker run", "docker rm", "docker image rm", "--purge-all",
            "--purge-model", "--purge-swap", "--purge-image",
            "systemctl restart", "sudo ", "apt install", "git reset",
            "git switch", "git merge", "git pull", "git fetch",
        ):
            self.assertNotIn(unsafe, body)
        self.assertNotIn('bash "${ROOT}/uninstall.sh"', body)

    def test_does_not_claim_lifecycle_e2e_on_status_success(self) -> None:
        body = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("MANAGED_LIFECYCLE_READONLY=COLLECTED_READ_ONLY", body)
        self.assertNotIn("MANAGED_LIFECYCLE_LIVE_E2E=PASS", body)
        self.assertNotIn("HOST_STABILITY=PASS", body)


if __name__ == "__main__":
    unittest.main()
