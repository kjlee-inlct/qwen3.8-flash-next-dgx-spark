#!/usr/bin/env python3
"""Read-only gate after exact 17 Docker removals, before deleting H3-H6."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "retirement_archive", ROOT / "scripts/model/hybrid-archive-git-summary.py")
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)
STAGES = ("qwen3.8-hybrid-quant-layout", "qwen3.8-h4-orca-all",
          "qwen3.8-h5-neutral-input-scale", "qwen3.8-h6-modelopt-w4a16")
PROTECTED = "qwen3.8-flash-next-orcarouter"
PINNED = "79ac8fcce46cc7063a6f0952537151dd80fda2d63a3e2828ee594a705c0f6701"


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True, timeout=90)


def inspect():
    record = archive.summarize(archive.ARCHIVE)
    if record["sha256_manifest"] != PINNED or len(record["container_ids"]) != 17:
        raise ValueError("archived provenance changed")
    container_ids = docker("ps", "-aq", "--no-trunc").splitlines()
    if set(container_ids) & set(record["container_ids"]):
        raise ValueError("some retired Hybrid containers still exist")
    objects = json.loads(docker("inspect", *container_ids)) if container_ids else []
    if {o["Id"] for o in objects} != set(container_ids):
        raise ValueError("Docker inspect identity mismatch")
    models = ROOT / "models"
    if models.is_symlink() or not models.is_dir():
        raise ValueError("unsafe models root")
    targets = {name: models / name for name in STAGES}
    protected = models / PROTECTED
    if protected.is_symlink() or not protected.is_dir():
        raise ValueError("protected model absent or symlink")
    for name, path in targets.items():
        if path.is_symlink() or not path.is_dir() or path.resolve() != path:
            raise ValueError("unsafe target directory: " + name)
        if os.stat(path, follow_symlinks=False).st_dev != os.stat(models).st_dev:
            raise ValueError("target on different filesystem: " + name)
    for obj in objects:
        for mount in obj.get("Mounts", []):
            source = str(mount.get("Source", ""))
            for name in STAGES:
                for alias in (str(targets[name]), str(Path.home() / "models" / name)):
                    if source == alias or source.startswith(alias + "/"):
                        raise ValueError("retained Docker references Hybrid: " + obj["Id"])
        # An old project alias may be missing, so check known mount fields literally.
        for mount in obj.get("HostConfig", {}).get("Binds", []) or []:
            source = str(mount).split(":", 1)[0]
            if any(source.endswith("/" + name) or "/"+name+"/" in source for name in STAGES):
                raise ValueError("retained Docker bind references Hybrid")
    counts = {}
    from pathlib import PurePosixPath
    for name, path in targets.items():
        counts[name] = 0
        for dirpath, dirs, files in os.walk(path, followlinks=False):
            for item in dirs + files:
                child = Path(dirpath) / item
                mode = child.lstat().st_mode
                if stat.S_ISLNK(mode):
                    raw = str(child.readlink())
                    allowed = {
                        STAGES[0]: "/base-model/",
                        STAGES[1]: "/h3-model/",
                        STAGES[2]: "/h4-all/",
                        STAGES[3]: "/h5-parent/",
                    }[name]
                    suffix = raw[len(allowed):] if raw.startswith(allowed) else ""
                    if not suffix or any(p in ("..", ".") for p in PurePosixPath(suffix).parts):
                        raise ValueError("unexpected symlink: " + str(child))
                    if item in dirs:
                        raise ValueError("directory symlink: " + str(child))
                    counts[name] += 1
                elif not (stat.S_ISREG(mode) or stat.S_ISDIR(mode)):
                    raise ValueError("special file in Hybrid tree: " + str(child))
                if os.lstat(child).st_dev != os.stat(models).st_dev:
                    raise ValueError("filesystem boundary in Hybrid tree")
    if counts != dict(zip(STAGES, (13, 76, 91, 139))):
        raise ValueError("Hybrid symlink inventory changed: " + str(counts))
    return {"post_docker_removal_gate": "PASS_READ_ONLY",
            "retired_docker_absent": 17, "retained_docker_count": len(container_ids),
            "model_targets": list(STAGES), "verified_symlink_counts": counts,
            "protected_orcarouter": PROTECTED, "model_delete_performed": False}


if __name__ == "__main__":
    try:
        if len(sys.argv) != 1:
            raise ValueError("no arguments accepted")
        print(json.dumps(inspect(), indent=2, sort_keys=True))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as err:
        print("HYBRID_POST_DOCKER_GATE=BLOCKED " + type(err).__name__ + ": " + str(err), file=sys.stderr)
        raise SystemExit(3)
