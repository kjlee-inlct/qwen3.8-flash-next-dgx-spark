"""Fail-closed synthetic source regression for input-scale counted-numel target."""
from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
INSPECTOR = REPO / "scripts/benchmark/inspect-h38-ct-load-target-input-scale.py"
WRAPPER = REPO / "scripts/benchmark/check-h38-ct-load-target-input-scale.sh"
spec = importlib.util.spec_from_file_location("h38_ct_input_target_gap", INSPECTOR)
assert spec is not None and spec.loader is not None
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

CT = """
class CompressedTensorsW4A4Nvfp4MoEMethod:
    def create_weights(self, layer, num_experts):
        w13_num_shards = 2 if self.moe.is_act_and_mul else 1
        w13_input_scale = torch.nn.Parameter(
            torch.empty(num_experts, w13_num_shards, dtype=torch.float32),
            requires_grad=False)
        layer.register_parameter("w13_input_global_scale", w13_input_scale)
        w2_input_scale = torch.nn.Parameter(
            torch.empty(num_experts, dtype=torch.float32), requires_grad=False)
        layer.register_parameter("w2_input_global_scale", w2_input_scale)
"""
META = """
SKIP_LOAD_TENSORS: set[str] = {
    "_expert_map",
    "expert_mask",
    "expert_global_to_physical",
}
"""
UTILS = """
def get_layer_tensors(layer):
    params, buffers = get_layer_params_buffers(layer)
    return params | buffers

def get_layer_params_buffers(layer):
    return (
        {name: param for name, param in layer._parameters.items() if param is not None},
        {name: buffer for name, buffer in layer._buffers.items() if buffer is not None},
    )

def get_layer_size(layer):
    from .meta import SKIP_LOAD_TENSORS
    return sum(
        tensor.numel()
        for name, tensor in get_layer_tensors(layer).items()
        if name not in SKIP_LOAD_TENSORS
    )
"""
LAYER = """
def initialize_online_processing(layer):
    info.load_numel = 0
    info.load_numel_total = get_layer_size(layer)

def make_online_process_loader(layer, param_name):
    info = get_layerwise_info(layer)
    def online_process_loader(*args, **kwargs):
        info.load_numel_total = get_layer_size(layer)
        info.load_numel += num_loaded
        if info.load_numel >= info.load_numel_total:
            _layerwise_process(layer, info)
    return online_process_loader
"""
FIXTURES = {"ct": CT, "meta": META, "utils": UTILS, "layerwise": LAYER}


