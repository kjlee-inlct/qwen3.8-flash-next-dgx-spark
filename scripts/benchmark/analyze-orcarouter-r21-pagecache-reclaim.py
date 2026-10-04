#!/usr/bin/env python3
"""Summarize R21 post-stop page-cache reclaim and compaction snapshots."""

from __future__ import annotations

import argparse
import pathlib
import re

PAGE_SIZE = 4096
BUDDY_RE = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+)\s+(.+)$")
PAGETYPE_RE = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+),\s+type\s+(\S+)\s+(.+)$")
STAGES = (
    ("BEFORE_RECLAIM", "poststop-before-reclaim"),
    ("AFTER_SYNC", "poststop-after-sync"),
    ("AFTER_DROP", "poststop-after-drop-caches"),
    ("AFTER_COMPACT", "poststop-after-compact"),
)


def read_required(path: pathlib.Path) -> str:
    if not path.is_file():
        raise SystemExit(f"missing R21 snapshot file: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def parse_counts(text: str, pattern: re.Pattern[str]) -> dict[tuple, list[int]]:
    result: dict[tuple, list[int]] = {}
    for raw in text.splitlines():
        match = pattern.match(raw.strip())
        if not match:
            continue
        values: list[int] = []
        payload = match.group(match.lastindex or 0)
        for token in payload.split():
            if token == ">100000":
                values.append(100001)
            else:
                try:
                    values.append(int(token))
                except ValueError:
                    pass
        if pattern is BUDDY_RE:
            key = (int(match.group(1)), match.group(2))
        else:
            key = (int(match.group(1)), match.group(2), match.group(3))
        result[key] = values
    return result


def parse_meminfo(text: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for raw in text.splitlines():
        if ":" not in raw:
            continue
        key, rest = raw.split(":", 1)
        parts = rest.split()
        if parts and parts[0].isdigit():
            result[key] = int(parts[0])
    return result


def order_mib(values: list[int], order: int) -> float:
    if len(values) <= order:
        return 0.0
    return values[order] * (1 << order) * PAGE_SIZE / (1024 * 1024)


def ge_mib(values: list[int], minimum: int) -> float:
    pages = sum(count * (1 << order) for order, count in enumerate(values) if order >= minimum)
    return pages * PAGE_SIZE / (1024 * 1024)


def load_snapshot(path: pathlib.Path) -> dict[str, object]:
    return {
        "buddy": parse_counts(read_required(path / "proc-buddyinfo.txt"), BUDDY_RE),
        "pagetype": parse_counts(read_required(path / "proc-pagetypeinfo.txt"), PAGETYPE_RE),
        "mem": parse_meminfo(read_required(path / "proc-meminfo.txt")),
    }


def metric(snap: dict[str, object]) -> dict[str, float]:
    buddy = snap["buddy"][(0, "Normal")]  # type: ignore[index]
    pagetype = snap["pagetype"]  # type: ignore[assignment]
    mem = snap["mem"]  # type: ignore[assignment]
    unmovable = pagetype.get((0, "Normal", "Unmovable"), [])
    movable = pagetype.get((0, "Normal", "Movable"), [])
    return {
        "memavailable": mem.get("MemAvailable", 0) / 1024,
        "memfree": mem.get("MemFree", 0) / 1024,
        "cached": mem.get("Cached", 0) / 1024,
        "active_file": mem.get("Active(file)", 0) / 1024,
        "inactive_file": mem.get("Inactive(file)", 0) / 1024,
        "swapfree": mem.get("SwapFree", 0) / 1024,
        "normal_o4": order_mib(buddy, 4),
        "normal_o5plus": ge_mib(buddy, 5),
        "normal_o4plus": ge_mib(buddy, 4),
        "unmovable_o4plus": ge_mib(unmovable, 4),
        "movable_o4plus": ge_mib(movable, 4),
    }


def emit(label: str, values: dict[str, float]) -> None:
    fields = " ".join(f"{key}_mib={value:.3f}" for key, value in values.items())
    print(f"r21_state={label} {fields}")


def emit_delta(label: str, before: dict[str, float], after: dict[str, float]) -> None:
    fields = " ".join(
        f"{key}_mib={after[key] - before[key]:+.3f}"
        for key in before
    )
    print(f"r21_delta={label} {fields}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r21", required=True, help="R21 evidence root")
    args = parser.parse_args()
    root = pathlib.Path(args.r21)

    states: list[tuple[str, dict[str, float]]] = []
    print("ORCA_R21_PAGECACHE_RECLAIM_ANALYSIS=BEGIN")
    for label, dirname in STAGES:
        values = metric(load_snapshot(root / dirname))
        states.append((label, values))
        emit(label, values)

    for (left_label, left), (right_label, right) in zip(states, states[1:]):
        emit_delta(f"{left_label}_TO_{right_label}", left, right)

    emit_delta("BEFORE_RECLAIM_TO_AFTER_COMPACT", states[0][1], states[-1][1])
    print("ORCA_R21_PAGECACHE_RECLAIM_ANALYSIS=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
