# OrcaRouter R27 — W4A16-linear / Qwen4Exp residual-constructor plan — 2026-10-05

## Status

**IMPLEMENTED — REPOSITORY CI PASS — STATIC IMAGE BUILD/PREFLIGHT PASS — HARNESS PREFLIGHT NEXT — NO LIVE RUN AUTHORIZED YET**

R26 is closed as:

**VALID_MEASURED — FUNCTIONAL PASS / HOST-STABILITY FAIL — `RM_ORDER4_MIXED_WITHIN_MODEL_CONSTRUCTOR`**

Canonical predecessor:

- `scripts/benchmark/evidence/orcarouter-r26-construction-boundary-result-20261005.md`

R27 static-image gate:

- `scripts/benchmark/evidence/orcarouter-r27-linear-image-preflight-result-20261005.md`
- image: `vllm-orcarouter-v029-r27-linear-marker:v1`
- image id: `sha256:e9e92c5cb98d443a8410f21345cb0e07c30c9e7c84516cedcc2a6dc213934119`
- static image contract: **PASS**
- managed container ID / `StartedAt`: unchanged
- exact managed OrcaRouter identity: revalidated

R26 reproduced `77,405.938 MiB` total direct-NVIDIA-RM order-4 activity, with `76,846.250 MiB` (`99.276945%`) inside the first top-level model constructor, `559.688 MiB` before it, and `0.000 MiB` after it. However, `ModelOptNvFp4FusedMoE.create_weights()` accounted for only `34,292.000 MiB` (`44.301511%` of total), leaving `42,554.250 MiB` elsewhere in the constructor.

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

The top-level model is `Qwen4ExpForCausalLM`, whose `Qwen4ExpModel` constructs the embedding, then decoder layers through `make_layers(...)`, then the final hyper-connection mixer. `Qwen4ExpDecoderLayer` constructs PLE where configured, linear-attention or full/QSA attention, MoE/MLP, and two hyper-connection branches.

The active checkpoint/runtime family has 48 decoder layers with hybrid linear/full attention. R27 instruments the exact `Qwen4ExpDecoderLayer` path rather than the adjacent `Qwen3NextDecoderLayer` implementation.

## PLE constructor exclusion

The matched runtime explicitly enables:

```text
VLLM_PLE_MMAP=1
VLLM_PLE_MMAP_DIR=/model
VLLM_PLE_MMAP_PREWARM=0
```

The v0.29 base image appends:

`_ple_mmap_apply(Qwen4ExpNGramEmbedding)`

to the Qwen4Exp PLE layer.

The vendored v0.29 mmap patch then replaces `PLEVocabParallelEmbedding` during N-gram embedding construction with `_MmapNgramEmbedding` and calls the stock constructor with `quant_config=None`. The giant N-gram table is therefore not materialized as the stock embedding parameter during constructor execution; shard tensors are later served from mmap.

R27 static preflight revalidated this placeholder contract as `r27_ple_mmap_placeholder_contract=PASS`. Therefore R27 does not add broad PLE tracing merely because the on-disk PLE table is large.

## Highest-information remaining allocation boundary

vLLM v0.29 `ModelOptNvFp4W4A16LinearMethod.create_weights()` allocates:

1. packed NVFP4 `weight` as `ModelWeightParameter(torch.empty(..., dtype=torch.uint8))`;
2. `weight_scale_2`;
3. per-group `weight_scale`;
4. placeholder `input_scale`.

R27 measures the complete W4A16-linear `create_weights()` interval and the packed `weight` allocation sub-interval. This directly tests whether the R26 non-MoE residual is mostly ordinary ModelOpt W4A16 linear storage construction.

## R27 markers

Patch:

- `scripts/patch-v029-r27-linear-boundary-markers.py`

It adds only INFO markers:

### ModelOpt W4A16 linear

- `QWEN38_R27_W4A16_LINEAR_BEGIN/END`;
- `QWEN38_R27_W4A16_WEIGHT_BEGIN/END`;
- process-local monotonic sequence number;
- input/output partition dimensions for the begin marker.

### Exact Qwen4Exp decoder layer

- `QWEN38_R27_QWEN4_LAYER_BEGIN/END`;
- sequence number;
- layer index;
- exact `layer_type`;
- prefix on begin.

The layer marker begins immediately after `self.layer_idx` is known, before the PLE/attention/MLP/hyper-connection construction that can materially allocate parameters, and ends after the layer's final hyper-connection constructor.

## Diagnostic image

Dockerfile:

- `scripts/Dockerfile.v029-r27-linear-boundary-markers`

Built tag:

`vllm-orcarouter-v029-r27-linear-marker:v1`

Image id:

`sha256:e9e92c5cb98d443a8410f21345cb0e07c30c9e7c84516cedcc2a6dc213934119`

Base image:

`vllm-orcarouter-v029-r26-construction-marker:v1`

Validated inherited labels:

```text
qwen38.stability-candidate=v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla
qwen38.r25=init-model-boundary-v1
qwen38.r26=construction-boundary-v1
```

