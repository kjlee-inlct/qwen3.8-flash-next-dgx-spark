#!/usr/bin/env python3
"""Read-only installed-H38 vLLM loader source path contract (no vLLM/torch import).

This checks named source *paths and branches*, not which branch/config was
selected at runtime. Its PASS cannot authorize CT meta materialization.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
from pathlib import Path
import sys

ROOT = Path("/usr/local/lib/python3.12/dist-packages")
FILES = {
    "default_loader": "vllm/model_executor/model_loader/default_loader.py",
    "weight_utils": "vllm/model_executor/model_loader/weight_utils.py",
    "model_utils": "vllm/model_executor/models/utils.py",
    "qwen4_exp": "vllm/models/qwen4_exp/nvidia/model.py",
    "layerwise": "vllm/model_executor/model_loader/reload/layerwise.py",
    "meta": "vllm/model_executor/model_loader/reload/meta.py",
    "base_loader": "vllm/model_executor/model_loader/base_loader.py",
    "ct": (
        "vllm/model_executor/layers/quantization/compressed_tensors/"
        "compressed_tensors_moe/compressed_tensors_moe_w4a4_nvfp4.py"
    ),
}


def check(condition: bool, label: str) -> None:
    if not condition:
        raise ValueError(f"missing_exact_installed_source_contract:{label}")


def member(nodes: list[ast.stmt], kind: type, name: str) -> ast.AST:
    found = [
        node for node in nodes
        if isinstance(node, kind) and getattr(node, "name", "") == name
    ]
    check(len(found) == 1, f"exactly_one_{name}")
    return found[0]


def function_source(text: str, tree: ast.Module, name: str,
                    cls_name: str | None = None) -> str:
    if cls_name is None:
        node = member(tree.body, ast.FunctionDef, name)
    else:
        cls = member(tree.body, ast.ClassDef, cls_name)
        node = member(cls.body, ast.FunctionDef, name)
    result = ast.get_source_segment(text, node)
    check(isinstance(result, str), f"source_segment_{cls_name}_{name}")
    return result


def require_all(source: str, label: str, fragments: tuple[str, ...]) -> None:
    for fragment in fragments:
        check(fragment in source, f"{label}:{fragment}")


def inspect_sources(raw: dict[str, str]) -> dict[str, str]:
    trees: dict[str, ast.Module] = {
        name: ast.parse(raw[name], filename=name) for name in FILES
    }
    default = trees["default_loader"]
    prepare = function_source(raw["default_loader"], default, "_prepare_weights",
                              "DefaultModelLoader")
    iterator = function_source(raw["default_loader"], default,
                               "_get_weights_iterator", "DefaultModelLoader")
    all_weights = function_source(raw["default_loader"], default,
                                  "get_all_weights", "DefaultModelLoader")
    default_load = function_source(raw["default_loader"], default,
                                   "load_weights", "DefaultModelLoader")
    require_all(prepare, "indexed_shard_filter",
                ("filter_duplicate_safetensors_files(", "hf_weights_files"))
    require_all(iterator, "iterator_selection",
                ("safetensors_weights_iterator(", "enable_multithread_load",
                 "multi_thread_safetensors_weights_iterator(",
                 "safetensors_load_strategy", "fastsafetensors_weights_iterator("))
    require_all(all_weights, "primary_secondary_weights",
                ("self._get_weights_iterator(primary_weights)",
                 "secondary_weights", "yield from self._get_weights_iterator(source)"))
    require_all(default_load, "default_model_load",
                ("model.load_weights(self.get_all_weights(",))

    w = trees["weight_utils"]
    filter_index = function_source(raw["weight_utils"], w,
                                   "filter_duplicate_safetensors_files")
    st = function_source(raw["weight_utils"], w,
                         "safetensors_weights_iterator")
    require_all(filter_index, "indexed_files",
                ('json.load(f)["weight_map"]', "weight_files_in_index",
                 "hf_weights_files"))
    require_all(st, "default_safetensors_stream",
                ("sorted(hf_weights_files, key=_natural_sort_key)",
                 "with safe_open(st_file", "for name in f.keys():",
                 "f.get_tensor(name)", 'safetensors_load_strategy == "eager"',
                 'safetensors_load_strategy == "torchao"', "should_prefetch"))

    mu = trees["model_utils"]
    mapped = function_source(raw["model_utils"], mu, "_map_name_with_shard",
                             "WeightsMapper")
    mapped_apply = function_source(raw["model_utils"], mu, "apply",
                                   "WeightsMapper")
    auto_load = function_source(raw["model_utils"], mu, "load_weights",
                                "AutoWeightsLoader")
    require_all(mapped, "mtp_name_filter_semantics",
                ("for substr, new_key in self.orig_to_new_substr.items():",
                 "if new_key is None:", "return None"))
    require_all(mapped_apply, "mapping_filters_dropped_names",
                ("self._map_name_with_shard(name)", "if result is None:",
                 "continue"))
    require_all(auto_load, "autoload_mapper_application",
                ("weights = mapper.apply(weights)",))
    q = trees["qwen4_exp"]
    for cls in ("Qwen4ExpForCausalLM",
                "Qwen4ExpForConditionalGeneration"):
        load = function_source(raw["qwen4_exp"], q, "load_weights", cls)
        require_all(load, cls, ('orig_to_new_substr={"mtp.": None}',
                                "AutoWeightsLoader(", "loader.load_weights(",
                                "mapper=mapper"))
    # The source only verifies named architecture methods, not that a live
    # H38 runtime actually selects one of these two classes.
    layer = trees["layerwise"]
    initialize = function_source(raw["layerwise"], layer,
                                 "initialize_online_processing")
    wrap = function_source(raw["layerwise"], layer,
                           "make_online_process_loader")
    finalize = function_source(raw["layerwise"], layer,
                               "finalize_layerwise_processing")
    process = function_source(raw["layerwise"], layer, "_layerwise_process")
    require_all(initialize, "layerwise_count_and_wrap",
                ("get_layer_size(layer)", "_wrap_parameters_weight_loader(layer)"))
    require_all(wrap, "layerwise_completion_and_buffering",
                ("info.loaded_weights.append(", "get_numel_loaded(",
                 "info.load_numel >= info.load_numel_total",
                 "_layerwise_process(layer, info)"))
    require_all(finalize, "layerwise_finalization",
                ("_layerwise_process(layer, info)",))
    require_all(process, "layerwise_replay_and_postload",
                ("materialize_layer(layer, info)", "info.loaded_weights",
                 "param.weight_loader(", "quant_method.process_weights_after_loading"))
    materialize = function_source(raw["meta"], trees["meta"],
                                  "materialize_layer")
    require_all(materialize, "meta_materialization",
                ("tensor.is_meta", "materialize_meta_tensor"))
    base = function_source(raw["base_loader"], trees["base_loader"],
                           "_has_online_quant")
    require_all(base, "meta_gate", ('getattr(quant_method, "uses_meta_device", False)',))

    ct = trees["ct"]
    create = function_source(raw["ct"], ct, "create_weights",
                             "CompressedTensorsW4A4Nvfp4MoEMethod")
    post = function_source(raw["ct"], ct, "process_weights_after_loading",
                           "CompressedTensorsW4A4Nvfp4MoEMethod")
    require_all(create, "h11_packed_weights",
                ('layer.register_parameter("w13_weight_packed"',
                 'layer.register_parameter("w2_weight_packed"',
                 "ModelWeightParameter(", "torch.empty("))
    require_all(post, "h12_postload_object_alias",
                ('layer.register_parameter("w13_weight", layer.w13_weight_packed)',
                 'layer.register_parameter("w2_weight", layer.w2_weight_packed)'))

    return {
        "default_index_file_filter": "SOURCE_PRESENT",
        "default_primary_and_secondary_source_enumeration": "SOURCE_PRESENT",
        "safetensors_natural_file_sort_and_key_iteration": "SOURCE_PRESENT",
        "safetensors_get_tensor_before_model_mapping": "SOURCE_PRESENT",
        "alternative_eager_prefetch_multithread_paths": "SOURCE_PRESENT",
        "qwen4_causal_and_conditional_mtp_name_drop": "SOURCE_PRESENT",
        "weights_mapper_none_skips_name": "SOURCE_PRESENT",
        "layerwise_numel_completion_and_buffer_replay": "SOURCE_PRESENT",
        "ct_h11_h12_packed_and_postload_aliases": "SOURCE_PRESENT",
    }


def inspect(root: Path) -> dict[str, str]:
    raw: dict[str, str] = {}
    result: dict[str, str] = {}
    for label, relative in FILES.items():
        path = root / relative
        check(path.is_file(), f"missing:{relative}")
        contents = path.read_bytes()
        raw[label] = contents.decode("utf-8", errors="strict")
        result[f"installed_source_sha256_{label}"] = hashlib.sha256(contents).hexdigest()
    result.update(inspect_sources(raw))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        result = inspect(args.root)
    except (OSError, ValueError, SyntaxError, UnicodeError) as exc:
        print(f"H38_LOADER_STATIC_CONTRACT=INVALID reason={exc}", file=sys.stderr)
        return 2
    print("H38_LOADER_STATIC_CONTRACT=BEGIN")
    for label, value in result.items():
        print(f"{label}={value}")
    print("source_scope=pinned_h38_image_only_not_selected_runtime_path")
    print("exact_h38_active_loader_config_verified=NO")
    print("runtime_file_and_mtp_iteration_proven=NO")
    print("mtp_file_payload_skipped_before_get_tensor_proven=NO")
    print("ct_meta_w13_patch_implemented=NO")
    print("ct_meta_materialization_proven=NO")
    print("shard_split_layer_8_11_buffer_peak_bounded=NO")
    print("rm_mitigation_proven=NO")
    print("host_stability_qualified=NO")
    print("H38_LOADER_STATIC_CONTRACT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
