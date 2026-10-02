# Managed Hybrid -> mazinb activation attempt — 2026-10-02

## Classification

**FUNCTIONAL FAIL / HOST-STABILITY FAIL**

This was a real managed profile activation attempt, not a dry-run and not an
instrumentation/tooling `NO TEST`.

The mazinb candidate did not reach the managed readiness boundary:

- `/health` never became ready before the candidate was stopped;
- runtime-commit attestation was never written;
- the runtime memory monitor entered its protected-stop path during startup;
- the service runner recognized the matching memory-protection stop marker;
- the previous `orcarouter-hybrid` runtime container was restored but left
  stopped; and
- the profile-switch/runtime transactions returned to `idle`.

The retained host evidence now resolves the previously unclassified stop. This
attempt is a host-stability failure under the current strict acceptance policy
because a kernel RM memory-allocation error occurred in the same startup window
and the safety monitor actually stopped the candidate before readiness.

## Attempt configuration

The activation used the already staged pinned mazinb checkpoint:

- repository: `mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4`;
- revision: `f2c21eb3d2ff5f24c208ea7e3afba65e2e70f83f`;
- local size: approximately 173.64 GiB;
- runtime image: `vllm-orcarouter-v029:v1`;
- checkpoint-default config;
- runtime memory monitor enabled;
- low-memory protection enabled;
- managed LAN/API access; and
- managed systemd service enabled.

Before runtime startup, the installer reported:

- all checkpoint files already verified;
- PLE layout detected as BF16/I64;
- MTP tensors detected as BF16;
- release tests PASS (`359 tests`);
- immutable release qualification PASS; and
- candidate profile manifest activation to `mazinb`.

These pre-start results do not imply runtime acceptance.

## Retained lifecycle evidence

The read-only evidence collector was run at 2026-10-02 20:15 KST for the
activation window beginning at 18:00 KST.

Post-rollback lifecycle state was clean:

- update transition: `idle`;
- runtime transition: `idle`;
- profile-switch transition: `idle`;
- systemd `Result=success`;
- `ExecMainStatus=0`; and
- service state `inactive/dead`.

The service journal gives an explicit protected-stop sequence:

- 18:02:54: mazinb candidate started with memory protection enabled;
- 18:16:46: readiness was still waiting at 840/1800 seconds;
- 18:17:16: `Candidate runtime was stopped by memory protection during startup`;
- 18:17:16: the previous runtime container was restored but deliberately left
  stopped after memory protection; and
- 18:17:16: the runtime transition reported `aborted by memory protection`
  with final state `idle`.

This is not an application/container crash classification. The managed
lifecycle intentionally treated the matching protected stop as a successful
service-runner exit so systemd ended `inactive` rather than restarting it as a
failure.

## Runtime progress before the stop

The candidate made substantial startup progress before host protection fired:

- checkpoint load completed; target + MTP model loading reported approximately
  79.42 GiB and 702.1 seconds;
- vLLM reserved the configured 24 GiB KV cache;
- torch compile completed;
- initial profiling/warmup completed;
- target and speculator CUDA graph capture completed;
- engine initialization completed; and
- the API-server process had advanced into final startup configuration.

The final captured runtime lines show graph capture completing at approximately
18:16:45 KST and engine initialization completing shortly afterward. The
candidate was therefore near the API-serving boundary, but managed readiness
was never committed before host protection stopped it.

## Memory-protection evidence

The runtime monitor was active in `protect` mode with the configured floors:

- warning floor: 6 GiB non-CMA available;
- protection free floor: 2 GiB non-CMA free;
- protection available gate: 10 GiB non-CMA available;
- minimum swap-free floor: 8 GiB; and
- five consecutive low samples required before protected stop.

The decisive 2026-10-02 sequence was:

- 18:16:36: first low-memory warning (`protect=1/5`), followed by recovery at
  18:16:38;
- 18:16:54: a new protection sequence began with
  `noncma_available=9311 MiB`, `noncmafree=1812 MiB`;
- 18:16:56: `protect=2/5`;
- 18:16:58: `protect=3/5`;
- 18:17:00: `protect=4/5`;
- 18:17:02: `protect=5/5`, with `noncma_available=8562 MiB` and
  `noncmafree=1053 MiB`; and
- 18:17:02: `PROTECT stopping qwen38-flash-next gracefully to preserve host
  stability`.

Swap was not exhausted. `SwapFree` remained roughly 143 GiB when protection
fired. The protected-stop condition was the low non-CMA free-memory + available
memory gate, not the swap-free floor.

## Kernel RM signal

The collector captured the following kernel event immediately before the
monitor entered the low-memory sequence:

```text
2026-10-02 18:16:33 kernel: NVRM: nvCheckOkFailedNoLog: Check failed: Out of memory [NV_ERR_NO_MEMORY] (0x00000051) returned from _memdescAllocInternal(pMemDesc) @ mem_desc.c:1359
```

This is the same top-level `_memdescAllocInternal` / `NV_ERR_NO_MEMORY (0x51)`
signature seen in the earlier Hybrid H6 R9 investigation.

