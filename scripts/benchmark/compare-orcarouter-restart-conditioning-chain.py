#!/usr/bin/env python3
"""Compare allocator conditioning across adjacent managed restart legs.

This analyzer is read-only. It consumes existing R11-style allocator-state
snapshots from a chronological sequence of experiment legs and reports how
Normal-zone high-order free capacity is split by migratetype at each baseline
and final snapshot. It also compares each leg final snapshot with the next leg
baseline to expose immediate carry-over versus state drift during idle gaps.
"""

from __future__ import annotations

import argparse
import dataclasses
import pathlib
import re

PAGE_SIZE = 4096
META_MONO_RE = re.compile(r"^monotonic_ns=(\d+)$", re.MULTILINE)
META_WALL_RE = re.compile(r"^wall=(.+)$", re.MULTILINE)
BUDDY_RE = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+)\s+(.+)$")
PAGETYPE_RE = re.compile(
    r"^Node\s+(\d+),\s+zone\s+(\S+),\s+type\s+(\S+)\s+(.+)$"
)
PAGEBLOCK_RE = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+)\s+(.+)$")


@dataclasses.dataclass(frozen=True)
class Snapshot:
    label: str
    kind: str
    path: pathlib.Path
    monotonic_ns: int
    wall: str
    buddy_ge4_mib: float
    pagetype_ge4_mib: dict[str, float]
    pagetype_order4: dict[str, int]
    pageblocks: dict[str, int]


def parse_count(token: str) -> int:
    if token == ">100000":
        return 100001
    return int(token)


def weighted_ge4_mib(values: list[int]) -> float:
    pages = sum(count * (1 << order) for order, count in enumerate(values) if order >= 4)
    return pages * PAGE_SIZE / (1024 * 1024)


def parse_buddy(text: str) -> dict[tuple[int, str], list[int]]:
    result: dict[tuple[int, str], list[int]] = {}
    for raw in text.splitlines():
        match = BUDDY_RE.match(raw.strip())
        if not match:
            continue
        values: list[int] = []
        for token in match.group(3).split():
            try:
                values.append(int(token))
            except ValueError:
                pass
        result[(int(match.group(1)), match.group(2))] = values
    return result


def parse_pagetype(
    text: str,
) -> tuple[dict[tuple[int, str, str], list[int]], dict[tuple[int, str], dict[str, int]]]:
    counts: dict[tuple[int, str, str], list[int]] = {}
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
            values: list[int] = []
            for token in match.group(4).split():
                try:
                    values.append(parse_count(token))
                except ValueError:
                    pass
            counts[(int(match.group(1)), match.group(2), match.group(3))] = values
            continue

        if in_blocks:
            block = PAGEBLOCK_RE.match(line)
            if block:
                values: list[int] = []
                for token in block.group(3).split():
                    try:
                        values.append(int(token))
                    except ValueError:
                        pass
                if block_types and len(values) >= len(block_types):
                    pageblocks[(int(block.group(1)), block.group(2))] = dict(
                        zip(block_types, values[: len(block_types)], strict=False)
                    )
    return counts, pageblocks


def find_snapshot(root: pathlib.Path, kind: str) -> pathlib.Path:
    matches = sorted((root / "allocator-state" / "events").glob(f"{kind}-*"))
    if len(matches) != 1:
        raise SystemExit(
            f"expected exactly one {kind} snapshot under {root}, found {len(matches)}"
        )
    return matches[0]


def load_snapshot(label: str, root: pathlib.Path, kind: str) -> Snapshot:
    snap = find_snapshot(root, kind)
    meta = (snap / "meta.txt").read_text(encoding="utf-8", errors="replace")
    mono_match = META_MONO_RE.search(meta)
    wall_match = META_WALL_RE.search(meta)
    if not mono_match:
        raise SystemExit(f"missing monotonic_ns in {snap / 'meta.txt'}")

    buddy_text = (snap / "proc-buddyinfo.txt").read_text(encoding="utf-8", errors="replace")
    pagetype_text = (snap / "proc-pagetypeinfo.txt").read_text(encoding="utf-8", errors="replace")

    buddy = parse_buddy(buddy_text)
    normal_buddy = buddy.get((0, "Normal"), [])
    counts, blocks = parse_pagetype(pagetype_text)

    pt_ge4: dict[str, float] = {}
    pt_o4: dict[str, int] = {}
    types = ("Unmovable", "Movable", "Reclaimable", "HighAtomic", "CMA", "Isolate")
    for migrate_type in types:
        values = counts.get((0, "Normal", migrate_type), [])
        pt_ge4[migrate_type] = weighted_ge4_mib(values)
        pt_o4[migrate_type] = values[4] if len(values) > 4 else 0

    return Snapshot(
        label=label,
        kind=kind,
        path=snap,
        monotonic_ns=int(mono_match.group(1)),
        wall=wall_match.group(1) if wall_match else "UNKNOWN",
        buddy_ge4_mib=weighted_ge4_mib(normal_buddy),
        pagetype_ge4_mib=pt_ge4,
        pagetype_order4=pt_o4,
        pageblocks=blocks.get((0, "Normal"), {}),
    )


