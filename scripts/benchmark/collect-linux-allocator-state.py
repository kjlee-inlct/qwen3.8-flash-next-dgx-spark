#!/usr/bin/env python3
"""Collect Linux allocator state while a managed RM trace is running.

This collector is intentionally read-only. It samples lightweight allocator
state at high frequency, heavier zone/page-type state less frequently, and
captures an immediate full snapshot when the kernel reports the known NVIDIA
RM sysmem OOM signature.
"""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import subprocess
import threading
import time
from typing import Iterable


FAST_FILES = (
    "/proc/buddyinfo",
    "/proc/meminfo",
    "/proc/vmstat",
    "/proc/pressure/memory",
)
SLOW_FILES = (
    "/proc/pagetypeinfo",
    "/proc/zoneinfo",
)
RM_MARKERS = ("NV_ERR_NO_MEMORY", "_memdescAllocInternal")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(path: str) -> str:
    return path.strip("/").replace("/", "-") or "root"


def read_text(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"READ_ERROR path={path} errno={exc.errno} message={exc.strerror}\n"


def append_snapshot(target: pathlib.Path, sources: Iterable[str], seq: int) -> None:
    wall = utc_now()
    mono_ns = time.monotonic_ns()
    with target.open("a", encoding="utf-8") as out:
        out.write(f"===== sample seq={seq} wall={wall} monotonic_ns={mono_ns} =====\n")
        for source in sources:
            out.write(f"--- {source} ---\n")
            out.write(read_text(pathlib.Path(source)))
            if not out.tell():
                out.write("\n")
            out.write("\n")
        out.flush()


def write_full_snapshot(root: pathlib.Path, tag: str) -> pathlib.Path:
    wall = utc_now()
    mono_ns = time.monotonic_ns()
    event_dir = root / "events" / f"{tag}-{mono_ns}"
    event_dir.mkdir(parents=True, exist_ok=False)
    (event_dir / "meta.txt").write_text(
        f"wall={wall}\nmonotonic_ns={mono_ns}\n",
        encoding="utf-8",
    )

    sources = list(FAST_FILES) + list(SLOW_FILES)
    node_root = pathlib.Path("/sys/devices/system/node")
    sources.extend(str(p) for p in sorted(node_root.glob("node*/meminfo")))

    for source in sources:
        (event_dir / f"{safe_name(source)}.txt").write_text(
            read_text(pathlib.Path(source)),
            encoding="utf-8",
        )
    return event_dir


def journal_worker(root: pathlib.Path, stop: threading.Event) -> None:
    log_path = root / "kernel-follow.txt"
    proc = subprocess.Popen(
        [
            "/usr/bin/journalctl",
            "-k",
            "-f",
            "-o",
            "short-monotonic",
            "--since",
            "now",
            "--no-pager",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    event_index = 0
    try:
        assert proc.stdout is not None
        with log_path.open("a", encoding="utf-8") as out:
            while not stop.is_set():
                line = proc.stdout.readline()
                if not line:
                    if proc.poll() is not None:
                        break
                    time.sleep(0.05)
                    continue
                out.write(line)
                out.flush()
                if any(marker in line for marker in RM_MARKERS):
                    event_index += 1
                    event_dir = write_full_snapshot(root, f"rm-oom-{event_index:02d}")
                    with (root / "rm-events.txt").open("a", encoding="utf-8") as event_out:
                        event_out.write(
                            f"event={event_index} wall={utc_now()} snapshot={event_dir.name} line={line}"
                        )
                        event_out.flush()
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=3)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--stop-file", required=True)
    parser.add_argument("--fast-interval", type=float, default=1.0)
    parser.add_argument("--slow-interval", type=float, default=5.0)
    args = parser.parse_args()

    root = pathlib.Path(args.output)
    stop_file = pathlib.Path(args.stop_file)
    root.mkdir(parents=True, exist_ok=False)

    if args.fast_interval <= 0 or args.slow_interval <= 0:
        raise SystemExit("intervals must be positive")

    (root / "collector-meta.txt").write_text(
        "\n".join(
            (
                f"started_wall={utc_now()}",
                f"started_monotonic_ns={time.monotonic_ns()}",
                f"fast_interval={args.fast_interval}",
                f"slow_interval={args.slow_interval}",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    write_full_snapshot(root, "baseline")

    stop_event = threading.Event()
    journal_thread = threading.Thread(
        target=journal_worker,
        args=(root, stop_event),
        name="allocator-journal-follow",
        daemon=True,
    )
    journal_thread.start()

    fast_seq = 0
    slow_seq = 0
    next_fast = time.monotonic()
    next_slow = next_fast

    try:
        while not stop_file.exists():
            now = time.monotonic()
            if now >= next_fast:
                fast_seq += 1
                append_snapshot(root / "fast-state.txt", FAST_FILES, fast_seq)
                next_fast += args.fast_interval
            if now >= next_slow:
                slow_seq += 1
                append_snapshot(root / "slow-state.txt", SLOW_FILES, slow_seq)
                next_slow += args.slow_interval
            sleep_for = min(next_fast, next_slow) - time.monotonic()
            time.sleep(max(0.02, min(0.25, sleep_for)))
    finally:
        write_full_snapshot(root, "final")
        stop_event.set()
        journal_thread.join(timeout=5)
        (root / "collector-meta.txt").open("a", encoding="utf-8").write(
            f"finished_wall={utc_now()}\nfinished_monotonic_ns={time.monotonic_ns()}\n"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
