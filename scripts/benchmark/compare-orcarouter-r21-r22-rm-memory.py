#!/usr/bin/env python3
"""Compare detailed R21/R22 memory composition at post-compact and RM event."""

from __future__ import annotations

import argparse
import pathlib

KEYS = (
    "MemAvailable",
    "MemFree",
    "Cached",
    "Active(anon)",
    "Inactive(anon)",
    "Active(file)",
    "Inactive(file)",
    "AnonPages",
    "Shmem",
    "Slab",
    "SReclaimable",
    "SUnreclaim",
    "KernelStack",
    "PageTables",
    "Unevictable",
    "Mlocked",
    "SwapFree",
)


def read_meminfo(path: pathlib.Path) -> dict[str, float]:
    if not path.is_file():
        raise SystemExit(f"missing meminfo snapshot: {path}")
    result: dict[str, float] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if ":" not in raw:
            continue
        key, rest = raw.split(":", 1)
        parts = rest.split()
        if not parts:
            continue
        try:
            kib = int(parts[0])
        except ValueError:
            continue
        result[key] = kib / 1024.0
    return result


def event_dir(root: pathlib.Path) -> pathlib.Path:
    dirs = sorted(p for p in (root / "allocator-state" / "events").glob("rm-oom-*") if p.is_dir())
    if len(dirs) != 1:
        raise SystemExit(f"expected exactly one RM event directory under {root}, found {len(dirs)}")
    return dirs[0]


def load(root: pathlib.Path) -> tuple[dict[str, float], dict[str, float]]:
    post = read_meminfo(root / "poststop-after-compact" / "proc-meminfo.txt")
    event = read_meminfo(event_dir(root) / "proc-meminfo.txt")
    return post, event


def emit(run: str, phase: str, values: dict[str, float]) -> None:
    fields = " ".join(f"{key.lower().replace('(', '_').replace(')', '')}_mib={values.get(key, 0.0):.3f}" for key in KEYS)
    print(f"rm_memory_state={run}_{phase} {fields}")


def emit_delta(run: str, before: dict[str, float], after: dict[str, float]) -> None:
    fields = " ".join(
        f"{key.lower().replace('(', '_').replace(')', '')}_mib={after.get(key, 0.0)-before.get(key, 0.0):+.3f}"
        for key in KEYS
    )
    print(f"rm_memory_delta={run}_POST_TO_EVENT {fields}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r21", required=True)
    parser.add_argument("--r22", required=True)
    args = parser.parse_args()

    roots = {"R21": pathlib.Path(args.r21), "R22": pathlib.Path(args.r22)}
    loaded: dict[str, tuple[dict[str, float], dict[str, float]]] = {}
    for run, root in roots.items():
        loaded[run] = load(root)

    print("ORCA_R21_R22_RM_MEMORY=BEGIN")
    for run in ("R21", "R22"):
        post, event = loaded[run]
        emit(run, "POST_COMPACT", post)
        emit(run, "RM_EVENT", event)
        emit_delta(run, post, event)

    r21_event = loaded["R21"][1]
    r22_event = loaded["R22"][1]
    fields = " ".join(
        f"{key.lower().replace('(', '_').replace(')', '')}_mib={r22_event.get(key, 0.0)-r21_event.get(key, 0.0):+.3f}"
        for key in KEYS
    )
    print(f"rm_memory_cross=R22_EVENT_MINUS_R21_EVENT {fields}")
    print("ORCA_R21_R22_RM_MEMORY=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
