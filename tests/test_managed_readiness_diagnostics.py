from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class ManagedReadinessDiagnosticsTests(unittest.TestCase):
    def test_failure_path_reports_service_monitor_and_container_context(self) -> None:
        manager = (ROOT / "scripts" / "manage-service.sh").read_text(encoding="utf-8")

        self.assertIn("print_readiness_failure_diagnostics()", manager)
        self.assertIn("ActiveState,SubState,Result,ExecMainCode,ExecMainStatus", manager)
        self.assertIn('journalctl -u "${UNIT}" -n 120 --no-pager -o cat', manager)
        self.assertIn('local monitor_log="${STATE_DIR}/monitor.log"', manager)
        self.assertIn("oom_killed={{.State.OOMKilled}}", manager)
        self.assertIn('docker logs --timestamps --tail 200 "${CONTAINER_NAME}"', manager)

    def test_inactive_and_timeout_paths_dump_diagnostics_before_failing(self) -> None:
        manager = (ROOT / "scripts" / "manage-service.sh").read_text(encoding="utf-8")

        inactive_diagnostics = 'print_readiness_failure_diagnostics "${candidate_container_id}"'
        inactive_failure = 'die "service stopped before readiness (state=${unit_state})"'
        timeout_diagnostics = 'print_readiness_failure_diagnostics "${candidate_container_id:-}"'
        timeout_failure = 'die "replacement runtime did not commit and attest within 30 minutes"'

        self.assertIn(inactive_diagnostics, manager)
        self.assertIn(inactive_failure, manager)
        self.assertLess(manager.index(inactive_diagnostics), manager.index(inactive_failure))
        self.assertIn(timeout_diagnostics, manager)
        self.assertIn(timeout_failure, manager)
        self.assertLess(manager.index(timeout_diagnostics), manager.index(timeout_failure))

    def test_read_only_collector_covers_lifecycle_service_monitor_container_and_kernel(self) -> None:
        collector = (
            ROOT / "scripts" / "runtime" / "collect-managed-readiness-evidence.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("update-transition.sh", collector)
        self.assertIn("runtime-transition.sh", collector)
        self.assertIn("profile-switch-transition.sh", collector)
        self.assertIn('journalctl -u "${UNIT}" --since "${SINCE}"', collector)
        self.assertIn('"${STATE_DIR}/monitor.log"', collector)
        self.assertIn("oom_killed={{.State.OOMKilled}}", collector)
        self.assertIn("NV_ERR_NO_MEMORY", collector)
        self.assertIn("_memdescAllocInternal", collector)
        self.assertNotIn("docker stop", collector)
        self.assertNotIn("systemctl stop", collector)
        self.assertNotIn("systemctl start", collector)


if __name__ == "__main__":
    unittest.main()
