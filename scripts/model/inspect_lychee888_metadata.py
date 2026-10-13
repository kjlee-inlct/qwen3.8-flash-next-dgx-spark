#!/usr/bin/env python3
"""Read-only L0 index probe for the planned lychee888 FP8-PLE checkpoint.

Downloads only Hub JSON metadata, config.json, and model.safetensors.index.json;
never retrieves a safetensors payload or runs Docker/GPU code.

A passing result proves index/file-name structure at a pinned HF revision.
It does NOT verify safetensors header dtype, file checksums, loader compatibility,
tensor payload or TP=1 single DGX Spark host-stability.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO = "lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHARD_KEY_RE = re.compile(r"(?:^|\.)ngram_embedding\.shard_(\d+)\.weight$")
PLE_FILES = tuple(f"model-plefp8-{i:05d}.safetensors" for i in range(10))
OLD_BF16_PLE_FILE = "model-00002-of-00017.safetensors"
MAX_JSON_BYTES = 128 * 1024 * 1024


class MetadataError(ValueError):
    """Fail-closed metadata/index integrity problem."""


def fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "qwen38-spark-lychee888-L0/1"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read(MAX_JSON_BYTES + 1)
    if len(payload) > MAX_JSON_BYTES:
        raise MetadataError("Hub JSON metadata exceeds 128 MiB bound")
    return load_object(payload, url)


def load_object(raw: bytes, source: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MetadataError(f"invalid JSON in {source}: {exc}") from exc
    if not isinstance(value, dict):
        raise MetadataError(f"{source} must contain a JSON object")
    return value


def load_offline(directory: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Fixture inputs are metadata documents, NOT actual checkpoint tensors."""
    paths = (directory / "api.json", directory / "config.json", directory / "index.json")
    result = []
    for path in paths:
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise MetadataError(f"cannot read fixture {path}: {exc}") from exc
        if len(content) > MAX_JSON_BYTES:
            raise MetadataError(f"fixture JSON exceeds bound: {path}")
        result.append(load_object(content, str(path)))
    return result[0], result[1], result[2]


def load_remote() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Pin a discovered SHA before fetching revision-bound JSON files."""
    url = f"https://huggingface.co/api/models/{REPO}"
    latest = fetch_json(url)
    revision = latest.get("sha")
    if not isinstance(revision, str) or not SHA_RE.fullmatch(revision):
        raise MetadataError("Hub did not return an immutable 40-hex revision")
    metadata = fetch_json(
        f"https://huggingface.co/api/models/{REPO}/revision/{revision}?blobs=true"
    )
    if metadata.get("sha") != revision:
        raise MetadataError("revision-scoped API SHA does not match selected SHA")
    base = f"https://huggingface.co/{REPO}/resolve/{revision}"
    config = fetch_json(f"{base}/config.json")
    index = fetch_json(f"{base}/model.safetensors.index.json")
    return metadata, config, index


def validate(
    metadata: dict[str, Any], config: dict[str, Any], index: dict[str, Any]
) -> dict[str, Any]:
    revision = metadata.get("sha")
    if not isinstance(revision, str) or not SHA_RE.fullmatch(revision):
        raise MetadataError("missing/invalid immutable source SHA")
    if metadata.get("id") not in (None, REPO):
        raise MetadataError("metadata repository identity mismatch")

    siblings = metadata.get("siblings")
    if not isinstance(siblings, list) or not siblings:
        raise MetadataError("Hub revision metadata has no file inventory")
    names = {item.get("rfilename") for item in siblings if isinstance(item, dict)}
    required_names = set(PLE_FILES) | {"config.json", "model.safetensors.index.json"}
    absent = sorted(required_names - names)
    if absent:
        raise MetadataError("Hub file inventory missing: " + ", ".join(absent))
    if OLD_BF16_PLE_FILE in names:
        raise MetadataError("unexpected unquantized BF16 PLE shard in source inventory")

    text = config.get("text_config")
    if not isinstance(text, dict) or text.get("ple_embedding_dtype") != "float8_e4m3fn":
        raise MetadataError("config.text_config.ple_embedding_dtype is not float8_e4m3fn")
    weight_map = index.get("weight_map")
    if not isinstance(weight_map, dict) or not weight_map:
        raise MetadataError("index has no weight_map")

    shard_keys: dict[int, str] = {}
    scale_keys: list[str] = []
    for key, file in weight_map.items():
        if not isinstance(key, str) or not isinstance(file, str):
            raise MetadataError("index weight_map must map strings to filenames")
        if file not in names:
            raise MetadataError(f"index references missing source file: {file}")
        if file == OLD_BF16_PLE_FILE:
            raise MetadataError("index references original BF16 PLE shard")
        match = SHARD_KEY_RE.search(key)
        if match:
            number = int(match.group(1))
            if number in shard_keys:
                raise MetadataError(f"duplicate PLE shard number {number}")
            if file not in PLE_FILES:
                raise MetadataError(f"PLE shard {number} is not mapped to FP8 PLE file")
            shard_keys[number] = file
        elif key.endswith("weight_scale") and ("ple." in key or "ple_embedding" in key):
            scale_keys.append(key)
            if file != PLE_FILES[-1]:
                raise MetadataError("global PLE scale is not in the last FP8 PLE file")

    if set(shard_keys) != set(range(128)):
        missing = sorted(set(range(128)) - set(shard_keys))
        extra = sorted(set(shard_keys) - set(range(128)))
        raise MetadataError(f"PLE index must contain exactly 128 numbered shards: missing={missing}, extra={extra}")
    if len(scale_keys) != 1:
        raise MetadataError(f"expected one global PLE weight_scale, found {len(scale_keys)}")
    used_ple = set(shard_keys.values()) | {weight_map[scale_keys[0]]}
    if used_ple != set(PLE_FILES):
        raise MetadataError("all ten FP8 PLE source files must be referenced")

    return {
        "checkpoint": REPO,
        "immutable_revision": revision,
        "index_tensor_keys": len(weight_map),
        "ple_weight_shards": 128,
        "ple_files": len(used_ple),
        "global_weight_scale_keys": 1,
        "config_ple_embedding_dtype": text["ple_embedding_dtype"],
        "verdict": "INDEX_STRUCTURE_PASS_METADATA_ONLY",
        "not_verified": [
            "actual safetensors header dtypes/shapes and BF16 scale dtype",
            "on-disk file hashes or downloaded weights",
            "single GB10 TP=1 FP8-PLE loader compatibility",
            "functional correctness and strict NVIDIA RM stability",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline-dir", type=Path,
        help="Read api.json/config.json/index.json from a local metadata-only fixture",
    )
    args = parser.parse_args()
    try:
        docs = load_offline(args.offline_dir) if args.offline_dir else load_remote()
        result = validate(*docs)
    except (MetadataError, OSError, urllib.error.URLError, TimeoutError) as exc:
        print(f"L0_METADATA_FAIL: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
