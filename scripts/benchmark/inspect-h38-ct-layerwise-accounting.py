#!/usr/bin/env python3
"""Extract bounded CT/online-loading accounting evidence from installed H38 source.

Source-only: never import torch/vLLM, load model/checkpoint tensors, or mutate
the installed image. A source capture is not proof of correct materialization.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path("/usr/local/lib/python3.12/dist-packages")
FILES = {
    "ct": ("vllm/model_executor/layers/quantization/compressed_tensors/"
           "compressed_tensors_moe/compressed_tensors_moe_w4a4_nvfp4.py"),
    "layerwise": "vllm/model_executor/model_loader/reload/layerwise.py",
    "meta": "vllm/model_executor/model_loader/reload/meta.py",
    "utils": "vllm/model_executor/model_loader/reload/utils.py",
    "routed": "vllm/model_executor/layers/fused_moe/routed_experts.py",
}
# Verified by earlier guarded installed-H38 inspections. Reject silent drift.
EXPECTED_SHA256 = {
    "ct": "d7b47e442cee1a333753143cbd727eac857c6bbdb27d6cd8107bd6210e98e9d2",
    "layerwise": "9f37db893446d1f8ddc654a3bbcc3addf4b3020565920c56ef0c1ae29fd32a4a",
    "meta": "87a98fe340f7e39a7ba3ed136506bf5e3eef463f9215420cce5ddeb5d25a2b9c",
    "utils": "9421654170a04244d9ad702ba8c81dcf6c09a3c8bfe7e04ccbe099baf57b63a1",
    "routed": "5206219da6b78315d6b35bee89fd0caa783681846affbf6917f430ef7f2481b5",
}
PACKED = ("w13_weight_packed", "w2_weight_packed")
SCALES = (
    "w13_weight_scale", "w2_weight_scale",
    "w13_weight_global_scale", "w2_weight_global_scale",
    "w13_input_global_scale", "w2_input_global_scale",
)
CT_CLASS = "CompressedTensorsW4A4Nvfp4MoEMethod"


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def member(nodes: list[ast.stmt], name: str, kind: type) -> ast.AST:
    found = [n for n in nodes if isinstance(n, kind)
             and getattr(n, "name", None) == name]
    require(len(found) == 1, f"expected_one:{name}")
    return found[0]


def source_method(tree: ast.Module, cls: str, method: str) -> ast.FunctionDef:
    owner = member(tree.body, cls, ast.ClassDef)
    result = member(owner.body, method, ast.FunctionDef)
    assert isinstance(result, ast.FunctionDef)
    return result


def source_func(tree: ast.Module, name: str) -> ast.FunctionDef:
    result = member(tree.body, name, ast.FunctionDef)
    assert isinstance(result, ast.FunctionDef)
    return result


def call_name(n: ast.AST) -> str:
    if isinstance(n, ast.Name):
        return n.id
    if isinstance(n, ast.Attribute):
        parent = call_name(n.value)
        return parent + "." + n.attr if parent else ""
    return ""


def one_line(n: ast.AST, limit: int = 260) -> str:
    value = " ".join(ast.unparse(n).split())
    return value if len(value) <= limit else value[:limit] + "...[TRUNCATED]"



def torch_empty_allocation(init: ast.AST) -> dict[str, object]:
    """Read literal AST allocation shape/metadata without evaluating any tensor."""
    require(isinstance(init, ast.Call), "unresolved_parameter_initializer")
    assert isinstance(init, ast.Call)
    outer = call_name(init.func)
    require(outer in ("ModelWeightParameter", "torch.nn.Parameter"),
            f"unsupported_CT_parameter_wrapper:{outer}")
    kwargs = {kw.arg: kw.value for kw in init.keywords if kw.arg is not None}
    if outer == "ModelWeightParameter":
        data = kwargs.get("data")
        require(data is not None, "missing_ModelWeightParameter_data")
    else:
        data = init.args[0] if init.args else None
    require(isinstance(data, ast.Call) and call_name(data.func) == "torch.empty",
            f"missing_parameter_torch_empty:{outer}")
    assert isinstance(data, ast.Call)
    empty_kwargs = {kw.arg: kw.value for kw in data.keywords if kw.arg is not None}
    require("dtype" in empty_kwargs, "missing_torch_empty_dtype")
    result: dict[str, object] = {
        "wrapper": outer,
        "shape": [ast.unparse(arg) for arg in data.args],
        "dtype": ast.unparse(empty_kwargs["dtype"]),
        "device": (ast.unparse(empty_kwargs["device"])
                   if "device" in empty_kwargs else "NOT_EXPLICIT"),
        "requires_grad": (ast.unparse(kwargs["requires_grad"])
                          if "requires_grad" in kwargs else "NOT_EXPLICIT"),
    }
    if outer == "ModelWeightParameter":
        for name, expected in (("input_dim", "1"), ("output_dim", "2"),
                               ("weight_loader", "weight_loader")):
            require(name in kwargs and ast.unparse(kwargs[name]) == expected,
                    f"invalid_H11_{name}")
        result["input_dim"] = "1"
        result["output_dim"] = "2"
        result["weight_loader"] = "weight_loader"
    return result

# Stored allocation dimensions from the upstream class preserved by H11/H12.
# A mismatch is an unqualified source change, NOT evidence of corrupt weights.
EXPECTED_CT_ALLOCATIONS = {
    "w13_weight_packed": (
        "ModelWeightParameter",
        ["num_experts", "w13_num_shards * intermediate_size_per_partition",
         "hidden_size // 2"], "torch.uint8"),
    "w2_weight_packed": (
        "ModelWeightParameter",
        ["num_experts", "hidden_size",
         "intermediate_size_per_partition // 2"], "torch.uint8"),
    "w13_weight_scale": (
        "torch.nn.Parameter",
        ["num_experts", "w13_num_shards * intermediate_size_per_partition",
         "hidden_size // self.group_size"], "torch.float8_e4m3fn"),
    "w2_weight_scale": (
        "torch.nn.Parameter",
        ["num_experts", "hidden_size",
         "intermediate_size_per_partition // self.group_size"],
        "torch.float8_e4m3fn"),
    "w13_weight_global_scale": (
        "torch.nn.Parameter", ["num_experts", "w13_num_shards"],
        "torch.float32"),
    "w2_weight_global_scale": (
        "torch.nn.Parameter", ["num_experts"], "torch.float32"),
    "w13_input_global_scale": (
        "torch.nn.Parameter", ["num_experts", "w13_num_shards"],
        "torch.float32"),
    "w2_input_global_scale": (
        "torch.nn.Parameter", ["num_experts"], "torch.float32"),
}


def parameter_registry(create: ast.FunctionDef) -> dict[str, dict[str, object]]:
    """Report registrations and originating initializer AST without evaluation."""
    assigns = {}
    registrations: dict[str, dict[str, object]] = {}
    # Traverse the function (including conditional branches) in source order.
    for node in sorted(ast.walk(create), key=lambda n: (getattr(n, 'lineno', 0),
                                                    getattr(n, 'col_offset', 0))):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                assigns[target.id] = node.value
        if not isinstance(node, ast.Call):
            continue
        if call_name(node.func) != "layer.register_parameter":
            continue
        require(len(node.args) >= 2 and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str),
                "non_literal_CT_parameter_registration")
        name = node.args[0].value
        require(name not in registrations, f"duplicate_registration:{name}")
        value = node.args[1]
        init = assigns.get(value.id) if isinstance(value, ast.Name) else None
        require(init is not None, f"registration_without_initializer:{name}")
        allocation = torch_empty_allocation(init)
        registrations[name] = {
            "line": node.lineno,
            "source_value": one_line(value),
            "initializer": one_line(init),
            "initializer_type": allocation["wrapper"],
            "allocation": allocation,
        }
    return registrations


def assert_packed_and_h12(trees: dict[str, ast.Module]) -> dict:
    ct = trees["ct"]
    create = source_method(ct, CT_CLASS, "create_weights")
    post = source_method(ct, CT_CLASS, "process_weights_after_loading")
    registry = parameter_registry(create)
    for name in PACKED + SCALES:
        require(name in registry, f"missing_parameter_registration:{name}")
    for name in PACKED + SCALES:
        row = registry[name]
        alloc = row["allocation"]
        wrapper, shape, dtype = EXPECTED_CT_ALLOCATIONS[name]
        require(alloc["wrapper"] == wrapper, f"incorrect_CT_parameter_wrapper:{name}")
        require(alloc["shape"] == shape, f"incorrect_CT_parameter_shape:{name}")
        require(alloc["dtype"] == dtype, f"incorrect_CT_parameter_dtype:{name}")
        require(alloc["device"] == "NOT_EXPLICIT",
                f"explicit_CT_allocation_device:{name}")
    post_code = ast.unparse(post)
    for packed in PACKED:
        target = packed.removesuffix("_packed")
        require(f"layer.register_parameter('{target}', layer.{packed})" in post_code,
                f"missing_H12_identity_alias:{packed}")
        require(f"delattr(layer, '{packed}')" in post_code,
                f"missing_H12_packed_name_cleanup:{packed}")
    return {"registrations": {k: registry[k] for k in PACKED + SCALES},
            "h12_object_alias_syntax": "PRESENT",
            "create_weights_line": create.lineno,
            "postload_line": post.lineno}


def check_accounting(trees: dict[str, ast.Module]) -> dict:
    """Assert actual source anchors, not runtime correctness of those anchors."""
    layer = trees["layerwise"]
    meta = trees["meta"]
    utils = trees["utils"]
    funcs = {
        "initialize": source_func(layer, "initialize_online_processing"),
        "online_loader": source_func(layer, "make_online_process_loader"),
        "process": source_func(layer, "_layerwise_process"),
        "finalize": source_func(layer, "finalize_layerwise_processing"),
        "size": source_func(utils, "get_layer_size"),
        "loaded_count": source_func(meta, "get_numel_loaded"),
        "materialize": source_func(meta, "materialize_layer"),
    }
    copy = member(meta.body, "CopyCounter", ast.ClassDef)
    assert isinstance(copy, ast.ClassDef)
    dispatch = member(copy.body, "__torch_dispatch__", ast.FunctionDef)
    assert isinstance(dispatch, ast.FunctionDef)
    bodies = {key: ast.unparse(val) for key, val in funcs.items()}
    anchors = {
        "initial_numel_target": "get_layer_size(layer)" in bodies["initialize"],
        "parameter_loader_wrap": "_wrap_parameters_weight_loader(layer)" in bodies["initialize"],
        "numel_count_by_loader": "get_numel_loaded(original_loader, bound_args)"
                                 in bodies["online_loader"],
        "loaded_numel_accumulates": "info.load_numel += num_loaded" in bodies["online_loader"],
        "completion_numel_gte": "info.load_numel >= info.load_numel_total"
                                in bodies["online_loader"],
        "buffered_loader_args": "info.loaded_weights.append" in bodies["online_loader"],
        "deferred_replay": "info.loaded_weights" in bodies["process"],
        "deferred_materialization": "materialize_layer(layer, info)" in bodies["process"],
        "quant_postload": "process_weights_after_loading(layer)" in bodies["process"],
        "finalize_can_call_process": "_layerwise_process(layer, info)" in bodies["finalize"],
        "per_call_count_capped": "min(numel, param.numel())" in bodies["loaded_count"],
        "copy_counter_aten_copy": "torch.ops.aten.copy_.default" in ast.unparse(dispatch),
        "copy_counter_numel": "self.copied_numel += args[0].numel()"
                              in ast.unparse(dispatch),
        "get_layer_size_uses_numel": ".numel()" in bodies["size"],
        "get_layer_size_skips_nonloadable": "SKIP_LOAD_TENSORS" in bodies["size"],
        "late_registered_size_refresh": (
            "info.load_numel_total = get_layer_size(layer)" in bodies["online_loader"]),
        "late_parameter_wrap": (
            "_wrap_parameters_weight_loader(layer)" in bodies["online_loader"]),
        "postcompletion_load_rejection": "not info.can_load()" in bodies["online_loader"],
        "materialize_preserves_parameter_class": (
            "tensor.__class__ = meta_tensor.__class__" in
            ast.unparse(source_func(meta, "materialize_meta_tensor"))),
        "materialize_preserves_parameter_attributes": (
            "tensor.__dict__ = meta_tensor.__dict__.copy()" in
            ast.unparse(source_func(meta, "materialize_meta_tensor"))),
        "partial_layer_finalization": (
            "info.load_numel < info.load_numel_total" in bodies["finalize"]),
    }
    require(all(anchors.values()),
            "accounting_source_contract_missing:" +
            ",".join(k for k, v in anchors.items() if not v))
    return {"anchors": anchors,
            "source_locations": {
                key: {"first_line": value.lineno, "last_line": value.end_lineno}
                for key, value in funcs.items()
            },
            "copy_counter_dispatch_line": dispatch.lineno,
            "note": ("These are source-level function contracts only. Element "
                     "coverage, overlapping copies, shard timing, and buffer "
                     "ownership are NOT proven by AST presence.")}



def inspect_routed_weight_loader(tree: ast.Module) -> dict[str, object]:
    """Inspect dispatched writes, not the effective Torch dispatcher events.

    A Tensor subscript assignment may trigger internal aten copy operations,
    but it cannot be equated with CopyCounter increments by static AST alone.
    """
    routed = member(tree.body, "RoutedExperts", ast.ClassDef)
    assert isinstance(routed, ast.ClassDef)
    def get_method(name: str, *, overloaded: bool = False) -> ast.FunctionDef:
        defs = [x for x in routed.body
                if isinstance(x, ast.FunctionDef) and x.name == name]
        require(bool(defs), f"missing_routed_method:{name}")
        if not overloaded:
            require(len(defs) == 1, f"ambiguous_routed_method:{name}")
        # weight_loader has @overload declarations before its implementation.
        # The concrete last definition is the one Python binds at import time.
        result = defs[-1]
        require(not (len(result.body) == 1 and isinstance(result.body[0], ast.Expr)
                     and isinstance(result.body[0].value, ast.Constant)
                     and result.body[0].value.value is Ellipsis),
                f"missing_concrete_routed_method:{name}")
        return result

    initializer = get_method("__init__")
    loader = get_method("weight_loader", overloaded=True)
    scalar = get_method("_load_single_value")
    tensor_scale = get_method("_load_per_tensor_weight_scale")
    group = get_method("_load_model_weight_or_group_weight_scale")
    w13 = get_method("_load_w13")
    w2 = get_method("_load_w2")

    init_text = ast.unparse(initializer)
    loader_text = ast.unparse(loader)
    checks = {
        "routed_constructor_exports_weight_loader":
            "'weight_loader': self.weight_loader" in init_text,
        "routed_global_to_local_expert_map":
            "self._map_global_expert_id_to_local_expert_id(global_expert_id)"
            in loader_text,
        "routed_nonlocal_expert_skip":
            "expert_id == -1" in loader_text and "use_global_sf" in loader_text,
        "routed_input_scale_dispatch":
            "self._load_single_value(" in loader_text,
        "routed_tensor_scale_dispatch":
            "self._load_per_tensor_weight_scale(" in loader_text,
        "routed_group_or_packed_dispatch":
            "self._load_model_weight_or_group_weight_scale(" in loader_text,
        "routed_GROUP_scale_tag":
            "FusedMoeWeightScaleSupported.GROUP.value" in loader_text,
        "routed_TENSOR_scale_tag":
            "FusedMoeWeightScaleSupported.TENSOR.value" in loader_text,
        "routed_group_helper_calls_w13":
            "self._load_w13(" in ast.unparse(group),
        "routed_group_helper_calls_w2":
            "self._load_w2(" in ast.unparse(group),
        "routed_w13_copy":
            "expert_data.copy_(loaded_weight)" in ast.unparse(w13),
        "routed_w2_copy":
            "expert_data.copy_(loaded_weight)" in ast.unparse(w2),
    }

    def subscript_assignment_count(node: ast.FunctionDef) -> int:
        return sum(isinstance(target, ast.Subscript)
                   for item in ast.walk(node)
                   if isinstance(item, (ast.Assign, ast.AnnAssign))
                   for target in (item.targets if isinstance(item, ast.Assign)
                                  else [item.target]))

    scalar_assigns = subscript_assignment_count(scalar)
    tensor_assigns = subscript_assignment_count(tensor_scale)
    checks["routed_single_value_subscript_write"] = scalar_assigns >= 1
    checks["routed_tensor_scale_subscript_write"] = tensor_assigns >= 2
    require(all(checks.values()),
            "routed_loader_source_contract_missing:" +
            ",".join(k for k, value in checks.items() if not value))
    return {
        "anchors": checks,
        "source_lines": {
            "weight_loader": loader.lineno,
            "single_value": scalar.lineno,
            "tensor_scale": tensor_scale.lineno,
            "group_or_packed": group.lineno,
            "w13": w13.lineno,
            "w2": w2.lineno,
        },
        "direct_subscript_assignment_sites": {
            "input_global_scale_helper": scalar_assigns,
            "tensor_global_scale_helper": tensor_assigns,
        },
        "dispatch_interpretation": "MIXED_EXPLICIT_COPY_AND_INDEXED_ASSIGNMENT",
        "actual_aten_copy_event_coverage": "UNVERIFIED",
        "actual_nonlocal_expert_or_global_sf_coverage": "UNVERIFIED",
        "actual_512_expert_parameter_completeness": "UNVERIFIED",
    }


def inspect(root: Path) -> dict:
    trees: dict[str, ast.Module] = {}
    actual: dict[str, str] = {}
    for key, relative in FILES.items():
        path = root / relative
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        require(digest == EXPECTED_SHA256[key],
                f"installed_source_sha256_mismatch:{key}:{digest}")
        actual[key] = digest
        trees[key] = ast.parse(raw.decode("utf-8"), filename=relative)
    return {
        "source_sha256": actual,
        "ct": assert_packed_and_h12(trees),
        "layerwise": check_accounting(trees),
        "routed_expert_dispatch": inspect_routed_weight_loader(trees["routed"]),
        "classification": "SOURCE_CONTRACT_ONLY_NOT_RUNTIME_QUALIFICATION",
        "complete_parameter_coverage": "UNVERIFIED",
        "per_expert_loader_mapping": "UNVERIFIED",
        "shard_split_8_11_completion": "UNVERIFIED",
        "peak_buffer_bytes": "UNVERIFIED",
        "meta_patch_or_host_mitigation": "NOT_IMPLEMENTED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        report = inspect(args.root)
    except (OSError, UnicodeError, SyntaxError, ValueError) as exc:
        print(f"H38_CT_ACCOUNTING_SOURCE=INVALID reason={exc}", file=sys.stderr)
        return 2
    print("H38_CT_ACCOUNTING_SOURCE=PASS_SOURCE_CONTRACT_ONLY")
    print(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
