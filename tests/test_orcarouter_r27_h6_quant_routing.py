import json
import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
INSPECTOR = REPO / "scripts/benchmark/inspect-orcarouter-r27-h6-quant-routing.py"


class H6QuantRoutingInspectorTest(unittest.TestCase):
    def test_reports_manifest_quant_and_approx_ignore_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "config.json").write_text(
                json.dumps(
                    {
                        "quantization_config": {
                            "quant_method": "modelopt",
                            "quant_algo": "W4A16_NVFP4",
                            "ignore": ["model.layers.*.self_attn.qkv_proj"],
                            "config_groups": {
                                "group_0": {
                                    "targets": ["Linear"],
                                    "weights": {"num_bits": 4},
                                    "input_activations": None,
                                }
                            },
                        }
                    }
                ),
                encoding="utf-8",
            )
            (root / "model.safetensors.index.json").write_text(
                json.dumps(
                    {
                        "weight_map": {
                            "model.layers.3.self_attn.qkv_proj.weight": "a.safetensors",
                            "model.layers.3.self_attn.o_proj.weight": "a.safetensors",
                        }
                    }
                ),
                encoding="utf-8",
            )
            (root / ".qwen38-hybrid-manifest.json").write_text(
                json.dumps(
                    {
                        "status": "complete",
                        "variant": "h6-modelopt-w4a16",
                        "parent_variant": "h5-neutral-input-scale",
                        "quant_algo_before": "NVFP4",
                        "quant_algo_after": "W4A16_NVFP4",
                        "safetensor_bytes_changed": 0,
                    }
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [sys.executable, str(INSPECTOR), str(root)],
                check=True,
                text=True,
                capture_output=True,
            )
            out = completed.stdout
            self.assertIn("R27_H6_QUANT_ROUTING_INSPECTION=BEGIN", out)
            self.assertIn("quant.quant_method=modelopt", out)
            self.assertIn("quant.quant_algo=W4A16_NVFP4", out)
            self.assertIn("quant.pattern_count=1", out)
            self.assertIn("pattern.1.approx_prefix_count=1", out)
            self.assertIn(
                "pattern.1.sample.1=model.layers.3.self_attn.qkv_proj", out
            )
            self.assertIn("quant.config_group_count=1", out)
            self.assertIn("R27_H6_QUANT_ROUTING_INSPECTION=END", out)


if __name__ == "__main__":
    unittest.main()
