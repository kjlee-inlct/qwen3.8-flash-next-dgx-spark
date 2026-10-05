# OrcaRouter M1 — deferred/meta w13 materialization plan — 2026-10-06

Status: **IMPLEMENTED — REPOSITORY/IMAGE STATIC GATES + CHECKPOINT-ORDER GATE NEXT — NO LIVE RUN AUTHORIZED**

## Why mitigation starts here

R23–R32 closed model-component ownership localization far enough to stop adding model-prefix markers.

The repeated large RM families are now separated:

- `400 MiB x48` is exactly one-to-one with the 48 packed routed-expert `w13_weight` construction intervals (`19200 MiB` total);
- `800 MiB x48` occurs immediately before those events but before `ModelOptNvFp4FusedMoE.create_weights()` begins and is not supported as a distinct explicit model-weight owner;
- the structural constructor burst is about `77.4 GiB` of order-4 RM activity and can occur with or without strict RM OOM.

The first mitigation should therefore move one *known* large family out of the ~3 s constructor burst without changing checkpoint values, tensor shapes, quantization, expert count, kernels, or the final model contract.

## Rejected first ideas

### Generic `--cpu-offload-gb`

Rejected as the first discriminator because vLLM v0.29 constructs the layer on the target device before the UVA offloader moves parameters to CPU. That does not guarantee constructor-time CUDA/RM backing is returned, and it introduces an additional CPU copy path.

### Direct CPU/UVA w13 construction

Rejected after checking exact v0.29 C++ source. For an unpinned CPU tensor, `get_cuda_view_from_cpu_tensor` allocates a new `cudaHostAlloc(..., cudaHostAllocMapped)` buffer and copies the tensor into it. On a unified-memory DGX Spark this can add large pinned backing rather than remove pressure.

M1 must not use either path.

## M1 hypothesis

**Defer only `ModelOptNvFp4FusedMoE.w13_weight` storage allocation from model construction to first weight loading by creating it on `device="meta"` and using vLLM's native layerwise online-processing lifecycle.**

M1 leaves unchanged:

- checkpoint files and values;
- H6 config / `W4A16_NVFP4` routing;
- routed-expert count and shapes;
- w2 construction;
- w13/w2 scale construction;
- ModelOpt weight loaders;
- `process_weights_after_loading()` implementation;
- selected NVFP4/Marlin MoE kernel;
- R26/R27/R28 diagnostic markers.

M1 changes only *when* the packed w13 storage is materialized.

## Exact vLLM lifecycle reused

`QuantizeMethodBase.uses_meta_device` exists specifically for methods that create weights on the meta device and process them layer-wise during first loading.

`initialize_online_processing(layer)`:

1. records the layer's total parameter size;
2. wraps its existing parameter weight loaders;
3. buffers incoming checkpoint tensors;
4. once the layer is sufficiently loaded, calls `materialize_layer(layer, info)`;
5. replays the original weight loaders into the materialized parameters;
6. calls the layer's existing quant method `process_weights_after_loading(layer)`.

`BaseModelLoader` detects `uses_meta_device=True` and calls `finalize_layerwise_processing()` after weight loading for any delayed/incomplete layer.

For M1, only `w13_weight` is meta, so `materialize_layer()` should allocate only that deferred storage; w2 and scale parameters already retain their original target-device storage.

## Implementation

- `scripts/patch-v029-m1-deferred-meta-w13.py`
- `scripts/Dockerfile.v029-m1-deferred-meta-w13`
- `scripts/benchmark/check-orcarouter-m1-deferred-meta-w13-image.sh`
- `scripts/benchmark/inspect-orcarouter-m1-checkpoint-order.py`
- `tests/test_orcarouter_m1_deferred_meta_w13.py`

Image ancestry:

`vllm-orcarouter-v029-r28-unquant-linear-marker:v1`

Expected M1 label:

`qwen38.m1=deferred-meta-w13-v1`

