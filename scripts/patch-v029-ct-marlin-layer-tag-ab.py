#!/usr/bin/env python3
"""Tag vLLM v0.29 CT Marlin experts with the owning decoder layer index."""

from __future__ import annotations

import sys
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit(
        "usage: patch-v029-ct-marlin-layer-tag-ab.py "
        "<compressed_tensors_moe_w4a4_nvfp4.py>"
    )

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

old = '''    def apply(
        self,
        layer: RoutedExperts,
        x: torch.Tensor,
        topk_weights: torch.Tensor,
        topk_ids: torch.Tensor,
        shared_experts: SharedExperts | None,
        shared_experts_input: torch.Tensor | None,
    ) -> torch.Tensor:
        assert self.moe_kernel is not None
        return self.moe_kernel.apply(
            x,
            layer.w13_weight,
            layer.w2_weight,
            topk_weights,
            topk_ids,
            activation=layer.activation,
            global_num_experts=layer.global_num_experts,
            expert_map=layer.expert_map,
            apply_router_weight_on_input=layer.apply_router_weight_on_input,
            shared_experts=shared_experts,
            shared_experts_input=shared_experts_input,
        )
'''

new = '''    def apply(
        self,
        layer: RoutedExperts,
        x: torch.Tensor,
        topk_weights: torch.Tensor,
        topk_ids: torch.Tensor,
        shared_experts: SharedExperts | None,
        shared_experts_input: torch.Tensor | None,
    ) -> torch.Tensor:
        assert self.moe_kernel is not None
        layer_name = str(getattr(layer, "layer_name", ""))
        try:
            layer_idx = int(
                layer_name.split(".layers.", 1)[1].split(".", 1)[0]
            )
        except (IndexError, ValueError):
            layer_idx = -1
        self.moe_kernel.impl.fused_experts._qwen38_marlin_layer_idx = layer_idx
        return self.moe_kernel.apply(
            x,
            layer.w13_weight,
            layer.w2_weight,
            topk_weights,
            topk_ids,
            activation=layer.activation,
            global_num_experts=layer.global_num_experts,
            expert_map=layer.expert_map,
            apply_router_weight_on_input=layer.apply_router_weight_on_input,
            shared_experts=shared_experts,
            shared_experts_input=shared_experts_input,
        )
'''

class_name = "CompressedTensorsW4A4Nvfp4MoEMethod"
start = text.index(f"class {class_name}")
end = text.find("\nclass ", start + 1)
if end < 0:
    end = len(text)
prefix, body, suffix = text[:start], text[start:end], text[end:]
if body.count(old) != 1:
    raise SystemExit(f"expected {class_name}.apply() exactly once")
text = prefix + body.replace(old, new, 1) + suffix

path.write_text(text, encoding="utf-8")
print("installed CT Marlin decoder-layer tag")
