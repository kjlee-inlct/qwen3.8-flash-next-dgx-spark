#!/usr/bin/env python3
"""Fail-closed read-only audit: no project model API, proxy, or auto-boot.

Installed files/checkpoints/reports may remain. This is a *host-idle* audit,
distinct from the mazinb-only evidence-retirement audit.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import stat
import subprocess
import sys

SCRIPT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_ROOT / "scripts/lib"))
from state_file import parse_install  # noqa: E402

MANAGED_UNITS = (
    "qwen38-flash-next.service",
    "qwen38-openwebui-proxy.socket",
    "qwen38-openwebui-proxy.service",
)
TRIAL_PORTS = (18888, 18889)
BACKEND_PORT = 8888


class NotIdle(RuntimeError):
    pass


def check(condition: bool, reason: str) -> None:
    if not condition:
        raise NotIdle(reason)


def run(*argv: str) -> str:
    p = subprocess.run(argv, text=True, capture_output=True, check=False, timeout=25)
    check(p.returncode == 0, f"COMMAND_UNAVAILABLE:{' '.join(argv[:3])}:{p.returncode}")
    return p.stdout


def systemd() -> None:
    for unit in MANAGED_UNITS:
        output = run("systemctl", "show", unit,
                     "--property=LoadState,ActiveState,UnitFileState", "--no-pager")
        values = {}
        for line in output.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                values[key] = value
        check("LoadState" in values and "ActiveState" in values
              and "UnitFileState" in values, f"UNIT_STATUS_UNAVAILABLE:{unit}")
        active = values["ActiveState"]
        boot = values["UnitFileState"]
        print(f"MANAGED_IDLE_UNIT={unit} load={values['LoadState']} active={active} boot={boot}")
        check(active in ("inactive", "failed"), f"UNIT_ACTIVE:{unit}:{active}")
        check(boot in ("disabled", "masked", "not-found", ""),
              f"UNIT_AUTO_START_POSSIBLE:{unit}:{boot}")
        # A failed service may auto-activate on dependency triggers; list it
        # as not a PASS until an operator has investigated and reset the fault.
        check(active == "inactive", f"UNIT_FAILED:{unit}")
    print("MANAGED_IDLE_SYSTEMD=NO_RUNNING_OR_BOOT_ENABLED_UNITS")


def listeners(ports: set[int]) -> None:
    output = run("ss", "-H", "-ltn")
    found: dict[int, list[str]] = {x: [] for x in ports}
    for line in output.splitlines():
        cols = line.split()
        check(len(cols) >= 4, "SOCKET_STATUS_MALFORMED")
        endpoint = cols[3]
        number = endpoint.rsplit(":", 1)[-1]
        if number.isdecimal() and int(number) in found:
            found[int(number)].append(endpoint)
    for port in sorted(ports):
        for addr in found[port]:
            print(f"MANAGED_IDLE_UNEXPECTED_LISTENER={addr}")
        check(not found[port], f"PORT_STILL_LISTENING:{port}")
    print("MANAGED_IDLE_MANAGED_PORTS=NO_LISTENERS")


def docker() -> None:
    running = [name.strip() for name in run("docker", "ps", "--format", "{{.Names}}").splitlines()]
    project_running = [x for x in running if x.startswith("qwen38-")]
    check(not project_running, "PROJECT_DOCKER_RUNNING:" + ",".join(project_running))
    print("MANAGED_IDLE_DOCKER=NO_RUNNING_QWEN38_CONTAINERS")


def verify(home: Path, state_dir: Path) -> None:
    manifest = state_dir / "install.env"
    check(manifest.is_file() and not manifest.is_symlink(),
          "MANIFEST_MISSING_OR_UNSAFE")
    data = parse_install(manifest, "install-maintenance")
    check(data.get("PHASE") == "complete", "INSTALL_NOT_COMPLETE")
    print(f"MANAGED_IDLE_MODEL_PROFILE={data.get('MODEL_PROFILE')}")
    print(f"MANAGED_IDLE_API_ACCESS_MODE={data.get('API_ACCESS_MODE')}")
    print(f"MANAGED_IDLE_SERVICE_ENABLED={data.get('SERVICE_ENABLED')}")
    check(data.get("API_ACCESS_MODE") == "local" and
          data.get("SERVICE_ENABLED") == "0",
          "MANIFEST_STILL_EXPOSES_API_OR_ENABLES_BOOT")
    candidates: set[int] = {BACKEND_PORT, *TRIAL_PORTS}
    for key in ("API_DOCKER_PORT", "API_LAN_PORT", "PROXY_PORT"):
        item = str(data.get(key, ""))
        if item:
            check(item.isdecimal() and 1 <= int(item) <= 65535,
                  "MANIFEST_PORT_INVALID:" + key)
            candidates.add(int(item))
    systemd()
    listeners(candidates)
    docker()
    print("MANAGED_IDLE_AUDIT=PASS_NO_MANAGED_API_LISTENER_OR_BOOT_START")
    print("MANAGED_IDLE_AUDIT_HOST_MUTATION=NONE")


def main() -> int:
    if len(sys.argv) != 1:
        print("Usage: verify-managed-idle.py", file=sys.stderr)
        return 2
    home = Path.home()
    state = Path(os.environ.get("XDG_STATE_HOME", str(home / ".local/state"))) / "qwen38-spark"
    try:
        verify(home, state)
    except (NotIdle, OSError, ValueError, KeyError, subprocess.SubprocessError) as e:
        print(f"MANAGED_IDLE_AUDIT=BLOCKED reason={str(e)[:440]}", file=sys.stderr)
        print("MANAGED_IDLE_AUDIT_HOST_MUTATION=NONE", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
