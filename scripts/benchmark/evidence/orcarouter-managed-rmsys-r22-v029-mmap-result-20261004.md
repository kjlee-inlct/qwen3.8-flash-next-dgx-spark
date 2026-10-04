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

## R21 versus R22 starting state

R21 post-compaction:

- Normal order-4+: `119743.188 MiB`
- Unmovable order-4+: `104607.312 MiB`
- Movable order-4+: `15083.688 MiB`
- MemFree: `122314.555 MiB`
- SwapFree: `146430.969 MiB`

R22 post-compaction:

- Normal order-4+: `117236.812 MiB`
- Unmovable order-4+: `96999.250 MiB`
- Movable order-4+: `20115.625 MiB`
- MemFree: `122021.215 MiB`
- SwapFree: `146442.938 MiB`

The post-conditioning host states are broadly comparable, although R22 starts with about `7.6 GiB` less Unmovable order-4+ capacity.

## Initial high-order collapse

The first high-order collapse remains catastrophic under mmap.

R21:

- Unmovable 50% crossing: about `45.99 s` after compaction
- Unmovable 10% crossing: about `50.99 s`
- Unmovable 1% crossing: about `56.00 s`
- largest 5 s Unmovable drop: `-74881.938 MiB`
- largest 1 s Normal order-4+ drop: `-26395.125 MiB`

R22:

- Unmovable 50% crossing: about `36.64 s` after compaction
- Unmovable 10% crossing: about `261.64 s`
- Unmovable 1% crossing: about `336.64 s`
- largest 5 s Unmovable drop: `-64215.375 MiB`
- largest 1 s Normal order-4+ drop: `-24882.938 MiB`

Therefore removing the legacy PLE CPU-offload worker does **not** remove the initial catastrophic high-order collapse. The first drain still occurs in the mmap candidate with a similar one-second/five-second scale.

However, the sustained-depletion trajectory changes materially. R21 reaches effectively zero Unmovable order-4+ capacity within about one minute; R22 takes several minutes to reach the same low-capacity regime.

## RM-event state discriminator

R21 RM event:

- Normal order-4+: `146.125 MiB`
- Unmovable order-4+: `0.562 MiB`
- Movable order-4+: `145.500 MiB`
- MemFree: `1675.527 MiB`
- SwapFree: `45146.141 MiB`
- SwapFree delta from post-compaction: `-101284.828 MiB`

R22 RM event:

- Normal order-4+: `3112.125 MiB`
- Unmovable order-4+: `1530.688 MiB`
- Movable order-4+: `1558.438 MiB`
- MemFree: `3847.605 MiB`
- SwapFree: `143279.770 MiB`
- SwapFree delta from post-compaction: `-3163.168 MiB`

This is the strongest discriminator so far.

R21 reaches the RM event after roughly `99 GiB` of additional swap use and with essentially no Unmovable high-order capacity left. R22 reaches the same strict RM failure with very little additional swap use and with about `3.1 GiB` of Normal order-4+ capacity still present, including about `1.53 GiB` Unmovable.

## Updated mechanism model

The evidence now supports a two-layer model:

1. **Legacy PLE CPU-offload strongly amplifies sustained residency/swap pressure and accelerates long-lived high-order depletion.** R22 substantially removes this behavior.
2. **The initial catastrophic high-order collapse and the strict RM fallback do not require that legacy path.** Both still occur in R22.

Therefore legacy PLE CPU-offload is an important pressure amplifier, but it is not the sole or necessary cause of `_memdescAllocInternal` failure.

The remaining RM failure mechanism is broader than PLE residency alone and should be investigated in the common model-loading / NVIDIA RM allocation path.

## Next read-only analysis

No R23 restart is justified yet.

R22 loses about `118 GiB` of MemFree between post-compaction and the RM event while SwapFree drops by only about `3 GiB` and file cache grows by only about `26 GiB`. The compact event analyzer does not account for the remainder of that residency.

The next comparison should quantify, for both R21 and R22 at POST_COMPACT and RM_EVENT:

- AnonPages
- Active(anon) / Inactive(anon)
- Cached / Active(file) / Inactive(file)
- Shmem
- Slab / SReclaimable / SUnreclaim
- KernelStack / PageTables
- Unevictable / Mlocked

That composition gap should be closed before designing another runtime mutation.

No merge or production integration is implied by this result.
