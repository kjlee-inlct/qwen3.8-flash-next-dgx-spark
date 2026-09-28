#!/usr/bin/env python3
"""Install H20-M v31 Marlin W13 buffer-semantics audit in vLLM v0.29."""

from __future__ import annotations

import sys
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit(
        "usage: patch-v029-h20-marlin-boundary.py <marlin_moe.py>"
    )

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"expected {label} exactly once, found {count}")
    return source.replace(old, new, 1)


text = replace_once(
    text,
    "import math\n",
    "import json\nimport math\nimport os\n",
    "math import",
)

helper_anchor = "from vllm.scalar_type import ScalarType, scalar_types\n\n\n"
helper = r'''from vllm.scalar_type import ScalarType, scalar_types


_QWEN38_H20M_TRIGGER = os.getenv(
    "QWEN38_H20M_TRIGGER", "/tmp/qwen38_h20m_marlin.enable"
)
_QWEN38_H20M_REQUEST_FILE = os.getenv(
    "QWEN38_H20M_REQUEST_FILE", "/tmp/qwen38_h20m_request_id"
)
_QWEN38_H20M_TARGET_LAYER = os.getenv(
    "QWEN38_H20M_TARGET_LAYER",
    "language_model.model.layers.15.mlp.experts",
)
try:
    _QWEN38_H20M_TARGET_LAYER_IDX = int(
        _QWEN38_H20M_TARGET_LAYER.split(".layers.", 1)[1].split(".", 1)[0]
    )
except (IndexError, ValueError):
    _QWEN38_H20M_TARGET_LAYER_IDX = -1

_QWEN38_H20M_ACTIVE: dict[int, dict[str, object]] = {}
_QWEN38_H20M_COMPLETED: dict[int, dict[str, object]] = {}
_QWEN38_H20M_STAGE_NAMES = {
    0: "entry_hidden_states",
    1: "entry_topk_weights",
    2: "entry_topk_ids",
    3: "aligned_sorted_token_ids",
    4: "aligned_expert_ids",
    5: "aligned_num_tokens_post_padded",
    6: "w13_input",
    7: "w13_input_scale",
    8: "w13_output",
    9: "activation_output",
    10: "w2_input",
    11: "w2_input_scale",
    12: "w2_output",
    13: "final_output",
    14: "alignment_expert_map",
    15: "w13_weight_scale",
    16: "w13_global_scale",
    17: "w13_zeros",
    18: "w13_g_idx",
    19: "w13_sort_indices",
    20: "w13_workspace_pre",
    21: "w13_output_buffer_pre",
    22: "w13_bias",
}


def _qwen38_h20m_compare(left: object, right: object) -> dict:
    if left is None or right is None:
        return {
            "equal": left is None and right is None,
            "shape_match": left is None and right is None,
        }
    if isinstance(left, int) or isinstance(right, int):
        return {
            "equal": isinstance(left, int)
            and isinstance(right, int)
            and left == right,
            "shape_match": isinstance(left, int) and isinstance(right, int),
            "request0": left,
            "request1": right,
        }
    assert isinstance(left, torch.Tensor)
    assert isinstance(right, torch.Tensor)
    if tuple(left.shape) != tuple(right.shape):
        return {
            "equal": False,
            "shape_match": False,
            "request0_shape": list(left.shape),
            "request1_shape": list(right.shape),
        }
    return {
        "equal": bool(torch.equal(left, right)),
        "shape_match": True,
        "shape": list(left.shape),
        "dtype": str(left.dtype),
    }


def _qwen38_h20m_scalar_int(value: object) -> int | None:
    if not isinstance(value, torch.Tensor) or value.numel() != 1:
        return None
    return int(value.item())


def _qwen38_h20m_sorted_detail(
    left: object,
    right: object,
    left_num_tokens: object,
    right_num_tokens: object,
) -> dict:
    full = _qwen38_h20m_compare(left, right)
    result = {
        "full_equal": full["equal"],
        "valid_equal": False,
        "tail_equal": False,
        "valid_first_mismatch": None,
        "valid_mismatch_count": None,
    }
    if not isinstance(left, torch.Tensor) or not isinstance(right, torch.Tensor):
        return result
    if tuple(left.shape) != tuple(right.shape):
        return result

    n0 = _qwen38_h20m_scalar_int(left_num_tokens)
    n1 = _qwen38_h20m_scalar_int(right_num_tokens)
    result["request0_num_tokens_post_padded"] = n0
    result["request1_num_tokens_post_padded"] = n1
    if n0 is None or n1 is None or n0 != n1:
        return result
    if n0 < 0 or n0 > left.numel() or n0 > right.numel():
        result["valid_range_error"] = True
        return result

    left_valid = left[:n0]
    right_valid = right[:n0]
    valid_equal = bool(torch.equal(left_valid, right_valid))
    result["valid_equal"] = valid_equal

    left_tail = left[n0:]
    right_tail = right[n0:]
    result["tail_equal"] = bool(torch.equal(left_tail, right_tail))
    result["valid_length"] = n0
    result["tail_length"] = left.numel() - n0

    if valid_equal:
        result["valid_mismatch_count"] = 0
        return result

    mismatches = torch.nonzero(left_valid != right_valid, as_tuple=False).flatten()
    result["valid_mismatch_count"] = int(mismatches.numel())
    if mismatches.numel():
        result["valid_first_mismatch"] = int(mismatches[0].item())
    return result


def _qwen38_h20m_expert_layout_detail(
    left_sorted: object,
    right_sorted: object,
    left_experts: object,
    right_experts: object,
    left_num_tokens: object,
    right_num_tokens: object,
    left_topk_ids: object,
    right_topk_ids: object,
    left_block_size: object,
    right_block_size: object,
) -> dict:
    result = {
        "membership_equal": False,
        "order_equal": False,
        "padding_layout_equal": False,
        "mismatching_membership_experts": [],
        "mismatching_order_experts": [],
    }
    tensors = (
        left_sorted,
        right_sorted,
        left_experts,
        right_experts,
        left_topk_ids,
        right_topk_ids,
    )
    if not all(isinstance(value, torch.Tensor) for value in tensors):
        return result
    assert isinstance(left_sorted, torch.Tensor)
    assert isinstance(right_sorted, torch.Tensor)
    assert isinstance(left_experts, torch.Tensor)
    assert isinstance(right_experts, torch.Tensor)
    assert isinstance(left_topk_ids, torch.Tensor)
    assert isinstance(right_topk_ids, torch.Tensor)

    n0 = _qwen38_h20m_scalar_int(left_num_tokens)
    n1 = _qwen38_h20m_scalar_int(right_num_tokens)
    if (
        n0 is None
        or n1 is None
        or n0 != n1
        or not isinstance(left_block_size, int)
        or not isinstance(right_block_size, int)
        or left_block_size != right_block_size
        or left_block_size <= 0
    ):
        return result

    block_size = left_block_size
    if n0 % block_size != 0:
        result["invalid_block_geometry"] = True
        return result
    if n0 > left_sorted.numel() or n0 > right_sorted.numel():
        result["invalid_sorted_length"] = True
        return result

    num_blocks = n0 // block_size
    if num_blocks > left_experts.numel() or num_blocks > right_experts.numel():
        result["invalid_expert_length"] = True
        return result

    total0 = left_topk_ids.numel()
    total1 = right_topk_ids.numel()
    if total0 != total1:
        result["routed_token_count_match"] = False
        return result

    left_sorted_cpu = left_sorted[:n0].detach().cpu().tolist()
    right_sorted_cpu = right_sorted[:n0].detach().cpu().tolist()
    left_experts_cpu = left_experts[:num_blocks].detach().cpu().tolist()
    right_experts_cpu = right_experts[:num_blocks].detach().cpu().tolist()

    result["routed_token_count_match"] = True
    result["routed_token_count"] = total0
    result["valid_length"] = n0
    result["block_size_m"] = block_size
    result["num_blocks"] = num_blocks
    result["expert_ids_equal"] = left_experts_cpu == right_experts_cpu

    left_padding = [value >= total0 for value in left_sorted_cpu]
    right_padding = [value >= total0 for value in right_sorted_cpu]
    result["padding_layout_equal"] = left_padding == right_padding

    def group(
        sorted_ids: list[int],
        expert_ids: list[int],
        total_tokens: int,
    ) -> dict[int, list[int]]:
        grouped: dict[int, list[int]] = {}
        for block_idx, expert_id in enumerate(expert_ids):
            start = block_idx * block_size
            block = sorted_ids[start : start + block_size]
            valid = [token for token in block if 0 <= token < total_tokens]
            grouped.setdefault(int(expert_id), []).extend(valid)
        return grouped

    left_grouped = group(left_sorted_cpu, left_experts_cpu, total0)
    right_grouped = group(right_sorted_cpu, right_experts_cpu, total0)
    expert_keys = sorted(set(left_grouped) | set(right_grouped))

    membership_mismatch: list[int] = []
    order_mismatch: list[int] = []
    for expert_id in expert_keys:
        left_tokens = left_grouped.get(expert_id, [])
        right_tokens = right_grouped.get(expert_id, [])
        if sorted(left_tokens) != sorted(right_tokens):
            membership_mismatch.append(expert_id)
        if left_tokens != right_tokens:
            order_mismatch.append(expert_id)

    result["membership_equal"] = not membership_mismatch
    result["order_equal"] = not order_mismatch
    result["mismatching_membership_expert_count"] = len(membership_mismatch)
    result["mismatching_order_expert_count"] = len(order_mismatch)
    result["mismatching_membership_experts"] = membership_mismatch[:16]
    result["mismatching_order_experts"] = order_mismatch[:16]
    return result


def _qwen38_h20m_tensor_meta(value: object) -> dict | None:
    if not isinstance(value, torch.Tensor):
        return None
    return {
        "data_ptr": int(value.data_ptr()),
        "shape": list(value.shape),
        "stride": list(value.stride()),
        "dtype": str(value.dtype),
        "storage_offset": int(value.storage_offset()),
    }


def _qwen38_h20m_commit(
    *,
    request_id: int,
    snapshots: dict[str, object],
) -> None:
    field_order = (
        "entry_hidden_states",
        "entry_topk_weights",
        "entry_topk_ids",
        "alignment_block_size_m",
        "alignment_global_num_experts",
        "alignment_expert_map",
        "w13_weight_scale",
        "w13_global_scale",
        "w13_zeros",
        "w13_g_idx",
        "w13_sort_indices",
        "w13_workspace_pre",
        "w13_output_buffer_pre",
        "w13_bias",
        "aligned_sorted_token_ids",
        "aligned_expert_ids",
        "aligned_num_tokens_post_padded",
        "w13_input",
        "w13_input_scale",
        "w13_output",
        "activation_output",
        "w2_input",
        "w2_input_scale",
        "w2_output",
        "final_output",
    )
    for previous_id in sorted(_QWEN38_H20M_COMPLETED):
        if previous_id == request_id:
            continue
        previous = _QWEN38_H20M_COMPLETED[previous_id]
        fields = {
            name: _qwen38_h20m_compare(previous.get(name), snapshots.get(name))
            for name in field_order
        }
        sorted_detail = _qwen38_h20m_sorted_detail(
            previous.get("aligned_sorted_token_ids"),
            snapshots.get("aligned_sorted_token_ids"),
            previous.get("aligned_num_tokens_post_padded"),
            snapshots.get("aligned_num_tokens_post_padded"),
        )
        expert_layout = _qwen38_h20m_expert_layout_detail(
            previous.get("aligned_sorted_token_ids"),
            snapshots.get("aligned_sorted_token_ids"),
            previous.get("aligned_expert_ids"),
            snapshots.get("aligned_expert_ids"),
            previous.get("aligned_num_tokens_post_padded"),
            snapshots.get("aligned_num_tokens_post_padded"),
            previous.get("entry_topk_ids"),
            snapshots.get("entry_topk_ids"),
            previous.get("alignment_block_size_m"),
            snapshots.get("alignment_block_size_m"),
        )
        w13_weight_meta_equal = (
            previous.get("w13_weight_meta") == snapshots.get("w13_weight_meta")
        )
        w13_scalar_meta_equal = (
            previous.get("w13_scalar_meta") == snapshots.get("w13_scalar_meta")
        )
        previous_output_meta = previous.get("w13_output_buffer_meta")
        current_output_meta = snapshots.get("w13_output_buffer_meta")
        previous_workspace_meta = previous.get("w13_workspace_meta")
        current_workspace_meta = snapshots.get("w13_workspace_meta")

        w13_buffer_meta_equal = (
            previous_output_meta == current_output_meta
            and previous_workspace_meta == current_workspace_meta
        )

        def structural_meta(value: object) -> object:
            if not isinstance(value, dict):
                return value
            return {
                key: item
                for key, item in value.items()
                if key != "data_ptr"
            }

        w13_buffer_layout_equal = (
            structural_meta(previous_output_meta)
            == structural_meta(current_output_meta)
            and structural_meta(previous_workspace_meta)
            == structural_meta(current_workspace_meta)
        )

        def pointer_equal(left: object, right: object) -> bool:
            if not isinstance(left, dict) or not isinstance(right, dict):
                return left == right
            return left.get("data_ptr") == right.get("data_ptr")

        w13_buffer_pointer_identity_equal = (
            pointer_equal(previous_output_meta, current_output_meta)
            and pointer_equal(previous_workspace_meta, current_workspace_meta)
        )

        def pointer_alignment(value: object) -> object:
            if not isinstance(value, dict):
                return value
            ptr = value.get("data_ptr")
            if not isinstance(ptr, int):
                return None
            return {
                "mod16": ptr % 16,
                "mod128": ptr % 128,
                "mod256": ptr % 256,
                "mod4096": ptr % 4096,
            }

        w13_buffer_pointer_alignment_equal = (
            pointer_alignment(previous_output_meta)
            == pointer_alignment(current_output_meta)
            and pointer_alignment(previous_workspace_meta)
            == pointer_alignment(current_workspace_meta)
        )
        w13_workspace_content_equal = fields["w13_workspace_pre"]["equal"]
        w13_output_buffer_content_equal = fields[
            "w13_output_buffer_pre"
        ]["equal"]
        w13_buffer_semantic_equal = (
            w13_buffer_layout_equal
            and w13_buffer_pointer_alignment_equal
            and w13_workspace_content_equal
            and w13_output_buffer_content_equal
        )
        w13_state_equal = (
            w13_weight_meta_equal
            and w13_scalar_meta_equal
            and w13_buffer_semantic_equal
            and all(
                fields[name]["equal"]
                for name in (
                    "w13_weight_scale",
                    "w13_global_scale",
                    "w13_zeros",
                    "w13_g_idx",
                    "w13_sort_indices",
                    "w13_bias",
                )
            )
        )
        semantic_checks = (
            ("entry_hidden_states", fields["entry_hidden_states"]["equal"]),
            ("entry_topk_weights", fields["entry_topk_weights"]["equal"]),
            ("entry_topk_ids", fields["entry_topk_ids"]["equal"]),
            ("alignment_block_size_m", fields["alignment_block_size_m"]["equal"]),
            (
                "alignment_global_num_experts",
                fields["alignment_global_num_experts"]["equal"],
            ),
            ("alignment_expert_map", fields["alignment_expert_map"]["equal"]),
            ("aligned_sorted_token_ids_valid", sorted_detail["valid_equal"]),
            ("aligned_expert_ids", fields["aligned_expert_ids"]["equal"]),
            (
                "aligned_num_tokens_post_padded",
                fields["aligned_num_tokens_post_padded"]["equal"],
            ),
            ("w13_input", fields["w13_input"]["equal"]),
            ("w13_input_scale", fields["w13_input_scale"]["equal"]),
            ("w13_state", w13_state_equal),
            ("w13_output", fields["w13_output"]["equal"]),
            ("activation_output", fields["activation_output"]["equal"]),
            ("w2_input", fields["w2_input"]["equal"]),
            ("w2_input_scale", fields["w2_input_scale"]["equal"]),
            ("w2_output", fields["w2_output"]["equal"]),
            ("final_output", fields["final_output"]["equal"]),
        )
        first_mismatch = next(
            (name for name, equal in semantic_checks if not equal),
            None,
        )
        record = {
            "schema": 7,
            "phase": "marlin-repeat",
            "backend": "MARLIN",
            "layer_name": _QWEN38_H20M_TARGET_LAYER,
            "request0": previous_id,
            "request1": request_id,
            "fields": fields,
            "sorted_token_ids": sorted_detail,
            "full_sorted_equal": sorted_detail["full_equal"],
            "valid_sorted_equal": sorted_detail["valid_equal"],
            "tail_sorted_equal": sorted_detail["tail_equal"],
            "valid_sorted_first_mismatch": sorted_detail[
                "valid_first_mismatch"
            ],
            "valid_sorted_mismatch_count": sorted_detail[
                "valid_mismatch_count"
            ],
            "expert_layout": expert_layout,
            "expert_membership_equal": expert_layout["membership_equal"],
            "expert_order_equal": expert_layout["order_equal"],
            "padding_layout_equal": expert_layout["padding_layout_equal"],
            "aligned_expert_ids_equal": fields["aligned_expert_ids"]["equal"],
            "aligned_num_tokens_post_padded_equal": fields[
                "aligned_num_tokens_post_padded"
            ]["equal"],
            "w13_weight_meta": snapshots.get("w13_weight_meta"),
            "w13_scalar_meta": snapshots.get("w13_scalar_meta"),
            "w13_weight_meta_equal": w13_weight_meta_equal,
            "w13_scalar_meta_equal": w13_scalar_meta_equal,
            "w13_buffer_meta_equal": w13_buffer_meta_equal,
            "w13_buffer_layout_equal": w13_buffer_layout_equal,
            "w13_buffer_pointer_identity_equal": (
                w13_buffer_pointer_identity_equal
            ),
            "w13_buffer_pointer_alignment_equal": (
                w13_buffer_pointer_alignment_equal
            ),
            "w13_workspace_content_equal": w13_workspace_content_equal,
            "w13_output_buffer_content_equal": (
                w13_output_buffer_content_equal
            ),
            "w13_buffer_semantic_equal": w13_buffer_semantic_equal,
            "w13_state_equal": w13_state_equal,
            "alignment_order_only_divergence": (
                not sorted_detail["valid_equal"]
                and expert_layout["membership_equal"]
                and fields["aligned_expert_ids"]["equal"]
                and fields["aligned_num_tokens_post_padded"]["equal"]
                and all(
                    fields[name]["equal"]
                    for name in (
                        "alignment_block_size_m",
                        "alignment_global_num_experts",
                        "alignment_expert_map",
                    )
                )
            ),
            "first_mismatch": first_mismatch,
            "entry_equal": all(
                fields[name]["equal"]
                for name in (
                    "entry_hidden_states",
                    "entry_topk_weights",
                    "entry_topk_ids",
                )
            ),
            "alignment_static_equal": all(
                fields[name]["equal"]
                for name in (
                    "alignment_block_size_m",
                    "alignment_global_num_experts",
                    "alignment_expert_map",
                )
            ),
            "alignment_equal": (
                sorted_detail["valid_equal"]
                and fields["aligned_expert_ids"]["equal"]
                and fields["aligned_num_tokens_post_padded"]["equal"]
                and all(
                    fields[name]["equal"]
                    for name in (
                        "alignment_block_size_m",
                        "alignment_global_num_experts",
                        "alignment_expert_map",
                    )
                )
            ),
            "w13_input_equal": all(
                fields[name]["equal"]
                for name in ("w13_input", "w13_input_scale")
            ),
            "w13_output_equal": fields["w13_output"]["equal"],
            "activation_output_equal": fields["activation_output"]["equal"],
            "w2_input_equal": all(
                fields[name]["equal"]
                for name in ("w2_input", "w2_input_scale")
            ),
            "w2_output_equal": fields["w2_output"]["equal"],
            "final_output_equal": fields["final_output"]["equal"],
        }
        print(
            "QWEN38_H20M_MARLIN " + json.dumps(record, sort_keys=True),
            flush=True,
        )

    _QWEN38_H20M_COMPLETED[request_id] = snapshots
    while len(_QWEN38_H20M_COMPLETED) > 16:
        oldest = min(_QWEN38_H20M_COMPLETED)
        del _QWEN38_H20M_COMPLETED[oldest]


@torch.library.custom_op(
    "qwen38_h20m::capture",
    mutates_args={"tensor"},
)
def _qwen38_h20m_capture(
    tensor: torch.Tensor,
    stage: int,
    layer_idx: int,
) -> None:
    if layer_idx != _QWEN38_H20M_TARGET_LAYER_IDX:
        return
    if not os.path.exists(_QWEN38_H20M_TRIGGER):
        return
    stage_name = _QWEN38_H20M_STAGE_NAMES.get(stage)
    if stage_name is None:
        return
    try:
        with open(_QWEN38_H20M_REQUEST_FILE, encoding="utf-8") as handle:
            request_id = int(handle.read().strip())
    except (OSError, ValueError):
        return

    if stage == 0:
        snapshots: dict[str, object] = {}
        _QWEN38_H20M_ACTIVE[request_id] = snapshots
    else:
        snapshots = _QWEN38_H20M_ACTIVE.setdefault(request_id, {})
    snapshots[stage_name] = tensor.detach().clone()
    if stage == 13:
        snapshots = _QWEN38_H20M_ACTIVE.pop(request_id)
        _qwen38_h20m_commit(request_id=request_id, snapshots=snapshots)


@torch.library.custom_op(
    "qwen38_h20m::capture_w13_meta",
    mutates_args={"anchor"},
)
def _qwen38_h20m_capture_w13_meta(
    anchor: torch.Tensor,
    weight: torch.Tensor,
    output_buffer: torch.Tensor,
    workspace: torch.Tensor,
    num_topk: int,
    block_size_m: int,
    size_m: int,
    size_n: int,
    size_k: int,
    apply_router_weight_on_input: bool,
    is_k_full: bool,
    layer_idx: int,
) -> None:
    if layer_idx != _QWEN38_H20M_TARGET_LAYER_IDX:
        return
    if not os.path.exists(_QWEN38_H20M_TRIGGER):
        return
    try:
        with open(_QWEN38_H20M_REQUEST_FILE, encoding="utf-8") as handle:
            request_id = int(handle.read().strip())
    except (OSError, ValueError):
        return

    snapshots = _QWEN38_H20M_ACTIVE.setdefault(request_id, {})
    snapshots["w13_weight_meta"] = _qwen38_h20m_tensor_meta(weight)
    snapshots["w13_output_buffer_meta"] = _qwen38_h20m_tensor_meta(output_buffer)
    snapshots["w13_workspace_meta"] = _qwen38_h20m_tensor_meta(workspace)
    snapshots["w13_scalar_meta"] = {
        "num_topk": int(num_topk),
        "block_size_m": int(block_size_m),
        "size_m": int(size_m),
        "size_n": int(size_n),
        "size_k": int(size_k),
        "apply_router_weight_on_input": bool(apply_router_weight_on_input),
        "is_k_full": bool(is_k_full),
    }


@torch.library.custom_op(
    "qwen38_h20m::capture_alignment_static",
    mutates_args={"tensor"},
)
def _qwen38_h20m_capture_alignment_static(
    tensor: torch.Tensor,
    block_size_m: int,
    global_num_experts: int,
    layer_idx: int,
) -> None:
    if layer_idx != _QWEN38_H20M_TARGET_LAYER_IDX:
        return
    if not os.path.exists(_QWEN38_H20M_TRIGGER):
        return
    try:
        with open(_QWEN38_H20M_REQUEST_FILE, encoding="utf-8") as handle:
            request_id = int(handle.read().strip())
    except (OSError, ValueError):
        return

    snapshots = _QWEN38_H20M_ACTIVE.setdefault(request_id, {})
    snapshots["alignment_block_size_m"] = int(block_size_m)
    snapshots["alignment_global_num_experts"] = int(global_num_experts)


'''
text = replace_once(text, helper_anchor, helper, "helper anchor")

