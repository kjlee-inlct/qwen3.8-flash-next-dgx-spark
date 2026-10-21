#!/usr/bin/env python3
"""Read-only audit of managed DGX Spark state retention; never remove files.

This is an inventory, NOT an automatic approval to delete any state file.
Byte sizes are approximate allocated bytes, not guaranteed reclaimable bytes.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys

CRITICAL = frozenset({
    "install.env", "asset-ownership.json", "operation.lock",
    "config.vllm.json", "monitor.log",
})
RETAIN_EVIDENCE = frozenset({
    "ab-trials", "analysis", "mazinb-m1",
})
REVIEW_HISTORY = frozenset({
    "hybrid-h6-m1", "hybrid-retirement-evidence",
    "ab-trial.json", "runtime-validation.json",
    "runtime-validation-after-reboot.json",
    "runtime-validation-after-restart.json",
    "runtime-validation-systemd.json",
})
STABILITY = re.compile(r"stability-[0-9]+\.json\Z")


def policy(name: str, parent: str = "") -> tuple[str, str]:
    if parent == "retirement-archives":
        if name == "hybrid-docker-17-20261015":
            return "RETAIN_UNIQUE_RAW_EVIDENCE", "17-container original logs are not in Git"
        if name.startswith("mazinb-docker-"):
            return "RETAIN_OTHER_MODEL_EVIDENCE", "Mazinb archive; unrelated to Hybrid removal"
        return "REVIEW_UNKNOWN_PROTECT", "Unrecognized archive; inspect before any action"
    if name in CRITICAL or name.startswith(("runtime-transition", "update-transition")):
        return "RETAIN_LIFECYCLE", "Managed runtime, ownership or lock state"
    if name.startswith("install.env."):
        return "RETAIN_RECOVERY", "Installation backup or recovery history"
    if name == "retirement-archives":
        return "RETAIN_ARCHIVES", "Container evidence archive collection"
    if name in RETAIN_EVIDENCE:
        return "RETAIN_RESEARCH", "Benchmark or experiment history"
    if name in REVIEW_HISTORY or STABILITY.fullmatch(name):
        return "REVIEW_ONLY", "Historical state; usage/duplication not established"
    return "REVIEW_UNKNOWN_PROTECT", "Unclassified state; preserve by default"


def measure(path: Path, expected_dev: int) -> dict[str, int]:
    allocated = 0
    files = 0
    symlinks = 0
    boundaries = 0
    special = 0
    seen_inodes = set()

    def record(p: Path) -> bool:
        nonlocal allocated, files, symlinks, boundaries, special
        st = p.lstat()
        if stat.S_ISLNK(st.st_mode):
            symlinks += 1
            return False
        if st.st_dev != expected_dev:
            boundaries += 1
            return False
        if not (stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode)):
            special += 1
            return False
        key = (st.st_dev, st.st_ino)
        if key not in seen_inodes:
            seen_inodes.add(key)
            allocated += st.st_blocks * 512
        if stat.S_ISREG(st.st_mode):
            files += 1
        return True

    if not record(path):
        return {"allocated_bytes": 0, "files": files, "symlinks": symlinks,
                "boundaries": boundaries, "special": special}
    if path.is_dir():
        for current, dirs, filenames in os.walk(path, followlinks=False):
            for dirname in dirs[:]:
                child = Path(current) / dirname
                if not record(child) or not child.is_dir():
                    dirs.remove(dirname)
            for filename in filenames:
                record(Path(current) / filename)
    return {"allocated_bytes": allocated, "files": files, "symlinks": symlinks,
            "boundaries": boundaries, "special": special}


def audit(root: Path) -> dict:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("state root missing or symlink")
    device = root.stat().st_dev
    entries = []
    for item in sorted(root.iterdir(), key=lambda p: p.name):
        category, reason = policy(item.name)
        stats = measure(item, device)
        entries.append({"name": item.name, "category": category,
                        "reason": reason, **stats})
        if item.name == "retirement-archives" and item.is_dir() and not item.is_symlink():
            for child in sorted(item.iterdir(), key=lambda p: p.name):
                child_category, child_reason = policy(child.name, item.name)
                entries.append({"name": "retirement-archives/" + child.name,
                                "category": child_category,
                                "reason": child_reason, **measure(child, device)})
    return {"state_root": str(root), "audit": "READ_ONLY",
            "entries": entries, "delete_authorized": False,
            "files_deleted": 0,
            "notes": [
                "Archive child sizes overlap with the retirement-archives parent total.",
                "Allocated bytes are not a prediction of recoverable disk space.",
                "No files are automatically approved for deletion.",
                "Raw logs and state-file content are not displayed.",
            ]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-root", type=Path,
                        default=Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state")))
                        / "qwen38-spark")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    try:
        report = audit(args.state_root)
    except (OSError, ValueError) as error:
        print("STATE_RETENTION_AUDIT=BLOCKED " + str(error), file=sys.stderr)
        return 3
    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("Read-only state retention audit / 상태 파일 보존 점검")
        print("ROOT=" + report["state_root"])
        for e in report["entries"]:
            size = e["allocated_bytes"] / 1024 / 1024
            print(f'{e["category"]:29} {size:9.2f} MiB  '
                  f'links={e["symlinks"]} boundaries={e["boundaries"]}  {e["name"]}')
        print("STATE_DELETE_AUTHORIZED=NO")
        print("STATE_FILES_DELETED=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
