#!/usr/bin/env python3
"""Check whether OrcaRouter routed experts can be normalized to ModelOpt NVFP4.

This is a read-only H4 feasibility gate. It verifies the on-disk tensor schema,
dtype/shape compatibility, reciprocal global-scale mapping, and whether a coherent
ModelOpt-style expert checkpoint can be built without dequantizing/requantizing.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


class FeasibilityError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise FeasibilityError(f"JSON root is not an object: {path}")
    return data


def weight_map(root: Path) -> dict[str, str]:
    data = load_json(root / "model.safetensors.index.json")
    mapping = data.get("weight_map")
    if not isinstance(mapping, dict):
        raise FeasibilityError(f"invalid weight map: {root}")
    return {str(k): str(v) for k, v in mapping.items()}


def main_expert_modules(mapping: dict[str, str]) -> set[str]:
    modules: set[str] = set()
    prefix = "model.language_model.layers."
    marker = ".mlp.experts."
    suffixes = (
        ".weight_packed",
        ".weight",
        ".weight_scale",
        ".weight_global_scale",
        ".weight_scale_2",
        ".input_scale",
        ".input_global_scale",
    )
    for key in mapping:
        if not key.startswith(prefix) or marker not in key:
            continue
        for suffix in suffixes:
            if key.endswith(suffix):
                modules.add(key[: -len(suffix)])
                break
    return modules


def tensor_meta(root: Path, mapping: dict[str, str], keys: set[str]) -> dict[str, tuple[str, tuple[int, ...]]]:
    from safetensors import safe_open

    by_shard: dict[str, list[str]] = defaultdict(list)
    for key in keys:
        if key in mapping:
            by_shard[mapping[key]].append(key)

    out: dict[str, tuple[str, tuple[int, ...]]] = {}
    for shard, shard_keys in sorted(by_shard.items()):
        with safe_open(root / shard, framework="pt", device="cpu") as handle:
            for key in shard_keys:
                sl = handle.get_slice(key)
                out[key] = (str(sl.get_dtype()), tuple(sl.get_shape()))
    return out


def scalar_values(root: Path, mapping: dict[str, str], keys: set[str]) -> dict[str, float]:
    from safetensors import safe_open

    by_shard: dict[str, list[str]] = defaultdict(list)
    for key in keys:
        if key in mapping:
            by_shard[mapping[key]].append(key)

    out: dict[str, float] = {}
    for shard, shard_keys in sorted(by_shard.items()):
        with safe_open(root / shard, framework="pt", device="cpu") as handle:
            for key in shard_keys:
                tensor = handle.get_tensor(key)
                if tensor.numel() != 1:
                    raise FeasibilityError(f"expected scalar tensor: {key}: shape={tuple(tensor.shape)}")
                out[key] = float(tensor.item())
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--overlay", type=Path, required=True)
    ap.add_argument("--sample-modules", type=int, default=32)
    ap.add_argument("--json-output", type=Path)
    args = ap.parse_args()

    base_map = weight_map(args.base)
    overlay_map = weight_map(args.overlay)
    base_modules = main_expert_modules(base_map)
    overlay_modules = main_expert_modules(overlay_map)
    common = sorted(base_modules & overlay_modules)

    if not common:
        raise FeasibilityError("no common main-model expert modules")
    if base_modules != overlay_modules:
        raise FeasibilityError(
            f"expert module sets differ: base={len(base_modules)} overlay={len(overlay_modules)} common={len(common)}"
        )

    required_base = {
        module + suffix
        for module in common
        for suffix in (".weight_packed", ".weight_scale", ".weight_global_scale")
    }
    required_overlay = {
        module + suffix
        for module in common
        for suffix in (".weight", ".weight_scale", ".weight_scale_2", ".input_scale")
    }
    missing_base = sorted(key for key in required_base if key not in base_map)
    missing_overlay = sorted(key for key in required_overlay if key not in overlay_map)
    if missing_base:
        raise FeasibilityError(f"base expert schema incomplete: {missing_base[:10]}")
    if missing_overlay:
        raise FeasibilityError(f"overlay expert schema incomplete: {missing_overlay[:10]}")

    sample = common[: max(1, min(args.sample_modules, len(common)))]
    meta_keys_base = {
        module + suffix
        for module in sample
        for suffix in (".weight_packed", ".weight_scale", ".weight_global_scale")
    }
    meta_keys_overlay = {
        module + suffix
        for module in sample
        for suffix in (".weight", ".weight_scale", ".weight_scale_2", ".input_scale")
    }
    base_meta = tensor_meta(args.base, base_map, meta_keys_base)
    overlay_meta = tensor_meta(args.overlay, overlay_map, meta_keys_overlay)

    shape_mismatches: list[dict[str, Any]] = []
    dtype_counts: Counter[str] = Counter()
    for module in sample:
        bp = base_meta[module + ".weight_packed"]
        bs = base_meta[module + ".weight_scale"]
        op = overlay_meta[module + ".weight"]
        os = overlay_meta[module + ".weight_scale"]
        dtype_counts[f"base_weight:{bp[0]}"] += 1
        dtype_counts[f"overlay_weight:{op[0]}"] += 1
        dtype_counts[f"base_scale:{bs[0]}"] += 1
        dtype_counts[f"overlay_scale:{os[0]}"] += 1
        if bp[1] != op[1] or bs[1] != os[1]:
            shape_mismatches.append({
                "module": module,
                "base_weight": bp,
                "overlay_weight": op,
                "base_scale": bs,
                "overlay_scale": os,
            })

    base_globals = scalar_values(
        args.base, base_map, {module + ".weight_global_scale" for module in sample}
    )
    overlay_globals = scalar_values(
        args.overlay, overlay_map, {module + ".weight_scale_2" for module in sample}
    )

    reciprocal_examples: list[dict[str, Any]] = []
    finite_nonzero = 0
    for module in sample:
        divisor = base_globals[module + ".weight_global_scale"]
        multiplier = 0.0 if divisor == 0.0 else 1.0 / divisor
        if divisor != 0.0:
            finite_nonzero += 1
        reciprocal_examples.append({
            "module": module,
            "orca_weight_global_scale": divisor,
            "orca_as_modelopt_weight_scale_2": multiplier,
            "mazinb_weight_scale_2": overlay_globals[module + ".weight_scale_2"],
        })

    gate_modules = sorted(module for module in common if module.endswith(".gate_proj"))
    pair_modules = [(module, module[:-len("gate_proj")] + "up_proj") for module in gate_modules]
    pair_base_keys = {
        item + ".weight_global_scale"
        for pair in pair_modules
        for item in pair
    }
    pair_overlay_keys = {
        item + ".weight_scale_2"
        for pair in pair_modules
        for item in pair
    }
    pair_base_values = scalar_values(args.base, base_map, pair_base_keys)
    pair_overlay_values = scalar_values(args.overlay, overlay_map, pair_overlay_keys)
    base_pair_mismatches = 0
    overlay_pair_mismatches = 0
    for gate, up in pair_modules:
        if pair_base_values[gate + ".weight_global_scale"] != pair_base_values[up + ".weight_global_scale"]:
            base_pair_mismatches += 1
        if pair_overlay_values[gate + ".weight_scale_2"] != pair_overlay_values[up + ".weight_scale_2"]:
            overlay_pair_mismatches += 1

    base_input_global = sum(
        1 for module in common if module + ".input_global_scale" in base_map
    )
    overlay_input = sum(
        1 for module in common if module + ".input_scale" in overlay_map
    )

    report = {
        "schema_version": 1,
        "status": "pass"
        if (
            not shape_mismatches
            and finite_nonzero == len(sample)
            and base_pair_mismatches == 0
            and overlay_pair_mismatches == 0
        )
        else "fail",
        "expert_modules": len(common),
        "sample_modules": len(sample),
        "base_schema": {
            "weight": "weight_packed",
            "group_scale": "weight_scale",
            "global_scale": "weight_global_scale",
            "input_global_scale_modules": base_input_global,
        },
        "overlay_schema": {
            "weight": "weight",
            "group_scale": "weight_scale",
            "global_scale": "weight_scale_2",
            "input_scale_modules": overlay_input,
        },
        "dtype_counts": dict(sorted(dtype_counts.items())),
        "shape_mismatches": shape_mismatches,
        "reciprocal_mapping": "modelopt.weight_scale_2 = 1 / compressed_tensors.weight_global_scale",
        "reciprocal_examples": reciprocal_examples,
        "gate_up_pairs": len(pair_modules),
        "base_gate_up_global_scale_mismatches": base_pair_mismatches,
        "overlay_gate_up_global_scale_mismatches": overlay_pair_mismatches,
        "h4_candidate": (
            "Normalize selected OrcaRouter experts into ModelOpt names without "
            "dequantizing: weight_packed->weight, preserve weight_scale, reciprocal "
            "weight_global_scale->weight_scale_2; retain mazinb input_scale unless "
            "an OrcaRouter input-global-scale mapping is present."
        ),
    }

    text = json.dumps(report, indent=2)
    print(text)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(text + "\n", encoding="utf-8")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FeasibilityError as exc:
        print(f"ERROR: {exc}")
        raise SystemExit(1)
