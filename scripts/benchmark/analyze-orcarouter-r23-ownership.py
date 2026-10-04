#!/usr/bin/env python3
"""Read-only analyzer for R23 early-burst RM/UVM ownership evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re
from collections import Counter, defaultdict

EVENT_MAP = {
    "nv_alloc_pages_entry": ("nv_alloc_pages", "entry"),
    "nv_alloc_pages_ret": ("nv_alloc_pages", "ret"),
    "nv_alloc_system_pages_entry": ("nv_alloc_system_pages", "entry"),
    "nv_alloc_system_pages_ret": ("nv_alloc_system_pages", "ret"),
    "pma_alloc_entry": ("nvUvmInterfacePmaAllocPages", "entry"),
    "pma_alloc_ret": ("nvUvmInterfacePmaAllocPages", "ret"),
    "uvm_dma_alloc_entry": ("uvm_gpu_dma_alloc", "entry"),
    "uvm_dma_alloc_ret": ("uvm_gpu_dma_alloc", "ret"),
    "uvm_mem_alloc_entry": ("uvm_mem_alloc", "entry"),
    "uvm_mem_alloc_ret": ("uvm_mem_alloc", "ret"),
    "uvm_pmm_alloc_entry": ("uvm_pmm_gpu_alloc_kernel", "entry"),
    "uvm_pmm_alloc_ret": ("uvm_pmm_gpu_alloc_kernel", "ret"),
}
TRACE_RE = re.compile(r"\s(\d+\.\d+):\s+([A-Za-z0-9_]+):\s*(.*)$")
TASK_RE = re.compile(r"(.+?)-(\d+)(?:\s+\(\s*\d+\))?\s+\[")
FIELD_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)=(0x[0-9A-Fa-f]+|-?\d+)\b")
SAMPLE_RE = re.compile(r"^===== sample seq=\d+ wall=(\S+) monotonic_ns=(\d+) =====$")
BUDDY_RE = re.compile(r"^Node\s+0,\s+zone\s+Normal\s+(.+)$")
PAGETYPE_RE = re.compile(r"^Node\s+0,\s+zone\s+Normal,\s+type\s+(\S+)\s+(.+)$")
LOG_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\S+)\s+(.*)$")


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        raise SystemExit(f"missing evidence file: {path}")
    return path.read_text(encoding="utf-8", errors="replace")


def number(raw: str) -> int:
    return int(raw, 16 if raw.lower().startswith("0x") else 10)


def iso(raw: str) -> dt.datetime:
    return dt.datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))


def parse_meminfo(lines: list[str]) -> dict[str, float]:
    out: dict[str, float] = {}
    for line in lines:
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        try:
            out[key] = float(rest.split()[0]) / 1024.0
        except (ValueError, IndexError):
            pass
    return out


def residual(base: dict[str, float], now: dict[str, float]) -> float:
    def d(key: str) -> float:
        return now.get(key, 0.0) - base.get(key, 0.0)

    explained = (
        d("Active(anon)")
        + d("Inactive(anon)")
        + d("Active(file)")
        + d("Inactive(file)")
        + d("Unevictable")
        + d("Slab")
        + d("KReclaimable")
        - d("SReclaimable")
        + d("PageTables")
        + d("SecPageTables")
        + d("KernelStack")
    )
    return -d("MemFree") - explained


def parse_samples(path: pathlib.Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    section = ""
    for line in read(path).splitlines():
        match = SAMPLE_RE.match(line)
        if match:
            if current is not None:
                rows.append(current)
            current = {
                "wall": iso(match.group(1)),
                "mono_ns": int(match.group(2)),
                "sections": {},
            }
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
    for i, (left, left_value) in enumerate(points):
        for right, right_value in points[i + 1 :]:
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


def nearest_sample(samples: list[dict[str, object]], target_ns: int) -> dict[str, object]:
    return min(samples, key=lambda sample: abs(int(sample["mono_ns"]) - target_ns))


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
        parts = line.split()
        if len(parts) == 2 and parts[0] == key:
            return int(parts[1])
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=pathlib.Path)
    root = parser.parse_args().evidence
    page_size = int(read(root / "host-page-size.txt").strip())
    request_ns = int(read(root / "replacement-request-monotonic-ns.txt").strip())
    trace_start_ns = int(read(root / "trace-window-start-monotonic-ns.txt").strip())
    trace_end_ns = int(read(root / "trace-window-end-monotonic-ns.txt").strip())
    trace_start_wall = iso(read(root / "trace-window-start-iso.txt"))
    container_started_wall = iso(read(root / "container-started-after.txt"))

    entries: dict[tuple[str, int], list[tuple[float, dict[str, int], str]]] = defaultdict(list)
    counts: Counter[str] = Counter()
    tasks: dict[str, Counter[tuple[str, int]]] = defaultdict(Counter)
    returns: dict[str, Counter[int]] = defaultdict(Counter)
    unmatched_ret: Counter[str] = Counter()
    matched_pages: list[tuple[dict[str, int], int | None]] = []
    first_ts: dict[str, float] = {}
    last_ts: dict[str, float] = {}

    for line in read(root / "ownership-trace.txt").splitlines():
        match = TRACE_RE.search(line)
        if not match or match.group(2) not in EVENT_MAP:
            continue
        ts, event, raw_fields = float(match.group(1)), match.group(2), match.group(3)
        base, kind = EVENT_MAP[event]
        prefix = line[: match.start()]
        task = TASK_RE.search(prefix)
        comm = task.group(1).strip() if task else "UNKNOWN"
        pid = int(task.group(2)) if task else -1
        fields = {key: number(value) for key, value in FIELD_RE.findall(raw_fields)}
        counts[event] += 1
        tasks[base][(comm, pid)] += 1
        first_ts[base] = min(first_ts.get(base, ts), ts)
        last_ts[base] = max(last_ts.get(base, ts), ts)
        key = (base, pid)
        if kind == "entry":
            entries[key].append((ts, fields, comm))
        else:
            value = fields.get("ret", fields.get("raw_ret"))
            if value is not None:
                returns[base][value] += 1
            if entries[key]:
                _, entry_fields, _ = entries[key].pop()
                if base == "nv_alloc_pages":
                    matched_pages.append((entry_fields, value))
            else:
                unmatched_ret[base] += 1

    unmatched_entry: Counter[str] = Counter()
    for (base, _pid), pending in entries.items():
        unmatched_entry[base] += len(pending)

    print("R23_OWNERSHIP_ANALYSIS=BEGIN")
    print(f"trace_window_start_monotonic={trace_start_ns / 1e9:.9f}")
    print(f"trace_window_end_monotonic={trace_end_ns / 1e9:.9f}")
    print(f"trace_window_duration_s={(trace_end_ns - trace_start_ns) / 1e9:.6f}")
    print(
        "trace_window_start_from_replacement_request_s="
        f"{(trace_start_ns - request_ns) / 1e9:.6f}"
    )
    print(
        "trace_window_start_from_container_started_s="
        f"{(trace_start_wall - container_started_wall).total_seconds():.6f}"
    )
    print(f"trace_text_bytes={(root / 'ownership-trace.txt').stat().st_size}")
    for event in EVENT_MAP:
        print(f"event_count.{event}={counts[event]}")

    bases = sorted({base for base, _kind in EVENT_MAP.values()})
    for base in bases:
        histogram = (
            ",".join(
                f"0x{value:x}:{count}" for value, count in sorted(returns[base].items())
            )
            or "NONE"
        )
        print(
            f"boundary.{base}.first_monotonic="
            f"{first_ts[base] if base in first_ts else 'NONE'}"
        )
        print(
            f"boundary.{base}.last_monotonic="
            f"{last_ts[base] if base in last_ts else 'NONE'}"
        )
        print(f"boundary.{base}.return_histogram={histogram}")
        print(f"boundary.{base}.unmatched_entries={unmatched_entry[base]}")
        print(f"boundary.{base}.unmatched_returns={unmatched_ret[base]}")
        print(f"boundary.{base}.window_boundary_capable=1")
        for (comm, pid), count in tasks[base].most_common(12):
            print(f"task.{base}=comm={comm!r} pid={pid} events={count}")

    shapes: Counter[tuple[int, int, int, int, str]] = Counter()
    total = order0 = order4 = 0
    for fields, status in matched_pages:
        if "page_count" not in fields or "page_size" not in fields:
            continue
        logical = fields["page_count"] * page_size
        total += logical
        if fields["page_size"] == 4096:
            order0 += logical
        if fields["page_size"] == 65536:
            order4 += logical
        shapes[
            (
                fields["page_count"],
                fields["page_size"],
                fields.get("contiguous", -1),
                fields.get("node_id", -999),
                f"0x{status:x}" if status is not None else "NONE",
            )
        ] += 1
    for key, calls in shapes.most_common():
        print(
            "nv_alloc_pages_shape="
            f"page_count={key[0]} page_size={key[1]} contiguous={key[2]} "
            f"node_id={key[3]} return={key[4]} calls={calls}"
        )
    print(f"nv_alloc_pages.logical_requested_bytes={total}")
    print(f"nv_alloc_pages.order0_logical_requested_bytes={order0}")
    print(f"nv_alloc_pages.order4_logical_requested_bytes={order4}")
    print("nv_alloc_pages.logical_bytes_semantics=activity_volume_not_resident_ownership")

    uvm_bases = (
        "nvUvmInterfacePmaAllocPages",
        "uvm_gpu_dma_alloc",
        "uvm_mem_alloc",
        "uvm_pmm_gpu_alloc_kernel",
    )
    for base in uvm_bases:
        print(f"uvm_discriminator.{base}.present={1 if tasks[base] else 0}")

    base_mem = parse_meminfo(
        read(root / "poststop-after-compact" / "proc-meminfo.txt").splitlines()
    )
    samples = parse_samples(root / "allocator-state" / "fast-state.txt")
    points = []
    for sample in samples:
        sections = sample["sections"]
        mem = parse_meminfo(sections.get("/proc/meminfo", []))  # type: ignore[union-attr]
        if (
            mem
            and trace_start_ns - 2_000_000_000
            <= int(sample["mono_ns"])
            <= trace_end_ns + 2_000_000_000
        ):
            points.append((sample, residual(base_mem, mem)))
    if not points:
        raise SystemExit("no allocator samples overlap trace window")

    best5 = None
    for label, seconds in (("1s", 1.0), ("5s", 5.0)):
        best = largest(points, seconds)
        if best is None:
            print(f"residual_largest_{label}.found=0")
            continue
        left, right, gain = best
        print(
            f"residual_largest_{label}.found=1 "
            f"start_monotonic={int(left['mono_ns']) / 1e9:.9f} "
            f"end_monotonic={int(right['mono_ns']) / 1e9:.9f} "
            f"delta_mib={gain:+.3f}"
        )
        if label == "5s":
            best5 = best

    if best5 is not None:
        left, right, gain = best5
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
        print(f"burst5.residual_delta_mib={gain:+.3f}")
        if left_normal is not None and right_normal is not None:
            print(f"burst5.node0_normal_free_delta_mib={right_normal - left_normal:+.3f}")
        if left_free is not None and right_free is not None:
            print(
                "burst5.nr_free_pages_delta_mib="
                f"{(right_free - left_free) * page_size / 1048576:+.3f}"
            )

        slow_samples = parse_samples(root / "allocator-state" / "slow-state.txt")
        if slow_samples:
            for edge, sample in (("start", left), ("end", right)):
                nearest = nearest_sample(slow_samples, int(sample["mono_ns"]))
                sections = nearest["sections"]
                page_lines = sections.get("/proc/pagetypeinfo", [])  # type: ignore[union-attr]
                unmovable = pagetype_high_mib(page_lines, page_size, "Unmovable")
                movable = pagetype_high_mib(page_lines, page_size, "Movable")
                if unmovable is not None:
                    print(
                        f"burst5.{edge}.normal_unmovable_order4plus_mib="
                        f"{unmovable:.3f}"
                    )
                if movable is not None:
                    print(
                        f"burst5.{edge}.normal_movable_order4plus_mib="
                        f"{movable:.3f}"
                    )

        milestones = []
        log_path = root / "container-window.txt"
        if log_path.is_file():
            for line in log_path.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines():
                if not re.search(
                    r"load|weight|safetensor|ple|model", line, re.IGNORECASE
                ):
                    continue
                match = LOG_RE.match(line)
                if match:
                    try:
                        milestones.append((iso(match.group(1)), match.group(2)))
                    except ValueError:
                        pass
        for edge, sample in (("start", left), ("end", right)):
            if not milestones:
                print(f"milestone_nearest_{edge}=NONE")
                continue
            wall = sample["wall"]
            near = min(
                milestones,
                key=lambda row: abs((row[0] - wall).total_seconds()),
            )
            text = re.sub(r"\s+", " ", near[1]).strip()[:220]
            print(
                f"milestone_nearest_{edge}="
                f"delta_s={(near[0] - wall).total_seconds():+.3f} "
                f"wall={near[0].isoformat()} text={text!r}"
            )

    kernel_path = root / "kernel-errors.txt"
    kernel = (
        kernel_path.read_text(encoding="utf-8", errors="replace")
        if kernel_path.is_file()
        else ""
    )
    rm_count = sum(
        1
        for line in kernel.splitlines()
        if "NV_ERR_NO_MEMORY" in line or "_memdescAllocInternal" in line
    )
    snapshots = sum(
        1
        for path in (root / "allocator-state" / "events").glob("rm-oom-*")
        if path.is_dir()
    )
    print(f"strict_rm_oom_count={rm_count}")
    print(f"rm_event_snapshot_count={snapshots}")

    rm_active = bool(tasks["nv_alloc_pages"] or tasks["nv_alloc_system_pages"])
    uvm_active = any(tasks[base] for base in uvm_bases)
    if rm_active and not uvm_active:
        result = "RM_SYSMEM_ACTIVE_SELECTED_UVM_SILENT"
    elif rm_active and uvm_active:
        result = "RM_AND_SELECTED_UVM_ACTIVE"
    elif uvm_active:
        result = "SELECTED_UVM_ACTIVE_RM_SYSMEM_SILENT"
    else:
        result = "SELECTED_BOUNDARIES_SILENT"
    print(f"ownership_discriminator={result}")
    print("R23_OWNERSHIP_ANALYSIS=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
