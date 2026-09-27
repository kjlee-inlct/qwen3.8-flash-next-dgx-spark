Warning: truncated output (original token count: 37407)
Total output lines: 3306

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
cat "${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark/analysis/orcarouter-vs-mazinb-structure.json"
```

The inventory compares tensor-key presence plus dtype/shape metadata without
loading full tensor payloads into RAM. It also summarizes routed-expert tensor
suffixes and the quantization config for each checkpoint. Use those counts to
choose the smallest next A/B region rather than guessing between MTP,
embeddings/head, normalization, expert packing, PLE, or other checkpoint paths.

For the observed OrcaRouter/mazinb pair, the structural inventory confirmed a
full routed-expert representation change:

- the initial diff showed 147600 OrcaRouter-only expert tensors and 221184
  mazinb-only expert tensors;
- the full expert layouts also share 73728 `weight_scale` tensors (three
  projection suffix families at 24576 each), so H3 must remove 221184 OrcaRouter
  expert tensors and add all 294912 mazinb expert tensors;
- OrcaRouter therefore has nine routed-expert suffix families in total, while
  mazinb has twelve;
- OrcaRouter expert quantization is compressed-tensors
  `nvfp4-pack-quantized`, 4-bit group-size 16;
- mazinb expert quantization is ModelOpt `NVFP4`, also 4-bit group-size 16, but
  with a different loader representation.

H3 expert selection is intentionally limited to `model.language_model.layers.*.mlp.experts.*`; any MTP expert tensors remain untouched and are excluded from the layout counts.

This makes the routed-expert quantization layout the next isolation target. H3
keeps OrcaRouter outside quantized regions, replaces all 300 group-0 weights with
the already-tested mazinb BF16 weights, replaces routed experts with mazinb
ModelOpt NVFP4 tensors, switches only `quantization_config` to mazinb, and
leaves MTP unchanged.

Plan H3 first; it reports the selected tensor counts and an estimated output
payload from safetensor metadata:

```bash
bash scripts/model/prepare-quant-layout-hybrid-checkpoint.sh plan
```

Only after the storage plan is acceptable, stop the current experiment and build:

```bash
./scripts/runtime/orcarouter-v029.sh stop --profile hybrid-group0
bash scripts/model/prepare-quant-layout-hybrid-checkpoint.sh build

./scripts/runtime/orcarouter-v029.sh preflight --profile hybrid-quant-layout
./scripts/runtime/orcarouter-v029.sh start --profile hybrid-quant-layout

./scripts/wait-ready.sh \
  --container qwen38-hybrid-quant-layout-v029 \
  --model hybrid-quant-layout/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

Then run the same seeded 1024/128 gate:

```bash
python3 scripts/benchmark/run.py determinism \
  --model hybrid-quant-layout/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --determinism-prompt-tokens 1024 \
  --determinism-output-tokens 128 \
  --determinism-repeats 5 \
  --output scripts/benchmark/results/local/hybrid-quant-layout-v029-det-1024.json
```

Interpretation:

- PASS: the differentiating region is the routed-expert quantization
  representation (or its interaction with the already-BF16 group0 path);
- FAIL: even matching mazinb's quantized tensor representations is insufficient,
  so compare the remaining common non-quantized tensor values/config fields
  rather than further subdividing group0.

Observed on 2026-09-21 with git revision `f4fba95`:

- H3 manifest completed with 300 group0 BF16 weights, 300 group0 FP8 scales
  removed, 221184 OrcaRouter expert tensors removed, 294912 mazinb ModelOpt
  expert tensors added, and zero MTP tensors changed;
- the built hybrid occupied approximately 73 GiB and passed the v0.29 preflight;
- the runtime reached API readiness after 732 seconds;
- the seeded 1024/128 determinism gate passed all five repetitions with one
  unique output hash;
- because H2 (group0 BF16 only) failed while H3 (same group0 BF16 plus mazinb
  routed-expert representation/config) passed, the H2->H3 delta is the primary
  remaining root-cause region.

Do not collapse this result to "all quantization" generally: H1 and H2 already
showed that the 300 non-expert group0 FP8 tensors were insufficient. The next
isolation should subdivide the routed-expert representation/config while keeping
the proven H2 group0-BF16 baseline fixed.

The same H3 boot then passed the wider QSA determinism sweep at requested prompt
sizes 1024, 2048, 4096, 8192, and 32768 with five repeats per size and exactly
one unique hash at every point. No first failing size was observed.

Decode also passed on the same boot:

