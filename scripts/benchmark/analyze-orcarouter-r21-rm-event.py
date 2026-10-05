#!/usr/bin/env python3
"""Compare R21 post-compaction allocator state with the captured RM-OOM event."""

from __future__ import annotations

import argparse
import pathlib
import re

PAGE_SIZE = 4096
BUDDY_RE = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+)\s+(.+)$")
PAGETYPE_RE = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+),\s+type\s+(\S+)\s+(.+)$")


def read_required(path: pathlib.Path) -> str:
    if not path.is_file():
        raise SystemExit(f"missing R21 RM-event input: {path}")
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


def ge_mib(values: list[int], minimum: int) -> float:
    pages = sum(count * (1 << order) for order, count in enumerate(values) if order >= minimum)
    return pages * PAGE_SIZE / (1024 * 1024)


def order_mib(values: list[int], order: int) -> float:
    if len(values) <= order:
        return 0.0
    return values[order] * (1 << order) * PAGE_SIZE / (1024 * 1024)


def load_metrics(path: pathlib.Path) -> dict[str, float]:
    buddy = parse_counts(read_required(path / "proc-buddyinfo.txt"), BUDDY_RE)
    pagetype = parse_counts(read_required(path / "proc-pagetypeinfo.txt"), PAGETYPE_RE)
    mem = parse_meminfo(read_required(path / "proc-meminfo.txt"))
    normal = buddy.get((0, "Normal"), [])
    unmovable = pagetype.get((0, "Normal", "Unmovable"), [])
    movable = pagetype.get((0, "Normal", "Movable"), [])
    return {
        "memavailable": mem.get("MemAvailable", 0) / 1024,
        "memfree": mem.get("MemFree", 0) / 1024,
        "cached": mem.get("Cached", 0) / 1024,
        "inactive_file": mem.get("Inactive(file)", 0) / 1024,
        "swapfree": mem.get("SwapFree", 0) / 1024,
        "normal_o4": order_mib(normal, 4),
        "normal_o5plus": ge_mib(normal, 5),
        "normal_o4plus": ge_mib(normal, 4),
        "unmovable_o4plus": ge_mib(unmovable, 4),
        "movable_o4plus": ge_mib(movable, 4),
    }


def emit(label: str, values: dict[str, float]) -> None:
    fields = " ".join(f"{key}_mib={value:.3f}" for key, value in values.items())
    print(f"r21_rm_state={label} {fields}")


def emit_delta(before: dict[str, float], after: dict[str, float]) -> None:
    fields = " ".join(
        f"{key}_mib={after[key] - before[key]:+.3f}" for key in before
    )
    print(f"r21_rm_delta=POST_COMPACT_TO_RM_EVENT {fields}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r21", required=True, help="R21 evidence root")
    args = parser.parse_args()
    root = pathlib.Path(args.r21)

    events = sorted((root / "allocator-state" / "events").glob("rm-oom-*"))
    if len(events) != 1:
        raise SystemExit(f"expected exactly one R21 RM event snapshot, found {len(events)}")

    post = load_metrics(root / "poststop-after-compact")
    event = load_metrics(events[0])
    meta = read_required(events[0] / "meta.txt").strip().replace("\n", " ")

    print("ORCA_R21_RM_EVENT_ANALYSIS=BEGIN")
    print(f"r21_rm_event_dir={events[0].name} {meta}")
    emit("POST_COMPACT", post)
    emit("RM_EVENT", event)
    emit_delta(post, event)
    print("ORCA_R21_RM_EVENT_ANALYSIS=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
