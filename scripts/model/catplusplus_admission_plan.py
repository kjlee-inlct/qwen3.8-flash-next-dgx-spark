#!/usr/bin/env python3
"""No-download catplusplus installation/runtime/benchmark admission planning.

Does not fetch Hugging Face content, run Docker, load GPU or mutate host.
Source model dimensions are from the historical pinned DGX metadata report.
This script never authorizes starting or downloading a checkpoint.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import sys

MODEL = "catplusplus/Qwen3.8-Flash-Next-uncensored-NVFP4-mixed"
REVISION = "3251fd8afbd08f76368a9bfa71132d9aef364813"
ROOT_SAFETENSORS_GIB_APPROX = 174.8553  # rounded DGX pinned-tree measurement
COMPLETE_REPOSITORY_BYTES = 188_540_029_444  # verified DGX pinned-tree
PLE_FP8_GIB_PUBLISHER_APPROX = 47.7  # publisher, NOT pinned tensor header measurement
NOMINAL_GB10_RAM_DECIMAL_BYTES = 128_000_000_000
GIB = 1024 ** 3
MIN_FREE_DISK_RESERVE_BYTES = 20 * GIB
BENCHY_SOURCE_SHA = "e9be344578cec17745066b220798b80a0d2686d3"
MODEL_SLUG = "qwen3.8-flash-next-catplusplus-mixed"
PORT = 18892


class GateBlocked(ValueError):
    pass


def data() -> dict:
    ram_gib = NOMINAL_GB10_RAM_DECIMAL_BYTES / GIB
    after_offload_approx = ROOT_SAFETENSORS_GIB_APPROX - PLE_FP8_GIB_PUBLISHER_APPROX
    # Only numerical planning using raw stored bytes, not projected allocations.
    return {
        "model": MODEL,
        "revision": REVISION,
        "pinned_dgx_repository_bytes": COMPLETE_REPOSITORY_BYTES,
        "root_weight_gib_rounded": ROOT_SAFETENSORS_GIB_APPROX,
        "fp8_ple_gib_publisher_estimate": PLE_FP8_GIB_PUBLISHER_APPROX,
        "optimistic_stored_weight_gib_after_ple_subtraction": round(after_offload_approx, 4),
        "nominal_unified_memory_gib": round(ram_gib, 4),
        "storage_reserve_gib": MIN_FREE_DISK_RESERVE_BYTES // GIB,
        "requested_install_path_name": MODEL_SLUG,
        "proposed_loopback_port": PORT,
        "source_gate": "PINNED_RAW_GET_AUDIT_REQUIRED",
        "engine_gate": "BLOCKED_NO_PINNED_GB10_SGLANG_WHEEL_OR_IMAGE",
        "mixed_fused_qkvz_gate": "BLOCKED_NO_ACTUAL_MXFP8_SCALE_CONSUMPTION_PROOF",
        "fp8_ple_gate": "BLOCKED_NO_MEASURED_GB10_OFFLOAD_RESIDENCY",
        "peak_rm_gate": "BLOCKED_NO_BOUND_PEAK_ALLOCATIONS",
        "checkpoint_gate": "BLOCKED_NOT_DOWNLOADED_OR_SHA256_VERIFIED",
        "download_gate": "BLOCKED_WHILE_MAZINB_IS_DOWNLOADING_AND_UNTIL_SEPARATE_APPROVAL",
        "gpu_gate": "BLOCKED_NO_PROTECTED_CATPLUSPLUS_CONTROLLER_OR_APPROVAL",
        "service_gate": "BLOCKED_NO_GB10_API_AND_SAFETY_SOAK",
        "benchmark_gate": "BLOCKED_UNTIL_EXACT_MODEL_API_READY_AND_WATCHDOG",
        "benchmark_shape": "PP512_2048_TG128_C1_DEPTH0_WARMUP1_RUNS3",
        "benchmark_source_sha": BENCHY_SOURCE_SHA,
        "status": "PREPARATION_SOURCE_ONLY_NO_HOST_ACTION",
        "live_admission": False,
    }


def plan() -> int:
    p = data()
    for key, value in p.items():
        print(f"CATPLUSPLUS_PREP_{key.upper()}={value}")
    print("CATPLUSPLUS_PREP_HOST_MUTATION=NONE")
    print("CATPLUSPLUS_PREP_WEIGHT_DOWNLOAD=NOT_PERFORMED")
    return 0


def host_readonly() -> int:
    """Observe *existing* lifecycle lock before disk probe; never create it."""
    lock = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
    lock = lock / "qwen38-spark" / "operation.lock"
    if not (lock.is_file() and not lock.is_symlink() and
            lock.stat().st_uid == os.getuid()):
        raise GateBlocked("HOST_LIFECYCLE_LOCK_MISSING_OR_UNSAFE")
    with lock.open("rb") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise GateBlocked("HOST_LIFECYCLE_BUSY_MAZINB_DOWNLOAD_MAY_BE_ACTIVE") from exc
        # Must use the existing project checkout and a confirmed *directory*.
        root = Path(__file__).resolve().parents[2]
        models = root / "models"
        if models.is_symlink() or not models.is_dir():
            raise GateBlocked("HOST_MODEL_STORAGE_ROOT_UNSAFE_OR_ABSENT")
        target = models / MODEL_SLUG
        if target.is_symlink() or target.exists():
            raise GateBlocked("HOST_TARGET_EXISTS_OR_SYMLINK_REVIEW_MANUALLY")
        free = shutil.disk_usage(models).free
        # Conservative full-repo budget: metadata inventory is not a minimal
        # inference download manifest, do not call it an installation pass.
        need = COMPLETE_REPOSITORY_BYTES + MIN_FREE_DISK_RESERVE_BYTES
        print(f"CATPLUSPLUS_PREP_HOST_FREE_BYTES={free}")
        print(f"CATPLUSPLUS_PREP_HOST_FULL_REPOSITORY_PLUS_RESERVE_BYTES={need}")
        print("CATPLUSPLUS_PREP_HOST_CHECKPOINT_BYTES=NOT_READ")
        print("CATPLUSPLUS_PREP_HOST_DOCKER_GPU_API_ACTION=NONE")
        if free < need:
            raise GateBlocked("HOST_DISK_BELOW_FULL_REPO_PLUS_RESERVE")
        print("CATPLUSPLUS_PREP_HOST_DISK_SCREEN=PASS_ESTIMATE_ONLY_NOT_INSTALL_ADMISSION")
    print("CATPLUSPLUS_PREP_HOST_SOURCE_ENGINE_MEMORY_GATES=STILL_BLOCKED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "disk-check"))
    args = parser.parse_args()
    try:
        return plan() if args.action == "plan" else host_readonly()
    except (GateBlocked, OSError, ValueError) as exc:
        print("CATPLUSPLUS_PREP_BLOCKED=" + str(exc), file=sys.stderr)
        print("CATPLUSPLUS_PREP_DOWNLOAD_DOCKER_GPU_SERVICE=NOT_PERFORMED")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
