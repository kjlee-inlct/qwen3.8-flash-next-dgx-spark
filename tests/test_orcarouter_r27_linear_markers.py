import ast
import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
PATCH = REPO / "scripts/patch-v029-r27-linear-boundary-markers.py"


MODELOPT = '''\
logger = init_logger(__name__)

class ModelOptNvFp4W4A16LinearMethod:
    def create_weights(self, layer, input_size_per_partition, output_partition_sizes,
                       input_size, output_size, params_dtype, **extra_weight_attrs):
        del input_size, output_size
        if input_size_per_partition % 16 != 0:
            raise ValueError("bad")
        output_size_per_partition = sum(output_partition_sizes)
        weight_loader = extra_weight_attrs.get("weight_loader")
        weight = ModelWeightParameter(
            data=torch.empty(output_size_per_partition, input_size_per_partition // 2,
                             dtype=torch.uint8),
            input_dim=1,
            output_dim=0,
            weight_loader=weight_loader,
        )
        layer.register_parameter("weight", weight)
        weight_scale_2 = PerTensorScaleParameter(
            data=torch.empty(len(output_partition_sizes), dtype=torch.float32),
            weight_loader=weight_loader,
        )
        layer.register_parameter("weight_scale_2", weight_scale_2)
        weight_scale = GroupQuantScaleParameter(
            data=torch.empty(output_size_per_partition, input_size_per_partition // 16),
            input_dim=1,
            output_dim=0,
            weight_loader=weight_loader,
        )
        layer.register_parameter("weight_scale", weight_scale)
        input_scale = PerTensorScaleParameter(
            data=torch.empty(len(output_partition_sizes), dtype=torch.float32),
            weight_loader=weight_loader,
        )
        layer.register_parameter("input_scale", input_scale)
'''


QWEN4 = '''\
from vllm.distributed import get_pp_group


def without_modelopt_fp4(
    quant_config,
):
    return quant_config


class Qwen4ExpDecoderLayer:
    def __init__(self, vllm_config, layer_type, prefix=""):
        super().__init__()
        config = vllm_config.model_config.hf_text_config
        self.config = config
        self.layer_type = layer_type
        self.layer_idx = extract_layer_index(prefix)
        self.ple = None
        if layer_type == "linear_attention":
            self.linear_attn = LinearAttention()
        else:
            self.self_attn = FullAttention()
        self.mlp = MLP()
        self.attn_hyper_connection = GatedResidual()
        self.mlp_hyper_connection = GatedResidual()


class Qwen4ExpForCausalLM:
    pass
'''


class R27MarkerPatchTest(unittest.TestCase):
    def test_patch_adds_exact_marker_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            modelopt = root / "modelopt.py"
            qwen4 = root / "model.py"
            modelopt.write_text(MODELOPT, encoding="utf-8")
            qwen4.write_text(QWEN4, encoding="utf-8")

            subprocess.run(
                [sys.executable, str(PATCH), str(modelopt), str(qwen4)],
                check=True,
                text=True,
                capture_output=True,
            )

            modelopt_text = modelopt.read_text(encoding="utf-8")
            qwen4_text = qwen4.read_text(encoding="utf-8")
            ast.parse(modelopt_text)
            ast.parse(qwen4_text)

            for marker in (
                "QWEN38_R27_W4A16_LINEAR_BEGIN",
                "QWEN38_R27_W4A16_LINEAR_END",
                "QWEN38_R27_W4A16_WEIGHT_BEGIN",
                "QWEN38_R27_W4A16_WEIGHT_END",
            ):
                self.assertEqual(modelopt_text.count(marker), 1)
            self.assertEqual(
                modelopt_text.count("_QWEN38_R27_W4A16_LINEAR_SEQ = 0"), 1
            )
            self.assertLess(
                modelopt_text.index("QWEN38_R27_W4A16_LINEAR_BEGIN"),
                modelopt_text.index("QWEN38_R27_W4A16_WEIGHT_BEGIN"),
            )
            self.assertLess(
                modelopt_text.index("QWEN38_R27_W4A16_WEIGHT_END"),
                modelopt_text.index("QWEN38_R27_W4A16_LINEAR_END"),
            )

            for marker in (
                "QWEN38_R27_QWEN4_LAYER_BEGIN",
                "QWEN38_R27_QWEN4_LAYER_END",
            ):
                self.assertEqual(qwen4_text.count(marker), 1)
            self.assertEqual(qwen4_text.count("_QWEN38_R27_QWEN4_LAYER_SEQ = 0"), 1)
            self.assertEqual(qwen4_text.count("logger = init_logger(__name__)"), 1)
            self.assertLess(
                qwen4_text.index("QWEN38_R27_QWEN4_LAYER_BEGIN"),
                qwen4_text.index("self.mlp = MLP()"),
            )
            self.assertLess(
                qwen4_text.index("self.mlp_hyper_connection = GatedResidual()"),
                qwen4_text.index("QWEN38_R27_QWEN4_LAYER_END"),
            )


if __name__ == "__main__":
    unittest.main()
