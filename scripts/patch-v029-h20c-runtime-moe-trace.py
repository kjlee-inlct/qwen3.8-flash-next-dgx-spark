#!/usr/bin/env python3
"""Install H20-C runtime MoE trace in FusedMoEModularMethod.apply()."""

from __future__ import annotations

import sys
from pathlib import Path

if len(sys.argv) != 3 or sys.argv[2] not in {"ct", "modelopt"}:
    raise SystemExit(
        "usage: patch-v029-h20c-runtime-moe-trace.py <fused_moe_modular_method.py> <ct|modelopt>"
    )

path = Path(sys.argv[1])
source = sys.argv[2]
text = path.read_text(encoding="utf-8")

old_import = "from typing import TYPE_CHECKING\n\nimport torch\n"
new_import = """from typing import TYPE_CHECKING

import hashlib
import json
import os

import torch
"""
if text.count(old_import) != 1:
    raise SystemExit("expected fused_moe_modular_method import block exactly once")
text = text.replace(old_import, new_import, 1)

logger_anchor = "logger = init_logger(__name__)\n"
helper = rf'''logger = init_logger(__name__)

_QWEN38_H20C_SOURCE = "{source}"
_QWEN38_H20C_TRACE_FILE = os.getenv(
    "QWEN38_H20C_TRACE_FILE", "/tmp/qwen38_h20c_trace.enable"
)
_QWEN38_H20C_REQUEST_FILE = os.getenv(
    "QWEN38_H20C_REQUEST_FILE", "/tmp/qwen38_h20c_request_id"
)
_QWEN38_H20C_MAX_CALLS = int(os.getenv("QWEN38_H20C_MAX_CALLS", "32"))
_QWEN38_H20C_FULL_HASH_MAX_BYTES = int(
    os.getenv("QWEN38_H20C_FULL_HASH_MAX_BYTES", "1048576")
)
_QWEN38_H20C_SAMPLE_ELEMS = int(
    os.getenv("QWEN38_H20C_SAMPLE_ELEMS", "1024")
)
_QWEN38_H20C_CALL = 0


def _qwen38_h20c_bytes(tensor: torch.Tensor) -> bytes:
    return (
        tensor.detach().contiguous().view(torch.uint8).cpu().numpy().tobytes()
    )


def _qwen38_h20c_fingerprint(tensor: torch.Tensor | None) -> dict | None:
    if tensor is None:
        return None
    t = tensor.detach()
    numel = int(t.numel())
    nbytes = int(numel * t.element_size())
    result = {{
        "shape": list(t.shape),
        "dtype": str(t.dtype),
        "stride": list(t.stride()),
        "contiguous": bool(t.is_contiguous()),
        "numel": numel,
        "nbytes": nbytes,
        "device": str(t.device),
    }}
    if nbytes <= _QWEN38_H20C_FULL_HASH_MAX_BYTES:
        payload = _qwen38_h20c_bytes(t)
        result["hash_scope"] = "full"
        result["sha256"] = hashlib.sha256(payload).hexdigest()
        return result
    if not t.is_contiguous():
        result["hash_scope"] = "metadata-only-noncontiguous"
        result["sha256"] = None
        return result

    flat = t.view(-1)
    k = min(_QWEN38_H20C_SAMPLE_ELEMS, numel)
    starts = sorted({{
        0,
        max(0, numel // 2 - k // 2),
        max(0, numel - k),
    }})
    payload = b"".join(
        _qwen38_h20c_bytes(flat.narrow(0, start, min(k, numel - start)))
        for start in starts
    )
    result["hash_scope"] = {{
        "kind": "head-middle-tail-elements",
        "elements_per_window": k,
        "starts": starts,
    }}
    result["sha256"] = hashlib.sha256(payload).hexdigest()
    return result


def _qwen38_h20c_request_id() -> int:
    try:
        return int(Path(_QWEN38_H20C_REQUEST_FILE).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return -1


def _qwen38_h20c_emit(
    *,
    phase: str,
    call_index: int,
    layer,
    tensors: dict[str, torch.Tensor | None],
) -> None:
    record = {{
        "schema": 1,
        "source": _QWEN38_H20C_SOURCE,
        "phase": phase,
        "call_index": call_index,
        "request_id": _qwen38_h20c_request_id(),
        "layer_name": str(getattr(layer, "layer_name", "")),
        "tensors": {{
            name: _qwen38_h20c_fingerprint(tensor)
            for name, tensor in tensors.items()
        }},
    }}
    print(
        "QWEN38_H20C_RUNTIME " + json.dumps(record, sort_keys=True),
        flush=True,
    )
'''
if text.count(logger_anchor) != 1:
    raise SystemExit("expected logger anchor exactly once")
text = text.replace(logger_anchor, helper, 1)

old_apply = '''    def apply(
        self,
        layer: "RoutedExperts",
        x: torch.Tensor,
        topk_weights: torch.Tensor,
        topk_ids: torch.Tensor,
        shared_experts: SharedExperts | None,
        shared_experts_input: torch.Tensor | None,
    ) -> torch.Tensor:
        assert self.moe_kernel is not None
        return self.moe_kernel.apply(
            hidden_states=x,
            w1=layer.w13_weight,
            w2=layer.w2_weight,
            topk_weights=topk_weights,
            topk_ids=topk_ids,
            activation=layer.activation,
            global_num_experts=layer.global_num_experts,
            apply_router_weight_on_input=layer.apply_router_weight_on_input,
            expert_map=layer.expert_map,
            shared_experts=shared_experts,
            shared_experts_input=shared_experts_input,
        )
'''
new_apply = '''    def apply(
        self,
        layer: "RoutedExperts",
        x: torch.Tensor,
        topk_weights: torch.Tensor,
        topk_ids: torch.Tensor,
        shared_experts: SharedExperts | None,
        shared_experts_input: torch.Tensor | None,
    ) -> torch.Tensor:
        assert self.moe_kernel is not None
        global _QWEN38_H20C_CALL
        h20c_enabled = (
            _QWEN38_H20C_CALL < _QWEN38_H20C_MAX_CALLS
            and os.path.exists(_QWEN38_H20C_TRACE_FILE)
        )
        h20c_call_index = _QWEN38_H20C_CALL
        if h20c_enabled:
            _QWEN38_H20C_CALL += 1
            _qwen38_h20c_emit(
                phase="pre",
                call_index=h20c_call_index,
                layer=layer,
                tensors={
                    "x": x,
                    "topk_weights": topk_weights,
                    "topk_ids": topk_ids,
                    "shared_experts_input": shared_experts_input,
                },
            )

        output = self.moe_kernel.apply(
            hidden_states=x,
            w1=layer.w13_weight,
            w2=layer.w2_weight,
            topk_weights=topk_weights,
            topk_ids=topk_ids,
            activation=layer.activation,
            global_num_experts=layer.global_num_experts,
            apply_router_weight_on_input=layer.apply_router_weight_on_input,
            expert_map=layer.expert_map,
            shared_experts=shared_experts,
            shared_experts_input=shared_experts_input,
        )
        if h20c_enabled:
            _qwen38_h20c_emit(
                phase="post",
                call_index=h20c_call_index,
                layer=layer,
                tensors={"output": output},
            )
        return output
'''
if text.count(old_apply) != 1:
    raise SystemExit("expected FusedMoEModularMethod.apply() exactly once")
text = text.replace(old_apply, new_apply, 1)

path.write_text(text, encoding="utf-8")
print(f"installed H20-C runtime MoE trace ({source})")
