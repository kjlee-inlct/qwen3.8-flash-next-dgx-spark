import ast
import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
PATCH = REPO / "scripts/patch-v029-r28-unquant-linear-markers.py"


SOURCE = '''\
logger = init_logger(__name__)

class UnquantizedLinearMethod(LinearMethodBase):
    def create_weights(
        self,
        layer,
        input_size_per_partition,
        output_partition_sizes,
        input_size,
        output_size,
        params_dtype,
        **extra_weight_attrs,
    ):
        weight_loader = extra_weight_attrs.pop("weight_loader")
        weight = ModelWeightParameter(
            data=torch.empty(
                sum(output_partition_sizes),
                input_size_per_partition,
                dtype=params_dtype,
            ),
            input_dim=1,
            output_dim=0,
            weight_loader=weight_loader,
        )
        layer.register_parameter("weight", weight)
        set_weight_attrs(weight, extra_weight_attrs)
'''


class R28UnquantLinearMarkerPatchTest(unittest.TestCase):
    def test_patch_adds_exact_marker_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "linear.py"
            path.write_text(SOURCE, encoding="utf-8")
            subprocess.run(
                [sys.executable, str(PATCH), str(path)],
                check=True,
                text=True,
                capture_output=True,
            )
            patched = path.read_text(encoding="utf-8")
            ast.parse(patched)
            self.assertEqual(patched.count("QWEN38_R28_UNQUANT_LINEAR_BEGIN"), 1)
            self.assertEqual(patched.count("QWEN38_R28_UNQUANT_LINEAR_END"), 1)
            self.assertEqual(
                patched.count("_QWEN38_R28_UNQUANT_LINEAR_SEQ = 0"), 1
            )
            self.assertIn("_qwen38_r28_elements", patched)
            self.assertIn('getattr(layer, "prefix", "")', patched)
            self.assertIn("data=torch.empty(", patched)


if __name__ == "__main__":
    unittest.main()
