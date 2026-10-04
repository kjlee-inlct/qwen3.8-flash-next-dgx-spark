#!/usr/bin/env python3
"""Compare predecessor-runtime age with RM OOM outcome across OrcaRouter legs.

This analyzer is read-only. Each input leg must be an R11 evidence root containing
an r10b directory. It correlates the age of the container being replaced with the
observed RM OOM count for that managed restart.
"""

from __future__ import annotations

import argparse
import datetime as dt
import pathlib
import re

RM_OOM_RE = re.compile(r"^rm_oom_count=(\d+)$", re.MULTILINE)


def parse_iso(text: str) -> dt.datetime:
    value = text.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp is not timezone-aware: {text!r}")
    return parsed


def read_required(path: pathlib.Path) -> str:
    if not path.is_file():
        raise SystemExit(f"missing evidence file: {path}")
    return path.read_text(encoding="utf-8", errors="replace").strip()


def rm_oom_count(root: pathlib.Path) -> int:
    summary = root / "r11-summary.txt"
    if summary.is_file():
        match = RM_OOM_RE.search(summary.read_text(encoding="utf-8", errors="replace"))
        if match:
            return int(match.group(1))

    errors = root / "r10b" / "kernel-errors.txt"
    if not errors.is_file():
        raise SystemExit(f"missing RM outcome evidence: {summary} or {errors}")
    return sum(
        1
        for line in errors.read_text(encoding="utf-8", errors="replace").splitlines()
        if "NV_ERR_NO_MEMORY" in line or "_memdescAllocInternal" in line
    )


def parse_leg(value: str) -> tuple[str, pathlib.Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("--leg must be LABEL=/path/to/r11-evidence")
    label, raw_path = value.split("=", 1)
    label = label.strip()
    raw_path = raw_path.strip()
    if not label or not raw_path:
        raise argparse.ArgumentTypeError("--leg must be LABEL=/path/to/r11-evidence")
    return label, pathlib.Path(raw_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--leg", action="append", required=True, type=parse_leg)
    args = parser.parse_args()

    print("ORCA_PREDECESSOR_RUNTIME_AGE=BEGIN")
    for label, root in args.leg:
        r10b = root / "r10b"
        container_started_text = read_required(r10b / "container-started-before.txt")
        restart_started_text = read_required(r10b / "managed-child-started.txt")
        container_started = parse_iso(container_started_text)
        restart_started = parse_iso(restart_started_text)
        age_s = (restart_started - container_started).total_seconds()
        if age_s < 0:
            raise SystemExit(
                f"negative predecessor runtime age for {label}: "
                f"container={container_started_text} restart={restart_started_text}"
            )
        oom = rm_oom_count(root)
        outcome = "CLEAN" if oom == 0 else "RM_OOM"
        print(
            f"leg={label} predecessor_started={container_started_text} "
            f"restart_started={restart_started_text} predecessor_age_s={age_s:.3f} "
            f"predecessor_age_min={age_s / 60.0:.3f} "
            f"predecessor_age_h={age_s / 3600.0:.3f} rm_oom_count={oom} outcome={outcome}"
        )
    print("ORCA_PREDECESSOR_RUNTIME_AGE=END")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
