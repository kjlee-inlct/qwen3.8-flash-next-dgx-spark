#!/usr/bin/env python3
"""Read-only, fail-closed capability probe for a future M1 user service.

This file does NOT install/start/stop any systemd unit, process, or Docker.
No background launch is exposed before a separate safety implementation and
physical qualification.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys


def command(*argv: str) -> subprocess.CompletedProcess[str]:
    """Only call fixed, read-only systemd inspection commands."""
    return subprocess.run(
        argv, check=False, capture_output=True, text=True, timeout=5,
    )


def runtime_dir_issues(uid: int, raw: str) -> list[str]:
    if not raw:
        return ["XDG_RUNTIME_DIR_MISSING"]
    path = Path(raw)
    if not path.is_absolute() or path.is_symlink():
        return ["XDG_RUNTIME_DIR_UNSAFE_PATH"]
    try:
        info = path.stat()
    except OSError:
        return ["XDG_RUNTIME_DIR_MISSING_OR_INACCESSIBLE"]
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != uid:
        return ["XDG_RUNTIME_DIR_UNSAFE_OWNER_OR_TYPE"]
    if stat.S_IMODE(info.st_mode) & 0o077:
        return ["XDG_RUNTIME_DIR_UNSAFE_PERMISSIONS"]
    return []


def probe() -> int:
    # Do not infer user-service availability from the current terminal alone.
    issues = runtime_dir_issues(os.getuid(), os.environ.get("XDG_RUNTIME_DIR", ""))
    missing = [name for name in ("systemctl", "loginctl", "systemd-run")
               if not shutil.which(name)]
    if missing:
        issues.append("MISSING_SYSTEMD_TOOLS:" + ",".join(missing))
    linger_state = "NOT_CHECKED"
    manager_state = "NOT_CHECKED"
    if not issues:
        try:
            linger = command("loginctl", "show-user", str(os.getuid()),
                             "--property=Linger", "--value")
            reported = linger.stdout.strip().lower()
            if linger.returncode != 0:
                linger_state = "UNKNOWN"
                issues.append("USER_LINGER_QUERY_FAILED")
            elif reported in ("yes", "linger=yes"):
                linger_state = "ENABLED"
            elif reported in ("no", "linger=no"):
                linger_state = "DISABLED"
                issues.append("USER_LINGER_DISABLED")
            else:
                linger_state = "UNKNOWN"
                issues.append("USER_LINGER_RESPONSE_UNRECOGNIZED")
            manager = command("systemctl", "--user", "show",
                              "--property=Version", "--no-pager")
            if manager.returncode == 0 and any(
                line.startswith("Version=") and line[len("Version="):].strip()
                for line in manager.stdout.splitlines()
            ):
                manager_state = "AVAILABLE"
            else:
                manager_state = "UNAVAILABLE"
                issues.append("USER_SERVICE_MANAGER_UNAVAILABLE")
        except (OSError, subprocess.TimeoutExpired):
            issues.append("USER_SERVICE_INSPECTION_FAILED")
    print("M1_BG_USER_LINGER=" + linger_state)
    print("M1_BG_USER_MANAGER=" + manager_state)
    print("M1_BG_LINGER_POLICY_CHANGE=NOT_PERFORMED")
    print("M1_BG_SUPERVISOR_IMPLEMENTED=NO")
    print("M1_BG_DOCKER_ACTION=NONE")
    print("M1_BG_USER_SERVICE_MUTATION=NONE")
    print("M1_BG_AUTO_START=DISABLED")
    if issues:
        print("M1_BG_HOST_PROBE=BLOCKED")
        for item in issues:
            print("M1_BG_BLOCK_REASON=" + item)
        return 2
    print("M1_BG_HOST_PROBE=PASS_CAPABILITY_ONLY")
    print("M1_BG_PHYSICAL_LIFECYCLE_QUALIFICATION=NOT_RUN")
    return 0


def plan() -> int:
    print("M1_BG_PLAN=USER_SYSTEMD_SUPERVISED_WORKER")
    print("M1_BG_MODE=DESIGN_AND_READ_ONLY_HOST_PROBE")
    print("M1_BG_START=NOT_IMPLEMENTED")
    print("M1_BG_STOP=NOT_IMPLEMENTED")
    print("M1_BG_AUTO_START=DISABLED")
    print("M1_BG_USER_LINGER_CHANGE=FORBIDDEN")
    print("M1_BG_WATCHDOG=REQUIRE_EXACT_ID_ARM_BEFORE_DOCKER_START")
    print("M1_BG_JOURNAL=REQUIRE_ATOMIC_STOP_AND_EXACT_ID_RECONCILE")
    print("M1_BG_GATES=SOURCE_REVIEW,LOCAL_SYNTHETIC,GITHUB_CI,ACTUAL_DGX_READ_ONLY,ACTUAL_DGX_FUNCTIONAL,HOST_STABILITY")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "probe"))
    args = parser.parse_args()
    return plan() if args.action == "plan" else probe()


if __name__ == "__main__":
    sys.exit(main())
