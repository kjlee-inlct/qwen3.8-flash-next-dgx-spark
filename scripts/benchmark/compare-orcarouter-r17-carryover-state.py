#!/usr/bin/env python3
"""Compare R17 allocator snapshot composition across adjacent restarts.

This analyzer is read-only. It compares the baseline/final full snapshots from
R17 leg A and leg B, with emphasis on the Normal-zone high-order buddy pool,
pagetype composition, pageblock ownership, and zone watermarks. The main
cross-leg comparison is leg-A final -> leg-B baseline, which tests allocator
state continuity across the adjacent managed restart boundary.
"""

from __future__ import annotations

import argparse
import pathlib
import re
from dataclasses import dataclass

PAGE_SIZE = 4096
BUDDY_RE = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+)\s+(.+)$")
PAGETYPE_RE = re.compile(
    r"^Node\s+(\d+),\s+zone\s+(\S+),\s+type\s+(\S+)\s+(.+)$"
)
PAGEBLOCK_RE = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+)\s+(.+)$")
ZONE_HEADER_RE = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+)$")
META_MONO_RE = re.compile(r"^monotonic_ns=(\d+)$", re.MULTILINE)


@dataclass(frozen=True)
class Snapshot:
    path: pathlib.Path
    monotonic_ns: int | None
    buddy: dict[tuple[int, str], list[int]]
    pagetype: dict[tuple[int, str, str], list[int]]
    pageblocks: dict[tuple[int, str], dict[str, int]]
    zoneinfo: dict[tuple[int, str], dict[str, int]]


def parse_int_tokens(text: str) -> list[int]:
    values: list[int] = []
    for token in text.split():
        if token == ">100000":
            values.append(100001)
            continue
        try:
            values.append(int(token))
        except ValueError:
            pass
    return values


def parse_buddy(text: str) -> dict[tuple[int, str], list[int]]:
    result: dict[tuple[int, str], list[int]] = {}
    for raw in text.splitlines():
        match = BUDDY_RE.match(raw.strip())
        if match:
            result[(int(match.group(1)), match.group(2))] = parse_int_tokens(
                match.group(3)
            )
    return result


def parse_pagetype(
    text: str,
) -> tuple[dict[tuple[int, str, str], list[int]], dict[tuple[int, str], dict[str, int]]]:
    order_counts: dict[tuple[int, str, str], list[int]] = {}
    pageblocks: dict[tuple[int, str], dict[str, int]] = {}
    block_types: list[str] = []
    in_blocks = False

    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("Number of blocks type"):
            block_types = line.split()[4:]
            in_blocks = True
            continue

        match = PAGETYPE_RE.match(line)
        if match:
            order_counts[(int(match.group(1)), match.group(2), match.group(3))] = (
                parse_int_tokens(match.group(4))
            )
            continue

        if in_blocks:
            block = PAGEBLOCK_RE.match(line)
            if block:
                values = parse_int_tokens(block.group(3))
                if block_types and len(values) >= len(block_types):
                    pageblocks[(int(block.group(1)), block.group(2))] = dict(
                        zip(block_types, values[: len(block_types)], strict=False)
                    )
    return order_counts, pageblocks


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
            continue
        if len(parts) >= 2 and parts[0] in wanted:
            try:
                result[current][parts[0]] = int(parts[1])
            except ValueError:
                pass
    return result


def ge4_metrics(values: list[int]) -> tuple[int, int, float]:
    order4 = values[4] if len(values) > 4 else 0
    blocks = sum(values[4:]) if len(values) > 4 else 0
    pages = sum(
        count * (1 << order)
        for order, count in enumerate(values)
        if order >= 4
    )
    return order4, blocks, pages * PAGE_SIZE / (1024 * 1024)


def unique_snapshot(state: pathlib.Path, prefix: str) -> pathlib.Path:
    matches = sorted((state / "events").glob(f"{prefix}-*"))
    if len(matches) != 1:
        raise SystemExit(
            f"expected exactly one {prefix} snapshot under {state / 'events'}, "
            f"found {len(matches)}"
        )
    return matches[0]


