# Benchmark evidence index

This directory preserves canonical evidence for live DGX Spark runtime, profile-switch, host-stability, and allocator experiments. Historical per-run documents should remain immutable in meaning: later analysis may add links or later-closure notes, but should not rewrite what a run actually observed.

## Current host-stability / RM allocator closure

Start with the R9–R22 allocator closure, then R23 ownership, R24 mitigation, R25 coarse userspace localization, R25b exact `initialize_model()` localization, and R26 construction-boundary localization:

- `orcarouter-managed-rmsys-r9-r22-allocator-closure-20261004.md`
- `orcarouter-managed-rmsys-r23-early-burst-ownership-result-20261004.md`
- `orcarouter-managed-rmsys-r23-ownership-closure-20261004.md`
- `orcarouter-hybrid-r24-kv16-rm-mitigation-result-20261005.md`
- `orcarouter-r25-load-phase-localization-result-20261005.md`
- `orcarouter-r25b-init-model-boundary-plan-20261005.md`
- `orcarouter-r25b-init-model-image-preflight-result-20261005.md`
- `orcarouter-r25b-live-harness-preflight-result-20261005.md`
- `orcarouter-r25b-live-attempt01-probe-group-invalid-20261005.md`
- `orcarouter-r25b-recovery-corrected-preflight-result-20261005.md`
- `orcarouter-r25b-init-model-boundary-result-20261005.md`
- `orcarouter-r26-construction-boundary-plan-20261005.md`

R21/R22 established a common early physical-page burst of about 75 GiB over roughly five seconds. R23 closes the observed driver-level ownership endpoint to direct NVIDIA RM system-memory allocation (`nv_alloc_pages` / `nv_alloc_system_pages`) rather than the selected UVM allocation boundaries. In the independently selected R23 five-second window, 64 KiB RM activity is `74,537.938 MiB` versus `75,083.652 MiB` unexplained-residual growth (`99.273191%`), while selected UVM coverage is `0.000000%`.

R24 tested H6 ModelOpt W4A16 under R22-matched 16 GiB runtime controls. It did not mitigate the mechanism: largest five-second residual `77,937.680 MiB`, R22 ratio `103.725991%`, same-window RM activity `77,405.938 MiB`, and one strict RM OOM. Classification remains **FUNCTIONAL PASS / HOST-STABILITY FAIL — H6 NO RM MITIGATION**.

R25 then localized that R24 RM activity with preserved evidence only. The RM order-4 episode lasts about `3.217673 s`, while checkpoint filling continues for `522.10 s`; `99.276945%` of traced RM activity lies between the coarse model-start and weight-load-completion markers. The first approximately `559.688 MiB` starts about `0.395 s` before the old model-start log, making the exact `initialize_model()` boundary the next highest-information discriminator.

R25b completed that boundary measurement. Attempt 01 was setup-invalid before candidate launch because the wrapper changed the shell kprobe group but not four inherited hard-coded probe definitions; the stale group was later verified and cleaned, the transform was fixed and regression-tested, and corrected preflight passed. Attempt 02 then completed as `VALID_MEASURED` with **FUNCTIONAL PASS / HOST-STABILITY FAIL**.

R25b exact alignment:

- total order-4 RM activity: `77405.938 MiB`;
- before selected `initialize_model()`: `559.688 MiB`;
- inside selected `initialize_model()`: `76846.250 MiB`;
- after selected `initialize_model()`: `0.000 MiB`;
- inside-init fraction: `99.276945%`;
- init duration: `3.161066 s`;
- RM episode duration: `3.468940 s`;
- strict discriminator: `RM_ORDER4_STARTS_BEFORE_INITIALIZE_MODEL`.

The strict label reflects a real approximately `0.418 s` / `559.688 MiB` precursor before the marker. Engineering closure is that the primary approximately 75–77 GiB burst occurs during the first `initialize_model()` / immediate model-construction interval, while the long checkpoint-fill phase continues separately and owns none of the remaining traced order-4 activity after init return.

R26 is the next observational discriminator. It keeps the R24/R25b runtime and narrow RM trace unchanged while adding INFO-only boundaries around the top-level `model_class(...)` constructor, `ModelOptNvFp4FusedMoE.create_weights()`, and the large routed-expert `w13_weight` / `w2_weight` allocations. Repository implementation is complete and CI-tested; the next gate is **static image build + static image preflight only**. No R26 live run is authorized yet.

