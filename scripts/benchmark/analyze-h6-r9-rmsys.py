#!/usr/bin/env python3
"""Recover and deeply analyze preserved H6 R9 RM sysmem trace evidence.

The R9 model run completed, but the runner's inline post-processing hit a
Python syntax error after trace collection.  This analyzer is intentionally
read-only with respect to the original trace and works in one streaming pass
through allocator-trace.txt so a large decoded trace does not need to be held
in memory.
"""

from __future__ import annotations

import argparse
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_OUT = Path("/tmp/hybrid-6.17-kv16-rmsys-r9-20261002")

TRACE_RE = re.compile(
    r"^\s*(?P<task>.+)-(?P<pid>\d+)\s+\[(?P<cpu>\d+)\]\s+"
    r"(?P<ts>\d+\.\d+):\s+(?P<event>[A-Za-z0-9_]+):\s*(?P<body>.*)$"
)
RM_RE = re.compile(
    r"\[\s*(?P<ts>\d+(?:\.\d+)?)\].*"
    r"(?:NV_ERR_NO_MEMORY|_memdescAllocInternal)"
)
FIELD_RE = re.compile(r"(?P<key>[A-Za-z_]+)=(?P<value>0x[0-9A-Fa-f]+|-?\d+)")


@dataclass(frozen=True)
class Event:
    task: str
    pid: int
    cpu: int
    ts: float
    name: str
    body: str
    line: str


@dataclass(frozen=True)
class OuterCall:
    task: str
    pid: int
    start: float
    end: float
    page_count: int
    page_size: int
    contiguous: int
    cache_type: int
    zeroed: int
    unencrypted: int
    node_id: int
    ret: int
    entry_line: str
    ret_line: str


@dataclass
class SysStats:
    event_counts: Counter[str] = field(default_factory=Counter)
    alloc_pfns: Counter[int] = field(default_factory=Counter)
    free_pfns: Counter[int] = field(default_factory=Counter)
    compaction_orders: Counter[int] = field(default_factory=Counter)
    reclaim_orders: Counter[int] = field(default_factory=Counter)
    extfrag_pairs: Counter[tuple[int, int]] = field(default_factory=Counter)
    extfrag_ownership: int = 0
    extfrag_gap_ge_2: int = 0


@dataclass(frozen=True)
class SysCall:
    task: str
    pid: int
    start: float
    end: float
    at: int
    ret: int
    stats: SysStats
    entry_line: str
    ret_line: str


@dataclass
class ActiveSys:
    entry: Event
    at: int
    stats: SysStats = field(default_factory=SysStats)


def parse_int(raw: str) -> int:
    return int(raw, 16 if raw.lower().startswith("0x") else 10)


def parse_fields(body: str) -> dict[str, int]:
    return {
        match.group("key"): parse_int(match.group("value"))
        for match in FIELD_RE.finditer(body)
    }


def parse_event(line: str) -> Event | None:
    match = TRACE_RE.match(line)
    if not match:
        return None
    return Event(
        task=match.group("task").strip(),
        pid=int(match.group("pid")),
        cpu=int(match.group("cpu")),
        ts=float(match.group("ts")),
        name=match.group("event"),
        body=match.group("body"),
        line=line.rstrip("\n"),
    )


def first_rm(path: Path) -> tuple[float, str]:
    for line in path.read_text(errors="replace").splitlines():
        match = RM_RE.search(line)
        if match:
            return float(match.group("ts")), line
    raise SystemExit(f"no RM NV_ERR_NO_MEMORY timestamp in {path}")


def host_page_size() -> int:
    value = os.sysconf("SC_PAGE_SIZE")
    if not isinstance(value, int) or value <= 0:
        raise SystemExit(f"invalid host page size: {value!r}")
    return value


def get_order(size: int, page_size: int) -> int:
    if size <= page_size:
        return 0
    pages = (size + page_size - 1) // page_size
    return (pages - 1).bit_length()


