#!/usr/bin/env python3
"""Install H20-M single-pass Marlin expert boundary capture in vLLM v0.29."""

from __future__ import annotations

import sys
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit(
        "usage: patch-v029-h20-marlin-boundary.py <marlin_moe.py>"
    )

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"expected {label} exactly once, found {count}")
    return source.replace(old, new, 1)


text = replace_once(
    text,
    "import math\n",
    "import json\nimport math\nimport os\n",
    "math import",
)

helper_anchor = "from vllm.scalar_type import ScalarType, scalar_types\n\n\n"
helper = r'''from vllm.scalar_type import ScalarType, scalar_types


_QWEN38_H20M_TRIGGER = os.getenv(
    "QWEN38_H20M_TRIGGER", "/tmp/qwen38_h20m_marlin.enable"
)
_QWEN38_H20M_REQUEST_FILE = os.getenv(
    "QWEN38_H20M_REQUEST_FILE", "/tmp/qwen38_h20m_request_id"
)
_QWEN38_H20M_TARGET_LAYER = os.getenv(
    "QWEN38_H20M_TARGET_LAYER",
    "language_model.model.layers.15.mlp.experts",
)
try:
    _QWEN38_H20M_TARGET_LAYER_IDX = int(
        _QWEN38_H20M_TARGET_LAYER.split(".layers.", 1)[1].split(".", 1)[0]
    )
except (IndexError, ValueError):
    _QWEN38_H20M_TARGET_LAYER_IDX = -1

_QWEN38_H20M_ACTIVE: dict[int, dict[str, torch.Tensor | None]] = {}
_QWEN38_H20M_COMPLETED: dict[int, dict[str, torch.Tensor | None]] = {}
_QWEN38_H20M_STAGE_NAMES = {
    0: "entry_hidden_states",
    1: "entry_topk_weights",
    2: "entry_topk_ids",
    3: "aligned_sorted_token_ids",
    4: "aligned_expert_ids",
    5: "aligned_num_tokens_post_padded",
    6: "w13_input",
    7: "w13_input_scale",
    8: "w13_output",
    9: "activation_output",
    10: "w2_input",
    11: "w2_input_scale",
    12: "w2_output",
    13: "final_output",
}


def _qwen38_h20m_compare(
    left: torch.Tensor | None,
    right: torch.Tensor | None,
) -> dict:
    if left is None or right is None:
        return {
            "equal": left is None and right is None,
            "shape_match": left is None and right is None,
        }
    if tuple(left.shape) != tuple(right.shape):
        return {
            "equal": False,
            "shape_match": False,
            "request0_shape": list(left.shape),
            "request1_shape": list(right.shape),
        }
    return {
        "equal": bool(torch.equal(left, right)),
        "shape_match": True,
        "shape": list(left.shape),
        "dtype": str(left.dtype),
    }


def _qwen38_h20m_commit(
    *,
    request_id: int,
    snapshots: dict[str, torch.Tensor | None],
) -> None:
    field_order = tuple(
        _QWEN38_H20M_STAGE_NAMES[index]
        for index in sorted(_QWEN38_H20M_STAGE_NAMES)
    )
    for previous_id in sorted(_QWEN38_H20M_COMPLETED):
        if previous_id == request_id:
            continue
        previous = _QWEN38_H20M_COMPLETED[previous_id]
        fields = {
            name: _qwen38_h20m_compare(previous.get(name), snapshots.get(name))
            for name in field_order
        }
        first_mismatch = next(
            (name for name in field_order if not fields[name]["equal"]),
            None,
        )
        record = {
            "schema": 3,
            "phase": "marlin-repeat",
            "backend": "MARLIN",
            "layer_name": _QWEN38_H20M_TARGET_LAYER,
            "request0": previous_id,
            "request1": request_id,
            "fields": fields,
            "first_mismatch": first_mismatch,
            "entry_equal": all(
                fields[name]["equal"]
                for name in (
                    "entry_hidden_states",
                    "entry_topk_weights",
                    "entry_topk_ids",
                )
            ),
            "alignment_equal": all(
                fields[name]["equal"]
                for name in (
                    "aligned_sorted_token_ids",
                    "aligned_expert_ids",
                    "aligned_num_tokens_post_padded",
                )
            ),
            "w13_input_equal": all(
                fields[name]["equal"]
                for name in ("w13_input", "w13_input_scale")
            ),
            "w13_output_equal": fields["w13_output"]["equal"],
            "activation_output_equal": fields["activation_output"]["equal"],
            "w2_input_equal": all(
                fields[name]["equal"]
                for name in ("w2_input", "w2_input_scale")
            ),
            "w2_output_equal": fields["w2_output"]["equal"],
            "final_output_equal": fields["final_output"]["equal"],
        }
        print(
            "QWEN38_H20M_MARLIN " + json.dumps(record, sort_keys=True),
            flush=True,
        )

    _QWEN38_H20M_COMPLETED[request_id] = snapshots
    while len(_QWEN38_H20M_COMPLETED) > 16:
        oldest = min(_QWEN38_H20M_COMPLETED)
        del _QWEN38_H20M_COMPLETED[oldest]


@torch.library.custom_op(
    "qwen38_h20m::capture",
    mutates_args={"tensor"},
)
def _qwen38_h20m_capture(
    tensor: torch.Tensor,
    stage: int,
    layer_idx: int,
) -> None:
    if layer_idx != _QWEN38_H20M_TARGET_LAYER_IDX:
        return
    if not os.path.exists(_QWEN38_H20M_TRIGGER):
        return
    stage_name = _QWEN38_H20M_STAGE_NAMES.get(stage)
    if stage_name is None:
        return
    try:
        with open(_QWEN38_H20M_REQUEST_FILE, encoding="utf-8") as handle:
            request_id = int(handle.read().strip())
    except (OSError, ValueError):
        return

    snapshots = _QWEN38_H20M_ACTIVE.setdefault(request_id, {})
    snapshots[stage_name] = tensor.detach().clone()
    if stage == 13:
        snapshots = _QWEN38_H20M_ACTIVE.pop(request_id)
        _qwen38_h20m_commit(request_id=request_id, snapshots=snapshots)


'''
text = replace_once(text, helper_anchor, helper, "helper anchor")

