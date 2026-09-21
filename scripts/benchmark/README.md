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


## Mazinb checkpoint A/B on vLLM v0.29

When the seeded OrcaRouter determinism gate fails on both the preview runtime and the
vLLM v0.29 release line, keep the runtime fixed and change only the checkpoint.

The `mazinb` profile remains a non-installable candidate. It can be downloaded only
with the explicit `--candidate` flag, so it cannot accidentally replace the stable
OrcaRouter install manifest or service.

The candidate registry currently uses the immutable Hugging Face source ref
`f2c21eb`; the downloader resolves it through the Hugging Face API and records the
full resolved SHA in `.qwen38-model-manifest.json`.

Preflight disk/revision metadata without downloading:

```bash
MODEL_PROFILE=mazinb ./scripts/download-weights.sh --candidate --check
```

Download and verify the candidate:

```bash
MODEL_PROFILE=mazinb ./scripts/download-weights.sh --candidate
```

Stop the OrcaRouter v0.29 experiment before using the shared API port:

```bash
./scripts/runtime/orcarouter-v029.sh stop --profile orcarouter
```

Run the candidate on the exact same v0.29 image and runtime controls:

```bash
./scripts/runtime/orcarouter-v029.sh preflight --profile mazinb
./scripts/runtime/orcarouter-v029.sh start --profile mazinb

./scripts/wait-ready.sh \
  --container qwen38-mazinb-v029 \
  --model mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

Run the same seeded 1024-token correctness gate:

```bash
python3 scripts/benchmark/run.py determinism \
  --determinism-prompt-tokens 1024 \
  --determinism-output-tokens 128 \
  --determinism-repeats 5 \
  --output scripts/benchmark/results/local/mazinb-v029-seeded-det-1024.json
```

Interpretation:

- mazinb passes while OrcaRouter fails on the same v0.29 runtime: checkpoint /
  quantization recipe becomes the primary differentiator;
- both fail: investigate shared GB10 math/kernel paths rather than the preview runtime
  or OrcaRouter-specific checkpoint packaging.


### 2026-09-20 checkpoint-only result

A same-runtime local A/B on one GB10 produced:

| Checkpoint | Runtime | Seeded 1024 / 128, repeats=5 | Unique hashes |
|---|---|---:|---:|
| OrcaRouter pinned NVFP4 | vLLM v0.29 experiment | FAIL | 3 |
| mazinb `f2c21eb3d2ff5f24c208ea7e3afba65e2e70f83f` | same vLLM v0.29 experiment | PASS | 1 |

The wider mazinb QSA-size sweep also passed at every tested prompt size with five
repeats each:

| Requested prompt tokens | Actual prompt tokens | Unique hashes |
|---:|---:|---:|
| 1024 | 1024 | 1 |
| 2048 | 2048 | 1 |
| 4096 | 4096 | 1 |
| 8192 | 8191 | 1 |
| 32768 | 32768 | 1 |

A same-boot decode check was repeated twice. Both runs were stable around
25.75-25.79 tok/s median decode, ~0.261 s warm median TTFT, 11.8-12.0 engine
steps/s, and 0.5625 speculative draft-token acceptance. The first request of
the first run paid a colder TTFT (~0.92 s); the second full repetition removed
that outlier and reproduced the warm figures.

These wider results make the checkpoint/quantization-layout explanation stronger
than the original single-size gate alone.

Both cases used the same v0.29 experiment image, exact QSA path, GB10 FLA fix,
MTP k=2, prefix cache disabled, and seeded greedy controls. This is strong
evidence against the preview runtime and sampler defaults as the sole cause.

The mazinb model card describes its routed experts as NVFP4 group-16 while
keeping PLE and the overlaid residual-writing path in BF16. Treat the next
isolation target as checkpoint quantization/layout, especially OrcaRouter's
non-expert FP8/dense path, rather than NVFP4 routed experts alone.

Do not promote mazinb to the stable installer from this one gate. Run the wider
QSA-size determinism sweep, decode/TTFT measurements, and qualification suite
first.

The subsequent local qualification gate also passed. The same mazinb boot then
passed the 1024/2048/4096/8192/32768 determinism sweep with five repeats at each
size and reproduced ~25.75-25.79 tok/s median decode on repeated warm runs.

### Residual-writer BF16 hybrid isolation

The installed OrcaRouter checkpoint has 300 explicit FP8 group-0 modules:

- 48 self-attention projections (12 q/k/v/o layers);
- 108 linear-attention projections (36 qkv/z/out layers);
- 144 shared-expert projections (48 gate/up/down layers).

The first hybrid isolates only the 96 projections that write directly back to the
residual stream:

- 12 `self_attn.o_proj`;
- 36 `linear_attn.out_proj`;
- 48 `mlp.shared_expert.down_proj`.

For those modules the OrcaRouter index contains 96 FP8 `.weight` tensors and
96 `.weight_scale` tensors. The mazinb checkpoint contains 96 corresponding
BF16 `.weight` tensors. Similar MTP names are explicitly excluded; the observed
extra keys are `mtp.layers.0.self_attn.o_proj.weight` and
`mtp.layers.0.mlp.shared_expert.down_proj.weight`.

The hybrid builder rewrites affected OrcaRouter safetensor shards so stale FP8
weights/scales cannot leak through the loader. Unaffected base files are linked to
the immutable OrcaRouter checkpoint and resolved at runtime through the additional
read-only `/base-model` mount. The originals are never modified.

Stop the running experiment first, then inspect the storage plan:

```bash
./scripts/runtime/orcarouter-v029.sh stop --profile mazinb

