# OrcaRouter R21 allocator collapse onset — 2026-10-04

## Scope

This document records the read-only full-history analysis of the R21 allocator samples. R21 itself remains `VALID_RM_OOM` (FUNCTIONAL PASS / strict HOST-STABILITY FAIL).

The purpose here is to locate when the prepared Normal-zone high-order reservoir first collapsed, not to introduce a new runtime mutation.

## Timing

- post-stop compaction completed: `2026-10-04T15:22:38+09:00` (`06:22:38Z`)
- strict RM event: `2026-10-04T06:35:00.611065+00:00`
- compact-to-event duration: `742.611 s`

Prepared state at the beginning of the scan:

- Normal Unmovable order-4+: `104613.938 MiB`
- aggregate Normal order-4+: `119742.938 MiB`

## First threshold crossings

Normal Unmovable order-4+:

- below 50% (`52306.969 MiB`): `06:23:23.990990Z`, value `29280.688 MiB`
- below 10% (`10461.394 MiB`): `06:23:28.990563Z`, value `6248.688 MiB`
- below 1% (`1046.139 MiB`): `06:23:34.003006Z`, value `0 MiB`
- below 1 GiB / 100 MiB / 10 MiB: the same `06:23:34.003006Z` sample, value `0 MiB`

Aggregate Normal order-4+:

- below 50% (`59871.469 MiB`): `06:23:22.990282Z`, value `50375.875 MiB`
- below 10% (`11974.294 MiB`): `06:23:28.990290Z`, value `6266.250 MiB`
- below 1% (`1197.429 MiB`): `06:23:29.995656Z`, value `0.438 MiB`
- below 1 GiB / 100 MiB / 10 MiB: the same `06:23:29.995656Z` sample, value `0.438 MiB`

Therefore the prepared high-order state collapses almost completely within roughly 45-56 seconds after compaction and more than eleven minutes before the final RM OOM event.

## Steepest observed drain

Largest consecutive 5-second Unmovable drop:

- interval: approximately `06:23:18.991Z -> 06:23:23.991Z`
- `104162.625 -> 29280.688 MiB`
- delta: `-74881.938 MiB` in `5.000 s`

Largest consecutive 5-second Movable drop:

- interval: approximately `06:23:23.991Z -> 06:23:28.991Z`
- `8921.438 -> 6.750 MiB`
- delta: `-8914.688 MiB` in `5.000 s`

Largest consecutive 1-second aggregate Normal order-4+ drop:

- interval: approximately `06:23:21.990Z -> 06:23:22.990Z`
- `76771.000 -> 50375.875 MiB`
- delta: `-26395.125 MiB` in about `1.000 s`

This is not a slow monotonic drain spread across the whole ~12 minute startup. The dominant collapse occurs near the beginning of model startup.

## Correlation with PLE/model loading

The preserved managed output contains the first visible PLE-offload progress marker at:

- `06:23:25.827677599Z`
- `PleOffloadWorker pid=458`
- `Loading safetensors checkpoint shards(PLE-offload): 6% Completed | 1/18`

The high-order collapse begins before this first visible progress line:

- aggregate Normal 50% crossing: ~`2.84 s` before the 6% PLE line
- Unmovable 50% crossing: ~`1.84 s` before the 6% PLE line

But the 6% PLE line lands inside the collapse window:

- Unmovable 50% crossing: `06:23:23.991Z`
- first visible PLE 6% line: `06:23:25.828Z`
- Unmovable 10% crossing: `06:23:28.991Z`
- aggregate Normal effectively zero: `06:23:29.996Z`
- Unmovable effectively zero: `06:23:34.003Z`

Because the first captured PLE progress line is already at 6%, it is not the PLE start timestamp. The evidence therefore supports a strong temporal correlation with the initial legacy PLE/shard-loading window, but does not prove that the `PleOffloadWorker` owns every consumed page or that PLE alone causes the collapse.

The later `Using MoEPrepareAndFinalizeNoDPEPModular` marker at `06:34:48.381Z` occurs long after Unmovable capacity was already exhausted and is not the onset cause.

## Runtime-path context

The managed OrcaRouter profile currently uses the legacy CPU-offload PLE path (`VLLM_PLE_CPU_OFFLOAD=1`). The repository also documents that this path loads approximately `95.37 GiB` into the offload process and that most of it is pushed back out to swap during startup.

That documented behavior is structurally consistent with the R21 observation that a ~104.6 GiB prepared Unmovable high-order reservoir collapses during the initial loading interval and that large swap consumption follows. This remains correlation plus implementation-context evidence, not per-page ownership proof.

## Interpretation

R21 now separates three stages:

1. post-stop reclaim/compaction creates a strong initial allocator state;
2. the initial model/PLE loading interval destroys almost all Normal high-order capacity within ~45-56 seconds after compaction;
3. much later, temporary Movable high-order capacity reforms and is drained again near the final RM allocation failure.

Therefore:

- a static pre-start allocator eligibility gate cannot solve this mechanism;
- one-shot post-stop reclaim/compaction cannot preserve the reservoir through startup;
- the late MoE marker is not the collapse onset;
- the highest-value next target is the exact early `06:23:18Z-06:23:40Z` runtime log window and the legacy PLE CPU-offload path.

No production mitigation is accepted from this analysis alone.

## Next read-only evidence

Before designing R22, preserve the exact live R21 container log window around `06:23:18Z-06:23:40Z`, validating that the current container ID is still the R21 candidate. This may expose the PLE initialization line or other allocations immediately preceding the first 50% crossing.
