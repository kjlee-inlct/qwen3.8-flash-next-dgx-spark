"""Pinned-source input-scale and online numel-threshold synthetic tests."""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
TOOL = BASE / "scripts/benchmark/inspect-h38-ct-input-scale-lifecycle.py"
SH = BASE / "scripts/benchmark/check-h38-ct-input-scale-lifecycle.sh"
spec = importlib.util.spec_from_file_location("ct_scale_lifecycle", TOOL)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

CT = """
class CompressedTensorsW4A4Nvfp4MoEMethod:
    def create_weights(self, layer, num_experts, w13_num_shards,
                       **extra_weight_attrs):
        w13_input_scale = torch.nn.Parameter(
            torch.empty(num_experts, w13_num_shards, dtype=torch.float32),
            requires_grad=False)
        layer.register_parameter("w13_input_global_scale", w13_input_scale)
        extra_weight_attrs.update({"quant_method": "tensor"})
        set_weight_attrs(w13_input_scale, extra_weight_attrs)
        w2_input_scale = torch.nn.Parameter(
            torch.empty(num_experts, dtype=torch.float32), requires_grad=False)
        layer.register_parameter("w2_input_global_scale", w2_input_scale)
        extra_weight_attrs.update({"quant_method": "tensor"})
        set_weight_attrs(w2_input_scale, extra_weight_attrs)

    def process_weights_after_loading(self, layer):
        a13_scale = 1.0 / layer.w13_input_global_scale
        a2_scale = 1.0 / layer.w2_input_global_scale
        layer.w13_input_scale = a13_scale
        layer.w2_input_scale = a2_scale
"""

LAYERWISE = """
def make_online_process_loader(layer, param_name):
    def online_process_loader(*args, **kwargs):
        info.loaded_weights.append((param_name, bound_args))
        num_loaded, ret = get_numel_loaded(original_loader, bound_args)
        info.load_numel += num_loaded
        if info.load_numel >= info.load_numel_total:
            _layerwise_process(layer, info)
        return ret
    return online_process_loader
"""

SAMPLES = {
    "ct": CT, "layerwise": LAYERWISE,
    "meta": "def marker_meta(): pass\n",
    "reload_utils": "def marker_utils(): pass\n",
}