bash scripts/model/prepare-hybrid-checkpoint.sh plan
```

The plan must report exactly 96 residual modules and shows the number/size of base
shards that must be rewritten. Build only after checking free disk space:

```bash
bash scripts/model/prepare-hybrid-checkpoint.sh build
```

The build runs inside `vllm-orcarouter-v029:v1`; no host torch, safetensors, or
Hugging Face Python installation is required. The completed local manifest must
record:

```text
residual_modules=96
fp8_targets_removed=96
fp8_scales_removed=96
bf16_weights_overlaid=96
mtp_tensors_changed=0
remaining_fp8_group0_targets=204
```

Start the hybrid on the otherwise identical v0.29 runtime:

```bash
./scripts/runtime/orcarouter-v029.sh preflight --profile hybrid-residual
./scripts/runtime/orcarouter-v029.sh start --profile hybrid-residual

./scripts/wait-ready.sh \
  --container qwen38-hybrid-residual-v029 \
  --model hybrid-residual/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

Run the small correctness gate first:

```bash
python3 scripts/benchmark/run.py determinism \
  --model hybrid-residual/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --determinism-prompt-tokens 1024 \
  --determinism-output-tokens 128 \
  --determinism-repeats 5 \
  --output scripts/benchmark/results/local/hybrid-residual-v029-det-1024.json
```

Interpretation:

- PASS: the root-cause region is narrowed to the 96 FP8 residual-writer modules;
  split next into self-attention o-proj (12), linear-attention out-proj (36), and
  shared-expert down-proj (48);
- FAIL: keep the residual BF16 overlay and expand the next hybrid to the remaining
  204 FP8 group-0 modules before moving back to unrelated runtime paths.

Observed on 2026-09-20 with git revision `804c811`:

- the residual hybrid manifest completed with 96 BF16 overlays, 204 FP8 group-0
  targets remaining, and zero MTP tensors changed;
- the v0.29 residual hybrid reached API readiness after 712 seconds;
- the 1024/128 greedy determinism gate failed with 3 unique output hashes across
  5 runs. Runs 1, 2, and 5 matched; runs 3 and 4 each produced a different hash;
- therefore the 96 residual-writer FP8 modules are not sufficient to explain or
  remove the observed non-determinism.

The next isolation step converts all 300 main-model group-0 FP8 modules to the
corresponding mazinb BF16 weights while still leaving MTP tensors untouched. Build
the full group-0 hybrid only after stopping the residual runtime:

