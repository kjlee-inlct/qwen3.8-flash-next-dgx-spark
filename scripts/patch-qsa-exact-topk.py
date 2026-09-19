#!/usr/bin/env python3
"""Add an opt-in exact QSA top-k path for Qwen3.8 Flash Next on GB10.

Adapted from blazux/qwen3.8-Flash-DGX src/patch_qsa_exact_topk.py.
The patch keeps the default path unchanged and activates only when
VLLM_QSA_EXACT_TOPK=1.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

target = Path(sys.argv[1])
src = target.read_text(encoding="utf-8")
call = "        topk_op(logits, visible_blocks, blocks, topk_workspace, block_topk, columns)\n"
if src.count(call) != 1:
    raise SystemExit(f"exact-topk patch anchor count={src.count(call)}; expected 1")

src = src.replace(
    call,
    '        if _QSA_TOPK_MODE == "1":\n'
    '            _qsa_exact_topk(logits, visible_blocks, blocks, block_topk, columns)\n'
    '        else:\n'
    '            topk_op(logits, visible_blocks, blocks, topk_workspace, block_topk, columns)\n',
    1,
)

if "import os\n" not in src:
    src = src.replace("import math\n", "import math\nimport os\n", 1)

src += r'''

# --- local opt-in exact QSA top-k for GB10 determinism ---
_QSA_TOPK_MODE = os.environ.get("VLLM_QSA_EXACT_TOPK", "0").lower()
if _QSA_TOPK_MODE in ("true", "yes"):
    _QSA_TOPK_MODE = "1"
_QSA_COLS_CACHE: dict = {}


def _qsa_cols(columns: int, device) -> torch.Tensor:
    key = (columns, device)
    value = _QSA_COLS_CACHE.get(key)
    if value is None:
        value = torch.arange(columns, device=device, dtype=torch.int32)
        _QSA_COLS_CACHE[key] = value
    return value


def _qsa_mask_invisible_(logits, visible_blocks, columns):
    cols = _qsa_cols(columns, logits.device)
    logits[:, :columns].masked_fill_(
        cols[None, :] >= visible_blocks[:, None],
        float("-inf"),
    )


def _qsa_exact_topk(logits, visible_blocks, blocks, block_topk, columns):
    _qsa_mask_invisible_(logits, visible_blocks, columns)
    k = min(block_topk, columns)
    idx = torch.topk(logits[:, :columns], k, dim=1, sorted=False).indices
    if k < block_topk:
        blocks[:, :k].copy_(idx)
        blocks[:, k:].fill_(-1)
    else:
        blocks.copy_(idx)
'''

ast.parse(src)
target.write_text(src, encoding="utf-8")
print("qsa.py: exact top-k path added")
