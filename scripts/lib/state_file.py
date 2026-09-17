#!/usr/bin/env python3
"""Strict parsers for qwen38 state and install manifest files.

No parser evaluates shell syntax. Lifecycle files use a small KEY=value format.
The installer manifest parser additionally decodes the subset of Bash ``printf
%q`` output used by install.sh, without invoking a shell, so existing manifests
with escaped whitespace remain compatible.
"""

from __future__ import annotations

import argparse
import re
import shlex
import sys
from pathlib import Path
from typing import Callable


Validator = Callable[[str], bool]

HEX_RELEASE = re.compile(r"[0-9a-f]{12,40}\Z")
HEX_CONTAINER = re.compile(r"[0-9a-f]{12,128}\Z")
TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
SAFE_NAME = re.compile(r"[A-Za-z0-9_.-]+\Z")
POSITIVE_INTEGER = re.compile(r"[1-9][0-9]*\Z")
NONNEGATIVE_INTEGER = re.compile(r"[0-9]+\Z")


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
    return value.startswith("/") and value != "/" and "\x00" not in value and "\n" not in value and "\r" not in value


def nonempty_text(value: str) -> bool:
    return bool(value) and "\x00" not in value and "\n" not in value and "\r" not in value


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

# install.sh schema 3/4 fields. Keeping a closed set means an injected shell
# assignment cannot silently become part of any consumer environment.
INSTALL_KEYS = {
    "SCHEMA_VERSION", "PHASE", "INSTALL_ROOT", "MODEL_PROFILE", "MODEL_REPO", "MODEL_REVISION",
    "MODEL_DIR", "MODEL_OWNED", "SWAP_FILE", "SWAP_OWNED", "VLLM_IMAGE", "IMAGE_OWNED",
    "SERVED_NAME", "CONTAINER_NAME", "CONFIG_OVERRIDE", "CONFIG_OWNED", "MONITOR_PROTECT",
    "MONITOR_ENABLED", "MONITOR_MIN_AVAILABLE_GIB", "MONITOR_MIN_FREE_GIB", "MONITOR_FREE_GATE_GIB",
    "MONITOR_MIN_SWAP_FREE_GIB", "MONITOR_CONSECUTIVE", "MONITOR_HEARTBEAT", "API_ACCESS_MODE",
    "API_DOCKER_PORT", "API_LAN_ADDRESS", "API_LAN_PORT", "PROXY_ENABLED", "PROXY_OWNED",
    "PROXY_PORT", "SERVICE_ENABLED", "SERVICE_OWNED", "SERVICE_UNIT", "UI_LANG",
}

INSTALL_RUNTIME_SCHEMA: dict[str, Validator] = {
    "SCHEMA_VERSION": one_of("3", "4"),
    "PHASE": exact("complete"),
    "MODEL_PROFILE": one_of("orcarouter", "nvidia"),
    "MODEL_DIR": absolute_path,
    "VLLM_IMAGE": nonempty_text,
    "SERVED_NAME": nonempty_text,
    "CONTAINER_NAME": exact("qwen38-flash-next"),
    "CONFIG_OVERRIDE": optional(absolute_path),
    "MONITOR_PROTECT": one_of("0", "1"),
    "MONITOR_ENABLED": one_of("0", "1"),
    "MONITOR_MIN_AVAILABLE_GIB": matches(POSITIVE_INTEGER),
    "MONITOR_MIN_FREE_GIB": matches(POSITIVE_INTEGER),
    "MONITOR_FREE_GATE_GIB": matches(POSITIVE_INTEGER),
    "MONITOR_MIN_SWAP_FREE_GIB": matches(POSITIVE_INTEGER),
    "MONITOR_CONSECUTIVE": matches(POSITIVE_INTEGER),
    "MONITOR_HEARTBEAT": matches(NONNEGATIVE_INTEGER),
}

INSTALL_SERVICE_SCHEMA: dict[str, Validator] = {
    "SCHEMA_VERSION": one_of("3", "4"),
    "PHASE": exact("complete"),
    "INSTALL_ROOT": absolute_path,
    "SERVED_NAME": nonempty_text,
    "CONTAINER_NAME": exact("qwen38-flash-next"),
}

INSTALL_SCHEMAS = {
    "install-runtime": INSTALL_RUNTIME_SCHEMA,
    "install-service": INSTALL_SERVICE_SCHEMA,
}


def decode_legacy_value(raw: str) -> str:
    if raw == "''":
        return ""
    if any(ch in raw for ch in ("'", '"', "`", "\\", "$", ";")):
        raise ValueError("shell syntax is not allowed in state values")
    return raw


def decode_bash_printf_q(raw: str) -> str:
    """Decode non-executable ``printf %q`` output used by install.sh."""
    if raw.startswith("$'"):
        raise ValueError("ANSI-C shell quoting is not allowed in install manifest values")
    try:
        words = shlex.split(raw, posix=True)
    except ValueError as exc:
        raise ValueError(f"invalid shell-escaped install value: {exc}") from exc
    if len(words) != 1:
        if raw == "''":
            return ""
        raise ValueError("install manifest value must decode to exactly one word")
    value = words[0]
    if any(ch in value for ch in ("\x00", "\n", "\r")):
        raise ValueError("control characters are not allowed in install manifest values")
    return value


def read_assignments(path: Path) -> list[tuple[int, str, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read state file: {exc}") from exc
    assignments: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line:
            continue
        if "=" not in line:
            raise ValueError(f"line {lineno}: expected KEY=value")
        key, raw = line.split("=", 1)
        if not SAFE_NAME.fullmatch(key):
            raise ValueError(f"line {lineno}: invalid key")
        assignments.append((lineno, key, raw))
    return assignments


def parse_state(path: Path, schema_name: str) -> dict[str, str]:
    schema = SCHEMAS[schema_name]
    values: dict[str, str] = {}
    for lineno, key, raw in read_assignments(path):
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


def parse_install(path: Path, schema_name: str) -> dict[str, str]:
    schema = INSTALL_SCHEMAS[schema_name]
    values: dict[str, str] = {}
    for lineno, key, raw in read_assignments(path):
        if key not in INSTALL_KEYS:
            raise ValueError(f"line {lineno}: unknown install manifest key: {key}")
        if key in values:
            raise ValueError(f"line {lineno}: duplicate key: {key}")
        values[key] = decode_bash_printf_q(raw)
    missing = [key for key in schema if key not in values]
    if missing:
        raise ValueError(f"missing required {schema_name} manifest key(s): {', '.join(missing)}")
    for key, validator in schema.items():
        if not validator(values[key]):
            raise ValueError(f"invalid {schema_name} manifest value for {key}")
    if schema_name == "install-runtime" and values["MONITOR_PROTECT"] == "1" and values["MONITOR_ENABLED"] != "1":
        raise ValueError("runtime manifest protection requires monitor enabled")
    return {key: values[key] for key in schema}


def emit_nul(values: dict[str, str], keys: list[str]) -> None:
    out = sys.stdout.buffer
    for key in keys:
        out.write(key.encode("utf-8") + b"\0")
        out.write(values[key].encode("utf-8") + b"\0")


def main() -> int:
    choices = sorted([*SCHEMAS, *INSTALL_SCHEMAS])
    parser = argparse.ArgumentParser()
    parser.add_argument("schema", choices=choices)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        if args.schema in INSTALL_SCHEMAS:
            values = parse_install(args.path, args.schema)
            keys = list(INSTALL_SCHEMAS[args.schema])
        else:
            values = parse_state(args.path, args.schema)
            keys = list(SCHEMAS[args.schema])
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    emit_nul(values, keys)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
