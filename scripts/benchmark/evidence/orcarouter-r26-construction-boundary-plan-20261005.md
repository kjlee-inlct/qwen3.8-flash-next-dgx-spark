# OrcaRouter R26 — model-construction / ModelOpt-MoE RM boundary plan — 2026-10-05

## Status

**IMPLEMENTED — CI GREEN — STATIC IMAGE BUILD/PREFLIGHT NEXT — NO LIVE RUN AUTHORIZED YET**

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

New repository files:

- `scripts/patch-v029-r26-construction-markers.py`;
- `scripts/Dockerfile.v029-r26-construction-markers`;
- `scripts/benchmark/check-orcarouter-r26-construction-image.sh`.

Planned image tag:

`vllm-orcarouter-v029-r26-construction-marker:v1`

The image derives from the already-validated R25 marker image:

`vllm-orcarouter-v029-r25-init-marker:v1`

so the outer `QWEN38_R25_INIT_MODEL_BEGIN/END` markers remain available.

R26 adds only INFO markers around:

- top-level new-style `model_class(...)` constructor begin/end;
- `ModelOptNvFp4FusedMoE.create_weights()` begin/end, with a monotonic process-local call sequence number;
- `w13_weight` allocation begin/end;
- `w2_weight` allocation begin/end.

It does not alter tensor shapes, dtypes, parameter classes, checkpoint mappings, quantization methods, allocator behavior, runtime flags, PLE mmap, exact QSA, KV size, model length, speculative decode, or post-load processing.

## Static image contract

`check-orcarouter-r26-construction-image.sh` must pass before any model restart. It verifies:

- inherited stability label `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`;
- inherited R25 label `init-model-boundary-v1`;
- R26 label `construction-boundary-v1`;
- inherited R25 marker ordering;
- exact top-level constructor marker ordering around `model_class(...)`;
- exactly one source literal for each ModelOpt MoE / w13 / w2 begin/end marker;
- sequence-counter contract;
- presence of `W4A16_NVFP4` support in the patched ModelOpt source.

Static preflight must report no model restart, no managed-service mutation, and no persistent VM tuning.

## Evidence analyzer

New analyzer:

- `scripts/benchmark/analyze-orcarouter-r26-construction-overlap.py`.

It reuses the established wall-clock to monotonic mapping from candidate-request / trace-start / trace-end anchors and consumes only:

- `candidate-container.log`;
- `rm-trace.txt`;
- existing clock anchors;
- host page size.

It selects the top-level model-constructor interval containing the most 64 KiB RM activity, then reports:

- total / before-constructor / inside-constructor / after-constructor RM activity;
- constructor coverage percentage;
- total ModelOpt MoE marker pairs and calls overlapping the selected constructor;
- RM activity inside the union of selected `ModelOptNvFp4FusedMoE.create_weights()` calls;
- w13 allocation activity;
- w2 allocation activity;
- union of w13+w2 packed allocations;
- ModelOpt-MoE activity outside those two packed allocations;
- constructor activity outside ModelOpt-MoE create-weights intervals;
- the five ModelOpt-MoE calls with the largest RM activity.

The `90%` threshold is an explicit analysis discriminator only; it is not a memory-safety acceptance threshold. Possible labels are:

- `RM_ORDER4_PRIMARY_IN_MODELOPT_MOE_CREATE_WEIGHTS`;
- `RM_ORDER4_PRIMARY_IN_MODEL_CONSTRUCTOR_OUTSIDE_MODELOPT_MOE`;
- `RM_ORDER4_MIXED_WITHIN_MODEL_CONSTRUCTOR`;
- `RM_ORDER4_NOT_LOCALIZED_TO_SELECTED_MODEL_CONSTRUCTOR`.

RM requested bytes remain activity volume, not exact resident ownership. Marker overlap remains temporal localization, not causal proof.

## Guarded live runner

New runner:

- `scripts/benchmark/run-orcarouter-r26-construction-boundary.sh`.

It reuses the validated historical R24 matched-control harness through an ephemeral copy; the historical R24 script is not edited. The ephemeral transform changes:

1. repository-root injection;
2. experiment container → `qwen38-hybrid-r26-construction-marker`;
3. kprobe group variable → `r26_rm`;
4. all exactly four hard-coded `r24_rm/...` probe definitions → `r26_rm/...`.

The transform requires exactly four probe-definition replacements and rejects any remaining `r24_rm/` definition. A dedicated regression test extracts and executes this exact embedded transform against the canonical R24 harness and requires four `r26_rm/` definitions with no `r24_rm/` leakage.

Default evidence path:

`/tmp/orcarouter-hybrid-r26-construction-boundary-01-20261005`

Preserved historical R24 evidence remains:

`/tmp/orcarouter-hybrid-r24-kv16-rm-mitigation-01-20261004`

The runner blocks if any of these stale probe groups exists:

- `r24_rm`;
- `r25b_rm`;
- `r26_rm`.

The runner defaults to `--preflight`. A live run additionally requires both explicit `run` mode and `ORCA_R26_LIVE_ACK=YES`.

Managed restoration is stricter than the original R25b wrapper: it waits for both container readiness and exact served model identity `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`.

## Trace scope

Keep the already-closed narrow RM trace only:

- `nv_alloc_pages`;
- `nv_alloc_system_pages`;
- existing static kernel-error capture.

Do not add UVM, generic page allocation, scheduler, function graph, CUDA API blanket tracing, or broad Python profiling.

## Interpretation / next branch

If ModelOpt MoE `create_weights()` contains at least 90% of total order-4 RM activity, then parameter/storage construction is directly implicated and the next discriminator can separate packed expert tensor object/storage semantics (including H11-like parameter-class differences) without broad tracing.

If the model constructor still contains the burst but ModelOpt MoE coverage is low, do not apply H11. Instead instrument the smallest constructor subpath responsible for the remaining activity (for example another routed-expert backend, embedding/PLE construction, or a different quantized storage path).

If w13+w2 packed allocation intervals themselves cover most ModelOpt-MoE activity, that is the strongest evidence that the burst is tied to the large expert storage materialization rather than scale/metadata creation.

Keep the R25b `559.688 MiB` precursor separate; R26 is designed to localize the main constructor burst, not to explain that smaller pre-init event.

## Tests

Regression coverage:

- `tests/test_orcarouter_r26_construction_markers.py`;
- `tests/test_orcarouter_r26_construction_overlap.py`;
- `tests/test_orcarouter_r26_runner_transform.py`.

The marker-patch test applies the real patch script to synthetic v0.29-shaped sources and validates AST plus marker ordering/counts. The analyzer test uses synthetic evidence with 90% of RM activity inside one ModelOpt-MoE call and requires the ModelOpt-MoE-primary discriminator. The runner-transform test extracts and executes the exact embedded R24→R26 harness transform.

## Validation

Repository implementation and regression tests are green through branch head `e90f0e71fe1152a3c476efa34ac6ee72b7e21c90`.

CI #1092 is **SUCCESS**: shell syntax, ShellCheck, Python compile, full unit tests including all R26 marker/analyzer/runner-transform coverage, and whitespace all PASS.

## Gate sequence

1. repository CI green — **CLOSED / PASS**;
2. build `vllm-orcarouter-v029-r26-construction-marker:v1` from the current branch;
3. run static R26 image preflight only;
4. verify managed runtime container ID and `StartedAt` unchanged across build/preflight;
5. record the static-preflight result canonically;
6. only then run the R26 harness preflight;
7. do not authorize a live measured run until both static and harness preflight gates are closed.

PR #244 remains open. No merge is implied or authorized.
