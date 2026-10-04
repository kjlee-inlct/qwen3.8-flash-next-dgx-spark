#!/usr/bin/env python3
"""Analyze R24 H6 16 GiB RM mitigation evidence.

The allocator residual is compared with the fixed R22 v0.29/PLE-mmap/16 GiB
control. RM logical bytes are activity volume, not exact resident ownership.
"""

from __future__ import annotations

import argparse
import pathlib
import re
from collections import Counter, defaultdict
from dataclasses import dataclass

BASELINE_R22_5S_MIB = 75138.043

TRACE_RE = re.compile(r"\s(\d+\.\d+):\s+([A-Za-z0-9_]+):\s*(.*)$")
TASK_RE = re.compile(r"(.+?)-(\d+)(?:\s+\(\s*\d+\))?\s+\[")
FIELD_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)=(0x[0-9A-Fa-f]+|-?\d+)\b")
SAMPLE_RE = re.compile(r"^===== sample seq=\d+ wall=(\S+) monotonic_ns=(\d+) =====$")
BUDDY_RE = re.compile(r"^Node\s+0,\s+zone\s+Normal\s+(.+)$")
PAGETYPE_RE = re.compile(r"^Node\s+0,\s+zone\s+Normal,\s+type\s+(\S+)\s+(.+)$")

