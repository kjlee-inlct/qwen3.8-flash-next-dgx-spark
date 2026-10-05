#!/usr/bin/env python3
"""R27: add observational Qwen4Exp-layer and ModelOpt-W4A16 markers.

R26 showed that 99.276945% of the direct-RM order-4 episode is inside the
first top-level model constructor, but only 44.301511% of total activity is
inside ModelOptNvFp4FusedMoE.create_weights(). R27 partitions the remaining
constructor activity without changing model, quantization, allocator, PLE,
or runtime behavior.
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


def _self_assignment(node: ast.AST, name: str) -> bool:
    if not isinstance(node, ast.Assign) or len(node.targets) != 1:
        return False
    target = node.targets[0]
    return (
        isinstance(target, ast.Attribute)
        and isinstance(target.value, ast.Name)
        and target.value.id == "self"
        and target.attr == name
    )


def patch_modelopt(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "QWEN38_R27_W4A16_LINEAR_BEGIN" in text:
        raise SystemExit("R27 ModelOpt markers already present")
    tree = ast.parse(text)
    lines = text.splitlines()

    classes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "ModelOptNvFp4W4A16LinearMethod"
    ]
    if len(classes) != 1:
        raise SystemExit(
            "expected one ModelOptNvFp4W4A16LinearMethod class, "
            f"found {len(classes)}"
        )
    cls = classes[0]
    funcs = [
        node
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "create_weights"
    ]
    if len(funcs) != 1:
        raise SystemExit(f"expected one W4A16 create_weights(), found {len(funcs)}")
    func = funcs[0]

    body = list(func.body)
    if body and isinstance(body[0], ast.Expr):
        value = body[0].value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            body = body[1:]
    if not body:
        raise SystemExit("W4A16 create_weights() body is empty")

    output_size_assignments = [
        node
        for node in ast.walk(func)
        if _named_assignment(node, "output_size_per_partition")
    ]
    weight_assignments = [
        node for node in ast.walk(func) if _named_assignment(node, "weight")
    ]
    if len(output_size_assignments) != 1:
        raise SystemExit(
            "expected one output_size_per_partition assignment in W4A16 create_weights"
        )
    if len(weight_assignments) != 1:
        raise SystemExit("expected one weight assignment in W4A16 create_weights")

    logger_lines = [
        idx
        for idx, line in enumerate(lines, start=1)
        if line.strip() == "logger = init_logger(__name__)"
    ]
    if len(logger_lines) != 1:
        raise SystemExit(f"expected one module logger assignment, found {len(logger_lines)}")

    output_assign = output_size_assignments[0]
    weight_assign = weight_assignments[0]
    last_stmt = body[-1]
    func_indent = _indent_of(lines[output_assign.lineno - 1])
    weight_indent = _indent_of(lines[weight_assign.lineno - 1])

    before: dict[int, list[str]] = defaultdict(list)
    after: dict[int, list[str]] = defaultdict(list)
    after[logger_lines[0]].append("_QWEN38_R27_W4A16_LINEAR_SEQ = 0")

    after[output_assign.end_lineno or output_assign.lineno].extend(
        [
            func_indent + "global _QWEN38_R27_W4A16_LINEAR_SEQ",
            func_indent + "_QWEN38_R27_W4A16_LINEAR_SEQ += 1",
            func_indent + "_qwen38_r27_linear_seq = _QWEN38_R27_W4A16_LINEAR_SEQ",
            func_indent
            + 'logger.info("QWEN38_R27_W4A16_LINEAR_BEGIN seq=%d input=%d output=%d '
            + 'partitions=%d", _qwen38_r27_linear_seq, input_size_per_partition, '
            + 'output_size_per_partition, len(output_partition_sizes))',
        ]
    )
    after[last_stmt.end_lineno or last_stmt.lineno].append(
        func_indent
        + 'logger.info("QWEN38_R27_W4A16_LINEAR_END seq=%d", '
        + '_qwen38_r27_linear_seq)'
    )

    before[weight_assign.lineno].append(
        weight_indent
        + 'logger.info("QWEN38_R27_W4A16_WEIGHT_BEGIN seq=%d", '
        + '_qwen38_r27_linear_seq)'
    )
    after[weight_assign.end_lineno or weight_assign.lineno].append(
        weight_indent
        + 'logger.info("QWEN38_R27_W4A16_WEIGHT_END seq=%d", '
        + '_qwen38_r27_linear_seq)'
    )

    patched = _apply_insertions(text, before, after)
    ast.parse(patched)
    for marker in (
        "QWEN38_R27_W4A16_LINEAR_BEGIN",
        "QWEN38_R27_W4A16_LINEAR_END",
        "QWEN38_R27_W4A16_WEIGHT_BEGIN",
        "QWEN38_R27_W4A16_WEIGHT_END",
    ):
        if patched.count(marker) != 1:
            raise SystemExit(f"R27 ModelOpt marker count mismatch: {marker}")
    if patched.count("_QWEN38_R27_W4A16_LINEAR_SEQ = 0") != 1:
        raise SystemExit("R27 W4A16 sequence-counter contract mismatch")
    path.write_text(patched, encoding="utf-8")


def patch_qwen4_model(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "QWEN38_R27_QWEN4_LAYER_BEGIN" in text:
        raise SystemExit("R27 Qwen4Exp layer markers already present")

    import_anchor = "from vllm.distributed import get_pp_group\n"
    if import_anchor not in text:
        raise SystemExit("Qwen4Exp logger import anchor changed")
    if "from vllm.logger import init_logger\n" not in text:
        text = text.replace(
            import_anchor,
            import_anchor + "from vllm.logger import init_logger\n",
            1,
        )

    func_anchor = "\n\ndef without_modelopt_fp4(\n"
    if func_anchor not in text:
        raise SystemExit("Qwen4Exp without_modelopt_fp4 anchor changed")
    text = text.replace(
        func_anchor,
        "\n\nlogger = init_logger(__name__)\n"
        "_QWEN38_R27_QWEN4_LAYER_SEQ = 0\n"
        "\n\ndef without_modelopt_fp4(\n",
        1,
    )

    tree = ast.parse(text)
    lines = text.splitlines()
    classes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "Qwen4ExpDecoderLayer"
    ]
    if len(classes) != 1:
        raise SystemExit(f"expected one Qwen4ExpDecoderLayer, found {len(classes)}")
    cls = classes[0]
    funcs = [
        node
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "__init__"
    ]
    if len(funcs) != 1:
        raise SystemExit(f"expected one Qwen4ExpDecoderLayer.__init__, found {len(funcs)}")
    func = funcs[0]
    body = list(func.body)
    if not body:
        raise SystemExit("Qwen4ExpDecoderLayer.__init__ body is empty")

    layer_idx_assignments = [
        node for node in ast.walk(func) if _self_assignment(node, "layer_idx")
    ]
    if len(layer_idx_assignments) != 1:
        raise SystemExit(
            "expected one self.layer_idx assignment in Qwen4ExpDecoderLayer.__init__"
        )
    layer_idx_assign = layer_idx_assignments[0]
    last_stmt = body[-1]
    indent = _indent_of(lines[layer_idx_assign.lineno - 1])

    before: dict[int, list[str]] = defaultdict(list)
    after: dict[int, list[str]] = defaultdict(list)
    after[layer_idx_assign.end_lineno or layer_idx_assign.lineno].extend(
        [
            indent + "global _QWEN38_R27_QWEN4_LAYER_SEQ",
            indent + "_QWEN38_R27_QWEN4_LAYER_SEQ += 1",
            indent + "_qwen38_r27_layer_seq = _QWEN38_R27_QWEN4_LAYER_SEQ",
            indent
            + 'logger.info("QWEN38_R27_QWEN4_LAYER_BEGIN seq=%d layer=%d type=%s '
            + 'prefix=%s", _qwen38_r27_layer_seq, self.layer_idx, layer_type, prefix)',
        ]
    )
    after[last_stmt.end_lineno or last_stmt.lineno].append(
        indent
        + 'logger.info("QWEN38_R27_QWEN4_LAYER_END seq=%d layer=%d type=%s", '
        + '_qwen38_r27_layer_seq, self.layer_idx, layer_type)'
    )

    patched = _apply_insertions(text, before, after)
    ast.parse(patched)
    for marker in (
        "QWEN38_R27_QWEN4_LAYER_BEGIN",
        "QWEN38_R27_QWEN4_LAYER_END",
    ):
        if patched.count(marker) != 1:
            raise SystemExit(f"R27 Qwen4Exp marker count mismatch: {marker}")
    if patched.count("_QWEN38_R27_QWEN4_LAYER_SEQ = 0") != 1:
        raise SystemExit("R27 Qwen4Exp layer sequence-counter contract mismatch")
    if patched.count("logger = init_logger(__name__)") != 1:
        raise SystemExit("R27 Qwen4Exp logger contract mismatch")
    path.write_text(patched, encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: patch-v029-r27-linear-boundary-markers.py "
            "<modelopt.py> <qwen4_exp/nvidia/model.py>"
        )
    modelopt = Path(sys.argv[1])
    qwen4_model = Path(sys.argv[2])
    patch_modelopt(modelopt)
    patch_qwen4_model(qwen4_model)
    print("installed R27 W4A16-linear and Qwen4Exp-layer timing markers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
