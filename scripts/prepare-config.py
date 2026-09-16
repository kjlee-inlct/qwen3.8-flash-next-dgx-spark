#!/usr/bin/env python3
"""Compatibility entry point for scripts.model.prepare_config."""

from model.prepare_config import *  # noqa: F401,F403
from model.prepare_config import main as _main


if __name__ == "__main__":
    _main()