The R28 image is intentionally inherited so R26/R27/R28 markers remain available if M1 later reaches a guarded measured run.

## Static image acceptance gate

The image checker must prove all of the following without launching a model:

- inherited stability/R25/R26/R27/R28 labels match;
- inherited R26 constructor, ModelOpt-MoE, and w13 markers remain exact;
- inherited R27 Qwen4 layer markers remain exact;
- inherited R28 unquantized-Linear markers remain exact;
- `ModelOptNvFp4FusedMoE.uses_meta_device = True` exists once;
- only the w13 packed allocation contains `device="meta"`;
- w2 remains on the original construction device;
- `initialize_online_processing(layer)` occurs exactly once after all original parameter registrations and before `process_weights_after_loading()`;
- native base-loader online-quant finalization contract remains present;
- native layerwise materialize/load/process contract remains present;
- no direct-UVA / `cudaHostAlloc` / `cpu_offload_gb` path is introduced.

Failure of any item blocks M1 live testing.

## Checkpoint-order feasibility gate

M1's layerwise loader buffers checkpoint tensor objects until a routed-expert layer is complete. The default v0.29 single-thread safetensors iterator walks natural-sorted shard files and then `safe_open(file).keys()`.

The read-only inspector reproduces exactly that *name order* and never reads tensor payloads.

For the H6 checkpoint, strict PASS requires:

- exactly `48` routed-expert decoder layers discovered;
- no missing/extra layer IDs;
- each routed-expert layer appears in exactly one contiguous run in iterator order;
- `routed_expert_revisited_layer_count=0`;
- `routed_expert_max_open_layer_intervals=1`.

This gate is valid only for the matched default single-thread safetensors path. If the candidate runtime enables multi-thread/alternative streaming loading, the gate must be redefined before live execution.

A FAIL blocks M1 live testing because buffered checkpoint tensors could accumulate across multiple expert layers and replace one peak-memory problem with another.

## Future measured discriminator — NOT YET AUTHORIZED

Only after repository CI, exact-image static preflight, and checkpoint-order feasibility all PASS may a single guarded M1 live run be considered.

The future live result must separately classify FUNCTIONAL and HOST-STABILITY and must preserve the strict RM rule.

### Primary mechanism target

The strongest success criterion is not merely READY. It is removal/deferment of the known constructor w13 family:

```text
constructor_400_mib_request_count: 48 -> 0 (target)
constructor_w13_rm_activity_mib:    19200 -> approximately 0 (target)
```

The actual 400 MiB allocation may reappear later during weight loading when each layer is materialized. If so, that is expected M1 timing behavior and must be reported separately rather than hidden.

### Structural burst target

If the 800 MiB precursor family is unaffected, moving only w13 predicts roughly a `19.2 GiB` reduction in constructor RM activity from the known 400 MiB series. The exact observed reduction must be measured; this is a hypothesis, not a guaranteed arithmetic subtraction because allocator behavior can change when allocation order changes.

The 800 MiB family is **not** a direct M1 target. If it also shrinks/disappears, classify that as allocator/backing coupling evidence, not as proof that w13 owned the earlier 800 MiB request.

### Host-stability classification

Any confirmed `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` in a valid M1 measured run remains HOST-STABILITY FAIL even if the candidate reaches READY.

A clean single M1 run is not sufficient to promote a production mitigation unless the structural burst is materially reduced and exact managed restoration succeeds.

## Current authorization

Authorized now:

- repository CI;
- building the M1 image from the already validated local R28 image;
- static image inspection;
- read-only checkpoint-order inspection;
- managed runtime identity checks before/after those static actions.

Not authorized now:

- stopping/restarting the managed model;
- launching M1 as a GPU model candidate;
- new RM/kprobe tracing;
- R33 live tracing;
- changing checkpoint/config tensors;
- applying generic CPU offload/UVA as a substitute;
- merging PR #244.

PR #244 remains intentionally open/unmerged.