fused_sig_old = '''    activation_config: ApplyMoEActivationConfig | None = None,
) -> torch.Tensor:
'''
fused_sig_new = '''    activation_config: ApplyMoEActivationConfig | None = None,
    h20m_layer_idx: int = -1,
) -> torch.Tensor:
'''
text = replace_once(
    text,
    fused_sig_old,
    fused_sig_new,
    "_fused_marlin_moe signature",
)

w13_input_old = '''    a_scales1 = None
    gate_up_input = hidden_states
    if input_dtype == torch.int8:
'''
w13_input_new = '''    a_scales1 = None
    gate_up_input = hidden_states
    if input_dtype == torch.int8:
'''
# Keep the quantization logic unchanged; capture immediately before GEMM.
if text.count(w13_input_old) != 1:
    raise SystemExit("unexpected w13 input anchor count")

w13_gemm_old = '''    intermediate_cache1 = ops.moe_wna16_marlin_gemm(
        gate_up_input,
'''
w13_gemm_new = '''    _qwen38_h20m_capture(gate_up_input, 6, h20m_layer_idx)
    if a_scales1 is not None:
        _qwen38_h20m_capture(a_scales1, 7, h20m_layer_idx)

    intermediate_cache1 = ops.moe_wna16_marlin_gemm(
        gate_up_input,
'''
text = replace_once(text, w13_gemm_old, w13_gemm_new, "w13 GEMM input")

activation_old = '''    activation_input = intermediate_cache1.view(-1, w13_num_shards * N)
    if activation_func is None:
'''
activation_new = '''    _qwen38_h20m_capture(intermediate_cache1, 8, h20m_layer_idx)
    activation_input = intermediate_cache1.view(-1, w13_num_shards * N)
    if activation_func is None:
'''
text = replace_once(text, activation_old, activation_new, "w13 output")

w2_quant_old = '''    if output is None:
        output = intermediate_cache3

    a_scales2 = None
'''
w2_quant_new = '''    _qwen38_h20m_capture(intermediate_cache2, 9, h20m_layer_idx)

    if output is None:
        output = intermediate_cache3

    a_scales2 = None
'''
text = replace_once(text, w2_quant_old, w2_quant_new, "activation output")

w2_gemm_old = '''    output = ops.moe_wna16_marlin_gemm(
        intermediate_cache2,
'''
w2_gemm_new = '''    _qwen38_h20m_capture(intermediate_cache2, 10, h20m_layer_idx)
    if a_scales2 is not None:
        _qwen38_h20m_capture(a_scales2, 11, h20m_layer_idx)

    output = ops.moe_wna16_marlin_gemm(
        intermediate_cache2,
'''
text = replace_once(text, w2_gemm_old, w2_gemm_new, "w2 GEMM input")

