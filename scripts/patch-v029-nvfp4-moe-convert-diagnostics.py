#!/usr/bin/env python3
"""H20: instrument NVFP4 MoE kernel-format conversion with bounded fingerprints.

Usage:
  patch-v029-nvfp4-moe-convert-diagnostics.py <python-file> ct
  patch-v029-nvfp4-moe-convert-diagnostics.py <python-file> modelopt

The diagnostic records the normalized tensors actually passed to
convert_to_nvfp4_moe_kernel_format() and the tensors returned by it. Large
contiguous tensors use a deterministic head/middle/tail sample hash; small
tensors use a full byte hash. Non-contiguous large tensors are metadata-only to
avoid accidental full-size copies during startup.
"""

from __future__ import annotations

import sys
from pathlib import Path

if len(sys.argv) != 3 or sys.argv[2] not in {"ct", "modelopt"}:
    raise SystemExit("usage: patch-v029-nvfp4-moe-convert-diagnostics.py <path> <ct|modelopt>")

path = Path(sys.argv[1])
mode = sys.argv[2]
text = path.read_text(encoding="utf-8")

imports_old = "import torch\n"
imports_new = """import hashlib
import json
import os

import torch
"""
if text.count(imports_old) != 1:
    raise SystemExit("expected single torch import")
text = text.replace(imports_old, imports_new, 1)

logger_anchor = "logger = init_logger(__name__)\n"
helper = r'''
logger = init_logger(__name__)

_QWEN38_H20_DIAG_CALL = 0
_QWEN38_H20_DIAG_MAX_CALLS = int(os.getenv("QWEN38_H20_DIAG_MAX_CALLS", "4"))
_QWEN38_H20_DIAG_FULL_HASH_MAX_BYTES = int(
    os.getenv("QWEN38_H20_DIAG_FULL_HASH_MAX_BYTES", "1048576")
)
_QWEN38_H20_DIAG_SAMPLE_ELEMS = int(
    os.getenv("QWEN38_H20_DIAG_SAMPLE_ELEMS", "1024")
)


def _qwen38_h20_bytes(tensor: torch.Tensor) -> bytes:
    # View as raw bytes before the host copy so CPU float8 support is irrelevant.
    cpu_bytes = tensor.detach().contiguous().view(torch.uint8).cpu()
    return cpu_bytes.numpy().tobytes()


def _qwen38_h20_fingerprint(tensor: torch.Tensor | None) -> dict | None:
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
        "storage_offset": int(t.storage_offset()),
    }
    if nbytes <= _QWEN38_H20_DIAG_FULL_HASH_MAX_BYTES:
        payload = _qwen38_h20_bytes(t)
        result["hash_scope"] = "full"
        result["sha256"] = hashlib.sha256(payload).hexdigest()
        return result
    if not t.is_contiguous():
        result["hash_scope"] = "metadata-only-noncontiguous"
        result["sha256"] = None
        return result

    flat = t.view(-1)
    k = min(_QWEN38_H20_DIAG_SAMPLE_ELEMS, numel)
    starts = sorted(
        {
            0,
            max(0, numel // 2 - k // 2),
            max(0, numel - k),
        }
    )
    pieces = [flat.narrow(0, start, min(k, numel - start)) for start in starts]
    # Hash raw windows independently of dtype arithmetic support (notably FP8).
    payload = b"".join(_qwen38_h20_bytes(piece) for piece in pieces)
    result["hash_scope"] = {
        "kind": "head-middle-tail-elements",
        "elements_per_window": k,
        "starts": starts,
    }
    result["sha256"] = hashlib.sha256(payload).hexdigest()
    return result


def _qwen38_h20_emit(
    *,
    source: str,
    phase: str,
    call_index: int,
    backend,
    use_a16: bool,
    layer,
    tensors: dict[str, torch.Tensor | None],
) -> None:
    if call_index >= _QWEN38_H20_DIAG_MAX_CALLS:
        return
    record = {
        "schema": 1,
        "source": source,
        "phase": phase,
        "call_index": call_index,
        "backend": str(backend),
        "use_a16": bool(use_a16),
        "num_experts": int(getattr(layer, "num_experts", -1)),
        "global_num_experts": int(getattr(layer, "global_num_experts", -1)),
        "tensors": {
            name: _qwen38_h20_fingerprint(tensor)
            for name, tensor in tensors.items()
        },
    }
    print(
        "QWEN38_H20_MOE_DIAG " + json.dumps(record, sort_keys=True),
        flush=True,
    )
'''
if text.count(logger_anchor) != 1:
    raise SystemExit("expected logger anchor exactly once")
