#!/usr/bin/env python3
"""Deep analysis of the preserved H6 R8 nv_alloc_pages failure episode.

This script reads only the already-decoded R8 trace and kernel monotonic log.
It does not rerun the model and does not mutate the original trace evidence.

It pairs nv_alloc_pages entry/return events per thread, identifies the call
spanning the first RM NV_ERR_NO_MEMORY log, the first failed outer call after
that log, and the immediate next call on the same thread.  For each selected
call interval it summarizes Linux compaction/reclaim/extfrag activity.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

DEFAULT_OUT = Path("/tmp/hybrid-6.17-kv16-rmuvm-r8-20261001")

TRACE_RE = re.compile(
    r"^\s*(?P<task>.+)-(?P<pid>\d+)\s+\[(?P<cpu>\d+)\]\s+"
    r"(?P<ts>\d+\.\d+):\s+(?P<event>[A-Za-z0-9_]+):\s*(?P<body>.*)$"
)
RM_RE = re.compile(
    r"\[\s*(?P<ts>\d+(?:\.\d+)?)\].*"
    r"(?:NV_ERR_NO_MEMORY|_memdescAllocInternal)"
)
FIELD_RE = re.compile(r"(?P<key>[A-Za-z_]+)=(?P<value>0x[0-9A-Fa-f]+|-?\d+)")
ORDER_RE = re.compile(r"\border=(?P<order>\d+)\b")
ALLOC_ORDER_RE = re.compile(r"\balloc_order=(?P<value>\d+)\b")
FALLBACK_ORDER_RE = re.compile(r"\bfallback_order=(?P<value>\d+)\b")
OWNERSHIP_RE = re.compile(r"\bchange_ownership=(?P<value>[01])\b")


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
class NvAllocCall:
    task: str
    pid: int
    entry_cpu: int
    ret_cpu: int
    start: float
    end: float
    page_count: int
    page_size: int
    contiguous: int
    ret: int
    entry_line: str
    ret_line: str

    @property
    def duration(self) -> float:
        return self.end - self.start

    @property
    def logical_bytes(self) -> int:
        return self.page_count * self.page_size

    @property
    def logical_gib(self) -> float:
        return self.logical_bytes / (1024**3)


def parse_int(raw: str) -> int:
    return int(raw, 16 if raw.lower().startswith("0x") else 10)


def parse_fields(body: str) -> dict[str, int]:
    return {
        match.group("key"): parse_int(match.group("value"))
        for match in FIELD_RE.finditer(body)
    }


def parse_events(path: Path) -> list[Event]:
    events: list[Event] = []
    for line in path.read_text(errors="replace").splitlines():
        match = TRACE_RE.match(line)
        if not match:
            continue
        events.append(
            Event(
                task=match.group("task").strip(),
                pid=int(match.group("pid")),
                cpu=int(match.group("cpu")),
                ts=float(match.group("ts")),
                name=match.group("event"),
                body=match.group("body"),
                line=line,
            )
        )
    return events


def first_rm_timestamp(path: Path) -> tuple[float, str]:
    for line in path.read_text(errors="replace").splitlines():
        match = RM_RE.search(line)
        if match:
            return float(match.group("ts")), line
    raise SystemExit(f"no RM NV_ERR_NO_MEMORY timestamp found in {path}")


def pair_nv_alloc_calls(events: list[Event]) -> list[NvAllocCall]:
    # nv_alloc_pages is not expected to recurse on the same task, but a stack
    # also handles that case correctly for kretprobe pairing.
    stacks: dict[int, list[Event]] = defaultdict(list)
    calls: list[NvAllocCall] = []

    for event in events:
        if event.name == "nv_alloc_pages_entry":
            stacks[event.pid].append(event)
            continue

        if event.name != "nv_alloc_pages_ret":
            continue

        if not stacks[event.pid]:
            continue

        entry = stacks[event.pid].pop()
        entry_fields = parse_fields(entry.body)
        ret_fields = parse_fields(event.body)

        required = ("page_count", "page_size", "contiguous")
        if any(key not in entry_fields for key in required) or "ret" not in ret_fields:
            continue

        calls.append(
            NvAllocCall(
                task=entry.task,
                pid=entry.pid,
                entry_cpu=entry.cpu,
                ret_cpu=event.cpu,
                start=entry.ts,
                end=event.ts,
                page_count=entry_fields["page_count"],
                page_size=entry_fields["page_size"],
                contiguous=entry_fields["contiguous"],
                ret=ret_fields["ret"],
                entry_line=entry.line,
                ret_line=event.line,
            )
        )

    return sorted(calls, key=lambda call: call.start)


def order_hist(events: list[Event], name: str) -> Counter[int]:
    result: Counter[int] = Counter()
    for event in events:
        if event.name != name:
            continue
        match = ORDER_RE.search(event.body)
        if match:
            result[int(match.group("order"))] += 1
    return result


def extfrag_stats(events: list[Event]) -> dict[str, object]:
    pairs: Counter[tuple[int, int]] = Counter()
    alloc_orders: Counter[int] = Counter()
    ownership = 0
    gap_ge_2 = 0
    parsed = 0

    for event in events:
        if event.name != "mm_page_alloc_extfrag":
            continue

        alloc_match = ALLOC_ORDER_RE.search(event.body)
        fallback_match = FALLBACK_ORDER_RE.search(event.body)
        if not alloc_match or not fallback_match:
            continue

        alloc_order = int(alloc_match.group("value"))
        fallback_order = int(fallback_match.group("value"))
        parsed += 1
        alloc_orders[alloc_order] += 1
        pairs[(alloc_order, fallback_order)] += 1

        ownership_match = OWNERSHIP_RE.search(event.body)
        if ownership_match and ownership_match.group("value") == "1":
            ownership += 1
        if fallback_order - alloc_order >= 2:
            gap_ge_2 += 1

    return {
        "parsed": parsed,
        "alloc_orders": alloc_orders,
        "pairs": pairs,
        "ownership": ownership,
        "gap_ge_2": gap_ge_2,
    }


def fmt_counter(counter: Counter[object], limit: int = 12) -> str:
    if not counter:
        return "NONE"
    return ", ".join(
        f"{key}={value}" for key, value in counter.most_common(limit)
    )


def events_between(events: list[Event], start: float, end: float) -> list[Event]:
    return [event for event in events if start <= event.ts <= end]


def print_call(label: str, call: NvAllocCall, rm_ts: float, events: list[Event]) -> None:
    interval = events_between(events, call.start, call.end)
    names = Counter(event.name for event in interval)
    compaction_orders = order_hist(interval, "mm_compaction_try_to_compact_pages")
    reclaim_orders = order_hist(interval, "mm_vmscan_direct_reclaim_begin")
    extfrag = extfrag_stats(interval)

    print(f"=== {label} ===")
    print(f"task={call.task} pid={call.pid}")
    print(f"start={call.start:.6f} delta_from_rm={call.start - rm_ts:+.9f}s")
    print(f"end={call.end:.6f} delta_from_rm={call.end - rm_ts:+.9f}s")
    print(f"duration_ms={call.duration * 1000:.3f}")
    print(f"page_count={call.page_count}")
    print(f"page_size={call.page_size}")
    print(f"logical_bytes={call.logical_bytes}")
    print(f"logical_gib={call.logical_gib:.6f}")
    print(f"contiguous={call.contiguous}")
    print(f"ret=0x{call.ret:x}({call.ret})")
    print(f"spans_rm={'YES' if call.start <= rm_ts <= call.end else 'NO'}")
    print(f"entry_cpu={call.entry_cpu} ret_cpu={call.ret_cpu}")
    print()
    print("linux_events_within_call:")
    print(
        "  compaction_try="
        f"{names['mm_compaction_try_to_compact_pages']} "
        f"orders=[{fmt_counter(compaction_orders)}]"
    )
    print(
        "  compaction_begin/end="
        f"{names['mm_compaction_begin']}/{names['mm_compaction_end']}"
    )
    print(
        "  direct_reclaim_begin/end="
        f"{names['mm_vmscan_direct_reclaim_begin']}/"
        f"{names['mm_vmscan_direct_reclaim_end']} "
        f"orders=[{fmt_counter(reclaim_orders)}]"
    )
    print(
        "  extfrag="
        f"{names['mm_page_alloc_extfrag']} parsed={extfrag['parsed']} "
        f"ownership={extfrag['ownership']} gap_ge_2={extfrag['gap_ge_2']}"
    )
    print(f"  extfrag_alloc_orders=[{fmt_counter(extfrag['alloc_orders'])}]")
    print(f"  extfrag_pairs=[{fmt_counter(extfrag['pairs'])}]")
    print()
    print(f"entry :: {call.entry_line}")
    print(f"return :: {call.ret_line}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "evidence",
        nargs="?",
        type=Path,
        default=DEFAULT_OUT,
        help="preserved R8 evidence directory",
    )
    args = parser.parse_args()

    out: Path = args.evidence
    trace_path = out / "allocator-trace.txt"
    kernel_path = out / "kernel-errors-monotonic.txt"

    if not trace_path.is_file():
        raise SystemExit(f"missing decoded trace: {trace_path}")
    if not kernel_path.is_file():
        raise SystemExit(f"missing kernel monotonic error log: {kernel_path}")

    events = parse_events(trace_path)
    calls = pair_nv_alloc_calls(events)
    rm_ts, rm_line = first_rm_timestamp(kernel_path)

    if not calls:
        raise SystemExit("no paired nv_alloc_pages calls found")

    spanning = [call for call in calls if call.start <= rm_ts <= call.end]
    failed_after = [call for call in calls if call.start > rm_ts and call.ret == 0x51]

    print("=== R8 NV_ALLOC EPISODE ANALYSIS ===")
    print(f"evidence={out}")
    print(f"parsed_trace_events={len(events)}")
    print(f"paired_nv_alloc_calls={len(calls)}")
    print(f"rm_monotonic={rm_ts:.6f}")
    print(f"rm_line={rm_line}")
    print()

    selected: list[tuple[str, NvAllocCall]] = []

    if spanning:
        # If multiple tasks span the timestamp, prefer the VLLM worker and then
        # the call whose interval is tightest around the RM event.
        spanning_call = min(
            spanning,
            key=lambda call: (
                0 if "VLLM::Worker" in call.task else 1,
                call.end - call.start,
            ),
        )
        selected.append(("CALL_SPANNING_RM", spanning_call))
    else:
        print("CALL_SPANNING_RM=NONE")
        print()

    if failed_after:
        failure = min(failed_after, key=lambda call: call.start)
        selected.append(("FIRST_FAILED_NV_ALLOC_AFTER_RM", failure))

        next_same_thread = [
            call for call in calls
            if call.pid == failure.pid and call.start > failure.end
        ]
        if next_same_thread:
            selected.append(
                ("NEXT_SAME_THREAD_NV_ALLOC", min(next_same_thread, key=lambda call: call.start))
            )
        else:
            print("NEXT_SAME_THREAD_NV_ALLOC=NONE")
            print()
    else:
        print("FIRST_FAILED_NV_ALLOC_AFTER_RM=NONE")
        print()

    for label, call in selected:
        print_call(label, call, rm_ts, events)

    print("=== CALLS WITHIN RM +/-1s ===")
    near = [
        call for call in calls
        if call.end >= rm_ts - 1.0 and call.start <= rm_ts + 1.0
    ]
    for index, call in enumerate(near, 1):
        print(
            f"{index:02d} pid={call.pid} task={call.task} "
            f"start_delta={call.start-rm_ts:+.6f}s "
            f"end_delta={call.end-rm_ts:+.6f}s "
            f"duration_ms={call.duration*1000:.3f} "
            f"count={call.page_count} page_size={call.page_size} "
            f"gib={call.logical_gib:.6f} contig={call.contiguous} "
            f"ret=0x{call.ret:x}"
        )

    print()
    print("=== INTERPRETATION GUARDS ===")
    print(
        "logical_gib is page_count * page_size from the public nv_alloc_pages "
        "API arguments; it describes the outer request represented by this probe."
    )
    print(
        "A kernel _memdescAllocInternal log that occurs while an outer call is "
        "in flight must not be assumed to be that outer call's final return."
    )
    print(
        "Likewise, a later call with the same page_count but a different page_size "
        "must not be called an equivalent retry unless deeper RM source evidence "
        "establishes that relationship."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
