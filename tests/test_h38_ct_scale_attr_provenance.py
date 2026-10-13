"""CPU/stdlib-only regression tests for H38 CT scale attribute source sites."""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PY = ROOT / "scripts/benchmark/inspect-h38-ct-scale-attr-provenance.py"
SH = ROOT / "scripts/benchmark/check-h38-ct-scale-attr-provenance.sh"

spec = importlib.util.spec_from_file_location("h38_ct_attr_sites", PY)
assert spec and spec.loader
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

CT = """
class CompressedTensorsW4A4Nvfp4MoEMethod:
    def create_weights(self, layer, **extra_weight_attrs):
        weight_loader = extra_weight_attrs.get("weight_loader")
        w13_input_scale = torch.nn.Parameter(torch.empty(512, 2))
        layer.register_parameter("w13_input_global_scale", w13_input_scale)
        extra_weight_attrs.update({"quant_method": FusedMoeWeightScaleSupported.TENSOR.value})
        set_weight_attrs(w13_input_scale, extra_weight_attrs)
        w2_input_scale = torch.nn.Parameter(torch.empty(512))
        layer.register_parameter("w2_input_global_scale", w2_input_scale)
        extra_weight_attrs.update({"quant_method": FusedMoeWeightScaleSupported.TENSOR.value})
        set_weight_attrs(w2_input_scale, extra_weight_attrs)
"""

ROUTED = """
class RoutedExperts:
    def __init__(self):
        quant_params = {'weight_loader': self.weight_loader}
"""

LAYERWISE = """
def _wrap_parameters_weight_loader(layer):
    for name, tensor in get_layer_tensors(layer).items():
        tensor.weight_loader = make_online_process_loader(layer, name)

def make_online_process_loader(layer, param_name):
    param = getattr(layer, param_name)
    original_loader = _get_original_loader(param)
    return original_loader
"""

ATTRS = """
def set_weight_attrs(weight, weight_attrs):
    if weight_attrs is None:
        return
    for key, value in weight_attrs.items():
        assert not hasattr(weight, key), "overwriting"
        setattr(weight, key, value)
"""

FIXTURES = {
    "ct": CT, "routed": ROUTED, "layerwise": LAYERWISE,
    "attrs_helper": ATTRS,
}


