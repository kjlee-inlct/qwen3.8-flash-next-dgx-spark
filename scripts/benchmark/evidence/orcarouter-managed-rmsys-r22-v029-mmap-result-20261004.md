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

R21/R22 allocator comparison further shows that mmap materially reduces sustained swap pressure and delays later high-order depletion, but does not remove the initial catastrophic high-order collapse. R22 still has one strict RM event even though the event occurs with roughly `3112 MiB` Normal order-4+ and `1531 MiB` Unmovable order-4+ remaining.

## Common physical-memory footprint

The detailed R21/R22 `/proc/meminfo` comparison adds a stronger common-path result.

R22 post-compaction -> RM event:

- MemFree: `-118173.609 MiB`
- MemAvailable: `-93169.719 MiB`
- Cached: `+25861.672 MiB`
- AnonPages: `+1650.254 MiB`
- Shmem: `+326.195 MiB`
- Slab: `+441.777 MiB`
- SwapFree: `-3163.168 MiB`

R21 shows a nearly identical MemAvailable reduction (`-91942.395 MiB`) despite a radically different SwapFree reduction (`-101284.828 MiB`).

The evidence therefore separates two effects:

1. a **common roughly 92-93 GiB loss of available physical memory** present in both legacy and mmap startup paths;
2. an additional roughly 100 GiB swap-pressure path associated with the legacy PLE CPU-offload startup.

The common footprint is not explained by any single conventional process/file/slab field measured so far. This is consistent with the already established R11 mechanism of direct NVIDIA RM high-order system-page allocation, but the accounting attribution remains provisional until all `/proc/meminfo` fields are checked.

## Relation to R21

R21 legacy startup:

- reaches near-zero Unmovable capacity within roughly one minute;
- consumes roughly 99 GiB additional swap before the RM event;
- records one strict RM OOM.

R22 mmap startup:

- reproduces the initial catastrophic high-order collapse;
- reaches low Unmovable capacity much more slowly;
- consumes only roughly 3 GiB additional swap before the RM event;
- still records one strict RM OOM.

Therefore legacy PLE CPU-offload is a strong sustained-pressure amplifier, not the sole or necessary cause of the RM failure.

## Next read-only analysis

Use the preserved R21/R22 snapshots with `scripts/benchmark/compare-orcarouter-r21-r22-rm-meminfo-all.py` to inspect every `/proc/meminfo` field, especially CMA, vmalloc, per-CPU, hugepage, page-table, kernel-stack, and locked-memory accounting.

If none contains a tens-of-GiB change matching the common 92-93 GiB unavailable footprint, direct driver-owned pages outside ordinary process/file/slab accounting become the leading closed accounting interpretation.

No R23 restart, merge, or production promotion is implied by R22.
