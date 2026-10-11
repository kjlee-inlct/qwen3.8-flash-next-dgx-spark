#!/usr/bin/env python3
"""Inspect H38 CT input-scale post-construction attribute source contracts.

No torch/vLLM imports, tensor allocations, checkpoint reads, CUDA, or model
runtime. This only reasons about AST under an exact-image guarded wrapper.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path("/usr/local/lib/python3.12/dist-packages")
SOURCES = {
    "ct": ("vllm/model_executor/layers/quantization/compressed_tensors/"
           "compressed_tensors_moe/compressed_tensors_moe_w4a4_nvfp4.py"),
    "routed": "vllm/model_executor/layers/fused_moe/routed_experts.py",
    "layerwise": "vllm/model_executor/model_loader/reload/layerwise.py",
    "attrs_helper": "vllm/model_executor/utils.py",
}
EXPECTED_SHA256 = {
    "ct": "d7b47e442cee1a333753143cbd727eac857c6bbdb27d6cd8107bd6210e98e9d2",
    "routed": "5206219da6b78315d6b35bee89fd0caa783681846affbf6917f430ef7f2481b5",
    "layerwise": "9f37db893446d1f8ddc654a3bbcc3addf4b3020565920c56ef0c1ae29fd32a4a",
}
INPUT_SCALES = {
    "w13_input_global_scale": "w13_input_scale",
    "w2_input_global_scale": "w2_input_scale",
}


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = call_name(node.value)
        return (prefix + "." if prefix else "") + node.attr
    return ""


def function(tree: ast.Module, name: str,
             cls: str | None = None) -> ast.FunctionDef:
    body: list[ast.stmt] = tree.body
    if cls is not None:
        owners = [item for item in body
                  if isinstance(item, ast.ClassDef) and item.name == cls]
        require(len(owners) == 1, "expected_one_class:" + cls)
        body = owners[0].body
    found = [item for item in body
             if isinstance(item, ast.FunctionDef) and item.name == name]
    require(len(found) == 1, "expected_one_function:" + (cls or "") + "." + name)
    return found[0]


def call_statement(stmt: ast.stmt, name: str) -> ast.Call | None:
    if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
        return None
    return stmt.value if call_name(stmt.value.func) == name else None


def quant_method_tensor_update(stmt: ast.stmt) -> bool:
    call = call_statement(stmt, "extra_weight_attrs.update")
    if call is None or len(call.args) != 1 or not isinstance(call.args[0], ast.Dict):
        return False
    kvs = call.args[0]
    return any(isinstance(k, ast.Constant) and k.value == "quant_method"
               and ast.unparse(v) == "FusedMoeWeightScaleSupported.TENSOR.value"
               for k, v in zip(kvs.keys, kvs.values))


def inspect_registration(create: ast.FunctionDef, name: str,
                         var: str) -> dict[str, object]:
    # The pinned CT implementation has straight-line create_weights call sites.
    # Keep this fail-closed rather than guessing branch-aware execution.
    statements = create.body
    regs: list[tuple[int, ast.Call]] = []
    setters: list[tuple[int, ast.Call]] = []
    updates: list[int] = []
    for index, stmt in enumerate(statements):
        reg = call_statement(stmt, "layer.register_parameter")
        if reg is not None and len(reg.args) == 2:
            if isinstance(reg.args[0], ast.Constant) and reg.args[0].value == name:
                regs.append((index, reg))
        setter = call_statement(stmt, "set_weight_attrs")
        if setter is not None and len(setter.args) == 2:
            if isinstance(setter.args[0], ast.Name) and setter.args[0].id == var:
                setters.append((index, setter))
        if quant_method_tensor_update(stmt):
            updates.append(index)

    require(len(regs) == 1, "expected_one_registration:" + name)
    require(len(setters) == 1, "expected_one_attr_setter:" + name)
    reg_idx, reg = regs[0]
    set_idx, setter = setters[0]
    require(isinstance(reg.args[1], ast.Name)
            and reg.args[1].id == var, "unexpected_registered_var:" + name)
    require(isinstance(setter.args[1], ast.Name)
            and setter.args[1].id == "extra_weight_attrs",
            "unexpected_attr_dict:" + name)
    require(reg_idx < set_idx, "attr_setter_before_registration:" + name)
    between = [idx for idx in updates if reg_idx < idx < set_idx]
    require(between, "missing_tensor_quant_tag_before_setter:" + name)
    return {
        "registration_name": name,
        "variable_name": var,
        "register_line": reg.lineno,
        "set_weight_attrs_line": setter.lineno,
        "quant_method_tensor_update_line": statements[between[-1]].lineno,
        "postconstruction_call": "set_weight_attrs(" + var + ", extra_weight_attrs)",
        "attr_setter_source_site": "PRESENT",
        "attribute_value_at_runtime": "UNVERIFIED",
    }


def inspect(root: Path) -> dict[str, object]:
    trees: dict[str, ast.Module] = {}
    digests: dict[str, str] = {}
    for key, relative in SOURCES.items():
        raw = (root / relative).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if key in EXPECTED_SHA256:
            require(digest == EXPECTED_SHA256[key],
                    "sha256_mismatch:" + key + ":" + digest)
        digests[key] = digest
        trees[key] = ast.parse(raw.decode("utf-8"), filename=relative)

    # Pin the known CT/RoutedExperts/layerwise source files; capture the
    # attribute-helper digest as fresh evidence from the *image-ID-guarded*
    # immutable image. We have no independently preapproved utils.py digest.
    create = function(trees["ct"], "create_weights",
                      "CompressedTensorsW4A4Nvfp4MoEMethod")
    sites = {name: inspect_registration(create, name, var)
             for name, var in INPUT_SCALES.items()}
    create_code = ast.unparse(create)
    require("weight_loader = extra_weight_attrs.get('weight_loader')"
            in create_code, "missing_H11_weight_loader_origin")
    # Explicitly flag any pop/del that could destroy that path prior to use.
    for n in ast.walk(create):
        if isinstance(n, ast.Call) and call_name(n.func) == "extra_weight_attrs.pop":
            if n.args and isinstance(n.args[0], ast.Constant):
                require(n.args[0].value != "weight_loader",
                        "extra_attrs_loader_popped")

    routed = function(trees["routed"], "__init__", "RoutedExperts")
    require("'weight_loader': self.weight_loader" in ast.unparse(routed),
            "missing_routed_loader_export")

    wrapper = function(trees["layerwise"], "_wrap_parameters_weight_loader")
    wrap_code = ast.unparse(wrapper)
    require("tensor.weight_loader = make_online_process_loader(layer, name)"
            in wrap_code, "missing_layerwise_loader_assignment")
    online = function(trees["layerwise"], "make_online_process_loader")
    require("original_loader = _get_original_loader(param)" in ast.unparse(online),
            "missing_layerwise_original_loader_source")

    helper = function(trees["attrs_helper"], "set_weight_attrs")
    helper_code = ast.unparse(helper)
    require("for key, value in weight_attrs.items()" in helper_code,
            "missing_attr_iteration")
    require("assert not hasattr(weight, key)" in helper_code,
            "missing_attr_overwrite_guard")
    require("setattr(weight, key, value)" in helper_code,
            "missing_setattr")

    return {
        "classification": "EXACT_IMAGE_SOURCE_SITES_ONLY_NOT_RUNTIME_QUALIFICATION",
        "source_sha256": digests,
        "attrs_helper_digest_status":
            "IMAGE_ID_GUARDED_OBSERVATION_NOT_PREPINNED",
        "ct_input_scale_sites": sites,
        "h11_loader_origin_source": "extra_weight_attrs.get('weight_loader')",
        "routed_loader_export_syntax": "PRESENT",
        "layerwise_weight_loader_reassignment_syntax": "PRESENT",
        "layerwise_original_loader_retrieval_syntax": "PRESENT",
        "set_weight_attrs_guarded_setattr_syntax": "PRESENT",
        "effective_runtime_attr_value": "UNVERIFIED",
        "torch_dispatch_scale_copy_credit": "UNVERIFIED",
        "complete_loaded_experts_and_scales": "UNVERIFIED",
        "image_or_host_mutation": "NOT_PERFORMED",
        "gpu_or_model_runtime": "NOT_EXECUTED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        report = inspect(args.root)
    except (OSError, UnicodeError, SyntaxError, ValueError) as exc:
        print("H38_CT_SCALE_ATTR_SOURCE=INVALID reason=" + str(exc),
              file=sys.stderr)
        return 2
    print("H38_CT_SCALE_ATTR_SOURCE=PASS_SOURCE_SITES_ONLY")
    print(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
