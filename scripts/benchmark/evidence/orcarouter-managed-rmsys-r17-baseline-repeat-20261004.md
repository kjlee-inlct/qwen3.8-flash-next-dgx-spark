# OrcaRouter R17 same-policy baseline repeat — 2026-10-04

## Purpose

R17 removes the `watermark_scale_factor` treatment variable entirely and runs two adjacent managed OrcaRouter restarts under the same measured host policy:

- `vm.watermark_scale_factor=10`
- `vm.compaction_proactiveness=20`
- repository-managed OrcaRouter 16 GiB KV default
- immutable release `ff67bab3c94d6992f61b9535836df97f03b9c022`

The purpose is to isolate restart ordinal / allocator-state carry-over after R15 and R16 showed opposite watermark assignments but the same first-leg-fail / second-leg-clean pattern.

## Validity

Both legs were independently valid managed replacements.

- leg A: `run_valid=1`, `rm_oom_count=4`
- leg B: `run_valid=1`, `rm_oom_count=0`
- final `watermark_scale_factor=10`
- final `compaction_proactiveness=20`
- result: `ORCA_R17_RESULT=VALID_A_RM_B_CLEAN`

No VM tunable was changed by the R17 pair itself.

## Leg A — first baseline restart

The first restart emitted four `_memdescAllocInternal` / `NV_ERR_NO_MEMORY (0x51)` events while still reaching the committed healthy runtime state.

The failures retained the already-established RM Linux-sysmem recovery shape:

1. non-contiguous 64 KiB / order-4 allocation request,
2. partial high-order allocation progress,
3. rollback of almost all observed order-4 PFNs,
4. RM `NV_ERR_NO_MEMORY`,
5. immediate same-thread retry for the same logical request at 4 KiB / order 0,
6. order-0 success.

Observed failed logical request sizes in this leg included 1.185547 GiB, 3.125 GiB, 1.5625 GiB, and another 1.185547 GiB request.

Despite the recoverable RM failures, the final managed runtime was active/running, API READY, and the container was not OOM-killed. Under the current strict policy, this leg is FUNCTIONAL PASS / HOST-STABILITY FAIL.

## Leg B — second baseline restart

The immediately adjacent second restart used the same host VM policy and the same managed OrcaRouter configuration.

It completed with:

- `run_valid=1`
- `rm_oom_count=0`
- no RM OOM event snapshot
- populated fast/slow allocator-state sampling

This leg is FUNCTIONAL PASS / HOST-STABILITY PASS for the measured restart.

## Interpretation

R17 directly reproduces the same ordinal pattern previously seen across R15 and R16 without changing the watermark policy:

- R15: first leg baseline 10 failed, second leg watermark 100 was clean.
- R16: first leg watermark 100 failed, second leg baseline 10 was clean.
- R17: first leg baseline 10 failed, second leg baseline 10 was clean.

Therefore the stronger common factor is restart ordinal / allocator-state carry-over, not `watermark_scale_factor=100`.

`watermark_scale_factor=100` must not be promoted as a persistent mitigation from the existing evidence. The R14 standalone clean result and the clean R15 treatment leg are now explained at least as plausibly by allocator-state variability / second-restart carry-over.

The next step should be read-only comparison of R17 leg-A versus leg-B allocator evidence to identify what state created by or surviving the first restart correlates with the clean second restart. New VM tuning experiments should remain paused until that comparison is complete.

## Current conclusion

The proximate RM/Linux failure mechanism remains unchanged and directly observed: Normal-zone Unmovable high-order demand can exhaust usable order-4 supply, triggering rollback and lower-order recovery.

The newly strengthened higher-level conclusion is:

> Whether a specific managed restart encounters the recoverable RM high-order failure is strongly allocator-state dependent. Across three adjacent two-leg campaigns, the first restart failed and the second restart was clean even when the watermark assignment was reversed or held constant.

This is evidence for restart-ordinal / allocator carry-over as the current leading unresolved factor, not proof of one specific kernel mechanism producing that carry-over.
