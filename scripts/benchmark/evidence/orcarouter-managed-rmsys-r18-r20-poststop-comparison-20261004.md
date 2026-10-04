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
| Unmovable | 106486.812 MiB | 95162.375 MiB | -11324.438 MiB |
| Movable | 6079.625 MiB | 10080.875 MiB | +4001.250 MiB |
| Reclaimable | 29.062 MiB | 20.188 MiB | -8.875 MiB |
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

- Unmovable order-4+: 105834.188 -> 106486.812 MiB, delta +652.625 MiB
- Movable order-4+: 4324.250 -> 6079.625 MiB, delta +1755.375 MiB

R20:

- Unmovable order-4+: 96043.062 -> 95162.375 MiB, delta -880.688 MiB
- Movable order-4+: 6046.188 -> 10080.875 MiB, delta +4034.688 MiB

Thus the R20 compaction pass increased aggregate order-4+ capacity while the directly relevant Unmovable reservoir actually decreased. Most of the visible gain appeared in Movable high-order free capacity.

This is the strongest current reason not to use only `compact_memory executed` or aggregate order-4+ growth as a production eligibility condition.

## Memory totals and composition

Post-compaction host-memory totals were:

| Metric | R18 POST | R20 POST | R20 - R18 |
|---|---:|---:|---:|
| MemAvailable | 121504.777 MiB | 121487.285 MiB | -17.492 MiB |
| MemFree | 118694.555 MiB | 107613.363 MiB | -11081.191 MiB |
| SwapFree | 146450.766 MiB | 146421.316 MiB | -29.449 MiB |

The nearly identical MemAvailable and SwapFree values therefore hide an approximately 11.081 GiB MemFree difference.

The detailed meminfo comparison explains that gap almost completely:

| Category | R20 - R18 |
|---|---:|
| Cached | +11114.258 MiB |
| Inactive(file) | +10938.918 MiB |
| Active(file) | +165.328 MiB |
| SwapCached | +23.543 MiB |
| AnonPages | +1.734 MiB |
| Inactive(anon) | +1.578 MiB |
| Active(anon) | -0.648 MiB |
| KReclaimable | -40.547 MiB |
| Slab | -41.723 MiB |
| SReclaimable | -40.547 MiB |
| SUnreclaim | -1.176 MiB |

R20 therefore did not have an additional ~11 GiB anonymous or unreclaimable allocation at this post-stop boundary. The missing MemFree was almost entirely represented as file cache, dominated by `Inactive(file)`.

This explains why MemAvailable was nearly identical: Linux counted that file-backed cache as reclaimable even though it was not currently free. A simple MemAvailable gate would therefore consider R18 and R20 almost equivalent despite a large difference in immediately free pages and in the Normal-zone Unmovable high-order reservoir.

The historical snapshots do not identify which files owned those cached pages. Checkpoint/model-file cache is a plausible source given the workload, but that attribution is an inference rather than something proved by these proc snapshots.

## Compaction vmstat counters

The captured `compact_stall`, `compact_fail`, `compact_success`, and `compact_daemon_wake` counters did not change across either explicit snapshot pair.

That does not mean the one-shot action had no allocator effect: the buddy distributions changed by multiple GiB in both runs. These vmstat counters therefore do not distinguish the explicit R18/R20 one-shot events in this measurement path; the buddy and pagetype snapshots are the direct evidence.

## Current interpretation

The comparison narrows the mitigation model:

1. Full stop alone is insufficient: R19 was valid and emitted RM OOM x5.
2. One-shot post-stop compaction can materially coalesce free buddies, but aggregate coalescing alone is not a sufficient eligibility signal.
3. R18 clean and R20 invalid differ strongly in the post-compaction Normal-zone Unmovable high-order reservoir.
4. R20 had almost exactly the same MemAvailable as R18 because ~11 GiB less MemFree was offset by ~11 GiB more reclaimable file cache, overwhelmingly `Inactive(file)`.
5. MemAvailable and SwapFree are therefore too coarse to distinguish the two states.
6. The leading allocator-state discriminator remains post-compaction node-0 Normal-zone Unmovable order-4+ free capacity, but no numerical threshold is accepted yet.
7. The R20 protected-stop path must also be reviewed against the monitor's exact free/non-CMA-free and available-memory logic because reclaimable file cache can keep MemAvailable high while immediately free pages remain lower.

## Next step

Do not perform another restart yet.

Review the managed memory-protection logic against the R20 monitor samples and the now-explained file-cache-heavy post-stop state. If the protection gate intentionally depends on immediately free/non-CMA-free memory as well as MemAvailable, preserve that safety behavior and design the next controlled treatment around a measured post-compaction allocator eligibility state rather than around MemAvailable alone.

If a future run needs to determine whether checkpoint files specifically account for the file cache, add file-residency capture at the post-stop boundary before mutating caches. Do not retrospectively attribute the existing R18/R20 cache pages to a specific file without direct evidence.
