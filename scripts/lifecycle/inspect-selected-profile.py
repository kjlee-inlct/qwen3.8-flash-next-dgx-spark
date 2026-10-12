#!/usr/bin/env python3
"""Read-only selected-profile snapshot: intent is not verified runtime health."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
from state_file import parse_install, parse_state  # noqa: E402

STATE = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "qwen38-spark"
CONTAINER = "qwen38-flash-next"
TX = (
    ("PROFILE_SWITCH_STATE", "profile-switch-transition.env", "profile-switch", "PROFILE_SWITCH_STATE"),
    ("RUNTIME_TRANSITION_STATE", "runtime-transition.env", "runtime-transition", "TRANSACTION_STATE"),
    ("UPDATE_STATE", "update-transition.env", "update", "UPDATE_STATE"),
    ("RELEASE_PROFILE_REFRESH_STATE", "release-profile-refresh-transition.env", "release-profile-refresh", "RELEASE_PROFILE_REFRESH_STATE"),
)


def emit(key: str, value: str) -> None:
    print(f"{key}={value}")


def parse_file(path: Path, schema: str) -> tuple[bool, dict[str, str]]:
    if not path.is_file() or path.is_symlink():
        return False, {}
    try:
        data = parse_install(path, schema) if schema == "install-maintenance" else parse_state(path, schema)
        return True, data
    except (OSError, ValueError, KeyError) as exc:
        print(f"READONLY_PARSE_ERROR={path.name}:{type(exc).__name__}", file=sys.stderr)
        return False, {}


def probe(command: list[str]) -> tuple[bool, str]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return False, ""
    return result.returncode == 0, result.stdout if result.returncode == 0 else result.stderr


def container_snapshot() -> dict[str, str]:
    result = dict(CONTAINER_STATE="UNKNOWN", CONTAINER_IMAGE="UNKNOWN",
                  CONTAINER_MODEL_MOUNT="UNKNOWN", CONTAINER_SERVED_NAME="UNKNOWN", CONTAINER_ID="UNKNOWN")
    ok, raw = probe(["docker", "inspect", "--type", "container", CONTAINER])
    if not ok:
        if any(token in raw.lower() for token in ("no such object:", "no such container:", "no such container ")):
            result["CONTAINER_STATE"] = "ABSENT"
        return result
    try:
        info = json.loads(raw)[0]
        result["CONTAINER_STATE"] = str(info["State"]["Status"]).upper()
        result["CONTAINER_IMAGE"] = str(info["Config"]["Image"])
        result["CONTAINER_ID"] = str(info["Id"])
        mounts = [m["Source"] for m in info.get("Mounts", []) if m.get("Destination") == "/model"]
        if len(mounts) == 1:
            result["CONTAINER_MODEL_MOUNT"] = mounts[0]
        cmd = info["Config"].get("Cmd") or []
        if isinstance(cmd, list) and "--served-model-name" in cmd:
            index = cmd.index("--served-model-name") + 1
            if index < len(cmd):
                result["CONTAINER_SERVED_NAME"] = str(cmd[index])
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        return {key: "UNKNOWN" for key in result}
    return result


def service_state() -> str:
    ok, raw = probe(["systemctl", "show", "qwen38-flash-next.service",
                     "--property=LoadState", "--property=ActiveState", "--no-pager"])
    if not ok:
        return "UNKNOWN"
    values = dict(line.split("=", 1) for line in raw.splitlines() if "=" in line)
    if values.get("LoadState") == "not-found":
        return "NOT_INSTALLED"
    if values.get("LoadState") != "loaded":
        return "UNKNOWN"
    return values.get("ActiveState", "UNKNOWN").upper()


def main() -> int:
    if len(sys.argv) != 1:
        print("Usage: python3 scripts/lifecycle/inspect-selected-profile.py", file=sys.stderr)
        return 2
    emit("SELECTED_PROFILE_SNAPSHOT", "READ_ONLY")
    path = STATE / "install.env"
    exists = path.exists() or path.is_symlink()
    valid, manifest = parse_file(path, "install-maintenance") if exists else (False, {})
    manifest_status = "VALID" if valid else ("INVALID" if exists else "MISSING")
    phase = manifest.get("PHASE", "UNKNOWN")
    selected = manifest.get("MODEL_PROFILE", "UNKNOWN") if valid else "UNKNOWN"
    if not exists or (valid and phase == "uninstalled"):
        selected = "NONE"
    emit("MANIFEST_STATUS", manifest_status)
    emit("INSTALL_PHASE", phase if valid else manifest_status)
    emit("SELECTED_PROFILE", selected)
    emit("RECORDED_PROFILE", manifest.get("MODEL_PROFILE", "UNKNOWN"))
    emit("PROFILE_REPOSITORY", manifest.get("MODEL_REPO", "UNKNOWN"))
    emit("MODEL_PATH", manifest.get("MODEL_DIR", "UNKNOWN"))
    emit("EXPECTED_IMAGE", manifest.get("VLLM_IMAGE", "UNKNOWN"))
    emit("EXPECTED_SERVED_NAME", manifest.get("SERVED_NAME", "UNKNOWN"))
    emit("MONITOR_PROTECT", manifest.get("MONITOR_PROTECT", "UNKNOWN"))
    emit("MONITOR_ENABLED", manifest.get("MONITOR_ENABLED", manifest.get("MONITOR_PROTECT", "UNKNOWN")))

    model_dir = Path(manifest["MODEL_DIR"]) if "MODEL_DIR" in manifest else None
    if model_dir is not None and model_dir.is_dir() and not model_dir.is_symlink():
        marker_name = ".qwen38-hybrid-manifest.json" if selected == "orcarouter-hybrid" else ".qwen38-model-manifest.json"
        marker = model_dir / marker_name
        model_status = "MARKER_PRESENT_NOT_VERIFIED" if marker.is_file() and not marker.is_symlink() else "PRESENT_UNVERIFIED"
    else:
        model_status = "ABSENT_OR_UNKNOWN" if model_dir is not None else "UNKNOWN"
    emit("MODEL_PATH_STATUS", model_status)

    pending = False
    for label, filename, schema, key in TX:
        txfile = STATE / filename
        if txfile.exists() or txfile.is_symlink():
            ok, state = parse_file(txfile, schema)
            tx_status = state[key] if ok else "INVALID"
            pending = True
            if label == "PROFILE_SWITCH_STATE" and ok:
                emit("PROFILE_SWITCH_TARGET", state["TO_PROFILE"])
        else:
            tx_status = "IDLE"
        emit(label, tx_status)

    leftovers = (
        "settings-transition.phase", "runtime-adopt.env",
        "install.env.profile-switch-backup", "install.env.profile-switch-candidate",
        "install.env.release-profile-refresh-backup", "install.env.release-profile-refresh-candidate",
    )
    stale = any((STATE / name).exists() or (STATE / name).is_symlink() for name in leftovers)
    emit("STALE_TRANSACTION_ARTIFACTS", "PRESENT" if stale else "NONE")
    pending = pending or stale

    runtime = container_snapshot()
    for key, value in runtime.items():
        if key != "CONTAINER_ID":
            emit(key, value)
    emit("SERVICE_STATE", service_state())

    commitfile = STATE / "runtime-commit.env"
    attestation = "MISSING"
    if commitfile.exists() or commitfile.is_symlink():
        ok, commit = parse_file(commitfile, "runtime-commit")
        if not ok:
            attestation = "INVALID"
        elif runtime["CONTAINER_ID"] == "UNKNOWN":
            attestation = "UNVERIFIED_CONTAINER"
        elif commit["RUNTIME_CONTAINER_ID"] == runtime["CONTAINER_ID"] and commit["RUNTIME_CONTAINER_NAME"] == CONTAINER:
            attestation = "MATCHING_CONTAINER_ID_NOT_HEALTH"
        else:
            attestation = "MISMATCH"
    emit("RUNTIME_ATTESTATION", attestation)

    running = runtime["CONTAINER_STATE"] == "RUNNING"
    match = (running and valid and phase == "complete"
             and runtime["CONTAINER_IMAGE"] == manifest.get("VLLM_IMAGE")
             and runtime["CONTAINER_MODEL_MOUNT"] == manifest.get("MODEL_DIR")
             and runtime["CONTAINER_SERVED_NAME"] == manifest.get("SERVED_NAME"))
    alignment = "MATCHED_NOT_READINESS" if match else ("MISMATCH_OR_UNKNOWN" if running else "NOT_APPLICABLE")
    emit("RUNTIME_CONFIGURATION", alignment)
    if manifest_status == "INVALID":
        summary = "INVALID_MANIFEST"
    elif pending:
        summary = "TRANSITION_OR_ARTIFACT_PENDING"
    elif manifest_status == "MISSING":
        summary = "NO_INSTALL_MANIFEST"
    elif phase == "uninstalled":
        summary = "UNINSTALLED_NOT_SERVING"
    elif match:
        summary = "RUNNING_CONFIG_ALIGNED_NOT_HEALTH_QUALIFIED"
    elif running:
        summary = "RUNNING_UNVERIFIED_OR_DRIFTED"
    elif runtime["CONTAINER_STATE"] == "ABSENT":
        summary = "CONTAINER_ABSENT"
    elif runtime["CONTAINER_STATE"] in ("EXITED", "CREATED", "DEAD", "PAUSED", "RESTARTING"):
        summary = "CONTAINER_NOT_RUNNING"
    else:
        summary = "UNKNOWN_RUNTIME"
    emit("PROFILE_STATUS_SUMMARY", summary)
    emit("ACTUAL_SERVED_PROFILE", "NOT_VERIFIED")
    emit("HOST_HEALTH_QUALIFICATION", "NOT_ESTABLISHED_BY_THIS_SNAPSHOT")
    return 3 if manifest_status == "INVALID" or pending else 0


if __name__ == "__main__":
    raise SystemExit(main())
