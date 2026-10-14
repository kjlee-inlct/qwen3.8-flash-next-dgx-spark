#!/usr/bin/env python3
"""Read-only benchmark evidence verification BEFORE selective model reclamation.

This script verifies repository-bundled per-model report status and file
digests in SHA256SUMS. It NEVER approves deletion, launches models, scans
Docker, accesses the network, or checks off-host backup existence.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import stat
import sys

PROFILES = ("orcarouter", "nvidia", "mazinb",
            "orcarouter-hybrid", "lychee888")
STATUS = re.compile(r"\*\*BENCHMARK_STATUS:\s*(MEASURED|NOT_MEASURED)\*\*")
SUM = re.compile(r"([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9_.-]*)\Z")
CHUNK = 1024 * 1024


def safe_regular(path: Path) -> bool:
    try:
        mode = path.lstat().st_mode
    except OSError:
        return False
    return stat.S_ISREG(mode) and not path.is_symlink()


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while block := file.read(CHUNK):
            digest.update(block)
    return digest.hexdigest()


def verify_set(archive: Path) -> tuple[bool, str, int]:
    """No symlink traversal; limit to simple relative file names."""
    if archive.is_symlink() or not archive.is_dir():
        return False, "archive_directory_unsafe", 0
    manifest = archive / "SHA256SUMS"
    if not safe_regular(manifest):
        return False, "portable_sha256_manifest_missing", 0
    try:
        rows = manifest.read_text(encoding="utf-8").splitlines()
    except (UnicodeError, OSError):
        return False, "sha256_manifest_unreadable", 0
    if not rows or len(rows) > 100:
        return False, "sha256_manifest_empty_or_large", 0
    seen = set()
    types = set()
    checked = 0
    for row in rows:
        match = SUM.fullmatch(row)
        if not match:
            return False, "sha256_manifest_nonportable", checked
        expected, name = match.groups()
        if name in seen or name in (".", ".."):
            return False, "sha256_manifest_duplicate_or_invalid", checked
        seen.add(name)
        target = archive / name
        if not safe_regular(target):
            return False, "artifact_missing_or_unsafe", checked
        try:
            actual = checksum(target)
        except OSError:
            return False, "artifact_unreadable", checked
        if actual != expected:
            return False, "artifact_sha256_mismatch", checked
        types.add(target.suffix.lower())
        checked += 1
    if ".json" not in types or ".md" not in types:
        return False, "raw_json_or_markdown_missing", checked
    return True, "digest_verified", checked


def inspect(root: Path) -> tuple[list[str], int]:
    reports = root / "docs" / "model-reports"
    lines = [
        "BENCHMARK_RECLAIM_AUDIT=READ_ONLY",
        "BENCHMARK_RECLAIM_AUTO_DELETE=FORBIDDEN",
        "BENCHMARK_RECLAIM_HOST_FREE_SPACE=NOT_CHECKED",
    ]
    error = False
    for profile in PROFILES:
        report = reports / (profile + ".md")
        if not safe_regular(report):
            lines.append(f"BENCHMARK_PROFILE={profile} RESULT=REPORT_MISSING")
            error = True
            continue
        try:
            found = STATUS.findall(report.read_text(encoding="utf-8"))
        except (UnicodeError, OSError):
            found = []
        if not found or len(set(found)) != 1:
            lines.append(f"BENCHMARK_PROFILE={profile} RESULT=STATUS_UNVERIFIED")
            error = True
            continue
        if found[0] == "NOT_MEASURED":
            lines.append(f"BENCHMARK_PROFILE={profile} RESULT=NOT_MEASURED HOLD")
            continue
        base = reports / "evidence" / profile
        if base.is_symlink() or not base.is_dir():
            lines.append(f"BENCHMARK_PROFILE={profile} RESULT=ARCHIVE_MISSING")
            error = True
            continue
        archives = sorted(p for p in base.iterdir() if p.is_dir() and not p.is_symlink())
        if not archives:
            lines.append(f"BENCHMARK_PROFILE={profile} RESULT=ARCHIVE_MISSING")
            error = True
            continue
        verified = 0
        for archive in archives:
            good, reason, count = verify_set(archive)
            lines.append(
                f"BENCHMARK_ARCHIVE={profile}/{archive.name} "
                f"RESULT={'SHA256_OK' if good else 'BLOCKED'} "
                f"FILES={count} DETAIL={reason}"
            )
            if good:
                verified += 1
            else:
                error = True
        lines.append(
            f"BENCHMARK_PROFILE={profile} RESULT="
            f"{'MEASURED_ARCHIVE_VERIFIED' if verified else 'ARCHIVE_UNVERIFIED'} "
            "RECLAIM=NOT_AUTHORIZED"
        )
        if not verified:
            error = True
    lines.extend([
        "RECLAIM_REQUIRES=PER_TARGET_DEPENDENCY_REVIEW,INDEPENDENT_ARCHIVE_COPY,"
        "ARCHIVE_SHA256_VERIFICATION,EXACT_DRY_RUN,OWNER_APPROVAL",
        "RECLAIM_ACTUAL_DELETION=NOT_PERFORMED",
        "BENCHMARK_RECLAIM_AUDIT_RESULT=" + ("INCOMPLETE" if error else "COLLECTED"),
    ])
    return lines, (2 if error else 0)


def main() -> int:
    if len(sys.argv) != 1:
        print("ERROR: arguments not supported", file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parents[2]
    lines, rc = inspect(root)
    for line in lines:
        print(line)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
