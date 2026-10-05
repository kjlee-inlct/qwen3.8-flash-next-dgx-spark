# OrcaRouter R25b — initialize_model RM-boundary discriminator — plan — 2026-10-05

## Status

**IMPLEMENTED / IMAGE BUILD + STATIC PREFLIGHT ONLY — LIVE RUN NOT YET AUTHORIZED**

R25 read-only localization showed that the R24 64 KiB NVIDIA RM episode is only about 3.218 seconds long even though checkpoint weight filling takes 522.10 seconds. `99.276945%` of traced order-4 activity falls between the existing `Loading model from scratch...` marker and `Loading weights took ...`, but the first approximately `559.688 MiB` begins about `0.395 s` before the existing model-load marker.

The pinned vLLM v0.29 `BaseModelLoader.load_model()` order is:

1. enter the target device context;
2. `initialize_model(...)`;
3. `load_weights(...)`;
4. online-quant finalization when applicable;
5. `process_weights_after_loading(...)`.

R25 therefore narrows the next question to model/parameter construction versus checkpoint filling. R25b adds exactly two userspace log boundaries around `initialize_model()` and otherwise preserves the R24 runtime/harness.

## Question

Does the approximately 77 GiB 64 KiB `nv_alloc_pages` episode occur primarily inside `initialize_model()` before checkpoint weight filling begins?

This is still a localization discriminator, not a mitigation test.

## Diagnostic image

Repository additions:

- `scripts/patch-v029-r25-init-model-markers.py`;
- `scripts/Dockerfile.v029-r25-init-model-markers`;
- `scripts/benchmark/check-orcarouter-r25b-init-model-image.sh`.

Intended image tag:

`vllm-orcarouter-v029-r25-init-marker:v1`

The image derives directly from `vllm-orcarouter-v029:v1`. It adds only these INFO markers in `BaseModelLoader.load_model()`:

- `QWEN38_R25_INIT_MODEL_BEGIN` immediately before entering the target-device `initialize_model(...)` block;
- `QWEN38_R25_INIT_MODEL_END` immediately after `initialize_model(...)` returns and before `load_weights(...)`.

It does not change checkpoint contents, parameter classes, quantization behavior, runtime flags, PLE mmap, exact QSA, KV size, host conditioning, allocator behavior, or post-load handling.

## Build/static-preflight gate

Before any live run:

1. build the diagnostic image locally from the already-present R24 base image;
2. run `scripts/benchmark/check-orcarouter-r25b-init-model-image.sh`;
3. require inherited stability label `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`;
4. require diagnostic label `qwen38.r25=init-model-boundary-v1`;
5. require exactly one begin marker and one end marker in `base_loader.py` with source ordering:
   `BEGIN < initialize_model < END < load_weights`;
6. do not restart the model, stop the managed service, or change VM/kernel state during this gate.

Expected terminal gate:

`R25B_IMAGE_PREFLIGHT=PASS`

## Live-run boundary

A live R25b run must not start merely because the image builds. The live runner must preserve the R24 matched controls and strict host-stability policy while using a unique experiment container/evidence path so the preserved R24 container/evidence are not overwritten.

The RM trace remains restricted to the already-closed boundaries:

- `nv_alloc_pages`;
- `nv_alloc_system_pages`;
- optional static NVIDIA Xid event if available.

No UVM, generic page allocation, scheduler, function graph, CUDA API blanket tracing, or broad Python profiling should be added.

## Interpretation

After a valid live run, map the two R25b markers onto the same monotonic clock as the RM trace and compute 64 KiB activity inside `initialize_model()`.

- If nearly all order-4 RM activity lies inside `initialize_model()`: close the next layer to CUDA-side model/parameter/storage construction and design mitigation around construction/materialization shape.
- If substantial activity begins only after `INIT_MODEL_END`: instrument the smallest weight-loader boundary next.
- If the episode straddles both: quantify each portion before changing behavior.

H11 is potentially relevant only after initialization is implicated because it changes packed expert parameter construction. H12 remains lower priority for this host-stability question because it changes a later post-load wrapping/rename path.

PR #244 remains open. No merge is implied.
