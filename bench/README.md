# Benchmark baseline

This directory contains read-only benchmark tooling for the managed Qwen3.8 Flash Next runtime.

The benchmark suite is intentionally separate from runtime patches and model-artifact builders. Its job is to measure a known runtime and record enough metadata to compare later changes without altering the server configuration.

## Safety rules

- The HTTP target must be credential-free loopback HTTP (`127.0.0.1`, `localhost`, or `::1`) with an explicit port.
- Proxy environment variables are ignored and redirects are rejected.
- Generated model text is never written to reports.
- The runner does not restart containers, clear caches, change sysctls, or modify model files.
- Run benchmarks only while the host is otherwise idle enough for the result to be meaningful.

## Phase 1 workloads

`qualification`
: Verifies health, served-model identity, and a deterministic chat response before performance measurements.

`decode`
: Repeats a single-stream technical-prose workload and records TTFT, completion-token rate, and stream event-gap statistics.

`prefill`
: Builds real-text prompts at approximately 8K, 16K, and 32K tokens using the live `/tokenize` endpoint, then measures TTFT and derived prompt-token throughput. This replaces the role of `scripts/bench-prefill.py` while keeping its real-text principle.

`concurrency`
: Starts synchronized requests at concurrency levels 1, 2, 4, and 8 and records aggregate token rate, per-stream rate, median TTFT, and minimum `MemAvailable`.

`all`
: Runs all Phase 1 workloads in the order above.

## Usage

Run a lightweight pre-check first:

```bash
python3 bench/run.py qualification
```

Run the full Phase 1 baseline and save JSON output:

```bash
mkdir -p bench/results/local
python3 bench/run.py all \
  --output bench/results/local/baseline.json
```

The served model is auto-detected when `/v1/models` exposes exactly one entry. An explicit model can be supplied with `--model`.

Useful overrides:

```bash
python3 bench/run.py decode \
  --decode-tokens 512 \
  --decode-repeats 5 \
  --output bench/results/local/decode.json

python3 bench/run.py prefill \
  --prefill-sizes 8192,32768,65536 \
  --corpus README.md \
  --output bench/results/local/prefill.json

python3 bench/run.py concurrency \
  --concurrency-levels 1,2,4,8 \
  --decode-tokens 384 \
  --output bench/results/local/concurrency.json
```

## Result schema

Each report uses `schema_version: 1` and records:

- benchmark start/completion timestamps;
- repository Git revision;
- immutable runtime release ID when present;
- served-model ID and reported maximum model length;
- selected host memory/swap counters;
- Python version;
- workload parameters and aggregate measurements;
- `generated_text_retained: false`.

The report deliberately does not record hostname, hardware serials, credentials, generated answers, or absolute corpus paths.

## Reproducible baseline policy

A performance number is useful only when the runtime under test is identifiable. Before publishing a baseline:

1. `./scripts/doctor.sh` should report no failures.
2. `scripts/update-transition.sh status` and `scripts/runtime-transition.sh status` should both be idle.
3. Record the current immutable release and Git revision in the benchmark report.
4. Run the same workload parameters for later comparisons.
5. Treat changes in model revision, image, context settings, cache policy, MTP settings, or host memory policy as a new baseline rather than silently comparing unlike configurations.

## Planned follow-up

Phase 2 will add cache-correctness, long-context/storage/page-fault observation, and mixed prefill+decode interference tests. Those checks are intentionally kept separate from this first baseline PR so the initial measurement harness remains small and reviewable.