- median deco…21407 tokens truncated…E kernel execution
  itself is the first observed divergence;
- CT request 0 vs 1 diverges before the CT-vs-H6 comparison point: prioritize
  that within-CT first mismatch because it directly localizes nondeterminism;
- all traced MoE calls match across both requests and both sources: continue
  H20 with the next non-MoE runtime boundary instead of creating H21.

#### H20-C observed result

Observed on 2026-09-22 after the ModelOpt class-scope hotfix:

- CT/H12 produced 192 runtime records across 48 MoE layers for two fixed
  requests;
- ModelOpt/H6 produced the same 192-record / 48-layer shape;
- `runtime-compare` reported `common_records=192`, `only_ct=0`,
  `only_modelopt=0`;
- the first CT-vs-H6 mismatch was request 0, ordinal 0, layer 0, `post`:
  the pre-call `x`, `topk_weights`, and `topk_ids` matched, but the
  MoE output hash differed;
- CT request 0 vs request 1 diverged at layer 0 `post`;
- ModelOpt/H6 request 0 vs request 1 first diverged at layer 3 `post`.

This is the first runtime evidence that the observed divergence appears at a
MoE kernel output boundary while the corresponding routed input/routing data
still match. It is not yet sufficient to attribute the production
nondeterminism to CT or to the Marlin kernel itself, because H20-C performs
CPU hashing/synchronization around every traced MoE call and even deterministic
H6 begins to diverge under that instrumentation.

#### H20-D same-input twin kernel probe

H20-D stays inside H20 and minimizes the H20-C observation before any new
repair experiment is created. The initial H20-D image label was v5; the immutable-input correction bumps it to v6.

For each fixed request, only
`language_model.model.layers.0.mlp.experts` is probed. Before the first kernel call, H20-D performs two GPU-only clone sets of `x`, `topk_weights`, `topk_ids`, and `shared_experts_input`: an immutable reference set used only for later fingerprinting, and a separate run2 set passed to the second kernel call. It does not hash or copy them to the CPU. Then:

1. execute the normal `moe_kernel.apply()`;
2. preserve its output with a GPU clone;
3. immediately execute the same `moe_kernel.apply()` again using only the separate run2 GPU clones;
4. only after both kernel executions, fingerprint the untouched reference clones and both outputs;
5. return the first output clone to the model so the second diagnostic call
   cannot overwrite the value used by the forward pass.

This directly tests whether the same loaded weights and same routed inputs can
produce two different outputs within one request. H20-C tracing is disabled
while the H20-D trigger is active.

Build/rebuild the v6 diagnostic images, start one profile, wait for READY, then
run:

```bash
python3 scripts/diagnostics/h20-nvfp4-moe.py twin-probe \
  --container qwen38-h20-ct-convert-diag-v029 \
  --model hybrid-h20-ct-convert-diag/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --repeats 2 \
  --output scripts/benchmark/results/local/h20d-ct-twin.jsonl
```

After stopping/removing CT and starting ModelOpt/H6:

```bash
python3 scripts/diagnostics/h20-nvfp4-moe.py twin-probe \
  --container qwen38-h20-modelopt-convert-diag-v029 \
  --model hybrid-h20-modelopt-convert-diag/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --repeats 2 \
  --output scripts/benchmark/results/local/h20d-modelopt-twin.jsonl
```

Compare:

```bash
python3 scripts/diagnostics/h20-nvfp4-moe.py twin-compare \
  --ct scripts/benchmark/results/local/h20d-ct-twin.jsonl \
  --modelopt scripts/benchmark/results/local/h20d-modelopt-twin.jsonl \
  --output scripts/benchmark/results/local/h20d-ct-vs-modelopt.json
```


Observed initial H20-D v5 result on 2026-09-22:

- CT/H12 request 0 and request 1 both reported `output_equal=true`;
- ModelOpt/H6 request 0 and request 1 both reported `output_equal=true`;
- the first cross-source compare reported `input_equal=false` and
  `output1_equal=false` for both requests.

The within-source twin result is valid evidence that neither path produces
immediate same-input/same-state nondeterminism in back-to-back layer-0 kernel
calls. However, the v5 cross-input result is not reliable: the same GPU clones
used as the purported input snapshots were also passed into the second kernel
call and fingerprinted only afterward. A backend that mutates hidden/routing
buffers in place could therefore change the recorded "input". H20-D v6 fixes
this by keeping immutable reference clones that are never passed to either
kernel invocation and separate run2 clones for the second execution.