However, this mazinb run did **not** capture the R9 allocation trace. Therefore
this evidence does not establish that the exact lower-level R9 mechanism
(order-4/64 KiB allocation rollback followed by an order-0/4 KiB retry) was
repeated here. The supported statement is narrower: the same RM error signature
occurred at 18:16:33, followed within seconds by low-memory monitor pressure and
a protected stop. Temporal proximity does not by itself prove the private RM
allocation path was identical.

The collected kernel RM/OOM section contains the `NV_ERR_NO_MEMORY` line above
and does not show an Xid, kernel/process OOM-kill, panic, or fallen-off-bus line
in the retained collector output. That absence does not convert the run into a
host pass because the monitor protected stop is itself a strict-gate failure.

## Docker evidence and scope limitation

After rollback, the canonical container name refers to the restored previous
`orcarouter-hybrid` container, not the removed mazinb candidate. The collector
therefore reports the restored canonical container (`exit=143`,
`OOMKilled=false`) and must not be used to claim `OOMKilled=false` for the
mazinb candidate itself.

The decisive candidate classification instead comes from the matching
memory-protection stop marker, monitor sequence, service-runner journal, and
kernel RM event.

## Why the strict host-stability gate fails

The repository's narrow recoverable-warning gate for the R9 signature requires,
among other conditions:

- API READY;
- successful post-ready soak;
- healthy served-model identity;
- clean runtime stop; and
- **no safety-monitor protected stop**.

This mazinb activation satisfies none of the readiness/soak completion
requirements and explicitly violates the last condition because the safety
monitor stopped the runtime. It therefore cannot be classified as
`HOST-STABILITY WARN / RECOVERABLE_RM_SYSMEM_FALLBACK` even though the same
high-level RM signature appeared.

## Acceptance impact

- Hybrid -> mazinb: **FUNCTIONAL FAIL / HOST-STABILITY FAIL**.
- The failure mode is a managed **memory-protection startup abort**, not an
  unexplained service inactivity or demonstrated vLLM crash.
- mazinb -> OrcaRouter remains pending because mazinb never reached committed
  readiness.
- The rollback restored `orcarouter-hybrid`; that rollback itself must not be
  counted as the still-pending final OrcaRouter -> Hybrid matrix leg.
- The earlier Hybrid H6 R9 mechanism remains independently established. This
  mazinb run re-observed the top-level RM signature but did not re-prove the R9
  lower-level allocation trace.
- PR #244 should remain open while mitigation/acceptance policy and remaining
  profile-switch legs are unresolved.

## Observability follow-up

The post-attempt diagnostics hardening remains useful. Managed readiness failure
handling now prints:

- systemd state/result/exit status;
- recent service journal;
- recent runtime memory-monitor log;
- Docker exit code and `OOMKilled`; and
- recent timestamped container logs.

A separate read-only collector can recover the same lifecycle, monitor, Docker,
and kernel evidence after a run without starting or stopping the model.

## Next mitigation experiment: mazinb KV 24 GiB vs 16 GiB

The failed managed activation does not prove that the configured 24 GiB KV
cache caused the RM event. It does establish a useful temporal sequence: vLLM
reserved 24 GiB for KV, the startup then entered its final warmup/graph-capture
phase, the kernel emitted `NV_ERR_NO_MEMORY`, and the safety monitor protected
the host seconds later. KV size is therefore a bounded mitigation variable worth
isolating before changing the checkpoint, PLE mmap path, or driver.

A guarded operator helper outside the benchmark category now provides a
controlled first-stage experiment:

- A: 24 GiB, the current mazinb default/control;
- B: 16 GiB, the reduced-KV candidate;
- every other mazinb runtime control is pinned to the failed attempt;
- the managed service and canonical container must remain stopped;
- temporary container names and monitor state are isolated from managed state;
- the memory safety monitor remains enabled in protect mode; and
- the helper records container, monitor, and kernel RM/OOM evidence for the
  exact case window.

Run B first. B is accepted as `FUNCTIONAL PASS / HOST-STABILITY PASS` only if
it reaches `/health`, exposes the expected mazinb served-model identity,
completes a 180-second soak, avoids a protected stop, avoids Docker
`OOMKilled=true`, and has no kernel `NV_ERR_NO_MEMORY` in the case window.

Interpretation is intentionally asymmetric:

- if B reproduces the RM/protected-stop failure, 16 GiB is not a sufficient
  mitigation and A need not be rerun;
- if B passes the strict gate, run A with the same helper to remove the
  managed-vs-temporary lifecycle difference and establish a controlled KV-size
  contrast; and
- if B becomes functionally ready but still logs `NV_ERR_NO_MEMORY`, it remains
  a host-stability failure under the current strict policy.

A B-case pass would be mitigation evidence only. It would not retroactively
change this managed activation result and would not qualify the managed
Hybrid -> mazinb leg until the selected KV value is promoted into the managed
profile and that managed transition is rerun successfully.
