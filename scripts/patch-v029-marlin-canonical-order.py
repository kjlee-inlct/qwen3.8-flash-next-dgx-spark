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
) -> torch.Tensor:
    """Return a deterministic within-expert physical routed-token order."""

    if block_size_m <= 0:
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
    )

    assert activation is not None
'''
text = replace_once(text, align_old, align_new, "Marlin alignment output")

path.write_text(text, encoding="utf-8")
print("installed minimal Marlin canonical-order repair")
