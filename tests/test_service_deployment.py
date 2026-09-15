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
        self.assertIn("WantedBy=multi-user.target", manager)
        self.assertIn("PUBLISH_HOST=127.0.0.1", runner)
        self.assertIn("RESTART_POLICY=no", runner)
        self.assertIn("docker wait", runner)

    def test_uninstaller_removes_only_owned_service(self) -> None:
        uninstaller = (ROOT / "uninstall.sh").read_text(encoding="utf-8")
        self.assertIn('if [[ "${SERVICE_OWNED}" == 1 ]]', uninstaller)
        self.assertIn('manage-service.sh" remove --yes', uninstaller)


if __name__ == "__main__":
    unittest.main()
