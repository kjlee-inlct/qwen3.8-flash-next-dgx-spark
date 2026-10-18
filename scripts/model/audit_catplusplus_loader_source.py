#!/usr/bin/env python3
"""Bounded source-only catplusplus mixed-loader/PLE inspection.

Never fetch weights, bundles, indexes, wildcards, or arbitrary paths.
Never invoke publisher-provided shell scripts, Docker, GPU, or subprocesses.
Only two explicitly approved small text paths on the immutable HF revision,
or offline test fixtures. A positive source-surface assessment is NOT
proof an installed SGLang/vLLM wheel implements these features.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request

MODEL = "catplusplus/Qwen3.8-Flash-Next-uncensored-NVFP4-mixed"
REVISION = "3251fd8afbd08f76368a9bfa71132d9aef364813"
BASE = f"https://huggingface.co/{MODEL}/resolve/{REVISION}/"
CONFIG = "config.json"
LAUNCHER = "extra/inference/inference_qwen38_flash_next_sglang.sh"
ALLOWED = {CONFIG: 256 * 1024, LAUNCHER: 128 * 1024}
MAX_OFFLINE = 256 * 1024


class SourceAuditBlocked(ValueError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise SourceAuditBlocked("SOURCE_REDIRECT_BLOCKED")


def source_bytes(path: str, offline: Path | None) -> bytes:
    if path not in ALLOWED:
        raise SourceAuditBlocked("SOURCE_PATH_NOT_ALLOWLISTED")
    limit = ALLOWED[path]
    if offline is not None:
        if offline.is_symlink() or not offline.is_dir():
            raise SourceAuditBlocked("SOURCE_OFFLINE_DIR_UNTRUSTED")
        for part in Path(path).parts:
            if part in ("", ".", ".."):
                raise SourceAuditBlocked("SOURCE_OFFLINE_PATH_UNTRUSTED")
        file = offline / path
        # Refuse symlinks in every part of the fixed path.
        current = offline
        for segment in Path(path).parts:
            current = current / segment
            if current.is_symlink():
                raise SourceAuditBlocked("SOURCE_SYMLINK_BLOCKED")
        if not file.is_file():
            raise SourceAuditBlocked("SOURCE_FIXTURE_MISSING_" + path)
        if file.stat().st_size > limit:
            raise SourceAuditBlocked("SOURCE_OVERSIZED_" + path)
        data = file.read_bytes()
    else:
        url = BASE + path
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect()
        )
        req = urllib.request.Request(
            url, headers={"Accept": "text/plain, application/json"},
        )
        try:
            with opener.open(req, timeout=15) as reply:
                if reply.status != 200:
                    raise SourceAuditBlocked("SOURCE_HTTP_NOT_200")
                reported_size = reply.headers.get("Content-Length")
                if reported_size is not None and int(reported_size) > limit:
                    raise SourceAuditBlocked("SOURCE_CONTENT_LENGTH_OVERSIZED")
                data = reply.read(limit + 1)
        except urllib.error.HTTPError as exc:
            raise SourceAuditBlocked("SOURCE_HTTP_ERROR_" + str(exc.code)) from exc
    if not data or len(data) > limit:
        raise SourceAuditBlocked("SOURCE_EMPTY_OR_OVERSIZED_" + path)
    return data


def scan_config(cfg: dict) -> dict:
    if not isinstance(cfg, dict):
        raise SourceAuditBlocked("CONFIG_NOT_OBJECT")
    quant = cfg.get("quantization_config")
    if not isinstance(quant, dict):
        raise SourceAuditBlocked("CONFIG_NO_QUANTIZATION_CONFIG")
    layers = quant.get("quantized_layers")
    if not isinstance(layers, dict):
        raise SourceAuditBlocked("CONFIG_NO_QUANTIZED_LAYER_TABLE")
    qkvz = sorted(k for k in layers if isinstance(k, str) and
                  k.endswith(".linear_attn.in_proj_qkvz"))
    # Distinguish a config-level name from proof that the wheel consumes scales.
    bad = [k for k in qkvz if not isinstance(layers[k], dict)]
    if bad:
        raise SourceAuditBlocked("QKVZ_NONOBJECT_QUANT_LAYER")
    algo = quant.get("quant_algo")
    method = quant.get("quant_method")
    txt = cfg.get("text_config")
    dtype = txt.get("ple_embedding_dtype") if isinstance(txt, dict) else None
    return {
        "quant_method": method,
        "quant_algo": algo,
        "quantized_layer_count": len(layers),
        "fused_qkvz_quantized_alias_count": len(qkvz),
        "fused_qkvz_alias_sample": qkvz[:2],
        "ple_embedding_dtype": dtype,
        "modelopt_mixed_config": method == "modelopt_mixed" and
                                 algo == "MIXED_PRECISION",
        "fused_qkvz_quantization_declared": len(qkvz) > 0,
        "fp8_ple_dtype_declared": dtype == "float8_e4m3fn",
    }


def scan_launcher(source: str) -> dict:
    # Source is DATA. Do not evaluate shell, follow its imports, or trust claims.
    flags = (
        "--ple-offload-embedding", "--ple-offload-backend",
        "--enable-hierarchical-cache", "--hicache-storage-backend",
        "--mem-fraction-static", "--speculative-algorithm",
        "--speculative-num-steps", "--moe-runner-backend",
    )
    found = {}
    for flag in flags:
        found[flag] = bool(re.search(
            r"(?<![A-Za-z0-9_-])" + re.escape(flag) + r"(?![A-Za-z0-9_-])",
            source))
    high_risk = {
        "cache_drop_command": bool(re.search(
            r"(?m)^[^\n#]*\b(drop_caches|/proc/sys/vm/drop_caches)\b", source)),
        "sudo_command": bool(re.search(r"(?m)^[^\n#]*\bsudo\b", source)),
        "public_bind": bool(re.search(r"--host\s+[\"']?0\.0\.0\.0", source)),
    }
    return {
        "sglang_entrypoint_claimed": bool(re.search(
            r"\bsglang\.launch_server\b", source)),
        "flags_mentioned": found,
        "script_operational_hazards": high_risk,
    }


def audit(offline: Path | None) -> dict:
    cfg_raw = source_bytes(CONFIG, offline)
    shell_raw = source_bytes(LAUNCHER, offline)
    try:
        cfg = json.loads(cfg_raw)
        shell = shell_raw.decode("utf-8")
    except (ValueError, UnicodeError) as exc:
        raise SourceAuditBlocked("SOURCE_TEXT_INVALID") from exc
    model = scan_config(cfg)
    launcher = scan_launcher(shell)
    source_declarations = (
        model["modelopt_mixed_config"] and
        model["fused_qkvz_quantization_declared"] and
        model["fp8_ple_dtype_declared"] and
        launcher["sglang_entrypoint_claimed"] and
        launcher["flags_mentioned"]["--ple-offload-embedding"] and
        launcher["flags_mentioned"]["--ple-offload-backend"]
    )
    return {
        "scope": "PINNED_SOURCE_TEXT_ONLY",
        "revision": REVISION, "checkpoint": MODEL,
        "transport": "PINNED_HF_TEXT" if offline is None else "OFFLINE_FIXTURE",
        "config_sha256": hashlib.sha256(cfg_raw).hexdigest(),
        "launcher_sha256": hashlib.sha256(shell_raw).hexdigest(),
        "source_declarations": "PRESENT_NOT_ENGINE_ATTESTED"
        if source_declarations else "MISSING_EXPECTED_DECLARATIONS",
        "config": model, "publisher_launcher": launcher,
        "engine_source_or_wheel_attested": False,
        "physical_gb10_memory_attested": False,
        "weight_download": False,
        "gpu_execution": False,
        "live_admission": "BLOCKED_ENGINE_LOADER_AND_MEMORY_NOT_ATTESTED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("audit",))
    parser.add_argument("--offline-dir", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        report = audit(args.offline_dir)
    except (SourceAuditBlocked, OSError, ValueError, json.JSONDecodeError) as exc:
        print("CATPLUSPLUS_SOURCE_AUDIT=BLOCKED_" + str(exc),
              file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("CATPLUSPLUS_SOURCE_SCOPE=" + str(report["scope"]))
        print("CATPLUSPLUS_SOURCE_REVISION=" + report["revision"])
        print("CATPLUSPLUS_SOURCE_TRANSPORT=" + report["transport"])
        print("CATPLUSPLUS_SOURCE_CONFIG_SHA256=" + report["config_sha256"])
        print("CATPLUSPLUS_SOURCE_LAUNCHER_SHA256=" + report["launcher_sha256"])
        cfg = report["config"]
        print("CATPLUSPLUS_SOURCE_QUANT_METHOD=" + str(cfg["quant_method"]))
        print("CATPLUSPLUS_SOURCE_QUANT_ALGO=" + str(cfg["quant_algo"]))
        print("CATPLUSPLUS_SOURCE_QKVZ_ALIAS_COUNT=" +
              str(cfg["fused_qkvz_quantized_alias_count"]))
        print("CATPLUSPLUS_SOURCE_PLE_DTYPE=" + str(cfg["ple_embedding_dtype"]))
        print("CATPLUSPLUS_SOURCE_DECLARATIONS=" + report["source_declarations"])
        for flag, present in report["publisher_launcher"]["flags_mentioned"].items():
            print("CATPLUSPLUS_LAUNCHER_FLAG_" + flag[2:].upper().replace("-", "_") +
                  "=" + ("DECLARED_NOT_VERIFIED" if present else "NOT_FOUND"))
        for name, present in report["publisher_launcher"]["script_operational_hazards"].items():
            print("CATPLUSPLUS_LAUNCHER_HAZARD_" + name.upper() +
                  "=" + ("PRESENT_DO_NOT_EXECUTE" if present else "NOT_DETECTED"))
        print("CATPLUSPLUS_ENGINE_LOADER=NOT_ATTESTED")
        print("CATPLUSPLUS_GB10_GPU=NOT_TESTED")
        print("CATPLUSPLUS_LIVE_ADMISSION=" + report["live_admission"])
        print("CATPLUSPLUS_DOCKER_WEIGHTS_HOST_MUTATION=NONE")
    return 0 if report["source_declarations"] == "PRESENT_NOT_ENGINE_ATTESTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
