#!/usr/bin/env python3
"""Build H6 config-only control: ModelOpt W4A16_NVFP4 over proven H5.

No tensor values are changed. The H5 Orca expert payload, normalized scales,
and neutral input_scale=1.0 tensors remain byte-identical. Only the ModelOpt
quant_algo changes from NVFP4 (W4A4) to W4A16_NVFP4.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

PARENT_MOUNT = "/h5-parent"
H4_MOUNT = "/h4-all"
H3_MOUNT = "/h3-model"
BASE_MOUNT = "/base-model"


class H6Error(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise H6Error(f"JSON root is not an object: {path}")
    return data


def validate_parent(root: Path) -> dict[str, Any]:
    manifest = load_json(root / ".qwen38-hybrid-manifest.json")
    if (
        manifest.get("status") != "complete"
        or manifest.get("variant") != "h5-neutral-input-scale"
        or manifest.get("parent_variant") != "h4-orca-all"
        or manifest.get("input_scale_tensors_changed") != 73728
        or manifest.get("input_scale_value") != 1.0
        or manifest.get("expert_value_source") != "orcarouter-h4-all"
        or manifest.get("mtp_tensors_changed") != 0
    ):
        raise H6Error("H5 parent manifest is inconsistent")

    config = load_json(root / "config.json")
    quant = config.get("quantization_config")
    if not isinstance(quant, dict):
        raise H6Error("H5 config has no quantization_config")
    if quant.get("quant_method") != "modelopt":
        raise H6Error("H5 parent is not ModelOpt")
    if str(quant.get("quant_algo", "")).upper() != "NVFP4":
        raise H6Error(f"unexpected H5 quant_algo: {quant.get('quant_algo')}")
    return manifest


def clear_output(output: Path, force: bool) -> None:
    if output.exists() and any(output.iterdir()):
        if not force:
            raise H6Error(f"output is not empty: {output}; use --force")
        for child in output.iterdir():
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                shutil.rmtree(child)
    output.mkdir(parents=True, exist_ok=True)


def link_parent_files(parent: Path, output: Path) -> None:
    excluded = {"config.json", ".qwen38-hybrid-manifest.json"}
    for source in sorted(parent.iterdir(), key=lambda p: p.name):
        if source.name in excluded:
            continue
        (output / source.name).symlink_to(
            Path(PARENT_MOUNT) / source.name,
            target_is_directory=source.is_dir(),
        )


def plan(parent: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = validate_parent(parent)
    config = load_json(parent / "config.json")
    print("H6 ModelOpt activation-mode control plan")
    print("  variant                    : h6-modelopt-w4a16")
    print("  parent                     : H5 neutral-input PASS")
    print("  expert tensor payload      : unchanged (OrcaRouter via H4-all)")
    print("  input_scale tensors        : unchanged (73728 values = 1.0)")
    print("  quant_method               : modelopt")
    print("  quant_algo before          : NVFP4 (W4A4)")
    print("  quant_algo after           : W4A16_NVFP4")
    print("  safetensor bytes changed   : 0")
    print("  MTP tensors changed        : 0")
    return manifest, config


def build(parent: Path, output: Path, force: bool) -> None:
    parent_manifest, config = plan(parent)
    clear_output(output, force)

    new_config = json.loads(json.dumps(config))
    quant = new_config["quantization_config"]
    quant["quant_algo"] = "W4A16_NVFP4"
    (output / "config.json").write_text(
        json.dumps(new_config, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    link_parent_files(parent, output)

    manifest = {
        "schema_version": 1,
        "status": "complete",
        "variant": "h6-modelopt-w4a16",
        "parent_variant": "h5-neutral-input-scale",
        "base_revision": parent_manifest.get("base_revision"),
        "expert_value_source": "orcarouter-h4-all",
        "input_scale_source": "h5-neutral-1.0",
        "input_scale_tensors_changed": 0,
        "quantization_config_source": "modelopt-w4a16-control",
        "quant_algo_before": "NVFP4",
        "quant_algo_after": "W4A16_NVFP4",
        "safetensor_bytes_changed": 0,
        "parent_runtime_mount": PARENT_MOUNT,
        "h4_runtime_mount": H4_MOUNT,
        "h3_runtime_mount": H3_MOUNT,
        "base_runtime_mount": BASE_MOUNT,
        "mtp_tensors_changed": 0,
    }
    (output / ".qwen38-hybrid-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"done -> {output} (config-only W4A16 control, tensor bytes changed=0)")


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
    except H6Error as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
