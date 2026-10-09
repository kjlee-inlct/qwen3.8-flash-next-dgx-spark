"""CPU-only synthetic tests for pinned H38 CT accounting source inspection."""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import hashlib
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / "scripts/benchmark/inspect-h38-ct-layerwise-accounting.py"
SH = ROOT / "scripts/benchmark/check-h38-ct-layerwise-accounting.sh"
spec = importlib.util.spec_from_file_location("h38_ct_accounting", PY)
assert spec and spec.loader
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

CT = """
class CompressedTensorsW4A4Nvfp4MoEMethod:
    def create_weights(self, layer):
        weight_loader = loader
        w13 = ModelWeightParameter(data=torch.empty(num_experts, w13_num_shards * intermediate_size_per_partition, hidden_size // 2, dtype=torch.uint8),
                                   input_dim=1, output_dim=2,
                                   weight_loader=weight_loader)
        w2 = ModelWeightParameter(data=torch.empty(num_experts, hidden_size, intermediate_size_per_partition // 2, dtype=torch.uint8),
                                  input_dim=1, output_dim=2,
                                  weight_loader=weight_loader)
        layer.register_parameter("w13_weight_packed", w13)
        layer.register_parameter("w2_weight_packed", w2)
        for name in []:
            pass
        a = torch.nn.Parameter(torch.empty(num_experts, w13_num_shards * intermediate_size_per_partition, hidden_size // self.group_size, dtype=torch.float8_e4m3fn))
        b = torch.nn.Parameter(torch.empty(num_experts, hidden_size, intermediate_size_per_partition // self.group_size, dtype=torch.float8_e4m3fn))
        c = torch.nn.Parameter(torch.empty(num_experts, w13_num_shards, dtype=torch.float32))
        d = torch.nn.Parameter(torch.empty(num_experts, dtype=torch.float32))
        e = torch.nn.Parameter(torch.empty(num_experts, w13_num_shards, dtype=torch.float32))
        f = torch.nn.Parameter(torch.empty(num_experts, dtype=torch.float32))
        layer.register_parameter("w13_weight_scale", a)
        layer.register_parameter("w2_weight_scale", b)
        layer.register_parameter("w13_weight_global_scale", c)
        layer.register_parameter("w2_weight_global_scale", d)
        layer.register_parameter("w13_input_global_scale", e)
        layer.register_parameter("w2_input_global_scale", f)

    def process_weights_after_loading(self, layer):
        layer.register_parameter("w13_weight", layer.w13_weight_packed)
        delattr(layer, "w13_weight_packed")
        layer.register_parameter("w2_weight", layer.w2_weight_packed)
        delattr(layer, "w2_weight_packed")
"""

LAYERWISE = """
def initialize_online_processing(layer):
    info.load_numel_total = get_layer_size(layer)
    _wrap_parameters_weight_loader(layer)

def make_online_process_loader(layer, param_name):
    def online_process_loader(*args, **kwargs):
        if not info.can_load():
            return
        info.load_numel_total = get_layer_size(layer)
        _wrap_parameters_weight_loader(layer)
        info.loaded_weights.append((param_name, args))
        num_loaded, ret = get_numel_loaded(original_loader, bound_args)
        info.load_numel += num_loaded
        if info.load_numel >= info.load_numel_total:
            _layerwise_process(layer, info)
        return ret
    return online_process_loader

def _layerwise_process(layer, info):
    materialize_layer(layer, info)
    for param_name, arguments in info.loaded_weights:
        param.weight_loader(*arguments)
    quant_method.process_weights_after_loading(layer)

def finalize_layerwise_processing(model, model_config):
    if info.load_numel < info.load_numel_total:
        _layerwise_process(layer, info)
"""

