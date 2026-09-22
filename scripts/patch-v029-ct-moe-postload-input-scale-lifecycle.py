#!/usr/bin/env python3
"""H18: align CT post-load input_scale lifecycle with ModelOpt.

Starting from H12:
- keep OrcaRouter checkpoint names/values unchanged during loading
- keep H12 packed-weight object preservation
- leave weight_scale_2/global-scale lifecycle unchanged
- after loading, rename w13/w2_input_global_scale parameter objects to the
  final w13/w2_input_scale names before kernel-format conversion
- keep reciprocal conversion values unchanged
- replace the converted input scales through replace_parameter(), matching the
  ModelOpt final-name lifecycle more closely
"""

from __future__ import annotations

import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
start = text.index("class CompressedTensorsW4A4Nvfp4MoEMethod")
body = text[start:]

anchor = '''        # Use a single gscale for w13.
'''
rename = '''        # Canonicalize loaded input-global-scale parameter names before
        # conversion so replace_parameter() operates on existing final names.
        w13_input_scale_param = layer.w13_input_global_scale
        delattr(layer, "w13_input_global_scale")
        layer.register_parameter("w13_input_scale", w13_input_scale_param)

        w2_input_scale_param = layer.w2_input_global_scale
        delattr(layer, "w2_input_global_scale")
        layer.register_parameter("w2_input_scale", w2_input_scale_param)

        # Use a single gscale for w13.
'''
if body.count(anchor) != 1:
    raise SystemExit("expected H12 single-gscale anchor not found exactly once")
body = body.replace(anchor, rename, 1)

conversions = {
    "a13_scale=(1.0 / layer.w13_input_global_scale)": "a13_scale=(1.0 / layer.w13_input_scale)",
    "a2_scale=(1.0 / layer.w2_input_global_scale)": "a2_scale=(1.0 / layer.w2_input_scale)",
}
for old, new in conversions.items():
    if body.count(old) != 1:
        raise SystemExit(f"expected H12 input-scale conversion fragment not found exactly once: {old}")
    body = body.replace(old, new, 1)

old_assign = '''        layer.w13_input_scale = a13_scale
        layer.w2_input_scale = a2_scale
'''
new_assign = '''        replace_parameter(layer, "w13_input_scale", a13_scale)
        replace_parameter(layer, "w2_input_scale", a2_scale)
'''
if body.count(old_assign) != 1:
    raise SystemExit("expected H12 direct input-scale assignment block not found exactly once")
body = body.replace(old_assign, new_assign, 1)

path.write_text(text[:start] + body, encoding="utf-8")
print("patched CT post-load input_scale lifecycle to canonical final names")
