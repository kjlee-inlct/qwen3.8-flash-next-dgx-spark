# OrcaRouter R25 — userspace load-phase localization plan — 2026-10-05

## Status

**COMPLETED — READ-ONLY POST-HOC PASS**

Canonical result:

`orcarouter-r25-load-phase-localization-result-20261005.md`

R24 rejects H6 ModelOpt W4A16 as a host-stability mitigation under R22-matched 16 GiB runtime controls. R25 therefore used the preserved R24 evidence only; it did not restart the model, mutate the managed service, or change host/kernel state.

## Question

Which coarse userspace model-loading phase contains the already-closed approximately 77 GiB 64 KiB-path `nv_alloc_pages` episode?

The intended distinction was model/weight loading versus post-load finalization versus later CUDA-graph/runtime initialization. This is temporal phase localization, not causal proof.

## Preserved evidence used

The analyzer consumed only the existing R24 evidence directory:

- `candidate-container.log` captured with `docker logs --timestamps`;
- `candidate-request-iso.txt` + `candidate-request-monotonic-ns.txt`;
- `trace-window-start-iso.txt` + `trace-window-start-monotonic-ns.txt`;
- `trace-window-end-iso.txt` + `trace-window-end-monotonic-ns.txt`;
- `rm-trace.txt`;
- `r24-analysis.txt`;
- `host-page-size.txt`.

No service, model, Docker container, VM setting, tracepoint, or kernel state was changed.

## Observed result

Clock alignment used three preserved anchors with `4.907608 ms` maximum offset spread.

R24 five-second burst:

- start: `382548.943040064`;
- end: `382553.943487653`;
- residual increase: `+77937.680 MiB`.

Observed 64 KiB/order-4 RM episode:

- first call: `382550.429568000`;
- last call: `382553.647241000`;
- duration: approximately `3.217673 s`;
- total activity: `77405.938 MiB`;
- all `77405.938 MiB` lies inside the independently selected five-second burst.

Mapped userspace markers:

- engine initialization: `382544.232777357`;
- `Loading model from scratch...`: `382550.824214458`;
- `Loading weights took 522.10 seconds`: `383076.126421452`;
- `Model loading took 79.41 GiB memory and 610.328639 seconds`: `383160.989125490`;
- no decisive CUDA-graph-start marker was required for this discriminator.

The existing model-load-start → weight-load-end interval contains `76846.250 MiB`, or `99.276945%`, of traced order-4 activity. Only approximately `559.688 MiB` (`0.723055%`) occurs before the existing `Loading model from scratch...` marker, and that leading portion starts only about `0.394646 s` earlier.

The live post-hoc discriminator is therefore:

`RM_ORDER4_ACTIVITY_PARTLY_BEFORE_MODEL_LOAD`

This label is intentionally conservative. The material conclusion is that the approximately 77 GiB RM episode is concentrated in the first approximately 3.2 seconds of model construction/loading and finishes hundreds of seconds before checkpoint filling and model-load completion.

## Source-order interpretation

Pinned vLLM v0.29 `BaseModelLoader.load_model()` executes:

1. enter target device context;
2. `initialize_model(...)`;
3. `load_weights(...)`;
4. online-quant finalization when applicable;
5. `process_weights_after_loading(...)`.

`DefaultModelLoader.load_weights()` emits `Loading weights took ...` only after the model's safetensors iterator has been consumed.

Therefore the timing is much more consistent with the earliest CUDA-side model/parameter/storage materialization around `initialize_model()` / immediate loader entry than with the full 522 s safetensors fill, post-load processing, or CUDA-graph capture. This remains a hypothesis until the exact `initialize_model()` boundary is measured.

## Consequence for H11/H12

R25 does not justify a direct H12 host-stability run. H12 changes a later post-load parameter wrapping/rename path, while the RM episode is already over hundreds of seconds earlier.

H11 remains potentially relevant later because it changes packed expert parameter construction. It should only be used after an exact initialization-boundary discriminator shows that construction is inside the RM episode.

## Follow-up

The next phase is R25b:

`orcarouter-r25b-init-model-boundary-plan-20261005.md`

R25b adds only two INFO markers around `initialize_model()` in a diagnostic image derived from the exact R24 base image. Before any live run, the required action is **image build + static image preflight only**. A model restart is not authorized by this plan.

Implementation:

- `scripts/benchmark/analyze-orcarouter-r24-load-phase.py`;
- `tests/test_orcarouter_r24_load_phase.py`;
- `scripts/patch-v029-r25-init-model-markers.py`;
- `scripts/Dockerfile.v029-r25-init-model-markers`;
- `scripts/benchmark/check-orcarouter-r25b-init-model-image.sh`.

Do not broaden to generic Python profiling, CUDA API blanket tracing, UVM, scheduler, generic page allocation, function graph, or all-driver tracing.

PR #244 remains open; no merge is implied.
