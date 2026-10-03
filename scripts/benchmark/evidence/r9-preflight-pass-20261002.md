# R9 RM sysmem preflight PASS — 2026-10-02

Classification: **NO TEST / instrumentation preflight PASS**. No model was
started and the R8 `FUNCTIONAL_PASS_HOST_FAIL` result is unchanged.

The live DGX Spark host accepted all four intended dynamic events:

- `nv_alloc_pages` entry/return;
- `nv_alloc_system_pages` entry/return.

The `nv_alloc_pages` entry format materialized all seven intended captured
fields on aarch64:

- `page_count`;
- `page_size`;
- `contiguous`;
- `cache_type`;
- `zeroed`;
- `unencrypted`;
- `node_id` from `$arg8`.

All retained static trace events were present, including compaction begin/end,
direct reclaim begin/end, `mm_page_alloc_extfrag`, `mm_page_alloc`, and
`mm_page_free`.

The trace-cmd smoke test accepted both new narrow filters:

- `mm_page_alloc` with `order == 4`;
- `mm_page_free` with `order == 4`.

It returned `trace-cmd.smoke.rc=0`, followed by:

- `R9_RMSYS_PROBE_PREFLIGHT=PASS`;
- `dynamic_probe_count=4`;
- `order4_page_alloc_trace=YES`;
- `order4_page_free_trace=YES`.

The zero-byte per-CPU smoke payload is expected because the smoke child is only
`true` and does not exercise the RM sysmem allocation path.

The full R9 runner is `scripts/benchmark/run-h6-kv16-rmsys-r9.sh`. It derives
its model-control child from the preserved validated R7 child, keeps the 16 GiB
KV and no-immediate-RM-watchdog semantics, removes the historical monitor CLI
option that failed in R8, and records only order-4 page alloc/free events in
addition to the light allocator trace and the two RM sysmem entry/return pairs.
