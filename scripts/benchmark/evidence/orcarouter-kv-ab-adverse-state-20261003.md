# OrcaRouter managed KV A/B under adverse allocator state — 2026-10-03

## Classification

| Variant | KV reservation | Functional | Host stability |
| --- | ---: | --- | --- |
| A | 24 GiB | **FAIL** | **FAIL** |
| B | 16 GiB | **PASS** | **PASS** |

This controlled follow-up was run without rebooting after the protected Hybrid failure and the subsequent failed normal OrcaRouter recovery. The intent was to preserve the adverse allocator/lifecycle state as much as practical while changing only the managed OrcaRouter KV reservation from 24 GiB to 16 GiB.

## Common setup

- Target profile: `orcarouter`
- Model: `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`
- Model revision: `c1209bda15a6bbc4c68b585e93d40c0d85f50306`
- Image: `vllm-skinny-tp1:v1`
- Immutable runtime release used by the managed service: `a8aeca47433dc4033b3f1f995eb59023467222ce`
- PLE: CPU offload
- Speculative decode: MTP, k=2
- max model length: 262144
- managed memory protection: enabled
- no reboot between the 24 GiB failure and the 16 GiB follow-up

The 16 GiB value was injected as a temporary service-scoped runtime override. The repository default was not changed before the measurement.

## A — 24 GiB

The preceding post-Hybrid OrcaRouter recovery used the normal 24 GiB manual KV reservation.

Observed result:

- model loading completed and startup progressed through warmup / graph capture
- the candidate never reached managed health/model validation
- kernel emitted seven `_memdescAllocInternal` / `NV_ERR_NO_MEMORY (0x51)` events:
  - 12:44:25 KST: 3 events
  - 12:44:26 KST: 2 events
  - 12:44:30 KST: 2 events
- the memory monitor then crossed protection 1/5 through 5/5
- protected stop at 12:44:49 KST
- swap-free remained about 45.9 GiB at the stop

Strict classification: **FUNCTIONAL FAIL / HOST-STABILITY FAIL**.

## B — 16 GiB

The managed service was started again without rebooting, with a temporary 16 GiB KV override (`17179869184` bytes).

The runtime confirmed the intended value rather than merely inheriting the service environment:

- initial free memory: 114.24 GiB
- reserved KV memory: 16.0 GiB
- GPU KV cache size: 579,086 tokens
- maximum reported concurrency at 262144 tokens: 2.21x

Managed lifecycle result:

- candidate container started at 14:42:14 KST
- health-ready at 14:57:06
- expected served model validated at 14:57:06
- runtime transition committed at 14:57:07
- runtime attestation written at 14:57:07
- `/health` and `/v1/models` both returned HTTP 200 after the required 180-second post-ready soak at 15:00:00
- container remained running through the 15:07 evidence collection
- Docker reported `OOMKilled=false`

Host evidence for the same 14:42:14+ window:

- no `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` kernel event
- no kernel OOM-killer event
- no `PROTECT stopping` event for the B-run
- memory monitor remained healthy throughout startup and after readiness
- after readiness, non-CMA available memory settled around 16.4–16.5 GiB and non-CMA free memory around 10.1–10.5 GiB through the final collection interval
- swap-free settled around 46.1 GiB

Strict classification: **FUNCTIONAL PASS / HOST-STABILITY PASS**.

## Interpretation

This A/B provides direct profile-specific evidence that reducing OrcaRouter KV pressure from 24 GiB to 16 GiB materially changes the fatal boundary under the tested adverse allocator/lifecycle state.

The comparison is stronger than comparing unrelated fresh boots because the machine was not rebooted between the failing 24 GiB recovery and the successful 16 GiB follow-up. The result therefore supports promoting 16 GiB as the managed OrcaRouter resilience default.

Do not over-generalize the result:

- it does not prove that 24 GiB always fails on a fresh allocator state; an earlier mazinb -> OrcaRouter leg passed strictly with the old 24 GiB configuration
- it does not prove that 16 GiB can never encounter an RM sysmem allocation failure in another allocator state
- it does not independently re-prove the exact R9 order-4 rollback / order-0 retry mechanism because no R9 allocation trace was active for this A/B

The supported operational conclusion is narrower: 24 GiB is not robust enough as the managed OrcaRouter default across the observed lifecycle states, while 16 GiB crossed the same adverse-state startup path cleanly and retained substantial post-ready host-memory margin.

## Operational decision

Promote OrcaRouter's managed KV default from 24 GiB to 16 GiB as a resilience mitigation, with regression coverage pinning the value. Keep the change described as mitigation rather than a universal RM fix.

The Hybrid profile remains a separate decision. This OrcaRouter A/B does not by itself justify changing the Hybrid default without a Hybrid-specific controlled run.
