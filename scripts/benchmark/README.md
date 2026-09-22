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

- median decode: 26.6382 tok/s (max 26.6634 tok/s);
- warm TTFT after the first request: about 0.222-0.230 s;
- engine steps: 11.917/s;
- speculative draft acceptance: 0.600733;
- accepted tokens per draft: 1.201465.

This wider result makes the H2->H3 routed-expert representation/config delta a
strong root-cause region rather than a single-size coincidence. Further
subdivision must preserve one coherent loader representation; mixing OrcaRouter
packed expert tensors with a mazinb ModelOpt quantization config is not a valid
isolation by itself.

### H1-H20 experiment ledger

This ledger is the canonical compact history for the checkpoint/loader
determinism isolation. Startup/build failures are explicitly separated from
valid determinism results.

| ID | Isolated change | Valid result | Key interpretation |
|---|---|---|---|
| H1 | Replace 96 residual-writer group-0 FP8 modules with mazinb BF16; MTP unchanged | FAIL, 3 unique hashes / 5 | Residual-writer subset is insufficient. |
| H2 | Replace all 300 main-model group-0 FP8 modules with mazinb BF16; MTP unchanged | FAIL, 3 / 5 | Main-model group-0 values are insufficient. |
| H3 | H2 + replace routed experts with mazinb ModelOpt NVFP4 representation/config | PASS, 1 / 5; wider 1024-32768 sweep also PASS | H2->H3 routed-expert representation/config delta is the decisive region. |
| H4a | H3 + restore OrcaRouter down-proj expert values | PASS, 1 / 5 | Down-proj values alone are insufficient. |
| H4b | H3 + restore OrcaRouter gate/up expert values | PASS, 1 / 5 | Gate/up values alone are insufficient. |
| H4c | H3 + restore all OrcaRouter expert weight/group/global-scale values | PASS, 1 / 5 | OrcaRouter expert numeric values themselves are insufficient under ModelOpt representation. |
| H5 | H4c + set all 73728 ModelOpt input_scale tensors to 1.0 | PASS, 1 / 5 | Specific mazinb input-scale values are not required. |
| H6 | H5 bytes unchanged; ModelOpt quant_algo NVFP4 -> W4A16_NVFP4 | PASS, 1 / 5 | W4A4 activation quantization is not required; representation/loader path remains. |
| H7 | H6 derivative intended to change ModelOpt weight_scale metadata BLOCK -> GROUP | FAIL, 3 / 5, but causal attribution inconclusive | Later source review showed this is not a clean metadata-only proof. |
| H8 | Original Orca CT path; weight_scale metadata GROUP -> BLOCK | FAIL, 3 / 5 | BLOCK metadata alone cannot repair CT. |
| H9 | H8 + weight_scale objects -> ModelWeightParameter + BLOCK | FAIL, 5 / 5 | weight_scale parameter/loader representation alone is insufficient. |
| H10 | H9 + weight_global_scale objects -> PerTensorScaleParameter | FAIL, 5 / 5 | global-scale object representation alone is insufficient. |
| H11 | H10 + packed expert weights -> ModelWeightParameter before post-load processing | FAIL, 5 / 5 | Pre-load packed-weight object representation alone is insufficient. |
| H12 | H11 + preserve loaded ModelWeightParameter objects across packed->weight rename | FAIL, 2 / 5; 4 runs matched H6 stable hash | Post-load object replacement is a strong interaction signal, not yet a standalone root-cause proof. |
| H13 | H12 + input-global-scale checkpoint objects -> PerTensorScaleParameter | FAIL, 4 / 5 | Input-global-scale parameter representation is not the missing repair; regression versus H12. |
| H14 | H12 + register converted post-load input scales as Parameters | FAIL, 5 / 5 | Final post-load input-scale Tensor/Parameter ownership is insufficient. |
| H15 | H14 runtime/image with MTP speculative decoding disabled | FAIL, 4 / 5 | MTP is not sufficient to explain the remaining nondeterminism; one pair of repeats matched, but the gate still failed. |
| H16 | H15 runtime with max_num_seqs 3 -> 1 | FAIL, 4 / 5 | Single-sequence scheduling is not sufficient; run 1 matched the H6 stable reference and runs 2-3 matched each other, but the gate failed. |
| H17 | H12 + rename loaded weight_global_scale parameters to final weight_scale_2 names before conversion | FAIL, 4 / 5 | Final weight_scale_2 name/object lifecycle alone is insufficient; two runs matched each other and one matched the H6 stable hash. |
| H18 | H12 + rename loaded input_global_scale parameters to final input_scale names before conversion and replace converted scales on those names | FAIL, 5 / 5 | Input-scale final-name/object lifecycle alone is insufficient; all five repeats diverged. |
| H19 | H12 + apply both H17 weight_scale_2 lifecycle and H18 input_scale lifecycle | FAIL, 5 / 5 | Combined final-name/object lifecycle alignment is insufficient; wrapper/object lifecycle isolation is closed. |
| H20 | Instrument H12 CT and deterministic H6 ModelOpt around convert_to_nvfp4_moe_kernel_format() with normalized tensor fingerprints | PENDING diagnostic | Locates the first CT-vs-ModelOpt divergence before or after kernel-format conversion without changing checkpoint bytes. |

Important invalid/non-result events:

- H9 had two startup-only failures before the corrected valid run: first missing
  quant_method metadata, then an attempted overwrite of the constructor-owned
  weight_loader. Neither is a determinism result.
- H10 initially had a startup-only loader failure because the new
  PerTensorScaleParameter global-scale objects lacked TENSOR quant_method
  metadata. The corrected H10 run is the valid determinism result.
- The first H17 image build failed before runtime because the patch script
  incorrectly required `layer.w13_weight_global_scale[:, 0]` to occur exactly
  once even though H12 uses it in both the `allclose` check and the contiguous
  extraction. This is a patch-application failure, not a determinism result.
- A missing image/container, build failure, or readiness failure is never
  classified as a determinism FAIL.
- H4a/H4b were disposable thin controls and may no longer exist on disk; H4c is
  the retained H4 checkpoint.

Validation still worth doing independently of the H20 conversion diagnostic:

- repeat H12 with a larger same-boot sample (for example 20 repeats) to estimate
  whether the observed 4/5 stable pattern is reproducible;
- repeat H12 after a fresh runtime start. If the 4/5 pattern disappears, do not
  use its apparent improvement as evidence of effect size;
- preserve the stable H6 hash as a reference marker, but do not equate matching
  one output hash with proof that the internal execution path is identical.

### H4 partial routed-expert A/B

The read-only conversion feasibility gate passed on the local OrcaRouter/mazinb
pair:

- 73728 routed-expert projection modules matched between checkpoints;
- sampled packed weights are U8 on both sides after name normalization;
- sampled group scales are F8_E4M3 on both sides with no shape mismatches;
- OrcaRouter exposes no routed-expert input-global-scale tensors, while mazinb
  provides 73728 `input_scale` tensors;
- `weight_global_scale` can be mapped to ModelOpt `weight_scale_2` by
  reciprocal;
- gate/up global scales are validated as a pair before an H4 build.

Therefore H4 keeps the H3 ModelOpt loader contract and mazinb `input_scale`
fixed while replacing only normalized OrcaRouter weight/group/global-scale
values. The first split follows the fused-MoE loader boundary:

- `orca-down`: all 24576 `down_proj` expert modules;
- `orca-gate-up`: all 49152 `gate_proj + up_proj` expert modules together.

Both are thin delta checkpoints over H3; unchanged tensors/files are referenced
through the read-only `/h3-model` mount instead of copying the 73-GiB parent.

Plan both variants before stopping H3:

