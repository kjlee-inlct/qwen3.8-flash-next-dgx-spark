#!/usr/bin/env python3
"""Map a preserved R11 failed order-4 interval to Linux zone/migratetype.

This is a read-only post-processor for R11 evidence. It streams the existing
allocator trace, selects the first failed nv_alloc_system_pages interval from
rmsys-analysis.txt, maps order-4 allocation/free PFNs to zone boundaries from
the RM-triggered /proc/zoneinfo snapshot, and summarizes trace migratetype and
external-fragmentation ownership/fallback fields.
"""

from __future__ import annotations

import argparse
import collections
import dataclasses
import pathlib
import re

PAGE_SIZE = 4096
ORDER4_BYTES = PAGE_SIZE << 4

TRACE_RE = re.compile(
    r"^\s*(?P<task>.+)-(?P<pid>\d+)\s+\[(?P<cpu>\d+)\]\s+"
    r"(?P<ts>\d+\.\d+):\s+(?P<event>[A-Za-z0-9_]+):\s*(?P<body>.*)$"
)
FIELD_RE = re.compile(r"(?P<key>[A-Za-z_]+)=(?P<value>0x[0-9A-Fa-f]+|-?\d+)")
SECTION_RE = re.compile(r"^=== FAILED_NV_ALLOC_PAGES_1_NESTED_SYS_1 ===$")
PID_RE = re.compile(r"^task=(.*?) pid=(\d+)$")
START_RE = re.compile(r"^start=([0-9.]+)")
END_RE = re.compile(r"^end=([0-9.]+)")
ZONE_HEADER_RE = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+)$")
START_PFN_RE = re.compile(r"^start_pfn:\s*(\d+)$")
SPANNED_RE = re.compile(r"^spanned\s+(\d+)$")

MIGRATE_TYPES = {
    0: "Unmovable",
    1: "Movable",
    2: "Reclaimable",
    3: "HighAtomic",
    4: "CMA",
    5: "Isolate",
}


@dataclasses.dataclass(frozen=True)
class FailedInterval:
    task: str
    pid: int
    start: float
    end: float


@dataclasses.dataclass(frozen=True)
class ZoneRange:
    node: int
    zone: str
    start_pfn: int
    spanned: int

    @property
    def end_pfn(self) -> int:
        return self.start_pfn + self.spanned

    def contains(self, pfn: int) -> bool:
        return self.start_pfn <= pfn < self.end_pfn


def parse_int(raw: str) -> int:
    return int(raw, 16 if raw.lower().startswith("0x") else 10)


def parse_fields(body: str) -> dict[str, int]:
    return {
        match.group("key"): parse_int(match.group("value"))
        for match in FIELD_RE.finditer(body)
    }


def parse_failed_interval(path: pathlib.Path) -> FailedInterval:
    in_section = False
    task = ""
    pid: int | None = None
    start: float | None = None
    end: float | None = None

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if SECTION_RE.match(raw):
            in_section = True
            continue
        if not in_section:
            continue
        if raw.startswith("=== "):
            break
        match = PID_RE.match(raw)
        if match:
            task = match.group(1)
            pid = int(match.group(2))
            continue
        match = START_RE.match(raw)
        if match:
            start = float(match.group(1))
            continue
        match = END_RE.match(raw)
        if match:
            end = float(match.group(1))
            continue

    if not task or pid is None or start is None or end is None:
        raise SystemExit(f"failed to parse first failed sysmem interval from {path}")
    return FailedInterval(task=task, pid=pid, start=start, end=end)


def parse_zone_ranges(text: str) -> list[ZoneRange]:
    result: list[ZoneRange] = []
    current_node: int | None = None
    current_zone = ""
    start_pfn: int | None = None
    spanned: int | None = None

    def flush() -> None:
        nonlocal current_node, current_zone, start_pfn, spanned
        if current_node is not None and current_zone and start_pfn is not None and spanned is not None:
            result.append(
                ZoneRange(
                    node=current_node,
                    zone=current_zone,
                    start_pfn=start_pfn,
                    spanned=spanned,
                )
            )
        start_pfn = None
        spanned = None

    for raw in text.splitlines():
        line = raw.strip()
        match = ZONE_HEADER_RE.match(line)
        if match:
            flush()
            current_node = int(match.group(1))
            current_zone = match.group(2)
            continue
        match = START_PFN_RE.match(line)
        if match and current_node is not None:
            start_pfn = int(match.group(1))
            continue
        match = SPANNED_RE.match(line)
        if match and current_node is not None:
            spanned = int(match.group(1))
            continue
    flush()
    return result


def zone_for_pfn(ranges: list[ZoneRange], pfn: int) -> str:
    matches = [item for item in ranges if item.contains(pfn)]
    if not matches:
        return "UNMAPPED"
    matches.sort(key=lambda item: item.spanned)
    chosen = matches[0]
    return f"node{chosen.node}:{chosen.zone}"


def migrate_name(value: int | None) -> str:
    if value is None:
        return "MISSING"
    return f"{value}:{MIGRATE_TYPES.get(value, 'UNKNOWN')}"


