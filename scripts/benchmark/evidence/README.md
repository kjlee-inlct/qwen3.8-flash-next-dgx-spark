# Benchmark evidence index

This directory preserves canonical evidence for live DGX Spark runtime, profile-switch, host-stability, and allocator experiments. Historical per-run documents should remain immutable in meaning: later analysis may add links or later-closure notes, but should not rewrite what a run actually observed.

## Current host-stability / RM allocator closure

Start with the R9–R22 allocator closure, then the R23 ownership result:

- `orcarouter-managed-rmsys-r9-r22-allocator-closure-20261004.md`
- `orcarouter-managed-rmsys-r23-early-burst-ownership-result-20261004.md`

R21 and R22 first established a common early physical-page allocation burst of about 75 GiB over roughly five seconds, ultimately leaving an approximately 89.5–90.0 GiB physical-page residual not explained by the selected conventional Linux resident accounting. Nearly the entire free-page loss occurs in node0 Normal while managed capacity remains unchanged.

R23 now directly aligns that common burst with NVIDIA RM system-memory activity. The R23 narrow trace recorded `75,077.375 MiB` of 64 KiB-path `nv_alloc_pages` logical activity while the independently reconstructed largest five-second unexplained residual increased by `75,083.652 MiB`, a difference of only `6.277 MiB` (~`0.0084%`). This is strong ownership evidence for the direct RM system-page path, while preserving the guard that cumulative requested bytes are activity volume rather than exact resident ownership.

Legacy PLE CPU-offload remains a separate pressure amplifier: it adds roughly 100 GiB of later swap/residency churn, but R22 shows that removing that path with mmap does not remove the common early burst or the strict RM OOM.

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

The cross-run trajectory remains the common-path baseline:

- R21 largest 5 s unexplained-residual increase: `+75174.387 MiB`;
- R22 largest 5 s unexplained-residual increase: `+75138.043 MiB`.

## R23 early-burst ownership trace

- `orcarouter-managed-rmsys-r23-early-burst-ownership-plan-20261004.md`
- `orcarouter-managed-rmsys-r23-probe-preflight-result-20261004.md`
- `orcarouter-managed-rmsys-r23-early-burst-ownership-result-20261004.md`

R23 is **VALID_RM_OOM — FUNCTIONAL PASS / HOST-STABILITY FAIL**. The live managed restart completed successfully and remained healthy, but four later `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` events were recorded, so strict host stability fails.

The narrow trace itself was valid: it started `20.020147 s` after the replacement request (`19.103315 s` after container `StartedAt`) and ran for `53.415677 s`. The trace captured 668 successful `nv_alloc_pages` calls and 599 successful `nv_alloc_system_pages` calls. Selected UVM PMA, DMA, and PMM boundaries were silent. `uvm_mem_alloc` executed exactly twice, once on the dominant `VLLM::Worker` task and once on a `python3` task.

The key R23 size match is:

- 64 KiB/order-4-path RM logical activity: `75,077.375 MiB`;
- independently reconstructed largest 5 s residual increase: `75,083.652 MiB`;
- absolute difference: `6.277 MiB` (~`0.0084%`).

The same five-second interval loses about `77,019.473 MiB` from node0 Normal and `77,019.848 MiB` from global `nr_free_pages`. Its start is within `0.713 s` of the `Loading model from scratch...` milestone.

Repository implementation now includes:

- `scripts/benchmark/check-orcarouter-r23-ownership-probes.sh` — probe-only validation;
- `scripts/benchmark/run-orcarouter-managed-rmsys-r23-early-burst-ownership.sh` — managed R21-style conditioning plus a startup `+20 s` to approximately `+70 s` RM/UVM trace window;
- `scripts/benchmark/analyze-orcarouter-r23-ownership.py` — window-boundary-aware ownership/allocator analysis;
- `scripts/benchmark/analyze-orcarouter-r23-rm-uvm-overlap.py` — read-only post-hoc call nesting and burst-window RM/UVM correlation on the preserved R23 trace;
- `tests/test_orcarouter_r23_ownership_trace.py` and `tests/test_orcarouter_r23_rm_uvm_overlap.py` — focused regression contracts.

## Current next diagnostic direction

Do not start another live run yet, and do not return to broad watermark, compaction, drop-cache, swap, page-allocation, scheduler, or function-graph tracing.

First run the read-only R23 overlap analyzer against the preserved live evidence. It will determine whether the two `uvm_mem_alloc` intervals on the same PIDs actually contain most of the 64 KiB RM activity and how much 64 KiB RM activity falls inside the independently measured five-second burst.

If `uvm_mem_alloc` brackets most burst-window RM activity, treat it as the immediate upstream UVM wrapper and move only one boundary lower/inside that path if additional closure is required. If it brackets little of the burst, treat the selected UVM activity as adjacent/incidental and retain direct RM system memory as the primary ownership path.

No production reclaim/compaction or mmap promotion is accepted from R9–R23 evidence alone. PR #244 remains intentionally open.