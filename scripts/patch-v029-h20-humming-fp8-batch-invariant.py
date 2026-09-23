#!/usr/bin/env python3
"""Patch vLLM v0.29 Humming FP8 linear compute config for H20 v15."""

from __future__ import annotations

import sys
from pathlib import Path

if len(sys.argv) != 2:
    raise SystemExit(
        "usage: patch-v029-h20-humming-fp8-batch-invariant.py "
        "<vllm/model_executor/kernels/linear/scaled_mm/humming.py>"
    )

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

anchor = """        self.layer_config = prepare_humming_linear_layer_config(layer, quant_config)
        self.compute_config = get_humming_linear_compute_config()
        self.locks = torch.zeros(1024, dtype=torch.int32, device=layer.weight.device)
"""
replacement = """        self.layer_config = prepare_humming_linear_layer_config(layer, quant_config)
        self.compute_config = get_humming_linear_compute_config()
        import json as _qwen38_h20_json

        _qwen38_h20_compute = _qwen38_h20_json.loads(self.compute_config)
        _qwen38_h20_compute["use_batch_invariant"] = True
        self.compute_config = _qwen38_h20_json.dumps(_qwen38_h20_compute)
        logger.warning(
            "QWEN38_H20Q_FP8_BATCH_INVARIANT compute_config=%s",
            self.compute_config,
        )
        self.locks = torch.zeros(1024, dtype=torch.int32, device=layer.weight.device)
"""

# Only the FP8 class should be changed. The file also contains an Int8 class
# with the same three-line initialization sequence.
class_start = text.index("class HummingFP8ScaledMMLinearKernel")
class_end = text.index("class HummingInt8ScaledMMLinearKernel")
prefix = text[:class_start]
body = text[class_start:class_end]
suffix = text[class_end:]

if body.count(anchor) != 1:
    raise SystemExit("expected FP8 Humming compute-config anchor exactly once")
body = body.replace(anchor, replacement, 1)

text = prefix + body + suffix
path.write_text(text, encoding="utf-8")
print("installed H20 local batch-invariant control for Humming FP8 linear")
