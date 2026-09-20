# Benchmark harness

This directory contains the repository's canonical read-only benchmark harness for the managed Qwen3.8 Flash Next runtime.

## Responsibilities

- Run read-only qualification and performance workloads against the already-running loopback API.
- Record reproducible environment/runtime metadata with benchmark results.
- Keep generated model text out of persisted reports.

## Dependencies

- May read repository/runtime state needed to label a benchmark result.
- May call the local serving API and standard host telemetry.
- Must not own runtime startup, lifecycle mutation, model preparation, or diagnostics policy.

## Non-responsibilities

- Do not restart or reconfigure the managed runtime.
- Do not change model files, swap, system settings, or lifecycle state.
- Do not become a second runtime validator; operational validation remains under `runtime/`.

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

`determinism`
: Repeats the same long greedy request and requires byte-identical output. Reports only SHA-256 digests, token counts, and timings; generated text is not persisted. This is the correctness gate for evaluating prefix-cache, Mamba, QSA, and speculative-decoding changes.

`decode`
: Repeats a single-stream technical-prose workload and records TTFT, completion-token rate, stream event-gap statistics, and optional vLLM engine/speculative-decoding counter deltas.

`tuning`
: Runs qualification, determinism, and decode only. Use this focused mode when comparing runtime knobs so correctness and decode performance are captured without adding prefill/concurrency noise.

`prefill`
: Builds real-text prompts at approximately 8K, 16K, and 32K tokens using the live `/tokenize` endpoint, then measures TTFT and derived prompt-token throughput.

`concurrency`
: Starts synchronized requests at concurrency levels 1, 2, 4, and 8 and records aggregate token rate, per-stream rate, median TTFT, and minimum `MemAvailable`.

`all`
: Runs qualification, determinism, decode, prefill, and concurrency in that order. A determinism mismatch makes the overall report fail.

## Usage

```bash
python3 scripts/benchmark/run.py qualification
python3 scripts/benchmark/run.py determinism

mkdir -p scripts/benchmark/results/local
python3 scripts/benchmark/run.py all \
  --output scripts/benchmark/results/local/baseline.json
```

The served model is auto-detected when `/v1/models` exposes exactly one entry. An explicit model can be supplied with `--model`.

Useful overrides:

```bash
python3 scripts/benchmark/run.py determinism \
  --determinism-prompt-tokens 32768 \
  --determinism-output-tokens 256 \
  --determinism-repeats 3 \
  --output scripts/benchmark/results/local/determinism.json

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


## Decode engine metrics

When the local vLLM `/metrics` endpoint exposes speculative-decoding
counters, the `decode` workload records counter deltas for the measured
decode interval under `engine_metrics`.

Recorded raw deltas include:

- `engine_steps`: vLLM engine-step count from
  `vllm:iteration_tokens_total_count`.
- `iteration_tokens`: token count reported by
  `vllm:iteration_tokens_total_sum`.
- `generation_tokens`: generated-token counter delta.
- `drafts`: speculative draft iterations.
- `draft_tokens`: speculative tokens proposed by the draft model.
- `accepted_tokens`: accepted speculative tokens.
- `accepted_tokens_per_position`: accepted speculative tokens at each
  draft position.

Derived values include:

- `steps_s = engine_steps / measured decode wall time`.
- `draft_acceptance_rate = accepted_tokens / draft_tokens`.
- `accepted_per_draft = accepted_tokens / drafts`.
- `generation_per_step = generation_tokens / engine_steps`.
- `iteration_tokens_per_step = iteration_tokens / engine_steps`.

These names are intentionally explicit. Do not treat
`draft_acceptance_rate`, `accepted_per_draft`, or
`generation_per_step` as interchangeable meanings of "mean acceptance".

The Prometheus counters are process-global. Decode engine metrics are
therefore valid only when no unrelated inference requests overlap the
benchmark interval. The benchmark remains usable when `/metrics` is
unavailable; in that case `engine_metrics` is omitted.

A Prometheus counter reset during the measured interval makes the
affected delta unavailable rather than producing a negative result.


## NVIDIA INDEX_SHARE x AUTOTUNE 2x2 experiment

The NVIDIA profile currently enables `NSPEC=3`, `INDEX_SHARE=1`, and
`AUTOTUNE=1` together. The MTP `k=3` choice has separate measurements,
but `INDEX_SHARE` and FlashInfer autotune have not been isolated. Use this
matrix while keeping every other runtime control fixed:

| Case | INDEX_SHARE | AUTOTUNE |
|---|---:|---:|
| A | 0 | 0 |
| B | 1 | 0 |
| C | 0 | 1 |
| D | 1 | 1 |

Fixed controls are the NVIDIA profile, `NSPEC=3`, `MAXLEN=524288`,
`KV_MEM=16106127360`, `MAXSEQS=8`, `PREFIX_CACHE=0`,
`--no-async-scheduling`, the same image/model revision, and the same host
memory/swap policy.

The runtime helper never stops the managed service for you. Stop it
explicitly first so the canonical container remains preserved:

```bash
sudo systemctl stop qwen38-flash-next.service
bash scripts/runtime/nvidia-2x2.sh status
bash scripts/runtime/nvidia-2x2.sh plan
```

Start one case at a time. The helper refuses to start while the managed
service or canonical runtime is still running:

```bash
bash scripts/runtime/nvidia-2x2.sh start A
# wait until http://127.0.0.1:8888/health is ready

