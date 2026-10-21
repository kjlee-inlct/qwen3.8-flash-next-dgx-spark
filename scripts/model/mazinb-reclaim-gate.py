#!/usr/bin/env python3
"""Strict read-only admission for retiring ONLY the original mazinb checkpoint.

Never deletes files, changes containers or authorizes broad prune. The owning
scripts/manage-models.sh must hold the lifecycle and benchmark locks for apply.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
FULL_ID = re.compile(r"[0-9a-f]{64}\Z")
EXPECTED = {
    "smoke.json": "0e7f42ef99c91098572558bb909c589ae7c470b3cb60f32599e394553cf1fafd",
    "mazinb.json": "377f5b5745aa16d454269490db408376d5f18d0289e576df8cd5a92a986fc23e",
    "mazinb-report.md": "b3e8f2d88ddfdc6894a3ed3678769f95a115ab4b665a7b3eb31ced1991bb298a",
}
MODEL = "qwen3.8-flash-next-mazinb"
TRIAL = "20261014T015805Z"
EXPECTED_REPO = "mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4"
PROTECTED_NAME = "qwen38-flash-next"
PROTECTED_ID = "f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24"


class Blocked(ValueError):
    pass


def require(ok: bool, msg: str) -> None:
    if not ok:
        raise Blocked(msg)


def safe_regular(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except OSError:
        return False


def safe_directory(path: Path) -> bool:
    try:
        return stat.S_ISDIR(path.lstat().st_mode)
    except OSError:
        return False


def read_json(path: Path) -> dict:
    require(safe_regular(path), f"missing or symlinked file: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(data, dict), f"expected JSON object: {path}")
    return data


def digest(path: Path) -> str:
    require(safe_regular(path), f"missing or symlinked archive payload: {path}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def archived_evidence(home: Path, candidate: Path) -> None:
    archive = ROOT / "docs/model-reports/evidence/mazinb" / TRIAL
    original = home / "Workspace/llm/qwen38-m1-bench-results" / TRIAL
    report = ROOT / "docs/model-reports/mazinb.md"
    require(safe_regular(report) and "**BENCHMARK_STATUS: MEASURED**" in
            report.read_text(encoding="utf-8"), "mazinb MEASURED report missing")
    require(safe_directory(archive) and safe_directory(original),
            "independent repository/original benchmark directories missing")
    require(not original.is_relative_to(candidate),
            "original benchmark folder is inside the deletion candidate")
    manifest = archive / "SHA256SUMS"
    require(safe_regular(manifest), "GitHub archive SHA256SUMS missing")
    rows = manifest.read_text(encoding="utf-8").splitlines()
    parsed = {}
    for row in rows:
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)", row)
        require(match is not None, "nonportable archive SHA manifest")
        sha, name = match.groups()
        require(name not in parsed, "duplicate SHA manifest entry")
        parsed[name] = sha
    require(parsed == EXPECTED, "archive SHA manifest does not match physical M1 evidence")
    for name, expected in EXPECTED.items():
        require(digest(archive / name) == expected, f"repository archive corrupt: {name}")
        require(digest(original / name) == expected, f"original DGX archive corrupt: {name}")
    print("MAZINB_RECLAIM_EVIDENCE=MEASURED_REPO_AND_ORIGINAL_SHA256_PASS")
    print("MAZINB_RECLAIM_EXTERNAL_GITHUB_COPY=REQUIRES_OPERATOR_CONFIRMATION")


def hybrid_provenance(model_root: Path, candidate: Path) -> None:
    names = ("qwen3.8-hybrid-quant-layout", "qwen3.8-h4-orca-all",
             "qwen3.8-h5-neutral-input-scale", "qwen3.8-h6-modelopt-w4a16")
    dirs = [model_root / n for n in names]
    present = [p.exists() or p.is_symlink() for p in dirs]
    require(not any(p.is_symlink() for p in dirs), "symlinked Hybrid stage")
    if not any(present):
        print("MAZINB_RECLAIM_HYBRID=NO_PRESENT_GENERATED_STAGES")
        return
    require(present[0], "Hybrid stages depend on a missing H3; keep mazinb source")
    for p in dirs:
        if p.exists():
            require(safe_directory(p), f"unsafe Hybrid stage: {p}")
            for base, folders, files in os.walk(p, followlinks=False):
                for filename in folders + files:
                    entry = Path(base) / filename
                    if entry.is_symlink():
                        target = os.readlink(entry)
                        require(not target.startswith(str(candidate)),
                                f"Hybrid stage references mazinb source: {entry}")
                        if not target.startswith("/"):
                            resolved = (entry.parent / target).resolve(strict=False)
                            require(not resolved.is_relative_to(candidate),
                                    f"Hybrid relative link references mazinb: {entry}")
    validator = ROOT / "scripts/model/validate-orcarouter-hybrid.py"
    def run(*args: str) -> None:
        p = subprocess.run([sys.executable, str(validator), *args],
                           text=True, capture_output=True, check=False, timeout=120)
        require(p.returncode == 0, "Hybrid validation blocked: " +
                (p.stderr or p.stdout)[-450:].strip())
    run("--h3-source-reuse-check", "--h3-dir", str(dirs[0]))
    if any(present[1:]):
        require(all(present), "incomplete H4/H5/H6 dependency chain; preserve original")
        run("--runtime-only", "--base-dir",
            str(model_root / "qwen3.8-flash-next-orcarouter"),
            "--h3-dir", str(dirs[0]), "--h4-dir", str(dirs[1]),
            "--h5-dir", str(dirs[2]), "--model-dir", str(dirs[3]))
    print("MAZINB_RECLAIM_HYBRID=PINNED_H3_PROVENANCE_AND_RUNTIME_CHAIN_PASS")


def docker_inventory(candidate: Path, root: Path, state_dir: Path) -> None:
    p = subprocess.run(["docker", "ps", "-aq", "--no-trunc"], capture_output=True,
                       text=True, check=False, timeout=30)
    require(p.returncode == 0, "Docker inventory unavailable")
    ids = [line.strip() for line in p.stdout.splitlines() if line.strip()]
    require(all(FULL_ID.fullmatch(x) for x in ids), "Docker inventory returned invalid IDs")
    containers = []
    if ids:
        p = subprocess.run(["docker", "inspect", *ids], capture_output=True,
                           text=True, check=False, timeout=45)
        require(p.returncode == 0, "Docker inspect incomplete")
        containers = json.loads(p.stdout)
        require(isinstance(containers, list) and len(containers) == len(ids),
                "Docker inspect inventory incomplete")
    indexed = {}
    affected = []
    for obj in containers:
        cid = obj.get("Id", "")
        require(FULL_ID.fullmatch(cid) and cid in ids and cid not in indexed,
                "Docker inspect identity mismatch")
        indexed[cid] = obj
        name = obj.get("Name", "").lstrip("/")
        status = obj.get("State") or {}
        running = status.get("Running")
        require(type(running) is bool, f"Docker running state unavailable: {cid}")
        if name.startswith("qwen38-") and running:
            raise Blocked(f"project Docker container still running: {name} {cid}")
        mounts = obj.get("Mounts") or []
        for mount in mounts:
            source = mount.get("Source", "")
            require(isinstance(source, str), "invalid Docker mount source")
            if not source.startswith("/"):
                continue
            resolved = Path(source).resolve(strict=False)
            if (resolved == candidate or resolved.is_relative_to(candidate)
                    or resolved == root):
                require(not running, f"running container references candidate: {name} {cid}")
                affected.append((cid, name))
                restart = (obj.get("HostConfig") or {}).get("RestartPolicy") or {}
                require(restart.get("Name") in (None, "", "no"),
                        f"stopped container has restart policy: {name} {cid}")
    old = indexed.get(PROTECTED_ID)
    require(old is not None and old.get("Name") == "/" + PROTECTED_NAME,
            "protected OrcaRouter predecessor identity missing/changed")
    journal = state_dir / "mazinb-m1/active.json"
    require(safe_regular(journal), "M1 journal must be reconciled and present")
    record = read_json(journal)
    require(record.get("phase") in ("stopped", "failed_stopped"),
            "M1 journal is not in a terminal stopped state")
    cid = record.get("id", "")
    require(FULL_ID.fullmatch(cid) and cid in indexed and
            indexed[cid].get("State", {}).get("Running") is False,
            "M1 exact candidate is missing or running")
    print(f"MAZINB_RECLAIM_STOPPED_MOUNTS={len(set(affected))}")
    for cid, name in sorted(set(affected)):
        print(f"MAZINB_RECLAIM_ARCHIVE_ONLY_CONTAINER={name} ID={cid}")
    print(f"MAZINB_RECLAIM_PROTECTED_PREDECESSOR={PROTECTED_ID}")


def inspect(home: Path, model_root: Path, state_dir: Path) -> None:
    require(safe_directory(model_root), f"model root absent or symlinked: {model_root}")
    candidate = model_root / MODEL
    require(safe_directory(candidate), "mazinb source checkpoint absent or symlinked")
    require(candidate.parent == model_root, "candidate is not directly under the model root")
    record = read_json(candidate / ".qwen38-model-manifest.json")
    require(record.get("status") == "complete" and record.get("repository") == EXPECTED_REPO
            and str(record.get("revision", "")).startswith("f2c21eb"),
            "mazinb complete pinned model manifest mismatch")
    require(safe_directory(state_dir), "managed state directory unavailable")
    # The shell manager parses the authoritative install.env using the strict parser.
    # Recheck its existence here; the manager separately enforces complete/active checks.
    require(safe_regular(state_dir / "install.env"), "managed manifest is missing/unsafe")
    print(f"MAZINB_RECLAIM_EXACT_CHECKPOINT={candidate}")
    archived_evidence(home, candidate)
    hybrid_provenance(model_root, candidate)
    docker_inventory(candidate, model_root, state_dir)
    print("MAZINB_RECLAIM_GATE=PASS_SOURCE_ONLY_READ_ONLY")
    print("MAZINB_RECLAIM_REMOVE=NOT_PERFORMED")


def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: mazinb-reclaim-gate.py HOME MODEL_ROOT STATE_DIR", file=sys.stderr)
        return 2
    try:
        home, root, state = map(Path, sys.argv[1:])
        require(home.is_absolute() and root.is_absolute() and state.is_absolute(),
                "absolute paths required")
        inspect(home, root, state)
    except (Blocked, ValueError, OSError, json.JSONDecodeError,
            subprocess.SubprocessError) as e:
        print(f"MAZINB_RECLAIM_GATE=BLOCKED reason={str(e)[:450]}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