The v6 `twin-compare` also reports which input differs (`x`,
`topk_weights`, `topk_ids`, or `shared_experts_input`) whenever
`input_equal=false`.

Observed H20-D v6 result on 2026-09-22:

- CT/H12 remained twin-stable for both fixed requests;
- ModelOpt/H6 remained twin-stable for both fixed requests;
- cross-source comparison still reported `input_equal=false` and
  `output1_equal=false` for both requests;
- every recorded layer-0 input differed cross-source: `x`,
  `topk_weights`, `topk_ids`, and `shared_experts_input`;
- CT request 0 and request 1 also had different layer-0 input hashes, while
  the two ModelOpt/H6 requests had identical layer-0 input hashes.

This conflicts with H20-C's observation that the CT repeat first diverged at
layer-0 `post`, so the next step must resolve the instrumentation difference
before moving deeper into Marlin state. In particular, the H20-D twin probe
adds a second layer-0 kernel invocation to request 0, which can perturb
request-to-request state even though the immutable snapshot itself is now
correct.

##### H20-D single-pass control

The v7 diagnostic image adds a single-pass control at the same layer-0 boundary.
It keeps the immutable GPU-only input snapshots but executes the normal
`moe_kernel.apply()` exactly once. No diagnostic second kernel invocation is
performed. H20-C tracing and the twin trigger are disabled while this control
is active.

Run on CT/H12:

```bash
python3 scripts/diagnostics/h20-nvfp4-moe.py single-probe \
  --container qwen38-h20-ct-convert-diag-v029 \
  --model hybrid-h20-ct-convert-diag/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --repeats 2 \
  --output scripts/benchmark/results/local/h20d-v7-ct-single.jsonl
```

Run on ModelOpt/H6:

```bash
python3 scripts/diagnostics/h20-nvfp4-moe.py single-probe \
  --container qwen38-h20-modelopt-convert-diag-v029 \
  --model hybrid-h20-modelopt-convert-diag/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --repeats 2 \
  --output scripts/benchmark/results/local/h20d-v7-modelopt-single.jsonl
```

Compare:

```bash
python3 scripts/diagnostics/h20-nvfp4-moe.py single-compare \
  --ct scripts/benchmark/results/local/h20d-v7-ct-single.jsonl \
  --modelopt scripts/benchmark/results/local/h20d-v7-modelopt-single.jsonl \
  --output scripts/benchmark/results/local/h20d-v7-ct-vs-modelopt-single.json
```

Interpretation:

- CT repeat inputs equal in single-pass control, but unequal in twin mode:
  the extra diagnostic kernel call is perturbing later request state; H20-C
  remains the more faithful runtime boundary result;
- CT repeat inputs still unequal in single-pass control while H6 repeat inputs
  are equal: divergence already exists before layer-0 MoE on the CT/H12 path;
  move the next H20 boundary upstream rather than into Marlin;
- both sources repeat-stable, cross inputs equal, outputs differ: then inspect
  Marlin/runtime state at layer 0;
- cross inputs already differ on request 0: CT and H6 are not entering layer-0
  MoE with the same state in this minimal control, so kernel-state comparison
  is premature.

Observed H20-D v7 single-pass result on 2026-09-22:

- CT/H12 request 0 vs request 1 differed in every layer-0 MoE boundary tensor:
  `x`, `topk_weights`, `topk_ids`, `shared_experts_input`, and
  `output`;
- ModelOpt/H6 request 0 vs request 1 matched in all of those tensors;
- CT and H6 also entered layer-0 MoE with different inputs on both requests.

This resolves the H20-C/H20-D instrumentation conflict: the CT/H12 path is
already request-unstable before the layer-0 routed experts kernel, even when no
diagnostic second kernel call is present. Marlin kernel-state comparison is
therefore premature.

##### H20 layer-0 upstream boundary probe

The initial v8 implementation failed during EngineCore profile/AOT compilation,
before READY and before any diagnostic request. The root cause was the upstream
patch calling a `@torch.compiler.disable` helper from inside
`Qwen4ExpModel`, which vLLM compiles with `torch.compile(fullgraph=True)`.
PyTorch rejected the graph with `Unsupported: Skip calling
torch.compiler.disable()d function`. This is an instrumentation failure, not
an H20 model/runtime result.

The first v9 image-build attempt on 2026-09-23 failed before the
fullgraph smoke test ran. The patched Qwen4Exp source contained the text
`@torch.compiler.disable` only inside an explanatory comment, but the
Dockerfile validation used a raw substring assertion
(`assert "@torch.compiler.disable" not in q4s`). That produced a false
positive and aborted both CT and ModelOpt image builds. This is a build-time
validation bug, not a runtime/H20 result. The validation now rejects only an
actual standalone decorator line (`"\n@torch.compiler.disable\n"`) so the
subsequent fullgraph custom-op smoke can execute.

