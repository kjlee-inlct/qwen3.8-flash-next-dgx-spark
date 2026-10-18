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
# Actual DGX one-time approved, unstarted/no-mount image-source extraction.
# THESE ARE ATTESTED STATIC RECEIPTS, NOT THE IMAGE'S REPRODUCED SOURCE BYTES.
# Never infer loader execution, checkpoint tensor dtype, or TP=1 support.
INSTALLED_IMAGE_ID = (
    "sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4"
)
INSTALLED_PLE_PATH = (
    "/usr/local/lib/python3.12/dist-packages/"
    "vllm/models/qwen3_8_flash_next/nvidia/ple_layer.py"
)
INSTALLED_PLE_SHA256 = (
    "a71144c1d36e06f22a2da1b1ada900076597fe5e824a911e7ada86249a0993e7"
)
INSTALLED_PLE_ROUTE = "NATIVE_FP8_CONFIG_ONLY_SOURCE"
ACTUAL_DGX_POSTCHECK = "PASS_CURRENT_ONLY_HISTORICAL_FAIL_REVIEW_RETAINED"
# NVIDIA documented nominal DGX Spark 128 GB *unified* system memory.
# Decimal bytes, NOT a claim of current MemAvailable or allocatable VRAM.
DGX_SPARK_NOMINAL_UNIFIED_BYTES = 128_000_000_000
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


def installed_ple_dispatch_contract(config: dict[str, Any]) -> dict[str, str]:
    """Fail-closed static dispatch assessment, using an ACTUAL_DGX source receipt.

    The real image-source bytes were NOT retained, only its SHA and source
    classifier. Do not conflate the model's top-level quantization format
    with the class instantiated by the installed vLLM runtime.
    """
    quant = config.get("quantization_config")
    if not isinstance(quant, dict):
        raise MetadataError("missing quantization_config for installed source contract")
    method = quant.get("quant_method")
    fmt = quant.get("format")
    if not isinstance(method, str) or not method.strip():
        raise MetadataError("quant_method absent from installed source contract")
    if method == "compressed-tensors" and fmt == "mixed-precision":
        declaration = "COMPRESSED_TENSORS_MIXED_PRECISION_CONFIRMED_IN_METADATA"
        expected_class = "COMPRESSED_TENSORS_CLASS_EXPECTED_NOT_RUNTIME_ATTESTED"
        native_gate = "NO_DIRECT_NATIVE_FP8_CLASS_MATCH_PROVEN"
        scale = "FP8_METHOD_CONDITIONAL_ONLY_BF16_SCALE_LOAD_UNVERIFIED"
    elif method == "compressed-tensors":
        declaration = "COMPRESSED_TENSORS_FORMAT_NOT_CONFIRMED_AS_MIXED_PRECISION"
        expected_class = "COMPRESSED_TENSORS_CLASS_EXPECTED_NOT_RUNTIME_ATTESTED"
        native_gate = "NO_DIRECT_NATIVE_FP8_CLASS_MATCH_PROVEN"
        scale = "FP8_METHOD_CONDITIONAL_ONLY_BF16_SCALE_LOAD_UNVERIFIED"
    elif method == "modelopt_mixed":
        declaration = "MODELOPT_MIXED_DECLARATION"
        expected_class = "MODELOPT_MIXED_CLASS_EXPECTED_NOT_RUNTIME_ATTESTED"
        native_gate = "NATIVE_FP8_GATE_NOT_A_MODELOPT_MIXED_ROUTE"
        scale = "FP8_METHOD_CONDITIONAL_ONLY_BF16_SCALE_LOAD_UNVERIFIED"
    else:
        declaration = "OTHER_QUANT_DECLARATION_UNQUALIFIED"
        expected_class = "UNKNOWN_RUNTIME_QUANT_CLASS"
        native_gate = "UNRESOLVED"
        scale = "BF16_SCALE_LOAD_UNVERIFIED"

    return {
        "installed_image_id": INSTALLED_IMAGE_ID,
        "installed_ple_source_path": INSTALLED_PLE_PATH,
        "installed_ple_source_sha256": INSTALLED_PLE_SHA256,
        "installed_ple_source_dispatch": INSTALLED_PLE_ROUTE,
        "installed_source_evidence": "ACTUAL_DGX_SHA_AND_STATIC_AST_ONLY_NOT_FULL_SOURCE_ARCHIVE",
        "physical_protected_postcheck": ACTUAL_DGX_POSTCHECK,
        "quant_declared_format_class": declaration,
        "runtime_quant_class_expectation": expected_class,
        "installed_native_gate_reachability": native_gate,
        "bf16_global_scale_loader_gate": scale,
        "ple_dtype_dispatch": "NOT_PROVEN_IN_INSTALLED_SOURCE",
        "ct_prefix_scheme_resolution": "NOT_AUDITED_FOR_INSTALLED_IMAGE",
        "installed_loader_contract": "BLOCKED_SOURCE_ONLY_UNQUALIFIED",
    }


