"""Guardrails for exact-SHA no-restart runtime-offline metadata audit."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/lifecycle/inspect-readonly-runtime-offline.sh"


class ManagedRuntimeOfflineReadOnlyTests(unittest.TestCase):
    def test_shell_syntax(self) -> None:
        proc = subprocess.run(
            ["bash", "-n", str(SCRIPT)], capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_missing_exact_sha_fails_before_host_queries(self) -> None:
        env = os.environ.copy()
        env.pop("QWEN38_OFFLINE_DIAGNOSTIC_TARGET_SHA", None)
        proc = subprocess.run(
            ["bash", str(SCRIPT)], env=env, capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("exact_checkout_sha_required", proc.stderr)
        self.assertNotIn("container_state", proc.stdout)

    def test_only_readonly_targeted_metadata_commands_are_present(self) -> None:
        body = SCRIPT.read_text(encoding="utf-8")
        for marker in (
            "QWEN38_OFFLINE_DIAGNOSTIC_TARGET_SHA",
            "checkout_sha_mismatch",
            "dirty_checkout",
            "docker inspect",
            ".State.ExitCode",
            ".State.OOMKilled",
            ".HostConfig.PortBindings",
            "systemctl show",
            "runtime-commit.env runtime-stop.env monitor.pid",
            "stat -c",
            "MANAGED_RUNTIME_OFFLINE=COLLECTED_READ_ONLY",
            "MANAGED_RUNTIME_OFFLINE=PARTIAL_READ_FAILURE",
            "RUNTIME_STOP_REASON=NOT_YET_PROVEN",
            "RUNTIME_ATTESTATION_VALIDITY=NOT_PROVEN",
            "MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED",
        ):
            self.assertIn(marker, body)
        for forbidden in (
            "docker run", "docker start", "docker restart", "docker rm",
            "docker exec", "docker image", "systemctl restart",
            "systemctl start", "sudo ", "journalctl", "rm -",
            "git fetch", "git reset", "git pull", "git switch",
            "uninstall.sh", "install.sh", "chmod ", "kill ",
        ):
            self.assertNotIn(forbidden, body)

    def test_status_collection_does_not_claim_runtime_qualification(self) -> None:
        body = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("HOST_STABILITY=PASS", body)
        self.assertNotIn("MANAGED_LIFECYCLE_LIVE_E2E=PASS", body)
        self.assertIn("H38_MODEL_GPU_RERUN=BLOCKED", body)


if __name__ == "__main__":
    unittest.main()
