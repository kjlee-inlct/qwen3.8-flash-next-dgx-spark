#!/usr/bin/env python3
"""Inspect exact H38 CT input-global-scale lifetime and layerwise threshold syntax.

Reads *only* the four already pinned vLLM source files; stdlib AST only.
Never imports torch/vLLM, reads checkpoint, starts model/GPU, or mutates host.
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
    "ct": (
        "vllm/model_executor/layers/quantization/compressed_tensors/"
        "compressed_tensors_moe/compressed_tensors_moe_w4a4_nvfp4.py"
    ),
    "layerwise": "vllm/model_executor/model_loader/reload/layerwise.py",
    "meta": "vllm/model_executor/model_loader/reload/meta.py",
    "reload_utils": "vllm/model_executor/model_loader/reload/utils.py",
}
SHA256 = {
    "ct": "d7b47e442cee1a333753143cbd727eac857c6bbdb27d6cd8107bd6210e98e9d2",
    "layerwise": "9f37db893446d1f8ddc654a3bbcc3addf4b3020565920c56ef0c1ae29fd32a4a",
    "meta": "87a98fe340f7e39a7ba3ed136506bf5e3eef463f9215420cce5ddeb5d25a2b9c",
    "reload_utils": "9421654170a04244d9ad702ba8c81dcf6c09a3c8bfe7e04ccbe099baf57b63a1",
}
CT_CLASS = "CompressedTensorsW4A4Nvfp4MoEMethod"
SCALE_NAMES = {
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
        return prefix + "." + node.attr if prefix else node.attr
    return ""


def method(tree: ast.Module, cls: str, name: str) -> ast.FunctionDef:
    owners = [node for node in tree.body
              if isinstance(node, ast.ClassDef) and node.name == cls]
    require(len(owners) == 1, "class_not_unique:" + cls)
    found = [node for node in owners[0].body
             if isinstance(node, ast.FunctionDef) and node.name == name]
    require(len(found) == 1, "method_not_unique:" + name)
    return found[0]


def function(tree: ast.Module, name: str) -> ast.FunctionDef:
    found = [node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name == name]
    require(len(found) == 1, "function_not_unique:" + name)
    return found[0]


def layer_attr(node: ast.AST, field: str) -> bool:
    return (isinstance(node, ast.Attribute) and node.attr == field
            and isinstance(node.value, ast.Name) and node.value.id == "layer")


def trace_scale(create: ast.FunctionDef, post: ast.FunctionDef,
                name: str, variable: str) -> dict[str, object]:
    assigns = [
        node for node in ast.walk(create)
        if isinstance(node, ast.Assign) and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == variable
    ]
    require(len(assigns) == 1, "initializer_not_unique:" + variable)
    init = assigns[0].value
    require(isinstance(init, ast.Call)
            and call_name(init.func) == "torch.nn.Parameter"
            and len(init.args) == 1
            and isinstance(init.args[0], ast.Call)
            and call_name(init.args[0].func) == "torch.empty",
            "not_plain_empty_parameter:" + name)
    empty = init.args[0]
    registrations = [
        node for node in ast.walk(create)
        if isinstance(node, ast.Call)
        and call_name(node.func) == "layer.register_parameter"
        and len(node.args) == 2
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == name
        and isinstance(node.args[1], ast.Name)
        and node.args[1].id == variable
    ]
    require(len(registrations) == 1, "registered_scale_not_unique:" + name)
    setter = [
        node for node in ast.walk(create)
        if isinstance(node, ast.Call) and call_name(node.func) == "set_weight_attrs"
        and len(node.args) == 2
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id == variable
        and isinstance(node.args[1], ast.Name)
        and node.args[1].id == "extra_weight_attrs"
    ]
    require(len(setter) == 1, "scale_attr_setter_not_unique:" + name)
    require(assigns[0].lineno < registrations[0].lineno < setter[0].lineno,
            "scale_init_register_attr_order:" + name)
    post_refs = [
        node.lineno for node in ast.walk(post) if layer_attr(node, name)
    ]
    # A post-load use may be absent in a changed implementation; do not
    # invent a use or silently approve it: report it as a source blocker.
    require(bool(post_refs), "missing_postload_consumer:" + name)
    reads = [
        {
            "line": node.lineno,
            "expr": ast.unparse(node),
        }
        for node in ast.walk(post)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)
        and (any(layer_attr(child, name) for child in ast.walk(node)))
    ]
    initialized_by_ctor = any(
        isinstance(node, ast.Call) and
        call_name(node.func) in ("torch.ones", "torch.zeros", "torch.full")
        for node in ast.walk(empty)
    )
    return {
        "registration_name": name,
        "local_variable": variable,
        "constructor": "torch.nn.Parameter(torch.empty(...))",
        "constructor_line": assigns[0].lineno,
        "registration_line": registrations[0].lineno,
        "set_weight_attrs_line": setter[0].lineno,
        "constructor_explicit_device": any(k.arg == "device" for k in empty.keywords),
        "constructor_has_explicit_fill_value": initialized_by_ctor,
        "postload_reference_lines": sorted(set(post_refs)),
        "postload_division_uses": reads,
        "effective_initial_value": "UNVERIFIED",
        "checkpoint_load_event_for_this_parameter": "UNVERIFIED",
        "actual_postload_invocation": "UNVERIFIED",
    }


def inspect(root: Path) -> dict[str, object]:
    trees = {}
    for key, relative in SOURCES.items():
        data = (root / relative).read_bytes()
        observed = hashlib.sha256(data).hexdigest()
        require(observed == SHA256[key],
                "source_sha256_mismatch:" + key + ":" + observed)
        trees[key] = ast.parse(data.decode("utf-8"), filename=relative)
    create = method(trees["ct"], CT_CLASS, "create_weights")
    post = method(trees["ct"], CT_CLASS, "process_weights_after_loading")
    scales = {name: trace_scale(create, post, name, var)
              for name, var in SCALE_NAMES.items()}
    online = function(trees["layerwise"], "make_online_process_loader")
    code = ast.unparse(online)
    # Inspect the exact source-level counter trigger. A numel threshold is
    # NOT a unique-destination-coverage proof.
    checks = {
        "copy_count_from_original_loader":
            "get_numel_loaded(original_loader, bound_args)" in code,
        "count_accumulation": "info.load_numel += num_loaded" in code,
        "completion_on_accumulated_threshold":
            "info.load_numel >= info.load_numel_total" in code,
        "buffers_weight_arguments": "info.loaded_weights.append(" in code,
        "online_processing_call": "_layerwise_process(layer, info)" in code,
    }
    require(all(checks.values()), "layerwise_counter_source_missing:"
            + ",".join(k for k, v in checks.items() if not v))
    # This is only a source audit, not an inference about counter calls.
    return {
        "classification": "PINNED_CT_INPUT_SCALE_LIFECYCLE_AND_COUNTER_SOURCE_ONLY",
        "source_sha256": dict(SHA256),
        "ct_input_scale_lifecycle": scales,
        "layerwise_counter_source": checks,
        "layerwise_online_loader_line": online.lineno,
        "input_scale_index_names": "NOT_INSPECTED_IN_THIS_SOURCE_ONLY_GATE",
        "effective_input_scale_values": "UNVERIFIED",
        "source_or_runtime_default_proven": "NO",
        "unique_destination_element_completion": "UNVERIFIED",
        "actual_copycounter_credit": "UNVERIFIED",
        "actual_checkpoint_loader_callback": "UNVERIFIED",
        "shard_8_11_buffer_lifetime": "UNVERIFIED",
        "gpu_model_or_checkpoint_read": "NOT_EXECUTED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        report = inspect(args.root)
    except (OSError, UnicodeError, SyntaxError, ValueError) as exc:
        print("H38_CT_INPUT_SCALE_LIFECYCLE=INVALID reason=" + str(exc),
              file=sys.stderr)
        return 2
    print("H38_CT_INPUT_SCALE_LIFECYCLE=PASS_SOURCE_ONLY")
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
