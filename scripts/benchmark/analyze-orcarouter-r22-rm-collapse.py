#!/usr/bin/env python3
"""Locate allocator-reservoir collapse points before the R22 RM OOM event."""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re

PAGE_SIZE = 4096
SAMPLE_RE = re.compile(r"^===== sample seq=(\d+) wall=(\S+) monotonic_ns=(\d+) =====$")
BUDDY_RE = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+)\s+(.+)$")
PAGETYPE_RE = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+),\s+type\s+(\S+)\s+(.+)$")


def iso(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))


def parse_counts(payload: str) -> list[int]:
    values: list[int] = []
    for token in payload.split():
        if token == ">100000":
            values.append(100001)
            continue
        try:
            values.append(int(token))
        except ValueError:
            pass
    return values


def ge_mib(values: list[int], minimum: int) -> float:
    pages = sum(count * (1 << order) for order, count in enumerate(values) if order >= minimum)
    return pages * PAGE_SIZE / (1024 * 1024)


def parse_sections(path: pathlib.Path) -> list[tuple[int, dt.datetime, str]]:
    if not path.is_file():
        raise SystemExit(f"missing sample file: {path}")
    result: list[tuple[int, dt.datetime, str]] = []
    current_ns: int | None = None
    current_wall: dt.datetime | None = None
    body: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = SAMPLE_RE.match(raw)
        if match:
            if current_ns is not None and current_wall is not None:
                result.append((current_ns, current_wall, "\n".join(body)))
            current_ns = int(match.group(3))
            current_wall = iso(match.group(2))
            body = []
        elif current_ns is not None:
            body.append(raw)
    if current_ns is not None and current_wall is not None:
        result.append((current_ns, current_wall, "\n".join(body)))
    if not result:
        raise SystemExit(f"no samples parsed from: {path}")
    return result


def parse_event(root: pathlib.Path) -> tuple[int, dt.datetime]:
    dirs = sorted(p for p in (root / "allocator-state/events").glob("rm-oom-*") if p.is_dir())
    if len(dirs) != 1:
        raise SystemExit(f"expected exactly one RM event directory, found {len(dirs)}")
    fields: dict[str, str] = {}
    for raw in (dirs[0] / "meta.txt").read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in raw:
            key, value = raw.split("=", 1)
            fields[key] = value
    return int(fields["monotonic_ns"]), iso(fields["wall"])


def parse_fast_o4plus(body: str) -> float:
    section = ""
    for raw in body.splitlines():
        if raw.startswith("--- ") and raw.endswith(" ---"):
            section = raw[4:-4]
            continue
        if section == "/proc/buddyinfo":
            match = BUDDY_RE.match(raw.strip())
            if match and int(match.group(1)) == 0 and match.group(2) == "Normal":
                return ge_mib(parse_counts(match.group(3)), 4)
    raise SystemExit("Normal buddyinfo missing from fast sample")


def parse_slow_types(body: str) -> tuple[float, float]:
    section = ""
    unmovable: list[int] = []
    movable: list[int] = []
    for raw in body.splitlines():
        if raw.startswith("--- ") and raw.endswith(" ---"):
            section = raw[4:-4]
            continue
        if section != "/proc/pagetypeinfo":
            continue
        match = PAGETYPE_RE.match(raw.strip())
        if not match or int(match.group(1)) != 0 or match.group(2) != "Normal":
            continue
        if match.group(3) == "Unmovable":
            unmovable = parse_counts(match.group(4))
        elif match.group(3) == "Movable":
            movable = parse_counts(match.group(4))
    return ge_mib(unmovable, 4), ge_mib(movable, 4)


def read_time(path: pathlib.Path) -> dt.datetime:
    if not path.is_file():
        raise SystemExit(f"missing timestamp file: {path}")
    return iso(path.read_text(encoding="utf-8", errors="replace"))


def offset_s(when: dt.datetime, event: dt.datetime) -> float:
    return (when - event).total_seconds()


def emit_crossings(
    label: str,
    samples: list[tuple[dt.datetime, float]],
    event_wall: dt.datetime,
    thresholds: list[float],
) -> None:
    for threshold in thresholds:
        found = next(((wall, value) for wall, value in samples if value <= threshold), None)
        if found is None:
            print(f"r22_crossing={label} threshold_mib={threshold:.3f} found=0")
        else:
            wall, value = found
            print(
                f"r22_crossing={label} threshold_mib={threshold:.3f} found=1 "
                f"offset_s={offset_s(wall, event_wall):+.3f} wall={wall.isoformat()} value_mib={value:.3f}"
            )


def largest_drop(label: str, samples: list[tuple[dt.datetime, float]], event_wall: dt.datetime) -> None:
    if len(samples) < 2:
        return
    pairs = list(zip(samples, samples[1:]))
    before_after = max(pairs, key=lambda pair: pair[0][1] - pair[1][1])
    (left_wall, left_value), (right_wall, right_value) = before_after
    print(
        f"r22_largest_drop={label} "
        f"start_offset_s={offset_s(left_wall, event_wall):+.3f} "
        f"end_offset_s={offset_s(right_wall, event_wall):+.3f} "
        f"start_mib={left_value:.3f} end_mib={right_value:.3f} "
        f"delta_mib={right_value-left_value:+.3f} duration_s={(right_wall-left_wall).total_seconds():.3f}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r22", required=True, help="R22 evidence root")
    args = parser.parse_args()
    root = pathlib.Path(args.r22)
    state = root / "allocator-state"
    event_ns, event_wall = parse_event(root)
    compact_done = read_time(root / "compact-complete-iso.txt")

    fast_raw = parse_sections(state / "fast-state.txt")
    slow_raw = parse_sections(state / "slow-state.txt")
    fast = [(wall, parse_fast_o4plus(body)) for _, wall, body in fast_raw if compact_done <= wall <= event_wall]
    slow_types = [(wall, *parse_slow_types(body)) for _, wall, body in slow_raw if compact_done <= wall <= event_wall]
    if not fast or not slow_types:
        raise SystemExit("no post-compaction pre-event samples found")

    unmovable = [(wall, u) for wall, u, _ in slow_types]
    movable = [(wall, m) for wall, _, m in slow_types]
    initial_u = unmovable[0][1]
    initial_total = fast[0][1]

    print("ORCA_R22_RM_COLLAPSE=BEGIN")
    print(
        f"r22_collapse_window compact_wall={compact_done.isoformat()} event_wall={event_wall.isoformat()} "
        f"event_monotonic_ns={event_ns} duration_s={(event_wall-compact_done).total_seconds():.3f}"
    )
    print(
        f"r22_collapse_initial unmovable_o4plus_mib={initial_u:.3f} "
        f"normal_o4plus_mib={initial_total:.3f}"
    )
    emit_crossings(
        "UNMOVABLE_O4PLUS",
        unmovable,
        event_wall,
        [initial_u * 0.5, initial_u * 0.1, initial_u * 0.01, 1024.0, 100.0, 10.0],
    )
    emit_crossings(
        "NORMAL_O4PLUS",
        fast,
        event_wall,
        [initial_total * 0.5, initial_total * 0.1, initial_total * 0.01, 1024.0, 100.0, 10.0],
    )
    largest_drop("UNMOVABLE_O4PLUS", unmovable, event_wall)
    largest_drop("MOVABLE_O4PLUS", movable, event_wall)
    largest_drop("NORMAL_O4PLUS", fast, event_wall)
    print("ORCA_R22_RM_COLLAPSE=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
