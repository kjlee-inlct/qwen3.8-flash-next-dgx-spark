"""No-torch synthetic CT index-to-expert/shard key-grid and safety tests."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts/benchmark/inspect-h38-ct-checkpoint-key-map.py"
WRAPPER = ROOT / "scripts/benchmark/check-h38-ct-checkpoint-key-map.sh"
spec = importlib.util.spec_from_file_location("ct_checkpoint_key_map", TOOL)
assert spec and spec.loader
mapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mapper)


def generate(layers: int = 2, experts: int = 3) -> dict[str, str]:
    result = {}
    for lid in range(layers):
        for eid in range(experts):
            for proj, component in sorted(mapper.ALL_SLOTS):
                name = (
                    f"model.language_model.layers.{lid}.mlp.experts."
                    f"{eid}.{proj}.{component}"
                )
                result[name] = f"model-{lid + 1:05d}-of-00018.safetensors"
    result["mtp.layers.0.mlp.experts.down_proj"] = "model-mtp.safetensors"
    return result


class H38CTCheckpointKeyMapTests(unittest.TestCase):
    def test_all_nine_per_expert_base_slot_keys(self) -> None:
        output = mapper.analyze(generate(), layers=2, experts=3)
        self.assertEqual(output["status"], "PASS_BASE_KEY_SCHEMA_ONLY")
        self.assertEqual(output["base_routed_key_candidates"], 54)
        self.assertEqual(output["expected_base_keys_per_layer"], 27)
        self.assertEqual(output["incomplete_expert_grid_count"], 0)
        self.assertEqual(output["missing_canonical_slot_count"], 0)
        self.assertEqual(sum(output["per_CT_parameter_key_counts"].values()), 54)
        self.assertEqual(output["auxiliary_mtp_namespace_key_count"], 1)
        self.assertEqual(output["unique_destination_element_coverage"],
                         "UNVERIFIED")
        self.assertEqual(output["ct_input_scale_initialization_or_loading"],
                         "UNVERIFIED")
        self.assertEqual(output["h38_gpu_or_model_runtime"], "NOT_EXECUTED")
        self.assertEqual(
            set(output["ct_input_scale_parameters_not_in_nine_slot_schema"]),
            set(mapper.EXPECTED_CT_INPUT_SCALES),
        )

    def test_gate_up_down_to_w1_w3_w2_mapping_is_unambiguous(self) -> None:
        self.assertEqual(mapper.PROJECTION_SHARDS,
                         {"gate_proj": "w1", "up_proj": "w3",
                          "down_proj": "w2"})
        self.assertEqual(
            mapper.COMPONENT_PARAMETERS[("gate_proj", "weight_global_scale")],
            "w13_weight_global_scale",
        )
        self.assertEqual(
            mapper.COMPONENT_PARAMETERS[("up_proj", "weight_scale")],
            "w13_weight_scale",
        )
        self.assertEqual(
            mapper.COMPONENT_PARAMETERS[("down_proj", "weight")],
            "w2_weight_packed",
        )
        self.assertEqual(len(mapper.COMPONENT_PARAMETERS), 9)

    def test_one_missing_scale_flags_incomplete_grid(self) -> None:
        manifest = generate()
        manifest.pop("model.language_model.layers.0.mlp.experts.1."
                     "gate_proj.weight_global_scale")
        output = mapper.analyze(manifest, layers=2, experts=3)
        self.assertEqual(output["status"], "FAIL_KEY_SCHEMA")
        self.assertEqual(output["missing_canonical_slot_count"], 1)
        self.assertEqual(output["incomplete_expert_grid_count"], 1)
        self.assertIn("gate_proj.weight_global_scale",
                      output["missing_expert_slot_samples"][0]["missing_slots"])

    def test_duplicate_semantic_slot_rejected_even_if_index_keys_distinct(self) -> None:
        manifest = generate()
        key = "model.language_model.layers.0.mlp.experts.0.gate_proj.weight"
        manifest[key.replace(".experts.0.", ".experts.00.")] = manifest[key]
        output = mapper.analyze(manifest, layers=2, experts=3)
        self.assertEqual(output["status"], "FAIL_KEY_SCHEMA")
        self.assertEqual(len(output["duplicate_semantic_slot_samples"]), 1)

    def test_unrecognized_base_tensor_name_fails_closed(self) -> None:
        manifest = generate()
        manifest["model.language_model.layers.1.mlp.experts.2."
                 "down_proj.input_scale"] = "model-00002-of-00018.safetensors"
        output = mapper.analyze(manifest, layers=2, experts=3)
        self.assertEqual(output["status"], "FAIL_KEY_SCHEMA")
        self.assertEqual(len(output["unclassified_base_routed_key_samples"]), 1)
        self.assertGreater(output["checkpoint_key_names_with_input_scale_substring"], 0)

    def test_out_of_range_expert_rejected(self) -> None:
        manifest = generate()
        manifest["model.language_model.layers.0.mlp.experts.512."
                 "up_proj.weight"] = "model-00002-of-00018.safetensors"
        output = mapper.analyze(manifest, layers=2, experts=3)
        self.assertEqual(output["status"], "FAIL_KEY_SCHEMA")
        self.assertEqual(len(output["out_of_range_base_routed_key_samples"]), 1)

    def test_cross_shard_expert_is_metadata_only(self) -> None:
        manifest = generate()
        key = "model.language_model.layers.0.mlp.experts.0.up_proj.weight"
        manifest[key] = "model-00002-of-00018.safetensors"
        output = mapper.analyze(manifest, layers=2, experts=3)
        self.assertEqual(output["status"], "PASS_BASE_KEY_SCHEMA_ONLY")
        self.assertEqual(output["expert_with_keys_in_multiple_shards_count"], 1)
        self.assertEqual(output["unique_destination_element_coverage"],
                         "UNVERIFIED")

    def test_index_parser_rejects_duplicate_json_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            file = Path(td) / "model.safetensors.index.json"
            file.write_text('{"weight_map":{"x":"a.safetensors",'
                            '"x":"b.safetensors"}}')
            with self.assertRaisesRegex(ValueError, "duplicate_json_field:x"):
                mapper.read_index(Path(td))

    def test_reuses_original_strict_shard_index_guard(self) -> None:
        manifest = generate()
        # Existing resolver expects 18 referenced .safetensors files.
        filenames = [f"model-{i:05d}-of-00018.safetensors" for i in range(1, 18)]
        filenames.append("model-mtp.safetensors")
        keys = list(manifest)
        for i, name in enumerate(filenames):
            manifest[keys[i]] = name
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for filename in filenames:
                (root / filename).write_bytes(b"")  # no header or payload reads
            (root / "model.safetensors.index.json").write_text(
                json.dumps({"weight_map": manifest}), encoding="utf-8")
            resolve = mapper.load_qualified_shards_guard()
            shards, original = resolve(root)
            loaded, digest = mapper.read_index(root)
            self.assertEqual(len(shards), 18)
            self.assertEqual(loaded, original)
            self.assertEqual(len(digest), 64)
            (root / "extra.safetensors").write_bytes(b"")
            with self.assertRaisesRegex(ValueError, "unindexed_shard_files_present"):
                resolve(root)

    def test_wrapper_guard_and_read_only_scope(self) -> None:
        source = WRAPPER.read_text(encoding="utf-8")
        for must in (
            "H38_CKPT_CT_KEY_MAP_TARGET_SHA",
            "H38_CKPT_CT_KEY_MAP_MODEL_DIR",
            "exact_checkout_sha", "checkout_sha_mismatch", "dirty_checkout",
            "image_id_mismatch", "--runtime runc", "--network none",
            "--read-only", "--pull never", "--cap-drop ALL",
            "--security-opt no-new-privileges", "--pids-limit 64",
            "--memory 1g", "--memory-swap 1g", "--cpus 1",
            "--user 65534:65534", "readonly",
            "H38_CKPT_CT_KEY_MAP_PREFLIGHT=KEY_SCHEMA_FAIL",
            "source_inspectors_missing",
            "inspect-h38-checkpoint-metadata-order.py",
            "image_identity_unchanged=YES",
        ):
            self.assertIn(must, source)
        for bad in ("--gpus all", "docker build", "docker pull ",
                    "--privileged", "--user 0:0", "systemctl", "sysctl -w",
                    "drop_caches", "compact_memory"):
            self.assertNotIn(bad, source)
        self.assertEqual(source.count("--mount "), 3)
        self.assertEqual(subprocess.run(["bash", "-n", str(WRAPPER)],
                                        capture_output=True).returncode, 0)
        os_env = dict(os.environ)
        os_env.pop("H38_CKPT_CT_KEY_MAP_TARGET_SHA", None)
        os_env.pop("H38_CKPT_CT_KEY_MAP_MODEL_DIR", None)
        proc = subprocess.run(["bash", str(WRAPPER)], env=os_env,
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("exact_checkout_sha_required", proc.stderr)

    def test_python_inspector_prohibits_tensor_payload_methods(self) -> None:
        source = TOOL.read_text(encoding="utf-8")
        for bad in ("get_tensor(", "get_slice(", "torch.load(",
                    "safe_open(", ".read_header(", "read_header("):
            self.assertNotIn(bad, source)
        self.assertIn("resolve_shards(args.model_dir)", source)
        self.assertIn("checkpoint_index_sha256", source)


if __name__ == "__main__":
    unittest.main()
