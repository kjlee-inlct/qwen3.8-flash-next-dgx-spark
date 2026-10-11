#!/usr/bin/env python3
"""Pinned H38 CT/RoutedExperts destination-path AST audit (source only).

No vLLM/torch import, GPU, model/checkpoint read, or host mutation. A PASS
identifies source branch syntax, not actual checkpoint-to-expert coverage.
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
    "routed": "vllm/model_executor/layers/fused_moe/routed_experts.py",
    "layerwise": "vllm/model_executor/model_loader/reload/layerwise.py",
    "meta": "vllm/model_executor/model_loader/reload/meta.py",
}
PINNED = {
    "ct": "d7b47e442cee1a333753143cbd727eac857c6bbdb27d6cd8107bd6210e98e9d2",
    "routed": "5206219da6b78315d6b35bee89fd0caa783681846affbf6917f430ef7f2481b5",
    "layerwise": "9f37db893446d1f8ddc654a3bbcc3addf4b3020565920c56ef0c1ae29fd32a4a",
    "meta": "87a98fe340f7e39a7ba3ed136506bf5e3eef463f9215420cce5ddeb5d25a2b9c",
}


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def exact_function(tree: ast.Module, cls_name: str, method_name: str,
                   *, allow_overload: bool = False) -> ast.FunctionDef:
    classes = [n for n in tree.body
               if isinstance(n, ast.ClassDef) and n.name == cls_name]
    require(len(classes) == 1, "expected_class:" + cls_name)
    functions = [n for n in classes[0].body
                 if isinstance(n, ast.FunctionDef) and n.name == method_name]
    require(bool(functions), "missing_method:" + method_name)
    if not allow_overload:
        require(len(functions) == 1, "ambiguous_method:" + method_name)
    result = functions[-1]  # concrete body after possible @overload stubs
    require(not (len(result.body) == 1 and
                 isinstance(result.body[0], ast.Expr) and
                 isinstance(result.body[0].value, ast.Constant) and
                 result.body[0].value.value is Ellipsis),
            "overload_only:" + method_name)
    return result


def all_true(checks: dict[str, bool], name: str) -> dict[str, bool]:
    require(all(checks.values()),
            name + "_missing:" + ",".join(k for k, v in checks.items() if not v))
    return checks


def inspect(root: Path) -> dict[str, object]:
    parsed: dict[str, ast.Module] = {}
    for key, rel in SOURCES.items():
        raw = (root / rel).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        require(digest == PINNED[key], "sha256_mismatch:" + key + ":" + digest)
        parsed[key] = ast.parse(raw.decode("utf-8"), filename=rel)

    cls = "RoutedExperts"
    routed = parsed["routed"]
    methods = {
        name: exact_function(routed, cls, name,
                             allow_overload=(name == "weight_loader"))
        for name in (
            "get_expert_mapping", "load_weights", "weight_loader",
            "_map_global_expert_id_to_local_expert_id",
            "_load_per_tensor_weight_scale", "_load_single_value",
            "_load_model_weight_or_group_weight_scale", "_load_w13", "_load_w2",
        )
    }
    code = {key: ast.unparse(value) for key, value in methods.items()}
    ct = exact_function(parsed["ct"],
                        "CompressedTensorsW4A4Nvfp4MoEMethod", "create_weights")
    ct_code = ast.unparse(ct)
    # These are intentionally source-only, high-discrimination predicates;
    # static branch presence is NOT branch execution or full data coverage.
    mapping = all_true({
        "expert_mapping_builder":
            "self.build_expert_params_mapping(" in code["get_expert_mapping"],
        "load_weights_get_mapping":
            "self.get_expert_mapping(include_fused=True)" in code["load_weights"],
        "load_weights_name_match":
            "weight_name not in qual_name" in code["load_weights"],
        "load_weights_fused_tensor_split":
            "shard_id in {'w1', 'w3'}" in code["load_weights"]
            and "fused_weight.chunk(2, dim=1)" in code["load_weights"],
        "load_weights_per_expert_fused_split":
            "loaded_weight.chunk(2, dim=0)" in code["load_weights"],
        "load_weights_callback":
            "param.weight_loader(" in code["load_weights"]
            and "return_success=True" in code["load_weights"],
        "global_to_local_expert_mapping":
            "self._map_global_expert_id_to_local_expert_id(global_expert_id)"
            in code["weight_loader"],
        "nonlocal_skip_with_global_sf_exception":
            "expert_id == -1 and (not use_global_sf)" in code["weight_loader"]
            or "expert_id == -1 and not use_global_sf" in code["weight_loader"],
        "global_scale_exception_guard":
            "getattr(self.quant_method, 'use_global_sf', False)"
            in code["weight_loader"],
        "shard_id_validation":
            "shard_id not in ('w1', 'w2', 'w3')" in code["weight_loader"],
        "full_load_branch":
            "full_load = len(loaded_weight.shape) == 3"
            in code["weight_loader"],
    }, "mapping")

    scale = all_true({
        "tensor_scale_w1_w3_indices":
            "idx = 0 if shard_id == 'w1' else 1"
            in code["_load_per_tensor_weight_scale"],
        "tensor_scale_destination_by_expert_and_index":
            "param_data[expert_id][idx] = self._to_scalar(loaded_weight)"
            in code["_load_per_tensor_weight_scale"],
        "tensor_scale_w2_destination":
            "param_data[expert_id] = self._to_scalar(loaded_weight)"
            in code["_load_per_tensor_weight_scale"],
        "input_scale_single_value_full_row_assignment":
            "param_data[expert_id] = loaded_weight"
            in code["_load_single_value"],
        "input_scale_branch_priority":
            code["weight_loader"].find("'input_scale' in weight_name")
            < code["weight_loader"].find("'scale' in weight_name"),
        "input_scale_global_expert_id_conditional":
            "global_expert_id if use_global_sf else expert_id"
            in code["weight_loader"],
        "input_scale_scalar_helper_call":
            "self._load_single_value(" in code["weight_loader"],
        "tensor_quantization_dispatch":
            "FusedMoeWeightScaleSupported.TENSOR.value"
            in code["weight_loader"],
        "group_quantization_dispatch":
            "FusedMoeWeightScaleSupported.GROUP.value"
            in code["weight_loader"],
        "modelopt_separate_input_w1_w3_conditional":
            "'ModelOpt' in quant_method_name" in code["weight_loader"]
            and "scale_shard_id = 0 if shard_id == 'w1' else 1"
            in code["weight_loader"],
        "compressed_input_scale_conflict_check":
            "'compressed' in quant_method_name.lower()"
            in code["weight_loader"] and "input_scales of w1 and w3"
            in code["weight_loader"],
    }, "scale")

    packed = all_true({
        "w13_logical_first_half":
            "expert_data.narrow(shard_dim, 0, shard_size)" in code["_load_w13"],
        "w13_logical_second_half":
            "expert_data.narrow(shard_dim, shard_size, shard_size)"
            in code["_load_w13"],
        "w13_explicit_copy":
            "expert_data.copy_(loaded_weight)" in code["_load_w13"],
        "w2_explicit_copy":
            "expert_data.copy_(loaded_weight)" in code["_load_w2"],
        "group_packed_common_w13_w2_delegate":
            "self._load_w13(" in code["_load_model_weight_or_group_weight_scale"]
            and "self._load_w2(" in code["_load_model_weight_or_group_weight_scale"],
        "w13_packed_parameter_shape":
            "layer.register_parameter('w13_weight_packed', w13_weight)"
            in ct_code,
        "w13_group_scale_parameter_shape":
            "layer.register_parameter('w13_weight_scale', w13_weight_scale)"
            in ct_code,
    }, "packed")

    # The mapping below is a compact interpretation of the inspected sites,
    # deliberately not a checkpoint-name/expert manifest or coverage proof.
    destinations = [
        {"ct_parameter": "w13_weight_packed", "shards": ["w1", "w3"],
         "source_helper": "_load_w13", "potential_destination": "per-expert two logical halves"},
        {"ct_parameter": "w2_weight_packed", "shards": ["w2"],
         "source_helper": "_load_w2", "potential_destination": "per-expert full down projection"},
        {"ct_parameter": "w13_weight_scale", "shards": ["w1", "w3"],
         "source_helper": "_load_w13", "potential_destination": "per-expert two group-scale halves"},
        {"ct_parameter": "w2_weight_scale", "shards": ["w2"],
         "source_helper": "_load_w2", "potential_destination": "per-expert group-scale down projection"},
        {"ct_parameter": "w13_weight_global_scale", "shards": ["w1", "w3"],
         "source_helper": "_load_per_tensor_weight_scale",
         "potential_destination": "per-expert index 0/1, conditional TENSOR dispatch"},
        {"ct_parameter": "w2_weight_global_scale", "shards": ["w2"],
         "source_helper": "_load_per_tensor_weight_scale",
         "potential_destination": "per-expert scalar, conditional TENSOR dispatch"},
        {"ct_parameter": "w13_input_global_scale", "shards": ["w1", "w3"],
         "source_helper": "_load_single_value OR ModelOpt special branch",
         "potential_destination": "generic full expert row; ModelOpt may use index 0/1"},
        {"ct_parameter": "w2_input_global_scale", "shards": ["w2"],
         "source_helper": "_load_single_value",
         "potential_destination": "per-expert scalar/row"},
    ]
    return {
        "classification": "PINNED_SOURCE_BRANCHES_ONLY_NO_REAL_EXPERT_COVERAGE",
        "source_sha256": dict(PINNED),
        "source_anchors": {
            "expert_mapping": mapping,
            "scale_paths": scale,
            "packed_and_group_paths": packed,
        },
        "source_method_lines": {k: v.lineno for k, v in methods.items()},
        "ct_creation_line": ct.lineno,
        "conditional_destination_hypotheses": destinations,
        "real_expert_id_mapping": "UNVERIFIED",
        "real_checkpoint_name_to_parameter_matches": "UNVERIFIED",
        "actual_input_scale_values_or_conflict": "UNVERIFIED",
        "real_copy_dispatch_numel": "UNVERIFIED",
        "unique_real_destination_coverage": "UNVERIFIED",
        "layer_8_11_shard_revisit_or_buffer_lifetime": "UNVERIFIED",
        "model_or_gpu_execution": "NOT_EXECUTED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        report = inspect(args.root)
    except (OSError, UnicodeError, SyntaxError, ValueError) as exc:
        print("H38_CT_EXPERT_DESTINATION_SOURCE=INVALID reason=" + str(exc),
              file=sys.stderr)
        return 2
    print("H38_CT_EXPERT_DESTINATION_SOURCE=PASS_SOURCE_BRANCHES_ONLY")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
