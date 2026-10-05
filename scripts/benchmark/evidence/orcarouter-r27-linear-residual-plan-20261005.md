# OrcaRouter R27 — W4A16-linear / Qwen4Exp residual-constructor plan — 2026-10-05

## Status

**IMPLEMENTED — REPOSITORY CI PASS — STATIC IMAGE GATE PASS — HARNESS PREFLIGHT PASS — ONE LIVE MEASURED RUN AUTHORIZED NEXT**

R26 is closed as:

**VALID_MEASURED — FUNCTIONAL PASS / HOST-STABILITY FAIL — `RM_ORDER4_MIXED_WITHIN_MODEL_CONSTRUCTOR`**

Canonical predecessor:

- `scripts/benchmark/evidence/orcarouter-r26-construction-boundary-result-20261005.md`

R27 prerequisite gates:

- static image: `scripts/benchmark/evidence/orcarouter-r27-linear-image-preflight-result-20261005.md`
- harness preflight: `scripts/benchmark/evidence/orcarouter-r27-live-harness-preflight-result-20261005.md`

Both are CLOSED/PASS.

R26 reproduced `77,405.938 MiB` total direct-NVIDIA-RM order-4 activity, with `76,846.250 MiB` (`99.276945%`) inside the first top-level model constructor, `559.688 MiB` before it, and `0.000 MiB` after it. `ModelOptNvFp4FusedMoE.create_weights()` accounted for `34,292.000 MiB` (`44.301511%` of total), leaving `42,554.250 MiB` elsewhere in the constructor.

R27 is an observational discriminator for that `42,554.250 MiB` residual. It does not test a mitigation.

## Why H11 remains deferred

R26 showed that packed routed-expert w13+w2 allocations are real contributors:

- packed w13+w2: `29,976.000 MiB`;
- `87.413974%` of the ModelOpt-MoE contribution;
- `38.725711%` of total order-4 RM activity.

But the constructor activity outside ModelOpt-MoE (`42,554.250 MiB`) is larger than the entire ModelOpt-MoE contribution. Changing H11-like expert parameter semantics now would alter only one major component while leaving a larger unlocalized component, confounding causal interpretation.

Therefore R27 measures the residual before any H11 behavior change.

## Exact active architecture

The matched v0.29 image uses the NVIDIA Qwen4Exp implementation:

`/usr/local/lib/python3.12/dist-packages/vllm/models/qwen4_exp/nvidia/model.py`

The top-level model is `Qwen4ExpForCausalLM`. `Qwen4ExpModel` constructs the embedding, then decoder layers through `make_layers(...)`, then the final hyper-connection mixer. `Qwen4ExpDecoderLayer` constructs PLE where configured, linear-attention or full/QSA attention, MoE/MLP, and two hyper-connection branches.

The active checkpoint/runtime family has 48 decoder layers with hybrid linear/full attention. R27 instruments the exact `Qwen4ExpDecoderLayer` path.

## PLE constructor exclusion

The matched runtime explicitly enables:

```text
VLLM_PLE_MMAP=1
VLLM_PLE_MMAP_DIR=/model
VLLM_PLE_MMAP_PREWARM=0
```

The v0.29 base image applies the mmap patch to `Qwen4ExpNGramEmbedding`. The patch substitutes a small `_MmapNgramEmbedding` placeholder during constructor execution and invokes the stock PLE constructor with `quant_config=None`; the giant N-gram table is not materialized as a stock embedding parameter during constructor execution and is later mmap-backed.

R27 static preflight revalidated this as:

`r27_ple_mmap_placeholder_contract=PASS`

Therefore R27 does not broaden into PLE table/page-fault tracing.

## Highest-information remaining allocation boundary

vLLM v0.29 `ModelOptNvFp4W4A16LinearMethod.create_weights()` allocates:

1. packed NVFP4 `weight` as `ModelWeightParameter(torch.empty(..., dtype=torch.uint8))`;
2. `weight_scale_2`;
3. per-group `weight_scale`;
4. placeholder `input_scale`.

R27 measures the complete W4A16-linear `create_weights()` interval and the packed `weight` allocation sub-interval. This tests whether the R26 non-MoE residual is mostly ordinary ModelOpt W4A16 linear storage construction.

## R27 marker-only image

Patch:

- `scripts/patch-v029-r27-linear-boundary-markers.py`

Markers:

- `QWEN38_R27_W4A16_LINEAR_BEGIN/END`;
- `QWEN38_R27_W4A16_WEIGHT_BEGIN/END`;
- `QWEN38_R27_QWEN4_LAYER_BEGIN/END`.

Diagnostic image:

- tag: `vllm-orcarouter-v029-r27-linear-marker:v1`
- image id: `sha256:e9e92c5cb98d443a8410f21345cb0e07c30c9e7c84516cedcc2a6dc213934119`
- stability: `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`
- `qwen38.r25=init-model-boundary-v1`
- `qwen38.r26=construction-boundary-v1`
- `qwen38.r27=w4a16-linear-boundary-v1`

Static image gate is CLOSED/PASS:

```text
r26_inherited_constructor_contract=PASS
r26_inherited_modelopt_moe_contract=PASS
r27_w4a16_linear_contract=PASS
r27_qwen4_layer_contract=PASS
r27_ple_mmap_placeholder_contract=PASS
R27_IMAGE_PREFLIGHT=PASS
R27_STATIC_PREFLIGHT_RC=0
R27_BUILD_AND_STATIC_PREFLIGHT=PASS
model_restart=NO
managed_service_mutation=NO
persistent_vm_tuning=NO
```