Validated new label:

`qwen38.r27=w4a16-linear-boundary-v1`

## Static image contract — CLOSED PASS

Checker:

- `scripts/benchmark/check-orcarouter-r27-linear-image.sh`

The live host static gate reported:

```text
r26_inherited_constructor_contract=PASS
r26_inherited_modelopt_moe_contract=PASS
r27_w4a16_linear_contract=PASS
r27_qwen4_layer_contract=PASS
r27_ple_mmap_placeholder_contract=PASS
R27_IMAGE_PREFLIGHT=PASS
model_restart=NO
managed_service_mutation=NO
persistent_vm_tuning=NO
R27_STATIC_PREFLIGHT_RC=0
R27_BUILD_AND_STATIC_PREFLIGHT=PASS
```

Managed container ID and `StartedAt` were exactly unchanged across build/static preflight, and exact `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4` with `max_model_len=262144` remained READY.

Canonical result:

- `scripts/benchmark/evidence/orcarouter-r27-linear-image-preflight-result-20261005.md`

## Evidence analyzer

Analyzer:

- `scripts/benchmark/analyze-orcarouter-r27-linear-overlap.py`

It reuses the established candidate-request / trace-start / trace-end wall-to-monotonic anchors and the same direct-RM 64 KiB trace.

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
- aggregated totals by `linear_attention` versus `full_attention` layer type;
- top decoder layers by non-MoE RM activity.

The primary threshold remains an explicit analysis discriminator at `90%`, not a memory-safety threshold.

Possible primary labels:

- `RM_ORDER4_R26_RESIDUAL_PRIMARY_IN_MODELOPT_W4A16_LINEAR`;
- `RM_ORDER4_R26_RESIDUAL_MIXED_WITHIN_QWEN4_LAYERS`;
- `RM_ORDER4_R26_RESIDUAL_OUTSIDE_SELECTED_LAYER_LINEAR_BOUNDARIES`.

RM requested bytes remain allocation activity volume, not exact resident ownership. Marker overlap remains temporal localization, not causal proof.

## Guarded runner

Runner:

- `scripts/benchmark/run-orcarouter-r27-linear-boundary.sh`

It reuses the validated historical R24 matched-control harness through an ephemeral copy. The historical R24 harness is not edited.

The transform changes exactly:

1. repository-root injection;
2. experiment container to `qwen38-hybrid-r27-linear-marker`;
3. kprobe group variable to `r27_rm`;
4. all exactly four inherited hard-coded `r24_rm/...` definitions to `r27_rm/...`.

The runner requires preserved R24 and R26 evidence and rejects reuse of either output path.

Default R27 evidence:

`/tmp/orcarouter-hybrid-r27-linear-boundary-01-20261005`

It blocks stale groups:

- `r24_rm`;
- `r25b_rm`;
- `r26_rm`;
- `r27_rm`.

Default mode is `--preflight`. A live run requires both explicit `run` mode and `ORCA_R27_LIVE_ACK=YES`.

Post-run restoration requires the exact managed served identity:

`orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`

## Trace scope

Keep the already-closed narrow trace only:

- `nv_alloc_pages`;
- `nv_alloc_system_pages`;
- existing static kernel-error capture.

Do not add UVM, generic page allocation, scheduler, function graph, CUDA API blanket tracing, broad Python profiling, or PLE page-fault tracing.

## Interpretation branches

### If W4A16 linear explains >=90% of the R26 residual

Then the residual is primarily ordinary packed W4A16 linear construction. If the packed `weight` sub-interval also explains most W4A16-linear activity, the next mitigation/discriminator can focus on W4A16 parameter/storage materialization semantics rather than H11's routed-expert-only parameter change.

### If W4A16 linear is substantial but below 90%

Use Qwen4Exp layer-type totals and per-layer residual rankings to identify the smallest remaining component. Do not immediately change H11.

### If Qwen4Exp layer union is low

The missing activity lies outside decoder-layer construction (for example top-level embedding/head/final mixer or another constructor path). Instrument that exact remaining boundary only.

## Regression tests

- `tests/test_orcarouter_r27_linear_markers.py`;
- `tests/test_orcarouter_r27_linear_overlap.py`;
- `tests/test_orcarouter_r27_runner_transform.py`.

Repository CI for the implementation head closed SUCCESS, including shell syntax, ShellCheck, Python compile, unit tests, and whitespace checks.

## Gate sequence

1. repository CI green — **PASS**;
2. build `vllm-orcarouter-v029-r27-linear-marker:v1` — **PASS**;
3. static R27 image preflight only — **PASS**;
4. verify managed container ID / `StartedAt` unchanged — **PASS**;
5. record static result canonically — **PASS**;
6. run guarded R27 harness preflight only — **NEXT**;
7. record harness preflight canonically;
8. only then authorize one live measured R27 run.

**No R27 live run is authorized yet.**

PR #244 remains open. No merge is implied or authorized.
