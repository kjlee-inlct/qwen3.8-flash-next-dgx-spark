#!/usr/bin/env python3
"""Validate that a safetensors index references a complete local checkpoint."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CheckpointIntegrity:
    shard_count: int
    missing: tuple[str, ...]
    invalid: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.missing and not self.invalid


def _load_index(index_path: Path) -> dict[str, Any]:
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read safetensors index: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("safetensors index root must be an object")
    weight_map = data.get("weight_map")
    if not isinstance(weight_map, dict) or not weight_map:
        raise ValueError("safetensors index has no non-empty weight_map")
    return weight_map


def inspect_checkpoint(model_dir: Path) -> CheckpointIntegrity:
    index_path = model_dir / "model.safetensors.index.json"
    if not index_path.exists() or not index_path.is_file():
        raise ValueError(f"model index is missing or not a file: {index_path}")

    weight_map = _load_index(index_path)
    shard_names: set[str] = set()
    invalid: set[str] = set()

    for value in weight_map.values():
        if not isinstance(value, str) or not value or os.path.isabs(value):
            invalid.add(repr(value))
            continue
        candidate = Path(value)
        if any(part == ".." for part in candidate.parts):
            invalid.add(value)
            continue
        shard_names.add(value)

    missing: list[str] = []
    for name in sorted(shard_names):
        path = model_dir / name
        try:
            if not path.exists() or not path.is_file() or path.stat().st_size <= 0:
                missing.append(name)
        except OSError:
            missing.append(name)

    return CheckpointIntegrity(
        shard_count=len(shard_names),
        missing=tuple(missing),
        invalid=tuple(sorted(invalid)),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify every shard referenced by model.safetensors.index.json."
    )
    parser.add_argument("model_dir", type=Path)
    args = parser.parse_args()

    try:
        result = inspect_checkpoint(args.model_dir)
    except ValueError as exc:
        print(f"checkpoint integrity failed: {exc}", file=sys.stderr)
        return 1

    if result.invalid:
        print(
            "checkpoint integrity failed: invalid shard path(s): "
            + ", ".join(result.invalid),
            file=sys.stderr,
        )
        return 1
    if result.missing:
        print(
            "checkpoint integrity failed: missing, dangling, or empty shard(s): "
            + ", ".join(result.missing),
            file=sys.stderr,
        )
        return 1

    print(f"checkpoint shards are complete ({result.shard_count} referenced shard(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
