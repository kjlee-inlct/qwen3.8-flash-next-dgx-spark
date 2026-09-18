# Benchmark compatibility paths

The canonical benchmark harness moved to `scripts/benchmark/`.

Use:

```bash
python3 scripts/benchmark/run.py qualification
python3 scripts/benchmark/run.py all
```

The top-level `bench/run.py` and `bench/common.py` files are thin compatibility shims for older commands and imports. New documentation, tests, and automation should use `scripts/benchmark/` directly.

The upstream-derived `scripts/bench-prefill.py` remains at its original path.
