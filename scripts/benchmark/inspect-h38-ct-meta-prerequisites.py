#!/usr/bin/env python3
"""Static-only H38 CT deferred-w13 prerequisites; NOT mitigation qualification.

Run against installed source in an already existing H38 image, with no
torch/vLLM imports, no model execution and no modifications.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
from pathlib import Path
import sys

DEFAULT_ROOT = Path("/usr/local/lib/python3.12/dist-packages")
FILES = {
    "ct": "vllm/model_executor/layers/quantization/compressed_tensors/"
          "compressed_tensors_moe/compressed_tensors_moe_w4a4_nvfp4.py",
    "base_loader": "vllm/model_executor/model_loader/base_loader.py",
    "layerwise": "vllm/model_executor/model_loader/reload/layerwise.py",
    "reload_meta": "vllm/model_executor/model_loader/reload/meta.py",
    "reload_utils": "vllm/model_executor/model_loader/reload/utils.py",
    "routed": "vllm/model_executor/layers/fused_moe/routed_experts.py",
}
CT_METHOD = "CompressedTensorsW4A4Nvfp4MoEMethod"


def require(condition: bool, why: str) -> None:
    if not condition:
        raise ValueError(why)


def call_name(node: ast.AST) -> str:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return ""


def find_class(tree: ast.Module, name: str) -> ast.ClassDef:
    found = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name]
    require(len(found) == 1, f"expected exactly one {name}")
    return found[0]


def find_func(nodes: list[ast.stmt], name: str) -> ast.FunctionDef:
    found = [n for n in nodes if isinstance(n, ast.FunctionDef) and n.name == name]
    require(len(found) == 1, f"expected exactly one {name}")
    return found[0]


def find_assignment_call(func: ast.FunctionDef, var: str) -> ast.Call:
    found: list[ast.Call] = []
    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            if any(isinstance(t, ast.Name) and t.id == var for t in node.targets):
                found.append(node.value)
    require(len(found) == 1, f"expected exactly one {var} assignment")
    return found[0]


def keyword(call: ast.Call, name: str) -> ast.AST | None:
    return next((k.value for k in call.keywords if k.arg == name), None)


def scoped_call_count(func: ast.FunctionDef, name: str) -> int:
    return sum(
        isinstance(n, ast.Call) and call_name(n.func) == name
        for n in ast.walk(func)
    )


def inspect_ct(text: str) -> dict[str, str]:
    tree = ast.parse(text)
    cls = find_class(tree, CT_METHOD)
    create = find_func(cls.body, "create_weights")
    post = find_func(cls.body, "process_weights_after_loading")
    for name in ("w13_weight", "w2_weight"):
        init = find_assignment_call(create, name)
        require(call_name(init.func) == "ModelWeightParameter",
                f"{name}: installed H11 ModelWeightParameter absent")
        data = keyword(init, "data")
        require(isinstance(data, ast.Call)
                and call_name(data.func) == "torch.empty",
                f"{name}: packed torch.empty absent")
        require(keyword(data, "device") is None,
                f"{name}: current allocation already specifies device")
        require(keyword(init, "weight_loader") is not None,
                f"{name}: weight_loader missing")
    for name in ("w13_weight_packed", "w2_weight_packed"):
        target = name.replace("_packed", "")
        require(f'layer.register_parameter("{name}", {target})' in text,
                f"{name}: packed registration missing")
        require(f'layer.register_parameter("{target}", layer.{name})' in text,
                f"{target}: H12 post-load alias missing")
    for target in ("w13_weight", "w2_weight"):
        require(f'layer.{target} = torch.nn.Parameter(' not in text,
                f"{target}: unexpected H12 rewrapping")
    require(scoped_call_count(post, "layer.register_parameter") >= 2,
            "H12 process_weights_after_loading registrations missing")
    own_meta = any(
        isinstance(n, (ast.Assign, ast.AnnAssign))
        and any(isinstance(t, ast.Name) and t.id == "uses_meta_device"
                for t in (n.targets if isinstance(n, ast.Assign) else [n.target]))
        for n in cls.body
    )
    return {
        "ct_packed_w13_h11_torch_empty": "YES",
        "ct_packed_w2_h11_torch_empty": "YES",
        "ct_h12_postload_alias": "PASS",
        "ct_declares_own_uses_meta_device": "YES" if own_meta else "NO",
    }


def inspect_lifecycle(texts: dict[str, str]) -> dict[str, str]:
    base = texts["base_loader"]
    layer = texts["layerwise"]
    meta = texts["reload_meta"]
    utils = texts["reload_utils"]
    routed = texts["routed"]
    # Intentionally check AST/parsing + known exact-v0.29 markers.
    # These source contracts are prerequisites, not a functional proof
    # for the H38 compressed-tensors variant.
    for label, needles in {
        "base_loader": (
            'getattr(quant_method, "uses_meta_device", False)',
            "finalize_layerwise_processing(model, model_config)",
        ),
        "layerwise": (
            "def initialize_online_processing(",
            "materialize_layer(layer, info)",
            "quant_method.process_weights_after_loading(layer)",
            "def _get_original_loader(",
            "get_layer_size(layer)",
        ),
        "reload_meta": ("def materialize_layer(",),
        "reload_utils": ("def get_layer_size(",),
        "routed": (
            "self.quant_method = self._get_quant_method(",
            "self.quant_method.create_weights(",
        ),
    }.items():
        for needle in needles:
            require(needle in texts[label], f"{label}: missing {needle}")
    require(
        routed.index("self.quant_method = self._get_quant_method(")
        < routed.index("self.quant_method.create_weights("),
        "RoutedExperts quant method constructed after create_weights",
    )
    layer_tree = ast.parse(layer)
    f = find_func(layer_tree.body, "initialize_online_processing")
    require(scoped_call_count(f, "_wrap_parameters_weight_loader") >= 1,
            "layerwise wrapper not installed")
    require(scoped_call_count(find_func(layer_tree.body, "_layerwise_process"),
                              "materialize_layer") >= 1,
            "layerwise materialization missing")
    return {
        "loader_online_quant_finalize": "SOURCE_PRESENT",
        "layerwise_weight_loader_wrapper": "SOURCE_PRESENT",
        "layerwise_materialize_and_process": "SOURCE_PRESENT",
        "routed_quant_method_order": "SOURCE_PRESENT",
    }


def inspect(root: Path) -> dict[str, str]:
    texts: dict[str, str] = {}
    out: dict[str, str] = {}
    for key, relative in FILES.items():
        path = root / relative
        require(path.is_file(), f"missing exact installed source {path}")
        raw = path.read_bytes()
        texts[key] = raw.decode("utf-8", errors="strict")
        ast.parse(texts[key], filename=str(path))
        out[f"source_sha256_{key}"] = hashlib.sha256(raw).hexdigest()
    out.update(inspect_ct(texts["ct"]))
    out.update(inspect_lifecycle(texts))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = ap.parse_args()
    try:
        out = inspect(args.root)
    except (ValueError, SyntaxError, OSError, UnicodeError) as e:
        print(f"H38_CT_META_STATIC_PREREQUISITES=INVALID reason={e}", file=sys.stderr)
        return 2
    print("H38_CT_META_STATIC_PREREQUISITES=BEGIN")
    for key, value in out.items():
        print(f"{key}={value}")
    print("m1_modelopt_direct_patch_reusable=NO")
    print("h38_ct_meta_w13_patch_implemented=NO")
    print("checkpoint_loader_name_order_verified=NO")
    print("meta_w13_materialization_proven=NO")
    print("logical_rm_reduction_proven=NO")
    print("physical_memory_reduction_proven=NO")
    print("host_stability_qualified=NO")
    print("H38_CT_META_STATIC_PREREQUISITES=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
