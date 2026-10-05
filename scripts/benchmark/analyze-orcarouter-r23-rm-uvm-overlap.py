#!/usr/bin/env python3
"""Post-hoc RM/UVM temporal overlap analysis for preserved R23 evidence.

This helper is read-only. It does not restart the managed model and does not
change any VM or driver setting. It consumes the existing R23 trace plus the
existing ownership-analysis output and asks a narrower question:

- do the two uvm_mem_alloc calls temporally bracket the RM system-page activity?
- how much 64 KiB nv_alloc_pages activity falls inside the measured 5 s burst?

Cumulative logical-request bytes are activity volume, not resident ownership.
"""

from __future__ import annotations

import argparse
import pathlib
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

TRACE_RE = re.compile(r"\s(\d+\.\d+):\s+([A-Za-z0-9_]+):\s*(.*)$")
TASK_RE = re.compile(r"(.+?)-(\d+)(?:\s+\(\s*\d+\))?\s+\[")
FIELD_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)=(0x[0-9A-Fa-f]+|-?\d+)\b")
BURST_RE = re.compile(
    r"^residual_largest_5s\.found=1\s+"
    r"start_monotonic=(\d+\.\d+)\s+"
    r"end_monotonic=(\d+\.\d+)\s+"
    r"delta_mib=([+-]?\d+(?:\.\d+)?)$"
)

EVENT_MAP = {
    "nv_alloc_pages_entry": ("nv_alloc_pages", "entry"),
    "nv_alloc_pages_ret": ("nv_alloc_pages", "ret"),
    "nv_alloc_system_pages_entry": ("nv_alloc_system_pages", "entry"),
    "nv_alloc_system_pages_ret": ("nv_alloc_system_pages", "ret"),
    "uvm_mem_alloc_entry": ("uvm_mem_alloc", "entry"),
    "uvm_mem_alloc_ret": ("uvm_mem_alloc", "ret"),
}


