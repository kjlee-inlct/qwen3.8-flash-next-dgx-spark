#!/usr/bin/env python3
"""Opt-in removal of four pinned Hybrid stage directories; no Docker operations."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "scripts/model/hybrid-post-docker-model-gate.py"
spec = importlib.util.spec_from_file_location("hybrid_post_docker_gate", GATE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
EXPECTED = tuple(gate.STAGES)


def disk_bytes():
    stat = os.statvfs(ROOT)
    return stat.f_bavail * stat.f_frsize


def run(args):
    if args not in ([], ["--execute", "--confirm-exact-h3-h6"]):
        raise ValueError("only --execute --confirm-exact-h3-h6 accepted")
    report = gate.inspect()
    if report["post_docker_removal_gate"] != "PASS_READ_ONLY" or tuple(report["model_targets"]) != EXPECTED:
        raise ValueError("model gate failed or scope changed")
    root = ROOT / "models"
    paths = [root / name for name in EXPECTED]
    if len(set(paths)) != 4 or any(p.is_symlink() or not p.is_dir() or p.parent != root for p in paths):
        raise ValueError("unsafe model deletion path")
    before = disk_bytes()
    if not args:
        print(json.dumps({"mode": "DRY_RUN", "targets": [str(p) for p in paths],
                          "available_bytes_before": before, "removed": False}, indent=2))
        return
    # The gate has confirmed physical Docker retirement, exact paths, and
    # verified virtual file links. shutil.rmtree never follows symlinks.
    if not shutil.rmtree.avoids_symlink_attacks:
        raise ValueError("platform lacks symlink-safe rmtree")
    for path in reversed(paths):
        # Refuse if the target changed between previous deletion steps.
        if path.is_symlink() or not path.is_dir() or path.parent != root:
            raise ValueError("target disappeared or changed: " + str(path))
        shutil.rmtree(path)
        print("REMOVED_HYBRID_STAGE=" + path.name, flush=True)
    after = disk_bytes()
    print(json.dumps({"mode": "EXECUTED", "removed_stages": list(reversed(EXPECTED)),
                      "available_bytes_before": before, "available_bytes_after": after,
                      "available_bytes_delta": after - before,
                      "protected_orcarouter_exists": (root / gate.PROTECTED).is_dir()}, indent=2))


if __name__ == "__main__":
    try:
        run(sys.argv[1:])
    except (OSError, ValueError, KeyError) as err:
        print("HYBRID_MODEL_REMOVE=BLOCKED_OR_PARTIAL " + type(err).__name__ + ": " + str(err),
              file=sys.stderr)
        raise SystemExit(3)