python3 scripts/benchmark/run.py tuning \
  --determinism-prompt-tokens 32768 \
  --determinism-output-tokens 256 \
  --determinism-repeats 3 \
  --decode-tokens 600 \
  --decode-repeats 5 \
  --output scripts/benchmark/results/local/nvidia-2x2-A.json

bash scripts/runtime/nvidia-2x2.sh stop A
```

Repeat for B, C, and D. Benchmark reports automatically inspect the Docker
container serving the benchmark port and record the effective image,
context length, KV memory, sequence/batch limits, speculative config,
FlashInfer autotune, prefix-caching state, async-scheduling state, and
executor backend under `environment.runtime_config`. This makes each
result self-describing instead of relying on its filename.

Compare `engine_metrics.steps_s` first. Use
`generation_per_step`, `draft_acceptance_rate`, decode tok/s, TTFT, and
the determinism result as supporting evidence. The Prometheus counters are
process-global, so do not send unrelated inference traffic during a
measurement.

After all four cases are complete, remove any experiment container and
restore the managed runtime:

```bash
bash scripts/runtime/nvidia-2x2.sh stop
sudo systemctl start qwen38-flash-next.service
./scripts/doctor.sh
```

Because identical configurations have previously produced different
sequences across boots, a single A/B/C/D pass is exploratory. Repeat the
matrix across fresh boots before treating small step-rate differences as
stable.


## OrcaRouter stock vs skinny-GEMM A/B experiment

Use this experiment to isolate whether the GB10/TP=1 skinny-GEMM image changes
correctness or performance on the pinned OrcaRouter checkpoint. The helper reads
the installed OrcaRouter model directory, config override, served-model name, and
revision from the strict installation manifest; the only intended runtime
difference is the image.

| Case | Image |
|---|---|
| `STOCK` | `vllm/vllm-openai:qwen38-flash-next-arm64-cu130` + MTP k=2 |
| `STOCK-NOSPEC` | stock image + no speculative decoding |
| `SKINNY` | `vllm-skinny-tp1:v1` + MTP k=2 |
| `SKINNY-NOSPEC` | skinny image + no speculative decoding |

All cases fix `MAXLEN=262144`, `KV_MEM=25769803776`, `MAXSEQS=3`,
`PREFIX_CACHE=0`, `INDEX_SHARE=0`, `AUTOTUNE=0`, loopback port 8888,
no runtime monitor, and no container restart policy. The regular cases use
MTP `k=2`; the `*-NOSPEC` cases set `SPEC=none` to isolate whether
speculative decoding contributes to greedy-output non-determinism.

The helper never stops the managed service or edits lifecycle state. Stop the
canonical managed service explicitly before the experiment, then preflight:

```bash
sudo systemctl stop qwen38-flash-next.service
bash scripts/runtime/orcarouter-stock-skinny.sh status
bash scripts/runtime/orcarouter-stock-skinny.sh preflight
```

Run the stock control first:

```bash
bash scripts/runtime/orcarouter-stock-skinny.sh start STOCK
./scripts/wait-ready.sh --container qwen38-orca-stock --model orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4

python3 scripts/benchmark/run.py determinism \
  --determinism-prompt-tokens 1024 \
  --determinism-output-tokens 128 \
  --determinism-repeats 3 \
  --output scripts/benchmark/results/local/orcarouter-stock-det-1024.json

