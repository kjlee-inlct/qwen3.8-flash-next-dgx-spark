#!/usr/bin/env python3
"""Install H20-W single-pass Humming indexed-expert stage capture in vLLM v0.29."""

from __future__ import annotations

import sys
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit(
        "usage: patch-v029-h20-humming-indexed-boundary.py <fused_humming_moe.py>"
    )

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")


def replace_once(source: str, old: str, new: str, label: str) -> str:
    if source.count(old) != 1:
        raise SystemExit(f"expected {label} exactly once, found {source.count(old)}")
    return source.replace(old, new, 1)


text = replace_once(text, "import json\n", "import json\nimport os\n", "json import")

logger_anchor = "logger = init_logger(__name__)\n"
helper = r'''logger = init_logger(__name__)

_QWEN38_H20W_TRIGGER = os.getenv(
    "QWEN38_H20W_TRIGGER", "/tmp/qwen38_h20w_expert.enable"
)
_QWEN38_H20W_REQUEST_FILE = os.getenv(
    "QWEN38_H20W_REQUEST_FILE", "/tmp/qwen38_h20w_request_id"
)
_QWEN38_H20W_TARGET_LAYER = os.getenv(
    "QWEN38_H20W_TARGET_LAYER",
    "language_model.model.layers.15.mlp.experts",
)
_QWEN38_H20W_PENDING: dict[int, dict[str, torch.Tensor | None]] = {}


def _qwen38_h20w_clone(tensor: torch.Tensor | None) -> torch.Tensor | None:
    return None if tensor is None else tensor.clone()


@torch.compiler.disable
def _qwen38_h20w_request_id(experts) -> int:
    if not os.path.exists(_QWEN38_H20W_TRIGGER):
        return -1
    if str(getattr(experts, "_qwen38_h20_layer_name", "")) != _QWEN38_H20W_TARGET_LAYER:
        return -1
    try:
        with open(_QWEN38_H20W_REQUEST_FILE, encoding="utf-8") as handle:
            return int(handle.read().strip())
    except (OSError, ValueError):
        return -1


@torch.compiler.disable
def _qwen38_h20w_commit(
    *,
    request_id: int,
    layer_name: str,
    snapshots: dict[str, torch.Tensor | None],
) -> None:
    field_order = (
        "entry_hidden_states",
        "entry_topk_weights",
        "entry_topk_ids",
        "entry_a1q_scale",
        "entry_expert_psum",
        "aligned_sorted_ids",
        "aligned_expert_ids",
        "aligned_num_tokens_padded",
        "w13_input",
        "w13_input_scale",
        "w13_output",
        "w2_input",
        "w2_input_scale",
        "w2_output",
        "final_output",
    )

    def compare(a: torch.Tensor | None, b: torch.Tensor | None) -> dict:
        if a is None or b is None:
            return {
                "equal": a is None and b is None,
                "shape_match": a is None and b is None,
            }
        if tuple(a.shape) != tuple(b.shape):
            return {
                "equal": False,
                "shape_match": False,
                "request0_shape": list(a.shape),
                "request1_shape": list(b.shape),
            }
        return {
            "equal": bool(torch.equal(a, b)),
            "shape_match": True,
            "shape": list(a.shape),
            "dtype": str(a.dtype),
        }

    for previous_id in sorted(_QWEN38_H20W_PENDING):
        previous = _QWEN38_H20W_PENDING[previous_id]
        fields = {
            name: compare(previous.get(name), snapshots.get(name))
            for name in field_order
        }
        first_mismatch = next(
            (name for name in field_order if not fields[name]["equal"]),
            None,
        )
        record = {
            "schema": 1,
            "phase": "humming-indexed-repeat",
            "layer_name": layer_name,
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
                    "entry_a1q_scale",
                    "entry_expert_psum",
                )
            ),
            "alignment_equal": all(
                fields[name]["equal"]
                for name in (
                    "aligned_sorted_ids",
                    "aligned_expert_ids",
                    "aligned_num_tokens_padded",
                )
            ),
            "w13_input_equal": all(
                fields[name]["equal"]
                for name in ("w13_input", "w13_input_scale")
            ),
            "w13_output_equal": fields["w13_output"]["equal"],
            "w2_input_equal": all(
                fields[name]["equal"]
                for name in ("w2_input", "w2_input_scale")
            ),
            "w2_output_equal": fields["w2_output"]["equal"],
            "final_output_equal": fields["final_output"]["equal"],
        }
        print(
            "QWEN38_H20W_EXPERT " + json.dumps(record, sort_keys=True),
            flush=True,
        )

    _QWEN38_H20W_PENDING[request_id] = snapshots
    while len(_QWEN38_H20W_PENDING) > 16:
        oldest = min(_QWEN38_H20W_PENDING)
        del _QWEN38_H20W_PENDING[oldest]
'''