```bash
bash scripts/model/prepare-h4-expert-ab.sh plan orca-down
bash scripts/model/prepare-h4-expert-ab.sh plan orca-gate-up
```

Build one variant at a time only after checking its reported delta size:

```bash
./scripts/runtime/orcarouter-v029.sh stop --profile hybrid-quant-layout

bash scripts/model/prepare-h4-expert-ab.sh build orca-down
./scripts/runtime/orcarouter-v029.sh preflight --profile hybrid-h4-down
./scripts/runtime/orcarouter-v029.sh start --profile hybrid-h4-down

./scripts/wait-ready.sh \
  --container qwen38-h4-down-v029 \
  --model hybrid-h4-down/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

Run the 1024/128 seeded gate first. If `orca-down` fails while H3 passes, the
down-projection expert values are sufficient to reintroduce nondeterminism. If it
passes, test `orca-gate-up` next under the same H3 parent and runtime controls.

Observed on 2026-09-21:

- H4 `orca-down` built successfully as a 22-GiB thin delta over H3;
- 24576 OrcaRouter `down_proj` expert modules / 73728 normalized tensors were
  substituted while mazinb/H3 `input_scale` and ModelOpt quantization config
  remained fixed;
- runtime reached READY after 952 seconds;
- the 1024/128 seeded determinism gate passed all five repeats with exactly one
  unique output hash.

Therefore restoring all OrcaRouter routed-expert `down_proj` values is not
sufficient to reproduce the original nondeterminism. The next discriminating
experiment is `orca-gate-up`.

Observed next on 2026-09-21:

- H4 `orca-gate-up` built successfully as a 43-GiB thin delta over H3;
- 49152 OrcaRouter `gate_proj + up_proj` expert modules / 147456 normalized
  tensors were substituted while mazinb/H3 `input_scale` and ModelOpt
  quantization config remained fixed;
- runtime reached READY after 1013 seconds;
- the 1024/128 seeded determinism gate passed all five repeats with exactly one
  unique output hash.

With both `orca-down` and `orca-gate-up` passing independently, neither
projection family alone is sufficient to reproduce the original instability.

Observed next on 2026-09-21 with `orca-all`:

- all 73728 OrcaRouter routed-expert projection modules / 221184 normalized
  expert weight/group/global-scale tensors were restored together;
- mazinb/H3 `input_scale` and ModelOpt quantization config remained fixed;
- the thin delta occupied about 64 GiB;
- runtime reached READY after 1212 seconds;
- the 1024/128 seeded determinism gate passed all five repeats with one unique
  output hash.

Therefore neither individual projection families nor their combined OrcaRouter
weight/group/global-scale values are sufficient to reproduce the original
nondeterminism. The leading remaining checkpoint/runtime difference is the
ModelOpt activation-input-scale path versus the original compressed-tensors
expert loader path.

The next isolation is H5 `neutral-input-scale`: keep the proven H4-all Orca
expert payload and ModelOpt config fixed, but replace all 73728 routed-expert
`input_scale` tensors with scalar 1.0 values. This distinguishes the mazinb
input-scale values from the ModelOpt loader/config path itself.

```bash
./scripts/runtime/orcarouter-v029.sh stop --profile hybrid-h4-all

bash scripts/model/prepare-h5-input-scale.sh plan
bash scripts/model/prepare-h5-input-scale.sh build

./scripts/runtime/orcarouter-v029.sh preflight --profile hybrid-h5-neutral-input
./scripts/runtime/orcarouter-v029.sh start --profile hybrid-h5-neutral-input

./scripts/wait-ready.sh \
  --container qwen38-h5-neutral-input-v029 \
  --model hybrid-h5-neutral-input/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

Interpretation:

- FAIL: the mazinb expert input-scale values are a material part of the
  determinism fix;
- PASS: neutralizing the values is still stable, so the remaining distinction is
  primarily the ModelOpt activation-quantization/loader representation rather
  than the specific mazinb input-scale values.

Observed on 2026-09-21:

- H5 `neutral-input-scale` reached READY after 421 seconds;
- all 73728 routed-expert `input_scale` tensors were replaced with scalar 1.0;
- OrcaRouter expert weight/group/global-scale values from H4-all and the
  mazinb/ModelOpt quantization config were retained;
- the 1024/128 seeded determinism gate passed all five repeats with one unique
  output hash;
- the output hash matched the H4-all result.

Therefore the specific mazinb input-scale values are not required for
determinism. The remaining high-value distinction is the expert
representation/loader contract itself: ModelOpt NVFP4 versus the original
compressed-tensors packed expert path.

H6 isolates the activation-quantization mode inside the ModelOpt representation.
It reuses the H5 checkpoint byte-for-byte and changes only the ModelOpt
`quant_algo` from `NVFP4` (W4A4) to `W4A16_NVFP4`. No safetensor bytes,
expert payloads, neutral input scales, MTP tensors, or other model config fields
are changed.

```bash
./scripts/runtime/orcarouter-v029.sh stop --profile hybrid-h5-neutral-input

bash scripts/model/prepare-h6-w4a16.sh plan
bash scripts/model/prepare-h6-w4a16.sh build

./scripts/runtime/orcarouter-v029.sh preflight --profile hybrid-h6-w4a16
./scripts/runtime/orcarouter-v029.sh start --profile hybrid-h6-w4a16

./scripts/wait-ready.sh \
  --container qwen38-h6-w4a16-v029 \
  --model hybrid-h6-w4a16/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

Interpretation:

- FAIL: switching from W4A4 activation quantization to the W4A16 path is
  sufficient to reintroduce instability. The activation/backend path becomes
  the primary root-cause region;
- PASS: the ModelOpt representation remains stable even in W4A16 mode, so the
  remaining difference is more specifically the ModelOpt versus
  compressed-tensors loader/parameter representation.

Observed on 2026-09-21:

- H6 `modelopt-w4a16` reached READY after 712 seconds;
- no safetensor bytes changed relative to H5;
- the only intended checkpoint change was
  `quant_algo: NVFP4 -> W4A16_NVFP4`;
- the 1024/128 seeded determinism gate passed all five repeats with one unique
  output hash.

Therefore W4A4 activation quantization is not required for determinism. The
remaining leading difference is the checkpoint loader/parameter representation
and its weight-processing path: ModelOpt versus compressed-tensors.

H7 isolates one explicit loader metadata difference while reusing the H6
checkpoint unchanged. vLLM v0.29 registers the routed-expert NVFP4
`weight_scale` parameter as `BLOCK` in the ModelOpt loader but as `GROUP`
in the compressed-tensors loader. H7 patches only the ModelOpt MoE metadata
assignment from `BLOCK` to `GROUP`; checkpoint tensors, W4A16 mode, QSA, MTP,
and all runtime controls stay fixed.

Build the tiny derivative image and run the H6 checkpoint through it:

```bash
docker build -t vllm-orcarouter-v029-h7-group:v1 \
  -f scripts/Dockerfile.v029-h7-modelopt-group scripts/

./scripts/runtime/orcarouter-v029.sh stop --profile hybrid-h6-w4a16
./scripts/runtime/orcarouter-v029.sh preflight --profile hybrid-h7-group-metadata
./scripts/runtime/orcarouter-v029.sh start --profile hybrid-h7-group-metadata

./scripts/wait-ready.sh \
  --container qwen38-h7-group-metadata-v029 \
  --model hybrid-h7-group-metadata/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

Interpretation:

- FAIL: the GROUP/BLOCK scale metadata and the weight-loading path it selects
  becomes a strong root-cause candidate;
- PASS: that metadata difference is also insufficient, leaving the
  compressed-tensors parameter naming/processing path itself as the next target.

Observed on 2026-09-21:

- H7 `group-metadata` reused the H6 checkpoint unchanged;
- the derivative image changed only the ModelOpt routed-expert `weight_scale`
  metadata from `BLOCK` to `GROUP`;
