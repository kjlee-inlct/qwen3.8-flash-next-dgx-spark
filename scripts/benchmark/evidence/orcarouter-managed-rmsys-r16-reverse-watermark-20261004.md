# OrcaRouter managed RM-sysmem R16 — reverse watermark pair — 2026-10-04

## Classification

- Experiment validity: **VALID**
- Leg A (`watermark_scale_factor=100`): FUNCTIONAL PASS / HOST-STABILITY FAIL, RM OOM x3
- Leg B (`watermark_scale_factor=10`): FUNCTIONAL PASS / HOST-STABILITY PASS for this measured restart, RM OOM x0
- Pair result: `ORCA_R16_RESULT=VALID_A_RM_B_CLEAN`
- Final VM policy restored: `watermark_scale_factor=10`, `compaction_proactiveness=20`

## Purpose

R15 produced baseline-10 failure followed immediately by treatment-100 clean. R16 reversed only the order to test whether the R15 result was truly attributable to `watermark_scale_factor=100` or instead reflected restart ordinal / allocator carry-over effects.

R16 sequence:

1. Leg A: temporary `watermark_scale_factor=100` under the proven R14/R11/R10b contract, restored to 10 afterward.
2. Leg B: baseline `watermark_scale_factor=10` under the proven R11/R10b contract.

Both legs required independent managed restart validity.

## Result

Leg A, treatment 100:

- `run_valid=1`
- `rm_oom_count=3`
- real container replacement
- runtime eventually READY, Docker OOMKilled=false
- all three RM failures were the already established 64 KiB/order-4 -> rollback -> same-thread 4 KiB/order-0 success path
- observed failed logical sizes included 3.125 GiB, 1.5625 GiB, and 1.193359 GiB
- treatment restored `watermark_scale_factor=100 -> 10`

Leg B, baseline 10:

- `run_valid=1`
- `rm_oom_count=0`
- real container replacement
- runtime READY

Pair summary:

- treatment 100 first: **RM OOM x3**
- baseline 10 second: **RM OOM x0**
- final policy: 10 / 20

## Interpretation

R16 contradicts the simple hypothesis that `watermark_scale_factor=100` itself prevents the RM fallback.

Combined with R15:

- R15 first leg baseline 10: RM OOM x1; second leg treatment 100: clean
- R16 first leg treatment 100: RM OOM x3; second leg baseline 10: clean

The stronger common pattern is therefore **first restart in the pair fails, second restart is clean**, independent of which watermark value is assigned to the first or second leg.

This makes restart ordinal / allocator carry-over the leading explanation for the R15 discrimination. The earlier standalone R14 clean result remains valid as one measured clean restart, but it no longer supports persistent adoption of `watermark_scale_factor=100` by itself.

## Mitigation status

- `watermark_scale_factor=100`: **NOT accepted as a causal mitigation**
- persistent sysctl promotion: **deferred / not justified**
- root Linux allocator mechanism remains unchanged and directly supported

## Next experiment

Run a same-policy repeat pair at baseline only:

- Leg A: `watermark_scale_factor=10`
- Leg B: `watermark_scale_factor=10`

No VM policy is changed between legs. If the same first-fail / second-clean pattern reproduces, it directly demonstrates a restart-ordinal / carry-over effect without watermark as a confounder.
