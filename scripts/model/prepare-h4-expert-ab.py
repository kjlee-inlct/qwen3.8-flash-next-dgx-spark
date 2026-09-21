#!/usr/bin/env python3
"""Build a thin H4 expert A/B delta on top of the proven H3 checkpoint.

Variants:
- orca-down: convert every OrcaRouter routed-expert down_proj into ModelOpt names.
- orca-gate-up: convert every OrcaRouter routed-expert gate_proj+up_proj pair.

The H3 ModelOpt quantization config and mazinb input_scale tensors are retained.
Only weight, weight_scale, and reciprocal weight_scale_2 are replaced.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

H3_MOUNT = "/h3-model"
BASE_MOUNT = "/base-model"
RESERVE_BYTES = 10 * 1024**3
EXPECTED_MODULES = {"orca-down": 24576, "orca-gate-up": 49152}


class H4Error(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise H4Error(f"JSON root is not an object: {path}")
    return data


def weight_map(root: Path) -> dict[str, str]:
    data = load_json(root / "model.safetensors.index.json")
    mapping = data.get("weight_map")
    if not isinstance(mapping, dict):
        raise H4Error(f"invalid weight map: {root}")
    return {str(k): str(v) for k, v in mapping.items()}


def main_expert_modules(mapping: dict[str, str]) -> set[str]:
    modules: set[str] = set()
    prefix = "model.language_model.layers."
    for key in mapping:
        if not key.startswith(prefix) or ".mlp.experts." not in key:
            continue
        if key.endswith(".weight_packed"):
            modules.add(key[: -len(".weight_packed")])
    return modules


def selected_modules(mapping: dict[str, str], variant: str) -> list[str]:
    modules = main_expert_modules(mapping)
    if variant == "orca-down":
        selected = sorted(m for m in modules if m.endswith(".down_proj"))
    elif variant == "orca-gate-up":
        selected = sorted(
            m for m in modules if m.endswith(".gate_proj") or m.endswith(".up_proj")
        )
    else:
        raise H4Error(f"unsupported variant: {variant}")
    expected = EXPECTED_MODULES[variant]
    if len(selected) != expected:
        raise H4Error(f"{variant}: selected {len(selected)} modules, expected {expected}")
    return selected


def validate_h3(root: Path) -> dict[str, Any]:
    manifest = load_json(root / ".qwen38-hybrid-manifest.json")
    if (
        manifest.get("status") != "complete"
        or manifest.get("variant") != "quant-layout-mazinb-experts"
        or manifest.get("group0_bf16_weights") != 300
        or manifest.get("mtp_tensors_changed") != 0
    ):
        raise H4Error("H3 checkpoint manifest is incomplete or inconsistent")
    config = load_json(root / "config.json")
    quant = config.get("quantization_config")
    if not isinstance(quant, dict) or quant.get("quant_method") != "modelopt":
        raise H4Error("H3 checkpoint is not ModelOpt")
    return manifest


def validate_keys(base_map: dict[str, str], h3_map: dict[str, str], modules: list[str]) -> None:
    missing: list[str] = []
    for module in modules:
        for key in (
            module + ".weight_packed",
            module + ".weight_scale",
            module + ".weight_global_scale",
        ):
            if key not in base_map:
                missing.append("base:" + key)
        for key in (
            module + ".weight",
            module + ".weight_scale",
            module + ".weight_scale_2",
            module + ".input_scale",
        ):
            if key not in h3_map:
                missing.append("h3:" + key)
    if missing:
        raise H4Error("missing H4 tensor keys: " + ", ".join(missing[:10]))


def ensure_gate_up_pairs(base: Path, base_map: dict[str, str], modules: list[str]) -> None:
    if not any(m.endswith(".gate_proj") for m in modules):
        return
    from safetensors import safe_open

    keys = {
        module + ".weight_global_scale"
        for module in modules
        if module.endswith(".gate_proj") or module.endswith(".up_proj")
    }
    by_shard: dict[str, list[str]] = defaultdict(list)
    for key in keys:
        by_shard[base_map[key]].append(key)
    values: dict[str, float] = {}
    for shard, shard_keys in by_shard.items():
        with safe_open(base / shard, framework="pt", device="cpu") as handle:
            for key in shard_keys:
                tensor = handle.get_tensor(key)
                if tensor.numel() != 1:
                    raise H4Error(f"global scale is not scalar: {key}")
                values[key] = float(tensor.item())

    mismatches = 0
    for gate in (m for m in modules if m.endswith(".gate_proj")):
        up = gate[:-len("gate_proj")] + "up_proj"
        if values[gate + ".weight_global_scale"] != values[up + ".weight_global_scale"]:
            mismatches += 1
    if mismatches:
        raise H4Error(f"OrcaRouter gate/up global-scale mismatches: {mismatches}")


def tensor_nbytes(handle: Any, key: str) -> int:
    bits = {
        "U8": 8, "I8": 8, "F8_E4M3": 8, "F8_E5M2": 8,
        "F16": 16, "BF16": 16, "F32": 32, "F64": 64,
        "I32": 32, "I64": 64,
    }
    sl = handle.get_slice(key)
    dtype = str(sl.get_dtype())
    if dtype not in bits:
        raise H4Error(f"unsupported dtype for estimate: {dtype}: {key}")
    return math.ceil(math.prod(sl.get_shape()) * bits[dtype] / 8)


def estimate_delta(base: Path, base_map: dict[str, str], modules: list[str]) -> int:
    from safetensors import safe_open

    keys = {
        module + suffix
        for module in modules
        for suffix in (".weight_packed", ".weight_scale", ".weight_global_scale")
    }
    by_shard: dict[str, list[str]] = defaultdict(list)
    for key in keys:
        by_shard[base_map[key]].append(key)
    total = 0
    for shard, shard_keys in by_shard.items():
        with safe_open(base / shard, framework="pt", device="cpu") as handle:
            total += sum(tensor_nbytes(handle, key) for key in shard_keys)
    return total


def gib(value: int) -> float:
    return value / 1024**3


def print_plan(variant: str, modules: list[str], estimated: int) -> None:
    print("H4 partial routed-expert A/B plan")
    print(f"  variant                    : h4-{variant}")
    print(f"  parent                     : H3 quant-layout PASS")
    print(f"  Orca modules normalized    : {len(modules)}")
    print(f"  normalized tensors         : {len(modules) * 3}")
    print(f"  input_scale source         : mazinb/H3")
    print(f"  quantization config        : mazinb/modelopt NVFP4")
    print(f"  estimated delta output     : {gib(estimated):.2f} GiB")
    print(f"  reserve                    : {gib(RESERVE_BYTES):.0f} GiB")
    print(f"  H3 runtime mount           : {H3_MOUNT}")
    print(f"  Orca base runtime mount    : {BASE_MOUNT}")
    print("  MTP tensors changed        : 0")


def clear_output(output: Path, force: bool) -> None:
    if output.exists() and any(output.iterdir()):
        if not force:
            raise H4Error(f"output is not empty: {output}; use --force")
        for child in output.iterdir():
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                shutil.rmtree(child)
    output.mkdir(parents=True, exist_ok=True)


def link_h3_files(h3: Path, output: Path, excluded: set[str]) -> None:
    for source in sorted(h3.iterdir(), key=lambda p: p.name):
        if source.name in excluded:
            continue
        destination = output / source.name
        destination.symlink_to(Path(H3_MOUNT) / source.name, target_is_directory=source.is_dir())


def build(
    variant: str,
    base: Path,
    h3: Path,
    output: Path,
    base_map: dict[str, str],
    h3_map: dict[str, str],
    modules: list[str],
    estimated: int,
    force: bool,
) -> None:
    import torch
    from safetensors import safe_open
    from safetensors.torch import save_file

    clear_output(output, force)
    free = shutil.disk_usage(output).free
    required = estimated + RESERVE_BYTES
    if free < required:
        raise H4Error(
            f"insufficient free space: free={gib(free):.2f} GiB required>={gib(required):.2f} GiB"
        )

    selected_keys = {
        module + suffix
        for module in modules
        for suffix in (".weight_packed", ".weight_scale", ".weight_global_scale")
    }
    by_shard: dict[str, list[str]] = defaultdict(list)
    for key in selected_keys:
        by_shard[base_map[key]].append(key)

    new_index = load_json(h3 / "model.safetensors.index.json")
    new_map: dict[str, str] = new_index["weight_map"]
    written = 0
    for idx, (source_shard, keys) in enumerate(sorted(by_shard.items()), start=1):
        out_name = f"h4-{variant}-{source_shard}"
        tensors: dict[str, Any] = {}
        with safe_open(base / source_shard, framework="pt", device="cpu") as handle:
            for source_key in sorted(keys):
                if source_key.endswith(".weight_packed"):
                    dest_key = source_key[: -len(".weight_packed")] + ".weight"
                    tensor = handle.get_tensor(source_key)
                elif source_key.endswith(".weight_global_scale"):
                    dest_key = source_key[: -len(".weight_global_scale")] + ".weight_scale_2"
                    raw = handle.get_tensor(source_key)
                    if raw.numel() != 1 or float(raw.item()) == 0.0:
                        raise H4Error(f"invalid global scale: {source_key}")
                    tensor = raw.to(dtype=torch.float32).reciprocal()
                else:
                    dest_key = source_key
                    tensor = handle.get_tensor(source_key)

                if dest_key not in h3_map:
                    raise H4Error(f"destination key absent in H3: {dest_key}")
                tensors[dest_key] = tensor
                new_map[dest_key] = out_name
                written += 1

        print(
            f"[delta {idx}/{len(by_shard)}] {source_shard} -> {out_name}: tensors={len(tensors)}",
            flush=True,
        )
        save_file(tensors, output / out_name)
        del tensors

    expected_written = len(modules) * 3
    if written != expected_written:
        raise H4Error(f"wrote {written} normalized tensors, expected {expected_written}")

    (output / "config.json").write_text((h3 / "config.json").read_text(encoding="utf-8"), encoding="utf-8")
    metadata = new_index.get("metadata")
    if isinstance(metadata, dict):
        metadata.pop("total_size", None)
    (output / "model.safetensors.index.json").write_text(
        json.dumps(new_index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    excluded = {
        "config.json",
        "model.safetensors.index.json",
        ".qwen38-hybrid-manifest.json",
    }
    link_h3_files(h3, output, excluded)

    h3_manifest = validate_h3(h3)
    manifest = {
        "schema_version": 1,
        "status": "complete",
        "variant": f"h4-{variant}",
        "parent_variant": "quant-layout-mazinb-experts",
        "parent_h3_revision": h3_manifest.get("overlay_revision"),
        "base_revision": h3_manifest.get("base_revision"),
        "orca_modules_normalized": len(modules),
        "normalized_tensors": written,
        "input_scale_source": "mazinb-h3",
        "quantization_config_source": "mazinb-modelopt-nvfp4",
        "h3_runtime_mount": H3_MOUNT,
        "base_runtime_mount": BASE_MOUNT,
        "mtp_tensors_changed": 0,
        "estimated_delta_bytes": estimated,
    }
    (output / ".qwen38-hybrid-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(f"done -> {output} ({manifest['variant']}, normalized={written}, MTP changed=0)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=("plan", "build"))
    ap.add_argument("--variant", choices=tuple(EXPECTED_MODULES), required=True)
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--h3", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    try:
        validate_h3(args.h3)
        base_map = weight_map(args.base)
        h3_map = weight_map(args.h3)
        modules = selected_modules(base_map, args.variant)
        validate_keys(base_map, h3_map, modules)
        ensure_gate_up_pairs(args.base, base_map, modules)
        estimated = estimate_delta(args.base, base_map, modules)
        print_plan(args.variant, modules, estimated)
        if args.action == "build":
            build(
                args.variant, args.base, args.h3, args.output,
                base_map, h3_map, modules, estimated, args.force
            )
    except H4Error as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
