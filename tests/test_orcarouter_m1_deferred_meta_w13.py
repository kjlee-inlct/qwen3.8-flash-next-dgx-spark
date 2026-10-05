import ast
import pathlib
import subprocess
import sys
import tempfile
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
PATCH = REPO / "scripts/patch-v029-m1-deferred-meta-w13.py"


SOURCE = '''\
import torch
from vllm.model_executor.layers.quantization import QuantizationMethods

class ModelOptNvFp4FusedMoE(FusedMoEMethodBase):
    """MoE Method for FP4 Quantization."""

    def __init__(
        self,
        quant_config,
        moe_config,
    ) -> None:
        self.quant_config = quant_config
        self.moe = moe_config

    def create_weights(
        self,
        layer: RoutedExperts,
        num_experts: int,
        hidden_size: int,
        intermediate_size_per_partition: int,
        params_dtype,
        **extra_weight_attrs,
    ):
        weight_dtype = torch.uint8
        weight_loader = extra_weight_attrs.get("weight_loader")
        w13_num_shards = 2
        # GEMM 1
        w13_weight = ModelWeightParameter(
            data=torch.empty(
                num_experts,
                w13_num_shards * intermediate_size_per_partition,
                hidden_size // 2,
                dtype=weight_dtype,
            ),
            input_dim=1,
            output_dim=2,
            weight_loader=weight_loader,
        )
        layer.register_parameter("w13_weight", w13_weight)

        # GEMM 2
        w2_weight = ModelWeightParameter(
            data=torch.empty(
                num_experts,
                hidden_size,
                intermediate_size_per_partition // 2,
                dtype=weight_dtype,
            ),
            input_dim=1,
            output_dim=2,
            weight_loader=weight_loader,
        )
        layer.register_parameter("w2_weight", w2_weight)

        w2_input_scale = PerTensorScaleParameter(
            data=torch.empty(num_experts, dtype=torch.float32),
            weight_loader=weight_loader,
        )
        layer.register_parameter("w2_input_scale", w2_input_scale)

    def process_weights_after_loading(self, layer: RoutedExperts) -> None:
        consume(layer.w13_weight, layer.w2_weight)


ModelOptNvFp4Config.LinearMethodCls = ModelOptNvFp4LinearMethod
'''


class M1DeferredMetaW13PatchTest(unittest.TestCase):
    def patch_source(self, source: str = SOURCE) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "modelopt.py"
            path.write_text(source, encoding="utf-8")
            subprocess.run(
                [sys.executable, str(PATCH), str(path)],
                check=True,
                text=True,
                capture_output=True,
            )
            return path.read_text(encoding="utf-8")

    def test_patch_defers_only_w13_and_installs_native_layerwise_loader(self) -> None:
        patched = self.patch_source()
        ast.parse(patched)

        self.assertEqual(patched.count("QWEN38_M1_DEFERRED_META_W13_V1"), 1)
        self.assertEqual(patched.count("uses_meta_device = True"), 1)
        self.assertEqual(patched.count("initialize_online_processing(layer)"), 1)
        self.assertIn(
            "from vllm.model_executor.model_loader.reload.layerwise import (",
            patched,
        )

        class_start = patched.index("class ModelOptNvFp4FusedMoE")
        class_end = patched.index("ModelOptNvFp4Config.LinearMethodCls", class_start)
        block = patched[class_start:class_end]
        w13_start = block.index("# GEMM 1")
        w13_end = block.index('layer.register_parameter("w13_weight", w13_weight)')
        w2_start = block.index("# GEMM 2", w13_end)
        w2_end = block.index('layer.register_parameter("w2_weight", w2_weight)')

        self.assertIn('device="meta"', block[w13_start:w13_end])
        self.assertNotIn('device="meta"', block[w2_start:w2_end])

        last_registration = block.index(
            'layer.register_parameter("w2_input_scale", w2_input_scale)'
        )
        online = block.index("initialize_online_processing(layer)")
        process = block.index("def process_weights_after_loading", online)
        self.assertLess(last_registration, online)
        self.assertLess(online, process)

    def test_patch_refuses_second_application(self) -> None:
        patched = self.patch_source()
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "modelopt.py"
            path.write_text(patched, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(PATCH), str(path)],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("source already patched", result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