def parse_leg(value: str) -> tuple[str, pathlib.Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("leg must be LABEL=PATH")
    label, raw_path = value.split("=", 1)
    if not label or not raw_path:
        raise argparse.ArgumentTypeError("leg must be LABEL=PATH")
    return label, pathlib.Path(raw_path)


def fmt_delta(value: float) -> str:
    return f"{value:+.3f}"


def emit_snapshot(snap: Snapshot) -> None:
    fields = [
        f"leg={snap.label}",
        f"kind={snap.kind}",
        f"monotonic_ns={snap.monotonic_ns}",
        f"wall={snap.wall}",
        f"normal_buddy_ge4_mib={snap.buddy_ge4_mib:.3f}",
    ]
    for migrate_type in ("Unmovable", "Movable", "Reclaimable", "HighAtomic"):
        fields.append(
            f"{migrate_type.lower()}_ge4_mib={snap.pagetype_ge4_mib.get(migrate_type, 0.0):.3f}"
        )
        fields.append(
            f"{migrate_type.lower()}_order4={snap.pagetype_order4.get(migrate_type, 0)}"
        )
    fields.append(f"unmovable_pageblocks={snap.pageblocks.get('Unmovable', 0)}")
    fields.append(f"movable_pageblocks={snap.pageblocks.get('Movable', 0)}")
    print("snapshot " + " ".join(fields))


def emit_transition(left: Snapshot, right: Snapshot) -> None:
    elapsed_s = (right.monotonic_ns - left.monotonic_ns) / 1_000_000_000
    print(
        "transition "
        f"from={left.label}:{left.kind} to={right.label}:{right.kind} "
        f"elapsed_s={elapsed_s:.3f} "
        f"buddy_delta_mib={fmt_delta(right.buddy_ge4_mib - left.buddy_ge4_mib)} "
        f"unmovable_delta_mib={fmt_delta(right.pagetype_ge4_mib['Unmovable'] - left.pagetype_ge4_mib['Unmovable'])} "
        f"movable_delta_mib={fmt_delta(right.pagetype_ge4_mib['Movable'] - left.pagetype_ge4_mib['Movable'])} "
        f"unmovable_order4_delta={right.pagetype_order4['Unmovable'] - left.pagetype_order4['Unmovable']:+d} "
        f"movable_order4_delta={right.pagetype_order4['Movable'] - left.pagetype_order4['Movable']:+d} "
        f"unmovable_pageblock_delta={right.pageblocks.get('Unmovable', 0) - left.pageblocks.get('Unmovable', 0):+d} "
        f"movable_pageblock_delta={right.pageblocks.get('Movable', 0) - left.pageblocks.get('Movable', 0):+d}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--leg",
        action="append",
        required=True,
        type=parse_leg,
        help="chronological LABEL=R11_EVIDENCE_ROOT; repeat for each leg",
    )
    args = parser.parse_args()

    if len(args.leg) < 2:
        raise SystemExit("at least two --leg entries are required")

    snapshots: list[tuple[Snapshot, Snapshot]] = []
    for label, root in args.leg:
        baseline = load_snapshot(label, root, "baseline")
        final = load_snapshot(label, root, "final")
        snapshots.append((baseline, final))

    print("ORCA_RESTART_CONDITIONING_CHAIN=BEGIN")
    for baseline, final in snapshots:
        emit_snapshot(baseline)
        emit_snapshot(final)
        emit_transition(baseline, final)

    print("ORCA_RESTART_CONDITIONING_BOUNDARIES=BEGIN")
    for index in range(len(snapshots) - 1):
        emit_transition(snapshots[index][1], snapshots[index + 1][0])
    print("ORCA_RESTART_CONDITIONING_BOUNDARIES=END")
    print("ORCA_RESTART_CONDITIONING_CHAIN=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
