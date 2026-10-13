#!/usr/bin/env python3
"""Wizard-internal, exact-ID OrcaRouter A/B trial. No managed lifecycle mutations.

The Python CLI is not a user-facing entry point; install.sh is the approved
front door. Docker CREATE precedes a pinned, armed watchdog; only then START.
A trial container is NEVER removed automatically, including on failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from state_file import parse_install  # noqa: E402

ORCA_REPO = "orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4"
REVISION = "c1209bda15a6bbc4c68b585e93d40c0d85f50306"
IMAGES = {"legacy": "vllm-skinny-tp1:v1", "v029": "vllm-orcarouter-v029:v1"}
PORT = 18888
OLD_NAME = "qwen38-flash-next"
SERVICE = "qwen38-flash-next.service"
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
BLOCKED_MARKERS = (
    "runtime-transition.env", "profile-switch-transition.env",
    "update-transition.env", "release-profile-refresh-transition.env",
    "settings-transition.phase", "runtime-adopt.env",
)


class TrialError(Exception):
    pass


def require(ok: bool, why: str) -> None:
    if not ok:
        raise TrialError(why)


def call(*args: str, env: dict[str, str] | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    p = subprocess.run(args, env=env, text=True, capture_output=True, check=False)
    if check and p.returncode:
        raise TrialError(f"{args[0]} {args[1] if len(args) > 1 else ''} failed (rc={p.returncode}): {p.stderr[-500:]}")
    return p


def inspect(name: str) -> dict | None:
    p = call("docker", "inspect", "--format", "{{json .}}", name, check=False)
    if p.returncode:
        return None
    return json.loads(p.stdout)


def docker_id(name: str) -> str:
    data = inspect(name)
    require(data is not None, f"missing container: {name}")
    result = str(data["Id"])
    require(bool(HEX64.fullmatch(result)), "not an exact 64-character Docker ID")
    return result


def preserve(before: dict) -> None:
    now = inspect(OLD_NAME)
    require(now is not None, "original managed Docker object disappeared")
    for path in (("Id",), ("Image",), ("State", "Status"), ("State", "Running"), ("State", "OOMKilled")):
        def select(obj: dict) -> object:
            for part in path:
                obj = obj[part]
            return obj
        require(select(now) == select(before), f"protected Docker identity/status drift: {path}")


def host_state() -> tuple[Path, Path, Path]:
    state = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "qwen38-spark"
    data = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "qwen38-spark"
    return state, data, state / "ab-trial.json"


def safe_dir(path: Path, *, create: bool = False) -> None:
    if create:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(path.is_dir() and not path.is_symlink(), f"unsafe directory: {path}")
    require(path.stat().st_uid == os.getuid(), f"directory owner mismatch: {path}")


def read_manifest(path: Path) -> tuple[dict, str]:
    require(path.is_file() and not path.is_symlink(), f"unsafe or missing install manifest: {path}")
    raw = path.read_bytes()
    values = parse_install(path, "install-maintenance")
    require(values.get("PHASE") == "complete", "installed manifest must be complete")
    require(values.get("MODEL_PROFILE") == "orcarouter", "requires installed OrcaRouter")
    require(values.get("MODEL_REPO") == ORCA_REPO and values.get("MODEL_REVISION") == REVISION,
            "checkpoint repo/revision mismatch")
    require(values.get("MONITOR_ENABLED") == "1" and values.get("MONITOR_PROTECT") == "1",
            "refusing trial without enabled managed monitoring and protection")
    return values, hashlib.sha256(raw).hexdigest()


def read_json(path: Path) -> dict | None:
    if not path.exists() and not path.is_symlink():
        return None
    require(path.is_file() and not path.is_symlink(), f"trial state unsafe: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: dict) -> None:
    safe_dir(path.parent)
    require(not path.is_symlink(), f"unsafe state path: {path}")
    tmp = path.with_suffix(".json.tmp")
    require(not tmp.is_symlink(), "symlinked temporary state")
    fd = os.open(tmp, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(value, out, indent=2, sort_keys=True)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def lock_is_held() -> None:
    # The parent interactive install.sh acquired operation.lock before
    # calling this helper. Never allow a standalone mutation call to bypass it.
    require(os.environ.get("QWEN38_OPERATION_LOCK_HELD") == "1", "wizard lifecycle lock absent")
    require(os.environ.get("QWEN38_OPERATION_LOCK_OWNER_PID", "").isdigit(), "wizard lock owner absent")
    owner = int(os.environ["QWEN38_OPERATION_LOCK_OWNER_PID"])
    parent = os.getppid()
    for _ in range(32):
        if parent == owner:
            return
        if parent < 2:
            break
        try:
            status = Path(f"/proc/{parent}/status").read_text()
        except OSError:
            break
        match = re.search(r"^PPid:\s+(\d+)$", status, re.M)
        if not match:
            break
        parent = int(match.group(1))
    raise TrialError("wizard lock owner is not an ancestor of this helper")


def mem_admission() -> None:
    vals = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        if ":" in line:
            key, v = line.split(":", 1)
            vals[key] = int(v.split()[0])
    cma = vals.get("CmaFree", 0)
    noncma_available = max(0, vals["MemAvailable"] - cma)
    noncma_free = max(0, vals["MemFree"] - cma)
    require(noncma_available >= 6 * 1048576, f"non-CMA available < 6 GiB: {noncma_available // 1024} MiB")
    require(noncma_free >= 2 * 1048576, f"non-CMA free < 2 GiB: {noncma_free // 1024} MiB")
    require(vals["SwapFree"] >= 8 * 1048576, "swap free < 8 GiB")


def check_candidates(target_variant: str) -> None:
    for variant in IMAGES:
        data = inspect("qwen38-ab-" + variant)
        if data is None:
            continue
        require(variant != target_variant,
                f"target trial name already exists: qwen38-ab-{variant}; preserve evidence first")
        require(not data["State"]["Running"] and data["State"]["Status"] == "exited",
                f"another trial image is not cleanly stopped: qwen38-ab-{variant}")
        labels = data["Config"]["Labels"]
        require(labels.get("qwen38.abtrial") == "orcarouter"
                and labels.get("qwen38.variant") == variant,
                f"prior trial object has unknown provenance: qwen38-ab-{variant}")


def can_bind() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        s.bind(("127.0.0.1", PORT))


def admission(state: Path, data_home: Path, manifest: dict, expected_old_id: str,
              target_variant: str) -> tuple[dict, str]:
    require(bool(HEX64.fullmatch(expected_old_id)), "exact 64-digit old Docker ID required")
    for marker in BLOCKED_MARKERS:
        require(not (state / marker).exists() and not (state / marker).is_symlink(),
                f"unfinished lifecycle transaction: {marker}")
    current = data_home / "current"
    require(current.is_symlink() and current.resolve().is_dir(),
            "missing/invalid immutable current release")
    require(current.resolve().parent == data_home / "releases", "release current target escaped managed release root")
    require(call("systemctl", "is-active", "--quiet", SERVICE, check=False).returncode != 0,
            "managed service is active")
    require(manifest.get("SERVICE_ENABLED") == "1", "expected managed service installation")
    require(manifest.get("SWAP_FILE") == "/swap-ple.img", "unexpected PLE swap")
    require("/swap-ple.img" in call("swapon", "--show=NAME", "--noheadings").stdout.split(),
            "PLE swap is not active")
    old = inspect(OLD_NAME)
    require(old is not None and old["Id"] == expected_old_id, "original Docker ID mismatch")
    require(old["State"]["Status"] == "exited" and not old["State"]["Running"]
            and not old["State"]["OOMKilled"], "original managed Docker is not a clean stopped object")
    require(inspect("qwen38-orca-v029") is None, "unmanaged experimental OrcaRouter already exists")
    check_candidates(target_variant)
    can_bind()
    mem_admission()
    model_dir = Path(manifest["MODEL_DIR"])
    require(model_dir.is_dir() and (model_dir / "model.safetensors.index.json").is_file(),
            "OrcaRouter checkpoint unavailable")
    config = manifest.get("CONFIG_OVERRIDE", "")
    require(config and Path(config).is_file(), "persisted compatible OrcaRouter config missing")
    return old, str(current.resolve())


def image_identity(variant: str) -> str:
    p = call("docker", "image", "inspect", "--format", "{{.Id}}", IMAGES[variant])
    image_id = p.stdout.strip()
    require(image_id.startswith("sha256:") and bool(HEX64.fullmatch(image_id[7:])),
            "runtime image ID invalid")
    if variant == "v029":
        label = call("docker", "image", "inspect",
                     "--format", '{{ index .Config.Labels "qwen38.base" }}', IMAGES[variant]).stdout.strip()
        require(label == "v0.29-orcarouter", "v0.29 image base label mismatch")
    return image_id


def trial_record(*, variant: str, candidate: dict, old: dict, sha: str,
                 release: str, image_id: str, trial_dir: Path, phase: str) -> dict:
    return {
        "schema": 1, "variant": variant, "container": candidate["Id"],
        "name": "qwen38-ab-" + variant, "image": IMAGES[variant],
        "image_id": image_id, "old_id": old["Id"], "old_image_id": old["Image"],
        "manifest_sha256": sha, "release": release,
        "trial_dir": str(trial_dir), "phase": phase, "created_at": int(time.time()),
    }


def trial_identity(record: dict) -> dict:
    name = record.get("name", "")
    require(name in {"qwen38-ab-legacy", "qwen38-ab-v029"}, "trial name invalid")
    container = inspect(name)
    require(container is not None and container["Id"] == record["container"],
            "candidate exact Docker ID drift")
    labels = container["Config"]["Labels"]
    require(labels.get("qwen38.abtrial") == "orcarouter"
            and labels.get("qwen38.variant") == record["variant"]
            and labels.get("qwen38.predecessor") == record["old_id"],
            "candidate trial labels drift")
    require(container["Image"] == record["image_id"], "candidate image ID drift")
    return container


def start(args: argparse.Namespace) -> None:
    lock_is_held()
    variant = args.variant
    state, data_home, record_path = host_state()
    safe_dir(state)
    safe_dir(data_home)
    require(read_json(record_path) is None or read_json(record_path).get("phase") == "stopped",
            "another trial is recorded; stop it before a new start")
    manifest, digest = read_manifest(state / "install.env")
    old, release = admission(state, data_home, manifest, args.expected_old_id, variant)
    image_id = image_identity(variant)
    trial_dir = state / "ab-trials" / f"{variant}-{int(time.time())}"
    require(not trial_dir.exists(), "trial run directory already exists")
    safe_dir(trial_dir, create=True)
    monitor_state = trial_dir / "monitor"
    safe_dir(monitor_state, create=True)
    home = trial_dir / "home"
    safe_dir(home, create=True)
    name = "qwen38-ab-" + variant
    env = dict(os.environ)
    env.update({
        "HOME": str(home), "MODEL_PROFILE": "orcarouter",
        "MODEL_DIR": manifest["MODEL_DIR"], "SERVED_NAME": ORCA_REPO,
        "VLLM_IMAGE": IMAGES[variant], "CONFIG_OVERRIDE": manifest["CONFIG_OVERRIDE"],
        "NAME": name, "PORT": str(PORT), "PUBLISH_HOST": "127.0.0.1",
        "RESTART_POLICY": "no", "MONITOR_ENABLED": "0", "MONITOR_PROTECT": "0",
        "TRIAL_CREATE_ONLY": "1", "TRIAL_VARIANT": variant,
        "TRIAL_PREDECESSOR_ID": args.expected_old_id,
        "XDG_STATE_HOME": str(trial_dir / "state"),
        "KV_MEM": "17179869184", "GPU_UTIL": "0.80",
    })
    candidate_id = ""
    watcher: subprocess.Popen | None = None
    try:
        # Create does not schedule the GPU workload. Host and pinned old
        # identity are rechecked before Docker START.
        call("bash", str(ROOT / "scripts" / "serve.sh"), env=env)
        candidate = inspect(name)
        require(candidate is not None and candidate["State"]["Status"] == "created"
                and not candidate["State"]["Running"], "trial must be created, not running")
        candidate_id = candidate["Id"]
        require(candidate["Image"] == image_id, "created candidate image ID differs")
        record = trial_record(variant=variant, candidate=candidate, old=old,
                              sha=digest, release=release, image_id=image_id,
                              trial_dir=trial_dir, phase="created")
        trial_identity(record)
        write_json(record_path, record)
        write_json(trial_dir / "record.json", record)
        preserve(old)
        require(hashlib.sha256((state / "install.env").read_bytes()).hexdigest() == digest,
                "installed manifest changed before trial start")
        require((data_home / "current").resolve().as_posix() == release,
                "immutable release changed before trial start")

        armed = monitor_state / "armed"
        heartbeat = monitor_state / "heartbeat"
        log_path = trial_dir / "monitor.log"
        log = log_path.open("a", encoding="utf-8")
        watcher = subprocess.Popen(
            ["bash", str(ROOT / "scripts/runtime/monitor-runtime.sh"),
             "--container", name, "--expected-id", candidate_id,
             "--wait-running", "120", "--state-dir", str(monitor_state),
             "--armed-file", str(armed), "--heartbeat-file", str(heartbeat),
             "--min-available-gib", manifest["MONITOR_MIN_AVAILABLE_GIB"],
             "--min-free-gib", manifest["MONITOR_MIN_FREE_GIB"],
             "--free-gate-gib", manifest["MONITOR_FREE_GATE_GIB"],
             "--min-swap-free-gib", manifest["MONITOR_MIN_SWAP_FREE_GIB"],
             "--consecutive", manifest["MONITOR_CONSECUTIVE"],
             "--heartbeat", manifest["MONITOR_HEARTBEAT"], "--protect"],
            cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
        )
        log.close()
        for _ in range(40):
            if armed.is_file() and armed.read_text().strip() == candidate_id and watcher.poll() is None:
                break
            require(watcher.poll() is None, "pinned monitor failed before arm")
            time.sleep(0.1)
        else:
            raise TrialError("monitor was not armed before Docker start")
        preserve(old)
        call("docker", "start", candidate_id)
        for _ in range(45):
            if heartbeat.is_file() and heartbeat.read_text().strip().isdigit():
                break
            require(watcher.poll() is None, "monitor died while starting")
            time.sleep(0.2)
        else:
            raise TrialError("running monitor never wrote heartbeat")
        require(inspect(name)["State"]["Running"], "trial stopped during startup")
        record["phase"] = "started_unqualified"
        record["monitor_pid"] = watcher.pid
        write_json(record_path, record)
        write_json(trial_dir / "record.json", record)
        preserve(old)
        print("AB_TRIAL_STARTED=UNQUALIFIED")
        print(f"AB_TRIAL_VARIANT={variant}")
        print(f"AB_TRIAL_CONTAINER_ID={candidate_id}")
        print(f"AB_TRIAL_API=http://127.0.0.1:{PORT}")
        print(f"AB_TRIAL_MONITOR_LOG={log_path}")
        print("AB_TRIAL_HOST_RM_QUALIFICATION=NOT_PERFORMED")
        print("AB_TRIAL_BENCHMARK=BLOCKED_UNTIL_API_AND_HOST_QUALIFIED")
    except BaseException:
        # Never target managed predecessor. Stop ONLY the created exact
        # candidate ID, preserve the container and all forensic files.
        if candidate_id:
            snapshot = inspect(name)
            if snapshot is not None and snapshot["Id"] == candidate_id and snapshot["State"]["Running"]:
                call("docker", "stop", "--timeout", "30", candidate_id, check=False)
            rec = read_json(record_path)
            if rec and rec.get("container") == candidate_id:
                rec["phase"] = "failed_stopped"
                write_json(record_path, rec)
                write_json(trial_dir / "record.json", rec)
        if watcher and watcher.poll() is not None:
            print(f"AB_MONITOR_EXIT_CODE={watcher.returncode}", file=sys.stderr)
        raise


def stop() -> None:
    lock_is_held()
    state, data_home, record_path = host_state()
    record = read_json(record_path)
    require(record is not None, "no recorded A/B trial to stop")
    candidate = trial_identity(record)
    # Safety requires stop authorization by the candidate's pinned ID.
    if candidate["State"]["Running"]:
        call("docker", "stop", "--timeout", "30", candidate["Id"])
    require(not trial_identity(record)["State"]["Running"], "trial still running")
    record["phase"] = "stopped"
    write_json(record_path, record)
    write_json(Path(record["trial_dir"]) / "record.json", record)
    print(f"AB_TRIAL_STOPPED_EXACT_ID={candidate['Id']}")
    print("AB_TRIAL_DOCKER_REMOVED=NO")
    old = inspect(OLD_NAME)
    require(old is not None and old["Id"] == record["old_id"],
            "managed old Docker changed while trial was running")
    require((data_home / "current").resolve().as_posix() == record["release"],
            "immutable release changed while trial was running")
    require(hashlib.sha256((state / "install.env").read_bytes()).hexdigest()
            == record["manifest_sha256"], "install manifest changed during trial")


def status() -> None:
    state, _, record_path = host_state()
    record = read_json(record_path)
    if record is None:
        print("AB_TRIAL_STATUS=ABSENT")
        return
    candidate = trial_identity(record)
    print(f"AB_TRIAL_PHASE={record['phase']}")
    print(f"AB_TRIAL_VARIANT={record['variant']}")
    print(f"AB_TRIAL_CONTAINER_ID={candidate['Id']}")
    print(f"AB_TRIAL_RUNNING={candidate['State']['Running']}")
    print(f"AB_TRIAL_MONITOR_LOG={record['trial_dir']}/monitor.log")
    if candidate["State"]["Running"]:
        heartbeat = Path(record["trial_dir"]) / "monitor" / "heartbeat"
        fresh = heartbeat.is_file() and time.time() - int(heartbeat.read_text().strip()) <= 10
        print("AB_TRIAL_WATCHDOG=" + ("FRESH" if fresh else "STALE_STOP_TRIAL"))
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2) as response:
                print(f"AB_API_HEALTH_HTTP={response.status}")
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/v1/models", timeout=2) as response:
                models = json.load(response)
            names = [item.get("id") for item in models.get("data", [])]
            print("AB_API_MODEL_IDENTITY=" + ("MATCH" if ORCA_REPO in names else "MISMATCH"))
        except Exception as e:
            print(f"AB_API_NOT_READY={type(e).__name__}")
    print("AB_HOST_RM_STABILITY=REQUIRES_SEPARATE_PHYSICAL_QUALIFICATION")
    print("AB_BENCHMARK=NOT_MEASURED")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("plan", "status", "start", "stop"))
    parser.add_argument("--variant", choices=tuple(IMAGES))
    parser.add_argument("--expected-old-id")
    args = parser.parse_args()
    try:
        if args.action == "plan":
            print("AB_TRIAL_WIZARD_PLAN_ONLY=YES")
            print("AB_TRIAL_CREATE_AND_WATCHDOG=SEPARATE")
            print("AB_TRIAL_START=OPT_IN_EXACT_OLD_DOCKER_ID")
            print("AB_TRIAL_OLD_DOCKER_MUTATIONS=FORBIDDEN")
            print("AB_TRIAL_PORT=127.0.0.1:18888")
            print("AB_TRIAL_KV_CACHE_GIB=16")
            print("AB_TRIAL_BENCHMARK=NOT_MEASURED")
        elif args.action == "status":
            status()
        elif args.action == "start":
            require(args.variant in IMAGES, "start requires variant")
            require(bool(args.expected_old_id), "start requires exact old Docker ID")
            start(args)
        else:
            stop()
    except (TrialError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"AB_TRIAL_BLOCKED={exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
