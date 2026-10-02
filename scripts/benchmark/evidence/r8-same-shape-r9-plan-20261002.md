# R8 same-shape result and R9 instrumentation plan — 2026-10-02

## R8 classification remains unchanged

R8 remains **FUNCTIONAL_PASS_HOST_FAIL**. The model reached READY, completed
the 180 s soak, and clean-stopped, while the privileged kernel window recorded
`NV_ERR_NO_MEMORY` and the recovered dynamic trace recorded one real
`nv_alloc_pages` return of `0x51`.

## Same-shape comparator result

Preserved-trace comparator:

`scripts/benchmark/compare-h6-r8-nv-alloc-same-shape.py`

Observed result for the failed partial shape:

- `page_count=409600`
- `requested_page_size=65536`
- `contiguous=0`
- total sysmem at host `PAGE_SIZE=4096`: `1.5625 GiB`
- derived allocation order: `4`
- required order-4 chunks: `25,600`
- `same_shape_calls=1`
- `same_shape_successes=0`
- `same_shape_failures=1`

Therefore R8 contains no second call with the exact three captured shape fields
that can serve as a success comparator. This means the preserved trace cannot
by itself reject a deterministic failure of that **partial** shape.

It still does not support a simple monotonic size threshold: immediately before
the failed 1.5625 GiB order-4 call, a larger 3.125 GiB non-contiguous order-4
request completed successfully. The failure therefore depends on more than
`page_count` magnitude alone.

## Important R8 probe blind spot

The exact NVIDIA 580.178.04 `nv_alloc_pages()` signature is:

- `nv`
- `page_count`
- `page_size`
- `contiguous`
- `cache_type`
- `zeroed`
- `unencrypted`
- `node_id`
- `pte_array`
- `priv_data`

R8 captured only `page_count`, `page_size`, and `contiguous`. The same-shape
comparison is therefore not a full function-input comparison.

This matters because the open-kernel source stores `cache_type`, `zeroed`,
`unencrypted`, and `node_id` in the allocation object. The sysmem path computes
its GFP mask from those flags. In particular, zeroing can add `__GFP_ZERO`, a
NUMA node request can add `__GFP_THISNODE`, and high-order allocations add
`__GFP_COMP`.

Do not describe the R8 comparator as proving that an otherwise identical
allocation always fails.

## Source-grounded R9 target

For `contiguous=0`, `nv_alloc_pages()` dispatches to
`nv_alloc_system_pages()`. The latter computes:

- allocation chunk bytes = `PAGE_SIZE << at->order`;
- allocation chunk count = ceil(`at->num_pages * PAGE_SIZE / chunk_bytes`);

and loops over those chunks. Each chunk uses `NV_GET_FREE_PAGES`, which maps to
Linux `__get_free_pages(gfp_mask, order)` on this source path. If one chunk
returns zero, `nv_alloc_system_pages()` sets `NV_ERR_NO_MEMORY`, rolls back
previously allocated chunks, and returns failure.

For the observed failed R8 call this means up to 25,600 order-4/64 KiB chunk
allocations.

## R9 purpose

R9 should not merely reproduce another RM error. Its purpose is to determine:

1. all allocation-policy inputs for the outer `nv_alloc_pages` request;
2. the exact `nv_alloc_system_pages` interval associated with the outer call;
3. how many order-4 page allocations succeed before the failed return;
4. how many order-4 pages are freed during rollback;
5. the reclaim/compaction/extfrag state during that exact interval.

The narrow trace profile is therefore:

- `nv_alloc_pages` entry/return with `page_count`, `page_size`, `contiguous`,
  `cache_type`, `zeroed`, `unencrypted`, and `node_id`;
- `nv_alloc_system_pages` entry/return;
- `mm_page_alloc` filtered to `order == 4`;
- `mm_page_free` filtered to `order == 4`;
- the existing light compaction/reclaim/extfrag profile.

Order-0 `mm_page_alloc` is intentionally not traced because the immediate
fallback may generate hundreds of thousands of order-0 events. Its success is
already visible at the outer `nv_alloc_pages` return boundary.

PMA, UVM coherent-DMA, and UVM GPU-PMM probes are dropped from R9 because they
were silent throughout R8.

## Tooling gate before any R9 model run

Repository preflight:

`scripts/benchmark/check-h6-r9-rmsys-probes.sh`

The preflight starts no model. It validates:

- aarch64 kprobe fetch through `$arg8` for `node_id`;
- all four RM sysmem dynamic events materialize;
- order-4 `mm_page_alloc` and `mm_page_free` filters are accepted by
  `trace-cmd`;
- retained compaction/reclaim/extfrag events are present;
- the current monitor CLI is compatible and the removed historical
  `--swap-activity-gate-mib` option is identified as absent.

Do not run the full R9 model experiment until this preflight reports
`R9_RMSYS_PROBE_PREFLIGHT=PASS`.
