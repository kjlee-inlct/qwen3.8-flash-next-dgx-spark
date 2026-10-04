#!/usr/bin/env python3
"""Locate when the R21/R22 core-unexplained physical-page loss develops.

This helper is read-only and operates only on preserved allocator snapshots.
The residual is deliberately approximate: it subtracts a non-overlapping core
set of Linux resident-memory categories from MemFree loss. It is not an exact
NVIDIA-owned-page measurement.
"""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re

SAMPLE_RE = re.compile(r"^===== sample seq=(\d+) wall=(\S+) monotonic_ns=(\d+) =====$")


def iso(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))


def parse_meminfo_text(text: str) -> dict[str, float]:
    result: dict[str, float] = {}
    for raw in text.splitlines():
        if ":" not in raw:
            continue
        key, rest = raw.split(":", 1)
        parts = rest.split()
        if not parts:
            continue
        try:
            result[key] = float(parts[0]) / 1024.0
        except ValueError:
            continue
    return result


def parse_meminfo_file(path: pathlib.Path) -> dict[str, float]:
    if not path.is_file():
        raise SystemExit(f"missing meminfo snapshot: {path}")
    return parse_meminfo_text(path.read_text(encoding="utf-8", errors="replace"))


def parse_fast_samples(path: pathlib.Path) -> list[tuple[dt.datetime, int, dict[str, float]]]:
    if not path.is_file():
        raise SystemExit(f"missing fast-state file: {path}")
    result: list[tuple[dt.datetime, int, dict[str, float]]] = []
    wall: dt.datetime | None = None
    mono_ns: int | None = None
    section = ""
    mem_lines: list[str] = []

    def flush() -> None:
        if wall is not None and mono_ns is not None and mem_lines:
            result.append((wall, mono_ns, parse_meminfo_text("\n".join(mem_lines))))

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        sample = SAMPLE_RE.match(raw)
        if sample:
            flush()
            wall = iso(sample.group(2))
            mono_ns = int(sample.group(3))
            section = ""
            mem_lines = []
            continue
        if wall is None:
            continue
        if raw.startswith("--- ") and raw.endswith(" ---"):
            section = raw[4:-4]
            continue
        if section == "/proc/meminfo":
            mem_lines.append(raw)
    flush()
    if not result:
        raise SystemExit(f"no meminfo samples parsed from: {path}")
    return result


def read_time(path: pathlib.Path) -> dt.datetime:
    if not path.is_file():
        raise SystemExit(f"missing timestamp file: {path}")
    return iso(path.read_text(encoding="utf-8", errors="replace"))


def event_dir(root: pathlib.Path) -> pathlib.Path:
    dirs = sorted(p for p in (root / "allocator-state" / "events").glob("rm-oom-*") if p.is_dir())
    if len(dirs) != 1:
        raise SystemExit(f"expected exactly one RM event directory under {root}, found {len(dirs)}")
    return dirs[0]


def event_wall(root: pathlib.Path) -> dt.datetime:
    fields: dict[str, str] = {}
    for raw in (event_dir(root) / "meta.txt").read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in raw:
            key, value = raw.split("=", 1)
            fields[key] = value
    return iso(fields["wall"])


def d(before: dict[str, float], after: dict[str, float], key: str) -> float:
    return after.get(key, 0.0) - before.get(key, 0.0)


def state_metrics(base: dict[str, float], now: dict[str, float]) -> dict[str, float]:
    anon_lru = d(base, now, "Active(anon)") + d(base, now, "Inactive(anon)")
    file_lru = d(base, now, "Active(file)") + d(base, now, "Inactive(file)")
    unevictable = d(base, now, "Unevictable")
    slab = d(base, now, "Slab")
    non_slab_kreclaimable = d(base, now, "KReclaimable") - d(base, now, "SReclaimable")
    pagetables = d(base, now, "PageTables") + d(base, now, "SecPageTables")
    kernelstack = d(base, now, "KernelStack")
    explained = anon_lru + file_lru + unevictable + slab + non_slab_kreclaimable + pagetables + kernelstack
    memfree_loss = -d(base, now, "MemFree")
    return {
        "residual": memfree_loss - explained,
        "memfree_loss": memfree_loss,
        "memavailable_loss": -d(base, now, "MemAvailable"),
        "anon_lru_growth": anon_lru,
        "file_lru_growth": file_lru,
        "slab_growth": slab,
        "pagetable_growth": pagetables,
        "swapfree_delta": d(base, now, "SwapFree"),
    }