text = replace_once(
    text,
    logger_anchor,
    helper,
    "logger anchor",
)

entry_old = '''        hidden_states = hidden_states.view(-1, hidden_states.size(-1))
        buffers = self.prepare_buffers(
'''
entry_new = '''        h20w_request_id = _qwen38_h20w_request_id(self)
        if h20w_request_id >= 0:
            h20w_entry_hidden_states = _qwen38_h20w_clone(hidden_states)
            h20w_entry_topk_weights = _qwen38_h20w_clone(topk_weights)
            h20w_entry_topk_ids = _qwen38_h20w_clone(topk_ids)
            h20w_entry_a1q_scale = _qwen38_h20w_clone(a1q_scale)
            h20w_entry_expert_psum = _qwen38_h20w_clone(
                None
                if expert_tokens_meta is None
                else expert_tokens_meta.psum_recv_per_rank
            )

        hidden_states = hidden_states.view(-1, hidden_states.size(-1))
        buffers = self.prepare_buffers(
'''
text = replace_once(text, entry_old, entry_new, "HummingIndexedExperts entry")

kwargs_old = '''        moe_kwargs1, moe_kwargs2 = self.prepare_humming_moe_kwargs(
            topk_ids=topk_ids,
            expert_map=expert_map,
            expert_tokens_meta=expert_tokens_meta,
        )

        inputs, input_scale = self.quantize_input(
'''
kwargs_new = '''        moe_kwargs1, moe_kwargs2 = self.prepare_humming_moe_kwargs(
            topk_ids=topk_ids,
            expert_map=expert_map,
            expert_tokens_meta=expert_tokens_meta,
        )
        if h20w_request_id >= 0:
            h20w_aligned_sorted_ids = _qwen38_h20w_clone(
                moe_kwargs1.get("sorted_ids")
            )
            h20w_aligned_expert_ids = _qwen38_h20w_clone(
                moe_kwargs1.get("expert_ids")
            )
            h20w_aligned_num_tokens_padded = _qwen38_h20w_clone(
                moe_kwargs1.get("num_tokens_padded")
            )

        inputs, input_scale = self.quantize_input(
'''
text = replace_once(text, kwargs_old, kwargs_new, "indexed alignment boundary")

quant13_old = '''        inputs, input_scale = self.quantize_input(
            "w13",
            inputs=hidden_states,
            input_scale=a1q_scale,
            quanted_input=buffers.get("quanted_gate_up_input", None),
        )

        self.humming_forward(
'''
quant13_new = '''        inputs, input_scale = self.quantize_input(
            "w13",
            inputs=hidden_states,
            input_scale=a1q_scale,
            quanted_input=buffers.get("quanted_gate_up_input", None),
        )
        if h20w_request_id >= 0:
            h20w_w13_input = _qwen38_h20w_clone(inputs)
            h20w_w13_input_scale = _qwen38_h20w_clone(input_scale)

        self.humming_forward(
'''
text = replace_once(text, quant13_old, quant13_new, "w13 quant boundary")

