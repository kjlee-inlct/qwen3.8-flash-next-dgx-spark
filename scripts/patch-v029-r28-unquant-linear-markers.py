#!/usr/bin/env python3
"""R28: add observational markers to UnquantizedLinearMethod.create_weights().

The patch changes logging only. It does not alter tensor shapes, dtypes,
parameter classes, allocation APIs, quantization routing, or runtime behavior.
"""

from __future__ import annotations

import ast
import sys
from collections import defaultdict
from pathlib import Path


BEGIN = "QWEN38_R28_UNQUANT_LINEAR_BEGIN"
END = "QWEN38_R28_UNQUANT_LINEAR_END"
COUNTER = "_QWEN38_R28_UNQUANT_LINEAR_SEQ"


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


def _is_weight_assignment(node: ast.AST) -> bool:
    if not isinstance(node, ast.Assign) or len(node.targets) != 1:
        return False
    target = node.targets[0]
    return isinstance(target, ast.Name) and target.id == "weight"


def _is_set_weight_attrs(node: ast.AST) -> bool:
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return False
    call = node.value
    return (
        isinstance(call.func, ast.Name)
        and call.func.id == "set_weight_attrs"
        and bool(call.args)
        and isinstance(call.args[0], ast.Name)
        and call.args[0].id == "weight"
    )


def patch(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if BEGIN in text or END in text:
        raise SystemExit("R28 unquantized-linear markers already present")

    tree = ast.parse(text)
    lines = text.splitlines()

    classes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "UnquantizedLinearMethod"
    ]
    if len(classes) != 1:
        raise SystemExit(
            f"expected one UnquantizedLinearMethod class, found {len(classes)}"
        )
    cls = classes[0]
    funcs = [
        node
        for node in cls.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "create_weights"
    ]
    if len(funcs) != 1:
        raise SystemExit(
            f"expected one UnquantizedLinearMethod.create_weights, found {len(funcs)}"
        )
    func = funcs[0]

    weight_assignments = [node for node in ast.walk(func) if _is_weight_assignment(node)]
    set_attrs = [node for node in ast.walk(func) if _is_set_weight_attrs(node)]
    if len(weight_assignments) != 1:
        raise SystemExit(
            f"expected one unquantized weight assignment, found {len(weight_assignments)}"
        )
    if len(set_attrs) != 1:
        raise SystemExit(
            f"expected one unquantized set_weight_attrs call, found {len(set_attrs)}"
        )

    logger_lines = [
        idx
        for idx, line in enumerate(lines, start=1)
        if line.strip() == "logger = init_logger(__name__)"
    ]
    if len(logger_lines) != 1:
        raise SystemExit(f"expected one module logger assignment, found {len(logger_lines)}")

    weight = weight_assignments[0]
    attrs = set_attrs[0]
    indent = _indent_of(lines[weight.lineno - 1])

    before: dict[int, list[str]] = defaultdict(list)
    after: dict[int, list[str]] = defaultdict(list)
    after[logger_lines[0]].append(f"{COUNTER} = 0")

    before[weight.lineno].extend(
        [
            indent + f"global {COUNTER}",
            indent + f"{COUNTER} += 1",
            indent + f"_qwen38_r28_seq = {COUNTER}",
            indent + '_qwen38_r28_prefix = getattr(layer, "prefix", "") or "<empty>"',
            indent + "_qwen38_r28_elements = sum(output_partition_sizes) * input_size_per_partition",
            indent
            + 'logger.info("QWEN38_R28_UNQUANT_LINEAR_BEGIN seq=%d prefix=%s layer=%s '
            + 'input=%d output=%d elements=%d dtype=%s", _qwen38_r28_seq, '
            + '_qwen38_r28_prefix, type(layer).__name__, input_size_per_partition, '
            + 'sum(output_partition_sizes), _qwen38_r28_elements, str(params_dtype))',
        ]
    )
    after[attrs.end_lineno or attrs.lineno].append(
        indent
        + 'logger.info("QWEN38_R28_UNQUANT_LINEAR_END seq=%d", _qwen38_r28_seq)'
    )

    patched = _apply_insertions(text, before, after)
    ast.parse(patched)
    if patched.count(BEGIN) != 1 or patched.count(END) != 1:
        raise SystemExit("R28 marker count mismatch")
    if patched.count(f"{COUNTER} = 0") != 1:
        raise SystemExit("R28 sequence-counter contract mismatch")
    if "data=torch.empty(" not in patched:
        raise SystemExit("unquantized torch.empty allocation contract changed")

    path.write_text(patched, encoding="utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(
            "usage: patch-v029-r28-unquant-linear-markers.py <linear.py>"
        )
    patch(Path(sys.argv[1]))
    print("installed R28 UnquantizedLinearMethod timing markers")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
