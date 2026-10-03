# OrcaRouter R11-R14 allocator-state comparison — 2026-10-03

## Purpose

Compare the existing R11/R12/R13/R14 allocator-state captures without another managed restart. The goal is to determine whether the first clean R14 run with temporary `vm.watermark_scale_factor=100` also changed allocator behavior in a direction consistent with the known Normal-zone Unmovable order-4 failure mechanism.

The compared runs are:

- R11: baseline VM policy, RM OOM x1;
- R12: one-shot pre-start `compact_memory`, RM OOM x2;
- R13: temporary `compaction_proactiveness=80`, RM OOM x1;
- R14: temporary `watermark_scale_factor=100`, RM OOM x0.

All four runs used the same R11/R10b managed-start and allocator-trace contract.

## Important interpretation rule

`normal_free_minus_low_min_pages` and `normal_free_minus_high_min_pages` are not directly comparable across R14 and R11-R13 because R14 intentionally changes `watermark_scale_factor` from 10 to 100. That change increases the low/high watermark distances themselves, so the more-negative R14 values do not by themselves indicate worse physical free-memory state.

Cross-run interpretation therefore emphasizes absolute free memory, high-order buddy capacity, reclaim counters, and compaction outcomes.

## Results

### RM outcome

- R11: RM OOM x1
- R12: RM OOM x2
- R13: RM OOM x1
- R14: RM OOM x0

R14 remains the first strict-clean Linux-side mitigation candidate.

### Normal-zone order-4+ capacity

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

The one-second sampler observed `normal_ge4_min_mib=0.000` in every run, including clean R14. Therefore a clean run does not require the sampled high-order reservoir to remain non-zero at every one-second observation. The relevant distinction is more likely the duration/recovery behavior around transient depletion rather than a simple never-zero threshold.

R14's median high-order capacity was approximately 24.1% above R11, 9.1% above R12, and 41.3% above R13.

### Absolute free-memory margin

Minimum `MemAvailable`:

- R11: 10,621.770 MiB
- R12: 15,604.723 MiB
- R13: 11,429.074 MiB
- R14: **7,053.609 MiB**

R14 was clean despite having the lowest minimum `MemAvailable`. This further argues against total available memory as the direct failure boundary.

Minimum `MemFree`:

- R11: 762.961 MiB
- R12: 796.453 MiB
- R13: 688.609 MiB
- R14: **1,975.012 MiB**

R14 preserved approximately 2.5-2.9x the minimum immediately free memory of the three failing runs. That direction is consistent with the intended effect of a larger watermark scale: kswapd maintains a larger free-page reserve for bursts.

### kswapd behavior

`kswapd_low_wmark_hit_quickly` deltas:

- R11: 2,394
- R12: 2,198
- R13: 1,538
- R14: **854**

R14 was approximately 44-64% lower than the failing runs. Linux VM documentation describes a high rate of this counter as a sign that kswapd may be going to sleep prematurely and maintaining too small a free-page margin for burst allocations. The direction observed in R14 is therefore consistent with `watermark_scale_factor=100` affecting the intended control path.

`pgscan_kswapd` remained large in every run and was only modestly lower in R14. The clean result cannot be explained as kswapd simply doing less work overall.

### Direct reclaim

`allocstall_normal`:

- R11: 35,439
- R12: 33,668
- R13: 36,665
- R14: **40,032**

`pgscan_direct` and `pgsteal_direct` also remained of the same order as the failing runs.

Therefore R14 did not eliminate direct reclaim pressure. The current evidence does not support the claim that the mitigation works merely by reducing reclaim activity.

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

R14 had more total compaction stalls but substantially more successful compaction and fewer failures. This is consistent with a larger free-page reserve giving compaction a healthier environment in which to reconstruct higher-order blocks, although one clean run cannot establish causality on its own.

## Interpretation

The read-only comparison strengthens, but does not yet prove, the `watermark_scale_factor=100` mitigation hypothesis.

The clean R14 run is not explained by more total available memory or by absence of reclaim pressure. Instead, R14 simultaneously showed:

1. the highest median and final Normal-zone order-4+ capacity;
2. a much larger minimum `MemFree` reserve;
3. substantially fewer `kswapd_low_wmark_hit_quickly` events;
4. a markedly better compaction success/failure balance;
5. zero RM fallback.

Those observations are directionally coherent with the known failure mechanism: NVIDIA RM requires a long sequence of Normal-zone Unmovable order-4 allocations, and the failure appears when the allocator cannot maintain enough reconstructable high-order supply during startup bursts.

The evidence is still allocator-state-dependent and non-randomized. A single R14 clean run must not be promoted to persistent host policy yet.

## Next experiment

R15 should use the same immutable release, 16 GiB managed OrcaRouter default, R11/R10b trace contract, and baseline `compaction_proactiveness=20`, while performing a sequential paired comparison:

1. leg A: baseline `watermark_scale_factor=10`;
2. leg B: temporary `watermark_scale_factor=100`, restored to 10 afterward.

Both legs must be individually valid managed restarts with distinct evidence directories. The result should be classified by the pair rather than treating either single run as definitive.

A particularly informative result would be A reproducing RM fallback while B is clean. If both legs are clean, the pair increases repeatability evidence for B but is not a causal proof. If B also emits RM fallback, 100 is not a sufficient mitigation. Sequence/carry-over remains a limitation; a reverse-order pair can be considered only if needed after R15.
