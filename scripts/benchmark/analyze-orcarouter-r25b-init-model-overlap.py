#!/usr/bin/env python3
"""Align R25b initialize_model markers with direct NVIDIA RM order-4 activity.

The analyzer consumes preserved live-run evidence only. RM bytes are logical
activity volume (page_count * host page size), not exact resident ownership.
Marker overlap is temporal localization, not causal proof.
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
BEGIN_TOKEN = "QWEN38_R25_INIT_MODEL_BEGIN"
END_TOKEN = "QWEN38_R25_INIT_MODEL_END"


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


def pair_init_intervals(events: list[LogEvent]) -> list[tuple[LogEvent, LogEvent]]:
    pairs: list[tuple[LogEvent, LogEvent]] = []
    pending: LogEvent | None = None
    for event in events:
        if BEGIN_TOKEN in event.text:
            pending = event
            continue
        if END_TOKEN in event.text and pending is not None:
            if event.mono >= pending.mono:
                pairs.append((pending, event))
            pending = None
    return pairs


def logical_bytes(rows: list[RmEntry], host_page_size: int) -> int:
    return sum(row.page_count * host_page_size for row in rows)


def in_interval(rows: list[RmEntry], start: float, end: float) -> list[RmEntry]:
    return [row for row in rows if start <= row.mono <= end]


def fmt_marker(name: str, event: LogEvent) -> None:
    print(f"marker.{name}=mono={event.mono:.9f} text={event.text!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=pathlib.Path)
    args = parser.parse_args()
    root = args.evidence

    offset, offsets = clock_offset(root)
    spread_ms = (max(offsets) - min(offsets)) * 1000.0
    events = parse_logs(read(root / "candidate-container.log"), offset)
    pairs = pair_init_intervals(events)
    if not pairs:
        raise SystemExit("R25b initialize_model marker pair missing")

    host_page_size = int(read(root / "host-page-size.txt").strip())
    order4 = [row for row in parse_rm_entries(read(root / "rm-trace.txt")) if row.page_size == 65536]
    if not order4:
        raise SystemExit("no 64 KiB-path nv_alloc_pages activity found")

    scored = [
        (logical_bytes(in_interval(order4, begin.mono, end.mono), host_page_size), begin, end)
        for begin, end in pairs
    ]
    inside_bytes, begin, end = max(scored, key=lambda item: item[0])

    total_bytes = logical_bytes(order4, host_page_size)
    before = [row for row in order4 if row.mono < begin.mono]
    after = [row for row in order4 if row.mono > end.mono]
    before_bytes = logical_bytes(before, host_page_size)
    after_bytes = logical_bytes(after, host_page_size)

    first = order4[0].mono
    last = order4[-1].mono
    tolerance_s = max(0.025, (spread_ms / 1000.0) * 2.0)

    starts_before = first < begin.mono - tolerance_s
    extends_after = last > end.mono + tolerance_s
    if starts_before and extends_after:
        discriminator = "RM_ORDER4_STRADDLES_INITIALIZE_MODEL"
    elif starts_before:
        discriminator = "RM_ORDER4_STARTS_BEFORE_INITIALIZE_MODEL"
    elif extends_after:
        discriminator = "RM_ORDER4_EXTENDS_AFTER_INITIALIZE_MODEL"
    else:
        discriminator = "RM_ORDER4_WITHIN_INITIALIZE_MODEL"

    mib = 1048576.0
    inside_pct = 100.0 * inside_bytes / total_bytes if total_bytes else 0.0

    print("R25B_INIT_MODEL_OVERLAP=BEGIN")
    print("analysis_semantics=temporal_boundary_alignment_not_causal_proof")
    print("rm_bytes_semantics=activity_volume_not_resident_ownership")
    print(f"clock_anchor_count={len(offsets)}")
    print(f"clock_offset_spread_ms={spread_ms:.6f}")
    print(f"classification_tolerance_s={tolerance_s:.6f}")
    print(f"init_marker_pair_count={len(pairs)}")
    fmt_marker("init_model_begin", begin)
    fmt_marker("init_model_end", end)
    print(f"init_interval.duration_s={end.mono - begin.mono:.6f}")
    print(f"rm_order4.first_monotonic={first:.9f}")
    print(f"rm_order4.last_monotonic={last:.9f}")
    print(f"rm_order4.duration_s={last - first:.6f}")
    print(f"rm_order4.total_activity_mib={total_bytes / mib:.3f}")
    print(f"rm_order4.before_init_activity_mib={before_bytes / mib:.3f}")
    print(f"rm_order4.inside_init_activity_mib={inside_bytes / mib:.3f}")
    print(f"rm_order4.after_init_activity_mib={after_bytes / mib:.3f}")
    print(f"rm_order4.inside_init_pct={inside_pct:.6f}")
    print(f"init_model_discriminator={discriminator}")
    print("R25B_INIT_MODEL_OVERLAP=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
