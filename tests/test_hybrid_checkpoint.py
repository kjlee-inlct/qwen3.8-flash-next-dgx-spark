from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]
TOOL = ROOT / "scripts" / "model" / "prepare-hybrid-checkpoint.py"
WRAPPER = ROOT / "scripts" / "model" / "prepare-hybrid-checkpoint.sh"
DIFF_TOOL = ROOT / "scripts" / "model" / "inspect-checkpoint-diff.py"
DIFF_WRAPPER = ROOT / "scripts" / "model" / "inspect-orcarouter-mazinb-diff.sh"
QUANT_LAYOUT_TOOL = ROOT / "scripts" / "model" / "prepare-quant-layout-hybrid-checkpoint.py"
QUANT_LAYOUT_WRAPPER = ROOT / "scripts" / "model" / "prepare-quant-layout-hybrid-checkpoint.sh"
H4_CHECK_TOOL = ROOT / "scripts" / "model" / "check-h4-expert-conversion.py"
H4_CHECK_WRAPPER = ROOT / "scripts" / "model" / "check-h4-expert-conversion.sh"
H4_AB_TOOL = ROOT / "scripts" / "model" / "prepare-h4-expert-ab.py"
H4_AB_WRAPPER = ROOT / "scripts" / "model" / "prepare-h4-expert-ab.sh"


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
        self.assertIn("for child in output.iterdir()", source)
        self.assertNotIn("shutil.rmtree(output)", source)

    def test_wrapper_uses_existing_container_image_for_build(self) -> None:
        source = WRAPPER.read_text(encoding="utf-8")
        self.assertIn("vllm-orcarouter-v029:v1", source)
        self.assertIn('port 8888 is owned by', source)
        self.assertIn('-v "${BASE}:/base:ro"', source)
        self.assertIn('-v "${OVERLAY}:/overlay:ro"', source)
        self.assertIn("--entrypoint python3", source)
        self.assertGreaterEqual(source.count('--variant "${VARIANT}"'), 2)
        self.assertNotIn("pip install", source)

    def test_checkpoint_diff_inventory_is_metadata_only(self) -> None:
        source = DIFF_TOOL.read_text(encoding="utf-8")
        self.assertIn("get_slice(key)", source)
        self.assertIn("get_dtype()", source)
        self.assertIn("get_shape()", source)
        self.assertNotIn("get_tensor(key)", source)
        self.assertIn('"metadata_differences"', source)
        self.assertIn("def expert_suffix_counts", source)
        self.assertIn('"expert_suffixes"', source)
        self.assertIn("def summarize_quantization", source)
        self.assertIn('"base_quantization"', source)
        self.assertIn('"candidate_quantization"', source)

    def test_checkpoint_diff_wrapper_uses_existing_runtime_image(self) -> None:
        source = DIFF_WRAPPER.read_text(encoding="utf-8")
        self.assertIn("vllm-orcarouter-v029:v1", source)
        self.assertIn("/base:ro", source)
        self.assertIn("/candidate:ro", source)
        self.assertIn("--json-output /report.json", source)

    def test_quant_layout_builder_keeps_mtp_and_switches_quantization_recipe(self) -> None:
        source = QUANT_LAYOUT_TOOL.read_text(encoding="utf-8")
        self.assertIn('VARIANT = "quant-layout-mazinb-experts"', source)
        self.assertIn('"group0_bf16_weights"', source)
        self.assertIn('"base_expert_tensors_removed"', source)
        self.assertIn('"overlay_expert_tensors_added"', source)
        self.assertIn('"down_proj.weight_scale": 24576', source)
        self.assertIn('"up_proj.weight_scale_2": 24576', source)
        self.assertIn('new_config["quantization_config"]', source)
        self.assertIn('"mazinb-modelopt-nvfp4"', source)
        self.assertIn('"mtp_tensors_changed": 0', source)

    def test_quant_layout_expert_selector_excludes_mtp(self) -> None:
        source = QUANT_LAYOUT_TOOL.read_text(encoding="utf-8")
        self.assertIn('key.startswith("model.language_model.layers.")', source)
        self.assertIn('".mlp.experts." in key', source)
        self.assertIn('key.startswith("mtp.") or key.startswith("model.mtp.")', source)

    def test_quant_layout_wrapper_uses_existing_builder_image_and_port_guard(self) -> None:
        source = QUANT_LAYOUT_WRAPPER.read_text(encoding="utf-8")
        self.assertIn("vllm-orcarouter-v029:v1", source)
        self.assertIn("stop the runtime before H3 build", source)
        self.assertIn("/base:ro", source)
        self.assertIn("/overlay:ro", source)
        self.assertIn("qwen3.8-hybrid-quant-layout", source)

    def test_h4_conversion_gate_checks_schema_without_requantization(self) -> None:
        source = H4_CHECK_TOOL.read_text(encoding="utf-8")
        self.assertIn('"weight_packed"', source)
        self.assertIn('"weight_scale_2"', source)
        self.assertIn('"modelopt.weight_scale_2 = 1 / compressed_tensors.weight_global_scale"', source)
        self.assertIn("get_slice(key)", source)
        self.assertIn('"input_global_scale_modules"', source)
        self.assertIn('"input_scale_modules"', source)

    def test_h4_conversion_wrapper_is_read_only(self) -> None:
        source = H4_CHECK_WRAPPER.read_text(encoding="utf-8")
        self.assertIn("/base:ro", source)
        self.assertIn("/overlay:ro", source)
        self.assertIn("h4-expert-conversion.json", source)
        self.assertNotIn("rm -rf", source)

    def test_h4_ab_builder_uses_thin_delta_modelopt_contract(self) -> None:
        source = H4_AB_TOOL.read_text(encoding="utf-8")
        self.assertIn('"orca-down": 24576', source)
        self.assertIn('"orca-gate-up": 49152', source)
        self.assertIn('"orca-all": 73728', source)
        self.assertIn('H3_MOUNT = "/h3-model"', source)
        self.assertIn('raw.to(dtype=torch.float32).reciprocal()', source)
        self.assertIn('"input_scale_source": "mazinb-h3"', source)
        self.assertIn('"parent_variant": "quant-layout-mazinb-experts"', source)
        self.assertIn('"mtp_tensors_changed": 0', source)

    def test_h4_ab_wrapper_guards_runtime_and_supports_both_variants(self) -> None:
        source = H4_AB_WRAPPER.read_text(encoding="utf-8")
        self.assertIn("orca-down", source)
        self.assertIn("orca-gate-up", source)
        self.assertIn("orca-all", source)
        self.assertIn("stop the runtime before H4 build", source)
        self.assertIn("/base:ro", source)
        self.assertIn("/h3:ro", source)

if __name__ == "__main__":
    unittest.main()