- runtime reached READY after 722 seconds;
- the 1024/128 seeded determinism gate failed with 3 unique hashes across 5
  repeats;
- runs 1, 2, and 4 matched the stable H6 hash, while runs 3 and 5 diverged.

H7 failed determinism, but later source review showed that ModelOpt
`ModelWeightParameter` does not consume the modified `extra_weight_attrs`
through the compressed-tensors generic scale-loading branch. Therefore H7 must
not be treated as a clean causal `BLOCK -> GROUP` proof. It remains evidence
that the derived runtime was unstable, but the specific metadata attribution is
inconclusive.

H8 is the reciprocal confirmation test on the original OrcaRouter
compressed-tensors checkpoint. It leaves the checkpoint and compressed-tensors
loader intact and changes only the routed-expert `weight_scale` metadata from
`GROUP` to `BLOCK` for both w13 and w2.

```bash
docker build -t vllm-orcarouter-v029-h8-ct-block:v1 \
  -f scripts/Dockerfile.v029-h8-ct-block scripts/

./scripts/runtime/orcarouter-v029.sh stop --profile hybrid-h7-group-metadata
./scripts/runtime/orcarouter-v029.sh preflight --profile hybrid-h8-ct-block
./scripts/runtime/orcarouter-v029.sh start --profile hybrid-h8-ct-block

./scripts/wait-ready.sh \
  --container qwen38-h8-ct-block-v029 \
  --model hybrid-h8-ct-block/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

Interpretation:

- PASS: the reciprocal change restores determinism on the original
  compressed-tensors checkpoint, strongly confirming GROUP/BLOCK metadata
  handling as the root-cause region;
- FAIL: BLOCK metadata alone is insufficient to repair compressed-tensors.
  Because later source review showed H7 is not a clean GROUP-metadata causal
  proof, the combined H7/H8 result only justifies moving to the
  compressed-tensors-specific parameter/loader and post-load processing path.

Observed on 2026-09-21:

- H8 reused the original OrcaRouter compressed-tensors checkpoint unchanged;
- only the routed-expert `weight_scale` metadata changed `GROUP -> BLOCK`;
- runtime reached READY after 742 seconds;
- the 1024/128 seeded determinism gate still failed with 3 unique hashes across
  5 repeats;
- runs 1-3 matched the stable H6 hash while runs 4-5 diverged;
- startup selected the weight-only FP4 Marlin path.

H8 shows that explicitly changing the compressed-tensors scale metadata to
`BLOCK` is insufficient to restore determinism. Combined with the H7 caveat
above, the next valid isolation target is the compressed-tensors-specific
parameter/weight-loader representation and post-load conversion path.

H9 isolates the first of those representation differences. It keeps the
original OrcaRouter compressed-tensors checkpoint and H8's `BLOCK` metadata,
but changes only the routed-expert w13/w2 `weight_scale` parameters from plain
`torch.nn.Parameter + set_weight_attrs` to the ModelOpt-style
`ModelWeightParameter(input_dim=1, output_dim=2, weight_loader=...)`.
Packed weights, global scales, quantization config, post-load rename/conversion,
and the W4A16/Marlin runtime path remain unchanged.

```bash
docker build -t vllm-orcarouter-v029-h9-ct-modelweight:v1 \
  -f scripts/Dockerfile.v029-h9-ct-modelweight-scale scripts/

./scripts/runtime/orcarouter-v029.sh stop --profile hybrid-h8-ct-block
./scripts/runtime/orcarouter-v029.sh preflight --profile hybrid-h9-ct-modelweight
./scripts/runtime/orcarouter-v029.sh start --profile hybrid-h9-ct-modelweight

./scripts/wait-ready.sh \
  --container qwen38-h9-ct-modelweight-v029 \
  --model hybrid-h9-ct-modelweight/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

Interpretation:

- PASS: the expert scale parameter/loader representation is the missing repair
  beyond BLOCK metadata and becomes the primary root-cause candidate;
- FAIL: scale parameter representation is still insufficient, leaving packed
  weight/global-scale parameter handling or compressed-tensors post-load
  conversion as the next isolation target.

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

### H9 loader correction

The first H9 image failed before inference because converting the
compressed-tensors expert `weight_scale` objects to `ModelWeightParameter`
dropped the `quant_method` attribute required by the generic
`RoutedExperts.weight_loader`. That startup failure is not a determinism
result. The corrected H9 patch keeps the ModelWeightParameter representation but
reapplies `set_weight_attrs(..., quant_method=BLOCK)` to both w13 and w2 scale
parameters before rerunning the control.

### H9 loader correction 2

The second H9 boot also failed before weight loading completed. The corrected
ModelWeightParameter objects already own their `weight_loader` attribute, so
passing the full `extra_weight_attrs` dict into `set_weight_attrs()` tried to
overwrite `weight_loader` and tripped vLLM's safety assertion. This is not a
determinism result.

The corrected control now applies only
`{"quant_method": "block"}` through `set_weight_attrs()`, while the
ModelWeightParameter retains its constructor-provided weight loader.

### H9 corrected result: FAIL

Observed on 2026-09-21:

- the corrected H9 image built successfully with the expected v2 image label;
- the runtime reached READY after 621 seconds;
- the original OrcaRouter compressed-tensors checkpoint was unchanged;
- routed-expert w13/w2 `weight_scale` parameters used
  `ModelWeightParameter(input_dim=1, output_dim=2)` with
  `quant_method=BLOCK`;
- the 1024/128 seeded determinism gate failed with 5 unique hashes across 5
  repeats.

Therefore the expert weight-scale parameter/loader representation is not
sufficient to repair the compressed-tensors path. The next isolation target is
the remaining compressed-tensors-specific expert representation: packed expert
weights, global-scale parameters, and post-load conversion.

### H10: compressed-tensors global-scale parameter control

H9 showed that changing only routed-expert `weight_scale` parameters to
ModelWeightParameter + BLOCK is insufficient: the corrected H9 runtime reached
READY but still produced 5 unique hashes in 5 deterministic repeats.

H10 keeps the corrected H9 image as its parent and changes only the routed-expert
weight-global-scale parameter representation:

- H9: plain `torch.nn.Parameter` + TENSOR attrs;
- H10: `PerTensorScaleParameter(weight_loader=...)`.

The original OrcaRouter checkpoint values and on-disk parameter names remain
unchanged. The compressed-tensors reciprocal conversion
`1 / weight_global_scale`, packed expert weights, input-global-scale handling,
post-load rename, W4A16/Marlin backend, QSA, and MTP controls are unchanged.

