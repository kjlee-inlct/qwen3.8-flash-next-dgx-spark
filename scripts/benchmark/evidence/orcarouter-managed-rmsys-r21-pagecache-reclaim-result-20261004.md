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

The page-cache reclaim step therefore changed the state by:

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

Relative to the initial post-stop state, the complete reclaim+compact treatment changed:

- MemFree: +8521.332 MiB
- Cached: -8221.598 MiB
- Inactive(file): -6322.863 MiB
- Normal order-4+: +16984.250 MiB
- Normal Unmovable order-4+: +4375.438 MiB
- Normal Movable order-4+: +12559.375 MiB

The compaction sub-step itself again shifted capacity away from the free-area Unmovable bucket while increasing aggregate and Movable high-order capacity:

- Normal order-4+: +2496.000 MiB
- Normal Unmovable order-4+: -1391.562 MiB
- Normal Movable order-4+: +3875.500 MiB

## Relation to R18/R20

R21 post-compaction Normal Unmovable order-4+ free capacity was 104607.312 MiB.

- versus R20 INVALID: ~95162.375 MiB, R21 is ~9444.937 MiB higher
- versus R18 CLEAN: ~106486.812 MiB, R21 is ~1879.500 MiB lower

R21 aggregate Normal order-4+ after treatment was 119743.188 MiB, higher than R18 CLEAN (~112597.438 MiB), yet R21 still produced one RM OOM.

Therefore:

1. aggregate Normal high-order capacity is not a sufficient discriminator;
2. page-cache reclaim materially improves immediate free memory and high-order allocator state;
3. page-cache reclaim also avoided the separate R20 startup protection boundary in this run;
4. reclaim + compaction is **not sufficient** to eliminate the recoverable RM 64 KiB/order-4 failure mechanism;
5. no production integration is justified from R21.

## RM-event allocator collapse

The allocator collector captured one immediate full snapshot at the strict RM OOM event:

- event wall time: `2026-10-04T06:35:00.611065+00:00`
- strict kernel line: `NV_ERR_NO_MEMORY` from `_memdescAllocInternal(pMemDesc)`

Post-compaction immediately before startup, the prepared state was:

- MemAvailable: 121720.500 MiB
- MemFree: 122314.555 MiB
- Cached: 202.426 MiB
- Inactive(file): 48.480 MiB
- SwapFree: 146430.969 MiB
- Normal exact order-4: 1904.938 MiB
- Normal order-5+: 117838.250 MiB
- Normal order-4+: 119743.188 MiB
- Normal Unmovable order-4+: 104607.312 MiB
- Normal Movable order-4+: 15083.688 MiB

At the RM OOM event, the state had collapsed to:

- MemAvailable: 29778.105 MiB
- MemFree: 1675.527 MiB
- Cached: 28796.648 MiB
- Inactive(file): 26643.223 MiB
- SwapFree: 45146.141 MiB
- Normal exact order-4: 110.625 MiB
- Normal order-5+: 35.500 MiB
- Normal order-4+: 146.125 MiB
- Normal Unmovable order-4+: 0.562 MiB
- Normal Movable order-4+: 145.500 MiB

The startup transition therefore consumed or transformed almost the entire prepared high-order reservoir before RM failed:

- MemFree: -120639.027 MiB
- SwapFree: -101284.828 MiB
- Cached: +28594.223 MiB
- Inactive(file): +26594.742 MiB
- Normal order-4+: -119597.062 MiB
- Normal Unmovable order-4+: -104606.750 MiB
- Normal Movable order-4+: -14938.188 MiB

The directly relevant Unmovable order-4+ reservoir fell from ~104.6 GiB to effectively zero before the strict RM failure. A strong post-stop allocator state is therefore not preserved through OrcaRouter startup, so a static pre-start eligibility threshold cannot by itself guarantee zero RM fallback.

This is consistent with startup demand exhausting/fragmenting the Normal-zone high-order reservoir until the lower-level mechanism identified in R11 is reached. The event snapshot alone does not attribute every consumed page to NVIDIA RM or to a specific vLLM/PLE component; it only proves the system-wide allocator state at the event.

## Harness note

The original R21 runner completed the managed replacement and reached healthy runtime, but its late kernel-journal finalization initially failed because the sudo timestamp expired during the long startup. The preserved run was finalized post hoc with the same recorded run window and the live candidate identity. The finalizer verified that the candidate start time falls inside the R21 run window before classifying the run.

The runner now maintains a sudo keepalive through long startup waits so future evidence finalization does not depend on the interactive sudo timestamp lifetime.

## Next analysis

No new restart is required. The next read-only step is to reconstruct the allocator trajectory immediately before the RM event from the existing 1-second fast samples and 5-second pagetype samples.

Use:

```bash
python3 scripts/benchmark/analyze-orcarouter-r21-rm-trajectory.py \
  --r21 /tmp/orcarouter-managed-rmsys-r21-pagecache-reclaim-compact-01-20261004
```

The trajectory emits samples nearest `-60`, `-30`, `-10`, `-5`, `-1`, and `0` seconds relative to the RM event for Normal buddy capacity, meminfo, and Normal Unmovable/Movable order-4+ capacity. It should distinguish a gradual startup drain from a sharp depletion boundary near the RM event.

Correlate the event wall time with the preserved managed/vLLM logs before designing another runtime mutation. No production integration or new runtime mutation is justified before this read-only trajectory analysis.
