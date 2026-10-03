# OrcaRouter managed RM-sysmem R12 — one-shot pre-compaction — 2026-10-03

## Classification

- Experiment validity: **VALID**
- Functional classification: **PASS**
- Host-stability classification: **FAIL** under the current strict policy
- Mitigation result: **FAIL** (`ORCA_R12_RESULT=VALID_RM_OOM`)
- Managed restart: valid (`run_valid=1`)
- RM events: **2 recoverable `NV_ERR_NO_MEMORY (0x51)`**
- Final runtime: active/running, API READY, Docker OOMKilled=false
- VM-tunable persistence: none; the experiment used only one write to `vm.compact_memory` before the otherwise unchanged R11 restart/trace.

## Purpose

R11 localized the RM fallback to node-0 Normal-zone Unmovable order-4 demand consuming/stealing from the Movable high-order reservoir. R12 tested the smallest Linux-side mitigation: compact all zones once immediately before the managed restart, without changing persistent VM policy.

## Pre-compaction state

Before the one-shot compaction, the allocator was already in a comparatively healthy high-order state:

- DMA order-4 blocks: 32
- DMA order-5+ blocks: 67
- DMA order-4+ capacity: 480.250 MiB
- Normal order-4 blocks: 14,690
- Normal order-5+ blocks: 12,878
- Normal order-4+ capacity: **2,845.875 MiB**

After writing `1` to `vm.compact_memory`:

- DMA order-4 blocks: 10
- DMA order-5+ blocks: 59
- DMA order-4+ capacity: 483.625 MiB
- Normal order-4 blocks: 14,679
- Normal order-5+ blocks: 12,872
- Normal order-4+ capacity: **2,844.438 MiB**

The Normal-zone high-order pool therefore changed by only -1.437 MiB. The one-shot operation did not create a materially larger starting reservoir because the starting reservoir was already large.

## Runtime outcome

The managed startup progressed normally and ultimately committed/attested as healthy, but two RM sysmem failures occurred during startup.

### Failure 1

The first failed logical allocation was 3.125 GiB:

- `page_count=819200`
- requested page size: 64 KiB
- derived Linux allocation order: 4
- expected order-4 chunks: 51,200
- captured policy: `contiguous=0`, `cache_type=0`, `zeroed=1`, `unencrypted=0`, `node_id=-1`
- return: `0x51`

Nested sysmem accounting:

- order-4 allocations: 40,450
- order-4 frees: 40,449
- identical PFNs allocated then freed: 40,449
- candidate failed chunk: 40,451
- rollback size: **2,528.0625 MiB**
- compaction attempts: 1,991
- direct reclaim attempts: 985
- extfrag events: 1,596
- extfrag ownership changes: 1,151

The immediately following same-thread request preserved the logical size and policy, switched to 4 KiB/order 0, and succeeded.

### Failure 2

The second failed logical allocation was approximately 1.185547 GiB:

- `page_count=310784`
- requested page size: 64 KiB
- order: 4
- expected chunks: 19,424
- order-4 allocations: 13,943
- order-4 frees: 13,942
- candidate failed chunk: 13,944
- compaction attempts: 22
- direct reclaim attempts: 21
- extfrag events: 443

The same logical request then succeeded immediately at 4 KiB/order 0.

## VM policy during R12

The relevant tunables remained at their pre-existing values:

- `compaction_proactiveness=20`
- `compact_unevictable_allowed=1`
- `extfrag_threshold=500`
- `min_free_kbytes=45155`
- `watermark_boost_factor=15000`
- `watermark_scale_factor=10`

R12 intentionally did not persistently change any of them.

## Interpretation

R12 rejects one-shot startup pre-compaction as a sufficient mitigation.

The key observation is that the experiment began with approximately 2.85 GiB of Normal-zone order-4+ free capacity, and the one-shot compaction barely changed it. Nevertheless, during the long model startup the Unmovable high-order demand again consumed/fragmented the high-order reservoir until a 3.125 GiB request failed after already acquiring and then rolling back about 2.53 GiB of order-4 chunks.

Therefore the failure is not explained by a bad allocator state only at service-start time. The relevant state evolves dynamically during startup. A useful mitigation must keep the high-order reservoir healthier throughout the load, not merely compact it once before the load begins.

The first failed request also shows why a pre-start high-order-capacity number cannot be treated as a simple acceptance threshold. The request required 3.125 GiB logically, while the kernel dynamically compacted, reclaimed, split fallback buddies, and accumulated more than 2.5 GiB of order-4 chunks before eventual failure. The allocator path evolves throughout the request.

## Next mitigation step

R13 changes exactly one runtime VM policy and restores it afterward: temporary `vm.compaction_proactiveness=80` for the full startup interval, with all other VM tunables unchanged and the same R11 trace/collector contract. The helper refuses to run unless the original value is the measured baseline 20 and restores the original value on normal, error, INT, and TERM paths.

If R13 still reproduces RM OOM, the next isolated variable should be free-page reserve/reclaim policy (most directly `watermark_scale_factor`) rather than another pre-start compaction or another KV reduction.
