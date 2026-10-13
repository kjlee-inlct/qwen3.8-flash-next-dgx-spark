#!/usr/bin/env python3
"""S4: read-only all-Hybrid-symlink closure and source mount contract check."""
from __future__ import annotations
from collections import Counter
import os
from pathlib import Path
import runpy
import shutil
import stat
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
S3 = runpy.run_path(str(ROOT / "scripts/diagnostics/inspect-hybrid-runtime-references.py"))
AuditError = S3["AuditError"]
VIRTUAL = S3["map_virtual_target"]

MOUNTS = (
    ("HYBRID_BASE_DIR", "/base-model"),
    ("HYBRID_H3_DIR", "/h3-model"),
    ("HYBRID_H4_DIR", "/h4-all"),
    ("HYBRID_H5_DIR", "/h5-parent"),
)

def check_source_contract(root: Path) -> None:
    source = (root / "scripts/serve.sh").read_text(encoding="utf-8")
    marker = "  orcarouter-hybrid)"
    if source.count(marker) != 1:
        raise AuditError("source_hybrid_profile_missing_or_ambiguous")
    block = source.split(marker, 1)[1].split("\n    ;;", 1)[0]
    for key, target in MOUNTS:
        required = '"' + "$" + "{" + key + "}:" + target + ':ro"'
        if required not in block:
            raise AuditError("source_readonly_mount_missing:" + target)
    use_array = '"' + "$" + "{HYBRID_MOUNTS[@]}" + '"'
    model_mount = '"' + "$" + "{MODEL_DIR}:/model:ro" + '"'
    if use_array not in source or model_mount not in source:
        raise AuditError("source_docker_mount_wiring_missing")
    for file, tokens in (
        ("prepare-quant-layout-hybrid-checkpoint.py", ('BASE_MOUNT = "/base-model"',)),
        ("prepare-h4-expert-ab.py", ('H3_MOUNT = "/h3-model"', 'BASE_MOUNT = "/base-model"')),
        ("prepare-h5-input-scale.py", ('PARENT_MOUNT = "/h4-all"',)),
        ("prepare-h6-w4a16.py", ('PARENT_MOUNT = "/h5-parent"',)),
    ):
        body = (root / "scripts/model" / file).read_text(encoding="utf-8")
        if any(token not in body for token in tokens):
            raise AuditError("source_builder_mount_contract_changed:" + file)

def resolve_link(stage: str, name: str, dirs: dict[str, Path]) -> str:
    visited: set[tuple[str, str]] = set()
    for _ in range(18):
        if not name or name in {".", ".."} or "/" in name or "\\" in name:
            return "INVALID_NAME"
        key = (stage, name)
        if key in visited:
            return "CYCLE"
        visited.add(key)
        path = dirs[stage] / name
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            return "MISSING"
        if stat.S_ISLNK(mode):
            next_ref = VIRTUAL(stage, os.readlink(path))
            if next_ref is None:
                return "UNRECOGNIZED_ALIAS"
            stage, name = next_ref
        elif stat.S_ISREG(mode):
            return "REGULAR_FILE"
        elif stat.S_ISDIR(mode):
            return "DIRECTORY"
        else:
            return "UNSUPPORTED_OBJECT"
    return "DEPTH_LIMIT"

def count_links(stage: str, root: Path, dirs: dict[str, Path]) -> Counter[str]:
    result: Counter[str] = Counter()
    for parent, folders, files in os.walk(root, followlinks=False):
        for entry in folders + files:
            path = Path(parent) / entry
            if not path.is_symlink():
                continue
            if path.parent != root:
                result["UNSUPPORTED_NESTED_LINK"] += 1
            else:
                result[resolve_link(stage, entry, dirs)] += 1
    return result

def main() -> int:
    if len(sys.argv) != 1:
        print("S4_LINK_CLOSURE=INVALID reason=unexpected_arguments", file=sys.stderr)
        return 2
    try:
        sha, dirs, before = S3["preflight"]()
        check_source_contract(ROOT)
        print(f"S4_LINK_CLOSURE=BEGIN\nSOURCE_SHA={sha}")
        print("SOURCE_MOUNT_CONTRACT=STATIC_PASS\nHOST_MUTATION=NO")
        print("MODEL_START=NO\nTENSOR_PAYLOAD_READ=NO")
        gaps = 0
        for stage, directory in dirs.items():
            result = count_links(stage, directory, dirs)
            print(f"STAGE={stage} ALL_SYMLINKS={sum(result.values())}")
            for status, count in sorted(result.items()):
                print(f"LINK_STAGE={stage} LINK_RESOLUTION={status} COUNT={count}")
                if status not in ("REGULAR_FILE", "DIRECTORY"):
                    gaps += count
        disk = os.statvfs(dirs["base"].parent)
        print(f"FS_DEVICE={dirs['base'].parent.stat().st_dev}")
        print(f"FS_AVAILABLE_BYTES_SNAPSHOT={disk.f_bavail * disk.f_frsize}")
        if shutil.which("findmnt"):
            result = subprocess.run(
                ["findmnt", "--noheadings", "--target", str(dirs["base"].parent),
                 "--output", "FSTYPE"], capture_output=True, text=True, check=False)
            print("FS_TYPE=" + (result.stdout.strip() if result.returncode == 0
                                and result.stdout.strip() else "NOT_DETERMINED"))
        else:
            print("FS_TYPE=NOT_DETERMINED")
        if (S3["snapshots"]() != before or S3["git"]("rev-parse", "HEAD") != sha or
                S3["git"]("status", "--porcelain=v1", "--untracked-files=all")):
            raise AuditError("source_or_installation_changed")
        print(f"ALL_LINK_REFERENCE_GAPS={gaps}")
        print("ACTUAL_DOCKER_BIND_MOUNTS=NOT_VERIFIED")
        print("REFLINK_COW_SHARED_EXTENTS=NOT_MEASURED")
        print("RECLAIMABLE_BYTES=NOT_CERTIFIED")
        print("BENCHMARK_BEFORE_RECLAIM=REQUIRED")
        print("MODEL_DELETION=BLOCKED_PENDING_EVIDENCE_AND_DEPENDENCY_REVIEW")
        print("S4_LINK_CLOSURE=" + ("COLLECTED_READ_ONLY" if gaps == 0 else "COLLECTED_PARTIAL"))
        return 0 if gaps == 0 else 3
    except (AuditError, OSError, ValueError) as error:
        print(f"S4_LINK_CLOSURE=INVALID reason={error}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
