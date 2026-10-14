#!/usr/bin/env python3
"""Offline llama-benchy JSON -> provenance-preserving model-specific Markdown report.

This script NEVER contacts an API, starts a service, or benchmarks a model.
Input must be an actual llama-benchy --format json --save-result capture.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys

PROFILES = (
    "orcarouter", "nvidia", "mazinb", "orcarouter-hybrid", "lychee888",
)
SHA40 = re.compile(r"^[0-9a-f]{40}$")
MEASURES = (
    ("pp_throughput", "PP total tok/s"),
    ("tg_throughput", "TG total tok/s"),
    ("tg_req_throughput", "TG/request tok/s"),
    ("peak_throughput", "Peak tok/s"),
    ("ttfr", "TTFR ms"),
    ("est_ppt", "Est. PPT ms"),
    ("e2e_ttft", "E2E TTFT ms"),
)


class ReportError(ValueError):
    """Invalid provenance, incompatible schema, or missing real measurement."""


def safe_value(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or any(
        marker in value for marker in ("\n", "\r", "|", "<", ">")
    ):
        raise ReportError(f"unsafe or empty {field}")
    return value


def metric(row: dict, key: str) -> str:
    obj = row.get(key)
    if obj is None:
        return "—"
    if not isinstance(obj, dict):
        raise ReportError(f"{key} must be an object or null")
    numbers = [obj.get("mean"), obj.get("std")]
    if any(
        isinstance(x, bool) or not isinstance(x, (int, float))
        or not math.isfinite(x) or x < 0 for x in numbers
    ):
        raise ReportError(f"{key} has invalid mean/std")
    return f"{numbers[0]:.2f} ± {numbers[1]:.2f}"


def render(data: dict, *, profile: str, expected_model: str,
           source_sha: str, release_sha: str, upstream_sha: str,
           raw_sha: str) -> str:
    if profile not in PROFILES:
        raise ReportError(f"unknown model profile {profile}")
    if data.get("model") != expected_model:
        raise ReportError("benchy model identity differs from --expected-model")
    for field, value in (
        ("source SHA", source_sha),
        ("installed release SHA", release_sha),
        ("llama-benchy SHA", upstream_sha),
    ):
        if not SHA40.fullmatch(value):
            raise ReportError(f"{field} must be a pinned 40-hex SHA")
    version = safe_value(data.get("version"), "benchy version")
    timestamp = safe_value(data.get("timestamp"), "capture timestamp")
    safe_value(expected_model, "expected model")
    rows = data.get("benchmarks")
    if not isinstance(rows, list) or not rows:
        raise ReportError("nonempty benchmarks array required")
    table = []
    measured = 0
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ReportError(f"benchmark {index} is not an object")
        dims = []
        for name, minimum in (
            ("concurrency", 1), ("context_size", 0),
            ("prompt_size", 1), ("response_size", 1),
        ):
            val = row.get(name)
            if isinstance(val, bool) or not isinstance(val, int) or val < minimum:
                raise ReportError(f"invalid benchmark dimension {name}")
            dims.append(str(val))
        values = [metric(row, key) for key, _ in MEASURES]
        measured += sum(value != "—" for value in values)
        phase = row.get("is_context_prefill_phase", False)
        if not isinstance(phase, bool):
            raise ReportError("invalid context-prefill indicator")
        table.append("| " + " | ".join(
            [*dims, "context prefill" if phase else "standard", *values]
        ) + " |")
    if not measured:
        raise ReportError("no numeric upstream benchmark metrics")
    headings = ["C", "Depth", "PP tokens", "TG tokens", "Phase"] + [label for _, label in MEASURES]
    out = [
        f"# {profile} — llama-benchy measured report",
        "",
        "**Evidence:** parsed upstream benchmark JSON with quantitative values.",
        "**Important:** benchmark throughput is NOT a functional, determinism,",
        "host-stability, NVIDIA RM or managed lifecycle acceptance certificate.",
        "",
        f"- Selected project profile: `{profile}`",
        f"- Exact reported model: `{expected_model}`",
        f"- Capture timestamp (source supplied): `{timestamp}`",
        f"- llama-benchy version: `{version}`",
        f"- llama-benchy upstream source SHA: `{upstream_sha}`",
        f"- Project source SHA: `{source_sha}`",
        f"- Installed runtime release SHA: `{release_sha}`",
        f"- Raw input JSON SHA256: `{raw_sha}`",
        f"- Context/prefix-caching mode: `{data.get('prefix_caching_enabled', 'UNKNOWN')}`",
        f"- Upstream latency mode: `{safe_value(data.get('latency_mode'), 'latency mode')}`",
        "",
        "| " + " | ".join(headings) + " |",
        "|" + "|".join(["---"] * len(headings)) + "|",
        *table,
        "",
        "## Gates NOT established by this report",
        "",
        "- Actual model readiness/API identity and response correctness require a separate functional test.",
        "- RM allocation stability, memory protection, OOM and host safety require a separate bounded monitored window.",
        "- A stopped or candidate-only model must not receive invented throughput values.",
        "- Compare models only when prompt corpus/tokenizer, test dimensions, workload,"
          " backend runtime, caching, concurrency, warmup and host protection are recorded and compatible.",
        "",
    ]
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, choices=PROFILES)
    parser.add_argument("--input", type=Path, required=True, help="Real llama-benchy JSON file")
    parser.add_argument("--output", type=Path, required=True, help="New local Markdown report file")
    parser.add_argument("--expected-model", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--release-sha", required=True)
    parser.add_argument("--upstream-sha", required=True)
    args = parser.parse_args()
    try:
        if not args.input.is_file() or args.input.is_symlink():
            raise ReportError("input must be a regular non-symlink file")
        raw = args.input.read_bytes()
        if len(raw) > 16 * 1024 * 1024:
            raise ReportError("benchmark JSON exceeds 16 MiB bound")
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ReportError("benchmark JSON must be an object")
        report = render(
            data, profile=args.profile, expected_model=args.expected_model,
            source_sha=args.source_sha, release_sha=args.release_sha,
            upstream_sha=args.upstream_sha,
            raw_sha=hashlib.sha256(raw).hexdigest(),
        )
        if args.output.is_symlink() or args.output.exists():
            raise ReportError("output exists or is symlink: refusing overwrite")
        if not args.output.parent.is_dir():
            raise ReportError("output directory must already exist")
        with args.output.open("x", encoding="utf-8") as file:
            file.write(report)
    except (OSError, UnicodeError, json.JSONDecodeError, ReportError) as exc:
        print(f"BENCHY_REPORT=INVALID reason={exc}", file=sys.stderr)
        return 2
    print(f"BENCHY_REPORT=CREATED profile={args.profile} path={args.output}")
    print("M1_HOST_STABILITY=NOT_ESTABLISHED_BY_BENCHMARK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
