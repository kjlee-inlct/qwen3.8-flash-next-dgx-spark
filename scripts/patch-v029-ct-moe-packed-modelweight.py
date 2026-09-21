#!/usr/bin/env python3
"""H11: change only compressed-tensors packed expert weight parameter objects.

Starting from H10:
- keep original OrcaRouter checkpoint names/values
- keep w13_weight_packed / w2_weight_packed on-disk names
- change only torch.nn.Parameter -> ModelWeightParameter
- keep CT post-load packed->weight rename/wrapping unchanged
"""

from __future__ import annotations

import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
start = text.index("class CompressedTensorsW4A4Nvfp4MoEMethod")
body = text[start:]

needle = """        layer.num_experts = num_experts
        layer.params_dtype = params_dtype
        w13_num_shards = 2 if self.moe.is_act_and_mul else 1
"""
repl = """        layer.num_experts = num_experts
        layer.params_dtype = params_dtype
        weight_loader = extra_weight_attrs.get("weight_loader")
        w13_num_shards = 2 if self.moe.is_act_and_mul else 1
"""
if body.count(needle) != 1:
    raise SystemExit("expected create_weights prologue not found exactly once")
body = body.replace(needle, repl, 1)

w13_old = """        w13_weight = torch.nn.Parameter(
            torch.empty(
                num_experts,
                w13_num_shards * intermediate_size_per_partition,
                # 2 fp4 items are packed in the input dimension
                hidden_size // 2,
                requires_grad=False,
                dtype=torch.uint8,
            ),
            requires_grad=False,
        )
        layer.register_parameter("w13_weight_packed", w13_weight)
        set_weight_attrs(w13_weight, extra_weight_attrs)
"""
w13_new = """        w13_weight = ModelWeightParameter(
            data=torch.empty(
                num_experts,
                w13_num_shards * intermediate_size_per_partition,
                # 2 fp4 items are packed in the input dimension
                hidden_size // 2,
                dtype=torch.uint8,
            ),
            input_dim=1,
            output_dim=2,
            weight_loader=weight_loader,
        )
        layer.register_parameter("w13_weight_packed", w13_weight)
"""

w2_old = """        w2_weight = torch.nn.Parameter(
            torch.empty(
                num_experts,
                hidden_size,
                # 2 fp4 items are packed in the input dimension
                intermediate_size_per_partition // 2,
                dtype=torch.uint8,
            ),
            requires_grad=False,
        )
        layer.register_parameter("w2_weight_packed", w2_weight)
        set_weight_attrs(w2_weight, extra_weight_attrs)
"""
w2_new = """        w2_weight = ModelWeightParameter(
            data=torch.empty(
                num_experts,
                hidden_size,
                # 2 fp4 items are packed in the input dimension
                intermediate_size_per_partition // 2,
                dtype=torch.uint8,
            ),
            input_dim=1,
            output_dim=2,
            weight_loader=weight_loader,
        )
        layer.register_parameter("w2_weight_packed", w2_weight)
"""

if body.count(w13_old) != 1:
    raise SystemExit("expected H10 w13 packed-weight block not found exactly once")
if body.count(w2_old) != 1:
    raise SystemExit("expected H10 w2 packed-weight block not found exactly once")

body = body.replace(w13_old, w13_new, 1).replace(w2_old, w2_new, 1)
path.write_text(text[:start] + body, encoding="utf-8")
print("patched CT packed expert weights to ModelWeightParameter")
