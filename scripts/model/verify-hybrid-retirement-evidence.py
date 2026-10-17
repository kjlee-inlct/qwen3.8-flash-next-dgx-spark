#!/usr/bin/env python3
"""Read-only verification of local Hybrid evidence; never authorizes deletion."""
import hashlib
import os
from pathlib import Path
import sys

ORIGINAL = ("active.json", "trial.json", "monitor.log", "runtime-stop.env",
            "docker-inspect.json", "docker.log", "kernel-window.log")
CONTAINERS = ("container-metadata.jsonl",
              "qwen38-hybrid-h6-m1-20261014141803-69ef3492.log",
              "qwen38-hybrid-r24-kv16.log",
              "qwen38-hybrid-r25b-init-marker.log",
              "qwen38-hybrid-r26-construction-marker.log",
              "qwen38-hybrid-r27-linear-marker.log",
              "qwen38-hybrid-r28-unquant-linear-marker.log")


def verify(root: Path, manifest: str, expected: tuple[str, ...]) -> tuple[bool, str]:
    if root.is_symlink() or not root.is_dir():
        return False, "ARCHIVE_DIRECTORY_MISSING_OR_SYMLINK"
    checksum = root / manifest
    if checksum.is_symlink() or not checksum.is_file():
        return False, "CHECKSUM_MANIFEST_MISSING_OR_SYMLINK"
    try:
        entries = {}
        for line in checksum.read_text(encoding="utf-8").splitlines():
            if len(line) < 67 or line[64:66] not in ("  ", " *"):
                return False, "INVALID_MANIFEST_FORMAT"
            digest, name = line[:64], line[66:]
            if len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
                return False, "INVALID_HASH"
            if name not in expected or name in entries:
                return False, "UNEXPECTED_OR_DUPLICATE_FILE"
            entries[name] = digest.lower()
        if set(entries) != set(expected):
            return False, "INCOMPLETE_FILE_SET"
        for name, digest in entries.items():
            path = root / name
            if path.is_symlink() or not path.is_file():
                return False, "MISSING_OR_SYMLINK_FILE"
            h = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    h.update(block)
            if h.hexdigest() != digest:
                return False, "CHECKSUM_MISMATCH"
    except (OSError, UnicodeError):
        return False, "ARCHIVE_READ_ERROR"
    return True, "PASS"


def main() -> int:
    if len(sys.argv) != 1:
        print("Usage: python3 scripts/model/verify-hybrid-retirement-evidence.py", file=sys.stderr)
        return 2
    home = Path.home()
    roots = (
        (home / "h6-m1-evidence-20261014.dvQmt6eq", "SHA256SUMS.txt", ORIGINAL, "H6_ORIGINAL"),
        (home / ".local/state/qwen38-spark/hybrid-retirement-evidence",
         "SHA256SUMS.txt", CONTAINERS, "SIX_CONTAINERS"),
    )
    all_good = True
    for path, manifest, expected, label in roots:
        ok, reason = verify(path, manifest, expected)
        print(f"{label}_SHA256={reason} files={len(expected)}")
        all_good &= ok
    print("OFF_HOST_BACKUP=NOT_VERIFIED")
    print("HYBRID_DELETE_AUTHORIZATION=NO")
    print("LOCAL_EVIDENCE_VERIFICATION=" + ("PASS" if all_good else "BLOCKED"))
    return 0 if all_good else 3


if __name__ == "__main__":
    raise SystemExit(main())
