#!/usr/bin/env python3
"""Compatibility entry point for scripts.model.inspect_model."""

from model.inspect_model import *  # noqa: F401,F403
from model.inspect_model import main as _main


if __name__ == "__main__":
    raise SystemExit(_main())
