## 2026-10-19 — catplusplus installation and benchmark gating update

Actual DGX HEAD (no body): both pinned `resolve`
files produced 307→same-HF-host API cache, while both
pinned `raw` paths gave 200. The maintained **source-only**
Wizard 5→23→7 now uses bounded pinned `raw` GET/no
redirect; physical GET declarations are **NOT_RUN**.
Wizard **5→23→9** is the static installation/loader/memory/
benchmark plan and **5→23→10** is lock-aware read-only disk
screen. The engine, PLE-offload peak, exact-ID protected run,
model API and actual catplusplus benchmark remain
**NOT_QUALIFIED / NOT_MEASURED**.
**mazinb R2 download is active**: no simultaneous catplusplus
weights/Docker/GPU work permitted. See
[complete source-only engineering runbook](../CATPLUSPLUS-SINGLE-GB10-INSTALL-SERVE-BENCH.md).

## Pinned model/source compatibility tool — still NOT a qualified loader

Source-only M1 Wizard **5 -> 23 -> 7** compares the
immutable catplusplus mixed-precision config and official
SGLang launcher declarations using two capped small-text
requests. The new
`scripts/model/audit_catplusplus_loader_source.py`
does not import or run publisher scripts and reports SHA256
hashes plus security-relevant launch hazards.
It does **not** inspect safetensors or establish executable
GB10 wheel support, peak unified-memory residency or MTP
correctness. Even a positive declaration result leaves
all live-start and benchmark gates blocked. Synthetic
offline tests cover fused qkvz alias, FP8 PLE, missing
flags, redirect/symlink/oversized refusal and no weight fetch.

# catplusplus — single-DGX benchmark preparation

**BENCHMARK_STATUS: NOT_MEASURED**

**CHECKPOINT_STATUS: RESEARCH_ONLY / NOT_REGISTERED / NOT_DOWNLOADED / GPU_NOT_TESTED** according to the last actual DGX L0 metadata inspection. This document is a source-only benchmark **plan**, not a successful model installation, inference run or benchmark report.

## mazinb M1-style session implementation status (source-only)

Wizard Benchmark **5 -> 23** presents the *same six lifecycle
actions* as mazinb M1: plan, status, preflight, benchmark admission,
live-start gate and journal reconciliation, plus **option 7** for a
bounded, pinned config/SGLang launcher text-only source audit. The full exact-ID
create-only/watchdog-before-start/READY/180s soak/smoke/Terminal-B
bench/STOP/evidence lifecycle is documented as a **contract only**.
`scripts/runtime/catplusplus-m1.py` intentionally rejects
preflight, GPU start and benchmark admission until checkpoint,
mixed-MXFP8/FP8 PLE loader, memory/offload, image and separate
owner approval are qualified. This is **not a runnable trial**.
Actual catplusplus throughput, TTFT and safety remain
**NOT_MEASURED**. See [catplusplus M1 Wizard contract](../CATPLUSPLUS-M1-WIZARD.md).
## Immutable target and prior physical metadata evidence

| Item | Recorded value | Qualification |
|---|---|---|
| Checkpoint | `catplusplus/Qwen3.8-Flash-Next-uncensored-NVFP4-mixed` | Research candidate; not in selectable model registry |
| Hub revision | `3251fd8afbd08f76368a9bfa71132d9aef364813` | Pinned |
| Actual DGX metadata | 17,448 repository entries; 96 `.safetensors` files | `TREE_METADATA_COMPLETE`, metadata only |
| Total repository size | 188,540,029,444 bytes ≈ 175.59 GiB | Actual pinned complete tree; NOT required-download minimum |
| Root weights | ≈ 174.8553 GiB | **Rounded** actual DGX inventory output, not exact bytes or resident RAM |
| DGX Spark RAM | 128 *decimal* GB ≈ 119.21 GiB | Nominal unified-memory capacity, not measured free memory |
| Model loader | ModelOpt MIXED_PRECISION, MXFP8 qkvz, NVFP4 experts, FP8 PLE | Source/format compatibility **not qualified** |
| Actual runtime/image ID | NOT_VERIFIED | No candidate container or API READY |
| GPU and benchmark | **NOT_MEASURED** | No authorisation to start |

The plain fully-resident, unchanged-weights case exceeds nominal single-GB10 physical RAM *before* CUDA buffers, KV cache, startup staging and safety margin. Partial residency, carefully bound NVMe offload or checkpoint transformation might eventually be viable, but have **not** been demonstrated on this DGX. Do not equate author/publisher claims with local results. Full pinned inventory and per-source limitations: [catplusplus metadata compatibility](../CATPLUSPLUS-METADATA-COMPATIBILITY.md).

