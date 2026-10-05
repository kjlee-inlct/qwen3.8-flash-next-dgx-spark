# OrcaRouter R26 — model-construction / ModelOpt-MoE RM boundary plan — 2026-10-05

## Status

**STATIC IMAGE PASS — HARNESS PREFLIGHT PASS — SINGLE LIVE MEASURED RUN AUTHORIZED**

R25b is closed as **VALID_MEASURED — FUNCTIONAL PASS / HOST-STABILITY FAIL**. Its valid attempt-02 localized `76,846.250 MiB` of `77,405.938 MiB` total 64 KiB direct-NVIDIA-RM order-4 activity (`99.276945%`) inside the first `initialize_model()` interval, with `559.688 MiB` before the marker and `0.000 MiB` after it. The main burst therefore belongs to immediate model construction rather than the later long checkpoint-fill path.

R26 moves inward observationally. It does not change parameter classes, tensor shapes, dtypes, quantization behavior, allocator behavior, runtime flags, or VM policy.

## Question

Within the first `initialize_model()` call, is the approximately 76.8 GiB main RM burst concentrated in:

1. the top-level vLLM model constructor;
2. `ModelOptNvFp4FusedMoE.create_weights()` for routed experts; and, if so,
3. the large packed `w13_weight` / `w2_weight` storage allocations specifically?

This is a localization discriminator, not a mitigation test.

## Pinned vLLM v0.29 path

The v0.29 model-loader `initialize_model()` resolves/configures the model class and executes the new-style constructor:

`model = model_class(vllm_config=vllm_config, prefix=prefix)`

inside `set_current_vllm_config(...)`.

The H6 matched-control checkpoint declares `W4A16_NVFP4`. vLLM v0.29 routes this NVFP4 MoE construction through `ModelOptNvFp4FusedMoE.create_weights()`, which creates the routed-expert `w13_weight` and `w2_weight` `ModelWeightParameter` objects from `torch.empty(...)` before scales/metadata. Those are the highest-information allocation boundaries to measure before any H11-like behavior-changing experiment.

## Diagnostic image

Repository components:

- `scripts/patch-v029-r26-construction-markers.py`
- `scripts/Dockerfile.v029-r26-construction-markers`
- `scripts/benchmark/check-orcarouter-r26-construction-image.sh`
- `scripts/benchmark/analyze-orcarouter-r26-construction-overlap.py`
- `scripts/benchmark/run-orcarouter-r26-construction-boundary.sh`

Image:

`vllm-orcarouter-v029-r26-construction-marker:v1`

Built image id:

`sha256:568d0ac6917b324eef6c29e5f06b0a1ba182b5db043052b13296fe7d3c5428aa`

The image derives from `vllm-orcarouter-v029-r25-init-marker:v1`, preserving the outer R25 `QWEN38_R25_INIT_MODEL_BEGIN/END` markers.

R26 adds INFO markers around:

- top-level new-style `model_class(...)` constructor begin/end;
- `ModelOptNvFp4FusedMoE.create_weights()` begin/end with a process-local sequence number;
- `w13_weight` allocation begin/end;
- `w2_weight` allocation begin/end.

It does not alter tensor shapes, dtypes, parameter classes, checkpoint mappings, quantization methods, allocator behavior, runtime flags, PLE mmap, exact QSA, KV size, model length, speculative decode, or post-load processing.

## Static image gate — CLOSED / PASS

Canonical result:

- `scripts/benchmark/evidence/orcarouter-r26-construction-image-preflight-result-20261005.md`

Observed DGX result:

```text
R26_BUILD_RC=0
r25_inherited_marker_contract=PASS
r26_model_constructor_contract=PASS
r26_modelopt_moe_contract=PASS
R26_IMAGE_PREFLIGHT=PASS
R26_STATIC_PREFLIGHT_RC=0
R26_BUILD_AND_STATIC_PREFLIGHT=PASS
```

Managed service remained active and exact container ID `e5422a909bf4e9b8c84bfa1a864b9ddeedac4686de5c449eb6aaf0a645add2cd` plus `StartedAt=2026-10-05T05:42:55.476327457Z` were unchanged before/after. Exact served identity remained `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`, `max_model_len=262144`.

## Harness preflight gate — CLOSED / PASS

Canonical result:

- `scripts/benchmark/evidence/orcarouter-r26-live-harness-preflight-result-20261005.md`

DGX harness preflight used repository head `80efd0e789493fd69ca6455ff794308f8723adff` and reported:

```text
stale_probe_groups=NONE
r25_inherited_marker_contract=PASS
r26_model_constructor_contract=PASS
r26_modelopt_moe_contract=PASS
R26_IMAGE_PREFLIGHT=PASS
r26_probe_definition_contract=PASS
R24_PREFLIGHT=PASS
R26_LIVE_PREFLIGHT=PASS
predecessor_age_s=9373.825
minimum_predecessor_age_s=2700
predecessor_age_ok=1
rm_probe_target_count=2
R26_HARNESS_PREFLIGHT_RC=0
R26_HARNESS_PREFLIGHT_AND_NONMUTATION=PASS
```

