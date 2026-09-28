#!/usr/bin/env python3
"""Validate the generated OrcaRouter/mazinb H6 hybrid checkpoint chain."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ORCA_REPO = "orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4"
ORCA_REVISION = "c1209bda15a6bbc4c68b585e93d40c0d85f50306"
MAZINB_REPO = "mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4"


class HybridValidationError(RuntimeError):
    """Raised when a generated hybrid stage is incomplete or inconsistent."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HybridValidationError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise HybridValidationError(f"JSON root is not an object: {path}")
    return data


def require(condition: bool, message: str) -> None:
    if not condition:
        raise HybridValidationError(message)


def model_manifest(root: Path, *, repository: str, revision: str | None = None) -> dict[str, Any]:
    data = load_json(root / ".qwen38-model-manifest.json")
    require(data.get("status") == "complete", f"incomplete model manifest: {root}")
    require(data.get("repository") == repository, f"unexpected repository in {root}")
    actual_revision = str(data.get("revision") or "")
    require(bool(actual_revision), f"missing model revision in {root}")
    if revision is not None:
        require(actual_revision == revision, f"unexpected revision in {root}: {actual_revision}")
    require((root / "model.safetensors.index.json").is_file(), f"model index missing: {root}")
    return data


def hybrid_manifest(root: Path, variant: str) -> dict[str, Any]:
    data = load_json(root / ".qwen38-hybrid-manifest.json")
    require(data.get("status") == "complete", f"incomplete hybrid manifest: {root}")
    require(data.get("variant") == variant, f"unexpected hybrid variant in {root}: {data.get('variant')}")
    require((root / "model.safetensors.index.json").is_file(), f"hybrid model index missing: {root}")
    return data


def validate(args: argparse.Namespace) -> None:
    stage_order = {"h3": 3, "h4": 4, "h5": 5, "h6": 6}
    through = stage_order[args.through]
    base = model_manifest(args.base_dir, repository=ORCA_REPO, revision=ORCA_REVISION)
    overlay = None
    if not args.runtime_only:
        require(args.overlay_dir is not None, "--overlay-dir is required without --runtime-only")
        overlay = model_manifest(args.overlay_dir, repository=MAZINB_REPO)

    h3 = hybrid_manifest(args.h3_dir, "quant-layout-mazinb-experts")
    require(h3.get("base_revision") == base.get("revision"), "H3 base revision mismatch")
    require(bool(h3.get("overlay_revision")), "H3 overlay revision is missing")
    if overlay is not None:
        require(h3.get("overlay_revision") == overlay.get("revision"), "H3 overlay revision mismatch")
    require(h3.get("group0_bf16_weights") == 300, "H3 group-0 BF16 count mismatch")
    require(h3.get("group0_fp8_scales_removed") == 300, "H3 removed FP8 scale count mismatch")
    require(h3.get("base_expert_tensors_removed") == 221184, "H3 removed expert tensor count mismatch")
    require(h3.get("overlay_expert_tensors_added") == 294912, "H3 overlay expert tensor count mismatch")
    require(h3.get("quantization_config_source") == "mazinb-modelopt-nvfp4", "H3 quantization source mismatch")
    require(h3.get("mtp_tensors_changed") == 0, "H3 unexpectedly changes MTP")
    if through == 3:
        print(
            "OrcaRouter hybrid chain is valid through H3 "
            f"(base={base.get('revision')}, overlay={h3.get('overlay_revision')})"
        )
        return

    h4 = hybrid_manifest(args.h4_dir, "h4-orca-all")
    require(h4.get("parent_variant") == "quant-layout-mazinb-experts", "H4 parent mismatch")
    require(h4.get("orca_modules_normalized") == 73728, "H4 normalized module count mismatch")
    require(h4.get("normalized_tensors") == 221184, "H4 normalized tensor count mismatch")
    require(h4.get("input_scale_source") == "mazinb-h3", "H4 input-scale source mismatch")
    require(h4.get("quantization_config_source") == "mazinb-modelopt-nvfp4", "H4 quantization source mismatch")
    require(h4.get("mtp_tensors_changed") == 0, "H4 unexpectedly changes MTP")
    if through == 4:
        print("OrcaRouter hybrid chain is valid through H4")
        return

    h5 = hybrid_manifest(args.h5_dir, "h5-neutral-input-scale")
    require(h5.get("parent_variant") == "h4-orca-all", "H5 parent mismatch")
    require(h5.get("input_scale_tensors_changed") == 73728, "H5 input-scale tensor count mismatch")
    require(h5.get("input_scale_value") == 1.0, "H5 input-scale value mismatch")
    require(h5.get("expert_value_source") == "orcarouter-h4-all", "H5 expert source mismatch")
    require(h5.get("quantization_config_source") == "mazinb-modelopt-nvfp4", "H5 quantization source mismatch")
    require(h5.get("mtp_tensors_changed") == 0, "H5 unexpectedly changes MTP")
    if through == 5:
        print("OrcaRouter hybrid chain is valid through H5")
        return

    h6 = hybrid_manifest(args.model_dir, "h6-modelopt-w4a16")
    require(h6.get("parent_variant") == "h5-neutral-input-scale", "H6 parent mismatch")
    require(h6.get("expert_value_source") == "orcarouter-h4-all", "H6 expert source mismatch")
    require(h6.get("input_scale_source") == "h5-neutral-1.0", "H6 input-scale source mismatch")
    require(h6.get("quant_algo_before") == "NVFP4", "H6 source quant_algo mismatch")
    require(h6.get("quant_algo_after") == "W4A16_NVFP4", "H6 quant_algo mismatch")
    require(h6.get("safetensor_bytes_changed") == 0, "H6 must be config-only")
    require(h6.get("mtp_tensors_changed") == 0, "H6 unexpectedly changes MTP")
    require(h6.get("base_revision") == base.get("revision"), "H6 base revision mismatch")

    config = load_json(args.model_dir / "config.json")
    quant = config.get("quantization_config")
    require(isinstance(quant, dict), "H6 config has no quantization_config")
    require(quant.get("quant_method") == "modelopt", "H6 quant_method is not modelopt")
    require(str(quant.get("quant_algo", "")).upper() == "W4A16_NVFP4", "H6 config is not W4A16_NVFP4")

    print(
        "OrcaRouter hybrid chain is valid "
        f"(base={base.get('revision')}, overlay={h3.get('overlay_revision')}, final=h6-modelopt-w4a16)"
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-dir", type=Path, required=True)
    p.add_argument("--overlay-dir", type=Path)
    p.add_argument("--runtime-only", action="store_true")
    p.add_argument(
        "--through",
        choices=("h3", "h4", "h5", "h6"),
        default="h6",
        help="validate provenance through this generated stage",
    )
    p.add_argument("--h3-dir", type=Path, required=True)
    p.add_argument("--h4-dir", type=Path, required=True)
    p.add_argument("--h5-dir", type=Path, required=True)
    p.add_argument("--model-dir", type=Path, required=True)
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        validate(args)
    except HybridValidationError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
