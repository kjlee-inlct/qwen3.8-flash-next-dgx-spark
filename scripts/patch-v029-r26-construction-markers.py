#!/usr/bin/env python3
"""R26: add observational construction markers to vLLM v0.29.

This patch does not change model or quantization behavior. It adds INFO markers
around the top-level model constructor and ModelOpt NVFP4 MoE weight creation,
including the large w13/w2 packed storage allocations.
"""

from __future__ import annotations

import ast
import sys
from collections import defaultdict
from pathlib import Path


def _indent_of(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def _apply_insertions(
    text: str,
    before: dict[int, list[str]],
    after: dict[int, list[str]],
) -> str:
    lines = text.splitlines()
    out: list[str] = []
    for lineno, line in enumerate(lines, start=1):
        out.extend(before.get(lineno, []))
        out.append(line)
        out.extend(after.get(lineno, []))
    return "\n".join(out) + "\n"


def _named_assignment(node: ast.AST, name: str) -> bool:
    if not isinstance(node, ast.Assign) or len(node.targets) != 1:
        return False
    target = node.targets[0]
    return isinstance(target, ast.Name) and target.id == name


def patch_loader_utils(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    lines = text.splitlines()

    funcs = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "initialize_model"
    ]
    if len(funcs) != 1:
        raise SystemExit(f"expected one initialize_model(), found {len(funcs)}")
    func = funcs[0]

    ctor_assignments: list[ast.Assign] = []
    for node in ast.walk(func):
        if not _named_assignment(node, "model"):
            continue
        call = node.value
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
            continue
        if call.func.id != "model_class":
            continue
        keywords = {kw.arg for kw in call.keywords if kw.arg is not None}
        if {"vllm_config", "prefix"}.issubset(keywords):
            ctor_assignments.append(node)

    if len(ctor_assignments) != 1:
        raise SystemExit(
            "expected exactly one new-style model_class constructor assignment, "
            f"found {len(ctor_assignments)}"
        )

    ctor = ctor_assignments[0]
    indent = _indent_of(lines[ctor.lineno - 1])
    before: dict[int, list[str]] = defaultdict(list)
    after: dict[int, list[str]] = defaultdict(list)
    before[ctor.lineno].append(
        indent
        + 'logger.info("QWEN38_R26_MODEL_CTOR_BEGIN class=%s prefix=%s", '
        + 'model_class.__name__, prefix)'
    )
    after[ctor.end_lineno or ctor.lineno].append(
        indent
        + 'logger.info("QWEN38_R26_MODEL_CTOR_END class=%s prefix=%s", '
        + 'model_class.__name__, prefix)'
    )

    patched = _apply_insertions(text, before, after)
    ast.parse(patched)
    if patched.count("QWEN38_R26_MODEL_CTOR_BEGIN") != 1:
        raise SystemExit("model constructor begin marker count mismatch")
    if patched.count("QWEN38_R26_MODEL_CTOR_END") != 1:
        raise SystemExit("model constructor end marker count mismatch")
    path.write_text(patched, encoding="utf-8")


def patch_modelopt(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    lines = text.splitlines()

    classes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ModelOptNvFp4FusedMoE"
    ]
    if len(classes) != 1:
        raise SystemExit(
            f"expected one ModelOptNvFp4FusedMoE class, found {len(classes)}"
        )
    cls = classes[0]
    funcs = [
        node
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "create_weights"
    ]
    if len(funcs) != 1:
        raise SystemExit(f"expected one create_weights(), found {len(funcs)}")
    func = funcs[0]

    body = list(func.body)
    if body and isinstance(body[0], ast.Expr):
        value = body[0].value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            body = body[1:]
    if not body:
        raise SystemExit("ModelOptNvFp4FusedMoE.create_weights() body is empty")

    w13 = [node for node in ast.walk(func) if _named_assignment(node, "w13_weight")]
    w2 = [node for node in ast.walk(func) if _named_assignment(node, "w2_weight")]
    if len(w13) != 1 or len(w2) != 1:
        raise SystemExit(
            "expected exactly one w13_weight and one w2_weight assignment in "
            f"ModelOptNvFp4FusedMoE.create_weights(); got {len(w13)}, {len(w2)}"
        )

    logger_lines = [
        idx
        for idx, line in enumerate(lines, start=1)
        if line.strip() == "logger = init_logger(__name__)"
    ]
    if len(logger_lines) != 1:
        raise SystemExit(f"expected one module logger assignment, found {len(logger_lines)}")

    first_stmt = body[0]
    last_stmt = body[-1]
    func_indent = _indent_of(lines[first_stmt.lineno - 1])
    w13_indent = _indent_of(lines[w13[0].lineno - 1])
    w2_indent = _indent_of(lines[w2[0].lineno - 1])

    before: dict[int, list[str]] = defaultdict(list)
    after: dict[int, list[str]] = defaultdict(list)

    after[logger_lines[0]].append("_QWEN38_R26_MODELOPT_MOE_SEQ = 0")

    before[first_stmt.lineno].extend(
        [
            func_indent + "global _QWEN38_R26_MODELOPT_MOE_SEQ",
            func_indent + "_QWEN38_R26_MODELOPT_MOE_SEQ += 1",
            func_indent + "_qwen38_r26_seq = _QWEN38_R26_MODELOPT_MOE_SEQ",
            func_indent
            + 'logger.info("QWEN38_R26_MODELOPT_MOE_BEGIN seq=%d experts=%d hidden=%d '
            + 'intermediate=%d", _qwen38_r26_seq, num_experts, hidden_size, '
            + 'intermediate_size_per_partition)',
        ]
    )
    after[last_stmt.end_lineno or last_stmt.lineno].append(
        func_indent
        + 'logger.info("QWEN38_R26_MODELOPT_MOE_END seq=%d", _qwen38_r26_seq)'
    )

    before[w13[0].lineno].append(
        w13_indent
        + 'logger.info("QWEN38_R26_MODELOPT_W13_BEGIN seq=%d", _qwen38_r26_seq)'
    )
    after[w13[0].end_lineno or w13[0].lineno].append(
        w13_indent
        + 'logger.info("QWEN38_R26_MODELOPT_W13_END seq=%d", _qwen38_r26_seq)'
    )
    before[w2[0].lineno].append(
        w2_indent
        + 'logger.info("QWEN38_R26_MODELOPT_W2_BEGIN seq=%d", _qwen38_r26_seq)'
    )
    after[w2[0].end_lineno or w2[0].lineno].append(
        w2_indent
        + 'logger.info("QWEN38_R26_MODELOPT_W2_END seq=%d", _qwen38_r26_seq)'
    )

    patched = _apply_insertions(text, before, after)
    ast.parse(patched)
    expected = (
        "QWEN38_R26_MODELOPT_MOE_BEGIN",
        "QWEN38_R26_MODELOPT_MOE_END",
        "QWEN38_R26_MODELOPT_W13_BEGIN",
        "QWEN38_R26_MODELOPT_W13_END",
        "QWEN38_R26_MODELOPT_W2_BEGIN",
        "QWEN38_R26_MODELOPT_W2_END",
    )
    for marker in expected:
        if patched.count(marker) != 1:
            raise SystemExit(f"marker count mismatch for {marker}")
    if patched.count("_QWEN38_R26_MODELOPT_MOE_SEQ = 0") != 1:
        raise SystemExit("ModelOpt marker sequence counter contract mismatch")
    path.write_text(patched, encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: patch-v029-r26-construction-markers.py <model_loader_utils.py> "
            "<modelopt.py>"
        )
    loader_utils = Path(sys.argv[1])
    modelopt = Path(sys.argv[2])
    patch_loader_utils(loader_utils)
    patch_modelopt(modelopt)
    print("installed R26 constructor and ModelOpt MoE timing markers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
