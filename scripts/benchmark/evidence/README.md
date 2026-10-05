# Benchmark evidence index

This directory preserves canonical evidence for live DGX Spark runtime, profile-switch, host-stability, and allocator experiments. Historical per-run documents should remain immutable in meaning: later analysis may add links or later-closure notes, but should not rewrite what a run actually observed.

## Current host-stability / RM allocator closure

Start with the R9–R22 allocator closure, then the R23 ownership closure and R24 mitigation result:

- `orcarouter-managed-rmsys-r9-r22-allocator-closure-20261004.md`
- `orcarouter-managed-rmsys-r23-early-burst-ownership-result-20261004.md`
- `orcarouter-managed-rmsys-r23-ownership-closure-20261004.md`
- `orcarouter-hybrid-r24-kv16-rm-mitigation-result-20261005.md`

R21 and R22 first established a common early physical-page allocation burst of about 75 GiB over roughly five seconds, ultimately leaving an approximately 89.5–90.0 GiB physical-page residual not explained by the selected conventional Linux resident accounting. Nearly the entire free-page loss occurs in node0 Normal while managed capacity remains unchanged.

R23 directly aligns that common burst with NVIDIA RM system-memory activity. The valid narrow trace recorded `75,077.375 MiB` of full-window 64 KiB-path `nv_alloc_pages` logical activity while the independently reconstructed largest five-second unexplained residual increased by `75,083.652 MiB`.

The subsequent read-only overlap analysis closes the same-window correlation more precisely:

- five-second residual growth: `75,083.652 MiB`;
- 64 KiB/order-4-path `nv_alloc_pages` activity inside that same five-second window: `74,537.938 MiB`;
- RM activity / residual ratio: **`99.273191%`**;
- `uvm_mem_alloc` coverage of burst-window RM activity: **`0.000000%`**;
- `uvm_mem_alloc` coverage of `nv_alloc_system_pages` calls: **`0.000000%`**;
- selected UVM PMA/DMA/PMM allocators: silent.

Therefore the common early burst is closed to the **observed direct NVIDIA RM system-memory allocation path** (`nv_alloc_pages` / `nv_alloc_system_pages`) rather than any selected UVM allocation boundary. This remains a driver-level ownership endpoint, not proof that cumulative request bytes equal exact resident ownership and not yet identification of the original userspace CUDA/vLLM caller.

R24 then tested the H6 ModelOpt W4A16 Hybrid representation under R22-matched 16 GiB runtime controls. It did **not** mitigate the mechanism: the candidate largest five-second residual was `+77937.680 MiB` (`103.725991%` of R22), the same window contained `77405.938 MiB` of observed 64 KiB RM activity, and one later strict RM OOM remained. R24 is therefore **VALID_RM_OOM — FUNCTIONAL PASS / HOST-STABILITY FAIL — H6 NO RM MITIGATION**.

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
- `orcarouter-managed-rmsys-r23-ownership-closure-20261004.md`

R23 is **VALID_RM_OOM — FUNCTIONAL PASS / HOST-STABILITY FAIL**. The live managed restart completed successfully and remained healthy, but four later `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` events were recorded, so strict host stability fails.

The narrow trace itself was valid: it started `20.020147 s` after the replacement request (`19.103315 s` after container `StartedAt`) and ran for `53.415677 s`. It captured 668 successful `nv_alloc_pages` calls and 599 successful `nv_alloc_system_pages` calls. Selected UVM PMA, DMA, and PMM boundaries were silent. `uvm_mem_alloc` executed exactly twice.

The read-only post-hoc analyzer then showed both `uvm_mem_alloc` calls were sub-millisecond and contained **zero** observed `nv_alloc_pages` and **zero** `nv_alloc_system_pages` calls. Their coverage of both total and burst-window 64 KiB RM activity is `0.000000%`.

By contrast, the independently selected five-second physical residual window contains `74,537.938 MiB` of 64 KiB RM activity, equal to `99.273191%` of its `75,083.652 MiB` residual growth.

This closes the remaining selected-UVM ambiguity: `uvm_mem_alloc` is adjacent/incidental startup activity rather than an observed wrapper around the common RM burst.