fused_start = text.index("def _fused_marlin_moe(")
public_start = text.index("\n\ndef fused_marlin_moe(", fused_start)
fused_body = text[fused_start:public_start]

fused_sig_old = '''    activation_config: ApplyMoEActivationConfig | None = None,
) -> torch.Tensor:
'''
fused_sig_new = '''    activation_config: ApplyMoEActivationConfig | None = None,
    h20m_layer_idx: int = -1,
) -> torch.Tensor:
'''
fused_body = replace_once(
    fused_body,
    fused_sig_old,
    fused_sig_new,
    "_fused_marlin_moe signature",
)

w13_gemm_old = '''    intermediate_cache1 = ops.moe_wna16_marlin_gemm(
        gate_up_input,
'''
w13_gemm_new = '''    _qwen38_h20m_capture(gate_up_input, 6, h20m_layer_idx)
    if a_scales1 is not None:
        _qwen38_h20m_capture(a_scales1, 7, h20m_layer_idx)
    _qwen38_h20m_capture(w1_scale, 15, h20m_layer_idx)
    if global_scale1 is not None:
        _qwen38_h20m_capture(global_scale1, 16, h20m_layer_idx)
    if w1_zeros is not None:
        _qwen38_h20m_capture(w1_zeros, 17, h20m_layer_idx)
    if g_idx1 is not None:
        _qwen38_h20m_capture(g_idx1, 18, h20m_layer_idx)
    if sort_indices1 is not None:
        _qwen38_h20m_capture(sort_indices1, 19, h20m_layer_idx)
    _qwen38_h20m_capture(workspace, 20, h20m_layer_idx)
    _qwen38_h20m_capture(intermediate_cache1, 21, h20m_layer_idx)
    if bias1 is not None:
        _qwen38_h20m_capture(bias1, 22, h20m_layer_idx)
    _qwen38_h20m_capture_w13_meta(
        gate_up_input,
        w1,
        intermediate_cache1,
        workspace,
        num_topk,
        block_size_m,
        M,
        w13_num_shards * N,
        K,
        apply_router_weight_on_input,
        is_k_full,
        h20m_layer_idx,
    )

    intermediate_cache1 = ops.moe_wna16_marlin_gemm(
        gate_up_input,
'''
fused_body = replace_once(
    fused_body, w13_gemm_old, w13_gemm_new, "w13 GEMM input"
)

