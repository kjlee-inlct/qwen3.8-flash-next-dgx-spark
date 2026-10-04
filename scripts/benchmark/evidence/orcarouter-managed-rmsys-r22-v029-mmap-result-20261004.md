# OrcaRouter R22 v0.29 PLE-mmap result — 2026-10-04

## Scope

R22 is the mechanism-discrimination follow-up to the R21 early allocator-collapse analysis.

It preserves the R21 post-stop conditioning sequence but starts the existing OrcaRouter v0.29 PLE-mmap candidate at the managed `16 GiB` KV setting instead of the legacy resident CPU-offload startup path.

R22 is not a pure single-variable A/B because the candidate also uses the v0.29 runtime line and its existing exact-QSA / GB10 compatibility fixes.

## Run validity

Observed summary:

- `run_valid=1`
- `candidate_start_rc=0`
- `collector_rc=0`
- `wait_ready_rc=0`
- `api_ready=1`
- `protected_stop=0`
- predecessor age: `14282.230 s`
- required minimum predecessor age: `2700 s`
- PLE mode: `mmap`
- KV cache: `17179869184` bytes (`16 GiB`)
- `rm_oom_count=1`
- `event_snapshot_count=1`

Candidate identity:

- image: `vllm-orcarouter-v029:v1`
- image label: `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`

The candidate reached the exact served-model readiness condition under the required memory-protection policy. The experimental container was then stopped and preserved as designed.

The managed OrcaRouter service was subsequently restored and reached READY again; host VM defaults remained `watermark_scale_factor=10` and `compaction_proactiveness=20`.

## Strict RM result

The valid R22 window contains one strict NVIDIA RM sysmem failure:

```text
NVRM: nvCheckOkFailedNoLog: Check failed: Out of memory [NV_ERR_NO_MEMORY] (0x00000051) returned from _memdescAllocInternal(pMemDesc) @ mem_desc.c:1359
```

Timestamp:

- `2026-10-04T19:32:50.919636+09:00`

Therefore:

- R22 result: `VALID_RM_OOM`
- FUNCTIONAL: **PASS**
- HOST-STABILITY: **FAIL** under the current strict policy

The fact that fallback recovered sufficiently for the runtime to become READY does not change the host-stability classification.

## What R22 establishes

R22 rejects the strong form of the previous hypothesis that merely replacing the legacy resident PLE CPU-offload path with the existing v0.29 PLE-mmap startup stack is sufficient to eliminate the strict RM order-4 fallback.

The mmap candidate:

- started successfully;
- was not stopped by host memory protection;
- reached the requested model READY state;
- nevertheless produced the same strict `_memdescAllocInternal / NV_ERR_NO_MEMORY` signature once.

Therefore legacy PLE CPU-offload is not, by itself, a sufficient explanation for the RM fallback.

R21/R22 allocator comparison further shows that mmap materially reduces sustained swap pressure and delays later high-order depletion, but does not remove the initial catastrophic high-order collapse.

The R22 RM-event snapshot contains roughly `3112 MiB` Normal order-4+ and `1531 MiB` Unmovable order-4+. These are **post-failure snapshot values**. R11 already established that the RM order-4 path can accumulate many pages, fail one allocation, and then roll back/free the pages already accumulated before returning `NV_ERR_NO_MEMORY`. Therefore some capacity visible in the event snapshot may already be rollback-released and must not be interpreted as the exact free reservoir immediately before failure.

## Common physical-memory footprint

The completed R21/R22 accounting comparison separates two effects.

R22 post-compaction -> RM event:

- MemFree: `-118173.609 MiB`
- MemAvailable: `-93169.719 MiB`
- Cached: `+25861.672 MiB`
- AnonPages: `+1650.254 MiB`
- Shmem: `+326.195 MiB`
- Slab: `+441.777 MiB`
- SwapFree: `-3163.168 MiB`

