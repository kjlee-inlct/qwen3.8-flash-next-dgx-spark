from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
RUNNER = ROOT / "scripts" / "benchmark" / "run-orcarouter-managed-rmsys-r19-stoponly-control.sh"


class OrcaRouterRmSysR19StopOnlyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = RUNNER.read_text(encoding="utf-8")

    def test_requires_aged_predecessor(self) -> None:
        self.assertIn("ORCA_R19_MIN_PREDECESSOR_AGE_S:-2700", self.text)
        self.assertIn("predecessor runtime is younger than required R19 minimum", self.text)

    def test_fully_stops_before_restart(self) -> None:
        self.assertIn('sudo -n systemctl stop "${UNIT}"', self.text)
        self.assertIn("managed container is still running after service stop", self.text)
        self.assertIn('snapshot_proc "${OUT}/poststop-before-start"', self.text)

    def test_control_does_not_compact_or_tune_vm(self) -> None:
        self.assertNotIn("/proc/sys/vm/compact_memory", self.text)
        self.assertNotIn("/proc/sys/vm/watermark_scale_factor", self.text)
        self.assertNotIn("/proc/sys/vm/compaction_proactiveness", self.text)
        self.assertIn("R19 control contract", self.text)

    def test_same_managed_release_contract(self) -> None:
        self.assertIn("CURRENT_RELEASE", self.text)
        self.assertIn("DEFAULT_KV_MEM=17179869184", self.text)
        self.assertIn('"${MANAGE_SERVICE}" create --runtime-root "${CURRENT_LINK}" --start --yes', self.text)

    def test_validity_requires_restart_and_ready(self) -> None:
        self.assertIn("restart-observed.txt", self.text)
        self.assertIn("api-ready.txt", self.text)
        self.assertIn("run-valid.txt", self.text)
        self.assertIn('"${RESTART_OBSERVED}" != 1', self.text)
        self.assertIn('"${API_READY}" != 1', self.text)

    def test_strict_rm_classification(self) -> None:
        self.assertIn("rm_oom_count", self.text)
        self.assertIn("ORCA_R19_RESULT=VALID_CLEAN", self.text)
        self.assertIn("ORCA_R19_RESULT=VALID_RM_OOM", self.text)


if __name__ == "__main__":
    unittest.main()
