# OrcaRouter R25 — userspace load-phase localization result — 2026-10-05

## Status

**READ-ONLY POST-HOC PASS — RM BURST LOCALIZED TO EARLIEST MODEL/WEIGHT MATERIALIZATION WINDOW**

R25 analyzed the preserved R24 H6 evidence without restarting the model, changing the service, or changing host/kernel state. The wall-clock/container-log timeline was aligned to the monotonic RM trace using three preserved anchors.

The live post-hoc discriminator was:

`RM_ORDER4_ACTIVITY_PARTLY_BEFORE_MODEL_LOAD`

This label is conservative because the first observed 64 KiB RM call precedes the existing `Loading model from scratch...` log marker by about 0.395 s. The important quantitative result is that essentially the entire RM episode is concentrated in the first few seconds of model materialization, while the later safetensors weight-fill phase continues for hundreds of seconds.

## Clock alignment

Observed alignment:

- anchor count: `3`;
- wall-clock/monotonic offset spread: `4.907608 ms`.

This spread is far smaller than the multi-second RM episode and is adequate for coarse phase localization.

## R24 burst and RM episode

The independently reconstructed R24 five-second burst was:

- start monotonic: `382548.943040064`;
- end monotonic: `382553.943487653`;
- unexplained residual growth: `+77937.680 MiB`.

The observed 64 KiB/order-4 `nv_alloc_pages` episode was:

- first call: `382550.429568000`;
- last call: `382553.647241000`;
- duration: approximately `3.217673 s`;
- total activity: `77405.938 MiB`;
- activity inside the same five-second burst: `77405.938 MiB`.

Thus the entire observed 64 KiB RM episode is contained inside the independently selected physical residual burst.

## Model-loading milestones

Mapped container-log milestones:

- engine initialization log: monotonic `382544.232777357`, `-4.710263 s` relative to burst start;
- `Loading model from scratch...`: monotonic `382550.824214458`, `+1.881174 s` relative to burst start;
- `Loading weights took 522.10 seconds`: monotonic `383076.126421452`, `+527.183381 s`;
- `Model loading took 79.41 GiB memory and 610.328639 seconds`: monotonic `383160.989125490`, `+612.046085 s`;
- no decisive CUDA-graph-start marker was present in the preserved log.

The first RM order-4 call precedes the existing `Loading model from scratch...` marker by approximately `0.394646 s`. The last RM order-4 call occurs only approximately `2.823027 s` after that marker.

By contrast, the weight-load completion marker appears roughly `525.302207 s` after model-load start.

## Weight-load interval coverage

Using the existing `Loading model from scratch...` marker as the coarse interval start and the weight-load completion marker as the interval end:

- order-4 RM activity in interval: `76846.250 MiB`;
- coverage of total traced order-4 RM activity: `99.276945%`;
- activity outside that coarse interval: approximately `559.688 MiB` (`0.723055%`).

The small out-of-interval fraction is entirely explained by the first approximately 0.395 s of the RM episode occurring before the current model-load log marker. No material RM activity persists anywhere near the 522 s weight-load completion boundary.

## Source-order interpretation

Pinned vLLM v0.29 source establishes this loader order in `BaseModelLoader.load_model()`:

1. enter `target_device`;
2. call `initialize_model(...)`;
3. call `load_weights(...)`;
4. run online-quant finalization when applicable;
5. call `process_weights_after_loading(...)`;
6. return `model.eval()`.

`DefaultModelLoader.load_weights()` then calls the model's `load_weights(...)` over the safetensors iterator and only afterward emits `Loading weights took ...`.

Therefore the R25 timing is much more consistent with the earliest CUDA-side model/parameter/storage materialization around `initialize_model()` / immediate loader entry than with:

- the full 522 s safetensors data-fill process;
- post-load `process_weights_after_loading()`;
- CUDA graph capture.

This is still temporal evidence, not causal proof. The existing `Loading model from scratch...` log is not an exact `initialize_model()` entry marker, and the first 559.688 MiB of RM activity begins before it.

## Consequence for H11/H12

R25 does **not** justify jumping directly to H12 post-load preservation as the next host-stability experiment. The direct RM burst is finished hundreds of seconds before post-load completion.

H11/H12 remain useful implementation controls later if a narrower model-initialization experiment shows that compressed-tensors expert parameter construction is part of the initial materialization burst. In particular:

- H11 changes packed expert weight parameter objects to `ModelWeightParameter` at construction time and is therefore potentially relevant to an initialization-phase discriminator;
- H12 changes the later post-load rename/wrapping lifecycle and is lower priority for the RM burst because the measured burst has already ended long before weight-load completion.

## Next engineering direction

The next live diagnostic should add only the smallest missing userspace boundaries around `BaseModelLoader.load_model()`:

- `initialize_model` entry;
- `initialize_model` return / `load_weights` entry.

Keep the already-closed narrow RM trace (`nv_alloc_pages` / `nv_alloc_system_pages`) and the matched R22/R24 host harness. Do not add broad Python profiling, CUDA API tracing, UVM tracing, scheduler tracing, generic page-allocation tracing, or all-driver tracing.

The next discriminator should answer one binary question:

> Does the approximately 77 GiB 64 KiB RM episode lie primarily inside `initialize_model()` before checkpoint weight filling begins?

If yes, the following mitigation work should target parameter/storage construction/materialization shape. If no, add the smallest next boundary inside `load_weights()` rather than broadening observability.

PR #244 remains open; no merge is implied.