def update_sys_stats(stats: SysStats, event: Event) -> None:
    stats.event_counts[event.name] += 1
    fields = parse_fields(event.body)

    if event.name == "mm_page_alloc":
        pfn = fields.get("pfn")
        if pfn is not None:
            stats.alloc_pfns[pfn] += 1
    elif event.name == "mm_page_free":
        pfn = fields.get("pfn")
        if pfn is not None:
            stats.free_pfns[pfn] += 1
    elif event.name == "mm_compaction_try_to_compact_pages":
        order = fields.get("order")
        if order is not None:
            stats.compaction_orders[order] += 1
    elif event.name == "mm_vmscan_direct_reclaim_begin":
        order = fields.get("order")
        if order is not None:
            stats.reclaim_orders[order] += 1
    elif event.name == "mm_page_alloc_extfrag":
        alloc_order = fields.get("alloc_order")
        fallback_order = fields.get("fallback_order")
        if alloc_order is not None and fallback_order is not None:
            stats.extfrag_pairs[(alloc_order, fallback_order)] += 1
            if fields.get("change_ownership") == 1:
                stats.extfrag_ownership += 1
            if fallback_order - alloc_order >= 2:
                stats.extfrag_gap_ge_2 += 1


def stream_trace(path: Path) -> tuple[list[OuterCall], list[SysCall], Counter[str], int, int]:
    outer_stacks: dict[int, list[Event]] = defaultdict(list)
    sys_stacks: dict[int, list[ActiveSys]] = defaultdict(list)
    outer_calls: list[OuterCall] = []
    sys_calls: list[SysCall] = []
    global_counts: Counter[str] = Counter()
    trace_lines = 0
    lost_markers = 0

    with path.open("r", errors="replace") as handle:
        for raw in handle:
            trace_lines += 1
            if "LOST EVENTS" in raw.upper():
                lost_markers += 1
            event = parse_event(raw)
            if event is None:
                continue

            global_counts[event.name] += 1

            # Attribute Linux allocator activity to every active sysmem call on
            # the same task. nv_alloc_system_pages is not expected to recurse,
            # but updating the full stack keeps the accounting safe if it does.
            for active in sys_stacks[event.pid]:
                update_sys_stats(active.stats, event)

            if event.name == "nv_alloc_pages_entry":
                outer_stacks[event.pid].append(event)
                continue

            if event.name == "nv_alloc_pages_ret":
                if not outer_stacks[event.pid]:
                    continue
                entry = outer_stacks[event.pid].pop()
                ef = parse_fields(entry.body)
                rf = parse_fields(event.body)
                required = (
                    "page_count",
                    "page_size",
                    "contiguous",
                    "cache_type",
                    "zeroed",
                    "unencrypted",
                    "node_id",
                )
                if any(key not in ef for key in required) or "ret" not in rf:
                    continue
                outer_calls.append(
                    OuterCall(
                        task=entry.task,
                        pid=entry.pid,
                        start=entry.ts,
                        end=event.ts,
                        page_count=ef["page_count"],
                        page_size=ef["page_size"],
                        contiguous=ef["contiguous"],
                        cache_type=ef["cache_type"],
                        zeroed=ef["zeroed"],
                        unencrypted=ef["unencrypted"],
                        node_id=ef["node_id"],
                        ret=rf["ret"],
                        entry_line=entry.line,
                        ret_line=event.line,
                    )
                )
                continue

            if event.name == "nv_alloc_system_pages_entry":
                fields = parse_fields(event.body)
                if "at" in fields:
                    sys_stacks[event.pid].append(ActiveSys(entry=event, at=fields["at"]))
                continue

            if event.name == "nv_alloc_system_pages_ret":
                if not sys_stacks[event.pid]:
                    continue
                active = sys_stacks[event.pid].pop()
                fields = parse_fields(event.body)
                if "ret" not in fields:
                    continue
                sys_calls.append(
                    SysCall(
                        task=active.entry.task,
                        pid=active.entry.pid,
                        start=active.entry.ts,
                        end=event.ts,
                        at=active.at,
                        ret=fields["ret"],
                        stats=active.stats,
                        entry_line=active.entry.line,
                        ret_line=event.line,
                    )
                )

    outer_calls.sort(key=lambda call: call.start)
    sys_calls.sort(key=lambda call: call.start)
    return outer_calls, sys_calls, global_counts, trace_lines, lost_markers


