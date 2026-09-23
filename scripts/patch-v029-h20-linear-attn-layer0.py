#!/usr/bin/env python3
"""Install H20 layer-0 Qwen GDN linear-attention boundary diagnostics."""

from __future__ import annotations

import sys
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit(
        "usage: patch-v029-h20-linear-attn-layer0.py "
        "<vllm/model_executor/layers/mamba/gdn/qwen_gdn_linear_attn.py>"
    )

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

# qwen_gdn_linear_attn.py already imports os and torch. Add only the modules
# needed by the diagnostic runtime implementation.
import_anchor = "import os\nfrom typing import Literal\n"
import_repl = """import hashlib
import json
import os
from typing import Literal
"""
if text.count(import_anchor) != 1:
    raise SystemExit("expected qwen GDN import block exactly once")
text = text.replace(import_anchor, import_repl, 1)

helper_anchor = "logger = init_logger(__name__)\n"
helper = r'''logger = init_logger(__name__)

_QWEN38_H20L_TRIGGER = os.getenv(
    "QWEN38_H20L_TRIGGER", "/tmp/qwen38_h20l_linear.enable"
)
_QWEN38_H20L_REQUEST_FILE = os.getenv(
    "QWEN38_H20L_REQUEST_FILE", "/tmp/qwen38_h20l_request_id"
)
_QWEN38_H20L_STAGE_NAMES = {
    0: "input_hidden",
    1: "mixed_qkvz",
    2: "ba",
    3: "mixed_qkv",
    4: "z",
    5: "b",
    6: "a",
    7: "core_attn_out",
    8: "output",
}
_QWEN38_H20L_PENDING: dict[int, dict[str, torch.Tensor]] = {}

_QWEN38_H20P_TRIGGER = os.getenv(
    "QWEN38_H20P_TRIGGER", "/tmp/qwen38_h20p_qkvz_twin.enable"
)
_QWEN38_H20P_REQUEST_FILE = os.getenv(
    "QWEN38_H20P_REQUEST_FILE", "/tmp/qwen38_h20p_request_id"
)
_QWEN38_H20P_QKVZ_PROJ = None


def _qwen38_h20l_bytes(tensor: torch.Tensor) -> bytes:
    return tensor.detach().contiguous().view(torch.uint8).cpu().numpy().tobytes()


def _qwen38_h20l_fingerprint(tensor: torch.Tensor) -> dict:
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
        result["sha256"] = hashlib.sha256(_qwen38_h20l_bytes(t)).hexdigest()
        return result
    if not t.is_contiguous():
        result["hash_scope"] = "metadata-only-noncontiguous"
        result["sha256"] = None
        return result
    flat = t.contiguous().view(-1)
    k = min(1024, numel)
    starts = sorted({0, max(0, numel // 2 - k // 2), max(0, numel - k)})
    payload = b"".join(
        _qwen38_h20l_bytes(flat.narrow(0, start, min(k, numel - start)))
        for start in starts
    )
    result["hash_scope"] = {
        "kind": "head-middle-tail-elements",
        "elements_per_window": k,
        "starts": starts,
    }
    result["sha256"] = hashlib.sha256(payload).hexdigest()
    return result


def _qwen38_h20l_emit_if_complete() -> None:
    if 0 not in _QWEN38_H20L_PENDING or 1 not in _QWEN38_H20L_PENDING:
        return
    # Stage 8 is the final output boundary. Stages 3-6 are absent when the
    # fused GDN path bypasses the explicit split path, so they are optional.
    if any("output" not in _QWEN38_H20L_PENDING[rid] for rid in (0, 1)):
        return
    for rid in (0, 1):
        record = {
            "schema": 1,
            "phase": "layer0-linear-attn",
            "request_id": rid,
            "tensors": {
                name: _qwen38_h20l_fingerprint(tensor)
                for name, tensor in _QWEN38_H20L_PENDING[rid].items()
            },
        }
        print(
            "QWEN38_H20L_LINEAR " + json.dumps(record, sort_keys=True),
            flush=True,
        )
    _QWEN38_H20L_PENDING.clear()


@torch.library.custom_op(
    "qwen38_h20l::capture",
    mutates_args={"tensor"},
)
def _qwen38_h20l_capture(
    tensor: torch.Tensor,
    stage: int,
    layer_idx: int,
) -> None:
    if layer_idx != 0 or not os.path.exists(_QWEN38_H20L_TRIGGER):
        return
    stage_name = _QWEN38_H20L_STAGE_NAMES.get(stage)
    if stage_name is None:
        return
    try:
        with open(_QWEN38_H20L_REQUEST_FILE, encoding="utf-8") as handle:
            request_id = int(handle.read().strip())
    except (OSError, ValueError):
        return
    if request_id not in (0, 1):
        return
    _QWEN38_H20L_PENDING.setdefault(request_id, {})[stage_name] = (
        tensor.detach().clone()
    )
    if request_id == 1 and stage == 8:
        _qwen38_h20l_emit_if_complete()


@torch.library.custom_op(
    "qwen38_h20p::qkvz_twin",
    mutates_args={"input_hidden", "output1"},
)
def _qwen38_h20p_qkvz_twin(
    input_hidden: torch.Tensor,
    output1: torch.Tensor,
    layer_idx: int,
) -> None:
    if layer_idx != 0 or not os.path.exists(_QWEN38_H20P_TRIGGER):
        return
    try:
        with open(_QWEN38_H20P_REQUEST_FILE, encoding="utf-8") as handle:
            request_id = int(handle.read().strip())
    except (OSError, ValueError):
        return
    if request_id not in (0, 1):
        return
    proj = _QWEN38_H20P_QKVZ_PROJ
    if proj is None:
        return

    input_ref = input_hidden.detach().clone()
    output1_ref = output1.detach().clone()
    scheme = getattr(proj, "scheme", None)
    kernel = getattr(scheme, "fp8_linear", None)
    if kernel is None:
        kernel = getattr(scheme, "linear_kernel", None)
    locks = getattr(kernel, "locks", None)

    lock_pre_ref = locks.detach().clone() if locks is not None else None
    natural, _ = proj(input_ref.clone())
    natural_ref = natural.detach().clone()
    lock_after_natural_ref = (
        locks.detach().clone() if locks is not None else None
    )

    if locks is not None:
        locks.zero_()
    lock_zero1_pre_ref = locks.detach().clone() if locks is not None else None
    zero1, _ = proj(input_ref.clone())
    zero1_ref = zero1.detach().clone()
    lock_zero1_post_ref = locks.detach().clone() if locks is not None else None

    if locks is not None:
        locks.zero_()
    lock_zero2_pre_ref = locks.detach().clone() if locks is not None else None
    zero2, _ = proj(input_ref.clone())
    zero2_ref = zero2.detach().clone()
    lock_zero2_post_ref = locks.detach().clone() if locks is not None else None

    input_fp = _qwen38_h20l_fingerprint(input_ref)
    output1_fp = _qwen38_h20l_fingerprint(output1_ref)
    natural_fp = _qwen38_h20l_fingerprint(natural_ref)
    zero1_fp = _qwen38_h20l_fingerprint(zero1_ref)
    zero2_fp = _qwen38_h20l_fingerprint(zero2_ref)

    def _fp_optional(tensor):
        return None if tensor is None else _qwen38_h20l_fingerprint(tensor)

    record = {
        "schema": 3,
        "phase": "layer0-qkvz-humming-lock-control",
        "request_id": request_id,
        "input": input_fp,
        "compiled_output": output1_fp,
        "natural_eager": natural_fp,
        "zeroed_eager1": zero1_fp,
        "zeroed_eager2": zero2_fp,
        "compiled_vs_natural_equal": output1_fp == natural_fp,
        "zeroed_repeat_equal": zero1_fp == zero2_fp,
        "natural_vs_zeroed_equal": natural_fp == zero1_fp,
        "locks_present": locks is not None,
        "lock_pre": _fp_optional(lock_pre_ref),
        "lock_after_natural": _fp_optional(lock_after_natural_ref),
        "lock_zero1_pre": _fp_optional(lock_zero1_pre_ref),
        "lock_zero1_post": _fp_optional(lock_zero1_post_ref),
        "lock_zero2_pre": _fp_optional(lock_zero2_pre_ref),
        "lock_zero2_post": _fp_optional(lock_zero2_post_ref),
        "scheme_cls": type(scheme).__name__,
        "kernel_cls": type(kernel).__name__,
    }
    print(
        "QWEN38_H20P_QKVZ " + json.dumps(record, sort_keys=True),
        flush=True,
    )
'''
if text.count(helper_anchor) != 1:
    raise SystemExit("expected qwen GDN logger anchor exactly once")
