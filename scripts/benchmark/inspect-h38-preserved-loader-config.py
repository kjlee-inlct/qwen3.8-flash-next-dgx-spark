#!/usr/bin/env python3
"""Attest H38 loader launch flags from a preserved, already-captured Docker archive.

Reads only pre-existing files. Does not call Docker, torch, vLLM, CUDA, or
run a model. No secret environment values or host mount source paths printed.
Absent launch flags are NOT interpreted as effective vLLM defaults.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

IMAGE = "vllm-orcarouter-v029-h38-decoder-scope:v1"
IMAGE_ID = "sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc"
MODEL_MOUNT = "/model"
MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_LOG_BYTES = 1024 * 1024
KNOWN_FLAGS = (
    "--load-format",
    "--safetensors-load-strategy",
    "--safetensors-prefetch-num-threads",
    "--safetensors-prefetch-block-size",
    "--model-loader-extra-config",
    "--tensor-parallel-size",
    "--pipeline-parallel-size",
    "--enable-expert-parallel",
    "--no-enable-expert-parallel",
    "--distributed-executor-backend",
    "--speculative-config",
)
SENSITIVE_VALUE_FLAGS = frozenset({"--model-loader-extra-config"})
SAFE_ENV_KEYS = (
    "VLLM_PLE_MMAP",
    "VLLM_QSA_EXACT_TOPK",
    "QWEN38_MARLIN_CANONICAL_ORDER",
    "QWEN38_MARLIN_CANONICAL_SCOPE",
)
FORBIDDEN_SECRETS = re.compile(r"(?:TOKEN|PASSWORD|SECRET|API_KEY|CREDENTIAL)", re.I)


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def read_limited(path: Path, limit: int, *, required: bool) -> str | None:
    if not path.exists():
        if required:
            raise ValueError("missing_capture:" + path.name)
        return None
    require(path.is_file() and not path.is_symlink(),
            "unsafe_or_non_file_capture:" + path.name)
    require(path.stat().st_size <= limit, "capture_exceeds_limit:" + path.name)
    return path.read_text(encoding="utf-8", errors="strict")


def read_json(path: Path, *, required: bool = True) -> Any | None:
    raw = read_limited(path, MAX_JSON_BYTES, required=required)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("capture_invalid_json:" + path.name) from exc


def flag_values(cmd: list[str], flag: str) -> list[str]:
    values: list[str] = []
    for i, arg in enumerate(cmd):
        if arg == flag:
            if flag.startswith("--no-") or flag == "--enable-expert-parallel":
                values.append("present")
            else:
                require(i + 1 < len(cmd) and not cmd[i + 1].startswith("--"),
                        "missing_flag_value:" + flag)
                values.append(cmd[i + 1])
        elif arg.startswith(flag + "="):
            values.append(arg.split("=", 1)[1])
    return values


def summarize_flag(cmd: list[str], flag: str) -> dict[str, object]:
    vals = flag_values(cmd, flag)
    require(len(vals) <= 1, "ambiguous_duplicate_flag:" + flag)
    if not vals:
        return {"state": "NOT_EXPLICIT", "value": None}
    value = vals[0]
    if flag in SENSITIVE_VALUE_FLAGS:
        try:
            object_value = json.loads(value)
        except json.JSONDecodeError:
            return {"state": "EXPLICIT_UNPARSED_REDACTED", "value": None}
        if not isinstance(object_value, dict):
            return {"state": "EXPLICIT_INVALID_OBJECT_REDACTED", "value": None}
        allowed = {}
        for key in ("enable_multithread_load", "num_threads"):
            if key in object_value:
                item = object_value[key]
                if key == "enable_multithread_load" and type(item) is bool:
                    allowed[key] = item
                elif key == "num_threads" and type(item) is int and 0 < item <= 4096:
                    allowed[key] = item
                else:
                    allowed[key] = "INVALID_TYPE"
        return {
            "state": "EXPLICIT_WHITELISTED",
            "value": allowed,
            "other_fields_present_count": len(object_value) - len(allowed),
        }
    if flag == "--speculative-config":
        return {"state": "EXPLICIT_REDACTED", "value": None}
    if flag not in ("--load-format", "--safetensors-load-strategy",
                    "--tensor-parallel-size", "--pipeline-parallel-size",
                    "--distributed-executor-backend",
                    "--safetensors-prefetch-num-threads",
                    "--safetensors-prefetch-block-size",
                    "--enable-expert-parallel", "--no-enable-expert-parallel"):
        return {"state": "EXPLICIT_REDACTED", "value": None}
    require(len(value) <= 128 and not FORBIDDEN_SECRETS.search(value),
            "sensitive_or_long_flag_value:" + flag)
    return {"state": "EXPLICIT", "value": value}


def analyze(archive_dir: Path) -> dict[str, object]:
    require(archive_dir.is_absolute(), "absolute_evidence_dir_required")
    require(archive_dir.is_dir() and not archive_dir.is_symlink(),
            "archive_directory_missing_or_symlink")
    obj = read_json(archive_dir / "candidate-inspect.json")
    require(isinstance(obj, list) and len(obj) == 1 and isinstance(obj[0], dict),
            "invalid_docker_inspect_shape")
    data = obj[0]
    config = data.get("Config")
    require(isinstance(config, dict), "missing_docker_config")
    require(config.get("Image") == IMAGE, "candidate_image_tag_mismatch")
    require(data.get("Image") == IMAGE_ID, "candidate_image_id_mismatch")
    cmd = config.get("Cmd")
    require(isinstance(cmd, list) and all(isinstance(x, str) for x in cmd),
            "missing_or_invalid_cmd_tokens")
    saved_cmd = read_json(archive_dir / "candidate-cmd.json")
    require(saved_cmd == cmd, "saved_cmd_differs_from_inspect")

    mounts = data.get("Mounts")
    require(isinstance(mounts, list), "missing_mounts")
    require(any(isinstance(m, dict) and m.get("Destination") == MODEL_MOUNT
                and isinstance(m.get("Source"), str) for m in mounts),
            "missing_model_mount")

    env = config.get("Env")
    require(isinstance(env, list) and all(isinstance(x, str) for x in env),
            "invalid_docker_env")
    env_pairs = dict(item.split("=", 1) for item in env if "=" in item)
    # Historical runner had a real identity assertion requiring these.
    expected = {
        "VLLM_PLE_MMAP": "1",
        "VLLM_QSA_EXACT_TOPK": "1",
        "QWEN38_MARLIN_CANONICAL_ORDER": "1",
        "QWEN38_MARLIN_CANONICAL_SCOPE": "decoder",
    }
    require(all(env_pairs.get(k) == v for k, v in expected.items()),
            "H38_runtime_lineage_env_mismatch")
    flags = {flag.removeprefix("--").replace("-", "_"): summarize_flag(cmd, flag)
             for flag in KNOWN_FLAGS}
    log = read_limited(archive_dir / "startup-phase.txt", MAX_LOG_BYTES,
                       required=False)
    if log is None:
        log = read_limited(archive_dir / "candidate-container.log",
                           MAX_LOG_BYTES, required=False)
    # These strings describe log evidence only, not inferred effective config.
    prefetch_log = (
        "AUTO_PREFETCH_DISABLED_LOG_OBSERVED"
        if log is not None and "Auto-prefetch is disabled" in log
        else "NO_PREFETCH_LOG_EVIDENCE"
    )
    mtp_spec = flags["speculative_config"]
    return {
        "archive_kind": "preserved_h38_mtp_none_candidate_inspect",
        "captured_image_tag_verified": True,
        "captured_image_id_verified": True,
        "captured_cmd_pair_consistent": True,
        "captured_model_mount_present": True,
        "captured_h38_env_lineage_verified": True,
        "recorded_safetensors_prefetch_log": prefetch_log,
        "recorded_speculative_config": mtp_spec,
        "explicit_loader_cli_flags": flags,
        "actual_effective_vllm_load_config_proven": False,
        "actual_tensor_iteration_proven": False,
        "base_vs_mtp_tensor_io_proven": False,
        "ct_meta_layer_completion_proven": False,
        "safe_peak_weight_buffers_proven": False,
        "host_stability_qualified": False,
        "metadata_order_gate_overridden": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = analyze(args.archive_dir)
    except (OSError, ValueError, UnicodeError, TypeError) as exc:
        print("H38_PRESERVED_LOADER_CONFIG=INVALID reason=" + str(exc),
              file=sys.stderr)
        return 2
    print("H38_PRESERVED_LOADER_CONFIG=BEGIN")
    print(json.dumps(result, sort_keys=True, indent=2))
    print("H38_PRESERVED_LOADER_CONFIG=END")
    print("H38_PRESERVED_LOADER_CONFIG_GATE=PASS_ARCHIVED_LAUNCH_FLAGS_ONLY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
