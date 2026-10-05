#!/usr/bin/env python3
"""R32: inspect exact installed vLLM source for the pre-create MoE path.

Static/source-only. No model load, CUDA launch, allocator mutation, or tracing.
The contract distinguishes direct tensor-allocation syntax from helper/factory
construction. It does not prove that helper constructors allocate nothing.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

DEFAULT_ROOT = Path("/usr/local/lib/python3.12/dist-packages")

ALLOC_NAMES = {
    "torch.empty",
    "torch.zeros",
    "torch.ones",
    "torch.full",
    "torch.empty_like",
    "torch.zeros_like",
    "torch.ones_like",
    "torch.nn.Parameter",
    "nn.Parameter",
    "Parameter",
}


def read(root: Path, rel: str) -> str:
    path = root / rel
    if not path.is_file():
        raise SystemExit(f"missing exact-image source: {path}")
    return path.read_text(encoding="utf-8", errors="strict")


def call_name(node: ast.Call) -> str:
    parts: list[str] = []
    cur: ast.AST = node.func
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        return ".".join(reversed(parts))
    return ""


def find_class(tree: ast.Module, name: str) -> ast.ClassDef:
    rows = [x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == name]
    if len(rows) != 1:
        raise SystemExit(f"expected one class {name}, found {len(rows)}")
    return rows[0]


def find_func(body: list[ast.stmt], name: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    rows = [
        x
        for x in body
        if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) and x.name == name
    ]
    if len(rows) != 1:
        raise SystemExit(f"expected one function {name}, found {len(rows)}")
    return rows[0]


def direct_alloc_calls_before(func: ast.AST, before_lineno: int) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        if getattr(node, "lineno", 10**9) >= before_lineno:
            continue
        name = call_name(node)
        if name in ALLOC_NAMES:
            rows.append((node.lineno, name))
    return sorted(rows)


def find_call_lineno(func: ast.AST, exact: str) -> int:
    rows = [
        node.lineno
        for node in ast.walk(func)
        if isinstance(node, ast.Call) and call_name(node) == exact
    ]
    if len(rows) != 1:
        raise SystemExit(f"expected one call {exact}, found {len(rows)}")
    return rows[0]


def find_assignment_call_lineno(func: ast.AST, target_name: str, call_suffix: str) -> int:
    rows: list[int] = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id != target_name:
            continue
        if not isinstance(node.value, ast.Call):
            continue
        name = call_name(node.value)
        if name.endswith(call_suffix):
            rows.append(node.lineno)
    if len(rows) != 1:
        raise SystemExit(
            f"expected one assignment {target_name}=*{call_suffix}, found {len(rows)}"
        )
    return rows[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.root

    qwen4 = read(root, "vllm/models/qwen4_exp/nvidia/model.py")
    qwen3 = read(root, "vllm/model_executor/models/qwen3_next.py")
    factory = read(root, "vllm/model_executor/layers/fused_moe/layer.py")
    routed = read(root, "vllm/model_executor/layers/fused_moe/routed_experts.py")

    # Qwen4Exp decoder ordering.
    required_qwen4 = {
        "linear_attn": qwen4.find("self.linear_attn = QwenGatedDeltaNetAttention("),
        "self_attn": qwen4.find("self.self_attn = Qwen4ExpQSAAttention("),
        "mlp": qwen4.find("self.mlp = Qwen4ExpSparseMoeBlock("),
        "attn_hc": qwen4.find("self.attn_hyper_connection = GatedResidual("),
        "mlp_hc": qwen4.find("self.mlp_hyper_connection = GatedResidual("),
    }
    if any(v < 0 for v in required_qwen4.values()):
        raise SystemExit(f"Qwen4Exp ordering anchor missing: {required_qwen4}")
    qwen4_order_pass = (
        required_qwen4["linear_attn"] < required_qwen4["mlp"]
        and required_qwen4["self_attn"] < required_qwen4["mlp"]
        and required_qwen4["mlp"] < required_qwen4["attn_hc"]
        and required_qwen4["attn_hc"] < required_qwen4["mlp_hc"]
    )

    # Qwen3Next Sparse-MoE constructor ordering.
    gate_pos = qwen3.find("self.gate = GateLinear(")
    shared_gate_pos = qwen3.find("self.shared_expert_gate = ReplicatedLinear(")
    experts_pos = qwen3.find("self.experts = FusedMoEFactory(")
    sparse_order_pass = min(gate_pos, shared_gate_pos, experts_pos) >= 0 and (
        gate_pos < shared_gate_pos < experts_pos
    )

    # FusedMoEFactory direct allocations before RoutedExperts construction.
    factory_tree = ast.parse(factory)
    factory_func = find_func(factory_tree.body, "FusedMoEFactory")
    routed_ctor_line = find_assignment_call_lineno(
        factory_func, "routed_experts", "routed_experts_cls"
    )
    factory_allocs = direct_alloc_calls_before(factory_func, routed_ctor_line)

    # RoutedExperts direct allocations before quant_method.create_weights().
    routed_tree = ast.parse(routed)
    routed_cls = find_class(routed_tree, "RoutedExperts")
    routed_init = find_func(routed_cls.body, "__init__")
    create_line = find_call_lineno(routed_init, "self.quant_method.create_weights")
    routed_allocs = direct_alloc_calls_before(routed_init, create_line)

    # Ordering anchors inside RoutedExperts.
    routed_text_before = routed[:]
    idx_update = routed_text_before.find("self.update_expert_map_info()")
    idx_quant = routed_text_before.find("self.quant_method = self._get_quant_method(")
    idx_round = routed_text_before.find("self.quant_method.maybe_roundup_sizes(")
    idx_create = routed_text_before.find("self.quant_method.create_weights(layer=self")
    routed_order_pass = min(idx_update, idx_quant, idx_round, idx_create) >= 0 and (
        idx_update < idx_quant < idx_round < idx_create
    )

    direct_alloc_zero = not factory_allocs and not routed_allocs
    overall = qwen4_order_pass and sparse_order_pass and routed_order_pass and direct_alloc_zero

    print("R32_PRECREATE_SOURCE_CONTRACT=BEGIN")
    print("semantics=static_exact_image_source_contract_not_runtime_causal_proof")
    print(f"qwen4_decoder_attention_before_mlp={'PASS' if qwen4_order_pass else 'FAIL'}")
    print(f"qwen4_decoder_hyperconnection_after_mlp={'PASS' if qwen4_order_pass else 'FAIL'}")
    print(f"sparse_moe_gate_before_factory={'PASS' if sparse_order_pass else 'FAIL'}")
    print(f"routed_experts_order_contract={'PASS' if routed_order_pass else 'FAIL'}")
    print(f"factory_pre_routed_direct_tensor_alloc_count={len(factory_allocs)}")
    print(
        "factory_pre_routed_direct_tensor_allocs="
        + (",".join(f"{ln}:{name}" for ln, name in factory_allocs) if factory_allocs else "NONE")
    )
    print(f"routed_pre_create_direct_tensor_alloc_count={len(routed_allocs)}")
    print(
        "routed_pre_create_direct_tensor_allocs="
        + (",".join(f"{ln}:{name}" for ln, name in routed_allocs) if routed_allocs else "NONE")
    )
    print(f"direct_precreate_tensor_alloc_syntax={'ABSENT' if direct_alloc_zero else 'PRESENT'}")
    print(
        "r32_discriminator="
        + (
            "R32_NO_DIRECT_PRECREATE_WEIGHT_ALLOCATION_SUPPORTS_ALLOCATOR_BACKING_GROWTH"
            if overall
            else "R32_PRECREATE_SOURCE_CONTRACT_NOT_CLOSED"
        )
    )
    print("R32_PRECREATE_SOURCE_CONTRACT=END")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
