#!/usr/bin/env python3
"""Summarize allocator trajectory leading into the R21 RM OOM event."""

from __future__ import annotations

import argparse
import pathlib
import re

PAGE_SIZE = 4096
SAMPLE_RE = re.compile(r"^===== sample seq=(\d+) wall=(\S+) monotonic_ns=(\d+) =====$")
BUDDY_RE = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+)\s+(.+)$")
PAGETYPE_RE = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+),\s+type\s+(\S+)\s+(.+)$")
TARGET_OFFSETS_S = (-60, -30, -10, -5, -1, 0)


def parse_counts(payload: str) -> list[int]:
    values: list[int] = []
    for token in payload.split():
        if token == ">100000":
            values.append(100001)
        else:
            try:
                values.append(int(token))
            except ValueError:
                pass
    return values


def ge_mib(values: list[int], minimum: int) -> float:
    pages = sum(count * (1 << order) for order, count in enumerate(values) if order >= minimum)
    return pages * PAGE_SIZE / (1024 * 1024)


def order_mib(values: list[int], order: int) -> float:
    if len(values) <= order:
        return 0.0
    return values[order] * (1 << order) * PAGE_SIZE / (1024 * 1024)


def parse_sections(path: pathlib.Path) -> list[tuple[int, str, str]]:
    if not path.is_file():
        raise SystemExit(f"missing sample file: {path}")
    result: list[tuple[int, str, str]] = []
    current_ns: int | None = None
    current_wall = ""
    body: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = SAMPLE_RE.match(raw)
        if match:
            if current_ns is not None:
                result.append((current_ns, current_wall, "\n".join(body)))
            current_wall = match.group(2)
            current_ns = int(match.group(3))
            body = []
        elif current_ns is not None:
            body.append(raw)
    if current_ns is not None:
        result.append((current_ns, current_wall, "\n".join(body)))
    if not result:
        raise SystemExit(f"no samples parsed from: {path}")
    return result


def parse_event_meta(events_root: pathlib.Path) -> tuple[pathlib.Path, int, str]:
    dirs = sorted(p for p in events_root.glob("rm-oom-*") if p.is_dir())
    if len(dirs) != 1:
        raise SystemExit(f"expected exactly one RM event directory, found {len(dirs)}")
    meta = dirs[0] / "meta.txt"
    values: dict[str, str] = {}
    for raw in meta.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in raw:
            key, value = raw.split("=", 1)
            values[key] = value
    try:
        event_ns = int(values["monotonic_ns"])
        wall = values["wall"]
    except (KeyError, ValueError) as exc:
        raise SystemExit(f"invalid event metadata: {meta}") from exc
    return dirs[0], event_ns, wall


def parse_fast(body: str) -> dict[str, float]:
    buddy: list[int] = []
    mem: dict[str, int] = {}
    section = ""
    for raw in body.splitlines():
        if raw.startswith("--- ") and raw.endswith(" ---"):
            section = raw[4:-4]
            continue
        if section == "/proc/buddyinfo":
            match = BUDDY_RE.match(raw.strip())
            if match and int(match.group(1)) == 0 and match.group(2) == "Normal":
                buddy = parse_counts(match.group(3))
        elif section == "/proc/meminfo" and ":" in raw:
            key, rest = raw.split(":", 1)
            parts = rest.split()
            if parts and parts[0].isdigit():
                mem[key] = int(parts[0])
    if not buddy:
        raise SystemExit("Normal-zone buddyinfo missing from fast sample")
    return {
        "memavailable": mem.get("MemAvailable", 0) / 1024,
        "memfree": mem.get("MemFree", 0) / 1024,
        "cached": mem.get("Cached", 0) / 1024,
        "inactive_file": mem.get("Inactive(file)", 0) / 1024,
        "swapfree": mem.get("SwapFree", 0) / 1024,
        "normal_o4": order_mib(buddy, 4),
        "normal_o5plus": ge_mib(buddy, 5),
        "normal_o4plus": ge_mib(buddy, 4),
    }


def parse_slow(body: str) -> dict[str, float]:
    unmovable: list[int] = []
    movable: list[int] = []
    section = ""
    for raw in body.splitlines():
        if raw.startswith("--- ") and raw.endswith(" ---"):
            section = raw[4:-4]
            continue
        if section != "/proc/pagetypeinfo":
            continue
        match = PAGETYPE_RE.match(raw.strip())
        if not match or int(match.group(1)) != 0 or match.group(2) != "Normal":
            continue
        values = parse_counts(match.group(4))
        if match.group(3) == "Unmovable":
            unmovable = values
        elif match.group(3) == "Movable":
            movable = values
    return {
        "unmovable_o4plus": ge_mib(unmovable, 4),
        "movable_o4plus": ge_mib(movable, 4),
    }


def nearest(samples: list[tuple[int, str, str]], target_ns: int) -> tuple[int, str, str]:
    return min(samples, key=lambda sample: abs(sample[0] - target_ns))


def emit(prefix: str, label: str, sample_ns: int, wall: str, event_ns: int, values: dict[str, float]) -> None:
    delta_s = (sample_ns - event_ns) / 1e9
    fields = " ".join(f"{key}_mib={value:.3f}" for key, value in values.items())
    print(f"{prefix}={label} sample_offset_s={delta_s:+.3f} wall={wall} {fields}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r21", required=True, help="R21 evidence root")
    args = parser.parse_args()
    root = pathlib.Path(args.r21)
    state = root / "allocator-state"
    event_dir, event_ns, event_wall = parse_event_meta(state / "events")
    fast = parse_sections(state / "fast-state.txt")
    slow = parse_sections(state / "slow-state.txt")

    print("ORCA_R21_RM_TRAJECTORY=BEGIN")
    print(f"r21_trajectory_event={event_dir.name} wall={event_wall} monotonic_ns={event_ns}")
    for offset_s in TARGET_OFFSETS_S:
        target_ns = event_ns + int(offset_s * 1e9)
        fast_sample = nearest(fast, target_ns)
        emit("r21_fast", f"T{offset_s:+d}", fast_sample[0], fast_sample[1], event_ns, parse_fast(fast_sample[2]))
        slow_sample = nearest(slow, target_ns)
        emit("r21_slow", f"T{offset_s:+d}", slow_sample[0], slow_sample[1], event_ns, parse_slow(slow_sample[2]))
    print("ORCA_R21_RM_TRAJECTORY=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
