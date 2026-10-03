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
- `vm.compaction_proactiveness` remained at 20
- Original policy restored: `vm.watermark_scale_factor=10`

## Purpose

R12 showed that one-shot pre-start compaction is insufficient and R13 showed that temporary `vm.compaction_proactiveness=80` alone is also insufficient. R14 therefore changed exactly one independent VM policy for the full startup interval: `vm.watermark_scale_factor` from the measured baseline 10 to 100. All other relevant VM tunables were intentionally left unchanged and the original value was restored after the experiment.

## Runtime outcome

The managed restart completed successfully and committed/attested as healthy.

The R10b/R11 trace contract was valid:

- trace return: 0
- managed command return: 0
- real container replacement observed
- `run_valid=1`
- allocator analysis return: 0
- populated trace captured across all CPUs
- kernel RM/OOM window: empty
- `RM_SYS_ANALYSIS=NO_RM_OOM_IN_CAPTURE_WINDOW`

The final service was active/running, the container reported `oom_killed=false`, and the API returned the expected OrcaRouter model.

## Policy restoration

R14 recorded:

- original `watermark_scale_factor=10`
- target `watermark_scale_factor=100`
- restored `watermark_scale_factor=10`
- `compaction_proactiveness=20` throughout

The current host policy after the run was independently verified as:

- `watermark_scale_factor=10`
- `compaction_proactiveness=20`

## Read-only R11-R14 comparison

A later read-only comparison of the already captured R11/R12/R13/R14 allocator-state samples strengthens the R14 mitigation hypothesis without requiring another restart.

Important caveat: `normal_free_minus_low_min_pages` and `normal_free_minus_high_min_pages` are not directly comparable between R14 and R11-R13 because R14 intentionally increases the low/high watermark distances themselves by changing `watermark_scale_factor` from 10 to 100.

The comparable allocator indicators show:

### Normal-zone order-4+ supply

Median Normal-zone order-4+ capacity:

- R11: 1,722.312 MiB
- R12: 1,958.344 MiB
- R13: 1,513.062 MiB
- R14: **2,137.531 MiB**

End-of-run Normal-zone order-4+ capacity:

- R11: 2,549.188 MiB
- R12: 2,905.500 MiB
- R13: 2,496.375 MiB
- R14: **3,607.938 MiB**

Every run, including clean R14, reached `normal_ge4_min_mib=0.000` in the one-second samples. Therefore the mitigation cannot be reduced to a simple requirement that sampled high-order capacity never reach zero. The duration and recovery behavior around transient depletion are more relevant.

### Absolute memory margin

Minimum `MemAvailable`:

- R11: 10,621.770 MiB
- R12: 15,604.723 MiB
- R13: 11,429.074 MiB
- R14: **7,053.609 MiB**

R14 was clean despite the lowest minimum `MemAvailable`, further rejecting total available memory as the direct failure boundary.

Minimum `MemFree`:

- R11: 762.961 MiB
- R12: 796.453 MiB
- R13: 688.609 MiB
- R14: **1,975.012 MiB**

R14 therefore preserved approximately 2.5-2.9x the minimum immediately free memory of the failing runs, consistent with the intended effect of a larger watermark scale.

### kswapd behavior

`kswapd_low_wmark_hit_quickly` deltas:

- R11: 2,394
- R12: 2,198
- R13: 1,538
- R14: **854**

R14 was roughly 44-64% lower than the failing runs. Linux VM documentation identifies a high rate of this counter as a sign that kswapd may be sleeping prematurely and maintaining too small a free-page margin for burst allocation demand. The R14 direction is therefore consistent with the policy knob affecting its intended control path.

### Direct reclaim

`allocstall_normal` remained high and was actually largest in R14:

- R11: 35,439
- R12: 33,668
- R13: 36,665
- R14: **40,032**

`pgscan_direct` and `pgsteal_direct` also remained comparable to the failing runs. The clean result therefore is not explained by eliminating direct reclaim activity.

### Compaction outcome

Compaction stall / failure / success:

- R11: 62,239 / 33,259 / 28,980
- R12: 59,001 / 30,106 / 28,895
- R13: 62,276 / 37,976 / 24,300
- R14: **69,010 / 23,687 / 45,323**

Approximate compaction-success fraction among stall outcomes:

- R11: 46.6%
- R12: 49.0%
- R13: 39.0%
- R14: **65.7%**

R14 had more total compaction stalls but substantially more successful compaction and fewer failures. This is directionally consistent with a larger free-page reserve giving compaction a healthier environment in which to rebuild high-order blocks.

## Interpretation

R14 is the first strict-clean Linux-side mitigation candidate and the cross-run allocator-state comparison makes the result more coherent with the known failure mechanism.

The clean R14 run is not explained by more total available memory or by absence of reclaim pressure. Instead, it combined:

1. higher median/final Normal-zone order-4+ capacity;
2. a much larger minimum immediately free-memory reserve;
3. fewer `kswapd_low_wmark_hit_quickly` events;
4. a better compaction success/failure balance;
5. zero RM fallback.

This pattern fits the existing mechanism in which NVIDIA RM creates sustained Normal-zone Unmovable order-4 demand and fails when the allocator cannot maintain enough reconstructable high-order supply during startup bursts.

The result remains a single allocator-state-dependent clean run. It is not yet sufficient to promote `watermark_scale_factor=100` to persistent host policy.

## Next mitigation step

R15 should perform a sequential paired comparison with distinct evidence directories:

1. leg A: baseline `watermark_scale_factor=10`, `compaction_proactiveness=20`;
2. leg B: temporary `watermark_scale_factor=100`, `compaction_proactiveness=20`, restored to 10 afterward.

Both legs must independently prove a real managed restart using the same R11/R10b trace contract.

The pair is interpreted conservatively:

- A RM / B clean: strong directional evidence for the watermark mitigation;
- both clean: repeatability evidence for B, but not causal proof;
- A clean / B RM: contradicts a simple protective interpretation;
- both RM: 100 is not a sufficient mitigation.

Because the pair is sequential rather than randomized, allocator carry-over remains a limitation. A reverse-order pair should be considered only if R15 results make that additional control necessary.