w13_old = '''        self.humming_forward(
            "w13",
            inputs=inputs,
            weight=w1,
            input_scale=input_scale,
            outputs=buffers["gate_up_output"],
            **moe_kwargs1,
        )

        # psum[-1:] is the DeepEP valid *token* count as a zero-cost int32 view.
'''
w13_new = '''        self.humming_forward(
            "w13",
            inputs=inputs,
            weight=w1,
            input_scale=input_scale,
            outputs=buffers["gate_up_output"],
            **moe_kwargs1,
        )
        if h20w_request_id >= 0:
            h20w_w13_output = _qwen38_h20w_clone(buffers["gate_up_output"])

        # psum[-1:] is the DeepEP valid *token* count as a zero-cost int32 view.
'''
text = replace_once(text, w13_old, w13_new, "w13 output boundary")

w2_forward_old = '''        self.humming_forward(
            "w2",
            inputs=inputs,
            weight=w2,
            input_scale=input_scale,
            outputs=buffers["down_output"].view(-1, hidden_states.size(-1)),
            **moe_kwargs2,
        )

        # expert_map masks any non-local id; num_valid_tokens bounds the
'''
w2_forward_new = '''        if h20w_request_id >= 0:
            h20w_w2_input = _qwen38_h20w_clone(inputs)
            h20w_w2_input_scale = _qwen38_h20w_clone(input_scale)

        self.humming_forward(
            "w2",
            inputs=inputs,
            weight=w2,
            input_scale=input_scale,
            outputs=buffers["down_output"].view(-1, hidden_states.size(-1)),
            **moe_kwargs2,
        )
        if h20w_request_id >= 0:
            h20w_w2_output = _qwen38_h20w_clone(buffers["down_output"])

        # expert_map masks any non-local id; num_valid_tokens bounds the
'''
text = replace_once(text, w2_forward_old, w2_forward_new, "w2 boundaries")

reduce_old = '''        moe_fused_mul_sum(
            inputs=buffers["down_output"].view(*topk_ids.shape, -1),
            topk_weights=topk_weights,
            topk_ids=topk_ids,
            expert_map=expert_map,
            outputs=output,
            num_valid_tokens=valid_tokens,
        )


class HummingGroupedExperts'''
reduce_new = '''        moe_fused_mul_sum(
            inputs=buffers["down_output"].view(*topk_ids.shape, -1),
            topk_weights=topk_weights,
            topk_ids=topk_ids,
            expert_map=expert_map,
            outputs=output,
            num_valid_tokens=valid_tokens,
        )
        if h20w_request_id >= 0:
            h20w_final_output = _qwen38_h20w_clone(output)
            _qwen38_h20w_commit(
                request_id=h20w_request_id,
                layer_name=str(getattr(self, "_qwen38_h20_layer_name", "")),
                snapshots={
                    "entry_hidden_states": h20w_entry_hidden_states,
                    "entry_topk_weights": h20w_entry_topk_weights,
                    "entry_topk_ids": h20w_entry_topk_ids,
                    "entry_a1q_scale": h20w_entry_a1q_scale,
                    "entry_expert_psum": h20w_entry_expert_psum,
                    "aligned_sorted_ids": h20w_aligned_sorted_ids,
                    "aligned_expert_ids": h20w_aligned_expert_ids,
                    "aligned_num_tokens_padded": h20w_aligned_num_tokens_padded,
                    "w13_input": h20w_w13_input,
                    "w13_input_scale": h20w_w13_input_scale,
                    "w13_output": h20w_w13_output,
                    "w2_input": h20w_w2_input,
                    "w2_input_scale": h20w_w2_input_scale,
                    "w2_output": h20w_w2_output,
                    "final_output": h20w_final_output,
                },
            )


class HummingGroupedExperts'''
text = replace_once(text, reduce_old, reduce_new, "indexed reduce boundary")

path.write_text(text, encoding="utf-8")
print("installed H20-W Humming indexed-expert boundary capture")
