#!/usr/bin/env python3
"""Hybrid H6 read-only launch admission. NEVER starts a model."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/lib"))
from state_file import parse_install  # noqa: E402

STAGES = ("qwen3.8-flash-next-orcarouter", "qwen3.8-hybrid-quant-layout",
          "qwen3.8-h4-orca-all", "qwen3.8-h5-neutral-input-scale",
          "qwen3.8-h6-modelopt-w4a16")


class Blocked(Exception):
    pass


def run(*argv: str) -> str:
    p = subprocess.run(argv, text=True, capture_output=True,
                       check=False, timeout=120)
    if p.returncode:
        raise Blocked(f"read_only_command_failed:{Path(argv[0]).name}:{p.returncode}")
    return p.stdout.strip()


def blockers(manifest: dict[str, str]) -> list[str]:
    issues = []
    if manifest.get("PHASE") != "complete":
        issues.append("INSTALL_NOT_COMPLETE")
    if manifest.get("MODEL_PROFILE") != "orcarouter":
        issues.append("UNEXPECTED_CURRENT_PROFILE")
    if manifest.get("SERVICE_ENABLED") != "1" or manifest.get("SERVICE_OWNED") != "1":
        issues.append("MANAGED_PROFILE_SWITCH_REQUIRES_ENABLED_OWNED_SERVICE")
    if manifest.get("MONITOR_ENABLED") != "1" or manifest.get("MONITOR_PROTECT") != "1":
        issues.append("PROTECTED_MONITOR_NOT_CONFIGURED")
    if manifest.get("MONITOR_HEARTBEAT") in (None, "", "0"):
        issues.append("MONITOR_HEARTBEAT_DISABLED")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--models-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        if not re.fullmatch(r"[0-9a-f]{40}", args.expected_sha):
            raise Blocked("exact_source_sha_required")
        directory = args.models_root
        if not directory.is_absolute() or directory.is_symlink() or not directory.is_dir():
            raise Blocked("absolute_non_symlink_models_root_required")
        root = directory.resolve(strict=True)
        if run("git", "-C", str(ROOT), "rev-parse", "HEAD") != args.expected_sha or run(
                "git", "-C", str(ROOT), "status", "--porcelain=v1", "--untracked-files=all"):
            raise Blocked("source_sha_mismatch_or_dirty")
        for name in STAGES:
            path = root / name
            if not path.is_dir() or path.is_symlink():
                raise Blocked("stage_missing_or_symlinked:" + name)
        state = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
        manifest_file = state / "qwen38-spark/install.env"
        if manifest_file.is_symlink() or not manifest_file.is_file():
            raise Blocked("unsafe_or_missing_install_manifest")
        original_hash = hashlib.sha256(manifest_file.read_bytes()).hexdigest()
        manifest = parse_install(manifest_file, "install-maintenance")
        print("HYBRID_H6_LAUNCH_ADMISSION=BEGIN")
        print("SOURCE_SHA=" + args.expected_sha)
        print("MANIFEST_SHA256=" + original_hash)
        for key in ("MODEL_PROFILE", "PHASE", "SERVICE_ENABLED", "SERVICE_OWNED",
                    "MONITOR_ENABLED", "MONITOR_PROTECT", "MONITOR_HEARTBEAT"):
            print("INSTALLED_" + key + "=" + manifest.get(key, "ABSENT"))
        print("=== MANAGED HOST IDLE ===")
        print(run("python3", "-B", str(ROOT / "scripts/diagnostics/verify-managed-idle.py")))
        print("=== H3-H6 RUNTIME-ONLY CHAIN VALIDATION ===")
        print(run("python3", "-B", str(ROOT / "scripts/model/validate-orcarouter-hybrid.py"),
                  "--runtime-only", "--base-dir", str(root / STAGES[0]),
                  "--h3-dir", str(root / STAGES[1]), "--h4-dir", str(root / STAGES[2]),
                  "--h5-dir", str(root / STAGES[3]), "--model-dir", str(root / STAGES[4])))
        state_line = run(
            "docker", "inspect", "--format",
            "{{.Id}}|{{.State.Status}}|{{.State.Running}}|{{.State.OOMKilled}}",
            "qwen38-flash-next",
        ).split("|")
        if len(state_line) != 4 or not re.fullmatch(r"[0-9a-f]{64}", state_line[0]):
            raise Blocked("invalid_canonical_predecessor_identity")
        if state_line[1:] != ["exited", "false", "false"]:
            raise Blocked("canonical_predecessor_not_stopped_non_oom")
        print("CANONICAL_PREDECESSOR_DOCKER_ID=" + state_line[0])
        issues = blockers(manifest)
        if hashlib.sha256(manifest_file.read_bytes()).hexdigest() != original_hash:
            raise Blocked("manifest_changed_during_readonly_probe")
        if run("git", "-C", str(ROOT), "rev-parse", "HEAD") != args.expected_sha or run(
                "git", "-C", str(ROOT), "status", "--porcelain=v1", "--untracked-files=all"):
            raise Blocked("source_changed_during_readonly_probe")
        for issue in issues:
            print("HYBRID_H6_LAUNCH_BLOCKER=" + issue)
        print("HOST_MUTATION=NO")
        print("HYBRID_H6_MODEL_START=NOT_PERFORMED")
        print("HYBRID_H6_BENCHMARK=NOT_MEASURED")
        print("HYBRID_STAGE_DELETION_AUTHORIZED=NO")
        if issues:
            print("HYBRID_H6_LAUNCH_ADMISSION=BLOCKED_PENDING_SAFE_CONTROLLER")
            return 3
        print("HYBRID_H6_LAUNCH_ADMISSION=REVIEW_ONLY_NOT_LIVE_AUTHORIZATION")
        return 0
    except (Blocked, OSError, ValueError, subprocess.SubprocessError) as exc:
        print("HYBRID_H6_LAUNCH_ADMISSION=INVALID reason=" + str(exc), file=sys.stderr)
        print("HYBRID_H6_MODEL_START=NOT_PERFORMED", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
