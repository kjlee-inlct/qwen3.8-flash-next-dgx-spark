#!/usr/bin/env python3
"""Pinned lychee888 metadata-vs-repository FP8-PLE source gate (read-only).

This is NOT a runtime probe: it only fetches Hub JSON and examines the
version-controlled NVIDIA-specific patch. No tensor bodies, Docker, GPU or
local model directory are accessed, and no candidate can be admitted.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
from pathlib import Path
from typing import Any

from inspect_lychee888_metadata import (
    MetadataError, REPO, fetch_json, load_offline, validate,
)

REVISION = "1b3c3cedc14fb3bee4294dea5e3515af74b8268a"
ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / "scripts/patch-nv-mixed.py"
DOCKERFILE = ROOT / "scripts/Dockerfile.nv-mixed"

# The project patch uses ModelOptMixedPrecisionConfig and an exact per-prefix
# algorithm equality test. This is NOT a generic compressed-tensors resolver.
PATCH_MARKERS = (
    "ModelOptMixedPrecisionConfig",
    'quant_config._resolve_quant_algo(prefix) != "FP8"',
    "Qwen3_8FlashNextPLEFp8EmbeddingMethod()",
)


def fetch_pinned() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Only immutable revision-scoped JSON endpoints. Never resolve mutable HEAD."""
    endpoint = f"https://huggingface.co/api/models/{REPO}/revision/{REVISION}?blobs=true"
    api = fetch_json(endpoint)
    if api.get("sha") != REVISION:
        raise MetadataError("pinned lychee888 API SHA mismatch")
    base = f"https://huggingface.co/{REPO}/resolve/{REVISION}"
    return (
        api,
        fetch_json(f"{base}/config.json"),
        fetch_json(f"{base}/model.safetensors.index.json"),
    )


def assess(
    api: dict[str, Any], config: dict[str, Any], index: dict[str, Any],
    patch_source: str, dockerfile_source: str,
) -> dict[str, Any]:
    """Fail closed on unknown source state; a positive result is INSPECTION ONLY."""
    if api.get("sha") != REVISION:
        raise MetadataError("lychee888 pin differs from the approved immutable revision")
    l0 = validate(api, config, index)
    if not all(marker in patch_source for marker in PATCH_MARKERS):
        raise MetadataError("NVIDIA patch FP8-PLE source anchors absent or changed")
    if ("COPY patch-nv-mixed.py" not in dockerfile_source
            or "FROM vllm-skinny-tp1:v1" not in dockerfile_source):
        raise MetadataError("NVIDIA image patch integration changed; inspect manually")

    quant = config.get("quantization_config")
    if not isinstance(quant, dict):
        raise MetadataError("pinned config has no quantization_config object")
    method = quant.get("quant_method")
    if not isinstance(method, str) or not method.strip():
        raise MetadataError("pinned config quant_method missing; cannot compare loader")
    algorithm = quant.get("quant_algo")
    fmt = quant.get("format")
    if method == "modelopt_mixed":
        patch_match = "CLASS_ONLY; FP8 PLE PREFIX AND ACTUAL IMAGE UNVERIFIED"
    else:
        patch_match = "NOT_APPLICABLE; NVIDIA PATCH EXPECTS ModelOptMixedPrecisionConfig"

    return {
        "checkpoint": REPO,
        "immutable_revision": REVISION,
        "l0_verdict": l0["verdict"],
        "index_tensor_keys": l0["index_tensor_keys"],
        "ple_weight_shards": l0["ple_weight_shards"],
        "ple_files": l0["ple_files"],
        "global_weight_scale_keys": l0["global_weight_scale_keys"],
        "ple_embedding_dtype": l0["config_ple_embedding_dtype"],
        "quant_method": method,
        "quant_algo": algorithm if isinstance(algorithm, str) else None,
        "quant_format": fmt if isinstance(fmt, str) else None,
        "nvidia_patch_source_dispatch": patch_match,
        "external_recipe_requires": "PLE_QUANT_OVERRIDE=fp8 + adapted resolver",
        "managed_runtime_adapter": "NOT_IMPLEMENTED_OR_NOT_QUALIFIED",
        "single_gb10_tp1": "NOT_VERIFIED",
        "verdict": "SOURCE_ONLY_LOADER_UNQUALIFIED",
        "not_verified": [
            "the selected installed image's exact digest and loader code",
            "actual PLE FP8 method chosen for this checkpoint by pinned backend",
            "global BF16 PLE scale parameter registration, load and use",
            "safetensors tensor headers/dtypes and weight hashes",
            "single DGX Spark TP=1 functional readiness and safe peak memory",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline-dir", type=Path,
                        help="synthetic-only fixture: api.json config.json index.json")
    parser.add_argument("--json", action="store_true",
                        help="show all source findings in JSON, no tensor payloads")
    opts = parser.parse_args()
    try:
        docs = load_offline(opts.offline_dir) if opts.offline_dir else fetch_pinned()
        result = assess(
            *docs,
            PATCH.read_text(encoding="utf-8"),
            DOCKERFILE.read_text(encoding="utf-8"),
        )
    except (MetadataError, OSError, urllib.error.URLError, TimeoutError) as exc:
        print(f"LYCHEE888_SOURCE_GATE_FAIL: {exc}", file=sys.stderr)
        return 2

    if opts.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        for name in (
            "immutable_revision", "l0_verdict", "index_tensor_keys",
            "ple_weight_shards", "ple_files", "global_weight_scale_keys",
            "ple_embedding_dtype", "quant_method", "quant_algo", "quant_format",
            "nvidia_patch_source_dispatch", "managed_runtime_adapter",
            "single_gb10_tp1", "verdict",
        ):
            print(f"{name}={result[name]}")
        print("MODEL_PAYLOAD_DOWNLOADED=NO")
        print("GPU_RUN=NOT_PERFORMED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
