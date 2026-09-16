#!/usr/bin/env python3
"""Build and verify immutable Qwen release manifests.

The manifest covers ordinary files and symbolic-link targets. Special files are
rejected so a staged release can be treated as a deterministic code payload.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path

MANIFEST_NAME = ".release-manifest.json"
SCHEMA_VERSION = 1


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect_entries(root: Path) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(root).as_posix()
        if relative == MANIFEST_NAME:
            continue
        info = path.lstat()
        if stat.S_ISDIR(info.st_mode):
            continue
        if stat.S_ISREG(info.st_mode):
            entries.append({"path": relative, "type": "file", "sha256": sha256_file(path)})
            continue
        if stat.S_ISLNK(info.st_mode):
            target = os.readlink(path)
            digest = hashlib.sha256(target.encode("utf-8", errors="surrogateescape")).hexdigest()
            entries.append({"path": relative, "type": "symlink", "target": target, "sha256": digest})
            continue
        raise SystemExit(f"unsupported special file in release: {relative}")
    return entries


def build(root: Path, revision: str) -> None:
    manifest_path = root / MANIFEST_NAME
    if manifest_path.exists() or manifest_path.is_symlink():
        raise SystemExit(f"manifest already exists: {manifest_path}")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "revision": revision,
        "files": collect_entries(root),
    }
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify(root: Path, expected_revision: str | None) -> None:
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise SystemExit(f"release manifest is missing or unsafe: {manifest_path}")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise SystemExit("unsupported release manifest schema")
    revision = payload.get("revision")
    if not isinstance(revision, str) or not revision:
        raise SystemExit("release manifest revision is missing")
    if expected_revision is not None and revision != expected_revision:
        raise SystemExit(f"release revision mismatch: expected {expected_revision}, found {revision}")
    current = collect_entries(root)
    if current != payload.get("files"):
        raise SystemExit("release payload differs from immutable manifest")
    print(f"Release manifest verified: revision={revision} files={len(current)}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("root", type=Path)
    build_parser.add_argument("revision")
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("root", type=Path)
    verify_parser.add_argument("--revision")
    args = parser.parse_args()

    root = args.root.resolve()
    if not root.is_dir():
        raise SystemExit(f"release root is not a directory: {root}")
    if args.command == "build":
        build(root, args.revision)
    else:
        verify(root, args.revision)


if __name__ == "__main__":
    main()
