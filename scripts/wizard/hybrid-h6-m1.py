#!/usr/bin/env python3
"""Isolated supervised Hybrid H6 first-benchmark experiment.

Not physically qualified: host-free tests are not GPU acceptance.
Unique create-only Docker, exact-ID watchdog armed BEFORE start,
immutable predecessor and installed release preserved. STOP preserves
trial container and raw Docker logs. Never cleans a model or Docker.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import select
import signal
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/lib"))
from state_file import parse_install  # noqa: E402

OLD = "qwen38-flash-next"
NAME = re.compile(r"qwen38-hybrid-h6-m1-[0-9]{14}-[a-f0-9]{8}\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
PORT = 18890
MODEL = "orcarouter-hybrid/Qwen3.8-Flash-Next-Uncensored-NVFP4"
IMAGE = "vllm-orcarouter-v029:v1"
KV = "17179869184"
MAX_SESSION = 5400
MAX_WATCHDOG = 7200
STARTUP_SECONDS = 1800
SOAK_SECONDS = 180
MARKERS = ("runtime-transition.env", "update-transition.env",
           "profile-switch-transition.env", "release-profile-refresh-transition.env",
           "settings-transition.phase", "runtime-adopt.env")
TREES = ("qwen3.8-flash-next-orcarouter", "qwen3.8-hybrid-quant-layout",
         "qwen3.8-h4-orca-all", "qwen3.8-h5-neutral-input-scale",
         "qwen3.8-h6-modelopt-w4a16")


class GuardError(Exception):
    pass


def check(ok: bool, why: str) -> None:
    if not ok:
        raise GuardError(why)


def cmd(*args: str, env: dict[str, str] | None = None,
        check_rc: bool = True, timeout: int = 120) -> str:
    result = subprocess.run(args, text=True, capture_output=True,
                            check=False, env=env, timeout=timeout)
    if check_rc and result.returncode:
        raise GuardError("command_failed:" + str(args[0]) + ":" + str(result.returncode)
                         + ":" + result.stderr[-200:])
    return result.stdout.strip()


def inspect(name: str) -> dict | None:
    result = subprocess.run(("docker", "inspect", name), capture_output=True,
                            text=True, check=False, timeout=30)
    if result.returncode:
        return None
    items = json.loads(result.stdout)
    check(isinstance(items, list) and len(items) == 1, "docker_inspect_bad_shape")
    return items[0]


def state_roots() -> tuple[Path, Path, Path]:
    state = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "qwen38-spark"
    data = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "qwen38-spark"
    return state, data, state / "hybrid-h6-m1"


def trusted_dir(path: Path) -> None:
    check(path.is_dir() and not path.is_symlink() and path.stat().st_uid == os.getuid(),
          "untrusted_directory:" + str(path))


@contextmanager
def lifecycle_lock(state: Path):
    trusted_dir(state)
    lock = state / "operation.lock"
    check(lock.is_file() and not lock.is_symlink() and lock.stat().st_uid == os.getuid(),
          "protected_operation_lock_missing")
    with lock.open("rb") as fd:
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError as e:
            raise GuardError("lifecycle_operation_in_progress") from e
        yield


def old_snapshot(old_id: str) -> tuple[str, str]:
    check(bool(HEX64.fullmatch(old_id)), "full_predecessor_id_required")
    old = inspect(OLD)
    check(old is not None and old.get("Id") == old_id, "canonical_old_identity_drift")
    state = old.get("State", {})
    check(state.get("Status") == "exited" and state.get("Running") is False
          and state.get("OOMKilled") is False, "canonical_old_not_stopped_nonoom")
    image = old.get("Image", "")
    check(isinstance(image, str) and image.startswith("sha256:")
          and bool(HEX64.fullmatch(image[7:])), "canonical_old_image_not_attested")
    return old_id, image


def validate_record(record: dict) -> dict:
    name, container_id = record["name"], record["id"]
    check(bool(NAME.fullmatch(name)) and bool(HEX64.fullmatch(container_id)),
          "invalid_candidate_identity")
    obj = inspect(name)
    check(obj is not None and obj.get("Id") == container_id, "candidate_id_drift")
    labels = obj.get("Config", {}).get("Labels") or {}
    check(labels.get("qwen38.abtrial") == "hybrid"
          and labels.get("qwen38.variant") == "h6-m1"
          and labels.get("qwen38.predecessor") == record["old_id"],
          "candidate_labels_untrusted")
    check(obj.get("Image") == record["image_id"], "candidate_image_identity_drift")
    check(obj.get("HostConfig", {}).get("RestartPolicy", {}).get("Name") == "no",
          "candidate_restart_policy_not_no")
    ports = obj.get("HostConfig", {}).get("PortBindings") or {}
    binds = ports.get(str(PORT) + "/tcp") or []
    check(len(binds) == 1 and binds[0].get("HostIp") in ("127.0.0.1",)
          and binds[0].get("HostPort") == str(PORT), "candidate_port_not_loopback")
    return obj


def atomic_json(path: Path, data: dict) -> None:
    trusted_dir(path.parent)
    check(not path.is_symlink(), "record_symlink")
    tmp = path.with_suffix(path.suffix + ".tmp")
    check(not tmp.exists() and not tmp.is_symlink(), "unfinished_journal_write")
    with tmp.open("x", encoding="utf-8") as f:
        os.chmod(tmp, 0o600)
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def journal(root: Path, rec: dict, phase: str, detail: str = "") -> None:
    rec["phase"] = phase
    rec["detail"] = detail
    rec["updated_at"] = datetime.now(timezone.utc).isoformat()
    atomic_json(root / "active.json", rec)
    atomic_json(root / (rec["name"] + ".json"), rec)


def load_record(path: Path) -> dict:
    check(path.is_file() and not path.is_symlink(), "journal_missing_or_symlink")
    obj = json.loads(path.read_text(encoding="utf-8"))
    check(isinstance(obj, dict) and obj.get("schema") == 1, "journal_invalid")
    return obj


def host_snapshot(state: Path, data: Path, old_id: str) -> dict:
    manifest_path = state / "install.env"
    check(manifest_path.is_file() and not manifest_path.is_symlink(),
          "installed_manifest_invalid")
    digest = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    manifest = parse_install(manifest_path, "install-maintenance")
    check(manifest.get("PHASE") == "complete" and manifest.get("MODEL_PROFILE") == "orcarouter",
          "expected_completed_orcarouter_manifest")
    check(manifest.get("API_ACCESS_MODE") == "local"
          and manifest.get("SERVICE_ENABLED") == "0"
          and manifest.get("SERVICE_OWNED") == "0",
          "isolated_H6_requires_nonboot_local_idle_policy")
    check(manifest.get("MONITOR_ENABLED") == "1"
          and manifest.get("MONITOR_PROTECT") == "1"
          and int(manifest.get("MONITOR_HEARTBEAT", "0")) > 0,
          "managed_monitor_protection_heartbeat_required")
    for key in ("MONITOR_MIN_AVAILABLE_GIB", "MONITOR_MIN_FREE_GIB",
                "MONITOR_FREE_GATE_GIB", "MONITOR_MIN_SWAP_FREE_GIB",
                "MONITOR_CONSECUTIVE"):
        check(manifest.get(key, "").isdecimal() and int(manifest[key]) > 0,
              "invalid_protection_threshold:" + key)
    for marker in MARKERS:
        check(not (state / marker).exists() and not (state / marker).is_symlink(),
              "unfinished_lifecycle_marker:" + marker)
    current = data / "current"
    check(current.is_symlink() and current.resolve().is_dir()
          and current.resolve().parent == data / "releases",
          "immutable_release_invalid")
    check(cmd("systemctl", "is-active", "qwen38-flash-next.service",
              check_rc=False) == "inactive", "managed_service_not_inactive")
    old_snapshot(old_id)
    idle = cmd("python3", "-B", str(ROOT / "scripts/diagnostics/verify-managed-idle.py"))
    check("MANAGED_IDLE_AUDIT=PASS_NO_MANAGED_API_LISTENER_OR_BOOT_START" in idle,
          "managed_host_not_idle")
    name = manifest.get("MODEL_DIR", "")
    root = Path(name).parent
    check(root.is_absolute() and not root.is_symlink() and root.is_dir(),
          "installed_model_root_not_real")
    model_dirs = [root / name for name in TREES]
    for directory in model_dirs:
        check(directory.is_dir() and not directory.is_symlink(),
              "missing_hybrid_source_stage:" + directory.name)
    cmd("python3", "-B", str(ROOT / "scripts/model/validate-orcarouter-hybrid.py"),
        "--runtime-only", "--base-dir", str(model_dirs[0]), "--h3-dir", str(model_dirs[1]),
        "--h4-dir", str(model_dirs[2]), "--h5-dir", str(model_dirs[3]),
        "--model-dir", str(model_dirs[4]))
    image_id = cmd("docker", "image", "inspect", "--format", "{{.Id}}", IMAGE)
    check(image_id.startswith("sha256:") and bool(HEX64.fullmatch(image_id[7:])),
          "hybrid_v029_image_unavailable")
    check(manifest.get("SWAP_FILE") == "/swap-ple.img"
          and "/swap-ple.img" in cmd("swapon", "--show=NAME", "--noheadings").split(),
          "expected_managed_swap_not_active")
    memory = {}
    for row in Path("/proc/meminfo").read_text().splitlines():
        if ":" in row:
            key, val = row.split(":", 1)
            pieces = val.split()
            if pieces and pieces[0].isdigit():
                memory[key] = int(pieces[0])
    for key in ("MemAvailable", "MemFree", "SwapFree", "CmaFree"):
        check(key in memory, "unavailable_memory_counter:" + key)
    check(memory["MemAvailable"] - memory["CmaFree"] >= 12 * 1048576,
          "nonCMA_available_below_12GiB")
    check(memory["MemFree"] - memory["CmaFree"] >= 4 * 1048576,
          "nonCMA_free_below_4GiB")
    check(memory["SwapFree"] >= 16 * 1048576, "swapfree_below_16GiB")
    check(os.statvfs(str(root)).f_bavail * os.statvfs(str(root)).f_frsize
          >= 20 * (1024 ** 3), "disk_free_below_20GiB")
    if not cmd("sudo", "-n", "journalctl", "-k", "-n", "5", "--no-pager"):
        # journalctl succeeds with no lines on some fresh hosts; rc is checked.
        pass
    with socket.socket() as server:
        server.bind(("127.0.0.1", PORT))
    running = cmd("docker", "ps", "--format", "{{.Names}}").splitlines()
    check(not any(item.startswith("qwen38-") for item in running),
          "unexpected_running_qwen_container")
    check(hashlib.sha256(manifest_path.read_bytes()).hexdigest() == digest,
          "manifest_changed_during_snapshot")
    return {"manifest": manifest, "manifest_sha256": digest, "release": str(current.resolve()),
            "old_image": old_snapshot(old_id)[1], "image_id": image_id,
            "model_root": str(root), "model_dir": str(model_dirs[4])}


def still_safe(record: dict, snap: dict, state: Path, data: Path) -> None:
    check(old_snapshot(record["old_id"])[1] == snap["old_image"],
          "old_canonical_drift")
    check(hashlib.sha256((state / "install.env").read_bytes()).hexdigest()
          == snap["manifest_sha256"], "installed_manifest_drift")
    check(str((data / "current").resolve()) == snap["release"], "release_drift")
    check(cmd("systemctl", "is-active", "qwen38-flash-next.service",
              check_rc=False) == "inactive", "managed_service_became_active")
    check(not (Path(record["monitor_dir"]) / "runtime-stop.env").exists(),
          "memory_protection_stop_marker")
    for item in cmd("sudo", "-n", "journalctl", "-k", "--since",
                    record["kernel_since"], "--no-pager").splitlines():
        if "NV_ERR_NO_MEMORY" in item or "_memdescAllocInternal" in item:
            raise GuardError("nvidia_rm_no_memory_detected")


def fresh(monitor: subprocess.Popen, record: dict) -> None:
    check(monitor.poll() is None, "pinned_monitor_exited")
    state = Path(record["monitor_dir"])
    arm, hb = state / "armed", state / "heartbeat"
    check(arm.is_file() and not arm.is_symlink() and arm.read_text().strip() == record["id"],
          "pinned_monitor_arm_untrusted")
    check(hb.is_file() and not hb.is_symlink(), "pinned_monitor_heartbeat_absent")
    delta = time.time() - int(hb.read_text().strip())
    check(0 <= delta <= 15, "pinned_monitor_heartbeat_stale")


def api_ready() -> bool:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open("http://127.0.0.1:" + str(PORT) + "/health", timeout=3) as r:
            if r.status != 200:
                return False
        with opener.open("http://127.0.0.1:" + str(PORT) + "/v1/models", timeout=3) as r:
            models = json.load(r)
        return [item.get("id") for item in models.get("data", [])] == [MODEL]
    except (ValueError, KeyError, OSError):
        return False


def smoke() -> None:
    body = json.dumps({"model": MODEL,
                       "messages": [{"role": "user", "content": "Reply briefly with OK."}],
                       "temperature": 0.0, "max_tokens": 64, "stream": False}).encode()
    req = urllib.request.Request("http://127.0.0.1:" + str(PORT) + "/v1/chat/completions",
                                 data=body, headers={"Content-Type": "application/json"},
                                 method="POST")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=120) as resp:
        check(resp.status == 200, "h6_smoke_not_http200")
        response = json.load(resp)
    choices = response.get("choices")
    check(isinstance(choices, list) and len(choices) == 1
          and bool(str(choices[0].get("message", {}).get("content", "")).strip()),
          "h6_smoke_empty")
    print("H6_INFERENCE_SMOKE=PASS_TEXT_NOT_PERSISTED", flush=True)


def stop_exact(record: dict, root: Path, failed: bool) -> None:
    # A second Ctrl-C or SIGTERM must not interrupt exact-ID stop/journal.
    prior = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
    for sig in prior:
        signal.signal(sig, signal.SIG_IGN)
    try:
        stop_exact_critical(record, root, failed)
    finally:
        for sig, handler in prior.items():
            signal.signal(sig, handler)


def stop_exact_critical(record: dict, root: Path, failed: bool) -> None:
    candidate = validate_record(record)
    if candidate["State"]["Running"]:
        journal(root, record, "stopping", "exact candidate protected stop")
        cmd("docker", "stop", "--timeout", "30", record["id"])
    final = validate_record(record)
    check(final["State"]["Running"] is False, "exact_candidate_failed_to_stop")
    record["exit_code"] = final["State"].get("ExitCode")
    journal(root, record, "failed_stopped" if failed else "stopped",
            "Docker and all forensic data preserved")
    print("H6_EXACT_STOPPED_ID=" + record["id"], flush=True)


def preflight(old_id: str) -> dict:
    state, data, root = state_roots()
    trusted_dir(state)
    trusted_dir(data)
    check(not root.is_symlink(), "trial_root_is_symlink")
    if root.exists():
        trusted_dir(root)
        if (root / "active.json").exists() or (root / "active.json").is_symlink():
            rec = load_record(root / "active.json")
            check(rec.get("phase") in ("stopped", "failed_stopped"),
                  "prior_h6_session_not_terminal")
            check(validate_record(rec)["State"]["Running"] is False,
                  "prior_h6_candidate_running")
    with lifecycle_lock(state):
        snap = host_snapshot(state, data, old_id)
    return snap


def run_session(old_id: str) -> None:
    check(os.environ.get("QWEN38_H6_WIZARD_APPROVED") == "1",
          "wizard_approval_missing")
    check(sys.stdin.isatty(), "interactive_foreground_tty_required")
    state, data, root = state_roots()
    def handle_exit(signum: int, frame: object) -> None:
        raise GuardError("foreground_terminal_signal:" + str(signum))
    for sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, handle_exit)
    with lifecycle_lock(state):
        snap = host_snapshot(state, data, old_id)
        if not root.exists():
            root.mkdir(mode=0o700)
        trusted_dir(root)
        if (root / "active.json").exists():
            last = load_record(root / "active.json")
            check(last["phase"] in ("stopped", "failed_stopped")
                  and validate_record(last)["State"]["Running"] is False,
                  "prior_h6_session_unresolved")
        now = datetime.now(timezone.utc)
        name = "qwen38-hybrid-h6-m1-" + now.strftime("%Y%m%d%H%M%S") + "-" + secrets.token_hex(4)
        trial = root / name
        trial.mkdir(mode=0o700)
        home = trial / "home"
        home.mkdir(mode=0o700)
        runner = trial / "runner"
        runner.mkdir(mode=0o700)
        monitor_dir = trial / "monitor"
        monitor_dir.mkdir(mode=0o700)
        record = {"schema": 1, "name": name, "id": "",
                  "old_id": old_id, "old_image_id": snap["old_image"],
                  "image_id": snap["image_id"], "manifest_sha256": snap["manifest_sha256"],
                  "release": snap["release"], "model": MODEL, "port": PORT, "kv_bytes": KV,
                  "monitor_dir": str(monitor_dir), "trial_dir": str(trial),
                  "started_at": now.isoformat(),
                  "kernel_since": now.astimezone().strftime("%Y-%m-%d %H:%M:%S")}
        env = dict(os.environ)
        env.update({"HOME": str(home), "XDG_STATE_HOME": str(runner),
                    "MODEL_PROFILE": "orcarouter-hybrid", "MODEL_DIR": snap["model_dir"],
                    "QWEN38_MODEL_ROOT": snap["model_root"], "VLLM_IMAGE": IMAGE,
                    "SERVED_NAME": MODEL, "NAME": name, "PORT": str(PORT),
                    "PUBLISH_HOST": "127.0.0.1", "RESTART_POLICY": "no",
                    "MONITOR_ENABLED": "0", "MONITOR_PROTECT": "0",
                    "TRIAL_CREATE_ONLY": "1", "TRIAL_VARIANT": "hybrid-h6-m1",
                    "TRIAL_PREDECESSOR_ID": old_id,
                    "KV_MEM": KV, "GPU_UTIL": "0.80", "NSPEC": "2",
                    "MAXLEN": "262144", "MAXSEQS": "3", "PREFIX_CACHE": "0",
                    "INDEX_SHARE": "0", "AUTOTUNE": "0", "QSA_EXACT_TOPK": "1"})
        bench_lock = root / "benchmark.lock"
        check(not bench_lock.is_symlink(), "benchmark_lock_symlink")
        if not bench_lock.exists():
            with bench_lock.open("x", encoding="utf-8"):
                os.chmod(bench_lock, 0o600)
        check(bench_lock.is_file() and bench_lock.stat().st_uid == os.getuid(),
              "benchmark_lock_not_owned")
        mon: subprocess.Popen | None = None
        failed = True
        try:
            cmd("bash", str(ROOT / "scripts/serve.sh"), env=env)
            obj = inspect(name)
            check(obj is not None and obj["State"]["Status"] == "created"
                  and obj["State"]["Running"] is False, "candidate_not_created_only")
            record["id"] = obj["Id"]
            validate_record(record)
            journal(root, record, "created")
            still_safe(record, snap, state, data)
            mon_args = ["bash", str(ROOT / "scripts/runtime/monitor-runtime.sh"),
                        "--container", name, "--expected-id", record["id"],
                        "--wait-running", "120", "--trial-max-seconds", str(MAX_WATCHDOG),
                        "--state-dir", str(monitor_dir),
                        "--armed-file", str(monitor_dir / "armed"),
                        "--heartbeat-file", str(monitor_dir / "heartbeat"),
                        "--min-available-gib", snap["manifest"]["MONITOR_MIN_AVAILABLE_GIB"],
                        "--min-free-gib", snap["manifest"]["MONITOR_MIN_FREE_GIB"],
                        "--free-gate-gib", snap["manifest"]["MONITOR_FREE_GATE_GIB"],
                        "--min-swap-free-gib", snap["manifest"]["MONITOR_MIN_SWAP_FREE_GIB"],
                        "--consecutive", snap["manifest"]["MONITOR_CONSECUTIVE"],
                        "--heartbeat", snap["manifest"]["MONITOR_HEARTBEAT"], "--protect"]
            with (trial / "monitor.log").open("a", encoding="utf-8") as stream:
                mon = subprocess.Popen(mon_args, stdin=subprocess.DEVNULL,
                                       stdout=stream, stderr=subprocess.STDOUT,
                                       start_new_session=True, env=env)
            for _ in range(50):
                check(mon.poll() is None, "monitor_exited_before_arm")
                if (monitor_dir / "armed").is_file() and (
                        monitor_dir / "armed").read_text().strip() == record["id"]:
                    break
                time.sleep(0.1)
            else:
                raise GuardError("monitor_never_armed")
            journal(root, record, "armed")
            still_safe(record, snap, state, data)
            cmd("docker", "start", record["id"], timeout=90)
            for _ in range(75):
                check(mon.poll() is None, "monitor_died_at_start")
                if (monitor_dir / "heartbeat").is_file():
                    break
                time.sleep(0.2)
            fresh(mon, record)
            journal(root, record, "started_unqualified")
            since = time.monotonic()
            print("H6_CANDIDATE_STARTED_UNQUALIFIED=" + name, flush=True)
            while time.monotonic() - since < STARTUP_SECONDS:
                fresh(mon, record)
                check(validate_record(record)["State"]["Running"], "candidate_exited_before_ready")
                still_safe(record, snap, state, data)
                if api_ready():
                    journal(root, record, "soaking")
                    break
                time.sleep(5)
            else:
                raise GuardError("h6_API_never_ready")
            for _ in range(SOAK_SECONDS // 5):
                fresh(mon, record)
                check(validate_record(record)["State"]["Running"], "candidate_exited_in_soak")
                still_safe(record, snap, state, data)
                time.sleep(5)
            smoke()
            fresh(mon, record)
            still_safe(record, snap, state, data)
            journal(root, record, "ready_for_bench")
            print("H6_READY_FOR_BENCH=http://127.0.0.1:" + str(PORT), flush=True)
            print("H6_SERVED_MODEL=" + MODEL, flush=True)
            print("H6_TRIAL_ID=" + record["id"], flush=True)
            print("H6_LLAMA_BENCHY=NOT_MEASURED", flush=True)
            print("Keep terminal A open; run admitted benchmark from terminal B.", flush=True)
            print("Type STOP to preserve and stop exact H6 candidate.", flush=True)
            while time.monotonic() - since < MAX_SESSION:
                fresh(mon, record)
                check(validate_record(record)["State"]["Running"], "trial_exited_unexpectedly")
                still_safe(record, snap, state, data)
                ready, _, _ = select.select([sys.stdin], [], [], 5)
                if ready and sys.stdin.readline().strip().upper() == "STOP":
                    with bench_lock.open("rb") as fd:
                        try:
                            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        except BlockingIOError:
                            print("H6_STOP_DEFERRED=BENCHMARK_RUNNING", flush=True)
                            continue
                    failed = False
                    break
            else:
                print("H6_MAX_SESSION_REACHED=YES", flush=True)
                failed = False
        except BaseException as exc:
            if record["id"]:
                try:
                    journal(root, record, "failed", type(exc).__name__ + ":" + str(exc)[:160])
                except Exception:
                    pass
            raise
        finally:
            if record["id"]:
                # Never remove candidate or historical containers on failure.
                stop_exact(record, root, failed)


def status() -> None:
    _, _, root = state_roots()
    record = root / "active.json"
    if not record.exists() and not record.is_symlink():
        print("H6_SESSION=ABSENT")
        return
    obj = load_record(record)
    candidate = validate_record(obj)
    print("H6_SESSION_PHASE=" + str(obj["phase"]))
    print("H6_SESSION_DOCKER_ID=" + obj["id"])
    print("H6_SESSION_RUNNING=" + str(candidate["State"]["Running"]))
    print("H6_SESSION_TRIAL_DIR=" + obj["trial_dir"])


def bench_admission() -> None:
    state, data, root = state_roots()
    trusted_dir(state)
    trusted_dir(data)
    trusted_dir(root)
    record = load_record(root / "active.json")
    check(record.get("phase") == "ready_for_bench" and record.get("model") == MODEL
          and record.get("port") == PORT and record.get("kv_bytes") == KV,
          "no_qualified_h6_bench_session")
    check(validate_record(record)["State"]["Running"] is True,
          "candidate_not_running")
    monitor = Path(record["monitor_dir"])
    trusted_dir(monitor)
    arm, heartbeat = monitor / "armed", monitor / "heartbeat"
    check(arm.is_file() and not arm.is_symlink() and arm.read_text().strip() == record["id"],
          "benchmark_watchdog_not_armed")
    check(heartbeat.is_file() and not heartbeat.is_symlink()
          and 0 <= time.time() - int(heartbeat.read_text().strip()) <= 15,
          "benchmark_watchdog_not_fresh")
    snap = {"old_image": record["old_image_id"],
            "manifest_sha256": record["manifest_sha256"],
            "release": record["release"]}
    still_safe(record, snap, state, data)
    check(api_ready(), "H6_API_not_READY")
    print("H6_BENCH_ADMISSION=PASS_EXACT_SESSION_PINNED_READ_ONLY")
    print("H6_BENCH_CONTAINER_ID=" + record["id"])
    print("H6_BENCH_API=http://127.0.0.1:" + str(PORT))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=("plan", "status", "preflight", "run", "bench-admission"))
    p.add_argument("--expected-old-id", default="")
    args = p.parse_args()
    try:
        if args.action == "plan":
            print("H6_PLAN=ISOLATED_16G_NO_BOOT")
            print("H6_EXPERIMENT_PORT=127.0.0.1:18890")
            print("H6_WATCHDOG=EXACT_ID_ARM_BEFORE_START")
            print("H6_PREDECESSOR=KEEP_UNCHANGED")
            print("H6_MAX_SESSION_SECONDS=" + str(MAX_SESSION))
            print("H6_BENCHMARK=NOT_MEASURED")
        elif args.action == "status":
            status()
        elif args.action == "bench-admission":
            bench_admission()
        elif args.action == "preflight":
            snap = preflight(args.expected_old_id)
            print("H6_PREFLIGHT=PASS_READ_ONLY")
            print("H6_OLD_DOCKER_ID=" + args.expected_old_id)
            print("H6_IMAGE_ID=" + snap["image_id"])
            print("H6_RELEASE=" + snap["release"])
            print("H6_CANDIDATE_START=NOT_PERFORMED")
        else:
            run_session(args.expected_old_id)
    except (GuardError, OSError, ValueError, KeyError, json.JSONDecodeError,
            subprocess.SubprocessError) as exc:
        print("H6_SESSION_BLOCKED=" + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
