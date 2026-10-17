#!/usr/bin/env python3
"""Read-only physical preflight for an exact 17-container Hybrid retirement."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

archive = load("hybrid_archive_git_summary", "scripts/model/hybrid-archive-git-summary.py")
inventory = load("hybrid_docker_inventory", "scripts/model/hybrid-docker-inventory.py")
PINNED_MANIFEST = "79ac8fcce46cc7063a6f0952537151dd80fda2d63a3e2828ee594a705c0f6701"
STAGES = ("qwen3.8-hybrid-quant-layout", "qwen3.8-h4-orca-all",
          "qwen3.8-h5-neutral-input-scale", "qwen3.8-h6-modelopt-w4a16")
PROTECTED = "qwen3.8-flash-next-orcarouter"


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True, timeout=90)


def inspect_and_validate():
    checked = archive.summarize(archive.ARCHIVE)
    if checked["sha256_manifest"] != PINNED_MANIFEST:
        raise ValueError("pinned archive manifest mismatch")
    expected = set(checked["container_ids"])
    ids = docker("ps", "-aq", "--no-trunc").splitlines()
    objects = json.loads(docker("inspect", *ids))
    found = {obj["Id"]: obj for obj in objects}
    if len(found) != len(ids):
        raise ValueError("duplicate or missing Docker inspect IDs")
    hybrid = inventory.inventory("\n".join(ids), json.dumps(objects))
    if {entry["id"] for entry in hybrid} != expected:
        raise ValueError("Docker Hybrid candidates differ from archived 17")
    for entry in hybrid:
        obj = found[entry["id"]]
        if entry["protected"] or entry["status"] != "exited":
            raise ValueError("protected/running Hybrid candidate")
        if obj.get("HostConfig", {}).get("RestartPolicy", {}).get("Name") not in ("", "no", None):
            raise ValueError("auto restarting Docker candidate")
        if obj.get("HostConfig", {}).get("AutoRemove"):
            raise ValueError("auto-removing Docker candidate")
        if any(m.get("Type") != "bind" for m in obj.get("Mounts", [])):
            raise ValueError("non-bind mount on Docker candidate; requires review")
    root = ROOT / "models"
    if root.is_symlink() or not root.is_dir():
        raise ValueError("unsafe models root")
    for name in (*STAGES, PROTECTED):
        target = root / name
        if target.is_symlink() or not target.is_dir():
            raise ValueError("missing or symlinked model: " + name)
    # Absolute symlinks are container-namespace references, not host / paths.
    # Deleting links never follows them; mapping is strictly for review.
    alias_sources = {
        STAGES[0]: ("/base-model", PROTECTED),
        STAGES[1]: ("/h3-model", STAGES[0]),
        STAGES[2]: ("/h4-all", STAGES[1]),
        STAGES[3]: ("/h5-parent", STAGES[2]),
    }
    counts = {name: 0 for name in STAGES}
    for name in STAGES:
        target = root / name
        alias, source_name = alias_sources[name]
        source_root = root / source_name
        for path in target.rglob("*"):
            if not path.is_symlink():
                continue
            # A symlinked directory is particularly dangerous to reason about;
            # refuse it even if the prefix otherwise looks familiar.
            raw = str(path.readlink())
            prefix = alias + "/"
            if not raw.startswith(prefix):
                raise ValueError("unexpected Hybrid symlink target: " + str(path) + " -> " + raw)
            suffix = raw[len(prefix):]
            from pathlib import PurePosixPath
            parts = PurePosixPath(suffix).parts
            if (not parts or any(part in ("", ".", "..") for part in parts)
                or raw.endswith("/") or "\\" in suffix):
                raise ValueError("unsafe Hybrid virtual link: " + str(path))
            mapped = source_root.joinpath(*parts)
            if not mapped.is_file() and not mapped.is_symlink():
                raise ValueError("mapped Hybrid source missing: " + str(path))
            # Earlier stages can themselves be virtual-link layouts.
            # That is safe for unlinking; do not resolve or traverse them.
            if mapped.is_dir():
                raise ValueError("mapped Hybrid source is a directory: " + str(path))
            counts[name] += 1
    expected_counts = {STAGES[0]: 13, STAGES[1]: 76, STAGES[2]: 91, STAGES[3]: 139}
    if counts != expected_counts:
        raise ValueError("Hybrid virtual-link counts changed: " + str(counts))
    return {"archived_container_count": len(expected),
            "hybrid_container_count": len(hybrid),
            "pinned_archive_manifest_sha256": PINNED_MANIFEST,
            "model_targets": list(STAGES),
            "verified_virtual_link_counts": counts,
            "protected_orcarouter": PROTECTED,
            "docker_delete_performed": False,
            "model_delete_performed": False,
            "read_only_preflight": "PASS"}


def main():
    if len(sys.argv) != 1:
        print("usage: python3 scripts/model/hybrid-retirement-final-gate.py", file=sys.stderr)
        return 2
    try:
        print(json.dumps(inspect_and_validate(), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as err:
        print("HYBRID_FINAL_GATE=BLOCKED " + type(err).__name__ + ": " + str(err), file=sys.stderr)
        return 3

if __name__ == "__main__":
    raise SystemExit(main())
