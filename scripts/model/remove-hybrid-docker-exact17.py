#!/usr/bin/env python3
"""Exact 17 stopped Hybrid Docker removal, explicitly opt-in; never touch volumes/images."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "scripts/model/hybrid-retirement-final-gate.py"
spec = importlib.util.spec_from_file_location("hybrid_final_gate", GATE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def execute(argv):
    if argv not in ([], ["--execute", "--confirm-exact-17"]):
        raise ValueError("only --execute --confirm-exact-17 is accepted")
    verified = gate.inspect_and_validate()
    if verified["read_only_preflight"] != "PASS" or verified["hybrid_container_count"] != 17:
        raise ValueError("final gate not passed")
    summary = gate.archive.summarize(gate.archive.ARCHIVE)
    ids = sorted(summary["container_ids"])
    if len(ids) != 17:
        raise ValueError("unexpected number of Docker IDs")
    if not argv:
        print(json.dumps({"mode": "DRY_RUN", "verified_ids": ids,
                          "next": "--execute --confirm-exact-17",
                          "docker_remove_performed": False}, indent=2))
        return
    # Revalidate each object immediately before removing. Never use -f / -v,
    # never prune images or volumes, and never touch any unlisted ID.
    for cid in ids:
        data = json.loads(subprocess.check_output(
            ["docker", "inspect", cid], text=True, timeout=30))
        if len(data) != 1 or data[0]["Id"] != cid or data[0]["State"]["Running"]:
            raise ValueError("Docker candidate changed or running: " + cid)
        if data[0]["State"]["Status"] != "exited":
            raise ValueError("Docker candidate not exited: " + cid)
        subprocess.run(["docker", "rm", "--", cid], check=True, timeout=45)
        print("REMOVED_EXACT_ID=" + cid, flush=True)
    print("HYBRID_DOCKER_EXACT_17=REMOVED")
    print("MODEL_DELETE=NOT_PERFORMED")


if __name__ == "__main__":
    try:
        execute(sys.argv[1:])
    except (ValueError, OSError, subprocess.SubprocessError, KeyError) as err:
        print("HYBRID_DOCKER_REMOVE=BLOCKED_OR_PARTIAL " + type(err).__name__ + ": " + str(err), file=sys.stderr)
        raise SystemExit(3)
