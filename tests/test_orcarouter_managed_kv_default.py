from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
SERVE = ROOT / "scripts" / "serve.sh"


class OrcaRouterManagedKvDefaultTests(unittest.TestCase):
    def test_orcarouter_uses_promoted_16_gib_kv_default(self) -> None:
        text = SERVE.read_text(encoding="utf-8")
        start = text.index("  orcarouter)\n")
        end = text.index("  nvidia)\n", start)
        block = text[start:end]

        self.assertIn("DEFAULT_KV_MEM=17179869184", block)
        self.assertNotIn("DEFAULT_KV_MEM=25769803776", block)
        self.assertIn("adverse-state controlled A/B", block)
        self.assertIn("16 GiB passed strict readiness/soak/host checks", block)
        self.assertIn("24 GiB reproduced repeated RM NV_ERR_NO_MEMORY", block)

    def test_existing_community_controls_are_already_present(self) -> None:
        """The third-party recipe does not justify changing already-matched controls."""
        source = SERVE.read_text(encoding="utf-8")
        block = source.split("  orcarouter)" + chr(10), 1)[1].split(
            "  nvidia)" + chr(10), 1
        )[0]
        for expected in (
            "DEFAULT_MAXLEN=262144",
            "DEFAULT_NSPEC=2",
            "DEFAULT_MAXSEQS=3",
            "DEFAULT_KV_MEM=17179869184",
            "DEFAULT_GPU_UTIL=0.85",
        ):
            self.assertIn(expected, block)
        self.assertNotIn("DEFAULT_KV_MEM=25769803776", block)
        self.assertIn('EXECUTOR="${EXECUTOR:-mp}"', source)
        self.assertIn('PLE_ENV=(-e VLLM_PLE_CPU_OFFLOAD=1', source)
        self.assertIn('PLE_TIMEOUT="${PLE_TIMEOUT:-1800}"', source)
        self.assertIn('--distributed-executor-backend "${EXECUTOR}"', source)
        self.assertIn('--no-async-scheduling', source)
        self.assertIn('--no-enable-prefix-caching', source)
        self.assertIn('--no-enable-flashinfer-autotune', source)

    def test_existing_legacy_and_v029_ple_storage_are_separate(self) -> None:
        source = SERVE.read_text(encoding="utf-8")
        self.assertIn("PLE_MODE=cpu-offload", source)
        self.assertIn('if [[ "${PLE_MODE}" == mmap ]]; then', source)
        self.assertIn('-e VLLM_PLE_MMAP=1', source)
        self.assertIn('KV_MEMORY_FLAG=--kv-cache-memory', source)
        self.assertIn('KV_MEMORY_FLAG=--kv-cache-memory-bytes', source)
        self.assertIn('IMAGE="${VLLM_IMAGE:-vllm-orcarouter-v029:v1}"', source)

    def test_hybrid_kv_default_is_unchanged(self) -> None:
        text = SERVE.read_text(encoding="utf-8")
        start = text.index("  orcarouter-hybrid)\n")
        end = text.index("  *) echo", start)
        block = text[start:end]

        self.assertIn("DEFAULT_KV_MEM=25769803776", block)
        self.assertNotIn("DEFAULT_KV_MEM=17179869184", block)


if __name__ == "__main__":
    unittest.main()
