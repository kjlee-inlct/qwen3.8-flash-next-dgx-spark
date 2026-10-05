# OrcaRouter R26 — model-construction / ModelOpt-MoE RM boundary plan — 2026-10-05

## Status

**STATIC IMAGE BUILD/PREFLIGHT PASS — HARNESS PREFLIGHT NEXT — NO LIVE RUN AUTHORIZED YET**

R25b is closed as **VALID_MEASURED — FUNCTIONAL PASS / HOST-STABILITY FAIL**. In the valid attempt-02 run, the 64 KiB direct NVIDIA RM order-4 episode was `77,405.938 MiB`; `76,846.250 MiB` (`99.276945%`) fell inside the first `initialize_model()` interval, `559.688 MiB` occurred before that interval, and `0.000 MiB` occurred after it. The strict discriminator was `RM_ORDER4_STARTS_BEFORE_INITIALIZE_MODEL` because the small precursor began about `0.418 s` before the marker.

The first initialize-model interval lasted only `3.161066 s`, while the first checkpoint weight fill later took `601.96 s`. The traced RM episode was already over before the first initialize-model call returned. R26 therefore moves inward to model construction rather than adding broader kernel/VM tracing or instrumenting the long checkpoint-fill path.

## Question

Within the first `initialize_model()` call, is the approximately 76.8 GiB main RM burst concentrated in:

1. the top-level vLLM model constructor generally;
2. `ModelOptNvFp4FusedMoE.create_weights()` for routed experts; and, if so,
3. the large packed `w13_weight` / `w2_weight` storage allocations specifically?

This remains a localization discriminator, not a mitigation test.

## Pinned vLLM v0.29 construction path

The v0.29.0 model-loader `initialize_model()` resolves/configures the model class and, for the new-style class used here, directly executes:

`model = model_class(vllm_config=vllm_config, prefix=prefix)`

inside `set_current_vllm_config(...)`.

The H6 checkpoint used by the matched R24/R25b control declares `W4A16_NVFP4`. vLLM v0.29 ModelOpt supports that algorithm and routes NVFP4 MoE weight creation through `ModelOptNvFp4FusedMoE.create_weights()`.

That method creates the large routed-expert `w13_weight` and `w2_weight` `ModelWeightParameter` objects from `torch.empty(...)`, followed by scales and other metadata. These are therefore the highest-information allocation boundaries to measure before changing H11-like parameter construction behavior.

## Diagnostic image

Repository files:

- `scripts/patch-v029-r26-construction-markers.py`;
- `scripts/Dockerfile.v029-r26-construction-markers`;
- `scripts/benchmark/check-orcarouter-r26-construction-image.sh`.

Image tag:

`vllm-orcarouter-v029-r26-construction-marker:v1`

The image derives from the validated R25 marker image:

`vllm-orcarouter-v029-r25-init-marker:v1`

so the outer `QWEN38_R25_INIT_MODEL_BEGIN/END` markers remain available.

R26 adds only INFO markers around:

- top-level new-style `model_class(...)` constructor begin/end;
- `ModelOptNvFp4FusedMoE.create_weights()` begin/end, with a monotonic process-local call sequence number;
- `w13_weight` allocation begin/end;
- `w2_weight` allocation begin/end.

It does not alter tensor shapes, dtypes, parameter classes, checkpoint mappings, quantization methods, allocator behavior, runtime flags, PLE mmap, exact QSA, KV size, model length, speculative decode, or post-load processing.

## Static image gate — CLOSED / PASS

Canonical result:

- `scripts/benchmark/evidence/orcarouter-r26-construction-image-preflight-result-20261005.md`

DGX build/static preflight used repository head `35f11709715aa3b445b95442d7e81262cfcf8518` and produced:

- image `vllm-orcarouter-v029-r26-construction-marker:v1`;
- image id `sha256:568d0ac6917b324eef6c29e5f06b0a1ba182b5db043052b13296fe7d3c5428aa`;
- `R26_BUILD_RC=0`;
- `R26_STATIC_PREFLIGHT_RC=0`;
- `R26_BUILD_AND_STATIC_PREFLIGHT=PASS`;
- `r25_inherited_marker_contract=PASS`;
- `r26_model_constructor_contract=PASS`;
- `r26_modelopt_moe_contract=PASS`;
- `R26_IMAGE_PREFLIGHT=PASS`.

Managed non-mutation also passed: service remained active, exact container ID `e5422a909bf4e9b8c84bfa1a864b9ddeedac4686de5c449eb6aaf0a645add2cd` and `StartedAt=2026-10-05T05:42:55.476327457Z` were unchanged before/after, and the exact managed served identity remained `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4` with `max_model_len=262144`.

