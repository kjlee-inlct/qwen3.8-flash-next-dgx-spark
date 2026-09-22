#!/usr/bin/env python3
"""Install H20 upstream layer-0 Qwen4Exp boundary diagnostics."""

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
_QWEN38_H20U_PENDING: dict[int, dict[str, torch.Tensor | None]] = {}


@torch.compiler.disable
def _qwen38_h20u_request_id(layer_idx: int) -> int:
    if layer_idx != 0 or not os.path.exists(_QWEN38_H20U_TRIGGER):
        return -1
    try:
        with open(_QWEN38_H20U_REQUEST_FILE, encoding="utf-8") as handle:
            return int(handle.read().strip())
    except (OSError, ValueError):
        return -1


def _qwen38_h20u_bytes(tensor: torch.Tensor) -> bytes:
    return tensor.detach().contiguous().view(torch.uint8).cpu().numpy().tobytes()


def _qwen38_h20u_fingerprint(tensor: torch.Tensor | None) -> dict | None:
    if tensor is None:
        return None
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


@torch.compiler.disable
def _qwen38_h20u_store_and_maybe_emit(
    request_id: int,
    tensors: dict[str, torch.Tensor | None],
) -> None:
    _QWEN38_H20U_PENDING[request_id] = tensors
    # Emit only after both requests are captured. This ensures request 0 has
    # no CPU fingerprint/synchronization before request 1 reaches layer 0.
    if 0 not in _QWEN38_H20U_PENDING or 1 not in _QWEN38_H20U_PENDING:
        return
    for rid in (0, 1):
        record = {
            "schema": 1,
            "phase": "layer0-upstream",
            "request_id": rid,
            "tensors": {
                name: _qwen38_h20u_fingerprint(tensor)
                for name, tensor in _QWEN38_H20U_PENDING[rid].items()
            },
        }
        print(
            "QWEN38_H20U_LAYER0 " + json.dumps(record, sort_keys=True),
            flush=True,
        )
    _QWEN38_H20U_PENDING.clear()
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
start_repl = """        h20u_request_id = _qwen38_h20u_request_id(self.layer_idx)
        h20u_entry_hidden = (
            hidden_states.clone() if h20u_request_id >= 0 else None
        )

        attn_hc = self.attn_hyper_connection
        if self.ple is not None:
"""
if body.count(start_anchor) != 1:
    raise SystemExit("expected layer forward start anchor exactly once")
body = body.replace(start_anchor, start_repl, 1)

attn_anchor = """        if self.layer_type == "linear_attention":
            attn_out = self.linear_attn(hidden_states=block_input)
"""
attn_repl = """        h20u_attn_block_input = (
            block_input.clone() if h20u_request_id >= 0 else None
        )

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
mlp_repl = """        h20u_attn_out = attn_out.clone() if h20u_request_id >= 0 else None

        mlp_hc = self.mlp_hyper_connection
        hidden_states, block_input, injection = mlp_hc.combine_and_mix(
            hidden_states, attn_out, injection
        )
        h20u_mlp_block_input = (
            block_input.clone() if h20u_request_id >= 0 else None
        )
        mlp_out = self.mlp(block_input)
        if h20u_request_id >= 0:
            _qwen38_h20u_store_and_maybe_emit(
                h20u_request_id,
                {
                    "entry_hidden": h20u_entry_hidden,
                    "attn_block_input": h20u_attn_block_input,
                    "attn_out": h20u_attn_out,
                    "mlp_block_input": h20u_mlp_block_input,
                    "mlp_out": mlp_out.clone(),
                },
            )
        return hidden_states, mlp_out, injection
"""
if body.count(mlp_anchor) != 1:
    raise SystemExit("expected MLP boundary anchor exactly once")
body = body.replace(mlp_anchor, mlp_repl, 1)

text = prefix + body + suffix
path.write_text(text, encoding="utf-8")
print("installed H20 layer-0 Qwen4Exp upstream diagnostics")