def nominal_full_resident_size_screen(index: dict[str, Any]) -> dict[str, Any]:
    """Necessary size comparison only, never a runtime peak-memory model.

    The safetensors index metadata total_size is file-side tensor bytes,
    not a validated sum of actual resident pages, CUDA allocations, cache
    or disk-mmap/offload behavior. Missing and malformed values fail closed.
    """
    meta = index.get("metadata")
    raw = meta.get("total_size") if isinstance(meta, dict) else None
    if not isinstance(raw, int) or isinstance(raw, bool) or raw <= 0:
        return {
            "indexed_tensor_bytes": None,
            "dgx_spark_nominal_unified_bytes": DGX_SPARK_NOMINAL_UNIFIED_BYTES,
            "full_resident_nominal_memory_screen": "NOT_VERIFIED_INDEX_TOTAL_SIZE_MISSING",
            "runtime_peak_memory": "NOT_MEASURED",
        }
    verdict = (
        "INDEXED_TENSOR_BYTES_EXCEED_NOMINAL_UNIFIED_MEMORY"
        if raw > DGX_SPARK_NOMINAL_UNIFIED_BYTES
        else "INDEXED_TENSOR_BYTES_WITHIN_NOMINAL_ONLY_NO_HEADROOM_PROOF"
    )
    return {
        "indexed_tensor_bytes": raw,
        "dgx_spark_nominal_unified_bytes": DGX_SPARK_NOMINAL_UNIFIED_BYTES,
        "full_resident_nominal_memory_screen": verdict,
        "runtime_peak_memory": "NOT_MEASURED",
    }


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

    installed_gate = installed_ple_dispatch_contract(config)
    memory_screen = nominal_full_resident_size_screen(index)
    return {
        "checkpoint": REPO,
        "immutable_revision": REVISION,
        **installed_gate,
        **memory_screen,
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
            "full installed PLE source bytes were not archived; physical SHA/AST signature only",
            "the exact vLLM quantization class and FP8 PLE method instantiated for lychee888",
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
            "nvidia_patch_source_dispatch", "installed_image_id",
            "installed_ple_source_sha256", "installed_ple_source_dispatch",
            "quant_declared_format_class", "runtime_quant_class_expectation",
            "installed_native_gate_reachability", "bf16_global_scale_loader_gate",
            "ple_dtype_dispatch", "ct_prefix_scheme_resolution",
            "installed_loader_contract", "indexed_tensor_bytes",
            "dgx_spark_nominal_unified_bytes",
            "full_resident_nominal_memory_screen", "runtime_peak_memory",
            "managed_runtime_adapter",
            "single_gb10_tp1", "verdict",
        ):
            print(f"{name}={result[name]}")
        print("MODEL_PAYLOAD_DOWNLOADED=NO")
        print("GPU_RUN=NOT_PERFORMED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
