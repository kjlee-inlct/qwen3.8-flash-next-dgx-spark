#!/usr/bin/env python3
"""Compatibility import for benchmark helpers under scripts/benchmark."""

from __future__ import annotations

import pathlib
import sys

CANONICAL_DIR = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "benchmark"
if str(CANONICAL_DIR) not in sys.path:
    sys.path.insert(0, str(CANONICAL_DIR))

from lib.common import *  # noqa: F401,F403,E402
