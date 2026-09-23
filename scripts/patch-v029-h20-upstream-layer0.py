#!/usr/bin/env python3
"""Install H20 sparse-layer Qwen4Exp boundary diagnostics."""

from __future__ import annotations

import sys
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit(
        "usage: patch-v029-h20-upstream-layer0.py <vllm/models/qwen4_exp/nvidia/model.py>"
    )

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

import_anchor = "import torch\nfrom torch import nn\n"
import_repl = """import hashlib
import json
import os

import torch
from torch import nn
"""
if text.count(import_anchor) != 1:
    raise SystemExit("expected torch import block exactly once")
text = text.replace(import_anchor, import_repl, 1)

helper_anchor = "from .hyperconnection import GatedResidual, HyperConnectionConfig\n"
helper = r'''from .hyperconnection import GatedResidual, HyperConnectionConfig

_QWEN38_H20U_TRIGGER = os.getenv(
    "QWEN38_H20U_TRIGGER", "/tmp/qwen38_h20u_layer0.enable"
)
_QWEN38_H20U_REQUEST_FILE = os.getenv(
    "QWEN38_H20U_REQUEST_FILE", "/tmp/qwen38_h20u_request_id"
)
_QWEN38_H20U_STAGE_NAMES = {
    0: "entry_hidden",
    1: "attn_block_input",
    2: "attn_out",
    3: "mlp_block_input",
    4: "mlp_out",
}
_QWEN38_H20U_LAYERS = (0, 1, 3, 7, 15, 31, 47)
_QWEN38_H20U_LAST_LAYER = _QWEN38_H20U_LAYERS[-1]
_QWEN38_H20U_PENDING: dict[tuple[int, int], dict[str, torch.Tensor]] = {}


def _qwen38_h20u_bytes(tensor: torch.Tensor) -> bytes:
    return tensor.detach().contiguous().view(torch.uint8).cpu().numpy().tobytes()


def _qwen38_h20u_fingerprint(tensor: torch.Tensor) -> dict:
    t = tensor.detach()
    numel = int(t.numel())
    nbytes = int(numel * t.element_size())
    result = {
        "shape": list(t.shape),
        "dtype": str(t.dtype),
        "stride": list(t.stride()),
        "contiguous": bool(t.is_contiguous()),
        "numel": numel,
        "nbytes": nbytes,
        "device": str(t.device),
    }
    if nbytes <= 1048576:
        result["hash_scope"] = "full"
        result["sha256"] = hashlib.sha256(_qwen38_h20u_bytes(t)).hexdigest()
        return result
    if not t.is_contiguous():
        result["hash_scope"] = "metadata-only-noncontiguous"
        result["sha256"] = None
        return result
    flat = t.view(-1)
    k = min(1024, numel)
    starts = sorted({0, max(0, numel // 2 - k // 2), max(0, numel - k)})
    payload = b"".join(
        _qwen38_h20u_bytes(flat.narrow(0, start, min(k, numel - start)))
        for start in starts
    )
    result["hash_scope"] = {
        "kind": "head-middle-tail-elements",
        "elements_per_window": k,
        "starts": starts,
    }
    result["sha256"] = hashlib.sha256(payload).hexdigest()
    return result


def _qwen38_h20u_emit_if_complete() -> None:
    required = set(_QWEN38_H20U_STAGE_NAMES.values())
    keys = [
        (layer_idx, request_id)
        for layer_idx in _QWEN38_H20U_LAYERS
        for request_id in (0, 1)
    ]
    if any(key not in _QWEN38_H20U_PENDING for key in keys):
        return
    if any(set(_QWEN38_H20U_PENDING[key]) != required for key in keys):
        return
    for layer_idx in _QWEN38_H20U_LAYERS:
        for request_id in (0, 1):
            key = (layer_idx, request_id)
            record = {
                "schema": 4,
                "phase": "sparse-layer-upstream",
                "layer_idx": layer_idx,
                "request_id": request_id,
                "tensors": {
                    name: _qwen38_h20u_fingerprint(
                        _QWEN38_H20U_PENDING[key][name]
                    )
                    for name in _QWEN38_H20U_STAGE_NAMES.values()
                },
            }
            print(
                "QWEN38_H20U_LAYER0 " + json.dumps(record, sort_keys=True),
                flush=True,
            )
    _QWEN38_H20U_PENDING.clear()


# Qwen4ExpModel is captured with torch.compile(fullgraph=True). A normal Python
# helper (including @torch.compiler.disable) is therefore illegal inside its
# forward graph. Keep the graph boundary opaque with a mutable custom op. The
# implementation does not alter tensor values; mutability is declared
# conservatively so compiler DCE cannot remove this diagnostic side-effect op.
@torch.library.custom_op(
    "qwen38_h20u::capture",
    mutates_args={"tensor"},
)
def _qwen38_h20u_capture(
    tensor: torch.Tensor,
    stage: int,
    layer_idx: int,
) -> None:
    if layer_idx not in _QWEN38_H20U_LAYERS or not os.path.exists(_QWEN38_H20U_TRIGGER):
        return
    stage_name = _QWEN38_H20U_STAGE_NAMES.get(stage)
    if stage_name is None:
        return
    try:
        with open(_QWEN38_H20U_REQUEST_FILE, encoding="utf-8") as handle:
            request_id = int(handle.read().strip())
    except (OSError, ValueError):
        return
    if request_id not in (0, 1):
        return
    key = (layer_idx, request_id)
    _QWEN38_H20U_PENDING.setdefault(key, {})[stage_name] = tensor.detach().clone()
    # Avoid perturbing intermediate layers with CPU synchronization. Keep all
    # sparse-layer snapshots on GPU and fingerprint only after request 1 has
    # reached the final selected layer.
    if (
        request_id == 1
        and layer_idx == _QWEN38_H20U_LAST_LAYER
        and stage == 4
    ):
        _qwen38_h20u_emit_if_complete()
'''
if text.count(helper_anchor) != 1:
    raise SystemExit("expected hyperconnection import anchor exactly once")
