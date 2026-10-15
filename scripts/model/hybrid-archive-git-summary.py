#!/usr/bin/env python3
"""Read-only, Git-safe summary of locally verified Hybrid Docker archive."""
import hashlib
import json
from pathlib import Path
import sys

ARCHIVE = Path.home() / ".local/state/qwen38-spark/retirement-archives/hybrid-docker-17-20261015"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def summarize(root):
    if not root.is_dir() or root.is_symlink():
        raise ValueError("archive root missing or symlink")
    manifest = root / "SHA256SUMS"
    if not manifest.is_file() or manifest.is_symlink():
        raise ValueError("manifest missing or symlink")
    files = [x for x in root.iterdir()]
    if len(files) != 35:
        raise ValueError("expected exactly 35 regular archive entries")
    entries = {}
    for row in manifest.read_text(encoding="utf-8").splitlines():
        if len(row) not in (64 + 2 + 68, 64 + 2 + 69) or row[64:66] != "  ":
            raise ValueError("unexpected sha manifest row")
        digest, name = row[:64], row[66:]
        if (name in entries or not name.endswith((".json", ".log"))
            or len(name.split(".")[0]) != 64
            or any(ch not in "0123456789abcdef" for ch in name.split(".")[0])
            or any(ch not in "0123456789abcdef" for ch in digest)):
            raise ValueError("invalid archive manifest filename or digest")
        entries[name] = digest
    if len(entries) != 34 or set(x.name for x in files) != set(entries) | {"SHA256SUMS"}:
        raise ValueError("archive file inventory mismatch")
    ids = sorted(name[:-5] for name in entries if name.endswith(".json"))
    if len(ids) != 17 or len(set(ids)) != 17:
        raise ValueError("17 unique IDs required")
    for name, digest in entries.items():
        path = root / name
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError("archive digest mismatch")
    for cid in ids:
        obj = json.loads((root / (cid + ".json")).read_text(encoding="utf-8"))
        if (obj.get("id") != cid or obj.get("status") != "exited"
            or obj.get("protected") is not False or not obj.get("hybrid_mounts")
            or cid + ".log" not in entries):
            raise ValueError("archived metadata mismatch")
    return {"schema_version": 1, "record_type": "hybrid_docker_archive_provenance",
            "sha256_manifest": sha256(manifest),
            "files_verified": len(entries), "containers_verified": len(ids),
            "container_ids": ids, "raw_logs_in_git": False,
            "docker_removal_performed": False, "model_removal_performed": False}


def main():
    if len(sys.argv) != 1:
        print("usage: python3 scripts/model/hybrid-archive-git-summary.py", file=sys.stderr)
        return 2
    try:
        print(json.dumps(summarize(ARCHIVE), sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print("HYBRID_GIT_SUMMARY=BLOCKED_" + type(exc).__name__, file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
