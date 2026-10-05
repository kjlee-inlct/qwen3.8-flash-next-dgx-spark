# OrcaRouter R25 — userspace load-phase localization plan — 2026-10-05

## Status

**IMPLEMENTED / READ-ONLY POST-HOC ANALYSIS NOT YET RUN**

R24 rejects H6 ModelOpt W4A16 as a host-stability mitigation under R22-matched 16 GiB runtime controls. The early direct NVIDIA RM system-memory burst remains unchanged and one strict RM OOM still occurs.

R25 therefore does not begin with another live checkpoint/config experiment. Its first step is a zero-restart, read-only localization pass over the preserved R24 evidence.

## Question

Which coarse userspace model-loading phase contains the already-closed approximately 77 GiB 64 KiB-path `nv_alloc_pages` episode?

The intended distinction is:

1. model/weight loading;
2. post-load model finalization/materialization;
3. CUDA graph capture / later initialization;
4. insufficient log milestones to distinguish them.

This is temporal phase localization, not causal proof.

## Preserved evidence used

The analyzer consumes only the existing R24 evidence directory:

- `candidate-container.log` captured with `docker logs --timestamps`;
- `candidate-request-iso.txt` + `candidate-request-monotonic-ns.txt`;
- `trace-window-start-iso.txt` + `trace-window-start-monotonic-ns.txt`;
- `trace-window-end-iso.txt` + `trace-window-end-monotonic-ns.txt`;
- `rm-trace.txt`;
- `r24-analysis.txt`;
- `host-page-size.txt`.

No service, model, Docker container, VM setting, tracepoint, or kernel state is changed.

## Clock alignment

The analyzer derives wall-clock to monotonic offset from three preserved anchor pairs and reports their offset spread. Timestamped container log lines are then mapped onto the same monotonic clock as the RM trace.

The relevant log markers are searched conservatively:

- `Loading model from scratch`;
- a weight-load completion line such as `Loading weights took ...` / `Loading model weights took ...`;
- a model-load completion line such as `Model loading took ...`;
- CUDA graph capture start when present.

The analyzer also prints nearby loading/materialization milestones around the independently selected R24 five-second burst.

## RM accounting

Only the already-closed `nv_alloc_pages` 64 KiB path is used. Logical activity bytes retain the established R23/R24 semantics:

`page_count * host_page_size`

where host page size is the preserved system page size (4096 bytes on the measured host).

These bytes are activity volume, not exact resident ownership.

## Discriminators

The analyzer emits one of:

- `RM_ORDER4_ACTIVITY_WITHIN_WEIGHT_LOAD_INTERVAL`;
- `RM_ORDER4_ACTIVITY_STRADDLES_WEIGHT_LOAD_END`;
- `RM_ORDER4_ACTIVITY_AFTER_WEIGHT_LOAD`;
- `RM_ORDER4_ACTIVITY_PARTLY_BEFORE_MODEL_LOAD`;
- `INSUFFICIENT_WEIGHT_LOAD_MILESTONES`.

If the full 64 KiB RM episode lies inside the model-start → weight-load-end interval, the next live R25 instrumentation should target the narrowest practical weight allocation/loading/materialization boundary rather than post-load or CUDA-graph code.

If the episode begins after the weight-load completion marker, the next live probe should instead target post-load conversion/materialization.

If the log lacks a decisive weight marker, preserve the inconclusive result and add only the smallest marker needed to distinguish those phases; do not broaden to generic Python, CUDA, UVM, scheduler, or all-driver tracing.

## Existing repository controls relevant to follow-up

The repository already contains loader-shape controls that may become useful only after phase localization:

- H11 changes packed expert weights from plain `torch.nn.Parameter` to `ModelWeightParameter` while preserving on-disk names/values;
- H12 preserves those packed parameter objects through the compressed-tensors post-load rename instead of wrapping `.data` in new `torch.nn.Parameter` objects.

These controls are not automatically selected for a live R25 run. The post-hoc result must first show whether the RM episode is in weight load versus post-load finalization, and any later use of H11/H12 must be justified by that phase result.

## Implementation

- `scripts/benchmark/analyze-orcarouter-r24-load-phase.py`
- `tests/test_orcarouter_r24_load_phase.py`

The analysis is intentionally read-only and can be run against the preserved R24 evidence without disturbing the now-restored managed service.

PR #244 remains open; no merge is implied.