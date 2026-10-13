"""Synthetic source contracts for the H38 CT meta-w13 preflight.

Only tests source inspection; never tests a CUDA allocator or starts a model.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INSPECTOR = ROOT / "scripts/benchmark/inspect-h38-ct-meta-prerequisites.py"
RUNNER = ROOT / "scripts/benchmark/check-h38-ct-meta-prerequisites.sh"
spec = importlib.util.spec_from_file_location("h38_ct_meta_prereqs", INSPECTOR)
assert spec and spec.loader
h38 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h38)

TEXTS = {
    "ct": '''\
class CompressedTensorsW4A4Nvfp4MoEMethod:
    def create_weights(self, layer):
        w13_weight = ModelWeightParameter(
            data=torch.empty(4, 5, dtype=dtype),
            input_dim=1, output_dim=2, weight_loader=weight_loader,
        )
        layer.register_parameter("w13_weight_packed", w13_weight)
        w2_weight = ModelWeightParameter(
            data=torch.empty(5, 4, dtype=dtype),
            input_dim=1, output_dim=2, weight_loader=weight_loader,
        )
        layer.register_parameter("w2_weight_packed", w2_weight)
    def process_weights_after_loading(self, layer):
        layer.register_parameter("w13_weight", layer.w13_weight_packed)
        delattr(layer, "w13_weight_packed")
        layer.register_parameter("w2_weight", layer.w2_weight_packed)
        delattr(layer, "w2_weight_packed")
''',
    "base_loader": '''\
def has_online_quant(quant_method):
    return getattr(quant_method, "uses_meta_device", False)

def load_model(model, model_config):
    finalize_layerwise_processing(model, model_config)
''',
    "layerwise": '''\
def initialize_online_processing(layer):
    get_layer_size(layer)
    _wrap_parameters_weight_loader(layer)

def _get_original_loader(param):
    return param.weight_loader

def _layerwise_process(layer, info):
    materialize_layer(layer, info)
    quant_method.process_weights_after_loading(layer)
''',
    "reload_meta": '''\
def materialize_layer(layer, info):
    pass
''',
    "reload_utils": '''\
def get_layer_size(layer):
    pass
''',
    "routed": '''\
class RoutedExperts:
    def __init__(self):
        self.quant_method = self._get_quant_method()
        self.quant_method.create_weights(layer=self)
''',
}


class H38CtMetaStaticPrerequisitesTests(unittest.TestCase):
    def test_current_h11_ct_allocation_is_not_meta(self) -> None:
        result = h38.inspect_ct(TEXTS["ct"])
        self.assertEqual(result["ct_packed_w13_h11_torch_empty"], "YES")
        self.assertEqual(result["ct_packed_w2_h11_torch_empty"], "YES")
        self.assertEqual(result["ct_declares_own_uses_meta_device"], "NO")

    def test_missing_or_changed_w13_source_fails_closed(self) -> None:
        broken = TEXTS["ct"].replace("data=torch.empty(4, 5, dtype=dtype)",
                                     "data=helper(4, 5)")
        with self.assertRaisesRegex(ValueError, "torch.empty"):
            h38.inspect_ct(broken)
        already_meta = TEXTS["ct"].replace("data=torch.empty(4, 5, dtype=dtype)",
                                            'data=torch.empty(4, 5, dtype=dtype, device="meta")')
        with self.assertRaisesRegex(ValueError, "already specifies device"):
            h38.inspect_ct(already_meta)

    def test_h12_alias_and_weight_loader_required(self) -> None:
        broken_alias = TEXTS["ct"].replace(
            'layer.register_parameter("w13_weight", layer.w13_weight_packed)',
            'layer.w13_weight = torch.nn.Parameter(layer.w13_weight_packed.data)',
        )
        with self.assertRaisesRegex(ValueError, "H12 post-load alias"):
            h38.inspect_ct(broken_alias)
        no_loader = TEXTS["ct"].replace("output_dim=2, weight_loader=weight_loader,",
                                        "output_dim=2,")
        with self.assertRaisesRegex(ValueError, "weight_loader missing"):
            h38.inspect_ct(no_loader)

    def test_lifecycle_markers_must_really_exist(self) -> None:
        result = h38.inspect_lifecycle(TEXTS)
        self.assertEqual(result["loader_online_quant_finalize"], "SOURCE_PRESENT")
        broken = dict(TEXTS)
        broken["layerwise"] = broken["layerwise"].replace(
            "materialize_layer(layer, info)", "skip_materialize(layer, info)"
        )
        with self.assertRaisesRegex(ValueError, "missing materialize_layer"):
            h38.inspect_lifecycle(broken)

    def test_installed_sources_are_hashed_from_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for key, rel in h38.FILES.items():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(TEXTS[key], encoding="utf-8")
            result = h38.inspect(root)
            self.assertEqual(sum(key.startswith("source_sha256_") for key in result), 6)
            self.assertEqual(result["routed_quant_method_order"], "SOURCE_PRESENT")
            self.assertTrue(all(len(value) == 64 for key, value in result.items()
                                if key.startswith("source_sha256_")))

    def test_runner_no_gpu_model_or_host_tuning(self) -> None:
        text = RUNNER.read_text(encoding="utf-8")
        self.assertIn("--runtime runc --network none --read-only", text)
        self.assertIn("--cap-drop ALL --security-opt no-new-privileges", text)
        self.assertIn("--memory 512m --memory-swap 512m", text)
        self.assertIn("--pull never", text)
        self.assertIn("--user 65534:65534", text)
        self.assertIn("checkout_dirty", text)
        self.assertIn("ct_meta_w13_patch_implemented=NO", text)
        for forbidden in ("docker build", "docker pull", "systemctl", "--gpus all",
                          "drop_caches", "compact_memory", "sysctl -w"):
            self.assertNotIn(forbidden, text)
        proc = subprocess.run(["bash", "-n", str(RUNNER)],
                              capture_output=True, text=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_runner_rejects_absent_sha_before_docker(self) -> None:
        import os
        env = dict(os.environ)
        env.pop("H38_CT_META_SOURCE_TARGET_SHA", None)
        proc = subprocess.run(
            ["bash", str(RUNNER)], env=env, capture_output=True,
            text=True, check=False,
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("exact_sha_required", proc.stderr)


if __name__ == "__main__":
    unittest.main()
