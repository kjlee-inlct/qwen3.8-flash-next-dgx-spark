#!/usr/bin/env python3
"""Read-only inventory of Hybrid Docker mounts (including historical symlink paths)."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
MODEL_ROOTS = (str(ROOT / "models"), "/home/inlc/models")
STAGES = (
    "qwen3.8-hybrid-quant-layout",
    "qwen3.8-h4-orca-all",
    "qwen3.8-h5-neutral-input-scale",
    "qwen3.8-h6-modelopt-w4a16",
)
PROTECTED_NAME = "/qwen38-flash-next"


def references(source: str) -> list[str]:
    if not isinstance(source, str) or not source.startswith("/"):
        raise ValueError("invalid mount source")
    return [stage for root in MODEL_ROOTS for stage in STAGES
            if source == root + "/" + stage or source.startswith(root + "/" + stage + "/")]


def inventory(ids: str, raw: str) -> list[dict]:
    all_ids = ids.splitlines()
    if len(set(all_ids)) != len(all_ids) or not all_ids:
        raise ValueError("duplicate/empty docker inventory")
    objects = json.loads(raw)
    if not isinstance(objects, list) or len(objects) != len(all_ids):
        raise ValueError("incomplete docker inspection")
    by_id = {obj["Id"]: obj for obj in objects}
    if set(by_id) != set(all_ids):
        raise ValueError("docker inventory changed")
    output = []
    for cid in sorted(by_id):
        obj = by_id[cid]
        name = obj.get("Name")
        if name == PROTECTED_NAME:
            continue
        mounts = obj.get("Mounts")
        if not isinstance(mounts, list):
            raise ValueError("missing mounts on " + cid)
        relevant = []
        for mount in mounts:
            source = mount.get("Source")
            stages = references(source)
            if stages:
                relevant.append({"source": source, "stages": sorted(set(stages))})
        if relevant:
            status = (obj.get("State") or {}).get("Status")
            output.append({"id": cid, "name": name, "status": status,
                           "hybrid_mounts": relevant,
                           "protected": False,
                           "review_required": True})
    return output


def docker(*args: str) -> str:
    return subprocess.run(["docker", *args], check=True, capture_output=True,
                          text=True, timeout=90).stdout


def main() -> int:
    if len(sys.argv) != 1:
        print("usage: python3 scripts/model/hybrid-docker-inventory.py", file=sys.stderr)
        return 2
    try:
        ids = docker("ps", "-aq", "--no-trunc")
        result = inventory(ids, docker("inspect", *ids.splitlines()))
        for obj in result:
            print(json.dumps(obj, sort_keys=True))
        print("HYBRID_RESEARCH_DOCKER_CANDIDATES=" + str(len(result)))
        print("HYBRID_DOCKER_DELETE=NOT_AUTHORIZED")
        print("HYBRID_DOCKER_INVENTORY=PASS_READ_ONLY")
        return 0
    except (OSError, KeyError, ValueError, TypeError, subprocess.SubprocessError) as exc:
        print("HYBRID_DOCKER_INVENTORY=BLOCKED_" + type(exc).__name__, file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