activation_old = '''    activation_input = intermediate_cache1.view(-1, w13_num_shards * N)
    if activation_func is None:
'''
activation_new = '''    _qwen38_h20m_capture(intermediate_cache1, 8, h20m_layer_idx)
    activation_input = intermediate_cache1.view(-1, w13_num_shards * N)
    if activation_func is None:
'''
fused_body = replace_once(
    fused_body, activation_old, activation_new, "w13 output"
)

activation_output_old = '''    if output is None:
        output = intermediate_cache3

    a_scales2 = None
'''
activation_output_new = '''    _qwen38_h20m_capture(intermediate_cache2, 9, h20m_layer_idx)

    if output is None:
        output = intermediate_cache3

    a_scales2 = None
'''
fused_body = replace_once(
    fused_body,
    activation_output_old,
    activation_output_new,
    "activation output",
)

w2_gemm_old = '''    output = ops.moe_wna16_marlin_gemm(
        intermediate_cache2,
'''
w2_gemm_new = '''    _qwen38_h20m_capture(intermediate_cache2, 10, h20m_layer_idx)
    if a_scales2 is not None:
        _qwen38_h20m_capture(a_scales2, 11, h20m_layer_idx)

    output = ops.moe_wna16_marlin_gemm(
        intermediate_cache2,
'''
fused_body = replace_once(
    fused_body, w2_gemm_old, w2_gemm_new, "w2 GEMM input"
)

