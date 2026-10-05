# OrcaRouter R22 v0.29 PLE-mmap mechanism discriminator — plan — 2026-10-04

## Motivation

R21 proved that post-stop page-cache reclaim plus compaction can create a very strong allocator state but does not preserve that state through the current managed OrcaRouter startup.

The exact R21 startup log closes the collapse onset to the initial legacy PLE/model-loading interval:

- legacy PLE worker spawn precedes the dominant collapse;
- PLE weight-discovery initialization overlaps the largest measured Unmovable drain;
- main and PLE safetensor loading reach `0/18` at the end of that drain interval;
- Unmovable order-4+ falls from roughly `104 GiB` to roughly `29 GiB` in the steepest five-second interval and reaches zero shortly afterward;
- the final strict RM OOM happens more than eleven minutes later.

The current evidence strongly implicates the resident legacy CPU-offload startup path as a major pressure source, but does not prove page ownership or single-variable causality.

## Existing experimental candidate

The repository already contains an OrcaRouter experimental image based on vLLM v0.29 that keeps the installed OrcaRouter checkpoint but replaces the resident PLE table with NVMe-backed mmap/page-cache lookup.

The mmap path:

- does not spawn the legacy CPU-offload PLE worker;
- drops the large PLE shard tensors from normal weight loading and opens their safetensor ranges as memory maps;
- keeps full-table prewarm disabled;
- uses random-access mmap advice suitable for hashed row lookups;
- includes the compatibility fixes required by this checkpoint and GB10 runtime.

R22 reuses that existing candidate rather than creating another PLE implementation.

## Controlled sequence

R22 is:

1. require an active, healthy, aged managed OrcaRouter predecessor (`>=2700 s`);
2. verify the current managed immutable release still defaults OrcaRouter to `16 GiB` KV;
3. start the existing 1-second / 5-second allocator collector;
4. fully stop the managed predecessor;
5. capture the post-stop allocator state;
6. run `sync`;
7. one-shot `drop_caches=1`;
8. one-shot `compact_memory`;
9. capture the conditioned allocator state;
10. start the experimental v0.29 PLE-mmap OrcaRouter candidate with matched `16 GiB` KV;
11. run the same host-memory protection thresholds used by the managed path;
12. wait for exact served-model readiness;
13. preserve candidate logs, kernel window, strict RM signatures, and allocator event snapshots;
14. stop and preserve the experimental container;
15. restart the managed service after the R22 evidence window has closed.

No persistent VM tuning is changed.

## Fixed controls

R22 pins:

- installed OrcaRouter checkpoint and served-model identity;
- KV cache: `17179869184` bytes (`16 GiB`);
- max model length: `262144`;
- max sequences: `3`;
- MTP: `k=2`;
- prefix caching disabled;
- max batched tokens: `8192`;
- PLE mmap prewarm disabled;
- host VM defaults unchanged;
- memory protection: non-CMA free `2 GiB`, non-CMA available gate `10 GiB`, SwapFree `8 GiB`, five consecutive samples;
- allocator collection: buddy/meminfo every `1 s`, pagetype and slower state every `5 s`;
- strict `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` classification.

## Interpretation limits

R22 is **not** a pure single-variable A/B.

Relative to the current managed runtime, the experimental candidate also changes the vLLM runtime line and includes exact-QSA and GB10 compatibility fixes. Therefore:

- `VALID_CLEAN` would be strong evidence that the alternative mmap startup stack avoids the R21 collapse/RM path;
- it would make legacy resident CPU-offload the leading mechanism target;
- it would **not** prove that mmap alone is the only causal difference;
- it would not justify immediate production promotion.

A later closer A/B would still be required before promotion if R22 is clean.

`VALID_RM_OOM` would show that avoiding the resident PLE table is not sufficient to remove the strict RM fallback under this alternative stack.

`INVALID` (including protected stop or failure to reach the exact served model) remains diagnostic only.

## Acceptance

Functional and host-stability classifications remain separate.

For a valid candidate:

- readiness PASS + zero strict RM signatures -> FUNCTIONAL PASS / HOST-STABILITY PASS;
- readiness PASS + one or more strict RM signatures -> FUNCTIONAL PASS / HOST-STABILITY FAIL.

Any candidate that does not reach readiness under the required protection policy is invalid for clean/strict comparison.

No merge, promotion, or production integration is implied by R22.
