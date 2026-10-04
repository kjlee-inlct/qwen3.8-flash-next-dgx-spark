# OrcaRouter R21 page-cache reclaim + post-stop compaction result — 2026-10-04

## Classification

R21 is **VALID_RM_OOM**.

- functional runtime result: PASS
- strict host-stability result: FAIL
- `run_valid=1`
- `managed_rc=0`
- `collector_rc=0`
- `restart_observed=1`
- `api_ready=1`
- `candidate_started_in_run_window=1`
- `predecessor_age_s=5995.942` (~99.9 min)
- `minimum_predecessor_age_s=2700`
- `rm_oom_count=1`
- `event_snapshot_count=1`

The replacement OrcaRouter runtime reached the normal committed/healthy state and remained active with Docker `OOMKilled=false`, but one strict NVIDIA RM sysmem OOM signature occurred during startup:

`NV_ERR_NO_MEMORY` returned from `_memdescAllocInternal(pMemDesc)`.

Under the existing strict policy, any such signature is HOST-STABILITY FAIL even when the fallback path allows the runtime to finish starting successfully.

## Treatment

The R21 sequence was:

1. aged OrcaRouter predecessor >=2700 s
2. full managed-service stop
3. post-stop allocator snapshot
4. `sync`
5. one-shot `drop_caches=1` to reclaim page cache
6. allocator snapshot
7. one-shot `compact_memory`
8. allocator snapshot
9. start the same immutable managed OrcaRouter 16 GiB release
10. preserve strict allocator/kernel evidence

No persistent VM knob was changed. Final host defaults remained `watermark_scale_factor=10` and `compaction_proactiveness=20`.

## Allocator treatment effect

Before reclaim:

- MemFree: 113793.223 MiB
- Cached: 8424.023 MiB
- Inactive(file): 6371.344 MiB
- Normal order-4+: 102758.938 MiB
- Normal Unmovable order-4+: 100231.875 MiB
- Normal Movable order-4+: 2524.312 MiB

After `drop_caches=1`:

- MemFree: 122278.359 MiB
- Cached: 202.391 MiB
- Inactive(file): 48.227 MiB
- Normal order-4+: 117247.188 MiB
- Normal Unmovable order-4+: 105998.875 MiB
- Normal Movable order-4+: 11208.188 MiB

The page-cache reclaim step changed the state by:

- MemFree: +8490.176 MiB
- Cached: -8221.984 MiB
- Inactive(file): -6323.301 MiB
- Normal order-4+: +14486.062 MiB
- Normal Unmovable order-4+: +5766.688 MiB
- Normal Movable order-4+: +8683.875 MiB

After the subsequent one-shot compaction:

- MemFree: 122314.555 MiB
- Cached: 202.426 MiB
- Inactive(file): 48.480 MiB
- Normal order-4+: 119743.188 MiB
- Normal Unmovable order-4+: 104607.312 MiB
- Normal Movable order-4+: 15083.688 MiB

Relative to the initial post-stop state, reclaim+compact changed:

- MemFree: +8521.332 MiB
- Cached: -8221.598 MiB
- Inactive(file): -6322.863 MiB
- Normal order-4+: +16984.250 MiB
- Normal Unmovable order-4+: +4375.438 MiB
- Normal Movable order-4+: +12559.375 MiB

The compaction sub-step itself increased aggregate/Movable high-order capacity while Unmovable order-4+ decreased by `1391.562 MiB`.

## Relation to R18/R20

R21 post-compaction Normal Unmovable order-4+ was `104607.312 MiB`.

- versus R20 INVALID (`95162.375 MiB`): R21 is about `9444.937 MiB` higher
- versus R18 CLEAN (`106486.812 MiB`): R21 is about `1879.500 MiB` lower

R21 aggregate Normal order-4+ after treatment was `119743.188 MiB`, higher than R18 CLEAN (`112597.438 MiB`), yet R21 still produced one RM OOM.

Therefore aggregate Normal high-order capacity is not a sufficient discriminator, and reclaim + compaction is not sufficient to eliminate the RM order-4 fallback mechanism.

## RM-event allocator collapse

The allocator collector captured one immediate full snapshot at the strict RM OOM event:

- event wall time: `2026-10-04T06:35:00.611065+00:00`
- strict kernel line: `NV_ERR_NO_MEMORY` from `_memdescAllocInternal(pMemDesc)`

Post-compaction state before startup:

- MemAvailable: 121720.500 MiB
- MemFree: 122314.555 MiB
- Cached: 202.426 MiB
- Inactive(file): 48.480 MiB
- SwapFree: 146430.969 MiB
- Normal order-4+: 119743.188 MiB
- Normal Unmovable order-4+: 104607.312 MiB
- Normal Movable order-4+: 15083.688 MiB

