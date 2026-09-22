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


def _qwen38_h20_type_name(value) -> str:
    cls = value if isinstance(value, type) else type(value)
    return f"{cls.__module__}.{cls.__qualname__}"


def _qwen38_h20_snapshot(value, depth: int = 0):
    if depth > 4:
        return {"type": _qwen38_h20_type_name(value), "truncated": True}
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, torch.Tensor):
        return {"tensor": _qwen38_h20_fingerprint(value)}
    if isinstance(value, type):
        return {"type_object": _qwen38_h20_type_name(value)}
    if isinstance(value, (list, tuple)):
        items = [_qwen38_h20_snapshot(item, depth + 1) for item in value[:32]]
        if len(value) > 32:
            items.append({"truncated_items": len(value) - 32})
        return items
    if isinstance(value, dict):
        items = sorted(value.items(), key=lambda item: str(item[0]))
        result = {
            str(key): _qwen38_h20_snapshot(val, depth + 1)
            for key, val in items[:64]
        }
        if len(items) > 64:
            result["__truncated_items__"] = len(items) - 64
        return result
    if hasattr(value, "value") and isinstance(
        getattr(value, "value"), (bool, int, float, str)
    ):
        return {
            "enum_type": _qwen38_h20_type_name(value),
            "value": getattr(value, "value"),
        }

    data = {"type": _qwen38_h20_type_name(value)}
    attrs = getattr(value, "__dict__", None)
    if isinstance(attrs, dict):
        selected = {}
        public_keys = [key for key in sorted(attrs) if not key.startswith("_")]
        for key in public_keys[:64]:
            val = attrs[key]
            if callable(val):
                continue
            selected[key] = _qwen38_h20_snapshot(val, depth + 1)
        if len(public_keys) > 64:
            selected["__truncated_attrs__"] = len(public_keys) - 64
        if selected:
            data["attrs"] = selected
    return data


def _qwen38_h20_emit_state(
    *,
    source: str,
    phase: str,
    call_index: int,
    backend,
    use_a16: bool,
    layer,
    state: dict,
) -> None:
    if call_index >= _QWEN38_H20_DIAG_MAX_CALLS:
        return
    record = {
        "schema": 2,
        "source": source,
        "phase": phase,
        "call_index": call_index,
        "backend": str(backend),
        "use_a16": bool(use_a16),
        "num_experts": int(getattr(layer, "num_experts", -1)),
        "global_num_experts": int(getattr(layer, "global_num_experts", -1)),
        "state": _qwen38_h20_snapshot(state),
    }
    print(
        "QWEN38_H20_MOE_DIAG " + json.dumps(record, sort_keys=True),
        flush=True,
    )


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

source_name = "ct" if mode == "ct" else "modelopt"
class_name = (
    "CompressedTensorsW4A4Nvfp4MoEMethod"
    if mode == "ct"
    else "ModelOptNvFp4FusedMoE"
)
class_start = text.index(f"class {class_name}")
method_start = text.index(
    "    def process_weights_after_loading(", class_start
)
method_end = text.find("\n    def ", method_start + 5)
if method_end < 0:
    method_end = len(text)
prefix = text[:method_start]
body = text[method_start:method_end]
suffix = text[method_end:]

kernel_anchor = '''        assert self.experts_cls is not None
        self.moe_kernel = make_nvfp4_moe_kernel(
'''
kernel_insert = f'''        assert self.experts_cls is not None
        h20_routing_tables = layer._expert_routing_tables()
        _qwen38_h20_emit_state(
            source="{source_name}",
            phase="quant_config",
            call_index=h20_call_index,
            backend=self.nvfp4_backend,
            use_a16=self.use_a16,
            layer=layer,
            state={{
                "moe_quant_config": self.moe_quant_config,
                "moe_config": self.moe,
                "experts_cls": self.experts_cls,
                "routing_tables": h20_routing_tables,
            }},
        )
        self.moe_kernel = make_nvfp4_moe_kernel(
'''
if body.count(kernel_anchor) != 1:
    raise SystemExit("expected modular-kernel creation anchor exactly once")
body = body.replace(kernel_anchor, kernel_insert, 1)

routing_old = "            routing_tables=layer._expert_routing_tables(),\n"
if body.count(routing_old) != 1:
    raise SystemExit("expected routing_tables call exactly once")
body = body.replace(routing_old, "            routing_tables=h20_routing_tables,\n", 1)

postload_old = "        self.moe_kernel.fused_experts.process_weights_after_loading(layer)\n"
postload_new = f'''        _qwen38_h20_emit_state(
            source="{source_name}",
            phase="kernel_created",
            call_index=h20_call_index,
            backend=self.nvfp4_backend,
            use_a16=self.use_a16,
            layer=layer,
            state={{
                "moe_kernel": self.moe_kernel,
                "fused_experts": self.moe_kernel.fused_experts,
            }},
        )
        self.moe_kernel.fused_experts.process_weights_after_loading(layer)
        _qwen38_h20_emit_state(
            source="{source_name}",
            phase="fused_postload",
            call_index=h20_call_index,
            backend=self.nvfp4_backend,
            use_a16=self.use_a16,
            layer=layer,
            state={{
                "moe_kernel": self.moe_kernel,
                "fused_experts": self.moe_kernel.fused_experts,
                "layer_w13": layer.w13_weight,
                "layer_w2": layer.w2_weight,
                "layer_w13_scale": layer.w13_weight_scale,
                "layer_w2_scale": layer.w2_weight_scale,
                "layer_w13_scale_2": layer.w13_weight_scale_2,
                "layer_w2_scale_2": layer.w2_weight_scale_2,
                "layer_a13_scale": layer.w13_input_scale,
                "layer_a2_scale": layer.w2_input_scale,
            }},
        )
'''
if body.count(postload_old) != 1:
    raise SystemExit("expected fused-experts post-load call exactly once")
body = body.replace(postload_old, postload_new, 1)
text = prefix + body + suffix

path.write_text(text, encoding="utf-8")
print(f"installed H20 NVFP4 MoE conversion diagnostics ({mode})")
