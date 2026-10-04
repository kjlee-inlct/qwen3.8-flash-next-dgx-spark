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

This is exceptionally strong temporal/size consistency with the R11 direct RM system-memory mechanism. However, it is still not legal to equate cumulative requested bytes with resident ownership: the RM request sum is activity volume and can include overlap, retry, rollback, and allocations outside the exact five-second sample window. A post-hoc per-call overlap calculation on the preserved trace is therefore required before making a stronger ownership statement.

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

## Ownership interpretation

The analyzer's coarse discriminator is `RM_AND_SELECTED_UVM_ACTIVE`, because `uvm_mem_alloc` fired twice. That label is factually correct but not yet specific enough to establish whether UVM is the upstream owner of the 75 GiB episode.

The detailed evidence is narrower:

- direct RM system-memory boundaries are heavily active exactly around the common burst;
- the RM 64 KiB activity volume is almost numerically identical to the common five-second residual growth;
- selected UVM PMA, DMA, and PMM allocation paths are completely silent;
- only the higher-level `uvm_mem_alloc` boundary is active, with exactly two calls on the same two tasks that dominate RM activity.

This strongly elevates the direct RM system-memory path from "consistent mechanism" to the leading carrier of the common early burst. The remaining ambiguity is whether the two `uvm_mem_alloc` calls temporally bracket/feed most of that RM activity or are merely adjacent startup allocations.

## Next diagnostic — no new live restart yet

Before any R24 live experiment, perform a read-only post-hoc correlation on the preserved R23 trace:

1. pair each `uvm_mem_alloc` entry/return by PID;
2. pair `nv_alloc_pages` and `nv_alloc_system_pages` calls by PID;
3. measure how many RM calls and how much 64 KiB logical activity occur inside each `uvm_mem_alloc` interval;
4. separately sum 64 KiB RM activity whose entry timestamp falls inside the independently measured five-second residual-burst window;
5. compare that burst-window RM activity with `75,083.652 MiB` residual growth.

Interpretation gate:

- if the two `uvm_mem_alloc` intervals contain nearly all burst-window RM activity, treat UVM `uvm_mem_alloc` as the immediate upstream wrapper and move only one boundary lower/inside that call path if further closure is needed;
- if they contain little of the burst-window RM activity, treat the selected UVM activity as incidental and retain direct RM system memory as the primary ownership path;
- do not return to broad VM tuning or broad tracing in either case.

No production mitigation is accepted from R23 alone, and PR #244 remains intentionally open.