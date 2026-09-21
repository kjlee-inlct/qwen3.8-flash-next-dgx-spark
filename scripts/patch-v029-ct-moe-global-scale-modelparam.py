#!/usr/bin/env python3
"""Patch H9 compressed-tensors NVFP4 MoE global-scale parameter representation.

H10 starts from the corrected H9 image and changes only w13/w2
weight_global_scale parameters:
- torch.nn.Parameter + TENSOR attrs
  -> PerTensorScaleParameter(weight_loader=...)

The on-disk checkpoint values, parameter names, reciprocal conversion
(1/global_scale), packed expert weights, input-global scales, and kernel path
remain unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

import_needle = "from vllm.model_executor.parameter import ModelWeightParameter\n"
import_repl = (
    "from vllm.model_executor.parameter import (\n"
    "    ModelWeightParameter,\n"
    "    PerTensorScaleParameter,\n"
    ")\n"
)
if import_needle not in text:
    raise SystemExit("expected H9 ModelWeightParameter import not found")
text = text.replace(import_needle, import_repl, 1)

start = text.index("class CompressedTensorsW4A4Nvfp4MoEMethod")
body = text[start:]

w13_old = '''        w13_weight_scale_2 = torch.nn.Parameter(
            torch.empty(num_experts, w13_num_shards, dtype=torch.float32),
            requires_grad=False,
        )
        layer.register_parameter("w13_weight_global_scale", w13_weight_scale_2)
        extra_weight_attrs.update(
            {"quant_method": FusedMoeWeightScaleSupported.TENSOR.value}
        )
        set_weight_attrs(w13_weight_scale_2, extra_weight_attrs)
'''
w13_new = '''        w13_weight_scale_2 = PerTensorScaleParameter(
            data=torch.empty(num_experts, w13_num_shards, dtype=torch.float32),
            weight_loader=weight_loader,
        )
        layer.register_parameter("w13_weight_global_scale", w13_weight_scale_2)
'''

w2_old = '''        w2_weight_scale_2 = torch.nn.Parameter(
            torch.empty(num_experts, dtype=torch.float32), requires_grad=False
        )
        layer.register_parameter("w2_weight_global_scale", w2_weight_scale_2)
        extra_weight_attrs.update(
            {"quant_method": FusedMoeWeightScaleSupported.TENSOR.value}
        )
        set_weight_attrs(w2_weight_scale_2, extra_weight_attrs)
'''
w2_new = '''        w2_weight_scale_2 = PerTensorScaleParameter(
            data=torch.empty(num_experts, dtype=torch.float32),
            weight_loader=weight_loader,
        )
        layer.register_parameter("w2_weight_global_scale", w2_weight_scale_2)
'''

if body.count(w13_old) != 1:
    raise SystemExit("expected H9 w13 global-scale block not found exactly once")
if body.count(w2_old) != 1:
    raise SystemExit("expected H9 w2 global-scale block not found exactly once")

body = body.replace(w13_old, w13_new, 1).replace(w2_old, w2_new, 1)
path.write_text(text[:start] + body, encoding="utf-8")
print("patched CT NVFP4 MoE weight_global_scale parameters to PerTensorScaleParameter")
