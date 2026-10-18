#!/usr/bin/env python3
"""Source-only catplusplus benchmark plan for the operator Wizard.

NO downloads, GPU work, Docker commands, service changes or API requests.
A planned benchmark is *not* a readiness, memory-admission or measurement.
"""
from __future__ import annotations

import argparse
import json

MODEL = "catplusplus/Qwen3.8-Flash-Next-uncensored-NVFP4-mixed"
PINNED_REVISION = "3251fd8afbd08f76368a9bfa71132d9aef364813"
UPSTREAM_BENCHY_SHA = "e9be344578cec17745066b220798b80a0d2686d3"
# ACTUAL_DGX metadata inventory captured on 2026-10-16, not weights
# fetched locally, physical residency, or memory usage.
PINNED_REPOSITORY_BYTES = 188_540_029_444
PINNED_ROOT_WEIGHTS_GIB_ROUNDED = 174.8553
DGX_SPARK_UNIFIED_RAM_DECIMAL_BYTES = 128_000_000_000
GIB = 1024 ** 3


def build_plan() -> dict[str, object]:
    return {
        "plan_version": 1,
        "operation": "SOURCE_ONLY_BENCHMARK_PLAN",
        "checkpoint": MODEL,
        "checkpoint_revision": PINNED_REVISION,
        "checkpoint_registry_status": "RESEARCH_ONLY_NOT_INSTALLABLE",
        "metadata_evidence": "ACTUAL_DGX_PINNED_L0_TREE_METADATA_COMPLETE_20261016",
        "repository_size_bytes": PINNED_REPOSITORY_BYTES,
        "root_weight_size_gib_rounded": PINNED_ROOT_WEIGHTS_GIB_ROUNDED,
        "host_unified_ram_bytes_nominal": DGX_SPARK_UNIFIED_RAM_DECIMAL_BYTES,
        "full_residency_without_offload": "EXCEEDS_NOMINAL_SINGLE_GB10_RAM",
        "loading_with_offload": "NOT_QUALIFIED",
        "benchmark_tool": "llama-benchy",
        "benchmark_tool_source_sha": UPSTREAM_BENCHY_SHA,
        "warmup_runs": 1,
        "measured_runs": 3,
        "concurrency": 1,
        "context_size": 0,
        "prefix_caching": "DISABLED_BASELINE",
        "latency_mode": "generation",
        "workloads": [
            {"prompt_tokens": 512, "generate_tokens": 128},
            {"prompt_tokens": 2048, "generate_tokens": 128},
        ],
        "must_verify_before_live": [
            "exact approved pinned safetensors and minimal loader assets",
            "fused qkvz MXFP8 scale mapping and ModelOpt mixed NVFP4 support",
            "FP8 PLE implementation and partial residency/offload design",
            "single GB10 memory/swap/RM allocation safety under monitor",
            "independent named container/create-only watchdog-before-start",
            "exact model identity, API READY and functional inference",
            "separate owner approval for checkpoint download and GPU start",
        ],
        "measurements": None,
        "benchmark_status": "NOT_MEASURED",
        "ready": False,
        "admission": "BLOCKED_MODEL_LOADER_MEMORY_AND_LIVE_AUTHORIZATION",
        "permitted_by_this_plan": "SOURCE_READ_ONLY_NO_HOST_CHANGE",
    }


def render(plan: dict[str, object]) -> str:
    out = [
        "CATPLUSPLUS_OPERATION=" + str(plan["operation"]),
        "CATPLUSPLUS_MODEL=" + str(plan["checkpoint"]),
        "CATPLUSPLUS_PINNED_REVISION=" + str(plan["checkpoint_revision"]),
        "CATPLUSPLUS_METADATA=" + str(plan["metadata_evidence"]),
        "CATPLUSPLUS_REPOSITORY_BYTES=" + str(plan["repository_size_bytes"]),
        "CATPLUSPLUS_ROOT_WEIGHTS_GIB_ROUNDED=" +
        str(plan["root_weight_size_gib_rounded"]),
        "CATPLUSPLUS_FULL_RESIDENCY=EXCEEDS_NOMINAL_SINGLE_GB10_RAM",
        "CATPLUSPLUS_BENCHY_SHA=" + str(plan["benchmark_tool_source_sha"]),
        "CATPLUSPLUS_BASELINE=PP512_TG128_AND_PP2048_TG128_C1_WARMUP1_MEASURED3",
        "CATPLUSPLUS_RUNTIME_LOADER=NOT_QUALIFIED",
        "CATPLUSPLUS_API_READY=NOT_MEASURED",
        "CATPLUSPLUS_BENCHMARK_STATUS=NOT_MEASURED",
        "CATPLUSPLUS_ADMISSION=" + str(plan["admission"]),
        "CATPLUSPLUS_DOCKER_GPU_DOWNLOAD=NOT_PERFORMED",
    ]
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan",))
    parser.add_argument("--json", action="store_true",
                        help="Print a plan object; measurements remain null")
    args = parser.parse_args()
    plan = build_plan()
    if args.json:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
    else:
        print(render(plan))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
