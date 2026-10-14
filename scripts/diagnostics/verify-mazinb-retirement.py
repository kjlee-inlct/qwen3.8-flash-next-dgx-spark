#!/usr/bin/env python3
"""Read-only, fail-closed mazinb post-retirement host audit.

Distinguishes mazinb-only artifacts from the installed OrcaRouter runtime
and its shared OpenWebUI socket proxy. NEVER removes anything or restarts a
service. No network request or runtime/model activation.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "scripts/model/retire-mazinb-containers.py"
SPEC = importlib.util.spec_from_file_location("mazinb_retirement_readonly", LIB)
assert SPEC and SPEC.loader
RETIRE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RETIRE
SPEC.loader.exec_module(RETIRE)
sys.path.insert(0, str(ROOT / "scripts/lib"))
from state_file import parse_install  # noqa: E402

UNIT = "qwen38-flash-next.service"
SOCKET_PROXY = ("qwen38-openwebui-proxy.socket", "qwen38-openwebui-proxy.service")
DEDICATED_UNIT = re.compile(r"^[a-z0-9_.@-]*mazinb[a-z0-9_.@-]*\.(?:service|socket|timer|path)$", re.I)
ARCHIVE_NAME = re.compile(r"([0-9a-f]{16})\.(json|log)\Z")
M1_PORT = 18889
SHARED_PORTS = (8888, 8000, 8001)


class AuditBlocked(RuntimeError):
    pass


def require(ok: bool, label: str) -> None:
    if not ok:
        raise AuditBlocked(label)


def command(*argv: str) -> str:
    result = subprocess.run(argv, capture_output=True, text=True, check=False, timeout=20)
    require(result.returncode == 0,
            f"COMMAND_FAILED:{' '.join(argv[:3])}:rc={result.returncode}")
    return result.stdout


def strict_file(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def strict_dir(path: Path) -> bool:
    try:
        return stat.S_ISDIR(path.lstat().st_mode)
    except OSError:
        return False


def sha256(path: Path) -> str:
    require(strict_file(path), f"ARCHIVE_FILE_MISSING_OR_SYMLINK:{path.name}")
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def archive_check(home: Path, model_root: Path, state: Path) -> Path:
    # Provenance is rechecked independently from the already-retired Docker.
    RETIRE.evidence(home, model_root, state)
    record = json.loads((state / "mazinb-m1/active.json").read_text(encoding="utf-8"))
    marker_path = state / "mazinb-m1/retired-docker.json"
    require(strict_file(marker_path), "M1_RETIREMENT_MARKER_MISSING")
    marker = json.loads(marker_path.read_text(encoding="utf-8"))
    m1_name = "qwen38-mazinb-m1-20261014013811-16ced779"
    require(marker.get("schema_version") == 1 and marker.get("state") ==
            "archived_docker_removed" and marker.get("id") == RETIRE.EXPECTED[m1_name]
            and marker.get("name") == m1_name and
            record.get("id") == marker["id"] and record.get("name") == m1_name,
            "M1_TOMBSTONE_IDENTITY_INVALID")
    archive = Path(marker.get("archive_path", ""))
    archive_root = state / "retirement-archives"
    require(archive.is_absolute() and archive.parent == archive_root and
            archive.name.startswith("mazinb-docker-") and strict_dir(archive) and
            not archive.is_symlink(), "DOCKER_ARCHIVE_OUTSIDE_MANAGED_STATE")
    manifest_path = archive / "SHA256SUMS"
    require(sha256(manifest_path) == marker.get("archive_sha256_manifest"),
            "DOCKER_ARCHIVE_MANIFEST_CHANGED")
    seen: dict[str, str] = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([0-9a-f]{16}\.(?:json|log))", line)
        require(match is not None, "DOCKER_ARCHIVE_MANIFEST_MALFORMED")
        digest, name = match.groups()
        require(name not in seen, "DOCKER_ARCHIVE_MANIFEST_DUPLICATE")
        seen[name] = digest
    expected_files = {cid[:16] + "." + ext
                      for cid in RETIRE.EXPECTED.values()
                      for ext in ("log", "json")}
    require(set(seen) == expected_files, "DOCKER_ARCHIVE_NOT_EXACTLY_FIVE_PAIRS")
    for name, digest in seen.items():
        require(sha256(archive / name) == digest, f"DOCKER_ARCHIVE_FILE_CHANGED:{name}")
    for name, cid in RETIRE.EXPECTED.items():
        info = json.loads((archive / (cid[:16] + ".json")).read_text(encoding="utf-8"))
        require(info.get("id") == cid and info.get("name") == "/" + name,
                f"DOCKER_ARCHIVE_METADATA_IDENTITY_CHANGED:{name}")
    print("MAZINB_AUDIT_ARCHIVE=PASS_EXACT_FIVE_INSPECT_AND_LOG_PAIRS_SHA256")
    print("MAZINB_AUDIT_ORIGINAL_AND_GITHUB_BENCHMARK=SHA256_PASS")
    print("MAZINB_AUDIT_ARCHIVE_PATH=" + str(archive))
    return archive


def docker_check() -> None:
    values = [s.strip() for s in command("docker", "ps", "-aq", "--no-trunc").splitlines() if s.strip()]
    require(all(RETIRE.FULL_ID.fullmatch(value) for value in values), "DOCKER_INVENTORY_INVALID")
    require(not set(values) & set(RETIRE.EXPECTED.values()),
            "MAZINB_EXACT_CONTAINER_STILL_EXISTS")
    require(RETIRE.PROTECTED_ID in values, "PROTECTED_ORCAROUTER_PREDECESSOR_MISSING")
    if values:
        entries = json.loads(command("docker", "inspect", *values))
        require(isinstance(entries, list) and len(entries) == len(values),
                "DOCKER_INSPECT_INCOMPLETE")
        actual = {}
        for entry in entries:
            cid = entry.get("Id", "")
            require(cid in values and cid not in actual, "DOCKER_INSPECT_IDENTITY_INVALID")
            actual[cid] = entry
            name = str(entry.get("Name", "")).lstrip("/")
            labels = (entry.get("Config") or {}).get("Labels") or {}
            require(not name.startswith("qwen38-mazinb") and
                    labels.get("qwen38.abtrial") != "mazinb" and
                    labels.get("qwen38.profile") != "mazinb",
                    "UNEXPECTED_MAZINB_DOCKER_REMAINS:" + name)
        require(set(actual) == set(values), "DOCKER_INSPECT_INVENTORY_CHANGED")
        protected = actual[RETIRE.PROTECTED_ID]
        require(protected.get("Name") == "/" + RETIRE.PROTECTED_NAME,
                "PROTECTED_ORCAROUTER_NAME_CHANGED")
    command("docker", "image", "inspect", RETIRE.EXPECTED_IMAGE)
    print("MAZINB_AUDIT_DOCKER=EXACT_FIVE_ABSENT_NO_OTHER_MAZINB")
    print("MAZINB_AUDIT_PROTECTED_DOCKER=" + RETIRE.PROTECTED_ID)
    print("MAZINB_AUDIT_SHARED_VLLM_IMAGE=PRESENT_PRESERVED")


def unit_names(output: str) -> set[str]:
    names = set()
    for line in output.splitlines():
        columns = line.split()
        if columns and DEDICATED_UNIT.fullmatch(columns[0]):
            names.add(columns[0])
    return names


def systemd_scope(prefix: tuple[str, ...], description: str) -> set[str]:
    files = command("systemctl", *prefix, "list-unit-files", "--all", "--no-legend",
                    "--no-pager", "--plain")
    loaded = command("systemctl", *prefix, "list-units", "--all", "--no-legend",
                     "--no-pager", "--plain")
    found = unit_names(files) | unit_names(loaded)
    print(f"MAZINB_AUDIT_SYSTEMD_{description}_DEDICATED={','.join(sorted(found)) or 'ABSENT'}")
    return found


def systemd_check(home: Path) -> None:
    system_found = systemd_scope((), "SYSTEM")
    user_found = systemd_scope(("--user",), "USER")
    dirs = (
        Path("/etc/systemd/system"), Path("/run/systemd/system"),
        Path("/run/systemd/transient"), Path("/usr/lib/systemd/system"),
        Path("/lib/systemd/system"), Path("/etc/systemd/user"),
        Path("/usr/lib/systemd/user"), home / ".config/systemd/user",
    )
    found_files = []
    for root in dirs:
        if root.is_dir():
            for candidate in root.glob("*mazinb*"):
                if DEDICATED_UNIT.fullmatch(candidate.name):
                    found_files.append(str(candidate))
    require(not (system_found or user_found or found_files),
            "MAZINB_DEDICATED_SYSTEMD_UNIT_REMAINS:" +
            ",".join(sorted(system_found | user_found | set(found_files))))
    for unit in (UNIT, *SOCKET_PROXY):
        details = command("systemctl", "show", unit, "--property=LoadState,ActiveState,UnitFileState",
                          "--no-pager")
        props = dict(line.partition("=")[::2] for line in details.splitlines() if "=" in line)
        require("LoadState" in props and "ActiveState" in props,
                "SHARED_SYSTEMD_STATUS_INCOMPLETE:" + unit)
        if props["LoadState"] == "loaded":
            source = command("systemctl", "cat", unit, "--no-pager")
            lower = source.lower()
            require("mazinb" not in lower and
                    "18889" not in source and
                    "qwen3.8-flash-next-mazinb" not in lower,
                    "SHARED_UNIT_STILL_REFERENCES_MAZINB:" + unit)
        print(f"MAZINB_AUDIT_SHARED_UNIT={unit} load={props['LoadState']} active={props['ActiveState']} PRESERVE")
    print("MAZINB_AUDIT_SYSTEMD=NO_DEDICATED_MAZINB_UNIT_SYSTEM_OR_USER")


def sockets_check() -> None:
    output = command("ss", "-H", "-ltn")
    found: dict[int, list[str]] = {port: [] for port in (M1_PORT, *SHARED_PORTS)}
    for line in output.splitlines():
        cols = line.split()
        require(len(cols) >= 4, "SS_LISTENER_OUTPUT_INVALID")
        local = cols[3]
        port_text = local.rsplit(":", 1)[-1]
        if port_text.isdecimal() and int(port_text) in found:
            found[int(port_text)].append(local)
    require(not found[M1_PORT], "MAZINB_M1_PORT_18889_STILL_LISTENING:" +
            ",".join(found[M1_PORT]))
    print("MAZINB_AUDIT_M1_PORT_18889=NO_LISTENER")
    for port in SHARED_PORTS:
        print(f"MAZINB_AUDIT_SHARED_PORT_{port}=" +
              (",".join(found[port]) if found[port] else "NO_LISTENER") +
              "_NOT_A_MAZINB_DELETION_TARGET")


def processes_check() -> None:
    output = command("ps", "-eo", "pid=,args=")
    for line in output.splitlines():
        _, _, argv = line.strip().partition(" ")
        if (re.search(r"(?:^|\s)mazinb-m1\.py\s+run(?:\s|$)", argv)
                or re.search(r"(?:^|\s)mazinb-kv-ab\.sh\s+(?:start|run)(?:\s|$)", argv)
                or ("monitor-runtime.sh" in argv and
                    any(cid in argv for cid in RETIRE.EXPECTED.values()))
                or "qwen3.8-flash-next-mazinb" in argv):
            raise AuditBlocked("MAZINB_RELATED_HOST_PROCESS_REMAINS")
    print("MAZINB_AUDIT_HOST_PROCESSES=NO_KNOWN_MAZINB_WORKER_OR_WATCHDOG")


def inspect(home: Path, state: Path) -> None:
    manifest = state / "install.env"
    require(strict_file(manifest), "MANAGED_INSTALL_MANIFEST_MISSING")
    data = parse_install(manifest, "install-maintenance")
    require(data.get("PHASE") == "complete"
            and data.get("MODEL_PROFILE") in ("orcarouter", "orcarouter-hybrid"),
            "MANAGED_PROFILE_NOT_PROVEN_NON_MAZINB")
    model = Path(data.get("MODEL_DIR") or "")
    require(model.is_absolute() and model.is_dir(), "ACTIVE_CHECKPOINT_MISSING")
    root = model.parent
    archive_check(home, root, state)
    docker_check()
    systemd_check(home)
    sockets_check()
    processes_check()
    print("MAZINB_RETIREMENT_AUDIT=PASS_READ_ONLY_DEDICATED_ARTIFACTS_ABSENT")
    print("MAZINB_RETIREMENT_SHARED_RUNTIME_AND_PROXY=REPORTED_NOT_DELETED")
    print("MAZINB_RETIREMENT_HOST_MUTATION=NONE")


def main() -> int:
    if len(sys.argv) != 1:
        print("Usage: verify-mazinb-retirement.py (read-only)", file=sys.stderr)
        return 2
    home = Path.home()
    state = Path(os.environ.get("XDG_STATE_HOME", str(home / ".local/state"))) / "qwen38-spark"
    try:
        inspect(home, state)
    except (AuditBlocked, RETIRE.Blocked, OSError, ValueError, KeyError,
            subprocess.SubprocessError, json.JSONDecodeError) as err:
        print("MAZINB_RETIREMENT_AUDIT=BLOCKED_OR_INCONCLUSIVE", file=sys.stderr)
        print("MAZINB_RETIREMENT_AUDIT_REASON=" + str(err)[:440], file=sys.stderr)
        print("MAZINB_RETIREMENT_HOST_MUTATION=NONE", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
