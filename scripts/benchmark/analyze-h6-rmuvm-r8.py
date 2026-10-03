#!/usr/bin/env python3
"""Recover and analyze preserved H6 R8 RM/UVM trace evidence.

This analyzer intentionally works from the already decoded trace text. It does
not rerun the model and does not mutate the preserved evidence.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

DEFAULT_OUT = Path("/tmp/hybrid-6.17-kv16-rmuvm-r8-20261001")

PROBE_EVENTS = (
    "nv_alloc_pages_entry",
    "nv_alloc_pages_ret",
    "pma_alloc_entry",
    "pma_alloc_ret",
    "uvm_dma_alloc_entry",
    "uvm_dma_alloc_ret",
    "uvm_pmm_alloc_entry",
    "uvm_pmm_alloc_ret",
)

LINUX_EVENTS = (
    "mm_compaction_try_to_compact_pages",
    "mm_compaction_begin",
    "mm_compaction_end",
    "mm_vmscan_direct_reclaim_begin",
    "mm_vmscan_direct_reclaim_end",
    "mm_page_alloc_extfrag",
    "nvidia_dev_xid",
)

RETURN_EVENTS = {
    "nv_alloc_pages_ret",
    "pma_alloc_ret",
    "uvm_dma_alloc_ret",
    "uvm_pmm_alloc_ret",
}

TRACE_TS_RE = re.compile(r"\s(?P<ts>\d+\.\d+):\s+")
RM_TS_RE = re.compile(
    r"\[\s*(?P<ts>\d+(?:\.\d+)?)\].*(?:NV_ERR_NO_MEMORY|_memdescAllocInternal)"
)
RET_RE = re.compile(r"\bret=(?P<ret>0x[0-9a-fA-F]+|\d+)\b")


def event_name(line: str) -> str | None:
    """Return the exact traced event name found in a trace-cmd report line."""
    for name in (*PROBE_EVENTS, *LINUX_EVENTS):
        # trace-cmd report normally prints only the event name, not subsystem.
        if re.search(rf":\s+{re.escape(name)}:\s", line):
            return name
        # Keep a conservative fallback for formatting differences.
        if f" {name}: " in line:
            return name
    return None


def trace_timestamp(line: str) -> float | None:
    match = TRACE_TS_RE.search(line)
    return float(match.group("ts")) if match else None


def parse_ret(line: str) -> int | None:
    match = RET_RE.search(line)
    if not match:
        return None
    raw = match.group("ret")
    return int(raw, 16 if raw.lower().startswith("0x") else 10)


def first_rm_timestamp(path: Path) -> tuple[float | None, list[str]]:
    if not path.exists():
        return None, []

    lines = path.read_text(errors="replace").splitlines()
    for line in lines:
        match = RM_TS_RE.search(line)
        if match:
            return float(match.group("ts")), lines
    return None, lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "evidence",
        nargs="?",
        type=Path,
        default=DEFAULT_OUT,
        help="R8 evidence directory",
    )
    args = parser.parse_args()

    out: Path = args.evidence
    trace_path = out / "allocator-trace.txt"
    kernel_path = out / "kernel-errors-monotonic.txt"

    if not trace_path.is_file():
        raise SystemExit(f"missing decoded trace: {trace_path}")

    trace_lines = trace_path.read_text(errors="replace").splitlines()
    counts: Counter[str] = Counter()
    probe_rows: list[tuple[float, str, str]] = []
    return_rows: list[tuple[float, str, int | None, str]] = []

    for line in trace_lines:
        name = event_name(line)
        if name is None:
            continue

        counts[name] += 1
        if name in PROBE_EVENTS:
            ts = trace_timestamp(line)
            if ts is not None:
                probe_rows.append((ts, name, line))
                if name in RETURN_EVENTS:
                    return_rows.append((ts, name, parse_ret(line), line))

    rm_ts, kernel_lines = first_rm_timestamp(kernel_path)

    print("=== R8 RECOVERY ANALYSIS ===")
    print(f"evidence={out}")
    print(f"trace_lines={len(trace_lines)}")
    print(f"rm_monotonic={rm_ts if rm_ts is not None else 'NONE'}")
    print()

    print("=== PROBE EVENT COUNTS ===")
    for name in PROBE_EVENTS:
        print(f"{name}={counts[name]}")
    print(f"probe_total={sum(counts[name] for name in PROBE_EVENTS)}")
    print()

    print("=== LINUX/NVIDIA TRACE EVENT COUNTS ===")
    for name in LINUX_EVENTS:
        print(f"{name}={counts[name]}")
    print()

    nv_oom_returns = [
        row for row in return_rows if row[2] == 0x51
    ]
    print("=== RETURN STATUS SUMMARY ===")
    for name in sorted(RETURN_EVENTS):
        values = Counter(
            ret for _, event, ret, _ in return_rows
            if event == name and ret is not None
        )
        formatted = ", ".join(
            f"0x{value:x}({value})={count}"
            for value, count in sorted(values.items())
        ) or "NONE"
        print(f"{name}: {formatted}")
    print(f"NV_ERR_NO_MEMORY_RETURNS={len(nv_oom_returns)}")
    print()

    if nv_oom_returns:
        print("=== NV_ERR_NO_MEMORY RETURN EVENTS ===")
        for _, _, _, line in nv_oom_returns:
            print(line)
        print()

    if rm_ts is not None:
        print("=== PROBE EVENTS WITHIN RM +/-3s ===")
        near = [row for row in probe_rows if abs(row[0] - rm_ts) <= 3.0]
        print(f"count={len(near)}")
        for ts, name, line in near:
            print(f"delta={ts - rm_ts:+.9f}s event={name} :: {line}")
        print()

        print("=== NEAREST PROBE EVENT PER TYPE ===")
        for name in PROBE_EVENTS:
            rows = [row for row in probe_rows if row[1] == name]
            if not rows:
                print(f"{name}=NONE")
                continue
            nearest = min(rows, key=lambda row: abs(row[0] - rm_ts))
            print(
                f"{name}: delta={nearest[0] - rm_ts:+.9f}s :: {nearest[2]}"
            )
        print()

    print("=== FIRST KERNEL ERROR LINES ===")
    for line in kernel_lines[:20]:
        print(line)

    # Explicit interpretation guard: zero parser counts no longer silently mean
    # that the probe subsystem was absent. We separately show Linux event counts
    # so the user can tell whether the decoded trace itself is populated.
    probe_total = sum(counts[name] for name in PROBE_EVENTS)
    linux_total = sum(counts[name] for name in LINUX_EVENTS)
    print()
    print("=== RECOVERY CLASSIFICATION ===")
    if probe_total == 0 and linux_total > 0:
        print("PROBE_RUNTIME_EVENTS=ZERO")
        print(
            "Decoded Linux trace is populated, but none of the eight target "
            "probe event names occur in it."
        )
    elif probe_total > 0:
        print("PROBE_RUNTIME_EVENTS=PRESENT")
    else:
        print("TRACE_EVENT_PARSE=INCONCLUSIVE")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
