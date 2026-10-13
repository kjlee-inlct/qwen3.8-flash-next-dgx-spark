#!/usr/bin/env python3
"""Pinned H38 CT input-scale contribution to layerwise numel target (AST only).

No torch/vLLM imports, model/checkpoint reads, CUDA, runtime or host mutation.
Reports conditional arithmetic, NEVER real H38 loader credit/initialized values.
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
    "meta": "vllm/model_executor/model_loader/reload/meta.py",
    "utils": "vllm/model_executor/model_loader/reload/utils.py",
    "layerwise": "vllm/model_executor/model_loader/reload/layerwise.py",
}
EXPECTED_SHA256 = {
    "ct": "d7b47e442cee1a333753143cbd727eac857c6bbdb27d6cd8107bd6210e98e9d2",
    "meta": "87a98fe340f7e39a7ba3ed136506bf5e3eef463f9215420cce5ddeb5d25a2b9c",
    "utils": "9421654170a04244d9ad702ba8c81dcf6c09a3c8bfe7e04ccbe099baf57b63a1",
    "layerwise": "9f37db893446d1f8ddc654a3bbcc3addf4b3020565920c56ef0c1ae29fd32a4a",
}
CT_CLASS = "CompressedTensorsW4A4Nvfp4MoEMethod"
INPUT_REGISTRATIONS = (
    "w13_input_global_scale", "w2_input_global_scale"
)


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def fn(tree: ast.Module, name: str, *, cls: str | None = None) -> ast.FunctionDef:
    body = tree.body
    if cls:
        owners = [x for x in body if isinstance(x, ast.ClassDef) and x.name == cls]
        require(len(owners) == 1, "class_not_unique:" + cls)
        body = owners[0].body
    found = [x for x in body if isinstance(x, ast.FunctionDef) and x.name == name]
    require(len(found) == 1, "function_not_unique:" + name)
    return found[0]


def name_of(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = name_of(node.value)
        return prefix + "." + node.attr if prefix else node.attr
    return ""


def skip_load_names(tree: ast.Module) -> tuple[set[str], int]:
    assignments = [
        x for x in tree.body if isinstance(x, (ast.Assign, ast.AnnAssign))
        and any(isinstance(y, ast.Name) and y.id == "SKIP_LOAD_TENSORS"
                for y in (x.targets if isinstance(x, ast.Assign) else [x.target]))
    ]
    require(len(assignments) == 1, "skip_load_set_not_unique")
    src = assignments[0].value
    require(isinstance(src, (ast.Set, ast.List, ast.Tuple)),
            "skip_load_set_not_literal")
    require(all(isinstance(el, ast.Constant) and isinstance(el.value, str)
                for el in src.elts), "skip_load_values_not_literal")
    names = {el.value for el in src.elts}
    require(len(names) == len(src.elts), "duplicate_skip_load_names")
    for target in INPUT_REGISTRATIONS:
        require(target not in names, "ct_scale_explicitly_skipped:" + target)
    return names, assignments[0].lineno


def get_scale_shapes(create: ast.FunctionDef) -> dict[str, list[str]]:
    assignments = {}
    registrations = {}
    for item in sorted(ast.walk(create),
                       key=lambda n: (getattr(n, "lineno", 0),
                                      getattr(n, "col_offset", 0))):
        if isinstance(item, ast.Assign) and len(item.targets) == 1:
            if isinstance(item.targets[0], ast.Name):
                assignments[item.targets[0].id] = item.value
        if isinstance(item, ast.Call) and name_of(item.func) == "layer.register_parameter":
            if len(item.args) != 2 or not isinstance(item.args[0], ast.Constant):
                continue
            key = item.args[0].value
            if key in INPUT_REGISTRATIONS:
                require(key not in registrations, "duplicate_ct_registration:" + key)
                require(isinstance(item.args[1], ast.Name),
                        "ct_parameter_indirection:" + key)
                registrations[key] = (item.args[1].id, item.lineno)
    result = {}
    for key in INPUT_REGISTRATIONS:
        require(key in registrations, "ct_input_scale_missing:" + key)
        local, reg_line = registrations[key]
        initializer = assignments.get(local)
        require(isinstance(initializer, ast.Call) and
                name_of(initializer.func) == "torch.nn.Parameter"
                and len(initializer.args) == 1
                and isinstance(initializer.args[0], ast.Call)
                and name_of(initializer.args[0].func) == "torch.empty",
                "ct_input_scale_not_empty:" + key)
        dimensions = [ast.unparse(x) for x in initializer.args[0].args]
        expected = (["num_experts", "w13_num_shards"]
                    if key == "w13_input_global_scale" else ["num_experts"])
        require(dimensions == expected, "ct_scale_unexpected_shape:" + key)
        result[key] = {
            "constructor": "torch.nn.Parameter(torch.empty(...))",
            "shape_expressions": dimensions,
            "registration_line": reg_line,
            "value_initialized_at_runtime": "UNVERIFIED",
        }
    return result


def inspect(root: Path) -> dict[str, object]:
    trees = {}
    for key, relative in SOURCES.items():
        raw = (root / relative).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        require(digest == EXPECTED_SHA256[key],
                "source_sha256_mismatch:" + key + ":" + digest)
        trees[key] = ast.parse(raw.decode("utf-8"), filename=relative)

    create = fn(trees["ct"], "create_weights", cls=CT_CLASS)
    shapes = get_scale_shapes(create)
    create_src = ast.unparse(create)
    require("w13_num_shards = 2 if self.moe.is_act_and_mul else 1" in create_src,
            "w13_shards_condition_unqualified")

    skip, skip_line = skip_load_names(trees["meta"])
    size = fn(trees["utils"], "get_layer_size")
    tensors = fn(trees["utils"], "get_layer_tensors")
    params = fn(trees["utils"], "get_layer_params_buffers")
    initialize = fn(trees["layerwise"], "initialize_online_processing")
    online = fn(trees["layerwise"], "make_online_process_loader")
    sz, ts, ps = ast.unparse(size), ast.unparse(tensors), ast.unparse(params)
    init, load = ast.unparse(initialize), ast.unparse(online)
    checks = {
        "size_enumerates_registered_tensors": (
            "get_layer_tensors(layer).items()" in sz and "tensor.numel()" in sz),
        "size_excludes_skip_names_only": "if name not in SKIP_LOAD_TENSORS" in sz,
        "get_layer_tensors_returns_param_buffer_union":
            "return params | buffers" in ts,
        "registered_parameters_enumerated":
            "layer._parameters.items()" in ps,
        "no_none_parameters": "if param is not None" in ps,
        "layerwise_initializes_total_from_layer_size":
            "info.load_numel_total = get_layer_size(layer)" in init,
        "layerwise_refreshes_total":
            "info.load_numel_total = get_layer_size(layer)" in load,
        "layerwise_accumulates_credit": "info.load_numel += num_loaded" in load,
        "layerwise_triggers_at_threshold":
            "info.load_numel >= info.load_numel_total" in load,
    }
    require(all(checks.values()),
            "numel_target_source_missing:" + ",".join(
                k for k, ok in checks.items() if not ok))
    # This is ONLY a symbolic contribution *if* the CT registrations are
    # present in the layer when get_layer_size is called. The model's actual
    # configuration, loader mapping and effective values have not been run.
    return {
        "classification": "PINNED_SOURCE_POTENTIAL_INPUT_SCALE_NUMEL_TARGET_ONLY",
        "source_sha256": dict(EXPECTED_SHA256),
        "input_scale_register_shapes": shapes,
        "skip_load_tensors_source_names": sorted(skip),
        "skip_load_tensors_line": skip_line,
        "input_scale_names_in_skip_load_tensors": [],
        "numel_target_source_checks": checks,
        "conditional_elements_per_expert": {
            "is_act_and_mul_true": 3,
            "is_act_and_mul_false": 2,
        },
        "illustrative_if_num_experts_is_512": {
            "per_layer_is_act_and_mul_true": 512 * 3,
            "per_layer_is_act_and_mul_false": 512 * 2,
            "across_48_layers_if_true": 48 * 512 * 3,
            "across_48_layers_if_false": 48 * 512 * 2,
        },
        "condition": "ONLY_IF_CT_REGISTERED_AND_INCLUDED_AT_GET_LAYER_SIZE_TIME",
        "actual_h38_runtime_num_experts": "UNVERIFIED",
        "real_input_scale_loader_events": "UNVERIFIED",
        "actual_layerwise_threshold_deficit": "UNVERIFIED",
        "alternative_initialization_or_default": "UNVERIFIED",
        "parameter_unique_element_coverage": "UNVERIFIED",
        "actual_shard_8_11_release": "UNVERIFIED",
        "model_gpu_checkpoint_runtime": "NOT_EXECUTED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        report = inspect(args.root)
    except (OSError, UnicodeError, ValueError, SyntaxError) as error:
        print("H38_CT_INPUT_TARGET_GAP=INVALID reason=" + str(error),
              file=sys.stderr)
        return 2
    print("H38_CT_INPUT_TARGET_GAP=PASS_SOURCE_POTENTIAL_ONLY")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
