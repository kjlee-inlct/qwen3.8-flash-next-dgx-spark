from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
RUNNER = ROOT / "scripts" / "benchmark" / "run-orcarouter-managed-rmsys-r11.sh"
COLLECTOR = ROOT / "scripts" / "benchmark" / "collect-linux-allocator-state.py"


class OrcaRouterRmSysR11Tests(unittest.TestCase):
    def test_runner_reuses_r10b_trace_contract(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("run-orcarouter-managed-rmsys-r10b.sh", text)
        self.assertIn('ORCA_R10B_OUT="${R10B_OUT}"', text)
        self.assertIn('RUN_VALID="$(cat "${R10B_OUT}/run-valid.txt"', text)

    def test_runner_requires_allocator_collector_success(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("collector.rc", text)
        self.assertIn('"${COLLECTOR_RC}" != 0', text)
        self.assertIn("event_snapshot_count", text)
        self.assertIn("fast_sample_count", text)
        self.assertIn("slow_sample_count", text)

    def test_collector_samples_allocator_state(self) -> None:
        text = COLLECTOR.read_text(encoding="utf-8")
        for token in (
            "/proc/buddyinfo",
            "/proc/pagetypeinfo",
            "/proc/zoneinfo",
            "/proc/meminfo",
            "/proc/vmstat",
            "/proc/pressure/memory",
        ):
            self.assertIn(token, text)

    def test_collector_triggers_full_snapshot_on_rm_oom(self) -> None:
        text = COLLECTOR.read_text(encoding="utf-8")
        self.assertIn("NV_ERR_NO_MEMORY", text)
        self.assertIn("_memdescAllocInternal", text)
        self.assertIn("rm-oom-", text)
        self.assertIn("/usr/bin/journalctl", text)


if __name__ == "__main__":
    unittest.main()