text = text.replace(helper_anchor, helper, 1)

# Save a construction-time integer. Passing this scalar into the custom op is
# fullgraph-safe and avoids runtime parsing of self.prefix inside the graph.
init_anchor = """        super().__init__(config, vllm_config, prefix)

        self.num_k_heads = config.linear_num_key_heads
"""
init_repl = """        super().__init__(config, vllm_config, prefix)

        marker = ".layers."
        if marker in prefix:
            self._qwen38_h20_layer_idx = int(
                prefix.split(marker, 1)[1].split(".", 1)[0]
            )
        else:
            self._qwen38_h20_layer_idx = -1

        self.num_k_heads = config.linear_num_key_heads
"""
if text.count(init_anchor) != 1:
    raise SystemExit("expected QwenGatedDeltaNetAttention init anchor exactly once")
text = text.replace(init_anchor, init_repl, 1)

qkvz_anchor = """        self.in_proj_qkvz = self.create_qkvz_proj(
            hidden_size=self.hidden_size,
            key_dim=self.key_dim,
            value_dim=self.value_dim,
            quant_config=self.quant_config,
            prefix=f"{prefix}.in_proj_qkvz",
        )
"""
qkvz_repl = """        self.in_proj_qkvz = self.create_qkvz_proj(
            hidden_size=self.hidden_size,
            key_dim=self.key_dim,
            value_dim=self.value_dim,
            quant_config=self.quant_config,
            prefix=f"{prefix}.in_proj_qkvz",
        )
        if self._qwen38_h20_layer_idx == 0:
            global _QWEN38_H20P_QKVZ_PROJ
            _QWEN38_H20P_QKVZ_PROJ = self.in_proj_qkvz
            logger.warning(
                "QWEN38_H20P_META layer=0 proj_cls=%s quant_method=%s quant_config=%s",
                type(self.in_proj_qkvz).__name__,
                type(getattr(self.in_proj_qkvz, "quant_method", None)).__name__,
                type(self.quant_config).__name__,
            )
            scheme = getattr(self.in_proj_qkvz, "scheme", None)
            kernel = getattr(scheme, "fp8_linear", None)
            if kernel is None:
                kernel = getattr(scheme, "linear_kernel", None)
            logger.warning(
                "QWEN38_H20P_BACKEND layer=0 scheme=%s kernel=%s",
                type(scheme).__name__,
                type(kernel).__name__,
            )
"""
if text.count(qkvz_anchor) != 1:
    raise SystemExit("expected qkvz projection construction anchor exactly once")