python3 scripts/benchmark/run.py qsa-determinism \
  --qsa-determinism-sizes 1024,2048,4096,8192,32768 \
  --determinism-output-tokens 128 \
  --determinism-repeats 3 \
  --output scripts/benchmark/results/local/orcarouter-stock-qsa.json

python3 scripts/benchmark/run.py decode \
  --decode-tokens 600 \
  --decode-repeats 5 \
  --output scripts/benchmark/results/local/orcarouter-stock-decode.json

bash scripts/runtime/orcarouter-stock-skinny.sh stop STOCK
```

Repeat with `SKINNY` only when a fresh same-boot comparison is needed. Existing
managed skinny results may be used as exploratory context, but a same-boot A/B
is preferred before attributing a small difference to the image.

After the experiment, remove experiment containers and restore the canonical
managed service:

```bash
bash scripts/runtime/orcarouter-stock-skinny.sh stop
sudo ./scripts/manage-service.sh create \
  --runtime-root "$HOME/.local/share/qwen38-spark/current" \
  --start \
  --yes
./scripts/doctor.sh
```

Interpret determinism before performance. If stock is deterministic and skinny
is not, treat the skinny patch as a correctness regression candidate. If both
are non-deterministic at the same prompt sizes, do not blame skinny-GEMM yet.
Run `STOCK-NOSPEC` next with the 1024-token determinism workload. If
`STOCK-NOSPEC` passes while `STOCK` fails, MTP/speculative decoding becomes
the primary regression candidate. If both fail, continue into the shared
OrcaRouter/QSA/runtime path.

Use `manage-service.sh create --start` when restoring the canonical runtime.
A raw `systemctl start` returns before the replacement runtime is committed,
so an immediate doctor run may correctly observe a temporary `validating`
transition, rollback container, missing attestation, and unavailable health
endpoint.



## OrcaRouter deterministic QSA top-k experiment

The stock and skinny OrcaRouter images both reproduced 1024-token greedy-output
non-determinism, and the stock image still failed with speculative decoding disabled.
This rules out skinny-GEMM and makes MTP unlikely as the root cause. The next isolated
variable is the GB10/sm121 QSA `persistent_topk` kernel.

The experimental image layers only the deterministic QSA kernel wiring on top of the
existing skinny-GEMM image:

```bash
docker build -t vllm-skinny-qsa-det:v1 \
  -f scripts/Dockerfile.qsa-det scripts/
```

The external kernel sources are pinned to commit
`e0ef69d4f5575dad00d34e05479eaf4c6547bace` and individually sha256-checked at build
time. No hybrid quantization, KV-cache, prefix-cache, MTP-vocabulary, or NVIDIA
mixed-precision patches are included.

After stopping the managed service, start only the deterministic-QSA case:

```bash
bash scripts/runtime/orcarouter-stock-skinny.sh start SKINNY-DET
./scripts/wait-ready.sh --container qwen38-orca-stock --model orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4

python3 scripts/benchmark/run.py determinism \
  --determinism-prompt-tokens 1024 \
  --determinism-output-tokens 128 \
  --determinism-repeats 5 \
  --output scripts/benchmark/results/local/orcarouter-skinny-detqsa-det-1024.json
```

If the 1024 gate passes, run the QSA sweep and decode benchmark using the same
parameters as the stock/skinny comparison. Treat this image as experimental until both
correctness and performance are measured locally.

Restore the canonical runtime through the managed commit-waiting path, not raw
`systemctl start`:

```bash
bash scripts/runtime/orcarouter-stock-skinny.sh stop SKINNY-DET
sudo ./scripts/manage-service.sh create \
  --runtime-root "$HOME/.local/share/qwen38-spark/current" \
  --start --yes
./scripts/doctor.sh
```


## OrcaRouter exact-QSA isolation

The deterministic persistent-topk kernel experiment improved one 1024-token sweep
case but did not make the OrcaRouter runtime globally deterministic: the standalone
1024-token gate still produced multiple output hashes, and 2048+ sweep sizes remained
unstable. The next isolation bypasses persistent_topk completely with exact
`torch.topk` over visible QSA columns.

Build the exact-QSA image:

```bash
docker build -t vllm-skinny-qsa-exact:v1 \
  -f scripts/Dockerfile.qsa-exact scripts/
