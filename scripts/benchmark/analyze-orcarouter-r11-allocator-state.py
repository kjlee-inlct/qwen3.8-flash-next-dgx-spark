#!/usr/bin/env python3
"""Correlate R11 Linux allocator-state samples with the traced RM OOM.

The analyzer is read-only. It aligns the R10b RM monotonic timestamp with the
R11 fast/slow samples and RM-triggered full snapshot, then summarizes buddy
order-4 capacity, migratetype order-4 capacity, pageblock distribution, memory
headroom, VM allocator counters, and PSI around the failure.
"""

from __future__ import annotations

import argparse
import dataclasses
import pathlib
import re
from typing import Iterable

PAGE_SIZE = 4096
SAMPLE_RE = re.compile(
    r"^===== sample seq=(\d+) wall=(.*?) monotonic_ns=(\d+) =====$"
)
SECTION_RE = re.compile(r"^--- (.+) ---$")
BUDDY_RE = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+)\s+(.+)$")
PAGETYPE_RE = re.compile(
    r"^Node\s+(\d+),\s+zone\s+(\S+),\s+type\s+(\S+)\s+(.+)$"
)
PAGEBLOCK_RE = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+)\s+(.+)$")
RM_RE = re.compile(r"^rm_monotonic=([0-9.]+)$", re.MULTILINE)
META_MONO_RE = re.compile(r"^monotonic_ns=(\d+)$", re.MULTILINE)


@dataclasses.dataclass(frozen=True)
class Sample:
    seq: int
    wall: str
    monotonic_ns: int
    sections: dict[str, str]