class InputScaleLoadTargetTests(unittest.TestCase):
    def check_fixture(self, **overrides: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pins = {}
            for name, relative in audit.SOURCES.items():
                data = overrides.get(name, FIXTURES[name]).encode("utf-8")
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                pins[name] = hashlib.sha256(data).hexdigest()
            with patch.dict(audit.EXPECTED_SHA256, pins):
                return audit.inspect(root)

    def test_source_conditional_target_contribution_only(self) -> None:
        report = self.check_fixture()
        self.assertEqual(
            report["classification"],
            "PINNED_SOURCE_POTENTIAL_INPUT_SCALE_NUMEL_TARGET_ONLY",
        )
        self.assertTrue(all(report["numel_target_source_checks"].values()))
        self.assertEqual(report["input_scale_names_in_skip_load_tensors"], [])
        self.assertEqual(
            report["input_scale_register_shapes"]["w13_input_global_scale"]
            ["shape_expressions"], ["num_experts", "w13_num_shards"],
        )
        self.assertEqual(
            report["input_scale_register_shapes"]["w2_input_global_scale"]
            ["shape_expressions"], ["num_experts"],
        )
        self.assertEqual(
            report["illustrative_if_num_experts_is_512"]
            ["per_layer_is_act_and_mul_true"], 1536,
        )
        self.assertEqual(
            report["illustrative_if_num_experts_is_512"]
            ["across_48_layers_if_true"], 73728,
        )
        self.assertEqual(report["actual_layerwise_threshold_deficit"],
                         "UNVERIFIED")
        self.assertEqual(report["model_gpu_checkpoint_runtime"],
                         "NOT_EXECUTED")

    def test_explicit_skip_input_scale_fails_closed(self) -> None:
        invalid = META.replace('"expert_mask",', '"expert_mask",\n"w2_input_global_scale",')
        with self.assertRaisesRegex(ValueError, "ct_scale_explicitly_skipped:w2"):
            self.check_fixture(meta=invalid)

    def test_nonliteral_skip_set_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "skip_load_set_not_literal"):
            self.check_fixture(meta="SKIP_LOAD_TENSORS = list(get_skips())")

    def test_missing_ct_registration_fails_closed(self) -> None:
        broken = CT.replace('"w13_input_global_scale"', '"w13_missing"')
        with self.assertRaisesRegex(ValueError, "ct_input_scale_missing:w13"):
            self.check_fixture(ct=broken)

    def test_wrong_packed_scale_shape_fails_closed(self) -> None:
        broken = CT.replace(
            "torch.empty(num_experts, w13_num_shards, dtype=torch.float32)",
            "torch.empty(num_experts, dtype=torch.float32)",
        )
        with self.assertRaisesRegex(ValueError, "ct_scale_unexpected_shape:w13"):
            self.check_fixture(ct=broken)

    def test_moe_shards_rule_must_be_preserved(self) -> None:
        broken = CT.replace("2 if self.moe.is_act_and_mul else 1", "1")
        with self.assertRaisesRegex(ValueError, "w13_shards_condition_unqualified"):
            self.check_fixture(ct=broken)

    def test_missing_get_layer_size_filtered_iteration_fails(self) -> None:
        broken = UTILS.replace(
            "if name not in SKIP_LOAD_TENSORS", "if True",
        )
        with self.assertRaisesRegex(ValueError, "size_excludes_skip_names_only"):
            self.check_fixture(utils=broken)

    def test_missing_parameters_from_layer_tensors_fails(self) -> None:
        broken = UTILS.replace("return params | buffers", "return buffers")
        with self.assertRaisesRegex(
                ValueError, "get_layer_tensors_returns_param_buffer_union"):
            self.check_fixture(utils=broken)

    def test_missing_layerwise_refresh_fails(self) -> None:
        broken = LAYER.replace(
            "info.load_numel_total = get_layer_size(layer)\n        info.load_numel",
            "info.load_numel_total = 1\n        info.load_numel",
        )
        with self.assertRaisesRegex(ValueError, "layerwise_refreshes_total"):
            self.check_fixture(layerwise=broken)

    def test_threshold_change_fails(self) -> None:
        broken = LAYER.replace(
            "info.load_numel >= info.load_numel_total",
            "info.load_numel == info.load_numel_total",
        )
        with self.assertRaisesRegex(ValueError, "layerwise_triggers_at_threshold"):
            self.check_fixture(layerwise=broken)

    def test_source_hash_drift_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pins = {}
            for name, relative in audit.SOURCES.items():
                raw = FIXTURES[name].encode("utf-8")
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
                pins[name] = hashlib.sha256(raw).hexdigest()
            with patch.dict(audit.EXPECTED_SHA256, pins):
                (root / audit.SOURCES["utils"]).write_text(UTILS + "\n#changed\n")
                with self.assertRaisesRegex(
                        ValueError, "source_sha256_mismatch:utils"):
                    audit.inspect(root)

    def test_wrapper_pin_and_isolation_safety(self) -> None:
        script = WRAPPER.read_text(encoding="utf-8")
        for token in (
            "H38_CT_INPUT_TARGET_GAP_TARGET_SHA",
            "checkout_sha_mismatch", "image_id_mismatch",
            "--runtime runc", "--pull never", "--network none",
            "--read-only", "--cap-drop ALL",
            "--security-opt no-new-privileges",
            "--memory 512m", "--memory-swap 512m",
            "--pids-limit 64", "--cpus 1", "--user 65534:65534",
            "image_identity_unchanged=YES",
        ):
            self.assertIn(token, script)
        for unsafe in (
            "--gpus", "docker build", "docker pull ",
            "--privileged", "sysctl -w", "systemctl",
        ):
            self.assertNotIn(unsafe, script)
        result = subprocess.run(
            ["bash", "-n", str(WRAPPER)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        env = os.environ.copy()
        env.pop("H38_CT_INPUT_TARGET_GAP_TARGET_SHA", None)
        result = subprocess.run(["bash", str(WRAPPER)], env=env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("exact_checkout_sha_required", result.stderr)


if __name__ == "__main__":
    unittest.main()
