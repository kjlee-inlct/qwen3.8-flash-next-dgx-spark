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

## Memory totals and composition

Post-compaction host-memory totals:

| Metric | R18 POST | R20 POST | R20 - R18 |
|---|---:|---:|---:|
| MemAvailable | 121504.777 MiB | 121487.285 MiB | -17.492 MiB |
| MemFree | 118694.555 MiB | 107613.363 MiB | -11081.192 MiB |
| SwapFree | 146450.766 MiB | 146421.316 MiB | -29.450 MiB |

The nearly identical MemAvailable and SwapFree values hide an approximately 11.081 GiB MemFree difference.

The detailed meminfo comparison closes that gap:

- Cached: +11114.258 MiB in R20
- Inactive(file): +10938.918 MiB
- Active(file): +165.328 MiB
- AnonPages: only +1.734 MiB
- Slab: -41.723 MiB
- KReclaimable/SReclaimable: -40.547 MiB
- SUnreclaim: -1.176 MiB

Therefore the ~11 GiB MemFree deficit is almost entirely represented by reclaimable file cache rather than extra anonymous or unreclaimable kernel memory. This explains why MemAvailable was nearly identical: Linux correctly counted most of that page cache as reclaimable even though it was not immediately free at the treatment boundary.

A simple MemAvailable or SwapFree gate would therefore not distinguish R18 from R20.

The exact files owning the historical R20 cache cannot be identified from proc snapshots alone. Model/checkpoint file cache is plausible in this workload but is not asserted as fact.

## Compaction vmstat counters

The captured `compact_stall`, `compact_fail`, `compact_success`, and `compact_daemon_wake` counters did not change across either explicit snapshot pair.

That does not mean the one-shot action had no allocator effect: the buddy distributions changed by multiple GiB in both runs. These vmstat counters therefore do not distinguish the explicit R18/R20 one-shot events in this measurement path; the buddy and pagetype snapshots are the direct evidence.

## R21 targeted follow-up and partial live result

R21 was designed directly from this comparison: after an aged predecessor is fully stopped, execute `sync`, reclaim page cache once with `drop_caches=1`, compact once, then start the same immutable OrcaRouter release.

The first live R21 attempt strongly validates the page-cache-conditioning part of the model at the allocator-state level:

- before reclaim: Cached ~8424.0 MiB, Inactive(file) ~6371.3 MiB, MemFree ~113793.2 MiB, Unmovable order-4+ ~100231.9 MiB
- after `drop_caches=1`: Cached ~202.4 MiB, Inactive(file) ~48.2 MiB, MemFree ~122278.4 MiB, Unmovable order-4+ ~105998.9 MiB
- delta from post-sync to post-drop: Cached -8221.984 MiB, MemFree +8490.176 MiB, Unmovable order-4+ +5766.688 MiB, aggregate Normal order-4+ +14486.062 MiB

The subsequent one-shot compaction increased aggregate Normal order-4+ by another +2496.000 MiB but reduced Unmovable order-4+ by -1391.562 MiB while Movable increased by +3875.500 MiB. Across the complete reclaim+compaction treatment, Unmovable order-4+ still ended +4375.438 MiB above the pre-reclaim state.

The managed replacement reached the committed-and-healthy state and remained active, but the runner's long startup exhausted the sudo timestamp before late kernel-journal finalization. The shell-level RM/OOM display was empty, but the canonical summary was not written. Therefore attempt 01 is temporarily classified as incomplete/INVALID until the exact historical kernel window and validity fields are reconstructed by the dedicated post-hoc finalizer. The runner has also been hardened with a sudo keepalive for future long startups.

## Current interpretation

The comparison and R21 partial result narrow the mitigation model:

1. Full stop alone is insufficient: R19 was valid and emitted RM OOM x5.
2. One-shot post-stop compaction can materially coalesce free buddies, but aggregate coalescing alone is not a sufficient eligibility signal.
3. R18 clean and R20 invalid differ strongly in the post-compaction Normal-zone Unmovable high-order reservoir.
4. R20 had nearly the same MemAvailable as R18 despite about 11 GiB less MemFree because the difference was almost entirely reclaimable file cache.
5. R21 directly demonstrates that reclaiming that page cache converts it to free memory and substantially increases the directly relevant Unmovable high-order reservoir before compaction.
6. The compaction step can still shift capacity from Unmovable toward Movable, so eligibility cannot rely on aggregate high-order growth alone.
7. A future production gate, if adopted, should be based on directly relevant allocator state and treatment outcome rather than only predecessor age, MemAvailable, SwapFree, or aggregate order-4+ total.

The leading candidate discriminator remains post-treatment node-0 Normal-zone Unmovable order-4+ free capacity, but no numerical threshold is accepted yet.

## Next step

Do not repeat the restart yet.

First finalize the existing R21 attempt with the dedicated post-hoc helper so the exact kernel window, strict RM count, replacement identity, API readiness, collector status, and `r21-summary.txt` are recovered from the already-captured run. Only then decide whether another aged-predecessor replication or production-integration experiment is warranted.
