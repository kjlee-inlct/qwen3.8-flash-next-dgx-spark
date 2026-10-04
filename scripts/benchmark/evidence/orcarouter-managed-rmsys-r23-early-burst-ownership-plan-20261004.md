# OrcaRouter R23 early-burst RM/UVM ownership trace — plan — 2026-10-04

## Classification before execution

R23 is currently **DESIGN / NO TEST**.

It is not a host-VM tuning experiment and it is not a production-mitigation trial.
The unresolved question is ownership of the common early physical-page burst that
appears in both R21 legacy PLE and R22 mmap startup.

## Motivation

R21 and R22 now agree on a much narrower phenomenon than the earlier broad
allocator-conditioning work:

- roughly `75 GiB` of the unexplained physical-page residual forms in about five
  seconds early in startup;
- the final unexplained residual is roughly `89.5–90.0 GiB`;
- nearly the entire corresponding free-page loss occurs in node0 Normal while
  Normal managed capacity remains unchanged;
- the initial burst exists both with legacy PLE CPU-offload and with the v0.29
  PLE-mmap candidate;
- R21's later roughly `100 GiB` swap/residency churn is therefore a separate
  amplifier and not the cause of the common burst;
- R11 already closes the later strict RM failure mechanism to NVIDIA RM
  non-contiguous 64 KiB/order-4 system-memory demand, Linux Normal-zone
  Unmovable pressure, Movable fallback/ownership changes, rollback, and
  immediate 4 KiB/order-0 retry.

The missing evidence is not another allocator-state threshold. It is the
**driver/runtime ownership boundary of the common early burst**.

## Primary question

> During the common early startup burst, which NVIDIA RM/UVM allocation boundary
> is active, on which task/thread, and how does that activity align with the
> approximately 75 GiB physical-page residual formation and model-loading
> milestones?

R23 must narrow that boundary without attempting to trace the entire 10–15
minute startup.

## Runtime under test

Use the current managed OrcaRouter runtime, not the R22 mmap candidate.

Fixed runtime controls:

- current immutable managed OrcaRouter release;
- installed OrcaRouter checkpoint and exact served-model identity;
- managed OrcaRouter KV default: `17179869184` bytes (`16 GiB`);
- no temporary KV override;
- existing host VM defaults unchanged;
- existing memory-protection policy unchanged;
- exact functional and strict host-stability classifications remain separate.

This choice avoids introducing another runtime-stack variable while tracing the
same managed startup family that produced the R21 burst. R22 remains the
cross-stack proof that the burst does not require legacy PLE CPU-offload.

## Conditioning held fixed, not tested

For comparability with the R21/R22 trajectory evidence, preserve the established
pre-start conditioning sequence:

1. require an active, healthy, sufficiently aged managed OrcaRouter predecessor;
2. start the existing allocator-state collector;
3. fully stop the predecessor;
4. `sync`;
5. one-shot `drop_caches=1`;
6. one-shot `compact_memory`;
7. capture the conditioned allocator state;
8. start the same managed OrcaRouter release.

The reclaim/compaction sequence is a **fixed harness condition only**. R23 must
not interpret it as a mitigation or re-test whether it prevents RM OOM. R21
already proves that it does not.

No persistent VM tunable is changed.

## Narrow trace window

Do not keep driver probes recording for the full startup.

Initial live window:

- anchor: managed replacement start request, with the new container ID and
  Docker `StartedAt` preserved separately;
- trace arm delay: approximately `20 s` after replacement start request;
- trace duration: approximately `50 s`;
- effective observation window: approximately startup `+20 s` through `+70 s`.

This intentionally brackets both prior burst timings with margin while remaining
small relative to the full startup. The runner must record wall-clock and
monotonic timestamps for:

- replacement start request;
- new container `StartedAt`;
- trace window begin;
- trace window end;
- readiness/end of measured run.

The analyzer must report actual offsets rather than assuming the requested delay
exactly equals container age.

## Probe set

Reuse the proven R8/R9 dynamic-probe infrastructure. Do not create a new tracing
framework unless the existing tracefs/kprobe mechanism fails preflight.

### Mandatory RM boundary

Capture entry/return for:

