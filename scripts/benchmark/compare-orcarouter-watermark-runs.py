#!/usr/bin/env python3
"""Compare Linux allocator-state evidence across OrcaRouter mitigation runs.

This is a read-only post-processing tool. It consumes the R11 allocator-state
collector output from one or more runs and emits comparable Normal-zone buddy,
watermark, memory, reclaim, and compaction metrics.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import statistics
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

PAGE_SIZE = 4096
SAMPLE_RE = re.compile(
    r"^===== sample seq=(?P<seq>\d+) wall=(?P<wall>\S+) monotonic_ns=(?P<mono>\d+) =====$"
)
SECTION_RE = re.compile(r"^--- (?P<name>/proc/\S+) ---$")
BUDDY_RE = re.compile(r"^Node\s+(?P<node>\d+),\s+zone\s+(?P<zone>\S+)\s+(?P<values>.+)$")
ZONE_RE = re.compile(r"^Node\s+(?P<node>\d+),\s+zone\s+(?P<zone>\S+)")

VMSTAT_KEYS = (
    "allocstall_normal",
    "pgscan_kswapd",
    "pgsteal_kswapd",
    "pgscan_direct",
    "pgsteal_direct",
    "kswapd_low_wmark_hit_quickly",
    "kswapd_high_wmark_hit_quickly",
    "compact_stall",
    "compact_fail",
    "compact_success",
)


@dataclass
class Sample:
    seq: int
    wall: str
    monotonic_ns: int
    sections: Dict[str, str]


def parse_samples(path: pathlib.Path) -> List[Sample]:
    samples: List[Sample] = []
    current_meta = None
    current_sections: Dict[str, List[str]] = {}
    current_section = None

    def flush() -> None:
        nonlocal current_meta, current_sections, current_section
        if current_meta is None:
            return
        seq, wall, mono = current_meta
        samples.append(
            Sample(
                seq=seq,
                wall=wall,
                monotonic_ns=mono,
                sections={key: "\n".join(value) for key, value in current_sections.items()},
            )
        )
        current_meta = None
        current_sections = {}
        current_section = None

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = SAMPLE_RE.match(raw)
        if match:
            flush()
            current_meta = (
                int(match.group("seq")),
                match.group("wall"),
                int(match.group("mono")),
            )
            continue
        section = SECTION_RE.match(raw)
        if section and current_meta is not None:
            current_section = section.group("name")
            current_sections.setdefault(current_section, [])
            continue
        if current_meta is not None and current_section is not None:
            current_sections[current_section].append(raw)
    flush()
    return samples


def parse_key_values(text: str) -> Dict[str, int]:
    values: Dict[str, int] = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2:
            try:
                values[parts[0].rstrip(":")] = int(parts[1])
            except ValueError:
                continue
    return values


def normal_buddy_ge4_mib(text: str) -> float | None:
    for line in text.splitlines():
        match = BUDDY_RE.match(line.strip())
        if not match:
            continue
        if int(match.group("node")) != 0 or match.group("zone") != "Normal":
            continue
        try:
            counts = [int(value) for value in match.group("values").split()]
        except ValueError:
            return None
        pages = sum(count * (1 << order) for order, count in enumerate(counts) if order >= 4)
        return pages * PAGE_SIZE / 1024 / 1024
    return None


def parse_normal_zone(text: str) -> Dict[str, int]:
    inside = False
    result: Dict[str, int] = {}
    for raw in text.splitlines():
        stripped = raw.strip()
        zone = ZONE_RE.match(stripped)
        if zone:
            inside = int(zone.group("node")) == 0 and zone.group("zone") == "Normal"
            continue
        if not inside:
            continue
        match = re.match(r"^pages free\s+(\d+)$", stripped)
        if match:
            result["free"] = int(match.group(1))
            continue
        match = re.match(r"^(min|low|high)\s+(\d+)$", stripped)
        if match:
            result[match.group(1)] = int(match.group(2))
    return result


def metric_stats(values: Iterable[float]) -> Tuple[float, float, float, float]:
    data = list(values)
    if not data:
        return (float("nan"),) * 4
    return data[0], min(data), statistics.median(data), data[-1]


def read_rm_count(evidence: pathlib.Path) -> int | None:
    summary = evidence / "r11-summary.txt"
    if not summary.is_file():
        return None
    for line in summary.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("rm_oom_count="):
            try:
                return int(line.split("=", 1)[1])
            except ValueError:
                return None
    return None


def format_float(value: float) -> str:
    if value != value:
        return "NA"
    return f"{value:.3f}"


def summarize(label: str, evidence: pathlib.Path) -> None:
    state = evidence / "allocator-state"
    fast_path = state / "fast-state.txt"
    slow_path = state / "slow-state.txt"
    if not fast_path.is_file() or not slow_path.is_file():
        raise SystemExit(f"{label}: allocator-state samples missing under {evidence}")

    fast = parse_samples(fast_path)
    slow = parse_samples(slow_path)
    if not fast or not slow:
        raise SystemExit(f"{label}: parsed sample set is empty")

    buddy = [
        value
        for sample in fast
        if (value := normal_buddy_ge4_mib(sample.sections.get("/proc/buddyinfo", ""))) is not None
    ]
    mem_available = []
    mem_free = []
    swap_free = []
    for sample in fast:
        mem = parse_key_values(sample.sections.get("/proc/meminfo", ""))
        if "MemAvailable" in mem:
            mem_available.append(mem["MemAvailable"] / 1024)
        if "MemFree" in mem:
            mem_free.append(mem["MemFree"] / 1024)
        if "SwapFree" in mem:
            swap_free.append(mem["SwapFree"] / 1024)

    first_vm = parse_key_values(fast[0].sections.get("/proc/vmstat", ""))
    last_vm = parse_key_values(fast[-1].sections.get("/proc/vmstat", ""))

    free_minus_low = []
    free_minus_high = []
    for sample in slow:
        zone = parse_normal_zone(sample.sections.get("/proc/zoneinfo", ""))
        if {"free", "low"}.issubset(zone):
            free_minus_low.append(zone["free"] - zone["low"])
        if {"free", "high"}.issubset(zone):
            free_minus_high.append(zone["free"] - zone["high"])

    b0, bmin, bmed, bend = metric_stats(buddy)
    ma0, mamin, mamed, maend = metric_stats(mem_available)
    mf0, mfmin, mfmed, mfend = metric_stats(mem_free)
    sf0, sfmin, sfmed, sfend = metric_stats(swap_free)

    rm_count = read_rm_count(evidence)
    print(
        " ".join(
            (
                f"run={label}",
                f"rm_oom_count={rm_count if rm_count is not None else 'NA'}",
                f"fast_samples={len(fast)}",
                f"slow_samples={len(slow)}",
                f"normal_ge4_start_mib={format_float(b0)}",
                f"normal_ge4_min_mib={format_float(bmin)}",
                f"normal_ge4_median_mib={format_float(bmed)}",
                f"normal_ge4_end_mib={format_float(bend)}",
                f"memavailable_min_mib={format_float(mamin)}",
                f"memfree_min_mib={format_float(mfmin)}",
                f"swapfree_min_mib={format_float(sfmin)}",
                f"normal_free_minus_low_min_pages={min(free_minus_low) if free_minus_low else 'NA'}",
                f"normal_free_minus_high_min_pages={min(free_minus_high) if free_minus_high else 'NA'}",
            )
        )
    )
    for key in VMSTAT_KEYS:
        if key in first_vm and key in last_vm:
            print(f"run={label} vmstat_delta {key}={last_vm[key] - first_vm[key]}")


def parse_run(value: str) -> Tuple[str, pathlib.Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--run must be LABEL=/path/to/r11-evidence")
    label, raw_path = value.split("=", 1)
    if not label or not raw_path:
        raise argparse.ArgumentTypeError("--run must be LABEL=/path/to/r11-evidence")
    return label, pathlib.Path(raw_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run",
        action="append",
        required=True,
        type=parse_run,
        help="LABEL=/path/to/R11-evidence; repeat for each run",
    )
    args = parser.parse_args()

    print("ORCA_WATERMARK_RUN_COMPARISON=BEGIN")
    for label, evidence in args.run:
        summarize(label, evidence)
    print("ORCA_WATERMARK_RUN_COMPARISON=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