class SourceScaleAttrTests(unittest.TestCase):
    def test_input_scales_require_postconstruction_setter(self) -> None:
        output = self.check()
        self.assertEqual(
            output["classification"],
            "EXACT_IMAGE_SOURCE_SITES_ONLY_NOT_RUNTIME_QUALIFICATION",
        )
        self.assertEqual(set(output["ct_input_scale_sites"]), set(tool.INPUT_SCALES))
        for row in output["ct_input_scale_sites"].values():
            self.assertEqual(row["attr_setter_source_site"], "PRESENT")
            self.assertLess(row["register_line"], row["set_weight_attrs_line"])
            self.assertLess(row["register_line"],
                            row["quant_method_tensor_update_line"])
            self.assertEqual(row["attribute_value_at_runtime"], "UNVERIFIED")
        self.assertEqual(output["effective_runtime_attr_value"], "UNVERIFIED")
        self.assertEqual(output["gpu_or_model_runtime"], "NOT_EXECUTED")
        self.assertEqual(
            output["attrs_helper_digest_status"],
            "IMAGE_ID_GUARDED_OBSERVATION_NOT_PREPINNED",
        )

    def check(self, **changes: str) -> dict:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            expected = {}
            for key, rel in tool.SOURCES.items():
                raw = changes.get(key, FIXTURES[key]).encode("utf-8")
                source = path / rel
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_bytes(raw)
                expected[key] = hashlib.sha256(raw).hexdigest()
            with patch.dict(tool.EXPECTED_SHA256, expected):
                return tool.inspect(path)

    def test_missing_input_scale_setter_fails_closed(self) -> None:
        broken = CT.replace("set_weight_attrs(w13_input_scale, extra_weight_attrs)",
                            "untracked_assignment(w13_input_scale)")
        with self.assertRaisesRegex(ValueError, "expected_one_attr_setter:w13"):
            self.check(ct=broken)

    def test_setter_before_register_fails_closed(self) -> None:
        broken = CT.replace(
            'layer.register_parameter("w13_input_global_scale", w13_input_scale)\n'
            '        extra_weight_attrs.update',
            'set_weight_attrs(w13_input_scale, extra_weight_attrs)\n'
            '        layer.register_parameter("w13_input_global_scale", w13_input_scale)\n'
            '        extra_weight_attrs.update',
            1,
        ).replace(
            '        set_weight_attrs(w13_input_scale, extra_weight_attrs)\n'
            '        w2_input_scale',
            '        w2_input_scale',
        )
        with self.assertRaisesRegex(ValueError, "attr_setter_before_registration:w13"):
            self.check(ct=broken)

    def test_tensor_quant_method_tag_must_precede_setter(self) -> None:
        broken = CT.replace(
            'extra_weight_attrs.update({"quant_method": FusedMoeWeightScaleSupported.TENSOR.value})',
            'extra_weight_attrs.update({"quant_method": FusedMoeWeightScaleSupported.GROUP.value})',
            1,
        )
        with self.assertRaisesRegex(ValueError, "missing_tensor_quant_tag_before_setter:w13"):
            self.check(ct=broken)

    def test_wrong_attribute_dict_fails_closed(self) -> None:
        broken = CT.replace(
            "set_weight_attrs(w13_input_scale, extra_weight_attrs)",
            "set_weight_attrs(w13_input_scale, {})",
        )
        with self.assertRaisesRegex(ValueError, "unexpected_attr_dict:w13"):
            self.check(ct=broken)

    def test_missing_weight_loader_origin_fails_closed(self) -> None:
        broken = CT.replace(
            'extra_weight_attrs.get("weight_loader")',
            'extra_weight_attrs.get("not_weight_loader")',
        )
        with self.assertRaisesRegex(ValueError, "missing_H11_weight_loader_origin"):
            self.check(ct=broken)

    def test_weight_loader_pop_fails_closed(self) -> None:
        broken = CT.replace(
            'weight_loader = extra_weight_attrs.get("weight_loader")',
            'weight_loader = extra_weight_attrs.get("weight_loader")\n'
            '        extra_weight_attrs.pop("weight_loader")',
        )
        with self.assertRaisesRegex(ValueError, "extra_attrs_loader_popped"):
            self.check(ct=broken)

    def test_routed_loader_export_must_exist(self) -> None:
        broken = ROUTED.replace(
            "'weight_loader': self.weight_loader",
            "'weight_loader': self.default_loader",
        )
        with self.assertRaisesRegex(ValueError, "missing_routed_loader_export"):
            self.check(routed=broken)

    def test_layerwise_reassign_loader_must_exist(self) -> None:
        broken = LAYERWISE.replace(
            "tensor.weight_loader = make_online_process_loader(layer, name)",
            "tensor.unexpected_attr = make_online_process_loader(layer, name)",
        )
        with self.assertRaisesRegex(ValueError, "missing_layerwise_loader_assignment"):
            self.check(layerwise=broken)

    def test_common_attr_helper_must_have_guarded_setattr(self) -> None:
        broken = ATTRS.replace("setattr(weight, key, value)",
                               "raise RuntimeError('no setter')")
        with self.assertRaisesRegex(ValueError, "missing_setattr"):
            self.check(attrs_helper=broken)
        broken = ATTRS.replace('assert not hasattr(weight, key), "overwriting"',
                               'assert True')
        with self.assertRaisesRegex(ValueError, "missing_attr_overwrite_guard"):
            self.check(attrs_helper=broken)

    def test_ct_source_sha_drift_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            expected = {}
            for key, rel in tool.SOURCES.items():
                source = path / rel
                source.parent.mkdir(parents=True, exist_ok=True)
                raw = FIXTURES[key].encode("utf-8")
                source.write_bytes(raw)
                expected[key] = hashlib.sha256(raw).hexdigest()
            with patch.dict(tool.EXPECTED_SHA256, expected):
                (path / tool.SOURCES["ct"]).write_text(CT + "\n# drift")
                with self.assertRaisesRegex(ValueError, "sha256_mismatch:ct"):
                    tool.inspect(path)

    def test_wrapper_maintains_isolation_and_sha_gate(self) -> None:
        shell = SH.read_text(encoding="utf-8")
        for guard in (
            "--runtime runc", "--network none", "--read-only",
            "--pull never", "--cap-drop ALL",
            "--security-opt no-new-privileges", "--pids-limit 64",
            "--memory 512m", "--memory-swap 512m",
            "--user 65534:65534", "checkout_sha_mismatch",
            "image_id_mismatch", "H11_label_mismatch",
            "H12_label_mismatch", "H38_label_mismatch",
        ):
            self.assertIn(guard, shell)
        for forbidden in ("docker build", "docker pull", "--gpus all",
                          "drop_caches", "sysctl -w", "systemctl"):
            self.assertNotIn(forbidden, shell)
        result = subprocess.run(
            ["bash", "-n", str(SH)], capture_output=True, text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_wrapper_requires_explicit_target(self) -> None:
        env = os.environ.copy()
        env.pop("H38_CT_SCALE_ATTR_TARGET_SHA", None)
        result = subprocess.run(
            ["bash", str(SH)], capture_output=True, text=True,
            check=False, env=env,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("exact_checkout_sha_required", result.stderr)


if __name__ == "__main__":
    unittest.main()
