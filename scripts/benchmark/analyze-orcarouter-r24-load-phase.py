#!/usr/bin/env python3
"""Read-only R24 post-hoc alignment of vLLM load phases with RM activity.

This analyzer does not restart the model or change host state. It maps timestamped
container log milestones onto the monotonic trace clock using preserved R24
wall/monotonic anchors, then reports where 64 KiB-path nv_alloc_pages activity
falls relative to model/weight loading milestones.

RM logical bytes remain activity volume, not exact resident ownership. Temporal
phase alignment is not causal proof.
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
BURST_RE = re.compile(
    r"^candidate\.largest_5s=start_monotonic=(\d+\.\d+) "
    r"end_monotonic=(\d+\.\d+) delta_mib=([+-]?\d+\.\d+)$"
)
LOG_RE = re.compile(r"^(\S+)\s+(.*)$")

MODEL_START_RE = re.compile(r"Loading model from scratch", re.IGNORECASE)
WEIGHTS_END_RE = re.compile(
    r"(?:Loading (?:model )?weights took|model weights.*took|weights loaded)",
    re.IGNORECASE,
)
MODEL_END_RE = re.compile(
    r"(?:Model loading took|model loaded in|model loading.*GiB)", re.IGNORECASE
)
GRAPH_START_RE = re.compile(
    r"(?:Captur(?:e|ing).*CUDA graph|cudagraph capture|capturing cudagraph)",
    re.IGNORECASE,
)
MILESTONE_RE = re.compile(
    r"(?:Loading model from scratch|Loading (?:model )?weights|model weights|"
    r"Model loading|safetensor|post[- ]?load|quantiz|"
    r"Captur(?:e|ing).*CUDA graph|cudagraph|KV cache|memory profiling|"
    r"Starting engine core|ModelRunner)",
    re.IGNORECASE,
)


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
    pairs = [
        ("candidate-request-iso.txt", "candidate-request-monotonic-ns.txt"),
        ("trace-window-start-iso.txt", "trace-window-start-monotonic-ns.txt"),
        ("trace-window-end-iso.txt", "trace-window-end-monotonic-ns.txt"),
    ]
    offsets: list[float] = []
    for iso_name, mono_name in pairs:
        wall, mono = read_anchor(root, iso_name, mono_name)
        offsets.append(mono - wall)
    return statistics.median(offsets), offsets


def parse_burst(text: str) -> tuple[float, float, float]:
    for line in text.splitlines():
        match = BURST_RE.match(line.strip())
        if match:
            return float(match.group(1)), float(match.group(2)), float(match.group(3))
    raise SystemExit("largest 5s burst missing from r24-analysis.txt")


def parse_rm_entries(text: str) -> list[RmEntry]:
    result: list[RmEntry] = []
    for line in text.splitlines():
        match = TRACE_RE.search(line)
        if not match:
            continue
        fields = {
            key: int(value, 16 if value.lower().startswith("0x") else 10)
            for key, value in FIELD_RE.findall(match.group(2))
        }
        result.append(
            RmEntry(
                mono=float(match.group(1)),
                page_count=fields.get("page_count", 0),
                page_size=fields.get("page_size", 0),
            )
        )
    return sorted(result, key=lambda row: row.mono)


def parse_logs(text: str, offset: float) -> list[LogEvent]:
    result: list[LogEvent] = []
    for line in text.splitlines():
        match = LOG_RE.match(line)
        if not match:
            continue
        try:
            wall = parse_iso_epoch(match.group(1))
        except ValueError:
            continue
        result.append(LogEvent(wall, wall + offset, match.group(2)))
    return result


def first_match(events: list[LogEvent], regex: re.Pattern[str], after: float | None = None) -> LogEvent | None:
    for event in events:
        if after is not None and event.mono < after:
            continue
        if regex.search(event.text):
            return event
    return None


def activity_mib(entries: list[RmEntry], host_page_size: int, start: float, end: float) -> float:
    logical = sum(
        row.page_count * host_page_size
        for row in entries
        if row.page_size == 65536 and start <= row.mono <= end
    )
    return logical / 1048576.0


def order4(entries: list[RmEntry]) -> list[RmEntry]:
    return [row for row in entries if row.page_size == 65536]


def marker(name: str, event: LogEvent | None, burst_start: float) -> None:
    if event is None:
        print(f"marker.{name}=NA")
        return
    print(
        f"marker.{name}=mono={event.mono:.9f} "
        f"rel_burst_start_s={event.mono - burst_start:+.6f} text={event.text!r}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=pathlib.Path)
    args = parser.parse_args()
    root = args.evidence

    offset, offsets = clock_offset(root)
    spread_ms = (max(offsets) - min(offsets)) * 1000.0
    burst_start, burst_end, burst_mib = parse_burst(read(root / "r24-analysis.txt"))
    entries = parse_rm_entries(read(root / "rm-trace.txt"))
    order4_entries = order4(entries)
    if not order4_entries:
        raise SystemExit("no 64 KiB-path nv_alloc_pages entries in R24 trace")

    host_page_size = int(read(root / "host-page-size.txt").strip())
    logs = parse_logs(read(root / "candidate-container.log"), offset)
    if not logs:
        raise SystemExit("no timestamped candidate log lines parsed")

    model_start = first_match(logs, MODEL_START_RE)
    weights_end = first_match(logs, WEIGHTS_END_RE, model_start.mono if model_start else None)
    model_end = first_match(logs, MODEL_END_RE, model_start.mono if model_start else None)
    graph_start = first_match(logs, GRAPH_START_RE, model_start.mono if model_start else None)

    first_rm = order4_entries[0].mono
    last_rm = order4_entries[-1].mono
    total_mib = activity_mib(order4_entries, host_page_size, first_rm, last_rm)
    burst_rm_mib = activity_mib(order4_entries, host_page_size, burst_start, burst_end)

    if model_start is not None and weights_end is not None:
        weight_phase_mib = activity_mib(
            order4_entries, host_page_size, model_start.mono, weights_end.mono
        )
        coverage = 100.0 * weight_phase_mib / total_mib if total_mib else 0.0
        tolerance = 0.250
        if first_rm >= model_start.mono - tolerance and last_rm <= weights_end.mono + tolerance:
            discriminator = "RM_ORDER4_ACTIVITY_WITHIN_WEIGHT_LOAD_INTERVAL"
        elif first_rm < weights_end.mono < last_rm:
            discriminator = "RM_ORDER4_ACTIVITY_STRADDLES_WEIGHT_LOAD_END"
        elif first_rm >= weights_end.mono:
            discriminator = "RM_ORDER4_ACTIVITY_AFTER_WEIGHT_LOAD"
        else:
            discriminator = "RM_ORDER4_ACTIVITY_PARTLY_BEFORE_MODEL_LOAD"
    else:
        weight_phase_mib = 0.0
        coverage = 0.0
        discriminator = "INSUFFICIENT_WEIGHT_LOAD_MILESTONES"

    context = [
        event
        for event in logs
        if burst_start - 5.0 <= event.mono <= burst_end + 5.0
        and MILESTONE_RE.search(event.text)
    ]

    print("R24_LOAD_PHASE_RM_OVERLAP=BEGIN")
    print("analysis_mode=read_only_post_hoc_no_restart")
    print("rm_bytes_semantics=activity_volume_not_resident_ownership")
    print("correlation_semantics=temporal_phase_alignment_not_causal_proof")
    print(f"clock_anchor_count={len(offsets)}")
    print(f"clock_offset_spread_ms={spread_ms:.6f}")
    print(f"burst5.start_monotonic={burst_start:.9f}")
    print(f"burst5.end_monotonic={burst_end:.9f}")
    print(f"burst5.residual_mib={burst_mib:+.3f}")
    print(f"rm_order4.first_monotonic={first_rm:.9f}")
    print(f"rm_order4.last_monotonic={last_rm:.9f}")
    print(f"rm_order4.total_activity_mib={total_mib:.3f}")
    print(f"rm_order4.burst5_activity_mib={burst_rm_mib:.3f}")
    marker("model_load_start", model_start, burst_start)
    marker("weights_end", weights_end, burst_start)
    marker("model_load_end", model_end, burst_start)
    marker("cuda_graph_start", graph_start, burst_start)
    if model_start is not None and weights_end is not None:
        print(f"weight_load_interval.order4_activity_mib={weight_phase_mib:.3f}")
        print(f"weight_load_interval.coverage_of_trace_order4_pct={coverage:.6f}")
    else:
        print("weight_load_interval.order4_activity_mib=NA")
        print("weight_load_interval.coverage_of_trace_order4_pct=NA")
    print(f"load_phase_discriminator={discriminator}")
    print(f"context_milestone_count={len(context)}")
    for index, event in enumerate(context):
        print(
            f"context.{index:03d}=mono={event.mono:.9f} "
            f"rel_burst_start_s={event.mono - burst_start:+.6f} text={event.text!r}"
        )
    print("R24_LOAD_PHASE_RM_OVERLAP=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
