# OrcaRouter managed RM-sysmem R13 — compaction_proactiveness=80 — 2026-10-03

## Classification

- Experiment validity: **VALID**
- Functional classification: **PASS**
- Host-stability classification: **FAIL** under the current strict policy
- Mitigation result: **FAIL** (`ORCA_R13_RESULT=VALID_RM_OOM`)
- Managed restart: valid (`run_valid=1`)
- RM events: **1 recoverable `NV_ERR_NO_MEMORY (0x51)`**
- Final runtime: active/running, API READY, Docker OOMKilled=false
- Temporary VM policy: `vm.compaction_proactiveness=80` for the full startup interval
- Original policy restored: `vm.compaction_proactiveness=20`

## Purpose

R12 showed that one-shot pre-start compaction is insufficient because the relevant Normal-zone high-order state degrades dynamically during the long OrcaRouter startup. R13 therefore changed exactly one VM policy for the full startup interval: `vm.compaction_proactiveness` from the measured baseline 20 to 80. All other VM tunables were intentionally left unchanged, and the original value was restored after the experiment.

## Runtime outcome

The managed restart completed successfully and committed/attested as healthy. The experiment captured one RM sysmem failure during startup.

The failed logical request was 3.125 GiB:

- `page_count=819200`
- requested page size: 64 KiB
- derived Linux allocation order: 4
- expected order-4 chunks: 51,200
- captured policy: `contiguous=0`, `cache_type=0`, `zeroed=1`, `unencrypted=0`, `node_id=-1`
- return: `0x51`

Nested sysmem accounting:

- order-4 allocations: 28,601
- order-4 frees: 28,600
- identical PFNs allocated then freed: 28,600
- candidate failed chunk: 28,602
- rollback size: **1,787.5 MiB**
- compaction attempts: 69
- direct reclaim attempts: 22
- extfrag events: 1,578
- extfrag ownership changes: 478

The immediately following same-thread request preserved the same logical size and captured policy, switched to 4 KiB/order 0, and succeeded.

## Policy restoration

R13 recorded:

- original `compaction_proactiveness=20`
- target `compaction_proactiveness=80`
- restored `compaction_proactiveness=20`

The current host value after the run was also verified as 20.

## Comparison with R12

R12 with the baseline `compaction_proactiveness=20` produced two recoverable RM OOM events. R13 with `compaction_proactiveness=80` produced one.

This difference is directionally consistent with sustained background compaction helping the workload, but one allocator-state-dependent run is not sufficient to attribute the lower event count causally. The strict mitigation criterion is zero RM fallback, and R13 did not meet it.

R13 therefore rejects `compaction_proactiveness=80` alone as a sufficient mitigation.

The first R13 failure also occurred later in the logical 3.125 GiB order-4 sequence than an immediate allocation failure but earlier than R12's corresponding 40,451st candidate chunk: R13 failed at candidate chunk 28,602 versus R12 at 40,451. This reinforces that high-order availability remains strongly state-dependent and that event count or progress-to-failure should not be treated as a monotonic quality metric across single runs.

## Interpretation

The R11/R12/R13 sequence now separates three observations:

1. one-shot compaction before startup is insufficient;
2. more aggressive proactive compaction throughout startup can still leave the Normal-zone Unmovable order-4 path unable to complete a large logical request;
3. the failure remains recoverable because the same logical request succeeds immediately at order 0.

The next isolated mitigation should therefore address the free-page reserve/reclaim margin maintained by kswapd rather than increasing compaction aggressiveness again.

## Next mitigation step

R14 should restore `compaction_proactiveness=20` and modify exactly one independent knob: `vm.watermark_scale_factor`.

The baseline is 10, meaning watermark distances are 0.1% of node/system memory. Linux VM documentation specifically identifies high direct-reclaim/allocstall rates as a signal that kswapd may be maintaining too small a free-page margin for burst allocations and recommends this knob for tuning kswapd aggressiveness.

A conservative first R14 target is 100 (1.0%), with every other relevant VM knob unchanged and the measured baseline restored on every exit path. The same R11/R10b trace contract must remain in place so zero RM fallback remains the acceptance criterion.
