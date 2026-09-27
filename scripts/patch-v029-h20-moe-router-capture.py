#!/usr/bin/env python3
"""Install opt-in layer-14/15 MoE routing repeat diagnostics."""

from __future__ import annotations

import sys
from pathlib import Path


def replace_once(text: str, old: str, new: str, description: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"expected {description} exactly once, found {count}")
    return text.replace(old, new, 1)


if len(sys.argv) != 3:
    raise SystemExit(
        "usage: patch-v029-h20-moe-router-capture.py "
        "<fused_moe_router.py> <fused_moe/layer.py>"
    )

router_path, layer_path = map(Path, sys.argv[1:])
router = router_path.read_text(encoding="utf-8")
router = replace_once(
    router,
    "from abc import ABC, abstractmethod\nfrom collections.abc import Callable\n",
    "import json\nimport os\n\n"
    "from abc import ABC, abstractmethod\nfrom collections.abc import Callable\n",
    "router imports",
)

route_helper = r'''


_QWEN38_H20U_ROUTE_TRIGGER = os.getenv(
    "QWEN38_H20U_TRIGGER", "/tmp/qwen38_h20u_layer0.enable"
)
_QWEN38_H20U_ROUTE_REQUEST_FILE = os.getenv(
    "QWEN38_H20U_REQUEST_FILE", "/tmp/qwen38_h20u_request_id"
)
_QWEN38_H20U_ROUTE_LAYERS = tuple(
    sorted(
        {
            int(value)
            for value in os.getenv("QWEN38_H20U_ROUTE_LAYERS", "14,15").split(",")
            if value.strip()
        }
    )
)
_QWEN38_H20U_ROUTE_PENDING: dict[
    int, dict[int, tuple[torch.Tensor, torch.Tensor, str]]
] = {}


def _qwen38_h20u_route_layer_idx(layer_name: str) -> int | None:
    for layer_idx in _QWEN38_H20U_ROUTE_LAYERS:
        if f".layers.{layer_idx}.mlp" in layer_name:
            return layer_idx
    return None


@torch.library.custom_op(
    "qwen38_h20u::route_capture",
    mutates_args={"topk_ids"},
)
def _qwen38_h20u_route_capture(
    topk_ids: torch.Tensor,
    topk_weights: torch.Tensor,
    layer_name: str,
) -> None:
    if not os.path.exists(_QWEN38_H20U_ROUTE_TRIGGER):
        return
    layer_idx = _qwen38_h20u_route_layer_idx(layer_name)
    if layer_idx is None:
        return
    try:
        with open(_QWEN38_H20U_ROUTE_REQUEST_FILE, encoding="utf-8") as handle:
            request_id = int(handle.read().strip())
    except (OSError, ValueError):
        return
    if request_id not in (0, 1):
        return

    if (
        request_id == 0
        and _QWEN38_H20U_ROUTE_LAYERS
        and layer_idx == _QWEN38_H20U_ROUTE_LAYERS[0]
    ):
        # A new probe starts at the lowest selected layer. Clear any incomplete
        # captures left by an interrupted earlier probe without clearing again
        # when a later selected layer is reached by the same request.
        _QWEN38_H20U_ROUTE_PENDING.clear()

    layer_pending = _QWEN38_H20U_ROUTE_PENDING.setdefault(layer_idx, {})
    if request_id in layer_pending:
        return
    layer_pending[request_id] = (
        topk_ids.detach().clone(),
        topk_weights.detach().clone(),
        layer_name,
    )
    if request_id != 1 or 0 not in layer_pending:
        return

    ids0, weights0, name0 = layer_pending[0]
    ids1, weights1, name1 = layer_pending[1]

    def compare_rows(a: torch.Tensor, b: torch.Tensor) -> dict:
        if tuple(a.shape) != tuple(b.shape):
            return {
                "shape_match": False,
                "request0_shape": list(a.shape),
                "request1_shape": list(b.shape),
            }
        diff = a != b
        if diff.ndim == 0:
            diff = diff.reshape(1, 1)
        else:
            diff = diff.reshape(diff.shape[0], -1)
        counts = diff.sum(dim=1).cpu().tolist()
        changed_rows = [i for i, count in enumerate(counts) if count]
        result = {
            "shape_match": True,
            "equal": not changed_rows,
            "changed_rows": changed_rows,
            "changed_elements_by_row": {
                str(i): int(counts[i]) for i in changed_rows
            },
        }
        if a.is_floating_point() or b.is_floating_point():
            row_max = (a.float() - b.float()).abs().reshape(diff.shape[0], -1)
            max_by_row = row_max.amax(dim=1).cpu().tolist()
            result["max_abs_diff"] = float(row_max.max().item())
            result["max_abs_diff_by_row"] = {
                str(i): float(max_by_row[i]) for i in changed_rows
            }
        return result

    record = {
        "schema": 2,
        "phase": "moe-router-repeat",
        "layer_idx": layer_idx,
        "layer_name": name1,
        "layer_name_match": name0 == name1,
        "request0_shape": list(ids0.shape),
        "request1_shape": list(ids1.shape),
        "topk_ids_equal": bool(torch.equal(ids0, ids1)),
        "topk_ids": {"request0": ids0.cpu().tolist(), "request1": ids1.cpu().tolist()},
        "topk_ids_row_comparison": compare_rows(ids0, ids1),
        "topk_weights_row_comparison": compare_rows(weights0, weights1),
        "topk_weights": {
            "request0": weights0.float().cpu().tolist(),
            "request1": weights1.float().cpu().tolist(),
        },
    }
    print("QWEN38_H20U_ROUTE " + json.dumps(record, sort_keys=True), flush=True)
    _QWEN38_H20U_ROUTE_PENDING.pop(layer_idx, None)
'''
router = replace_once(
    router,
    "from vllm.model_executor.layers.fused_moe.config import RoutingMethodType\n",
    "from vllm.model_executor.layers.fused_moe.config import RoutingMethodType\n"
    + route_helper,
    "router diagnostic helper insertion anchor",
)
router = replace_once(
    router,
    "        )\n\n        # Write routing data for non-monolithic path (Triton, etc.)\n",
    "        )\n"
    "\n        # Opt-in diagnostic: capture the actual selected routes, after the\n"
    "        # router has made its normal selection and before expert execution.\n"
    "        _qwen38_h20u_route_capture(\n"
    "            topk_ids,\n"
    "            topk_weights,\n"
    "            getattr(self, \"_qwen38_h20_layer_name\", \"\"),\n"
    "        )\n\n"
    "        # Write routing data for non-monolithic path (Triton, etc.)\n",
    "route capture call insertion anchor",
)

layer = layer_path.read_text(encoding="utf-8")
layer = replace_once(
    layer,
    "    if params_dtype is None:\n",
    "    # Diagnostic routers can identify the owning model layer without\n"
    "    # changing routing inputs or recomputing the gate.\n"
    "    router._qwen38_h20_layer_name = layer_name\n"
    "\n    if params_dtype is None:\n",
    "router layer-name assignment anchor",
)

router_path.write_text(router, encoding="utf-8")
layer_path.write_text(layer, encoding="utf-8")
print("installed opt-in H20 layer-14/15 MoE route capture")
