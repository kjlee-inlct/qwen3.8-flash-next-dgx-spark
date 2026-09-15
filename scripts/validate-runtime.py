#!/usr/bin/env python3
"""Validate the OpenAI-compatible Qwen runtime without changing server state."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable


DEFAULT_URL = "http://127.0.0.1:8888"
DEFAULT_MODEL = "orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4"


class ValidationError(RuntimeError):
    """A runtime response failed a compatibility or behavior check."""


def request_json(url: str, *, payload: dict[str, Any] | None, timeout: float) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data is not None else {},
        method="POST" if data is not None else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError) as error:
        raise ValidationError(f"request failed: {url}: {error}") from error
    try:
        return json.loads(body) if body else {}
    except json.JSONDecodeError as error:
        raise ValidationError(f"non-JSON response from {url}") from error


def iter_sse_data(lines: Iterable[bytes]) -> Iterable[str]:
    """Yield data fields from an OpenAI-compatible server-sent event stream."""
    for raw in lines:
        line = raw.decode("utf-8").strip()
        if line.startswith("data:"):
            yield line[5:].strip()


def validate_chat_response(data: Any) -> None:
    choices = data.get("choices") if isinstance(data, dict) else None
    if not choices or not isinstance(choices[0], dict):
        raise ValidationError("chat response has no choices")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ValidationError("chat response has no message")
    if not message.get("content") and not message.get("tool_calls"):
        raise ValidationError("chat response contains neither text nor tool calls")


def chat_payload(model: str, *, stream: bool = False) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with exactly: READY"}],
        "temperature": 0,
        "max_tokens": 32,
        "stream": stream,
    }


def validate_stream(url: str, model: str, timeout: float) -> int:
    payload = json.dumps(chat_payload(model, stream=True)).encode("utf-8")
    request = urllib.request.Request(
        f"{url}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    chunks = 0
    done = False
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            for item in iter_sse_data(response):
                if item == "[DONE]":
                    done = True
                    break
                event = json.loads(item)
                if event.get("choices"):
                    chunks += 1
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise ValidationError(f"streaming validation failed: {error}") from error
    if not done or chunks == 0:
        raise ValidationError("stream ended without chunks and [DONE]")
    return chunks


def validate_tool_call(url: str, model: str, timeout: float) -> None:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "What is the weather in Seoul? Use the weather tool."}],
        "temperature": 0,
        "max_tokens": 128,
        "tool_choice": "required",
        "tools": [{
            "type": "function",
            "function": {
                "name": "weather",
                "description": "Get weather for a city",
                "parameters": {
                    "type": "object",
                    "properties": {"city": {"type": "string"}},
                    "required": ["city"],
                },
            },
        }],
    }
    data = request_json(f"{url}/v1/chat/completions", payload=payload, timeout=timeout)
    validate_chat_response(data)
    calls = data["choices"][0]["message"].get("tool_calls") or []
    if not calls or calls[0].get("function", {}).get("name") != "weather":
        raise ValidationError("tool parser did not return the required weather call")


def write_report(path: Path, report: dict[str, Any]) -> None:
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--skip-stream", action="store_true")
    parser.add_argument("--skip-tool", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.concurrency < 1 or args.concurrency > 32:
        parser.error("--concurrency must be between 1 and 32")

    url = args.base_url.rstrip("/")
    started = time.monotonic()
    report: dict[str, Any] = {"base_url": url, "model": args.model, "checks": {}}
    try:
        request_json(f"{url}/health", payload=None, timeout=args.timeout)
        report["checks"]["health"] = "pass"

        models = request_json(f"{url}/v1/models", payload=None, timeout=args.timeout)
        model_ids = [item.get("id") for item in models.get("data", []) if isinstance(item, dict)]
        if args.model not in model_ids:
            raise ValidationError(f"served model is missing; received: {model_ids}")
        report["checks"]["models"] = "pass"

        response = request_json(
            f"{url}/v1/chat/completions", payload=chat_payload(args.model), timeout=args.timeout
        )
        validate_chat_response(response)
        report["checks"]["chat"] = "pass"

        if not args.skip_stream:
            report["stream_chunks"] = validate_stream(url, args.model, args.timeout)
            report["checks"]["stream"] = "pass"
        if not args.skip_tool:
            validate_tool_call(url, args.model, args.timeout)
            report["checks"]["tool_call"] = "pass"

        def one_request(_: int) -> None:
            result = request_json(
                f"{url}/v1/chat/completions", payload=chat_payload(args.model), timeout=args.timeout
            )
            validate_chat_response(result)

        with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as executor:
            list(executor.map(one_request, range(args.concurrency)))
        report["checks"]["concurrency"] = "pass"
        report["concurrency"] = args.concurrency
        report["status"] = "pass"
    except ValidationError as error:
        report["status"] = "fail"
        report["error"] = str(error)
    report["elapsed_seconds"] = round(time.monotonic() - started, 3)
    if args.output:
        write_report(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
