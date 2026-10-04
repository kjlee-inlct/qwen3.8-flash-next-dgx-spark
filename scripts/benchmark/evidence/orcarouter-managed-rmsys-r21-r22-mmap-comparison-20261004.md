# OrcaRouter R21 vs R22 allocator comparison — 2026-10-04

## Scope

This comparison uses the completed R21 and R22 evidence only. Both runs were valid, reached the exact served model, avoided host-protection stop, and recorded exactly one strict `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` event.

- R21: current managed OrcaRouter startup with legacy `VLLM_PLE_CPU_OFFLOAD=1` after `sync -> drop_caches=1 -> compact`.
- R22: vLLM v0.29 PLE-mmap experimental startup with the same checkpoint, matched 16 GiB KV, same preconditioning, and the same protection thresholds.

R22 is not a pure single-variable A/B because the candidate also changes the runtime line and includes the repository's existing QSA/GB10 compatibility fixes.

## Strict result

Both runs are:

- FUNCTIONAL PASS
- HOST-STABILITY FAIL
- strict RM OOM count: 1

Therefore replacing the legacy resident PLE CPU-offload path with the existing mmap stack is **not sufficient** to remove the strict RM fallback.

## Post-compaction starting state

R21:

- Normal order-4+: 119743.188 MiB
- Unmovable order-4+: 104607.312 MiB
- Movable order-4+: 15083.688 MiB
- MemFree: 122314.555 MiB
- SwapFree: 146430.969 MiB

R22:

- Normal order-4+: 117236.812 MiB
- Unmovable order-4+: 96999.250 MiB
- Movable order-4+: 20115.625 MiB
- MemFree: 122021.215 MiB
- SwapFree: 146442.938 MiB

The two runs therefore begin from broadly comparable post-conditioning host memory states, although R22 starts with about 7.6 GiB less Unmovable order-4+ capacity.

## Initial catastrophic high-order collapse

R21 prepared Unmovable order-4+ is about 104614 MiB.

- 50% crossing: about 45.99 s after compaction
- 10% crossing: about 50.99 s after compaction
- 1% crossing: about 56.00 s after compaction
- largest 5 s Unmovable drop: -74881.938 MiB
- largest 1 s Normal order-4+ drop: -26395.125 MiB

R22 prepared Unmovable order-4+ is about 96968 MiB.

- 50% crossing: about 36.64 s after compaction
- 10% crossing: about 261.64 s after compaction
- 1% crossing: about 336.64 s after compaction
- largest 5 s Unmovable drop: -64215.375 MiB
- largest 1 s Normal order-4+ drop: -24882.938 MiB

The first high-order collapse therefore still occurs in R22 and remains catastrophic in scale. Removing the legacy PLE CPU-offload worker is **not necessary** for this initial collapse to happen.

However, the post-collapse trajectory is materially different: R21 reaches near-zero Unmovable capacity within about one minute, while R22 takes several minutes to reach the same low-capacity regime.

## RM-event state

R21 RM event:

- Normal order-4+: 146.125 MiB
- Unmovable order-4+: 0.562 MiB
- Movable order-4+: 145.500 MiB
- MemFree: 1675.527 MiB
- SwapFree: 45146.141 MiB
- swap-free delta from post-compaction: -101284.828 MiB

R22 RM event:

- Normal order-4+: 3112.125 MiB
- Unmovable order-4+: 1530.688 MiB
- Movable order-4+: 1558.438 MiB
- MemFree: 3847.605 MiB
- SwapFree: 143279.770 MiB
- swap-free delta from post-compaction: -3163.168 MiB

This is the strongest discriminator so far. R21 reaches the RM event after roughly 99 GiB of additional swap use and with essentially no Unmovable high-order capacity left. R22 reaches the same strict RM failure with very little additional swap use and with about 3.1 GiB of Normal order-4+ capacity still present, including about 1.53 GiB Unmovable.

## Detailed RM-event memory composition

The detailed `/proc/meminfo` comparison shows that R22's large MemFree loss is **not** explained by a correspondingly large anonymous, slab, page-table, or locked-memory increase.

R21 post-compaction -> RM event:

- MemFree: `-120639.027 MiB`
- MemAvailable: `-91942.395 MiB`
- Cached: `+28594.223 MiB`
- AnonPages: `+1307.094 MiB`
- Shmem: `+96.527 MiB`
- Slab: `+856.305 MiB`
- PageTables: `+215.492 MiB`
- SwapFree: `-101284.828 MiB`

R22 post-compaction -> RM event:

- MemFree: `-118173.609 MiB`
- MemAvailable: `-93169.719 MiB`
- Cached: `+25861.672 MiB`
- AnonPages: `+1650.254 MiB`
- Shmem: `+326.195 MiB`
- Slab: `+441.777 MiB`
- PageTables: `+16.551 MiB`
- SwapFree: `-3163.168 MiB`

The most important common signal is that **MemAvailable falls by almost the same amount in both runs**: about 91.9 GiB in R21 and 93.2 GiB in R22. The roughly 25-29 GiB gap between MemFree loss and MemAvailable loss closely tracks the growth of file cache in each run. That means the large common remainder is not ordinary reclaimable page cache.

At the same time, R22 removes almost all of R21's additional swap consumption: the RM-event SwapFree difference is about `+98133.629 MiB` in R22. Therefore the legacy PLE CPU-offload path strongly explains the extra swap churn, but it does **not** explain the roughly 92-93 GiB common loss of available physical memory.

The tracked conventional categories are individually far too small to explain that common unavailable footprint. This is consistent with the R11 mechanism in which NVIDIA RM allocates high-order system pages directly via the kernel page allocator: such driver-owned pages reduce zone free capacity but need not appear as process anonymous memory, file cache, or slab. This is currently the leading accounting interpretation, but it is not yet proven because the full `/proc/meminfo` key set has not been checked for CMA/vmalloc/per-CPU/hugepage-specific changes.

## Interpretation

The evidence now supports a two-layer model:

1. **A common startup allocation footprint consumes roughly 92-93 GiB of available physical memory in both legacy and mmap paths and drives the initial high-order collapse.** Its accounting is not explained by the conventional process/file/slab fields measured so far and is consistent with direct NVIDIA RM/kernel page allocation.
2. **Legacy PLE CPU-offload adds a separate roughly 100 GiB swap/residency pressure path.** R22 substantially removes this sustained pressure and slows later high-order depletion, but the common allocation footprint and strict RM fallback remain.

Therefore legacy PLE CPU-offload is an important pressure amplifier but not the sole or necessary cause of `_memdescAllocInternal` failure.

The remaining RM failure mechanism should now be investigated in the common model-loading / NVIDIA RM allocation path rather than by further page-cache or swap tuning.

## Next evidence

Before another restart, inspect every `/proc/meminfo` key in the already captured POST_COMPACT and RM_EVENT snapshots. The read-only `scripts/benchmark/compare-orcarouter-r21-r22-rm-meminfo-all.py` helper reports all deltas and explicitly highlights:

- `CmaTotal` / `CmaFree`
- `VmallocTotal` / `VmallocUsed` / `VmallocChunk`
- `Percpu`
- `KernelStack` / `PageTables`
- `Unevictable` / `Mlocked`
- hugepage / hugetlb fields
- all remaining meminfo keys sorted by absolute delta

If none of these fields contains a tens-of-GiB increase or free-pool decrease that explains the common 92-93 GiB unavailable footprint, the evidence will strongly support direct driver-owned page allocation outside the ordinary process/file/slab accounting categories.

No R23 restart is justified until that accounting check is closed.