RM-event snapshot:

- MemAvailable: 29778.105 MiB
- MemFree: 1675.527 MiB
- Cached: 28796.648 MiB
- Inactive(file): 26643.223 MiB
- SwapFree: 45146.141 MiB
- Normal order-4+: 146.125 MiB
- Normal Unmovable order-4+: 0.562 MiB
- Normal Movable order-4+: 145.500 MiB

Transition:

- MemFree: -120639.027 MiB
- SwapFree: -101284.828 MiB
- Cached: +28594.223 MiB
- Inactive(file): +26594.742 MiB
- Normal order-4+: -119597.062 MiB
- Normal Unmovable order-4+: -104606.750 MiB
- Normal Movable order-4+: -14938.188 MiB

The event snapshot is post-failure and may include rollback-released pages. It is still sufficient to show that the strong pre-start allocator state was not preserved through startup.

## Pre-event trajectory and onset

The preserved 1-second buddy/meminfo samples and 5-second pagetype samples show two phases.

First, the prepared Unmovable reservoir collapsed near startup onset:

- aggregate Normal 50% crossing: `06:23:22.990Z`, `50375.875 MiB`
- Unmovable 50% crossing: `06:23:23.991Z`, `29280.688 MiB`
- Unmovable 10% crossing: `06:23:28.991Z`, `6248.688 MiB`
- aggregate Normal effectively zero: `06:23:29.996Z`, `0.438 MiB`
- Unmovable effectively zero: `06:23:34.003Z`

Largest drains:

- Unmovable: `104162.625 -> 29280.688 MiB`, `-74881.938 MiB` over 5 s
- Movable: `8921.438 -> 6.750 MiB`, `-8914.688 MiB` over 5 s
- aggregate Normal order-4+: `76771.000 -> 50375.875 MiB`, `-26395.125 MiB` over 1 s

The exact preserved container log places this interval across PLE worker spawn, model structure initialization/weight discovery, and entry into safetensor loading. The later `Using MoEPrepareAndFinalizeNoDPEPModular` marker occurs long after Unmovable was already exhausted and is not the collapse onset.

Second, later in startup, Movable high-order capacity transiently re-formed and was drained again near the final RM event.

Focused onset evidence is recorded in `orcarouter-managed-rmsys-r21-collapse-onset-20261004.md`.

## Harness note

The original R21 runner reached healthy runtime but its late kernel-journal finalization initially failed because the sudo timestamp expired during the long startup. The preserved run was finalized post hoc with the recorded run window and live candidate identity. The finalizer verified that the candidate start time falls inside the R21 run window.

The runner now maintains a sudo keepalive through long startup waits.

## Later cross-run closure

R22 subsequently tested the existing v0.29 PLE-mmap path with matched 16 GiB KV and the same conditioning family. R22 also reached READY and also recorded one strict RM OOM, so replacing legacy resident CPU-offload with mmap is not sufficient to eliminate the failure.

Cross-run physical accounting established:

- R21 node0 Normal free loss: `120609.535 MiB`
- R22 node0 Normal free loss: `118161.762 MiB`
- node0 Normal managed pages unchanged in both runs
- R21 `core_unexplained_loss`: `89465.184 MiB`
- R22 `core_unexplained_loss`: `90000.770 MiB`

The one-second trajectory then showed an almost identical common early allocation burst:

- R21 largest 5 s unexplained residual increase: `+75174.387 MiB`
- R22 largest 5 s unexplained residual increase: `+75138.043 MiB`

At those early crossings SwapFree had barely moved, so the roughly 75 GiB common burst is independent of R21's later roughly 100 GiB legacy PLE swap churn.

## Current conclusion

R21 separates multiple effects:

- page-cache conditioning can determine whether startup hits the host protection boundary;
- reclaim/compaction can improve the pre-start allocator state but cannot preserve it through startup;
- the strict RM order-4 failure can still occur after protection problems are avoided;
- the dominant common physical-page burst occurs very early in both legacy and mmap startup stacks.

Therefore neither one-shot reclaim/compaction, a static pre-start threshold, PLE-only explanation, nor broad VM tuning is sufficient as a production mitigation.

The next causal target is ownership of the common early approximately 75 GiB / five-second allocation burst using narrowly scoped RM/UVM observability.

Canonical follow-up evidence:

- `orcarouter-managed-rmsys-r22-v029-mmap-result-20261004.md`
- `orcarouter-managed-rmsys-r21-r22-mmap-comparison-20261004.md`
- `orcarouter-managed-rmsys-r21-r22-unaccounted-trajectory-20261004.md`
