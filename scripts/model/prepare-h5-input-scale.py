#!/usr/bin/env python3
"""Build H5 by neutralizing all routed-expert ModelOpt input_scale tensors.

Parent: proven H4 orca-all checkpoint.
Change: every main-model routed-expert *.input_scale -> 1.0, preserving dtype/shape.
Keep: OrcaRouter expert weight/group/global-scale values and ModelOpt config.
"""

from __future__ import annotations

import argparse
import json
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

PARENT_MOUNT = "/h4-all"
H3_MOUNT = "/h3-model"
EXPECTED_INPUT_SCALES = 73728
RESERVE_BYTES = 2 * 1024**3


class H5Error(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise H5Error(f"JSON root is not an object: {path}")
    return data


def validate_parent(root: Path) -> dict[str, Any]:
    manifest = load_json(root / ".qwen38-hybrid-manifest.json")
    if (
        manifest.get("status") != "complete"
        or manifest.get("variant") != "h4-orca-all"
        or manifest.get("orca_modules_normalized") != 73728
        or manifest.get("normalized_tensors") != 221184
        or manifest.get("input_scale_source") != "mazinb-h3"
        or manifest.get("mtp_tensors_changed") != 0
    ):
        raise H5Error("H4 orca-all parent manifest is inconsistent")
    config = load_json(root / "config.json")
    quant = config.get("quantization_config")
    if not isinstance(quant, dict) or quant.get("quant_method") != "modelopt":
        raise H5Error("H4 parent is not ModelOpt")
    return manifest


def weight_map(root: Path) -> dict[str, str]:
    data = load_json(root / "model.safetensors.index.json")
    mapping = data.get("weight_map")
    if not isinstance(mapping, dict):
        raise H5Error("invalid parent weight map")
    return {str(k): str(v) for k, v in mapping.items()}


def input_scale_keys(mapping: dict[str, str]) -> list[str]:
    keys = sorted(
        key for key in mapping
        if key.startswith("model.language_model.layers.")
        and ".mlp.experts." in key
        and key.endswith(".input_scale")
    )
    if len(keys) != EXPECTED_INPUT_SCALES:
        raise H5Error(f"input_scale count={len(keys)}, expected={EXPECTED_INPUT_SCALES}")
    return keys


def clear_output(output: Path, force: bool) -> None:
    if output.exists() and any(output.iterdir()):
        if not force:
            raise H5Error(f"output is not empty: {output}; use --force")
        for child in output.iterdir():
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                shutil.rmtree(child)
    output.mkdir(parents=True, exist_ok=True)


def link_parent_files(parent: Path, output: Path, excluded: set[str]) -> None:
    for source in sorted(parent.iterdir(), key=lambda p: p.name):
        if source.name in excluded:
            continue
        (output / source.name).symlink_to(
            Path(PARENT_MOUNT) / source.name,
            target_is_directory=source.is_dir(),
        )


def plan(parent: Path) -> tuple[dict[str, Any], dict[str, str], list[str]]:
    manifest = validate_parent(parent)
    mapping = weight_map(parent)
    keys = input_scale_keys(mapping)
    print("H5 routed-expert input-scale isolation plan")
    print("  variant                    : h5-neutral-input-scale")
    print("  parent                     : H4 orca-all PASS")
    print(f"  input_scale tensors        : {len(keys)}")
    print("  replacement value          : 1.0")
    print("  expert weights/scales      : OrcaRouter via H4-all")
    print("  quantization config        : mazinb/modelopt NVFP4")
    print("  H4 parent runtime mount    : /h4-all")
    print("  H3 runtime mount           : /h3-model")
    print("  MTP tensors changed        : 0")
    return manifest, mapping, keys


def build(parent: Path, output: Path, force: bool) -> None:
    import torch
    from safetensors import safe_open
    from safetensors.torch import save_file

    parent_manifest, parent_map, keys = plan(parent)
    clear_output(output, force)
    if shutil.disk_usage(output).free < RESERVE_BYTES:
        raise H5Error("insufficient free space for H5 reserve")

    by_shard: dict[str, list[str]] = defaultdict(list)
    for key in keys:
        by_shard[parent_map[key]].append(key)

    new_index = load_json(parent / "model.safetensors.index.json")
    new_map: dict[str, str] = new_index["weight_map"]
    written = 0

    for idx, (source_shard, shard_keys) in enumerate(sorted(by_shard.items()), start=1):
        out_name = f"h5-neutral-input-{idx:03d}.safetensors"
        tensors: dict[str, Any] = {}
        with safe_open(parent / source_shard, framework="pt", device="cpu") as handle:
            for key in shard_keys:
                original = handle.get_tensor(key)
                tensors[key] = torch.ones_like(original)
                new_map[key] = out_name
                written += 1
        save_file(tensors, output / out_name)
        print(f"[input-scale {idx}/{len(by_shard)}] {source_shard} -> {out_name}: tensors={len(tensors)}", flush=True)

    if written != EXPECTED_INPUT_SCALES:
        raise H5Error(f"wrote {written} input scales, expected {EXPECTED_INPUT_SCALES}")

    (output / "config.json").write_text(
        (parent / "config.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    metadata = new_index.get("metadata")
    if isinstance(metadata, dict):
        metadata.pop("total_size", None)
    (output / "model.safetensors.index.json").write_text(
        json.dumps(new_index, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    excluded = {"config.json", "model.safetensors.index.json", ".qwen38-hybrid-manifest.json"}
    link_parent_files(parent, output, excluded)

    manifest = {
        "schema_version": 1,
        "status": "complete",
        "variant": "h5-neutral-input-scale",
        "parent_variant": "h4-orca-all",
        "base_revision": parent_manifest.get("base_revision"),
        "input_scale_tensors_changed": written,
        "input_scale_value": 1.0,
        "expert_value_source": "orcarouter-h4-all",
        "quantization_config_source": "mazinb-modelopt-nvfp4",
        "parent_runtime_mount": PARENT_MOUNT,
        "h3_runtime_mount": H3_MOUNT,
        "mtp_tensors_changed": 0,
    }
    (output / ".qwen38-hybrid-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"done -> {output} (h5-neutral-input-scale, input_scales={written}, MTP changed=0)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("action", choices=("plan", "build"))
    ap.add_argument("--parent", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    try:
        if args.action == "plan":
            plan(args.parent)
        else:
            build(args.parent, args.output, args.force)
    except H5Error as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
