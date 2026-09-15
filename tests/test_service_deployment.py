from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class ServiceDeploymentTests(unittest.TestCase):
    def test_service_has_bounded_restart_and_loopback_runner(self) -> None:
        manager = (ROOT / "scripts" / "manage-service.sh").read_text(encoding="utf-8")
        runner = (ROOT / "scripts" / "service-runner.sh").read_text(encoding="utf-8")
        self.assertIn("StartLimitBurst=2", manager)
        self.assertIn("Restart=on-failure", manager)
        self.assertIn("docker stop --timeout 30", manager)
        self.assertIn("WantedBy=multi-user.target", manager)
        self.assertNotIn('docker rm -f "${CONTAINER_NAME}"', manager)
        self.assertIn("PUBLISH_HOST=127.0.0.1", runner)
        self.assertIn("RESTART_POLICY=no", runner)
        self.assertIn("docker wait", runner)
        self.assertIn("preflight-runtime.sh", runner)
        self.assertIn("runtime-transition.sh\" recover", runner)
        server = (ROOT / "scripts" / "serve.sh").read_text(encoding="utf-8")
        self.assertIn("--init", server)

    def test_memory_protection_stop_is_not_restarted_as_failure(self) -> None:
        monitor = (ROOT / "scripts" / "monitor-runtime.sh").read_text(encoding="utf-8")
        runner = (ROOT / "scripts" / "service-runner.sh").read_text(encoding="utf-8")
        self.assertIn("runtime-stop.env", monitor)
        self.assertIn("STOP_REASON=%q", monitor)
        self.assertIn("STOP_CONTAINER_NAME=%q", monitor)
        self.assertIn("STOP_CONTAINER_ID=%q", monitor)
        self.assertIn("runtime-stop.env", runner)
        self.assertIn("memory-protection", runner)
        self.assertIn('"${STOP_CONTAINER_ID:-}" == "${container_id}"', runner)
        self.assertIn("leaving service stopped", runner)
        self.assertIn("exit 0", runner)
        self.assertIn("ignoring stale runtime stop marker", runner)

    def test_doctor_checks_runtime_lifecycle_drift(self) -> None:
        doctor = (ROOT / "scripts" / "doctor.sh").read_text(encoding="utf-8")
        self.assertIn("runtime-transition.env", doctor)
        self.assertIn("no incomplete runtime transition exists", doctor)
        self.assertIn("no stale rollback container exists", doctor)
        self.assertIn("runtime container image matches installation manifest", doctor)
        self.assertIn("runtime model mount matches installation manifest", doctor)
        self.assertIn("runtime served model name matches installation manifest", doctor)
        self.assertIn("runtime image drift", doctor)
        self.assertIn("runtime model mount drift", doctor)
        self.assertIn("runtime served-name drift", doctor)

    def test_uninstaller_removes_only_owned_service(self) -> None:
        uninstaller = (ROOT / "uninstall.sh").read_text(encoding="utf-8")
        self.assertIn('if [[ "${SERVICE_OWNED}" == 1 ]]', uninstaller)
        self.assertIn('manage-service.sh" remove --yes', uninstaller)


if __name__ == "__main__":
    unittest.main()
