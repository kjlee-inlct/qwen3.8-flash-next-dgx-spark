#!/usr/bin/env python3
"""S3: read-only host audit of hybrid shard links through known container mounts.

Never loads tensor payloads, starts a runtime, edits a checkpoint or approves deletion.
Run with python3 -B and exact SHA in a pristine detached audit worktree.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
TREE_NAMES = {
    "base": "qwen3.8-flash-next-orcarouter",
    "mazinb": "qwen3.8-flash-next-mazinb",
    "h3": "qwen3.8-hybrid-quant-layout",
    "h4": "qwen3.8-h4-orca-all",
    "h5": "qwen3.8-h5-neutral-input-scale",
    "h6": "qwen3.8-h6-modelopt-w4a16",
}
# Source builder contracts. A host-dangling absolute link to one of these
# aliases may be valid inside the intended read-only Docker bind mount layout.
VIRTUAL_MOUNTS = {
    "base": {},
    "mazinb": {},
    "h3": {"/base-model": "base"},
    "h4": {"/base-model": "base", "/h3-model": "h3"},
    "h5": {"/h4-all": "h4", "/h3-model": "h3"},
    "h6": {
        "/h5-parent": "h5", "/h4-all": "h4",
        "/h3-model": "h3", "/base-model": "base",
    },
}
SHA = re.compile(r"^[0-9a-f]{40}$")
SHARD = re.compile(r"^[A-Za-z0-9_.-]+\.safetensors$")


class AuditError(Exception):
    pass


def git(*args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(ROOT), *args], text=True, capture_output=True,
        check=False,
    )
    if done.returncode:
        raise AuditError(f"git_{args[0]}_failed")
    return done.stdout.strip()


def fingerprint(path: Path) -> str:
    if path.is_symlink():
        return "SYMLINK_UNSAFE"
    if not path.exists():
        return "ABSENT"
    if not path.is_file():
        return "NOT_REGULAR"
    dig = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            dig.update(chunk)
    return dig.hexdigest()


def snapshots() -> tuple[str, str, str]:
    state = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
    data = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
    manifest = state / "qwen38-spark/install.env"
    ownership = state / "qwen38-spark/asset-ownership.json"
    current = data / "qwen38-spark/current"
    if manifest.is_symlink() or not manifest.is_file():
        raise AuditError("invalid_installed_manifest")
    if ownership.is_symlink() or not current.is_symlink():
        raise AuditError("invalid_ownership_or_release_symlink")
    return fingerprint(manifest), fingerprint(ownership), str(current.resolve(strict=True))


def preflight() -> tuple[str, dict[str, Path], tuple[str, str, str]]:
    target = os.environ.get("QWEN38_RECLAIM_AUDIT_SHA", "")
    raw_root = os.environ.get("QWEN38_RECLAIM_MODELS_ROOT", "")
    if not SHA.fullmatch(target):
        raise AuditError("exact_checkout_sha_required")
    if not raw_root.startswith("/") or Path(raw_root).is_symlink() or not Path(raw_root).is_dir():
        raise AuditError("explicit_real_models_root_required")
    if git("rev-parse", "HEAD") != target or git("status", "--porcelain=v1", "--untracked-files=all"):
        raise AuditError("checkout_sha_mismatch_or_dirty")
    root = Path(raw_root).resolve(strict=True)
    dirs = {key: root / dirname for key, dirname in TREE_NAMES.items()}
    for label, path in dirs.items():
        if path.is_symlink() or not path.is_dir():
            raise AuditError(f"missing_non_symlink_tree:{label}")
        if not ((path / ".qwen38-model-manifest.json").is_file() or
                (path / ".qwen38-hybrid-manifest.json").is_file()):
            raise AuditError(f"missing_tree_manifest:{label}")
    return target, dirs, snapshots()


def map_virtual_target(stage: str, target: str) -> tuple[str, str] | None:
    if not target.startswith("/"):
        return None
    # Reject traversal rather than resolving arbitrary host paths.
    parts = PurePosixPath(target).parts
    if ".." in parts or "." in parts:
        return None
    for mount, owner in VIRTUAL_MOUNTS[stage].items():
        prefix = mount + "/"
        if target.startswith(prefix):
            rest = target[len(prefix):]
            if rest and rest != "." and not rest.startswith("/"):
                return owner, rest
    return None


def resolve_shard(stage: str, filename: str, dirs: dict[str, Path]) -> str:
    if not SHARD.fullmatch(filename) or filename in {".", ".."}:
        return "INVALID_NAME"
    visited: set[tuple[str, str]] = set()
    current, name = stage, filename
    while True:
        entry = (current, name)
        if entry in visited or len(visited) > 16:
            return "CYCLE"
        visited.add(entry)
        path = dirs[current] / name
        if path.is_symlink():
            nxt = map_virtual_target(current, os.readlink(path))
            if nxt is None:
                return "UNKNOWN_ALIAS"
            current, name = nxt
            if not SHARD.fullmatch(name):
                return "INVALID_TARGET"
        elif path.is_file():
            return "DIRECT" if len(visited) == 1 else "VIRTUAL_CHAIN"
        else:
            return "MISSING"


def link_summary(stage: str, directory: Path) -> tuple[Counter[str], int]:
    aliases: Counter[str] = Counter()
    count = 0
    for parent, subdirs, files in os.walk(directory, topdown=True, followlinks=False):
        for name in subdirs + files:
            path = Path(parent) / name
            if not path.is_symlink():
                continue
            count += 1
            raw = os.readlink(path)
            target = map_virtual_target(stage, raw)
            aliases[target[0] if target else "UNMAPPED_OR_RELATIVE"] += 1
    return aliases, count


def index_summary(stage: str, directory: Path, dirs: dict[str, Path]) -> tuple[int, int, Counter[str]]:
    index_path = directory / "model.safetensors.index.json"
    if index_path.is_symlink() or not index_path.is_file():
        raise AuditError(f"missing_direct_index:{stage}")
    with index_path.open(encoding="utf-8") as stream:
        index = json.load(stream)
    weight_map = index.get("weight_map")
    if not isinstance(weight_map, dict) or not weight_map:
        raise AuditError(f"invalid_index_weight_map:{stage}")
    filenames = set()
    for value in weight_map.values():
        if not isinstance(value, str):
            raise AuditError(f"invalid_index_shard_type:{stage}")
        filenames.add(value)
    counts = Counter(resolve_shard(stage, name, dirs) for name in filenames)
    return len(weight_map), len(filenames), counts


def main() -> int:
    try:
        target, dirs, before = preflight()
        print(f"S3_REFERENCE_SURVEY=BEGIN\nSOURCE_SHA={target}")
        print("HOST_MUTATION=NO\nMODEL_START=NO\nTENSOR_PAYLOAD_READ=NO")
        print("HOST_DANGLING_VIRTUAL_LINKS_ARE_NOT_AUTOMATIC_FAILURE=YES")
        total_gaps = 0
        for stage in TREE_NAMES:
            alias_counts, link_count = link_summary(stage, dirs[stage])
            tensors, shards, statuses = index_summary(stage, dirs[stage], dirs)
            print(f"STAGE={stage} SYMLINKS={link_count} INDEX_TENSORS={tensors} INDEX_SHARDS={shards}")
            for key, value in sorted(alias_counts.items()):
                print(f"LINK_TARGET_STAGE={stage} ALIAS_OWNER={key} COUNT={value}")
            for key, value in sorted(statuses.items()):
                print(f"INDEX_STAGE={stage} RESOLUTION={key} COUNT={value}")
            total_gaps += alias_counts["UNMAPPED_OR_RELATIVE"]
            total_gaps += sum(v for k, v in statuses.items() if k not in ("DIRECT", "VIRTUAL_CHAIN"))
        after = snapshots()
        if before != after or git("rev-parse", "HEAD") != target or git("status", "--porcelain=v1", "--untracked-files=all"):
            raise AuditError("source_or_installed_state_changed_during_survey")
        print(f"REFERENCE_GAPS={total_gaps}")
        print("BENCHMARK_BEFORE_RECLAIM=REQUIRED")
        print("MODEL_DELETION=BLOCKED_PENDING_EVIDENCE_AND_DEPENDENCY_REVIEW")
        if total_gaps:
            print("S3_REFERENCE_SURVEY=COLLECTED_PARTIAL_UNMAPPED_REFERENCES")
            return 3
        print("S3_REFERENCE_SURVEY=COLLECTED_READ_ONLY")
        return 0
    except (AuditError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"S3_REFERENCE_SURVEY=INVALID reason={exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
