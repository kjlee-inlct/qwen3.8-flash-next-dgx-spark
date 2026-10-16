"""Offline/synthetic-only catplusplus Hub inventory tests; never fetch model weights."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "scripts/model/inspect_catplusplus_metadata.py"
spec = importlib.util.spec_from_file_location("catplusplus_metadata", SOURCE)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def snapshot(with_index=True):
    api = {
        "id": mod.REPO, "sha": mod.REVISION,
        "siblings": [
            {"rfilename": "config.json", "size": 100},
            {"rfilename": "experts-layer00.safetensors", "size": 120},
            {"rfilename": "model-00001.safetensors"},  # old API left size null
        ],
    }
    tree = [
        {"type": "file", "path": "config.json", "size": 100},
        {"type": "file", "path": "experts-layer00.safetensors",
         "size": 120, "lfs": {"size": 120, "oid": "sha256:abc"}},
        {"type": "file", "path": "model-00001.safetensors",
         "lfs": {"size": 330, "oid": "sha256:def"}},
        {"type": "file", "path": "extra/inference/launcher.sh", "size": 20},
    ]
    config = {
        "architectures": ["Qwen4ExpForConditionalGeneration"],
        "model_type": "qwen4_exp",
        "text_config": {"ple_embedding_dtype": "float8_e4m3fn"},
        "quantization_config": {
            "quant_method": "modelopt_mixed",
            "quant_algo": "MIXED_PRECISION",
            "quantized_layers": {
                "model.layers.2.linear_attn.in_proj_qkvz": {"quant_algo": "MXFP8"},
                "model.layers.2.mlp.experts": {"quant_algo": "NVFP4"},
            },
        },
    }
    index = {"weight_map": {
        "model.layers.2.mlp.experts": "experts-layer00.safetensors",
        "model.layers.2.linear_attn.in_proj_qkv": "model-00001.safetensors",
    }} if with_index else None
    if with_index:
        tree.append({"type": "file", "path": "model.safetensors.index.json", "size": 50})
    return api, tree, config, index


class InventoryTests(unittest.TestCase):
    def test_lfs_fallback_reconciles_legacy_understatement(self):
        result = mod.validate(*snapshot())
        self.assertEqual(result["verdict"], "TREE_METADATA_COMPLETE")
        self.assertEqual(result["legacy_siblings_known_bytes"], 220)
        self.assertEqual(result["legacy_siblings_unknown_size_entries"], 1)
        self.assertEqual(result["all_repository_bytes"], 620)
        self.assertEqual(result["root_safetensors_bytes"], 450)
        self.assertEqual(result["index_referenced_weight_bytes"], 450)
        self.assertEqual(result["index_tensor_keys"], 2)
        self.assertEqual(result["config"]["qkvz_alias_count"], 1)
        self.assertEqual(result["config"]["quantized_layer_algorithms"], {"MXFP8": 1, "NVFP4": 1})
        self.assertIn("actual safetensors tensor", " ".join(result["not_verified"]))

    def test_absent_index_does_not_imply_safe_selective_download(self):
        result = mod.validate(*snapshot(with_index=False))
        self.assertIsNone(result["index_referenced_weight_bytes"])
        self.assertIsNone(result["index_file_count"])
        self.assertEqual(result["root_safetensors_bytes"], 450)

    def test_missing_tree_size_is_not_reported_as_zero(self):
        docs = snapshot()
        docs[1][2].pop("lfs")
        result = mod.validate(*docs)
        self.assertEqual(result["verdict"], "TREE_SIZE_INCOMPLETE")
        self.assertIsNone(result["root_safetensors_bytes"])
        self.assertEqual(result["unknown_size_files"], ["model-00001.safetensors"])

    def test_missing_referenced_safetensors_fails(self):
        docs = snapshot()
        docs[3]["weight_map"]["invalid"] = "missing.safetensors"
        with self.assertRaisesRegex(mod.InventoryError, "missing/invalid"):
            mod.validate(*docs)

    def test_conflicting_tree_and_lfs_sizes_fail(self):
        docs = snapshot()
        docs[1][1]["lfs"]["size"] = 121
        with self.assertRaisesRegex(mod.InventoryError, "conflicting"):
            mod.validate(*docs)

    def test_unpinned_api_identity_fails(self):
        docs = snapshot()
        docs[0]["sha"] = "main"
        with self.assertRaisesRegex(mod.InventoryError, "identity"):
            mod.validate(*docs)

    def test_duplicate_pages_fail_instead_of_double_count(self):
        docs = snapshot()
        docs[1].append(dict(docs[1][0]))
        with self.assertRaisesRegex(mod.InventoryError, "duplicate"):
            mod.validate(*docs)

    def test_index_inconsistency_fails(self):
        docs = snapshot()
        docs[1] = [x for x in docs[1] if x["path"] != "model.safetensors.index.json"]
        with self.assertRaisesRegex(mod.InventoryError, "index.json"):
            mod.validate(*docs)

    def test_offline_file_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            docs = snapshot()
            for name, data in zip(("api.json", "tree.json", "config.json", "index.json"), docs):
                (Path(directory) / name).write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(mod.validate(*mod.offline_snapshot(Path(directory)))["index_file_count"], 2)

    def test_network_pagination_and_no_weight_fetch(self):
        api, tree, config, index = snapshot()
        page1, page2 = tree[:2], tree[2:]
        requests = []
        def get_json(url):
            requests.append(url)
            if "/api/models/" in url and "/revision/" in url:
                return api, None
            if "/api/models/" in url and "/tree/" in url:
                return page1, "https://huggingface.co/api/models/next-page"
            if url.endswith("/api/models/next-page"):
                return page2, None
            if url.endswith("/config.json"):
                return config, None
            if url.endswith("/model.safetensors.index.json"):
                return index, None
            raise AssertionError(f"unexpected endpoint: {url}")
        with patch.object(mod, "_get_json", side_effect=get_json):
            result = mod.validate(*mod.remote_snapshot())
        self.assertEqual(result["all_repository_bytes"], 620)
        self.assertEqual(len(requests), 5)
        self.assertTrue(all(".safetensors" not in url or url.endswith(".index.json") for url in requests))


if __name__ == "__main__":
    unittest.main()
