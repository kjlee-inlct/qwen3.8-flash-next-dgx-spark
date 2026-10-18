#!/usr/bin/env python3
"""Inspect existing protected OrcaRouter bind sources; never guess a model path.

Read-only only. Validate exact protected Docker IDs/image and mount topology,
then inspect at most the original and nested-override *config.json* files.
No Docker cp/create/run/exec/start/pull/rm, no host write, no model headers,
checkpoint loading, full disk walk, GPU use, or network access.
Only publish fixed classification labels and integer counts, never paths,
environment, mount source values or actual config content.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
from typing import Any

import inspect_ple_postcheck_readonly as guard
import prepare_config

MAX_CONFIG_BYTES = 8 * 1024 * 1024
CONTAINERS = (
    ("MANAGED", guard.probe.EXPECTED_MANAGED_ID),
    ("LEGACY", guard.probe.EXPECTED_LEGACY_ID),
)
IMPORTANT_FIELDS = (
    "architectures", "model_type", "quantization_config", "text_config",
)


class PreflightStop(Exception):
    """Fail closed without printing sensitive exception text."""


def file_category(path: Path) -> str:
    try:
        if path.is_symlink():
            return "SYMLINK_STOP"
        info = path.stat()
        if not stat.S_ISREG(info.st_mode):
            return "NOT_REGULAR_FILE"
        if info.st_size == 0 or info.st_size > MAX_CONFIG_BYTES:
            return "SIZE_OUTSIDE_LIMIT"
        return "REGULAR_BOUNDED_FILE"
    except FileNotFoundError:
        return "NOT_PRESENT"
    except OSError:
        return "INACCESSIBLE"


def read_small_json(path: Path) -> dict[str, Any]:
    if file_category(path) != "REGULAR_BOUNDED_FILE":
        raise PreflightStop("CONFIG_FILE_UNAVAILABLE")
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb", closefd=True) as f:
            info = os.fstat(f.fileno())
            if (not stat.S_ISREG(info.st_mode)
                    or info.st_size < 1 or info.st_size > MAX_CONFIG_BYTES):
                raise PreflightStop("CONFIG_FILE_UNAVAILABLE")
            raw = f.read(MAX_CONFIG_BYTES + 1)
        if not raw or len(raw) > MAX_CONFIG_BYTES:
            raise PreflightStop("CONFIG_FILE_UNAVAILABLE")
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise PreflightStop("CONFIG_ROOT_INVALID")
        return value
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as exc:
        raise PreflightStop("CONFIG_FILE_UNREADABLE_OR_INVALID") from exc


def model_mounts(info: dict[str, Any]) -> tuple[Path, Path]:
    mounts = info.get("Mounts")
    if not isinstance(mounts, list):
        raise PreflightStop("MOUNTS_UNAVAILABLE")
    mapping: dict[str, str] = {}
    for m in mounts:
        if not isinstance(m, dict):
            raise PreflightStop("MOUNT_SCHEMA_INVALID")
        d = m.get("Destination")
        if d in ("/model", "/model/config.json"):
            if d in mapping or m.get("Type") != "bind" or m.get("RW") is not False:
                raise PreflightStop("MOUNT_IDENTITY_OR_PERMISSIONS_INVALID")
            src = m.get("Source")
            if not isinstance(src, str) or not src.startswith("/"):
                raise PreflightStop("MOUNT_SOURCE_UNQUALIFIED")
            mapping[d] = src
    if set(mapping) != {"/model", "/model/config.json"}:
        raise PreflightStop("MODEL_CONFIG_MOUNTS_MISSING")
    return Path(mapping["/model"]), Path(mapping["/model/config.json"])


def layer_counts(config: dict[str, Any]) -> tuple[int, int, int]:
    tc = config.get("text_config")
    if not isinstance(tc, dict):
        return (0, 0, 0)
    ls = tc.get("layer_types")
    if not isinstance(ls, list) or any(not isinstance(t, str) for t in ls):
        return (0, 0, 0)
    return (
        len(ls),
        sum(x == "linear_attention" for x in ls),
        sum(x == "full_attention" for x in ls),
    )


def quant_counts(config: dict[str, Any]) -> tuple[str, int, int, int]:
    q = config.get("quantization_config")
    if not isinstance(q, dict):
        return ("NOT_DECLARED", 0, 0, 0)
    method = q.get("quant_method")
    if method != "compressed-tensors":
        return ("NOT_CT", 0, 0, 0)
    groups = q.get("config_groups")
    ignored = q.get("ignore", [])
    if not isinstance(groups, dict) or not isinstance(ignored, list):
        return ("CT_STRUCTURE_INVALID", 0, 0, 0)
    targets = []
    for item in groups.values():
        if not isinstance(item, dict) or not isinstance(item.get("targets"), list):
            return ("CT_STRUCTURE_INVALID", 0, 0, 0)
        targets += item["targets"]
    if any(not isinstance(x, str) for x in targets + ignored):
        return ("CT_STRUCTURE_INVALID", 0, 0, 0)
    return ("CT_STRUCTURE_READABLE", len(groups), len(targets), len(ignored))


def compare_config(original: dict[str, Any], override: dict[str, Any]) -> str:
    expected, converted = prepare_config.convert_layer_types(original)
    if expected == override:
        return ("EXACT_EXPECTED_LAYER_TYPE_REWRITE" if converted
                else "ORIGINAL_EQUIVALENT")
    if all(original.get(k) == override.get(k) for k in IMPORTANT_FIELDS):
        return "CRITICAL_FIELDS_EQUAL_OTHER_DIFF"
    return "CRITICAL_FIELDS_DIFFER_NOT_ONLY_EXPECTED_REWRITE"


def assess() -> tuple[dict[str, str], bool]:
    result = {
        "operation": "DOCKER_INSPECT_AND_SMALL_CONFIG_READ_ONLY",
        "docker_mutation": "NONE",
        "weights_read": "NONE",
        "gpu_run": "NOT_PERFORMED",
        "original_config_source": "PROTECTED_CONTAINER_BIND_NOT_GUESSED_HOME",
    }
    baseline, permitted = guard.inspect_now()
    result["protected_current_check"] = baseline["current_static_postcheck"]
    if not permitted:
        result["verdict"] = "STOP_PROTECTED_PRECHECK_FAILED"
        return result, False
    entries: dict[str, tuple[Path, Path]] = {}
    for label, cid in CONTAINERS:
        try:
            info = guard.fetch_one("container", cid)
            if info.get("Id") != cid or info.get("Image") != guard.probe.EXPECTED_IMAGE_ID:
                raise PreflightStop("CONTAINER_IDENTITY_CHANGED")
            model_dir, config_override = model_mounts(info)
        except (PreflightStop, guard.ReviewError, guard.probe.ProbeError,
                guard.audit.AttestationError, OSError, ValueError):
            result[label.lower() + "_mount"] = "STOP_UNQUALIFIED"
            result["verdict"] = "STOP_PROTECTED_MOUNT_UNQUALIFIED"
            return result, False
        entries[label] = (model_dir, config_override)
        result[label.lower() + "_mount"] = "EXACT_PROTECTED_RO_BIND"
        result[label.lower() + "_model_root"] = (
            "DIRECTORY_READABLE" if model_dir.is_dir()
            and not model_dir.is_symlink() else "NOT_READABLE_OR_SYMLINK"
        )
        result[label.lower() + "_original_config"] = file_category(model_dir / "config.json")
        result[label.lower() + "_override_config"] = file_category(config_override)
    result["model_sources"] = ("MATCH" if
        entries["MANAGED"][0] == entries["LEGACY"][0] else "DIFFERENT")
    result["override_sources"] = ("MATCH" if
        entries["MANAGED"][1] == entries["LEGACY"][1] else "DIFFERENT")
    if result["model_sources"] != "MATCH" or result["override_sources"] != "MATCH":
        result["verdict"] = "STOP_PROTECTED_MODEL_SOURCES_DIFFER"
        return result, False
    model_dir, override_path = entries["MANAGED"]
    if result["managed_model_root"] != "DIRECTORY_READABLE":
        result["verdict"] = "STOP_MOUNTED_MODEL_ROOT_UNREADABLE"
        return result, False
    if (result["managed_original_config"] != "REGULAR_BOUNDED_FILE"
            or result["managed_override_config"] != "REGULAR_BOUNDED_FILE"):
        result["verdict"] = "STOP_MOUNTED_CONFIG_UNAVAILABLE"
        return result, False
    try:
        original, override = read_small_json(model_dir / "config.json"), read_small_json(override_path)
    except PreflightStop:
        result["verdict"] = "STOP_CONFIG_PARSE_OR_READ"
        return result, False
    result["config_rewrite"] = compare_config(original, override)
    for label, config in (("original", original), ("override", override)):
        n, linear, full = layer_counts(config)
        result[label + "_layer_total"] = str(n)
        result[label + "_linear_attention"] = str(linear)
        result[label + "_full_attention"] = str(full)
        qt, groups, targets, ignored = quant_counts(config)
        result[label + "_quant_structure"] = qt
        result[label + "_ct_groups"] = str(groups)
        result[label + "_ct_targets"] = str(targets)
        result[label + "_ct_ignored"] = str(ignored)
    if any(result[key] == "CT_STRUCTURE_INVALID" for key in (
            "original_quant_structure", "override_quant_structure")):
        result["verdict"] = "STOP_CT_STRUCTURE_INVALID"
        return result, False
    result["community_layer_shape"] = (
        "COUNTS_MATCH_NOT_CONFIG_EQUIVALENCE"
        if (result["override_layer_total"], result["override_linear_attention"],
            result["override_full_attention"]) == ("48", "36", "12")
        else "NOT_IDENTICAL_TO_REPORTED_COUNTS"
    )
    result["verdict"] = "PASS_SOURCE_CONFIG_ONLY_NOT_RUNTIME"
    return result, True


def main() -> int:
    try:
        report, ok = assess()
    except Exception:
        # Never disclose raw Docker inspect, host paths, secrets or JSON.
        print("ORCA_CONFIG_PREFLIGHT=INCONCLUSIVE_UNCLASSIFIED")
        return 2
    for key, value in report.items():
        print(f"ORCA_CONFIG_{key.upper()}={value}")
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
