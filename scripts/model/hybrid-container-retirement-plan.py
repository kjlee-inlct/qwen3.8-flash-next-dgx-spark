#!/usr/bin/env python3
"""Read-only exact six Hybrid Docker retirement plan, never removal."""
import json
from pathlib import Path
import re
import subprocess
import sys

EXPECTED = {
    "qwen38-hybrid-h6-m1-20261014141803-69ef3492": "e526189f1093e95d81568d82eb10b8beaeb6227adca49029f241634769e6cbc7",
    "qwen38-hybrid-r28-unquant-linear-marker": "e2b000b28d5e71922e20d59f9725c8ebe54c5794349a20515343302f8d608e2a",
    "qwen38-hybrid-r27-linear-marker": "43afd5055614c273181bd8f91d251ab19ac88d49080f3362cf7bcc31143c5c65",
    "qwen38-hybrid-r26-construction-marker": "bd6886aa4499f14e12e8ce3e49c2400ec2a0d940bf4e0d03a0d8fe3d1d5ba14c",
    "qwen38-hybrid-r25b-init-marker": "6484fdf56ffbec15d76333bda1a36f05ca50b9f17841b37e41e0781343a8b2e0",
    "qwen38-hybrid-r24-kv16": "e937e0f23e45ba4ee8851e79e60eaefc509367b74a021e67a74fea098ad17f62",
}
STAGES = (
    "qwen3.8-hybrid-quant-layout",
    "qwen3.8-h4-orca-all",
    "qwen3.8-h5-neutral-input-scale",
    "qwen3.8-h6-modelopt-w4a16",
)
FULL_ID = re.compile(r"[a-f0-9]{64}\Z")


def docker(*args: str) -> str:
    result = subprocess.run(["docker", *args], check=True, capture_output=True, text=True, timeout=60)
    return result.stdout


def plan(ids_text: str, inspect_text: str) -> tuple[bool, list[str]]:
    all_ids = ids_text.splitlines()
    if not all_ids or len(set(all_ids)) != len(all_ids) or any(not FULL_ID.fullmatch(v) for v in all_ids):
        return False, ["BLOCKED_INVALID_DOCKER_ID_INVENTORY"]
    expected_ids = set(EXPECTED.values())
    if not expected_ids.issubset(set(all_ids)):
        return False, ["BLOCKED_TARGET_CONTAINER_MISSING"]
    objects = json.loads(inspect_text)
    if not isinstance(objects, list) or len(objects) != len(all_ids):
        return False, ["BLOCKED_INCOMPLETE_DOCKER_INSPECT"]
    by_id = {obj.get("Id"): obj for obj in objects if isinstance(obj, dict)}
    if set(by_id) != set(all_ids) or len(by_id) != len(objects):
        return False, ["BLOCKED_DOCKER_ID_MISMATCH"]
    lines = []
    for name, cid in EXPECTED.items():
        item = by_id[cid]
        state = item.get("State") or {}
        host = item.get("HostConfig") or {}
        policy = host.get("RestartPolicy") or {}
        if (item.get("Name") != "/" + name
            or state.get("Status") != "exited"
            or state.get("Running") is not False
            or host.get("AutoRemove") is not False
            or policy.get("Name") not in (None, "", "no")):
            return False, ["BLOCKED_TARGET_STATE_OR_POLICY_CHANGED"]
        mounts = item.get("Mounts")
        if not isinstance(mounts, list) or not all(
            isinstance(m, dict) and isinstance(m.get("Source"), str) and m["Source"].startswith("/")
            for m in mounts
        ):
            return False, ["BLOCKED_TARGET_MOUNTS_UNVERIFIED"]
        lines.append("TARGET_EXACT_EXITED=" + name + " id=" + cid)
    for cid, item in by_id.items():
        if cid in expected_ids:
            continue
        mounts = item.get("Mounts")
        if not isinstance(mounts, list):
            return False, ["BLOCKED_OTHER_CONTAINER_MOUNTS_UNVERIFIED"]
        for mount in mounts:
            if not isinstance(mount, dict) or not isinstance(mount.get("Source"), str):
                return False, ["BLOCKED_OTHER_CONTAINER_MOUNTS_UNVERIFIED"]
            source = mount["Source"].rstrip("/")
            model_root = str(Path(__file__).resolve().parents[2] / "models")
            if any(source == model_root + "/" + stage or
                   source.startswith(model_root + "/" + stage + "/") for stage in STAGES):
                return False, ["BLOCKED_UNEXPECTED_CONTAINER_HYBRID_REFERENCE id=" + cid + " source=" + source]
    lines.append("TARGET_COUNT=6")
    lines.append("OTHER_DOCKER_CONTAINERS=UNCHANGED")
    return True, lines


def main() -> int:
    if len(sys.argv) != 1:
        print("Usage: python3 scripts/model/hybrid-container-retirement-plan.py", file=sys.stderr)
        return 2
    try:
        ids = docker("ps", "-aq", "--no-trunc")
        id_list = ids.splitlines()
        if not id_list:
            raise ValueError("no containers found")
        report = docker("inspect", *id_list)
        ok, lines = plan(ids, report)
        for line in lines:
            print(line)
        print("OFF_HOST_BACKUP=NOT_VERIFIED")
        print("HYBRID_CONTAINER_DELETE=NOT_AUTHORIZED")
        print("HYBRID_CONTAINER_PLAN=" + ("PASS_READ_ONLY" if ok else "BLOCKED"))
        return 0 if ok else 3
    except (subprocess.SubprocessError, OSError, ValueError, TypeError, KeyError,
            json.JSONDecodeError) as error:
        print("HYBRID_CONTAINER_PLAN=BLOCKED_INSPECTION_ERROR")
        print(type(error).__name__, file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
