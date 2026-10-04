# Benchmark evidence index

This directory preserves canonical evidence for live DGX Spark runtime, profile-switch, host-stability, and allocator experiments. Historical per-run documents should remain immutable in meaning: later analysis may add links or later-closure notes, but should not rewrite what a run actually observed.

## Current host-stability / RM allocator closure

Start here for the current R9–R22 conclusion:

- `orcarouter-managed-rmsys-r9-r22-allocator-closure-20261004.md`

The current leading result is that R21 and R22 share an early physical-page allocation burst of about 75 GiB over roughly five seconds, ultimately leaving an approximately 89.5–90.0 GiB physical-page residual not explained by the selected conventional Linux resident accounting. Nearly the entire free-page loss occurs in node0 Normal while managed capacity remains unchanged. This is strongly consistent with the direct NVIDIA RM/kernel system-page mechanism traced in R11, but exact ownership of the common 75–90 GiB footprint is not yet proven.

Legacy PLE CPU-offload is a separate pressure amplifier: it adds roughly 100 GiB of later swap/residency churn, but R22 shows that removing that path with mmap does not remove the common early burst or the strict RM OOM.

Strict classification policy remains:

> Any confirmed `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` in a valid measured run is HOST-STABILITY FAIL even if fallback recovers and the runtime reaches READY.

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

## R21 page-cache / startup-collapse evidence

- `orcarouter-managed-rmsys-r21-pagecache-reclaim-plan-20261004.md`
- `orcarouter-managed-rmsys-r21-pagecache-reclaim-result-20261004.md`
- `orcarouter-managed-rmsys-r21-collapse-onset-20261004.md`

R21 is `VALID_RM_OOM`: page-cache reclaim and post-stop compaction materially improve pre-start state and avoid the R20 protection boundary, but do not eliminate strict RM fallback.

## R22 mmap discriminator and cross-run closure

- `orcarouter-managed-rmsys-r22-v029-mmap-plan-20261004.md`
- `orcarouter-managed-rmsys-r22-v029-mmap-result-20261004.md`
- `orcarouter-managed-rmsys-r21-r22-mmap-comparison-20261004.md`
- `orcarouter-managed-rmsys-r21-r22-unaccounted-trajectory-20261004.md`

R22 is also `VALID_RM_OOM`. mmap materially reduces sustained swap pressure and slows later high-order depletion, but it does not remove the initial catastrophic high-order collapse or strict RM failure.

The cross-run trajectory is the current strongest common-path discriminator:

- R21 largest 5 s unexplained-residual increase: `+75174.387 MiB`;
- R22 largest 5 s unexplained-residual increase: `+75138.043 MiB`.

## R23 early-burst ownership trace

- `orcarouter-managed-rmsys-r23-early-burst-ownership-plan-20261004.md`

R23 is currently **DESIGN / NO TEST**. It is explicitly not another broad VM-tuning experiment. The plan keeps the current managed OrcaRouter runtime and established conditioning/protection harness fixed, then records only a narrow startup window around the known common burst using the minimum RM/UVM allocation-boundary probes needed for ownership attribution.

The first live instrumentation set centers on `nv_alloc_pages`, `nv_alloc_system_pages`, `nvUvmInterfacePmaAllocPages`, `uvm_gpu_dma_alloc`, `uvm_mem_alloc`, and `uvm_pmm_gpu_alloc_kernel`. Broad page alloc/free, compaction/reclaim/extfrag, function-graph, scheduler, and full-driver tracing are excluded from the first R23 live run because R11 already closes the Linux high-order allocator mechanism.

## Current next diagnostic direction

Do not return to broad watermark, compaction, drop-cache, or swap tuning as the primary diagnostic path.

Complete the R23 probe-only preflight/helper, focused tests, narrow-window managed runner, and analyzer. Only after CI is green should a live R23 restart be issued. The live goal is to align RM/UVM boundary activity and task attribution with the approximately 75 GiB early residual formation, not to evaluate another mitigation.

Do not merge or promote reclaim/compaction or mmap behavior as a production mitigation from R9–R22 evidence alone.
