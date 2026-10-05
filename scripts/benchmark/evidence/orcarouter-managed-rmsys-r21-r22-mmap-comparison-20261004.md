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

The RM-event snapshots are **post-failure observations, not exact pre-failure free-pool measurements**. R11 showed that the 64 KiB/order-4 RM path can accumulate many high-order pages, fail one allocation, and then free/roll back the pages already accumulated before returning `NV_ERR_NO_MEMORY`. Therefore some high-order capacity visible in the R22 event snapshot may already be rollback-released capacity. The R22 event value is useful evidence against a simple static aggregate threshold, but it must not be interpreted as proof that the same 3.1/1.53 GiB was continuously free immediately before the failed allocation.

## Detailed RM-event memory composition

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

The most important common signal is that **MemAvailable falls by almost the same amount in both runs**: about 91.9 GiB in R21 and 93.2 GiB in R22. The roughly 25-29 GiB gap between MemFree loss and MemAvailable loss closely tracks file-cache growth, so the common unavailable footprint is not ordinary reclaimable page cache.

R22 also removes almost all of R21's additional swap consumption: the RM-event SwapFree difference is about `+98133.629 MiB` in R22. Therefore the legacy PLE CPU-offload path strongly explains the extra swap churn, but it does **not** explain the roughly 92-93 GiB common loss of available physical memory.

## Full `/proc/meminfo` accounting closure

The complete meminfo-key comparison closes the remaining obvious accounting alternatives.

R22 post-compaction -> RM event:

- `CmaFree`: `0 MiB` change
- `Percpu`: `0 MiB` change
- `Hugetlb`: `0 MiB` change
- hugepage reservation/count fields: unchanged
- `VmallocUsed`: only `+557.672 MiB`
- `PageTables`: only `+16.551 MiB`
- `SecPageTables`: `+159.781 MiB`
- `KernelStack`: only `+3.438 MiB`
- `Unevictable` / `Mlocked`: only about `+0.125 MiB`
- `Slab`: `+441.777 MiB`
- `AnonPages`: `+1650.254 MiB`
- `Shmem`: `+326.195 MiB`
- `FileHugePages`: `+94 MiB`

No CMA, vmalloc, per-CPU, hugepage, page-table, locked-memory, slab, or anonymous-memory field contains a tens-of-GiB change capable of explaining the common ~92-93 GiB MemAvailable loss.

Several meminfo fields overlap by definition (`Cached` with file LRU, `AnonPages` with anon LRU, `Slab` with its reclaimable/unreclaimable children), so they must not be summed as independent buckets. The conclusion is instead based on the direct MemAvailable loss plus the absence of any conventional physical-memory category of comparable scale.

## Physical-page accounting closure

The read-only page-accounting helper closes the host-side free-page correlation using the already captured POST_COMPACT and RM_EVENT snapshots.

R21:

- MemFree loss: `120639.027 MiB`
- node0 Normal-zone free-page loss: `120609.535 MiB`
- global `nr_free_pages` loss: `120638.160 MiB`
- node0 Normal `managed` pages: unchanged at `31725420`
- deliberately non-overlapping core accounted growth: `31173.844 MiB`
- approximate `core_unexplained_loss`: `89465.184 MiB`
- MemAvailable loss: `91942.395 MiB`

R22:

- MemFree loss: `118173.609 MiB`
- node0 Normal-zone free-page loss: `118161.762 MiB`
- global `nr_free_pages` loss: `118174.477 MiB`
- node0 Normal `managed` pages: unchanged at `31725420`
- deliberately non-overlapping core accounted growth: `28172.840 MiB`
- approximate `core_unexplained_loss`: `90000.770 MiB`
- MemAvailable loss: `93169.719 MiB`

The zone and global counters agree closely with MemFree in both runs. Nearly the entire physical free-page loss is therefore observed directly in node0 Normal while the zone's managed-page population remains constant; it is not explained by pages leaving the managed zone or by CMA accounting.

The non-overlapping core accounting includes active/inactive anon/file LRU, Unevictable, Slab, non-slab KReclaimable excess, primary and secondary page tables, and kernel stack. After those conventional resident categories are accounted for, approximately `89.5 GiB` in R21 and `90.0 GiB` in R22 remain unattributed by this accounting model.