Repository implementation includes:

- `scripts/benchmark/check-orcarouter-r23-ownership-probes.sh` — probe-only validation;
- `scripts/benchmark/run-orcarouter-managed-rmsys-r23-early-burst-ownership.sh` — managed narrow ownership trace;
- `scripts/benchmark/analyze-orcarouter-r23-ownership.py` — ownership/allocator analysis;
- `scripts/benchmark/analyze-orcarouter-r23-rm-uvm-overlap.py` — read-only same-PID nesting and burst-window RM/UVM correlation;
- `tests/test_orcarouter_r23_ownership_trace.py` and `tests/test_orcarouter_r23_rm_uvm_overlap.py` — focused regression contracts.

## R24 H6 16 GiB RM mitigation discriminator

- `orcarouter-hybrid-r24-kv16-rm-mitigation-plan-20261004.md`
- `orcarouter-hybrid-r24-kv16-rm-mitigation-result-20261005.md`

R24 is **VALID_RM_OOM — FUNCTIONAL PASS / HOST-STABILITY FAIL — H6 NO RM MITIGATION**. It moved from ownership discovery to mitigation discrimination and used R22 as the matched control.

The candidate was the generated H6 ModelOpt W4A16 Hybrid checkpoint with the managed-profile `24 GiB` KV default deliberately overridden to the R22-matched `16 GiB` value (`17179869184` bytes). This kept the v0.29 PLE-mmap/exact-QSA runtime line and key runtime controls matched while changing the H6 checkpoint/loader representation rather than also changing KV allocation.

The run was valid: candidate start, collector, trace, trace report, analyzer, readiness, and candidate identity all passed. The candidate reached API READY with `functional_class=PASS`, but one strict RM OOM produced `host_stability_class=FAIL`.

The mitigation discriminator is decisive:

- R22 largest 5 s residual baseline: `75138.043 MiB`;
- H6 largest 5 s residual: `77937.680 MiB`;
- candidate/R22 ratio: `103.725991%`;
- operational band: `BURST_UNCHANGED`;
- 64 KiB RM activity inside the same H6 burst: `77405.938 MiB` across `526` calls;
- node0 Normal free delta over the burst: `-78832.938 MiB`;
- strict RM OOM count: `1`;
- discriminator: `H6_NO_RM_MITIGATION_HOST_FAIL`.

All observed H6 64 KiB RM activity was inside the independently selected five-second burst, and the narrow trace fully covered that window. H6 therefore reproduces the same already-closed direct RM system-memory mechanism rather than avoiding it.

Repository implementation includes:

- `scripts/benchmark/run-orcarouter-hybrid-r24-kv16-rm-mitigation.sh` — `--preflight` plus live H6/R22-matched discriminator;
- `scripts/benchmark/analyze-orcarouter-hybrid-r24-rm-mitigation.py` — residual/RM/high-order comparison against R22;
- `tests/test_orcarouter_hybrid_r24_rm_mitigation.py` — fixed-control, identity, trace-scope, restoration, and classification contracts.

Post-run cleanup restarted `qwen38-flash-next.service` and the unit reported `active`, but the immediate `/health` call disconnected before READY was confirmed. This does not invalidate the completed H6 measurement; restored managed API readiness remains a follow-up confirmation item.

## Current next engineering direction

Do not repeat H6 merely to seek a different outcome, and do not return to broad watermark, compaction, drop-cache, swap, page-allocation, scheduler, function-graph, UVM, or all-driver tracing.

R24 rejects the H6 ModelOpt W4A16 checkpoint/loader representation as a host-stability mitigation under R22-matched controls. The next discriminator must target a variable with an explicit mechanism for changing the **source or shape of the approximately 75 GiB direct RM 64 KiB system-memory demand**, rather than only changing checkpoint labels or quantization metadata.

Before the next live experiment, confirm that the restored managed runtime is API READY and preserve that confirmation. Conditioning and mmap remain measurement controls/discriminators, not accepted production mitigations.

PR #244 remains intentionally open and must not be merged before mitigation/Hybrid closure and explicit merge timing.