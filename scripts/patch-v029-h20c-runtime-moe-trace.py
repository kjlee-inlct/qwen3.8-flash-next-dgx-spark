#!/usr/bin/env python3
"""Install H20-C runtime tracing in the actual v0.29 NVFP4 quant-method apply()."""

from __future__ import annotations

import sys
from pathlib import Path

if len(sys.argv) != 3 or sys.argv[2] not in {"ct", "modelopt"}:
    raise SystemExit(
        "usage: patch-v029-h20c-runtime-moe-trace.py <nvfp4-quant-file.py> <ct|modelopt>"
    )

path = Path(sys.argv[1])
source = sys.argv[2]
text = path.read_text(encoding="utf-8")

# H20-A/B conversion diagnostics run first and provide json/os plus
# _qwen38_h20_fingerprint(). Reuse those helpers so H20-C fingerprints are
# identical and avoid a second instrumentation stack.
for required in (
    "import json\n",
    "import os\n",
    "def _qwen38_h20_fingerprint(",
    "QWEN38_H20_MOE_DIAG ",
):
    if required not in text:
        raise SystemExit(f"expected H20-A/B instrumentation first: missing {required!r}")

logger_anchor = "logger = init_logger(__name__)\n"
helper = rf'''logger = init_logger(__name__)

_QWEN38_H20C_SOURCE = "{source}"
_QWEN38_H20C_TRACE_FILE = os.getenv(
    "QWEN38_H20C_TRACE_FILE", "/tmp/qwen38_h20c_trace.enable"
)
_QWEN38_H20C_REQUEST_FILE = os.getenv(
    "QWEN38_H20C_REQUEST_FILE", "/tmp/qwen38_h20c_request_id"
)
_QWEN38_H20C_MAX_CALLS = int(os.getenv("QWEN38_H20C_MAX_CALLS", "128"))
_QWEN38_H20C_CALL = 0


@torch.compiler.disable
def _qwen38_h20c_enabled(call_index: int) -> bool:
    return (
        call_index < _QWEN38_H20C_MAX_CALLS
        and os.path.exists(_QWEN38_H20C_TRACE_FILE)
    )


@torch.compiler.disable
def _qwen38_h20c_request_id() -> int:
    try:
        with open(_QWEN38_H20C_REQUEST_FILE, encoding="utf-8") as handle:
            return int(handle.read().strip())
    except (OSError, ValueError):
        return -1


@torch.compiler.disable
def _qwen38_h20c_emit(
    *,
    phase: str,
    call_index: int,
    layer,
    tensors: dict[str, torch.Tensor | None],
) -> None:
    record = {{
        "schema": 2,
        "source": _QWEN38_H20C_SOURCE,
        "phase": phase,
        "call_index": call_index,
        "request_id": _qwen38_h20c_request_id(),
        "layer_name": str(getattr(layer, "layer_name", "")),
        "tensors": {{
            name: _qwen38_h20_fingerprint(tensor)
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

ct_old = '''    def apply(
        self,
        layer: RoutedExperts,
        x: torch.Tensor,
        topk_weights: torch.Tensor,
        topk_ids: torch.Tensor,
        shared_experts: SharedExperts | None,
        shared_experts_input: torch.Tensor | None,
    ) -> torch.Tensor:
        assert self.moe_kernel is not None
        return self.moe_kernel.apply(
            x,
            layer.w13_weight,
            layer.w2_weight,
            topk_weights,
            topk_ids,
            activation=layer.activation,
            global_num_experts=layer.global_num_experts,
            expert_map=layer.expert_map,
            apply_router_weight_on_input=layer.apply_router_weight_on_input,
            shared_experts=shared_experts,
            shared_experts_input=shared_experts_input,
        )
'''

modelopt_old = '''    def apply(
        self,
        layer: RoutedExperts,
        x: torch.Tensor,
        topk_weights: torch.Tensor,
        topk_ids: torch.Tensor,
        shared_experts: SharedExperts | None,
        shared_experts_input: torch.Tensor | None,
    ) -> torch.Tensor:
        assert not self.is_monolithic
        assert self.moe_kernel is not None
        return self.moe_kernel.apply(
            x,
            layer.w13_weight,
            layer.w2_weight,
            topk_weights,
            topk_ids,
            activation=layer.activation,
            global_num_experts=layer.global_num_experts,
            expert_map=layer.expert_map,
            apply_router_weight_on_input=layer.apply_router_weight_on_input,
            shared_experts=shared_experts,
            shared_experts_input=shared_experts_input,
        )
'''

assert_line = (
    "        assert self.moe_kernel is not None\n"
    if source == "ct"
    else "        assert not self.is_monolithic\n        assert self.moe_kernel is not None\n"
)
new_apply = f'''    def apply(
        self,
        layer: RoutedExperts,
        x: torch.Tensor,
        topk_weights: torch.Tensor,
        topk_ids: torch.Tensor,
        shared_experts: SharedExperts | None,
        shared_experts_input: torch.Tensor | None,
    ) -> torch.Tensor:
{assert_line}        global _QWEN38_H20C_CALL
        h20c_enabled = _qwen38_h20c_enabled(_QWEN38_H20C_CALL)
        h20c_call_index = _QWEN38_H20C_CALL
        if h20c_enabled:
            _QWEN38_H20C_CALL += 1
            _qwen38_h20c_emit(
                phase="pre",
                call_index=h20c_call_index,
                layer=layer,
                tensors={{
                    "x": x,
                    "topk_weights": topk_weights,
                    "topk_ids": topk_ids,
                    "shared_experts_input": shared_experts_input,
                }},
            )

        output = self.moe_kernel.apply(
            x,
            layer.w13_weight,
            layer.w2_weight,
            topk_weights,
            topk_ids,
            activation=layer.activation,
            global_num_experts=layer.global_num_experts,
            expert_map=layer.expert_map,
            apply_router_weight_on_input=layer.apply_router_weight_on_input,
            shared_experts=shared_experts,
            shared_experts_input=shared_experts_input,
        )
        if h20c_enabled:
            _qwen38_h20c_emit(
                phase="post",
                call_index=h20c_call_index,
                layer=layer,
                tensors={{"output": output}},
            )
        return output
'''

old_apply = ct_old if source == "ct" else modelopt_old
class_name = (
    "CompressedTensorsW4A4Nvfp4MoEMethod"
    if source == "ct"
    else "ModelOptNvFp4FusedMoE"
)
class_start = text.index(f"class {class_name}")
next_class = text.find("\nclass ", class_start + 1)
if next_class < 0:
    next_class = len(text)
prefix = text[:class_start]
body = text[class_start:next_class]
suffix = text[next_class:]
if body.count(old_apply) != 1:
    raise SystemExit(f"expected {class_name}.apply() exactly once in class body")
text = prefix + body.replace(old_apply, new_apply, 1) + suffix

path.write_text(text, encoding="utf-8")
print(f"installed H20-C internal-MK runtime MoE trace ({source})")