META = """
class CopyCounter:
    def __torch_dispatch__(self, func, types, args=(), kwargs=None):
        if func is torch.ops.aten.copy_.default:
            self.copied_numel += args[0].numel()

def get_numel_loaded(weight_loader, args):
    numel = counter.copied_numel
    if isinstance(param, torch.Tensor):
        numel = min(numel, param.numel())
    return numel, value

def materialize_layer(layer, info):
    if tensor.is_meta:
        materialize_meta_tensor(tensor)

def materialize_meta_tensor(meta_tensor):
    tensor = torch.empty_strided(size=meta_tensor.size(), stride=meta_tensor.stride(), dtype=meta_tensor.dtype)
    tensor.__class__ = meta_tensor.__class__
    tensor.__dict__ = meta_tensor.__dict__.copy()
    return tensor
"""

UTILS = """
def get_layer_size(layer):
    return sum(t.numel() for name, t in tensors.items() if name not in SKIP_LOAD_TENSORS)
"""

FIXTURES = {"ct": CT, "layerwise": LAYERWISE, "meta": META, "utils": UTILS}


class H38CtAccountingTests(unittest.TestCase):
    def parse(self, name: str) -> ast.Module:
        return ast.parse(FIXTURES[name])

    def test_ct_packed_and_six_scale_registrations(self) -> None:
        row = tool.assert_packed_and_h12({"ct": self.parse("ct")})
        self.assertEqual(len(row["registrations"]), 8)
        self.assertEqual(row["h12_object_alias_syntax"], "PRESENT")
        self.assertEqual(row["registrations"]["w13_weight_packed"]["initializer_type"],
                         "ModelWeightParameter")


    def test_packed_dimensions_and_dtypes_are_explicitly_captured(self) -> None:
        row = tool.assert_packed_and_h12({"ct": self.parse("ct")})
        w13 = row["registrations"]["w13_weight_packed"]["allocation"]
        self.assertEqual(w13["dtype"], "torch.uint8")
        self.assertEqual(w13["device"], "NOT_EXPLICIT")
        self.assertEqual(w13["input_dim"], "1")
        self.assertEqual(w13["output_dim"], "2")
        self.assertEqual(
            row["registrations"]["w13_weight_scale"]["allocation"]["dtype"],
            "torch.float8_e4m3fn")
        self.assertEqual(row["registrations"]["w2_weight_global_scale"]
                         ["allocation"]["shape"], ["num_experts"])

    def test_changed_shape_or_dtype_fails_closed(self) -> None:
        changed = CT.replace("hidden_size // 2, dtype=torch.uint8",
                             "hidden_size, dtype=torch.uint8")
        with self.assertRaisesRegex(ValueError, "incorrect_CT_parameter_shape"):
            tool.assert_packed_and_h12({"ct": ast.parse(changed)})
        changed_scale = CT.replace(
            "hidden_size // self.group_size, dtype=torch.float8_e4m3fn",
            "hidden_size // self.group_size, dtype=torch.float32")
        with self.assertRaisesRegex(ValueError, "incorrect_CT_parameter_dtype"):
            tool.assert_packed_and_h12({"ct": ast.parse(changed_scale)})

    def test_meta_allocation_is_not_accepted_as_old_image(self) -> None:
        changed = CT.replace(
            "hidden_size // 2, dtype=torch.uint8)",
            "hidden_size // 2, dtype=torch.uint8, device='meta')")
        with self.assertRaisesRegex(ValueError, "explicit_CT_allocation_device"):
            tool.assert_packed_and_h12({"ct": ast.parse(changed)})

    def test_missing_meta_subclass_preservation_fails_closed(self) -> None:
        changed = META.replace(
            "tensor.__class__ = meta_tensor.__class__", "tensor.__class__ = torch.Tensor")
        with self.assertRaisesRegex(ValueError, "materialize_preserves_parameter_class"):
            tool.check_accounting({
                "layerwise": self.parse("layerwise"),
                "meta": ast.parse(changed),
                "utils": self.parse("utils"),
            })

    def test_missing_partial_finalization_is_reported(self) -> None:
        changed = LAYERWISE.replace(
            "if info.load_numel < info.load_numel_total:",
            "if info.load_numel == info.load_numel_total:")
        with self.assertRaisesRegex(ValueError, "partial_layer_finalization"):
            tool.check_accounting({
                "layerwise": ast.parse(changed),
                "meta": self.parse("meta"),
                "utils": self.parse("utils"),
            })

    def test_missing_scale_blocks_source_contract(self) -> None:
        broken = CT.replace('layer.register_parameter("w2_input_global_scale", f)',
                            'layer.skip_parameter("w2_input_global_scale", f)')
        with self.assertRaisesRegex(ValueError, "missing_parameter_registration"):
            tool.assert_packed_and_h12({"ct": ast.parse(broken)})

    def test_rewrapping_does_not_match_h12_identity_contract(self) -> None:
        broken = CT.replace(
            'layer.register_parameter("w13_weight", layer.w13_weight_packed)',
            'layer.w13_weight = torch.nn.Parameter(layer.w13_weight_packed.data)',
        )
        with self.assertRaisesRegex(ValueError, "missing_H12_identity_alias"):
            tool.assert_packed_and_h12({"ct": ast.parse(broken)})

    def test_accounting_count_and_replay_source_anchors(self) -> None:
        out = tool.check_accounting({
            "layerwise": self.parse("layerwise"),
            "meta": self.parse("meta"),
            "utils": self.parse("utils"),
        })
        self.assertTrue(all(out["anchors"].values()))
        self.assertIn("NOT proven", out["note"])

    def test_removed_count_cap_fails_closed(self) -> None:
        broken = META.replace("min(numel, param.numel())", "numel")
        with self.assertRaisesRegex(ValueError, "per_call_count_capped"):
            tool.check_accounting({
                "layerwise": self.parse("layerwise"),
                "meta": ast.parse(broken),
                "utils": self.parse("utils"),
            })

    def test_installed_source_hashes_reject_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            expected = {}
            for key, rel in tool.FILES.items():
                path = directory / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                raw = FIXTURES[key].encode("utf-8")
                path.write_bytes(raw)
                expected[key] = hashlib.sha256(raw).hexdigest()
            with patch.dict(tool.EXPECTED_SHA256, expected):
                report = tool.inspect(directory)
                self.assertEqual(report["classification"],
                                 "SOURCE_CONTRACT_ONLY_NOT_RUNTIME_QUALIFICATION")
                self.assertEqual(report["complete_parameter_coverage"], "UNVERIFIED")
                path = directory / tool.FILES["meta"]
                path.write_text(META + "\n# drift\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "sha256_mismatch:meta"):
                    tool.inspect(directory)

    def test_no_unsafe_host_or_gpu_actions_in_runner(self) -> None:
        script = SH.read_text(encoding="utf-8")
        for guard in ("--runtime runc", "--network none", "--read-only",
                      "--pull never", "--cap-drop ALL",
                      "--security-opt no-new-privileges", "--user 65534:65534",
                      "--memory 512m", "checkout_sha_mismatch", "image_id_mismatch"):
            self.assertIn(guard, script)
        for forbidden in ("docker build", "docker pull", "--gpus all",
                          "systemctl", "drop_caches", "sysctl -w"):
            self.assertNotIn(forbidden, script)
        syntax = subprocess.run(["bash", "-n", str(SH)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)

    def test_runner_requires_exact_sha_before_docker(self) -> None:
        env = dict(os.environ)
        env.pop("H38_CT_ACCOUNTING_TARGET_SHA", None)
        run = subprocess.run(["bash", str(SH)], env=env,
                             capture_output=True, text=True, check=False)
        self.assertEqual(run.returncode, 2)
        self.assertIn("exact_checkout_sha_required", run.stderr)


if __name__ == "__main__":
    unittest.main()
