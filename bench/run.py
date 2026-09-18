#!/usr/bin/env python3
"""Compatibility entry point for scripts/benchmark/run.py."""

from __future__ import annotations

import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CANONICAL_DIR = ROOT / "scripts" / "benchmark"
CANONICAL = CANONICAL_DIR / "run.py"

if str(CANONICAL_DIR) not in sys.path:
    sys.path.insert(0, str(CANONICAL_DIR))

spec = importlib.util.spec_from_file_location("_qwen38_benchmark_run", CANONICAL)
if spec is None or spec.loader is None:
    raise RuntimeError(f"cannot load canonical benchmark runner: {CANONICAL}")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

for name in dir(module):
    if not name.startswith("_"):
        globals()[name] = getattr(module, name)

if __name__ == "__main__":
    sys.exit(module.main())
