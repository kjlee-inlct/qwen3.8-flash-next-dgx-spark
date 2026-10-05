#!/usr/bin/env python3
"""Compare the failed R8 nv_alloc_pages call with same-shape calls.

Reads only preserved decoded R8 trace evidence. No model execution or evidence
mutation is performed. The primary question is whether the exact failed
(page_count, requested_page_size, contiguous) shape also succeeded elsewhere,
and how Linux allocator activity differs inside those call intervals.
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
FIELD_RE = re.compile(r"(?P<key>[A-Za-z_]+)=(?P<value>0x[0-9A-Fa-f]+|-?\d+)")
ORDER_RE = re.compile(r"\border=(?P<order>\d+)\b")
ALLOC_ORDER_RE = re.compile(r"\balloc_order=(?P<value>\d+)\b")
FALLBACK_ORDER_RE = re.compile(r"\bfallback_order=(?P<value>\d+)\b")
OWNERSHIP_RE = re.compile(r"\bchange_ownership=(?P<value>[01])\b")


@dataclass(frozen=True)
class Event:
    task: str
    pid: int
    ts: float
    name: str
    body: str


@dataclass(frozen=True)
class Call:
    task: str
    pid: int
    start: float
    end: float
    page_count: int
    page_size: int
    contiguous: int
    ret: int

    @property
    def duration_ms(self) -> float:
        return (self.end - self.start) * 1000.0

    @property
    def shape(self) -> tuple[int, int, int]:
        return self.page_count, self.page_size, self.contiguous


@dataclass(frozen=True)
class Metrics:
    compaction_try: int
    reclaim_begin: int
    extfrag: int
    ownership: int
    gap_ge_2: int
    extfrag_pairs: Counter[tuple[int, int]]
    compaction_orders: Counter[int]
    reclaim_orders: Counter[int]


def parse_int(raw: str) -> int:
    return int(raw, 16 if raw.lower().startswith("0x") else 10)


def fields(body: str) -> dict[str, int]:
    return {
        match.group("key"): parse_int(match.group("value"))
        for match in FIELD_RE.finditer(body)
    }


def parse_events(path: Path) -> list[Event]:
    result: list[Event] = []
    for line in path.read_text(errors="replace").splitlines():
        match = TRACE_RE.match(line)
        if not match:
            continue
        result.append(
            Event(
                task=match.group("task").strip(),
                pid=int(match.group("pid")),
                ts=float(match.group("ts")),
                name=match.group("event"),
                body=match.group("body"),
            )
        )
    return result


def pair_calls(events: list[Event]) -> list[Call]:
    stacks: dict[int, list[Event]] = defaultdict(list)
    calls: list[Call] = []

    for event in events:
        if event.name == "nv_alloc_pages_entry":
            stacks[event.pid].append(event)
            continue
        if event.name != "nv_alloc_pages_ret" or not stacks[event.pid]:
            continue

        entry = stacks[event.pid].pop()
        ef = fields(entry.body)
        rf = fields(event.body)
        if not all(k in ef for k in ("page_count", "page_size", "contiguous")):
            continue
        if "ret" not in rf:
            continue
        calls.append(
            Call(
                task=entry.task,
                pid=entry.pid,
                start=entry.ts,
                end=event.ts,
                page_count=ef["page_count"],
                page_size=ef["page_size"],
                contiguous=ef["contiguous"],
                ret=rf["ret"],
            )
        )

    return sorted(calls, key=lambda call: call.start)


def interval_metrics(events: list[Event], call: Call) -> Metrics:
    compaction_try = 0
    reclaim_begin = 0
    extfrag = 0
    ownership = 0
    gap_ge_2 = 0
    extfrag_pairs: Counter[tuple[int, int]] = Counter()
    compaction_orders: Counter[int] = Counter()
    reclaim_orders: Counter[int] = Counter()

    for event in events:
        if event.ts < call.start:
            continue
        if event.ts > call.end:
            break

        if event.name == "mm_compaction_try_to_compact_pages":
            compaction_try += 1
            match = ORDER_RE.search(event.body)
            if match:
                compaction_orders[int(match.group("order"))] += 1
        elif event.name == "mm_vmscan_direct_reclaim_begin":
            reclaim_begin += 1
            match = ORDER_RE.search(event.body)
            if match:
                reclaim_orders[int(match.group("order"))] += 1
        elif event.name == "mm_page_alloc_extfrag":
            alloc = ALLOC_ORDER_RE.search(event.body)
            fallback = FALLBACK_ORDER_RE.search(event.body)
            if not alloc or not fallback:
                continue
            extfrag += 1
            alloc_order = int(alloc.group("value"))
            fallback_order = int(fallback.group("value"))
            extfrag_pairs[(alloc_order, fallback_order)] += 1
            own = OWNERSHIP_RE.search(event.body)
            if own and own.group("value") == "1":
                ownership += 1
            if fallback_order - alloc_order >= 2:
                gap_ge_2 += 1

    return Metrics(
        compaction_try=compaction_try,
        reclaim_begin=reclaim_begin,
        extfrag=extfrag,
        ownership=ownership,
        gap_ge_2=gap_ge_2,
        extfrag_pairs=extfrag_pairs,
        compaction_orders=compaction_orders,
        reclaim_orders=reclaim_orders,
    )


def rate(count: int, duration_ms: float) -> float:
    return count / duration_ms if duration_ms > 0 else 0.0


def pct(num: int, den: int) -> float:
    return 100.0 * num / den if den else 0.0


def fmt_counter(counter: Counter[object], limit: int = 8) -> str:
    if not counter:
        return "NONE"
    return ", ".join(f"{key}={value}" for key, value in counter.most_common(limit))


def print_call(index: int, call: Call, metrics: Metrics, page_size: int) -> None:
    total_gib = call.page_count * page_size / 1024**3
    print(
        f"{index:02d} start={call.start:.6f} end={call.end:.6f} "
        f"duration_ms={call.duration_ms:.3f} ret=0x{call.ret:x} "
        f"total_gib={total_gib:.6f}"
    )
    print(
        "   counts: "
        f"compaction={metrics.compaction_try} reclaim={metrics.reclaim_begin} "
        f"extfrag={metrics.extfrag} ownership={metrics.ownership} "
        f"gap_ge_2={metrics.gap_ge_2}"
    )
    print(
        "   rates/ms: "
        f"compaction={rate(metrics.compaction_try, call.duration_ms):.6f} "
        f"reclaim={rate(metrics.reclaim_begin, call.duration_ms):.6f} "
        f"extfrag={rate(metrics.extfrag, call.duration_ms):.6f} "
        f"ownership={rate(metrics.ownership, call.duration_ms):.6f}"
    )
    print(
        "   ratios: "
        f"ownership/extfrag={pct(metrics.ownership, metrics.extfrag):.3f}% "
        f"gap_ge_2/extfrag={pct(metrics.gap_ge_2, metrics.extfrag):.3f}%"
    )
    print(f"   compaction_orders=[{fmt_counter(metrics.compaction_orders)}]")
    print(f"   reclaim_orders=[{fmt_counter(metrics.reclaim_orders)}]")
    print(f"   extfrag_pairs=[{fmt_counter(metrics.extfrag_pairs)}]")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", nargs="?", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    trace = args.evidence / "allocator-trace.txt"
    if not trace.is_file():
        raise SystemExit(f"missing decoded trace: {trace}")

    import os

    host_page_size = os.sysconf("SC_PAGE_SIZE")
    events = parse_events(trace)
    calls = pair_calls(events)
    failures = [call for call in calls if call.ret == 0x51]
    if len(failures) != 1:
        raise SystemExit(f"expected exactly one nv_alloc_pages 0x51 call, found {len(failures)}")

    failed = failures[0]
    same_shape = [call for call in calls if call.shape == failed.shape]
    successes = [call for call in same_shape if call.ret == 0]

    print("=== R8 SAME-SHAPE NV_ALLOC COMPARATOR ===")
    print(f"evidence={args.evidence}")
    print(f"host_page_size={host_page_size}")
    print(f"paired_calls={len(calls)}")
    print(
        "failed_shape="
        f"page_count={failed.page_count},requested_page_size={failed.page_size},"
        f"contiguous={failed.contiguous}"
    )
    print(f"same_shape_calls={len(same_shape)}")
    print(f"same_shape_successes={len(successes)}")
    print(f"same_shape_failures={len(same_shape) - len(successes)}")
    print()

    rows: list[tuple[Call, Metrics]] = [
        (call, interval_metrics(events, call)) for call in same_shape
    ]
    for index, (call, metrics) in enumerate(rows, 1):
        print_call(index, call, metrics, host_page_size)
        print()

    failed_metrics = interval_metrics(events, failed)
    if successes:
        print("=== FAILED VS SAME-SHAPE SUCCESS RANGE ===")
        success_rows = [(call, interval_metrics(events, call)) for call in successes]

        def range_line(name: str, values: list[float], failed_value: float) -> None:
            print(
                f"{name}: failed={failed_value:.6f} "
                f"success_min={min(values):.6f} success_max={max(values):.6f}"
            )

        range_line(
            "duration_ms",
            [call.duration_ms for call, _ in success_rows],
            failed.duration_ms,
        )
        range_line(
            "reclaim_rate_per_ms",
            [rate(m.reclaim_begin, c.duration_ms) for c, m in success_rows],
            rate(failed_metrics.reclaim_begin, failed.duration_ms),
        )
        range_line(
            "compaction_rate_per_ms",
            [rate(m.compaction_try, c.duration_ms) for c, m in success_rows],
            rate(failed_metrics.compaction_try, failed.duration_ms),
        )
        range_line(
            "extfrag_rate_per_ms",
            [rate(m.extfrag, c.duration_ms) for c, m in success_rows],
            rate(failed_metrics.extfrag, failed.duration_ms),
        )
        range_line(
            "ownership_pct",
            [pct(m.ownership, m.extfrag) for _, m in success_rows],
            pct(failed_metrics.ownership, failed_metrics.extfrag),
        )
        range_line(
            "gap_ge_2_pct",
            [pct(m.gap_ge_2, m.extfrag) for _, m in success_rows],
            pct(failed_metrics.gap_ge_2, failed_metrics.extfrag),
        )
    else:
        print("=== FAILED VS SAME-SHAPE SUCCESS RANGE ===")
        print("NO_SAME_SHAPE_SUCCESS_CALLS")

    print()
    print("=== INTERPRETATION GUARD ===")
    print(
        "A same-shape success disproves a deterministic request-shape failure. "
        "Differences in reclaim/extfrag metrics remain correlation unless the "
        "same temporal ordering is shown to precede the failed chunk allocation."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