class InputScaleLifecycleTests(unittest.TestCase):
    def inspect_fixture(self, **changes: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            digest = {}
            for key, rel in audit.SOURCES.items():
                raw = changes.get(key, SAMPLES[key]).encode("utf-8")
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                digest[key] = hashlib.sha256(raw).hexdigest()
            with patch.dict(audit.SHA256, digest):
                return audit.inspect(root)

    def test_pinned_source_fixture_reports_uses_not_runtime(self) -> None:
        report = self.inspect_fixture()
        self.assertEqual(report["classification"],
                         "PINNED_CT_INPUT_SCALE_LIFECYCLE_AND_COUNTER_SOURCE_ONLY")
        self.assertEqual(set(report["ct_input_scale_lifecycle"]),
                         set(audit.SCALE_NAMES))
        for scale in report["ct_input_scale_lifecycle"].values():
            self.assertEqual(
                scale["constructor"],
                "torch.nn.Parameter(torch.empty(...))",
            )
            self.assertFalse(scale["constructor_explicit_device"])
            self.assertFalse(scale["constructor_has_explicit_fill_value"])
            self.assertEqual(len(scale["postload_division_uses"]), 1)
            self.assertLess(scale["registration_line"],
                            scale["set_weight_attrs_line"])
            self.assertEqual(scale["effective_initial_value"], "UNVERIFIED")
        self.assertTrue(all(report["layerwise_counter_source"].values()))
        self.assertEqual(report["actual_copycounter_credit"], "UNVERIFIED")
        self.assertEqual(report["unique_destination_element_completion"],
                         "UNVERIFIED")
        self.assertEqual(report["gpu_model_or_checkpoint_read"],
                         "NOT_EXECUTED")

    def test_missing_postload_consumer_fails_closed(self) -> None:
        broken = CT.replace("1.0 / layer.w2_input_global_scale", "1.0")
        with self.assertRaisesRegex(ValueError, "missing_postload_consumer:w2"):
            self.inspect_fixture(ct=broken)

    def test_nonempty_constructor_is_rejected(self) -> None:
        broken = CT.replace(
            "torch.empty(num_experts, w13_num_shards, dtype=torch.float32)",
            "torch.ones(num_experts, w13_num_shards, dtype=torch.float32)",
        )
        with self.assertRaisesRegex(ValueError, "not_plain_empty_parameter:w13"):
            self.inspect_fixture(ct=broken)

    def test_loader_attribute_setter_missing_fails_closed(self) -> None:
        broken = CT.replace("set_weight_attrs(w13_input_scale, extra_weight_attrs)",
                            "register_only(w13_input_scale)")
        with self.assertRaisesRegex(ValueError, "scale_attr_setter_not_unique:w13"):
            self.inspect_fixture(ct=broken)

    def test_both_scales_required(self) -> None:
        broken = CT.replace(
            'layer.register_parameter("w2_input_global_scale", w2_input_scale)',
            'layer.register_parameter("missing_scale", w2_input_scale)',
        )
        with self.assertRaisesRegex(ValueError, "registered_scale_not_unique:w2"):
            self.inspect_fixture(ct=broken)

    def test_counter_must_use_original_loader(self) -> None:
        broken = LAYERWISE.replace(
            "get_numel_loaded(original_loader, bound_args)",
            "get_numel_loaded(unknown_loader, bound_args)",
        )
        with self.assertRaisesRegex(ValueError, "copy_count_from_original_loader"):
            self.inspect_fixture(layerwise=broken)

    def test_count_accumulation_must_exist(self) -> None:
        broken = LAYERWISE.replace(
            "info.load_numel += num_loaded", "info.load_numel += 0",
        )
        with self.assertRaisesRegex(ValueError, "count_accumulation"):
            self.inspect_fixture(layerwise=broken)

    def test_threshold_change_fails_closed(self) -> None:
        broken = LAYERWISE.replace(
            "info.load_numel >= info.load_numel_total",
            "info.load_numel == info.load_numel_total",
        )
        with self.assertRaisesRegex(ValueError, "completion_on_accumulated_threshold"):
            self.inspect_fixture(layerwise=broken)

    def test_missing_buffer_append_fails_closed(self) -> None:
        broken = LAYERWISE.replace(
            "info.loaded_weights.append((param_name, bound_args))",
            "unexpected_buffer((param_name, bound_args))",
        )
        with self.assertRaisesRegex(ValueError, "buffers_weight_arguments"):
            self.inspect_fixture(layerwise=broken)

    def test_source_drift_fails_before_any_ast_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            digests = {}
            for key, rel in audit.SOURCES.items():
                data = SAMPLES[key].encode("utf-8")
                file = root / rel
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(data)
                digests[key] = hashlib.sha256(data).hexdigest()
            with patch.dict(audit.SHA256, digests):
                (root / audit.SOURCES["ct"]).write_text(CT + "\n# drift")
                with self.assertRaisesRegex(ValueError, "source_sha256_mismatch:ct"):
                    audit.inspect(root)

    def test_wrapper_is_read_only_and_requires_pin(self) -> None:
        shell = SH.read_text(encoding="utf-8")
        for token in (
            "H38_CT_INPUT_SCALE_LIFECYCLE_TARGET_SHA",
            "--runtime runc", "--pull never", "--network none",
            "--read-only", "--cap-drop ALL",
            "--security-opt no-new-privileges", "--user 65534:65534",
            "--memory 512m", "--memory-swap 512m", "--cpus 1",
            "--pids-limit 64", "checkout_sha_mismatch",
            "image_id_mismatch", "H11_label_mismatch",
            "H12_label_mismatch", "H38_label_mismatch",
            "image_identity_unchanged=YES",
        ):
            self.assertIn(token, shell)
        for bad in (
            "--gpus", "docker build", "docker pull ",
            "--privileged", "systemctl", "sysctl -w", "drop_caches",
        ):
            self.assertNotIn(bad, shell)
        syntax = subprocess.run(["bash", "-n", str(SH)],
                                capture_output=True, text=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)
        env = os.environ.copy()
        env.pop("H38_CT_INPUT_SCALE_LIFECYCLE_TARGET_SHA", None)
        result = subprocess.run(
            ["bash", str(SH)], capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 2)
        self.assertIn("exact_checkout_sha_required", result.stderr)


if __name__ == "__main__":
    unittest.main()
