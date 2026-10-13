"""Fail-closed stdlib-only synthetic regression tests for pinned-source destinations."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts/benchmark/inspect-h38-ct-expert-destination-source.py"
SHELL = ROOT / "scripts/benchmark/check-h38-ct-expert-destination-source.sh"
spec = importlib.util.spec_from_file_location("h38_ct_expert_destination", TOOL)
assert spec and spec.loader
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)

CT = """
class CompressedTensorsW4A4Nvfp4MoEMethod:
    def create_weights(self, layer):
        w13_weight = object()
        w13_weight_scale = object()
        layer.register_parameter("w13_weight_packed", w13_weight)
        layer.register_parameter("w13_weight_scale", w13_weight_scale)
"""

ROUTED = """
class RoutedExperts:
    def get_expert_mapping(self):
        return self.build_expert_params_mapping()

    def load_weights(self, weights):
        expert_mapping = self.get_expert_mapping(include_fused=True)
        for expert_name, loaded_weight in weights:
            qual_name = expert_name
            for param_name, weight_name, expert_id, shard_id in expert_mapping:
                if weight_name not in qual_name:
                    continue
                if shard_id in {"w1", "w3"}:
                    fused_weight.chunk(2, dim=1)
                    loaded_weight.chunk(2, dim=0)
                success = param.weight_loader(
                    param=param, loaded_weight=loaded_weight,
                    weight_name=weight_name, shard_id=shard_id,
                    expert_id=expert_id, return_success=True)
                if success:
                    yield param_name

    def _map_global_expert_id_to_local_expert_id(self, expert_id):
        return self.expert_map_manager.map_global_to_local(expert_id)

    def weight_loader(self, param, loaded_weight, weight_name, shard_id, expert_id):
        global_expert_id = expert_id
        expert_id = self._map_global_expert_id_to_local_expert_id(global_expert_id)
        use_global_sf = getattr(self.quant_method, "use_global_sf", False) and "input_scale" in weight_name
        if expert_id == -1 and not use_global_sf:
            return
        if shard_id not in ("w1", "w2", "w3"):
            raise ValueError("bad shard")
        full_load = len(loaded_weight.shape) == 3
        if "input_scale" in weight_name:
            if "ModelOpt" in quant_method_name and shard_id in ("w1", "w3"):
                scale_shard_id = 0 if shard_id == "w1" else 1
            if "compressed" in quant_method_name.lower():
                raise ValueError("input_scales of w1 and w3")
            self._load_single_value(
                param=param, loaded_weight=loaded_weight,
                expert_id=global_expert_id if use_global_sf else expert_id)
        elif "scale" in weight_name:
            if param.quant_method == FusedMoeWeightScaleSupported.TENSOR.value:
                self._load_per_tensor_weight_scale(...)
            if param.quant_method == FusedMoeWeightScaleSupported.GROUP.value:
                self._load_model_weight_or_group_weight_scale(...)

    def _load_per_tensor_weight_scale(self, shard_id, param, loaded_weight, expert_id):
        param_data = param.data
        if shard_id in ("w1", "w3"):
            idx = 0 if shard_id == "w1" else 1
            param_data[expert_id][idx] = self._to_scalar(loaded_weight)
        elif shard_id == "w2":
            param_data[expert_id] = self._to_scalar(loaded_weight)

    def _load_single_value(self, param, loaded_weight, expert_id):
        param_data = param.data
        param_data[expert_id] = loaded_weight

    def _load_model_weight_or_group_weight_scale(self, shard_id):
        self._load_w13(...)
        self._load_w2(...)

    def _load_w13(self, expert_data, shard_dim, shard_id, loaded_weight):
        expert_data.narrow(shard_dim, 0, shard_size)
        expert_data.narrow(shard_dim, shard_size, shard_size)
        expert_data.copy_(loaded_weight)

    def _load_w2(self, expert_data, loaded_weight):
        expert_data.copy_(loaded_weight)