def parse_samples(path: pathlib.Path) -> list[Sample]:
    samples: list[Sample] = []
    seq: int | None = None
    wall = ""
    mono = 0
    sections: dict[str, list[str]] = {}
    current: str | None = None

    def flush() -> None:
        nonlocal seq, wall, mono, sections, current
        if seq is None:
            return
        samples.append(
            Sample(
                seq=seq,
                wall=wall,
                monotonic_ns=mono,
                sections={key: "".join(value) for key, value in sections.items()},
            )
        )
        seq = None
        wall = ""
        mono = 0
        sections = {}
        current = None

    with path.open(encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.rstrip("\n")
            match = SAMPLE_RE.match(line)
            if match:
                flush()
                seq = int(match.group(1))
                wall = match.group(2)
                mono = int(match.group(3))
                continue
            section = SECTION_RE.match(line)
            if section and seq is not None:
                current = section.group(1)
                sections.setdefault(current, [])
                continue
            if seq is not None and current is not None:
                sections[current].append(raw)
    flush()
    return samples


def nearest(samples: list[Sample], target_ns: int) -> tuple[Sample | None, Sample | None]:
    before = None
    after = None
    for sample in samples:
        if sample.monotonic_ns <= target_ns:
            before = sample
        elif after is None:
            after = sample
            break
    return before, after


def parse_buddy(text: str) -> dict[tuple[int, str], list[int]]:
    result: dict[tuple[int, str], list[int]] = {}
    for raw in text.splitlines():
        match = BUDDY_RE.match(raw.strip())
        if not match:
            continue
        values = [int(value) for value in match.group(3).split() if value.isdigit()]
        result[(int(match.group(1)), match.group(2))] = values
    return result


def buddy_metrics(values: list[int]) -> tuple[int, float, int]:
    order4 = values[4] if len(values) > 4 else 0
    ge4_pages = sum(count * (1 << order) for order, count in enumerate(values) if order >= 4)
    higher_blocks = sum(values[5:]) if len(values) > 5 else 0
    mib = ge4_pages * PAGE_SIZE / (1024 * 1024)
    return order4, mib, higher_blocks


def parse_pagetype(
    text: str,
) -> tuple[dict[tuple[int, str, str], list[int]], dict[tuple[int, str], dict[str, int]]]:
    order_counts: dict[tuple[int, str, str], list[int]] = {}
    pageblocks: dict[tuple[int, str], dict[str, int]] = {}
    block_types: list[str] = []
    in_blocks = False

    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("Number of blocks type"):
            block_types = line.split()[4:]
            in_blocks = True
            continue

        match = PAGETYPE_RE.match(line)
        if match:
            values = []
            for token in match.group(4).split():
                if token == ">100000":
                    values.append(100001)
                else:
                    try:
                        values.append(int(token))
                    except ValueError:
                        pass
            order_counts[(int(match.group(1)), match.group(2), match.group(3))] = values
            continue

        if in_blocks:
            block = PAGEBLOCK_RE.match(line)
            if block:
                values = []
                for token in block.group(3).split():
                    try:
                        values.append(int(token))
                    except ValueError:
                        pass
                if block_types and len(values) >= len(block_types):
                    pageblocks[(int(block.group(1)), block.group(2))] = dict(
                        zip(block_types, values[: len(block_types)], strict=False)
                    )
    return order_counts, pageblocks


def parse_kv(text: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for raw in text.splitlines():
        parts = raw.split()
        if len(parts) < 2:
            continue
        key = parts[0].rstrip(":")
        try:
            result[key] = int(parts[1])
        except ValueError:
            continue
    return result


def parse_psi(text: str) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = {}
    for raw in text.splitlines():
        parts = raw.split()
        if not parts:
            continue
        values: dict[str, float] = {}
        for token in parts[1:]:
            if "=" not in token:
                continue
            key, value = token.split("=", 1)
            try:
                values[key] = float(value)
            except ValueError:
                pass
        result[parts[0]] = values
    return result


def ms_delta(sample: Sample | None, target_ns: int) -> str:
    if sample is None:
        return "NA"
    return f"{(sample.monotonic_ns - target_ns) / 1_000_000:+.3f}"


def emit_buddy(label: str, sample: Sample | None) -> None:
    if sample is None:
        print(f"{label}=MISSING")
        return
    buddy = parse_buddy(sample.sections.get("/proc/buddyinfo", ""))
    if not buddy:
        print(f"{label}=NO_BUDDYINFO")
        return
    for (node, zone), values in sorted(buddy.items()):
        order4, ge4_mib, higher = buddy_metrics(values)
        print(
            f"{label} node={node} zone={zone} order4_blocks={order4} "
            f"order5plus_blocks={higher} ge4_free_mib={ge4_mib:.3f}"
        )


def emit_mem(label: str, sample: Sample | None) -> None:
    if sample is None:
        return
    mem = parse_kv(sample.sections.get("/proc/meminfo", ""))
    wanted = ("MemFree", "MemAvailable", "SwapFree", "CmaFree")
    values = " ".join(f"{key}_kib={mem[key]}" for key in wanted if key in mem)
    if values:
        print(f"{label} {values}")


def emit_vm_delta(before: Sample | None, after: Sample | None) -> None:
    if before is None or after is None:
        return
    left = parse_kv(before.sections.get("/proc/vmstat", ""))
    right = parse_kv(after.sections.get("/proc/vmstat", ""))
    prefixes = (
        "compact_",
        "pgscan_direct",
        "pgsteal_direct",
        "allocstall",
        "pgalloc_",
    )
    for key in sorted(set(left) & set(right)):
        if key.startswith(prefixes):
            delta = right[key] - left[key]
            if delta:
                print(f"vmstat_delta key={key} delta={delta}")


def emit_psi(label: str, sample: Sample | None) -> None:
    if sample is None:
        return
    psi = parse_psi(sample.sections.get("/proc/pressure/memory", ""))
    for kind in ("some", "full"):
        if kind not in psi:
            continue
        values = psi[kind]
        fields = " ".join(
            f"{key}={values[key]:.3f}" for key in ("avg10", "avg60", "avg300", "total") if key in values
        )
        print(f"{label} kind={kind} {fields}")


def read_event_snapshot(event_dir: pathlib.Path) -> tuple[int | None, str, str]:
    meta = (event_dir / "meta.txt").read_text(encoding="utf-8", errors="replace")
    match = META_MONO_RE.search(meta)
    mono = int(match.group(1)) if match else None
    buddy = (event_dir / "proc-buddyinfo.txt").read_text(encoding="utf-8", errors="replace")
    pagetype = (event_dir / "proc-pagetypeinfo.txt").read_text(
        encoding="utf-8", errors="replace"
    )
    return mono, buddy, pagetype


def emit_event(event_dir: pathlib.Path, rm_ns: int) -> None:
    mono, buddy_text, pagetype_text = read_event_snapshot(event_dir)
    if mono is not None:
        print(f"event_snapshot_delay_ms={(mono - rm_ns) / 1_000_000:+.3f}")
    for (node, zone), values in sorted(parse_buddy(buddy_text).items()):
        order4, ge4_mib, higher = buddy_metrics(values)
        print(
            f"event_buddy node={node} zone={zone} order4_blocks={order4} "
            f"order5plus_blocks={higher} ge4_free_mib={ge4_mib:.3f}"
        )

    order_counts, pageblocks = parse_pagetype(pagetype_text)
    for (node, zone, migratetype), values in sorted(order_counts.items()):
        order4 = values[4] if len(values) > 4 else 0
        ge4 = sum(values[4:]) if len(values) > 4 else 0
        print(
            f"event_pagetype node={node} zone={zone} type={migratetype} "
            f"order4_blocks={order4} order4plus_blocks={ge4}"
        )
    for (node, zone), values in sorted(pageblocks.items()):
        fields = " ".join(f"{key}={value}" for key, value in values.items())
        print(f"event_pageblocks node={node} zone={zone} {fields}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", required=True)
    args = parser.parse_args()

    root = pathlib.Path(args.evidence)
    state = root / "allocator-state"
    rmsys = root / "r10b" / "rmsys-analysis.txt"
    fast_path = state / "fast-state.txt"
    slow_path = state / "slow-state.txt"
    for path in (rmsys, fast_path, slow_path):
        if not path.is_file():
            raise SystemExit(f"missing R11 evidence file: {path}")

    analysis = rmsys.read_text(encoding="utf-8", errors="replace")
    match = RM_RE.search(analysis)
    if not match:
        raise SystemExit("R11 evidence has no rm_monotonic marker")
    rm_s = float(match.group(1))
    rm_ns = int(round(rm_s * 1_000_000_000))

    fast = parse_samples(fast_path)
    slow = parse_samples(slow_path)
    fast_before, fast_after = nearest(fast, rm_ns)
    slow_before, slow_after = nearest(slow, rm_ns)

    events = sorted((state / "events").glob("rm-oom-*"))
    print("R11_ALLOCATOR_STATE_ANALYSIS=RM_OOM_CORRELATED")
    print(f"rm_monotonic_s={rm_s:.6f}")
    print(f"fast_samples={len(fast)} slow_samples={len(slow)} rm_event_snapshots={len(events)}")
    if fast_before:
        print(f"fast_before_seq={fast_before.seq} delta_ms={ms_delta(fast_before, rm_ns)}")
    if fast_after:
        print(f"fast_after_seq={fast_after.seq} delta_ms={ms_delta(fast_after, rm_ns)}")
    if slow_before:
        print(f"slow_before_seq={slow_before.seq} delta_ms={ms_delta(slow_before, rm_ns)}")
    if slow_after:
        print(f"slow_after_seq={slow_after.seq} delta_ms={ms_delta(slow_after, rm_ns)}")

    emit_buddy("buddy_before", fast_before)
    emit_buddy("buddy_after", fast_after)
    emit_mem("mem_before", fast_before)
    emit_mem("mem_after", fast_after)
    emit_psi("psi_before", fast_before)
    emit_psi("psi_after", fast_after)
    emit_vm_delta(fast_before, fast_after)

    if events:
        emit_event(events[0], rm_ns)
    else:
        print("event_snapshot=MISSING")

    if slow_before is not None:
        counts, blocks = parse_pagetype(slow_before.sections.get("/proc/pagetypeinfo", ""))
        for (node, zone, migratetype), values in sorted(counts.items()):
            order4 = values[4] if len(values) > 4 else 0
            ge4 = sum(values[4:]) if len(values) > 4 else 0
            print(
                f"slow_before_pagetype node={node} zone={zone} type={migratetype} "
                f"order4_blocks={order4} order4plus_blocks={ge4}"
            )
        for (node, zone), values in sorted(blocks.items()):
            fields = " ".join(f"{key}={value}" for key, value in values.items())
            print(f"slow_before_pageblocks node={node} zone={zone} {fields}")

    if slow_after is not None:
        counts, blocks = parse_pagetype(slow_after.sections.get("/proc/pagetypeinfo", ""))
        for (node, zone, migratetype), values in sorted(counts.items()):
            order4 = values[4] if len(values) > 4 else 0
            ge4 = sum(values[4:]) if len(values) > 4 else 0
            print(
                f"slow_after_pagetype node={node} zone={zone} type={migratetype} "
                f"order4_blocks={order4} order4plus_blocks={ge4}"
            )
        for (node, zone), values in sorted(blocks.items()):
            fields = " ".join(f"{key}={value}" for key, value in values.items())
            print(f"slow_after_pageblocks node={node} zone={zone} {fields}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
