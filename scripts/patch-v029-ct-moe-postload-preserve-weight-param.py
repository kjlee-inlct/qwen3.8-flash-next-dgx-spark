#!/usr/bin/env python3
"""H12: remove compressed-tensors post-load packed->weight re-wrapping.

Starting from H11:
- keep OrcaRouter checkpoint names/values unchanged
- keep packed expert weights as ModelWeightParameter during loading
- after loading, rename the registered parameter object without wrapping .data
  in a new torch.nn.Parameter
- leave CT kernel-format conversion and all scale paths unchanged
"""

from __future__ import annotations

import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
start = text.index("class CompressedTensorsW4A4Nvfp4MoEMethod")
body = text[start:]

old = '''        layer.w13_weight = torch.nn.Parameter(
            layer.w13_weight_packed.data, requires_grad=False
        )
        delattr(layer, "w13_weight_packed")

        layer.w2_weight = torch.nn.Parameter(
            layer.w2_weight_packed.data, requires_grad=False
        )
        delattr(layer, "w2_weight_packed")
'''

new = '''        layer.register_parameter("w13_weight", layer.w13_weight_packed)
        delattr(layer, "w13_weight_packed")

        layer.register_parameter("w2_weight", layer.w2_weight_packed)
        delattr(layer, "w2_weight_packed")
'''

if body.count(old) != 1:
    raise SystemExit("expected H11 packed->weight wrapping block not found exactly once")

body = body.replace(old, new, 1)
path.write_text(text[:start] + body, encoding="utf-8")
print("patched CT packed->weight post-load rename to preserve parameter objects")