"""

FIXTURES = {
    "ct": CT,
    "routed": ROUTED,
    "layerwise": "def example(): pass\n",
    "meta": "def example(): pass\n",
}


class ExpertDestinationSourceTests(unittest.TestCase):
    def inspect_fixture(self, **changes: str) -> dict[str, object]:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            expected = {}
            for key, rel in tool.SOURCES.items():
                source = changes.get(key, FIXTURES[key]).encode("utf-8")
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(source)
                expected[key] = hashlib.sha256(source).hexdigest()
            with patch.dict(tool.PINNED, expected):
                return tool.inspect(root)

    def test_bounded_positive_source_anchor_contract(self) -> None:
        report = self.inspect_fixture()
        self.assertEqual(
            report["classification"],
            "PINNED_SOURCE_BRANCHES_ONLY_NO_REAL_EXPERT_COVERAGE",
        )
        self.assertTrue(all(
            all(section.values())
            for section in report["source_anchors"].values()
        ))
        self.assertEqual(len(report["conditional_destination_hypotheses"]), 8)
        self.assertEqual(
            report["unique_real_destination_coverage"], "UNVERIFIED")
        self.assertEqual(report["model_or_gpu_execution"], "NOT_EXECUTED")
        self.assertEqual(
            report["actual_input_scale_values_or_conflict"], "UNVERIFIED")

    def test_mapping_rejects_missing_callback(self) -> None:
        broken = ROUTED.replace("param.weight_loader(", "unexpected_loader(")
        with self.assertRaisesRegex(ValueError, "load_weights_callback"):
            self.inspect_fixture(routed=broken)

    def test_mapping_rejects_global_local_expert_removed(self) -> None:
        broken = ROUTED.replace(
            "expert_id = self._map_global_expert_id_to_local_expert_id(global_expert_id)",
            "expert_id = global_expert_id",
        )
        with self.assertRaisesRegex(ValueError, "global_to_local_expert_mapping"):
            self.inspect_fixture(routed=broken)

    def test_mapping_rejects_nonlocal_skip_removed(self) -> None:
        broken = ROUTED.replace("expert_id == -1 and not use_global_sf",
                                "expert_id > 0")
        with self.assertRaisesRegex(ValueError, "nonlocal_skip"):
            self.inspect_fixture(routed=broken)

    def test_mapping_rejects_fused_split_missing(self) -> None:
        broken = ROUTED.replace("fused_weight.chunk(2, dim=1)",
                                "unexpected_split()")
        with self.assertRaisesRegex(ValueError, "fused_tensor_split"):
            self.inspect_fixture(routed=broken)

    def test_tensor_w1_w3_slot_selection_must_be_present(self) -> None:
        broken = ROUTED.replace(
            'idx = 0 if shard_id == "w1" else 1',
            "idx = 0",
        )
        with self.assertRaisesRegex(ValueError, "tensor_scale_w1_w3_indices"):
            self.inspect_fixture(routed=broken)

    def test_input_scale_broad_row_write_site_must_exist(self) -> None:
        broken = ROUTED.replace(
            "param_data[expert_id] = loaded_weight",
            "param_data[expert_id][0] = loaded_weight",
        )
        with self.assertRaisesRegex(
                ValueError, "input_scale_single_value_full_row_assignment"):
            self.inspect_fixture(routed=broken)

    def test_modelopt_distinct_branch_stays_distinct(self) -> None:
        broken = ROUTED.replace(
            'scale_shard_id = 0 if shard_id == "w1" else 1',
            "scale_shard_id = 0",
        )
        with self.assertRaisesRegex(
                ValueError, "modelopt_separate_input_w1_w3_conditional"):
            self.inspect_fixture(routed=broken)

    def test_packed_w13_halves_must_remain_separate(self) -> None:
        broken = ROUTED.replace(
            "expert_data.narrow(shard_dim, shard_size, shard_size)",
            "expert_data.narrow(shard_dim, 0, shard_size)",
        )
        with self.assertRaisesRegex(ValueError, "w13_logical_second_half"):
            self.inspect_fixture(routed=broken)

    def test_ct_registration_source_mismatch_rejected(self) -> None:
        broken = CT.replace('"w13_weight_scale"', '"unexpected_scale"')
        with self.assertRaisesRegex(
                ValueError, "w13_group_scale_parameter_shape"):
            self.inspect_fixture(ct=broken)

    def test_source_digest_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            expected = {}
            for key, rel in tool.SOURCES.items():
                file = root / rel
                file.parent.mkdir(parents=True, exist_ok=True)
                b = FIXTURES[key].encode("utf-8")
                file.write_bytes(b)
                expected[key] = hashlib.sha256(b).hexdigest()
            with patch.dict(tool.PINNED, expected):
                (root / tool.SOURCES["routed"]).write_text(
                    ROUTED + "\n# unqualified drift")
                with self.assertRaisesRegex(ValueError, "sha256_mismatch:routed"):
                    tool.inspect(root)

    def test_wrapper_requires_pin_and_unchanged_safety(self) -> None:
        source = SHELL.read_text(encoding="utf-8")
        for required in (
            "--runtime runc", "--network none", "--read-only",
            "--pull never", "--cap-drop ALL",
            "--security-opt no-new-privileges",
            "--memory 512m", "--memory-swap 512m",
            "--pids-limit 64", "--user 65534:65534",
            "image_id_mismatch", "checkout_sha_mismatch",
            "H38_CT_EXPERT_DESTINATION_TARGET_SHA",
        ):
            self.assertIn(required, source)
        for forbidden in ("docker build", "docker pull", "--gpus all",
                          "drop_caches", "systemctl", "sysctl -w"):
            self.assertNotIn(forbidden, source)
        syntax = subprocess.run(["bash", "-n", str(SHELL)],
                                capture_output=True, text=True, check=False)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)

    def test_wrapper_missing_target_fails_pre_docker(self) -> None:
        env = os.environ.copy()
        env.pop("H38_CT_EXPERT_DESTINATION_TARGET_SHA", None)
        run = subprocess.run(["bash", str(SHELL)], env=env,
                             capture_output=True, text=True, check=False)
        self.assertEqual(run.returncode, 2)
        self.assertIn("exact_checkout_sha_required", run.stderr)


if __name__ == "__main__":
    unittest.main()
