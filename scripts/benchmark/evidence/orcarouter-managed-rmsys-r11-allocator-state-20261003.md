# OrcaRouter managed RM-sysmem R11 — allocator-state correlation — 2026-10-03

## Classification

- Experiment validity: **VALID**
- Functional classification: **PASS**
- Host-stability classification: **FAIL** under the current strict policy
- RM events: **1 recoverable `NV_ERR_NO_MEMORY (0x51)`**
- R11 state collector: **VALID** (`collector_rc=0`)
- RM-triggered full snapshots: **1**
- Fast allocator-state samples: **904** at 1 s cadence
- Slow allocator-state samples: **181** at 5 s cadence
- Final runtime: **active/running, API READY, Docker OOMKilled=false**

R11 preserved the proven R10b RM boundary and added allocator-state sampling around the same managed OrcaRouter restart. The run reproduced one 64 KiB/order-4 RM sysmem failure and captured the Linux allocator state before and after that failure.

## RM allocation boundary

The failed logical request was 1.193359 GiB (`page_count=312832`) with:

- requested page size: 64 KiB;
- Linux allocation order: 4;
- expected chunks: 19,552;
- `contiguous=0`;
- `cache_type=0`;
- `zeroed=1`;
- `unencrypted=0`;
- `node_id=-1`;
- return: `0x51`.

The nested Linux sysmem interval captured:

- 17,984 order-4 page allocations;
- 17,983 order-4 frees;
- 17,983 identical PFNs allocated then freed;
- candidate failed chunk index 17,985;
- 1,323 order-4 compaction attempts;
- 694 order-4 direct reclaim attempts;
- 671 extfrag events.

The immediately following same-thread request preserved the same logical size and captured policy but switched to 4 KiB/order 0 and succeeded.

## Failure-time state localization

The nearest fast sample before the RM signal was 304.156 ms earlier. At that point:

- system `MemFree`: 6,935,052 KiB;
- system `MemAvailable`: 21,037,540 KiB;
- `SwapFree`: 45,643,732 KiB;
- DMA zone order-4 blocks: 2;
- DMA zone order-5+ blocks: 146;
- DMA zone order-4+ free capacity: 504.750 MiB;
- **Normal zone order-4 blocks: 1**;
- **Normal zone order-5+ blocks: 3**;
- **Normal zone order-4+ free capacity: only 1.688 MiB**.

Therefore the RM fallback was not caused by exhaustion of total free memory or swap. The allocator had substantial base-page memory available while the Normal-zone high-order buddy supply was almost empty.

## Immediate post-failure rollback signature

The nearest fast sample after the RM signal was 695.877 ms later. By then:

- DMA-zone high-order state was unchanged;
- Normal-zone order-4 blocks had risen from 1 to 1,610;
- Normal-zone order-5+ blocks had risen from 3 to 2,456;
- Normal-zone order-4+ free capacity had risen from 1.688 MiB to 1,121.375 MiB.

The traced failed sysmem interval rolled back 17,983 64 KiB chunks. That rollback represents 1,123.9375 MiB. The observed Normal-zone high-order increase to 1,121.375 MiB differs by only 2.5625 MiB (about 0.23%).

This is strong state-level evidence that the failed RM order-4 attempt had accumulated its high-order pages predominantly from the Normal-zone buddy allocator and that its rollback repopulated that same high-order pool. DMA-zone high-order capacity did not show the corresponding change.

The fast post sample occurred while the successful order-0 retry was already running, so it should be interpreted as rollback/recovery state rather than a pristine post-transaction state.

## Compaction and allocation-stall pressure

Across the approximately one-second fast-sample interval spanning the failure, vmstat deltas included:

- `allocstall_normal`: +990;
- `compact_stall`: +1,907;
- `compact_success`: +916;
- `compact_fail`: +991;
- `compact_free_scanned`: +7,511,443;
- `compact_migrate_scanned`: +2,395,696;
- `compact_daemon_free_scanned`: +490,271;
- `compact_daemon_migrate_scanned`: +1,929,901;
- `pgalloc_normal`: +563,979.

Memory PSI was also elevated (`some avg10=9.33`, `full avg10=9.33`) on both sides of the event.

This is consistent with severe transient high-order allocation pressure: the kernel repeatedly compacted/scanned/reclaimed while attempting to supply order-4 pages even though base-page memory was still available.

## Watermark assessment

The RM-triggered full snapshot was taken 1.033 s after the kernel RM timestamp. It is therefore supporting post-event evidence, not an instantaneous failure-state snapshot.

At that snapshot, Normal zone showed:

- free pages: 994,423;
- low watermark: 154,881 pages;
- free minus low: 839,542 pages;
- managed pages: 31,725,420.

The nearest slow sample after the event likewise showed Normal-zone free pages 1,316,982 and free-minus-low 1,162,101 pages.

The nearest slow sample before the failure was 4.303 s earlier and had much more free memory. Because the watermark values changed during this highly active startup interval, the slow snapshots should not be treated as exact failure-time watermarks. However, neither the post-event zone state nor the system-wide fast samples support ordinary low-watermark or total-memory exhaustion as the primary failure condition.

## Migratetype and pageblock transition

The 5 s pagetype snapshots show a major transition around the failure interval.

Normal zone before (`-4.303 s`):

