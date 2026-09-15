#!/usr/bin/env python3
"""Inspect a Qwen3.8-Flash-Next checkpoint before attempting a costly boot.

The Hugging Face API inspection is intentionally metadata-only.  A local model
directory is required for definitive tensor-layout checks, which only read each
safetensors JSON header rather than loading any tensor data.
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable


DEFAULT_REPO = "orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4"
GIB = 1024**3
PLE_MARKERS = ("ngram_embedding", ".ple.")
MTP_MARKERS = ("mtp.", "mtp_layers", "mtp_head")


@dataclass
class Finding:
    level: str
    code: str
    message: str


@dataclass
class Report:
    repository: str
    revision: str | None = None
    gated: bool | str | None = None
    remote_size_gib: float | None = None
    local_size_gib: float | None = None
    architecture: str | None = None
    model_type: str | None = None
    quantization_method: str | None = None
    safetensors_files: int = 0
    tensor_count: int = 0
    ple_files: list[str] = field(default_factory=list)
    ple_dtypes: list[str] = field(default_factory=list)
    mtp_files: list[str] = field(default_factory=list)
    mtp_dtypes: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    def add(self, level: str, code: str, message: str) -> None:
        self.findings.append(Finding(level, code, message))


def request_json(url: str, token: str | None) -> dict[str, Any]:
    headers = {"User-Agent": "qwen38-checkpoint-inspector/1"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {path}: {exc}") from exc


def read_safetensors_header(path: Path) -> dict[str, Any]:
    """Read only the length-prefixed JSON header of a safetensors file."""
    try:
        with path.open("rb") as stream:
            raw_length = stream.read(8)
            if len(raw_length) != 8:
                raise ValueError("file is shorter than the safetensors prefix")
            header_length = struct.unpack("<Q", raw_length)[0]
            if header_length == 0 or header_length > 512 * 1024 * 1024:
                raise ValueError(f"implausible header length: {header_length}")
            raw_header = stream.read(header_length)
            if len(raw_header) != header_length:
                raise ValueError("truncated safetensors header")
        return json.loads(raw_header)
    except (OSError, json.JSONDecodeError, struct.error) as exc:
        raise ValueError(f"cannot inspect {path}: {exc}") from exc


def flatten_quant_method(config: dict[str, Any]) -> str | None:
    quant = config.get("quantization_config")
    if not isinstance(quant, dict):
        return None
    for key in ("quant_method", "quant_algo", "format", "quantization_method"):
        value = quant.get(key)
        if value:
            return str(value)
    return "present (per-layer or unspecified)"


def tensor_matches(name: str, markers: Iterable[str]) -> bool:
    lowered = name.lower()
    return any(marker in lowered for marker in markers)


def inspect_remote(report: Report, token: str | None) -> None:
    url = f"https://huggingface.co/api/models/{report.repository}?blobs=true"
    try:
        metadata = request_json(url, token)
    except urllib.error.HTTPError as exc:
        hint = " Accept the model terms and run `hf auth login`." if exc.code in (401, 403) else ""
        report.add("ERROR", "REMOTE_ACCESS", f"Hugging Face returned HTTP {exc.code}.{hint}")
        return
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        report.add("ERROR", "REMOTE_ACCESS", f"Hugging Face metadata request failed: {exc}")
        return

    report.revision = metadata.get("sha")
    report.gated = metadata.get("gated")
    siblings = metadata.get("siblings") or []
    report.remote_size_gib = sum(int(item.get("size") or 0) for item in siblings) / GIB
    names = {item.get("rfilename") for item in siblings}
    if "model-mtp.safetensors" in names:
        report.add("INFO", "SEPARATE_MTP", "Checkpoint contains a separate model-mtp.safetensors file.")
    large_files = sorted(
        ((int(item.get("size") or 0), item.get("rfilename", "")) for item in siblings), reverse=True
    )
    if large_files and large_files[0][0] >= 80 * GIB:
        size, name = large_files[0]
        report.add("WARN", "LARGE_SHARD", f"Largest shard is {name} ({size / GIB:.2f} GiB); it is likely the BF16 PLE table.")
    if report.remote_size_gib and report.remote_size_gib > 160:
        report.add("WARN", "LARGE_CHECKPOINT", f"Checkpoint is {report.remote_size_gib:.2f} GiB and requires substantial swap-backed offload on a 121 GiB DGX Spark.")


def compare_override_config(report: Report, original: dict[str, Any], override_path: Path) -> None:
    override = read_json(override_path)
    keys = ("architectures", "model_type", "text_config", "quantization_config")
    changed = [key for key in keys if original.get(key) != override.get(key)]
    if changed:
        report.add("WARN", "CONFIG_OVERRIDE", f"Override config differs in: {', '.join(changed)}. Validate that these changes are intentional.")
    else:
        report.add("INFO", "CONFIG_OVERRIDE", "Override config matches the checkpoint for compatibility-critical fields.")


def inspect_local(report: Report, model_dir: Path, override_config: Path | None) -> None:
    if not model_dir.is_dir():
        report.add("ERROR", "MODEL_DIR", f"Local model directory does not exist: {model_dir}")
        return
    config_path = model_dir / "config.json"
    if not config_path.is_file():
        report.add("ERROR", "CONFIG_MISSING", f"Missing {config_path}")
        return

    try:
        config = read_json(config_path)
        if override_config:
            compare_override_config(report, config, override_config)
    except ValueError as exc:
        report.add("ERROR", "CONFIG_INVALID", str(exc))
        return

    architectures = config.get("architectures") or []
    report.architecture = architectures[0] if architectures else None
    report.model_type = config.get("model_type") or (config.get("text_config") or {}).get("model_type")
    report.quantization_method = flatten_quant_method(config)
    if report.architecture and report.architecture != "Qwen4ExpForConditionalGeneration":
        report.add("WARN", "ARCHITECTURE", f"Unexpected architecture: {report.architecture}")

    files = sorted(model_dir.glob("*.safetensors"))
    report.safetensors_files = len(files)
    report.local_size_gib = sum(path.stat().st_size for path in model_dir.rglob("*") if path.is_file()) / GIB
    if not files:
        report.add("ERROR", "WEIGHTS_MISSING", "No safetensors files found in the model directory.")
        return

    bad_headers = 0
    for path in files:
        try:
            header = read_safetensors_header(path)
        except ValueError as exc:
            bad_headers += 1
            report.add("ERROR", "SAFETENSORS_HEADER", str(exc))
            continue
        tensors = {name: meta for name, meta in header.items() if name != "__metadata__"}
        report.tensor_count += len(tensors)
        ple = {name: meta for name, meta in tensors.items() if tensor_matches(name, PLE_MARKERS)}
        mtp = {name: meta for name, meta in tensors.items() if tensor_matches(name, MTP_MARKERS)}
        if ple:
            report.ple_files.append(path.name)
            report.ple_dtypes.extend(str(meta.get("dtype", "unknown")) for meta in ple.values())
        if mtp or path.name == "model-mtp.safetensors":
            report.mtp_files.append(path.name)
            report.mtp_dtypes.extend(str(meta.get("dtype", "unknown")) for meta in (mtp or tensors).values())

    report.ple_files = sorted(set(report.ple_files))
    report.ple_dtypes = sorted(set(report.ple_dtypes))
    report.mtp_files = sorted(set(report.mtp_files))
    report.mtp_dtypes = sorted(set(report.mtp_dtypes))

    if not report.ple_files:
        report.add("ERROR", "PLE_NOT_FOUND", "No PLE/ngram embedding tensors were found; PLE CPU offload compatibility is unconfirmed.")
    elif any(dtype in {"BF16", "F16", "F32"} for dtype in report.ple_dtypes):
        report.add("INFO", "PLE_LAYOUT", f"PLE appears unquantized ({', '.join(report.ple_dtypes)}); stock PLE offload is the first configuration to test.")
    else:
        report.add("WARN", "PLE_LAYOUT", f"PLE is quantized ({', '.join(report.ple_dtypes)}); inspect scale tensors before selecting a PLE loader patch.")

    if not report.mtp_files:
        report.add("WARN", "MTP_NOT_FOUND", "No MTP tensors were found; start with speculative decoding disabled.")
    else:
        report.add("INFO", "MTP_LAYOUT", f"MTP tensors found in {', '.join(report.mtp_files)} with dtypes {', '.join(report.mtp_dtypes)}.")
    if bad_headers == 0:
        report.add("PASS", "HEADERS", f"Read {report.tensor_count:,} tensor headers from {len(files)} safetensors files.")


def print_report(report: Report) -> None:
    def value(item: Any) -> str:
        if item is None:
            return "not available"
        if isinstance(item, list):
            return ", ".join(item) if item else "not found"
        return str(item)

    rows = [
        ("Repository", report.repository), ("Revision", report.revision), ("Gated", report.gated),
        ("Remote size", f"{report.remote_size_gib:.2f} GiB" if report.remote_size_gib is not None else None),
        ("Local size", f"{report.local_size_gib:.2f} GiB" if report.local_size_gib is not None else None),
        ("Architecture", report.architecture), ("Model type", report.model_type),
        ("Quantization", report.quantization_method), ("Safetensors", report.safetensors_files),
        ("Tensor headers", report.tensor_count), ("PLE files", report.ple_files),
        ("PLE dtypes", report.ple_dtypes), ("MTP files", report.mtp_files), ("MTP dtypes", report.mtp_dtypes),
    ]
    print("Qwen3.8 checkpoint compatibility report\n")
    for label, item in rows:
        print(f"{label:16}: {value(item)}")
    print("\nFindings")
    for finding in report.findings:
        print(f"[{finding.level:5}] {finding.code:20} {finding.message}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPO, help="Hugging Face repository id")
    parser.add_argument("--model-dir", type=Path, help="downloaded checkpoint directory")
    parser.add_argument("--config-override", type=Path, help="config.json mounted over the checkpoint at runtime")
    parser.add_argument("--offline", action="store_true", help="skip the Hugging Face metadata request")
    parser.add_argument("--json", action="store_true", dest="json_output", help="emit machine-readable JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = Report(repository=args.repo)
    if not args.offline:
        inspect_remote(report, os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN"))
    if args.model_dir:
        inspect_local(report, args.model_dir.resolve(), args.config_override)
    else:
        report.add("WARN", "LOCAL_REQUIRED", "Pass --model-dir for definitive PLE/MTP tensor compatibility checks.")

    if args.json_output:
        print(json.dumps(asdict(report), indent=2, ensure_ascii=False))
    else:
        print_report(report)
    return 2 if any(item.level == "ERROR" for item in report.findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
