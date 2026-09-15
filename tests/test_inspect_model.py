from __future__ import annotations

import importlib.util
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "inspect-model.py"
SPEC = importlib.util.spec_from_file_location("inspect_model", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def write_safetensors(path: Path, tensors: dict) -> None:
    raw = json.dumps(tensors).encode()
    path.write_bytes(struct.pack("<Q", len(raw)) + raw)


class InspectorTests(unittest.TestCase):
    def test_reads_only_safetensors_header(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.safetensors"
            tensors = {
                "model.layers.1.ple.ngram_embedding.weight": {
                    "dtype": "BF16", "shape": [10, 4], "data_offsets": [0, 80]
                }
            }
            write_safetensors(path, tensors)
            self.assertEqual(MODULE.read_safetensors_header(path), tensors)

    def test_detects_ple_and_mtp_layout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            model_dir = Path(directory)
            (model_dir / "config.json").write_text(json.dumps({
                "architectures": ["Qwen4ExpForConditionalGeneration"],
                "model_type": "qwen4_exp",
                "quantization_config": {"quant_method": "compressed-tensors"},
            }))
            write_safetensors(model_dir / "model-00001.safetensors", {
                "model.layers.1.ple.ngram_embedding.weight": {
                    "dtype": "BF16", "shape": [10, 4], "data_offsets": [0, 80]
                }
            })
            write_safetensors(model_dir / "model-mtp.safetensors", {
                "mtp.layers.0.mlp.weight": {
                    "dtype": "F8_E4M3", "shape": [4, 4], "data_offsets": [0, 16]
                }
            })
            report = MODULE.Report(repository=MODULE.DEFAULT_REPO)
            MODULE.inspect_local(report, model_dir, None)
            self.assertEqual(report.ple_dtypes, ["BF16"])
            self.assertEqual(report.mtp_dtypes, ["F8_E4M3"])
            self.assertFalse([finding for finding in report.findings if finding.level == "ERROR"])


if __name__ == "__main__":
    unittest.main()
