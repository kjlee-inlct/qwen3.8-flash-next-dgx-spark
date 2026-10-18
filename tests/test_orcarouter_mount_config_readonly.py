"""Host-free read-only OrcaRouter protected-mount config inspector tests."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SRC = Path(__file__).resolve().parents[1] / "scripts" / "model"
sys.path.insert(0, str(SRC))
spec = importlib.util.spec_from_file_location(
    "orca_mount_config_test_target", SRC / "inspect_orcarouter_mount_config_readonly.py"
)
assert spec and spec.loader
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def source_config() -> dict:
    return {
        "architectures": ["Qwen4ExpForConditionalGeneration"],
        "model_type": "qwen4_exp",
        "text_config": {
            "layer_types": ["linear_attention"] * 36 + ["qwen_sparse_attention"] * 12,
            "ple_layer_ids": [2],
        },
        "quantization_config": {
            "quant_method": "compressed-tensors",
            "format": "mixed-precision",
            "config_groups": {
                "g0": {"targets": ["ModuleA", "ModuleB"]},
                "g1": {"targets": ["re:.*experts"]},
            },
            "ignore": ["a", "b", "c"],
        },
    }


class FakeMountEnvironment:
    def __init__(self, parent: Path):
        self.model = parent / "real-preserved-model"
        self.model.mkdir()
        self.override = parent / "existing-config-override.json"
        self.original = source_config()
        (self.model / "config.json").write_text(json.dumps(self.original), encoding="utf-8")
        self.override.write_text(
            json.dumps(checker.prepare_config.convert_layer_types(self.original)[0]),
            encoding="utf-8",
        )
        self.different_legacy_source = False
        self.inspected: list[str] = []
        self.precheck_ok = True

    def inspect_now(self):
        return ({"current_static_postcheck": (
            "PASS_CURRENT_ONLY" if self.precheck_ok else "STOP_REVIEW_REQUIRED"
        )}, self.precheck_ok)

    def fetch(self, kind: str, cid: str):
        self.inspected.append(f"{kind}:{cid}")
        assert kind == "container"
        assert cid in [v for _, v in checker.CONTAINERS]
        model = self.model
        if cid == checker.CONTAINERS[1][1] and self.different_legacy_source:
            model = self.model.parent / "different-model"
        return {
            "Id": cid,
            "Image": checker.guard.probe.EXPECTED_IMAGE_ID,
            "Mounts": [
                {"Destination": "/model", "Type": "bind",
                 "RW": False, "Source": str(model)},
                {"Destination": "/model/config.json", "Type": "bind",
                 "RW": False, "Source": str(self.override)},
            ],
        }


class OrcaMountConfigTests(unittest.TestCase):
    def test_success_from_mounts_when_guessed_home_model_path_does_not_exist(self):
        with tempfile.TemporaryDirectory() as d:
            env = FakeMountEnvironment(Path(d))
            with (patch.object(checker.guard, "inspect_now", side_effect=env.inspect_now),
                  patch.object(checker.guard, "fetch_one", side_effect=env.fetch)):
                result, ok = checker.assess()
            self.assertTrue(ok)
            self.assertEqual(result["verdict"], "PASS_SOURCE_CONFIG_ONLY_NOT_RUNTIME")
            self.assertEqual(result["config_rewrite"], "EXACT_EXPECTED_LAYER_TYPE_REWRITE")
            self.assertEqual(result["managed_original_config"], "REGULAR_BOUNDED_FILE")
            self.assertEqual(result["legacy_override_config"], "REGULAR_BOUNDED_FILE")
            self.assertEqual(result["community_layer_shape"],
                             "COUNTS_MATCH_NOT_CONFIG_EQUIVALENCE")
            self.assertEqual(result["original_ct_targets"], "3")
            self.assertEqual(result["original_ct_ignored"], "3")
            self.assertEqual(result["original_ct_groups"], "2")
            self.assertEqual(result["override_full_attention"], "12")
            self.assertEqual(len(env.inspected), 2)
            self.assertNotIn(str(Path(d)), repr(result))
            self.assertNotIn("Source", repr(result))
            self.assertEqual(result["docker_mutation"], "NONE")
            self.assertEqual(result["weights_read"], "NONE")

    def test_protected_current_postcheck_must_pass_before_inspecting_models(self):
        with tempfile.TemporaryDirectory() as d:
            env = FakeMountEnvironment(Path(d))
            env.precheck_ok = False
            with (patch.object(checker.guard, "inspect_now", side_effect=env.inspect_now),
                  patch.object(checker.guard, "fetch_one", side_effect=env.fetch)):
                result, ok = checker.assess()
            self.assertFalse(ok)
            self.assertEqual(result["verdict"], "STOP_PROTECTED_PRECHECK_FAILED")
            self.assertEqual(env.inspected, [])

    def test_missing_actual_original_config_is_not_claimed_deleted(self):
        with tempfile.TemporaryDirectory() as d:
            env = FakeMountEnvironment(Path(d))
            (env.model / "config.json").unlink()
            with (patch.object(checker.guard, "inspect_now", side_effect=env.inspect_now),
                  patch.object(checker.guard, "fetch_one", side_effect=env.fetch)):
                result, ok = checker.assess()
            self.assertFalse(ok)
            self.assertEqual(result["managed_original_config"], "NOT_PRESENT")
            self.assertEqual(result["verdict"], "STOP_MOUNTED_CONFIG_UNAVAILABLE")

    def test_different_protected_sources_refuses_single_config_fingerprint(self):
        with tempfile.TemporaryDirectory() as d:
            env = FakeMountEnvironment(Path(d))
            env.different_legacy_source = True
            with (patch.object(checker.guard, "inspect_now", side_effect=env.inspect_now),
                  patch.object(checker.guard, "fetch_one", side_effect=env.fetch)):
                result, ok = checker.assess()
            self.assertFalse(ok)
            self.assertEqual(result["model_sources"], "DIFFERENT")
            self.assertEqual(result["verdict"], "STOP_PROTECTED_MODEL_SOURCES_DIFFER")
            self.assertNotIn(str(Path(d)), repr(result))

    def test_nested_config_override_difference_is_reported_not_hidden(self):
        with tempfile.TemporaryDirectory() as d:
            env = FakeMountEnvironment(Path(d))
            changed = checker.prepare_config.convert_layer_types(env.original)[0]
            changed["quantization_config"]["ignore"].append("unexpected")
            env.override.write_text(json.dumps(changed), encoding="utf-8")
            with (patch.object(checker.guard, "inspect_now", side_effect=env.inspect_now),
                  patch.object(checker.guard, "fetch_one", side_effect=env.fetch)):
                result, ok = checker.assess()
            self.assertTrue(ok)
            self.assertEqual(result["config_rewrite"],
                             "CRITICAL_FIELDS_DIFFER_NOT_ONLY_EXPECTED_REWRITE")
            self.assertEqual(result["override_ct_ignored"], "4")

    def test_symlink_override_is_rejected_not_followed(self):
        with tempfile.TemporaryDirectory() as d:
            env = FakeMountEnvironment(Path(d))
            target = Path(d) / "target.json"
            target.write_text(json.dumps(source_config()), encoding="utf-8")
            env.override.unlink()
            env.override.symlink_to(target)
            with (patch.object(checker.guard, "inspect_now", side_effect=env.inspect_now),
                  patch.object(checker.guard, "fetch_one", side_effect=env.fetch)):
                result, ok = checker.assess()
            self.assertFalse(ok)
            self.assertEqual(result["managed_override_config"], "SYMLINK_STOP")
            self.assertEqual(result["verdict"], "STOP_MOUNTED_CONFIG_UNAVAILABLE")

    def test_invalid_quant_structure_returns_stop(self):
        with tempfile.TemporaryDirectory() as d:
            env = FakeMountEnvironment(Path(d))
            broken = copy.deepcopy(env.original)
            broken["quantization_config"]["config_groups"] = ["not a dict"]
            (env.model / "config.json").write_text(json.dumps(broken), encoding="utf-8")
            with (patch.object(checker.guard, "inspect_now", side_effect=env.inspect_now),
                  patch.object(checker.guard, "fetch_one", side_effect=env.fetch)):
                result, ok = checker.assess()
            self.assertFalse(ok)
            self.assertEqual(result["verdict"], "STOP_CT_STRUCTURE_INVALID")

    def test_readonly_protected_mount_permissions_must_hold(self):
        with tempfile.TemporaryDirectory() as d:
            env = FakeMountEnvironment(Path(d))
            original_fetch = env.fetch
            def altered(kind, cid):
                info = original_fetch(kind, cid)
                info["Mounts"][0]["RW"] = True
                return info
            with (patch.object(checker.guard, "inspect_now", side_effect=env.inspect_now),
                  patch.object(checker.guard, "fetch_one", side_effect=altered)):
                result, ok = checker.assess()
            self.assertFalse(ok)
            self.assertEqual(result["verdict"], "STOP_PROTECTED_MOUNT_UNQUALIFIED")


if __name__ == "__main__":
    unittest.main()