def fmt_counter(counter: Counter[object], limit: int = 12) -> str:
    if not counter:
        return "NONE"
    return ", ".join(f"{key}={value}" for key, value in counter.most_common(limit))


def print_outer(label: str, call: OuterCall, rm_ts: float, page_size: int) -> None:
    order = get_order(call.page_size, page_size)
    chunk_bytes = page_size << order
    total_bytes = call.page_count * page_size
    chunks = (total_bytes + chunk_bytes - 1) // chunk_bytes
    print(f"=== {label} ===")
    print(f"task={call.task} pid={call.pid}")
    print(f"start={call.start:.6f} delta_from_rm={call.start-rm_ts:+.9f}s")
    print(f"end={call.end:.6f} delta_from_rm={call.end-rm_ts:+.9f}s")
    print(f"duration_ms={(call.end-call.start)*1000:.3f}")
    print(f"page_count={call.page_count}")
    print(f"requested_page_size={call.page_size}")
    print(f"host_page_size={page_size}")
    print(f"total_gib={total_bytes/(1024**3):.6f}")
    print(f"derived_get_order={order}")
    print(f"allocation_chunk_bytes={chunk_bytes}")
    print(f"expected_chunk_count={chunks}")
    print(f"contiguous={call.contiguous}")
    print(f"cache_type={call.cache_type}")
    print(f"zeroed={call.zeroed}")
    print(f"unencrypted={call.unencrypted}")
    print(f"node_id={call.node_id}")
    print(f"ret=0x{call.ret:x}({call.ret})")
    print(f"entry :: {call.entry_line}")
    print(f"return :: {call.ret_line}")
    print()


