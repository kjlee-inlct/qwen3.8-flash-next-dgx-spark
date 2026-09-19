from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
PATCH = ROOT / "scripts" / "patch-nv-mixed.py"
DOCKERFILE = ROOT / "scripts" / "Dockerfile.nv-mixed"


class NvidiaMixedPatchTests(unittest.TestCase):
    def test_mtp_draft_cache_config_is_copied_and_sanitized(self) -> None:
        text = PATCH.read_text(encoding="utf-8")

        self.assertIn(
            "draft_cache_config = vllm_config.cache_config",
            text,
        )
        self.assertIn(
            "not draft_cache_config.enable_prefix_caching",
            text,
        )
        self.assertIn(
            "draft_cache_config.mamba_block_size is not None",
            text,
        )
        self.assertIn(
            "mamba_block_size=None",
            text,
        )
        self.assertIn(
            "cache_config=draft_cache_config",
            text,
        )
        self.assertIn(
            "cache.layer_index >= target_layers",
            text,
        )

    def test_speculative_csa_fallback_is_targeted_to_appended_draft_layers(self) -> None:
        text = PATCH.read_text(encoding="utf-8")
        self.assertIn("target_layers = vllm_config.model_config.get_total_num_hidden_layers()", text)
        self.assertIn("vllm_config.speculative_config is not None", text)
        self.assertIn("cache.layer_index >= target_layers", text)
        self.assertIn("return None", text)

    def test_image_build_asserts_draft_cache_patch(self) -> None:
        text = DOCKERFILE.read_text(encoding="utf-8")
        self.assertIn(
            "draft_cache_config.mamba_block_size is not None",
            text,
        )
        self.assertIn(
            "cache_config=draft_cache_config",
            text,
        )


if __name__ == "__main__":
    unittest.main()