fused_return_old = '''    return output
'''
fused_return_new = '''    _qwen38_h20m_capture(output, 12, h20m_layer_idx)
    return output
'''
fused_body = replace_once(
    fused_body, fused_return_old, fused_return_new, "w2 output"
)

public_end = text.index("\n\ndef batched_fused_marlin_moe(", public_start)
public_body = text[public_start:public_end]

public_sig_old = '''    activation_config: ApplyMoEActivationConfig | None = None,
) -> torch.Tensor:
'''
public_sig_new = '''    activation_config: ApplyMoEActivationConfig | None = None,
    h20m_layer_idx: int = -1,
) -> torch.Tensor:
'''
public_body = replace_once(
    public_body,
    public_sig_old,
    public_sig_new,
    "fused_marlin_moe signature",
)

align_old = '''    sorted_token_ids, expert_ids, num_tokens_post_padded = moe_align_block_size(
        topk_ids,
        block_size_m,
        global_num_experts,
        expert_map,
        ignore_invalid_experts=True,
    )

    assert activation is not None
'''
align_new = '''    _qwen38_h20m_capture_alignment_static(
        topk_ids,
        block_size_m,
        global_num_experts,
        h20m_layer_idx,
    )
    if expert_map is not None:
        _qwen38_h20m_capture(expert_map, 14, h20m_layer_idx)

    sorted_token_ids, expert_ids, num_tokens_post_padded = moe_align_block_size(
        topk_ids,
        block_size_m,
        global_num_experts,
        expert_map,
        ignore_invalid_experts=True,
    )
    _qwen38_h20m_capture(sorted_token_ids, 3, h20m_layer_idx)
    _qwen38_h20m_capture(expert_ids, 4, h20m_layer_idx)
    _qwen38_h20m_capture(num_tokens_post_padded, 5, h20m_layer_idx)

    assert activation is not None
'''
public_body = replace_once(
    public_body, align_old, align_new, "alignment outputs"
)