def read_required(path: pathlib.Path) -> str:
    if not path.is_file():
        raise SystemExit(f"missing allocator snapshot file: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def load_snapshot(path: pathlib.Path) -> Snapshot:
    meta = read_required(path / "meta.txt")
    match = META_MONO_RE.search(meta)
    mono = int(match.group(1)) if match else None
    buddy = parse_buddy(read_required(path / "proc-buddyinfo.txt"))
    pagetype, pageblocks = parse_pagetype(
        read_required(path / "proc-pagetypeinfo.txt")
    )
    zoneinfo = parse_zoneinfo(read_required(path / "proc-zoneinfo.txt"))
    return Snapshot(path, mono, buddy, pagetype, pageblocks, zoneinfo)


def load_leg(root: pathlib.Path) -> tuple[Snapshot, Snapshot]:
    state = root / "allocator-state"
    if not state.is_dir():
        raise SystemExit(f"missing allocator-state directory: {state}")
    return (
        load_snapshot(unique_snapshot(state, "baseline")),
        load_snapshot(unique_snapshot(state, "final")),
    )


def emit_snapshot(label: str, snap: Snapshot) -> None:
    mono = snap.monotonic_ns if snap.monotonic_ns is not None else "NA"
    print(f"snapshot={label} monotonic_ns={mono} path={snap.path}")

    for (node, zone), values in sorted(snap.buddy.items()):
        order4, blocks, mib = ge4_metrics(values)
        print(
            f"snapshot_buddy={label} node={node} zone={zone} "
            f"order4_blocks={order4} order4plus_blocks={blocks} ge4_mib={mib:.3f}"
        )

    for (node, zone, migratetype), values in sorted(snap.pagetype.items()):
        order4, blocks, mib = ge4_metrics(values)
        print(
            f"snapshot_pagetype={label} node={node} zone={zone} type={migratetype} "
            f"order4_blocks={order4} order4plus_blocks={blocks} ge4_mib={mib:.3f}"
        )

    for (node, zone), values in sorted(snap.pageblocks.items()):
        fields = " ".join(f"{key}={value}" for key, value in values.items())
        print(f"snapshot_pageblocks={label} node={node} zone={zone} {fields}")

    for (node, zone), values in sorted(snap.zoneinfo.items()):
        fields = " ".join(
            f"{key}_pages={values[key]}"
            for key in ("free", "min", "low", "high", "managed", "cma")
            if key in values
        )
        if "free" in values and "low" in values:
            fields += f" free_minus_low_pages={values['free'] - values['low']}"
        print(f"snapshot_zone={label} node={node} zone={zone} {fields}".rstrip())


def pct_delta(left: float, right: float) -> str:
    if left == 0:
        return "NA"
    return f"{((right - left) / left) * 100:+.3f}"


def emit_carryover(a_final: Snapshot, b_baseline: Snapshot) -> None:
    keys = sorted(set(a_final.buddy) | set(b_baseline.buddy))
    for key in keys:
        left = a_final.buddy.get(key, [])
        right = b_baseline.buddy.get(key, [])
        _, _, left_mib = ge4_metrics(left)
        _, _, right_mib = ge4_metrics(right)
        print(
            f"carryover_buddy node={key[0]} zone={key[1]} "
            f"a_final_ge4_mib={left_mib:.3f} b_baseline_ge4_mib={right_mib:.3f} "
            f"delta_mib={right_mib - left_mib:+.3f} pct={pct_delta(left_mib, right_mib)}"
        )

    pkeys = sorted(set(a_final.pagetype) | set(b_baseline.pagetype))
    for key in pkeys:
        left = a_final.pagetype.get(key, [])
        right = b_baseline.pagetype.get(key, [])
        left_o4, _, left_mib = ge4_metrics(left)
        right_o4, _, right_mib = ge4_metrics(right)
        print(
            f"carryover_pagetype node={key[0]} zone={key[1]} type={key[2]} "
            f"a_final_order4={left_o4} b_baseline_order4={right_o4} "
            f"delta_order4={right_o4 - left_o4:+d} "
            f"a_final_ge4_mib={left_mib:.3f} b_baseline_ge4_mib={right_mib:.3f} "
            f"delta_ge4_mib={right_mib - left_mib:+.3f}"
        )

    block_keys = sorted(set(a_final.pageblocks) | set(b_baseline.pageblocks))
    for key in block_keys:
        left = a_final.pageblocks.get(key, {})
        right = b_baseline.pageblocks.get(key, {})
        for migratetype in sorted(set(left) | set(right)):
            lv = left.get(migratetype, 0)
            rv = right.get(migratetype, 0)
            print(
                f"carryover_pageblock node={key[0]} zone={key[1]} type={migratetype} "
                f"a_final={lv} b_baseline={rv} delta={rv - lv:+d}"
            )

    zone_keys = sorted(set(a_final.zoneinfo) | set(b_baseline.zoneinfo))
    for key in zone_keys:
        left = a_final.zoneinfo.get(key, {})
        right = b_baseline.zoneinfo.get(key, {})
        fields: list[str] = []
        for name in ("free", "low", "high"):
            if name in left or name in right:
                lv = left.get(name, 0)
                rv = right.get(name, 0)
                fields.append(f"a_final_{name}={lv}")
                fields.append(f"b_baseline_{name}={rv}")
                fields.append(f"delta_{name}={rv - lv:+d}")
        print(f"carryover_zone node={key[0]} zone={key[1]} {' '.join(fields)}".rstrip())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--leg-a", required=True)
    parser.add_argument("--leg-b", required=True)
    args = parser.parse_args()

    a_baseline, a_final = load_leg(pathlib.Path(args.leg_a))
    b_baseline, b_final = load_leg(pathlib.Path(args.leg_b))

    print("R17_CARRYOVER_STATE_COMPARISON=BEGIN")
    emit_snapshot("A_BASELINE", a_baseline)
    emit_snapshot("A_FINAL", a_final)
    emit_snapshot("B_BASELINE", b_baseline)
    emit_snapshot("B_FINAL", b_final)
    print("R17_CARRYOVER_BOUNDARY=A_FINAL_TO_B_BASELINE")
    emit_carryover(a_final, b_baseline)
    print("R17_CARRYOVER_STATE_COMPARISON=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
