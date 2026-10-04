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

## Interpretation

The evidence now supports a two-layer model:

1. **Legacy PLE CPU-offload strongly amplifies sustained residency/swap pressure and accelerates long-lived high-order depletion.** R22 substantially removes this aspect.
2. **The initial catastrophic high-order collapse and the strict RM fallback do not require that legacy path.** Both still occur under the mmap candidate.

Therefore the legacy PLE CPU-offload path is an important pressure amplifier but not the sole or necessary cause of `_memdescAllocInternal` failure.

The remaining RM failure mechanism is now broader than PLE residency alone and should be investigated in the common model-loading / NVIDIA RM allocation path.

## Next evidence

Before another restart, compare the full RM-event memory composition for R21 and R22. R22 loses about 118 GiB of MemFree while SwapFree drops by only about 3 GiB and file cache grows by only about 26 GiB. The remaining memory residency is not explained by the metrics currently emitted by the compact event analyzer.

The read-only `scripts/benchmark/compare-orcarouter-r21-r22-rm-memory.py` helper now quantifies at POST_COMPACT and RM_EVENT:

- AnonPages
- Active(anon) / Inactive(anon)
- Cached / Active(file) / Inactive(file)
- Shmem
- Slab / SReclaimable / SUnreclaim
- KernelStack / PageTables
- Unevictable / Mlocked
- SwapFree

No R23 restart is justified until that composition gap is closed.