text = text.replace(qkvz_anchor, qkvz_repl, 1)

class_start = text.index("class QwenGatedDeltaNetAttention(GatedDeltaNetAttention):")
next_class = text.find("\nclass ", class_start + 1)
if next_class < 0:
    next_class = len(text)
prefix = text[:class_start]
body = text[class_start:next_class]
suffix = text[next_class:]

start_anchor = """        num_tokens = hidden_states.size(0)
        # ============================================================
        # Part 1: Input Projection
"""
start_repl = """        num_tokens = hidden_states.size(0)
        if self._qwen38_h20_layer_idx == 0:
            _qwen38_h20l_capture(
                hidden_states, 0, self._qwen38_h20_layer_idx
            )
        # ============================================================
        # Part 1: Input Projection
"""
if body.count(start_anchor) != 1:
    raise SystemExit("expected forward_cuda start anchor exactly once")
body = body.replace(start_anchor, start_repl, 1)

proj_anchor = """        mixed_qkvz, _ = self.in_proj_qkvz(hidden_states)
        ba, _ = self.in_proj_ba(hidden_states)

        use_fused_gdn_decode = (
"""
proj_repl = """        mixed_qkvz, _ = self.in_proj_qkvz(hidden_states)
        ba, _ = self.in_proj_ba(hidden_states)
        if self._qwen38_h20_layer_idx == 0:
            _qwen38_h20l_capture(
                mixed_qkvz, 1, self._qwen38_h20_layer_idx
            )
            _qwen38_h20p_qkvz_twin(
                hidden_states,
                mixed_qkvz,
                self._qwen38_h20_layer_idx,
            )
            _qwen38_h20l_capture(ba, 2, self._qwen38_h20_layer_idx)

        use_fused_gdn_decode = (
"""
if body.count(proj_anchor) != 1:
    raise SystemExit("expected projection anchor exactly once")
