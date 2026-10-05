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

## Aggregate allocator A/B comparison

A read-only comparison of the two R17 evidence sets shows that the clean second leg is not explained by a larger initial aggregate high-order pool or by globally lower reclaim/compaction pressure.

Normal-zone order-4+ buddy capacity:

- leg A start: 4148.688 MiB
- leg A median: 1635.156 MiB
- leg A end: 3701.062 MiB
- leg B start: 3692.312 MiB
- leg B median: 1958.938 MiB
- leg B end: 2419.062 MiB

The first important result is that leg A actually started with more aggregate order-4+ capacity than the clean leg B, so the initial high-order total by itself is not a sufficient predictor of RM failure.

The second important result is continuity across the restart boundary: leg A ended at 3701.062 MiB and leg B began at 3692.312 MiB, only 8.750 MiB apart, about 0.24% of the leg-A final value. This strongly supports physical allocator-state continuity from the first restart into the second rather than a fresh independent starting state.

Other aggregate pressure counters do not show the clean leg B as uniformly less stressed:

- `allocstall_normal`: A 32989, B 34979
- `kswapd_low_wmark_hit_quickly`: A 1973, B 2478
- `compact_stall`: A 65990, B 96447
- `compact_fail`: A 37269, B 59291
- `compact_success`: A 28721, B 37156

Minimum `MemAvailable` was also similar (A 9189.203 MiB, B 9081.137 MiB), while minimum `MemFree` was only modestly higher in B (A 796.703 MiB, B 861.430 MiB).

## Migratetype / pageblock carry-over

A second read-only comparison used the full baseline/final snapshots to inspect Normal-zone high-order free-area composition and pageblock ownership.

At leg-A baseline, Normal-zone order-4+ free capacity was split as:

- Unmovable: 3473.062 MiB, including 18,991 order-4 blocks
- Movable: 675.562 MiB, including 2,661 order-4 blocks
- Reclaimable: 0.062 MiB
- total buddy order-4+: 4148.688 MiB

At leg-A final, after the failing/recovering restart had completed:

- Unmovable: 3699.812 MiB, including 19,707 order-4 blocks
- Movable: 0 MiB, including zero order-4 blocks
- Reclaimable: 1.250 MiB
- total buddy order-4+: 3701.062 MiB

At leg-B baseline, only about 220.665 ms later, the state remained almost unchanged:

- Unmovable: 3692.062 MiB, including 19,669 order-4 blocks
- Movable: 0 MiB
- Reclaimable: 0.250 MiB
- total buddy order-4+: 3692.312 MiB

Thus the clean B restart began with about 456 MiB less aggregate high-order capacity than failing A, but about 219 MiB more high-order capacity already classified as Unmovable, the migratetype directly requested by the traced NVIDIA RM order-4 allocations. B also began with 678 more Unmovable order-4 blocks than A.

The A-final -> B-baseline boundary is especially strong carry-over evidence:

- total Normal order-4+ delta: -8.750 MiB (-0.236%)
- Unmovable order-4+ delta: -7.750 MiB
- Movable order-4+ delta: 0 MiB
- Unmovable pageblocks: 55,626 -> 55,621
- Movable pageblocks: 8,770 -> 8,775

The pageblock counts require a careful distinction. During A, Normal pageblock ownership did not simply move toward Unmovable; the counts moved slightly in the opposite direction (Unmovable 55,892 -> 55,626, Movable 8,500 -> 8,770). What changed dramatically was the migratetype composition of the *free high-order areas*: free Movable high-order capacity disappeared while free Unmovable high-order capacity increased.

## Cross-campaign conditioning chain

A chronological read-only comparison across R15, R16 and R17 adds two important corrections.

First, the immediately adjacent pair boundaries preserve allocator state almost exactly:

- R15A final -> R15B baseline: 0.467 s, total high-order -6.500 MiB
- R16A final -> R16B baseline: 6.394 s, total high-order -2.438 MiB
- R17A final -> R17B baseline: 0.221 s, total high-order -8.750 MiB

This confirms that the second leg is not starting from an independent allocator state.

Second, the simple hypothesis "a clean second leg starts with Movable high-order near zero" does not hold for all pairs. R15B was clean even though its baseline still contained about 552.375 MiB of Movable high-order free capacity. In contrast, R16B and R17B did begin with approximately zero Movable high-order capacity and were also clean. Therefore free-area migratetype composition is part of the observed conditioning state but is not, by itself, a sufficient cross-campaign predictor.

The longer between-campaign boundaries show substantial drift while the current loaded runtime remains active:

