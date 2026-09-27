#!/usr/bin/env python3
"""Install opt-in H20 v25 modular MoE boundary capture."""

from __future__ import annotations

import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, description: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected {description} exactly once, found {count}")
    return text.replace(old, new, 1)


if len(sys.argv) != 2:
    raise SystemExit(
        "usage: patch-v029-h20-modular-boundary.py <fused_moe/modular_kernel.py>"
    )

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

text = replace_once(
    text,
    "from abc import ABC, abstractmethod\n",
    "import json\nimport os\n\nfrom abc import ABC, abstractmethod\n",
    "modular-kernel imports",
)

helper = r'''

_QWEN38_H20V_BOUNDARY_TRIGGER = os.getenv(
    "QWEN38_H20V_BOUNDARY_TRIGGER", "/tmp/qwen38_h20v_boundary.enable"
)
_QWEN38_H20V_BOUNDARY_REQUEST_FILE = os.getenv(
    "QWEN38_H20V_BOUNDARY_REQUEST_FILE", "/tmp/qwen38_h20v_boundary_request_id"
)
_QWEN38_H20V_BOUNDARY_TARGET_LAYER = os.getenv(
    "QWEN38_H20V_BOUNDARY_TARGET_LAYER",
    "language_model.model.layers.15.mlp.experts",
)
_QWEN38_H20V_BOUNDARY_PENDING: dict[int, dict[str, torch.Tensor | None]] = {}


@torch.compiler.disable
def _qwen38_h20v_boundary_request_id(kernel) -> int:
    if not os.path.exists(_QWEN38_H20V_BOUNDARY_TRIGGER):
        return -1
    if str(getattr(kernel, "_qwen38_h20_layer_name", "")) != (
        _QWEN38_H20V_BOUNDARY_TARGET_LAYER
    ):
        return -1
    try:
        with open(_QWEN38_H20V_BOUNDARY_REQUEST_FILE, encoding="utf-8") as handle:
            return int(handle.read().strip())
    except (OSError, ValueError):
        return -1


def _qwen38_h20v_boundary_clone(tensor: torch.Tensor | None):
    return None if tensor is None else tensor.detach().clone()


@torch.compiler.disable
def _qwen38_h20v_boundary_commit(
    *,
    request_id: int,
    layer_name: str,
    snapshots: dict[str, torch.Tensor | None],
) -> None:
    field_order = (
        "prepared_a1q",
        "prepared_a1q_scale",
        "prepared_topk_ids",
        "prepared_topk_weights",
        "fused_out",
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

    for previous_id in sorted(_QWEN38_H20V_BOUNDARY_PENDING):
        previous = _QWEN38_H20V_BOUNDARY_PENDING[previous_id]
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
            "phase": "modular-boundary-repeat",
            "layer_name": layer_name,
            "request0": previous_id,
            "request1": request_id,
            "fields": fields,
            "first_mismatch": first_mismatch,
            "prepared_equal": all(
                fields[name]["equal"]
                for name in (
                    "prepared_a1q",
                    "prepared_a1q_scale",
                    "prepared_topk_ids",
                    "prepared_topk_weights",
                )
            ),
            "fused_out_equal": fields["fused_out"]["equal"],
            "final_output_equal": fields["final_output"]["equal"],
        }
        print(
            "QWEN38_H20V_BOUNDARY " + json.dumps(record, sort_keys=True),
            flush=True,
        )

    _QWEN38_H20V_BOUNDARY_PENDING[request_id] = snapshots
    while len(_QWEN38_H20V_BOUNDARY_PENDING) > 8:
        oldest = min(_QWEN38_H20V_BOUNDARY_PENDING)
        del _QWEN38_H20V_BOUNDARY_PENDING[oldest]
'''

text = replace_once(
    text,
    "logger = init_logger(__name__)\n",
    "logger = init_logger(__name__)\n" + helper,
    "modular-kernel logger anchor",
)

prepare_old = '''        a1q, a1q_scale, expert_tokens_meta, topk_ids, topk_weights = self._prepare(
            hidden_states,
            topk_weights,
            topk_ids,
            global_num_experts,
            expert_map,
            apply_router_weight_on_input,
        )
'''
prepare_new = prepare_old + '''
        h20v_request_id = _qwen38_h20v_boundary_request_id(self)
        if h20v_request_id >= 0:
            h20v_prepared_a1q = _qwen38_h20v_boundary_clone(a1q)
            h20v_prepared_a1q_scale = _qwen38_h20v_boundary_clone(a1q_scale)
            h20v_prepared_topk_ids = _qwen38_h20v_boundary_clone(topk_ids)
            h20v_prepared_topk_weights = _qwen38_h20v_boundary_clone(topk_weights)
'''
text = replace_once(
    text,
    prepare_old,
    prepare_new,
    "modular-kernel prepare boundary",
)

fused_old = '''        fused_out = self._fused_experts(
            in_dtype=hidden_states.dtype,
            a1q=a1q,
            a1q_scale=a1q_scale,
            w1=w1,
            w2=w2,
            topk_weights=topk_weights,
            topk_ids=topk_ids,
            activation=activation,
            global_num_experts=global_num_experts,
            local_num_experts=local_num_experts,
            expert_map=expert_map,
            apply_router_weight_on_input=apply_router_weight_on_input,
            expert_tokens_meta=expert_tokens_meta,
            output_alias=output,
        )
'''
fused_new = fused_old + '''
        if h20v_request_id >= 0:
            h20v_fused_out = _qwen38_h20v_boundary_clone(fused_out)
'''
text = replace_once(
    text,
    fused_old,
    fused_new,
    "modular-kernel fused-experts boundary",
)

final_old = '''        return self._finalize(
            output,
            fused_out,
            hidden_states,
            topk_weights,
            topk_ids,
            apply_router_weight_on_input,
            shared_experts=shared_experts,
            shared_experts_input=shared_experts_input,
        )
'''
final_new = '''        final_output = self._finalize(
            output,
            fused_out,
            hidden_states,
            topk_weights,
            topk_ids,
            apply_router_weight_on_input,
            shared_experts=shared_experts,
            shared_experts_input=shared_experts_input,
        )
        if h20v_request_id >= 0:
            h20v_final_output = _qwen38_h20v_boundary_clone(final_output)
            _qwen38_h20v_boundary_commit(
                request_id=h20v_request_id,
                layer_name=str(getattr(self, "_qwen38_h20_layer_name", "")),
                snapshots={
                    "prepared_a1q": h20v_prepared_a1q,
                    "prepared_a1q_scale": h20v_prepared_a1q_scale,
                    "prepared_topk_ids": h20v_prepared_topk_ids,
                    "prepared_topk_weights": h20v_prepared_topk_weights,
                    "fused_out": h20v_fused_out,
                    "final_output": h20v_final_output,
                },
            )
        return final_output
'''
text = replace_once(
    text,
    final_old,
    final_new,
    "modular-kernel finalize boundary",
)

path.write_text(text, encoding="utf-8")
print("installed opt-in H20 v25 modular MoE boundary capture")