```bash
./scripts/runtime/orcarouter-v029.sh stop --profile hybrid-residual

bash scripts/model/prepare-group0-hybrid-checkpoint.sh plan
bash scripts/model/prepare-group0-hybrid-checkpoint.sh build

# If an older build created a residual-bf16 manifest in the group0 output path,
# update to a fixed revision and rebuild the same path explicitly:
# bash scripts/model/prepare-group0-hybrid-checkpoint.sh build --force

./scripts/runtime/orcarouter-v029.sh preflight --profile hybrid-group0
./scripts/runtime/orcarouter-v029.sh start --profile hybrid-group0

./scripts/wait-ready.sh \
  --container qwen38-hybrid-group0-v029 \
  --model hybrid-group0/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

The completed group-0 hybrid manifest must report:

```text
selected_modules=300
fp8_targets_removed=300
fp8_scales_removed=300
bf16_weights_overlaid=300
mtp_tensors_changed=0
remaining_fp8_group0_targets=0
```

Observed after the #76 builder fix:

- full group-0 plan selected 300 modules across 15 rewritten shards;
- the completed checkpoint reported 300 FP8 targets/scales removed and 300 BF16
  weights overlaid;
- MTP tensors remained unchanged and no FP8 group-0 targets remained;
- local checkpoint size was approximately 73 GiB;
- the v0.29 `hybrid-group0` preflight accepted the checkpoint, image, and manifest,
  with the managed/canonical runtimes stopped and API port 8888 free.

Then repeat the same small determinism gate:

```bash
python3 scripts/benchmark/run.py determinism \
  --model hybrid-group0/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --determinism-prompt-tokens 1024 \
  --determinism-output-tokens 128 \
  --determinism-repeats 5 \
  --output scripts/benchmark/results/local/hybrid-group0-v029-det-1024.json
```

Interpret the second isolation gate as follows:

- PASS: the non-deterministic region is inside the 204 FP8 group-0 modules added
  beyond the residual-writer subset; subdivide those module families next;
- FAIL: full main-model group-0 BF16 replacement is still insufficient, so keep
  this result recorded before investigating MTP or other runtime paths.

Observed on 2026-09-21 with git revision `c19b36e`:

- the full group-0 BF16 hybrid was healthy and served the expected model;
- the seeded 1024/128 determinism gate still failed with 3 unique hashes across
  5 runs;
- runs 1, 3, and 4 matched, while runs 2 and 5 each produced a different hash;
- therefore replacing all 300 main-model FP8 group-0 modules with mazinb BF16
  weights is still insufficient to reproduce mazinb determinism.

Before building another hybrid, inventory the remaining checkpoint structure and
tensor metadata differences between OrcaRouter and mazinb:

```bash
bash scripts/model/inspect-orcarouter-mazinb-diff.sh
cat scripts/benchmark/results/local/orcarouter-vs-mazinb-structure.json
```

The inventory compares tensor-key presence plus dtype/shape metadata without
loading full tensor payloads into RAM. Use its category counts to choose the
smallest next A/B region rather than guessing between MTP, embeddings/head,
normalization, expert, PLE, or other checkpoint paths.


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

## OrcaRouter on vLLM v0.29

If the seeded stability candidate still produces multiple greedy output hashes, keep
the OrcaRouter checkpoint fixed and move only the runtime base from the Qwen preview
image to the official vLLM v0.29 release line.

The v0.29 experiment is deliberately minimal:

- OrcaRouter checkpoint from the active install manifest;
- vLLM `v0.29.0`;
- compatibility backport for newer checkpoints that use the explicit
  `qwen_sparse_attention` layer type;
- PLE mmap so the large n-gram table does not have to remain resident in unified RAM;
- exact QSA top-k;
- GB10 FLA shared-memory/num-warps workaround;
- MTP k=2;
- prefix cache disabled;
- no hybrid quantization, draft-vocab reduction, or other throughput patches.

Build and run:

```bash
docker build -t vllm-orcarouter-v029:v1 \
  -f scripts/Dockerfile.v029-orcarouter scripts/

sudo systemctl stop qwen38-flash-next.service
./scripts/runtime/orcarouter-v029.sh preflight
./scripts/runtime/orcarouter-v029.sh start

./scripts/wait-ready.sh \
  --container qwen38-orca-v029 \
  --model orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

Run the seeded determinism gate first:

```bash
python3 scripts/benchmark/run.py determinism \
  --determinism-prompt-tokens 1024 \
  --determinism-output-tokens 128 \
  --determinism-repeats 5 \
  --output scripts/benchmark/results/local/orcarouter-v029-seeded-det-1024.json
```

The report must show `vllm_base="v0.29"`, `ple_mmap="1"`,
`qsa_exact_topk="1"`, and the explicit seeded sampling controls before the result is
used for diagnosis.

Restore the canonical runtime through the managed service path after the experiment.

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


## Determinism sampling controls

Determinism requests explicitly pin `temperature=0`, `top_p=1.0`, `seed=0`, and disable thinking. The report records these controls so a failure cannot be attributed to an implicit sampler default.
