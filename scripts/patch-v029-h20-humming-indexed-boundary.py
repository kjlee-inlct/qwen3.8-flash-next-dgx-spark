#!/usr/bin/env python3
"""Historical H20-W wrong-backend probe; retained for v26 reproducibility only."""

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
try:
    _QWEN38_H20W_TARGET_LAYER_IDX = int(
        _QWEN38_H20W_TARGET_LAYER.split(".layers.", 1)[1].split(".", 1)[0]
    )
except (IndexError, ValueError):
    _QWEN38_H20W_TARGET_LAYER_IDX = -1

_QWEN38_H20W_PENDING: dict[int, dict[str, torch.Tensor | None]] = {}
_QWEN38_H20W_STAGE_NAMES = {
    0: "entry_hidden_states",
    1: "entry_topk_weights",
    2: "entry_topk_ids",
    3: "entry_a1q_scale",
    4: "entry_expert_psum",
    5: "aligned_sorted_ids",
    6: "aligned_expert_ids",
    7: "aligned_num_tokens_padded",
    8: "w13_input",
    9: "w13_input_scale",
    10: "w13_output",
    11: "w2_input",
    12: "w2_input_scale",
    13: "w2_output",
    14: "final_output",
}


def _qwen38_h20w_commit(
    *,
    request_id: int,
    layer_name: str,
    snapshots: dict[str, torch.Tensor | None],
) -> None:
    field_order = tuple(
        _QWEN38_H20W_STAGE_NAMES[index]
        for index in sorted(_QWEN38_H20W_STAGE_NAMES)
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
            "schema": 2,
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


@torch.library.custom_op(
    "qwen38_h20w::capture",
    mutates_args={"tensor"},
)
def _qwen38_h20w_capture(
    tensor: torch.Tensor,
    stage: int,
    layer_idx: int,
) -> None:
    if layer_idx != _QWEN38_H20W_TARGET_LAYER_IDX:
        return
    if not os.path.exists(_QWEN38_H20W_TRIGGER):
        return
    stage_name = _QWEN38_H20W_STAGE_NAMES.get(stage)
    if stage_name is None:
        return
    try:
        with open(_QWEN38_H20W_REQUEST_FILE, encoding="utf-8") as handle:
            request_id = int(handle.read().strip())
    except (OSError, ValueError):
        return

    snapshots = _QWEN38_H20W_PENDING.setdefault(request_id, {})
    snapshots[stage_name] = tensor.detach().clone()
    if stage == 14:
        _qwen38_h20w_commit(
            request_id=request_id,
            layer_name=_QWEN38_H20W_TARGET_LAYER,
            snapshots=snapshots,
        )
'''

text = replace_once(
    text,
    logger_anchor,
    helper,
    "logger anchor",
)

class_start = text.index("class HummingIndexedExperts")
class_end = text.index("\n\nclass HummingGroupedExperts", class_start)
prefix = text[:class_start]
indexed_body = text[class_start:class_end]
suffix = text[class_end:]

entry_old = '''        hidden_states = hidden_states.view(-1, hidden_states.size(-1))
        buffers = self.prepare_buffers(
'''
entry_new = '''        h20w_layer_idx = int(getattr(self, "_qwen38_h20_layer_idx", -1))
        _qwen38_h20w_capture(hidden_states, 0, h20w_layer_idx)
        _qwen38_h20w_capture(topk_weights, 1, h20w_layer_idx)
        _qwen38_h20w_capture(topk_ids, 2, h20w_layer_idx)
        if a1q_scale is not None:
            _qwen38_h20w_capture(a1q_scale, 3, h20w_layer_idx)
        if (
            expert_tokens_meta is not None
            and expert_tokens_meta.psum_recv_per_rank is not None
        ):
            _qwen38_h20w_capture(
                expert_tokens_meta.psum_recv_per_rank, 4, h20w_layer_idx
            )

        hidden_states = hidden_states.view(-1, hidden_states.size(-1))
        buffers = self.prepare_buffers(
'''
indexed_body = replace_once(indexed_body, entry_old, entry_new, "HummingIndexedExperts entry")

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
        _qwen38_h20w_capture(
            moe_kwargs1["sorted_ids"], 5, h20w_layer_idx
        )
        _qwen38_h20w_capture(
            moe_kwargs1["expert_ids"], 6, h20w_layer_idx
        )
        _qwen38_h20w_capture(
            moe_kwargs1["num_tokens_padded"], 7, h20w_layer_idx
        )

        inputs, input_scale = self.quantize_input(
'''
indexed_body = replace_once(indexed_body, kwargs_old, kwargs_new, "indexed alignment boundary")

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
        _qwen38_h20w_capture(inputs, 8, h20w_layer_idx)
        if input_scale is not None:
            _qwen38_h20w_capture(input_scale, 9, h20w_layer_idx)

        self.humming_forward(
'''
indexed_body = replace_once(indexed_body, quant13_old, quant13_new, "w13 quant boundary")

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
        _qwen38_h20w_capture(
            buffers["gate_up_output"], 10, h20w_layer_idx
        )

        # psum[-1:] is the DeepEP valid *token* count as a zero-cost int32 view.
'''
indexed_body = replace_once(indexed_body, w13_old, w13_new, "w13 output boundary")

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
w2_forward_new = '''        _qwen38_h20w_capture(inputs, 11, h20w_layer_idx)
        if input_scale is not None:
            _qwen38_h20w_capture(input_scale, 12, h20w_layer_idx)

        self.humming_forward(
            "w2",
            inputs=inputs,
            weight=w2,
            input_scale=input_scale,
            outputs=buffers["down_output"].view(-1, hidden_states.size(-1)),
            **moe_kwargs2,
        )
        _qwen38_h20w_capture(
            buffers["down_output"], 13, h20w_layer_idx
        )

        # expert_map masks any non-local id; num_valid_tokens bounds the
'''
indexed_body = replace_once(indexed_body, w2_forward_old, w2_forward_new, "w2 boundaries")

reduce_old = '''        moe_fused_mul_sum(
            inputs=buffers["down_output"].view(*topk_ids.shape, -1),
            topk_weights=topk_weights,
            topk_ids=topk_ids,
            expert_map=expert_map,
            outputs=output,
            num_valid_tokens=valid_tokens,
        )'''
reduce_new = '''        moe_fused_mul_sum(
            inputs=buffers["down_output"].view(*topk_ids.shape, -1),
            topk_weights=topk_weights,
            topk_ids=topk_ids,
            expert_map=expert_map,
            outputs=output,
            num_valid_tokens=valid_tokens,
        )
        _qwen38_h20w_capture(output, 14, h20w_layer_idx)'''
indexed_body = replace_once(indexed_body, reduce_old, reduce_new, "indexed reduce boundary")

text = prefix + indexed_body + suffix

path.write_text(text, encoding="utf-8")
print("installed H20-W Humming indexed-expert boundary capture")
