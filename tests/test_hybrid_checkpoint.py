from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
TOOL = ROOT / "scripts" / "model" / "prepare-hybrid-checkpoint.py"
WRAPPER = ROOT / "scripts" / "model" / "prepare-hybrid-checkpoint.sh"


class HybridCheckpointTests(unittest.TestCase):
    def test_plan_selects_exact_main_model_residual_writers_without_mtp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "base"
            overlay = root / "overlay"
            output = root / "output"
            base.mkdir()
            overlay.mkdir()

            targets: list[str] = []
            for layer in range(48):
                if layer % 4 == 3:
                    targets.append(
                        f"model.language_model.layers.{layer}.self_attn.o_proj"
                    )
                else:
                    targets.append(
                        f"model.language_model.layers.{layer}.linear_attn.out_proj"
                    )
                targets.append(
                    f"model.language_model.layers.{layer}.mlp.shared_expert.down_proj"
                )

            base_config = {
                "quantization_config": {
                    "config_groups": {
                        "group_0": {
                            "targets": targets,
                        }
                    }
                }
            }
            (base / "config.json").write_text(json.dumps(base_config))

            base_map: dict[str, str] = {}
            overlay_map: dict[str, str] = {}
            for module in targets:
                base_map[module + ".weight"] = "model-00001.safetensors"
                base_map[module + ".weight_scale"] = "model-00001.safetensors"
                overlay_map[module + ".weight"] = "model-bf16.safetensors"

            # These look similar but must never enter the 96-module hybrid set.
            base_map["mtp.layers.0.self_attn.o_proj.weight"] = "model-mtp.safetensors"
            base_map[
                "mtp.layers.0.mlp.shared_expert.down_proj.weight"
            ] = "model-mtp.safetensors"
            overlay_map["mtp.layers.0.self_attn.o_proj.weight"] = "model-bf16.safetensors"
            overlay_map[
                "mtp.layers.0.mlp.shared_expert.down_proj.weight"
            ] = "model-bf16.safetensors"

            (base / "model.safetensors.index.json").write_text(
                json.dumps({"weight_map": base_map})
            )
            (overlay / "model.safetensors.index.json").write_text(
                json.dumps({"weight_map": overlay_map})
            )
            (base / "model-00001.safetensors").write_bytes(b"x")
            (overlay / "model-bf16.safetensors").write_bytes(b"x")

            result = subprocess.run(
                [
                    "python3",
                    str(TOOL),
                    "plan",
                    "--base",
                    str(base),
                    "--overlay",
                    str(overlay),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("residual modules : 96", result.stdout)
            self.assertIn("'self_attn.o_proj': 12", result.stdout)
            self.assertIn("'linear_attn.out_proj': 36", result.stdout)
            self.assertIn("'shared_expert.down_proj': 48", result.stdout)
            self.assertIn("FP8 scales       : 96", result.stdout)
            self.assertIn("affected shards  : 1", result.stdout)
            self.assertNotIn("model-mtp.safetensors", result.stdout)

    def test_plan_supports_full_group0_variant(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "base"
            overlay = root / "overlay"
            output = root / "output"
            base.mkdir()
            overlay.mkdir()

            targets = [
                f"model.language_model.layers.{layer}.mock.proj{slot}"
                for layer in range(50)
                for slot in range(6)
            ]
            base_config = {
                "quantization_config": {
                    "config_groups": {"group_0": {"targets": targets}}
                }
            }
            (base / "config.json").write_text(json.dumps(base_config))

            base_map: dict[str, str] = {}
            overlay_map: dict[str, str] = {}
            for module in targets:
                base_map[module + ".weight"] = "model-00001.safetensors"
                base_map[module + ".weight_scale"] = "model-00001.safetensors"
                overlay_map[module + ".weight"] = "model-bf16.safetensors"

            (base / "model.safetensors.index.json").write_text(
                json.dumps({"weight_map": base_map})
            )
            (overlay / "model.safetensors.index.json").write_text(
                json.dumps({"weight_map": overlay_map})
            )
            (base / "model-00001.safetensors").write_bytes(b"x")
            (overlay / "model-bf16.safetensors").write_bytes(b"x")

            result = subprocess.run(
                [
                    "python3",
                    str(TOOL),
                    "plan",
                    "--variant",
                    "group0-bf16",
                    "--base",
                    str(base),
                    "--overlay",
                    str(overlay),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Full group-0 BF16 hybrid plan", result.stdout)
            self.assertIn("variant          : group0-bf16", result.stdout)
            self.assertIn("group-0 modules  : 300", result.stdout)
            self.assertIn("FP8 scales       : 300", result.stdout)

    def test_group0_wrapper_selects_variant_and_output(self) -> None:
        wrapper = (
            ROOT / "scripts" / "model" / "prepare-group0-hybrid-checkpoint.sh"
        ).read_text(encoding="utf-8")
        self.assertIn("HYBRID_VARIANT=group0-bf16", wrapper)
        self.assertIn("qwen3.8-hybrid-group0-bf16", wrapper)

    def test_builder_requires_bf16_and_removes_exact_fp8_scales(self) -> None:
        source = TOOL.read_text(encoding="utf-8")
        self.assertIn("tensor.dtype != torch.bfloat16", source)
        self.assertIn('module + ".weight_scale"', source)
        self.assertIn('"fp8_scales_removed": expected_removed', source)
        self.assertIn('"bf16_weights_overlaid": expected_removed', source)
        self.assertIn('"mtp_tensors_changed": 0', source)
        self.assertIn('"remaining_fp8_group0_targets": len(new_targets)', source)

    def test_wrapper_uses_existing_container_image_for_build(self) -> None:
        source = WRAPPER.read_text(encoding="utf-8")
        self.assertIn("vllm-orcarouter-v029:v1", source)
        self.assertIn('port 8888 is owned by', source)
        self.assertIn('-v "${BASE}:/base:ro"', source)
        self.assertIn('-v "${OVERLAY}:/overlay:ro"', source)
        self.assertIn("--entrypoint python3", source)
        self.assertNotIn("pip install", source)


if __name__ == "__main__":
    unittest.main()
