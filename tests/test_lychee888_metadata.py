"""Source-only lychee888 FP8 PLE index checker tests. No network or model download."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "scripts/model/inspect_lychee888_metadata.py"
spec = importlib.util.spec_from_file_location("lychee888_meta", SOURCE)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture() -> tuple[dict, dict, dict]:
    repo = mod.REPO
    files = list(mod.PLE_FILES) + [
        "config.json", "model.safetensors.index.json",
        "model-00003-of-00017.safetensors",
    ]
    metadata = {"id": repo, "sha": "a" * 40, "siblings": [{"rfilename": f} for f in files]}
    config = {"text_config": {"ple_embedding_dtype": "float8_e4m3fn"}}
    prefix = "model.language_model.ple.ple_embedding."
    weight_map = {
        f"{prefix}ngram_embedding.shard_{i}.weight": mod.PLE_FILES[i // 13]
        for i in range(128)
    }
    weight_map[prefix + "weight_scale"] = mod.PLE_FILES[-1]
    weight_map[prefix + "ngram_heads_offsets"] = "model-00003-of-00017.safetensors"
    weight_map[prefix + "ngram_heads_vocab_sizes"] = "model-00003-of-00017.safetensors"
    return metadata, config, {"weight_map": weight_map}


class Lychee888MetadataTests(unittest.TestCase):
    def test_complete_metadata_index_only_never_claims_runtime_pass(self) -> None:
        result = mod.validate(*fixture())
        self.assertEqual(result["verdict"], "INDEX_STRUCTURE_PASS_METADATA_ONLY")
        self.assertEqual(result["ple_weight_shards"], 128)
        self.assertEqual(result["ple_files"], 10)
        self.assertIn("strict NVIDIA RM", " ".join(result["not_verified"]))

    def test_missing_fp8_ple_file_fails(self) -> None:
        metadata, config, index = fixture()
        metadata["siblings"] = [
            s for s in metadata["siblings"] if s["rfilename"] != mod.PLE_FILES[9]
        ]
        with self.assertRaisesRegex(mod.MetadataError, "file inventory missing"):
            mod.validate(metadata, config, index)

    def test_bf16_ple_file_must_not_be_mixed(self) -> None:
        metadata, config, index = fixture()
        metadata["siblings"].append({"rfilename": mod.OLD_BF16_PLE_FILE})
        with self.assertRaisesRegex(mod.MetadataError, "unquantized BF16"):
            mod.validate(metadata, config, index)

    def test_wrong_config_dtype_fails(self) -> None:
        metadata, config, index = fixture()
        config["text_config"]["ple_embedding_dtype"] = "bfloat16"
        with self.assertRaisesRegex(mod.MetadataError, "float8_e4m3fn"):
            mod.validate(metadata, config, index)

    def test_missing_one_shard_fails(self) -> None:
        metadata, config, index = fixture()
        index["weight_map"].pop(
            "model.language_model.ple.ple_embedding.ngram_embedding.shard_127.weight"
        )
        with self.assertRaisesRegex(mod.MetadataError, "exactly 128"):
            mod.validate(metadata, config, index)

    def test_duplicate_scale_fails(self) -> None:
        metadata, config, index = fixture()
        index["weight_map"]["other.ple.ple_embedding.weight_scale"] = mod.PLE_FILES[-1]
        with self.assertRaisesRegex(mod.MetadataError, "one global"):
            mod.validate(metadata, config, index)

    def test_scale_in_wrong_file_fails(self) -> None:
        metadata, config, index = fixture()
        index["weight_map"]["model.language_model.ple.ple_embedding.weight_scale"] = mod.PLE_FILES[0]
        with self.assertRaisesRegex(mod.MetadataError, "last FP8"):
            mod.validate(metadata, config, index)

    def test_unpinned_revision_fails(self) -> None:
        metadata, config, index = fixture()
        metadata["sha"] = "main"
        with self.assertRaisesRegex(mod.MetadataError, "immutable source SHA"):
            mod.validate(metadata, config, index)

    def test_unknown_index_shard_file_fails(self) -> None:
        metadata, config, index = fixture()
        index["weight_map"]["model.language_model.ple.ple_embedding.ngram_embedding.shard_0.weight"] = "missing.safetensors"
        with self.assertRaisesRegex(mod.MetadataError, "missing source file"):
            mod.validate(metadata, config, index)

    def test_offline_triplet_reader_uses_json_only(self) -> None:
        metadata, config, index = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, value in (
                ("api.json", metadata),
                ("config.json", config),
                ("index.json", index),
            ):
                (root / name).write_text(json.dumps(value), encoding="utf-8")
            loaded = mod.load_offline(root)
            self.assertEqual(mod.validate(*loaded)["ple_files"], 10)


if __name__ == "__main__":
    unittest.main()