def emit_point(prefix: str, run: str, compact: dt.datetime, event: dt.datetime, wall: dt.datetime, metrics: dict[str, float], extra: str) -> None:
    print(
        f"{prefix}={run} {extra} wall={wall.isoformat()} "
        f"from_compact_s={(wall-compact).total_seconds():+.3f} to_event_s={(wall-event).total_seconds():+.3f} "
        f"residual_mib={metrics['residual']:+.3f} memfree_loss_mib={metrics['memfree_loss']:+.3f} "
        f"memavailable_loss_mib={metrics['memavailable_loss']:+.3f} anon_lru_growth_mib={metrics['anon_lru_growth']:+.3f} "
        f"file_lru_growth_mib={metrics['file_lru_growth']:+.3f} slab_growth_mib={metrics['slab_growth']:+.3f} "
        f"pagetable_growth_mib={metrics['pagetable_growth']:+.3f} swapfree_delta_mib={metrics['swapfree_delta']:+.3f}"
    )


def largest_increase(points: list[tuple[dt.datetime, dict[str, float]]], target_s: float) -> tuple[dt.datetime, dt.datetime, float] | None:
    best: tuple[dt.datetime, dt.datetime, float] | None = None
    for i, (left_wall, left) in enumerate(points):
        candidate: tuple[dt.datetime, dict[str, float]] | None = None
        best_error = float("inf")
        for right_wall, right in points[i + 1 :]:
            elapsed = (right_wall - left_wall).total_seconds()
            if elapsed < target_s - 0.6:
                continue
            error = abs(elapsed - target_s)
            if error < best_error:
                best_error = error
                candidate = (right_wall, right)
            if elapsed > target_s + 0.6:
                break
        if candidate is None:
            continue
        right_wall, right = candidate
        gain = right["residual"] - left["residual"]
        if best is None or gain > best[2]:
            best = (left_wall, right_wall, gain)
    return best


def run_one(run: str, root: pathlib.Path) -> None:
    compact = read_time(root / "compact-complete-iso.txt")
    event = event_wall(root)
    base = parse_meminfo_file(root / "poststop-after-compact" / "proc-meminfo.txt")
    event_mem = parse_meminfo_file(event_dir(root) / "proc-meminfo.txt")
    final = state_metrics(base, event_mem)

    raw = parse_fast_samples(root / "allocator-state" / "fast-state.txt")
    points = [(wall, state_metrics(base, mem)) for wall, _, mem in raw if compact <= wall <= event]
    if not points:
        raise SystemExit(f"no post-compact pre-event fast samples for {run}")

    print(
        f"unaccounted_window={run} compact_wall={compact.isoformat()} event_wall={event.isoformat()} "
        f"duration_s={(event-compact).total_seconds():.3f} samples={len(points)} final_residual_mib={final['residual']:.3f}"
    )
    for fraction in (0.25, 0.50, 0.75, 0.90):
        threshold = final["residual"] * fraction
        found = next(((wall, metrics) for wall, metrics in points if metrics["residual"] >= threshold), None)
        if found is None:
            print(f"unaccounted_crossing={run} fraction={fraction:.2f} threshold_mib={threshold:.3f} found=0")
        else:
            wall, metrics = found
            emit_point(
                "unaccounted_crossing",
                run,
                compact,
                event,
                wall,
                metrics,
                f"fraction={fraction:.2f} threshold_mib={threshold:.3f} found=1",
            )

    for target in (1.0, 5.0):
        best = largest_increase(points, target)
        if best is None:
            print(f"unaccounted_largest_increase={run} target_s={target:.0f} found=0")
            continue
        left_wall, right_wall, gain = best
        right_metrics = next(metrics for wall, metrics in points if wall == right_wall)
        emit_point(
            "unaccounted_largest_increase",
            run,
            compact,
            event,
            right_wall,
            right_metrics,
            f"target_s={target:.0f} found=1 start_wall={left_wall.isoformat()} duration_s={(right_wall-left_wall).total_seconds():.3f} delta_residual_mib={gain:+.3f}",
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r21", required=True)
    parser.add_argument("--r22", required=True)
    args = parser.parse_args()

    print("ORCA_R21_R22_UNACCOUNTED_TRAJECTORY=BEGIN")
    run_one("R21", pathlib.Path(args.r21))
    run_one("R22", pathlib.Path(args.r22))
    print("ORCA_R21_R22_UNACCOUNTED_TRAJECTORY=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