text = text.replace(logger_anchor, helper, 1)

if mode == "ct":
    start = text.index("class CompressedTensorsW4A4Nvfp4MoEMethod")
    prefix, body = text[:start], text[start:]

    old = '''        # Shuffle weights into the NvFp4 kernel format.
        (
            w13,
            w13_scale,
            w13_scale_2,
            a13_scale,
            w2,
            w2_scale,
            w2_scale_2,
            a2_scale,
        ) = convert_to_nvfp4_moe_kernel_format(
            nvfp4_backend=self.nvfp4_backend,
            layer=layer,
            w13=layer.w13_weight,
            w13_scale=layer.w13_weight_scale,
            w13_scale_2=(1.0 / w13_weight_global_scale),
            a13_scale=(1.0 / layer.w13_input_global_scale),
            w2=layer.w2_weight,
            w2_scale=layer.w2_weight_scale,
            w2_scale_2=(1.0 / layer.w2_weight_global_scale),
            a2_scale=(1.0 / layer.w2_input_global_scale),
            is_act_and_mul=self.moe.is_act_and_mul,
            use_a16=self.use_a16,
        )
'''
    new = '''        # H20: fingerprint the normalized tensors actually passed to conversion.
        global _QWEN38_H20_DIAG_CALL
        h20_call_index = _QWEN38_H20_DIAG_CALL
        _QWEN38_H20_DIAG_CALL += 1
        h20_w13_scale_2 = 1.0 / w13_weight_global_scale
        h20_a13_scale = 1.0 / layer.w13_input_global_scale
        h20_w2_scale_2 = 1.0 / layer.w2_weight_global_scale
        h20_a2_scale = 1.0 / layer.w2_input_global_scale
        _qwen38_h20_emit(
            source="ct",
            phase="pre",
            call_index=h20_call_index,
            backend=self.nvfp4_backend,
            use_a16=self.use_a16,
            layer=layer,
            tensors={
                "w13": layer.w13_weight,
                "w13_scale": layer.w13_weight_scale,
                "w13_scale_2": h20_w13_scale_2,
                "a13_scale": h20_a13_scale,
                "w2": layer.w2_weight,
                "w2_scale": layer.w2_weight_scale,
                "w2_scale_2": h20_w2_scale_2,
                "a2_scale": h20_a2_scale,
            },
        )

        # Shuffle weights into the NvFp4 kernel format.
        (
            w13,
            w13_scale,
            w13_scale_2,
            a13_scale,
            w2,
            w2_scale,
            w2_scale_2,
            a2_scale,
        ) = convert_to_nvfp4_moe_kernel_format(
            nvfp4_backend=self.nvfp4_backend,
            layer=layer,
            w13=layer.w13_weight,
            w13_scale=layer.w13_weight_scale,
            w13_scale_2=h20_w13_scale_2,
            a13_scale=h20_a13_scale,
            w2=layer.w2_weight,
            w2_scale=layer.w2_weight_scale,
            w2_scale_2=h20_w2_scale_2,
            a2_scale=h20_a2_scale,
            is_act_and_mul=self.moe.is_act_and_mul,
            use_a16=self.use_a16,
        )
        _qwen38_h20_emit(
            source="ct",
            phase="post",
            call_index=h20_call_index,
            backend=self.nvfp4_backend,
            use_a16=self.use_a16,
            layer=layer,
            tensors={
                "w13": w13,
                "w13_scale": w13_scale,
                "w13_scale_2": w13_scale_2,
                "a13_scale": a13_scale,
                "w2": w2,
                "w2_scale": w2_scale,
                "w2_scale_2": w2_scale_2,
                "a2_scale": a2_scale,
            },
        )
'''
    if body.count(old) != 1:
        raise SystemExit("expected CT conversion block not found exactly once")
    text = prefix + body.replace(old, new, 1)