body = body.replace(proj_anchor, proj_repl, 1)

fused_anchor = """            torch.ops.vllm.qwen_gdn_attention_core_fused_norm_packed(
                mixed_qkvz,
                ba,
                core_attn_out,
                layer_name=_encode_layer_name(self.prefix),
            )
            output, _ = self.out_proj(core_attn_out.flatten(-2))
            return output
"""
fused_repl = """            torch.ops.vllm.qwen_gdn_attention_core_fused_norm_packed(
                mixed_qkvz,
                ba,
                core_attn_out,
                layer_name=_encode_layer_name(self.prefix),
            )
            if self._qwen38_h20_layer_idx == 0:
                _qwen38_h20l_capture(
                    core_attn_out, 7, self._qwen38_h20_layer_idx
                )
            output, _ = self.out_proj(core_attn_out.flatten(-2))
            if self._qwen38_h20_layer_idx == 0:
                _qwen38_h20l_capture(
                    output, 8, self._qwen38_h20_layer_idx
                )
            return output
"""
if body.count(fused_anchor) != 1:
    raise SystemExit("expected fused GDN anchor exactly once")
body = body.replace(fused_anchor, fused_repl, 1)

split_anchor = """            mixed_qkv, z = mixed_qkvz.split([qkv_size, z_size], dim=-1)
            z = z.reshape(z.size(0), -1, self.head_v_dim)
            b, a = self.split_ba(ba)

        # ============================================================
        # Part 2: Core Attention (Custom Op)
"""
split_repl = """            mixed_qkv, z = mixed_qkvz.split([qkv_size, z_size], dim=-1)
            z = z.reshape(z.size(0), -1, self.head_v_dim)
            b, a = self.split_ba(ba)

        if self._qwen38_h20_layer_idx == 0:
            _qwen38_h20l_capture(
                mixed_qkv, 3, self._qwen38_h20_layer_idx
            )
            _qwen38_h20l_capture(z, 4, self._qwen38_h20_layer_idx)
            _qwen38_h20l_capture(b, 5, self._qwen38_h20_layer_idx)
            _qwen38_h20l_capture(a, 6, self._qwen38_h20_layer_idx)

        # ============================================================
        # Part 2: Core Attention (Custom Op)
"""
if body.count(split_anchor) != 1:
    raise SystemExit("expected nonfused split anchor exactly once")
body = body.replace(split_anchor, split_repl, 1)

core_anchor = """        torch.ops.vllm.qwen_gdn_attention_core(
            mixed_qkv,
            b.contiguous(),
            a.contiguous(),
            core_attn_out,
            layer_name=_encode_layer_name(self.prefix),
        )

        # ============================================================
        # Part 3: Output Projection
        # ============================================================
        return self._output_projection(core_attn_out, z)
"""
core_repl = """        torch.ops.vllm.qwen_gdn_attention_core(
            mixed_qkv,
            b.contiguous(),
            a.contiguous(),
            core_attn_out,
            layer_name=_encode_layer_name(self.prefix),
        )
        if self._qwen38_h20_layer_idx == 0:
            _qwen38_h20l_capture(
                core_attn_out, 7, self._qwen38_h20_layer_idx
            )

        # ============================================================
        # Part 3: Output Projection
        # ============================================================
        output = self._output_projection(core_attn_out, z)
        if self._qwen38_h20_layer_idx == 0:
            _qwen38_h20l_capture(output, 8, self._qwen38_h20_layer_idx)
        return output
"""
if body.count(core_anchor) != 1:
    raise SystemExit("expected nonfused core/output anchor exactly once")
body = body.replace(core_anchor, core_repl, 1)

text = prefix + body + suffix
path.write_text(text, encoding="utf-8")
print("installed H20 layer-0 Qwen GDN linear-attention diagnostics")