Strict classification policy remains:

> Any confirmed `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` in a valid measured run is HOST-STABILITY FAIL even if fallback recovers and the runtime reaches READY.

RM logical requested bytes remain activity volume rather than exact resident ownership. Userspace marker alignment is temporal localization rather than causal proof.

## Lower-level allocator mechanism

- `r9-acceptance-gate-20261002.md`
- `r9-rm-sysmem-root-cause-20261002.md`
- `orcarouter-managed-rmsys-r10b-02-rm-oom-20261003.md`
- `orcarouter-managed-rmsys-r11-allocator-state-20261003.md`

R11 is the canonical exact zone/migratetype closure: node0 Normal-zone Unmovable order-4 demand, Movable fallback/pageblock stealing, failed chunk acquisition, rollback, and immediate order-0 retry.

## Conditioning / mitigation experiments

- `orcarouter-managed-rmsys-r12-precompact-20261003.md`
- `orcarouter-managed-rmsys-r13-proactive80-20261003.md`
- `orcarouter-managed-rmsys-r14-watermark100-20261003.md`
- `orcarouter-managed-rmsys-r14-watermark-comparison-20261003.md`
- `orcarouter-managed-rmsys-r15-paired-watermark-20261003.md`
- `orcarouter-managed-rmsys-r16-reverse-watermark-20261004.md`
- `orcarouter-managed-rmsys-r17-baseline-repeat-20261004.md`
- `orcarouter-managed-rmsys-r18-poststop-compact-20261004.md`
- `orcarouter-managed-rmsys-r19-stoponly-control-20261004.md`
- `orcarouter-managed-rmsys-r20-poststop-compact-invalid-20261004.md`

These runs collectively reject broad watermark/compaction/full-stop/static-high-order-state explanations as deterministic production fixes.

## R21 / R22 startup-collapse evidence

- `orcarouter-managed-rmsys-r21-pagecache-reclaim-plan-20261004.md`
- `orcarouter-managed-rmsys-r21-pagecache-reclaim-result-20261004.md`
- `orcarouter-managed-rmsys-r21-collapse-onset-20261004.md`
- `orcarouter-managed-rmsys-r22-v029-mmap-plan-20261004.md`
- `orcarouter-managed-rmsys-r22-v029-mmap-result-20261004.md`
- `orcarouter-managed-rmsys-r21-r22-mmap-comparison-20261004.md`
- `orcarouter-managed-rmsys-r21-r22-unaccounted-trajectory-20261004.md`

Both R21 and R22 are `VALID_RM_OOM`. mmap materially reduces later PLE swap/residency pressure but does not remove the common early burst or strict RM failure.

## R23 ownership closure

- `orcarouter-managed-rmsys-r23-early-burst-ownership-plan-20261004.md`
- `orcarouter-managed-rmsys-r23-probe-preflight-result-20261004.md`
- `orcarouter-managed-rmsys-r23-early-burst-ownership-result-20261004.md`
- `orcarouter-managed-rmsys-r23-ownership-closure-20261004.md`

R23 is **VALID_RM_OOM — FUNCTIONAL PASS / HOST-STABILITY FAIL**. The narrow trace captured 668 successful `nv_alloc_pages` calls and 599 successful `nv_alloc_system_pages` calls. Selected UVM PMA/DMA/PMM boundaries were silent, and the two observed `uvm_mem_alloc` calls wrapped zero RM calls.

## R24 H6 16 GiB discriminator

- `orcarouter-hybrid-r24-kv16-rm-mitigation-plan-20261004.md`
- `orcarouter-hybrid-r24-kv16-rm-mitigation-result-20261005.md`

R24 is **VALID_RM_OOM — FUNCTIONAL PASS / HOST-STABILITY FAIL — H6 NO RM MITIGATION**. Managed restoration was later verified healthy and is closed PASS.

## R25 load-phase localization

- `orcarouter-r25-load-phase-localization-plan-20261005.md`
- `orcarouter-r25-load-phase-localization-result-20261005.md`

