# OrcaRouter R25b — initialize_model RM-boundary discriminator — result — 2026-10-05

## Status

**VALID_MEASURED — FUNCTIONAL PASS / HOST-STABILITY FAIL — PRIMARY RM BURST LOCALIZED TO `initialize_model()` WITH A SMALL PRECURSOR BEFORE ENTRY**

R25b is a localization experiment, not a mitigation test. The run preserves the R24 H6/R22-matched controls and adds only userspace timing markers around vLLM v0.29 `initialize_model(...)`.

Strict host-stability policy remains unchanged: any confirmed `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` in a valid measured run is HOST-STABILITY FAIL even if fallback recovers and the runtime reaches READY.

RM logical bytes below are allocator activity volume, not exact resident ownership. Marker overlap is temporal localization, not causal proof.

## Evidence

Attempt-02 evidence:

`/tmp/orcarouter-hybrid-r25b-init-model-boundary-02-20261005`

Console log:

`/tmp/r25b-attempt02-live-20261005-142917.log`

Preserved failed setup attempt:

`/tmp/orcarouter-hybrid-r25b-init-model-boundary-01-20261005`

Preserved R24 baseline evidence:

`/tmp/orcarouter-hybrid-r24-kv16-rm-mitigation-01-20261004`

## Gate / identity

- branch head at launch: `42b2e3bb97a0631993e0dac430710142dac87a3c`;
- stale probe groups before launch: NONE;
- `r25_marker_contract=PASS`;
- `R25B_IMAGE_PREFLIGHT=PASS`;
- diagnostic image: `vllm-orcarouter-v029-r25-init-marker:v1`;
- stability label: `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`;
- diagnostic label: `qwen38.r25=init-model-boundary-v1`;
- `r25b_probe_definition_contract=PASS`;
- `R24_PREFLIGHT=PASS`;
- `R25B_LIVE_PREFLIGHT=PASS`;
- candidate checkpoint: `qwen3.8-h6-modelopt-w4a16`;
- profile: `orcarouter-hybrid`;
- KV bytes: `17179869184`;
- predecessor age at measured run: `9306.307 s` versus required `2700 s`;
- `predecessor_age_ok=1`;
- RM probe target count: `2`.

## Underlying measured run

The R24-matched harness completed validly:

- `run_valid=1`;
- `candidate_start_rc=0`;
- `collector_rc=0`;
- `trace_rc=0`;
- `trace_report_rc=0`;
- `analyzer_rc=0`;
- `wait_ready_rc=0`;
- `api_ready=1`;
- `protected_stop=0`;
- `trace_window_valid=1`;
- `candidate_identity_valid=1`;
- `functional_class=PASS`;
- `host_stability_class=FAIL`;
- `rm_oom_count=3`;
- `event_snapshot_count=3`;
- `ORCA_R24_RESULT=VALID_RM_OOM`.

The strict RM failures were three `_memdescAllocInternal(pMemDesc) @ mem_desc.c:1359` `NV_ERR_NO_MEMORY` events at 2026-10-05 14:40:13.014635, 14:40:13.086800, and 14:42:03.456858 KST.

The common burst remained unchanged relative to R22:

- R22 baseline largest 5 s residual: `75138.043 MiB`;
- R25b candidate largest 1 s residual: `+27138.910 MiB`;
- R25b candidate largest 5 s residual: `+77870.578 MiB`;
- candidate/R22 ratio: `103.636687%`;
- reduction: `-3.636687%`;
- band: `BURST_UNCHANGED`;
- `trace_covers_burst5=1`;
- node0 Normal free delta over burst5: `-78974.434 MiB`;
- global `nr_free_pages` delta over burst5: `-78975.039 MiB`;
- `nv_alloc_pages` events: `575`;
- `nv_alloc_system_pages` events: `538`;
- 64 KiB/order-4 calls: `526`;
- order-4 activity: `77405.938 MiB`;
- order-0 activity: `1.613 MiB`;
- unmatched `nv_alloc_pages` entries/returns: `0/0`;
- unmatched `nv_alloc_system_pages` entries/returns: `0/0`;
- underlying discriminator: `H6_NO_RM_MITIGATION_HOST_FAIL`.

This repeat is not interpreted as a new H6 mitigation trial; it is the matched control needed to localize the already-established RM episode.

## Exact `initialize_model()` alignment

Analyzer result:

