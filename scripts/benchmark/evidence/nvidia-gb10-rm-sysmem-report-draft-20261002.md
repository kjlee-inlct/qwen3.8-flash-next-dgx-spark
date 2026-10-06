# Draft upstream report: GB10 recoverable RM sysmem high-order allocation failure

Status: **HISTORICAL R9-ERA INTERNAL DRAFT — DO NOT POST UPSTREAM AS CURRENT WITHOUT REFRESHING FROM R23–R32 CLOSURE**.

> This body intentionally preserves the R9-era evidence and then-known unknowns. The
> statement below that the exact Linux buddy/zone/migratetype/pageblock state remained
> unknown was superseded by later repository work: R11 localized node0 Normal-zone
> Unmovable order-4 demand with Movable fallback/pageblock stealing, and R23–R32 closed
> the driver/userspace localization chain further. For any new external report, start
> from `orcarouter-r23-r32-allocation-localization-closure-20261006.md` and the current
> evidence index rather than posting this draft verbatim.

## Environment

- Hardware: single NVIDIA DGX Spark / GB10
- Architecture: aarch64
- Kernel: `6.17.0-1032-nvidia`
- NVIDIA driver: `580.178.04`
- CUDA family: 13.0
- Kernel command line includes `kho=off`
- CMA total: 128 MiB
- Runtime: vLLM v0.29
- Model: `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`
- Model load: 79.41 GiB
- Manual KV cache: 16 GiB
- Max model length: 262,144
- MTP speculative decode: k=2
- PLE mmap enabled
- CUDA graph mode: PIECEWISE

## User-visible/runtime behavior

The runtime reaches READY, serves `/health`, completes a 180 s post-ready soak,
keeps the expected model identity available, and clean-stops with exit code 0
and `OOMKilled=false`.

Despite that successful functional outcome, the kernel logs:

```text
NVRM: nvCheckOkFailedNoLog: Check failed: Out of memory [NV_ERR_NO_MEMORY]
(0x00000051) returned from _memdescAllocInternal(pMemDesc) @ mem_desc.c:1359
```

There is no matched Xid, kernel OOM kill, process OOM kill, panic, or host wedge
in this R9 episode.

## Driver-boundary instrumentation

Dynamic kprobe/kretprobe instrumentation on the exact live host captured:

- `nv_alloc_pages` entry/return including all policy inputs used by this path;
- `nv_alloc_system_pages` entry/return;
- Linux `mm_page_alloc` filtered to order 4;
- Linux `mm_page_free` filtered to order 4;
- compaction, direct-reclaim, and high-order extfrag tracepoints.

The decoded trace contains 4,529,859 lines and reports zero lost-event markers.

## Failing RM Linux-sysmem request

Outer `nv_alloc_pages`:

```text
page_count=4193792
page_size=65536
contiguous=0
cache_type=0
zeroed=1
unencrypted=0
node_id=-1
ret=0x51
```

On a 4 KiB host PAGE_SIZE:

- logical total size: 15.998047 GiB;
- requested allocation granularity: 64 KiB;
- derived Linux allocation order: 4;
- expected order-4 chunk count: 262,112.

The nested `nv_alloc_system_pages` call also returns `0x51`.

Within that exact nested interval the trace records:

```text
order4_page_alloc_events=135366
order4_page_free_events=135365
allocated_then_freed_same_pfn=135365
allocated_not_freed_same_pfn=1
candidate_failed_chunk_index=135367
compaction_try=246
all compaction requests order=4
direct_reclaim_begin=24
all direct reclaim requests order=4
extfrag=15559
```

The 135,365 identical PFN allocate/free matches provide direct evidence that the
failed high-order sysmem request rolled back previously allocated pages.

`candidate_failed_chunk_index=135367` is intentionally described only as a
trace-derived candidate. The instrumentation observes Linux allocator events,
not the NVIDIA private RM loop counter itself.

## Immediate fallback

The next `nv_alloc_pages` call on the same VLLM worker keeps all captured
logical/policy inputs the same:

```text
page_count=4193792
contiguous=0
cache_type=0
zeroed=1
unencrypted=0
node_id=-1
```

and changes only:

```text
page_size=4096
```

That changes the Linux allocation granularity from order 4 to order 0 while
keeping the same 15.998047 GiB logical total size. The retry returns `0x0` and
the runtime then completes startup/soak normally.

## Interpretation

The evidence supports a proximate failure in the RM Linux sysmem path where the
large non-contiguous allocation cannot be completed using 64 KiB/order-4
physically contiguous chunks under the instantaneous Linux allocator state.
RM rolls back the high-order chunks, retries at 4 KiB/order-0 granularity, and
succeeds.

This episode is not explained by global host-memory exhaustion or swap
exhaustion, and the same logical request succeeds immediately after lowering
allocation granularity.

The remaining unknown is the exact Linux buddy/zone/migratetype/pageblock state
that makes the next order-4 allocation unavailable.

## Related public report

NVIDIA/open-gpu-kernel-modules issue #1358 reports the same
`_memdescAllocInternal` / `NV_ERR_NO_MEMORY` signature on GB10 under sustained
unified-memory pressure. That report has a more severe outcome (whole-host
wedge) and therefore should not be conflated with this recoverable episode.
The issue body states reproduction on both driver 580.173.02 and 595.84.

## Reproduction artifacts in this project

Canonical local evidence directory:

```text
/tmp/hybrid-6.17-kv16-rmsys-r9-20261002
```

Important files:

```text
allocator-trace.dat
allocator-trace.txt
kernel-errors-monotonic.txt
container.log
monitor.log
r9-recovery-analysis.txt
```

Repository recovery analyzer:

```text
scripts/benchmark/analyze-h6-r9-rmsys.py
```

The report should not attach the 551 MiB decoded trace by default. Prefer the
binary trace plus a compact analyzer output, and provide the decoded trace only
if requested.

## Project-side acceptance status

Root-cause tracing is complete at the proximate mechanism level. The current
project policy remains strict: this recoverable fallback is still classified as
`FUNCTIONAL PASS / HOST-STABILITY FAIL` until an explicit project decision
introduces the narrow recoverable-warning exception documented separately.
No additional allocator-tracing run is required for this report.
