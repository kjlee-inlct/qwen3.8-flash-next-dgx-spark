"""Host-free Hybrid H6 managed-start policy guard tests."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/wizard/hybrid-h6-launch-admission.py"
MENU = ROOT / "scripts/wizard/model-menu.sh"
spec = importlib.util.spec_from_file_location("hybrid_h6_launch_admission", SCRIPT)
assert spec and spec.loader
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class H6LaunchAdmissionTests(unittest.TestCase):
    def test_shutdown_service_blocks_even_protected(self):
        case = dict(PHASE="complete", MODEL_PROFILE="orcarouter",
                    SERVICE_ENABLED="0", SERVICE_OWNED="0",
                    MONITOR_ENABLED="1", MONITOR_PROTECT="1", MONITOR_HEARTBEAT="60")
        self.assertEqual(guard.blockers(case),
                         ["MANAGED_PROFILE_SWITCH_REQUIRES_ENABLED_OWNED_SERVICE"])

    def test_disabled_monitor_and_heartbeat_are_blocking(self):
        case = dict(PHASE="complete", MODEL_PROFILE="orcarouter",
                    SERVICE_ENABLED="1", SERVICE_OWNED="1",
                    MONITOR_ENABLED="0", MONITOR_PROTECT="0", MONITOR_HEARTBEAT="0")
        self.assertEqual(guard.blockers(case),
                         ["PROTECTED_MONITOR_NOT_CONFIGURED", "MONITOR_HEARTBEAT_DISABLED"])

    def test_valid_metadata_is_still_not_start_authorization(self):
        case = dict(PHASE="complete", MODEL_PROFILE="orcarouter",
                    SERVICE_ENABLED="1", SERVICE_OWNED="1",
                    MONITOR_ENABLED="1", MONITOR_PROTECT="1", MONITOR_HEARTBEAT="60")
        self.assertEqual(guard.blockers(case), [])
        self.assertIn("REVIEW_ONLY_NOT_LIVE_AUTHORIZATION", SCRIPT.read_text())

    def test_bad_sha_fails_closed(self):
        result = subprocess.run(
            ["python3", "-B", str(SCRIPT), "--expected-sha", "bad",
             "--models-root", str(ROOT)],
            text=True, capture_output=True, check=False, timeout=20)
        self.assertEqual(result.returncode, 2)
        self.assertIn("HYBRID_H6_MODEL_START=NOT_PERFORMED", result.stderr)

    def test_no_host_mutation_or_unreviewed_start(self):
        content = SCRIPT.read_text()
        for bad in ("docker start", "docker run", "docker rm", "sudo ",
                    "systemctl start", "unlink(", "rmtree(", "swapoff", "git reset",
                    "install.sh", "manage-service.sh"):
            self.assertNotIn(bad, content)
        self.assertIn("hybrid-h6-launch-admission.py", MENU.read_text())


if __name__ == "__main__":
    unittest.main()
