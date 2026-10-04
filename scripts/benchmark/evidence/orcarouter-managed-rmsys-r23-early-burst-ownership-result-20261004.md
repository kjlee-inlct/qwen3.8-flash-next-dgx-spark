# OrcaRouter R23 early-burst RM/UVM ownership result — 2026-10-04

## Status

**VALID_RM_OOM — FUNCTIONAL PASS / HOST-STABILITY FAIL**

R23 reproduced the common early physical-page burst under the current managed OrcaRouter runtime while tracing only the prevalidated RM/UVM ownership boundaries. The run is valid and the managed service recovered to healthy READY state, but four strict NVIDIA RM `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` events occurred later in the same measured run. Per project policy, any such event in a valid run is HOST-STABILITY FAIL even when fallback recovers.

This result is an ownership diagnostic, not a mitigation result. R21-style `STOP -> sync -> drop_caches=1 -> compact -> START` conditioning was held fixed as the measurement harness; no persistent VM tuning was introduced.

## Run validity

Observed live summary:

- `run_valid=1`
- `managed_rc=0`
- `collector_rc=0`
- `trace_rc=0`
- `trace_report_rc=0`
- `ownership_analyzer_rc=0`
- `trace_window_valid=1`
- `restart_observed=1`
- `release_stable=1`
- `api_ready=1`
- `functional_class=PASS`
- `host_stability_class=FAIL`
- `rm_oom_count=4`
- `event_snapshot_count=4`

The trace window started `20.020147 s` after the managed replacement request and `19.103315 s` after the replacement container `StartedAt`. Actual trace duration was `53.415677 s`.

## Boundary activity

The early trace recorded:

| Boundary | Entry | Return | Return result |
| --- | ---: | ---: | --- |
| `nv_alloc_pages` | 668 | 668 | `0x0:668` |
| `nv_alloc_system_pages` | 599 | 599 | `0x0:599` |
| `nvUvmInterfacePmaAllocPages` | 0 | 0 | none |
| `uvm_gpu_dma_alloc` | 0 | 0 | none |
| `uvm_mem_alloc` | 2 | 2 | `0x0:2` |
| `uvm_pmm_gpu_alloc_kernel` | 0 | 0 | none |

There were no unmatched entry/return pairs for any selected boundary.

`nv_alloc_pages` was active from monotonic `376772.330738` through `376786.301442`. `nv_alloc_system_pages` was active from `376779.500841` through `376786.301442`. The two `uvm_mem_alloc` calls occupied the same broad episode (`376779.632818` through `376786.216950` globally), while the selected UVM PMA, DMA, and PMM boundaries were silent.

Task attribution is dominated by the model worker:

- `nv_alloc_pages`: `VLLM::Worker` PID `1991664` = 1118 entry/return events; `python3` PID `1991878` = 208; `python3` PID `1991480` = 10.
- `nv_alloc_system_pages`: `VLLM::Worker` PID `1991664` = 1054 events; `python3` PID `1991878` = 144.
- `uvm_mem_alloc`: one entry/return pair on `VLLM::Worker` PID `1991664` and one on `python3` PID `1991878`.

## 64 KiB RM activity and the common 5-second burst

The most important R23 observation is the numerical match between RM 64 KiB allocation activity and the independently reconstructed physical-page residual burst.

`nv_alloc_pages` activity over the narrow trace:

- total logical requested bytes: `78,727,696,384` bytes;
- 4 KiB-path logical requested bytes: `3,362,816` bytes;
- 64 KiB/order-4-path logical requested bytes: `78,724,333,568` bytes = **75,077.375 MiB**.

The independently reconstructed largest five-second unexplained-residual increase was:

- `+75,083.652 MiB` from monotonic `376782.427229721` to `376787.427224355`.

Thus the full-trace 64 KiB RM activity volume differs from the five-second residual increase by only **6.277 MiB**, approximately **0.0084%** of the 64 KiB activity volume.

This is exceptionally strong temporal/size consistency with the R11 direct RM system-memory mechanism. However, it is still not legal to equate cumulative requested bytes with resident ownership: the RM request sum is activity volume and can include overlap, retry, rollback, and allocations outside the exact five-second sample window.

## Host allocator movement during the five-second burst

The same five-second interval shows:

- unexplained residual: `+75,083.652 MiB`;
- node0 Normal free: `-77,019.473 MiB`;
- global `nr_free_pages`: `-77,019.848 MiB`;
- nearest slow sample, Normal Unmovable order-4+: `108,160.500 -> 53,121.875 MiB`;
- nearest slow sample, Normal Movable order-4+: `5,878.312 -> 5,108.375 MiB`.

The burst begins essentially at model load: the nearest logged milestone to its start is `Loading model from scratch...` at `+0.713 s`. The nearest logged milestone to the burst end is the `PleOffloadWorker` process at `-0.662 s`.

This independently reproduces the R21/R22 common early ~75 GiB physical-page burst and aligns it with the direct RM allocation episode.

## Strict RM failures are a later phase

