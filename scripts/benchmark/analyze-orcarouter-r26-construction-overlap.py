#!/usr/bin/env python3
"""Align R26 construction markers with direct NVIDIA RM 64 KiB activity.

The analyzer is evidence-only. RM bytes are logical allocation activity volume,
not exact resident ownership. Marker overlap is temporal localization, not
causal proof.
"""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re
import statistics
from dataclasses import dataclass

TRACE_RE = re.compile(r"\s(\d+\.\d+):\s+nv_alloc_pages_entry:\s*(.*)$")
FIELD_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)=(0x[0-9A-Fa-f]+|-?\d+)\b")
LOG_RE = re.compile(r"^(\S+)\s+(.*)$")
CTOR_BEGIN = "QWEN38_R26_MODEL_CTOR_BEGIN"
CTOR_END = "QWEN38_R26_MODEL_CTOR_END"
SEQ_RE = re.compile(r"\bseq=(\d+)\b")
TOKENS = {
    "moe_begin": "QWEN38_R26_MODELOPT_MOE_BEGIN",
    "moe_end": "QWEN38_R26_MODELOPT_MOE_END",
    "w13_begin": "QWEN38_R26_MODELOPT_W13_BEGIN",
    "w13_end": "QWEN38_R26_MODELOPT_W13_END",
    "w2_begin": "QWEN38_R26_MODELOPT_W2_BEGIN",
    "w2_end": "QWEN38_R26_MODELOPT_W2_END",
}


@dataclass(frozen=True)
class LogEvent:
    wall_epoch: float
    mono: float
    text: str


@dataclass(frozen=True)
class RmEntry:
    mono: float
    page_count: int
    page_size: int


