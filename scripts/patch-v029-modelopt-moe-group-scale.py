#!/usr/bin/env python3
"""Patch vLLM v0.29 ModelOpt NVFP4 MoE weight-scale metadata BLOCK -> GROUP.

This patch is intentionally narrow: only ModelOptNvFp4FusedMoE.create_weights()
is modified. Tensor shapes, checkpoint values, quant_algo, activation mode, and
kernel selection logic are unchanged.
"""

from __future__ import annotations

import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
start = text.index("class ModelOptNvFp4FusedMoE")
end = text.index("\nclass ", start + 1)
head, body, tail = text[:start], text[start:end], text[end:]
needle = '{"quant_method": FusedMoeWeightScaleSupported.BLOCK.value}'
replacement = '{"quant_method": FusedMoeWeightScaleSupported.GROUP.value}'
count = body.count(needle)
if count != 1:
    raise SystemExit(f"expected exactly one ModelOpt NVFP4 MoE BLOCK metadata assignment, found {count}")
body = body.replace(needle, replacement, 1)
patched = head + body + tail
path.write_text(patched, encoding="utf-8")
print("patched ModelOptNvFp4FusedMoE weight_scale metadata: BLOCK -> GROUP")
