# OrcaRouter -> Hybrid final managed return — 2026-10-03

## Status

**FUNCTIONAL FAIL / HOST-STABILITY FAIL**

This is the final managed return leg of the live profile-switch matrix, from the committed OrcaRouter runtime back to `orcarouter-hybrid`.

The candidate did not reach health readiness. Startup was stopped by the memory-protection policy after an NVIDIA RM `NV_ERR_NO_MEMORY (0x51)` event and a five-sample low-memory sequence.

## Provenance

- collection window start: `2026-10-03T11:21:18+09:00`;
- Hybrid candidate start: `2026-10-03T11:23:44+09:00`;
- target profile: `orcarouter-hybrid`;
- served-model target: `orcarouter-hybrid/Qwen3.8-Flash-Next-Uncensored-NVFP4`;
- generated checkpoint: `local/orcarouter-mazinb-h6-w4a16`;
- image: `vllm-orcarouter-v029:v1`;
- PLE: mmap;
- MTP speculative decode: k=2;
- exact QSA enabled;
- max model length: 262144;
- max sequences: 3;
- GPU utilization: 0.80;
- manual KV reservation: 24 GiB (`25769803776` bytes);
- memory protection: enabled.

The H6 chain was validated before runtime startup with base `c1209bda15a6bbc4c68b585e93d40c0d85f50306`, overlay `f2c21eb3d2ff5f24c208ea7e3afba65e2e70f83f`, and final `h6-modelopt-w4a16`.

## Startup result

The candidate progressed through model loading, compilation, warmup, KV creation, and graph capture. vLLM reported:

- model loading: 79.41 GiB;
- manual KV reservation: 24.0 GiB;
- KV capacity: 867,889 tokens;
- maximum concurrency at 262,144 tokens/request: 3.31x.

However, the candidate never reached the managed `health-ready` or `model-list-validated` phases.

The service readiness loop reached 720 seconds and then reported:

- candidate stopped by memory protection during startup;
- previous OrcaRouter container restored but left stopped;
- runtime transition aborted by memory protection and returned to idle.

Therefore there was no runtime commit, no runtime attestation, and no post-ready soak for the Hybrid candidate.

## RM and protection evidence

At `11:35:55 KST`, the kernel recorded:

`_memdescAllocInternal` -> `NV_ERR_NO_MEMORY (0x51)`.

The monitor then observed:

- 11:35:57: protection 1/5, non-CMA available 8,389 MiB, non-CMA free 1,684 MiB;
- 11:35:59: margin temporarily recovered, non-CMA available 10,600 MiB;
- 11:36:09: protection 1/5, non-CMA available 8,159 MiB, non-CMA free 1,709 MiB;
- 11:36:11: protection 2/5, non-CMA available 8,011 MiB, non-CMA free 1,558 MiB;
- 11:36:13: protection 3/5, non-CMA available 7,669 MiB, non-CMA free 1,213 MiB;
- 11:36:15: protection 4/5, non-CMA available 7,459 MiB, non-CMA free 1,004 MiB;
- 11:36:17: protection 5/5, non-CMA available 7,870 MiB, non-CMA free 1,194 MiB;
- 11:36:17: `PROTECT stopping qwen38-flash-next gracefully to preserve host stability`.

Swap was not exhausted. Swap-free remained roughly 143 GiB during the decisive protection sequence.

This is therefore not a Linux OOM-killer classification and not a swap-exhaustion failure. It is an RM allocation failure followed by the repository's intentional host-protection stop.

## Recovery state

After the protected abort:

- update transition: idle;
- runtime transition: idle;
- profile-switch transition: idle;
- managed service: inactive/dead;
- previous OrcaRouter container restored as the canonical container but left stopped;
- restored OrcaRouter container: exit 0, `OOMKilled=false`.

The restored container metadata must not be attributed to the failed Hybrid candidate. The candidate was removed as part of the protected rollback path.

## Classification

### Functional

**FAIL**

The Hybrid candidate never reached health readiness, never validated the served-model list, never committed, and never completed a post-ready soak.

### Host stability

**FAIL** under the current strict policy.

The candidate window contains both:

1. NVIDIA RM `_memdescAllocInternal` / `NV_ERR_NO_MEMORY (0x51)`; and
2. an actual five-sample memory-protection stop.

The optional `RECOVERABLE_RM_SYSMEM_FALLBACK` exception cannot apply because the candidate did not recover to READY and the protection policy intervened.

## Interpretation

This final return reproduces the operational Hybrid failure boundary after a clean managed mazinb -> OrcaRouter leg had just passed strict host-stability acceptance.

The result strengthens the conclusion that the Hybrid 24 GiB runtime remains vulnerable to allocator-state-dependent RM sysmem allocation failure on this GB10 host. It does not independently prove the exact R9 order-4 rollback/order-0 retry mechanism because no R9 allocator trace was captured for this managed return.

The current evidence also continues to rule out swap exhaustion as the immediate cause: approximately 143 GiB of swap remained free when protection triggered.

## Matrix consequence

The final live-switch matrix leg is:

`OrcaRouter -> Hybrid final return: FUNCTIONAL FAIL / HOST-STABILITY FAIL`.

With this result, all planned live-switch legs have an observed outcome. The PR should remain open until an explicit decision is made about acceptance policy, additional mitigation work, or merging the accumulated evidence.