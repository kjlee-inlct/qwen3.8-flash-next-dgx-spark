#!/usr/bin/env python3
"""H14: register CT post-load input scales as parameters.

Starting from H12 (not H13):
- keep input_global_scale checkpoint objects/values unchanged
- keep H12 packed-weight object preservation
- keep reciprocal conversion unchanged
- change only final post-load a13/a2 assignment from plain tensor attributes
  to registered torch.nn.Parameter objects
"""

from __future__ import annotations

import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
start = text.index("class CompressedTensorsW4A4Nvfp4MoEMethod")
body = text[start:]

old = '''        layer.w13_input_scale = a13_scale
        layer.w2_input_scale = a2_scale
'''
new = '''        layer.register_parameter(
            "w13_input_scale",
            torch.nn.Parameter(a13_scale, requires_grad=False),
        )
        layer.register_parameter(
            "w2_input_scale",
            torch.nn.Parameter(a2_scale, requires_grad=False),
        )
'''

if body.count(old) != 1:
    raise SystemExit("expected H12 direct input-scale assignment block not found exactly once")

body = body.replace(old, new, 1)
path.write_text(text[:start] + body, encoding="utf-8")
print("patched CT post-load input scales to registered parameters")