```

The image is the existing skinny-GEMM runtime plus only
`scripts/patch-qsa-exact-topk.py`. The default QSA path stays unchanged unless
`VLLM_QSA_EXACT_TOPK=1`.

Run the isolated case after stopping the managed service:

```bash
bash scripts/runtime/orcarouter-stock-skinny.sh start SKINNY-EXACT
./scripts/wait-ready.sh --container qwen38-orca-skinny-exact --model orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4

python3 scripts/benchmark/run.py determinism \
  --determinism-prompt-tokens 1024 \
  --determinism-output-tokens 128 \
  --determinism-repeats 5 \
  --output scripts/benchmark/results/local/orcarouter-skinny-exact-det-1024.json
```

Benchmark reports record both `qsa_det_topk` and `qsa_exact_topk` from the live
container environment, so results prove which QSA selection path was active.

If the 1024 gate passes, run the same QSA sweep and decode workload used by the
stock/skinny comparison. Exact top-k is a diagnostic correctness path and may reduce
long-prefill throughput; do not promote it to the default image without local
correctness and performance results.

Restore the canonical runtime with the managed commit-waiting path:

```bash
bash scripts/runtime/orcarouter-stock-skinny.sh stop SKINNY-EXACT
sudo ./scripts/manage-service.sh create \
  --runtime-root "$HOME/.local/share/qwen38-spark/current" \
  --start --yes
./scripts/doctor.sh
```


## OrcaRouter stability candidate

After stock, skinny, MTP-off, deterministic-QSA, and exact-QSA all reproduced
greedy-output non-determinism, the next stability candidate combines the exact QSA
selection path with two correctness fixes that current DGX Spark recipes apply
unconditionally:

- GB10 Flash Linear Attention shared-memory/num-warps workaround, including the
  Blackwell `tl.dot` race workaround;
- guarded Mamba state-copy implementation containing the vLLM overlapping-copy race
  fix plus bounds checks.

This is still an experiment, not the installer default.

Build it on top of the existing exact-QSA image:

```bash
docker build -t vllm-skinny-stable-candidate:v1 \
  -f scripts/Dockerfile.stable-candidate scripts/
```

Run it with the managed runtime stopped:

```bash
bash scripts/runtime/orcarouter-stock-skinny.sh start STABLE-CANDIDATE

./scripts/wait-ready.sh \
  --container qwen38-orca-stable-candidate \
  --model orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

Then run the 1024-token correctness gate first:

```bash
python3 scripts/benchmark/run.py determinism \
  --determinism-prompt-tokens 1024 \
  --determinism-output-tokens 128 \
  --determinism-repeats 5 \
  --output scripts/benchmark/results/local/orcarouter-stable-candidate-det-1024.json
```

The benchmark metadata must show:

```json
"qsa_exact_topk": "1",
"gb10_fla_fix": "1",
"mamba_state_fix": "1"
```

Only if the 1024 gate passes should the wider QSA determinism sweep and decode
benchmark be run. Restore the canonical runtime through the managed service path after
the experiment.

## QSA determinism diagnostic

Qwen3.8 Flash Next uses a sparse QSA indexer. On the NVIDIA checkpoint used by
this project, the model config currently reports `indexer_budget=2048` and
`indexer_compress_ratio=4`. A correctness sweep should therefore include
prompt sizes on both sides of the sparse-selection boundary.

Run:

```bash
python3 scripts/benchmark/run.py qsa-determinism \
  --qsa-determinism-sizes 1024,2048,4096,8192,32768 \
  --determinism-output-tokens 128 \
  --determinism-repeats 3 \
  --output scripts/benchmark/results/local/qsa-determinism.json
```

The mode reports the first observed failing prompt size and the number of unique
greedy-output hashes at each size. This diagnostic is intentionally separate
from the `tuning` performance mode: a tuning run may produce useful engine
metrics even when the correctness gate fails, but such numbers must not be
treated as a validated production configuration.

Runtime metadata also records `mtp_index_share` explicitly. A false value is
recorded as `false` rather than inferred from an absent speculative-config
field, so A/B/C/D results remain self-describing.

## Reusable operator helpers

Long model boots should use `./scripts/wait-ready.sh` rather than copied polling loops. Model inventory and stale checkpoint cleanup should use `./scripts/manage-models.sh`; the command refuses to delete the active installation model.
