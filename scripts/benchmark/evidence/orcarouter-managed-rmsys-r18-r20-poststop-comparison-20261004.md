# OrcaRouter R18 vs R20 post-stop state comparison — 2026-10-04

## Purpose

This read-only comparison uses the already-captured post-stop snapshots from:

- R18: aged-predecessor post-stop compaction treatment, valid clean
- R20: aged-predecessor post-stop compaction replication attempt, invalid because the managed memory-protection gate stopped the candidate before readiness

No additional restart or VM-policy mutation is required.

## High-order buddy state

Normal-zone buddy state after the explicit post-stop compaction differed materially:

| Metric | R18 POST | R20 POST | R20 - R18 |
|---|---:|---:|---:|
| exact order-4 | 3221.062 MiB | 1761.062 MiB | -1460.000 MiB |
| order-5+ | 109376.375 MiB | 103502.375 MiB | -5874.000 MiB |
| order-4+ total | 112597.438 MiB | 105263.438 MiB | -7334.000 MiB |

R20 therefore entered replacement startup with about 7.334 GiB less Normal-zone order-4+ free capacity than R18.

This is not a hard threshold claim. R20 did not complete startup, so the observed boundary cannot yet be treated as a sufficient-condition cutoff.

## Migratetype composition

The larger discriminator is the Normal-zone free-area migratetype composition.

Post-compaction order-4+ values:

| Migratetype | R18 POST | R20 POST | R20 - R18 |
|---|---:|---:|---:|
| Unmovable | 106486.812 MiB | 95162.375 MiB | -11324.437 MiB |
| Movable | 6079.625 MiB | 10080.875 MiB | +4001.250 MiB |
| Reclaimable | 29.062 MiB | 20.188 MiB | -8.874 MiB |
| HighAtomic | 1.938 MiB | 0 MiB | -1.938 MiB |

Approximate shares of total Normal order-4+ free capacity:

- R18 POST Unmovable: ~94.57%
- R20 POST Unmovable: ~90.40%
- R18 POST Movable: ~5.40%
- R20 POST Movable: ~9.58%

The R20 deficit is therefore not only a lower aggregate high-order total. It has about 11.324 GiB less Unmovable high-order free capacity while simultaneously having about 4.001 GiB more Movable high-order free capacity.

This matters because the earlier exact RM/Linux trace localized the relevant demand to node-0 Normal-zone Unmovable order-4 allocations.

## Compaction direction differs by migratetype

Both runs show upward buddy coalescing at the aggregate level:

- R18 order-4+ delta: +2413.125 MiB
- R20 order-4+ delta: +3154.000 MiB

But the migratetype effect is different.

R18:

- Unmovable order-4+: 105834.188 -> 106486.812 MiB, delta +652.624 MiB
- Movable order-4+: 4324.250 -> 6079.625 MiB, delta +1755.375 MiB

R20:

- Unmovable order-4+: 96043.062 -> 95162.375 MiB, delta -880.687 MiB
- Movable order-4+: 6046.188 -> 10080.875 MiB, delta +4034.687 MiB

Thus the R20 compaction pass increased aggregate order-4+ capacity while the directly relevant Unmovable reservoir actually decreased. Most of the visible gain appeared in Movable high-order free capacity.

This is the strongest current reason not to use only `compact_memory executed` or aggregate order-4+ growth as a production eligibility condition.

## Memory totals

Post-compaction host-memory totals were also different:

| Metric | R18 POST | R20 POST | R20 - R18 |
|---|---:|---:|---:|
| MemAvailable | 121504.777 MiB | 121487.285 MiB | -17.492 MiB |
| MemFree | 118694.555 MiB | 107613.363 MiB | -11081.192 MiB |
| SwapFree | 146450.766 MiB | 146421.316 MiB | -29.450 MiB |

The nearly identical MemAvailable and SwapFree values therefore hide an approximately 11.081 GiB MemFree difference.

This means a simple pre-start MemAvailable or SwapFree gate would not distinguish R18 from R20. The missing free RAM must be represented elsewhere in the memory composition and may be reclaimable, but the first comparison output does not identify which meminfo categories account for it.

The comparator was therefore extended to emit detailed `proc/meminfo` composition including file/anon active/inactive memory, Cached, KReclaimable, SReclaimable/SUnreclaim, Slab, Shmem, SwapCached, and related fields. Re-running that read-only analyzer is the next discriminator.

## Compaction vmstat counters

The captured `compact_stall`, `compact_fail`, `compact_success`, and `compact_daemon_wake` counters did not change across either explicit snapshot pair.

That does not mean the one-shot action had no allocator effect: the buddy distributions changed by multiple GiB in both runs. These vmstat counters therefore do not distinguish the explicit R18/R20 one-shot events in this measurement path; the buddy and pagetype snapshots are the direct evidence.

## Current interpretation

The comparison narrows the mitigation model:

1. Full stop alone is insufficient: R19 was valid and emitted RM OOM x5.
2. One-shot post-stop compaction can materially coalesce free buddies, but aggregate coalescing alone is not a sufficient eligibility signal.
3. R18 clean and R20 invalid differ strongly in the post-compaction Normal-zone Unmovable high-order reservoir.
4. R20 had nearly the same MemAvailable as R18 despite about 11 GiB less MemFree, so generic available-memory gating is too coarse.
5. A future production gate, if adopted, should be based on directly relevant allocator state rather than only predecessor age, MemAvailable, SwapFree, or aggregate order-4+ total.

The leading candidate discriminator is post-compaction node-0 Normal-zone Unmovable order-4+ free capacity, but no numerical threshold is accepted yet because there is only one completed clean treatment and one invalid protected-stop treatment at these states.

## Next step

Do not perform another restart yet.

Re-run the updated read-only R18/R20 comparator against the existing evidence so the detailed meminfo composition and per-migratetype compaction/cross-run deltas can explain the ~11 GiB MemFree gap. Only after that comparison should the next aged-predecessor treatment or an explicit allocator-state eligibility gate be designed.
