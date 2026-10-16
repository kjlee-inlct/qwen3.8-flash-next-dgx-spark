#!/usr/bin/env python3
"""Revision-pinned, JSON-only Hugging Face checkpoint inventory.

Never downloads weights, reads tensor payloads, starts GPU processes or changes
host state. A complete metadata inventory does not qualify a serving backend.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

REPO = "catplusplus/Qwen3.8-Flash-Next-uncensored-NVFP4-mixed"
REVISION = "3251fd8afbd08f76368a9bfa71132d9aef364813"
SHA = re.compile(r"^[a-f0-9]{40}$")
MAX_JSON = 128 * 1024 * 1024
GIB = 1024 ** 3


class InventoryError(ValueError):
    """Invalid or incomplete inventory evidence."""


def _object(raw: bytes, context: str) -> Any:
    if len(raw) > MAX_JSON:
        raise InventoryError(f"{context}: JSON exceeds 128 MiB limit")
    try:
        return json.loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise InventoryError(f"{context}: invalid JSON: {exc}") from exc


def _get_json(url: str) -> tuple[Any, str | None]:
    if not url.startswith("https://huggingface.co/"):
        raise InventoryError("refusing non-Hugging Face pagination URL")
    req = urllib.request.Request(url, headers={"User-Agent": "qwen38-spark-catplusplus-metadata/1"})
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read(MAX_JSON + 1)
        links = response.headers.get("Link", "")
    next_url = None
    for candidate, relation in re.findall(r'<([^>]+)>;\s*rel="([^"]+)"', links):
        if relation == "next":
            next_url = candidate
            break
    return _object(data, url), next_url


def remote_snapshot() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any] | None]:
    if not SHA.fullmatch(REVISION):
        raise InventoryError("source revision is not immutable SHA")
    base = f"https://huggingface.co/{REPO}/resolve/{REVISION}"
    api, _ = _get_json(f"https://huggingface.co/api/models/{REPO}/revision/{REVISION}?blobs=true")
    if not isinstance(api, dict) or api.get("sha") != REVISION:
        raise InventoryError("Hub revision API did not confirm requested commit")
    url: str | None = f"https://huggingface.co/api/models/{REPO}/tree/{REVISION}?recursive=true&expand=true"
    tree: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    while url is not None:
        if url in seen_urls or len(seen_urls) >= 100:
            raise InventoryError("tree pagination repeated or exceeded 100 pages")
        seen_urls.add(url)
        page, url = _get_json(url)
        if not isinstance(page, list):
            raise InventoryError("Hub tree page is not an array")
        if not all(isinstance(x, dict) for x in page):
            raise InventoryError("Hub tree contains non-object entries")
        tree.extend(page)
    file_names = {x.get("path") for x in tree if x.get("type") == "file"}
    if "config.json" not in file_names:
        raise InventoryError("missing config.json in tree")
    config, _ = _get_json(f"{base}/config.json")
    index = None
    if "model.safetensors.index.json" in file_names:
        index, _ = _get_json(f"{base}/model.safetensors.index.json")
    return api, tree, config, index


def offline_snapshot(directory: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any], dict[str, Any] | None]:
    def read(name: str) -> Any:
        path = directory / name
        try:
            raw = path.read_bytes()
        except OSError as exc:
            raise InventoryError(f"cannot read {path}: {exc}") from exc
        return _object(raw, str(path))
    api, tree, config = read("api.json"), read("tree.json"), read("config.json")
    index = read("index.json") if (directory / "index.json").is_file() else None
    return api, tree, config, index


def _size(record: dict[str, Any]) -> int | None:
    size = record.get("size")
    lfs = record.get("lfs")
    lfs_size = lfs.get("size") if isinstance(lfs, dict) else None
    numbers = [x for x in (size, lfs_size) if isinstance(x, int) and not isinstance(x, bool) and x >= 0]
    if len(numbers) == 2 and numbers[0] != numbers[1]:
        raise InventoryError(f"conflicting tree/LFS sizes: {record.get('path')}")
    return numbers[0] if numbers else None


def validate(
    api: dict[str, Any], tree: list[dict[str, Any]],
    config: dict[str, Any], index: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(api, dict) or api.get("sha") != REVISION or api.get("id") not in (None, REPO):
        raise InventoryError("API SHA/repository identity mismatch")
    if not isinstance(tree, list) or not tree:
        raise InventoryError("empty/invalid Hub tree")
    if not isinstance(config, dict):
        raise InventoryError("config is not a JSON object")
    files: dict[str, dict[str, Any]] = {}
    for entry in tree:
        if not isinstance(entry, dict):
            raise InventoryError("tree item is not an object")
        if entry.get("type") != "file":
            continue
        name = entry.get("path")
        if not isinstance(name, str) or not name or name.startswith("/") or "\\" in name or any(p in ("", "..", ".") for p in name.split("/")):
            raise InventoryError(f"invalid file path in tree: {name!r}")
        if name in files:
            raise InventoryError(f"duplicate file in paginated tree: {name}")
        files[name] = entry
    if not files or "config.json" not in files:
        raise InventoryError("tree has no files or config")
    if (index is None) != ("model.safetensors.index.json" not in files):
        raise InventoryError("index.json input does not match tree index presence")

    file_sizes = {name: _size(item) for name, item in files.items()}
    unknown = sorted(n for n, size in file_sizes.items() if size is None)
    weights = sorted(n for n in files if n.endswith(".safetensors"))
    root_weights = [n for n in weights if "/" not in n]
    extras = [n for n in files if n.startswith("extra/")]
    # The old remote inspector sums only siblings[].size. Xet/LFS blobs can
    # have a missing size here while the revision-pinned expanded tree knows it.
    siblings = api.get("siblings")
    if not isinstance(siblings, list):
        raise InventoryError("revision API siblings are missing or invalid")
    legacy: dict[str, int | None] = {}
    for entry in siblings:
        if not isinstance(entry, dict):
            raise InventoryError("revision API contains non-object sibling")
        name = entry.get("rfilename")
        if not isinstance(name, str) or not name or name in legacy:
            raise InventoryError("revision API contains invalid/duplicate sibling filename")
        raw_size = entry.get("size")
        if raw_size is not None and (
            not isinstance(raw_size, int) or isinstance(raw_size, bool) or raw_size < 0
        ):
            raise InventoryError(f"invalid sibling size: {name}")
        legacy[name] = raw_size
    api_only_names = sorted(set(legacy) - set(files))
    if api_only_names:
        raise InventoryError("revision API siblings absent from full tree: " + ", ".join(api_only_names[:10]))
    mismatched = sorted(
        name for name, size in legacy.items()
        if size is not None and file_sizes[name] is not None and size != file_sizes[name]
    )
    if mismatched:
        raise InventoryError("revision API and tree report different file sizes: " + ", ".join(mismatched[:10]))
    legacy_known = sum(size for size in legacy.values() if size is not None)
    missing_legacy_names = sorted(name for name, size in legacy.items() if size is None)
    tree_only_names = sorted(set(files) - set(legacy))
    missing_legacy_bytes = sum(file_sizes[name] or 0 for name in missing_legacy_names)
    tree_only_bytes = sum(file_sizes[name] or 0 for name in tree_only_names)
    reconciliation_complete = all(
        file_sizes[name] is not None for name in missing_legacy_names + tree_only_names
    )
    # The tree's byte sum must partition cleanly into known legacy,
    # missing-size legacy entries and files omitted from legacy siblings.
    if not unknown and legacy_known + missing_legacy_bytes + tree_only_bytes != sum(file_sizes.values()):
        raise InventoryError("legacy/tree byte reconciliation does not balance")
    weight_map: dict[str, str] | None = None
    index_files: list[str] | None = None
    if index is not None:
        if not isinstance(index, dict) or not isinstance(index.get("weight_map"), dict) or not index["weight_map"]:
            raise InventoryError("index weight_map is invalid")
        weight_map = index["weight_map"]
        for key, name in weight_map.items():
            if not isinstance(key, str) or not isinstance(name, str) or name not in files or not name.endswith(".safetensors"):
                raise InventoryError(f"index tensor references missing/invalid weight file: {key}: {name}")
        index_files = sorted(set(weight_map.values()))
    quant = config.get("quantization_config")
    quant = quant if isinstance(quant, dict) else {}
    layers = quant.get("quantized_layers")
    layers = layers if isinstance(layers, dict) else {}
    algorithms = dict(sorted(Counter(
        value.get("quant_algo", "UNSPECIFIED")
        for value in layers.values() if isinstance(value, dict)
    ).items()))
    size_complete = not unknown
    root_size_complete = all(file_sizes[n] is not None for n in root_weights)
    all_total = sum(size or 0 for size in file_sizes.values())
    root_total = sum(file_sizes[n] or 0 for n in root_weights)
    required_total = (sum(file_sizes[n] or 0 for n in index_files) if index_files is not None else None)
    all_required_sized = index_files is not None and all(file_sizes[n] is not None for n in index_files)
    return {
        "checkpoint": REPO, "immutable_revision": REVISION,
        "verdict": "TREE_METADATA_COMPLETE" if size_complete else "TREE_SIZE_INCOMPLETE",
        "all_repository_bytes": all_total if size_complete else None,
        "all_repository_gib": round(all_total / GIB, 4) if size_complete else None,
        "root_safetensors_bytes": root_total if root_size_complete else None,
        "root_safetensors_gib": round(root_total / GIB, 4) if root_size_complete else None,
        "index_referenced_weight_bytes": required_total if all_required_sized else None,
        "index_file_count": len(index_files) if index_files is not None else None,
        "index_tensor_keys": len(weight_map) if weight_map is not None else None,
        "unindexed_root_safetensors": sorted(set(root_weights) - set(index_files or [])) if index_files is not None else None,
        "legacy_siblings_known_bytes": legacy_known,
        "legacy_siblings_unknown_size_entries": len(missing_legacy_names),
        "legacy_siblings_missing_size_paths": missing_legacy_names,
        "legacy_missing_size_recovered_tree_bytes": missing_legacy_bytes if reconciliation_complete else None,
        "tree_only_files_absent_from_legacy_siblings": tree_only_names,
        "tree_only_bytes": tree_only_bytes if reconciliation_complete else None,
        "legacy_tree_reconciliation_complete": size_complete and reconciliation_complete,
        "repository_file_count": len(files),
        "safetensors_file_count": len(weights),
        "root_safetensors_file_count": len(root_weights),
        "extra_file_count": len(extras),
        "unknown_size_files": unknown,
        "config": {
            "architectures": config.get("architectures"),
            "model_type": config.get("model_type"),
            "quant_method": quant.get("quant_method"),
            "quant_algo": quant.get("quant_algo"),
            "quantized_layer_algorithms": algorithms,
            "qkvz_alias_count": sum(k.endswith(".in_proj_qkvz") for k in layers),
            "ple_embedding_dtype": (config.get("text_config") or {}).get("ple_embedding_dtype"),
            "auto_map": config.get("auto_map"),
        },
        "file_inventory": [
            {"path": name, "bytes": file_sizes[name],
             "lfs_sha256": (files[name].get("lfs") or {}).get("sha256") if isinstance(files[name].get("lfs"), dict) else None,
             "xet_hash": files[name].get("xetHash")}
            for name in sorted(files)
        ],
        "not_verified": [
            "actual safetensors tensor dtype/shape/content",
            "whether absent index implies an alternative runtime file manifest",
            "which unindexed files are strictly required for inference",
            "loader support for mixed ModelOpt MXFP8/NVFP4 and FP8 PLE on GB10 TP=1",
            "peak host memory and functional GPU readiness",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline-dir", type=Path, help="read api.json, tree.json, config.json, optional index.json fixture")
    parser.add_argument("--json", action="store_true", help="print full file-by-file inventory")
    args = parser.parse_args()
    try:
        docs = offline_snapshot(args.offline_dir) if args.offline_dir else remote_snapshot()
        result = validate(*docs)
    except (InventoryError, OSError, urllib.error.URLError, TimeoutError) as exc:
        print(f"CATPLUSPLUS_METADATA_FAIL: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        for key in ("immutable_revision", "verdict", "repository_file_count", "safetensors_file_count",
                    "root_safetensors_gib", "all_repository_gib", "legacy_siblings_known_bytes",
                    "legacy_siblings_unknown_size_entries", "legacy_missing_size_recovered_tree_bytes",
                    "tree_only_bytes", "legacy_tree_reconciliation_complete", "index_file_count"):
            print(f"{key}={result[key]}")
        print("GPU_RUN=NOT_PERFORMED")
    return 0 if result["verdict"] == "TREE_METADATA_COMPLETE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
