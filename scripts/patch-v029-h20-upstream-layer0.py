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
    5: "prev_block_output",
    6: "prev_injection",
    7: "pre_attn_hc_hidden",
    8: "post_attn_hc_hidden",
    9: "attn_injection",
    10: "mlp_hc_hidden",
    11: "mlp_injection",
    12: "post_mlp_hc_hidden",
    13: "post_mlp_hc_injection",
}
_QWEN38_H20U_BASE_STAGE_NAMES = (
    "entry_hidden",
    "attn_block_input",
    "attn_out",
    "mlp_block_input",
    "mlp_out",
)
_QWEN38_H20U_LAYER15_EXTRA_STAGE_NAMES = (
    "prev_block_output",
    "prev_injection",
    "pre_attn_hc_hidden",
    "post_attn_hc_hidden",
    "attn_injection",
)
_QWEN38_H20U_LAYER14_EXTRA_STAGE_NAMES = (
    "prev_block_output",
    "prev_injection",
    "pre_attn_hc_hidden",
    "post_attn_hc_hidden",
    "attn_injection",
    "post_mlp_hc_hidden",
    "post_mlp_hc_injection",
)
_QWEN38_H20U_CAPTURE_LAYER14 = os.environ.get(
    "QWEN38_H20U_CAPTURE_LAYER14", "1"
) == "1"
_QWEN38_H20U_LAYER14_GROUP = os.environ.get(
    "QWEN38_H20U_LAYER14_GROUP", "all"
).strip().lower()
if _QWEN38_H20U_LAYER14_GROUP not in {
    "none", "entry", "attention", "mlp", "mlp_hc", "mlp_block", "all"
}:
    raise ValueError(
        "QWEN38_H20U_LAYER14_GROUP must be none, entry, attention, mlp, "
        "mlp_hc, mlp_block, or all"
    )
if not _QWEN38_H20U_CAPTURE_LAYER14:
    _QWEN38_H20U_LAYER14_GROUP = "none"
_QWEN38_H20U_LAYER14_GROUPS = (
    {"entry", "attention", "mlp_hc", "mlp_block"}
    if _QWEN38_H20U_LAYER14_GROUP == "all"
    else ({_QWEN38_H20U_LAYER14_GROUP} - {"none"})
)
_QWEN38_H20U_LAYER14_ENTRY = "entry" in _QWEN38_H20U_LAYER14_GROUPS
_QWEN38_H20U_LAYER14_ATTENTION = "attention" in _QWEN38_H20U_LAYER14_GROUPS
_QWEN38_H20U_LAYER14_MLP_HC = bool(
    {"mlp", "mlp_hc"} & _QWEN38_H20U_LAYER14_GROUPS
)
_QWEN38_H20U_LAYER14_MLP_BLOCK = bool(
    {"mlp", "mlp_block"} & _QWEN38_H20U_LAYER14_GROUPS
)
_QWEN38_H20U_LAYER14_MLP = (
    _QWEN38_H20U_LAYER14_MLP_HC or _QWEN38_H20U_LAYER14_MLP_BLOCK
)
_QWEN38_H20U_LAYERS = (
    (0, 1, 3, 7, 14, 15, 31, 47)
    if _QWEN38_H20U_LAYER14_GROUPS
    else (0, 1, 3, 7, 15, 31, 47)
)
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


def _qwen38_h20u_required_names(layer_idx: int) -> tuple[str, ...]:
    if layer_idx == 15:
        return (
            _QWEN38_H20U_BASE_STAGE_NAMES
            + _QWEN38_H20U_LAYER15_EXTRA_STAGE_NAMES
        )
    if layer_idx == 14:
        names = []
        if "entry" in _QWEN38_H20U_LAYER14_GROUPS:
            names.extend(("entry_hidden", "prev_block_output", "prev_injection"))
        if "attention" in _QWEN38_H20U_LAYER14_GROUPS:
            names.extend((
                "pre_attn_hc_hidden",
                "post_attn_hc_hidden",
                "attn_injection",
                "attn_block_input",
                "attn_out",
            ))
        if _QWEN38_H20U_LAYER14_MLP_HC:
            names.extend((
                "post_mlp_hc_hidden",
                "post_mlp_hc_injection",
            ))
        if _QWEN38_H20U_LAYER14_MLP_BLOCK:
            names.extend((
                "mlp_block_input",
                "mlp_out",
            ))
        return tuple(names)
    return _QWEN38_H20U_BASE_STAGE_NAMES


