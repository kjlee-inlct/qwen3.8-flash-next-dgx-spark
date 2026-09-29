#!/usr/bin/env python3
"""Safely migrate a legacy repo-local OrcaRouter checkpoint to its canonical path."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from checkpoint_integrity import inspect_checkpoint


ORCA_REPOSITORY = "orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4"
ORCA_REVISION = "c1209bda15a6bbc4c68b585e93d40c0d85f50306"


class MigrationError(RuntimeError):
    """Raised when migration safety conditions are not satisfied."""


@dataclass(frozen=True)
class MigrationPlan:
    legacy: Path
    canonical: Path
    backup: Path | None
    create_legacy_link: bool
    already_migrated: bool


def load_manifest(root: Path) -> dict[str, object]:
    path = root / ".qwen38-model-manifest.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MigrationError(f"cannot read model manifest: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise MigrationError(f"model manifest root is not an object: {path}")
    return data


def validate_manifest(root: Path, *, require_complete: bool) -> dict[str, object]:
    data = load_manifest(root)
    status = data.get("status")
    if require_complete and status != "complete":
        raise MigrationError(f"model manifest is not complete: {root} (status={status})")
    if data.get("repository") != ORCA_REPOSITORY:
        raise MigrationError(f"unexpected repository in {root}: {data.get('repository')}")
    if data.get("revision") != ORCA_REVISION:
        raise MigrationError(f"unexpected revision in {root}: {data.get('revision')}")
    return data


def validate_complete_checkpoint(root: Path) -> None:
    validate_manifest(root, require_complete=True)
    result = inspect_checkpoint(root)
    if result.invalid:
        raise MigrationError(
            "checkpoint contains invalid shard path(s): " + ", ".join(result.invalid)
        )
    if result.missing:
        raise MigrationError(
            "checkpoint is incomplete; missing/dangling shard(s): " + ", ".join(result.missing)
        )


def backup_candidate(canonical: Path) -> Path:
    base = canonical.with_name(canonical.name + ".partial-backup")
    if not base.exists() and not base.is_symlink():
        return base
    index = 1
    while True:
        candidate = canonical.with_name(f"{canonical.name}.partial-backup.{index}")
        if not candidate.exists() and not candidate.is_symlink():
            return candidate
        index += 1


def nearest_existing_parent(path: Path) -> Path:
    current = path
    while not current.exists():
        if current.parent == current:
            raise MigrationError(f"cannot find existing parent for: {path}")
        current = current.parent
    return current


def same_filesystem(source: Path, destination_parent: Path) -> bool:
    probe = nearest_existing_parent(destination_parent)
    return source.stat().st_dev == probe.stat().st_dev


def absolute_path(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path.expanduser())))


def running_container_mounts(target: Path) -> list[str]:
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
        raise MigrationError("cannot inspect running Docker containers; docker ps failed")

    target_real = target.resolve(strict=False)
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
            raise MigrationError(
                f"cannot inspect running Docker container: {container_id}"
            )
        try:
            payload = json.loads(inspected.stdout)
            container = payload[0]
            name = str(container.get("Name") or container_id).lstrip("/")
            mounts = container.get("Mounts") or []
        except (json.JSONDecodeError, IndexError, TypeError, AttributeError) as exc:
            raise MigrationError(
                f"cannot parse Docker inspect output for: {container_id}"
            ) from exc

        for mount in mounts:
            if not isinstance(mount, dict):
                continue
            source = str(mount.get("Source") or "")
            if not source:
                continue
            source_path = Path(source)
            if source_path == target or source_path.resolve(strict=False) == target_real:
                owners.append(name)
                break
    return owners

def prepare_plan(
    legacy: Path,
    canonical: Path,
    *,
    mount_checker: Callable[[Path], list[str]] = running_container_mounts,
) -> MigrationPlan:
    legacy = absolute_path(legacy)
    canonical = absolute_path(canonical)

    if legacy.resolve(strict=False) == canonical.resolve(strict=False) and not legacy.is_symlink():
        raise MigrationError("legacy and canonical paths resolve to the same path")

    if legacy.is_symlink():
        if legacy.resolve(strict=False) != canonical:
            raise MigrationError(
                f"legacy path is an unexpected symlink: {legacy} -> {legacy.resolve(strict=False)}"
            )
        if not canonical.is_dir():
            raise MigrationError(f"canonical checkpoint directory is missing: {canonical}")
        validate_complete_checkpoint(canonical)
        return MigrationPlan(
            legacy=legacy,
            canonical=canonical,
            backup=None,
            create_legacy_link=False,
            already_migrated=True,
        )

    if not legacy.is_dir():
        if canonical.is_dir():
            validate_complete_checkpoint(canonical)
            return MigrationPlan(
                legacy=legacy,
                canonical=canonical,
                backup=None,
                create_legacy_link=True,
                already_migrated=False,
            )
        raise MigrationError(f"legacy checkpoint directory is missing: {legacy}")

    validate_complete_checkpoint(legacy)

    legacy_owners = mount_checker(legacy)
    if legacy_owners:
        raise MigrationError(
            "legacy checkpoint is mounted by running container(s): "
            + ", ".join(sorted(legacy_owners))
        )

    if not same_filesystem(legacy, canonical.parent):
        raise MigrationError(
            "legacy and canonical locations are on different filesystems; "
            "copy migration is intentionally unsupported"
        )

    if canonical.exists() or canonical.is_symlink():
        if canonical.is_symlink():
            raise MigrationError(f"canonical path is an unexpected symlink: {canonical}")
        if not canonical.is_dir():
            raise MigrationError(f"canonical path exists but is not a directory: {canonical}")

        canonical_owners = mount_checker(canonical)
        if canonical_owners:
            raise MigrationError(
                "canonical checkpoint is mounted by running container(s): "
                + ", ".join(sorted(canonical_owners))
            )

        manifest = validate_manifest(canonical, require_complete=False)
        if manifest.get("status") == "complete":
            validate_complete_checkpoint(canonical)
            raise MigrationError(
                "canonical path already contains a complete pinned checkpoint while "
                "legacy is still a real directory; manual reconciliation is required"
            )
        backup = backup_candidate(canonical)
    else:
        backup = None

    return MigrationPlan(
        legacy=legacy,
        canonical=canonical,
        backup=backup,
        create_legacy_link=True,
        already_migrated=False,
    )


def apply_plan(plan: MigrationPlan, *, dry_run: bool) -> None:
    print("OrcaRouter checkpoint migration")
    print(f"  legacy    : {plan.legacy}")
    print(f"  canonical : {plan.canonical}")
    print(f"  backup    : {plan.backup or '-'}")

    if plan.already_migrated:
        print("  status    : already migrated; canonical checkpoint is complete")
        return

    if dry_run:
        if plan.backup is not None:
            print(f"DRY-RUN: mv {plan.canonical} {plan.backup}")
        if plan.legacy.is_dir():
            print(f"DRY-RUN: mv {plan.legacy} {plan.canonical}")
        if plan.create_legacy_link:
            print(f"DRY-RUN: ln -s {plan.canonical} {plan.legacy}")
        print("DRY-RUN: no files changed.")
        return

    plan.canonical.parent.mkdir(parents=True, exist_ok=True)

    if plan.backup is not None:
        os.replace(plan.canonical, plan.backup)

    if plan.legacy.is_dir():
        os.replace(plan.legacy, plan.canonical)

    if plan.create_legacy_link:
        plan.legacy.symlink_to(plan.canonical, target_is_directory=True)

    validate_complete_checkpoint(plan.canonical)
    if not plan.legacy.is_symlink() or plan.legacy.resolve(strict=False) != plan.canonical:
        raise MigrationError("legacy compatibility symlink verification failed")

    print("  status    : migrated and verified")


def parser() -> argparse.ArgumentParser:
    script_root = Path(__file__).resolve().parents[2]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--legacy-dir", type=Path, default=script_root / "model")
    p.add_argument(
        "--canonical-dir",
        type=Path,
        default=Path.home() / "models/qwen3.8-flash-next-orcarouter",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", action="store_true")
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        plan = prepare_plan(args.legacy_dir, args.canonical_dir)
        if not args.dry_run and not args.yes and not plan.already_migrated:
            answer = input("Type MIGRATE to apply this checkpoint migration: ")
            if answer != "MIGRATE":
                raise MigrationError("cancelled")
        apply_plan(plan, dry_run=args.dry_run)
    except MigrationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
