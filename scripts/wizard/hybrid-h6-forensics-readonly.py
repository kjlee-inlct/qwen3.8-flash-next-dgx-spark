#!/usr/bin/env python3
"""Read-only, bounded forensic summary of an existing Hybrid H6 M1 trial.

Never creates, starts, stops, deletes, or changes a Docker object, service,
journal, checkpoint, or benchmark. Does not mistake Docker OOMKilled=false
for proof that NVIDIA RM was healthy. Kernel journal access is optional.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

NAME_RE = re.compile(r"qwen38-hybrid-h6-m1-[0-9]{14}-[0-9a-f]{8}\Z")
SHA64 = re.compile(r"[0-9a-f]{64}\Z")
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
STAMP = re.compile(r"20[0-9]{2}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}\Z")
KEEP_MONITOR = ("monitor started:", "AB_MONITOR_ARMED_ID=", "WARNING memory margin low",
                "PROTECT stopping", "TRIAL WATCHDOG EXIT", "memory margin recovered",
                "TRIAL_RUNTIME_LIMIT_REACHED", "ERROR:")
KERNEL_MARKERS = ("NV_ERR_NO_MEMORY", "_memdescAllocInternal", "NVRM", "Xid",
                  "out of memory", "oom-killer")


class EvidenceError(Exception):
    pass


def require(ok: bool, why: str) -> None:
    if not ok:
        raise EvidenceError(why)


def checked_file(path: Path, *, max_size: int) -> None:
    require(path.is_file() and not path.is_symlink(), f"file_missing_or_symlink:{path.name}")
    st = path.stat()
    require(st.st_uid == os.getuid() and 0 < st.st_size <= max_size,
            f"file_owner_or_size_invalid:{path.name}")


def checked_dir(path: Path) -> None:
    require(path.is_dir() and not path.is_symlink() and path.stat().st_uid == os.getuid(),
            f"directory_owner_or_symlink_invalid:{path.name}")


def marker_fields(data: str, *, name: str, container_id: str) -> dict[str, str]:
    """Parse only literal safe atoms; shell '%' quoting is NOT evaluated."""
    values: dict[str, str] = {}
    for row in data.splitlines():
        parts = row.split("=", 1)
        require(len(parts) == 2, "malformed_stop_marker")
        key, val = parts
        require(re.fullmatch(r"[A-Z_]+", key) is not None and key not in values,
                "unexpected_or_duplicate_stop_marker_key")
        require(re.fullmatch(r"[A-Za-z0-9:._/-]+", val) is not None,
                "escaped_or_unsafe_stop_marker_value")
        values[key] = val
    require(values.get("RUNTIME_STOP_SCHEMA_VERSION") == "1"
            and values.get("STOP_REASON") == "memory-protection"
            and values.get("STOP_CONTAINER_NAME") == name
            and values.get("STOP_CONTAINER_ID") == container_id
            and re.fullmatch(r"20\d\d-\d\d-\d\dT\d\d:\d\d:\d\dZ",
                             values.get("UPDATED_AT", "")) is not None,
            "stop_marker_does_not_match_protected_candidate")
    return values


def monitor_events(path: Path) -> tuple[list[str], bool, int]:
    checked_file(path, max_size=256 * 1024 * 1024)
    latest = deque(maxlen=16)
    protect_seen = False
    warnings = 0
    with path.open(encoding="utf-8", errors="replace") as src:
        for line in src:
            if "WARNING memory margin low" in line:
                warnings += 1
            if "PROTECT stopping" in line:
                protect_seen = True
            if any(term in line for term in KEEP_MONITOR):
                latest.append(line.strip()[:750])
    return list(latest), protect_seen, warnings


def inspect_exact(container_id: str, name: str, record: dict) -> dict:
    result = subprocess.run(["docker", "inspect", container_id], capture_output=True,
                            text=True, check=False, timeout=25)
    require(result.returncode == 0, "docker_inspect_failed")
    objs = json.loads(result.stdout)
    require(isinstance(objs, list) and len(objs) == 1, "docker_inspect_shape_invalid")
    obj = objs[0]
    labels = (obj.get("Config") or {}).get("Labels") or {}
    require(obj.get("Id") == container_id and obj.get("Name") == "/" + name,
            "candidate_docker_id_or_name_drift")
    require(obj.get("Image") == record.get("image_id")
            and labels.get("qwen38.abtrial") == "hybrid"
            and labels.get("qwen38.variant") == "h6-m1"
            and labels.get("qwen38.predecessor") == record.get("old_id"),
            "candidate_docker_provenance_drift")
    require(obj.get("HostConfig", {}).get("RestartPolicy", {}).get("Name") == "no",
            "candidate_auto_restart_not_disabled")
    return obj


def kernel_summary(since: str) -> None:
    """Best-effort evidence, not an admission PASS; never authenticate or write."""
    if STAMP.fullmatch(since) is None:
        print("H6_FORENSIC_KERNEL=NOT_CHECKED_BAD_TIMESTAMP")
        return
    try:
        result = subprocess.run(
            ["sudo", "-n", "journalctl", "-k", "--since", since, "--no-pager"],
            capture_output=True, text=True, check=False, timeout=40,
        )
    except (OSError, subprocess.TimeoutExpired):
        print("H6_FORENSIC_KERNEL=NOT_CHECKED_PERMISSION_OR_TIMEOUT")
        return
    if result.returncode:
        print("H6_FORENSIC_KERNEL=NOT_CHECKED_NO_NONINTERACTIVE_SUDO")
        return
    found = [x.strip()[:900] for x in result.stdout.splitlines()
             if any(word.lower() in x.lower() for word in KERNEL_MARKERS)]
    print(f"H6_FORENSIC_KERNEL_MATCHES={len(found)}")
    for line in found[-12:]:
        print("H6_KERNEL_EVENT=" + line)
    print("H6_FORENSIC_KERNEL=REVIEW_MATCHED_WINDOW_ONLY")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--expected-id", default="")
    p.add_argument("--expected-source-sha", default="")
    p.add_argument("--name", default="")
    p.add_argument("--latest", action="store_true",
                   help="Use latest H6 journal and verify exact Docker ID")
    args = p.parse_args()
    try:
        if args.latest:
            require(not (args.name or args.expected_id or args.expected_source_sha),
                    "cannot_combine_latest_and_explicit_ids")
            state = Path(os.environ.get(
                "XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "qwen38-spark"
            root = state / "hybrid-h6-m1"
            checked_dir(state)
            checked_dir(root)
            checked_file(root / "active.json", max_size=1024 * 1024)
            latest = json.loads((root / "active.json").read_bytes())
            require(isinstance(latest, dict), "latest_record_not_object")
            args.name = latest.get("name", "")
            args.expected_id = latest.get("id", "")
            args.expected_source_sha = latest.get("source_sha", "")
        require(isinstance(args.expected_id, str) and isinstance(args.name, str)
                and isinstance(args.expected_source_sha, str)
                and SHA64.fullmatch(args.expected_id) is not None
                and SHA40.fullmatch(args.expected_source_sha) is not None
                and NAME_RE.fullmatch(args.name) is not None,
                "explicit_full_ids_and_trial_name_required")
        state = Path(os.environ.get(
            "XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "qwen38-spark"
        trial_root = state / "hybrid-h6-m1"
        trial_dir = trial_root / args.name
        monitor_dir = trial_dir / "monitor"
        for path in (state, trial_root, trial_dir, monitor_dir):
            checked_dir(path)
        active = trial_root / "active.json"
        historical = trial_root / (args.name + ".json")
        for path in (active, historical):
            checked_file(path, max_size=1024 * 1024)
        a, b = active.read_bytes(), historical.read_bytes()
        require(a == b, "active_and_per_trial_journal_drift")
        record = json.loads(a)
        require(isinstance(record, dict) and record.get("schema") == 1
                and record.get("id") == args.expected_id
                and record.get("name") == args.name
                and record.get("source_sha") == args.expected_source_sha
                and record.get("trial_dir") == str(trial_dir)
                and record.get("monitor_dir") == str(monitor_dir),
                "trial_journal_identity_drift")
        require(record.get("phase") == "failed_stopped",
                "only_existing_failed_stopped_session_is_forensically_reviewed")
        print("H6_FORENSIC_SOURCE_SHA=" + record["source_sha"])
        print("H6_FORENSIC_CANDIDATE=" + record["name"])
        print("H6_FORENSIC_EXACT_DOCKER_ID=" + record["id"])
        print("H6_FORENSIC_JOURNAL_SHA256=" + hashlib.sha256(a).hexdigest())
        print("H6_FORENSIC_JOURNAL_PHASE=" + record["phase"])
        print("H6_FORENSIC_JOURNAL_DETAIL=" + str(record.get("detail", ""))[:350])
        obj = inspect_exact(args.expected_id, args.name, record)
        state_obj = obj.get("State", {})
        print("H6_FORENSIC_DOCKER_STATUS=" + str(state_obj.get("Status")))
        print("H6_FORENSIC_DOCKER_EXIT_CODE=" + str(state_obj.get("ExitCode")))
        print("H6_FORENSIC_DOCKER_OOM_KILLED=" + str(state_obj.get("OOMKilled")))
        require(state_obj.get("Status") == "exited"
                and state_obj.get("Running") is False, "candidate_not_proven_stopped")
        events, saw_protect, n_warning = monitor_events(trial_dir / "monitor.log")
        print(f"H6_FORENSIC_WARNING_EVENTS={n_warning}")
        for line in events:
            print("H6_MONITOR_EVENT=" + line)
        marker = monitor_dir / "runtime-stop.env"
        checked_file(marker, max_size=4096)
        stop = marker_fields(marker.read_text(encoding="utf-8"),
                             name=args.name, container_id=args.expected_id)
        print("H6_FORENSIC_STOP_REASON=" + stop["STOP_REASON"])
        print("H6_FORENSIC_STOP_AT=" + stop["UPDATED_AT"])
        print("H6_FORENSIC_PROTECT_LOG_PRESENT=" + str(saw_protect))
        print("H6_FORENSIC_DOCKER_OOM_INTERPRETATION=DOCKER_OOM_KILLED_FALSE_DOES_NOT_EXCLUDE_RM")
        kernel_summary(str(record.get("kernel_since", "")))
        print("H6_FORENSIC_HOST_MUTATION=NONE")
        print("H6_FORENSIC_RELAUNCH=NOT_AUTHORIZED")
        print("H6_FIRST_BENCHMARK=NOT_MEASURED")
        if not saw_protect:
            print("H6_FORENSIC_VERDICT=INCOMPLETE_NO_MONITOR_PROTECT_EVENT")
            return 3
        print("H6_FORENSIC_VERDICT=CONFIRMED_WATCHDOG_MEMORY_PROTECTION_STOP")
        return 0
    except (EvidenceError, OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print("H6_FORENSIC_VERDICT=INVALID_OR_INCONSISTENT reason=" + str(exc),
              file=sys.stderr)
        print("H6_FORENSIC_HOST_MUTATION=NONE", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
