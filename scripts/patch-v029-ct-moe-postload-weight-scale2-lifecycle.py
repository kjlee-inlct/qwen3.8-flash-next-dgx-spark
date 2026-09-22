#!/usr/bin/env python3
"""H17: align CT post-load weight_scale_2 lifecycle with ModelOpt.

Starting from H12:
- keep OrcaRouter checkpoint names/values unchanged during loading
- keep H10 PerTensorScaleParameter global-scale objects
- keep H12 packed-weight object preservation
- after loading, rename the loaded w13/w2 weight_global_scale parameter objects
  to the final w13/w2_weight_scale_2 names before kernel-format conversion
- keep reciprocal conversion values unchanged
- let replace_parameter() replace an existing final-name parameter, matching the
  ModelOpt post-load lifecycle more closely
- leave input-global-scale/input-scale handling unchanged
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
rename = '''        # Canonicalize loaded global-scale parameter names before conversion so
        # replace_parameter() operates on an existing final-name parameter.
        w13_weight_scale_2_param = layer.w13_weight_global_scale
        delattr(layer, "w13_weight_global_scale")
        layer.register_parameter("w13_weight_scale_2", w13_weight_scale_2_param)

        w2_weight_scale_2_param = layer.w2_weight_global_scale
        delattr(layer, "w2_weight_global_scale")
        layer.register_parameter("w2_weight_scale_2", w2_weight_scale_2_param)

        # Use a single gscale for w13.
'''
if body.count(anchor) != 1:
    raise SystemExit("expected H12 single-gscale anchor not found exactly once")
body = body.replace(anchor, rename, 1)

replacements = {
    "layer.w13_weight_global_scale[:, 0]": "layer.w13_weight_scale_2[:, 0]",
    "layer.w13_weight_global_scale[:, 1]": "layer.w13_weight_scale_2[:, 1]",
    "w13_weight_global_scale = layer.w13_weight_global_scale[:, 0].contiguous()": "w13_weight_scale_2 = layer.w13_weight_scale_2[:, 0].contiguous()",
    "w13_scale_2=(1.0 / w13_weight_global_scale)": "w13_scale_2=(1.0 / w13_weight_scale_2)",
    "w2_scale_2=(1.0 / layer.w2_weight_global_scale)": "w2_scale_2=(1.0 / layer.w2_weight_scale_2)",
}
for old, new in replacements.items():
    if body.count(old) != 1:
        raise SystemExit(f"expected H12 fragment not found exactly once: {old}")
    body = body.replace(old, new, 1)

path.write_text(text[:start] + body, encoding="utf-8")
print("patched CT post-load weight_scale_2 lifecycle to canonical final names")