R21 shows a nearly identical MemAvailable reduction (`-91942.395 MiB`) despite a radically different SwapFree reduction (`-101284.828 MiB`).

Full `/proc/meminfo` accounting finds no conventional tens-of-GiB bucket that explains the common footprint: CMA, per-CPU, hugetlb/hugepages, vmalloc, page tables, locked memory, slab, anon, and shmem are all individually far too small.

The physical-page accounting further closes the host-side localization for R22:

- node0 Normal free-page loss: `118161.762 MiB`
- global `nr_free_pages` loss: `118174.477 MiB`
- node0 Normal managed pages: unchanged at `31725420`
- non-overlapping core accounted growth: `28172.840 MiB`
- approximate `core_unexplained_loss`: `90000.770 MiB`

R21 produces the same pattern with approximate residual `89465.184 MiB`.

`core_unexplained_loss` is an approximate residual, not an exact NVIDIA-owned-page measurement. However, the near-identical residual scale, direct node0 Normal free-page loss, unchanged managed capacity, and R11's direct RM order-4 trace are strongly consistent with a common direct system-page allocation pressure mechanism.

## Time-series closure

The one-second trajectory shows when the common residual forms.

R22 final residual: `90000.770 MiB`.

- 25% crossing: `+35.638 s` after compaction, residual `39416.078 MiB`
- 50% crossing: `+36.638 s`, residual `64328.199 MiB`
- 75% crossing: `+37.638 s`, residual `75189.867 MiB`
- 90% crossing: `+588.638 s`, residual `81546.207 MiB`
- largest 1 s residual increase: `+24912.121 MiB`
- largest 5 s residual increase: `+75138.043 MiB`

R21 shows an almost identical early five-second residual burst (`+75174.387 MiB`) despite using the legacy CPU-offload path.

At the R22 early 75% crossing, SwapFree had changed by only `+0.203 MiB`; at the R21 early 75% crossing it had changed by only `+3.668 MiB`. The common approximately 75 GiB early burst therefore precedes and is independent of R21's later approximately 100 GiB swap churn.

The early residual burst aligns with the initial catastrophic high-order collapse in both runtime stacks. This is now the highest-value common allocation interval for ownership tracing.

Focused cross-run trajectory evidence is recorded in `orcarouter-managed-rmsys-r21-r22-unaccounted-trajectory-20261004.md`.

## Relation to R21

R21 legacy startup:

- reaches near-zero Unmovable capacity within roughly one minute;
- forms about `75.17 GiB` unexplained residual over its strongest five-second startup burst;
- later consumes roughly 99-100 GiB additional swap before the RM event;
- records one strict RM OOM.

R22 mmap startup:

- reproduces the initial catastrophic high-order collapse;
- forms about `75.14 GiB` unexplained residual over its strongest five-second startup burst;
- reaches low Unmovable capacity much more slowly;
- consumes only roughly 3 GiB additional swap before the RM event;
- still records one strict RM OOM.

Therefore legacy PLE CPU-offload is a strong sustained-pressure amplifier, not the sole or necessary cause of either the common early physical-page burst or the strict RM failure.

## Current conclusion and next step

R22 has completed its intended mechanism-discrimination role.

The broad tuning questions are closed sufficiently for this branch:

- mmap alone does not eliminate strict RM fallback;
- legacy PLE swap pressure is separable from the common startup footprint;
- the common footprint is localized to node0 Normal free-page consumption with unchanged managed capacity;
- approximately 75 GiB of the roughly 90 GiB unexplained residual forms in a common five-second early-startup burst.

No further watermark, compaction, drop-cache, or swap-tuning experiment is the primary next step.

The next live experiment should narrowly trace the common early allocation burst, approximately the first `30-50 s` after post-stop compaction/candidate start, and add only the minimum NVIDIA RM/UVM observability needed to attribute page ownership or the responsible common model-loading boundary.

No merge or production promotion is implied by R22.