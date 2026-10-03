# Managed OrcaRouter recovery after protected Hybrid failure — 2026-10-03

## Classification

- Functional: **FAIL**
- Host stability: **FAIL**
- Kernel RM/OOM evidence: **not collected in this attempt**

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

## Host-stability interpretation

This attempt is a strict **HOST-STABILITY FAIL** because memory protection intervened during startup. A protected stop is disqualifying under the current policy even without a captured kernel RM/OOM line.

The available output from this attempt does **not** contain a sudo-enabled kernel journal collection, so do not claim that `_memdescAllocInternal` / `NV_ERR_NO_MEMORY (0x51)` was re-observed here. A separate read-only evidence collection is required to determine whether the protected stop was accompanied by the same RM signature.

The failure also shows that the previously strict-PASS OrcaRouter profile is not guaranteed to recover immediately after the protected Hybrid failure under the allocator/lifecycle state present at this later point. This does not invalidate the earlier mazinb -> OrcaRouter PASS/PASS observation; it demonstrates state-dependent reproducibility.

## Operational state

At the end of this attempt the managed service is inactive/dead and the loopback API is unavailable. Repeating the same 24 GiB recovery blindly is not justified until kernel evidence is collected and the next mitigation/recovery strategy is selected.
