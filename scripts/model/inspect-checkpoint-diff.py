#!/usr/bin/env python3
"""Inventory structural differences between two local Qwen3.8 checkpoints.

This intentionally compares configuration, tensor key presence, dtype, shape, and
quantization target membership without loading full tensor payloads into RAM.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"ERROR: JSON root is not an object: {path}")
    return data


def weight_map(root: Path) -> dict[str, str]:
    data = load_json(root / "model.safetensors.index.json")
    result = data.get("weight_map")
    if not isinstance(result, dict):
        raise SystemExit(f"ERROR: invalid weight_map: {root}")
    return {str(k): str(v) for k, v in result.items()}


def group0_targets(root: Path) -> set[str]:
    config = load_json(root / "config.json")
    try:
        targets = config["quantization_config"]["config_groups"]["group_0"]["targets"]
    except (KeyError, TypeError):
        return set()
    return {str(x) for x in targets} if isinstance(targets, list) else set()


def category(key: str) -> str:
    if key.startswith("mtp."):
        return "mtp"
    if ".experts." in key or ".shared_expert." in key:
        return "expert"
    if "embed_tokens" in key or "lm_head" in key:
        return "embedding_or_head"
    if ".norm" in key or key.endswith("_norm.weight"):
        return "norm"
    if ".self_attn." in key:
        return "self_attn"
    if ".linear_attn." in key:
        return "linear_attn"
    if ".mlp." in key:
        return "mlp_other"
    if "ple" in key.lower() or "ngram" in key.lower():
        return "ple"
    return "other"


def tensor_meta(root: Path, mapping: dict[str, str]) -> dict[str, tuple[str, tuple[int, ...]]]:
    try:
        from safetensors import safe_open
    except ImportError as exc:
        raise SystemExit("ERROR: safetensors is required for tensor metadata inspection") from exc

    by_shard: dict[str, list[str]] = defaultdict(list)
    for key, shard in mapping.items():
        by_shard[shard].append(key)

    result: dict[str, tuple[str, tuple[int, ...]]] = {}
    for shard, keys in sorted(by_shard.items()):
        path = root / shard
        with safe_open(path, framework="pt", device="cpu") as handle:
            for key in keys:
                sl = handle.get_slice(key)
                result[key] = (str(sl.get_dtype()), tuple(sl.get_shape()))
    return result


def expert_suffix(key: str) -> str | None:
    marker = ".mlp.experts."
    if marker not in key:
        return None
    tail = key.split(marker, 1)[1]
    parts = tail.split(".", 1)
    return parts[1] if len(parts) == 2 else None


def expert_suffix_counts(keys: set[str]) -> dict[str, int]:
    counts = Counter(suffix for key in keys if (suffix := expert_suffix(key)))
    return dict(sorted(counts.items()))


def summarize_quantization(root: Path) -> dict[str, Any]:
    config = load_json(root / "config.json")
    quant = config.get("quantization_config")
    if not isinstance(quant, dict):
        return {"present": False}

    result: dict[str, Any] = {"present": True}
    for key, value in quant.items():
        if key != "config_groups":
            result[key] = value

    groups = quant.get("config_groups")
    group_summary: dict[str, Any] = {}
    if isinstance(groups, dict):
        for name, group in sorted(groups.items()):
            if not isinstance(group, dict):
                group_summary[str(name)] = group
                continue
            item = {k: v for k, v in group.items() if k != "targets"}
            targets = group.get("targets")
            if isinstance(targets, list):
                item["target_count"] = len(targets)
                item["target_examples"] = [str(x) for x in targets[:10]]
            group_summary[str(name)] = item
    result["config_groups"] = group_summary
    return result


def summarize(label: str, keys: set[str]) -> dict[str, Any]:
    cats = Counter(category(key) for key in keys)
    result = {
        "label": label,
        "count": len(keys),
        "categories": dict(sorted(cats.items())),
    }
    suffixes = expert_suffix_counts(keys)
    if suffixes:
        result["expert_suffixes"] = suffixes
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--json-output", type=Path)
    args = ap.parse_args()

    base_map = weight_map(args.base)
    cand_map = weight_map(args.candidate)
    base_keys = set(base_map)
    cand_keys = set(cand_map)
    common = base_keys & cand_keys

    base_meta = tensor_meta(args.base, {k: base_map[k] for k in common})
    cand_meta = tensor_meta(args.candidate, {k: cand_map[k] for k in common})

    meta_diff = {
        key
        for key in common
        if base_meta[key] != cand_meta[key]
    }
    base_g0 = group0_targets(args.base)
    cand_g0 = group0_targets(args.candidate)

    report = {
        "base": str(args.base),
        "candidate": str(args.candidate),
        "base_tensor_count": len(base_keys),
        "candidate_tensor_count": len(cand_keys),
        "common_tensor_count": len(common),
        "only_base": summarize("only_base", base_keys - cand_keys),
        "only_candidate": summarize("only_candidate", cand_keys - base_keys),
        "metadata_differences": summarize("metadata_differences", meta_diff),
        "base_group0_targets": len(base_g0),
        "candidate_group0_targets": len(cand_g0),
        "group0_only_base": len(base_g0 - cand_g0),
        "group0_only_candidate": len(cand_g0 - base_g0),
        "base_quantization": summarize_quantization(args.base),
        "candidate_quantization": summarize_quantization(args.candidate),
        "metadata_difference_examples": [
            {
                "key": key,
                "category": category(key),
                "base": {"dtype": base_meta[key][0], "shape": base_meta[key][1]},
                "candidate": {"dtype": cand_meta[key][0], "shape": cand_meta[key][1]},
            }
            for key in sorted(meta_diff)[:100]
        ],
        "only_base_examples": sorted(base_keys - cand_keys)[:100],
        "only_candidate_examples": sorted(cand_keys - base_keys)[:100],
    }

    text = json.dumps(report, indent=2)
    print(text)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
