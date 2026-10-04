from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
ANALYZER = (
    ROOT
    / "scripts"
    / "benchmark"
    / "analyze-orcarouter-r23-rm-uvm-overlap.py"
)

spec = importlib.util.spec_from_file_location("r23_rm_uvm_overlap", ANALYZER)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class OrcaRouterR23RmUvmOverlapTests(unittest.TestCase):
    def test_analyzer_is_read_only_post_hoc(self) -> None:
        text = ANALYZER.read_text(encoding="utf-8")
        self.assertIn("analysis_mode=read_only_post_hoc_no_restart", text)
        self.assertIn("activity_volume_not_resident_ownership", text)
        self.assertIn("temporal_same_pid_nesting_not_causal_proof", text)
        for forbidden in (
            "systemctl stop",
            "systemctl start",
            "manage-service.sh",
            "/proc/sys/vm/drop_caches",
            "/proc/sys/vm/compact_memory",
            "trace-cmd record",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)

    def test_parse_burst(self) -> None:
        start, end, residual = mod.parse_burst(
            "residual_largest_5s.found=1 "
            "start_monotonic=10.000000000 "
            "end_monotonic=15.000000000 delta_mib=+75083.652\n"
        )
        self.assertEqual(start, 10.0)
        self.assertEqual(end, 15.0)
        self.assertAlmostEqual(residual, 75083.652)

    def test_pairing_and_same_pid_nesting(self) -> None:
        trace = "\n".join(
            (
                "VLLM::Worker-100 [000] .... 10.000000: uvm_mem_alloc_entry:",
                "VLLM::Worker-100 [000] .... 10.100000: nv_alloc_pages_entry: page_count=256 page_size=65536 contiguous=0 node_id=-1",
                "VLLM::Worker-100 [000] .... 10.200000: nv_alloc_pages_ret: ret=0",
                "VLLM::Worker-100 [000] .... 10.300000: nv_alloc_system_pages_entry: at=0x1000",
                "VLLM::Worker-100 [000] .... 10.400000: nv_alloc_system_pages_ret: ret=0",
                "VLLM::Worker-100 [000] .... 10.500000: uvm_mem_alloc_ret: raw_ret=0",
                "python3-200 [001] .... 10.150000: nv_alloc_pages_entry: page_count=128 page_size=65536 contiguous=0 node_id=-1",
                "python3-200 [001] .... 10.250000: nv_alloc_pages_ret: ret=0",
            )
        )
        calls, unmatched_entries, unmatched_returns = mod.parse_calls(trace)
        self.assertEqual(len(calls["uvm_mem_alloc"]), 1)
        self.assertEqual(len(calls["nv_alloc_pages"]), 2)
        self.assertEqual(len(calls["nv_alloc_system_pages"]), 1)
        self.assertEqual(unmatched_entries["nv_alloc_pages"], 0)
        self.assertEqual(unmatched_returns["nv_alloc_pages"], 0)

        parent = calls["uvm_mem_alloc"][0]
        worker_page = next(call for call in calls["nv_alloc_pages"] if call.pid == 100)
        other_page = next(call for call in calls["nv_alloc_pages"] if call.pid == 200)
        self.assertTrue(mod.nested(parent, worker_page))
        self.assertFalse(mod.nested(parent, other_page))
        self.assertTrue(mod.is_order4(worker_page))
        self.assertEqual(mod.logical_bytes(worker_page, 4096), 256 * 4096)

    def test_overlap_discriminator_contract_is_present(self) -> None:
        text = ANALYZER.read_text(encoding="utf-8")
        for token in (
            "nv_alloc_pages.order4_activity_mib.burst5",
            "burst5.order4_activity_minus_residual_mib",
            "uvm_mem_alloc.coverage_of_burst5_order4_activity_pct",
            "uvm_mem_alloc.coverage_of_nv_alloc_system_pages_calls_pct",
            "UVM_MEM_ALLOC_BRACKETS_MOST_BURST_RM_ACTIVITY",
            "UVM_MEM_ALLOC_ADJACENT_OR_INCIDENTAL_TO_BURST_RM_ACTIVITY",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)


if __name__ == "__main__":
    unittest.main()
