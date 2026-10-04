#!/usr/bin/env python3
"""Compare post-stop allocator/memory snapshots for R18 and R20.

Read-only analyzer for the completed R18 clean treatment and the R20 invalid
protected-stop treatment attempt. It compares the explicit snapshots captured
immediately before and after the one-shot post-teardown compaction.
"""

from __future__ import annotations

import argparse
import pathlib
import re

PAGE_SIZE = 4096
BUDDY_RE = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+)\s+(.+)$")
PAGETYPE_RE = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+),\s+type\s+(\S+)\s+(.+)$")
ZONE_HEADER_RE = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+)$")


def read_required(path: pathlib.Path) -> str:
    if not path.is_file():
        raise SystemExit(f"missing snapshot file: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def parse_counts(text: str, pattern: re.Pattern[str]) -> dict[tuple, list[int]]:
    result: dict[tuple, list[int]] = {}
    for raw in text.splitlines():
        match = pattern.match(raw.strip())
        if not match:
            continue
        values: list[int] = []
        for token in match.group(match.lastindex or 0).split():
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


def parse_vmstat(text: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for raw in text.splitlines():
        parts = raw.split()
        if len(parts) == 2:
            try:
                result[parts[0]] = int(parts[1])
            except ValueError:
                pass
    return result


def parse_zoneinfo(text: str) -> dict[tuple[int, str], dict[str, int]]:
    result: dict[tuple[int, str], dict[str, int]] = {}
    current: tuple[int, str] | None = None
    wanted = {"free", "min", "low", "high", "managed", "cma"}
    for raw in text.splitlines():
        line = raw.strip()
        header = ZONE_HEADER_RE.match(line)
        if header:
            current = (int(header.group(1)), header.group(2))
            result.setdefault(current, {})
            continue
        if current is None:
            continue
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "pages" and parts[1] == "free":
            try:
                result[current]["free"] = int(parts[2])
            except ValueError:
                pass
        elif len(parts) >= 2 and parts[0] in wanted:
            try:
                result[current][parts[0]] = int(parts[1])
            except ValueError:
                pass
    return result


def mib_for_orders(values: list[int], minimum: int) -> float:
    pages = sum(count * (1 << order) for order, count in enumerate(values) if order >= minimum)
    return pages * PAGE_SIZE / (1024 * 1024)


def order_mib(values: list[int], order: int) -> float:
    if len(values) <= order:
        return 0.0
    return values[order] * (1 << order) * PAGE_SIZE / (1024 * 1024)


def load_snapshot(path: pathlib.Path) -> dict[str, object]:
    return {
        "buddy": parse_counts(read_required(path / "proc-buddyinfo.txt"), BUDDY_RE),
        "pagetype": parse_counts(read_required(path / "proc-pagetypeinfo.txt"), PAGETYPE_RE),
        "zone": parse_zoneinfo(read_required(path / "proc-zoneinfo.txt")),
        "mem": parse_meminfo(read_required(path / "proc-meminfo.txt")),
        "vm": parse_vmstat(read_required(path / "proc-vmstat.txt")),
    }


def emit_snapshot(label: str, snap: dict[str, object]) -> None:
    buddy = snap["buddy"][(0, "Normal")]  # type: ignore[index]
    mem = snap["mem"]  # type: ignore[assignment]
    zone = snap["zone"].get((0, "Normal"), {})  # type: ignore[union-attr]
    print(
        f"snapshot={label} normal_order4_mib={order_mib(buddy, 4):.3f} "
        f"normal_order5plus_mib={mib_for_orders(buddy, 5):.3f} "
        f"normal_order4plus_mib={mib_for_orders(buddy, 4):.3f} "
        f"memavailable_mib={mem.get('MemAvailable', 0) / 1024:.3f} "
        f"memfree_mib={mem.get('MemFree', 0) / 1024:.3f} "
        f"swapfree_mib={mem.get('SwapFree', 0) / 1024:.3f} "
        f"zone_free_pages={zone.get('free', 0)} zone_low_pages={zone.get('low', 0)} "
        f"zone_high_pages={zone.get('high', 0)}"
    )
    pagetype = snap["pagetype"]  # type: ignore[assignment]
    for migratetype in ("Unmovable", "Movable", "Reclaimable", "HighAtomic"):
        values = pagetype.get((0, "Normal", migratetype), [])
        print(
            f"snapshot_pagetype={label} type={migratetype} "
            f"order4_mib={order_mib(values, 4):.3f} "
            f"order5plus_mib={mib_for_orders(values, 5):.3f} "
            f"order4plus_mib={mib_for_orders(values, 4):.3f}"
        )


def emit_compaction_delta(label: str, before: dict[str, object], after: dict[str, object]) -> None:
    b = before["buddy"][(0, "Normal")]  # type: ignore[index]
    a = after["buddy"][(0, "Normal")]  # type: ignore[index]
    print(
        f"compaction_delta={label} "
        f"order4_mib={order_mib(a, 4) - order_mib(b, 4):+.3f} "
        f"order5plus_mib={mib_for_orders(a, 5) - mib_for_orders(b, 5):+.3f} "
        f"order4plus_mib={mib_for_orders(a, 4) - mib_for_orders(b, 4):+.3f}"
    )
    bv = before["vm"]  # type: ignore[assignment]
    av = after["vm"]  # type: ignore[assignment]
    fields = []
    for key in ("compact_stall", "compact_fail", "compact_success", "compact_daemon_wake"):
        fields.append(f"{key}_delta={av.get(key, 0) - bv.get(key, 0):+d}")
    print(f"compaction_vmstat={label} {' '.join(fields)}")


def emit_post_cross(r18: dict[str, object], r20: dict[str, object]) -> None:
    a = r18["buddy"][(0, "Normal")]  # type: ignore[index]
    b = r20["buddy"][(0, "Normal")]  # type: ignore[index]
    am = r18["mem"]  # type: ignore[assignment]
    bm = r20["mem"]  # type: ignore[assignment]
    print(
        "postcompact_cross=R20_MINUS_R18 "
        f"order4plus_mib={mib_for_orders(b, 4) - mib_for_orders(a, 4):+.3f} "
        f"order5plus_mib={mib_for_orders(b, 5) - mib_for_orders(a, 5):+.3f} "
        f"memavailable_mib={(bm.get('MemAvailable', 0) - am.get('MemAvailable', 0)) / 1024:+.3f} "
        f"memfree_mib={(bm.get('MemFree', 0) - am.get('MemFree', 0)) / 1024:+.3f} "
        f"swapfree_mib={(bm.get('SwapFree', 0) - am.get('SwapFree', 0)) / 1024:+.3f}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r18", required=True, help="R18 evidence root")
    parser.add_argument("--r20", required=True, help="R20 evidence root")
    args = parser.parse_args()

    r18 = pathlib.Path(args.r18)
    r20 = pathlib.Path(args.r20)
    snapshots = {
        "R18_PRE": load_snapshot(r18 / "poststop-before-compact"),
        "R18_POST": load_snapshot(r18 / "poststop-after-compact"),
        "R20_PRE": load_snapshot(r20 / "poststop-before-compact"),
        "R20_POST": load_snapshot(r20 / "poststop-after-compact"),
    }

    print("ORCA_R18_R20_POSTSTOP_COMPARISON=BEGIN")
    for label, snap in snapshots.items():
        emit_snapshot(label, snap)
    emit_compaction_delta("R18", snapshots["R18_PRE"], snapshots["R18_POST"])
    emit_compaction_delta("R20", snapshots["R20_PRE"], snapshots["R20_POST"])
    emit_post_cross(snapshots["R18_POST"], snapshots["R20_POST"])
    print("ORCA_R18_R20_POSTSTOP_COMPARISON=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