No R26 model load or live RM measurement occurred in this gate.

## Static image contract

`check-orcarouter-r26-construction-image.sh` verifies:

- inherited stability label `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`;
- inherited R25 label `init-model-boundary-v1`;
- R26 label `construction-boundary-v1`;
- inherited R25 marker ordering;
- exact top-level constructor marker ordering around `model_class(...)`;
- exactly one source literal for each ModelOpt MoE / w13 / w2 begin/end marker;
- sequence-counter contract;
- presence of `W4A16_NVFP4` support in the patched ModelOpt source.

This contract is now closed PASS for the built R26 image above.

## Evidence analyzer

- `scripts/benchmark/analyze-orcarouter-r26-construction-overlap.py`.

It selects the top-level model-constructor interval containing the most 64 KiB RM activity, then reports total/before/inside/after constructor activity, ModelOpt-MoE coverage, w13/w2 coverage, packed w13+w2 coverage, remaining MoE activity, constructor activity outside ModelOpt-MoE, and the five largest ModelOpt-MoE calls.

The `90%` threshold is an analysis discriminator only, not a memory-safety acceptance threshold. Possible labels are:

- `RM_ORDER4_PRIMARY_IN_MODELOPT_MOE_CREATE_WEIGHTS`;
- `RM_ORDER4_PRIMARY_IN_MODEL_CONSTRUCTOR_OUTSIDE_MODELOPT_MOE`;
- `RM_ORDER4_MIXED_WITHIN_MODEL_CONSTRUCTOR`;
- `RM_ORDER4_NOT_LOCALIZED_TO_SELECTED_MODEL_CONSTRUCTOR`.

RM requested bytes remain activity volume, not exact resident ownership. Marker overlap remains temporal localization, not causal proof.

## Guarded live runner

- `scripts/benchmark/run-orcarouter-r26-construction-boundary.sh`.

It reuses the validated R24 matched-control harness through an ephemeral copy and changes only repository-root injection, experiment container identity, kprobe group `r26_rm`, and the exact four inherited `r24_rm/...` definitions. It rejects stale `r24_rm`, `r25b_rm`, or `r26_rm` groups, defaults to `--preflight`, and requires explicit `run` plus `ORCA_R26_LIVE_ACK=YES` for a live run.

Default evidence:

`/tmp/orcarouter-hybrid-r26-construction-boundary-01-20261005`

Managed restoration requires exact served identity `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`.

The next gate is **harness preflight only**. It must verify the built image contract again, the R24 matched-control preflight, unique evidence/container identities, exact four-probe `r26_rm` transform, stale-probe absence, predecessor-age requirement, and no managed-service mutation. Passing this gate does not itself constitute a live measurement.

## Trace scope

Keep only the already-closed narrow RM trace:

- `nv_alloc_pages`;
- `nv_alloc_system_pages`;
- existing static kernel-error capture.

Do not add UVM, generic page allocation, scheduler, function graph, CUDA API blanket tracing, or broad Python profiling.

## Interpretation / next branch

If ModelOpt MoE `create_weights()` contains at least 90% of total order-4 RM activity, parameter/storage construction is directly implicated and the next discriminator can separate packed expert tensor object/storage semantics, including H11-like parameter-class differences, without broad tracing.

If the model constructor contains the burst but ModelOpt MoE coverage is low, do not apply H11; instrument the smallest remaining constructor subpath instead. If w13+w2 intervals cover most ModelOpt-MoE activity, that is the strongest evidence for large expert storage materialization rather than scale/metadata creation.

Keep the R25b `559.688 MiB` precursor separate.

## Tests

- `tests/test_orcarouter_r26_construction_markers.py`;
- `tests/test_orcarouter_r26_construction_overlap.py`;
- `tests/test_orcarouter_r26_runner_transform.py`.

## Validation

The R26 implementation is CI-green and the actual DGX static image build/preflight is now closed PASS in the canonical result above. Documentation-only commits made after the local static execution do not change the built image contract or runtime code.

## Gate sequence

1. repository CI green — **CLOSED / PASS**;
2. build `vllm-orcarouter-v029-r26-construction-marker:v1` — **CLOSED / PASS**;
3. static R26 image preflight — **CLOSED / PASS**;
4. managed container ID / `StartedAt` unchanged across build/preflight — **CLOSED / PASS**;
5. canonical static-preflight result — **CLOSED / PASS**;
6. R26 harness preflight only — **NEXT**;
7. canonical harness-preflight result — required before live authorization;
8. live R26 measured run — **NOT AUTHORIZED YET**.

PR #244 remains open. No merge is implied or authorized.
