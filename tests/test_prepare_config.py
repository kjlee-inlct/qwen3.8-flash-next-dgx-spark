import json
import tempfile
import unittest
from pathlib import Path

import importlib.util


SCRIPT = Path(__file__).parents[1] / "scripts" / "prepare-config.py"
SPEC = importlib.util.spec_from_file_location("prepare_config", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class PrepareConfigTests(unittest.TestCase):
    def test_replaces_only_exact_layer_type_values(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            model = root / "model"
            model.mkdir()
            source = {
                "text_config": {
                    "layer_types": ["linear_attention", "qwen_sparse_attention"],
                    "description": "qwen_sparse_attention remains text",
                }
            }
            (model / "config.json").write_text(json.dumps(source), encoding="utf-8")
            output = root / "config.vllm.json"

            count = MODULE.prepare(model / "config.json", output)
            result = json.loads(output.read_text(encoding="utf-8"))

            self.assertEqual(count, 1)
            self.assertEqual(result["text_config"]["layer_types"][1], "compressed_sparse_attention")
            self.assertEqual(result["text_config"]["description"], source["text_config"]["description"])

    def test_copies_an_already_compatible_config(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "config.json"
            output = root / "override.json"
            source.write_text('{"layer_types":["compressed_sparse_attention"]}', encoding="utf-8")
            self.assertEqual(MODULE.prepare(source, output), 0)
            self.assertEqual(json.loads(output.read_text()), json.loads(source.read_text()))


if __name__ == "__main__":
    unittest.main()
