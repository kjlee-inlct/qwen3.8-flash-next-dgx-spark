# R9 recoverable RM sysmem fallback acceptance gate — 2026-10-02

## Current classification

R9 remains **FUNCTIONAL PASS / HOST-STABILITY FAIL** under the current project
policy because the kernel emitted `NV_ERR_NO_MEMORY` from `_memdescAllocInternal`.
The model nevertheless reached READY, completed the configured 180 s soak, and
clean-stopped with exit code 0 and `OOMKilled=false`.

## Mechanism established by R9

The preserved R9 trace captures the complete Linux-sysmem RM boundary:

- one `nv_alloc_pages` return of `0x51`;
- one nested `nv_alloc_system_pages` return of `0x51`;
- failed outer request size: 15.998047 GiB at host `PAGE_SIZE=4096`;
- failed allocation policy: `contiguous=0`, `cache_type=0`, `zeroed=1`,
  `unencrypted=0`, `node_id=-1`;
- failed granularity: 64 KiB / Linux order 4;
- nested failed interval recorded 135,366 order-4 allocation events and
  135,365 order-4 free events;
- 135,365 identical PFNs were observed allocated and then freed, directly
  showing rollback;
- no trace-loss markers were present;
- the immediately following same-thread request kept the same `page_count` and
  all captured allocation-policy inputs, changed only the requested page size
  from 64 KiB/order 4 to 4 KiB/order 0, and returned success.

The trace-derived `candidate_failed_chunk_index=135367` is useful evidence but
must remain a **candidate**, not a claim that the NVIDIA private RM loop index
was observed directly. Linux page-allocation tracepoints are not private RM
loop variables.

## Supported proximate root cause

The supported proximate mechanism is:

> Under the allocator state present at that moment, the NVIDIA RM Linux sysmem
> path could not finish the approximately 16 GiB non-contiguous request using
> 64 KiB/order-4 physically contiguous chunks. RM rolled back the high-order
> allocations and immediately succeeded after retrying the same total request
> and policy at 4 KiB/order-0 granularity.

This is stronger than a generic "memory pressure" explanation. It directly
rules out the following as sufficient causes for this R9 episode:

- global host RAM exhaustion;
- swap exhaustion;
- a fixed manual-KV capacity threshold;
- total requested bytes by themselves;
- PMA, coherent-DMA, or GPU-PMM failure as the observed failing boundary.

The remaining lower-level uncertainty is why the next order-4 chunk was not
available at that instant: exact Linux zone, migratetype, buddy free-list, and
pageblock state were not captured.

## Narrow recoverable-warning gate

Do **not** silently downgrade every `NV_ERR_NO_MEMORY` to a warning. A future
run may be treated as the same recoverable fallback class only when **all** of
the following are true:

1. the matched kernel signal is only the known `_memdescAllocInternal` /
   `NV_ERR_NO_MEMORY (0x51)` signature;
2. there is no Xid, GPU-fallen-off-bus event, kernel OOM kill, process OOM kill,
   panic, or host-liveness loss;
3. the failing RM Linux-sysmem request is followed by a successful lower-order
   retry for the same logical allocation policy/size, or equivalent trace
   evidence establishes successful fallback;
4. the API reaches READY;
5. the configured post-ready soak completes;
6. the model identity endpoint remains healthy;
7. the runtime clean-stops with exit code 0 and `OOMKilled=false`;
8. the safety monitor does not trigger a protected stop.

If any condition fails, keep **HOST-STABILITY FAIL**.

## Project decision gate

The evidence is sufficient to stop root-cause tracing at the current level.
There are now two legitimate project choices:

- **Strict gate:** retain `FUNCTIONAL PASS / HOST-STABILITY FAIL` and keep the
  mazinb profile leg blocked until a software/driver/kernel mitigation removes
  the RM error.
- **Documented recoverable exception:** introduce a distinct
  `HOST-STABILITY WARN / RECOVERABLE_RM_SYSMEM_FALLBACK` class using the narrow
  conditions above, and permit the remaining profile-switch matrix to proceed
  while the upstream driver issue remains tracked separately.

The repository must not change from the strict gate to the recoverable
exception implicitly. That is an acceptance-policy decision, not an inference
from one successful runtime fallback.

## External context checked on 2026-10-02

NVIDIA's DGX OS 7.6 release information lists the Spark-specific qualified GPU
driver as 580.173.02 (Canonical signed), while 580.178.04 is the current generic
DGX OS 7 driver version for other listed architectures.

A public NVIDIA open-gpu-kernel-modules issue (#1358) reports the same
`_memdescAllocInternal` / `NV_ERR_NO_MEMORY` signature on GB10 under unified
memory pressure and states reproduction across 580.173.02 and 595.84. That
report progresses to whole-host wedge and therefore is **not** treated as the
same severity as R9, but it is evidence that a simple downgrade from
580.178.04 to 580.173.02 should not be assumed to remove the signature.

Accordingly, do not alter a working kernel/driver stack solely on the
assumption that 580.173.02 is a guaranteed fix. Any driver/kernel A/B should be
an explicit mitigation-validation experiment with rollback instructions and
its own acceptance criteria.