```bash
docker build --no-cache \
  -t vllm-orcarouter-v029-h10-ct-global-scale:v1 \
  -f scripts/Dockerfile.v029-h10-ct-global-scale \
  scripts/

./scripts/runtime/orcarouter-v029.sh stop --profile hybrid-h9-ct-modelweight
./scripts/runtime/orcarouter-v029.sh preflight --profile hybrid-h10-ct-global-scale
./scripts/runtime/orcarouter-v029.sh start --profile hybrid-h10-ct-global-scale

./scripts/wait-ready.sh \
  --container qwen38-h10-ct-global-scale-v029 \
  --model hybrid-h10-ct-global-scale/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

Interpretation:

- PASS: global-scale parameter/loader representation is the missing difference
  beyond H9 and becomes the primary root-cause candidate;
- FAIL: global-scale parameter representation is also insufficient, leaving the
  packed expert-weight parameter representation and compressed-tensors
  post-load rename/conversion as the next isolation target.


### H10 result: FAIL

Observed on 2026-09-22:

- corrected H10 reached READY after 672 seconds;
- original OrcaRouter checkpoint values and names were unchanged;
- H9 expert `weight_scale` used `ModelWeightParameter + BLOCK`;
- H10 expert `weight_global_scale` used
  `PerTensorScaleParameter(weight_loader=...)` with TENSOR metadata;
- the 1024/128 seeded determinism gate failed with 5 unique hashes across 5
  repeats;
- one repeat matched the previously stable H6 hash
  `44867e5c36d54b5bbec26f7c4f7c500783602a4bbc1b1545758929fc1c763670`,
  while other repeats matched hashes previously seen in H9.

Therefore the global-scale parameter/loader representation is also insufficient
to repair the compressed-tensors path.

### H11: compressed-tensors packed expert weight parameter control

H11 starts from the corrected H10 image and changes only the pre-load packed
expert weight parameter objects:

- H10: plain `torch.nn.Parameter` for `w13_weight_packed` /
  `w2_weight_packed`;
- H11: `ModelWeightParameter(input_dim=1, output_dim=2,
  weight_loader=...)` for those same on-disk names.

The OrcaRouter checkpoint, packed weight bytes, H9 scale representation, H10
global-scale representation, reciprocal scale conversion, and the existing
compressed-tensors post-load `weight_packed -> weight` wrapping/rename are
unchanged.

Build and run:

```bash
docker build --no-cache \
  -t vllm-orcarouter-v029-h11-ct-packed-modelweight:v1 \
  -f scripts/Dockerfile.v029-h11-ct-packed-modelweight \
  scripts/

./scripts/runtime/orcarouter-v029.sh preflight \
  --profile hybrid-h11-ct-packed-modelweight
./scripts/runtime/orcarouter-v029.sh start \
  --profile hybrid-h11-ct-packed-modelweight

./scripts/wait-ready.sh \
  --container qwen38-h11-ct-packed-modelweight-v029 \
  --model hybrid-h11-ct-packed-modelweight/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

Interpretation:

- PASS: the packed-weight parameter/loader representation becomes the strongest
  remaining root-cause candidate;
- FAIL: pre-load packed-weight parameter representation is insufficient, making
  the compressed-tensors post-load `weight_packed -> weight` rename/wrapping
  the next isolation target.


### H11 result: FAIL

Observed on 2026-09-22:

- H11 reached READY after 622 seconds;
- packed expert weights used `ModelWeightParameter(input_dim=1, output_dim=2,
  weight_loader=...)` while retaining the original
  `w13_weight_packed` / `w2_weight_packed` checkpoint names;
- the existing compressed-tensors post-load wrapping/rename path remained
  unchanged;
- the 1024/128 seeded determinism gate failed with 5 unique hashes across 5
  repeats.

Therefore the packed expert pre-load parameter/loader representation is also
insufficient.

### H12: preserve packed expert parameter objects across post-load rename

H12 starts from H11 and changes only the compressed-tensors post-load rename:

- H11 creates new plain `torch.nn.Parameter` objects from
  `layer.w*_weight_packed.data`, then deletes the packed names;
- H12 re-registers the already-loaded `ModelWeightParameter` objects directly
  as `w13_weight` / `w2_weight`, then deletes the packed names.

Checkpoint bytes/names, H9/H10 scale representations, kernel-format conversion,
backend selection, QSA, and MTP are unchanged.

```bash
docker build --no-cache \
  -t vllm-orcarouter-v029-h12-ct-postload-preserve:v1 \
  -f scripts/Dockerfile.v029-h12-ct-postload-preserve \
  scripts/

./scripts/runtime/orcarouter-v029.sh preflight \
  --profile hybrid-h12-ct-postload-preserve
./scripts/runtime/orcarouter-v029.sh start \
  --profile hybrid-h12-ct-postload-preserve

./scripts/wait-ready.sh \
  --container qwen38-h12-ct-postload-preserve-v029 \
  --model hybrid-h12-ct-postload-preserve/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

Interpretation:

- PASS: post-load packed-weight re-wrapping/object replacement is the strongest
  remaining root-cause candidate;
- FAIL: even preserving the loaded packed weight objects is insufficient, so the
  next target is the broader compressed-tensors post-load scale/input-scale
  assignment/conversion path rather than the packed-weight object identity alone.


### H12 result: FAIL, but strongly improved

Observed on 2026-09-22:

- H12 reached READY after 611 seconds;
- the 1024/128 seeded determinism gate still failed;
- however only 2 unique hashes were observed across 5 repeats;
- 4 of 5 repeats matched the stable H6 hash
  `44867e5c36d54b5bbec26f7c4f7c500783602a4bbc1b1545758929fc1c763670`;
- the fifth repeat produced
  `973e217f93f585dac5b8a11275d5329716a672fc268f682b884b53d18c53ca0a`.

In this five-repeat run, preserving the loaded packed-weight parameter objects
was associated with a strong reduction from five unique hashes to two, but it
was not sufficient for a PASS. Treat the apparent improvement as a high-value
signal rather than a quantified effect until it reproduces across additional
same-boot repeats and fresh runtime starts.

### H13: input-global-scale parameter representation

H13 starts from H12 and changes only the input-global-scale parameter objects:

- H12: plain `torch.nn.Parameter` for
  `w13_input_global_scale` / `w2_input_global_scale`;
- H13: `PerTensorScaleParameter(weight_loader=...)` for the same on-disk names.

The CT reciprocal conversion `1 / input_global_scale`, post-load assignments,
checkpoint values/names, H12 packed-weight preservation, weight scale/global
scale paths, backend selection, QSA, and MTP remain unchanged.

```bash
docker build --no-cache \
  -t vllm-orcarouter-v029-h13-ct-input-scale:v1 \
  -f scripts/Dockerfile.v029-h13-ct-input-scale \
  scripts/

./scripts/runtime/orcarouter-v029.sh preflight --profile hybrid-h13-ct-input-scale
./scripts/runtime/orcarouter-v029.sh start --profile hybrid-h13-ct-input-scale

./scripts/wait-ready.sh \
  --container qwen38-h13-ct-input-scale-v029 \
  --model hybrid-h13-ct-input-scale/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

Interpretation:

- PASS: input-scale parameter/loader representation is the remaining difference
  needed on top of H12;
- FAIL with the same 4/5 stable pattern: move next to the input-scale post-load
  assignment/name conversion itself;
- broader regression: reassess interaction between H12 object preservation and
  scale object semantics.


### H13 result: FAIL and regression versus H12

Observed on 2026-09-22:

- H13 reached READY after 621 seconds;
- changing only the input-global-scale checkpoint parameter objects to
  `PerTensorScaleParameter(weight_loader=...)` did not restore determinism;
- the 1024/128 seeded gate produced 4 unique hashes across 5 repeats;
- only runs 2 and 5 matched the H6 stable reference hash;
- this is worse than H12's single observed 5-repeat run (2 unique hashes, 4/5
  matching the H6 reference).

Therefore the H13 input-global-scale object representation is not the missing
repair and should not be carried forward as the next parent.

### H14: post-load input-scale parameter registration

H14 deliberately branches from H12, not H13. It changes only the final
compressed-tensors input-scale assignment after kernel-format conversion:

- H12: `layer.w13_input_scale = a13_scale` and
  `layer.w2_input_scale = a2_scale` leave plain Tensor attributes;
- H14: register the converted `a13_scale/a2_scale` as
  `torch.nn.Parameter` objects under the same final names.

The original `w*_input_global_scale` checkpoint objects and values, reciprocal
conversion, H12 packed-weight object preservation, all weight/global-scale
paths, backend, QSA, and MTP remain unchanged.