@dataclass(frozen=True)
class Call:
    base: str
    comm: str
    pid: int
    start: float
    end: float
    fields: dict[str, int]
    ret: int | None

    @property
    def duration_s(self) -> float:
        return self.end - self.start


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        raise SystemExit(f"missing evidence file: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def number(raw: str) -> int:
    return int(raw, 16 if raw.lower().startswith("0x") else 10)


def parse_burst(text: str) -> tuple[float, float, float]:
    for raw in text.splitlines():
        match = BURST_RE.match(raw.strip())
        if match:
            return float(match.group(1)), float(match.group(2)), float(match.group(3))
    raise SystemExit("missing residual_largest_5s.found=1 in ownership analysis")


def parse_calls(text: str) -> tuple[dict[str, list[Call]], Counter[str], Counter[str]]:
    stacks: dict[tuple[str, int], list[tuple[float, dict[str, int], str]]] = defaultdict(list)
    calls: dict[str, list[Call]] = defaultdict(list)
    unmatched_entries: Counter[str] = Counter()
    unmatched_returns: Counter[str] = Counter()

    for line in text.splitlines():
        match = TRACE_RE.search(line)
        if not match:
            continue
        event = match.group(2)
        if event not in EVENT_MAP:
            continue

        ts = float(match.group(1))
        raw_fields = match.group(3)
        base, kind = EVENT_MAP[event]
        prefix = line[: match.start()]
        task = TASK_RE.search(prefix)
        comm = task.group(1).strip() if task else "UNKNOWN"
        pid = int(task.group(2)) if task else -1
        fields = {key: number(value) for key, value in FIELD_RE.findall(raw_fields)}
        key = (base, pid)

        if kind == "entry":
            stacks[key].append((ts, fields, comm))
            continue

        ret = fields.get("ret", fields.get("raw_ret"))
        if not stacks[key]:
            unmatched_returns[base] += 1
            continue

        start, entry_fields, entry_comm = stacks[key].pop()
        calls[base].append(
            Call(
                base=base,
                comm=entry_comm,
                pid=pid,
                start=start,
                end=ts,
                fields=entry_fields,
                ret=ret,
            )
        )

    for (base, _pid), pending in stacks.items():
        unmatched_entries[base] += len(pending)

    for group in calls.values():
        group.sort(key=lambda call: (call.start, call.end, call.pid))

    return calls, unmatched_entries, unmatched_returns


def logical_bytes(call: Call, host_page_size: int) -> int:
    if call.base != "nv_alloc_pages":
        return 0
    page_count = call.fields.get("page_count")
    if page_count is None:
        return 0
    return page_count * host_page_size


def is_order4(call: Call) -> bool:
    return call.base == "nv_alloc_pages" and call.fields.get("page_size") == 65536


def within(call: Call, start: float, end: float) -> bool:
    return start <= call.start <= end


def nested(parent: Call, child: Call) -> bool:
    return parent.pid == child.pid and parent.start <= child.start and child.end <= parent.end


def mib(value: int) -> float:
    return value / 1048576.0


def pct(part: float, whole: float) -> float:
    return 0.0 if whole == 0 else 100.0 * part / whole


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=pathlib.Path)
    args = parser.parse_args()
    root = args.evidence

    host_page_size = int(read(root / "host-page-size.txt").strip())
    burst_start, burst_end, residual_mib = parse_burst(read(root / "ownership-analysis.txt"))
    calls, unmatched_entries, unmatched_returns = parse_calls(read(root / "ownership-trace.txt"))

    rm_pages = calls["nv_alloc_pages"]
    rm_system = calls["nv_alloc_system_pages"]
    uvm = calls["uvm_mem_alloc"]

    order4_calls = [call for call in rm_pages if is_order4(call)]
    burst_order4 = [call for call in order4_calls if within(call, burst_start, burst_end)]
    total_order4_bytes = sum(logical_bytes(call, host_page_size) for call in order4_calls)
    burst_order4_bytes = sum(logical_bytes(call, host_page_size) for call in burst_order4)

    nested_order4_ids: set[int] = set()
    nested_burst_order4_ids: set[int] = set()
    nested_system_ids: set[int] = set()

    print("R23_RM_UVM_OVERLAP=BEGIN")
    print("analysis_mode=read_only_post_hoc_no_restart")
    print("logical_bytes_semantics=activity_volume_not_resident_ownership")
    print("correlation_semantics=temporal_same_pid_nesting_not_causal_proof")
    print(f"host_page_size={host_page_size}")
    print(f"burst5.start_monotonic={burst_start:.9f}")
    print(f"burst5.end_monotonic={burst_end:.9f}")
    print(f"burst5.residual_delta_mib={residual_mib:+.3f}")
    print(f"nv_alloc_pages.order4_calls.total={len(order4_calls)}")
    print(f"nv_alloc_pages.order4_activity_mib.total={mib(total_order4_bytes):.3f}")
    print(f"nv_alloc_pages.order4_calls.burst5={len(burst_order4)}")
    print(f"nv_alloc_pages.order4_activity_mib.burst5={mib(burst_order4_bytes):.3f}")
    print(
        "burst5.order4_activity_minus_residual_mib="
        f"{mib(burst_order4_bytes) - residual_mib:+.3f}"
    )
    print(
        "burst5.order4_activity_to_residual_pct="
        f"{pct(mib(burst_order4_bytes), residual_mib):.6f}"
    )

    for index, parent in enumerate(uvm, start=1):
        nested_pages = [child for child in rm_pages if nested(parent, child)]
        nested_order4 = [child for child in nested_pages if is_order4(child)]
        nested_burst_order4 = [
            child for child in nested_order4 if within(child, burst_start, burst_end)
        ]
        nested_system = [child for child in rm_system if nested(parent, child)]

        nested_order4_ids.update(id(call) for call in nested_order4)
        nested_burst_order4_ids.update(id(call) for call in nested_burst_order4)
        nested_system_ids.update(id(call) for call in nested_system)

        order4_bytes = sum(logical_bytes(call, host_page_size) for call in nested_order4)
        burst_bytes = sum(
            logical_bytes(call, host_page_size) for call in nested_burst_order4
        )
        overlap_start = max(parent.start, burst_start)
        overlap_end = min(parent.end, burst_end)
        overlap_s = max(0.0, overlap_end - overlap_start)

        print(
            "uvm_mem_alloc_call="
            f"index={index} comm={parent.comm!r} pid={parent.pid} "
            f"start={parent.start:.9f} end={parent.end:.9f} "
            f"duration_s={parent.duration_s:.6f} ret="
            f"{('NONE' if parent.ret is None else hex(parent.ret))} "
            f"burst5_overlap_s={overlap_s:.6f} "
            f"nested_nv_alloc_pages_calls={len(nested_pages)} "
            f"nested_nv_alloc_pages_order4_calls={len(nested_order4)} "
            f"nested_nv_alloc_pages_order4_activity_mib={mib(order4_bytes):.3f} "
            f"nested_burst5_order4_calls={len(nested_burst_order4)} "
            f"nested_burst5_order4_activity_mib={mib(burst_bytes):.3f} "
            f"nested_nv_alloc_system_pages_calls={len(nested_system)}"
        )

    nested_order4_bytes = sum(
        logical_bytes(call, host_page_size)
        for call in order4_calls
        if id(call) in nested_order4_ids
    )
    nested_burst_order4_bytes = sum(
        logical_bytes(call, host_page_size)
        for call in burst_order4
        if id(call) in nested_burst_order4_ids
    )

    print(f"uvm_mem_alloc.calls={len(uvm)}")
    print(
        "uvm_mem_alloc.nested_order4_activity_mib="
        f"{mib(nested_order4_bytes):.3f}"
    )
    print(
        "uvm_mem_alloc.coverage_of_total_order4_activity_pct="
        f"{pct(nested_order4_bytes, total_order4_bytes):.6f}"
    )
    print(
        "uvm_mem_alloc.nested_burst5_order4_activity_mib="
        f"{mib(nested_burst_order4_bytes):.3f}"
    )
    print(
        "uvm_mem_alloc.coverage_of_burst5_order4_activity_pct="
        f"{pct(nested_burst_order4_bytes, burst_order4_bytes):.6f}"
    )
    print(
        "uvm_mem_alloc.coverage_of_nv_alloc_system_pages_calls_pct="
        f"{pct(len(nested_system_ids), len(rm_system)):.6f}"
    )

    for base in ("nv_alloc_pages", "nv_alloc_system_pages", "uvm_mem_alloc"):
        print(f"boundary.{base}.unmatched_entries={unmatched_entries[base]}")
        print(f"boundary.{base}.unmatched_returns={unmatched_returns[base]}")

    burst_coverage = pct(nested_burst_order4_bytes, burst_order4_bytes)
    if not uvm:
        discriminator = "UVM_MEM_ALLOC_SILENT"
    elif burst_coverage >= 90.0:
        discriminator = "UVM_MEM_ALLOC_BRACKETS_MOST_BURST_RM_ACTIVITY"
    elif burst_coverage <= 10.0:
        discriminator = "UVM_MEM_ALLOC_ADJACENT_OR_INCIDENTAL_TO_BURST_RM_ACTIVITY"
    else:
        discriminator = "UVM_MEM_ALLOC_PARTIALLY_BRACKETS_BURST_RM_ACTIVITY"
    print(f"rm_uvm_overlap_discriminator={discriminator}")
    print("R23_RM_UVM_OVERLAP=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
