#!/usr/bin/env python3
"""Strict parser for release qualification markers.

Schema 1 is retained only for read-only observability of historical markers.
Schema 2 binds qualification to the SHA-256 digest of .release-manifest.json.
No shell syntax is evaluated.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HEX_RELEASE = re.compile(r"[0-9a-f]{12,40}\Z")
HEX_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
KEY = re.compile(r"[A-Z0-9_]+\Z")

SCHEMA_V1 = {
    "QUALIFICATION_SCHEMA_VERSION",
    "QUALIFIED_RELEASE",
    "QUALIFIED_AT",
}
SCHEMA_V2 = SCHEMA_V1 | {"RELEASE_MANIFEST_SHA256"}


def parse(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read qualification marker: {exc}") from exc
    values: dict[str, str] = {}
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line or "=" not in line:
            raise ValueError(f"line {lineno}: expected KEY=value")
        key, value = line.split("=", 1)
        if not KEY.fullmatch(key):
            raise ValueError(f"line {lineno}: invalid key")
        if key in values:
            raise ValueError(f"line {lineno}: duplicate key: {key}")
        if any(ch in value for ch in ("\x00", "\n", "\r", "`", "$", ";", "'", '"', "\\")):
            raise ValueError(f"line {lineno}: unsafe value for {key}")
        values[key] = value

    version = values.get("QUALIFICATION_SCHEMA_VERSION")
    expected = SCHEMA_V1 if version == "1" else SCHEMA_V2 if version == "2" else None
    if expected is None:
        raise ValueError("unsupported qualification marker schema")
    unknown = sorted(values.keys() - expected)
    missing = sorted(expected - values.keys())
    if unknown:
        raise ValueError(f"unknown qualification key(s): {', '.join(unknown)}")
    if missing:
        raise ValueError(f"missing qualification key(s): {', '.join(missing)}")
    if not HEX_RELEASE.fullmatch(values["QUALIFIED_RELEASE"]):
        raise ValueError("invalid QUALIFIED_RELEASE")
    if not TIMESTAMP.fullmatch(values["QUALIFIED_AT"]):
        raise ValueError("invalid QUALIFIED_AT")
    if version == "2" and not HEX_SHA256.fullmatch(values["RELEASE_MANIFEST_SHA256"]):
        raise ValueError("invalid RELEASE_MANIFEST_SHA256")
    return values


def emit(values: dict[str, str]) -> None:
    out = sys.stdout.buffer
    for key, value in values.items():
        out.write(key.encode() + b"\0" + value.encode() + b"\0")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--require-bound", action="store_true")
    args = parser.parse_args()
    try:
        values = parse(args.path)
        if args.require_bound and values["QUALIFICATION_SCHEMA_VERSION"] != "2":
            raise ValueError("qualification marker is legacy and not manifest-bound")
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    emit(values)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