Managed container ID / `StartedAt` were unchanged and exact OrcaRouter identity with `max_model_len=262144` remained READY.

## Guarded harness preflight — CLOSED PASS

Runner:

- `scripts/benchmark/run-orcarouter-r27-linear-boundary.sh`

The runner reuses the validated historical R24 matched-control harness through an ephemeral copy. It changes exactly the repository root injection, experiment container, kprobe group, and all four inherited hard-coded `r24_rm/...` definitions to `r27_rm/...`.

Live-host preflight on repository head `f359a6183233164bc4ec0b5d6febe68d5cc5dc5e` reported:

```text
stale_probe_groups_before=NONE
stale_probe_groups=NONE
r27_probe_definition_contract=PASS
R24_PREFLIGHT=PASS
R27_LIVE_PREFLIGHT=PASS
predecessor_age_s=3683.743
minimum_predecessor_age_s=2700
predecessor_age_ok=1
rm_probe_target_count=2
R27_HARNESS_PREFLIGHT_RC=0
stale_probe_groups_after=NONE
R27_HARNESS_PREFLIGHT_GATE=PASS
```

Preserved evidence:

- R24: `/tmp/orcarouter-hybrid-r24-kv16-rm-mitigation-01-20261004`
- R26: `/tmp/orcarouter-hybrid-r26-construction-boundary-01-20261005`

Fresh R27 evidence reserved for the live run:

`/tmp/orcarouter-hybrid-r27-linear-boundary-01-20261005`

Experiment container:

`qwen38-hybrid-r27-linear-marker`

The preflight created neither the live evidence path nor experiment container.

Managed non-mutation passed exactly:

```text
managed_id_before=cd2d34ec90de03b74a8cb8dc76a2311dd4b90b88bd2700b35026016f9c05f911
managed_id_after=cd2d34ec90de03b74a8cb8dc76a2311dd4b90b88bd2700b35026016f9c05f911
started_before=2026-10-05T08:55:17.15500875Z
started_after=2026-10-05T08:55:17.15500875Z
model_restart=NO
managed_service_mutation=NO
persistent_vm_tuning=NO
```

Exact managed model identity was revalidated after preflight:

- `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`
- `max_model_len=262144`
- READY after 0 s.

Canonical result:

- `scripts/benchmark/evidence/orcarouter-r27-live-harness-preflight-result-20261005.md`

## Evidence analyzer

Analyzer:

- `scripts/benchmark/analyze-orcarouter-r27-linear-overlap.py`

It reports:

- total / before / inside / after top-level constructor order-4 RM activity;
- inherited R26 ModelOpt-MoE activity;
- exact R26 residual outside ModelOpt-MoE;
- W4A16-linear `create_weights()` activity;
- W4A16-linear percentage of the R26 residual;
- packed W4A16 `weight` allocation activity and percentage of W4A16-linear activity;
- union of ModelOpt-MoE + W4A16-linear coverage;
- constructor activity left uncovered by those two allocation families;
- Qwen4Exp decoder-layer union coverage;
- totals by `linear_attention` versus `full_attention` layer type;
- top decoder layers by non-MoE RM activity.

The primary discriminator threshold is `90%` of the R26 residual. It is an analysis threshold, not a memory-safety threshold.

Possible labels:

- `RM_ORDER4_R26_RESIDUAL_PRIMARY_IN_MODELOPT_W4A16_LINEAR`;
- `RM_ORDER4_R26_RESIDUAL_MIXED_WITHIN_QWEN4_LAYERS`;
- `RM_ORDER4_R26_RESIDUAL_OUTSIDE_SELECTED_LAYER_LINEAR_BOUNDARIES`.

RM requested bytes remain allocation activity volume, not exact resident ownership. Marker overlap remains temporal localization, not causal proof.

## Trace scope

Keep only the already-closed narrow trace:

- `nv_alloc_pages`;
- `nv_alloc_system_pages`;
- static kernel-error capture.

Do not add UVM, generic page allocation, scheduler, function graph, CUDA API blanket tracing, broad Python profiling, or PLE page-fault tracing.

## Interpretation branches

### W4A16 linear explains >=90% of the R26 residual

The residual is primarily ordinary packed W4A16 linear construction. If the packed `weight` interval also explains most W4A16-linear activity, the next mitigation/discriminator should focus on W4A16 parameter/storage materialization semantics rather than H11's routed-expert-only parameter change.

### W4A16 linear is substantial but below 90%

Use Qwen4Exp layer-type totals and per-layer residual rankings to identify the smallest remaining component. Do not immediately change H11.

### Qwen4Exp layer union is low

The missing activity lies outside decoder-layer construction, such as top-level embedding/head/final mixer or another constructor path. Instrument only that exact remaining boundary.

## Gate sequence

1. repository CI green — **PASS**;
2. build marker-only R27 image — **PASS**;
3. static R27 image preflight — **PASS**;
4. static managed non-mutation — **PASS**;
5. canonical static result — **PASS**;
6. guarded R27 harness preflight — **PASS**;
7. harness managed non-mutation — **PASS**;
8. canonical harness result — **PASS**;
9. one guarded live R27 measurement — **AUTHORIZED NEXT**.

A live run requires explicit `run` mode and `ORCA_R27_LIVE_ACK=YES`.

This authorization is for exactly one measurement. If any evidence is produced, preserve it even if the run fails or is invalid; do not delete and silently retry.

Strict policy remains: any confirmed `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` in a valid measured run is **HOST-STABILITY FAIL** even if fallback recovers and functional readiness succeeds.

PR #244 remains open. No merge is implied or authorized.
