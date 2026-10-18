#!/usr/bin/env python3
"""catplusplus M1 session contract, matching the mazinb M1 Wizard workflow.

SOURCE-ONLY/READ-ONLY SCAFFOLD. Unlike the physically measured mazinb M1,
catplusplus has NO qualified GB10 mixed-MXFP8+NVFP4/FP8-PLE loader,
checkpoint install, bounded weight offload, protected live controller or
GPU-load approval. Preflight, run and benchmark admission FAIL CLOSED.
This is deliberately NOT a modified copy of mazinb's runnable Docker M1.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
PLAN_FILE = ROOT / "scripts" / "benchmark" / "catplusplus-plan.py"
SPEC = importlib.util.spec_from_file_location("catplusplus_plan", PLAN_FILE)
assert SPEC is not None and SPEC.loader is not None
PLAN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PLAN)

MODEL = PLAN.MODEL
REVISION = PLAN.PINNED_REVISION
SESSION_ID = "catplusplus-m1"
SOURCE_AUDIT_FILE = ROOT / "scripts" / "model" / "audit_catplusplus_loader_source.py"
PROPOSED_PORT = 18892  # Never bind/publish this during an M0 source gate.
PHASES = (
    "candidate_qualified", "created", "armed", "started_unqualified",
    "soaking", "ready_for_bench", "stopping", "stopped",
    "failed_stopped", "recovery_required",
)
# mazinb M1 shape, not inherited authorization or a known-working loader.
GATES = (
    ("CHECKPOINT", "BLOCKED_NOT_DOWNLOADED_OR_HASH_ATTESTED"),
    ("ENGINE", "BLOCKED_NO_PINNED_GB10_IMAGE"),
    ("MIXED_LOADER", "BLOCKED_MXFP8_QKVZ_AND_SCALE_NOT_VERIFIED"),
    ("FP8_PLE", "BLOCKED_OFFLOAD_RESIDENCY_NOT_QUALIFIED"),
    ("MEMORY_RM", "BLOCKED_PEAK_GPU_RM_AND_NONCMA_BUDGET_NOT_QUALIFIED"),
    ("PROTECTED_SESSION", "BLOCKED_CREATE_ONLY_EXACT_ID_WATCHDOG_NOT_IMPLEMENTED"),
    ("OWNER_APPROVAL", "BLOCKED_NO_CATPLUSPLUS_LIVE_AUTHORIZATION"),
)
STEPS = (
    "01 READ_ONLY_PREFLIGHT",
    "02 EXACT_PROTECTED_OLD_IDENTITY_AND_LIFECYCLE_LOCK",
    "03 UNIQUE_CANDIDATE_DOCKER_CREATE_ONLY",
    "04 PERSIST_EXACT_ID_AND_ARM_WATCHDOG_BEFORE_START",
    "05 EXACT_ID_START_AND_WATCHDOG_HEARTBEAT",
    "06 EXACT_MODEL_API_READY",
    "07 POST_READY_180_SECOND_SOAK",
    "08 INFERENCE_SMOKE_AND_RM_AUDIT",
    "09 TERMINAL_B_BENCH_ADMISSION_WITH_LEASE",
    "10 LLAMA_BENCHY_C1_PP512_2048_TG128_WARMUP1_RUNS3",
    "11 FOREGROUND_EXPLICIT_STOP_EXACT_ID",
    "12 PRESERVE_RAW_JSON_KERNEL_MEMORY_AND_DOCKER_EVIDENCE",
)


class M1Blocked(ValueError):
    pass


def state_file() -> Path:
    home = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
    return home / "qwen38-spark" / SESSION_ID / "active.json"


def read_journal() -> dict[str, object] | None:
    """Never follow untrusted symlinks or execute persisted content."""
    path = state_file()
    if not path.exists() and not path.is_symlink():
        return None
    for item in (path.parent.parent, path.parent, path):
        if item.is_symlink():
            raise M1Blocked("journal path is a symlink")
    if not path.is_file() or path.stat().st_uid != os.getuid():
        raise M1Blocked("untrusted journal owner/type")
    if path.stat().st_size > 256 * 1024:
        raise M1Blocked("untrusted oversized journal")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise M1Blocked("invalid journal JSON object")
    if (value.get("schema") != 1 or value.get("model") != MODEL or
            value.get("revision") != REVISION or
            value.get("phase") not in PHASES):
        raise M1Blocked("journal identity/schema/phase mismatch")
    # The future actual runtime has NOT been implemented. A journal
    # cannot be promoted to READY merely by editing a JSON file.
    return value


def plan() -> int:
    print(PLAN.render(PLAN.build_plan()))
    print("CATPLUSPLUS_M1_WORKFLOW=MAZINB_M1_PARITY_SOURCE_CONTRACT")
    print("CATPLUSPLUS_M1_PROPOSED_PORT=127.0.0.1:" + str(PROPOSED_PORT))
    print("CATPLUSPLUS_M1_PORT_STATUS=NOT_RESERVED")
    print("CATPLUSPLUS_M1_SOURCE_MODEL=" + MODEL)
    print("CATPLUSPLUS_M1_SOURCE_REVISION=" + REVISION)
    print("CATPLUSPLUS_M1_KV16G=PROPOSED_UNQUALIFIED")
    print("CATPLUSPLUS_M1_LOADER=NOT_SELECTED")
    print("CATPLUSPLUS_M1_STAGE_COUNT=" + str(len(STEPS)))
    for step in STEPS:
        print("CATPLUSPLUS_M1_STAGE=" + step)
    print("CATPLUSPLUS_M1_START_CONTROLLER=NOT_IMPLEMENTED")
    print("CATPLUSPLUS_M1_BENCHMARK=NOT_MEASURED")
    print("CATPLUSPLUS_M1_PROTECTED_MANAGED_AB=MANDATORY")
    return 0


def status() -> int:
    journal = read_journal()
    if journal is None:
        print("CATPLUSPLUS_M1_SESSION=ABSENT")
    else:
        print("CATPLUSPLUS_M1_SESSION=JOURNAL_UNATTESTED")
        print("CATPLUSPLUS_M1_SESSION_PHASE=" + str(journal["phase"]))
        print("CATPLUSPLUS_M1_SESSION_DOCKER_ID=NOT_ATTESTED_BY_THIS_CONTROLLER")
    print("CATPLUSPLUS_M1_LIVE_READY=NOT_QUALIFIED")
    print("CATPLUSPLUS_M1_BENCHMARK=NOT_MEASURED")
    print("CATPLUSPLUS_M1_DOCKER_ACTION=NONE")
    return 0


def preflight() -> int:
    """Static compatibility/readiness gate; NO Docker or host mutation."""
    print("CATPLUSPLUS_M1_OPERATION=SOURCE_ONLY_READ_ONLY_PREFLIGHT")
    print("CATPLUSPLUS_M1_PRECHECK=MAZINB_M1_SAFETY_SEQUENCE_DEFINED")
    print("CATPLUSPLUS_M1_CHECKPOINT_REVISION=" + REVISION)
    for name, value in GATES:
        print("CATPLUSPLUS_M1_GATE_" + name + "=" + value)
    journal = read_journal()
    if journal is not None:
        print("CATPLUSPLUS_M1_JOURNAL=EXISTS_REVIEW_REQUIRED")
    else:
        print("CATPLUSPLUS_M1_JOURNAL=ABSENT")
    print("CATPLUSPLUS_M1_ADMISSION=BLOCKED_COMPATIBILITY_MEMORY_AND_LIVE_AUTHORIZATION")
    print("CATPLUSPLUS_M1_DOCKER_GPU_MODEL_DOWNLOAD=NOT_PERFORMED")
    return 2


def blocked(action: str) -> int:
    if action == "run":
        marker = "NOT_IMPLEMENTED_OR_AUTHORIZED"
        print("CATPLUSPLUS_M1_LIVE_START=" + marker)
        print("CATPLUSPLUS_M1_WATCHDOG=NOT_ARMED")
    elif action == "bench-admission":
        print("CATPLUSPLUS_M1_BENCH_ADMISSION=BLOCKED_NOT_READY_EXACT_ID_MONITORED")
    elif action == "reconcile":
        journal = read_journal()
        if journal is None:
            print("CATPLUSPLUS_M1_RECONCILE=NO_SESSION_OR_JOURNAL")
            print("CATPLUSPLUS_M1_DOCKER_ACTION=NONE")
            return 0
        print("CATPLUSPLUS_M1_RECONCILE=BLOCKED_MANUAL_FORENSIC_REVIEW")
    print("CATPLUSPLUS_M1_DOCKER_ACTION=NONE")
    print("CATPLUSPLUS_M1_BENCHMARK=NOT_MEASURED")
    return 2


def source_audit(offline_dir: Path | None) -> int:
    """Optional pinned small-text source gate; never imports/executes loader."""
    spec = importlib.util.spec_from_file_location(
        "catplusplus_source_audit", SOURCE_AUDIT_FILE)
    if spec is None or spec.loader is None:
        raise M1Blocked("pinned source audit module missing")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.audit(offline_dir)
    print("CATPLUSPLUS_M1_SOURCE_REVISION=" + str(report["revision"]))
    print("CATPLUSPLUS_M1_SOURCE_TRANSPORT=" + str(report["transport"]))
    print("CATPLUSPLUS_M1_SOURCE_CONFIG_SHA256=" + report["config_sha256"])
    print("CATPLUSPLUS_M1_SOURCE_LAUNCHER_SHA256=" + report["launcher_sha256"])
    print("CATPLUSPLUS_M1_SOURCE_DECLARATIONS=" + report["source_declarations"])
    print("CATPLUSPLUS_M1_FUSED_QKVZ_ALIAS_COUNT=" +
          str(report["config"]["fused_qkvz_quantized_alias_count"]))
    for hazard, value in report["publisher_launcher"]["script_operational_hazards"].items():
        print("CATPLUSPLUS_M1_PUBLISHER_LAUNCH_HAZARD_" + hazard.upper() +
              "=" + ("PRESENT_DO_NOT_EXECUTE" if value else "NOT_DETECTED"))
    print("CATPLUSPLUS_M1_ENGINE_LOADER=NOT_ATTESTED_BY_SOURCE_TEXT")
    print("CATPLUSPLUS_M1_LIVE_ADMISSION=" + report["live_admission"])
    print("CATPLUSPLUS_M1_DOCKER_GPU_MODEL_DOWNLOAD=NOT_PERFORMED")
    return 0 if report["source_declarations"] == "PRESENT_NOT_ENGINE_ATTESTED" else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=(
        "plan", "status", "preflight", "run", "bench-admission", "reconcile",
        "source-audit",
    ))
    parser.add_argument("--offline-dir", type=Path,
                        help="only with source-audit; offline fixtures")
    args = parser.parse_args()
    try:
        if args.action == "source-audit":
            return source_audit(args.offline_dir)
        if args.offline_dir is not None:
            raise M1Blocked("--offline-dir is only permitted for source-audit")
        if args.action == "plan":
            return plan()
        if args.action == "status":
            return status()
        if args.action == "preflight":
            return preflight()
        return blocked(args.action)
    except (M1Blocked, OSError, ValueError, json.JSONDecodeError) as exc:
        print("CATPLUSPLUS_M1_BLOCKED=" + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
