# Benchmark harness

This directory contains the repository's canonical read-only benchmark harness for the managed Qwen3.8 Flash Next runtime.

## Layout

- `run.py`: canonical benchmark CLI.
- `lib/common.py`: canonical shared implementation helpers.
- `common.py`: local compatibility import used by the CLI and older imports.
- `results/local/`: ignored local benchmark output.

The upstream-derived `scripts/bench-prefill.py` intentionally remains at its upstream path. It is a compatibility/reference benchmark, while `scripts/benchmark/run.py` is the benchmark entry point maintained by this fork.

The top-level `bench/run.py` path is retained only as a compatibility shim. New documentation, automation, and internal references should use `scripts/benchmark/run.py`.

## Safety rules

- The HTTP target must be credential-free loopback HTTP (`127.0.0.1`, `localhost`, or `::1`) with an explicit port.
- Proxy environment variables are ignored and redirects are rejected.
- Generated model text is never written to reports.
- The runner does not restart containers, clear caches, change sysctls, or modify model files.
- Run benchmarks only while the host is otherwise idle enough for the result to be meaningful.

## Workloads

`qualification`
: Verifies health, served-model identity, and a deterministic chat response before performance measurements.

`decode`
: Repeats a single-stream technical-prose workload and records TTFT, completion-token rate, and stream event-gap statistics.

`prefill`
: Builds real-text prompts at approximately 8K, 16K, and 32K tokens using the live `/tokenize` endpoint, then measures TTFT and derived prompt-token throughput.

`concurrency`
: Starts synchronized requests at concurrency levels 1, 2, 4, and 8 and records aggregate token rate, per-stream rate, median TTFT, and minimum `MemAvailable`.

`all`
: Runs all workloads in the order above.

## Usage

```bash
python3 scripts/benchmark/run.py qualification

mkdir -p scripts/benchmark/results/local
python3 scripts/benchmark/run.py all \
  --output scripts/benchmark/results/local/baseline.json
```

The served model is auto-detected when `/v1/models` exposes exactly one entry. An explicit model can be supplied with `--model`.

Useful overrides:

```bash
python3 scripts/benchmark/run.py decode \
  --decode-tokens 512 \
  --decode-repeats 5 \
  --output scripts/benchmark/results/local/decode.json

python3 scripts/benchmark/run.py prefill \
  --prefill-sizes 8192,32768,65536 \
  --corpus README.md \
  --output scripts/benchmark/results/local/prefill.json

python3 scripts/benchmark/run.py concurrency \
  --concurrency-levels 1,2,4,8 \
  --decode-tokens 384 \
  --output scripts/benchmark/results/local/concurrency.json
```

## Reproducible baseline policy

Before publishing a baseline:

1. `./scripts/doctor.sh` should report no failures.
2. `scripts/update-transition.sh status` and `scripts/runtime-transition.sh status` should both be idle.
3. Record the current immutable release and Git revision in the benchmark report.
4. Run the same workload parameters for later comparisons.
5. Treat changes in model revision, image, context settings, cache policy, MTP settings, or host memory policy as a new baseline rather than silently comparing unlike configurations.
