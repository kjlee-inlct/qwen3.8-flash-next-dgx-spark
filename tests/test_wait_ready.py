from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "runtime" / "wait-ready.sh"


class WaitReadyDiagnosticsTests(unittest.TestCase):
    def test_failure_path_prints_root_cause_and_large_log_tail(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('FAILURE_LOG_TAIL="${FAILURE_LOG_TAIL:-300}"', script)
        self.assertIn("print_failure_diagnostics()", script)
        self.assertIn("ROOT CAUSE CANDIDATES", script)
        self.assertIn("LAST %s LOG LINES", script)
        self.assertIn("ValueError", script)
        self.assertIn("RuntimeError", script)
        self.assertIn("weight_scale", script)
        self.assertIn("scale_inv", script)

    def test_stopped_and_timeout_paths_use_failure_diagnostics(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertGreaterEqual(script.count('print_failure_diagnostics "${CONTAINER}"'), 2)


    def test_wait_ready_reports_container_disappearance_events(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("seen_container=0", script)
        self.assertIn("CONTAINER DISAPPEARED", script)
        self.assertIn("print_container_events", script)
        self.assertIn("docker events", script)
        self.assertIn('--filter "container=${CONTAINER}"', script)


    def test_wait_ready_rejects_missing_initial_container(self) -> None:
        script = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("container not found before readiness wait", script)
        self.assertIn('docker inspect "${CONTAINER}"', script)
        self.assertIn("seen_container=1", script)


if __name__ == "__main__":
    unittest.main()
