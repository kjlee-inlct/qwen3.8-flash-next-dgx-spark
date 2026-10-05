#!/usr/bin/env python3
"""Align R28 unquantized Linear markers with direct NVIDIA RM 64 KiB activity.

Evidence-only analyzer. RM bytes are logical allocation activity volume, not
exact resident ownership. Marker overlap is temporal localization, not causal
proof. Nominal payload bytes are the sizes of the torch.empty weight tensors
requested by UnquantizedLinearMethod and are reported separately.
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
PREFIX_RE = re.compile(r"\bprefix=([^\s]+)")
LAYER_CLASS_RE = re.compile(r"\blayer=([^\s]+)")
INPUT_RE = re.compile(r"\binput=(\d+)\b")
OUTPUT_RE = re.compile(r"\boutput=(\d+)\b")
ELEMENTS_RE = re.compile(r"\belements=(\d+)\b")
DTYPE_RE = re.compile(r"\bdtype=([^\s]+)")

CTOR_BEGIN = "QWEN38_R26_MODEL_CTOR_BEGIN"
CTOR_END = "QWEN38_R26_MODEL_CTOR_END"
MOE_BEGIN = "QWEN38_R26_MODELOPT_MOE_BEGIN"
MOE_END = "QWEN38_R26_MODELOPT_MOE_END"
UNQUANT_BEGIN = "QWEN38_R28_UNQUANT_LINEAR_BEGIN"
UNQUANT_END = "QWEN38_R28_UNQUANT_LINEAR_END"

DTYPE_BYTES = {
    "torch.bfloat16": 2,
    "torch.float16": 2,
    "torch.half": 2,
    "torch.float32": 4,
    "torch.float": 4,
    "torch.float64": 8,
    "torch.double": 8,
    "torch.int8": 1,
    "torch.uint8": 1,
    "torch.int16": 2,
    "torch.int32": 4,
    "torch.int64": 8,
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


@dataclass(frozen=True)
class UnquantInterval:
    seq: int
    prefix: str
    layer_class: str
    input_size: int
    output_size: int
    elements: int
    dtype: str
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


def _required_match(regex: re.Pattern[str], text: str, field: str) -> str:
    match = regex.search(text)
    if match is None:
        raise SystemExit(f"R28 marker missing {field}: {text}")
    return match.group(1)


def pair_unquant(events: list[LogEvent]) -> list[UnquantInterval]:
    pending: dict[int, tuple[LogEvent, str, str, int, int, int, str]] = {}
    pairs: list[UnquantInterval] = []
    for event in events:
        if UNQUANT_BEGIN not in event.text and UNQUANT_END not in event.text:
            continue
        seq_match = SEQ_RE.search(event.text)
        if seq_match is None:
            continue
        seq = int(seq_match.group(1))
        if UNQUANT_BEGIN in event.text:
            pending[seq] = (
                event,
                _required_match(PREFIX_RE, event.text, "prefix"),
                _required_match(LAYER_CLASS_RE, event.text, "layer"),
                int(_required_match(INPUT_RE, event.text, "input")),
                int(_required_match(OUTPUT_RE, event.text, "output")),
                int(_required_match(ELEMENTS_RE, event.text, "elements")),
                _required_match(DTYPE_RE, event.text, "dtype"),
            )
            continue
        prior = pending.pop(seq, None)
        if prior is None:
            continue
        begin, prefix, layer_class, input_size, output_size, elements, dtype = prior
        if event.mono >= begin.mono:
            pairs.append(
                UnquantInterval(
                    seq,
                    prefix,
                    layer_class,
                    input_size,
                    output_size,
                    elements,
                    dtype,
                    begin,
                    event,
                )
            )
    return sorted(pairs, key=lambda row: (row.begin.mono, row.seq))


def rows_in_interval(rows: list[RmEntry], start: float, end: float) -> list[RmEntry]:
    return [row for row in rows if start <= row.mono <= end]


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


def logical_bytes(rows: list[RmEntry] | set[RmEntry], host_page_size: int) -> int:
    return sum(row.page_count * host_page_size for row in rows)


def pct(part: int, whole: int) -> float:
    return 100.0 * part / whole if whole else 0.0


def family(prefix: str) -> str:
    if ".linear_attn." in prefix:
        return "linear_attn"
    if ".self_attn." in prefix:
        return "self_attn"
    if "hyper_connection" in prefix:
        return "hyper_connection"
    if ".mlp.shared_expert." in prefix:
        return "shared_expert"
    if ".mlp.shared_expert_gate" in prefix or ".mlp.gate" in prefix:
        return "router"
    if ".ple." in prefix:
        return "ple"
    return "other"


def payload_bytes(item: UnquantInterval) -> int:
    size = DTYPE_BYTES.get(item.dtype)
    if size is None:
        raise SystemExit(f"unsupported R28 marker dtype: {item.dtype}")
    return item.elements * size


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
    scored = [
        (
            logical_bytes(rows_in_interval(order4, begin.mono, end.mono), host_page_size),
            begin,
            end,
        )
        for begin, end in ctor_pairs
    ]
    ctor_bytes, ctor_begin, ctor_end = max(scored, key=lambda item: item[0])
    ctor_rows = rows_in_interval(order4, ctor_begin.mono, ctor_end.mono)
    ctor_set = set(ctor_rows)

    moe_all = pair_seq(events, MOE_BEGIN, MOE_END)
    moe_selected = [
        item
        for item in moe_all
        if item.end.mono >= ctor_begin.mono and item.begin.mono <= ctor_end.mono
    ]
    moe_rows = row_set_for_intervals(
        ctor_rows, [(item.begin.mono, item.end.mono) for item in moe_selected]
    )
    residual_rows = ctor_set - moe_rows

    unquant_all = pair_unquant(events)
    unquant_selected = [
        item
        for item in unquant_all
        if item.end.mono >= ctor_begin.mono and item.begin.mono <= ctor_end.mono
    ]
    unquant_rows = row_set_for_intervals(
        ctor_rows, [(item.begin.mono, item.end.mono) for item in unquant_selected]
    )
    unquant_residual_rows = unquant_rows & residual_rows

    total_bytes = logical_bytes(order4, host_page_size)
    moe_bytes = logical_bytes(moe_rows, host_page_size)
    residual_bytes = logical_bytes(residual_rows, host_page_size)
    unquant_bytes = logical_bytes(unquant_rows, host_page_size)
    unquant_residual_bytes = logical_bytes(unquant_residual_rows, host_page_size)
    uncovered_residual_bytes = logical_bytes(residual_rows - unquant_rows, host_page_size)
    nominal_bytes = sum(payload_bytes(item) for item in unquant_selected)

    family_stats: dict[str, dict[str, int]] = {}
    for name in (
        "linear_attn",
        "self_attn",
        "hyper_connection",
        "shared_expert",
        "router",
        "ple",
        "other",
    ):
        items = [item for item in unquant_selected if family(item.prefix) == name]
        rows = row_set_for_intervals(
            ctor_rows, [(item.begin.mono, item.end.mono) for item in items]
        )
        residual_part = rows & residual_rows
        family_stats[name] = {
            "calls": len(items),
            "rm": logical_bytes(rows, host_page_size),
            "residual_rm": logical_bytes(residual_part, host_page_size),
            "payload": sum(payload_bytes(item) for item in items),
        }

    threshold = 90.0
    coverage = pct(unquant_residual_bytes, residual_bytes)
    if coverage >= threshold:
        discriminator = "RM_ORDER4_R26_RESIDUAL_PRIMARY_IN_UNQUANTIZED_LINEAR_CONSTRUCTION"
    else:
        discriminator = "RM_ORDER4_R26_RESIDUAL_MIXED_OUTSIDE_UNQUANTIZED_LINEAR_CONSTRUCTION"

    mib = 1048576.0
    ratio = unquant_residual_bytes / nominal_bytes if nominal_bytes else 0.0
    print("R28_UNQUANT_LINEAR_OVERLAP=BEGIN")
    print("analysis_semantics=temporal_boundary_alignment_not_causal_proof")
    print("rm_bytes_semantics=activity_volume_not_resident_ownership")
    print("payload_semantics=nominal_unquantized_weight_tensor_bytes")
    print(f"primary_threshold_pct={threshold:.6f}")
    print(f"clock_anchor_count={len(offsets)}")
    print(f"clock_offset_spread_ms={spread_ms:.6f}")
    print(f"classification_tolerance_s={tolerance_s:.6f}")
    print(f"model_ctor.marker_pair_count={len(ctor_pairs)}")
    print(f"rm_order4.total_activity_mib={total_bytes / mib:.3f}")
    print(f"rm_order4.inside_model_ctor_activity_mib={ctor_bytes / mib:.3f}")
    print(f"r26_modelopt_moe.activity_mib={moe_bytes / mib:.3f}")
    print(f"r26_residual_outside_moe.activity_mib={residual_bytes / mib:.3f}")
    print(f"unquant_linear.marker_pair_count_total={len(unquant_all)}")
    print(f"unquant_linear.selected_call_count={len(unquant_selected)}")
    print(f"unquant_linear.activity_mib={unquant_bytes / mib:.3f}")
    print(
        "unquant_linear.in_r26_residual_activity_mib="
        f"{unquant_residual_bytes / mib:.3f}"
    )
    print(
        "unquant_linear.pct_of_r26_residual="
        f"{coverage:.6f}"
    )
    print(f"unquant_linear.nominal_payload_mib={nominal_bytes / mib:.3f}")
    print(f"unquant_linear.rm_to_nominal_payload_ratio={ratio:.6f}")
    print(
        "r26_residual_uncovered_by_unquant_linear_mib="
        f"{uncovered_residual_bytes / mib:.3f}"
    )

    for name, stats in family_stats.items():
        print(f"family.{name}.calls={stats['calls']}")
        print(f"family.{name}.rm_activity_mib={stats['rm'] / mib:.3f}")
        print(
            f"family.{name}.r26_residual_rm_activity_mib="
            f"{stats['residual_rm'] / mib:.3f}"
        )
        print(f"family.{name}.nominal_payload_mib={stats['payload'] / mib:.3f}")

    top = []
    for item in unquant_selected:
        rows = set(rows_in_interval(ctor_rows, item.begin.mono, item.end.mono))
        rm_value = logical_bytes(rows & residual_rows, host_page_size)
        top.append((rm_value, item))
    top.sort(key=lambda pair: pair[0], reverse=True)
    for rank, (rm_value, item) in enumerate(top[:12], start=1):
        print(
            f"top.{rank}=seq={item.seq} family={family(item.prefix)} "
            f"rm_mib={rm_value / mib:.3f} payload_mib={payload_bytes(item) / mib:.3f} "
            f"input={item.input_size} output={item.output_size} dtype={item.dtype} "
            f"layer={item.layer_class} prefix={item.prefix}"
        )

    print(f"unquant_linear_discriminator={discriminator}")
    print("R28_UNQUANT_LINEAR_OVERLAP=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
