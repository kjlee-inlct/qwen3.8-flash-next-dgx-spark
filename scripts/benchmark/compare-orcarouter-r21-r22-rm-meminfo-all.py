#!/usr/bin/env python3
"""Compare every /proc/meminfo field for R21/R22 post-compact and RM-event states."""

from __future__ import annotations

import argparse
import pathlib


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
            value = float(parts[0])
        except ValueError:
            continue
        unit = parts[1] if len(parts) > 1 else ""
        if unit == "kB":
            result[key] = value / 1024.0
        else:
            # Unitless meminfo fields (for example HugePages_Total) are kept
            # numerically as-is and explicitly labelled unitless in output.
            result[key] = value
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


def is_unitless(key: str) -> bool:
    return key.startswith("HugePages_")


def emit_delta(run: str, before: dict[str, float], after: dict[str, float]) -> None:
    keys = sorted(set(before) | set(after), key=lambda key: abs(after.get(key, 0.0) - before.get(key, 0.0)), reverse=True)
    for key in keys:
        post = before.get(key, 0.0)
        event = after.get(key, 0.0)
        delta = event - post
        unit = "count" if is_unitless(key) else "MiB"
        print(
            f"meminfo_delta={run}_POST_TO_EVENT key={key} unit={unit} "
            f"post={post:.3f} event={event:.3f} delta={delta:+.3f}"
        )


def emit_cross(r21: dict[str, float], r22: dict[str, float]) -> None:
    keys = sorted(set(r21) | set(r22), key=lambda key: abs(r22.get(key, 0.0) - r21.get(key, 0.0)), reverse=True)
    for key in keys:
        left = r21.get(key, 0.0)
        right = r22.get(key, 0.0)
        delta = right - left
        unit = "count" if is_unitless(key) else "MiB"
        print(
            f"meminfo_cross=R22_EVENT_MINUS_R21_EVENT key={key} unit={unit} "
            f"r21={left:.3f} r22={right:.3f} delta={delta:+.3f}"
        )


def emit_focus(run: str, before: dict[str, float], after: dict[str, float]) -> None:
    keys = (
        "MemFree",
        "MemAvailable",
        "Cached",
        "AnonPages",
        "Shmem",
        "Slab",
        "SReclaimable",
        "SUnreclaim",
        "CmaTotal",
        "CmaFree",
        "VmallocTotal",
        "VmallocUsed",
        "VmallocChunk",
        "Percpu",
        "KernelStack",
        "PageTables",
        "Unevictable",
        "Mlocked",
        "SwapFree",
        "HugePages_Total",
        "HugePages_Free",
        "HugePages_Rsvd",
        "HugePages_Surp",
        "Hugetlb",
    )
    for key in keys:
        if key not in before and key not in after:
            continue
        post = before.get(key, 0.0)
        event = after.get(key, 0.0)
        unit = "count" if is_unitless(key) else "MiB"
        print(
            f"meminfo_focus={run} key={key} unit={unit} "
            f"post={post:.3f} event={event:.3f} delta={event-post:+.3f}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r21", required=True)
    parser.add_argument("--r22", required=True)
    args = parser.parse_args()

    r21_post, r21_event = load(pathlib.Path(args.r21))
    r22_post, r22_event = load(pathlib.Path(args.r22))

    print("ORCA_R21_R22_RM_MEMINFO_ALL=BEGIN")
    emit_focus("R21", r21_post, r21_event)
    emit_focus("R22", r22_post, r22_event)
    emit_delta("R21", r21_post, r21_event)
    emit_delta("R22", r22_post, r22_event)
    emit_cross(r21_event, r22_event)
    print("ORCA_R21_R22_RM_MEMINFO_ALL=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