@dataclass(frozen=True)
class SeqInterval:
    seq: int
    begin: LogEvent
    end: LogEvent


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        raise SystemExit(f"missing evidence file: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def parse_iso_epoch(raw: str) -> float:
    value = raw.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return dt.datetime.fromisoformat(value).timestamp()


def read_anchor(root: pathlib.Path, iso_name: str, mono_name: str) -> tuple[float, float]:
    wall = parse_iso_epoch(read(root / iso_name).strip())
    mono = int(read(root / mono_name).strip()) / 1e9
    return wall, mono


def clock_offset(root: pathlib.Path) -> tuple[float, list[float]]:
    names = [
        ("candidate-request-iso.txt", "candidate-request-monotonic-ns.txt"),
        ("trace-window-start-iso.txt", "trace-window-start-monotonic-ns.txt"),
        ("trace-window-end-iso.txt", "trace-window-end-monotonic-ns.txt"),
    ]
    offsets: list[float] = []
    for iso_name, mono_name in names:
        wall, mono = read_anchor(root, iso_name, mono_name)
        offsets.append(mono - wall)
    return statistics.median(offsets), offsets


def parse_logs(text: str, offset: float) -> list[LogEvent]:
    events: list[LogEvent] = []
    for line in text.splitlines():
        match = LOG_RE.match(line)
        if not match:
            continue
        try:
            wall = parse_iso_epoch(match.group(1))
        except ValueError:
            continue
        events.append(LogEvent(wall, wall + offset, match.group(2)))
    return events


def parse_rm_entries(text: str) -> list[RmEntry]:
    rows: list[RmEntry] = []
    for line in text.splitlines():
        match = TRACE_RE.search(line)
        if not match:
            continue
        fields = {
            key: int(value, 16 if value.lower().startswith("0x") else 10)
            for key, value in FIELD_RE.findall(match.group(2))
        }
        rows.append(
            RmEntry(
                mono=float(match.group(1)),
                page_count=fields.get("page_count", 0),
                page_size=fields.get("page_size", 0),
            )
        )
    return sorted(rows, key=lambda row: row.mono)


def pair_simple(events: list[LogEvent], begin_token: str, end_token: str) -> list[tuple[LogEvent, LogEvent]]:
    pairs: list[tuple[LogEvent, LogEvent]] = []
    pending: LogEvent | None = None
    for event in events:
        if begin_token in event.text:
            pending = event
            continue
        if end_token in event.text and pending is not None:
            if event.mono >= pending.mono:
                pairs.append((pending, event))
            pending = None
    return pairs


def pair_seq(events: list[LogEvent], begin_token: str, end_token: str) -> list[SeqInterval]:
    pending: dict[int, LogEvent] = {}
    pairs: list[SeqInterval] = []
    for event in events:
        if begin_token not in event.text and end_token not in event.text:
            continue
        match = SEQ_RE.search(event.text)
        if not match:
            continue
        seq = int(match.group(1))
        if begin_token in event.text:
            pending[seq] = event
            continue
        begin = pending.pop(seq, None)
        if begin is not None and event.mono >= begin.mono:
            pairs.append(SeqInterval(seq, begin, event))
    return sorted(pairs, key=lambda row: (row.begin.mono, row.seq))


def logical_bytes(rows: list[RmEntry], host_page_size: int) -> int:
    return sum(row.page_count * host_page_size for row in rows)


def rows_in_interval(rows: list[RmEntry], start: float, end: float) -> list[RmEntry]:
    return [row for row in rows if start <= row.mono <= end]


def rows_in_any(rows: list[RmEntry], intervals: list[tuple[float, float]]) -> list[RmEntry]:
    if not intervals:
        return []
    return [
        row
        for row in rows
        if any(start <= row.mono <= end for start, end in intervals)
    ]


def interval_overlaps(start: float, end: float, outer_start: float, outer_end: float) -> bool:
    return end >= outer_start and start <= outer_end


def pct(part: int, whole: int) -> float:
    return 100.0 * part / whole if whole else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=pathlib.Path)
    args = parser.parse_args()
    root = args.evidence

    offset, offsets = clock_offset(root)
    spread_ms = (max(offsets) - min(offsets)) * 1000.0
    tolerance_s = max(0.025, (spread_ms / 1000.0) * 2.0)
    events = parse_logs(read(root / "candidate-container.log"), offset)
    ctor_pairs = pair_simple(events, CTOR_BEGIN, CTOR_END)
    if not ctor_pairs:
        raise SystemExit("R26 model constructor marker pair missing")

    host_page_size = int(read(root / "host-page-size.txt").strip())
    order4 = [row for row in parse_rm_entries(read(root / "rm-trace.txt")) if row.page_size == 65536]
    if not order4:
        raise SystemExit("no 64 KiB-path nv_alloc_pages activity found")

    scored_ctors = [
        (logical_bytes(rows_in_interval(order4, begin.mono, end.mono), host_page_size), begin, end)
        for begin, end in ctor_pairs
    ]
    ctor_bytes, ctor_begin, ctor_end = max(scored_ctors, key=lambda item: item[0])
    ctor_rows = rows_in_interval(order4, ctor_begin.mono, ctor_end.mono)

    moe_all = pair_seq(events, TOKENS["moe_begin"], TOKENS["moe_end"])
    w13_all = pair_seq(events, TOKENS["w13_begin"], TOKENS["w13_end"])
    w2_all = pair_seq(events, TOKENS["w2_begin"], TOKENS["w2_end"])

    selected_moe = [
        row
        for row in moe_all
        if interval_overlaps(row.begin.mono, row.end.mono, ctor_begin.mono, ctor_end.mono)
    ]
    selected_seqs = {row.seq for row in selected_moe}
    selected_w13 = [row for row in w13_all if row.seq in selected_seqs]
    selected_w2 = [row for row in w2_all if row.seq in selected_seqs]

    moe_intervals = [(row.begin.mono, row.end.mono) for row in selected_moe]
    w13_intervals = [(row.begin.mono, row.end.mono) for row in selected_w13]
    w2_intervals = [(row.begin.mono, row.end.mono) for row in selected_w2]

    moe_rows = rows_in_any(ctor_rows, moe_intervals)
    w13_rows = rows_in_any(ctor_rows, w13_intervals)
    w2_rows = rows_in_any(ctor_rows, w2_intervals)
    packed_rows = rows_in_any(ctor_rows, w13_intervals + w2_intervals)
    nonpacked_moe_rows = [row for row in moe_rows if row not in packed_rows]
    ctor_non_moe_rows = [row for row in ctor_rows if row not in moe_rows]

    total_bytes = logical_bytes(order4, host_page_size)
    before_ctor_bytes = logical_bytes([row for row in order4 if row.mono < ctor_begin.mono], host_page_size)
    after_ctor_bytes = logical_bytes([row for row in order4 if row.mono > ctor_end.mono], host_page_size)
    moe_bytes = logical_bytes(moe_rows, host_page_size)
    w13_bytes = logical_bytes(w13_rows, host_page_size)
    w2_bytes = logical_bytes(w2_rows, host_page_size)
    packed_bytes = logical_bytes(packed_rows, host_page_size)
    nonpacked_moe_bytes = logical_bytes(nonpacked_moe_rows, host_page_size)
    ctor_non_moe_bytes = logical_bytes(ctor_non_moe_rows, host_page_size)

    ctor_pct = pct(ctor_bytes, total_bytes)
    moe_pct_total = pct(moe_bytes, total_bytes)
    moe_pct_ctor = pct(moe_bytes, ctor_bytes)
    packed_pct_total = pct(packed_bytes, total_bytes)
    packed_pct_moe = pct(packed_bytes, moe_bytes)

    if moe_pct_total >= 90.0:
        discriminator = "RM_ORDER4_PRIMARY_IN_MODELOPT_MOE_CREATE_WEIGHTS"
    elif ctor_pct >= 90.0 and pct(ctor_non_moe_bytes, ctor_bytes) >= 90.0:
        discriminator = "RM_ORDER4_PRIMARY_IN_MODEL_CONSTRUCTOR_OUTSIDE_MODELOPT_MOE"
    elif ctor_pct >= 90.0:
        discriminator = "RM_ORDER4_MIXED_WITHIN_MODEL_CONSTRUCTOR"
    else:
        discriminator = "RM_ORDER4_NOT_LOCALIZED_TO_SELECTED_MODEL_CONSTRUCTOR"

    mib = 1048576.0
    print("R26_CONSTRUCTION_OVERLAP=BEGIN")
    print("analysis_semantics=temporal_boundary_alignment_not_causal_proof")
    print("rm_bytes_semantics=activity_volume_not_resident_ownership")
    print("primary_threshold_pct=90.000000")
    print(f"clock_anchor_count={len(offsets)}")
    print(f"clock_offset_spread_ms={spread_ms:.6f}")
    print(f"classification_tolerance_s={tolerance_s:.6f}")
    print(f"model_ctor.marker_pair_count={len(ctor_pairs)}")
    print(f"model_ctor.begin_monotonic={ctor_begin.mono:.9f}")
    print(f"model_ctor.end_monotonic={ctor_end.mono:.9f}")
    print(f"model_ctor.duration_s={ctor_end.mono - ctor_begin.mono:.6f}")
    print(f"rm_order4.first_monotonic={order4[0].mono:.9f}")
    print(f"rm_order4.last_monotonic={order4[-1].mono:.9f}")
    print(f"rm_order4.total_activity_mib={total_bytes / mib:.3f}")
    print(f"rm_order4.before_model_ctor_activity_mib={before_ctor_bytes / mib:.3f}")
    print(f"rm_order4.inside_model_ctor_activity_mib={ctor_bytes / mib:.3f}")
    print(f"rm_order4.after_model_ctor_activity_mib={after_ctor_bytes / mib:.3f}")
    print(f"rm_order4.inside_model_ctor_pct={ctor_pct:.6f}")
    print(f"modelopt_moe.marker_pair_count_total={len(moe_all)}")
    print(f"modelopt_moe.selected_call_count={len(selected_moe)}")
    print(f"modelopt_moe.activity_mib={moe_bytes / mib:.3f}")
    print(f"modelopt_moe.pct_of_total={moe_pct_total:.6f}")
    print(f"modelopt_moe.pct_of_model_ctor={moe_pct_ctor:.6f}")
    print(f"modelopt_w13.activity_mib={w13_bytes / mib:.3f}")
    print(f"modelopt_w2.activity_mib={w2_bytes / mib:.3f}")
    print(f"modelopt_packed_w13_w2.activity_mib={packed_bytes / mib:.3f}")
    print(f"modelopt_packed_w13_w2.pct_of_total={packed_pct_total:.6f}")
    print(f"modelopt_packed_w13_w2.pct_of_modelopt_moe={packed_pct_moe:.6f}")
    print(f"modelopt_moe_nonpacked.activity_mib={nonpacked_moe_bytes / mib:.3f}")
    print(f"model_ctor_outside_modelopt_moe.activity_mib={ctor_non_moe_bytes / mib:.3f}")

    per_call: list[tuple[int, int, float]] = []
    for interval in selected_moe:
        rows = rows_in_interval(order4, interval.begin.mono, interval.end.mono)
        per_call.append(
            (
                logical_bytes(rows, host_page_size),
                interval.seq,
                interval.end.mono - interval.begin.mono,
            )
        )
    per_call.sort(reverse=True)
    for rank, (activity, seq, duration) in enumerate(per_call[:5], start=1):
        print(
            f"modelopt_moe.top_call_{rank}=seq={seq} "
            f"activity_mib={activity / mib:.3f} duration_s={duration:.6f}"
        )

    print(f"construction_discriminator={discriminator}")
    print("R26_CONSTRUCTION_OVERLAP=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