The v9 correction keeps the same H20 upstream boundary design but represents
each capture point as an opaque `torch.library.custom_op`. The custom op is
declared conservatively mutable so compiler dead-code elimination cannot remove
the side-effecting diagnostic node. Its runtime implementation performs the
trigger/request-id file checks, stores GPU clones, and emits fingerprints only
after request 1 has reached all five boundaries. No
`torch.compiler.disable` call remains inside the fullgraph model path.

The v9 diagnostic image instruments the actual NVIDIA Qwen4Exp decoder path in
`vllm/models/qwen4_exp/nvidia/model.py`. It records only layer 0 and keeps all
request-0 snapshots on GPU until request 1 reaches the same boundary. CPU
fingerprinting is deferred until both requests have been captured.

Boundaries:

- `entry_hidden`: multi-stream hidden state entering
  `Qwen4ExpDecoderLayer.forward()`;
- `attn_block_input`: output of the attention hyper-connection mix;
- `attn_out`: attention/QSA or linear-attention output;
- `mlp_block_input`: output of `mlp_hyper_connection.combine_and_mix()`,
  which is the exact input passed into the MoE block;
- `mlp_out`: layer-0 MLP/MoE output.

Run CT/H12 after READY:

```bash
python3 scripts/diagnostics/h20-nvfp4-moe.py upstream-probe \
  --container qwen38-h20-ct-convert-diag-v029 \
  --model hybrid-h20-ct-convert-diag/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --output scripts/benchmark/results/local/h20u-v9-ct.jsonl
```

Run ModelOpt/H6 after READY:

```bash
python3 scripts/diagnostics/h20-nvfp4-moe.py upstream-probe \
  --container qwen38-h20-modelopt-convert-diag-v029 \
  --model hybrid-h20-modelopt-convert-diag/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --output scripts/benchmark/results/local/h20u-v9-modelopt.jsonl
```

Compare:

```bash
python3 scripts/diagnostics/h20-nvfp4-moe.py upstream-compare \
  --ct scripts/benchmark/results/local/h20u-v9-ct.jsonl \
  --modelopt scripts/benchmark/results/local/h20u-v9-modelopt.jsonl \
  --output scripts/benchmark/results/local/h20u-v9-ct-vs-modelopt.json
```

Observed H20 upstream v9 result on 2026-09-23:

- CT/H12 request 0 vs request 1 matched at `entry_hidden` and
  `attn_block_input`, then first diverged at `attn_out`;
- ModelOpt/H6 request 0 vs request 1 matched at every recorded boundary;
- CT-vs-H6 also first diverged at `attn_out` for both request 0 and request 1.

This moves the first observed CT repeat divergence inside layer-0 attention.
The Qwen3.8 Flash Next layer schedule starts with `linear_attention`, so layer
0 uses `QwenGatedDeltaNetAttention`, not QSA/full attention.

##### H20 layer-0 GDN linear-attention probe

The v10 diagnostic image instruments
`QwenGatedDeltaNetAttention.forward_cuda()` at layer 0 with the same
fullgraph-safe mutable custom-op pattern. Request-0 tensors remain GPU-only
until request 1 reaches the final output boundary.

Recorded stages:

- `input_hidden`: exact linear-attention input;
- `mixed_qkvz`: result of `in_proj_qkvz`;
- `ba`: result of `in_proj_ba`;
- `mixed_qkv`, `z`, `b`, `a`: explicit split path inputs when the
  non-fused GDN path is used;
- `core_attn_out`: output of the GDN core, or fused core+norm buffer on the
  fused path;
- `output`: final linear-attention output after output projection.

The probe reports CT request 0 vs request 1 directly, so ModelOpt/H6 does not
need to be rebooted initially because v9 already established H6 repeat
stability through `attn_out`.

Run CT/H12 after rebuilding the v10 CT image and reaching READY:

```bash
python3 scripts/diagnostics/h20-nvfp4-moe.py linear-probe \
  --container qwen38-h20-ct-convert-diag-v029 \
  --model hybrid-h20-ct-convert-diag/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --output scripts/benchmark/results/local/h20l-v10-ct.jsonl
```

Observed H20 v10 result on 2026-09-23:

