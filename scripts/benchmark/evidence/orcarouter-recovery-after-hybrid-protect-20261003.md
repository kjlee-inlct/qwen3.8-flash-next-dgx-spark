# Managed OrcaRouter recovery after protected Hybrid failure — 2026-10-03

## Classification

- Functional: **FAIL**
- Host stability: **FAIL**
- Kernel RM/OOM evidence: **CONFIRMED**

This recovery attempt is outside the planned live-switch matrix. It was run after the final OrcaRouter -> Hybrid return had already failed and the previous OrcaRouter container had been restored in a stopped state.

## Setup

- Immutable release: `a8aeca47433dc4033b3f1f995eb59023467222ce`
- Target profile: `orcarouter`
- Model: `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`
- Model revision: `c1209bda15a6bbc4c68b585e93d40c0d85f50306`
- Image: `vllm-skinny-tp1:v1`
- PLE: CPU offload
- Speculative decode: MTP, k=2
- max model length: 262144
- managed memory protection: enabled
- preflight: memory=121551 MiB, swapfree=146448 MiB, diskfree=120514 MiB

## Observed startup

The candidate container started successfully and remained active while checkpoint loading, PLE worker initialization, model warmup, compilation, and graph capture progressed.

The runtime later reported:

- model loading: 76.8 GiB
- initial free memory: 114.57 GiB
- manual KV reservation: 24.0 GiB
- KV capacity: 867,889 tokens
- maximum reported concurrency at 262144 tokens: 3.31x

The candidate never reached the managed `health-ready` / `model-list-validated` / transition-commit sequence for this recovery attempt.

After the 780-second readiness checkpoint, the managed path reported:

- `Candidate runtime was stopped by memory protection during startup`
- previous runtime container restored but left stopped
- runtime transition aborted by memory protection
- service deactivated successfully

Subsequent loopback `/health` and `/v1/models` requests failed because port 8888 was no longer serving.

## Memory-protection sequence

The read-only follow-up evidence collection used the same recovery window beginning at 12:30 KST and confirmed the decisive memory sequence.

The runtime monitor first stayed above the protection gate while checkpoint paging consumed substantial swap. Near startup completion:

- 12:44:31: protection sample 1/5 at 9585 MiB non-CMA available and 1903 MiB non-CMA free
- 12:44:33: margin recovered to 11666 MiB non-CMA available
- 12:44:41: protection sample 1/5 at 9790 MiB non-CMA available
- 12:44:43: 2/5
- 12:44:45: 3/5
- 12:44:47: 4/5
- 12:44:49: 5/5 followed by `PROTECT stopping`

Swap-free at the protected stop was about 45.9 GiB, so total swap exhaustion was not the immediate trigger.

## Kernel RM/OOM closure

The sudo-enabled kernel window confirms seven top-level NVIDIA RM allocation failures immediately before the protection sequence:

- three `_memdescAllocInternal` / `NV_ERR_NO_MEMORY (0x51)` events at 12:44:25
- two more at 12:44:26
- two more at 12:44:30

The first managed low-memory protection sample followed at 12:44:31. The timing therefore establishes the same top-level ordering seen in the fatal managed cases: RM sysmem allocation failure first, then managed host-protection pressure, then protected stop.

No R9 allocation trace was active for this recovery attempt. Therefore this result re-confirms the top-level `_memdescAllocInternal` / `NV_ERR_NO_MEMORY (0x51)` signature, but it does **not** re-prove the exact R9 order-4 rollback / order-0 retry mechanism for this OrcaRouter run.

## Host-stability interpretation

This attempt is a strict **HOST-STABILITY FAIL** for two independent reasons:

1. the kernel emitted repeated NVIDIA RM `NV_ERR_NO_MEMORY` failures; and
2. managed memory protection intervened before readiness.

It is also a **FUNCTIONAL FAIL** because the candidate never reached the managed readiness/model-validation/commit sequence and the loopback API was unavailable after abort.

The failure shows that the previously strict-PASS OrcaRouter profile is not guaranteed to recover immediately after the protected Hybrid failure under the allocator/lifecycle state present at this later point. This does not invalidate the earlier mazinb -> OrcaRouter PASS/PASS observation; it demonstrates state-dependent reproducibility.

The result also strengthens the evidence against a Hybrid-only explanation. Both the Hybrid final return and the later normal OrcaRouter recovery used a 24 GiB manual KV reservation and crossed the fatal/protected-stop boundary under adverse allocator state. This remains an observed association, not proof that 24 GiB alone is a sufficient cause across all fresh states.

## Operational state

At evidence collection time the managed service remained inactive/dead and the loopback API was unavailable. The canonical restored container metadata showed `exit=0` and `oom_killed=false`, but that container is the earlier restored OrcaRouter instance, not the failed recovery candidate, so those fields must not be attributed to the failed candidate.

Repeating the same 24 GiB recovery blindly is not justified. The next controlled step should change allocator state or KV pressure deliberately rather than simply retrying the identical failed recovery path.