- R15B final -> R16A baseline: 6551.934 s (~109 min), total high-order +833.625 MiB, Movable +934.688 MiB
- R16B final -> R17A baseline: 16950.590 s (~282.5 min), total high-order +847.438 MiB, Movable +665.500 MiB

Both following first legs failed. This makes elapsed time / predecessor-runtime residency a stronger common discriminator than watermark assignment or one specific migratetype composition.

## Predecessor runtime age correlation

A direct read-only correlation used the already-recorded predecessor container start time and managed restart start time for every R15-R17 leg.

The six observations separate completely:

- R15A: predecessor age 50.722 min, RM OOM x1
- R15B: predecessor age 14.947 min, clean
- R16A: predecessor age 125.120 min, RM OOM x3
- R16B: predecessor age 15.052 min, clean
- R17A: predecessor age 298.448 min, RM OOM x4
- R17B: predecessor age 15.953 min, clean

There is no overlap between the observed clean and failing predecessor ages. The three clean restarts replaced runtimes approximately 15-16 minutes old, while all three failures replaced substantially older runtimes, starting at about 50.7 minutes in the shortest observed failure.

The failure count also rose across the three older-predecessor observations (1, 3, 4) as predecessor age increased (50.7, 125.1, 298.4 minutes). With only three failing samples this must not be treated as a calibrated dose-response curve, but it strengthens the evidence that elapsed residency is related to the allocator state presented at teardown.

This still does not prove that wall-clock age itself is causal. Runtime age is a proxy for allocator/residency drift while the loaded predecessor remains active. The mechanism could be the physical-page layout released by teardown after a long residency rather than elapsed time directly.

## R18 post-stop compaction plan

The age correlation changes where the next mitigation should act. R12 compacted while the predecessor runtime was still resident, so the pages later released by predecessor teardown were not available to that compaction pass. The managed service path also stops the predecessor and immediately starts the replacement.

R18 therefore tests a narrower teardown-boundary intervention:

1. require the predecessor to be at least 2700 seconds (45 minutes) old,
2. begin read-only allocator-state collection,
3. fully stop the predecessor service and verify its container is no longer running,
4. capture post-stop allocator state,
5. write `1` to `vm.compact_memory` exactly once,
6. capture post-compaction allocator state,
7. start the same immutable OrcaRouter release through the normal managed service helper,
8. require a real container replacement and healthy API,
9. classify any `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` as HOST-STABILITY FAIL under the unchanged strict policy.

R18 changes no persistent VM tunable. Its helper is `scripts/benchmark/run-orcarouter-managed-rmsys-r18-poststop-compact.sh`; regression coverage enforces the aged-predecessor guard, stop-before-compact ordering, exactly one `compact_memory` write, absence of persistent VM-knob writes, allocator-state capture, and explicit VALID_CLEAN / VALID_RM_OOM outcomes. CI #915 passed.

## Interpretation

R17 directly reproduces the same ordinal pattern previously seen across R15 and R16 without changing the watermark policy:

- R15: first leg baseline 10 failed, second leg watermark 100 was clean.
- R16: first leg watermark 100 failed, second leg baseline 10 was clean.
- R17: first leg baseline 10 failed, second leg baseline 10 was clean.

Therefore the stronger common factor is not `watermark_scale_factor=100`.

`watermark_scale_factor=100` must not be promoted as a persistent mitigation from the existing evidence. The R14 standalone clean result and the clean R15 treatment leg are now explained at least as plausibly by allocator-state variability / adjacent-restart carry-over.

The R15-R17 conditioning chain further shows that aggregate high-order capacity, free-area migratetype composition, and pageblock ownership are individually insufficient to explain all three pairs. The direct age correlation provides the cleanest higher-level discriminator observed so far: every approximately 15-16 minute predecessor was clean, while every 50.7-298.4 minute predecessor emitted recoverable RM OOM.

New persistent VM tuning experiments remain paused. R18 instead targets the moment when an aged predecessor releases its physical pages.

## Current conclusion

The proximate RM/Linux failure mechanism remains unchanged and directly observed: Normal-zone Unmovable high-order demand can exhaust usable order-4 supply, triggering rollback and lower-order recovery.

The strengthened higher-level conclusion is:

> Whether a specific managed restart encounters the recoverable RM high-order failure is strongly dependent on the state of the predecessor runtime and allocator at teardown. Across R15-R17, predecessor age cleanly separates the six observed outcomes: approximately 15-16 minute predecessors were clean, while 50.7-298.4 minute predecessors emitted RM OOM. Age is best treated as a proxy for residency/allocator-layout drift, not yet as a causal timer threshold.

R18 tests whether compacting only after the aged predecessor has fully released its pages can turn that otherwise failure-associated restart boundary into a strict-clean replacement.
