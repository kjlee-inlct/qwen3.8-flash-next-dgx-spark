from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
BENCH = ROOT / "scripts" / "benchmark"
PREFLIGHT = BENCH / "check-orcarouter-r23-ownership-probes.sh"
RUNNER = BENCH / "run-orcarouter-managed-rmsys-r23-early-burst-ownership.sh"
ANALYZER = BENCH / "analyze-orcarouter-r23-ownership.py"
EVIDENCE = BENCH / "evidence"
PLAN = EVIDENCE / "orcarouter-managed-rmsys-r23-early-burst-ownership-plan-20261004.md"
PREFLIGHT_RESULT = EVIDENCE / "orcarouter-managed-rmsys-r23-probe-preflight-result-20261004.md"

spec = importlib.util.spec_from_file_location("r23_ownership", ANALYZER)
assert spec is not None and spec.loader is not None
r23 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r23)


class OrcaRouterR23OwnershipTraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preflight = PREFLIGHT.read_text(encoding="utf-8")
        self.runner = RUNNER.read_text(encoding="utf-8")
        self.analyzer = ANALYZER.read_text(encoding="utf-8")
        self.plan = PLAN.read_text(encoding="utf-8")
        self.preflight_result = PREFLIGHT_RESULT.read_text(encoding="utf-8")

    def test_plan_is_ownership_trace_not_broad_tuning(self) -> None:
        self.assertIn("driver/runtime ownership boundary", self.plan)
        self.assertIn("approximately startup `+20 s` through `+70 s`", self.plan)
        self.assertIn("No persistent VM tunable is changed", self.plan)
        self.assertIn("Cumulative RM requested bytes are **activity volume**", self.plan)

    def test_host_preflight_is_recorded_as_pass_without_live_test(self) -> None:
        self.assertIn("PREFLIGHT PASS / LIVE TEST NOT YET RUN", self.preflight_result)
        self.assertIn("target_count=6", self.preflight_result)
        self.assertIn("event_count=12", self.preflight_result)
        self.assertIn("model_restart=NO", self.preflight_result)
        self.assertIn("persistent_vm_tuning=NO", self.preflight_result)

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

    def test_runner_uses_fixed_narrow_window_and_same_managed_runtime(self) -> None:
        self.assertIn("TRACE_ARM_DELAY_S=20", self.runner)
        self.assertIn("TRACE_DURATION_S=50", self.runner)
        self.assertIn('CONTAINER="qwen38-flash-next"', self.runner)
        self.assertIn("DEFAULT_KV_MEM=17179869184", self.runner)
        self.assertIn('create --runtime-root "${CURRENT_LINK}" --start --yes', self.runner)
        self.assertIn("replacement-request-monotonic-ns.txt", self.runner)
        self.assertIn("trace-window-start-monotonic-ns.txt", self.runner)
        self.assertIn("trace-window-end-monotonic-ns.txt", self.runner)
        self.assertIn("15.0 <= start_offset <= 30.0", self.runner)
        self.assertIn("45.0 <= duration <= 60.0", self.runner)

    def test_runner_preserves_r21_conditioning_as_fixed_harness(self) -> None:
        self.assertIn("systemctl stop", self.runner)
        self.assertIn("sync", self.runner)
        self.assertIn("/proc/sys/vm/drop_caches", self.runner)
        self.assertIn("/proc/sys/vm/compact_memory", self.runner)
        self.assertIn("poststop-after-compact", self.runner)
        for forbidden_tuning in (
            "watermark_scale_factor=",
            "compaction_proactiveness=",
            "min_free_kbytes=",
            "swappiness=",
        ):
            with self.subTest(forbidden_tuning=forbidden_tuning):
                self.assertNotIn(forbidden_tuning, self.runner)

    def test_runner_records_only_selected_driver_boundaries(self) -> None:
        for token in (
            "nv_alloc_pages_entry",
            "nv_alloc_system_pages_entry",
            "pma_alloc_entry",
            "uvm_dma_alloc_entry",
            "uvm_mem_alloc_entry",
            "uvm_pmm_alloc_entry",
        ):
            self.assertIn(token, self.runner)
        for forbidden_event in (
            "kmem:mm_page_alloc",
            "kmem:mm_page_free",
            "mm_page_alloc_extfrag",
            "compaction:mm_",
            "vmscan:mm_",
            "function_graph",
            "sched_switch",
        ):
            with self.subTest(forbidden_event=forbidden_event):
                self.assertNotIn(forbidden_event, self.runner)
        self.assertIn("nvidia:nvidia_dev_xid", self.runner)

    def test_runner_keeps_recovery_armed_during_async_managed_start(self) -> None:
        stop_index = self.runner.index("SERVICE_RECOVERY_ARMED=1")
        launch_index = self.runner.index('sudo -n /bin/bash "${MANAGE_SERVICE}"', stop_index)
        clear_index = self.runner.index("SERVICE_RECOVERY_ARMED=0", launch_index)
        wait_index = self.runner.index('wait "${MANAGED_PID}"', launch_index)
        self.assertLess(stop_index, launch_index)
        self.assertLess(launch_index, wait_index)
        self.assertLess(wait_index, clear_index)
        self.assertIn('stop_background_pid "${MANAGED_PID}"', self.runner)
        self.assertIn('! systemctl is-active --quiet "${UNIT}"', self.runner)
        self.assertIn('sudo -n systemctl start "${UNIT}"', self.runner)
        self.assertIn("managed start exited before replacement was observed", self.runner)

    def test_runner_has_cleanup_identity_and_strict_classification(self) -> None:
        self.assertIn("cleanup_probes", self.runner)
        self.assertIn("SUDO_KEEPALIVE_PID", self.runner)
        self.assertIn("RESTART_OBSERVED", self.runner)
        self.assertIn("RELEASE_STABLE", self.runner)
        self.assertIn("TRACE_WINDOW_VALID", self.runner)
        self.assertIn('FUNCTIONAL_CLASS="PASS"', self.runner)
        self.assertIn('HOST_CLASS="FAIL"', self.runner)
        self.assertIn("NV_ERR_NO_MEMORY|_memdescAllocInternal", self.runner)

    def test_analyzer_emits_complete_window_and_boundary_metrics(self) -> None:
        for token in (
            "trace_window_start_from_container_started_s",
            ".first_monotonic=",
            ".last_monotonic=",
            "window_boundary_capable=1",
            "unmatched_entries",
            "unmatched_returns",
            "activity_volume_not_resident_ownership",
            "node0_normal_free_delta_mib",
            "nr_free_pages_delta_mib",
            "normal_unmovable_order4plus_mib",
            "normal_movable_order4plus_mib",
            "milestone_nearest_",
            "ownership_discriminator",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.analyzer)

    def test_analyzer_residual_buddy_and_pagetype_weighting(self) -> None:
        base = {
            "MemFree": 1000.0,
            "Active(anon)": 10.0,
            "Inactive(anon)": 10.0,
            "Active(file)": 10.0,
            "Inactive(file)": 10.0,
            "Unevictable": 0.0,
            "Slab": 20.0,
            "KReclaimable": 5.0,
            "SReclaimable": 5.0,
            "PageTables": 1.0,
            "SecPageTables": 0.0,
            "KernelStack": 1.0,
        }
        now = dict(base)
        now["MemFree"] = 900.0
        now["Active(anon)"] = 20.0
        self.assertAlmostEqual(r23.residual(base, now), 90.0)

        buddy = ["Node 0, zone   Normal      1 2 0"]
        self.assertAlmostEqual(
            r23.normal_free_mib(buddy, 4096),
            20 * 1024 / 1024 / 1024,
        )

        pagetype = [
            "Node 0, zone Normal, type Unmovable 1 1 1 1 2 1 0",
        ]
        expected_pages = 2 * (1 << 4) + 1 * (1 << 5)
        self.assertAlmostEqual(
            r23.pagetype_high_mib(pagetype, 4096, "Unmovable"),
            expected_pages * 4096 / 1048576,
        )


if __name__ == "__main__":
    unittest.main()
