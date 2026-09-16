#!/usr/bin/env python3
"""Compatibility entry point for scripts.runtime.validate_runtime."""

from runtime.validate_runtime import *  # noqa: F401,F403
from runtime.validate_runtime import main as _main


if __name__ == "__main__":
    raise SystemExit(_main())