- Movable order-4 blocks: 8,629;
- Movable order-4+ block count: 11,081;
- Unmovable order-4 blocks: 1;
- pageblocks: Unmovable 49,471 / Movable 14,910 / Reclaimable 130 / HighAtomic 1.

Normal zone after (`+0.696 s`):

- Movable order-4 blocks: 5;
- Movable order-4+ block count: 15;
- Unmovable order-4 blocks: 1,605;
- pageblocks: Unmovable 54,035 / Movable 10,371 / Reclaimable 106 / HighAtomic 0.

The RM-triggered snapshot at +1.033 s showed nearly all remaining Normal-zone high-order free blocks classified under Unmovable, with only one Movable order-4+ block.

This establishes a strong association between the startup interval, collapse of the Movable high-order pool, heavy pageblock ownership/migratetype change, and the RM order-4 fallback.

## Exact zone / migratetype closure

The preserved raw R11 trace was post-processed against the zone PFN boundaries captured in the RM-triggered zone snapshot.

The failed nested `nv_alloc_system_pages` interval contained 36,638 matching trace events and directly mapped the RM high-order allocation path as follows:

- order-4 allocation events: 17,984;
- order-4 free events: 17,983;
- identical PFNs allocated then freed: 17,983;
- rollback size: 1,123.9375 MiB;
- allocation-zone coverage: 17,983 / 17,984 events mapped to a captured zone boundary;
- all 17,983 mapped allocation PFNs: **node 0 Normal zone**;
- all 17,983 free/rollback PFNs: **node 0 Normal zone**;
- the one unmapped allocation event was not part of the 17,983-PFN rollback set;
- all 17,984 `mm_page_alloc` events carried trace migratetype **0 / Unmovable**.

The extfrag tracepoint also closes the fallback source:

- all 671 extfrag events requested **Unmovable** and fell back to **Movable**;
- 643 / 671 events (95.8%) reported `change_ownership=1`;
- fallback buddy orders were 8 (231), 9 (145), 7 (128), 6 (88), 5 (61), and 4 (18).

Therefore the allocator path is directly observed rather than inferred: NVIDIA RM's 64 KiB requests enter the Linux allocator as **Normal-zone Unmovable order-4 demand**. When same-type high-order supply is unavailable, the allocator repeatedly falls back to larger **Movable** buddy blocks and, in most observed extfrag events, changes ownership while satisfying the Unmovable allocation. During this startup interval that process coincides with collapse of the Movable high-order pool and conversion of thousands of Normal-zone pageblocks toward Unmovable ownership.

The `mm_page_free` tracepoint used by this capture does not expose a migratetype field, so the free-side migratetype is correctly recorded as unavailable rather than inferred. Zone identity for the rollback PFNs is nevertheless directly mapped from the PFNs themselves.

## Root-cause status after R11

R11 closes the previously unresolved Linux allocator dimensions for this failure.

Supported conclusions:

1. **Not total-memory exhaustion.** Tens of GiB of available/swap memory remained.
2. **Not a fixed logical request-size threshold.** Prior traces reproduced the same mechanism from 40 MiB to approximately 16 GiB.
3. **Not an order-0 allocation failure.** The identical logical request succeeded immediately when RM retried with 4 KiB/order 0.
4. **The failing high-order path is node-0 Normal-zone Unmovable.** 17,983 rollback PFNs map directly to Normal, and every captured order-4 allocation event carried Unmovable migratetype.
5. **Movable is the directly observed fallback reservoir.** Every extfrag event was Unmovable -> Movable, with ownership change reported in 643 / 671 cases.
6. **The Normal-zone high-order buddy pool was effectively exhausted at the failure boundary.** The nearest pre-failure fast sample had only 1.688 MiB of Normal-zone order-4+ free capacity despite substantial base-page memory.
7. **Rollback repopulated the same Normal-zone high-order pool.** 1,123.9375 MiB of traced rollback closely matches the 1,121.375 MiB post-failure Normal-zone high-order capacity.
8. **Compaction/reclaim/fragmentation pressure is directly present.** The interval contains heavy compaction, direct reclaim, allocator stalls, and Unmovable -> Movable extfrag fallback.

Current lower-level mechanism:

> During some OrcaRouter startup states, NVIDIA RM issues non-contiguous 64 KiB sysmem allocations that reach Linux as Normal-zone Unmovable order-4 requests. Same-type high-order supply becomes insufficient, so the allocator repeatedly steals/splits larger Movable buddy blocks, usually changing pageblock ownership. The Movable high-order reservoir collapses while substantial base-page memory remains available. Eventually RM cannot complete the logical request at order 4, returns `NV_ERR_NO_MEMORY`, rolls back the accumulated Normal-zone order-4 pages, and immediately retries the same logical allocation at 4 KiB/order 0, which succeeds.

The proximate failure mechanism is therefore closed through the NVIDIA RM boundary, Linux zone, migratetype, buddy fallback source, ownership-change behavior, rollback, and successful lower-order retry. The remaining work is mitigation selection and validation rather than another reproduction run merely to identify the mechanism.

## Follow-up tooling

The repository includes `scripts/benchmark/analyze-orcarouter-r11-zone-migratetype.py`, a read-only post-processor for the preserved R11 trace. It maps the failed interval's order-4 allocation/free PFNs to zone boundaries from the RM event snapshot and reports trace migratetype, extfrag fallback migratetype, ownership-change counts, and fallback orders. This follow-up analysis does not restart or mutate the runtime.