call_tail_old = '''        input_dtype=input_dtype,
        is_k_full=is_k_full,
    ).view(-1, topk, K)
'''
call_tail_new = '''        input_dtype=input_dtype,
        is_k_full=is_k_full,
        h20m_layer_idx=h20m_layer_idx,
    ).view(-1, topk, K)
'''
public_body = replace_once(
    public_body, call_tail_old, call_tail_new, "_fused_marlin_moe call"
)

reduce_old = '''    if moe_sum is None:
        if expert_map is not None:
            ops.moe_sum(moe_output, output, topk_ids, expert_map)
            return output
        return torch.sum(moe_output.view(-1, topk, K), dim=1, out=output)
    else:
        return moe_sum(moe_output, output, topk_ids, expert_map)
'''
reduce_new = '''    if moe_sum is None:
        if expert_map is not None:
            ops.moe_sum(moe_output, output, topk_ids, expert_map)
            result = output
        else:
            result = torch.sum(moe_output.view(-1, topk, K), dim=1, out=output)
    else:
        result = moe_sum(moe_output, output, topk_ids, expert_map)

    _qwen38_h20m_capture(
        output if result is None else result,
        13,
        h20m_layer_idx,
    )
    return result
'''
public_body = replace_once(
    public_body, reduce_old, reduce_new, "final reduction"
)

