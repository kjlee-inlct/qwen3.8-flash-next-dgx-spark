#!/usr/bin/env python3
"""Compatibility entry point for scripts/runtime/validate_runtime.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_TARGET = Path(__file__).with_name("runtime") / "validate_runtime.py"
_SPEC = importlib.util.spec_from_file_location("_qwen38_validate_runtime", _TARGET)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"cannot load canonical runtime validator: {_TARGET}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)
for _name in dir(_MODULE):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_MODULE, _name)

if __name__ == "__main__":
    raise SystemExit(_MODULE.main())
