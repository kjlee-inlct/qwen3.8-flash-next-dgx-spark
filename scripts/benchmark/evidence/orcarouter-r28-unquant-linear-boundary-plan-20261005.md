# OrcaRouter R28 — unquantized Linear construction boundary plan — 2026-10-05

## Status

**IMPLEMENTED IN REPOSITORY — CI / STATIC IMAGE / HARNESS PREFLIGHT REQUIRED — NO LIVE RUN AUTHORIZED YET**

Canonical predecessors:

- `scripts/benchmark/evidence/orcarouter-r27-linear-residual-result-20261005.md`
- `scripts/benchmark/evidence/orcarouter-r27-h6-quant-routing-inspection-result-20261005.md`

R27 is closed as:

**VALID_MEASURED — FUNCTIONAL PASS / HOST-STABILITY FAIL — `RM_ORDER4_R26_RESIDUAL_MIXED_WITHIN_QWEN4_LAYERS`**

The follow-up read-only routing inspection is also closed PASS and explains why R27 observed zero `ModelOptNvFp4W4A16LinearMethod.create_weights()` calls: the relevant Qwen4Exp attention families are excluded from ModelOpt quantization and route through unquantized Linear construction, with an additional explicit QSA qkv opt-out.

## Objective

Measure whether `UnquantizedLinearMethod.create_weights()` temporally explains the R26 non-MoE constructor residual.

R27 localized approximately `39,148.250 MiB` of non-MoE direct-RM order-4 activity inside decoder-layer intervals. Static source/config inspection shows that ordinary BF16 parameter payload is much smaller than that RM activity. Therefore R28 must keep two quantities separate:

1. direct-RM logical requested bytes — allocation activity volume;
2. nominal `torch.empty` weight tensor bytes — parameter payload.

Neither quantity is exact resident ownership.

## Marker scope

Patch:

- `scripts/patch-v029-r28-unquant-linear-markers.py`

The patch touches only vLLM v0.29 `UnquantizedLinearMethod.create_weights()` in `linear.py`.

Markers:

- `QWEN38_R28_UNQUANT_LINEAR_BEGIN`
- `QWEN38_R28_UNQUANT_LINEAR_END`

BEGIN records:

- sequence ID;
- exact `layer.prefix`;
- Linear subclass;
- input partition width;
- summed output partition width;
- nominal element count;
- parameter dtype.

The marker interval begins immediately before the existing `ModelWeightParameter(data=torch.empty(...))` allocation and ends after the existing parameter registration attributes are applied. It does not change tensor shapes, dtype, allocation API, parameter class, quantization routing, or checkpoint data.

## Diagnostic image

Dockerfile:

- `scripts/Dockerfile.v029-r28-unquant-linear-markers`

Image tag to build:

`vllm-orcarouter-v029-r28-unquant-linear-marker:v1`

Parent:

`vllm-orcarouter-v029-r27-linear-marker:v1`

The image therefore inherits:

- R26 top-level constructor markers;
- R26 ModelOpt-MoE markers;
- R27 Qwen4Exp decoder-layer markers;
- the exact H6/R22-matched runtime behavior.

New label:

`qwen38.r28=unquant-linear-boundary-v1`

## Static image gate

Checker:

- `scripts/benchmark/check-orcarouter-r28-unquant-linear-image.sh`

The checker must pass inherited R25/R26/R27 labels, inherited R26/R27 marker contracts, exact R28 marker count, `UnquantizedLinearMethod` source identity, and the unchanged `data=torch.empty(...)` allocation contract.

Static build/check must not restart or mutate the managed runtime.

## Analyzer

Analyzer:

- `scripts/benchmark/analyze-orcarouter-r28-unquant-linear-overlap.py`

It reports:

- total / constructor direct-RM order-4 activity;
- inherited R26 ModelOpt-MoE activity;
- R26 residual outside ModelOpt-MoE;
- union of R28 unquantized Linear intervals;
- R28 activity inside the R26 residual;
- percentage of the R26 residual covered by R28 intervals;
- nominal unquantized weight payload;
- diagnostic RM-activity / nominal-payload ratio;
- residual left uncovered;
- per-family calls, RM activity and nominal payload for:
  - `linear_attn`;
  - `self_attn`;
  - `hyper_connection`;
  - `shared_expert`;
  - `router`;
  - `ple`;
  - `other`;
- highest-RM individual unquantized calls.

The ratio is diagnostic only. It must not be described as resident-memory amplification without additional evidence.

Primary threshold: `90%` of the R26 residual.

Possible discriminators:

- `RM_ORDER4_R26_RESIDUAL_PRIMARY_IN_UNQUANTIZED_LINEAR_CONSTRUCTION`
- `RM_ORDER4_R26_RESIDUAL_MIXED_OUTSIDE_UNQUANTIZED_LINEAR_CONSTRUCTION`

## Guarded harness

Runner:

- `scripts/benchmark/run-orcarouter-r28-unquant-linear-boundary.sh`

Default mode is `--preflight`.

The runner reuses the validated R24 H6/R22-matched harness through an ephemeral transform, with a fresh `r28_rm` probe group and experiment container. It preserves R24, R26 and R27 evidence and refuses an existing R28 evidence directory.

Fresh default evidence path:

`/tmp/orcarouter-hybrid-r28-unquant-linear-boundary-01-20261005`

Experiment container:

`qwen38-hybrid-r28-unquant-linear-marker`

A future live run requires explicit `ORCA_R28_LIVE_ACK=YES`, but **this plan does not authorize a live run yet**.

## Trace scope and policy

Keep only the already validated narrow trace:

- `nv_alloc_pages`;
- `nv_alloc_system_pages`;
- static kernel-error capture.

Do not broaden to UVM, generic page allocation, scheduler, function graph, CUDA API blanket tracing, Python profiling, or PLE page-fault tracing.

Strict policy remains: any confirmed NVIDIA RM `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` in a valid measured run is **HOST-STABILITY FAIL**, even if fallback recovers and the runtime reaches READY. FUNCTIONAL and HOST-STABILITY classifications remain separate.

RM logical requested bytes remain allocation activity volume, not exact resident ownership. Marker overlap remains temporal localization, not causal proof.

## Gate sequence

1. repository CI — required;
2. build R28 marker-only image — required;
3. static R28 image preflight — required;
4. verify managed container ID / StartedAt unchanged across static work — required;
5. guarded R28 harness `--preflight` — required;
6. verify fresh evidence path/container remain absent after preflight — required;
7. canonicalize static/harness preflight evidence — required;
8. only then decide whether one live R28 measurement is authorized.

Do not apply H11 before this discriminator closes.

PR #244 remains open. No merge is implied or authorized.
