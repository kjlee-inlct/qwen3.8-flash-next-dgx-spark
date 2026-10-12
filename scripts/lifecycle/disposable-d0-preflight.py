#!/usr/bin/env python3
"""Offline D0 disposable-host evidence review; NEVER grants live E2E admission.

Reads only two operator-supplied JSON files. It does not inspect, connect to,
start, stop, install, remove, or change any host, service, Docker daemon, or GPU.
JSON is an untrusted assertion, not a signed machine identity attestation.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from pathlib import Path, PurePosixPath
from typing import Any

MAX_JSON_BYTES = 65536
MAX_FIXTURE_BYTES = 64 * 1024 * 1024
SHA40 = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
REPO = "kjlee-inlct/qwen3.8-flash-next-dgx-spark"


class PreflightRefusal(ValueError):
    """One stable, non-sensitive refusal code."""


def reject(code: str) -> None:
    raise PreflightRefusal(code)


def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            reject("duplicate_json_field")
        result[key] = value
    return result


def read_json(path: Path) -> dict[str, Any]:
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_JSON_BYTES:
            reject("unsafe_or_oversized_evidence_file")
        with path.open("rb") as source:
            data = source.read(MAX_JSON_BYTES + 1)
        if len(data) > MAX_JSON_BYTES:
            reject("oversized_evidence_file")
        item = json.loads(data, object_pairs_hook=unique_pairs)
    except PreflightRefusal:
        raise
    except (OSError, ValueError, UnicodeError, TypeError):
        reject("unreadable_or_invalid_json")
    if type(item) is not dict:
        reject("json_object_required")
    return item


def shape(value: Any, keys: tuple[str, ...], code: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != set(keys):
        reject(code)
    return value


def text(value: Any, code: str) -> str:
    if type(value) is not str or not value or any(c in value for c in "\x00\r\n"):
        reject(code)
    return value


def digest(value: Any, pattern: re.Pattern[str], code: str) -> str:
    string = text(value, code)
    if pattern.fullmatch(string) is None:
        reject(code)
    return string


def unique_strings(value: Any, code: str) -> list[str]:
    if type(value) is not list or not value or not all(type(x) is str and x for x in value):
        reject(code)
    if len(value) != len(set(value)):
        reject(code)
    return value


def safe_path(value: Any, code: str) -> str:
    path = text(value, code)
    if not path.startswith("/") or path == "/" or "//" in path or os.path.normpath(path) != path:
        reject(code)
    if any(x in (".", "..") for x in PurePosixPath(path).parts):
        reject(code)
    return path


def under(candidate: str, root: str) -> bool:
    return os.path.commonpath((candidate, root)) == root


def validate(policy: dict[str, Any], inventory: dict[str, Any]) -> None:
    shape(policy, (
        "schema_version", "expected_repo", "expected_sha",
        "protected_machine_id_hashes", "protected_docker_daemon_ids",
        "forbidden_roots",
    ), "policy_schema")
    shape(inventory, (
        "schema_version", "git", "host", "docker", "paths",
        "fixture", "service", "pending_transactions",
    ), "inventory_schema")
    if type(policy["schema_version"]) is not int or policy["schema_version"] != 1:
        reject("policy_version")
    if type(inventory["schema_version"]) is not int or inventory["schema_version"] != 1:
        reject("inventory_version")
    if policy["expected_repo"] != REPO:
        reject("unexpected_policy_repo")
    expected_sha = digest(policy["expected_sha"], SHA40, "policy_sha")
    protected = unique_strings(policy["protected_machine_id_hashes"], "protected_machine_set")
    for candidate in protected:
        digest(candidate, SHA256, "protected_machine_hash")
    docker_ids = unique_strings(policy["protected_docker_daemon_ids"], "protected_docker_set")
    forbidden = [safe_path(v, "forbidden_root") for v in unique_strings(policy["forbidden_roots"], "forbidden_root_set")]

    git = shape(inventory["git"], ("sha", "origin", "clean"), "git_schema")
    if digest(git["sha"], SHA40, "git_sha") != expected_sha:
        reject("unexpected_checkout_sha")
    origin = text(git["origin"], "git_origin")
    if origin.removesuffix(".git") not in (
        "https://github.com/" + REPO, "git@github.com:" + REPO
    ):
        reject("unexpected_git_origin")
    if git["clean"] is not True:
        reject("dirty_or_unverified_checkout")

    host = shape(inventory["host"], (
        "machine_id_sha256", "host_id", "architecture",
        "owner_declares_disposable", "restore_point",
    ), "host_schema")
    current_machine = digest(host["machine_id_sha256"], SHA256, "host_machine_hash")
    if current_machine in protected:
        reject("protected_host_identity")
    for field in ("host_id", "architecture", "restore_point"):
        text(host[field], "missing_host_" + field)
    if host["owner_declares_disposable"] is not True:
        reject("disposable_owner_declaration_missing")

    docker = shape(inventory["docker"], (
        "daemon_id", "context", "isolated", "external_users",
    ), "docker_schema")
    if text(docker["daemon_id"], "docker_daemon_id") in docker_ids:
        reject("protected_docker_daemon")
    if text(docker["context"], "docker_context") in ("default", "desktop-linux"):
        reject("shared_or_default_docker_context")
    if docker["isolated"] is not True or docker["external_users"] is not False:
        reject("docker_isolation_unproven")

    paths = shape(inventory["paths"], (
        "work_root", "model_root", "log_root",
    ), "paths_schema")
    roots = [safe_path(paths[key], "unsafe_" + key) for key in (
        "work_root", "model_root", "log_root"
    )]
    for i, candidate in enumerate(roots):
        if any(under(candidate, path) or under(path, candidate) for path in forbidden):
            reject("overlap_with_protected_root")
        if any(under(candidate, x) or under(x, candidate) for x in roots[:i]):
            reject("overlapping_disposable_roots")
        if any(under(candidate, x) for x in (
            "/dev", "/proc", "/sys", "/etc", "/root", "/home", "/var/lib/docker",
        )):
            reject("unsafe_system_path")

    fixture = shape(inventory["fixture"], (
        "model_bytes", "is_production_checkpoint", "owned",
    ), "fixture_schema")
    size = fixture["model_bytes"]
    if type(size) is not int or not 0 < size <= MAX_FIXTURE_BYTES:
        reject("fixture_size_not_bounded")
    if fixture["is_production_checkpoint"] is not False or fixture["owned"] is not True:
        reject("fixture_ownership_or_production_risk")

    service = shape(inventory["service"], ("unit", "exclusive"), "service_schema")
    unit = text(service["unit"], "service_unit")
    if re.fullmatch(r"qwen38-d0-[a-z0-9-]+\.service", unit) is None or service["exclusive"] is not True:
        reject("nonexclusive_or_production_service")

    if inventory["pending_transactions"] != [] or type(inventory["pending_transactions"]) is not list:
        reject("pending_or_unknown_transactions")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        validate(read_json(args.policy), read_json(args.inventory))
    except PreflightRefusal as exc:
        print("D0_STATIC_REVIEW=REFUSED")
        print("D0_REFUSAL=" + str(exc))
        print("D0_ADMISSION=NOT_GRANTED")
        return 2
    print("D0_STATIC_REVIEW=READY_FOR_INDEPENDENT_REVIEW")
    print("D0_ADMISSION=NOT_GRANTED")
    print("D0_REAL_HOST_VERIFICATION=NOT_PERFORMED")
    print("D0_LIVE_E2E=NOT_AUTHORIZED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