R25 is a completed read-only post-hoc localization. It does not itself prove the userspace cause, but it excludes post-load/CUDA-graph timing as the primary location of the short common RM episode and prioritizes exact early model construction boundaries.

Repository implementation:

- `scripts/benchmark/analyze-orcarouter-r24-load-phase.py`
- `tests/test_orcarouter_r24_load_phase.py`

## R25b initialize_model boundary discriminator

Canonical sequence:

- `orcarouter-r25b-init-model-boundary-plan-20261005.md`
- `orcarouter-r25b-init-model-image-preflight-result-20261005.md`
- `orcarouter-r25b-live-harness-preflight-result-20261005.md`
- `orcarouter-r25b-live-attempt01-probe-group-invalid-20261005.md`
- `orcarouter-r25b-recovery-corrected-preflight-result-20261005.md`
- `orcarouter-r25b-init-model-boundary-result-20261005.md`

Repository implementation:

- `scripts/patch-v029-r25-init-model-markers.py`
- `scripts/Dockerfile.v029-r25-init-model-markers`
- `scripts/benchmark/check-orcarouter-r25b-init-model-image.sh`
- `scripts/benchmark/run-orcarouter-r25b-init-model-boundary.sh`
- `scripts/benchmark/analyze-orcarouter-r25b-init-model-overlap.py`
- `tests/test_orcarouter_r25b_init_model_overlap.py`

R25b is **COMPLETED — VALID_MEASURED — FUNCTIONAL PASS / HOST-STABILITY FAIL**. The primary RM episode is localized to the first `initialize_model()` interval with a small pre-init precursor. Managed restoration closed PASS after `880 s`, and the final wrapper/command returned zero.

## R26 construction / ModelOpt-MoE boundary discriminator

- `orcarouter-r26-construction-boundary-plan-20261005.md`

Repository implementation:

- `scripts/patch-v029-r26-construction-markers.py`
- `scripts/Dockerfile.v029-r26-construction-markers`
- `scripts/benchmark/check-orcarouter-r26-construction-image.sh`
- `scripts/benchmark/analyze-orcarouter-r26-construction-overlap.py`
- `scripts/benchmark/run-orcarouter-r26-construction-boundary.sh`
- `tests/test_orcarouter_r26_construction_markers.py`
- `tests/test_orcarouter_r26_construction_overlap.py`
- `tests/test_orcarouter_r26_runner_transform.py`

R26 is **IMPLEMENTED — STATIC IMAGE BUILD/PREFLIGHT NEXT — NO LIVE RUN AUTHORIZED YET**. It refines the R25b first-init interval into the top-level constructor, ModelOpt NVFP4 routed-expert `create_weights()`, and w13/w2 packed-storage allocation boundaries. The R26 runner preserves the matched R24 controls, transforms all four RM probe definitions to a unique `r26_rm` group, blocks stale R24/R25b/R26 groups, and requires exact managed OrcaRouter identity during post-run restoration.

## Current next engineering direction

Do not repeat H6 merely to seek a different outcome, and do not return to broad watermark, compaction, drop-cache, swap, page-allocation, scheduler, function-graph, UVM, or all-driver tracing.

Build the R26 marker-only image and run **static image preflight only**, with managed container ID and `StartedAt` checked before and after. Do not start the R26 harness preflight or any live R26 measured run until the static image gate is canonically closed.

If a later R26 measured run places at least 90% of total order-4 RM activity inside `ModelOptNvFp4FusedMoE.create_weights()`, parameter/storage construction is directly implicated and the next discriminator may isolate H11-like parameter-object/storage semantics. If ModelOpt-MoE coverage is low while constructor coverage remains high, instrument the smallest remaining constructor subpath instead. Keep the approximately `559.688 MiB` pre-init precursor separate from the primary 76.8 GiB burst.

H11 is now materially relevant because initialization/parameter construction is implicated, but behavior-changing H11 work should follow this R26 internal construction-boundary measurement. H12 remains lower priority because the traced RM episode is already finished before post-load processing.

Conditioning and mmap remain measurement controls/discriminators, not accepted production mitigations.

PR #244 remains intentionally open and must not be merged before mitigation/Hybrid closure and explicit merge timing.