```bash
docker build --no-cache \
  -t vllm-orcarouter-v029-h14-ct-input-scale-postload:v1 \
  -f scripts/Dockerfile.v029-h14-ct-input-scale-postload \
  scripts/

./scripts/runtime/orcarouter-v029.sh preflight \
  --profile hybrid-h14-ct-input-scale-postload
./scripts/runtime/orcarouter-v029.sh start \
  --profile hybrid-h14-ct-input-scale-postload

./scripts/wait-ready.sh \
  --container qwen38-h14-ct-input-scale-postload-v029 \
  --model hybrid-h14-ct-input-scale-postload/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

Interpretation:

- PASS: final post-load input-scale registration/parameter semantics, together
  with H12 weight-object preservation, are sufficient for the 1024 gate;
- H12-like partial improvement: repeat with a larger same-boot sample before
  attribution;
- broad FAIL/regression: move to the remaining post-load scale_2/global-scale
  conversion and replacement semantics rather than carrying H13 forward.

### H14 result: FAIL

Observed on 2026-09-22:

- H14 reached READY after 641 seconds;
- registering the converted post-load `w13_input_scale` /
  `w2_input_scale` tensors as `torch.nn.Parameter` objects did not restore
  determinism;
- the seeded 1024/128 gate produced 5 unique hashes across 5 repeats;
- all five repeats produced different outputs;
- the runtime controls remained PLE mmap, exact QSA, prefix caching disabled,
  max_num_seqs=3, and MTP k=2.

Therefore the final post-load input-scale Tensor-vs-Parameter representation is
insufficient to explain the remaining nondeterminism. H14 is a clean negative
result and its post-load registration change must not be treated as an assumed
repair.

### H15: MTP-off runtime control

H15 is a runtime-only A/B against H14. It reuses the exact H14 image and
checkpoint and changes only speculative decoding:

- H14: MTP speculative decoding enabled with k=2;
- H15: no `--speculative-config` argument, so MTP speculative decoding is off.

Checkpoint bytes, H12/H14 compressed-tensors post-load changes, PLE mmap, exact
QSA, GB10 FLA fix, context length, prefix-cache setting, batching limits, and
container image remain unchanged. No H15 Docker image is built.

Run the control:

```bash
./scripts/runtime/orcarouter-v029.sh stop \\
  --profile hybrid-h14-ct-input-scale-postload

./scripts/runtime/orcarouter-v029.sh preflight \\
  --profile hybrid-h15-mtp-off
./scripts/runtime/orcarouter-v029.sh start \\
  --profile hybrid-h15-mtp-off

./scripts/wait-ready.sh \\
  --container qwen38-h15-mtp-off-v029 \\
  --model hybrid-h15-mtp-off/Qwen3.8-Flash-Next-Uncensored-NVFP4

python3 scripts/benchmark/run.py determinism \\
  --model hybrid-h15-mtp-off/Qwen3.8-Flash-Next-Uncensored-NVFP4 \\
  --determinism-prompt-tokens 1024 \\
  --determinism-output-tokens 128 \\
  --determinism-repeats 5 \\
  --output scripts/benchmark/results/local/h15-mtp-off-v029-det-1024.json
```

Interpretation:

- PASS: MTP participation is strongly implicated in the H14 nondeterminism and
  should be isolated further before additional CT object-semantics patches;
- FAIL with multiple hashes: MTP is not sufficient to explain the remaining
  nondeterminism; proceed to a single-sequence/runtime-scheduling control or the
  remaining CT/MoE post-load scale conversion path;
- do not compare H15 to a rebuilt or modified H14 image: the control is valid
  only when the same H14 image ID is reused.

### H15 result: FAIL

Observed on 2026-09-22:

- H15 reused `vllm-orcarouter-v029-h14-ct-input-scale-postload:v1`;
- benchmark metadata recorded `speculative_config=null`, confirming MTP was
  disabled for the measured run;
- PLE mmap, exact QSA, prefix caching disabled, max_num_seqs=3, and the H14
  checkpoint/image path remained unchanged;
- the seeded 1024/128 gate produced 4 unique hashes across 5 repeats;
- runs 1 and 2 matched each other; runs 3, 4, and 5 diverged;
- run 5 produced a hash previously observed in H14, but cross-experiment hash
  reuse is only a marker and is not proof of an identical internal path.

Therefore disabling MTP speculative decoding is not sufficient to restore
determinism. The apparent reduction from H14's 5 unique hashes to H15's 4 is
not treated as an effect-size claim from a single five-repeat sample.

The H15 boot also showed a readiness-observation anomaly: `/health` returned
ready before the waiter accepted the exact served model, while rerunning the
waiter later returned READY immediately. This is recorded as an operational
observation only and is not classified as a determinism result.

### H16: single-sequence runtime control

H16 is a runtime-only A/B against H15. It reuses the same H14 image/checkpoint,
keeps MTP disabled, and changes only:

- H15: `max_num_seqs=3`;
- H16: `max_num_seqs=1`.

All other H15 controls remain unchanged, including PLE mmap, exact QSA, GB10 FLA
fix, context length, prefix-cache setting, max batched tokens, and the container
image. No H16 Docker image is built.

Run the control:

```bash
./scripts/runtime/orcarouter-v029.sh stop \
  --profile hybrid-h15-mtp-off

./scripts/runtime/orcarouter-v029.sh preflight \
  --profile hybrid-h16-single-seq
./scripts/runtime/orcarouter-v029.sh start \
  --profile hybrid-h16-single-seq

./scripts/wait-ready.sh \
  --container qwen38-h16-single-seq-v029 \
  --model hybrid-h16-single-seq/Qwen3.8-Flash-Next-Uncensored-NVFP4

python3 scripts/benchmark/run.py determinism \
  --model hybrid-h16-single-seq/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --determinism-prompt-tokens 1024 \
  --determinism-output-tokens 128 \
  --determinism-repeats 5 \
  --output scripts/benchmark/results/local/h16-single-seq-v029-det-1024.json
```

Interpretation:

- PASS: scheduler/batching concurrency becomes strongly implicated; follow with
  a focused runtime scheduling/cudagraph control before returning to CT patches;
- FAIL with multiple hashes: max_num_seqs is not sufficient to explain the
  nondeterminism; return to the remaining CT/MoE post-load scale conversion or
  lower-level kernel/runtime isolation;
- the control is valid only if H15 and H16 reuse the same H14 image ID and H16
  metadata records both `speculative_config=null` and `max_num_seqs=1`.

### H16 result: FAIL

Observed on 2026-09-22:

- H16 reused `vllm-orcarouter-v029-h14-ct-input-scale-postload:v1`;
- benchmark metadata recorded `speculative_config=null` and
  `max_num_seqs=1`, confirming both intended runtime controls;
- PLE mmap, exact QSA, prefix caching disabled, and the H14 checkpoint/image
  remained unchanged;
- the seeded 1024/128 gate produced 4 unique hashes across 5 repeats;
- run 1 matched the H6 stable reference hash
  `44867e5c36d54b5bbec26f7c4f7c500783602a4bbc1b1545758929fc1c763670`;
- runs 2 and 3 matched each other; runs 4 and 5 diverged;
- run 5 matched the non-stable hash previously observed as H12's fifth repeat.

Therefore reducing `max_num_seqs` to one is not sufficient to restore
determinism. The repeated hashes are retained as diagnostic markers only; this
single five-repeat sample does not establish that single-sequence scheduling
improved stability.

### H17: post-load weight_scale_2 lifecycle control

The first H17 build attempt failed in the patch script before an image was
created. The failure came from an overlapping text-replacement assertion, not
from vLLM startup or inference. The corrected patch now matches the `allclose`
and contiguous-extraction blocks independently, and CI executes the patch
against an H12-shaped fixture to guard this exact failure mode.

H17 returns to H12 as the parent because H12 is the strongest observed CT-side
signal and H13-H16 did not establish a repair. H17 changes only the lifecycle of
the loaded weight-global-scale parameter objects after checkpoint loading.

The vLLM v0.29 ModelOpt path creates `w13_weight_scale_2` /
`w2_weight_scale_2` parameters under their final names before post-load kernel
conversion, then calls `replace_parameter()` on those same names. The CT path
loads the corresponding values as `w13_weight_global_scale` /
`w2_weight_global_scale`, computes reciprocal kernel scales, and only then
creates/replaces `w*_weight_scale_2`.

H17 keeps H10's loaded `PerTensorScaleParameter` objects and H12's packed-weight
object preservation, but after loading:

- moves the loaded `w13_weight_global_scale` object to
  `w13_weight_scale_2`;
- moves the loaded `w2_weight_global_scale` object to
  `w2_weight_scale_2`;
- keeps the exact reciprocal conversion values unchanged;
- lets the existing CT `replace_parameter()` calls operate on final-name
  parameters that already exist;
- leaves the input-global-scale/input-scale path unchanged.

Build and run:

```bash
docker build --no-cache \
  -t vllm-orcarouter-v029-h17-ct-weight-scale2-postload:v1 \
  -f scripts/Dockerfile.v029-h17-ct-weight-scale2-postload \
  scripts/