- CT/H12 request 0 vs request 1 had identical `input_hidden`;
- `mixed_qkvz` was the first mismatching tensor;
- `ba` remained identical;
- `core_attn_out` and final `output` then differed;
- the fused GDN path was active, so `mixed_qkv`, `z`, `b`, and `a`
  were not materialized as separate probe boundaries.

This localizes the first observed instability to layer-0
`in_proj_qkvz`, before GDN recurrent/core state. Because `in_proj_ba`
receives the same hidden input and remains stable, the next H20 step targets
the QKVZ projection itself rather than the broader linear-attention block.

##### H20 layer-0 QKVZ projection probe

Observed v11 result on 2026-09-23:

- projection class: `MergedColumnParallelLinear`;
- quant method: `CompressedTensorsLinearMethod`;
- quant config: `CompressedTensorsConfig`;
- both requests reported `output_equal=false`;
- request 0 vs request 1 kept `input_equal=true` while the normal first
  projection outputs differed.

This confirms the v10 localization to `in_proj_qkvz`, but v11 mixed two
execution contexts: the normal first projection ran inside the fullgraph/AOT
compiled model, while the diagnostic second projection was invoked eagerly
inside the custom-op runtime. Therefore v11 does not by itself prove immediate
same-kernel nondeterminism.

##### H20 QKVZ compiled-vs-eager control

The v12 image keeps the same production compiled projection output, then runs
the same layer-0 QKVZ projection twice eagerly on identical GPU clones inside
the READY-triggered custom-op. It records:

- `compiled_output`: the production fullgraph/AOT projection result;
- `eager1`, `eager2`: two consecutive eager calls on the same input;
- `compiled_vs_eager_equal`;
- `eager_repeat_equal`;
- the actual compressed-tensors scheme class and underlying linear-kernel class.

Run CT/H12 after rebuilding the v12 CT image and reaching READY:

```bash
python3 scripts/diagnostics/h20-nvfp4-moe.py qkvz-twin-probe \
  --container qwen38-h20-ct-convert-diag-v029 \
  --model hybrid-h20-ct-convert-diag/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --output scripts/benchmark/results/local/h20p-v12-ct.jsonl
```

Observed H20 v12 result on 2026-09-23:

- scheme: `CompressedTensorsW8A16Fp8`;
- kernel: `HummingFP8ScaledMMLinearKernel`;
- both request 0 and request 1 reported
  `compiled_vs_eager_equal=false`;
- both requests also reported `eager_repeat_equal=false`;
- request 0 vs request 1 kept `input_equal=true` while
  `compiled_output_equal=false`.

The second point is the decisive one: two eager calls of the same layer-0
QKVZ projection on identical input clones already disagree. The instability is
therefore below `CompressedTensorsLinearMethod` / `CompressedTensorsW8A16Fp8`
and inside the Humming FP8 linear path or its persistent execution state.

The vLLM v0.29 Humming FP8 kernel allocates a persistent
`self.locks = torch.zeros(1024, int32, device=...)` once during
`process_weights_after_loading()` and passes the same lock tensor into every
`apply_humming_linear(..., locks=self.locks)` call. Neither the kernel wrapper
nor `apply_humming_linear()` resets the lock tensor before execution.

##### H20 Humming lock-state control

The first v13 image-build attempt on 2026-09-23 failed in Dockerfile static
validation before the fullgraph smoke or runtime probe executed. The v13
diagnostic record renamed the v12 field `compiled_vs_eager_equal` to
`compiled_vs_natural_equal`, but both diagnostic Dockerfiles still asserted
that the removed v12 key existed. The new v13 keys and lock-reset code had
already been installed successfully; the stale validation assertion alone
aborted the build. This is a build-validation regression, not an H20 runtime
result. The stale v12 assertion was removed and a regression test now requires
v13 Dockerfiles to contain the new lock-control keys while rejecting the old
one.

The v13 control records the persistent Humming lock tensor before and after a
natural eager QKVZ call, then executes two additional same-input eager calls
with `locks.zero_()` immediately before each call. No CPU fingerprinting is
performed until all three eager executions have completed.

For each request it records:

- `natural_eager`: normal eager execution using the current lock state;
- `zeroed_eager1`, `zeroed_eager2`: executions after explicit lock reset;
- `natural_vs_zeroed_equal`;
- `zeroed_repeat_equal`;
- lock fingerprints before/after natural and both zeroed calls.

Run CT/H12 after rebuilding the v13 CT image and reaching READY:

```bash
python3 scripts/diagnostics/h20-nvfp4-moe.py qkvz-twin-probe \
  --container qwen38-h20-ct-convert-diag-v029 \
  --model hybrid-h20-ct-convert-diag/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --output scripts/benchmark/results/local/h20p-v13-ct.jsonl
```

Observed H20 v13 result on 2026-09-23:

- `locks_present=true` for both requests;
- request 0 and request 1 both reported `zeroed_repeat_equal=false`;
- every recorded lock pre/post comparison was equal:
  `pre_vs_after_natural=true`, `zero1_pre_vs_post=true`, and
  `zero2_pre_vs_post=true`;
- request inputs remained equal across requests;
- in this run, the production compiled outputs also matched across requests;
- the first explicitly zero-reset eager outputs still differed across requests.

This deprioritizes persistent Humming `locks` as the cause. Explicit lock
reset neither stabilized same-input eager execution nor exposed any mutation
of the lock tensor.

The Humming linear wrapper derives its compute config from
`VLLM_BATCH_INVARIANT` and passes that value as `use_batch_invariant` to
the Humming backend. The repository did not set this environment variable, so
the preceding H20 runs used the default non-batch-invariant Humming mode.

##### H20 Humming batch-invariant controls

Observed v14 startup result on 2026-09-23:

- the CT v14 image built successfully and carried
  `VLLM_BATCH_INVARIANT=1`;
- EngineCore loaded the model but failed before READY;
- the root cause was
  `RuntimeError: VLLM batch_invariant mode is not supported for GDN_ATTN.`;
- therefore no v14 QKVZ probe result exists.

This is a control-design failure rather than an H20 runtime result. The global
environment variable affects the GDN attention backend selector in addition to
the Humming FP8 linear kernel, so it cannot be used for this model.

##### H20 Humming FP8-local batch-invariant control

The v15 CT image removes the global `VLLM_BATCH_INVARIANT=1` setting. Instead,
it patches only
`HummingFP8ScaledMMLinearKernel.process_weights_after_loading()` after the
normal Humming FP8 compute config is created. The patch parses that config,
sets only:

```json
{"use_batch_invariant": true}
```

and serializes it back into the FP8 linear kernel's `self.compute_config`.
The GDN attention selector continues to see the default global
batch-invariant setting and should therefore start normally.

The patch intentionally does not modify
`HummingInt8ScaledMMLinearKernel`, the Humming MoE backend, the H12
checkpoint, or any H20 probe logic. Startup emits
`QWEN38_H20Q_FP8_BATCH_INVARIANT` with the resulting FP8 compute config.

Run the existing QKVZ probe after rebuilding and starting the v15 CT image:

```bash
python3 scripts/diagnostics/h20-nvfp4-moe.py qkvz-twin-probe \
  --container qwen38-h20-ct-convert-diag-v029 \
  --model hybrid-h20-ct-convert-diag/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --output scripts/benchmark/results/local/h20p-v15-ct.jsonl
```

Observed H20 v15 result on 2026-09-23:

- the v15 image started successfully and reached READY;
- startup logged the local FP8 compute config as
  `{"use_batch_invariant": true, "use_f16_accum": false, "gemm_type": "dense"}`;
- request 0 and request 1 both reported
  `compiled_vs_natural_equal=true`;
- both requests reported `natural_vs_zeroed_equal=true`;
- both requests reported `zeroed_repeat_equal=true`;
- request-to-request comparison reported
  `input_equal=true compiled_output_equal=true zeroed_eager1_equal=true`.

This closes the H20 localization loop: the same layer-0 QKVZ projection that
was unstable with the default Humming FP8 compute mode becomes stable when
batch-invariant mode is enabled only for
`HummingFP8ScaledMMLinearKernel`. The global batch-invariant mode remains
disabled, so GDN attention is unaffected.

##### H20 FP8 batch-invariant repair candidate

Observed repair validation on 2026-09-23:

- the diagnostic-free repair image built successfully with label
  `ct-h12-humming-fp8-batch-invariant-v1` and reached READY;
- runtime metadata retained vLLM v0.29, exact QSA, MTP k=2,
  max_num_seqs=3, prefix caching disabled, and the H12 checkpoint;
- the primary 8192-requested-token / 128-output / 5-repeat determinism gate
  failed with five distinct output hashes;
- the wider sweep was also executed and failed at every tested size:
  - 1024: 4 unique hashes / 5 repeats;
  - 2048: 5 / 5;
  - 4096: 5 / 5;
  - 8192 requested (8191 actual): 5 / 5;
  - 32768: 5 / 5.

