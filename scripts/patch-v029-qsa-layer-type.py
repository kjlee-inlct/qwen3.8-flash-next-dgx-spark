#!/usr/bin/env python3
"""Backport qwen_sparse_attention layer-type compatibility to vLLM v0.29.

vLLM v0.29's Qwen4Exp decoder accepts only "linear_attention" and
"full_attention". Newer Qwen3.8/Qwen4Exp checkpoints may emit the explicit
"qwen_sparse_attention" layer type. Current vLLM treats that value as an
attention layer and forces QSA for it.

This patch mirrors that narrow behavior without otherwise changing v0.29.
"""

from __future__ import annotations

import pathlib
import sys


INIT_OLD = '''        elif layer_type == "full_attention":
            use_qsa = getattr(config, "indexer_n_heads", None) is not None
'''
INIT_NEW = '''        elif layer_type in ("full_attention", "qwen_sparse_attention"):
            use_qsa = (
                layer_type == "qwen_sparse_attention"
                or getattr(config, "indexer_n_heads", None) is not None
            )
'''

FORWARD_OLD = '''        elif self.layer_type == "full_attention":
            attn_out = self.self_attn(
'''
FORWARD_NEW = '''        elif self.layer_type in ("full_attention", "qwen_sparse_attention"):
            attn_out = self.self_attn(
'''


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} MODEL_PY", file=sys.stderr)
        return 2

    path = pathlib.Path(sys.argv[1])
    text = path.read_text(encoding="utf-8")

    init_done = INIT_NEW in text
    forward_done = FORWARD_NEW in text
    if init_done and forward_done:
        print(f"already patched: {path}")
        return 0
    if not init_done and INIT_OLD not in text:
        print(f"expected v0.29 decoder init block not found: {path}", file=sys.stderr)
        return 1
    if not forward_done and FORWARD_OLD not in text:
        print(f"expected v0.29 decoder forward block not found: {path}", file=sys.stderr)
        return 1

    if not init_done:
        text = text.replace(INIT_OLD, INIT_NEW, 1)
    if not forward_done:
        text = text.replace(FORWARD_OLD, FORWARD_NEW, 1)
    path.write_text(text, encoding="utf-8")
    print(f"patched qwen_sparse_attention init+forward compatibility: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