./scripts/runtime/orcarouter-v029.sh stop \
  --profile hybrid-h16-single-seq

./scripts/runtime/orcarouter-v029.sh preflight \
  --profile hybrid-h17-ct-weight-scale2-postload
./scripts/runtime/orcarouter-v029.sh start \
  --profile hybrid-h17-ct-weight-scale2-postload

./scripts/wait-ready.sh \
  --container qwen38-h17-ct-weight-scale2-postload-v029 \
  --model hybrid-h17-ct-weight-scale2-postload/Qwen3.8-Flash-Next-Uncensored-NVFP4

python3 scripts/benchmark/run.py determinism \
  --model hybrid-h17-ct-weight-scale2-postload/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --determinism-prompt-tokens 1024 \
  --determinism-output-tokens 128 \
  --determinism-repeats 5 \
  --output scripts/benchmark/results/local/h17-ct-weight-scale2-postload-v029-det-1024.json
```

Interpretation:

- PASS: post-load weight-scale2 object/name lifecycle becomes a strong
  root-cause candidate and should be followed by a reproduction run before
  combining it with input-scale lifecycle changes;
- FAIL with an H12-like partial pattern: repeat H12/H17 with larger same-boot
  samples before attributing an effect;
- broad FAIL: weight-scale2 lifecycle alone is insufficient; the next clean CT
  isolation target is the analogous input_global_scale -> input_scale canonical
  lifecycle, while preserving reciprocal values.

### H17 result: FAIL

Observed on 2026-09-22:

- the corrected H17 image built successfully and reached READY after 692 seconds;
- runtime metadata recorded vLLM v0.29, PLE mmap, exact QSA, prefix caching
  disabled, max_num_seqs=3, and MTP k=2;
- the seeded 1024/128 gate produced 4 unique hashes across 5 repeats;
- runs 1 and 5 matched each other at
  `910fbeaa4995c601cca46fa323dbc5dfe855aaf94b35721f8a18d5a721e4d0ee`;
- run 4 matched the H6 stable reference hash
  `44867e5c36d54b5bbec26f7c4f7c500783602a4bbc1b1545758929fc1c763670`;
- the remaining runs produced distinct hashes.

Therefore canonicalizing only the post-load
`weight_global_scale -> weight_scale_2` object/name lifecycle is not
sufficient to restore determinism. The repeated hashes are retained as
diagnostic markers only and are not interpreted as an effect-size estimate.

### H18: post-load input_scale lifecycle control

H18 returns to H12 as its parent and does not carry H17 forward. It isolates the
analogous input-scale lifecycle while keeping checkpoint bytes and reciprocal
conversion values unchanged.

After checkpoint loading H18:

- moves the loaded `w13_input_global_scale` parameter object to the final
  `w13_input_scale` name;
- moves the loaded `w2_input_global_scale` parameter object to the final
  `w2_input_scale` name;
- keeps `1 / input_scale` conversion semantics unchanged;
- replaces the converted `a13_scale` / `a2_scale` tensors through
  `replace_parameter()` on those existing final names;
- leaves the H12 weight/global-scale path unchanged, including the original
  `weight_global_scale -> weight_scale_2` behavior.

Build and run:

```bash
docker build --no-cache \
  -t vllm-orcarouter-v029-h18-ct-input-scale-lifecycle:v1 \
  -f scripts/Dockerfile.v029-h18-ct-input-scale-lifecycle \
  scripts/

./scripts/runtime/orcarouter-v029.sh stop \
  --profile hybrid-h17-ct-weight-scale2-postload

./scripts/runtime/orcarouter-v029.sh preflight \
  --profile hybrid-h18-ct-input-scale-lifecycle
./scripts/runtime/orcarouter-v029.sh start \
  --profile hybrid-h18-ct-input-scale-lifecycle

./scripts/wait-ready.sh \
  --container qwen38-h18-ct-input-scale-lifecycle-v029 \
  --model hybrid-h18-ct-input-scale-lifecycle/Qwen3.8-Flash-Next-Uncensored-NVFP4

python3 scripts/benchmark/run.py determinism \
  --model hybrid-h18-ct-input-scale-lifecycle/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --determinism-prompt-tokens 1024 \
  --determinism-output-tokens 128 \
  --determinism-repeats 5 \
  --output scripts/benchmark/results/local/h18-ct-input-scale-lifecycle-v029-det-1024.json
```

Interpretation:

- PASS: post-load input-scale lifecycle becomes a strong root-cause candidate;
  reproduce H18 before combining it with the H17 weight-scale2 lifecycle;
- H12-like partial convergence: repeat H12/H18 with larger same-boot samples
  before making a causal claim;
- broad FAIL: input-scale lifecycle alone is also insufficient, leaving a
  combined post-load lifecycle control or lower-level kernel-format conversion
  as the next isolation target.

### H18 result: FAIL

Observed on 2026-09-22:

- H18 built successfully and reached READY after 641 seconds;
- runtime metadata recorded vLLM v0.29, PLE mmap, exact QSA, prefix caching
  disabled, max_num_seqs=3, and MTP k=2;
- the seeded 1024/128 determinism gate produced 5 unique hashes across 5
  repeats;
- no repeat matched the H6 stable reference hash;
- hashes previously observed in other experiments reappeared, but cross-run
  hash reuse remains only a diagnostic marker.

Therefore canonicalizing only the post-load
`input_global_scale -> input_scale` final-name/object lifecycle is not
sufficient to restore determinism. H18 is a clean broad negative result.

### H19: combined post-load scale lifecycle control

H19 returns to H12 and combines exactly the already-tested H17 and H18
post-load lifecycle changes. It does not introduce a new checkpoint transform
or a new numerical scale conversion.

The H19 image applies the two existing patches sequentially to the H12 parent:

1. H17 canonicalizes `weight_global_scale -> weight_scale_2` before kernel
   conversion and lets the converted weight scale_2 tensors replace those
   existing final-name parameters.
2. H18 canonicalizes `input_global_scale -> input_scale` before kernel
   conversion and lets the converted input-scale tensors replace those existing
   final-name parameters.

Checkpoint bytes, reciprocal values, H12 packed-weight preservation, backend,
QSA, MTP, batching, and cache controls remain unchanged.

Build and run:

```bash
docker build --no-cache \
  -t vllm-orcarouter-v029-h19-ct-combined-lifecycle:v1 \
  -f scripts/Dockerfile.v029-h19-ct-combined-lifecycle \
  scripts/

./scripts/runtime/orcarouter-v029.sh stop \
  --profile hybrid-h18-ct-input-scale-lifecycle

