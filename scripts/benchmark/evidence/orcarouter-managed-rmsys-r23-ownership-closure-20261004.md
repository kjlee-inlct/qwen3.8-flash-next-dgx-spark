# OrcaRouter R23 RM ownership closure — 2026-10-04

## Closure status

**EARLY-BURST OWNERSHIP CLOSED TO THE OBSERVED NVIDIA RM SYSTEM-MEMORY PATH**

R23's live narrow trace and the subsequent read-only overlap analysis close the common early ~75 GiB startup burst to the observed NVIDIA RM system-memory allocation path represented by `nv_alloc_pages` / `nv_alloc_system_pages`.

This does **not** mean cumulative RM requested bytes are identical to resident ownership, and it does **not** yet identify the original userspace API/caller that causes the driver to request those pages. It establishes the lowest directly observed carrier/ownership endpoint for the common physical-page burst in the current evidence.

R23 remains **VALID_RM_OOM — FUNCTIONAL PASS / HOST-STABILITY FAIL** because four later `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` events occurred after the early successful burst.

## Live R23 baseline

The valid live trace recorded:

- `nv_alloc_pages`: 668 matched calls, all successful;
- `nv_alloc_system_pages`: 599 matched calls, all successful;
- `nvUvmInterfacePmaAllocPages`: silent;
- `uvm_gpu_dma_alloc`: silent;
- `uvm_mem_alloc`: 2 matched calls, both successful;
- `uvm_pmm_gpu_alloc_kernel`: silent.

The trace had no unmatched selected-boundary entry/return pairs.

The independently reconstructed largest five-second unexplained-residual burst was:

- start: monotonic `376782.427229721`;
- end: monotonic `376787.427224355`;
- residual increase: `+75,083.652 MiB`.

Over the full trace, 64 KiB-path `nv_alloc_pages` logical activity was `75,077.375 MiB`.

## Read-only post-hoc RM/UVM overlap result

The preserved R23 evidence was analyzed without service stop/start, model restart, tracing changes, VM changes, or driver mutation.

Analyzer semantics remain explicit:

- logical bytes are **activity volume, not resident ownership**;
- same-PID temporal nesting is **correlation, not causal proof**.

### Burst-window RM activity

Inside the independently determined five-second residual window:

- 64 KiB/order-4-path `nv_alloc_pages` calls: `515`;
- 64 KiB/order-4-path logical activity: `74,537.938 MiB`;
- residual growth: `75,083.652 MiB`;
- difference: `-545.715 MiB`;
- RM 64 KiB activity / residual ratio: **`99.273191%`**.

This is stronger than the original full-trace size comparison because both quantities are now restricted to the same independently selected five-second burst window.

The remaining ~0.727% difference must not be overinterpreted: allocator sampling boundaries, concurrent allocations, page accounting dimensions not included in the selected residual model, and request/activity semantics can all contribute.

### `uvm_mem_alloc` nesting

Exactly two `uvm_mem_alloc` calls were present:

1. `VLLM::Worker`, PID `1991664`
   - start `376779.632818000`
   - end `376779.633153000`
   - duration `0.000335 s`
   - burst-window overlap `0`
   - nested `nv_alloc_pages` calls `0`
   - nested 64 KiB RM calls `0`
   - nested 64 KiB RM activity `0 MiB`
   - nested `nv_alloc_system_pages` calls `0`

2. `python3`, PID `1991878`
   - start `376786.216778000`
   - end `376786.216950000`
   - duration `0.000172 s`
   - burst-window overlap `0.000172 s`
   - nested `nv_alloc_pages` calls `0`
   - nested 64 KiB RM calls `0`
   - nested 64 KiB RM activity `0 MiB`
   - nested `nv_alloc_system_pages` calls `0`

Aggregate coverage:

- `uvm_mem_alloc` coverage of total 64 KiB RM activity: `0.000000%`;
- `uvm_mem_alloc` coverage of burst-window 64 KiB RM activity: `0.000000%`;
- `uvm_mem_alloc` coverage of `nv_alloc_system_pages` calls: `0.000000%`.

All three analyzed boundaries had zero unmatched entries and zero unmatched returns.

The post-hoc discriminator is therefore:

`UVM_MEM_ALLOC_ADJACENT_OR_INCIDENTAL_TO_BURST_RM_ACTIVITY`

## Ownership conclusion

The evidence now rejects the remaining selected-UVM ambiguity:

1. The selected UVM PMA, DMA, and PMM allocators are completely silent during the measured early episode.
2. `uvm_mem_alloc` fires only twice for sub-millisecond intervals.
3. Neither `uvm_mem_alloc` call contains a single observed `nv_alloc_pages` or `nv_alloc_system_pages` call on the same PID.
4. Its coverage of burst-window 64 KiB RM activity is exactly zero.
5. In contrast, the same five-second physical residual window contains `74,537.938 MiB` of directly observed 64 KiB RM activity, equal to `99.273191%` of the `75,083.652 MiB` residual increase.
6. R11 already establishes how this RM 64 KiB demand reaches node0 Normal as Unmovable order-4 Linux allocation pressure and eventually falls back to order-0 after failure.

Therefore, for the common early startup/model-loading burst, the **primary observed ownership endpoint is the direct NVIDIA RM system-memory allocation path** (`nv_alloc_pages` / `nv_alloc_system_pages`), not any of the selected UVM allocation boundaries.

The phrase "ownership endpoint" is intentional. The evidence does not prove which userspace CUDA/vLLM API originally causes RM to allocate these pages, nor does it prove that every requested byte remains resident. Those are separate questions and are not required to accept the driver-level early-burst closure.

## What is now closed

The following diagnostic branches should be considered closed unless new contradictory evidence appears:

- broad watermark tuning as root cause;
- broad compaction/drop-cache tuning as root cause;
- swap behavior as prerequisite for the common early burst;
- legacy PLE CPU-offload as prerequisite for the common early burst;
- selected UVM PMA/DMA/PMM allocation paths as the owner of the common burst;
- `uvm_mem_alloc` as an immediate wrapper around the common RM burst.

Broad function-graph tracing, scheduler tracing, all-driver tracing, and generic Linux page alloc/free tracing are not justified by the current evidence.

## Next direction

Do **not** start another ownership-trace run merely to broaden instrumentation.

The next engineering phase should shift from ownership discovery to a narrowly controlled mitigation/discriminator that changes the mechanism responsible for the RM system-memory demand while preserving the established runtime identity and strict host-stability gate.

Priority should be given to Hybrid/runtime-specific mitigation work already planned for the project, with each candidate evaluated against:

- whether the early ~75 GiB RM burst is reduced or removed;
- whether node0 Normal high-order depletion is reduced;
- whether later `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` disappears;
- whether functionality, model identity, KV configuration, and readiness remain unchanged.

Conditioning (`drop_caches` / compaction), mmap behavior, or broad VM tuning remain measurement controls or discriminators, not accepted production mitigations.

If later mitigation work needs to identify the originating userspace trigger, instrument only the smallest evidence-driven CUDA/RM call boundary needed for that specific mitigation question. Do not reopen broad UVM ownership tracing solely because userspace attribution remains unknown.

PR #244 remains intentionally open and must not be merged until the planned mitigation/Hybrid closure and explicit merge timing are complete.
