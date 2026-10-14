#!/usr/bin/env python3
"""Read-only Hybrid H3-H6 dependency audit. It NEVER authorizes deletion."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
STAGES = {
    "h3": "qwen3.8-hybrid-quant-layout",
    "h4": "qwen3.8-h4-orca-all",
    "h5": "qwen3.8-h5-neutral-input-scale",
    "h6": "qwen3.8-h6-modelopt-w4a16",
}
DEPENDENCY_PROFILES = {
    "h3": "hybrid-quant-layout",
    "h4": "hybrid-h4-all",
    "h5": "hybrid-h5-neutral-input",
    "h6": "hybrid-h6-w4a16",
}
STAGE_PROFILES = set(DEPENDENCY_PROFILES.values())
SHA = re.compile(r"^[0-9a-f]{40}$")
DOCKER_ID = re.compile(r"^[0-9a-f]{64}$")


class Blocked(Exception):
    pass


def command(*args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        list(args), text=True, capture_output=True, check=False, env=env,
    )
    if result.returncode:
        raise Blocked(f"command_failed:{Path(args[0]).name}:{result.returncode}")
    return result.stdout.strip()


def match_mount_source(raw: str, root: Path) -> tuple[str, str] | None:
    if not isinstance(raw, str) or not raw.startswith("/"):
        return None
    path = Path(raw)
    for stage, name in STAGES.items():
        if name not in path.parts:
            continue
        candidate = root / name
        resolved = Path(os.path.realpath(path))
        try:
            resolved.relative_to(candidate)
            return stage, "CURRENT_ROOT"
        except ValueError:
            return stage, "ALIAS_OR_OTHER_ROOT"
    return None


def registry_references(root: Path) -> list[tuple[str, str, str]]:
    registry = ROOT / "scripts/model-assets.sh"
    if registry.is_symlink() or not registry.is_file():
        raise Blocked("model_asset_registry_missing_or_symlink")
    program = (
        'source "$1"; '
        'while IFS= read -r profile; do '
        'describe_model_asset "$profile" || exit 2; '
        'printf "%s\\t%s\\t%s\\n" "$profile" '
        '"$MODEL_ASSET_CHECKPOINT" "$MODEL_ASSET_CHECKPOINT_DEPENDS_ON"; '
        'done < <(model_asset_profiles)'
    )
    env = {**os.environ, "QWEN38_MODEL_ROOT": str(root)}
    raw = command("bash", "-c", program, "hybrid-dependency-audit", str(registry), env=env)
    findings: set[tuple[str, str, str]] = set()
    for line in raw.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            raise Blocked("invalid_model_asset_registry_output")
        profile, checkpoint, dependencies = parts
        if profile in STAGE_PROFILES:
            continue
        for stage, dirname in STAGES.items():
            alias = Path(checkpoint) == root / dirname
            dependency = DEPENDENCY_PROFILES[stage] in dependencies.split()
            if alias or dependency:
                findings.add((profile, stage, "PATH_ALIAS" if alias else "DECLARED_DEPENDENCY"))
    return sorted(findings)


def docker_references(root: Path) -> tuple[list[tuple[str, str, str, str, str]], list[str]]:
    ids = command("docker", "ps", "-aq", "--no-trunc").splitlines()
    if any(not DOCKER_ID.fullmatch(cid) for cid in ids):
        raise Blocked("invalid_docker_inventory")
    if not ids:
        return [], ids
    containers = json.loads(command("docker", "inspect", *ids))
    if not isinstance(containers, list) or len(containers) != len(ids):
        raise Blocked("docker_inspect_count_mismatch")
    seen: set[str] = set()
    findings: set[tuple[str, str, str, str, str]] = set()
    for info in containers:
        cid = info.get("Id", "")
        if cid not in ids or cid in seen:
            raise Blocked("docker_inspect_identity_mismatch")
        seen.add(cid)
        name = str(info.get("Name", "")).lstrip("/")
        state = info.get("State", {}).get("Status", "unknown")
        mounts = info.get("Mounts")
        if not isinstance(mounts, list):
            raise Blocked("docker_mounts_unavailable")
        for mount in mounts:
            if mount.get("Type") != "bind":
                continue
            matched = match_mount_source(mount.get("Source", ""), root)
            if matched:
                stage, scope = matched
                findings.add((cid, name, str(state), stage, scope))
    return sorted(findings), ids


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models-root", required=True, type=Path)
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args()
    try:
        if not SHA.fullmatch(args.expected_sha):
            raise Blocked("exact_sha_required")
        if not args.models_root.is_absolute() or args.models_root.is_symlink():
            raise Blocked("explicit_non_symlink_absolute_models_root_required")
        root = args.models_root.resolve(strict=True)
        if not root.is_dir():
            raise Blocked("models_root_not_directory")
        if command("git", "-C", str(ROOT), "rev-parse", "HEAD") != args.expected_sha:
            raise Blocked("source_sha_mismatch")
        if command("git", "-C", str(ROOT), "status", "--porcelain=v1", "--untracked-files=all"):
            raise Blocked("source_dirty")
        for stage, name in STAGES.items():
            directory = root / name
            if directory.is_symlink() or not directory.is_dir():
                raise Blocked(f"missing_or_symlinked_stage:{stage}")
        print(f"HYBRID_REFERENCE_AUDIT=BEGIN\nSOURCE_SHA={args.expected_sha}")
        print(f"MODEL_ROOT={root}\nMODEL_START=NO\nHOST_MUTATION=NO")
        profiles = registry_references(root)
        for profile, stage, reason in profiles:
            print(f"PROTECTED_PROFILE_REFERENCE={profile} STAGE={stage} TYPE={reason}")
        mounts, ids_before = docker_references(root)
        print(f"DOCKER_CONTAINERS_INSPECTED={len(ids_before)}")
        container_ids: set[str] = set()
        other_root: set[str] = set()
        for cid, name, state, stage, scope in mounts:
            container_ids.add(cid)
            if scope != "CURRENT_ROOT":
                other_root.add(cid)
            print(f"DOCKER_STAGE_REFERENCE={cid} NAME={name} STATE={state} STAGE={stage} SCOPE={scope}")
        ids_after = command("docker", "ps", "-aq", "--no-trunc").splitlines()
        if ids_before != ids_after:
            raise Blocked("docker_inventory_changed")
        if command("git", "-C", str(ROOT), "rev-parse", "HEAD") != args.expected_sha or \
                command("git", "-C", str(ROOT), "status", "--porcelain=v1", "--untracked-files=all"):
            raise Blocked("source_changed_during_audit")
        print(f"PROTECTED_PROFILE_REFERENCES={len(profiles)}")
        print(f"DOCKER_REFERENCING_CONTAINERS={len(container_ids)}")
        print(f"DOCKER_OTHER_ROOT_REVIEW_CONTAINERS={len(other_root)}")
        print("HYBRID_DELETION_AUTHORIZED=NO")
        print("BENCHMARK_EVIDENCE=NOT_EVALUATED")
        if profiles or mounts:
            print("HYBRID_REFERENCE_AUDIT=BLOCKED_KNOWN_REFERENCES")
            return 3
        print("HYBRID_REFERENCE_AUDIT=NO_KNOWN_REFERENCES_NOT_A_DELETE_PERMIT")
        return 0
    except (Blocked, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"HYBRID_REFERENCE_AUDIT=INVALID reason={error}", file=sys.stderr)
        print("HYBRID_DELETION_AUTHORIZED=NO", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
