#!/usr/bin/env python3
"""Verify that a safetensors index resolves to a complete local shard set."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def fail(message: str, code: int = 1) -> int:
    print(message, file=sys.stderr)
    return code


def load_index(model_dir: Path) -> dict[str, object]:
    index_path = model_dir / "model.safetensors.index.json"
    try:
        with index_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"checkpoint index is unreadable: {index_path}: {exc}") from exc

    weight_map = data.get("weight_map")
    if not isinstance(weight_map, dict) or not weight_map:
        raise ValueError(f"checkpoint index has no non-empty weight_map: {index_path}")
    return weight_map


def shard_paths(model_dir: Path, weight_map: dict[str, object]) -> list[Path]:
    root = model_dir.resolve()
    names: set[str] = set()

    for tensor_name, raw_name in weight_map.items():
        if not isinstance(tensor_name, str) or not tensor_name:
            raise ValueError("checkpoint index contains an invalid tensor name")
        if not isinstance(raw_name, str) or not raw_name:
            raise ValueError(f"checkpoint index has an invalid shard for tensor {tensor_name!r}")

        candidate = Path(raw_name)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError(f"checkpoint index contains an unsafe shard path: {raw_name}")

        names.add(raw_name)

    paths: list[Path] = []
    for name in sorted(names):
        candidate = model_dir / name
        try:
            resolved = candidate.resolve(strict=False)
            resolved.relative_to(root)
        except (OSError, ValueError) as exc:
            raise ValueError(f"checkpoint shard escapes model directory: {name}") from exc
        paths.append(candidate)
    return paths


def verify(model_dir: Path) -> tuple[list[str], list[str]]:
    weight_map = load_index(model_dir)
    paths = shard_paths(model_dir, weight_map)

    missing: list[str] = []
    invalid: list[str] = []
    for path in paths:
        relative = os.fspath(path.relative_to(model_dir))
        if not path.exists():
            missing.append(relative)
            continue
        if not path.is_file():
            invalid.append(f"{relative} (not a regular file)")
            continue
        try:
            if path.stat().st_size <= 0:
                invalid.append(f"{relative} (empty)")
        except OSError as exc:
            invalid.append(f"{relative} ({exc})")

    return missing, invalid


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify every shard referenced by model.safetensors.index.json."
    )
    parser.add_argument("model_dir", type=Path)
    args = parser.parse_args()

    model_dir = args.model_dir
    if not model_dir.is_dir():
        return fail(f"model directory is missing: {model_dir}")

    try:
        missing, invalid = verify(model_dir)
    except ValueError as exc:
        return fail(str(exc), 2)

    if missing or invalid:
        for name in missing:
            print(f"MISSING_SHARD={name}")
        for item in invalid:
            print(f"INVALID_SHARD={item}")
        return 1

    print("CHECKPOINT_SHARDS=complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