./scripts/runtime/orcarouter-v029.sh preflight \
  --profile hybrid-h19-ct-combined-lifecycle
./scripts/runtime/orcarouter-v029.sh start \
  --profile hybrid-h19-ct-combined-lifecycle

./scripts/wait-ready.sh \
  --container qwen38-h19-ct-combined-lifecycle-v029 \
  --model hybrid-h19-ct-combined-lifecycle/Qwen3.8-Flash-Next-Uncensored-NVFP4

python3 scripts/benchmark/run.py determinism \
  --model hybrid-h19-ct-combined-lifecycle/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --determinism-prompt-tokens 1024 \
  --determinism-output-tokens 128 \
  --determinism-repeats 5 \
  --output scripts/benchmark/results/local/h19-ct-combined-lifecycle-v029-det-1024.json
```

Interpretation:

- PASS: the weight-scale2 and input-scale lifecycle changes have a meaningful
  interaction; reproduce H19 before any broader attribution;
- H12-like partial convergence: expand same-boot repeats and compare directly
  against a fresh H12 run before calling it an interaction effect;
- broad FAIL: final-name/object lifecycle alignment is insufficient even in
  combination. Stop adding wrapper-only CT patches and move to tensor-level
  diagnostics around `convert_to_nvfp4_moe_kernel_format()` to locate the
  first CT-vs-ModelOpt divergence.

### H19 result: FAIL

Observed on 2026-09-22:

- H19 built successfully and reached READY after 621 seconds;
- runtime metadata recorded vLLM v0.29, PLE mmap, exact QSA, prefix caching
  disabled, max_num_seqs=3, and MTP k=2;
- the seeded 1024/128 determinism gate produced 5 unique hashes across 5
  repeats;
- run 3 matched the H6 stable reference hash
  `44867e5c36d54b5bbec26f7c4f7c500783602a4bbc1b1545758929fc1c763670`;
- all five H19 repeats were mutually distinct.

Therefore combining the H17 weight-scale2 lifecycle and H18 input-scale
lifecycle changes is also insufficient. H17-H19 close the wrapper/final-name
object-lifecycle branch: do not add further wrapper-only CT patches without new
tensor-level evidence.

### H20: NVFP4 MoE kernel-format conversion diagnostics

H20 is a diagnostic, not another determinism-fix patch. It compares the H12 CT
path against the deterministic H6 ModelOpt/W4A16 path at the boundary of
`convert_to_nvfp4_moe_kernel_format()`.

Two images are used:

- `vllm-orcarouter-v029-h20-ct-convert-diag:v1`: H12 CT parent plus
  conversion fingerprint instrumentation;
- `vllm-orcarouter-v029-h20-modelopt-convert-diag:v1`: the shared v0.29 base
  plus the same normalized instrumentation in `ModelOptNvFp4FusedMoE`, run
  against the H6 checkpoint.

For each of the first four routed-expert conversion calls, H20 records both
`pre` and `post` phases using the same tensor names:

- `w13`, `w13_scale`, `w13_scale_2`, `a13_scale`;
- `w2`, `w2_scale`, `w2_scale_2`, `a2_scale`.

Each fingerprint includes shape, dtype, stride, contiguous state, numel, byte
size, device, storage offset, and a SHA-256 digest. Tensors up to 1 MiB are
hashed in full. Larger contiguous tensors use a deterministic
head/middle/tail sample (1024 elements per window) so diagnostics do not copy
entire expert weights back to the CPU. Large non-contiguous tensors are
metadata-only. A matching sampled digest is useful evidence but is not proof
that every byte of a large tensor is identical.

Build both diagnostic images:

```bash
docker build --no-cache \
  -t vllm-orcarouter-v029-h20-ct-convert-diag:v1 \
  -f scripts/Dockerfile.v029-h20-ct-convert-diag \
  scripts/

docker build --no-cache \
  -t vllm-orcarouter-v029-h20-modelopt-convert-diag:v1 \
  -f scripts/Dockerfile.v029-h20-modelopt-convert-diag \
  scripts/
```

Collect the CT side first:

```bash
./scripts/runtime/orcarouter-v029.sh stop \
  --profile hybrid-h19-ct-combined-lifecycle

./scripts/runtime/orcarouter-v029.sh preflight \
  --profile hybrid-h20-ct-convert-diag
./scripts/runtime/orcarouter-v029.sh start \
  --profile hybrid-h20-ct-convert-diag

./scripts/wait-ready.sh \
  --container qwen38-h20-ct-convert-diag-v029 \
  --model hybrid-h20-ct-convert-diag/Qwen3.8-Flash-Next-Uncensored-NVFP4

python3 scripts/diagnostics/h20-nvfp4-moe.py collect \
  --container qwen38-h20-ct-convert-diag-v029 \
  --output scripts/benchmark/results/local/h20-ct-convert-diag.jsonl

./scripts/runtime/orcarouter-v029.sh stop \
  --profile hybrid-h20-ct-convert-diag
```

Then collect the deterministic ModelOpt/H6 side:

```bash
./scripts/runtime/orcarouter-v029.sh preflight \
  --profile hybrid-h20-modelopt-convert-diag
./scripts/runtime/orcarouter-v029.sh start \
  --profile hybrid-h20-modelopt-convert-diag

./scripts/wait-ready.sh \
  --container qwen38-h20-modelopt-convert-diag-v029 \
  --model hybrid-h20-modelopt-convert-diag/Qwen3.8-Flash-Next-Uncensored-NVFP4

python3 scripts/diagnostics/h20-nvfp4-moe.py collect \
  --container qwen38-h20-modelopt-convert-diag-v029 \
  --output scripts/benchmark/results/local/h20-modelopt-convert-diag.jsonl
```

Compare the normalized records:

```bash
python3 scripts/diagnostics/h20-nvfp4-moe.py compare \
  --ct scripts/benchmark/results/local/h20-ct-convert-diag.jsonl \
  --modelopt scripts/benchmark/results/local/h20-modelopt-convert-diag.jsonl \
  --output scripts/benchmark/results/local/h20-ct-vs-modelopt.json
```

Interpretation:

- first mismatch in `pre`: the normalized values/layout entering conversion
  still differ; focus on checkpoint normalization, loader semantics, or the
  exact reciprocal/global-scale representation before the kernel converter;
- `pre` matches but the first mismatch appears in `post`: isolate
  `convert_to_nvfp4_moe_kernel_format()`, backend selection, or hidden
  layout/state used by that conversion;
- both `pre` and `post` match for the sampled calls: inspect the H20-B
  `quant_config`, `kernel_created`, and `fused_postload` records before
  creating another numbered experiment.

#### H20-A observed result and comparator correction

The first local H20-A run collected 8 records on each side (calls 0-3,
pre/post). The original comparator incorrectly classified `None` vs `None`
activation-scale outputs as mismatches, so its reported
`first_mismatch=... phase=post tensor=a13_scale` was a tooling bug.

Direct record inspection showed:

- CT and ModelOpt used `NvFp4MoeBackend.MARLIN` with `use_a16=true`;
- sampled/full hashes for `w13`, `w2`, `w13_scale`, `w2_scale`,
  `w13_scale_2`, and `w2_scale_2` matched after conversion for the observed
  calls;
- the pre-conversion activation-scale hashes differed, but W4A16/Marlin
  returned `a13_scale=None` and `a2_scale=None` on both sides.

The comparator now treats `None` vs `None` as equal. Existing H20-A JSONL
files can therefore be re-compared after pulling the fix; no re-run is required
for that correction.

#### H20-B post-conversion localization

The first H20-B ModelOpt v2 build attempt failed before runtime because the
patcher searched the entire `ModelOptNvFp4FusedMoE` class for
`routing_tables=layer._expert_routing_tables()` and incorrectly required that
text to occur exactly once. v0.29 contains additional routed-expert methods
with the same expression. This is a patch-application/build failure, not an
H20 diagnostic result. The corrected patcher scopes all kernel-creation
replacements to `process_weights_after_loading()` only, and the regression
fixture includes an additional method with the same routing-table expression.

The same H20 image/profile names are retained, but the image label is bumped to
v2 so stale H20-A images are rejected. Rebuild both images and repeat the
collection. Each call now emits three additional state records:

- `quant_config`: normalized snapshot of the fused-MoE quant config, MoE
  config, experts class, and routing tables;
- `kernel_created`: normalized kernel and fused-experts state immediately
  after `make_nvfp4_moe_kernel()`;
- `fused_postload`: state plus final layer tensor fingerprints after
  `fused_experts.process_weights_after_loading()`.

The snapshot recursion depth and collection sizes are bounded. Large tensors
continue to use the existing bounded fingerprint policy.

Because experimental `stop` intentionally preserves stopped containers for
diagnostics, remove an old H20 container before starting a rebuilt image:

```bash
./scripts/runtime/orcarouter-v029.sh stop \
  --profile hybrid-h20-ct-convert-diag \
  --remove