class_start = text.index("class MarlinExperts(")
class_end = text.index("\n\nclass BatchedMarlinExperts", class_start)
class_body = text[class_start:class_end]

apply_entry_old = '''        assert self.w1_scale is not None
        assert self.w2_scale is not None

        ctx = self._lora_context
'''
apply_entry_new = '''        assert self.w1_scale is not None
        assert self.w2_scale is not None

        h20m_layer_idx = int(getattr(self, "_qwen38_h20_layer_idx", -1))
        _qwen38_h20m_capture(hidden_states, 0, h20m_layer_idx)
        _qwen38_h20m_capture(topk_weights, 1, h20m_layer_idx)
        _qwen38_h20m_capture(topk_ids, 2, h20m_layer_idx)

        ctx = self._lora_context
'''
class_body = replace_once(
    class_body, apply_entry_old, apply_entry_new, "MarlinExperts apply entry"
)

non_lora_tail_old = '''                is_k_full=self.is_k_full,
                input_dtype=self.input_dtype,
            )
            return
'''
non_lora_tail_new = '''                is_k_full=self.is_k_full,
                input_dtype=self.input_dtype,
                h20m_layer_idx=h20m_layer_idx,
            )
            return
'''
class_body = replace_once(
    class_body, non_lora_tail_old, non_lora_tail_new, "non-LoRA call"
)

lora_tail_old = '''            is_k_full=self.is_k_full,
            input_dtype=self.input_dtype,
        )
'''
lora_tail_new = '''            is_k_full=self.is_k_full,
            input_dtype=self.input_dtype,
            h20m_layer_idx=h20m_layer_idx,
        )
'''
class_body = replace_once(
    class_body, lora_tail_old, lora_tail_new, "LoRA call"
)

text = (
    text[:fused_start]
    + fused_body
    + public_body
    + text[public_end:class_start]
    + class_body
    + text[class_end:]
)

path.write_text(text, encoding="utf-8")
print("installed H20-M Marlin boundary capture")