def _qwen38_h20u_emit_if_complete() -> None:
    keys = [
        (layer_idx, request_id)
        for layer_idx in _QWEN38_H20U_LAYERS
        for request_id in (0, 1)
    ]
    if any(key not in _QWEN38_H20U_PENDING for key in keys):
        return
    for layer_idx in _QWEN38_H20U_LAYERS:
        names = _qwen38_h20u_required_names(layer_idx)
        for request_id in (0, 1):
            key = (layer_idx, request_id)
            captured = _QWEN38_H20U_PENDING[key]
            present_names = tuple(name for name in names if name in captured)
            record = {
                "schema": 6,
                "phase": "sparse-layer-upstream",
                "layer_idx": layer_idx,
                "request_id": request_id,
                "tensors": {
                    name: _qwen38_h20u_fingerprint(
                        captured[name]
                    )
                    for name in present_names
                },
                "missing_tensors": [name for name in names if name not in captured],
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
start_repl = """        if self.layer_idx in _QWEN38_H20U_LAYERS and (
            self.layer_idx != 14 or _QWEN38_H20U_LAYER14_ENTRY
        ):
            _qwen38_h20u_capture(hidden_states, 0, self.layer_idx)
        if self.layer_idx == 15 or (
            self.layer_idx == 14 and _QWEN38_H20U_LAYER14_ENTRY
        ):
            if prev_block_output is not None:
                _qwen38_h20u_capture(prev_block_output, 5, self.layer_idx)
            if prev_injection is not None:
                _qwen38_h20u_capture(prev_injection, 6, self.layer_idx)

        attn_hc = self.attn_hyper_connection
        if self.ple is not None:
"""
if body.count(start_anchor) != 1:
    raise SystemExit("expected layer forward start anchor exactly once")
body = body.replace(start_anchor, start_repl, 1)

pending_anchor = """        # Fuse a pending combine with this HC module's mix when possible.
        if prev_block_output is not None and prev_injection is not None:
            hidden_states, block_input, injection = attn_hc.combine_and_mix(
                hidden_states, prev_block_output, prev_injection
            )
        else:
            hidden_states, block_input, injection = attn_hc.mix(hidden_states)

"""
pending_repl = """        # Fuse a pending combine with this HC module's mix when possible.
        if self.layer_idx == 15 or (
            self.layer_idx == 14 and _QWEN38_H20U_LAYER14_ATTENTION
        ):
            _qwen38_h20u_capture(hidden_states, 7, self.layer_idx)

        if prev_block_output is not None and prev_injection is not None:
            hidden_states, block_input, injection = attn_hc.combine_and_mix(
                hidden_states, prev_block_output, prev_injection
            )
        else:
            hidden_states, block_input, injection = attn_hc.mix(hidden_states)

        if self.layer_idx == 15 or (
            self.layer_idx == 14 and _QWEN38_H20U_LAYER14_ATTENTION
        ):
            _qwen38_h20u_capture(hidden_states, 8, self.layer_idx)
            if injection is not None:
                _qwen38_h20u_capture(injection, 9, self.layer_idx)

"""
if body.count(pending_anchor) != 1:
    raise SystemExit("expected pending HC anchor exactly once")
body = body.replace(pending_anchor, pending_repl, 1)

attn_anchor = """        if self.layer_type == "linear_attention":
            attn_out = self.linear_attn(hidden_states=block_input)
"""
attn_repl = """        if self.layer_idx in _QWEN38_H20U_LAYERS and (
            self.layer_idx != 14 or _QWEN38_H20U_LAYER14_ATTENTION
        ):
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
mlp_repl = """        if self.layer_idx in _QWEN38_H20U_LAYERS and (
            self.layer_idx != 14 or _QWEN38_H20U_LAYER14_ATTENTION
        ):
            _qwen38_h20u_capture(attn_out, 2, self.layer_idx)

        mlp_hc = self.mlp_hyper_connection
        hidden_states, block_input, injection = mlp_hc.combine_and_mix(
            hidden_states, attn_out, injection
        )
        if self.layer_idx == 14 and _QWEN38_H20U_LAYER14_MLP_HC:
            _qwen38_h20u_capture(hidden_states, 12, self.layer_idx)
            if injection is not None:
                _qwen38_h20u_capture(injection, 13, self.layer_idx)
        if self.layer_idx in _QWEN38_H20U_LAYERS and (
            self.layer_idx != 14 or _QWEN38_H20U_LAYER14_MLP_BLOCK
        ):
            _qwen38_h20u_capture(block_input, 3, self.layer_idx)
        mlp_out = self.mlp(block_input)
        if self.layer_idx in _QWEN38_H20U_LAYERS and (
            self.layer_idx != 14 or _QWEN38_H20U_LAYER14_MLP
        ):
            _qwen38_h20u_capture(mlp_out, 4, self.layer_idx)
        return hidden_states, mlp_out, injection
"""
if body.count(mlp_anchor) != 1:
    raise SystemExit("expected MLP boundary anchor exactly once")
body = body.replace(mlp_anchor, mlp_repl, 1)

text = prefix + body + suffix
path.write_text(text, encoding="utf-8")
print("installed H20 v19 sparse-layer + layer-14 producer diagnostics")