def print_sys(label: str, call: SysCall, rm_ts: float, expected_chunks: int | None) -> None:
    stats = call.stats
    alloc_events = stats.event_counts["mm_page_alloc"]
    free_events = stats.event_counts["mm_page_free"]
    matched_pfns = sum((stats.alloc_pfns & stats.free_pfns).values())
    remaining_pfns = sum((stats.alloc_pfns - stats.free_pfns).values())

    print(f"=== {label} ===")
    print(f"task={call.task} pid={call.pid}")
    print(f"start={call.start:.6f} delta_from_rm={call.start-rm_ts:+.9f}s")
    print(f"end={call.end:.6f} delta_from_rm={call.end-rm_ts:+.9f}s")
    print(f"duration_ms={(call.end-call.start)*1000:.3f}")
    print(f"at=0x{call.at:x}")
    print(f"ret=0x{call.ret:x}({call.ret})")
    print(f"order4_page_alloc_events={alloc_events}")
    print(f"order4_page_free_events={free_events}")
    print(f"allocated_then_freed_same_pfn={matched_pfns}")
    print(f"allocated_not_freed_same_pfn={remaining_pfns}")
    if expected_chunks is not None:
        print(f"expected_order4_chunks={expected_chunks}")
        if call.ret == 81 and alloc_events < expected_chunks:
            print(f"candidate_failed_chunk_index={alloc_events + 1}")
        else:
            print("candidate_failed_chunk_index=UNRESOLVED")
    print(f"compaction_try={stats.event_counts['mm_compaction_try_to_compact_pages']}")
    print(f"compaction_orders=[{fmt_counter(stats.compaction_orders)}]")
    print(f"direct_reclaim_begin={stats.event_counts['mm_vmscan_direct_reclaim_begin']}")
    print(f"reclaim_orders=[{fmt_counter(stats.reclaim_orders)}]")
    print(f"extfrag={stats.event_counts['mm_page_alloc_extfrag']}")
    print(f"extfrag_pairs=[{fmt_counter(stats.extfrag_pairs)}]")
    print(f"extfrag_ownership={stats.extfrag_ownership}")
    print(f"extfrag_gap_ge_2={stats.extfrag_gap_ge_2}")
    print(f"entry :: {call.entry_line}")
    print(f"return :: {call.ret_line}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", nargs="?", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    out = args.evidence
    trace_path = out / "allocator-trace.txt"
    kernel_path = out / "kernel-errors-monotonic.txt"
    for path in (trace_path, kernel_path):
        if not path.is_file():
            raise SystemExit(f"missing evidence: {path}")

    page_size = host_page_size()
    rm_ts, rm_line = first_rm(kernel_path)
    outer_calls, sys_calls, counts, trace_lines, lost = stream_trace(trace_path)

    failed_outer = [call for call in outer_calls if call.ret == 81]
    failed_sys = [call for call in sys_calls if call.ret == 81]

    print("=== R9 RM SYS RECOVERY ANALYSIS ===")
    print(f"evidence={out}")
    print(f"host_page_size={page_size}")
    print(f"trace_lines={trace_lines}")
    print(f"lost_event_markers={lost}")
    print(f"paired_nv_alloc_pages_calls={len(outer_calls)}")
    print(f"paired_nv_alloc_system_pages_calls={len(sys_calls)}")
    print(f"nv_alloc_pages_nv_oom_returns={len(failed_outer)}")
    print(f"nv_alloc_system_pages_nv_oom_returns={len(failed_sys)}")
    print(f"rm_monotonic={rm_ts:.6f}")
    print(f"rm_line={rm_line}")
    print()
    print("=== GLOBAL TRACE COUNTS ===")
    for name in (
        "nv_alloc_pages_entry",
        "nv_alloc_pages_ret",
        "nv_alloc_system_pages_entry",
        "nv_alloc_system_pages_ret",
        "mm_page_alloc",
        "mm_page_free",
        "mm_page_alloc_extfrag",
        "mm_compaction_try_to_compact_pages",
        "mm_vmscan_direct_reclaim_begin",
    ):
        print(f"{name}={counts[name]}")
    print()

    if not failed_outer:
        print("FAILED_OUTER_CALL=NONE")
        print("R9_RECOVERY_CLASSIFICATION=HOST_FAIL_WITHOUT_OUTER_NV_ALLOC_0X51")
        return 0

    for index, outer in enumerate(failed_outer, 1):
        print_outer(f"FAILED_NV_ALLOC_PAGES_{index}", outer, rm_ts, page_size)
        order = get_order(outer.page_size, page_size)
        chunk_bytes = page_size << order
        total_bytes = outer.page_count * page_size
        expected_chunks = (total_bytes + chunk_bytes - 1) // chunk_bytes

        nested = [
            call
            for call in sys_calls
            if call.pid == outer.pid
            and outer.start <= call.start
            and call.end <= outer.end
        ]
        if not nested:
            print(f"FAILED_NV_ALLOC_PAGES_{index}_NESTED_SYS=NONE")
            print()
        else:
            for sys_index, sys_call in enumerate(nested, 1):
                print_sys(
                    f"FAILED_NV_ALLOC_PAGES_{index}_NESTED_SYS_{sys_index}",
                    sys_call,
                    rm_ts,
                    expected_chunks if outer.contiguous == 0 and order == 4 else None,
                )

        # Show the immediate next outer call on the same worker. R8 suggested
        # this is the same total request retried at order 0.
        later = [
            call
            for call in outer_calls
            if call.pid == outer.pid and call.start >= outer.end
        ]
        if later:
            print_outer(
                f"FAILED_NV_ALLOC_PAGES_{index}_NEXT_SAME_THREAD",
                later[0],
                rm_ts,
                page_size,
            )

    if lost:
        conclusion = "TRACE_HAS_LOST_EVENT_MARKERS_DO_NOT_INFER_EXACT_CHUNK_INDEX"
    elif failed_sys:
        conclusion = "RM_SYSMEM_FAILURE_CAPTURED_WITH_ORDER4_ALLOC_FREE_ACCOUNTING"
    else:
        conclusion = "OUTER_NV_ALLOC_FAILURE_CAPTURED_BUT_SYS_RETURN_0X51_NOT_OBSERVED"
    print("=== RECOVERY CLASSIFICATION ===")
    print(f"R9_RECOVERY_CLASSIFICATION={conclusion}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