This is a broad negative end-to-end result. It supersedes the earlier
"repair candidate pending" state. The v15 QKVZ probe remains valid evidence
that the local batch-invariant setting stabilizes that specific layer-0
projection boundary, but it does not prove that the same setting removes all
later sources of nondeterminism.

The ordinary end-to-end determinism workload was also run on the v15
diagnostic image itself on 2026-09-23. It failed with three unique hashes across
five repeats. Runs 1, 3, and 5 shared the same hash, while runs 2 and 4 each
differed. This proves the H20 instrumentation did not make the whole model
deterministic, although the diagnostic image was less variable than the
diagnostic-free repair in this sample.

Because the v15 QKVZ-local probe remains stable while the full generation still
fails, the existing layer-0 GDN boundary probe was reused on the same v15 image.
The two requests matched at every captured stage:

- `input_hidden=true`;
- `mixed_qkvz=true`;
- `ba=true`;
- `core_attn_out=true`;
- final attention `output=true`;
- overall `all_equal=true`, with no first mismatch.

The missing `mixed_qkv/z/b/a` split stages are expected because the active
runtime uses the fused GDN decode path. The existing upstream probe was then
reused on the same v15 image and layer 0 also matched at every captured
decoder boundary: `entry_hidden`, `attn_block_input`, `attn_out`,
`mlp_block_input`, and `mlp_out` were all equal across the two requests.

Observed v16 result on 2026-09-23:

- the v16 image built successfully with label `ct-nvfp4-convert-diag-v16`
  and reached READY;
- two separate upstream-probe runs produced the same result;
- layer 0 was fully stable across all five boundaries;
- layer 1 was also fully stable across all five boundaries;
- therefore the remaining end-to-end divergence is downstream of layer 1.

Rather than extend one layer at a time, v17 captures sparse layers
`0,1,3,7,15,31,47`. All sparse-layer tensors remain GPU snapshots until
request 1 reaches layer 47, then they are fingerprinted and emitted together.
This keeps the search lightweight while locating the first unstable layer
interval in a single boot.

Therefore the remaining end-to-end divergence is strictly downstream of layer
0 in this control. H20 v16 extends only the same upstream custom-op capture to
layer 1. No new repair behavior is introduced. The collector now emits
layer-indexed records and prints one repeat summary per captured layer:

```text
upstream_repeat layer=0 all_equal=...
upstream_repeat layer=1 all_equal=...
```

Interpretation:

- layer 0 stable, layer 1 `entry_hidden=false`: divergence was introduced
  between layer 0 output handoff and layer 1 entry;
- layer 1 entry stable but a later layer-1 field differs: localize within
  layer 1 using the first mismatching boundary;
- layers 0 and 1 both stable: extend the same pattern farther downstream rather
  than adding another repair patch.

Before introducing another repair patch, run the ordinary end-to-end
determinism workload on the v15 diagnostic image itself. Use the same 8192/128
×5 workload. Interpretation:

- v15 diagnostic image PASS, diagnostic-free repair FAIL: H20 instrumentation
  or its altered execution schedule is materially changing end-to-end
  behavior; do not attribute the repair to batch-invariant mode alone;
- both v15 diagnostic and diagnostic-free repair FAIL: layer-0 QKVZ was a real
  localized divergence but not the only end-to-end divergence; resume tracing
  after the now-stable QKVZ boundary;
- v15 diagnostic FAIL with layer-0 QKVZ still stable: move the next lightweight
  boundary probe downstream rather than revisiting QKVZ.

The next validation removes all H20 runtime instrumentation. The repair image
is built directly on H12 and applies only the local Humming FP8
batch-invariant patch. Use profile `hybrid-h20-ct-fp8-bi-repair`.

Build:

```bash
docker build --no-cache \
  -t vllm-orcarouter-v029-h20-fp8-bi-repair:v1 \
  -f scripts/Dockerfile.v029-h20-fp8-bi-repair \
  scripts/
```

Start:

```bash
./scripts/runtime/orcarouter-v029.sh preflight \
  --profile hybrid-h20-ct-fp8-bi-repair

./scripts/runtime/orcarouter-v029.sh start \
  --profile hybrid-h20-ct-fp8-bi-repair

./scripts/wait-ready.sh \
  --container qwen38-h20-ct-fp8-bi-repair-v029 \
  --model hybrid-h20-ct-fp8-bi-repair/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

Primary repair validation:

```bash
python3 scripts/benchmark/run.py determinism \
  --model hybrid-h20-ct-fp8-bi-repair/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --determinism-prompt-tokens 8192 \
  --determinism-output-tokens 128 \
  --determinism-repeats 5 \
  --output scripts/benchmark/results/local/h20-fp8-bi-repair-determinism.json
