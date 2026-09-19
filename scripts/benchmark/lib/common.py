#!/usr/bin/env python3
"""Shared, side-effect-free helpers for local Qwen benchmark workloads."""

from __future__ import annotations

import json
import math
import os
import pathlib
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from typing import Any, Iterable


ROOT = pathlib.Path(__file__).resolve().parents[3]
DEFAULT_BASE_URL = "http://127.0.0.1:8888"


class BenchmarkError(RuntimeError):
    """A benchmark precondition or runtime response was invalid."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Reject redirects so a local benchmark can never escape loopback."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise BenchmarkError("benchmark endpoint redirected; refusing to leave loopback")


def validate_base_url(value: str) -> str:
    """Normalize a credential-free loopback HTTP URL or raise ValueError."""

    parsed = urllib.parse.urlsplit(value)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ValueError("--base-url must be credential-free loopback HTTP with no path")
    if parsed.port is None:
        raise ValueError("--base-url must include an explicit port")
    return value.rstrip("/")


def opener() -> urllib.request.OpenerDirector:
    """Build an opener that ignores proxy environment variables and redirects."""

    return urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())


def request_json(
    base_url: str,
    path: str,
    payload: dict[str, Any] | None = None,
    timeout: float = 120.0,
) -> dict[str, Any]:
    """Perform one JSON request against the local backend."""

    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        base_url + path,
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
        method="POST" if data is not None else "GET",
    )
    try:
        with opener().open(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except OSError as exc:
        raise BenchmarkError(f"request failed: {path}: {exc}") from exc
    try:
        decoded = json.loads(body) if body else {}
    except json.JSONDecodeError as exc:
        raise BenchmarkError(f"non-JSON response: {path}") from exc
    if not isinstance(decoded, dict):
        raise BenchmarkError(f"JSON response is not an object: {path}")
    return decoded


def request_text(
    base_url: str,
    path: str,
    timeout: float = 30.0,
) -> str:
    """Perform one text GET request against the local backend."""

    request = urllib.request.Request(base_url + path, method="GET")
    try:
        with opener().open(request, timeout=timeout) as response:
            return response.read().decode("utf-8", "replace")
    except OSError as exc:
        raise BenchmarkError(f"request failed: {path}: {exc}") from exc


def prometheus_samples(text: str) -> dict[str, float]:
    """Parse numeric Prometheus samples while preserving their label set."""

    result: dict[str, float] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            metric, raw_value = line.rsplit(None, 1)
            value = float(raw_value)
        except (ValueError, TypeError):
            continue
        if math.isfinite(value):
            result[metric] = value
    return result


def metrics_snapshot(base_url: str) -> dict[str, float] | None:
    """Return a local /metrics snapshot, or None when metrics are unavailable."""

    try:
        return prometheus_samples(request_text(base_url, "/metrics"))
    except BenchmarkError:
        return None


def metric_total(samples: dict[str, float], name: str) -> float | None:
    """Sum all label variants for one exact Prometheus metric name."""

    prefix = name + "{"
    values = [
        value
        for metric, value in samples.items()
        if metric == name or metric.startswith(prefix)
    ]
    return sum(values) if values else None


def metric_position_totals(
    samples: dict[str, float],
    name: str,
) -> dict[str, float]:
    """Return position-labelled totals for a Prometheus metric."""

    prefix = name + "{"
    result: dict[str, float] = {}
    for metric, value in samples.items():
        if not metric.startswith(prefix):
            continue
        marker = 'position="'
        start = metric.find(marker)
        if start < 0:
            continue
        start += len(marker)
        end = metric.find('"', start)
        if end < 0:
            continue
        position = metric[start:end]
        result[position] = result.get(position, 0.0) + value
    return result


def metric_delta(
    before: dict[str, float] | None,
    after: dict[str, float] | None,
    name: str,
) -> float | None:
    """Return a monotonic metric delta, or None if unavailable/reset."""

    if before is None or after is None:
        return None
    first = metric_total(before, name)
    second = metric_total(after, name)
    if first is None or second is None or second < first:
        return None
    return second - first


def metric_position_delta(
    before: dict[str, float] | None,
    after: dict[str, float] | None,
    name: str,
) -> dict[str, float] | None:
    """Return monotonic per-position deltas, or None if unavailable/reset."""

    if before is None or after is None:
        return None
    first = metric_position_totals(before, name)
    second = metric_position_totals(after, name)
    if not first and not second:
        return None

    result: dict[str, float] = {}
    for position in sorted(set(first) | set(second), key=lambda value: int(value)):
        old = first.get(position, 0.0)
        new = second.get(position, 0.0)
        if new < old:
            return None
        result[position] = new - old
    return result


def iter_sse(lines: Iterable[bytes]) -> Iterable[dict[str, Any]]:
    """Yield JSON objects from SSE data fields and stop at [DONE]."""

    for raw in lines:
        line = raw.decode("utf-8", "replace").strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            return
        try:
            event = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise BenchmarkError("invalid JSON in SSE stream") from exc
        if not isinstance(event, dict):
            raise BenchmarkError("SSE event is not a JSON object")
        if event.get("error"):
            raise BenchmarkError("backend returned an SSE error")
        yield event


def check_backend(base_url: str, model: str | None, timeout: float = 30.0) -> str:
    """Verify health and return the selected served-model ID."""

    request_json(base_url, "/health", timeout=timeout)
    models = request_json(base_url, "/v1/models", timeout=timeout)
    model_ids = [
        item.get("id")
        for item in models.get("data", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    ]
    if model is None:
        if len(model_ids) != 1:
            raise BenchmarkError("--model is required unless /v1/models exposes exactly one model")
        return model_ids[0]
    if model not in model_ids:
        raise BenchmarkError(f"served model is missing: {model!r}")
    return model


def tokenize_count(base_url: str, model: str, text: str) -> int:
    """Use the serving tokenizer so context sizes match the live runtime."""

    result = request_json(base_url, "/tokenize", {"model": model, "prompt": text})
    count = result.get("count")
    if isinstance(count, int):
        return count
    tokens = result.get("tokens")
    if isinstance(tokens, list):
        return len(tokens)
    raise BenchmarkError("/tokenize returned neither count nor tokens")


def corpus_text(path: pathlib.Path, minimum_chars: int) -> str:
    """Repeat real local text with unique markers until minimum_chars is reached."""

    source = path.read_text(encoding="utf-8", errors="replace")
    if not source.strip():
        raise ValueError(f"corpus is empty: {path}")
    sections: list[str] = []
    total = 0
    index = 0
    while total < minimum_chars:
        section = f"\n\n<!-- benchmark section {index} -->\n\n{source}"
        sections.append(section)
        total += len(section)
        index += 1
    return "".join(sections)


def prompt_for_tokens(
    base_url: str,
    model: str,
    corpus: pathlib.Path,
    target_tokens: int,
    *,
    suffix: str = "\n\nReply with exactly one word: ok",
) -> tuple[str, int]:
    """Binary-search real text into a prompt close to target_tokens."""

    text = corpus_text(corpus, max(50_000, target_tokens * 8))
    low, high = 1, len(text)
    best = suffix
    best_count = tokenize_count(base_url, model, best)
    for _ in range(22):
        if low > high:
            break
        middle = (low + high) // 2
        candidate = text[:middle] + suffix
        count = tokenize_count(base_url, model, candidate)
        if abs(count - target_tokens) < abs(best_count - target_tokens):
            best, best_count = candidate, count
        if count < target_tokens:
            low = middle + 1
        else:
            high = middle - 1
    return best, best_count


def stream_chat(
    base_url: str,
    model: str,
    prompt: str,
    max_tokens: int,
    timeout: float = 1800.0,
) -> dict[str, Any]:
    """Measure one streaming chat request without retaining generated text."""

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
        "chat_template_kwargs": {"enable_thinking": False},
    }
    request = urllib.request.Request(
        base_url + "/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.monotonic()
    first_content: float | None = None
    content_events: list[float] = []
    completion_tokens = 0
    prompt_tokens = 0
    done = False
    try:
        with opener().open(request, timeout=timeout) as response:
            for event in iter_sse(response):
                usage = event.get("usage") or {}
                if isinstance(usage, dict):
                    completion_tokens = int(usage.get("completion_tokens") or completion_tokens)
                    prompt_tokens = int(usage.get("prompt_tokens") or prompt_tokens)
                for choice in event.get("choices") or []:
                    delta = choice.get("delta") or {}
                    if delta.get("content") or delta.get("reasoning"):
                        now = time.monotonic()
                        if first_content is None:
                            first_content = now
                        content_events.append(now)
            done = True
    except OSError as exc:
        raise BenchmarkError(f"stream request failed: {exc}") from exc
    ended = time.monotonic()
    if first_content is None:
        raise BenchmarkError("stream produced no content")
    elapsed = ended - started
    decode_elapsed = max(ended - first_content, 1e-9)
    gaps = [right - left for left, right in zip(content_events, content_events[1:])]
    return {
        "ok": done and completion_tokens > 0,
        "elapsed_s": round(elapsed, 6),
        "ttft_s": round(first_content - started, 6),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "decode_tokens_s": round(completion_tokens / decode_elapsed, 4),
        "content_events": len(content_events),
        "event_gaps": summarize(gaps),
    }


def summarize(values: list[float]) -> dict[str, float | int | None]:
    """Return count/median/p95/max for a numeric series."""

    if not values:
        return {"count": 0, "median": None, "p95": None, "max": None}
    ordered = sorted(values)
    p95_index = min(len(ordered) - 1, math.ceil(len(ordered) * 0.95) - 1)
    return {
        "count": len(values),
        "median": round(statistics.median(values), 6),
        "p95": round(ordered[p95_index], 6),
        "max": round(max(values), 6),
    }


def meminfo_gib() -> dict[str, float]:
    """Read selected /proc/meminfo counters in GiB."""

    wanted = {"MemTotal", "MemAvailable", "MemFree", "SwapTotal", "SwapFree"}
    result: dict[str, float] = {}
    with open("/proc/meminfo", encoding="utf-8") as handle:
        for line in handle:
            key = line.split(":", 1)[0]
            if key in wanted:
                result[key] = round(int(line.split()[1]) / 1048576, 3)
    return result


def git_revision(root: pathlib.Path = ROOT) -> str | None:
    """Return HEAD when root is a Git worktree, otherwise None."""

    try:
        return subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def current_release_id() -> str | None:
    """Return the immutable current release directory name without exposing paths."""

    data_home = pathlib.Path(os.environ.get("XDG_DATA_HOME", pathlib.Path.home() / ".local/share"))
    current = data_home / "qwen38-spark" / "current"
    try:
        return current.resolve(strict=True).name
    except OSError:
        return None


def runtime_config_from_docker_config(
    container_name: str,
    config: dict[str, Any],
) -> dict[str, Any] | None:
    """Extract benchmark-relevant vLLM settings from Docker config data."""

    command = config.get("Cmd")
    if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
        return None

    def option(name: str) -> str | None:
        try:
            index = command.index(name)
        except ValueError:
            return None
        return command[index + 1] if index + 1 < len(command) else None

    result: dict[str, Any] = {
        "container_name": container_name,
        "image": config.get("Image"),
        "served_model_name": option("--served-model-name"),
        "max_model_len": option("--max-model-len"),
        "max_num_seqs": option("--max-num-seqs"),
        "max_num_batched_tokens": option("--max-num-batched-tokens"),
        "kv_cache_memory": option("--kv-cache-memory"),
        "kv_cache_dtype": option("--kv-cache-dtype"),
        "distributed_executor_backend": option("--distributed-executor-backend"),
        "flashinfer_autotune": (
            True
            if "--enable-flashinfer-autotune" in command
            else False
            if "--no-enable-flashinfer-autotune" in command
            else None
        ),
        "prefix_caching": (
            True
            if "--enable-prefix-caching" in command
            else False
            if "--no-enable-prefix-caching" in command
            else None
        ),
        "async_scheduling": (
            False if "--no-async-scheduling" in command else None
        ),
    }

    raw_spec = option("--speculative-config")
    if raw_spec is None:
        result["speculative_config"] = None
        result["mtp_index_share"] = None
    else:
        try:
            parsed = json.loads(raw_spec)
        except json.JSONDecodeError:
            parsed = raw_spec
        result["speculative_config"] = parsed
        result["mtp_index_share"] = (
            bool(parsed.get("index_share_for_mtp_iteration", False))
            if isinstance(parsed, dict) and parsed.get("method") == "mtp"
            else None
        )

    return result


def runtime_config_snapshot(base_url: str) -> dict[str, Any] | None:
    """Read the running Docker config serving the benchmark's loopback port."""

    try:
        port = urllib.parse.urlsplit(base_url).port
    except ValueError:
        return None
    if port is None:
        return None

    try:
        names = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                f"publish={port}",
                "--format",
                "{{.Names}}",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        return None

    names = [name.strip() for name in names if name.strip()]
    if len(names) != 1:
        return None

    try:
        raw = subprocess.run(
            [
                "docker",
                "inspect",
                "--format",
                "{{json .Config}}",
                names[0],
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout
        config = json.loads(raw)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return None
    if not isinstance(config, dict):
        return None
    return runtime_config_from_docker_config(names[0], config)


def environment_snapshot(base_url: str, model: str) -> dict[str, Any]:
    """Capture reproducibility metadata without credentials, hostname, or serials."""

    models = request_json(base_url, "/v1/models", timeout=30)
    selected = next(
        (item for item in models.get("data", []) if isinstance(item, dict) and item.get("id") == model),
        {},
    )
    return {
        "git_revision": git_revision(),
        "release_id": current_release_id(),
        "model": model,
        "max_model_len": selected.get("max_model_len"),
        "runtime_config": runtime_config_snapshot(base_url),
        "memory_gib": meminfo_gib(),
        "python": {
            "major": sys.version_info.major,
            "minor": sys.version_info.minor,
            "micro": sys.version_info.micro,
        },
        "generated_text_retained": False,
    }


def write_json_atomic(path: pathlib.Path, report: dict[str, Any]) -> None:
    """Atomically write a benchmark report."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
