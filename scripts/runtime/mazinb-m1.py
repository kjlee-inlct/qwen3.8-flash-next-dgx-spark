#!/usr/bin/env python3
"""Wizard-owned, foreground supervised mazinb M1 session.

A new unique Docker object is CREATEd first; an exact-ID, detached,
bounded, fail-closed memory watchdog is armed BEFORE Docker START.
This controller never deletes containers/experiments or mutates the
installed OrcaRouter predecessor. The interactive session owns a shared
lifecycle lock continuously; a separate benchmark may acquire a shared
lock, but lifecycle writers require an exclusive lock.

This is source implementation: passing source CI is not a DGX live gate.
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

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise M1Error("benchmark API redirect forbidden")


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from state_file import parse_install  # noqa: E402

OLD = "qwen38-flash-next"
SERVICE = "qwen38-flash-next.service"
IMAGE = "vllm-orcarouter-v029:v1"
PROFILE = "mazinb"
MODEL = "mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4"
KV_BYTES = "17179869184"
PORT = 18889
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
NAME_RE = re.compile(r"qwen38-mazinb-m1-[0-9]{14}-[a-f0-9]{8}\Z")
MARKERS = (
    "runtime-transition.env", "update-transition.env", "profile-switch-transition.env",
    "release-profile-refresh-transition.env", "settings-transition.phase",
    "runtime-adopt.env",
)
MAX_SESSION_SECONDS = 5400
MAX_WATCHDOG_SECONDS = 7200
STARTUP_SECONDS = 1800
SOAK_SECONDS = 180


class M1Error(Exception):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise M1Error(message)


def call(*args: str, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, check=False, text=True, capture_output=True, env=env)
    if check and result.returncode:
        raise M1Error(f"command failed: {args[0]} {args[1] if len(args) > 1 else ''}; rc={result.returncode}; {result.stderr[-300:]}")
    return result


def inspect(name: str) -> dict | None:
    p = call("docker", "inspect", "--format", "{{json .}}", name, check=False)
    return json.loads(p.stdout) if p.returncode == 0 else None


def state_paths() -> tuple[Path, Path, Path]:
    root = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "qwen38-spark"
    data = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "qwen38-spark"
    return root, data, root / "mazinb-m1"


def safe_dir(path: Path) -> None:
    require(path.is_dir() and not path.is_symlink() and path.stat().st_uid == os.getuid(),
            f"unsafe or wrongly-owned directory: {path}")


@contextmanager
def operation_lock(state: Path):
    safe_dir(state)
    lock = state / "operation.lock"
    require(lock.is_file() and not lock.is_symlink() and lock.stat().st_uid == os.getuid(),
            "existing owner-controlled operation lock required")
    with lock.open("rb") as fd:
        try:
            fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        except BlockingIOError as err:
            raise M1Error("lifecycle transaction currently holds operation lock") from err
        yield


def read_manifest(state: Path) -> tuple[dict, str]:
    path = state / "install.env"
    require(path.is_file() and not path.is_symlink(), "unsafe install manifest")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = parse_install(path, "install-maintenance")
    require(manifest.get("PHASE") == "complete" and manifest.get("MODEL_PROFILE") == "orcarouter",
            "expected completed managed OrcaRouter predecessor")
    require(manifest.get("MONITOR_ENABLED") == "1" and manifest.get("MONITOR_PROTECT") == "1",
            "managed memory protection must remain ON")
    require(manifest.get("SERVICE_ENABLED") == "1", "expected managed systemd installation")
    return manifest, digest


def snapshot_old(expected: str) -> dict:
    require(bool(HEX64.fullmatch(expected)), "full old Docker ID required")
    old = inspect(OLD)
    require(old is not None and old.get("Id") == expected, "protected predecessor exact Docker ID mismatch")
    s = old["State"]
    require(s["Status"] == "exited" and not s["Running"] and not s["OOMKilled"],
            "managed predecessor must be stopped, not Docker-OOM-killed")
    require(str(old.get("Image", "")).startswith("sha256:"), "old Docker immutable image ID missing")
    return old


def old_unchanged(previous: dict) -> None:
    now = inspect(OLD)
    require(now is not None, "protected predecessor missing")
    for path in (("Id",), ("Image",), ("State", "Status"), ("State", "Running"), ("State", "OOMKilled")):
        def get(item: dict) -> object:
            for key in path:
                item = item[key]
            return item
        require(get(now) == get(previous), f"predecessor drift: {path}")


def check_trial_history() -> None:
    for name in ("qwen38-mazinb-kv-a", "qwen38-mazinb-kv-b"):
        obj = inspect(name)
        if obj:
            require(obj["State"]["Status"] == "exited" and not obj["State"]["Running"],
                    f"historical case must be stopped: {name}")
    # Fail if any OTHER M1 instance is running; no new session while one is active.
    p = call("docker", "ps", "-aq", "--filter", "label=qwen38.abtrial=mazinb", check=True)
    for candidate_id in p.stdout.splitlines():
        c = inspect(candidate_id)
        if c and NAME_RE.fullmatch(str(c.get("Name", "")).lstrip("/")):
            require(not c["State"]["Running"], "prior M1 trial is still running")


def memory_admission(manifest: dict) -> None:
    """Fail closed on host/swap headroom before any GPU workload is created."""
    values: dict[str, int] = {}
    for row in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if ":" in row:
            key, _, value = row.partition(":")
            fields = value.split()
            if fields:
                values[key] = int(fields[0])
    for name in ("MemAvailable", "MemFree", "SwapFree"):
        require(name in values, f"missing /proc/meminfo field {name}")
    cma = values.get("CmaFree", 0)
    require(max(0, values["MemAvailable"] - cma) >= 6 * 1048576,
            "non-CMA available memory below 6 GiB")
    require(max(0, values["MemFree"] - cma) >= 2 * 1048576,
            "non-CMA free memory below 2 GiB")
    require(values["SwapFree"] >= 8 * 1048576, "SwapFree below 8 GiB")
    swaps = call("swapon", "--show=NAME", "--noheadings").stdout.split()
    require(manifest.get("SWAP_FILE") == "/swap-ple.img" and "/swap-ple.img" in swaps,
            "expected active managed PLE swap missing")


def preflight(expected: str, state: Path, data: Path, m1: Path) -> dict:
    safe_dir(state)
    safe_dir(data)
    for marker in MARKERS:
        require(not (state / marker).exists() and not (state / marker).is_symlink(),
                f"unfinished lifecycle marker: {marker}")
    manifest, digest = read_manifest(state)
    current = data / "current"
    require(current.is_symlink() and current.resolve().is_dir(), "current release missing")
    release = current.resolve()
    require(release.parent == data / "releases", "immutable release root mismatch")
    service = call("systemctl", "is-active", SERVICE, check=False).stdout.strip()
    require(service == "inactive", f"managed service is not proven inactive: {service}")
    old = snapshot_old(expected)
    memory_admission(manifest)
    check_trial_history()
    if m1.exists() or m1.is_symlink():
        safe_dir(m1)
        active = m1 / "active.json"
        if active.exists() or active.is_symlink():
            record = read_json(active)
            require(record.get("phase") in ("stopped", "failed_stopped"),
                    "unfinished M1 session exists: recovery required; no overwrite")
            prior = inspect(record["name"])
            require(prior is not None and prior["Id"] == record["id"] and
                    not prior["State"]["Running"],
                    "prior session identity requires recovery")
    model_path = Path(manifest["MODEL_DIR"]).resolve().parent / "qwen3.8-flash-next-mazinb"
    require(model_path.is_dir() and (model_path / "config.json").is_file()
            and (model_path / "model.safetensors.index.json").is_file(),
            "mazinb checkpoint files unavailable")
    image_id = call("docker", "image", "inspect", "--format", "{{.Id}}", IMAGE).stdout.strip()
    require(image_id.startswith("sha256:") and bool(HEX64.fullmatch(image_id[7:])),
            "pinned mazinb image digest missing")
    with socket.socket() as s:
        s.bind(("127.0.0.1", PORT))
    # Existing preflight checks dependency versions, managed state, lifecycle
    # idle, swap and sudo read-only evidence access. It never starts Docker.
    call("bash", str(ROOT / "scripts/runtime/mazinb-kv-ab.sh"), "preflight")
    old_unchanged(old)
    require(hashlib.sha256((state / "install.env").read_bytes()).hexdigest() == digest,
            "install manifest changed in preflight")
    require(current.resolve() == release, "release changed in preflight")
    return {"old": old, "release": str(release), "manifest_sha256": digest,
            "image_id": image_id, "model_path": str(model_path),
            "monitor": manifest}


def read_json(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink(), f"unsafe JSON record: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(data, dict), "invalid JSON record")
    return data


def save_json(path: Path, record: dict) -> None:
    safe_dir(path.parent)
    require(not path.is_symlink(), f"symlink record: {path}")
    tmp = path.with_suffix(path.suffix + ".tmp")
    require(not tmp.exists() and not tmp.is_symlink(), f"pending state transaction: {tmp}")
    with tmp.open("x", encoding="utf-8") as f:
        os.chmod(tmp, 0o600)
        json.dump(record, f, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def journal(m1: Path, record: dict, phase: str, detail: str = "") -> None:
    record["phase"] = phase
    record["updated_at"] = datetime.now(timezone.utc).isoformat()
    record["detail"] = detail
    save_json(m1 / "active.json", record)
    save_json(m1 / (record["name"] + ".json"), record)


def pinned_candidate(record: dict) -> dict:
    name, candidate_id = record["name"], record["id"]
    require(bool(NAME_RE.fullmatch(name)) and bool(HEX64.fullmatch(candidate_id)),
            "invalid M1 trial identity")
    d = inspect(name)
    require(d is not None and d.get("Id") == candidate_id, "candidate exact Docker ID drift")
    labels = d["Config"].get("Labels") or {}
    require(labels.get("qwen38.abtrial") == "mazinb"
            and labels.get("qwen38.variant") == "m1"
            and labels.get("qwen38.predecessor") == record["old_id"],
            "candidate provenance labels differ")
    require(d.get("Image") == record["image_id"], "candidate immutable image changed")
    require(d.get("HostConfig", {}).get("RestartPolicy", {}).get("Name") == "no",
            "candidate restart policy must be no")
    return d


def watch_fresh(monitor: subprocess.Popen, monitor_dir: Path, candidate_id: str) -> None:
    require(monitor.poll() is None, "pinned watchdog exited")
    armed = monitor_dir / "armed"
    heartbeat = monitor_dir / "heartbeat"
    require(armed.is_file() and not armed.is_symlink()
            and armed.read_text(encoding="utf-8").strip() == candidate_id,
            "watchdog exact-ID arm lost")
    require(heartbeat.is_file() and not heartbeat.is_symlink(), "watchdog heartbeat absent")
    ts = int(heartbeat.read_text(encoding="utf-8").strip())
    require(0 <= time.time() - ts <= 15, "watchdog heartbeat stale")


def api_healthy() -> bool:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(f"http://127.0.0.1:{PORT}/health", timeout=3) as resp:
            if resp.status != 200:
                return False
        with opener.open(f"http://127.0.0.1:{PORT}/v1/models", timeout=3) as resp:
            body = json.load(resp)
        return [item.get("id") for item in body.get("data", [])] == [MODEL]
    except (OSError, ValueError, KeyError):
        return False


def inference_smoke() -> None:
    """One supervised OpenAI-compatible inference, without saving model text."""
    payload = json.dumps({
        "model": MODEL, "messages": [
            {"role": "user", "content": "Reply briefly with the word OK."}
        ], "temperature": 0.0, "max_tokens": 64,
        "stream": False,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{PORT}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
    try:
        with opener.open(req, timeout=120) as resp:
            require(resp.status == 200, "M1 smoke HTTP status not 200")
            result = json.load(resp)
    except (OSError, ValueError, KeyError) as exc:
        raise M1Error(f"M1 inference smoke request failed: {type(exc).__name__}") from exc
    choices = result.get("choices")
    require(isinstance(choices, list) and len(choices) == 1, "M1 smoke invalid completion envelope")
    msg = choices[0].get("message", {})
    require(isinstance(msg, dict) and isinstance(msg.get("content"), str)
            and bool(msg["content"].strip()), "M1 smoke produced no assistant text")
    print("M1_INFERENCE_SMOKE=PASS_NO_GENERATED_TEXT_PERSISTED", flush=True)


def kernel_rm_since(utc_start: str) -> str:
    r = call("sudo", "-n", "journalctl", "-k", "--since", utc_start,
             "--no-pager", check=True)
    return "\n".join(line for line in r.stdout.splitlines()
                     if "NV_ERR_NO_MEMORY" in line or "_memdescAllocInternal" in line)


def verify_host(record: dict, snap: dict, state: Path, data: Path) -> None:
    old_unchanged(snap["old"])
    require(hashlib.sha256((state / "install.env").read_bytes()).hexdigest()
            == snap["manifest_sha256"], "manifest drift")
    require((data / "current").resolve().as_posix() == snap["release"], "release drift")
    require(call("systemctl", "is-active", SERVICE, check=False).stdout.strip() == "inactive",
            "managed service became active")
    require(not (Path(record["monitor_dir"]) / "runtime-stop.env").exists(),
            "candidate triggered memory-protection stop")
    require(not kernel_rm_since(record["kernel_since"]), "NVIDIA RM memory allocation error")


def stop_exact(record: dict, m1: Path) -> None:
    candidate = pinned_candidate(record)
    if candidate["State"]["Running"]:
        journal(m1, record, "stopping", "operator end or protective error")
        call("docker", "stop", "--timeout", "30", candidate["Id"])
    final = pinned_candidate(record)
    require(not final["State"]["Running"], "candidate did not stop")
    record["exit_code"] = final["State"].get("ExitCode")
    phase = "failed_stopped" if record["phase"] == "failed" else "stopped"
    journal(m1, record, phase, "Docker object and forensic files preserved")
    print(f"M1_STOPPED_EXACT_ID={record['id']}")
    print("M1_DOCKER_REMOVED=NO")


def run_session(expected: str) -> None:
    require(os.environ.get("QWEN38_M1_WIZARD_APPROVED") == "1",
            "live M1 requires Wizard default-NO operator approval")
    require(sys.stdin.isatty(), "live M1 must run interactively in foreground terminal")
    def signal_abort(signum: int, frame) -> None:
        raise M1Error(f"foreground M1 interrupted by signal {signum}")
    for sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, signal_abort)
    state, data, m1 = state_paths()
    with operation_lock(state):
        snap = preflight(expected, state, data, m1)
        if not m1.exists():
            m1.mkdir(mode=0o700)
        safe_dir(m1)
        bench_lock = m1 / "benchmark.lock"
        require(not bench_lock.is_symlink(), "unsafe M1 benchmark lock")
        if not bench_lock.exists():
            with bench_lock.open("x", encoding="utf-8"):
                os.chmod(bench_lock, 0o600)
        require(bench_lock.is_file() and bench_lock.stat().st_uid == os.getuid(),
                "unsafe M1 benchmark lock owner")
        now = datetime.now(timezone.utc)
        name = "qwen38-mazinb-m1-" + now.strftime("%Y%m%d%H%M%S") + "-" + secrets.token_hex(4)
        trial_dir = m1 / name
        trial_dir.mkdir(mode=0o700)
        monitor_dir = trial_dir / "monitor"
        monitor_dir.mkdir(mode=0o700)
        runner_state = trial_dir / "state"
        runner_state.mkdir(mode=0o700)
        record = {"schema": 1, "name": name, "id": "",
                  "old_id": expected, "old_image_id": snap["old"]["Image"],
                  "image_id": snap["image_id"], "release": snap["release"],
                  "manifest_sha256": snap["manifest_sha256"],
                  "model": MODEL, "port": PORT, "kv_bytes": KV_BYTES,
                  "monitor_dir": str(monitor_dir), "started_at": now.isoformat(),
                  "kernel_since": now.astimezone().strftime("%Y-%m-%d %H:%M:%S")}
        env = dict(os.environ)
        env.update({
            "MODEL_PROFILE": PROFILE, "MODEL_DIR": snap["model_path"],
            "SERVED_NAME": MODEL, "VLLM_IMAGE": IMAGE,
            "NAME": name, "PORT": str(PORT), "PUBLISH_HOST": "127.0.0.1",
            "RESTART_POLICY": "no", "MONITOR_ENABLED": "0", "MONITOR_PROTECT": "0",
            "TRIAL_CREATE_ONLY": "1", "TRIAL_VARIANT": "mazinb-m1",
            "TRIAL_PREDECESSOR_ID": expected, "XDG_STATE_HOME": str(runner_state),
            "KV_MEM": KV_BYTES, "GPU_UTIL": "0.80", "NSPEC": "2",
            "MAXLEN": "262144", "MAXSEQS": "3", "PREFIX_CACHE": "0",
            "INDEX_SHARE": "0", "AUTOTUNE": "0", "QSA_EXACT_TOPK": "1",
        })
        monitor = None
        try:
            call("bash", str(ROOT / "scripts/serve.sh"), env=env)
            created = inspect(name)
            require(created is not None and created["State"]["Status"] == "created"
                    and not created["State"]["Running"], "candidate was not only created")
            record["id"] = created["Id"]
            require(bool(HEX64.fullmatch(record["id"])), "created Docker ID invalid")
            journal(m1, record, "created")
            pinned_candidate(record)
            verify_host(record, snap, state, data)
            args = [
                "bash", str(ROOT / "scripts/runtime/monitor-runtime.sh"),
                "--container", name, "--expected-id", record["id"],
                "--wait-running", "120", "--trial-max-seconds", str(MAX_WATCHDOG_SECONDS),
                "--state-dir", str(monitor_dir),
                "--armed-file", str(monitor_dir / "armed"),
                "--heartbeat-file", str(monitor_dir / "heartbeat"),
                "--min-available-gib", snap["monitor"]["MONITOR_MIN_AVAILABLE_GIB"],
                "--min-free-gib", snap["monitor"]["MONITOR_MIN_FREE_GIB"],
                "--free-gate-gib", snap["monitor"]["MONITOR_FREE_GATE_GIB"],
                "--min-swap-free-gib", snap["monitor"]["MONITOR_MIN_SWAP_FREE_GIB"],
                "--consecutive", snap["monitor"]["MONITOR_CONSECUTIVE"],
                "--heartbeat", snap["monitor"]["MONITOR_HEARTBEAT"], "--protect",
            ]
            with (trial_dir / "monitor.log").open("a", encoding="utf-8") as output:
                monitor = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=output,
                                           stderr=subprocess.STDOUT, start_new_session=True, env=env)
            for _ in range(50):
                if monitor.poll() is not None:
                    raise M1Error("watchdog exited before exact-ID arm")
                if (monitor_dir / "armed").is_file() and (
                    monitor_dir / "armed").read_text().strip() == record["id"]:
                    break
                time.sleep(.1)
            else:
                raise M1Error("watchdog never armed: Docker not started")
            journal(m1, record, "armed")
            old_unchanged(snap["old"])
            call("docker", "start", record["id"])
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if (monitor_dir / "heartbeat").is_file():
                    break
                require(monitor.poll() is None, "watchdog exited during start")
                time.sleep(.2)
            watch_fresh(monitor, monitor_dir, record["id"])
            journal(m1, record, "started_unqualified")
            started = time.monotonic()
            print(f"M1_CANDIDATE_STARTED_UNQUALIFIED={name}", flush=True)
            while time.monotonic() - started < STARTUP_SECONDS:
                watch_fresh(monitor, monitor_dir, record["id"])
                require(pinned_candidate(record)["State"]["Running"], "candidate stopped before READY")
                verify_host(record, snap, state, data)
                if api_healthy():
                    journal(m1, record, "soaking")
                    break
                time.sleep(5)
            else:
                raise M1Error("candidate never reached exact-model API readiness")
            for _ in range(SOAK_SECONDS // 5):
                watch_fresh(monitor, monitor_dir, record["id"])
                require(pinned_candidate(record)["State"]["Running"], "candidate stopped during soak")
                verify_host(record, snap, state, data)
                time.sleep(5)
            verify_host(record, snap, state, data)
            require(api_healthy(), "exact model API identity lost after soak")
            inference_smoke()
            watch_fresh(monitor, monitor_dir, record["id"])
            verify_host(record, snap, state, data)
            journal(m1, record, "ready_for_bench", "API, smoke, soak and RM/monitor checks passed")
            print(f"M1_READY_FOR_BENCH=http://127.0.0.1:{PORT}", flush=True)
            print(f"M1_SERVED_NAME={MODEL}", flush=True)
            print(f"M1_EXACT_CONTAINER_ID={record['id']}", flush=True)
            print(f"M1_TRIAL_RECORD={m1 / 'active.json'}", flush=True)
            print("M1_LLAMA_BENCHY=NOT_MEASURED; run pinned benchmark in Terminal B", flush=True)
            print("Type STOP and Enter in this Wizard terminal to stop exact M1 candidate.", flush=True)
            while time.monotonic() - started < MAX_SESSION_SECONDS:
                watch_fresh(monitor, monitor_dir, record["id"])
                require(pinned_candidate(record)["State"]["Running"], "candidate stopped during benchmark window")
                verify_host(record, snap, state, data)
                ready, _, _ = select.select([sys.stdin], [], [], 5)
                if ready:
                    response = sys.stdin.readline()
                    require(response != "", "terminal input stream closed")
                    if response.strip().upper() == "STOP":
                        with bench_lock.open("rb") as bench_fd:
                            try:
                                fcntl.flock(bench_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                            except BlockingIOError:
                                print("M1_STOP_DEFERRED=BENCHMARK_RUNNING; finish Terminal B first", flush=True)
                                continue
                        break
                    print("Enter STOP to finish this supervised session.", flush=True)
            else:
                print("M1_MAX_SESSION_REACHED=YES; stopping candidate", flush=True)
        except BaseException as err:
            if record["id"]:
                try:
                    journal(m1, record, "failed", f"{type(err).__name__}: {str(err)[:180]}")
                except Exception:
                    pass
            raise
        finally:
            if record["id"]:
                # Stop only the unique newly-created candidate, never old Docker.
                try:
                    stop_exact(record, m1)
                except (M1Error, OSError, ValueError) as stop_error:
                    print(f"M1_EXACT_STOP_FAILED={stop_error}", file=sys.stderr)
                    print("M1_MANUAL_INTERVENTION=REQUIRED; watchdog remains bounded/armed", file=sys.stderr)
                    raise M1Error(f"candidate exact-ID stop failed: {stop_error}") from stop_error


def status() -> None:
    state, _, m1 = state_paths()
    path = m1 / "active.json"
    if not path.exists() and not path.is_symlink():
        print("M1_SESSION=ABSENT")
        return
    record = read_json(path)
    candidate = pinned_candidate(record)
    print(f"M1_SESSION_PHASE={record['phase']}")
    print(f"M1_SESSION_NAME={record['name']}")
    print(f"M1_CONTAINER_ID={record['id']}")
    print(f"M1_RUNNING={candidate['State']['Running']}")
    print(f"M1_EXIT_CODE={candidate['State'].get('ExitCode')}")
    print(f"M1_STATE_DIR={m1}")
    print("M1_DOCKER_REMOVED=NO")


def bench_admission() -> None:
    """Read-only Terminal-B attestation; caller must itself hold shared flock."""
    state, data, m1 = state_paths()
    safe_dir(state)
    safe_dir(data)
    record = read_json(m1 / "active.json")
    require(record.get("phase") == "ready_for_bench", "M1 is not admitted for benchmark")
    require(record.get("model") == MODEL and record.get("kv_bytes") == KV_BYTES
            and record.get("port") == PORT, "M1 benchmark configuration drift")
    candidate = pinned_candidate(record)
    require(candidate["State"]["Running"], "M1 candidate is not running")
    monitor_dir = Path(record["monitor_dir"])
    safe_dir(monitor_dir)
    armed = monitor_dir / "armed"
    heartbeat = monitor_dir / "heartbeat"
    require(armed.is_file() and not armed.is_symlink()
            and armed.read_text().strip() == record["id"], "M1 pinned monitor arm missing")
    require(heartbeat.is_file() and not heartbeat.is_symlink(), "M1 monitor heartbeat absent")
    require(0 <= time.time() - int(heartbeat.read_text().strip()) <= 15,
            "M1 watchdog heartbeat stale")
    snap = {"old": snapshot_old(record["old_id"]), "release": record["release"],
            "manifest_sha256": record["manifest_sha256"]}
    verify_host(record, snap, state, data)
    require(api_healthy(), "M1 API not ready with exact mazinb model identity")
    print(f"M1_BENCH_ADMISSION=PASS_SESSION_PINNED_READ_ONLY")
    print(f"M1_BENCH_CONTAINER_ID={record['id']}")
    print(f"M1_BENCH_API=http://127.0.0.1:{PORT}")
    print("M1_BENCH_HOST_RM=NO_MATCHING_EVENTS_IN_CURRENT_WINDOW")


def main() -> int:
    parser = argparse.ArgumentParser(description="Internal Wizard mazinb M1 controller")
    parser.add_argument("action", choices=("plan", "status", "preflight", "run", "bench-admission"))
    parser.add_argument("--expected-old-id", default="")
    args = parser.parse_args()
    try:
        if args.action == "plan":
            print("M1_PLAN=NEW_ISOLATED_MAZINB_16G")
            print("M1_PORT=127.0.0.1:18889")
            print("M1_WATCHDOG=ARM_EXACT_ID_BEFORE_START")
            print("M1_SESSION_MAX_SECONDS=5400")
            print("M1_KEEP_OLD_AB_AND_MANAGED=YES")
            print("M1_START=ONLY_INTERACTIVE_WIZARD_OPT_IN")
            print("M1_BENCHMARK=NOT_MEASURED")
        elif args.action == "status":
            status()
        elif args.action == "bench-admission":
            bench_admission()
        elif args.action == "preflight":
            state, data, m1 = state_paths()
            with operation_lock(state):
                s = preflight(args.expected_old_id, state, data, m1)
            print("M1_PREFLIGHT=PASS_READ_ONLY")
            print(f"M1_OLD_DOCKER_ID={s['old']['Id']}")
            print(f"M1_IMMUTABLE_RELEASE={s['release']}")
            print(f"M1_IMAGE_ID={s['image_id']}")
            print("M1_CANDIDATE_START=NOT_PERFORMED")
        else:
            run_session(args.expected_old_id)
    except (M1Error, OSError, ValueError, KeyError, subprocess.SubprocessError) as err:
        print(f"M1_BLOCKED={err}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