All selected `nv_alloc_pages` and `nv_alloc_system_pages` calls inside the early R23 trace returned success. Nevertheless, the measured startup later recorded four strict NVIDIA RM failures:

- `22:55:24.321845 +09:00`
- `22:55:35.163876 +09:00`
- `22:55:36.801342 +09:00`
- `22:55:37.194332 +09:00`

Each was `_memdescAllocInternal(pMemDesc)` returning `NV_ERR_NO_MEMORY`.

Therefore R23 separates two related but distinct phases:

1. an early, successful, approximately 75 GiB RM system-page allocation burst during model loading;
2. later strict RM allocation failures after the prepared high-order state has already been heavily consumed.

The early narrow trace was designed to attribute the common burst, not to capture the later failure episode.

## Live-run ownership interpretation

The live analyzer's coarse discriminator was `RM_AND_SELECTED_UVM_ACTIVE`, because `uvm_mem_alloc` fired twice. At live-run completion this label was factually correct but did not establish whether UVM was the upstream owner of the 75 GiB episode.

The live evidence already showed:

- direct RM system-memory boundaries heavily active around the common burst;
- RM 64 KiB activity almost numerically identical to the common residual growth;
- selected UVM PMA, DMA, and PMM allocation paths completely silent;
- only `uvm_mem_alloc` active, with exactly two calls on tasks that also generated RM activity.

That left one narrow ambiguity: whether those two `uvm_mem_alloc` calls actually bracketed the RM activity or were merely adjacent startup work.

## Post-hoc RM/UVM overlap closure

The preserved R23 trace was then analyzed read-only with `scripts/benchmark/analyze-orcarouter-r23-rm-uvm-overlap.py`. No model restart, service mutation, new trace, VM tuning, or driver change was performed.

The independently determined five-second residual interval contains:

- `515` 64 KiB/order-4-path `nv_alloc_pages` calls;
- `74,537.938 MiB` of 64 KiB RM logical activity;
- `75,083.652 MiB` residual growth;
- `-545.715 MiB` activity-minus-residual difference;
- **`99.273191%`** RM 64 KiB activity/residual ratio.

The two `uvm_mem_alloc` calls were both sub-millisecond:

- `VLLM::Worker` PID `1991664`: `0.000335 s`, before the measured burst window, with zero nested `nv_alloc_pages`, zero nested 64 KiB RM activity, and zero nested `nv_alloc_system_pages` calls;
- `python3` PID `1991878`: `0.000172 s`, overlapping the burst by only `0.000172 s`, again with zero nested `nv_alloc_pages`, zero nested 64 KiB RM activity, and zero nested `nv_alloc_system_pages` calls.

Aggregate `uvm_mem_alloc` coverage is therefore:

- total 64 KiB RM activity: `0.000000%`;
- burst-window 64 KiB RM activity: `0.000000%`;
- `nv_alloc_system_pages` calls: `0.000000%`.

All relevant entry/return pairs remain matched. The post-hoc discriminator is:

`UVM_MEM_ALLOC_ADJACENT_OR_INCIDENTAL_TO_BURST_RM_ACTIVITY`

This closes the remaining selected-UVM ambiguity. `uvm_mem_alloc` is temporally adjacent startup activity, not an observed wrapper around the common RM burst.

## Final R23 ownership conclusion

For the common early startup/model-loading burst, the **primary observed ownership endpoint is the direct NVIDIA RM system-memory path** represented by `nv_alloc_pages` / `nv_alloc_system_pages`.

The selected UVM PMA/DMA/PMM allocation paths are silent, and the only active selected UVM boundary (`uvm_mem_alloc`) contains none of the observed RM calls and covers zero percent of the RM activity.

The same independently selected five-second physical residual window contains `74,537.938 MiB` of 64 KiB RM activity, equal to `99.273191%` of its `75,083.652 MiB` residual growth. Combined with R11's lower-level zone/migratetype trace, the driver-level common-burst mechanism is now sufficiently closed for the project to stop broadening ownership tracing.

Two guards remain:

1. cumulative requested bytes are activity volume, not exact resident ownership;
2. R23 does not identify the original userspace CUDA/vLLM API or caller that triggers the RM demand.

Those guards do not reopen the selected-UVM ownership question.

Canonical closure:

`orcarouter-managed-rmsys-r23-ownership-closure-20261004.md`

## Next engineering direction

Do not start another broad ownership-trace run and do not return to broad watermark, compaction, drop-cache, swap, scheduler, function-graph, or generic page-allocation tracing.

The next phase should move to narrowly controlled mitigation/discriminator work, especially the planned Hybrid/runtime-specific path, while holding runtime identity and the strict host-stability gate fixed.

A mitigation candidate must be judged on whether it:

- reduces or removes the early ~75 GiB RM system-memory burst;
- preserves more node0 Normal high-order supply;
- eliminates later `_memdescAllocInternal` / `NV_ERR_NO_MEMORY`;
- preserves functionality, model identity, KV configuration, and readiness.

Conditioning and mmap behavior remain measurement controls/discriminators rather than accepted production mitigation.

PR #244 remains intentionally open and must not be merged before mitigation/Hybrid closure and explicit merge timing.