```

If that passes, run the wider prompt-size sweep:

```bash
python3 scripts/benchmark/run.py qsa-determinism \
  --model hybrid-h20-ct-fp8-bi-repair/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --qsa-determinism-sizes 1024,2048,4096,8192,32768 \
  --determinism-output-tokens 128 \
  --determinism-repeats 5 \
  --output scripts/benchmark/results/local/h20-fp8-bi-repair-qsa.json
```

Pass criteria:

- primary determinism: `status=pass`, `all_equal=true`,
  `unique_hashes=1`;
- wider sweep: every size `status=pass`, every `unique_hashes=1`;
- no H20 diagnostic custom-op or twin-call instrumentation is present in this
  repair image.

Interpretation:

- READY succeeds and same-input eager outputs become stable: Humming FP8
  batch-invariant compute mode is strongly implicated and becomes a repair
  candidate for the W8A16 QKVZ path;
- READY succeeds but eager outputs remain unstable: batch-invariant mode is
  insufficient, so continue into Humming GEMM internals or an alternate FP8
  backend control;
- startup still reports a GDN batch-invariant rejection: the local patch leaked
  into the global selector and must be fixed before interpreting any probe.

Interpretation:

- `zeroed_repeat_equal=true` while the natural eager result differs:
  persistent Humming lock state is strongly implicated; the next control should
  patch/reset locks at the kernel boundary and re-run determinism;
- `zeroed_repeat_equal=false`: resetting locks is insufficient, so continue
  into Humming GEMM internals/workspace/algorithm behavior;
- lock pre/post fingerprints differ: confirms the lock workspace is mutated by
  the GEMM call;
- lock fingerprints stay equal while outputs differ: the lock tensor is not
  explaining the nondeterminism and should be deprioritized.

Interpretation:

- `eager_repeat_equal=false`: same-input eager calls are themselves unstable;
  inspect the reported underlying linear-kernel/backend directly;
- `eager_repeat_equal=true` but `compiled_vs_eager_equal=false`: the
  projection is stable in eager execution but the fullgraph/AOT result differs;
  focus on compiled-vs-eager kernel selection, AOT graph lowering, or compiled
  buffer/workspace behavior;
- both are true, but `qkvz_repeat input_equal=true compiled_output_equal=false`:
  request-to-request state affects only the production compiled path;
- `input_equal=false`: the v10/v11 same-input premise was not reproduced.

Interpretation:

- first mismatch at `mixed_qkvz` or `ba`: input projection/quantized linear
  path is request-unstable despite identical hidden input;
- projections equal and first mismatch at `core_attn_out`: focus on GDN
  conv/recurrent state allocation, restore/reset, and the core kernel;
- `core_attn_out` equal but `output` differs: focus on gated norm or
  `out_proj`;
- all stages equal: the v9 `attn_out` difference was probe-dependent and
  should be reproduced before going deeper.

A ModelOpt/H6 v10 detailed control can be collected later with the same command
and compared via `linear-compare`, but it is not required for the first CT
localization pass.

Interpretation:

- CT repeat first mismatch at `entry_hidden`: divergence exists before decoder
  layer 0; next H20 probe moves to embedding / initial HC multi-stream setup;
- `entry_hidden` equal but `attn_block_input` differs: attention
  hyper-connection mix is the first boundary;
- first mismatch at `attn_out`: attention/QSA/linear-attention path is the
  first unstable stage;
- first mismatch at `mlp_block_input`: MLP hyper-connection combine/mix is the
  first unstable stage;
- H6 should remain repeat-stable; if it does not, treat the probe itself as
  perturbing before localizing further.

Interpretation:

- CT `output_equal=false`, H6 `output_equal=true`: strong evidence that the
  CT-loaded/runtime state causes same-input kernel nondeterminism;
- both CT and H6 `output_equal=false`: focus on Marlin/GB10 kernel execution,
  workspace reuse, or the diagnostic twin-call interaction rather than CT
  checkpoint semantics;
- both `output_equal=true` but CT-vs-H6 `output1_equal=false` with
  `input_equal=true`: the two paths are stable within one call context but
  still compute different layer-0 MoE results; inspect runtime kernel state not
  captured by H20-B;
- both twin outputs and cross-source outputs match: H20-C's layer-0 divergence
  was instrumentation/request-sequencing induced; move the next minimal probe
  downstream without creating H21.

