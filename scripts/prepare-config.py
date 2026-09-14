#!/usr/bin/env python3
"""Create a vLLM-compatible config without modifying checkpoint files."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any


SOURCE_LAYER_TYPE = "qwen_sparse_attention"
VLLM_LAYER_TYPE = "compressed_sparse_attention"


def convert_layer_types(value: Any) -> tuple[Any, int]:
    """Recursively replace only the exact unsupported layer type."""
    if isinstance(value, dict):
        converted: dict[str, Any] = {}
        count = 0
        for key, item in value.items():
            converted[key], item_count = convert_layer_types(item)
            count += item_count
        return converted, count
    if isinstance(value, list):
        converted_items = []
        count = 0
        for item in value:
            converted_item, item_count = convert_layer_types(item)
            converted_items.append(converted_item)
            count += item_count
        return converted_items, count
    if value == SOURCE_LAYER_TYPE:
        return VLLM_LAYER_TYPE, 1
    return value, 0


def prepare(source: Path, destination: Path) -> int:
    try:
        original = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read source config {source}: {exc}") from exc
    converted, count = convert_layer_types(original)
    if count == 0:
        # A config already using vLLM's canonical name is valid and reproducible.
        serialized = json.dumps(original, indent=2, ensure_ascii=False) + "\n"
    else:
        serialized = json.dumps(converted, indent=2, ensure_ascii=False) + "\n"
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=destination.name + ".", dir=destination.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(serialized)
        os.replace(temporary_name, destination)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.model_dir / "config.json"
    try:
        count = prepare(source, args.output)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"vLLM config: {args.output.resolve()}")
    if count:
        print(f"converted {count} layer type entries: {SOURCE_LAYER_TYPE} -> {VLLM_LAYER_TYPE}")
    else:
        print("no conversion required; copied the checkpoint config")


if __name__ == "__main__":
    main()