def find_event_zoneinfo(state_root: pathlib.Path) -> pathlib.Path:
    candidates = sorted((state_root / "events").glob("rm-oom-*/proc-zoneinfo.txt"))
    if not candidates:
        raise SystemExit(f"no RM event zoneinfo snapshot under {state_root / 'events'}")
    return candidates[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()

    root = pathlib.Path(args.evidence)
    r10b = root / "r10b"
    analysis_path = r10b / "rmsys-analysis.txt"
    trace_path = r10b / "allocator-trace.txt"
    state_root = root / "allocator-state"
    for path in (analysis_path, trace_path):
        if not path.is_file():
            raise SystemExit(f"missing evidence file: {path}")

    interval = parse_failed_interval(analysis_path)
    zone_path = find_event_zoneinfo(state_root)
    zone_ranges = parse_zone_ranges(zone_path.read_text(encoding="utf-8", errors="replace"))
    if not zone_ranges:
        raise SystemExit(f"failed to parse zone PFN ranges from {zone_path}")

    alloc_pfns: collections.Counter[int] = collections.Counter()
    free_pfns: collections.Counter[int] = collections.Counter()
    alloc_zones: collections.Counter[str] = collections.Counter()
    free_zones: collections.Counter[str] = collections.Counter()
    alloc_migrate: collections.Counter[str] = collections.Counter()
    free_migrate: collections.Counter[str] = collections.Counter()
    extfrag_pairs: collections.Counter[tuple[str, str]] = collections.Counter()
    extfrag_change_pairs: collections.Counter[tuple[str, str]] = collections.Counter()
    extfrag_fallback_orders: collections.Counter[tuple[int, int]] = collections.Counter()
    matching_trace_events = 0

    with trace_path.open(encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            match = TRACE_RE.match(raw)
            if not match:
                continue
            pid = int(match.group("pid"))
            if pid != interval.pid:
                continue
            ts = float(match.group("ts"))
            if ts < interval.start or ts > interval.end:
                continue
            event = match.group("event")
            if event not in {"mm_page_alloc", "mm_page_free", "mm_page_alloc_extfrag"}:
                continue
            fields = parse_fields(match.group("body"))
            matching_trace_events += 1

            if event == "mm_page_alloc":
                pfn = fields.get("pfn")
                order = fields.get("order")
                if pfn is None or order != 4:
                    continue
                alloc_pfns[pfn] += 1
                alloc_zones[zone_for_pfn(zone_ranges, pfn)] += 1
                alloc_migrate[migrate_name(fields.get("migratetype"))] += 1
                continue

            if event == "mm_page_free":
                pfn = fields.get("pfn")
                order = fields.get("order")
                if pfn is None or order != 4:
                    continue
                free_pfns[pfn] += 1
                free_zones[zone_for_pfn(zone_ranges, pfn)] += 1
                free_migrate[migrate_name(fields.get("migratetype"))] += 1
                continue

            alloc_mt = migrate_name(fields.get("alloc_migratetype"))
            fallback_mt = migrate_name(fields.get("fallback_migratetype"))
            extfrag_pairs[(alloc_mt, fallback_mt)] += 1
            if fields.get("change_ownership") == 1:
                extfrag_change_pairs[(alloc_mt, fallback_mt)] += 1
            alloc_order = fields.get("alloc_order")
            fallback_order = fields.get("fallback_order")
            if alloc_order is not None and fallback_order is not None:
                extfrag_fallback_orders[(alloc_order, fallback_order)] += 1

    rolled_back = alloc_pfns & free_pfns
    remaining = alloc_pfns - free_pfns
    rollback_zones: collections.Counter[str] = collections.Counter()
    for pfn, count in rolled_back.items():
        rollback_zones[zone_for_pfn(zone_ranges, pfn)] += count

    print("R11_ZONE_MIGRATETYPE_ANALYSIS=FAILED_INTERVAL_MAPPED")
    print(f"task={interval.task} pid={interval.pid}")
    print(f"start={interval.start:.6f} end={interval.end:.6f}")
    print(f"zoneinfo_source={zone_path}")
    for item in zone_ranges:
        print(
            f"zone_range node={item.node} zone={item.zone} start_pfn={item.start_pfn} "
            f"end_pfn={item.end_pfn} spanned={item.spanned}"
        )
    print(f"matching_trace_events={matching_trace_events}")
    print(f"order4_alloc_events={sum(alloc_pfns.values())}")
    print(f"order4_free_events={sum(free_pfns.values())}")
    print(f"rolled_back_same_pfn={sum(rolled_back.values())}")
    print(f"remaining_allocated_same_pfn={sum(remaining.values())}")
    print(f"rollback_mib={sum(rolled_back.values()) * ORDER4_BYTES / (1024 * 1024):.4f}")

    for label, counter in (
        ("alloc_zone", alloc_zones),
        ("free_zone", free_zones),
        ("rollback_zone", rollback_zones),
        ("alloc_migratetype", alloc_migrate),
        ("free_migratetype", free_migrate),
    ):
        if not counter:
            print(f"{label}=NONE")
            continue
        for key, count in counter.most_common():
            print(f"{label} value={key} count={count}")

    if extfrag_pairs:
        for (alloc_mt, fallback_mt), count in extfrag_pairs.most_common():
            print(
                f"extfrag_migratetype alloc={alloc_mt} fallback={fallback_mt} count={count}"
            )
    else:
        print("extfrag_migratetype=NONE")

    if extfrag_change_pairs:
        for (alloc_mt, fallback_mt), count in extfrag_change_pairs.most_common():
            print(
                f"extfrag_change_ownership alloc={alloc_mt} fallback={fallback_mt} count={count}"
            )
    else:
        print("extfrag_change_ownership=NONE")

    for (alloc_order, fallback_order), count in extfrag_fallback_orders.most_common():
        print(
            f"extfrag_order_pair alloc_order={alloc_order} fallback_order={fallback_order} count={count}"
        )

    mapped_allocs = sum(count for key, count in alloc_zones.items() if key != "UNMAPPED")
    total_allocs = sum(alloc_zones.values())
    if total_allocs:
        print(f"zone_mapping_coverage={mapped_allocs}/{total_allocs}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
