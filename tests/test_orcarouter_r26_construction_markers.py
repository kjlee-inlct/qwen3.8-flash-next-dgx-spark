import ast
import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
PATCH = REPO / "scripts/patch-v029-r26-construction-markers.py"


class R26ConstructionMarkerPatchTest(unittest.TestCase):
    def test_patch_adds_constructor_and_modelopt_markers(self) -> None:
        loader_source = '''\
def initialize_model(vllm_config, *, prefix="", model_class=None, model_config=None):
    if model_class is None:
        model_class = object
    with set_current_vllm_config(vllm_config, check_compile=True, prefix=prefix):
        model = model_class(vllm_config=vllm_config, prefix=prefix)
        return model
'''
        modelopt_source = '''\
logger = init_logger(__name__)

class ModelOptNvFp4FusedMoE:
    def create_weights(
        self,
        layer,
        num_experts,
        hidden_size,
        intermediate_size_per_partition,
        params_dtype,
        **extra_weight_attrs,
    ):
        layer.num_experts = num_experts
        w13_weight = ModelWeightParameter(
            data=torch.empty(num_experts, intermediate_size_per_partition, hidden_size)
        )
        layer.register_parameter("w13_weight", w13_weight)
        w2_weight = ModelWeightParameter(
            data=torch.empty(num_experts, hidden_size, intermediate_size_per_partition)
        )
        layer.register_parameter("w2_weight", w2_weight)
        layer.params_dtype = params_dtype
'''
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            loader = root / "utils.py"
            modelopt = root / "modelopt.py"
            loader.write_text(loader_source, encoding="utf-8")
            modelopt.write_text(modelopt_source, encoding="utf-8")

            subprocess.run(
                [sys.executable, str(PATCH), str(loader), str(modelopt)],
                check=True,
                text=True,
                capture_output=True,
            )

            loader_text = loader.read_text(encoding="utf-8")
            modelopt_text = modelopt.read_text(encoding="utf-8")
            ast.parse(loader_text)
            ast.parse(modelopt_text)

            self.assertEqual(loader_text.count("QWEN38_R26_MODEL_CTOR_BEGIN"), 1)
            self.assertEqual(loader_text.count("QWEN38_R26_MODEL_CTOR_END"), 1)
            self.assertLess(
                loader_text.index("QWEN38_R26_MODEL_CTOR_BEGIN"),
                loader_text.index("model = model_class("),
            )
            self.assertLess(
                loader_text.index("model = model_class("),
                loader_text.index("QWEN38_R26_MODEL_CTOR_END"),
            )

            for marker in (
                "QWEN38_R26_MODELOPT_MOE_BEGIN",
                "QWEN38_R26_MODELOPT_MOE_END",
                "QWEN38_R26_MODELOPT_W13_BEGIN",
                "QWEN38_R26_MODELOPT_W13_END",
                "QWEN38_R26_MODELOPT_W2_BEGIN",
                "QWEN38_R26_MODELOPT_W2_END",
            ):
                self.assertEqual(modelopt_text.count(marker), 1)
            self.assertEqual(
                modelopt_text.count("_QWEN38_R26_MODELOPT_MOE_SEQ = 0"), 1
            )


if __name__ == "__main__":
    unittest.main()