Matched-control identity remained:

```text
profile=orcarouter-hybrid
candidate_checkpoint=/home/inlc/Workspace/llm/qwen3.8-flash-next-dgx-spark/models/qwen3.8-h6-modelopt-w4a16
candidate_image=vllm-orcarouter-v029-r26-construction-marker:v1
candidate_image_label=v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla
kv_bytes=17179869184
```

Evidence/container identities are unique:

- preserved R24 evidence: `/tmp/orcarouter-hybrid-r24-kv16-rm-mitigation-01-20261004`
- R26 evidence: `/tmp/orcarouter-hybrid-r26-construction-boundary-01-20261005`
- experiment container: `qwen38-hybrid-r26-construction-marker`

Managed non-mutation also passed through harness preflight: the exact container ID and `StartedAt` above remained unchanged, service stayed active, and exact OrcaRouter identity remained READY.

No live model load or RM measurement occurred in either preflight gate.

## Evidence analyzer

`analyze-orcarouter-r26-construction-overlap.py` selects the top-level model-constructor interval containing the most 64 KiB RM activity and reports:

- total / before-constructor / inside-constructor / after-constructor RM activity;
- constructor coverage;
- selected ModelOpt-MoE `create_weights()` call count and union activity;
- `w13` activity;
- `w2` activity;
- packed `w13+w2` union activity;
- ModelOpt-MoE activity outside packed allocations;
- constructor activity outside ModelOpt-MoE;
- five largest ModelOpt-MoE calls by RM activity.

The 90% threshold is an analysis discriminator only, not a memory-safety threshold. Possible labels:

- `RM_ORDER4_PRIMARY_IN_MODELOPT_MOE_CREATE_WEIGHTS`
- `RM_ORDER4_PRIMARY_IN_MODEL_CONSTRUCTOR_OUTSIDE_MODELOPT_MOE`
- `RM_ORDER4_MIXED_WITHIN_MODEL_CONSTRUCTOR`
- `RM_ORDER4_NOT_LOCALIZED_TO_SELECTED_MODEL_CONSTRUCTOR`

RM bytes remain allocation activity volume, not exact resident ownership. Marker overlap remains temporal localization, not causal proof.

## Guarded live run

The validated runner is:

`scripts/benchmark/run-orcarouter-r26-construction-boundary.sh`

It reuses an ephemeral transformed copy of the historical R24 matched-control harness. The transform changes only repository-root injection, experiment-container identity, kprobe group `r26_rm`, and exactly four hard-coded inherited `r24_rm/...` probe definitions. The canonical R24 harness itself is not edited.

A live run requires both:

- explicit `run` mode;
- `ORCA_R26_LIVE_ACK=YES`.

The runner rejects stale `r24_rm`, `r25b_rm`, or `r26_rm` groups and existing evidence/container collisions. Managed restoration requires exact served identity `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`.

## Trace scope

Keep only the already-closed narrow RM trace:

- `nv_alloc_pages`;
- `nv_alloc_system_pages`;
- existing kernel-error capture.

Do not add UVM, generic page allocation, scheduler, function graph, blanket CUDA API tracing, or broad Python profiling.

## Strict classification

For the live R26 measurement, keep functional and host-stability classification separate. Any confirmed `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` in a valid measured run remains **HOST-STABILITY FAIL**, even if fallback succeeds and runtime reaches READY.

R26 is still useful as a localization measurement under HOST-STABILITY FAIL if the run itself is valid and marker/trace evidence is complete.

## Interpretation / next branch

If ModelOpt-MoE `create_weights()` contains at least 90% of total order-4 RM activity, parameter/storage construction is directly implicated. If packed `w13+w2` intervals also dominate ModelOpt-MoE activity, the next discriminator should target expert storage/parameter construction semantics, making H11 materially actionable.

If constructor coverage remains high but ModelOpt-MoE coverage is low, do not apply H11; instead instrument the smallest remaining constructor subpath. Keep the R25b `559.688 MiB` precursor separate from the main burst.

## Gate sequence

1. repository CI — **CLOSED / PASS**;
2. R26 image build — **CLOSED / PASS**;
3. static R26 image contract — **CLOSED / PASS**;
4. static managed non-mutation — **CLOSED / PASS**;
5. canonical static result — **CLOSED / PASS**;
6. guarded R26 harness preflight — **CLOSED / PASS**;
7. harness managed non-mutation — **CLOSED / PASS**;
8. canonical harness-preflight result — **CLOSED / PASS**;
9. one guarded R26 live measured run — **AUTHORIZED / NEXT**;
10. canonical live result and next discriminator — pending measured evidence.

PR #244 remains open. No merge is implied or authorized.
