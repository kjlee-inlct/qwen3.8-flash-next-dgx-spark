#!/usr/bin/env python3
"""Archive and retire five exact, stopped mazinb experiments, never prune.

An apply is called ONLY by the locked manage-models.sh Wizard flow.
All Docker images, volumes, benchmark artifacts and journals remain untouched.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid

EXPECTED = {
    "qwen38-mazinb-m1-20261013235416-edd777eb":
        "1ebe723a279171794d7753cdbc3726e8c0db052c7cac02ec3060b8fc23c2700d",
    "qwen38-mazinb-kv-b":
        "64a4dfacebc0369887742440b5f1a084420b4ca1dc65c4324de61be5d49a1be3",
    "qwen38-mazinb-m1-20261014013811-16ced779":
        "7af3966f3d0cae79f8277eaf9ad003fb04c1e15ea01f86574c2d8eeac396e7a1",
    "qwen38-mazinb-m1-20261014003622-035e91fd":
        "b47e01628492da3f49d5aca2b677ed66dabde08680ae690df700926a37c0d631",
    "qwen38-mazinb-kv-a":
        "e9107e3cbebecea9affe7e92dfaf13f711ebf84f8ed8e6e06b1ba16985c9e647",
}
EXPECTED_IMAGE = "vllm-orcarouter-v029:v1"
PROTECTED_NAME = "qwen38-flash-next"
PROTECTED_ID = "f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24"
TRIAL = "20261014T015805Z"
CHECKSUMS = {
    "smoke.json": "0e7f42ef99c91098572558bb909c589ae7c470b3cb60f32599e394553cf1fafd",
    "mazinb.json": "377f5b5745aa16d454269490db408376d5f18d0289e576df8cd5a92a986fc23e",
    "mazinb-report.md": "b3e8f2d88ddfdc6894a3ed3678769f95a115ab4b665a7b3eb31ced1991bb298a",
}
FULL_ID = re.compile(r"[0-9a-f]{64}\Z")
ROOT = Path(__file__).resolve().parents[2]
MAX_LOG_BYTES = 128 * 1024 * 1024


class Blocked(RuntimeError):
    pass


def require(test: bool, reason: str) -> None:
    if not test:
        raise Blocked(reason)


def is_regular(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def is_directory(path: Path) -> bool:
    try:
        return stat.S_ISDIR(path.lstat().st_mode)
    except OSError:
        return False


def digest(path: Path) -> str:
    require(is_regular(path), f"archive payload missing/symlinked: {path}")
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(block)
    return sha.hexdigest()


def evidence(home: Path, model_root: Path, state: Path) -> None:
    candidate = model_root / "qwen3.8-flash-next-mazinb"
    require(is_directory(model_root) and not candidate.exists() and not candidate.is_symlink(),
            "source checkpoint must be previously removed before retiring containers")
    report = ROOT / "docs/model-reports/mazinb.md"
    require(is_regular(report) and "**BENCHMARK_STATUS: MEASURED**" in
            report.read_text(encoding="utf-8"), "mazinb measured report is not present")
    archive = ROOT / "docs/model-reports/evidence/mazinb" / TRIAL
    original = home / "Workspace/llm/qwen38-m1-bench-results" / TRIAL
    require(is_directory(archive) and is_directory(original),
            "repo/archive or original DGX evidence missing")
    sha_file = archive / "SHA256SUMS"
    require(is_regular(sha_file), "archive SHA256SUMS missing")
    rows = sha_file.read_text(encoding="utf-8").splitlines()
    expected_rows = [f"{v}  {k}" for k, v in CHECKSUMS.items()]
    require(sorted(rows) == sorted(expected_rows), "portable SHA manifest mismatch")
    for name, sha in CHECKSUMS.items():
        for base in (archive, original):
            require(digest(base / name) == sha, f"benchmark evidence digest mismatch: {base}/{name}")
    journal = state / "mazinb-m1/active.json"
    require(is_regular(journal), "M1 journal missing or symlinked")
    record = json.loads(journal.read_text(encoding="utf-8"))
    require(isinstance(record, dict) and record.get("phase") == "stopped",
            "M1 journal not reconciled to stopped")
    require(record.get("id") == EXPECTED["qwen38-mazinb-m1-20261014013811-16ced779"],
            "M1 journal Docker identity changed")
    for stage in ("qwen3.8-hybrid-quant-layout", "qwen3.8-h4-orca-all",
                  "qwen3.8-h5-neutral-input-scale", "qwen3.8-h6-modelopt-w4a16"):
        require(is_directory(model_root / stage), f"hybrid dependency missing: {stage}")
    print("MAZINB_DOCKER_EVIDENCE=ORIGINAL_AND_REPOSITORY_SHA256_PASS")
    print("MAZINB_DOCKER_JOURNAL=STOPPED_EXACT_ID")
    print("MAZINB_DOCKER_HYBRID_STAGES=PRESERVED")


def docker(*args: str, timeout: int = 45) -> str:
    proc = subprocess.run(["docker", *args], text=True, capture_output=True,
                          check=False, timeout=timeout)
    require(proc.returncode == 0, f"docker {' '.join(args[:2])} failed: {proc.stderr[-300:]}")
    return proc.stdout


def inventory(candidate: Path) -> tuple[dict[str, dict], set[str]]:
    ids = set(line.strip() for line in docker("ps", "-aq", "--no-trunc").splitlines() if line.strip())
    require(all(FULL_ID.fullmatch(cid) for cid in ids), "invalid Docker inventory IDs")
    require(PROTECTED_ID in ids, "protected predecessor not found")
    require(set(EXPECTED.values()).issubset(ids),
            "an expected mazinb container is absent/replaced: needs manual review")
    data = json.loads(docker("inspect", *sorted(ids), timeout=60))
    require(isinstance(data, list) and len(data) == len(ids), "Docker inspect incomplete")
    entries = {}
    for item in data:
        cid = item.get("Id", "")
        require(cid in ids and cid not in entries, "Docker identity mismatch/duplicate")
        entries[cid] = item
    require(set(entries) == ids, "Docker inspect inventory changed during inspection")
    require(entries[PROTECTED_ID].get("Name") == "/" + PROTECTED_NAME,
            "protected predecessor name/ID mismatch")
    for name, cid in EXPECTED.items():
        obj = entries[cid]
        require(obj.get("Name") == "/" + name, f"mazinb container name/ID mismatch: {name}")
        state = obj.get("State") or {}
        require(state.get("Running") is False and state.get("Status") == "exited",
                f"not a confirmed exited container: {name}")
        require((obj.get("Config") or {}).get("Image") == EXPECTED_IMAGE,
                f"shared vLLM image tag changed: {name}")
        restart = (obj.get("HostConfig") or {}).get("RestartPolicy") or {}
        require(restart.get("Name") in (None, "", "no"),
                f"container has restart policy: {name}")
        mounts = obj.get("Mounts")
        require(isinstance(mounts, list), f"mount metadata missing: {name}")
        require(any(m.get("Source") == str(candidate) for m in mounts),
                f"source checkpoint mount does not match: {name}")
        require(not (obj.get("HostConfig") or {}).get("AutoRemove", False),
                f"container auto-removal enabled: {name}")
        print(f"MAZINB_DOCKER_EXACT_STOPPED={name} ID={cid}")
    for cid, obj in entries.items():
        name = str(obj.get("Name", "")).lstrip("/")
        if name.startswith("qwen38-"):
            require((obj.get("State") or {}).get("Running") is False,
                    f"another project container is running: {name}")
    docker("image", "inspect", EXPECTED_IMAGE)
    print("MAZINB_DOCKER_PROTECTED_PREDECESSOR=" + PROTECTED_ID)
    print("MAZINB_DOCKER_SHARED_IMAGE=PRESERVED:" + EXPECTED_IMAGE)
    return entries, ids


def safe_archive_parent(state: Path) -> Path:
    require(is_directory(state) and not state.is_symlink(), "unsafe managed state directory")
    root = state / "retirement-archives"
    if root.exists() or root.is_symlink():
        require(is_directory(root) and not root.is_symlink(), "unsafe retirement archive root")
        require(root.stat().st_uid == os.getuid() and root.stat().st_mode & 0o077 == 0,
                "retirement archive root must be private and owned by caller")
    else:
        root.mkdir(mode=0o700)
    return root


def write_bytes(path: Path, data: bytes) -> None:
    with path.open("xb") as out:
        os.fchmod(out.fileno(), 0o600)
        out.write(data)
        out.flush()
        os.fsync(out.fileno())


def capture_log(cid: str, path: Path) -> None:
    # Stream logs: never keep a multi-GB experiment log in RAM or silently truncate it.
    with path.open("xb") as file:
        os.fchmod(file.fileno(), 0o600)
        p = subprocess.Popen(["docker", "logs", "--timestamps", cid],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        try:
            amount = 0
            assert p.stdout is not None
            while block := p.stdout.read(1024 * 1024):
                amount += len(block)
                require(amount <= MAX_LOG_BYTES, f"Docker log exceeds {MAX_LOG_BYTES} bytes: {cid}")
                file.write(block)
            require(p.wait(timeout=45) == 0, f"Docker logs unavailable: {cid}")
            file.flush()
            os.fsync(file.fileno())
        except BaseException:
            if p.poll() is None:
                p.kill()
            p.wait()
            raise


def save_all_logs_and_metadata(state: Path, entries: dict[str, dict]) -> Path:
    root = safe_archive_parent(state)
    name = ("mazinb-docker-" +
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:10])
    folder = root / (".pending-" + name)
    final = root / name
    # Atomic publication: an incomplete archive is never presented as ready.
    folder.mkdir(mode=0o700)
    manifest = []
    for name, cid in EXPECTED.items():
        obj = entries[cid]
        meta = {
            "id": cid, "name": obj["Name"], "created": obj.get("Created"),
            "docker_image_tag": (obj.get("Config") or {}).get("Image"),
            "docker_image_id": obj.get("Image"),
            "state": obj.get("State"),
            "mounts": [{"type": m.get("Type"), "source": m.get("Source"),
                        "destination": m.get("Destination")}
                       for m in obj.get("Mounts", [])],
            "restart": (obj.get("HostConfig") or {}).get("RestartPolicy"),
        }
        tag = cid[:16]
        meta_file = folder / (tag + ".json")
        log_file = folder / (tag + ".log")
        write_bytes(meta_file, (json.dumps(meta, sort_keys=True, indent=2) + "\n").encode())
        capture_log(cid, log_file)
        for f in (meta_file, log_file):
            manifest.append(f"{digest(f)}  {f.name}\n")
    write_bytes(folder / "SHA256SUMS", "".join(manifest).encode())
    for row in manifest:
        expected_hash, name = row.strip().split("  ", 1)
        require(digest(folder / name) == expected_hash, "archive verification failed")
    folder.rename(final)
    print("MAZINB_DOCKER_ARCHIVED_PATH=" + str(final))
    print("MAZINB_DOCKER_ARCHIVE_SHA256=PASS_10_FILES")
    return final


def write_m1_retirement_marker(state: Path, archived: Path) -> None:
    """Preserve immutable journals, write a separate, pinned Docker tombstone."""
    directory = state / "mazinb-m1"
    require(is_directory(directory), "M1 journal directory missing")
    marker = directory / "retired-docker.json"
    require(not marker.exists() and not marker.is_symlink(), "M1 Docker tombstone already exists")
    sha_file = archived / "SHA256SUMS"
    require(is_regular(sha_file), "archive checksum manifest missing")
    record = json.loads((directory / "active.json").read_text(encoding="utf-8"))
    expected_name = "qwen38-mazinb-m1-20261014013811-16ced779"
    require(record.get("name") == expected_name and
            record.get("id") == EXPECTED[expected_name] and
            record.get("phase") == "stopped", "original M1 record changed")
    data = {
        "schema_version": 1,
        "id": record["id"],
        "name": record["name"],
        "archive_path": str(archived),
        "archive_sha256_manifest": digest(sha_file),
        "retired_at": datetime.now(timezone.utc).isoformat(),
        "state": "archived_docker_removed",
    }
    write_bytes(marker, (json.dumps(data, sort_keys=True, indent=2) + "\n").encode())
    print("MAZINB_DOCKER_M1_TOMBSTONE=" + str(marker))


def apply(home: Path, root: Path, state: Path) -> None:
    require(os.environ.get("QWEN38_OPERATION_LOCK_HELD") == "1" and
            os.environ.get("QWEN38_MAZINB_BENCH_LOCK_HELD") == "1",
            "apply must be invoked through locked lifecycle manager")
    candidate = root / "qwen3.8-flash-next-mazinb"
    evidence(home, root, state)
    before, before_ids = inventory(candidate)
    tombstone = state / "mazinb-m1/retired-docker.json"
    require(not tombstone.exists() and not tombstone.is_symlink(),
            "historical M1 Docker retirement marker already exists")
    free_before = shutil.disk_usage(root).free
    archived = save_all_logs_and_metadata(state, before)
    # Changes between evidence archival and deletion must fail closed.
    again, again_ids = inventory(candidate)
    require(before_ids == again_ids and all(
        before[cid].get("Id") == again[cid].get("Id") and
        before[cid].get("State") == again[cid].get("State")
        for cid in EXPECTED.values()), "Docker inventory/state changed before deletion")
    count = 0
    for name, cid in EXPECTED.items():
        # docker rm without -f or -v: never force-stop or delete volumes.
        docker("rm", cid)
        count += 1
        print(f"MAZINB_DOCKER_REMOVED={name} ID={cid}")
    after_ids = set(line.strip() for line in
                    docker("ps", "-aq", "--no-trunc").splitlines() if line.strip())
    require(after_ids == before_ids - set(EXPECTED.values()),
            "postcheck mismatch: Docker objects outside approved five changed")
    remaining = json.loads(docker("inspect", *sorted(after_ids), timeout=60))
    require(isinstance(remaining, list), "postcheck Docker inspect invalid")
    require(any(x.get("Id") == PROTECTED_ID and
                x.get("Name") == "/" + PROTECTED_NAME for x in remaining),
            "protected Docker predecessor changed")
    docker("image", "inspect", EXPECTED_IMAGE)
    evidence(home, root, state)
    write_m1_retirement_marker(state, archived)
    free_after = shutil.disk_usage(root).free
    print("MAZINB_DOCKER_REMOVED_COUNT=" + str(count))
    print("MAZINB_DOCKER_OBJECTS_OTHER_THAN_FIVE=UNCHANGED")
    print("MAZINB_DOCKER_FS_AVAILABLE_BEFORE_BYTES=" + str(free_before))
    print("MAZINB_DOCKER_FS_AVAILABLE_AFTER_BYTES=" + str(free_after))
    print("MAZINB_DOCKER_FS_AVAILABLE_DELTA_BYTES=" + str(free_after-free_before))
    print("MAZINB_DOCKER_ARCHIVE_PATH=" + str(archived))
    print("MAZINB_DOCKER_RETIRE_RESULT=REMOVED_FIVE_VERIFIED")


def main() -> int:
    if len(sys.argv) != 5 or sys.argv[1] not in ("plan", "apply"):
        print("Usage: retire-mazinb-containers.py plan|apply HOME MODEL_ROOT STATE_DIR",
              file=sys.stderr)
        return 2
    mode = sys.argv[1]
    home, root, state = map(Path, sys.argv[2:])
    try:
        require(all(p.is_absolute() for p in (home, root, state)), "absolute paths required")
        evidence(home, root, state)
        inventory(root / "qwen3.8-flash-next-mazinb")
        if mode == "plan":
            print("MAZINB_DOCKER_RETIRE_SCOPE=EXACT_FIVE_STOPPED_ONLY")
            print("MAZINB_DOCKER_RETIRE_LOGS=TO_BE_ARCHIVED_BEFORE_REMOVAL")
            print("MAZINB_DOCKER_RETIRE_PLAN=PASS_NO_MUTATION")
        else:
            apply(home, root, state)
    except (Blocked, ValueError, OSError, TimeoutError, subprocess.SubprocessError,
            json.JSONDecodeError) as exc:
        print(f"MAZINB_DOCKER_RETIRE=BLOCKED reason={str(exc)[:450]}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
