#!/usr/bin/env python3
"""Read-only H38 allocator trajectories; no protection verdict from heuristics.

Uses the established R21/R22 4-KiB page, node0/Normal and order-4+ conventions.
Produces measured-time-aligned values only. Reservoir health and safe-to-continue
are intentionally NOT inferred from a single run.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import pathlib
import re
from zoneinfo import ZoneInfo

PAGE_SIZE = 4096
TARGETS = (-60, -30, -10, -5, -1, 0)
SAMPLE = re.compile(r"^===== sample seq=(\d+) wall=(\S+) monotonic_ns=(\d+) =====$")
BUDDY = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+)\s+(.+)$")
PAGETYPE = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+),\s+type\s+(\S+)\s+(.+)$")
PROTECT = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) PROTECT stopping ")
CSV_FIELDS = (
    "source", "kind", "wall_utc", "offset_s", "normal_o4_mib",
    "normal_o4plus_mib", "unmovable_o4plus_mib", "movable_o4plus_mib",
    "memavailable_mib", "memfree_mib", "swapfree_mib",
    "psi_some_avg10", "psi_full_avg10",
)


def timestamp(raw: str) -> dt.datetime:
    value = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError(f"timestamp lacks timezone: {raw}")
    return value.astimezone(dt.timezone.utc)


def samples(path: pathlib.Path) -> list[tuple[dt.datetime, int, str]]:
    if not path.is_file():
        raise ValueError(f"missing collector sample file: {path}")
    result: list[tuple[dt.datetime, int, str]] = []
    current: tuple[dt.datetime, int] | None = None
    body: list[str] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = SAMPLE.match(line)
        if match:
            if current is not None:
                result.append((current[0], current[1], "\n".join(body)))
            current = timestamp(match.group(2)), int(match.group(3))
            body = []
        elif current is not None:
            body.append(line)
    if current is not None:
        result.append((current[0], current[1], "\n".join(body)))
    if not result:
        raise ValueError(f"collector has no samples: {path}")
    if any(b[1] <= a[1] for a, b in zip(result, result[1:])):
        raise ValueError(f"non-increasing collector monotonic clock: {path}")
    return result


def counts(raw: str) -> list[int]:
    result = []
    for token in raw.split():
        if token == ">100000":
            result.append(100001)  # Same conservative lower bound as R21/R22.
        else:
            try:
                result.append(int(token))
            except ValueError:
                continue
    return result


def mib(values: list[int], first_order: int, last_order: int | None = None) -> float:
    return (
        sum(
            count * (1 << order)
            for order, count in enumerate(values)
            if order >= first_order and (last_order is None or order <= last_order)
        )
        * PAGE_SIZE / (1024 * 1024)
    )


def parse_body(body: str, kind: str) -> dict[str, float]:
    section = ""
    values: dict[str, float] = {}
    found = False
    types: set[str] = set()
    for raw in body.splitlines():
        if raw.startswith("--- ") and raw.endswith(" ---"):
            section = raw[4:-4]
            continue
        line = raw.strip()
        if kind == "fast" and section == "/proc/buddyinfo":
            match = BUDDY.match(line)
            if match and match.group(1) == "0" and match.group(2) == "Normal":
                blocks = counts(match.group(3))
                if len(blocks) < 5:
                    raise ValueError("Normal buddyinfo has no order-4 column")
                values["normal_o4_mib"] = mib(blocks, 4, 4)
                values["normal_o4plus_mib"] = mib(blocks, 4)
                found = True
        elif kind == "fast" and section == "/proc/meminfo" and ":" in line:
            key, rest = line.split(":", 1)
            if key in ("MemAvailable", "MemFree", "SwapFree"):
                tokens = rest.split()
                if tokens:
                    values[key.lower() + "_mib"] = int(tokens[0]) / 1024
        elif kind == "fast" and section == "/proc/pressure/memory":
            if line.startswith(("some ", "full ")):
                name = line.split()[0]
                match = re.search(r"\bavg10=([0-9.]+)", line)
                if match:
                    values["psi_" + name + "_avg10"] = float(match.group(1))
        elif kind == "slow" and section == "/proc/pagetypeinfo":
            match = PAGETYPE.match(line)
            if match and match.group(1) == "0" and match.group(2) == "Normal":
                group = match.group(3)
                if group in ("Unmovable", "Movable"):
                    values[group.lower() + "_o4plus_mib"] = mib(counts(match.group(4)), 4)
                    types.add(group)
    if kind == "fast" and (not found or not all(
        field in values for field in ("memavailable_mib", "memfree_mib", "swapfree_mib")
    )):
        raise ValueError("fast sample missing node0 Normal or required meminfo")
    if kind == "slow" and types != {"Unmovable", "Movable"}:
        raise ValueError("slow sample missing Normal Unmovable/Movable rows")
    return values


def rm_event(root: pathlib.Path) -> dt.datetime | None:
    event_root = root / "allocator-state" / "events"
    events: list[dt.datetime] = []
    for directory in sorted(event_root.glob("rm-oom-*")):
        if not directory.is_dir():
            continue
        fields = dict(
            line.split("=", 1)
            for line in (directory / "meta.txt").read_text(encoding="utf-8").splitlines()
            if "=" in line
        )
        events.append(timestamp(fields["wall"]))
    return min(events) if events else None


def protection_event(root: pathlib.Path, timezone: str) -> dt.datetime | None:
    log = root / "memory-monitor.log"
    if not log.is_file():
        return None
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines:
        match = PROTECT.match(line)
        if match:
            local = dt.datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
            return local.replace(tzinfo=ZoneInfo(timezone)).astimezone(dt.timezone.utc)
    return None


def get_event(root: pathlib.Path, timezone: str) -> tuple[str, dt.datetime]:
    rm = rm_event(root)
    if rm is not None:
        return "RM_EVENT", rm
    protected = protection_event(root, timezone)
    if protected is not None:
        return "PROTECTED_STOP", protected
    fast = samples(root / "allocator-state" / "fast-state.txt")
    return "NO_RM_OR_PROTECTION_EVENT_LAST_SAMPLE", fast[-1][0]


def build(root: pathlib.Path, event: dt.datetime, source: str) -> tuple[
    list[dict[str, str | float]], dict[str, list[dict[str, str | float]]]
]:
    rows: list[dict[str, str | float]] = []
    streams: dict[str, list[dict[str, str | float]]] = {}
    for kind in ("fast", "slow"):
        parsed = samples(root / "allocator-state" / (kind + "-state.txt"))
        stream: list[dict[str, str | float]] = []
        for wall, _, body in parsed:
            row: dict[str, str | float] = {
                "source": source, "kind": kind, "wall_utc": wall.isoformat(),
                "offset_s": round((wall - event).total_seconds(), 3),
            }
            row.update(parse_body(body, kind))
            rows.append(row)
            stream.append(row)
        streams[kind] = stream
    return rows, streams


def nearest(stream: list[dict[str, str | float]], target: int, max_distance: float
            ) -> dict[str, str | float] | None:
    chosen = min(stream, key=lambda row: abs(float(row["offset_s"]) - target))
    if abs(float(chosen["offset_s"]) - target) > max_distance:
        return None
    return chosen


def fmt(row: dict[str, str | float] | None, metrics: tuple[str, ...]) -> str:
    if row is None:
        return "coverage=MISSING"
    return (
        f"coverage=OBSERVED actual_offset_s={float(row['offset_s']):+.3f} "
        + " ".join(
            f"{key}={float(row[key]):.3f}" for key in metrics if key in row
        )
    )


FAST_METRICS = (
    "normal_o4_mib", "normal_o4plus_mib",
    "memavailable_mib", "memfree_mib", "swapfree_mib",
    "psi_some_avg10", "psi_full_avg10",
)
SLOW_METRICS = ("unmovable_o4plus_mib", "movable_o4plus_mib")


def analysis(evidence: pathlib.Path, timezone: str, reference: pathlib.Path | None
             ) -> tuple[list[dict[str, str | float]], str]:
    event_kind, event = get_event(evidence, timezone)
    rows, streams = build(evidence, event, "h38")
    report = [
        "H38_ALLOCATOR_PROTECTION_TRAJECTORY=BEGIN",
        f"event_type={event_kind} event_utc={event.isoformat()}",
        "page_size_bytes=4096 node=0 zone=Normal min_order=4",
        "WARNING: metrics are snapshot reservoirs, not proof of contiguous availability",
        "RESERVOIR_CLASSIFICATION=UNDETERMINED",
    ]
    for kind, metrics, window in (
        ("fast", FAST_METRICS, 2.5), ("slow", SLOW_METRICS, 7.5)
    ):
        for target in TARGETS:
            report.append(
                f"h38_{kind}=T{target:+d} "
                + fmt(nearest(streams[kind], target, window), metrics)
            )
    if reference is not None:
        ref_type, ref_event = get_event(reference, timezone)
        if ref_type != "RM_EVENT":
            raise ValueError("reference must contain captured strict RM event snapshots")
        ref_rows, ref_streams = build(reference, ref_event, "strict_rm_reference")
        rows.extend(ref_rows)
        report.append(
            f"reference_type={ref_type} reference_event_utc={ref_event.isoformat()}"
        )
        for kind, metrics, window in (
            ("fast", FAST_METRICS, 2.5), ("slow", SLOW_METRICS, 7.5)
        ):
            for target in TARGETS:
                report.append(
                    f"reference_{kind}=T{target:+d} "
                    + fmt(nearest(ref_streams[kind], target, window), metrics)
                )
        report.append("COMPARISON_VERDICT=UNDETERMINED; no classifier threshold inferred")
    report.append("H38_ALLOCATOR_PROTECTION_TRAJECTORY=END")
    return rows, "\n".join(report) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=pathlib.Path, required=True)
    parser.add_argument("--csv", type=pathlib.Path, required=True)
    parser.add_argument("--report", type=pathlib.Path, required=True)
    parser.add_argument("--reference", type=pathlib.Path)
    parser.add_argument("--monitor-timezone", default="Asia/Seoul")
    args = parser.parse_args()
    rows, report = analysis(args.evidence, args.monitor_timezone, args.reference)
    with args.csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    args.report.write_text(report, encoding="utf-8")
    print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