1. `nv_alloc_pages`
   - `page_count`
   - `page_size`
   - `contiguous`
   - `cache_type`
   - `zeroed`
   - `unencrypted`
   - `node_id`
   - return status
2. `nv_alloc_system_pages`
   - entry/return
   - retain the `at` pointer only as a correlation identity; do not dereference
     undocumented structure layout in the first R23 run.

These are the highest-value probes because R8/R9/R11 already place the strict
failure mechanism in this RM system-memory path.

### UVM ownership discriminators

Capture low-volume entry/return events for:

3. `nvUvmInterfacePmaAllocPages`
4. `uvm_gpu_dma_alloc`
5. `uvm_mem_alloc`
6. `uvm_pmm_gpu_alloc_kernel`

Use only argument fields whose ABI/signature has already been validated by
preflight or existing R8 definitions. For `uvm_mem_alloc`, event presence,
task/PID, timestamps, and return status are sufficient for the first run if the
argument ABI has not been source-validated.

### Explicitly excluded from the first live trace

Do not enable:

- broad function-graph tracing;
- all NVIDIA/NVIDIA-UVM functions;
- `kmem:mm_page_alloc` / `mm_page_free` across the startup;
- broad compaction/reclaim/extfrag tracing;
- `replayable_faults_isr_bottom_half` unless a later result specifically points
  to a fault-driven path;
- scheduler-wide tracing.

R11 already closes the Linux high-order allocation/fallback mechanics. Repeating
those high-volume events would increase observer effect without answering R23's
ownership question.

`nv_alloc_contig_pages` remains a reserve probe. Add it only if preflight/source
review shows that an uncovered contiguous RM path is necessary to interpret the
first R23 trace.

## Existing infrastructure to reuse

R23 should reuse rather than duplicate:

- `scripts/benchmark/discover-rm-uvm-trace.sh`
  - read-only module/function/event discovery;
- `scripts/benchmark/check-rm-uvm-probe-targets.sh`
  - exact RM/UVM target presence;
- R8 dynamic probe create/verify/cleanup mechanics from
  `scripts/benchmark/run-h6-kv16-rmuvm-r8.sh`;
- R9 full `nv_alloc_pages` policy-argument definition and
  `nv_alloc_system_pages` boundary from
  `scripts/runtime/check-h6-r9-rmsys-probes.sh` and the R9 runner;
- `scripts/benchmark/collect-linux-allocator-state.py`
  - 1-second buddy/meminfo/vmstat/PSI sampling;
  - 5-second pagetype/zone state;
  - wall + `monotonic_ns` timestamps;
  - immediate RM-OOM snapshots;
- the managed R21 control/restore and protection pattern;
- existing R21/R22 residual-trajectory accounting logic for post-run alignment.

Benchmark code should keep using stable top-level compatibility wrappers rather
than importing or calling internal runtime implementation paths directly.

## Trace execution model

The live runner should use a dedicated R23 probe group and preserve the R8/R9
one-control-write-per-command safety pattern.

Required sequence:

1. complete static target discovery/preflight with no model restart;
2. verify dynamic probes can be created, formatted, smoke-recorded, disabled,
   and removed;
3. remove all smoke probes before the live run;
4. execute the established managed preconditioning sequence;
5. create/verify R23 dynamic probes before replacement startup, but leave live
   recording outside the full startup path;
6. start the managed replacement;
7. after the narrow delay, start `trace-cmd record -C mono` with **only** the
   selected R23 dynamic events (plus `nvidia:nvidia_dev_xid` if available);
8. stop trace recording after the fixed narrow duration even if model startup
   continues;
9. keep allocator-state collection and memory protection running until the
   normal readiness/failure endpoint;
10. decode and preserve trace text after the live window closes;
11. collect the strict kernel window and candidate/service logs;
12. restore the managed service/state exactly as existing runners do;
13. run the R23 analyzer from preserved evidence.

The long runner must retain sudo keepalive. Dynamic probes must be disabled and
removed on normal exit, failure, signal, or protection stop.

## Metrics

The R23 analyzer must emit machine-readable labels for at least:

