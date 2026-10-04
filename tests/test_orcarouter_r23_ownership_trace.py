from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
PREFLIGHT = ROOT / "scripts" / "benchmark" / "check-orcarouter-r23-ownership-probes.sh"
PLAN = (
    ROOT
    / "scripts"
    / "benchmark"
    / "evidence"
    / "orcarouter-managed-rmsys-r23-early-burst-ownership-plan-20261004.md"
)


class OrcaRouterR23OwnershipTraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preflight = PREFLIGHT.read_text(encoding="utf-8")
        self.plan = PLAN.read_text(encoding="utf-8")

    def test_plan_is_ownership_trace_not_broad_tuning(self) -> None:
        self.assertIn("DESIGN / NO TEST", self.plan)
        self.assertIn("driver/runtime ownership boundary", self.plan)
        self.assertIn("approximately startup `+20 s` through `+70 s`", self.plan)
        self.assertIn("No persistent VM tunable is changed", self.plan)
        self.assertIn("Cumulative RM requested bytes are **activity volume**", self.plan)

    def test_preflight_contains_required_rm_and_uvm_boundaries(self) -> None:
        for token in (
            "nv_alloc_pages",
            "nv_alloc_system_pages",
            "nvUvmInterfacePmaAllocPages",
            "uvm_gpu_dma_alloc",
            "uvm_mem_alloc",
            "uvm_pmm_gpu_alloc_kernel",
            "page_count=$arg2:u32",
            "page_size=$arg3:u64",
            "contiguous=$arg4:u8",
            "cache_type=$arg5:u32",
            "zeroed=$arg6:u8",
            "unencrypted=$arg7:u8",
            "node_id=$arg8:s32",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.preflight)

    def test_preflight_is_probe_only(self) -> None:
        for forbidden in (
            "systemctl stop",
            "systemctl start",
            "docker run",
            "docker stop",
            "manage-service.sh",
            "/proc/sys/vm/drop_caches",
            "/proc/sys/vm/compact_memory",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.preflight)
        self.assertIn("model_restart=NO", self.preflight)
        self.assertIn("persistent_vm_tuning=NO", self.preflight)

    def test_preflight_uses_narrow_dynamic_trace_only(self) -> None:
        self.assertIn('GROUP="r23_own"', self.preflight)
        self.assertIn("trace-cmd record", self.preflight)
        self.assertIn("-C mono", self.preflight)
        for forbidden_event in (
            "-e kmem:mm_page_alloc",
            "-e kmem:mm_page_free",
            "-e kmem:mm_page_alloc_extfrag",
            "-e compaction:",
            "-e vmscan:",
            "function_graph",
            "sched_switch",
        ):
            with self.subTest(forbidden_event=forbidden_event):
                self.assertNotIn(forbidden_event, self.preflight)

    def test_preflight_has_cleanup_and_one_write_per_probe_command(self) -> None:
        self.assertIn("cleanup_probes", self.preflight)
        self.assertIn("disable_probe_events", self.preflight)
        self.assertIn("os.open(path, os.O_WRONLY)", self.preflight)
        self.assertIn("os.write(fd, command + b\"\\n\")", self.preflight)
        self.assertIn("stale ${GROUP} probes remain", self.preflight)
        self.assertIn("R23_PROBE_PREFLIGHT=PASS", self.preflight)


if __name__ == "__main__":
    unittest.main()
