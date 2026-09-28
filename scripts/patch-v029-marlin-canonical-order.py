#!/usr/bin/env python3
"""Install the minimal vLLM v0.29 Marlin MoE deterministic-order repair."""

from __future__ import annotations

import sys
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit(
        "usage: patch-v029-marlin-canonical-order.py <marlin_moe.py>"
    )

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"expected {label} exactly once, found {count}")
    return source.replace(old, new, 1)


helper_anchor = "from vllm.scalar_type import ScalarType, scalar_types\n\n\n"
helper = r'''from vllm.scalar_type import ScalarType, scalar_types


def _qwen38_canonicalize_marlin_sorted_tokens(
    sorted_token_ids: torch.Tensor,
    expert_ids: torch.Tensor,
    num_tokens_post_padded: torch.Tensor,
    block_size_m: int,
    total_routed_tokens: int,
    layer_idx: int,
) -> torch.Tensor:
    """Return deterministic ordering for tagged decoder Marlin experts."""

    if block_size_m <= 0 or layer_idx < 0:
        return sorted_token_ids

    full_blocks = sorted_token_ids.numel() // block_size_m
    if full_blocks <= 0:
        return sorted_token_ids
    prefix_len = full_blocks * block_size_m

    block_experts = expert_ids[:full_blocks].to(torch.int64)
    if block_experts.numel() != full_blocks:
        return sorted_token_ids

    changes = torch.cat(
        (
            torch.ones(
                (1,),
                dtype=torch.int64,
                device=sorted_token_ids.device,
            ),
            (block_experts[1:] != block_experts[:-1]).to(torch.int64),
        )
    )
    group_rank = torch.cumsum(changes, dim=0) - 1
    position_group = torch.repeat_interleave(group_rank, block_size_m)

    positions = torch.arange(
        prefix_len,
        dtype=torch.int64,
        device=sorted_token_ids.device,
    )
    valid_limit = num_tokens_post_padded.to(torch.int64).reshape(())
    valid_mask = positions < valid_limit

    token_ids = sorted_token_ids[:prefix_len].to(torch.int64)
    token_key = torch.where(
        (token_ids >= 0) & (token_ids < total_routed_tokens),
        token_ids,
        torch.full_like(token_ids, total_routed_tokens),
    )
    base = total_routed_tokens + 1
    valid_key = position_group * base + token_key
    invalid_base = (group_rank[-1] + 2) * base
    key = torch.where(valid_mask, valid_key, invalid_base + positions)

    order = torch.argsort(key, stable=True)
    canonical_prefix = sorted_token_ids[:prefix_len][order]
    if prefix_len == sorted_token_ids.numel():
        return canonical_prefix
    return torch.cat((canonical_prefix, sorted_token_ids[prefix_len:]))


'''
text = replace_once(text, helper_anchor, helper, "helper anchor")

fused_start = text.index("def _fused_marlin_moe(")
public_start = text.index("\n\ndef fused_marlin_moe(", fused_start)
fused_body = text[fused_start:public_start]
fused_body = replace_once(
    fused_body,
    "    activation_config: ApplyMoEActivationConfig | None = None,\n) -> torch.Tensor:\n",
    "    activation_config: ApplyMoEActivationConfig | None = None,\n    h38_layer_idx: int = -1,\n) -> torch.Tensor:\n",
    "_fused_marlin_moe signature",
)

public_end = text.index("\n\ndef batched_fused_marlin_moe(", public_start)
public_body = text[public_start:public_end]
public_body = replace_once(
    public_body,
    "    activation_config: ApplyMoEActivationConfig | None = None,\n) -> torch.Tensor:\n",
    "    activation_config: ApplyMoEActivationConfig | None = None,\n    h38_layer_idx: int = -1,\n) -> torch.Tensor:\n",
    "fused_marlin_moe signature",
)

align_old = '''    sorted_token_ids, expert_ids, num_tokens_post_padded = moe_align_block_size(
        topk_ids,
        block_size_m,
        global_num_experts,
        expert_map,
        ignore_invalid_experts=True,
    )

    assert activation is not None
'''
align_new = '''    sorted_token_ids, expert_ids, num_tokens_post_padded = moe_align_block_size(
        topk_ids,
        block_size_m,
        global_num_experts,
        expert_map,
        ignore_invalid_experts=True,
    )
    sorted_token_ids = _qwen38_canonicalize_marlin_sorted_tokens(
        sorted_token_ids,
        expert_ids,
        num_tokens_post_padded,
        block_size_m,
        topk_ids.numel(),
        h38_layer_idx,
    )

    assert activation is not None
'''
public_body = replace_once(
    public_body, align_old, align_new, "Marlin alignment output"
)
public_body = replace_once(
    public_body,
    "        input_dtype=input_dtype,\n        is_k_full=is_k_full,\n    ).view(-1, topk, K)\n",
    "        input_dtype=input_dtype,\n        is_k_full=is_k_full,\n        h38_layer_idx=h38_layer_idx,\n    ).view(-1, topk, K)\n",
    "_fused_marlin_moe call",
)

class_start = text.index("class MarlinExperts(")
class_end = text.index("\n\nclass BatchedMarlinExperts", class_start)
class_body = text[class_start:class_end]

apply_anchor = """        assert self.w1_scale is not None
        assert self.w2_scale is not None

        ctx = self._lora_context
"""
apply_new = """        assert self.w1_scale is not None
        assert self.w2_scale is not None

        h38_layer_idx = int(
            getattr(self, "_qwen38_marlin_layer_idx", -1)
        )
        ctx = self._lora_context
"""
class_body = replace_once(
    class_body, apply_anchor, apply_new, "MarlinExperts apply layer tag"
)

non_lora_old = """                is_k_full=self.is_k_full,
                input_dtype=self.input_dtype,
            )
            return
"""
non_lora_new = """                is_k_full=self.is_k_full,
                input_dtype=self.input_dtype,
                h38_layer_idx=h38_layer_idx,
            )
            return
"""
class_body = replace_once(
    class_body, non_lora_old, non_lora_new, "non-LoRA call"
)

lora_old = """            is_k_full=self.is_k_full,
            input_dtype=self.input_dtype,
        )
"""
lora_new = """            is_k_full=self.is_k_full,
            input_dtype=self.input_dtype,
            h38_layer_idx=h38_layer_idx,
        )
"""
class_body = replace_once(
    class_body, lora_old, lora_new, "LoRA call"
)

text = (
    text[:fused_start]
    + fused_body
    + public_body
    + text[public_end:class_start]
    + class_body
    + text[class_end:]
)

path.write_text(text, encoding="utf-8")
print("installed minimal Marlin canonical-order repair")
