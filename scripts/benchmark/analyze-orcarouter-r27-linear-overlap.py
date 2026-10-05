#!/usr/bin/env python3
"""Align R27 Qwen4Exp/W4A16 markers with direct NVIDIA RM 64 KiB activity.

Evidence-only analyzer. RM bytes are logical allocation activity volume, not
exact resident ownership. Marker overlap is temporal localization, not causal
proof.
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
SEQ_RE = re.compile(r"\bseq=(\d+)\b")
LAYER_RE = re.compile(r"\blayer=(\d+)\b")
TYPE_RE = re.compile(r"\btype=([^\s]+)")

CTOR_BEGIN = "QWEN38_R26_MODEL_CTOR_BEGIN"
CTOR_END = "QWEN38_R26_MODEL_CTOR_END"
MOE_BEGIN = "QWEN38_R26_MODELOPT_MOE_BEGIN"
MOE_END = "QWEN38_R26_MODELOPT_MOE_END"
LINEAR_BEGIN = "QWEN38_R27_W4A16_LINEAR_BEGIN"
LINEAR_END = "QWEN38_R27_W4A16_LINEAR_END"
WEIGHT_BEGIN = "QWEN38_R27_W4A16_WEIGHT_BEGIN"
WEIGHT_END = "QWEN38_R27_W4A16_WEIGHT_END"
LAYER_BEGIN = "QWEN38_R27_QWEN4_LAYER_BEGIN"
LAYER_END = "QWEN38_R27_QWEN4_LAYER_END"


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


@dataclass(frozen=True)
class LayerInterval:
    seq: int
    layer: int
    layer_type: str
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


def pair_simple(
    events: list[LogEvent], begin_token: str, end_token: str
) -> list[tuple[LogEvent, LogEvent]]:
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


def pair_layers(events: list[LogEvent]) -> list[LayerInterval]:
    pending: dict[int, tuple[LogEvent, int, str]] = {}
    pairs: list[LayerInterval] = []
    for event in events:
        if LAYER_BEGIN not in event.text and LAYER_END not in event.text:
            continue
        seq_match = SEQ_RE.search(event.text)
        if not seq_match:
            continue
        seq = int(seq_match.group(1))
        if LAYER_BEGIN in event.text:
            layer_match = LAYER_RE.search(event.text)
            type_match = TYPE_RE.search(event.text)
            if layer_match is None or type_match is None:
                continue
            pending[seq] = (event, int(layer_match.group(1)), type_match.group(1))
            continue
        prior = pending.pop(seq, None)
        if prior is not None:
            begin, layer, layer_type = prior
            if event.mono >= begin.mono:
                pairs.append(LayerInterval(seq, layer, layer_type, begin, event))
    return sorted(pairs, key=lambda row: (row.begin.mono, row.seq))


def logical_bytes(rows: list[RmEntry] | set[RmEntry], host_page_size: int) -> int:
    return sum(row.page_count * host_page_size for row in rows)


def rows_in_interval(rows: list[RmEntry], start: float, end: float) -> list[RmEntry]:
    return [row for row in rows if start <= row.mono <= end]


def interval_overlaps(start: float, end: float, outer_start: float, outer_end: float) -> bool:
    return end >= outer_start and start <= outer_end


def row_set_for_intervals(
    rows: list[RmEntry], intervals: list[tuple[float, float]]
) -> set[RmEntry]:
    if not intervals:
        return set()
    return {
        row
        for row in rows
        if any(start <= row.mono <= end for start, end in intervals)
    }


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
    host_page_size = int(read(root / "host-page-size.txt").strip())
    order4 = [
        row
        for row in parse_rm_entries(read(root / "rm-trace.txt"))
        if row.page_size == 65536
    ]
    if not order4:
        raise SystemExit("no 64 KiB-path nv_alloc_pages activity found")

    ctor_pairs = pair_simple(events, CTOR_BEGIN, CTOR_END)
    if not ctor_pairs:
        raise SystemExit("R26 inherited model-constructor marker pair missing")
    scored_ctors = [
        (logical_bytes(rows_in_interval(order4, begin.mono, end.mono), host_page_size), begin, end)
        for begin, end in ctor_pairs
    ]
    ctor_bytes, ctor_begin, ctor_end = max(scored_ctors, key=lambda item: item[0])
    ctor_rows = rows_in_interval(order4, ctor_begin.mono, ctor_end.mono)
    ctor_row_set = set(ctor_rows)

    moe_all = pair_seq(events, MOE_BEGIN, MOE_END)
    linear_all = pair_seq(events, LINEAR_BEGIN, LINEAR_END)
    weight_all = pair_seq(events, WEIGHT_BEGIN, WEIGHT_END)
    layers_all = pair_layers(events)

    selected_moe = [
        item
        for item in moe_all
        if interval_overlaps(item.begin.mono, item.end.mono, ctor_begin.mono, ctor_end.mono)
    ]
    selected_linear = [
        item
        for item in linear_all
        if interval_overlaps(item.begin.mono, item.end.mono, ctor_begin.mono, ctor_end.mono)
    ]
    selected_linear_seqs = {item.seq for item in selected_linear}
    selected_weight = [item for item in weight_all if item.seq in selected_linear_seqs]
    selected_layers = [
        item
        for item in layers_all
        if interval_overlaps(item.begin.mono, item.end.mono, ctor_begin.mono, ctor_end.mono)
    ]

    moe_rows = row_set_for_intervals(
        ctor_rows, [(item.begin.mono, item.end.mono) for item in selected_moe]
    )
    linear_rows = row_set_for_intervals(
        ctor_rows, [(item.begin.mono, item.end.mono) for item in selected_linear]
    )
    weight_rows = row_set_for_intervals(
        ctor_rows, [(item.begin.mono, item.end.mono) for item in selected_weight]
    )
    layer_rows = row_set_for_intervals(
        ctor_rows, [(item.begin.mono, item.end.mono) for item in selected_layers]
    )

    total_bytes = logical_bytes(order4, host_page_size)
    before_ctor_bytes = logical_bytes(
        [row for row in order4 if row.mono < ctor_begin.mono], host_page_size
    )
    after_ctor_bytes = logical_bytes(
        [row for row in order4 if row.mono > ctor_end.mono], host_page_size
    )
    moe_bytes = logical_bytes(moe_rows, host_page_size)
    linear_bytes = logical_bytes(linear_rows, host_page_size)
    weight_bytes = logical_bytes(weight_rows, host_page_size)
    layer_bytes = logical_bytes(layer_rows, host_page_size)

    r26_residual_rows = ctor_row_set - moe_rows
    r26_residual_bytes = logical_bytes(r26_residual_rows, host_page_size)
    linear_in_residual_rows = linear_rows & r26_residual_rows
    linear_in_residual_bytes = logical_bytes(linear_in_residual_rows, host_page_size)
    moe_linear_union = moe_rows | linear_rows
    moe_linear_union_bytes = logical_bytes(moe_linear_union, host_page_size)
    uncovered_ctor_rows = ctor_row_set - moe_linear_union
    uncovered_ctor_bytes = logical_bytes(uncovered_ctor_rows, host_page_size)

    layer_type_stats: dict[str, dict[str, int]] = {}
    per_layer: list[tuple[int, int, str, int, int, int, float]] = []
    for item in selected_layers:
        rows = set(rows_in_interval(ctor_rows, item.begin.mono, item.end.mono))
        moe_part = rows & moe_rows
        linear_part = rows & linear_rows
        non_moe = rows - moe_rows
        stats = layer_type_stats.setdefault(
            item.layer_type,
            {"total": 0, "moe": 0, "linear": 0, "non_moe": 0},
        )
        total = logical_bytes(rows, host_page_size)
        moe_value = logical_bytes(moe_part, host_page_size)
        linear_value = logical_bytes(linear_part, host_page_size)
        non_moe_value = logical_bytes(non_moe, host_page_size)
        stats["total"] += total
        stats["moe"] += moe_value
        stats["linear"] += linear_value
        stats["non_moe"] += non_moe_value
        per_layer.append(
            (
                non_moe_value,
                item.layer,
                item.layer_type,
                total,
                linear_value,
                moe_value,
                item.end.mono - item.begin.mono,
            )
        )

    primary_threshold = 90.0
    linear_pct_r26_residual = pct(linear_in_residual_bytes, r26_residual_bytes)
    layer_pct_ctor = pct(layer_bytes, ctor_bytes)
    union_pct_ctor = pct(moe_linear_union_bytes, ctor_bytes)
    weight_pct_linear = pct(weight_bytes, linear_bytes)

    if linear_pct_r26_residual >= primary_threshold:
        discriminator = "RM_ORDER4_R26_RESIDUAL_PRIMARY_IN_MODELOPT_W4A16_LINEAR"
    elif layer_pct_ctor >= primary_threshold:
        discriminator = "RM_ORDER4_R26_RESIDUAL_MIXED_WITHIN_QWEN4_LAYERS"
    else:
        discriminator = "RM_ORDER4_R26_RESIDUAL_OUTSIDE_SELECTED_LAYER_LINEAR_BOUNDARIES"

    mib = 1048576.0
    print("R27_LINEAR_RESIDUAL_OVERLAP=BEGIN")
    print("analysis_semantics=temporal_boundary_alignment_not_causal_proof")
    print("rm_bytes_semantics=activity_volume_not_resident_ownership")
    print(f"primary_threshold_pct={primary_threshold:.6f}")
    print(f"clock_anchor_count={len(offsets)}")
    print(f"clock_offset_spread_ms={spread_ms:.6f}")
    print(f"classification_tolerance_s={tolerance_s:.6f}")
    print(f"model_ctor.marker_pair_count={len(ctor_pairs)}")
    print(f"model_ctor.duration_s={ctor_end.mono - ctor_begin.mono:.6f}")
    print(f"rm_order4.total_activity_mib={total_bytes / mib:.3f}")
    print(f"rm_order4.before_model_ctor_activity_mib={before_ctor_bytes / mib:.3f}")
    print(f"rm_order4.inside_model_ctor_activity_mib={ctor_bytes / mib:.3f}")
    print(f"rm_order4.after_model_ctor_activity_mib={after_ctor_bytes / mib:.3f}")
    print(f"rm_order4.inside_model_ctor_pct={pct(ctor_bytes, total_bytes):.6f}")

    print(f"r26_modelopt_moe.activity_mib={moe_bytes / mib:.3f}")
    print(f"r26_modelopt_moe.pct_of_total={pct(moe_bytes, total_bytes):.6f}")
    print(f"r26_residual_outside_moe.activity_mib={r26_residual_bytes / mib:.3f}")

    print(f"w4a16_linear.marker_pair_count_total={len(linear_all)}")
    print(f"w4a16_linear.selected_call_count={len(selected_linear)}")
    print(f"w4a16_linear.activity_mib={linear_bytes / mib:.3f}")
    print(f"w4a16_linear.pct_of_total={pct(linear_bytes, total_bytes):.6f}")
    print(f"w4a16_linear.pct_of_model_ctor={pct(linear_bytes, ctor_bytes):.6f}")
    print(f"w4a16_linear.in_r26_residual_activity_mib={linear_in_residual_bytes / mib:.3f}")
    print(f"w4a16_linear.pct_of_r26_residual={linear_pct_r26_residual:.6f}")
    print(f"w4a16_weight.activity_mib={weight_bytes / mib:.3f}")
    print(f"w4a16_weight.pct_of_w4a16_linear={weight_pct_linear:.6f}")

    print(f"moe_w4a16_union.activity_mib={moe_linear_union_bytes / mib:.3f}")
    print(f"moe_w4a16_union.pct_of_model_ctor={union_pct_ctor:.6f}")
    print(f"model_ctor_uncovered_after_moe_w4a16.activity_mib={uncovered_ctor_bytes / mib:.3f}")
    print(
        "model_ctor_uncovered_after_moe_w4a16.pct_of_model_ctor="
        f"{pct(uncovered_ctor_bytes, ctor_bytes):.6f}"
    )

    print(f"qwen4_layer.marker_pair_count_total={len(layers_all)}")
    print(f"qwen4_layer.selected_layer_count={len(selected_layers)}")
    print(f"qwen4_layer.activity_mib={layer_bytes / mib:.3f}")
    print(f"qwen4_layer.pct_of_model_ctor={layer_pct_ctor:.6f}")
    print(
        "model_ctor_outside_qwen4_layers.activity_mib="
        f"{logical_bytes(ctor_row_set - layer_rows, host_page_size) / mib:.3f}"
    )

    for layer_type in sorted(layer_type_stats):
        stats = layer_type_stats[layer_type]
        prefix = f"qwen4_layer_type.{layer_type}"
        print(f"{prefix}.total_activity_mib={stats['total'] / mib:.3f}")
        print(f"{prefix}.modelopt_moe_activity_mib={stats['moe'] / mib:.3f}")
        print(f"{prefix}.w4a16_linear_activity_mib={stats['linear'] / mib:.3f}")
        print(f"{prefix}.non_moe_activity_mib={stats['non_moe'] / mib:.3f}")

    per_layer.sort(reverse=True)
    for rank, (
        non_moe_value,
        layer,
        layer_type,
        total,
        linear_value,
        moe_value,
        duration,
    ) in enumerate(per_layer[:8], start=1):
        print(
            f"qwen4_layer.top_non_moe_{rank}=layer={layer} type={layer_type} "
            f"non_moe_mib={non_moe_value / mib:.3f} "
            f"w4a16_linear_mib={linear_value / mib:.3f} "
            f"moe_mib={moe_value / mib:.3f} total_mib={total / mib:.3f} "
            f"duration_s={duration:.6f}"
        )

    print(f"residual_discriminator={discriminator}")
    print("R27_LINEAR_RESIDUAL_OVERLAP=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