EVENT_MAP = {
    "nv_alloc_pages_entry": ("nv_alloc_pages", "entry"),
    "nv_alloc_pages_ret": ("nv_alloc_pages", "ret"),
    "nv_alloc_system_pages_entry": ("nv_alloc_system_pages", "entry"),
    "nv_alloc_system_pages_ret": ("nv_alloc_system_pages", "ret"),
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


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        raise SystemExit(f"missing evidence file: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def number(raw: str) -> int:
    return int(raw, 16 if raw.lower().startswith("0x") else 10)


def parse_meminfo(lines: list[str]) -> dict[str, float]:
    result: dict[str, float] = {}
    for line in lines:
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        try:
            result[key] = float(rest.split()[0]) / 1024.0
        except (ValueError, IndexError):
            pass
    return result


def residual(base: dict[str, float], now: dict[str, float]) -> float:
    def delta(key: str) -> float:
        return now.get(key, 0.0) - base.get(key, 0.0)

    explained = (
        delta("Active(anon)")
        + delta("Inactive(anon)")
        + delta("Active(file)")
        + delta("Inactive(file)")
        + delta("Unevictable")
        + delta("Slab")
        + delta("KReclaimable")
        - delta("SReclaimable")
        + delta("PageTables")
        + delta("SecPageTables")
        + delta("KernelStack")
    )
    return -delta("MemFree") - explained


def parse_samples(path: pathlib.Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    section = ""
    for line in read(path).splitlines():
        match = SAMPLE_RE.match(line)
        if match:
            if current is not None:
                rows.append(current)
            current = {"mono_ns": int(match.group(2)), "sections": {}}
            section = ""
            continue
        if current is None:
            continue
        if line.startswith("--- ") and line.endswith(" ---"):
            section = line[4:-4]
            current["sections"].setdefault(section, [])  # type: ignore[union-attr]
        elif section:
            current["sections"][section].append(line)  # type: ignore[index]
    if current is not None:
        rows.append(current)
    return rows


def largest(points: list[tuple[dict[str, object], float]], seconds: float):
    best = None
    for index, (left, left_value) in enumerate(points):
        for right, right_value in points[index + 1 :]:
            elapsed = (int(right["mono_ns"]) - int(left["mono_ns"])) / 1e9
            if elapsed < seconds - 0.6:
                continue
            if elapsed > seconds + 0.6:
                break
            gain = right_value - left_value
            if best is None or gain > best[2]:
                best = (left, right, gain)
            break
    return best


def normal_free_mib(lines: list[str], page_size: int) -> float | None:
    for line in lines:
        match = BUDDY_RE.match(line.strip())
        if not match:
            continue
        counts = [int(token) for token in match.group(1).split()]
        pages = sum(value * (1 << order) for order, value in enumerate(counts))
        return pages * page_size / 1048576.0
    return None


def pagetype_high_mib(
    lines: list[str], page_size: int, wanted: str, min_order: int = 4
) -> float | None:
    for line in lines:
        match = PAGETYPE_RE.match(line.strip())
        if not match or match.group(1) != wanted:
            continue
        counts: list[int] = []
        for token in match.group(2).split():
            token = token.removeprefix(">")
            try:
                counts.append(int(token))
            except ValueError:
                return None
        pages = sum(
            value * (1 << order)
            for order, value in enumerate(counts)
            if order >= min_order
        )
        return pages * page_size / 1048576.0
    return None


def vmstat_value(lines: list[str], key: str) -> int | None:
    for line in lines:
        fields = line.split()
        if len(fields) == 2 and fields[0] == key:
            return int(fields[1])
    return None


def nearest_sample(samples: list[dict[str, object]], target_ns: int) -> dict[str, object]:
    return min(samples, key=lambda row: abs(int(row["mono_ns"]) - target_ns))


def parse_calls(text: str) -> tuple[dict[str, list[Call]], Counter[str], Counter[str]]:
    stacks: dict[tuple[str, int], list[tuple[float, dict[str, int], str]]] = defaultdict(list)
    calls: dict[str, list[Call]] = defaultdict(list)
    unmatched_entries: Counter[str] = Counter()
    unmatched_returns: Counter[str] = Counter()

    for line in text.splitlines():
        match = TRACE_RE.search(line)
        if not match or match.group(2) not in EVENT_MAP:
            continue
        timestamp = float(match.group(1))
        event = match.group(2)
        raw_fields = match.group(3)
        base, kind = EVENT_MAP[event]
        task_match = TASK_RE.search(line[: match.start()])
        comm = task_match.group(1).strip() if task_match else "UNKNOWN"
        pid = int(task_match.group(2)) if task_match else -1
        fields = {key: number(value) for key, value in FIELD_RE.findall(raw_fields)}
        key = (base, pid)
        if kind == "entry":
            stacks[key].append((timestamp, fields, comm))
            continue
        ret = fields.get("ret", fields.get("raw_ret"))
        if not stacks[key]:
            unmatched_returns[base] += 1
            continue
        start, entry_fields, entry_comm = stacks[key].pop()
        calls[base].append(
            Call(base, entry_comm, pid, start, timestamp, entry_fields, ret)
        )

    for (base, _pid), pending in stacks.items():
        unmatched_entries[base] += len(pending)
    for group in calls.values():
        group.sort(key=lambda call: (call.start, call.end, call.pid))
    return calls, unmatched_entries, unmatched_returns


def logical_bytes(call: Call, host_page_size: int) -> int:
    page_count = call.fields.get("page_count", 0)
    return page_count * host_page_size


def burst_band(ratio_pct: float) -> str:
    if ratio_pct >= 90.0:
        return "BURST_UNCHANGED"
    if ratio_pct >= 75.0:
        return "BURST_PARTIAL_REDUCTION"
    if ratio_pct > 25.0:
        return "BURST_MATERIAL_REDUCTION"
    return "BURST_STRONGLY_SUPPRESSED"


def mitigation_discriminator(band: str, rm_oom_count: int) -> str:
    if rm_oom_count:
        if band == "BURST_UNCHANGED":
            return "H6_NO_RM_MITIGATION_HOST_FAIL"
        return "H6_EARLY_BURST_IMPROVED_HOST_FAIL"
    if band in {"BURST_MATERIAL_REDUCTION", "BURST_STRONGLY_SUPPRESSED"}:
        return "H6_STRONG_MITIGATION_CANDIDATE"
    if band == "BURST_PARTIAL_REDUCTION":
        return "H6_PARTIAL_CLEAN_MITIGATION_CANDIDATE"
    return "H6_LATER_FAILURE_MARGIN_ONLY"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=pathlib.Path)
    args = parser.parse_args()
    root = args.evidence

    page_size = int(read(root / "host-page-size.txt").strip())
    trace_start_ns = int(read(root / "trace-window-start-monotonic-ns.txt").strip())
    trace_end_ns = int(read(root / "trace-window-end-monotonic-ns.txt").strip())

    base_mem = parse_meminfo(
        read(root / "poststop-after-compact" / "proc-meminfo.txt").splitlines()
    )
    fast_samples = parse_samples(root / "allocator-state" / "fast-state.txt")
    points: list[tuple[dict[str, object], float]] = []
    for sample in fast_samples:
        sections = sample["sections"]
        mem = parse_meminfo(sections.get("/proc/meminfo", []))  # type: ignore[union-attr]
        if mem:
            points.append((sample, residual(base_mem, mem)))
    if not points:
        raise SystemExit("no allocator samples available")

    best1 = largest(points, 1.0)
    best5 = largest(points, 5.0)
    if best5 is None:
        raise SystemExit("no five-second allocator window available")

    left, right, burst_mib = best5
    burst_start_ns = int(left["mono_ns"])
    burst_end_ns = int(right["mono_ns"])
    ratio_pct = 100.0 * burst_mib / BASELINE_R22_5S_MIB
    reduction_pct = 100.0 - ratio_pct
    band = burst_band(ratio_pct)
    trace_covers_burst = int(
        trace_start_ns <= burst_start_ns and burst_end_ns <= trace_end_ns
    )

    calls, unmatched_entries, unmatched_returns = parse_calls(read(root / "rm-trace.txt"))
    page_calls = calls["nv_alloc_pages"]
    system_calls = calls["nv_alloc_system_pages"]
    order4 = [call for call in page_calls if call.fields.get("page_size") == 65536]
    order0 = [call for call in page_calls if call.fields.get("page_size") == 4096]
    order4_total = sum(logical_bytes(call, page_size) for call in order4)
    order0_total = sum(logical_bytes(call, page_size) for call in order0)
    burst_order4 = [
        call
        for call in order4
        if burst_start_ns / 1e9 <= call.start <= burst_end_ns / 1e9
    ]
    burst_order4_bytes = sum(logical_bytes(call, page_size) for call in burst_order4)

    slow_samples = parse_samples(root / "allocator-state" / "slow-state.txt")
    start_slow = nearest_sample(slow_samples, burst_start_ns) if slow_samples else None
    end_slow = nearest_sample(slow_samples, burst_end_ns) if slow_samples else None

    left_sections = left["sections"]
    right_sections = right["sections"]
    left_normal = normal_free_mib(
        left_sections.get("/proc/buddyinfo", []), page_size  # type: ignore[union-attr]
    )
    right_normal = normal_free_mib(
        right_sections.get("/proc/buddyinfo", []), page_size  # type: ignore[union-attr]
    )
    left_free = vmstat_value(
        left_sections.get("/proc/vmstat", []), "nr_free_pages"  # type: ignore[union-attr]
    )
    right_free = vmstat_value(
        right_sections.get("/proc/vmstat", []), "nr_free_pages"  # type: ignore[union-attr]
    )

    kernel_errors = (root / "kernel-errors.txt")
    kernel_text = kernel_errors.read_text(encoding="utf-8", errors="replace") if kernel_errors.is_file() else ""
    rm_oom_count = sum(
        1
        for line in kernel_text.splitlines()
        if "NV_ERR_NO_MEMORY" in line or "_memdescAllocInternal" in line
    )

    print("R24_HYBRID_RM_MITIGATION_ANALYSIS=BEGIN")
    print("analysis_semantics=rm_activity_volume_not_exact_resident_ownership")
    print(f"baseline.r22_largest_5s_residual_mib={BASELINE_R22_5S_MIB:.3f}")
    if best1 is not None:
        one_left, one_right, one_gain = best1
        print(
            "candidate.largest_1s="
            f"start_monotonic={int(one_left['mono_ns']) / 1e9:.9f} "
            f"end_monotonic={int(one_right['mono_ns']) / 1e9:.9f} "
            f"delta_mib={one_gain:+.3f}"
        )
    print(
        "candidate.largest_5s="
        f"start_monotonic={burst_start_ns / 1e9:.9f} "
        f"end_monotonic={burst_end_ns / 1e9:.9f} "
        f"delta_mib={burst_mib:+.3f}"
    )
    print(f"candidate_to_r22_burst_pct={ratio_pct:.6f}")
    print(f"candidate_burst_reduction_pct={reduction_pct:+.6f}")
    print(f"burst_band={band}")
    print(f"trace_covers_burst5={trace_covers_burst}")
    print(f"trace_window_start_monotonic={trace_start_ns / 1e9:.9f}")
    print(f"trace_window_end_monotonic={trace_end_ns / 1e9:.9f}")

    if left_normal is not None and right_normal is not None:
        print(f"burst5.node0_normal_free_delta_mib={right_normal - left_normal:+.3f}")
    if left_free is not None and right_free is not None:
        print(
            "burst5.nr_free_pages_delta_mib="
            f"{(right_free - left_free) * page_size / 1048576:+.3f}"
        )

    for edge, sample in (("start", start_slow), ("end", end_slow)):
        if sample is None:
            continue
        sections = sample["sections"]
        page_lines = sections.get("/proc/pagetypeinfo", [])  # type: ignore[union-attr]
        unmovable = pagetype_high_mib(page_lines, page_size, "Unmovable")
        movable = pagetype_high_mib(page_lines, page_size, "Movable")
        if unmovable is not None:
            print(f"burst5.{edge}.normal_unmovable_order4plus_mib={unmovable:.3f}")
        if movable is not None:
            print(f"burst5.{edge}.normal_movable_order4plus_mib={movable:.3f}")

    print(f"event_count.nv_alloc_pages={len(page_calls)}")
    print(f"event_count.nv_alloc_system_pages={len(system_calls)}")
    print(f"nv_alloc_pages.order4_calls.total={len(order4)}")
    print(f"nv_alloc_pages.order4_activity_mib.total={order4_total / 1048576:.3f}")
    print(f"nv_alloc_pages.order0_activity_mib.total={order0_total / 1048576:.3f}")
    print(f"nv_alloc_pages.order4_calls.burst5={len(burst_order4)}")
    print(f"nv_alloc_pages.order4_activity_mib.burst5={burst_order4_bytes / 1048576:.3f}")
    print("nv_alloc_pages.logical_bytes_semantics=activity_volume_not_resident_ownership")
    print(f"boundary.nv_alloc_pages.unmatched_entries={unmatched_entries['nv_alloc_pages']}")
    print(f"boundary.nv_alloc_pages.unmatched_returns={unmatched_returns['nv_alloc_pages']}")
    print(f"boundary.nv_alloc_system_pages.unmatched_entries={unmatched_entries['nv_alloc_system_pages']}")
    print(f"boundary.nv_alloc_system_pages.unmatched_returns={unmatched_returns['nv_alloc_system_pages']}")
    print(f"strict_rm_oom_count={rm_oom_count}")
    print(f"mitigation_discriminator={mitigation_discriminator(band, rm_oom_count)}")
    print("R24_HYBRID_RM_MITIGATION_ANALYSIS=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
