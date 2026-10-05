# OrcaRouter R18 post-stop compaction — 2026-10-04

## Purpose

R18 tests whether one-shot compaction becomes effective when it is moved across the teardown boundary.

R12 ran `vm.compact_memory` while the predecessor runtime was still resident and later failed with recoverable RM OOM events. R18 instead requires an aged predecessor, fully stops it, captures allocator state, compacts once after teardown, then starts the same immutable OrcaRouter release.

The host VM policy remains at its defaults outside the one-shot compaction action:

- `vm.watermark_scale_factor=10`
- `vm.compaction_proactiveness=20`
- OrcaRouter managed KV default: 16 GiB
- immutable release: `ff67bab3c94d6992f61b9535836df97f03b9c022`

## Validity

The measured run was valid:

- `run_valid=1`
- `managed_rc=0`
- `collector_rc=0`
- `restart_observed=1`
- `api_ready=1`
- predecessor age: `19169.687 s` (~319.495 min / ~5.325 h)
- minimum age guard: `2700 s`
- `rm_oom_count=0`
- `event_snapshot_count=0`
- result: `ORCA_R18_RESULT=VALID_CLEAN`

The final service was active and host VM defaults remained `watermark_scale_factor=10`, `compaction_proactiveness=20`.

Under the strict current acceptance policy this run is:

- FUNCTIONAL PASS
- HOST-STABILITY PASS

## Post-stop allocator effect

R18 captured Normal-zone buddy state after the aged predecessor was fully stopped and immediately before/after the one-shot `compact_memory` write.

Normal-zone buddy counts imply:

- order-4+ free before compaction: ~110184.313 MiB
- order-4+ free after compaction: ~112597.438 MiB
- delta: +2413.125 MiB

The order distribution moved upward:

- exact order-4 free: ~4013.688 -> ~3221.062 MiB
- order-5+ free: ~106170.625 -> ~109376.375 MiB
- order-5+ delta: +3205.750 MiB

Thus the one-shot compaction visibly coalesced free memory into larger buddy blocks after teardown. Although exact order-4 count decreased, the larger free buddies form a reservoir that can be split to satisfy order-4 demand.

## Interpretation

R18 is the first measured Linux-side mitigation run that directly targets the newly observed predecessor-age boundary and remains strict-clean despite replacing a long-lived predecessor.

The result is materially stronger than the earlier R12/R13/R14 experiments because the predecessor was ~319.5 minutes old, well inside the age range that had previously correlated with RM OOM:

- 50.722 min -> RM OOM x1
- 125.120 min -> RM OOM x3
- 298.448 min -> RM OOM x4

R18:

- 319.495 min predecessor
- full stop
- one-shot post-stop compaction
- RM OOM x0

However R18 alone did **not** isolate whether the causal mitigation was:

1. the explicit post-stop compaction, or
2. the full stop / quiescent teardown boundary itself.

That ambiguity was tested directly by R19.

## R19 stop-only control result

R19 used the same aged-predecessor guard and the same immutable OrcaRouter release, but deliberately removed the compaction treatment:

> aged predecessor -> full stop -> post-stop allocator snapshot -> no `compact_memory` write -> immediate start

R19 was a valid replacement startup but emitted five recoverable RM OOM events:

- predecessor age: ~53.461 min
- `run_valid=1`
- `restart_observed=1`
- `api_ready=1`
- `rm_oom_count=5`
- result: `ORCA_R19_RESULT=VALID_RM_OOM`

This directly rejects the simpler explanation that R18 was clean merely because it inserted a full-stop/quiescent boundary. Full teardown by itself is not sufficient for an aged predecessor.

The R18/R19 outcomes therefore materially strengthen post-stop compaction as the leading mitigation candidate:

- R18 treatment: aged predecessor -> stop -> compact -> start -> clean
- R19 control: aged predecessor -> stop -> no compact -> start -> RM OOM x5

The two runs did not begin from identical post-stop allocator states, so treatment necessity/sufficiency is not yet proven for every aged state. R19 post-stop Normal order-4+ free was ~105494.875 MiB, whereas R18 pre-compaction was ~110184.313 MiB.

## R20 replication outcome

R20 repeated the R18 treatment on another aged predecessor but did not complete the validity boundary. Post-stop compaction again visibly coalesced Normal-zone free buddies, and no RM OOM was observed before termination, but the managed memory-protection gate intentionally stopped the candidate before API readiness.

Therefore the sequence is not a completed treatment/control/treatment proof:

- R18 treatment: VALID CLEAN
- R19 control: VALID RM OOM x5
- R20 treatment replication: INVALID protected stop, RM OOM x0 observed before stop

The R20 result does not refute the RM-side compaction hypothesis, but it establishes a separate startup memory-margin boundary that must not be conflated with recoverable RM/sysmem fallback.

The managed OrcaRouter service was subsequently recovered normally and returned to active/healthy state. Before another treatment restart, the existing R18 and R20 post-stop pre/post-compaction snapshots should be compared directly for buddy distribution, migratetype composition, memory totals, Normal-zone watermarks, and compaction vmstat deltas. The read-only comparator is `scripts/benchmark/compare-orcarouter-r18-r20-poststop-state.py`.

## Current conclusion

The proximate failure mechanism remains unchanged: NVIDIA RM Linux-sysmem 64 KiB/order-4 Unmovable demand can exhaust usable high-order supply, roll back, return `NV_ERR_NO_MEMORY`, then succeed on immediate order-0 retry.

R18 plus R19 still provide the strongest Linux-side mitigation evidence so far:

> Full teardown alone does not remove the aged-predecessor failure boundary. A one-shot compaction performed after teardown and before replacement startup is the leading mitigation candidate: the R18 treatment was strict-clean, while the matched R19 stop-only control failed with five recoverable RM OOM events.

R20 prevents promotion to production integration because treatment repeatability is not yet established. Analyze the already-captured R18/R20 allocator state before deciding the next controlled restart.