## Planned fair mazinb M1 baseline comparison (not measured for catplusplus)

Protocol uses pinned [llama-benchy](https://github.com/eugr/llama-benchy) revision `e9be344578cec17745066b220798b80a0d2686d3`, concurrency 1, context size 0, prefix caching disabled, generation latency mode, one warmup and three measured repeats per shape.

| Metric | catplusplus PP512/TG128 | catplusplus PP2048/TG128 | Real mazinb M1 reference |
|---|---|---|---|
| Prompt-processing throughput | NOT_MEASURED | NOT_MEASURED | 1115.21 ± 428.53 / 1597.94 ± 53.31 tok/s |
| Token-generation throughput | NOT_MEASURED | NOT_MEASURED | 23.11 ± 1.05 / 22.54 ± 1.68 tok/s |
| E2E TTFT | NOT_MEASURED | NOT_MEASURED | 758.40 ± 296.44 / 1469.04 ± 43.43 ms |
| API READY | NOT_VERIFIED | NOT_VERIFIED | mazinb M1 was READY in its historical approved session |
| Host memory/RM stability | NOT_VERIFIED | NOT_VERIFIED | mazinb long-term host qualification remains inconclusive |

The two mazinb entries in each reference cell correspond to PP512 and PP2048 respectively; they are historical actual DGX data, **not predictions for catplusplus**. Model quantization, runtime and hardware memory policies can differ; do not claim a controlled head-to-head comparison until their provenance is normalized.

## Wizard-first workflow and exact safety gates

The operator enters **`./wizard.sh` → 5 Benchmark → 22 catplusplus M0 benchmark plan (read-only)**. This calls maintained `scripts/benchmark/catplusplus-plan.py plan`, outputs the immutable candidate and two shapes, and marks `CATPLUSPLUS_ADMISSION=BLOCKED_MODEL_LOADER_MEMORY_AND_LIVE_AUTHORIZATION` and `CATPLUSPLUS_BENCHMARK_STATUS=NOT_MEASURED`. It does **not** write host files, download or open safetensors, call the serving API, create a Docker container, launch GPU processes or alter services. The optional `--json` prints the **plan**, with `measurements=null`, never synthetic results.

Before a live session can even be proposed for separate approval:
1. Bind exact immutable HF weight-file identities, minimal actual inference payload, total free storage, available RAM and evidence archiving limits. No checkpoint download is currently authorized.
2. Confirm the target engine's exact source/wheel actually consumes the mixed NVFP4 + MXFP8 fused qkvz scales and global FP8 PLE table, with MTP behavior tracked separately; a generic `pip install vllm` example or upstream README is not single-GB10 evidence.
3. Establish a bounded weight-residency/offload and peak allocation strategy compatible with GPU/NVIDIA RM, host memory/swap protections and reserve. Do not infer swap availability equals safe GPU addressability.
4. Implement the model/backend option in the **shared Wizard** as disabled until qualification; protected existing managed/OrcaRouter A/B Docker IDs remain untouched. An isolated named candidate requires create-only and exact-ID watchdog-armed-before-start control with strict fail-closed admission.
5. With separate explicit owner approval, collect a protected actual DGX startup, precise API `/health` and `/v1/models` identity, correctness/smoke evidence, 180-second post-ready stability and safe termination first.
6. Only **after** that, run the existing frozen llama-benchy shapes, preserve raw JSON/CLI+version, pinned model/source/image/release identities, kernel RM/memory snapshots, hashes and post-trial state. Use `scripts/benchmark/llama-benchy-report.py --profile catplusplus` with **real** JSON; the converter refuses unknown model IDs, invalid numeric data and missing measurements.

**No live runner, installation, GPU, bulk download, benchmark run or ordinary Wizard model switch is approved or implemented by this M0 plan.**

## Status markers

```text
CATPLUSPLUS_METADATA=ACTUAL_DGX_PINNED_L0_TREE_METADATA_COMPLETE_20261016
CATPLUSPLUS_PLAN=SOURCE_ONLY
CATPLUSPLUS_LOADER=NOT_QUALIFIED
CATPLUSPLUS_WEIGHT_DOWNLOAD=NOT_AUTHORIZED
CATPLUSPLUS_RUNTIME_READY=NOT_MEASURED
CATPLUSPLUS_BENCHMARK_STATUS=NOT_MEASURED
CATPLUSPLUS_HOST_PROTECTION=NOT_ATTESTED
CATPLUSPLUS_INSTALL_SWITCH=DISABLED_RESEARCH_ONLY
```
