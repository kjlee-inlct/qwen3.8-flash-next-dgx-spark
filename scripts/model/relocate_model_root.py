#!/usr/bin/env python3
"""Safely relocate the managed Qwen3.8 model root into the repository."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import IO

from checkpoint_integrity import inspect_checkpoint


MANIFEST_NAMES = (
    ".qwen38-model-manifest.json",
    ".qwen38-hybrid-manifest.json",
)
ORCA_DIRNAME = "qwen3.8-flash-next-orcarouter"
SERVICE_UNIT = "qwen38-flash-next.service"


class RelocationError(RuntimeError):
    """Raised when model-root relocation cannot be proven safe."""


@dataclass(frozen=True)
class ManagedEntry:
    path: Path
    manifest: Path
    kind: str


@dataclass(frozen=True)
class RelocationPlan:
    source: Path
    destination: Path
    legacy_model: Path
    entries: tuple[ManagedEntry, ...]
    already_relocated: bool


def absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path.expanduser())))


def nearest_existing_parent(path: Path) -> Path:
    current = path
    while not current.exists():
        if current.parent == current:
            raise RelocationError(f"cannot find existing parent for: {path}")
        current = current.parent
    return current


def same_filesystem(source: Path, destination: Path) -> bool:
    destination_probe = nearest_existing_parent(destination.parent)
    return source.stat().st_dev == destination_probe.stat().st_dev


def manifest_for(root: Path) -> Path | None:
    for name in MANIFEST_NAMES:
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def load_managed_manifest(path: Path) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RelocationError(f"cannot read managed manifest: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise RelocationError(f"managed manifest root is not an object: {path}")
    status = data.get("status")
    if status != "complete":
        raise RelocationError(
            f"managed checkpoint is not complete: {path.parent} (status={status})"
        )
    return data


def validate_manifest(path: Path) -> str:
    load_managed_manifest(path)
    return "hybrid" if path.name == ".qwen38-hybrid-manifest.json" else "model"


def validate_checkpoint_index(root: Path) -> None:
    index = root / "model.safetensors.index.json"
    if not index.is_file():
        return
    result = inspect_checkpoint(root)
    if result.invalid:
        raise RelocationError(
            f"invalid shard path(s) in {root}: " + ", ".join(result.invalid)
        )
    if result.missing:
        raise RelocationError(
            f"missing/dangling shard(s) in {root}: " + ", ".join(result.missing)
        )


HYBRID_VARIANTS = {
    "quant-layout-mazinb-experts": ("h3", "h3_dir"),
    "h4-orca-all": ("h4", "h4_dir"),
    "h5-neutral-input-scale": ("h5", "h5_dir"),
    "h6-modelopt-w4a16": ("h6", "model_dir"),
}
HYBRID_STAGE_ORDER = {"h3": 3, "h4": 4, "h5": 5, "h6": 6}


def validate_hybrid_chain(root: Path, entries: tuple[ManagedEntry, ...]) -> None:
    hybrid_entries = [entry for entry in entries if entry.kind == "hybrid"]
    if not hybrid_entries:
        return

    stage_paths: dict[str, Path] = {}
    highest_stage = "h3"
    for entry in hybrid_entries:
        data = load_managed_manifest(entry.manifest)
        variant = str(data.get("variant") or "")
        mapping = HYBRID_VARIANTS.get(variant)
        if mapping is None:
            raise RelocationError(
                f"unsupported hybrid variant for relocation validation: {variant or '-'}"
            )
        stage, argument_name = mapping
        stage_paths[argument_name] = entry.path
        if HYBRID_STAGE_ORDER[stage] > HYBRID_STAGE_ORDER[highest_stage]:
            highest_stage = stage

    expected_names = {
        "h3_dir": root / "qwen3.8-hybrid-quant-layout",
        "h4_dir": root / "qwen3.8-h4-orca-all",
        "h5_dir": root / "qwen3.8-h5-neutral-input-scale",
        "model_dir": root / "qwen3.8-h6-modelopt-w4a16",
    }
    for key, default_path in expected_names.items():
        stage_paths.setdefault(key, default_path)

    validator = Path(__file__).resolve().with_name("validate-orcarouter-hybrid.py")
    command = [
        sys.executable,
        os.fspath(validator),
        "--runtime-only",
        "--through",
        highest_stage,
        "--base-dir",
        os.fspath(root / ORCA_DIRNAME),
        "--h3-dir",
        os.fspath(stage_paths["h3_dir"]),
        "--h4-dir",
        os.fspath(stage_paths["h4_dir"]),
        "--h5-dir",
        os.fspath(stage_paths["h5_dir"]),
        "--model-dir",
        os.fspath(stage_paths["model_dir"]),
    ]
    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stdout + result.stderr).strip()
        raise RelocationError(
            "hybrid chain validation failed before relocation"
            + (f": {detail}" if detail else "")
        )


def inspect_root(root: Path) -> tuple[ManagedEntry, ...]:
    if not root.is_dir() or root.is_symlink():
        raise RelocationError(f"model root must be a real directory: {root}")

    entries: list[ManagedEntry] = []
    unmanaged: list[str] = []
    for child in sorted(root.iterdir()):
        if child.is_symlink() or not child.is_dir():
            unmanaged.append(child.name)
            continue
        manifest = manifest_for(child)
        if manifest is None:
            unmanaged.append(child.name)
            continue
        kind = validate_manifest(manifest)
        if kind == "model":
            validate_checkpoint_index(child)
        entries.append(ManagedEntry(child, manifest, kind))

    if unmanaged:
        raise RelocationError(
            "refusing whole-root relocation because unmanaged top-level entries exist: "
            + ", ".join(unmanaged)
        )
    if not entries:
        raise RelocationError(f"no managed model directories found under: {root}")
    managed_entries = tuple(entries)
    validate_hybrid_chain(root, managed_entries)
    return managed_entries


def path_is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def running_container_mounts(root: Path) -> list[str]:
    docker = shutil.which("docker")
    if docker is None:
        return []

    ps = subprocess.run(
        [docker, "ps", "-q"],
        text=True,
        capture_output=True,
        check=False,
    )
    if ps.returncode != 0:
        raise RelocationError("cannot inspect running Docker containers; docker ps failed")

    root_real = root.resolve(strict=False)
    owners: list[str] = []
    for container_id in (line.strip() for line in ps.stdout.splitlines()):
        if not container_id:
            continue
        inspected = subprocess.run(
            [docker, "inspect", container_id],
            text=True,
            capture_output=True,
            check=False,
        )
        if inspected.returncode != 0:
            raise RelocationError(f"cannot inspect running container: {container_id}")
        try:
            data = json.loads(inspected.stdout)
        except json.JSONDecodeError as exc:
            raise RelocationError(
                f"invalid docker inspect output for {container_id}"
            ) from exc
        if not data:
            continue
        name = str(data[0].get("Name", "")).lstrip("/") or container_id[:12]
        for mount in data[0].get("Mounts", []):
            source = mount.get("Source")
            if not isinstance(source, str) or not source:
                continue
            source_real = Path(source).resolve(strict=False)
            if source_real == root_real or path_is_within(source_real, root_real):
                owners.append(f"{name}:{source}")
    return owners


def managed_service_active() -> bool:
    systemctl = shutil.which("systemctl")
    if systemctl is None:
        return False
    result = subprocess.run(
        [systemctl, "is-active", "--quiet", SERVICE_UNIT],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def acquire_lifecycle_lock(*, dry_run: bool) -> IO[str] | None:
    state_home = Path(
        os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))
    )
    state_dir = state_home / "qwen38-spark"
    lock_path = state_dir / "operation.lock"

    if dry_run and not lock_path.exists():
        return None
    if not dry_run:
        state_dir.mkdir(parents=True, exist_ok=True)

    handle = lock_path.open("a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        handle.close()
        raise RelocationError(
            f"another lifecycle operation holds the lock: {lock_path}"
        ) from exc
    return handle


def readable_size(path: Path) -> str:
    result = subprocess.run(
        ["du", "-sh", "--", os.fspath(path)],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return "?"
    return result.stdout.split()[0]


def validate_legacy_model_path(legacy_model: Path, source: Path, destination: Path) -> None:
    if not legacy_model.exists() and not legacy_model.is_symlink():
        return
    if not legacy_model.is_symlink():
        raise RelocationError(
            f"legacy repository ./model path is not a symlink: {legacy_model}"
        )

    target = legacy_model.resolve(strict=False)
    allowed = {
        (source / ORCA_DIRNAME).resolve(strict=False),
        (destination / ORCA_DIRNAME).resolve(strict=False),
    }
    if target not in allowed:
        raise RelocationError(
            f"legacy ./model symlink points outside the expected OrcaRouter path: "
            f"{legacy_model} -> {target}"
        )


def plan_relocation(source: Path, destination: Path, repo_root: Path) -> RelocationPlan:
    source = absolute_path(source)
    destination = absolute_path(destination)
    repo_root = absolute_path(repo_root)
    legacy_model = repo_root / "model"

    if source == destination:
        raise RelocationError("source and destination model roots are identical")

    if source.is_symlink():
        if not destination.is_dir() or destination.is_symlink():
            raise RelocationError(
                f"source is a symlink but destination is not a real directory: {destination}"
            )
        if source.resolve(strict=False) != destination.resolve(strict=False):
            raise RelocationError(
                f"source symlink points somewhere unexpected: {source} -> "
                f"{source.resolve(strict=False)}"
            )
        entries = inspect_root(destination)
        validate_legacy_model_path(legacy_model, source, destination)
        return RelocationPlan(
            source=source,
            destination=destination,
            legacy_model=legacy_model,
            entries=entries,
            already_relocated=True,
        )

    if not source.is_dir():
        raise RelocationError(f"source model root does not exist: {source}")
    if destination.exists() or destination.is_symlink():
        raise RelocationError(f"destination already exists: {destination}")
    if not same_filesystem(source, destination):
        raise RelocationError(
            "source and destination are on different filesystems; atomic rename is required"
        )

    entries = inspect_root(source)
    validate_legacy_model_path(legacy_model, source, destination)

    mounts = running_container_mounts(source)
    if mounts:
        raise RelocationError(
            "refusing relocation while running container(s) mount the source root: "
            + ", ".join(mounts)
        )
    if managed_service_active():
        raise RelocationError(
            f"refusing relocation while {SERVICE_UNIT} is active; stop the service first"
        )

    return RelocationPlan(
        source=source,
        destination=destination,
        legacy_model=legacy_model,
        entries=entries,
        already_relocated=False,
    )


def print_plan(plan: RelocationPlan) -> None:
    physical_root = plan.destination if plan.already_relocated else plan.source
    print("Qwen3.8 model-root relocation")
    print(f"source      : {plan.source}")
    print(f"destination : {plan.destination}")
    print(f"managed     : {len(plan.entries)} directorie(s)")
    print(f"size        : {readable_size(physical_root)}")
    print(f"compat root : {plan.source} -> {plan.destination}")
    orca_destination = plan.destination / ORCA_DIRNAME
    if any(entry.path.name == ORCA_DIRNAME for entry in plan.entries):
        print(f"legacy model: {plan.legacy_model} -> {orca_destination}")
    print(
        "status      : "
        + ("already relocated" if plan.already_relocated else "ready for atomic rename")
    )


def update_compatibility_links(plan: RelocationPlan) -> None:
    source = plan.source
    destination = plan.destination

    if source.is_symlink():
        if source.resolve(strict=False) != destination.resolve(strict=False):
            raise RelocationError(f"unexpected compatibility root symlink: {source}")
    else:
        source.symlink_to(destination, target_is_directory=True)

    orca_destination = destination / ORCA_DIRNAME
    if orca_destination.is_dir():
        legacy_model = plan.legacy_model
        if legacy_model.is_symlink():
            legacy_model.unlink()
        elif legacy_model.exists():
            raise RelocationError(
                f"legacy ./model path became a non-symlink unexpectedly: {legacy_model}"
            )
        legacy_model.symlink_to(orca_destination, target_is_directory=True)


def apply_relocation(plan: RelocationPlan) -> None:
    if plan.already_relocated:
        update_compatibility_links(plan)
        return

    source = plan.source
    destination = plan.destination
    source_parent = source.parent
    destination.parent.mkdir(parents=True, exist_ok=True)

    old_legacy_target: str | None = None
    if plan.legacy_model.is_symlink():
        old_legacy_target = os.readlink(plan.legacy_model)

    os.rename(source, destination)
    try:
        update_compatibility_links(plan)
        inspect_root(destination)
    except Exception:
        if source.is_symlink():
            source.unlink()
        if plan.legacy_model.is_symlink():
            plan.legacy_model.unlink()
        os.rename(destination, source)
        if old_legacy_target is not None:
            plan.legacy_model.symlink_to(old_legacy_target, target_is_directory=True)
        if not source_parent.exists():
            source_parent.mkdir(parents=True, exist_ok=True)
        raise


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path.home() / "models",
        help="source model root (default: $HOME/models)",
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=repo_root / "models",
        help="destination model root (default: repository ./models)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    lock: IO[str] | None = None
    try:
        lock = acquire_lifecycle_lock(dry_run=args.dry_run)
        plan = plan_relocation(args.source, args.destination, repo_root)
        print_plan(plan)

        if args.dry_run:
            print("DRY-RUN: no files or symlinks changed.")
            return 0

        if not args.yes:
            answer = input("Type MOVE to relocate the managed model root: ").strip()
            if answer != "MOVE":
                raise RelocationError("cancelled")

        apply_relocation(plan)
        verified = plan_relocation(args.source, args.destination, repo_root)
        if not verified.already_relocated:
            raise RelocationError("post-migration verification did not detect relocated root")
        print("Model-root relocation complete and verified.")
        return 0
    except (RelocationError, OSError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    finally:
        if lock is not None:
            lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