fused_return_old = '''    return output


def fused_marlin_moe(
'''
fused_return_new = '''    _qwen38_h20m_capture(output, 12, h20m_layer_idx)
    return output


def fused_marlin_moe(
'''
text = replace_once(text, fused_return_old, fused_return_new, "w2 output")

public_sig_old = '''    activation_config: ApplyMoEActivationConfig | None = None,
) -> torch.Tensor:
    """
    This function computes a Mixture of Experts (MoE) layer using two sets of
'''
public_sig_new = '''    activation_config: ApplyMoEActivationConfig | None = None,
    h20m_layer_idx: int = -1,
) -> torch.Tensor:
    """
    This function computes a Mixture of Experts (MoE) layer using two sets of
'''
text = replace_once(text, public_sig_old, public_sig_new, "fused_marlin_moe signature")

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
    _qwen38_h20m_capture(sorted_token_ids, 3, h20m_layer_idx)
    _qwen38_h20m_capture(expert_ids, 4, h20m_layer_idx)
    _qwen38_h20m_capture(num_tokens_post_padded, 5, h20m_layer_idx)

    assert activation is not None
'''
text = replace_once(text, align_old, align_new, "alignment outputs")

call_tail_old = '''        input_dtype=input_dtype,
        is_k_full=is_k_full,
    ).view(-1, topk, K)

    if output is None:
'''
call_tail_new = '''        input_dtype=input_dtype,
        is_k_full=is_k_full,
        h20m_layer_idx=h20m_layer_idx,
    ).view(-1, topk, K)

    if output is None:
'''
text = replace_once(text, call_tail_old, call_tail_new, "_fused_marlin_moe call")

reduce_old = '''    if moe_sum is None:
        if expert_map is not None:
            ops.moe_sum(moe_output, output, topk_ids, expert_map)
            return output
        return torch.sum(moe_output.view(-1, topk, K), dim=1, out=output)
    else:
        return moe_sum(moe_output, output, topk_ids, expert_map)
'''
reduce_new = '''    if moe_sum is None:
        if expert_map is not None:
            ops.moe_sum(moe_output, output, topk_ids, expert_map)
            result = output
        else:
            result = torch.sum(moe_output.view(-1, topk, K), dim=1, out=output)
    else:
        result = moe_sum(moe_output, output, topk_ids, expert_map)

    _qwen38_h20m_capture(
        output if result is None else result,
        13,
        h20m_layer_idx,
    )
    return result
'''
text = replace_once(text, reduce_old, reduce_new, "final reduction")

apply_entry_old = '''        assert self.w1_scale is not None
        assert self.w2_scale is not None

        ctx = self._lora_context
'''
apply_entry_new = '''        assert self.w1_scale is not None
        assert self.w2_scale is not None

        h20m_layer_idx = int(getattr(self, "_qwen38_h20_layer_idx", -1))
        _qwen38_h20m_capture(hidden_states, 0, h20m_layer_idx)
        _qwen38_h20m_capture(topk_weights, 1, h20m_layer_idx)
        _qwen38_h20m_capture(topk_ids, 2, h20m_layer_idx)

        ctx = self._lora_context
'''
text = replace_once(text, apply_entry_old, apply_entry_new, "MarlinExperts apply entry")

non_lora_tail_old = '''                is_k_full=self.is_k_full,
                input_dtype=self.input_dtype,
            )
            return
'''
non_lora_tail_new = '''                is_k_full=self.is_k_full,
                input_dtype=self.input_dtype,
                h20m_layer_idx=h20m_layer_idx,
            )
            return
'''
text = replace_once(text, non_lora_tail_old, non_lora_tail_new, "non-LoRA call")

lora_tail_old = '''            is_k_full=self.is_k_full,
            input_dtype=self.input_dtype,
        )
'''
lora_tail_new = '''            is_k_full=self.is_k_full,
            input_dtype=self.input_dtype,
            h20m_layer_idx=h20m_layer_idx,
        )
'''
text = replace_once(text, lora_tail_old, lora_tail_new, "LoRA call")

path.write_text(text, encoding="utf-8")
print("installed H20-M Marlin boundary capture")
