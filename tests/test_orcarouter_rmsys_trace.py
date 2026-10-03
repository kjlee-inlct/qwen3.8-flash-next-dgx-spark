from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
RUNNER = ROOT / "scripts" / "benchmark" / "run-orcarouter-managed-rmsys-r10.sh"


class OrcaRouterRmSysTraceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = RUNNER.read_text(encoding="utf-8")

    def test_runner_targets_managed_orcarouter_16_gib_release(self) -> None:
        self.assertIn("MODEL_PROFILE=orcarouter", self.text)
        self.assertIn("DEFAULT_KV_MEM=17179869184", self.text)
        self.assertIn(
            'DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"',
            self.text,
        )
        self.assertIn('CURRENT_LINK="${DATA_HOME}/current"', self.text)
        self.assertIn("kv16-ab.conf", self.text)
        self.assertIn("temporary KV override is still present", self.text)

    def test_runner_uses_normal_managed_service_restart(self) -> None:
        self.assertIn("scripts/manage-service.sh", self.text)
        self.assertIn('--runtime-root "${CURRENT_LINK}"', self.text)
        self.assertIn("--start", self.text)
        self.assertIn("--yes", self.text)
        self.assertNotIn("docker run", self.text)

    def test_runner_captures_r9_rm_sysmem_boundary_and_order4_activity(self) -> None:
        for token in (
            "nv_alloc_pages_entry",
            "nv_alloc_pages_ret",
            "nv_alloc_system_pages_entry",
            "nv_alloc_system_pages_ret",
            "page_count=$arg2:u32",
            "page_size=$arg3:u64",
            "contiguous=$arg4:u8",
            "cache_type=$arg5:u32",
            "zeroed=$arg6:u8",
            "unencrypted=$arg7:u8",
            "node_id=$arg8:s32",
            "mm_page_alloc -f 'order == 4'",
            "mm_page_free -f 'order == 4'",
            "mm_page_alloc_extfrag -f 'alloc_order >= 4'",
        ):
            self.assertIn(token, self.text)

    def test_runner_preserves_raw_and_analyzed_evidence(self) -> None:
        for name in (
            "allocator-trace.dat",
            "allocator-trace.txt",
            "kernel-window.txt",
            "kernel-window-monotonic.txt",
            "kernel-errors.txt",
            "kernel-errors-monotonic.txt",
            "service-window.txt",
            "container-window.txt",
            "container-state.txt",
            "managed-state.txt",
            "api-state.txt",
            "rmsys-analysis.txt",
        ):
            self.assertIn(name, self.text)
        self.assertIn("analyze-h6-r9-rmsys.py", self.text)


if __name__ == "__main__":
    unittest.main()
