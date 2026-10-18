#!/usr/bin/env python3
"""One-shot CPU-only OCI CLI metadata probe for official pinned peer C.

No GPU, network, model mounts, Docker image pull, serving, or host service work.
Only the newly created uniquely named *probe* is --rm'ed on its own exit.
The existing managed/A/B objects are read-only exact-ID protected.
Explicit owner approval: 2026-10-18, CPU-only CLI/package probe ONLY.
This tool is NOT a peer-C model trial launcher.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
READONLY = ROOT / "scripts/runtime/orcarouter-peer-c-readonly.py"
SPEC = importlib.util.spec_from_file_location("peer_c_readonly", READONLY)
assert SPEC is not None and SPEC.loader is not None
PEER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PEER)

BRANCH = "feature/wizard-modular-phase1-20261014"
PROBE_APPROVAL_ID = "cpu-cli-only-20261018"
OUTROOT = Path.home() / "orcarouter-bench-evidence"
# A *fixed* non-rotating receipt prevents repeating a one-time approval.
ONCE = OUTROOT / "peer-c-cli-approved-once-20261018.json"

# This script runs within the UNPRIVILEGED, offline, GPU-less container.
# No imported torch/vllm module is needed for package version metadata.
IN_CONTAINER = r'''
import base64
import hashlib
import importlib.metadata as md
import os
import re
import subprocess
import sys

print("PEER_C_CONTAINER_OPERATION=CLI_HELP_AND_DIST_METADATA_ONLY", flush=True)
print("PEER_C_CUDA_VISIBLE_DEVICES=" + os.environ.get("CUDA_VISIBLE_DEVICES", "UNSET"), flush=True)
print("PEER_C_NVIDIA_VISIBLE_DEVICES=" + os.environ.get("NVIDIA_VISIBLE_DEVICES", "UNSET"), flush=True)
for dist in ("vllm", "torch", "transformers", "flashinfer-python", "compressed-tensors"):
    try:
        version = md.version(dist)
    except md.PackageNotFoundError:
        version = "NOT_INSTALLED_OR_DIFFERENT_DISTRIBUTION_NAME"
    print("PEER_C_PACKAGE_" + dist.upper().replace("-", "_") + "=" + version, flush=True)

flags = (
    "--kv-cache-memory-bytes", "--kv-cache-memory", "--speculative-config",
    "--distributed-executor-backend", "--tensor-parallel-size",
    "--gpu-memory-utilization", "--max-model-len", "--max-num-seqs",
    "--no-enable-prefix-caching", "--no-async-scheduling",
    "--enable-chunked-prefill", "--no-enable-flashinfer-autotune",
    "--load-format", "--served-model-name", "--reasoning-parser",
    "--tool-call-parser", "--limit-mm-per-prompt",
)
try:
    p = subprocess.run(
        ["vllm", "serve", "--help=all"], capture_output=True, text=True,
        errors="replace", timeout=120, check=False)
except (OSError, subprocess.TimeoutExpired) as exc:
    print("PEER_C_CLI_HELP=FAILED_" + type(exc).__name__, flush=True)
    sys.exit(12)

combined = (p.stdout or "") + "\n" + (p.stderr or "")
print("PEER_C_HELP_EXIT_CODE=" + str(p.returncode), flush=True)
print("PEER_C_HELP_SHA256=" + hashlib.sha256(combined.encode()).hexdigest(), flush=True)
for flag in flags:
    pattern = r"(?<![A-Za-z0-9_-])" + re.escape(flag) + r"(?![A-Za-z0-9_-])"
    print("PEER_C_FLAG_" + flag[2:].upper().replace("-", "_") +
          "=" + ("NOT_EVALUATED_HELP_FAILED" if p.returncode != 0 else
                 ("PRESENT_IN_HELP" if re.search(pattern, combined)
                  else "NOT_FOUND_IN_HELP")),
          flush=True)
# Host decodes this into a separate preserved raw help file; don't flood chat.
print("PEER_C_HELP_BASE64=" + base64.b64encode(combined.encode()).decode(), flush=True)
if p.returncode != 0:
    print("PEER_C_CLI_HELP=FAILED", flush=True)
    sys.exit(13)
print("PEER_C_CLI_HELP=PASS_METADATA_ONLY_NO_MODEL", flush=True)
'''

class ProbeError(Exception):
    pass


def check(ok: bool, reason: str) -> None:
    if not ok:
        raise ProbeError(reason)


def query(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, text=True, capture_output=True, check=False, timeout=15)


def receipt() -> dict:
    data = {}
    for name in PEER.PROTECTED:
        obj = PEER.metadata(name, image=False)
        check(obj is not None, "cannot inspect protected " + name)
        data[name] = {
            "id": obj.get("Id"),
            "image": obj.get("Image"),
            "status": (obj.get("State") or {}).get("Status"),
            "running": (obj.get("State") or {}).get("Running"),
            "oom_killed": (obj.get("State") or {}).get("OOMKilled"),
        }
    return data


def preadmission() -> tuple[str, dict]:
    branch = query("git", "-C", str(ROOT), "branch", "--show-current")
    check(branch.returncode == 0 and branch.stdout.strip() == BRANCH,
          "unexpected source branch")
    clean = query("git", "-C", str(ROOT), "status", "--porcelain")
    check(clean.returncode == 0 and not clean.stdout.strip(),
          "dirty worktree; preserve local changes")
    sha = query("git", "-C", str(ROOT), "rev-parse", "HEAD")
    check(sha.returncode == 0 and len(sha.stdout.strip()) == 40,
          "invalid Git SHA")
    check(PEER.image_receipt() == "PINNED_MATCH",
          "exact pinned official image/config ID not verified")
    check(PEER.image_runtime_receipt() ==
          "ENTRYPOINT_SHAPE_MATCH_WHEEL_SOURCE_UNATTESTED",
          "official OCI runtime metadata mismatch")
    check(PEER.protected_receipt() == "THREE_STOPPED_EXISTING_IDS",
          "protected managed/A/B IDs or states changed")
    before = receipt()
    check(PEER.host_check() == 0, "host snapshot blocked")
    return sha.stdout.strip(), before


def docker_args(name: str) -> list[str]:
    # Security contract: exact pinned local image, no auto-pull, zero GPU
    # devices, network none, mountless/read-only container, restricted process
    # and memory budgets. Disposable NEW container only; never old A/B.
    return [
        "docker", "run", "--pull=never", "--rm", "--name", name,
        "--label", "qwen38.peer-c-cpu-cli-probe=20261018",
        "--platform", "linux/arm64", "--runtime", "runc",
        "--network", "none", "--read-only",
        "--tmpfs", "/tmp:rw,nosuid,nodev,size=256m",
        "--pids-limit", "128", "--cpus", "2", "--memory", "4g",
        "--memory-swap", "4g", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--user", "65534:65534",
        "--env", "NVIDIA_VISIBLE_DEVICES=void",
        "--env", "CUDA_VISIBLE_DEVICES=-1",
        "--env", "PYTHONDONTWRITEBYTECODE=1",
        "--env", "VLLM_NO_USAGE_STATS=1",
        "--env", "HF_HUB_OFFLINE=1",
        "--env", "TRANSFORMERS_OFFLINE=1",
        "--env", "HF_HUB_DISABLE_TELEMETRY=1",
        "--env", "HOME=/tmp",
        "--env", "XDG_CACHE_HOME=/tmp",
        "--env", "VLLM_CACHE_ROOT=/tmp/vllm",
        "--entrypoint", "python3", PEER.PINNED, "-c", IN_CONTAINER,
    ]


def recover_own_timeout(name: str) -> None:
    """Stop only our own unique, labeled probe after a host timeout."""
    obj = PEER.metadata(name, image=False)
    if obj is None:
        return
    check((obj.get("Config") or {}).get("Labels", {}).get(
          "qwen38.peer-c-cpu-cli-probe") == "20261018",
          "TIMEOUT probe name ownership mismatch; no stop attempted")
    check(obj.get("Image") == PEER.EXPECTED_IMAGE_ID,
          "TIMEOUT probe image ID mismatch; no stop attempted")
    cid = obj.get("Id")
    check(isinstance(cid, str) and len(cid) == 64 and
          cid not in [x[0] for x in PEER.PROTECTED_IDENTITIES.values()],
          "TIMEOUT candidate Docker ID invalid/protected")
    p = subprocess.run(["docker", "stop", "--time", "5", cid],
                       text=True, capture_output=True, check=False, timeout=15)
    check(p.returncode == 0, "TIMEOUT: only-new-probe stop failed")


def run_once() -> int:
    print("PEER_C_OWNER_APPROVAL=CPU_ONLY_CLI_HELP_ONCE_20261018", flush=True)
    sha, before = preadmission()
    check(not ONCE.exists() and not ONCE.is_symlink(),
          "one-time approval already consumed; further run requires new approval")
    OUTROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    check(OUTROOT.is_dir() and not OUTROOT.is_symlink(),
          "evidence root must not be a symlink")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    suffix = secrets.token_hex(4)
    name = "qwen38-peer-c-cpu-cli-" + stamp + "-" + suffix
    output = OUTROOT / ("peer-c-cli-" + stamp + "-" + suffix)
    output.mkdir(mode=0o700, exist_ok=False)
    absent = query("docker", "container", "inspect", name)
    check(absent.returncode != 0,
          "new unique probe container name already exists")
    argv = docker_args(name)
    check(not any(arg in argv for arg in
                  ("--gpus", "--device", "--mount", "-v", "-p", "--privileged")),
          "mutating GPU/mount/network option in probe")
    # Persist approval consumption before Docker creates any new object.
    record = {"operation": "one-time-cpu-cli-probe",
              "approved_scope": "NO_GPU_NO_MODEL_NO_NETWORK",
              "source_sha": sha, "name": name, "evidence": str(output)}
    fd = os.open(ONCE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as out:
        json.dump(record, out, indent=2)
    (output / "before-protected.json").write_text(
        json.dumps(before, indent=2), encoding="utf-8")
    (output / "docker-argv-summary.json").write_text(json.dumps({
        "image": PEER.PINNED, "image_config_id": PEER.EXPECTED_IMAGE_ID,
        "name": name, "entrypoint": "python3",
        "flags": argv[2:argv.index(PEER.PINNED)],
        "mode": "no-gpu,no-net,no-mount,read-only,4g-mem,2cpu,128pids",
    }, indent=2), encoding="utf-8")
    print("PEER_C_SOURCE_SHA=" + sha)
    print("PEER_C_PROBE_NAME=" + name)
    print("PEER_C_EVIDENCE_DIR=" + str(output))
    timeout = False
    try:
        result = subprocess.run(argv, text=True, capture_output=True,
                                check=False, timeout=180)
        raw = (result.stdout or "") + "\n" + (result.stderr or "")
        code = result.returncode
    except subprocess.TimeoutExpired as exc:
        timeout = True
        raw = (exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        raw += "\nTIMEOUT_HOST_180S\n"
        code = 124
        recover_own_timeout(name)
    (output / "raw.log").write_text(raw, encoding="utf-8")
    lines = raw.splitlines()
    for line in lines:
        if line.startswith("PEER_C_HELP_BASE64="):
            try:
                payload = base64.b64decode(line.split("=", 1)[1], validate=True)
                (output / "vllm-serve-help-all.txt").write_bytes(payload)
            except (ValueError, base64.binascii.Error):
                print("PEER_C_HELP_ARTIFACT=BASE64_INVALID")
        elif line.startswith("PEER_C_"):
            print(line)
    (output / "after-protected.json").write_text(
        json.dumps(receipt(), indent=2), encoding="utf-8")
    after = receipt()
    protected_same = after == before and PEER.protected_receipt() == "THREE_STOPPED_EXISTING_IDS"
    remaining = PEER.metadata(name, image=False)
    print("PEER_C_PROTECTED_AFTER=" + ("UNCHANGED" if protected_same else "DRIFT_BLOCKED"))
    print("PEER_C_DISPOSABLE_PROBE_REMOVED=" + ("YES" if remaining is None else "NO_INSPECT"))
    print("PEER_C_DOCKER_RUN_EXIT_CODE=" + str(code))
    checks = []
    for file in sorted(output.iterdir()):
        if file.is_file():
            checks.append(hashlib.sha256(file.read_bytes()).hexdigest() +
                          "  " + file.name)
    (output / "SHA256SUMS.txt").write_text("\n".join(checks) + "\n", encoding="utf-8")
    ok = (not timeout and code == 0 and protected_same and remaining is None
          and "PEER_C_CLI_HELP=PASS_METADATA_ONLY_NO_MODEL" in raw
          and (output / "vllm-serve-help-all.txt").is_file())
    print("PEER_C_CLI_PROBE=" + ("PASS_METADATA_ONLY" if ok else "FAILED_REVIEW"))
    return 0 if ok else 2



def saved_report() -> int:
    """Read the already-consumed probe's evidence, NEVER rerun Docker.

    The one-use authorization is not reissued by reading diagnostics.
    Print a bounded excerpt of the saved decoded CLI stdout/stderr.
    """
    print("PEER_C_OPERATION=OFFLINE_CLI_REPORT_NO_DOCKER")
    if (not ONCE.is_file() or ONCE.is_symlink() or
            not OUTROOT.is_dir() or OUTROOT.is_symlink()):
        print("PEER_C_SAVED_REPORT=NO_APPROVED_RECEIPT")
        return 2
    record = json.loads(ONCE.read_text(encoding="utf-8"))
    check(isinstance(record, dict), "malformed approval receipt")
    check(record.get("operation") == "one-time-cpu-cli-probe" and
          record.get("approved_scope") == "NO_GPU_NO_MODEL_NO_NETWORK",
          "not an approved CPU-only CLI receipt")
    name = record.get("name")
    directory = record.get("evidence")
    check(isinstance(name, str) and name.startswith("qwen38-peer-c-cpu-cli-") and
          isinstance(directory, str), "invalid saved probe identifiers")
    evidence = Path(directory)
    check(evidence.is_absolute() and evidence.parent == OUTROOT and
          evidence.name.startswith("peer-c-cli-") and
          evidence.is_dir() and not evidence.is_symlink() and
          evidence.resolve() == evidence, "invalid saved evidence path")
    help_file = evidence / "vllm-serve-help-all.txt"
    raw_file = evidence / "raw.log"
    check(help_file.is_file() and not help_file.is_symlink() and
          raw_file.is_file() and not raw_file.is_symlink(),
          "saved CLI log/help artifact missing")
    check(help_file.stat().st_size <= 8 * 1024 * 1024 and
          raw_file.stat().st_size <= 16 * 1024 * 1024,
          "unexpectedly large saved CLI evidence; inspect separately")
    help_text = help_file.read_text(encoding="utf-8", errors="replace")
    raw = raw_file.read_text(encoding="utf-8", errors="replace")
    print("PEER_C_REPORT_SOURCE_SHA=" + str(record.get("source_sha", "UNKNOWN")))
    print("PEER_C_REPORT_PROBE_NAME=" + name)
    print("PEER_C_REPORT_EVIDENCE_DIR=" + str(evidence))
    evidence_sha = hashlib.sha256(help_file.read_bytes()).hexdigest()
    print("PEER_C_REPORT_HELP_FILE_SHA256=" + evidence_sha)
    markers = (
        "PEER_C_PACKAGE_", "PEER_C_HELP_EXIT_CODE=",
        "PEER_C_HELP_SHA256=", "PEER_C_CLI_HELP=",
        "PEER_C_PROTECTED_AFTER=", "PEER_C_DISPOSABLE_PROBE_REMOVED=",
        "PEER_C_DOCKER_RUN_EXIT_CODE=",
    )
    for line in raw.splitlines():
        if line.startswith(markers):
            print(line[:500])
    help_failed = ("PEER_C_CLI_HELP=FAILED" in raw or
                   "PEER_C_HELP_EXIT_CODE=1" in raw)
    if help_failed:
        print("PEER_C_CLI_FLAGS=NOT_EVALUATED_HELP_FAILED")
    else:
        print("PEER_C_CLI_FLAGS=REVIEW_SAVED_SUCCESSFUL_HELP")
    before_path = evidence / "before-protected.json"
    after_path = evidence / "after-protected.json"
    if (before_path.is_file() and after_path.is_file() and
            not before_path.is_symlink() and not after_path.is_symlink()):
        before = json.loads(before_path.read_text(encoding="utf-8"))
        after = json.loads(after_path.read_text(encoding="utf-8"))
        print("PEER_C_SAVED_PROTECTED=" + ("UNCHANGED" if before == after
                                         else "DRIFT_IN_SAVED_RECORDS"))
    else:
        print("PEER_C_SAVED_PROTECTED=NOT_AVAILABLE")
    print("PEER_C_SAVED_CLI_ERROR_EXCERPT_BEGIN")
    # Bound printed output (not the underlying retained files).
    lines = help_text.splitlines()
    tail = lines[-70:]
    for line in tail:
        print(line[:400])
    print("PEER_C_SAVED_CLI_ERROR_EXCERPT_END")
    print("PEER_C_SAVED_REPORT=READ_ONLY_COMPLETE_NO_REPEAT")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("plan", "run", "report"))
    parser.add_argument("--approved-cpu-only", action="store_true")
    args = parser.parse_args()
    if args.action == "plan":
        print("PEER_C_OPERATION=CPU_CLI_PROBE_PLAN_ONLY_NO_DOCKER")
        print("PEER_C_PINNED_IMAGE=" + PEER.PINNED)
        print("PEER_C_IMAGE_CONFIG_ID=" + PEER.EXPECTED_IMAGE_ID)
        print("PEER_C_HELP_COMMAND=vllm serve --help=all")
        print("PEER_C_APPROVED_SCOPE=ONCE_CPU_ONLY_NO_GPU_NO_NETWORK_NO_MOUNTS")
        print("PEER_C_SOURCE_ONLY_PLAN=PASS")
        return 0
    if args.action == "report":
        try:
            return saved_report()
        except (ProbeError, OSError, ValueError, KeyError, TypeError) as exc:
            print("PEER_C_SAVED_REPORT=BLOCKED_READ_ERROR")
            print("PEER_C_DIAGNOSTIC=" + str(exc))
            return 2
    if not args.approved_cpu_only:
        print("PEER_C_CLI_PROBE=BLOCKED_EXPLICIT_APPROVAL_FLAG")
        return 2
    try:
        return run_once()
    except (ProbeError, OSError, subprocess.SubprocessError, ValueError) as exc:
        print("PEER_C_CLI_PROBE=FAILED_REVIEW")
        print("PEER_C_DIAGNOSTIC=" + str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
