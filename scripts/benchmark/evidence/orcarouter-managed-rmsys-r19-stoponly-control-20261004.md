# OrcaRouter R19 aged-predecessor stop-only control — 2026-10-04

## Purpose

R19 is the matched stop-only control for the R18 post-stop compaction candidate.

R18 replaced an aged OrcaRouter predecessor by fully stopping it, running one explicit `vm.compact_memory` pass after teardown, then starting the same immutable managed release. R18 was strict-clean.

R19 keeps the same aged-predecessor guard and the same managed release but removes the compaction treatment entirely:

> aged predecessor >=45 min -> full stop -> post-stop allocator snapshot -> no `compact_memory` write and no VM tuning -> start same immutable OrcaRouter release

Host policy remained:

- `vm.watermark_scale_factor=10`
- `vm.compaction_proactiveness=20`
- OrcaRouter managed KV default: 16 GiB
- immutable release: `ff67bab3c94d6992f61b9535836df97f03b9c022`

## Validity

The measured control run was valid:

- `run_valid=1`
- `managed_rc=0`
- `collector_rc=0`
- `restart_observed=1`
- `api_ready=1`
- predecessor age: `3207.680 s` (~53.461 min)
- minimum age guard: `2700 s`
- `rm_oom_count=5`
- `event_snapshot_count=4`
- result: `ORCA_R19_RESULT=VALID_RM_OOM`

The replacement runtime still reached the committed healthy state, the final service was active, and host VM defaults remained `watermark_scale_factor=10`, `compaction_proactiveness=20`.

Under the strict current acceptance policy this run is:

- FUNCTIONAL PASS
- HOST-STABILITY FAIL

## RM failure window

Five `_memdescAllocInternal` / `NV_ERR_NO_MEMORY (0x51)` kernel events were observed during the valid startup window.

The events occurred at approximately:

- 12:05:29.679 KST
- 12:07:20.635 KST
- 12:07:22.467 KST
- 12:07:22.928 KST
- 12:07:23.206 KST

The allocator-state collector captured four RM-OOM event snapshots; the raw kernel window contains all five events. The count mismatch does not invalidate the run because startup validity, real container replacement, API readiness, and the kernel RM failures are independently established.

## Post-stop allocator state

R19 captured Normal-zone buddy state after the aged predecessor was fully stopped and immediately before the replacement startup.

The post-stop Normal-zone buddy counts imply:

- order-4+ free: ~105494.875 MiB
- exact order-4 free: ~4334.125 MiB
- order-5+ free: ~101160.750 MiB

No `compact_memory` write or persistent VM tuning occurred between this snapshot and replacement startup.

The startup then emitted five recoverable RM OOM events.

## R18 / R19 interpretation

R19 directly answers one part of the R18 ambiguity:

> A full stop / quiescent teardown boundary by itself is not sufficient to prevent the aged-predecessor RM failure.

The matched high-level outcomes are now:

- R18: predecessor ~319.5 min -> full stop -> one-shot post-stop compaction -> clean
- R19: predecessor ~53.5 min -> full stop -> no compaction -> RM OOM x5

This materially strengthens the post-stop compaction hypothesis and rejects the simpler explanation that R18 was clean merely because the predecessor was fully stopped before restart.

However, R18 and R19 were separate runs and did not begin from identical post-stop allocator states. In particular:

- R18 pre-compaction Normal order-4+ free: ~110184.313 MiB
- R18 post-compaction Normal order-4+ free: ~112597.438 MiB
- R19 stop-only Normal order-4+ free: ~105494.875 MiB

R18 also showed explicit upward coalescing during compaction:

- exact order-4 free: ~4013.688 -> ~3221.062 MiB
- order-5+ free: ~106170.625 -> ~109376.375 MiB
- order-5+ delta: +3205.750 MiB

Therefore R19 provides strong causal support for the placement of compaction after teardown, but the current evidence does not yet prove that the `compact_memory` write alone is sufficient across arbitrary aged allocator states. Treatment repeatability should be established on another aged predecessor before production adoption.

## Current conclusion

The proximate RM/Linux mechanism remains unchanged: NVIDIA RM non-contiguous 64 KiB/order-4 Unmovable demand can exhaust usable high-order supply, roll back, return `NV_ERR_NO_MEMORY`, then recover on lower-order allocation.

R18/R19 now establish the strongest Linux-side mitigation result so far:

> Full teardown alone does not remove the recoverable RM OOM boundary for an aged OrcaRouter runtime. An explicit one-shot compaction placed after teardown and before replacement startup is the leading mitigation candidate, because the corresponding R18 treatment was strict-clean while the R19 stop-only control failed under the same managed profile/release and default VM policy.

The next efficient validation is a second aged-predecessor post-stop-compaction treatment run using the already-proven R18 runner with a distinct evidence directory. If that replication is clean, the treatment/control/treatment sequence will provide substantially stronger evidence for production integration.
