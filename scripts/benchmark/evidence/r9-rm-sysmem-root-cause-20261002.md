# R9 RM sysmem root-cause evidence — 2026-10-02

## Classification

R9 is **FUNCTIONAL_PASS_HOST_FAIL** under the existing acceptance policy.

The H6 16 GiB runtime reached READY, completed the configured 180 s post-ready
soak, and clean-stopped with exit code 0 and `OOMKilled=false`. During the same
run the privileged kernel window recorded NVIDIA RM
`NV_ERR_NO_MEMORY (0x51)` from `_memdescAllocInternal`.

The trace itself was preserved successfully. The original inline R9
post-processor stopped on a Python quoting error after trace collection; the
preserved trace was then analyzed by the dedicated R9 recovery analyzer. This
post-processing defect does not invalidate the model run or trace evidence.

## Complete RM sysmem failure capture

The recovered R9 trace contains:

- `lost_event_markers=0`;
- 1,542 paired `nv_alloc_pages` calls;
- 1,487 paired `nv_alloc_system_pages` calls;
- exactly one `nv_alloc_pages` return of `NV_ERR_NO_MEMORY`;
- exactly one `nv_alloc_system_pages` return of `NV_ERR_NO_MEMORY`.

The failed outer `nv_alloc_pages` call was:

- task: `VLLM::Worker`;
- `page_count=4193792`;
- host `PAGE_SIZE=4096`;
- total sysmem request: `15.998047 GiB`;
- requested allocation page size: `65536` bytes;
- derived Linux allocation order: `4`;
- physical allocation chunk size: `64 KiB`;
- expected order-4 chunk count: `262112`;
- `contiguous=0`;
- `cache_type=0`;
- `zeroed=1`;
- `unencrypted=0`;
- `node_id=-1`;
- return: `NV_ERR_NO_MEMORY (0x51)`.

The nested `nv_alloc_system_pages` call also returned `0x51`.

## Order-4 allocation / rollback accounting

Within the failed `nv_alloc_system_pages` interval, attributed to the same
`VLLM::Worker` PID, the trace recorded:

- `order4_page_alloc_events=135366`;
- `order4_page_free_events=135365`;
- `allocated_then_freed_same_pfn=135365`;
- `allocated_not_freed_same_pfn=1`;
- 246 order-4 compaction requests;
- 24 order-4 direct-reclaim begins;
- 15,559 filtered extfrag events;
- no trace loss marker.

The 135,365 same-PFN alloc/free pairs correspond to about 8.262 GiB of
64 KiB chunks that were allocated and then observed being freed during the
failed interval. This is direct evidence of rollback after the high-order
sysmem allocation could not complete.

The analyzer reports `candidate_failed_chunk_index=135367`. Keep the word
**candidate**: the order-4 allocator tracepoints are attributed to the same
PID and nested call interval and are strongly correlated with the RM loop, but
they are still Linux tracepoint observations rather than a direct probe of the
private loop index inside `nv_alloc_system_pages`.

## Immediate same-policy order-0 fallback succeeds

Immediately after the failed outer call, the same `VLLM::Worker` issued
another `nv_alloc_pages` request with:

- the same `page_count=4193792`;
- the same total `15.998047 GiB` request;
- the same `contiguous=0`;
- the same `cache_type=0`;
- the same `zeroed=1`;
- the same `unencrypted=0`;
- the same `node_id=-1`;
- only `requested_page_size` changed from `65536` to `4096`.

That changes the Linux allocation granularity from order 4 / 64 KiB chunks to
order 0 / 4 KiB pages. The retry returned success (`0x0`) and the runtime
continued through engine initialization, READY, soak, and clean shutdown.

This closes the R8 full-input blind spot: in R9 the allocation-policy inputs
were captured and match across the failed order-4 request and the successful
order-0 retry. The relevant differentiator is allocation granularity.

## Root-cause conclusion

The supported **proximate root cause** is:

> NVIDIA RM's Linux sysmem allocation path cannot complete the approximately
> 16 GiB request using 64 KiB physically contiguous order-4 chunks under the
> allocator state present at that moment. `nv_alloc_system_pages` returns
> `NV_ERR_NO_MEMORY`, the already allocated order-4 chunks are rolled back,
> and RM retries the same allocation policy/size with 4 KiB/order-0
> granularity, which succeeds.

This rules out global host-memory exhaustion, swap exhaustion, a fixed manual
KV-capacity threshold, and the request's total byte count as sufficient causes.
It also rules out the previously probed PMA/UVM-DMA/UVM-PMM paths for this
specific episode.

The evidence is consistent with a timing/state-sensitive shortage of usable
high-order physical pages — i.e. fragmentation / buddy/pageblock state under
reclaim and compaction pressure — rather than insufficient total memory.
However, R9 does **not** directly identify the exact zone, migratetype, or buddy
free-list entry that causes the first failed order-4 chunk. Describing a more
specific allocator-internal cause would require another lower-level kernel
allocator experiment and is not required to explain the observed RM fallback.

## Practical status

No further model run is required to establish the failure mechanism above.
A future experiment would only be justified if the project needs to identify
the exact Linux zone/migratetype/buddy-state reason for the failed order-4
chunk, or to validate a mitigation/driver update.

Under the current acceptance policy, Hybrid remains **FUNCTIONAL PASS /
HOST-STABILITY FAIL** because the RM error is still emitted even though the
runtime transparently recovers and remains functional. Keep mazinb blocked
until the project explicitly decides whether this recoverable RM fallback is
acceptable or validates a mitigation that removes the kernel RM error.
