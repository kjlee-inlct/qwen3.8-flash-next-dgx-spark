#!/usr/bin/env python3
"""Patch vLLM v0.29 compressed-tensors NVFP4 MoE scale metadata GROUP -> BLOCK.

Only CompressedTensorsW4A4Nvfp4MoEMethod.create_weights() is changed.
Tensor shapes, checkpoint values, quantization config, activation mode, and
kernel-selection logic stay untouched.
"""

from __future__ import annotations

import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
start = text.index("class CompressedTensorsW4A4Nvfp4MoEMethod")
body = text[start:]
needle = '{"quant_method": FusedMoeWeightScaleSupported.GROUP.value}'
replacement = '{"quant_method": FusedMoeWeightScaleSupported.BLOCK.value}'
count = body.count(needle)
if count != 2:
    raise SystemExit(
        f"expected exactly two compressed-tensors NVFP4 MoE GROUP metadata assignments, found {count}"
    )
body = body.replace(needle, replacement)
path.write_text(text[:start] + body, encoding="utf-8")
print("patched compressed-tensors NVFP4 MoE weight_scale metadata: GROUP -> BLOCK (w13+w2)")
