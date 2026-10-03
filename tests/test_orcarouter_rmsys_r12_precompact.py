from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
RUNNER = ROOT / "scripts" / "benchmark" / "run-orcarouter-managed-rmsys-r12-precompact.sh"


class OrcaRouterRmSysR12PrecompactTests(unittest.TestCase):
    def test_runner_wraps_r11_without_changing_runtime_contract(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("run-orcarouter-managed-rmsys-r11.sh", text)
        self.assertIn('ORCA_R11_OUT="${R11_OUT}"', text)
        self.assertIn('RUN_VALID="$(grep -E \'^run_valid=\'', text)

    def test_runner_uses_one_shot_compact_memory(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        compact_write = "printf '1\\n' | sudo -n tee /proc/sys/vm/compact_memory >/dev/null"
        self.assertEqual(text.count(compact_write), 1)
        self.assertNotIn("tee /proc/sys/vm/compaction_proactiveness", text)
        self.assertNotIn("tee /proc/sys/vm/extfrag_threshold", text)
        self.assertNotIn("tee /proc/sys/vm/watermark_scale_factor", text)
        self.assertNotIn("tee /proc/sys/vm/watermark_boost_factor", text)

    def test_runner_records_allocator_state_before_and_after_compaction(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        for token in (
            "/proc/buddyinfo",
            "/proc/pagetypeinfo",
            "/proc/zoneinfo",
            "/proc/meminfo",
            "/proc/vmstat",
            "/proc/pressure/memory",
            "before-buddyinfo.txt",
            "after-buddyinfo.txt",
            "precompact-buddy-summary.txt",
        ):
            self.assertIn(token, text)

    def test_runner_preserves_current_vm_tunables(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        for name in (
            "compaction_proactiveness",
            "compact_unevictable_allowed",
            "extfrag_threshold",
            "min_free_kbytes",
            "watermark_boost_factor",
            "watermark_scale_factor",
        ):
            self.assertIn(name, text)
        self.assertIn("vm-tunables.txt", text)

    def test_result_distinguishes_clean_from_recoverable_rm_oom(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("ORCA_R12_RESULT=VALID_CLEAN", text)
        self.assertIn("ORCA_R12_RESULT=VALID_RM_OOM", text)
        self.assertIn("ORCA_R12_RESULT=INVALID", text)


if __name__ == "__main__":
    unittest.main()
