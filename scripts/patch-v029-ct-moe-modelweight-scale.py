#!/usr/bin/env python3
"""Patch vLLM v0.29 compressed-tensors NVFP4 MoE expert weight scales.

H9 changes only the w13/w2 expert weight_scale parameter representation:
- torch.nn.Parameter + set_weight_attrs
  -> ModelWeightParameter(input_dim=1, output_dim=2, weight_loader=...)
- scale metadata GROUP -> BLOCK

Packed weights, global scales, quantization config, post-load conversion, and
kernel selection remain unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

import_needle = "from vllm.model_executor.utils import replace_parameter, set_weight_attrs\n"
import_repl = (
    "from vllm.model_executor.parameter import ModelWeightParameter\n"
    + import_needle
)
if import_needle not in text:
    raise SystemExit("expected utils import not found")
text = text.replace(import_needle, import_repl, 1)

start = text.index("class CompressedTensorsW4A4Nvfp4MoEMethod")
body = text[start:]

w13_old = '''        w13_weight_scale = torch.nn.Parameter(
            torch.empty(
                num_experts,
                w13_num_shards * intermediate_size_per_partition,
                # 2 fp4 items are packed in the input dimension
                hidden_size // self.group_size,
                dtype=torch.float8_e4m3fn,
            ),
            requires_grad=False,
        )
        layer.register_parameter("w13_weight_scale", w13_weight_scale)
        extra_weight_attrs.update(
            {"quant_method": FusedMoeWeightScaleSupported.GROUP.value}
        )
        set_weight_attrs(w13_weight_scale, extra_weight_attrs)
'''
w13_new = '''        weight_loader = extra_weight_attrs.get("weight_loader")
        w13_weight_scale = ModelWeightParameter(
            data=torch.empty(
                num_experts,
                w13_num_shards * intermediate_size_per_partition,
                # 2 fp4 items are packed in the input dimension
                hidden_size // self.group_size,
                dtype=torch.float8_e4m3fn,
            ),
            input_dim=1,
            output_dim=2,
            weight_loader=weight_loader,
        )
        layer.register_parameter("w13_weight_scale", w13_weight_scale)
        extra_weight_attrs.update(
            {"quant_method": FusedMoeWeightScaleSupported.BLOCK.value}
        )
'''

w2_old = '''        w2_weight_scale = torch.nn.Parameter(
            torch.empty(
                num_experts,
                hidden_size,
                # 2 fp4 items are packed in the input dimension
                intermediate_size_per_partition // self.group_size,
                dtype=torch.float8_e4m3fn,
            ),
            requires_grad=False,
        )
        layer.register_parameter("w2_weight_scale", w2_weight_scale)
        extra_weight_attrs.update(
            {"quant_method": FusedMoeWeightScaleSupported.GROUP.value}
        )
        set_weight_attrs(w2_weight_scale, extra_weight_attrs)
'''
w2_new = '''        w2_weight_scale = ModelWeightParameter(
            data=torch.empty(
                num_experts,
                hidden_size,
                # 2 fp4 items are packed in the input dimension
                intermediate_size_per_partition // self.group_size,
                dtype=torch.float8_e4m3fn,
            ),
            input_dim=1,
            output_dim=2,
            weight_loader=weight_loader,
        )
        layer.register_parameter("w2_weight_scale", w2_weight_scale)
        extra_weight_attrs.update(
            {"quant_method": FusedMoeWeightScaleSupported.BLOCK.value}
        )
'''

if body.count(w13_old) != 1:
    raise SystemExit("expected w13 compressed-tensors scale block not found exactly once")
if body.count(w2_old) != 1:
    raise SystemExit("expected w2 compressed-tensors scale block not found exactly once")
body = body.replace(w13_old, w13_new, 1).replace(w2_old, w2_new, 1)
path.write_text(text[:start] + body, encoding="utf-8")
print("patched CT NVFP4 MoE weight_scale parameters to ModelWeightParameter + BLOCK")