`core_unexplained_loss` is **not an exact NVIDIA-owned-page measurement**. It is an approximate residual derived from a deliberately limited, non-overlapping Linux accounting set. However, the residual's near-identical scale in the legacy and mmap runs, together with the direct node0 Normal free-page collapse and unchanged managed-page count, strongly supports a common direct system-page pressure mechanism.

This is consistent with R11, where NVIDIA RM's non-contiguous 64 KiB allocation reached Linux as node0 Normal-zone Unmovable order-4 page demand and rolled back accumulated same-order pages after a failed chunk. The R21/R22 host accounting and the R11 allocator trace are therefore now consistent with the same lower-level mechanism, while exact ownership of every page in the ~90 GiB residual remains unproven.

## Unexplained physical-page trajectory closure

The one-second time-series comparison closes when the common residual forms.

R21 final residual: `89465.184 MiB`.

- 25% crossing: `+43.991 s` after compaction, residual `37154.699 MiB`
- 50% crossing: `+44.990 s`, residual `63909.523 MiB`
- 75% crossing: `+45.991 s`, residual `75885.785 MiB`
- 90% crossing: `+730.991 s`, residual `81927.586 MiB`
- largest 1 s increase: `+26754.824 MiB`
- largest 5 s increase: `+75174.387 MiB`

R22 final residual: `90000.770 MiB`.

- 25% crossing: `+35.638 s` after compaction, residual `39416.078 MiB`
- 50% crossing: `+36.638 s`, residual `64328.199 MiB`
- 75% crossing: `+37.638 s`, residual `75189.867 MiB`
- 90% crossing: `+588.638 s`, residual `81546.207 MiB`
- largest 1 s increase: `+24912.121 MiB`
- largest 5 s increase: `+75138.043 MiB`

The largest five-second increases differ by only `36.344 MiB` out of roughly 75 GiB. About 84% of the final unexplained physical-page residual therefore forms in a short early-startup burst in both runtime stacks.

That burst is independent of the later legacy PLE swap path:

- at the R21 early 75% crossing, SwapFree delta was only about `+3.668 MiB`;
- at the R22 early 75% crossing, SwapFree delta was only about `+0.203 MiB`;
- R21's roughly 100 GiB swap loss accumulated later;
- R22 never develops a comparable swap loss.

The R21 five-second residual burst is aligned with the same `06:23:18.991Z -> 06:23:23.991Z` interval that contains the largest Unmovable order-4+ drop. R22 likewise forms its 25/50/75% residual within a three-second span during the initial mmap high-order collapse.

This makes the short common startup allocation burst, rather than late swap exhaustion or a static pre-start allocator threshold, the highest-value next ownership target.

Focused trajectory evidence is recorded in `orcarouter-managed-rmsys-r21-r22-unaccounted-trajectory-20261004.md`.

## Interpretation

The evidence supports a two-layer model:

1. **A common startup allocation footprint creates a roughly 75 GiB burst in about five seconds and ultimately consumes roughly 90 GiB of physical pages not explained by the selected conventional resident accounting in both legacy and mmap paths.** It is directly visible as node0 Normal free-page loss with unchanged managed capacity and temporally aligned with the initial high-order collapse. This is strongly consistent with the direct NVIDIA RM/kernel page-allocation behavior observed in R11.
2. **Legacy PLE CPU-offload adds a separate roughly 100 GiB swap/residency pressure path.** R22 substantially removes this sustained pressure and slows later high-order depletion, but the common allocation footprint and strict RM fallback remain.

Therefore legacy PLE CPU-offload is an important pressure amplifier but not the sole or necessary cause of `_memdescAllocInternal` failure.

Further page-cache, watermark, compaction, or swap tuning is no longer the primary diagnostic direction.

## Current next step

No R23 restart has been justified solely from broad host-pressure tuning.

The next live experiment should target ownership of the common early allocation burst. The useful observation window is the short startup interval that covers approximately the first `30-50 s` after post-stop compaction/candidate start, rather than the entire long model startup.

The next trace should add only the minimum NVIDIA RM/UVM observability needed to identify which common model-loading/RM boundary is responsible for the approximately 75 GiB five-second physical-page burst. Exact attribution remains the open causal question.

No production reclaim/compaction or mmap promotion is accepted from R21/R22.