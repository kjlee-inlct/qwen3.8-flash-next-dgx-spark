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

## Exact zone and migratetype closure

Read-only post-processing of the preserved raw R11 trace closed the previously unresolved zone/migratetype dimension:

- failed interval: `VLLM::Worker`, PID 4,075,858;
- order-4 allocations: 17,984;
- order-4 frees: 17,983;
- rollback PFNs: 17,983;
- all 17,983 rollback PFNs map to **node-0 Normal zone**;
- allocation-zone mapping coverage: 17,983 / 17,984; the one unmapped allocation was not part of the rollback set;
- all 17,984 `mm_page_alloc` events report migratetype `0 / Unmovable`;
- all 671 extfrag events report `Unmovable -> Movable` fallback;
- 643 / 671 extfrag events (95.8%) report `change_ownership=1`;
- fallback buddy orders span 4 through 9 and are dominated by orders 8, 9, and 7.

This directly closes the allocation path observed during the failure: NVIDIA RM generates Normal-zone Unmovable order-4 demand. When compatible high-order supply is insufficient, Linux repeatedly falls back to larger Movable buddy blocks, splits them, and usually changes pageblock ownership. The Movable high-order reservoir collapses during startup. The logical order-4 request eventually cannot obtain its next chunk, RM rolls back the accumulated Normal-zone high-order pages, and the same logical request then succeeds at order 0.

## Root-cause status after R11

Supported conclusions:

1. **Not total-memory exhaustion.** Tens of GiB of available/swap memory remained.
2. **Not a fixed logical request-size threshold.** Prior traces reproduced the same mechanism from 40 MiB to approximately 16 GiB.
3. **Not an order-0 allocator failure.** The same request succeeded immediately at order 0.
4. **Directly localized to Normal-zone Unmovable high-order demand and Movable fallback.** Raw PFN and migratetype trace closes both dimensions.
5. **Compaction/reclaim was actively struggling to maintain high-order supply.** Large allocstall, compaction, reclaim, and extfrag activity occurred around the failure.
6. **Pageblock stealing/ownership transition is part of the observed path.** 95.8% of captured Unmovable->Movable extfrag fallback events reported ownership change.

Current lower-level model:

> During some OrcaRouter startup states, NVIDIA RM creates sustained Normal-zone Unmovable order-4 demand. Same-type high-order supply becomes insufficient, so Linux repeatedly steals and splits larger Movable buddy blocks, usually changing ownership. The Movable high-order reservoir collapses despite substantial base-page memory remaining. RM's logical high-order request eventually cannot obtain its next order-4 chunk, rolls back the accumulated Normal-zone high-order pages, then retries the same logical request at 4 KiB/order 0 and succeeds.

## Mitigation follow-up

R12 tested a one-shot write to `vm.compact_memory` immediately before startup. It began with approximately 2.85 GiB of Normal-zone order-4+ free capacity, and the one-shot compaction barely changed that starting capacity. Nevertheless two RM order-4 failures reappeared later during the long model startup, including a 3.125 GiB request that accumulated and rolled back about 2.53 GiB of order-4 chunks before falling back successfully to order 0.

Therefore one-shot pre-start compaction is not a sufficient mitigation. The relevant allocator state evolves during startup; mitigation must preserve high-order supply during the load. R13 is the next isolated A/B: temporarily raise `vm.compaction_proactiveness` from 20 to 80 for the full startup interval, restore it afterward on every exit path, and keep every other VM tunable unchanged.

Canonical R12 evidence: `scripts/benchmark/evidence/orcarouter-managed-rmsys-r12-precompact-20261003.md`.
