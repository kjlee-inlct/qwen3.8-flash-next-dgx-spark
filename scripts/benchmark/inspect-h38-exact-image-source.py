#!/usr/bin/env python3
"""Inspect H38 *installed image* vLLM source without importing vLLM/torch/CUDA.

Only static AST/source semantics are tested. R32 is executed as a separate
source-only process on the same image, and its original R28 causal scope is
preserved. No reduction in NVIDIA RM allocation is inferred.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import pathlib
import subprocess
import sys

SP = pathlib.Path("/usr/local/lib/python3.12/dist-packages")
SOURCE = {
    "ct": "vllm/model_executor/layers/quantization/compressed_tensors/"
          "compressed_tensors_moe/compressed_tensors_moe_w4a4_nvfp4.py",
    "humming": "vllm/model_executor/kernels/linear/scaled_mm/humming.py",
    "marlin": "vllm/model_executor/layers/fused_moe/experts/marlin_moe.py",
}
H11 = "ModelWeightParameter"
EXPECTED_R32 = "direct_precreate_tensor_alloc_syntax=ABSENT"


def require(ok: bool, detail: str) -> None:
    if not ok:
        raise ValueError(detail)


def call_name(node: ast.AST) -> str:
    names: list[str] = []
    while isinstance(node, ast.Attribute):
        names.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        names.append(node.id)
        return ".".join(reversed(names))
    return ""


def selected_class(tree: ast.Module, name: str) -> ast.ClassDef:
    found = [x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == name]
    require(len(found) == 1, f"expected one class {name}: found {len(found)}")
    return found[0]


def selected_method(cls: ast.ClassDef, name: str) -> ast.FunctionDef:
    found = [x for x in cls.body if isinstance(x, ast.FunctionDef) and x.name == name]
    require(len(found) == 1, f"expected one {cls.name}.{name}: found {len(found)}")
    return found[0]


def assigned_call(func: ast.FunctionDef, name: str) -> ast.Call:
    rows: list[ast.Call] = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        if any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            rows.append(node.value)
    require(len(rows) == 1, f"expected one {name} assignment in create_weights: found {len(rows)}")
    return rows[0]


def kwarg(call: ast.Call, name: str) -> ast.AST | None:
    return next((k.value for k in call.keywords if k.arg == name), None)


def register_calls(cls: ast.ClassDef, parameter: str, value: str) -> list[int]:
    found: list[int] = []
    for method in cls.body:
        if not isinstance(method, ast.FunctionDef):
            continue
        for node in ast.walk(method):
            if not isinstance(node, ast.Call) or call_name(node.func) != "layer.register_parameter":
                continue
            if len(node.args) != 2:
                continue
            key, val = node.args
            if (isinstance(key, ast.Constant) and key.value == parameter
                    and call_name(val) == value):
                found.append(node.lineno)
    return found


def inspect_ct(source: str) -> dict[str, str]:
    tree = ast.parse(source)
    cls = selected_class(tree, "CompressedTensorsW4A4Nvfp4MoEMethod")
    method = selected_method(cls, "create_weights")
    for name in ("w13_weight", "w2_weight"):
        call = assigned_call(method, name)
        require(call_name(call.func) == H11, f"{name} is not H11 ModelWeightParameter")
        tensor = kwarg(call, "data")
        require(isinstance(tensor, ast.Call) and call_name(tensor.func) == "torch.empty",
                f"{name} no longer contains torch.empty allocation")
        for attr in ("input_dim", "output_dim", "weight_loader"):
            require(kwarg(call, attr) is not None, f"{name} missing H11 {attr}")
        packed = name + "_packed"
        require(len(register_calls(cls, packed, name)) == 1,
                f"{name} packed registration differs from H11")
        require(len(register_calls(cls, name, "layer." + packed)) == 1,
                f"{name} post-load alias differs from H12")
        require(f"layer.{name} = torch.nn.Parameter(" not in source,
                f"{name} post-load rewrapping still present")
    require("_qwen38_marlin_layer_idx" in source,
            "H38 decoder layer tag missing from CT source")
    return {
        "h11_packed_weights": "PASS",
        "h11_tensor_allocations_retained": "YES",
        "h12_postload_object_alias": "PASS",
        "h38_ct_marlin_layer_tag": "PASS",
    }


def inspect_humming(source: str) -> dict[str, str]:
    tree = ast.parse(source)
    cls = selected_class(tree, "HummingFP8ScaledMMLinearKernel")
    require('''_qwen38_h20_compute["use_batch_invariant"] = True''' in ast.get_source_segment(
        source, cls
    ), "H38 FP8 batch-invariant source control missing")
    return {"h38_humming_fp8_control": "PASS"}


def inspect_marlin(source: str) -> dict[str, str]:
    tree = ast.parse(source)
    funcs = [f for f in tree.body if isinstance(f, ast.FunctionDef) and
             f.name == "_qwen38_canonicalize_marlin_sorted_tokens"]
    require(len(funcs) == 1, "H38 Marlin canonical helper absent/nonunique")
    require("torch.argsort(key, stable=True)" in ast.get_source_segment(source, funcs[0]),
            "H38 Marlin stable argsort missing")
    cls = selected_class(tree, "MarlinExperts")
    body = ast.get_source_segment(source, cls)
    require('getattr(self, "_qwen38_marlin_layer_idx", -1)' in body,
            "H38 Marlin decoder-tag guard missing")
    return {"h38_marlin_canonical_scoped": "PASS"}


def inspect_installed(root: pathlib.Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for label, relative in SOURCE.items():
        path = root / relative
        require(path.is_file(), f"missing installed source {path}")
        binary = path.read_bytes()
        text = binary.decode("utf-8")
        ast.parse(text, filename=str(path))
        result[f"sha256_{label}"] = hashlib.sha256(binary).hexdigest()
        if label == "ct":
            result.update(inspect_ct(text))
        elif label == "humming":
            result.update(inspect_humming(text))
        elif label == "marlin":
            result.update(inspect_marlin(text))
    return result


def run_r32(root: pathlib.Path, script: pathlib.Path) -> str:
    require(script.is_file(), f"R32 checker missing: {script}")
    proc = subprocess.run(
        [sys.executable, "-B", str(script), "--root", str(root)],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        check=False, timeout=30,
    )
    require(proc.returncode == 0, f"R32 checker rejected H38 image source: {proc.stderr.strip()}")
    require("R32_PRECREATE_SOURCE_CONTRACT=BEGIN" in proc.stdout
            and EXPECTED_R32 in proc.stdout
            and "R32_PRECREATE_SOURCE_CONTRACT=END" in proc.stdout,
            "R32 checker output incomplete or negative")
    return proc.stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=pathlib.Path, default=SP)
    parser.add_argument("--r32-script", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        result = inspect_installed(args.root)
        r32_output = run_r32(args.root, args.r32_script)
    except (ValueError, SyntaxError, OSError, subprocess.SubprocessError) as exc:
        print(f"H38_EXACT_IMAGE_SOURCE_CONTRACT=INVALID reason={exc}", file=sys.stderr)
        return 2

    print("H38_EXACT_IMAGE_SOURCE_CONTRACT=BEGIN")
    print("semantics=cpu_only_installed_source_syntax_no_gpu_no_model_load")
    for key, value in result.items():
        print(f"{key}={value}")
    print("r32_reuse_scope=THIS_IMAGE_SOURCE_ONLY_NOT_R28_RUNTIME_EVENT_TRANSFER")
    print(r32_output.rstrip())
    print("rm_oom_qualified=NO")
    print("allocator_mitigation_proven=NO")
    print("exact_original_cuda_caller_identified=NO")
    print("H38_EXACT_IMAGE_SOURCE_CONTRACT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