- `clock_anchor_count=3`;
- clock-offset spread: `6.176949 ms`;
- classification tolerance: `0.025000 s`;
- marker-pair count: `2`;
- selected `INIT_MODEL_BEGIN`: `433548.345373869`;
- selected `INIT_MODEL_END`: `433551.506439924`;
- selected init duration: `3.161066 s`;
- first RM order-4 activity: `433547.927515000`;
- last RM order-4 activity: `433551.396455000`;
- RM episode duration: `3.468940 s`;
- total order-4 activity: `77405.938 MiB`;
- before selected init: `559.688 MiB`;
- inside selected init: `76846.250 MiB`;
- after selected init: `0.000 MiB`;
- inside-init fraction: `99.276945%`;
- discriminator: `RM_ORDER4_STARTS_BEFORE_INITIALIZE_MODEL`.

The first order-4 RM activity precedes `INIT_MODEL_BEGIN` by approximately `0.417859 s`. The final order-4 RM activity occurs approximately `0.109985 s` before `INIT_MODEL_END`.

Therefore the strict discriminator is correctly `RM_ORDER4_STARTS_BEFORE_INITIALIZE_MODEL`: the episode is not wholly enclosed by the marker pair. However, the engineering interpretation is stronger and more specific than the label alone:

- only `559.688 MiB` (`0.723055%`) occurs before the selected initialization boundary;
- `76846.250 MiB` (`99.276945%`) occurs during `initialize_model()`;
- no order-4 activity occurs after `initialize_model()` returns.

This closes the primary approximately 75–77 GiB RM burst to the first `initialize_model()` / immediate model-construction interval, with a small but real precursor immediately before entry.

## Weight-loading separation

The candidate log contains two initialization marker pairs. For the first pair selected by RM overlap:

- `Loading model from scratch...`: 2026-10-05 05:30:07 UTC;
- first `INIT_MODEL_BEGIN`: 05:30:07;
- first `INIT_MODEL_END`: 05:30:10;
- first `Loading weights took ...`: `601.96 seconds` at 05:40:12.

A second initialization pair appears later:

- second `INIT_MODEL_BEGIN`: 05:40:23;
- second `INIT_MODEL_END`: 05:40:24;
- second `Loading weights took ...`: `69.95 seconds` at 05:41:35.

The full traced order-4 episode has already ended by `433551.396455`, before the first selected `INIT_MODEL_END`. Therefore neither the long 601.96 s checkpoint-fill interval nor the later second initialization/69.95 s load interval owns the approximately 77 GiB RM episode.

This does not yet identify which constructor, module family, tensor-storage materialization, or parameter registration inside `initialize_model()` is causal. It localizes the next boundary.

## Managed restoration

Managed restoration closed PASS:

- wrapper `managed_restore_ready_rc=0`;
- exact managed OrcaRouter service became READY after `880 s`;
- restored model id: `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`;
- restored `max_model_len=262144`;
- service active after restoration;
- attempt-02 wrapper final result: `ORCA_R25B_RESULT=VALID_MEASURED`;
- command RC: `0`.

The long restoration interval reflects the normal PLE/safetensors reload path and does not invalidate the completed candidate measurement.

## Closure

R25b closes the current userspace phase question as follows:

`model-loading entry / small precursor (~560 MiB) -> initialize_model() (~76.85 GiB direct-RM order-4 activity) -> no remaining order-4 activity after init -> long checkpoint filling continues separately`

Combined with R23/R24, the highest-confidence observed chain is now:

`early model construction -> direct NVIDIA RM 64 KiB system-page demand -> node0 Normal/Unmovable order-4 depletion -> high-order allocation failure -> rollback/order-0 fallback -> NV_ERR_NO_MEMORY`

The userspace trigger is not yet closed below `initialize_model()`.

## Next engineering direction

Do not repeat H6, and do not broaden tracing.

The next discriminator should instrument the smallest stable boundaries **inside the first `initialize_model()` path** to separate:

1. model-class resolution/import and constructor entry;
2. top-level model/module construction;
3. routed-expert / packed expert parameter construction or storage materialization;
4. constructor return.

The approximately `559.688 MiB` precursor should also be retained as a distinct pre-init side observation rather than merged into the main 76.8 GiB burst.

H11 is now a materially relevant hypothesis because initialization/parameter construction is implicated, but changing H11 behavior should follow one more observational boundary split rather than precede it. H12 remains lower priority because the RM episode is already finished before post-load processing.

PR #244 remains open. No merge is implied.
