#!/usr/bin/env python3
"""Patch vLLM v0.29 ModelOpt NVFP4 MoE to defer only w13 allocation.

M1 is intentionally narrow:
- w13_weight is created on the meta device instead of the current default CUDA device;
- w2 and all scale tensors keep their original construction behavior;
- vLLM's native layerwise online-processing machinery materializes w13 during
  first weight loading and then runs the original ModelOpt post-load path.

This script is an exact-source diagnostic/mitigation patch, not a general
upstream-compatible transformer.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path


IMPORT_ANCHOR = (
    "from vllm.model_executor.layers.quantization import QuantizationMethods\n"
)
IMPORT_TEXT = (
    "from vllm.model_executor.model_loader.reload.layerwise import (\n"
    "    initialize_online_processing,\n"
    ")\n"
)
CLASS_START = "class ModelOptNvFp4FusedMoE(FusedMoEMethodBase):\n"
CLASS_END = "\n\nModelOptNvFp4Config.LinearMethodCls = ModelOptNvFp4LinearMethod\n"
INIT_ANCHOR = "    def __init__(\n"
W13_START = "        # GEMM 1\n"
W13_END = '        layer.register_parameter("w13_weight", w13_weight)\n'
W2_START = "        # GEMM 2\n"
W2_END = '        layer.register_parameter("w2_weight", w2_weight)\n'
FINAL_REGISTRATION = (
    '        layer.register_parameter("w2_input_scale", w2_input_scale)\n'
)
PROCESS_ANCHOR = "\n    def process_weights_after_loading(self, layer: RoutedExperts) -> None:\n"
PATCH_MARKER = "QWEN38_M1_DEFERRED_META_W13_V1"


def fail(message: str) -> None:
    raise SystemExit(f"M1 patch refused: {message}")


def slice_once(text: str, start: str, end: str, label: str) -> tuple[int, int, str]:
    if text.count(start) != 1:
        fail(f"{label} start count={text.count(start)}")
    start_idx = text.index(start)
    end_idx = text.find(end, start_idx)
    if end_idx < 0:
        fail(f"{label} end missing")
    return start_idx, end_idx, text[start_idx:end_idx]


def patch_source(source: str) -> str:
    ast.parse(source)
    if PATCH_MARKER in source:
        fail("source already patched")

    if source.count(IMPORT_ANCHOR) != 1:
        fail("quantization import anchor mismatch")
    if "initialize_online_processing" in source:
        fail("unexpected pre-existing initialize_online_processing reference")

    class_start, class_end, class_block = slice_once(
        source, CLASS_START, CLASS_END, "ModelOptNvFp4FusedMoE"
    )

    if class_block.count(INIT_ANCHOR) != 1:
        fail("__init__ anchor mismatch")
    class_block = class_block.replace(
        INIT_ANCHOR,
        (
            f"    # {PATCH_MARKER}\n"
            "    # M1 defers only packed w13 storage; w2/scales stay unchanged.\n"
            "    uses_meta_device = True\n\n"
            + INIT_ANCHOR
        ),
        1,
    )

    w13_start, w13_end, w13_block = slice_once(
        class_block, W13_START, W13_END, "w13"
    )
    if w13_block.count("data=torch.empty(") != 1:
        fail("w13 torch.empty count mismatch")
    if 'device="meta"' in w13_block:
        fail("w13 already uses meta")
    if w13_block.count("dtype=weight_dtype,\n") != 1:
        fail("w13 dtype anchor mismatch")
    patched_w13 = w13_block.replace(
        "                dtype=weight_dtype,\n",
        "                dtype=weight_dtype,\n                device=\"meta\",\n",
        1,
    )
    class_block = class_block[:w13_start] + patched_w13 + class_block[w13_end:]

    _, _, w2_block = slice_once(class_block, W2_START, W2_END, "w2")
    if w2_block.count("data=torch.empty(") != 1:
        fail("w2 torch.empty count mismatch")
    if 'device="meta"' in w2_block:
        fail("w2 must remain on the original construction device")

    if class_block.count(FINAL_REGISTRATION) != 1:
        fail("final registration anchor mismatch")
    if class_block.count(PROCESS_ANCHOR) != 1:
        fail("process_weights_after_loading anchor mismatch")
    class_block = class_block.replace(
        FINAL_REGISTRATION + PROCESS_ANCHOR,
        (
            FINAL_REGISTRATION
            + "\n"
            + "        # Native vLLM first-load layerwise materialization.\n"
            + "        initialize_online_processing(layer)\n"
            + PROCESS_ANCHOR
        ),
        1,
    )

    # Replace the class before inserting the new import. Inserting the import first
    # would shift class_start/class_end and corrupt the exact-source splice.
    source = source[:class_start] + class_block + source[class_end:]
    source = source.replace(IMPORT_ANCHOR, IMPORT_ANCHOR + IMPORT_TEXT, 1)
    ast.parse(source)
    return source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    source = args.path.read_text(encoding="utf-8")
    patched = patch_source(source)
    args.path.write_text(patched, encoding="utf-8")
    print(f"M1_PATCH=PASS path={args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
