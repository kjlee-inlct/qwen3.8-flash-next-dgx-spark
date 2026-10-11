#!/usr/bin/env python3
"""Offline-only H38 allocator attempt archive analysis.

Reads an existing evidence tarball without extraction, host mutation, or a
model restart. All change windows end before the recorded protection event.
Historical R21/R22 comparisons belong in dated evidence, not this analyzer.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import re
import tarfile
from typing import Any

UTC = dt.timezone.utc
SAMPLE = re.compile(r"^===== sample seq=\d+ wall=(\S+) monotonic_ns=\d+ =====$", re.M)
MEM = re.compile(r"^([^:\n]+):\s+(\d+)\s+kB$", re.M)
NORMAL = re.compile(r"^Node\s+0,\s+zone\s+Normal\s+(.+)$", re.M)
EVENT = re.compile(r"^event_type=(\S+) event_utc=(\S+)$", re.M)
SHARD = re.compile(
    r"^(\S+).*Loading safetensors checkpoint shards:\s+\d+% Completed \|\s+(\d+)/(\d+)",
    re.M,
)
CORE = (
    "Active(anon)", "Inactive(anon)", "Active(file)", "Inactive(file)",
    "Unevictable", "Slab", "PageTables", "SecPageTables", "KernelStack",
)
REQUIRED = (
    "allocator-trajectory.csv", "allocator-analysis.txt",
    "startup-phase.txt", "allocator-state/fast-state.txt",
)


def utc(value: str) -> dt.datetime:
    result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp missing UTC offset: " + value)
    return result.astimezone(UTC)


def resident_core(mem: dict[str, float]) -> float:
    """Non-overlapping conventional resident categories used in R21/R22."""
    return sum(mem[name] for name in CORE) + max(
        0.0, mem["KReclaimable"] - mem["SReclaimable"]
    )


def largest_window(rows: list[dict], field: str, seconds: int,
                   *, increase: bool = False, cadence: int = 1) -> dict:
    """Observed sample-to-sample change, never interpolation or post-event data."""
    steps = seconds // cadence
    if seconds % cadence or len(rows) <= steps:
        raise ValueError("insufficient data for requested window")
    candidates = []
    for i in range(len(rows) - steps):
        start, end = rows[i], rows[i + steps]
        elapsed = (end["time"] - start["time"]).total_seconds()
        if abs(elapsed - seconds) > 0.5:
            continue
        delta = end[field] - start[field]
        candidates.append((delta, start, end))
    if not candidates:
        raise ValueError("missing continuous samples for window")
    delta, start, end = (max if increase else min)(
        candidates, key=lambda item: item[0]
    )
    return {
        "start_utc": start["time"].isoformat(),
        "end_utc": end["time"].isoformat(),
        "delta_mib": round(delta, 3),
        "start_mib": round(start[field], 3),
        "end_mib": round(end[field], 3),
    }


def crossings(rows: list[dict], field: str) -> dict[str, dict]:
    first = rows[0][field]
    if first <= 0:
        raise ValueError("invalid zero starting reservoir")
    out = {}
    for level in (0.5, 0.1, 0.01):
        match = next((r for r in rows if r[field] < first * level), None)
        out[f"lt_{round(level * 100)}pct"] = None if match is None else {
            "time_utc": match["time"].isoformat(),
            "value_mib": round(match[field], 3),
        }
    return out


def read_tar(archive: str) -> tuple[dict[str, str], dict[str, str]]:
    content = {}
    digest = {}
    with tarfile.open(archive, "r:gz") as handle:
        members = {m.name: m for m in handle.getmembers() if m.isfile()}
        for name in REQUIRED:
            if name not in members:
                raise ValueError("missing archive entry: " + name)
            if members[name].size > 20_000_000:
                raise ValueError("oversized archive entry: " + name)
            raw = handle.extractfile(members[name]).read()
            content[name] = raw.decode("utf-8", errors="strict")
            digest[name] = hashlib.sha256(raw).hexdigest()
    return content, digest


def read_fast_raw(text: str) -> list[dict]:
    """R21/R22 meminfo resident accounting, node0 Normal physical free pool."""
    tokens = SAMPLE.split(text)
    if (len(tokens) - 1) % 2:
        raise ValueError("malformed allocator-state sample boundaries")
    result = []
    for i in range(1, len(tokens), 2):
        body = tokens[i + 1]
        mem_section = body.split("--- /proc/meminfo ---\n", 1)[1].split(
            "--- /proc/vmstat ---", 1
        )[0]
        mem = {k: int(v) / 1024 for k, v in MEM.findall(mem_section)}
        if not all(name in mem for name in (*CORE, "KReclaimable",
                    "SReclaimable", "MemFree", "MemAvailable", "SwapFree")):
            raise ValueError("incomplete meminfo sample: " + tokens[i])
        buddy_section = body.split("--- /proc/buddyinfo ---\n", 1)[1].split(
            "--- /proc/meminfo ---", 1
        )[0]
        match = NORMAL.search(buddy_section)
        if not match:
            raise ValueError("missing node0 Normal buddyinfo: " + tokens[i])
        blocks = [int(x) for x in match.group(1).split()]
        if len(blocks) < 5:
            raise ValueError("truncated Normal buddyinfo row")
        result.append({
            "time": utc(tokens[i]),
            "core_mib": resident_core(mem),
            "memfree_mib": mem["MemFree"],
            "normal_free_mib": sum(
                count * 2**order for order, count in enumerate(blocks)
            ) / 256,
        })
    return result


def inspect(archive: str) -> dict[str, Any]:
    texts, digests = read_tar(archive)
    match = EVENT.search(texts["allocator-analysis.txt"])
    if not match:
        raise ValueError("missing analyzer event timestamp")
    event_type, event = match.group(1), utc(match.group(2))
    if event_type != "PROTECTED_STOP":
        raise ValueError("expected original PROTECTED_STOP event")
    fast, slow = [], []
    for row in csv.DictReader(io.StringIO(texts["allocator-trajectory.csv"])):
        if row["source"] != "h38":
            raise ValueError("unexpected reference samples mixed into H38 archive")
        item = {"time": utc(row["wall_utc"])}
        if abs((item["time"] - event).total_seconds() - float(row["offset_s"])) > 0.01:
            raise ValueError("CSV offset/event time mismatch")
        if row["kind"] == "fast":
            for col in ("normal_o4plus_mib", "normal_o4_mib", "memfree_mib",
                        "memavailable_mib", "swapfree_mib"):
                item[col] = float(row[col])
            fast.append(item)
        elif row["kind"] == "slow":
            for col in ("unmovable_o4plus_mib", "movable_o4plus_mib"):
                item[col] = float(row[col])
            slow.append(item)
        else:
            raise ValueError("unknown allocator sample kind")
    for seq in (fast, slow):
        if len(seq) < 2 or any(b["time"] <= a["time"] for a,b in zip(seq,seq[1:])):
            raise ValueError("empty, duplicate or non-increasing samples")
    pre = [r for r in fast if r["time"] <= event]
    pre_slow = [r for r in slow if r["time"] <= event]
    raw = read_fast_raw(texts["allocator-state/fast-state.txt"])
    rawpre = [r for r in raw if r["time"] <= event]
    if len(rawpre) != len(pre) or any(
        abs((a["time"] - b["time"]).total_seconds()) > 0.01
        for a, b in zip(rawpre, pre)
    ):
        raise ValueError("raw and CSV fast sample timestamps disagree")
    for a, b in zip(rawpre, pre):
        if abs(a["memfree_mib"] - b["memfree_mib"]) > .01:
            raise ValueError("raw and CSV MemFree values disagree")
        b["core_mib"] = a["core_mib"]
        b["normal_free_mib"] = a["normal_free_mib"]
    first_free, first_core = pre[0]["memfree_mib"], pre[0]["core_mib"]
    for row in pre:
        row["core_residual_growth_mib"] = (
            first_free - row["memfree_mib"] - (row["core_mib"] - first_core)
        )
    phases = []
    for line in texts["startup-phase.txt"].split("\n"):
        m = SHARD.search(line)
        if m:
            phases.append({"time": utc(m.group(1)), "completed": int(m.group(2)),
                           "total": int(m.group(3))})
    if not phases:
        raise ValueError("no timestamped shard progress in startup phase")
    at_event = [p for p in phases if p["time"] <= event]
    after_event = [p for p in phases if p["time"] > event]
    if not at_event:
        raise ValueError("missing shard phase before protected stop")
    strongest = largest_window(pre, "normal_o4plus_mib", 5)
    residual = largest_window(pre, "core_residual_growth_mib", 5, increase=True)
    burst_start = next(r for r in pre if r["time"].isoformat() == strongest["start_utc"])
    burst_end = next(r for r in pre if r["time"].isoformat() == strongest["end_utc"])
    burst_metrics = {
        key + "_delta_mib": round(burst_end[key] - burst_start[key], 3)
        for key in (
            "normal_o4plus_mib", "normal_free_mib", "memfree_mib",
            "memavailable_mib", "swapfree_mib", "core_mib",
            "core_residual_growth_mib",
        )
    }
    return {
        "event_type": event_type,
        "event_utc": event.isoformat(),
        "sha256_by_entry": digests,
        "samples": {
            "fast_total": len(fast), "fast_pre_event": len(pre),
            "fast_post_event_excluded": len(fast) - len(pre),
            "slow_total": len(slow), "slow_pre_event": len(pre_slow),
            "slow_post_event_excluded": len(slow) - len(pre_slow),
        },
        "first_fast_sample_utc": pre[0]["time"].isoformat(),
        "initial_normal_o4plus_mib": round(pre[0]["normal_o4plus_mib"], 3),
        "initial_unmovable_o4plus_mib": round(pre_slow[0]["unmovable_o4plus_mib"], 3),
        "normal_crossings": crossings(pre, "normal_o4plus_mib"),
        "unmovable_crossings": crossings(pre_slow, "unmovable_o4plus_mib"),
        "largest_normal_o4plus_drop_1s": largest_window(pre, "normal_o4plus_mib", 1),
        "largest_normal_o4plus_drop_5s": strongest,
        "largest_unmovable_drop_5s": largest_window(
            pre_slow, "unmovable_o4plus_mib", 5, cadence=5
        ),
        "largest_core_residual_growth_5s": residual,
        "normal_burst_aligned_metrics": burst_metrics,
        "last_pre_event_fast": {
            "time_utc": pre[-1]["time"].isoformat(),
            "normal_o4plus_mib": round(pre[-1]["normal_o4plus_mib"], 3),
        },
        "startup_progress": {
            "last_logged_before_protection": at_event[-1]["completed"],
            "last_before_time_utc": at_event[-1]["time"].isoformat(),
            "first_logged_after_protection": after_event[0]["completed"] if after_event else None,
            "first_after_time_utc": after_event[0]["time"].isoformat() if after_event else None,
            "first_shard_completed_utc": next(
                p["time"].isoformat() for p in phases if p["completed"] == 1
            ),
        },
        "classification": "PROTECTED_STOP; FUNCTIONAL NOT_REACHED; HOST-STABILITY INCONCLUSIVE",
        "claim_boundary": "Physical-page residual is approximate and not an NVIDIA page-ownership measurement",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive", required=True)
    ap.add_argument("--json-output", help="optional local analysis JSON output")
    args = ap.parse_args()
    result = json.dumps(inspect(args.archive), indent=2, sort_keys=True) + "\n"
    print(result, end="")
    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as handle:
            handle.write(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
