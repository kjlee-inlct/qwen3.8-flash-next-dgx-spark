#!/usr/bin/env python3
"""Read-only exact-container evidence preflight; never starts/stops/removes Docker."""
import json
import re
import subprocess
import sys

EXPECTED = {
    "qwen38-hybrid-h6-m1-20261014141803-69ef3492": "e526189f1093",
    "qwen38-hybrid-r28-unquant-linear-marker": "e2b000b28d5e",
    "qwen38-hybrid-r27-linear-marker": "43afd5055614",
    "qwen38-hybrid-r26-construction-marker": "bd6886aa4499",
    "qwen38-hybrid-r25b-init-marker": "6484fdf56ff",
    "qwen38-hybrid-r24-kv16": "e937e0f23e45",
}
def docker(*args):
    return subprocess.run(["docker", *args], check=True, capture_output=True, text=True).stdout

def main():
    if len(sys.argv) != 1:
        raise SystemExit("usage: python3 scripts/model/hybrid-container-evidence.py")
    try:
        raw = docker("inspect", *EXPECTED)
        objects = json.loads(raw)
        by_name = {x["Name"].lstrip("/"): x for x in objects}
        if set(by_name) != set(EXPECTED):
            raise ValueError("expected exact six containers only")
        for name, prefix in EXPECTED.items():
            item = by_name[name]
            cid = item["Id"]
            state = item["State"]["Status"]
            mounts = [x["Source"] for x in item["Mounts"]]
            if not re.fullmatch(r"[0-9a-f]{64}", cid) or not cid.startswith(prefix):
                raise ValueError("container identity changed: " + name)
            if state != "exited":
                raise ValueError("container not exited: " + name)
            if not all(isinstance(p, str) and p.startswith("/") for p in mounts):
                raise ValueError("unexpected mount: " + name)
            # Docker inspect contains environment variables and potentially credentials.
            # Emit only explicitly selected nonsecret fields; never serialize raw inspect.
            print(json.dumps({"name": name, "id": cid, "status": state,
                              "image_id": item["Image"],
                              "mount_sources": mounts,
                              "log_driver": item["HostConfig"]["LogConfig"]["Type"]},
                             ensure_ascii=False, sort_keys=True))
        print("EVIDENCE_PREFLIGHT=PASS_READ_ONLY_NOT_ARCHIVED_NOT_DELETE_AUTHORIZATION")
    except (subprocess.CalledProcessError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print("EVIDENCE_PREFLIGHT=BLOCKED", file=sys.stderr)
        print(type(exc).__name__, file=sys.stderr)
        raise SystemExit(3)

if __name__ == "__main__":
    main()
