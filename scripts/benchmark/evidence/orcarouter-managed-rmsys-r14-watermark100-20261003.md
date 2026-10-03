# OrcaRouter managed RM-sysmem R14 — watermark_scale_factor=100 — 2026-10-03

## Classification

- Experiment validity: **VALID**
- Functional classification: **PASS**
- Host-stability classification: **PASS** for this measured restart under the current strict policy
- Mitigation result: **CANDIDATE PASS** (`ORCA_R14_RESULT=VALID_CLEAN`)
- Managed restart: valid (`run_valid=1`)
- RM events: **0**
- Final runtime: active/running, API READY, Docker OOMKilled=false
- Temporary VM policy: `vm.watermark_scale_factor=100` for the full startup interval
- Original policy restored: `vm.watermark_scale_factor=10`
- `vm.compaction_proactiveness` remained at baseline 20

## Purpose

R12 showed that one-shot pre-start compaction is insufficient. R13 showed that raising only `vm.compaction_proactiveness` from 20 to 80 for the full startup interval can still leave the Normal-zone Unmovable order-4 path unable to complete a logical allocation. R14 therefore isolated the free-page reserve/reclaim margin controlled by `vm.watermark_scale_factor` while returning compaction proactiveness to its baseline value.

R14 changed exactly one VM policy for the startup interval:

- `watermark_scale_factor`: 10 -> 100

The measured baseline was restored after the run.

## Runtime outcome

The managed replacement runtime completed successfully, committed/attested as healthy, and the allocator trace contained no RM sysmem OOM event.

Measured result:

- `trace_rc=0`
- `managed_rc=0`
- `restart_observed=1`
- `run_valid=1`
- `analysis_rc=0`
- container replaced successfully
- `RM_SYS_ANALYSIS=NO_RM_OOM_IN_CAPTURE_WINDOW`
- final service: active/running
- final container: running, exit 0, OOMKilled=false
- API health: ready
- expected OrcaRouter model present

R11 nested collection was also valid:

- `r10b_rc=0`
- `collector_rc=0`
- `run_valid=1`
- `rm_oom_count=0`
- `event_snapshot_count=0`
- fast samples: 964
- slow samples: 193

## Policy restoration

R14 recorded:

- original `watermark_scale_factor=10`
- target `watermark_scale_factor=100`
- restored `watermark_scale_factor=10`
- `compaction_proactiveness=20`

The host values after the experiment were explicitly verified as:

- `watermark_scale_factor=10`
- `compaction_proactiveness=20`

No temporary KV override was present.

## Interpretation

R14 is the first Linux-side mitigation experiment in this sequence to satisfy the strict measured-run criterion of zero RM fallback while still reaching READY.

This result is directionally consistent with the Linux VM interpretation already supported by R11: the workload creates a burst of Normal-zone Unmovable order-4 demand, and the baseline free-page/reclaim margin may be too small to preserve a sufficiently healthy high-order reservoir through the long startup interval. Raising `watermark_scale_factor` causes kswapd to maintain a larger distance between watermarks and therefore a larger free-page margin for burst allocations.

However, the repository already contains both clean and failing restarts under otherwise identical OrcaRouter settings. Therefore one clean R14 run does **not** establish causality or justify a persistent production sysctl change by itself.

The correct classification is therefore **candidate mitigation pass**, not final mitigation acceptance.

## Next validation step

Before promoting `watermark_scale_factor=100` into any persistent startup or host policy, compare the existing R11/R12/R13/R14 allocator-state samples and then perform a controlled paired validation that includes both baseline 10 and candidate 100 under the same non-reboot campaign.

The comparison should focus on:

- Normal-zone `free - low` and `free - high` margins over startup;
- `allocstall_normal` and direct-reclaim deltas;
- kswapd wake/sleep-related vmstat counters where available;
- Normal-zone order-4+ buddy capacity through the load;
- pageblock/migratetype mixing and extfrag behavior;
- RM fallback count as the strict acceptance outcome.

Until that validation is complete, the host default remains `watermark_scale_factor=10` and no persistent VM policy change is approved.
