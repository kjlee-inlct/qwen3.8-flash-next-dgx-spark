# OrcaRouter Hybrid R24 — H6 16 GiB RM mitigation discriminator — plan — 2026-10-04

## Purpose

R23 closes the common early approximately 75 GiB startup burst to the observed NVIDIA RM system-memory allocation path (`nv_alloc_pages` / `nv_alloc_system_pages`). R24 therefore does **not** reopen broad ownership tracing. It asks a mitigation question: does the H6 ModelOpt W4A16 hybrid representation reduce the direct RM system-memory burst and remove the later strict RM allocation failure?

## Matched control

The canonical comparison baseline is R22, not the managed Hybrid default.

R22 used the v0.29 PLE-mmap stack with exact QSA/GB10 compatibility, `16 GiB` KV (`17179869184` bytes), max model length `262144`, max sequences `3`, MTP `k=2`, prefix caching disabled, GPU utilization `0.80`, max batched tokens `8192`, and the fixed R21 conditioning harness. It was `VALID_RM_OOM` and its largest five-second unexplained-residual increase was `+75138.043 MiB`.

The managed `orcarouter-hybrid` profile currently defaults to `24 GiB` KV. That default is intentionally **not** used for the first R24 run because it would confound checkpoint/loader representation with an additional 8 GiB KV allocation.

## Candidate

R24 candidate identity is the generated H6 hybrid:

- profile: `orcarouter-hybrid`;
- checkpoint: `qwen3.8-h6-modelopt-w4a16`;
- served identity: `orcarouter-hybrid/Qwen3.8-Flash-Next-Uncensored-NVFP4`;
- image: `vllm-orcarouter-v029:v1`;
- image stability label: `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`;
- KV cache forced to `17179869184` bytes (`16 GiB`);
- PLE mmap enabled, exact QSA enabled, MTP `k=2`;
- max model length `262144`, max sequences `3`, GPU utilization `0.80`;
- prefix caching disabled, FlashInfer autotune disabled;
- required OrcaRouter/H3/H4/H5 parent checkpoint mounts preserved.

The H6 manifest must prove `variant=h6-modelopt-w4a16`, `parent_variant=h5-neutral-input-scale`, `expert_value_source=orcarouter-h4-all`, `input_scale_source=h5-neutral-1.0`, `quant_algo_before=NVFP4`, `quant_algo_after=W4A16_NVFP4`, `safetensor_bytes_changed=0`, and `mtp_tensors_changed=0`.

## Fixed host harness

R24 keeps the R21/R22 conditioning sequence fixed for comparability:

1. require an active, healthy, aged managed OrcaRouter predecessor (`>=2700 s`);
2. start the existing allocator-state collector (`1 s` fast / `5 s` slow);
3. fully stop the managed service;
4. snapshot allocator state;
5. `sync`;
6. one-shot `drop_caches=1`;
7. one-shot `compact_memory`;
8. snapshot the conditioned baseline;
9. start only the H6 candidate on port 8888;
10. apply the same host-memory protection thresholds used by R22;
11. wait for the exact H6 served-model identity and API readiness;
12. preserve the full kernel window, candidate logs, allocator state, and strict RM-event snapshots;
13. stop and preserve the H6 experiment container;
14. restore the managed OrcaRouter service.

No persistent VM tunable is changed. Conditioning remains a measurement harness, not a proposed production mitigation.

## Narrow RM observability only

R23 already rejected the selected UVM boundaries as the owner of the common burst. R24 therefore records only:

- `nv_alloc_pages` entry/return, including `page_count`, `page_size`, `contiguous`, `cache_type`, `zeroed`, `unencrypted`, and `node_id`;
- `nv_alloc_system_pages` entry/return;
- `nvidia_dev_xid` only when the static tracepoint is available.

UVM probes, generic Linux page alloc/free events, compaction/reclaim/extfrag tracepoints, scheduler tracing, function-graph tracing, and all-driver tracing are excluded.

The RM trace uses the same startup arm contract as R23: target start around candidate-request `+20 s`, duration `50 s`. The allocator collector continues for the entire startup, so a shifted H6 burst remains measurable even if it falls outside the narrow RM trace. The analyzer must report whether the independently detected largest five-second burst is fully covered by the trace rather than silently assuming coverage.

Cumulative RM requested bytes remain **activity volume, not exact resident ownership**.

## Primary comparison metrics

R24 compares the H6 candidate against the fixed R22 five-second baseline `75138.043 MiB` using:

- largest one-second and five-second unexplained-residual increase;
- five-second burst ratio and reduction relative to R22;
- node0 Normal free-page delta and global `nr_free_pages` delta over the candidate burst;
- nearest Normal Unmovable/Movable order-4+ state around the burst;
- 64 KiB `nv_alloc_pages` activity, including activity inside the candidate burst when the trace covers it;
- strict `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` count through readiness;
- protected-stop state;
- exact model, image, KV, PLE-mmap, and readiness identity.

Operational burst bands are predeclared only to make the result machine-readable; they are not physical laws:

- candidate/R22 >= 90%: `BURST_UNCHANGED`;
- 75% <= candidate/R22 < 90%: `BURST_PARTIAL_REDUCTION`;
- 25% < candidate/R22 < 75%: `BURST_MATERIAL_REDUCTION`;
- candidate/R22 <= 25%: `BURST_STRONGLY_SUPPRESSED`.

## Interpretation matrix

- Burst materially reduced/suppressed and strict RM OOM disappears: strong H6 host-stability mitigation candidate.
- Burst reduced but strict RM OOM remains: early footprint improved, host-stability gate still fails.
- Burst unchanged but strict RM OOM disappears: H6 changes later failure margin/pressure, not the common early burst.
- Burst unchanged and strict RM OOM remains: H6 does not mitigate the closed RM mechanism.
- Invalid readiness/protection/identity/collector run: preserve evidence; make no mitigation claim.
- Narrow RM trace misses a shifted candidate burst: residual comparison remains usable, but per-burst RM activity is explicitly incomplete.

Functional and host-stability classifications remain separate. Any strict RM OOM in a valid run is HOST-STABILITY FAIL even if the candidate reaches READY.

## Promotion boundary

R24 is a discriminator, not an automatic production promotion. A clean H6 result would justify a subsequent confirmation/repeat and then evaluation of whether the same mitigation can be safely reflected in the managed Hybrid profile. PR #244 remains open; no merge is implied.