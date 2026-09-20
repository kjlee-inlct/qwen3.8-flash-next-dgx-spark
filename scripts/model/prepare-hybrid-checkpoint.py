#!/usr/bin/env python3
"""Plan or build OrcaRouter/mazinb BF16 hybrid checkpoints.

Two variants are supported:
- residual-bf16: replace the 96 main-model residual-writer FP8 modules.
- group0-bf16: replace all 300 main-model FP8 group-0 modules.

Both variants leave MTP tensors untouched. Plan mode needs only the Python
standard library. Build mode additionally needs safetensors + torch and is
normally invoked by prepare-hybrid-checkpoint.sh inside the existing v0.29
runtime image.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

VARIANTS = ("residual-bf16", "group0-bf16")
BASE_MOUNT = "/base-model"
RESERVE_BYTES = 20 * 1024**3
MODULE_PATTERNS = {
    "self_attn.o_proj": re.compile(
        r"^model\.language_model\.layers\.\d+\.self_attn\.o_proj$"
    ),
    "linear_attn.out_proj": re.compile(
        r"^model\.language_model\.layers\.\d+\.linear_attn\.out_proj$"
    ),
    "shared_expert.down_proj": re.compile(
        r"^model\.language_model\.layers\.\d+\.mlp\.shared_expert\.down_proj$"
    ),
}
EXPECTED = {
    "self_attn.o_proj": 12,
    "linear_attn.out_proj": 36,
    "shared_expert.down_proj": 48,
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


def module_group(name: str) -> str | None:
    for group, pattern in MODULE_PATTERNS.items():
        if pattern.fullmatch(name):
            return group
    return None


def target_modules(base_config: dict[str, Any], variant: str) -> list[str]:
    try:
        targets = base_config["quantization_config"]["config_groups"]["group_0"]["targets"]
    except (KeyError, TypeError) as exc:
        raise HybridError("base config has no compressed-tensors group_0 targets") from exc
    if not isinstance(targets, list) or not all(isinstance(x, str) for x in targets):
        raise HybridError("base group_0 targets are invalid")

    if variant == "group0-bf16":
        if any(name.startswith("mtp.") for name in targets):
            raise HybridError("MTP target entered base group_0 target set")
        if len(targets) != 300:
            raise HybridError(f"unexpected group_0 target count: {len(targets)}")
        return list(targets)

    selected = [name for name in targets if module_group(name)]
    counts = {group: 0 for group in EXPECTED}
    for name in selected:
        counts[module_group(name)] += 1  # type: ignore[index]

    if counts != EXPECTED or len(selected) != 96:
        raise HybridError(
            f"unexpected residual-writer target set: total={len(selected)} counts={counts}"
        )
    return selected


def weight_map(index: dict[str, Any], label: str) -> dict[str, str]:
    result = index.get("weight_map")
    if not isinstance(result, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in result.items()
    ):
        raise HybridError(f"{label} index has an invalid weight_map")
    return result


def validate_tensor_keys(
    modules: list[str],
    base_map: dict[str, str],
    overlay_map: dict[str, str],
) -> None:
    missing: list[str] = []
    for module in modules:
        bw = module + ".weight"
        bs = module + ".weight_scale"
        ow = module + ".weight"
        if bw not in base_map:
            missing.append(f"base:{bw}")
        if bs not in base_map:
            missing.append(f"base:{bs}")
        if ow not in overlay_map:
            missing.append(f"overlay:{ow}")
        if module.startswith("mtp."):
            raise HybridError(f"MTP tensor entered hybrid set: {module}")
    if missing:
        raise HybridError("missing expected tensor keys: " + ", ".join(missing[:10]))


def inspect(base: Path, overlay: Path, variant: str) -> dict[str, Any]:
    base_config = load_json(base / "config.json")
    base_index = load_json(base / "model.safetensors.index.json")
    overlay_index = load_json(overlay / "model.safetensors.index.json")
    modules = target_modules(base_config, variant)
    base_map = weight_map(base_index, "base")
    overlay_map = weight_map(overlay_index, "overlay")
    validate_tensor_keys(modules, base_map, overlay_map)

    affected = sorted({base_map[module + ".weight"] for module in modules})
    affected += sorted(
        {base_map[module + ".weight_scale"] for module in modules}
        - set(affected)
    )
    affected = sorted(set(affected))

    missing_files = [
        str(path)
        for path in [*(base / name for name in affected)]
        if not path.is_file()
    ]
    overlay_shards = sorted({overlay_map[module + ".weight"] for module in modules})
    missing_files.extend(
        str(path)
        for path in (overlay / name for name in overlay_shards)
        if not path.is_file()
    )
    if missing_files:
        raise HybridError("missing required shard(s): " + ", ".join(missing_files))

    rewrite_bytes = sum((base / name).stat().st_size for name in affected)
    return {
        "base_config": base_config,
        "base_index": base_index,
        "overlay_index": overlay_index,
        "modules": modules,
        "base_map": base_map,
        "overlay_map": overlay_map,
        "affected_shards": affected,
        "rewrite_bytes": rewrite_bytes,
    }


def gib(value: int) -> float:
    return value / 1024**3


def print_plan(
    base: Path, overlay: Path, output: Path, info: dict[str, Any], variant: str
) -> None:
    modules = info["modules"]
    counts = {group: sum(module_group(x) == group for x in modules) for group in EXPECTED}
    title = "Residual BF16 hybrid plan" if variant == "residual-bf16" else "Full group-0 BF16 hybrid plan"
    print(title)
    print(f"  variant          : {variant}")
    print(f"  base             : {base}")
    print(f"  overlay          : {overlay}")
    print(f"  output           : {output}")
    if variant == "residual-bf16":
        print(f"  residual modules : {len(modules)} ({counts})")
    else:
        print(f"  group-0 modules  : {len(modules)}")
    print(f"  FP8 weights      : {len(modules)}")
    print(f"  FP8 scales       : {len(modules)}")
    print(f"  BF16 overlays    : {len(modules)}")
    print(f"  affected shards  : {len(info['affected_shards'])}")
    print(f"  rewrite source   : {gib(info['rewrite_bytes']):.2f} GiB")
    print(f"  reserve          : {gib(RESERVE_BYTES):.0f} GiB")
    print(f"  base runtime mount: {BASE_MOUNT}")
    for name in info["affected_shards"]:
        print(f"    rewrite {name}")


def link_unaffected_base_files(
    base: Path,
    output: Path,
    affected_shards: set[str],
) -> None:
    excluded = {
        "config.json",
        "model.safetensors.index.json",
        ".qwen38-hybrid-manifest.json",
    } | affected_shards
    for source in sorted(base.iterdir(), key=lambda p: p.name):
        if source.name in excluded:
            continue
        destination = output / source.name
        if destination.exists() or destination.is_symlink():
            continue
        # Runtime mounts the immutable base checkpoint at /base-model.
        destination.symlink_to(Path(BASE_MOUNT) / source.name, target_is_directory=source.is_dir())


def build(
    base: Path,
    overlay: Path,
    output: Path,
    info: dict[str, Any],
    force: bool,
    base_revision: str,
    overlay_revision: str,
    variant: str,
) -> None:
    try:
        import torch
        from safetensors import safe_open
        from safetensors.torch import save_file
    except ImportError as exc:
        raise HybridError(
            "build requires torch+safetensors; use scripts/model/prepare-hybrid-checkpoint.sh build"
        ) from exc

    if output.exists() and any(output.iterdir()):
        if not force:
            raise HybridError(f"output is not empty: {output}; use --force to rebuild it")
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    free = shutil.disk_usage(output).free
    required = info["rewrite_bytes"] + RESERVE_BYTES
    if free < required:
        raise HybridError(
            f"insufficient free space: free={gib(free):.2f} GiB "
            f"required>={gib(required):.2f} GiB"
        )

    manifest_path = output / ".qwen38-hybrid-manifest.json"
    manifest = {
        "schema_version": 1,
        "status": "building",
        "variant": variant,
        "base_revision": base_revision,
        "overlay_revision": overlay_revision,
        "base_runtime_mount": BASE_MOUNT,
        "selected_modules": len(info["modules"]),
        "affected_shards": info["affected_shards"],
    }
    if variant == "residual-bf16":
        # Preserve the original manifest field for backward/runtime compatibility.
        manifest["residual_modules"] = len(info["modules"])
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    modules = set(info["modules"])
    base_map: dict[str, str] = info["base_map"]
    overlay_map: dict[str, str] = info["overlay_map"]
    affected = set(info["affected_shards"])

    by_base_shard: dict[str, set[str]] = {name: set() for name in affected}
    for module in modules:
        by_base_shard[base_map[module + ".weight"]].add(module)
        by_base_shard[base_map[module + ".weight_scale"]].add(module)

    for index, shard in enumerate(sorted(affected), start=1):
        source = base / shard
        destination = output / shard
        selected_modules = by_base_shard[shard]
        replace_weights = {m + ".weight" for m in selected_modules if base_map[m + ".weight"] == shard}
        remove_scales = {
            m + ".weight_scale"
            for m in selected_modules
            if base_map[m + ".weight_scale"] == shard
        }
        replacements: dict[str, Any] = {}
        by_overlay_shard: dict[str, set[str]] = {}
        for key in replace_weights:
            by_overlay_shard.setdefault(overlay_map[key], set()).add(key)
        for overlay_shard, keys in sorted(by_overlay_shard.items()):
            with safe_open(overlay / overlay_shard, framework="pt", device="cpu") as handle:
                for key in sorted(keys):
                    tensor = handle.get_tensor(key)
                    if tensor.dtype != torch.bfloat16:
                        raise HybridError(
                            f"overlay tensor is not BF16: {key}: {tensor.dtype}"
                        )
                    replacements[key] = tensor

        tensors: dict[str, Any] = {}
        metadata = None
        with safe_open(source, framework="pt", device="cpu") as handle:
            metadata = handle.metadata()
            for key in handle.keys():
                if key in remove_scales:
                    continue
                if key in replace_weights:
                    tensors[key] = replacements[key]
                else:
                    tensors[key] = handle.get_tensor(key)
        print(
            f"[{index}/{len(affected)}] rewrite {shard}: "
            f"replace={len(replace_weights)} remove_scales={len(remove_scales)}",
            flush=True,
        )
        save_file(tensors, destination, metadata=metadata)
        del tensors
        del replacements

    link_unaffected_base_files(base, output, affected)

    new_config = json.loads(json.dumps(info["base_config"]))
    targets = new_config["quantization_config"]["config_groups"]["group_0"]["targets"]
    new_targets = [name for name in targets if name not in modules]
    expected_removed = len(modules)
    if len(targets) - len(new_targets) != expected_removed:
        raise HybridError(
            f"failed to remove exactly {expected_removed} FP8 config targets"
        )
    new_config["quantization_config"]["config_groups"]["group_0"]["targets"] = new_targets
    (output / "config.json").write_text(
        json.dumps(new_config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    new_index = json.loads(json.dumps(info["base_index"]))
    metadata = new_index.get("metadata")
    if isinstance(metadata, dict):
        # The BF16 overlays change tensor byte counts; a stale total_size is worse
        # than omitting this optional advisory field.
        metadata.pop("total_size", None)
    new_map = new_index["weight_map"]
    removed_scales = 0
    for module in modules:
        scale_key = module + ".weight_scale"
        if new_map.pop(scale_key, None) is not None:
            removed_scales += 1
    if removed_scales != expected_removed:
        raise HybridError(
            f"removed {removed_scales} scales, expected {expected_removed}"
        )
    (output / "model.safetensors.index.json").write_text(
        json.dumps(new_index, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    manifest.update(
        {
            "status": "complete",
            "fp8_targets_removed": expected_removed,
            "fp8_scales_removed": expected_removed,
            "bf16_weights_overlaid": expected_removed,
            "mtp_tensors_changed": 0,
            "remaining_fp8_group0_targets": len(new_targets),
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"done -> {output} "
        f"(BF16 overlays={expected_removed}, remaining FP8 group_0={len(new_targets)}, MTP changed=0)"
    )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("action", choices=("plan", "build"))
    result.add_argument(
        "--variant",
        choices=VARIANTS,
        default=os.environ.get("HYBRID_VARIANT", "residual-bf16"),
    )
    result.add_argument("--base", type=Path, required=True)
    result.add_argument("--overlay", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--base-revision", default="")
    result.add_argument("--overlay-revision", default="")
    result.add_argument("--force", action="store_true")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        info = inspect(args.base, args.overlay, args.variant)
        print_plan(args.base, args.overlay, args.output, info, args.variant)
        if args.action == "build":
            build(
                args.base,
                args.overlay,
                args.output,
                info,
                args.force,
                args.base_revision,
                args.overlay_revision,
                args.variant,
            )
    except HybridError as exc:
        print(f"ERROR: {exc}", file=os.sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
