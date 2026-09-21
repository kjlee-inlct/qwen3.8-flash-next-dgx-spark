#!/usr/bin/env python3
"""Plan/build an OrcaRouter + mazinb full quantization-layout hybrid.

The hybrid keeps OrcaRouter tensors outside the quantized regions, but replaces:
- all 300 OrcaRouter FP8 group-0 weights with mazinb BF16 weights;
- OrcaRouter routed-expert packed NVFP4 tensors with mazinb ModelOpt NVFP4 tensors;
- OrcaRouter quantization_config with mazinb quantization_config.

MTP tensors remain from OrcaRouter and are never overlaid.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BASE_MOUNT = "/base-model"
RESERVE_BYTES = 20 * 1024**3
VARIANT = "quant-layout-mazinb-experts"

EXPECTED_BASE_EXPERT_SUFFIXES = {
    "down_proj.weight_global_scale": 24576,
    "down_proj.weight_packed": 24576,
    "down_proj.weight_scale": 24576,
    "gate_proj.weight_global_scale": 24576,
    "gate_proj.weight_packed": 24576,
    "gate_proj.weight_scale": 24576,
    "up_proj.weight_global_scale": 24576,
    "up_proj.weight_packed": 24576,
    "up_proj.weight_scale": 24576,
}
EXPECTED_OVERLAY_EXPERT_SUFFIXES = {
    "down_proj.input_scale": 24576,
    "down_proj.weight": 24576,
    "down_proj.weight_scale": 24576,
    "down_proj.weight_scale_2": 24576,
    "gate_proj.input_scale": 24576,
    "gate_proj.weight": 24576,
    "gate_proj.weight_scale": 24576,
    "gate_proj.weight_scale_2": 24576,
    "up_proj.input_scale": 24576,
    "up_proj.weight": 24576,
    "up_proj.weight_scale": 24576,
    "up_proj.weight_scale_2": 24576,
}
DTYPE_BITS = {
    "BOOL": 8,
    "U8": 8,
    "I8": 8,
    "F8_E4M3": 8,
    "F8_E5M2": 8,
    "I16": 16,
    "U16": 16,
    "F16": 16,
    "BF16": 16,
    "I32": 32,
    "U32": 32,
    "F32": 32,
    "I64": 64,
    "U64": 64,
    "F64": 64,
    "F4": 4,
    "F4_E2M1": 4,
}


class HybridError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HybridError(f"cannot read JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise HybridError(f"JSON root is not an object: {path}")
    return data


def weight_map(index: dict[str, Any], label: str) -> dict[str, str]:
    result = index.get("weight_map")
    if not isinstance(result, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in result.items()
    ):
        raise HybridError(f"{label} index has an invalid weight_map")
    return result


def group0_modules(config: dict[str, Any]) -> list[str]:
    try:
        targets = config["quantization_config"]["config_groups"]["group_0"]["targets"]
    except (KeyError, TypeError) as exc:
        raise HybridError("base config has no group_0 targets") from exc
    if not isinstance(targets, list) or not all(isinstance(x, str) for x in targets):
        raise HybridError("base group_0 targets are invalid")
    if len(targets) != 300:
        raise HybridError(f"unexpected base group_0 target count: {len(targets)}")
    if any(x.startswith("mtp.") for x in targets):
        raise HybridError("MTP target entered base group_0 target set")
    return list(targets)


def is_expert_key(key: str) -> bool:
    return ".mlp.experts." in key


def expert_suffix(key: str) -> str | None:
    marker = ".mlp.experts."
    if marker not in key:
        return None
    tail = key.split(marker, 1)[1]
    parts = tail.split(".", 1)
    return parts[1] if len(parts) == 2 else None


def suffix_counts(keys: set[str]) -> dict[str, int]:
    return dict(sorted(Counter(expert_suffix(k) for k in keys if expert_suffix(k)).items()))


def validate_quantization_configs(
    base_config: dict[str, Any], overlay_config: dict[str, Any]
) -> None:
    base_q = base_config.get("quantization_config")
    overlay_q = overlay_config.get("quantization_config")
    if not isinstance(base_q, dict) or not isinstance(overlay_q, dict):
        raise HybridError("both checkpoints must have quantization_config")
    if base_q.get("quant_method") != "compressed-tensors":
        raise HybridError("unexpected OrcaRouter quantization method")
    if overlay_q.get("quant_method") != "modelopt":
        raise HybridError("unexpected mazinb quantization method")
    if overlay_q.get("quant_algo") != "NVFP4":
        raise HybridError("unexpected mazinb quantization algorithm")


def require_files(root: Path, names: set[str], label: str) -> None:
    missing = [str(root / name) for name in sorted(names) if not (root / name).is_file()]
    if missing:
        raise HybridError(f"missing {label} shard(s): " + ", ".join(missing[:10]))


def inspect(base: Path, overlay: Path) -> dict[str, Any]:
    base_config = load_json(base / "config.json")
    overlay_config = load_json(overlay / "config.json")
    validate_quantization_configs(base_config, overlay_config)

    base_index = load_json(base / "model.safetensors.index.json")
    overlay_index = load_json(overlay / "model.safetensors.index.json")
    base_map = weight_map(base_index, "base")
    overlay_map = weight_map(overlay_index, "overlay")
    modules = group0_modules(base_config)

    missing: list[str] = []
    for module in modules:
        for label, mapping, key in (
            ("base", base_map, module + ".weight"),
            ("base", base_map, module + ".weight_scale"),
            ("overlay", overlay_map, module + ".weight"),
        ):
            if key not in mapping:
                missing.append(f"{label}:{key}")
    if missing:
        raise HybridError("missing group0 tensor keys: " + ", ".join(missing[:10]))

    base_expert = {key for key in base_map if is_expert_key(key)}
    overlay_expert = {key for key in overlay_map if is_expert_key(key)}
    base_suffix = suffix_counts(base_expert)
    overlay_suffix = suffix_counts(overlay_expert)
    if base_suffix != EXPECTED_BASE_EXPERT_SUFFIXES:
        raise HybridError(f"unexpected OrcaRouter expert layout: {base_suffix}")
    if overlay_suffix != EXPECTED_OVERLAY_EXPERT_SUFFIXES:
        raise HybridError(f"unexpected mazinb expert layout: {overlay_suffix}")
    if any(key.startswith("mtp.") for key in base_expert | overlay_expert):
        raise HybridError("MTP tensor entered routed-expert set")

    base_remove = set(base_expert)
    base_replace = {module + ".weight" for module in modules}
    base_remove.update(module + ".weight_scale" for module in modules)

    overlay_add = set(overlay_expert)
    overlay_replace = {module + ".weight" for module in modules}
    overlay_selected = overlay_add | overlay_replace

    affected_base_shards = {base_map[key] for key in base_remove | base_replace}
    overlay_shards = {overlay_map[key] for key in overlay_selected}
    require_files(base, affected_base_shards, "base")
    require_files(overlay, overlay_shards, "overlay")

    return {
        "base_config": base_config,
        "overlay_config": overlay_config,
        "base_index": base_index,
        "overlay_index": overlay_index,
        "base_map": base_map,
        "overlay_map": overlay_map,
        "modules": modules,
        "base_expert": base_expert,
        "overlay_expert": overlay_expert,
        "base_remove": base_remove,
        "base_replace": base_replace,
        "overlay_replace": overlay_replace,
        "affected_base_shards": sorted(affected_base_shards),
        "overlay_shards": sorted(overlay_shards),
        "base_suffix": base_suffix,
        "overlay_suffix": overlay_suffix,
    }


def gib(value: int) -> float:
    return value / 1024**3


def tensor_nbytes(handle: Any, key: str) -> int:
    sl = handle.get_slice(key)
    dtype = str(sl.get_dtype())
    bits = DTYPE_BITS.get(dtype)
    if bits is None:
        raise HybridError(f"unsupported dtype for size estimate: {dtype}: {key}")
    count = math.prod(sl.get_shape())
    return math.ceil(count * bits / 8)


def estimate_output_bytes(base: Path, overlay: Path, info: dict[str, Any]) -> int:
    try:
        from safetensors import safe_open
    except ImportError as exc:
        raise HybridError("size estimate requires safetensors") from exc

    base_remove: set[str] = info["base_remove"]
    base_replace: set[str] = info["base_replace"]
    base_map: dict[str, str] = info["base_map"]
    overlay_map: dict[str, str] = info["overlay_map"]
    overlay_selected = set(info["overlay_expert"]) | set(info["overlay_replace"])

    total = 0
    by_base: dict[str, set[str]] = defaultdict(set)
    for key, shard in base_map.items():
        if shard in info["affected_base_shards"]:
            by_base[shard].add(key)
    for shard, keys in by_base.items():
        with safe_open(base / shard, framework="pt", device="cpu") as handle:
            for key in keys:
                if key in base_remove or key in base_replace:
                    continue
                total += tensor_nbytes(handle, key)

    by_overlay: dict[str, set[str]] = defaultdict(set)
    for key in overlay_selected:
        by_overlay[overlay_map[key]].add(key)
    for shard, keys in by_overlay.items():
        with safe_open(overlay / shard, framework="pt", device="cpu") as handle:
            for key in keys:
                total += tensor_nbytes(handle, key)
    return total


def print_plan(
    base: Path, overlay: Path, output: Path, info: dict[str, Any], estimated: int | None
) -> None:
    print("Full quantization-layout hybrid plan")
    print(f"  variant                    : {VARIANT}")
    print(f"  base                       : {base}")
    print(f"  overlay                    : {overlay}")
    print(f"  output                     : {output}")
    print(f"  group0 BF16 replacements   : {len(info['modules'])}")
    print(f"  group0 FP8 scales removed  : {len(info['modules'])}")
    print(f"  base expert tensors removed: {len(info['base_expert'])}")
    print(f"  overlay expert tensors add : {len(info['overlay_expert'])}")
    print(f"  base expert suffixes       : {info['base_suffix']}")
    print(f"  overlay expert suffixes    : {info['overlay_suffix']}")
    print(f"  base shards rewritten      : {len(info['affected_base_shards'])}")
    print(f"  overlay source shards      : {len(info['overlay_shards'])}")
    if estimated is not None:
        print(f"  estimated tensor output    : {gib(estimated):.2f} GiB")
        print(f"  reserve                    : {gib(RESERVE_BYTES):.0f} GiB")
    print(f"  base runtime mount         : {BASE_MOUNT}")
    print("  quantization config        : mazinb/modelopt NVFP4")
    print("  MTP tensors changed        : 0")


def clear_output(output: Path, force: bool) -> None:
    if output.exists() and any(output.iterdir()):
        if not force:
            raise HybridError(f"output is not empty: {output}; use --force to rebuild it")
        for child in output.iterdir():
            if child.is_symlink() or child.is_file():
                child.unlink()
            elif child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    output.mkdir(parents=True, exist_ok=True)


def link_unaffected_base_files(
    base: Path, output: Path, affected_shards: set[str]
) -> None:
    excluded = {
        "config.json",
        "model.safetensors.index.json",
        ".qwen38-model-manifest.json",
        ".qwen38-hybrid-manifest.json",
    } | affected_shards
    for source in sorted(base.iterdir(), key=lambda p: p.name):
        if source.name in excluded:
            continue
        destination = output / source.name
        if destination.exists() or destination.is_symlink():
            continue
        destination.symlink_to(Path(BASE_MOUNT) / source.name, target_is_directory=source.is_dir())


def build(
    base: Path,
    overlay: Path,
    output: Path,
    info: dict[str, Any],
    force: bool,
    base_revision: str,
    overlay_revision: str,
) -> None:
    try:
        import torch
        from safetensors import safe_open
        from safetensors.torch import save_file
    except ImportError as exc:
        raise HybridError("build requires torch+safetensors") from exc

    estimated = estimate_output_bytes(base, overlay, info)
    clear_output(output, force)
    required = estimated + RESERVE_BYTES
    free = shutil.disk_usage(output).free
    if free < required:
        raise HybridError(
            f"insufficient free space: free={gib(free):.2f} GiB "
            f"required>={gib(required):.2f} GiB"
        )

    manifest_path = output / ".qwen38-hybrid-manifest.json"
    manifest = {
        "schema_version": 1,
        "status": "building",
        "variant": VARIANT,
        "base_revision": base_revision,
        "overlay_revision": overlay_revision,
        "base_runtime_mount": BASE_MOUNT,
        "group0_bf16_weights": len(info["modules"]),
        "base_expert_tensors_removed": len(info["base_expert"]),
        "overlay_expert_tensors_added": len(info["overlay_expert"]),
        "mtp_tensors_changed": 0,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    base_map: dict[str, str] = info["base_map"]
    overlay_map: dict[str, str] = info["overlay_map"]
    base_remove: set[str] = info["base_remove"]
    base_replace: set[str] = info["base_replace"]

    replace_by_base: dict[str, set[str]] = defaultdict(set)
    for key in base_replace:
        replace_by_base[base_map[key]].add(key)

    for idx, shard in enumerate(info["affected_base_shards"], start=1):
        replacements: dict[str, Any] = {}
        by_overlay: dict[str, set[str]] = defaultdict(set)
        for key in replace_by_base.get(shard, set()):
            by_overlay[overlay_map[key]].add(key)
        for overlay_shard, keys in by_overlay.items():
            with safe_open(overlay / overlay_shard, framework="pt", device="cpu") as handle:
                for key in sorted(keys):
                    tensor = handle.get_tensor(key)
                    if tensor.dtype != torch.bfloat16:
                        raise HybridError(f"group0 overlay is not BF16: {key}: {tensor.dtype}")
                    replacements[key] = tensor

        tensors: dict[str, Any] = {}
        metadata = None
        with safe_open(base / shard, framework="pt", device="cpu") as handle:
            metadata = handle.metadata()
            for key in handle.keys():
                if key in base_remove:
                    continue
                if key in base_replace:
                    tensors[key] = replacements[key]
                else:
                    tensors[key] = handle.get_tensor(key)
        print(
            f"[base {idx}/{len(info['affected_base_shards'])}] rewrite {shard}: "
            f"keep={len(tensors)} replace={len(replacements)}",
            flush=True,
        )
        save_file(tensors, output / shard, metadata=metadata)
        del tensors
        del replacements

    expert_output_map: dict[str, str] = {}
    selected_by_overlay: dict[str, set[str]] = defaultdict(set)
    for key in info["overlay_expert"]:
        selected_by_overlay[overlay_map[key]].add(key)
    for idx, (source_shard, keys) in enumerate(sorted(selected_by_overlay.items()), start=1):
        out_name = "expert-" + source_shard
        tensors: dict[str, Any] = {}
        metadata = None
        with safe_open(overlay / source_shard, framework="pt", device="cpu") as handle:
            metadata = handle.metadata()
            for key in sorted(keys):
                tensors[key] = handle.get_tensor(key)
                expert_output_map[key] = out_name
        print(
            f"[expert {idx}/{len(selected_by_overlay)}] extract {source_shard}: "
            f"tensors={len(tensors)}",
            flush=True,
        )
        save_file(tensors, output / out_name, metadata=metadata)
        del tensors

    link_unaffected_base_files(base, output, set(info["affected_base_shards"]))

    new_config = json.loads(json.dumps(info["base_config"]))
    new_config["quantization_config"] = json.loads(
        json.dumps(info["overlay_config"]["quantization_config"])
    )
    (output / "config.json").write_text(
        json.dumps(new_config, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    new_index = json.loads(json.dumps(info["base_index"]))
    metadata = new_index.get("metadata")
    if isinstance(metadata, dict):
        metadata.pop("total_size", None)
    new_map: dict[str, str] = new_index["weight_map"]
    for key in info["base_expert"]:
        new_map.pop(key, None)
    removed_scales = 0
    for module in info["modules"]:
        if new_map.pop(module + ".weight_scale", None) is not None:
            removed_scales += 1
    if removed_scales != 300:
        raise HybridError(f"removed {removed_scales} group0 scales, expected 300")
    new_map.update(expert_output_map)
    (output / "model.safetensors.index.json").write_text(
        json.dumps(new_index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    manifest.update(
        {
            "status": "complete",
            "group0_fp8_scales_removed": removed_scales,
            "quantization_config_source": "mazinb-modelopt-nvfp4",
            "estimated_tensor_output_bytes": estimated,
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"done -> {output} (group0 BF16=300, base experts removed={len(info['base_expert'])}, "
        f"mazinb experts added={len(info['overlay_expert'])}, MTP changed=0)"
    )


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=("plan", "build"))
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--overlay", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--base-revision", default="")
    ap.add_argument("--overlay-revision", default="")
    ap.add_argument("--force", action="store_true")
    return ap


def main() -> int:
    args = parser().parse_args()
    try:
        info = inspect(args.base, args.overlay)
        estimated = estimate_output_bytes(args.base, args.overlay, info)
        print_plan(args.base, args.overlay, args.output, info, estimated)
        if args.action == "build":
            build(
                args.base,
                args.overlay,
                args.output,
                info,
                args.force,
                args.base_revision,
                args.overlay_revision,
            )
    except HybridError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