text = text.replace(helper_anchor, helper, 1)

class_start = text.index("class Qwen4ExpDecoderLayer(nn.Module):")
next_class = text.find("\nclass ", class_start + 1)
if next_class < 0:
    next_class = len(text)
prefix = text[:class_start]
body = text[class_start:next_class]
suffix = text[next_class:]

start_anchor = """        attn_hc = self.attn_hyper_connection
        if self.ple is not None:
"""
start_repl = """        if self.layer_idx in _QWEN38_H20U_LAYERS:
            _qwen38_h20u_capture(hidden_states, 0, self.layer_idx)

        attn_hc = self.attn_hyper_connection
        if self.ple is not None:
"""
if body.count(start_anchor) != 1:
    raise SystemExit("expected layer forward start anchor exactly once")
body = body.replace(start_anchor, start_repl, 1)

attn_anchor = """        if self.layer_type == "linear_attention":
            attn_out = self.linear_attn(hidden_states=block_input)
"""
attn_repl = """        if self.layer_idx in _QWEN38_H20U_LAYERS:
            _qwen38_h20u_capture(block_input, 1, self.layer_idx)

        if self.layer_type == "linear_attention":
            attn_out = self.linear_attn(hidden_states=block_input)
"""
if body.count(attn_anchor) != 1:
    raise SystemExit("expected attention anchor exactly once")
body = body.replace(attn_anchor, attn_repl, 1)

mlp_anchor = """        mlp_hc = self.mlp_hyper_connection
        hidden_states, block_input, injection = mlp_hc.combine_and_mix(
            hidden_states, attn_out, injection
        )
        mlp_out = self.mlp(block_input)
        return hidden_states, mlp_out, injection
"""
mlp_repl = """        if self.layer_idx in _QWEN38_H20U_LAYERS:
            _qwen38_h20u_capture(attn_out, 2, self.layer_idx)

        mlp_hc = self.mlp_hyper_connection
        hidden_states, block_input, injection = mlp_hc.combine_and_mix(
            hidden_states, attn_out, injection
        )
        if self.layer_idx in _QWEN38_H20U_LAYERS:
            _qwen38_h20u_capture(block_input, 3, self.layer_idx)
        mlp_out = self.mlp(block_input)
        if self.layer_idx in _QWEN38_H20U_LAYERS:
            _qwen38_h20u_capture(mlp_out, 4, self.layer_idx)
        return hidden_states, mlp_out, injection
"""
if body.count(mlp_anchor) != 1:
    raise SystemExit("expected MLP boundary anchor exactly once")
body = body.replace(mlp_anchor, mlp_repl, 1)

text = prefix + body + suffix
path.write_text(text, encoding="utf-8")
print("installed H20 sparse-layer Qwen4Exp upstream custom-op diagnostics")