else:
    start = text.index("class ModelOptNvFp4FusedMoE")
    prefix, body = text[:start], text[start:]
    old = '''        (
            w13,
            w13_scale,
            w13_scale_2,
            a13_scale,
            w2,
            w2_scale,
            w2_scale_2,
            a2_scale,
        ) = convert_to_nvfp4_moe_kernel_format(
            nvfp4_backend=self.nvfp4_backend,
            layer=layer,
            w13=layer.w13_weight,
            w13_scale=layer.w13_weight_scale,
            w13_scale_2=w13_weight_scale_2,
            a13_scale=layer.w13_input_scale,
            w2=layer.w2_weight,
            w2_scale=layer.w2_weight_scale,
            w2_scale_2=layer.w2_weight_scale_2,
            a2_scale=layer.w2_input_scale,
            is_act_and_mul=self.moe.is_act_and_mul,
            use_a16=self.use_a16,
        )
'''
    new = '''        # H20: fingerprint the normalized tensors actually passed to conversion.
        global _QWEN38_H20_DIAG_CALL
        h20_call_index = _QWEN38_H20_DIAG_CALL
        _QWEN38_H20_DIAG_CALL += 1
        _qwen38_h20_emit(
            source="modelopt",
            phase="pre",
            call_index=h20_call_index,
            backend=self.nvfp4_backend,
            use_a16=self.use_a16,
            layer=layer,
            tensors={
                "w13": layer.w13_weight,
                "w13_scale": layer.w13_weight_scale,
                "w13_scale_2": w13_weight_scale_2,
                "a13_scale": layer.w13_input_scale,
                "w2": layer.w2_weight,
                "w2_scale": layer.w2_weight_scale,
                "w2_scale_2": layer.w2_weight_scale_2,
                "a2_scale": layer.w2_input_scale,
            },
        )

        (
            w13,
            w13_scale,
            w13_scale_2,
            a13_scale,
            w2,
            w2_scale,
            w2_scale_2,
            a2_scale,
        ) = convert_to_nvfp4_moe_kernel_format(
            nvfp4_backend=self.nvfp4_backend,
            layer=layer,
            w13=layer.w13_weight,
            w13_scale=layer.w13_weight_scale,
            w13_scale_2=w13_weight_scale_2,
            a13_scale=layer.w13_input_scale,
            w2=layer.w2_weight,
            w2_scale=layer.w2_weight_scale,
            w2_scale_2=layer.w2_weight_scale_2,
            a2_scale=layer.w2_input_scale,
            is_act_and_mul=self.moe.is_act_and_mul,
            use_a16=self.use_a16,
        )
        _qwen38_h20_emit(
            source="modelopt",
            phase="post",
            call_index=h20_call_index,
            backend=self.nvfp4_backend,
            use_a16=self.use_a16,
            layer=layer,
            tensors={
                "w13": w13,
                "w13_scale": w13_scale,
                "w13_scale_2": w13_scale_2,
                "a13_scale": a13_scale,
                "w2": w2,
                "w2_scale": w2_scale,
                "w2_scale_2": w2_scale_2,
                "a2_scale": a2_scale,
            },
        )
'''
    if body.count(old) != 1:
        raise SystemExit("expected ModelOpt NVFP4 MoE conversion block not found exactly once")
    text = prefix + body.replace(old, new, 1)

path.write_text(text, encoding="utf-8")
print(f"installed H20 NVFP4 MoE conversion diagnostics ({mode})")
