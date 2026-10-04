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

However R18 does **not** isolate whether the causal mitigation is:

1. the explicit post-stop compaction, or
2. the full stop / quiescent teardown boundary itself.

The managed restart path normally stops the service and immediately starts the replacement. R18 inserts allocator observation plus a one-shot compaction between those phases. Therefore the next required control is an otherwise matched aged-predecessor run that performs:

> full stop -> no `compact_memory` write -> immediate start

If that control fails while R18 remains clean, post-stop compaction gains direct causal support. If the control is also clean, the teardown/quiescence boundary itself becomes the stronger mitigation candidate.

## Current conclusion

The proximate failure mechanism remains unchanged: NVIDIA RM Linux-sysmem 64 KiB/order-4 Unmovable demand can exhaust usable high-order supply, roll back, return `NV_ERR_NO_MEMORY`, then succeed on immediate order-0 retry.

R18 adds a new mitigation result:

> A one-shot compaction performed only after a ~5.3-hour OrcaRouter predecessor was fully torn down produced a valid strict-clean replacement startup with no recoverable RM OOM, while visibly coalescing Normal-zone free buddy capacity upward.

This is a strong mitigation candidate, not yet proof that the compaction write itself is necessary. R19 must isolate stop-only control behavior before production adoption.
