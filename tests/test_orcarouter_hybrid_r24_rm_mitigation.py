from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
BENCH = ROOT / "scripts" / "benchmark"
RUNNER = BENCH / "run-orcarouter-hybrid-r24-kv16-rm-mitigation.sh"
ANALYZER = BENCH / "analyze-orcarouter-hybrid-r24-rm-mitigation.py"
PLAN = (
    BENCH
    / "evidence"
    / "orcarouter-hybrid-r24-kv16-rm-mitigation-plan-20261004.md"
)


class OrcaRouterHybridR24MitigationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = RUNNER.read_text(encoding="utf-8")
        self.analyzer = ANALYZER.read_text(encoding="utf-8")
        self.plan = PLAN.read_text(encoding="utf-8")

    def test_plan_uses_r22_as_matched_control(self) -> None:
        self.assertIn("canonical comparison baseline is R22", self.plan)
        self.assertIn("`+75138.043 MiB`", self.plan)
        self.assertIn("`17179869184` bytes (`16 GiB`)", self.plan)
        self.assertIn("managed `orcarouter-hybrid` profile currently defaults to `24 GiB` KV", self.plan)
        self.assertIn("not used for the first R24 run", self.plan)

    def test_candidate_is_h6_modelopt_w4a16_with_kv16(self) -> None:
        for token in (
            "orcarouter-hybrid",
            "qwen3.8-h6-modelopt-w4a16",
            "orcarouter-hybrid/Qwen3.8-Flash-Next-Uncensored-NVFP4",
            "vllm-orcarouter-v029:v1",
            "KV_BYTES=17179869184",
            "DEFAULT_KV_MEM=25769803776",
            "MAXLEN=262144",
            "NSPEC=2",
            "GPU_UTIL=0.80",
            "MAXSEQS=3",
            "QSA_EXACT_TOPK=1",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.runner)

    def test_h6_manifest_and_parent_identity_are_guarded(self) -> None:
        for token in (
            '"variant": "h6-modelopt-w4a16"',
            '"parent_variant": "h5-neutral-input-scale"',
            '"expert_value_source": "orcarouter-h4-all"',
            '"input_scale_source": "h5-neutral-1.0"',
            '"quant_algo_before": "NVFP4"',
            '"quant_algo_after": "W4A16_NVFP4"',
            '"safetensor_bytes_changed": 0',
            '"mtp_tensors_changed": 0',
            '"/base-model"',
            '"/h3-model"',
            '"/h4-all"',
            '"/h5-parent"',
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.runner)

    def test_runner_preserves_r21_conditioning_and_r22_protection(self) -> None:
        for token in (
            'systemctl stop "${UNIT}"',
            "sync",
            "/proc/sys/vm/drop_caches",
            "/proc/sys/vm/compact_memory",
            "poststop-after-compact",
            "--min-free-gib 2",
            "--free-gate-gib 10",
            "--min-swap-free-gib 8",
            "--consecutive 5",
            "--protect",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.runner)
        for forbidden in (
            "watermark_scale_factor=",
            "compaction_proactiveness=",
            "min_free_kbytes=",
            "swappiness=",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.runner)

    def test_runner_uses_rm_only_narrow_trace(self) -> None:
        self.assertIn("TRACE_ARM_DELAY_S=20", self.runner)
        self.assertIn("TRACE_DURATION_S=50", self.runner)
        for token in (
            "nv_alloc_pages_entry",
            "nv_alloc_pages_ret",
            "nv_alloc_system_pages_entry",
            "nv_alloc_system_pages_ret",
            "page_count=$arg2:u32",
            "page_size=$arg3:u64",
            "node_id=$arg8:s32",
            "nvidia:nvidia_dev_xid",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.runner)
        for forbidden in (
            "pma_alloc_entry",
            "uvm_dma_alloc_entry",
            "uvm_mem_alloc_entry",
            "uvm_pmm_alloc_entry",
            "kmem:mm_page_alloc",
            "kmem:mm_page_free",
            "mm_page_alloc_extfrag",
            "compaction:mm_",
            "vmscan:mm_",
            "function_graph",
            "sched_switch",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.runner)

    def test_preflight_is_explicitly_non_restart(self) -> None:
        self.assertIn('MODE="${1:-run}"', self.runner)
        self.assertIn("R24_PREFLIGHT=PASS", self.runner)
        self.assertIn("R24_PREFLIGHT=BLOCKED_PREDECESSOR_AGE", self.runner)
        self.assertIn("model_restart=NO", self.runner)
        self.assertIn("persistent_vm_tuning=NO", self.runner)
        self.assertIn("predecessor_age_ok=", self.runner)

    def test_runner_restores_managed_service_and_strictly_classifies_rm(self) -> None:
        self.assertIn('sudo -n systemctl start "${UNIT}"', self.runner)
        self.assertIn("NV_ERR_NO_MEMORY|_memdescAllocInternal", self.runner)
        self.assertIn('FUNCTIONAL_CLASS="PASS"', self.runner)
        self.assertIn('HOST_CLASS="FAIL"', self.runner)
        self.assertIn("ORCA_R24_RESULT=VALID_CLEAN", self.runner)
        self.assertIn("ORCA_R24_RESULT=VALID_RM_OOM", self.runner)
        self.assertIn("TRACE_WINDOW_VALID", self.runner)
        self.assertIn("15.0 <= start_offset <= 30.0", self.runner)
        self.assertIn("45.0 <= duration <= 60.0", self.runner)

    def test_analyzer_compares_against_fixed_r22_baseline(self) -> None:
        for token in (
            "BASELINE_R22_5S_MIB = 75138.043",
            "candidate_to_r22_burst_pct",
            "candidate_burst_reduction_pct",
            "BURST_UNCHANGED",
            "BURST_PARTIAL_REDUCTION",
            "BURST_MATERIAL_REDUCTION",
            "BURST_STRONGLY_SUPPRESSED",
            "trace_covers_burst5",
            "node0_normal_free_delta_mib",
            "nr_free_pages_delta_mib",
            "normal_unmovable_order4plus_mib",
            "normal_movable_order4plus_mib",
            "activity_volume_not_resident_ownership",
            "mitigation_discriminator",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.analyzer)

    def test_benchmark_files_do_not_depend_on_internal_runtime_category(self) -> None:
        for name, text in (
            ("runner", self.runner),
            ("analyzer", self.analyzer),
            ("plan", self.plan),
        ):
            with self.subTest(name=name):
                self.assertNotIn("scripts/runtime/", text)
                self.assertNotIn("../runtime/", text)


if __name__ == "__main__":
    unittest.main()
