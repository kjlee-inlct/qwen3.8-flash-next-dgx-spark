#!/usr/bin/env python3
"""Compatibility entry point for scripts/lib/state_file.py."""

from __future__ import annotations

import runpy
from pathlib import Path


TARGET = Path(__file__).resolve().parent / "lib" / "state_file.py"
runpy.run_path(str(TARGET), run_name="__main__")