- `trace_window_start_monotonic`
- `trace_window_end_monotonic`
- `trace_window_duration_s`
- actual trace offset from replacement/container start;
- event count for every RM/UVM entry and return probe;
- first/last event timestamp per boundary;
- return-status histogram per boundary;
- task/comm/PID attribution per boundary;
- `nv_alloc_pages` call shapes grouped by:
  - `page_count`
  - `page_size`
  - `contiguous`
  - `node_id`
  - return status;
- cumulative logical requested bytes for `nv_alloc_pages` using
  `page_count * host PAGE_SIZE`;
- order-4 (`page_size=65536`) versus order-0 (`page_size=4096`) request totals;
- unmatched entry/return counts, explicitly marked as expected-capable at trace
  window boundaries rather than silently treated as parser failure;
- UVM discriminator presence/absence during the burst;
- largest 1-second and 5-second unexplained-residual increases from the existing
  collector;
- node0 Normal free delta and global `nr_free_pages` delta across the burst;
- Unmovable/Movable order-4+ trajectory around the burst;
- nearest model-loading log milestones to burst start/end;
- strict RM OOM count and event-snapshot count.

Cumulative RM requested bytes are **activity volume**, not owned resident bytes.
Do not equate the sum of requests with the approximately 75–90 GiB physical
footprint because calls may overlap, retry, roll back, or free memory.

## Interpretation matrix

### A. RM sysmem activity aligns with the burst; UVM boundaries are silent

This would strongly support a direct RM system-memory ownership boundary for the
common burst and deprioritize the selected UVM PMA/DMA/PMM paths for this phase.
It would still not prove the final closed-source RM object owner without a lower
RM-level discriminator.

### B. UVM boundary activity aligns with the burst and feeds RM activity

This would narrow ownership to a UVM -> RM path. The next experiment should add
only the single lower boundary needed to distinguish the active UVM allocation
family, not broad VM tracing.

### C. RM/UVM probes fire but their activity is temporally separate from residual formation

This rejects those boundaries as direct explanations for the common burst and
justifies moving one layer toward the CUDA/RM physical-allocation boundary.

### D. Selected probes are silent during a reproduced 75 GiB burst

This is valid negative evidence, not a failed experiment, provided the trace
preflight and timing window are valid. The next step is to identify one missing
allocation boundary; do not return to watermark/compaction/drop-cache tuning.

### E. Burst is not reproduced

The ownership result is inconclusive. Preserve the run and classify it according
to harness validity and host observations. Do not infer that tracing removed the
problem from one non-reproduction.

## Validity and host classification

Experiment validity and host stability remain independent.

A live run is valid for ownership analysis only if:

- preflight succeeds;
- trace window starts and stops successfully;
- decoded trace is readable;
- candidate/replacement identity and run window are validated;
- allocator collector succeeds;
- protection monitor evidence is preserved;
- startup reaches the normal measured endpoint without harness corruption.

A protection stop may make the ownership experiment incomplete/invalid while
still providing a real FUNCTIONAL/HOST observation.

For any valid measured run, one confirmed `_memdescAllocInternal` /
`NV_ERR_NO_MEMORY` signature means **HOST-STABILITY FAIL** even if the runtime
reaches READY through fallback.

## Observer-effect guard

Record the trace event count and decoded trace size. If event volume is
unexpectedly high, classify observer impact explicitly and do not silently treat
the run as equivalent to R21/R22.

The first live R23 run should prefer missing a secondary Linux detail over
turning the experiment into another broad allocator trace.

## Implementation split

Before a live restart, land and validate in this order:

1. R23 canonical plan (this document);
2. R23 probe-only preflight/helper reusing R8/R9 mechanics;
3. unit tests for probe set, narrow-window constants, cleanup, stable-wrapper
   usage, no persistent VM tuning, strict classification, and protection policy;
4. R23 managed runner with the narrow trace worker;
5. R23 analyzer with window-boundary-aware pairing and allocator/log alignment;
6. shell syntax / ShellCheck / Python compile / focused unit tests / whitespace;
7. CI success;
8. only then issue the copy-paste live execution command.

## Acceptance of the design stage

The design stage is complete when the repository contains a tested runner and
analyzer whose live instrumentation is limited to the defined early window and
selected RM/UVM boundaries, with no broad Linux VM tuning variable added.

Until the live run occurs, R23 remains **NO TEST** and no mitigation or ownership
claim is promoted.
