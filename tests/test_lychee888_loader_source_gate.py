"""Offline lychee888 source-only loader diagnostic; never touches HF/model/GPU."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/model"))
gate = importlib.import_module("assess_lychee888_loader")
ple = importlib.import_module("inspect_lychee888_metadata")
PATCH = gate.PATCH.read_text(encoding="utf-8")
DOCKERFILE = gate.DOCKERFILE.read_text(encoding="utf-8")


def fixture(method="compressed-tensors"):
    names = list(ple.PLE_FILES) + [
        "config.json", "model.safetensors.index.json",
        "model-00003-of-00017.safetensors",
    ]
    api = {"id": ple.REPO, "sha": gate.REVISION,
           "siblings": [{"rfilename": name} for name in names]}
    config = {
        "text_config": {"ple_embedding_dtype": "float8_e4m3fn"},
        "quantization_config": {"quant_method": method},
    }
    prefix = "model.language_model.ple.ple_embedding."
    weight_map = {
        f"{prefix}ngram_embedding.shard_{i}.weight": ple.PLE_FILES[min(i // 13, 9)]
        for i in range(128)
    }
    weight_map[prefix + "weight_scale"] = ple.PLE_FILES[-1]
    return api, config, {"weight_map": weight_map}


class Lychee888LoaderSourceGateTests(unittest.TestCase):
    def test_compressed_tensors_does_not_claim_nv_patch_compatibility(self):
        result = gate.assess(*fixture(), PATCH, DOCKERFILE)
        self.assertEqual(result["verdict"], "SOURCE_ONLY_LOADER_UNQUALIFIED")
        self.assertEqual(result["l0_verdict"], "INDEX_STRUCTURE_PASS_METADATA_ONLY")
        self.assertIn("NOT_APPLICABLE", result["nvidia_patch_source_dispatch"])
        self.assertEqual(result["global_weight_scale_keys"], 1)
        self.assertEqual(result["single_gb10_tp1"], "NOT_VERIFIED")

    def test_even_modelopt_mixed_is_not_a_runtime_pass(self):
        result = gate.assess(*fixture(method="modelopt_mixed"), PATCH, DOCKERFILE)
        self.assertIn("CLASS_ONLY", result["nvidia_patch_source_dispatch"])
        self.assertEqual(result["verdict"], "SOURCE_ONLY_LOADER_UNQUALIFIED")

    def test_wrong_revision_rejected(self):
        docs = fixture()
        docs[0]["sha"] = "f" * 40
        with self.assertRaisesRegex(ple.MetadataError, "approved immutable"):
            gate.assess(*docs, PATCH, DOCKERFILE)

    def test_missing_quant_config_or_method_rejected(self):
        docs = fixture()
        docs[1].pop("quantization_config")
        with self.assertRaisesRegex(ple.MetadataError, "quantization_config"):
            gate.assess(*docs, PATCH, DOCKERFILE)
        docs[1]["quantization_config"] = {}
        with self.assertRaisesRegex(ple.MetadataError, "quant_method"):
            gate.assess(*docs, PATCH, DOCKERFILE)

    def test_missing_fp8_ple_shard_fails_closed(self):
        docs = fixture()
        docs[2]["weight_map"].pop(
            "model.language_model.ple.ple_embedding.ngram_embedding.shard_127.weight")
        with self.assertRaisesRegex(ple.MetadataError, "exactly 128"):
            gate.assess(*docs, PATCH, DOCKERFILE)

    def test_source_patch_marker_or_docker_base_changed_fails_closed(self):
        with self.assertRaisesRegex(ple.MetadataError, "source anchors"):
            gate.assess(*fixture(), PATCH.replace("ModelOptMixedPrecisionConfig", "MissingConfig"), DOCKERFILE)
        with self.assertRaisesRegex(ple.MetadataError, "integration changed"):
            gate.assess(*fixture(), PATCH, DOCKERFILE.replace("vllm-skinny-tp1:v1", "unknown"))

    def test_remote_pinned_never_fetches_mutable_main_or_safetensors(self):
        docs = fixture()
        calls = []
        def fake(url):
            calls.append(url)
            if "/revision/" in url:
                return docs[0]
            if url.endswith("/config.json"):
                return docs[1]
            if url.endswith("/model.safetensors.index.json"):
                return docs[2]
            raise AssertionError("unapproved URL: " + url)
        with patch.object(gate, "fetch_json", side_effect=fake):
            result = gate.assess(*gate.fetch_pinned(), PATCH, DOCKERFILE)
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(gate.REVISION in url for url in calls))
        self.assertTrue(all(not url.endswith(".safetensors") for url in calls))
        self.assertEqual(result["verdict"], "SOURCE_ONLY_LOADER_UNQUALIFIED")

    def test_revision_api_disagreement_prevents_config_fetch(self):
        docs = fixture()
        docs[0]["sha"] = "0" * 40
        with patch.object(gate, "fetch_json", return_value=docs[0]) as get:
            with self.assertRaisesRegex(ple.MetadataError, "SHA mismatch"):
                gate.fetch_pinned()
        self.assertEqual(get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