./scripts/runtime/orcarouter-v029.sh stop \
  --profile hybrid-h20-modelopt-convert-diag \
  --remove
```

It is safe for either command to report that the corresponding container is
already absent. Do not delete collected JSONL files when removing containers.

After rebuilding/rerunning both sides, use the same compare command. The first
real mismatch now localizes the remaining search:

- `quant_config`: config/routing/expert-class construction differs;
- `kernel_created`: kernel/backend internal setup diverges despite matching
  converter outputs;
- `fused_postload`: downstream expert post-load processing creates the first
  observable difference;
- no material mismatch through `fused_postload`: move next to a single
  first-token MoE input/output trace inside H20 rather than creating H21.

#### H20-B observed result

Observed on 2026-09-22 after the scoped-anchor hotfix:

- both v3-predecessor H20-B images built successfully;
- CT/H12 reached READY and produced 20 records:
  4 calls x 5 phases (`pre`, `post`, `quant_config`,
  `kernel_created`, `fused_postload`);
- ModelOpt/H6 reached READY and produced the same 20-record shape;
- comparison reported `common_records=20`, `only_ct=0`,
  `only_modelopt=0`;
- the only 8 tensor mismatches were the four calls' pre-conversion
  `a13_scale` / `a2_scale` fingerprints;
- no additional state mismatch appeared in `quant_config`,
  `kernel_created`, or `fused_postload`.

This keeps the activation-scale representation difference as a known
pre-conversion difference, but it does not survive the W4A16/Marlin conversion
boundary and no downstream load-time state divergence was observed. The next
localization step therefore remains inside H20 and moves to actual runtime MoE
execution.

#### H20-C runtime first-token MoE trace

H20-C keeps the same H20 profile/image names. The initial v3 implementation
patched `FusedMoEModularMethod.apply()`, but the v0.29 NVFP4 paths under test
already own an internal modular kernel (`supports_internal_mk=True`) and call
their quant-method `apply()` directly. Both CT and ModelOpt v3 requests
completed successfully but emitted zero `QWEN38_H20C_RUNTIME` records. This
was an instrumentation-location failure, not a model/runtime comparison result.

The corrected v4 images patch the actual runtime methods instead:

- CT: `CompressedTensorsW4A4Nvfp4MoEMethod.apply()`;
- ModelOpt: `ModelOptNvFp4FusedMoE.apply()`.

Both methods receive the already-selected expert routing tensors and directly
call `moe_kernel.apply()`. The READY-time trigger test is isolated behind
`torch.compiler.disable` so the file-existence condition is re-evaluated at
runtime instead of being frozen during torch.compile/warmup.

The runtime trace is disabled during startup/warmup. The `trace` command
enables it only after READY via a container-local trigger file, then sends the
same fixed request twice. Each traced MoE call records:

- `layer_name`;
- request id and call index;
- pre-call `x`, `topk_weights`, `topk_ids`,
  `shared_experts_input`;
- post-call MoE `output`;
- the same bounded full/sample SHA-256 fingerprint policy used by H20-A/B.

Rebuild both H20 images after pulling the H20-C internal-MK hotfix because the image labels are v4.


The failed v3 trace attempt also exposed a CLI rough edge: because neither
runtime JSONL existed, `runtime-compare` raised `FileNotFoundError`.
The CLI now reports missing trace files cleanly and instructs the operator to
run both trace commands successfully before comparing.

CT/H12 runtime trace:

```bash
./scripts/runtime/orcarouter-v029.sh stop \
  --profile hybrid-h20-ct-convert-diag \
  --remove

./scripts/runtime/orcarouter-v029.sh preflight \
  --profile hybrid-h20-ct-convert-diag
./scripts/runtime/orcarouter-v029.sh start \
  --profile hybrid-h20-ct-convert-diag

./scripts/wait-ready.sh \
  --container qwen38-h20-ct-convert-diag-v029 \
  --model hybrid-h20-ct-convert-diag/Qwen3.8-Flash-Next-Uncensored-NVFP4

python3 scripts/diagnostics/h20-nvfp4-moe.py trace \
  --container qwen38-h20-ct-convert-diag-v029 \
  --model hybrid-h20-ct-convert-diag/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --repeats 2 \
  --output scripts/benchmark/results/local/h20c-ct-runtime.jsonl
```

Then stop/remove CT and run the same trace on ModelOpt/H6:

```bash
./scripts/runtime/orcarouter-v029.sh stop \
  --profile hybrid-h20-ct-convert-diag \
  --remove

./scripts/runtime/orcarouter-v029.sh preflight \
  --profile hybrid-h20-modelopt-convert-diag
./scripts/runtime/orcarouter-v029.sh start \
  --profile hybrid-h20-modelopt-convert-diag

./scripts/wait-ready.sh \
  --container qwen38-h20-modelopt-convert-diag-v029 \
  --model hybrid-h20-modelopt-convert-diag/Qwen3.8-Flash-Next-Uncensored-NVFP4

python3 scripts/diagnostics/h20-nvfp4-moe.py trace \
  --container qwen38-h20-modelopt-convert-diag-v029 \
  --model hybrid-h20-modelopt-convert-diag/Qwen3.8-Flash-Next-Uncensored-NVFP4 \
  --repeats 2 \
  --output scripts/benchmark/results/local/h20c-modelopt-runtime.jsonl
```

Compare both runtime traces:

```bash
python3 scripts/diagnostics/h20-nvfp4-moe.py runtime-compare \
  --ct scripts/benchmark/results/local/h20c-ct-runtime.jsonl \
  --modelopt scripts/benchmark/results/local/h20c-modelopt-runtime.jsonl \
  --output scripts/benchmark/results/local/h20c-ct-vs-modelopt.json
```

The comparator normalizes each source by request id and per-request MoE-call
ordinal, rather than assuming global call indices match across boots. It also
reports repeat stability independently for CT and ModelOpt.

Interpretation:

- first mismatch in pre `x`: divergence already exists before that MoE call;
  the previous layer/residual/attention path becomes the next boundary;
- `x` matches but `topk_weights` or `topk_ids` differs: the router path is
  the first observed runtime divergence;
- all pre tensors match but `output` differs: the routed MoE kernel execution
  itself is the first observed divergence;
- CT request 0 vs 1 diverges before the CT-vs-H6 comparison point: prioritize
  that within-CT first mismatch because it directly localizes nondeterminism;
- all traced MoE calls match across both requests and both sources: continue
  H20 with the next non-MoE runtime boundary instead of creating H21.
