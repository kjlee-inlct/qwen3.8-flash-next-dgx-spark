#!/usr/bin/env python3
"""H13: change only CT input-global-scale parameter objects.

Starting from H12:
- keep checkpoint names/values unchanged
- keep packed-weight object preservation from H12
- change w13_input_global_scale / w2_input_global_scale from plain Parameter
  to PerTensorScaleParameter(weight_loader=...)
- keep reciprocal conversion and post-load assignments unchanged
"""

from __future__ import annotations

import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

import_needle = """from vllm.model_executor.parameter import (
    ModelWeightParameter,
    PerTensorScaleParameter,
)
"""
if import_needle not in text:
    raise SystemExit("expected H10/H12 parameter import not found")

start = text.index("class CompressedTensorsW4A4Nvfp4MoEMethod")
body = text[start:]

w13_old = '''        w13_input_scale = torch.nn.Parameter(
            torch.empty(num_experts, w13_num_shards, dtype=torch.float32),
            requires_grad=False,
        )
        layer.register_parameter("w13_input_global_scale", w13_input_scale)
        extra_weight_attrs.update(
            {"quant_method": FusedMoeWeightScaleSupported.TENSOR.value}
        )
        set_weight_attrs(w13_input_scale, extra_weight_attrs)
'''
w13_new = '''        w13_input_scale = PerTensorScaleParameter(
            data=torch.empty(
                num_experts,
                w13_num_shards,
                dtype=torch.float32,
            ),
            weight_loader=weight_loader,
        )
        layer.register_parameter("w13_input_global_scale", w13_input_scale)
        set_weight_attrs(
            w13_input_scale,
            {"quant_method": FusedMoeWeightScaleSupported.TENSOR.value},
        )
'''

w2_old = '''        w2_input_scale = torch.nn.Parameter(
            torch.empty(num_experts, dtype=torch.float32), requires_grad=False
        )
        layer.register_parameter("w2_input_global_scale", w2_input_scale)
        extra_weight_attrs.update(
            {"quant_method": FusedMoeWeightScaleSupported.TENSOR.value}
        )
        set_weight_attrs(w2_input_scale, extra_weight_attrs)
'''
w2_new = '''        w2_input_scale = PerTensorScaleParameter(
            data=torch.empty(num_experts, dtype=torch.float32),
            weight_loader=weight_loader,
        )
        layer.register_parameter("w2_input_global_scale", w2_input_scale)
        set_weight_attrs(
            w2_input_scale,
            {"quant_method": FusedMoeWeightScaleSupported.TENSOR.value},
        )
'''

if body.count(w13_old) != 1:
    raise SystemExit("expected H12 w13 input-global-scale block not found exactly once")
if body.count(w2_old) != 1:
    raise SystemExit("expected H12 w2 input-global-scale block not found exactly once")

body = body.replace(w13_old, w13_new, 1).replace(w2_old, w2_new, 1)
path.write_text(text[:start] + body, encoding="utf-8")
print("patched CT input global scales to PerTensorScaleParameter")
