#!/usr/bin/env python3
"""Add R25 timing markers around vLLM initialize_model().

This patch is observational only. It does not change model construction,
weight loading, post-load processing, allocator behavior, or runtime flags.
The markers are used to align the already-closed NVIDIA RM order-4 episode
with the exact BaseModelLoader.initialize_model() boundary.
"""

from __future__ import annotations

import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")

needle = '''        with set_default_torch_dtype(model_config.dtype):
            with target_device:
                model = initialize_model(
                    vllm_config=vllm_config,
                    model_config=model_config,
                    prefix=prefix,
                )

            log_model_inspection(model)
'''

replacement = '''        with set_default_torch_dtype(model_config.dtype):
            logger.info("QWEN38_R25_INIT_MODEL_BEGIN")
            with target_device:
                model = initialize_model(
                    vllm_config=vllm_config,
                    model_config=model_config,
                    prefix=prefix,
                )
            logger.info("QWEN38_R25_INIT_MODEL_END")

            log_model_inspection(model)
'''

if text.count(needle) != 1:
    raise SystemExit("expected BaseModelLoader initialize_model block not found exactly once")

text = text.replace(needle, replacement, 1)
path.write_text(text, encoding="utf-8")
print("installed R25 initialize_model timing markers")
