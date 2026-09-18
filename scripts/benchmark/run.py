#!/usr/bin/env python3
"""Run reproducible local benchmark workloads against the managed Qwen runtime."""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import pathlib
import statistics
import sys
import threading
import time
from datetime import datetime, timezone
from typing import Any

import common


DECODE_PROMPT = (
    "Explain how an operating-system page cache serves random reads from an "
    "NVMe-backed memory mapping. Write continuous technical prose and do not "
    "use headings. /no_think"
)


def parse_int_list(value: str, *, minimum: int, maximum: int) -> list[int]:
    """Parse a unique comma-separated integer list within bounds."""

    try:
        values = [int(item) for item in value.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected comma-separated integers") from exc
    if not values or len(values) != len(set(values)):
        raise argparse.ArgumentTypeError("values must be non-empty and unique")
    if any(item < minimum or item > maximum for item in values):
        raise argparse.ArgumentTypeError(f"values must be between {minimum} and {maximum}")
    return values


def run_qualification(base_url: str, model: str) -> dict[str, Any]:
    """Perform lightweight health/model/chat checks before measuring performance."""

    started = time.monotonic()
    selected = common.check_backend(base_url, model)
    response = common.request_json(
        base_url,
        "/v1/chat/completions",
        {
            "model": selected,
            "messages": [{"role": "user", "content": "Reply with exactly: READY /no_think"}],
            "temperature": 0,
            "max_tokens": 32,
            "chat_template_kwargs": {"enable_thinking": False},
        },
        timeout=120,
    )
    choices = response.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        raise common.BenchmarkError("qualification chat response has no choices")
    message = choices[0].get("message") or {}
    if not message.get("content"):
        raise common.BenchmarkError("qualification chat response has no text")
    return {"status": "pass", "elapsed_s": round(time.monotonic() - started, 4)}


def sha256_text(value: str) -> str:
    """Return a stable digest without retaining generated model text."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def run_determinism(
    base_url: str,
    model: str,
    corpus: pathlib.Path,
    prompt_tokens: int,
    output_tokens: int,
    repeats: int,
) -> dict[str, Any]:
    """Require byte-identical greedy output across repeated identical requests."""

    suffix = (
        "\n\nContinue with a concise deterministic technical explanation of the material above. "
        "Do not use headings. /no_think"
    )
    prompt, actual = common.prompt_for_tokens(
        base_url, model, corpus, prompt_tokens, suffix=suffix
    )
    runs: list[dict[str, Any]] = []
    hashes: list[str] = []
    for index in range(repeats):
        started = time.monotonic()
        response = common.request_json(
            base_url,
            "/v1/chat/completions",
            {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": output_tokens,
                "chat_template_kwargs": {"enable_thinking": False},
            },
            timeout=1800,
        )
        choices = response.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            raise common.BenchmarkError("determinism response has no choices")
        message = choices[0].get("message") or {}
        content = message.get("content")
        if not isinstance(content, str) or not content:
            raise common.BenchmarkError("determinism response has no text")
        digest = sha256_text(content)
        hashes.append(digest)
        usage = response.get("usage") or {}
        runs.append(
            {
                "run": index + 1,
                "sha256": digest,
                "elapsed_s": round(time.monotonic() - started, 6),
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
            }
        )
    all_equal = len(set(hashes)) == 1
    return {
        "status": "pass" if all_equal else "fail",
        "all_equal": all_equal,
        "unique_hashes": len(set(hashes)),
        "requested_prompt_tokens": prompt_tokens,
        "actual_prompt_tokens": actual,
        "output_tokens": output_tokens,
        "repeats": repeats,
        "runs": runs,
    }


def run_decode(base_url: str, model: str, max_tokens: int, repeats: int) -> dict[str, Any]:
    """Measure repeated single-stream decode performance."""

    runs = [common.stream_chat(base_url, model, DECODE_PROMPT, max_tokens) for _ in range(repeats)]
    tps = [item["decode_tokens_s"] for item in runs]
    ttft = [item["ttft_s"] for item in runs]
    return {
        "max_tokens": max_tokens,
        "repeats": repeats,
        "decode_tokens_s": common.summarize(tps),
        "ttft_s": common.summarize(ttft),
        "runs": runs,
    }


def run_prefill(
    base_url: str,
    model: str,
    corpus: pathlib.Path,
    sizes: list[int],
) -> dict[str, Any]:
    """Measure long-prompt time-to-first-token and derived prompt-token rate."""

    runs = []
    for target in sizes:
        prompt, actual = common.prompt_for_tokens(base_url, model, corpus, target)
        result = common.stream_chat(base_url, model, prompt, 1)
        ttft = float(result["ttft_s"])
        prompt_tokens = int(result["prompt_tokens"] or actual)
        runs.append(
            {
                "requested_tokens": target,
                "actual_tokens": actual,
                "reported_prompt_tokens": prompt_tokens,
                "ttft_s": ttft,
                "prompt_tokens_s": round(prompt_tokens / ttft, 3) if ttft else None,
            }
        )
    return {"corpus": corpus.name, "runs": runs}


def one_concurrent_request(
    base_url: str,
    model: str,
    max_tokens: int,
    gate: threading.Barrier,
) -> dict[str, Any]:
    """Synchronize request start so a level measures genuine concurrency."""

    gate.wait()
    return common.stream_chat(base_url, model, DECODE_PROMPT, max_tokens)


def run_concurrency(
    base_url: str,
    model: str,
    levels: list[int],
    max_tokens: int,
) -> dict[str, Any]:
    """Measure aggregate throughput and TTFT at several concurrency levels."""

    rows = []
    for concurrency in levels:
        gate = threading.Barrier(concurrency + 1)
        memory_samples = [common.meminfo_gib().get("MemAvailable")]
        stop = threading.Event()

        def sample_memory() -> None:
            while not stop.wait(0.25):
                memory_samples.append(common.meminfo_gib().get("MemAvailable"))

        sampler = threading.Thread(target=sample_memory, daemon=True)
        sampler.start()
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
                futures = [
                    pool.submit(one_concurrent_request, base_url, model, max_tokens, gate)
                    for _ in range(concurrency)
                ]
                gate.wait()
                started = time.monotonic()
                results = [future.result() for future in futures]
                wall_s = time.monotonic() - started
        finally:
            stop.set()
            sampler.join(timeout=1)
        total_tokens = sum(int(item["completion_tokens"]) for item in results)
        ttfts = [float(item["ttft_s"]) for item in results]
        available = [value for value in memory_samples if value is not None]
        rows.append(
            {
                "concurrency": concurrency,
                "requests": concurrency,
                "successful_requests": sum(bool(item["ok"]) for item in results),
                "wall_s": round(wall_s, 4),
                "total_completion_tokens": total_tokens,
                "aggregate_tokens_s": round(total_tokens / wall_s, 4) if wall_s else None,
                "per_stream_tokens_s": round(total_tokens / wall_s / concurrency, 4)
                if wall_s
                else None,
                "median_ttft_s": round(statistics.median(ttfts), 6),
                "min_mem_available_gib": round(min(available), 3) if available else None,
            }
        )
    return {"max_tokens": max_tokens, "levels": rows}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument(
        "mode",
        choices=("qualification", "determinism", "decode", "prefill", "concurrency", "all"),
    )
    result.add_argument("--base-url", default=common.DEFAULT_BASE_URL)
    result.add_argument("--model", default=None)
    result.add_argument("--corpus", type=pathlib.Path, default=common.ROOT / "README.md")
    result.add_argument("--decode-tokens", type=int, default=384)
    result.add_argument("--decode-repeats", type=int, default=3)
    result.add_argument("--determinism-prompt-tokens", type=int, default=8192)
    result.add_argument("--determinism-output-tokens", type=int, default=128)
    result.add_argument("--determinism-repeats", type=int, default=3)
    result.add_argument(
        "--prefill-sizes",
        type=lambda value: parse_int_list(value, minimum=512, maximum=250000),
        default=parse_int_list("8192,16384,32768", minimum=512, maximum=250000),
    )
    result.add_argument(
        "--concurrency-levels",
        type=lambda value: parse_int_list(value, minimum=1, maximum=32),
        default=parse_int_list("1,2,4,8", minimum=1, maximum=32),
    )
    result.add_argument("--output", type=pathlib.Path)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        args.base_url = common.validate_base_url(args.base_url)
    except ValueError as exc:
        parser().error(str(exc))
    if not 16 <= args.decode_tokens <= 8192:
        parser().error("--decode-tokens must be between 16 and 8192")
    if not 1 <= args.decode_repeats <= 20:
        parser().error("--decode-repeats must be between 1 and 20")
    if not 512 <= args.determinism_prompt_tokens <= 250000:
        parser().error("--determinism-prompt-tokens must be between 512 and 250000")
    if not 16 <= args.determinism_output_tokens <= 8192:
        parser().error("--determinism-output-tokens must be between 16 and 8192")
    if not 2 <= args.determinism_repeats <= 20:
        parser().error("--determinism-repeats must be between 2 and 20")
    if not args.corpus.is_file():
        parser().error(f"corpus does not exist: {args.corpus}")

    started = datetime.now(timezone.utc)
    try:
        model = common.check_backend(args.base_url, args.model)
        report: dict[str, Any] = {
            "schema_version": 1,
            "started": started.isoformat(),
            "mode": args.mode,
            "environment": common.environment_snapshot(args.base_url, model),
            "workloads": {},
        }
        modes = (
            ("qualification", "determinism", "decode", "prefill", "concurrency")
            if args.mode == "all"
            else (args.mode,)
        )
        for mode in modes:
            if mode == "qualification":
                report["workloads"][mode] = run_qualification(args.base_url, model)
            elif mode == "determinism":
                report["workloads"][mode] = run_determinism(
                    args.base_url,
                    model,
                    args.corpus,
                    args.determinism_prompt_tokens,
                    args.determinism_output_tokens,
                    args.determinism_repeats,
                )
            elif mode == "decode":
                report["workloads"][mode] = run_decode(
                    args.base_url, model, args.decode_tokens, args.decode_repeats
                )
            elif mode == "prefill":
                report["workloads"][mode] = run_prefill(
                    args.base_url, model, args.corpus, args.prefill_sizes
                )
            else:
                report["workloads"][mode] = run_concurrency(
                    args.base_url, model, args.concurrency_levels, args.decode_tokens
                )
        report["completed"] = datetime.now(timezone.utc).isoformat()
        workload_failed = any(
            isinstance(item, dict) and item.get("status") == "fail"
            for item in report["workloads"].values()
        )
        report["status"] = "fail" if workload_failed else "pass"
    except (common.BenchmarkError, OSError, ValueError) as exc:
        report = {
            "schema_version": 1,
            "started": started.isoformat(),
            "completed": datetime.now(timezone.utc).isoformat(),
            "mode": args.mode,
            "status": "fail",
            "error": str(exc),
        }

    if args.output:
        common.write_json_atomic(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
