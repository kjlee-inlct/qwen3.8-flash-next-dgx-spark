#!/usr/bin/env python3
"""Strict parser for small qwen38 lifecycle state files.

The parser never evaluates shell syntax. It accepts only whitelisted keys and
schema-specific values, rejects duplicates/unknown keys, and emits NUL-delimited
key/value pairs for safe consumption by Bash via `read -d ''` + `printf -v`.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Callable


Validator = Callable[[str], bool]

HEX_RELEASE = re.compile(r"[0-9a-f]{12,40}\Z")
HEX_CONTAINER = re.compile(r"[0-9a-f]{12,128}\Z")
TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
SAFE_NAME = re.compile(r"[A-Za-z0-9_.-]+\Z")


def exact(expected: str) -> Validator:
    return lambda value: value == expected


def one_of(*values: str) -> Validator:
    allowed = set(values)
    return lambda value: value in allowed


def matches(pattern: re.Pattern[str]) -> Validator:
    return lambda value: pattern.fullmatch(value) is not None


def optional(validator: Validator) -> Validator:
    return lambda value: value == "" or validator(value)


def absolute_path(value: str) -> bool:
    """Accept a simple absolute path without whitespace or shell metacharacters."""

    return (
        value.startswith("/")
        and value != "/"
        and not any(ch.isspace() for ch in value)
        and not any(ch in value for ch in ("'", '"', "`", "\\", "$", ";"))
    )


SCHEMAS: dict[str, dict[str, Validator]] = {
    "update": {
        "UPDATE_SCHEMA_VERSION": exact("1"),
        "UPDATE_STATE": one_of("preparing", "staged"),
        "TARGET_RELEASE": matches(HEX_RELEASE),
        "OLD_CURRENT_RELEASE": optional(matches(HEX_RELEASE)),
        "OLD_PREVIOUS_RELEASE": optional(matches(HEX_RELEASE)),
        "UPDATED_AT": matches(TIMESTAMP),
    },
    "qualification": {
        "QUALIFICATION_SCHEMA_VERSION": exact("1"),
        "QUALIFIED_RELEASE": matches(HEX_RELEASE),
        "QUALIFIED_AT": matches(TIMESTAMP),
    },
    "runtime-stop": {
        "RUNTIME_STOP_SCHEMA_VERSION": exact("1"),
        "STOP_REASON": exact("memory-protection"),
        "STOP_CONTAINER_NAME": matches(SAFE_NAME),
        "STOP_CONTAINER_ID": matches(HEX_CONTAINER),
        "UPDATED_AT": matches(TIMESTAMP),
    },
    "runtime-commit": {
        "RUNTIME_COMMIT_SCHEMA_VERSION": exact("1"),
        "RUNTIME_ROOT": absolute_path,
        "RUNTIME_CONTAINER_NAME": matches(SAFE_NAME),
        "RUNTIME_CONTAINER_ID": matches(HEX_CONTAINER),
        "COMMITTED_AT": matches(TIMESTAMP),
    },
}


def decode_legacy_value(raw: str) -> str:
    """Accept the legacy `%q` encoding only for the empty string.

    Existing lifecycle files use values made entirely from safe characters, so
    `%q` wrote them unchanged except that an empty value was written as `''`.
    Anything else that looks shell-escaped is rejected instead of interpreted.
    """

    if raw == "''":
        return ""
    if any(ch in raw for ch in ("'", '"', "`", "\\", "$", ";")):
        raise ValueError("shell syntax is not allowed in state values")
    return raw


def parse_state(path: Path, schema_name: str) -> dict[str, str]:
    schema = SCHEMAS[schema_name]
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read state file: {exc}") from exc

    values: dict[str, str] = {}
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line:
            continue
        if "=" not in line:
            raise ValueError(f"line {lineno}: expected KEY=value")
        key, raw = line.split("=", 1)
        if key not in schema:
            raise ValueError(f"line {lineno}: unknown key: {key}")
        if key in values:
            raise ValueError(f"line {lineno}: duplicate key: {key}")
        value = decode_legacy_value(raw)
        if not schema[key](value):
            raise ValueError(f"line {lineno}: invalid value for {key}")
        values[key] = value

    missing = [key for key in schema if key not in values]
    if missing:
        raise ValueError(f"missing required key(s): {', '.join(missing)}")
    return values


def emit_nul(values: dict[str, str], schema_name: str) -> None:
    out = sys.stdout.buffer
    for key in SCHEMAS[schema_name]:
        out.write(key.encode("utf-8") + b"\0")
        out.write(values[key].encode("utf-8") + b"\0")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("schema", choices=sorted(SCHEMAS))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        values = parse_state(args.path, args.schema)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    emit_nul(values, args.schema)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
