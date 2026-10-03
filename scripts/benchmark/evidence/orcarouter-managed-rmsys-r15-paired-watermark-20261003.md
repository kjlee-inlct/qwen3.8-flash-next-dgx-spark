# OrcaRouter managed RM-sysmem R15 — paired watermark 10 -> 100 — 2026-10-03

## Classification

- Experiment validity: **VALID**
- Pair result: **VALID_A_RM_B_CLEAN**
- Leg A (`watermark_scale_factor=10`): **FUNCTIONAL PASS / HOST-STABILITY FAIL**
- Leg B (`watermark_scale_factor=100`): **FUNCTIONAL PASS / HOST-STABILITY PASS** for this measured restart
- Both legs independently observed real managed container replacement and `run_valid=1`
- Final host policy restored to `watermark_scale_factor=10`, `compaction_proactiveness=20`

## Purpose

R14 produced the first strict-clean restart while temporarily raising only `vm.watermark_scale_factor` from 10 to 100. Because clean and failing restarts had already been observed under identical OrcaRouter runtime settings, a single clean treatment could not establish causality.

R15 therefore ran an adjacent paired campaign without reboot:

1. Leg A: baseline `watermark_scale_factor=10`, `compaction_proactiveness=20`.
2. Leg B: treatment `watermark_scale_factor=100`, `compaction_proactiveness=20`, with the watermark restored to 10 after the run.

No temporary KV override was present. The immutable release and repository-managed 16 GiB OrcaRouter default were unchanged.

## Leg A — baseline 10

Leg A was a valid managed restart and reproduced the known recoverable RM sysmem failure:

- `run_valid=1`
- `rm_oom_count=1`
- final service active/running
- final container running, Docker OOMKilled=false
- API READY with the expected OrcaRouter model

The failing logical allocation was 3.125 GiB:

- `page_count=819200`
- requested page size: 64 KiB
- Linux order: 4
- expected order-4 chunks: 51,200
- RM return: `NV_ERR_NO_MEMORY (0x51)`

Nested Linux allocator accounting recorded:

- order-4 allocation events: 33,897
- order-4 free events: 33,898
- allocated-then-freed identical PFNs: 33,896
- candidate failed chunk index: 33,898
- compaction attempts: 774
- direct reclaim starts: 547
- extfrag events: 4,300

Immediately afterward the same thread retried the same 3.125 GiB logical request with 4 KiB/order-0 pages and succeeded (`ret=0`). This is the already established RM high-order rollback/lower-order fallback mechanism.

## Leg B — watermark 100

The treatment leg immediately followed the baseline leg in the same non-reboot campaign. It was independently valid:

- `run_valid=1`
- `rm_oom_count=0`
- `RM_SYS_ANALYSIS=NO_RM_OOM_IN_CAPTURE_WINDOW`
- final service active/running
- final container running, Docker OOMKilled=false
- API READY with the expected OrcaRouter model
- `watermark_scale_factor`: 10 -> 100 -> 10
- `compaction_proactiveness=20` throughout

The allocator trace was populated and the kernel RM/OOM window was empty.

## Paired result

R15 summary:

```text
leg_a_run_valid=1
leg_a_rm_oom_count=1
leg_b_run_valid=1
leg_b_rm_oom_count=0
leg_b_watermark_restored=10
watermark_scale_factor_final=10
compaction_proactiveness_final=20
ORCA_R15_RESULT=VALID_A_RM_B_CLEAN
```

This is materially stronger than the standalone R14 clean result. Within one adjacent non-reboot campaign, the baseline policy reproduced the strict host-stability failure and the immediately following treatment did not.

## Interpretation

The R15 pair strengthens the causal case that increasing `watermark_scale_factor` mitigates the observed NVIDIA RM Normal-zone Unmovable order-4 failure path. It is consistent with the prior R11-R14 allocator comparison: the larger watermark scale preserved a larger free-page reserve and coincided with healthier high-order reconstruction/compaction behavior even though total `MemAvailable` was not larger and direct reclaim was not eliminated.

However, the treatment was always second in this pair. Sequential allocator history can influence the next restart, so R15 alone does not eliminate ordering/carry-over as an alternative explanation.

The next controlled validation is therefore a reversed pair: run `watermark_scale_factor=100` first, restore to 10, then run the baseline 10 restart. The most discriminating reverse-order outcome is treatment clean followed by baseline RM OOM.

## Acceptance state

- `watermark_scale_factor=100` is now an **evidence-backed mitigation candidate**, stronger than a single clean restart.
- Persistent host-policy adoption is still deferred pending reverse-order validation.
- The strict host-stability policy remains unchanged: any observed recoverable RM `NV_ERR_NO_MEMORY` keeps that measured restart at HOST-STABILITY FAIL.
- The live host policy after R15 is restored to the original `watermark_scale_factor=10`, `compaction_proactiveness=20`.
