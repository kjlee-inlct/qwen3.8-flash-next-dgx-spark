# Benchmark evidence index

This directory preserves canonical evidence for live DGX Spark runtime, profile-switch, host-stability, and allocator experiments. Historical per-run documents should remain immutable in meaning: later analysis may add links or later-closure notes, but should not rewrite what a run actually observed.

## Current host-stability / RM allocator closure

Start with the R9–R22 allocator closure, then the R23 ownership closure and R24 mitigation result:

- `orcarouter-managed-rmsys-r9-r22-allocator-closure-20261004.md`
- `orcarouter-managed-rmsys-r23-early-burst-ownership-result-20261004.md`
- `orcarouter-managed-rmsys-r23-ownership-closure-20261004.md`
- `orcarouter-hybrid-r24-kv16-rm-mitigation-result-20261005.md`

R21 and R22 first established a common early physical-page allocation burst of about 75 GiB over roughly five seconds. R23 closed the observed ownership endpoint to the direct NVIDIA RM system-memory allocation path (`nv_alloc_pages` / `nv_alloc_system_pages`) rather than the selected UVM allocators. RM requested bytes remain activity volume, not exact resident ownership.

R24 tested H6 ModelOpt W4A16 Hybrid under R22-matched 16 GiB controls and did not mitigate the mechanism: candidate 5 s residual `77937.680 MiB`, same-window order-4 RM activity `77405.938 MiB`, strict RM OOM count `1`, discriminator `H6_NO_RM_MITIGATION_HOST_FAIL`.

Strict classification remains:

> Any confirmed `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` in a valid measured run is HOST-STABILITY FAIL even if fallback recovers and the runtime reaches READY.

## R25 / R25b userspace phase localization

Canonical R25 read-only localization:

- `orcarouter-r25-load-phase-localization-plan-20261005.md`
- `orcarouter-r25-load-phase-localization-result-20261005.md`

R25 aligned the R24 timestamped vLLM log with the RM trace. The order-4 episode lasted about `3.217673 s` and totaled `77405.938 MiB`, while checkpoint filling continued for `522.10 s`. `76846.250 MiB` (`99.276945%`) fell in the coarse model-start→weights-end interval, with only about `559.688 MiB` beginning roughly `0.395 s` before the existing `Loading model from scratch...` marker.

That result made exact `initialize_model()` timing the next highest-information discriminator.

Canonical R25b evidence:

- `orcarouter-r25b-init-model-boundary-plan-20261005.md`
- `orcarouter-r25b-init-model-image-preflight-result-20261005.md`
- `orcarouter-r25b-live-harness-preflight-result-20261005.md`

R25b adds only two INFO markers around vLLM v0.29 `initialize_model(...)`:

- `QWEN38_R25_INIT_MODEL_BEGIN` before the call;
- `QWEN38_R25_INIT_MODEL_END` after return and before `load_weights(...)`.

The marker-only image build/static preflight passed, producing `vllm-orcarouter-v029-r25-init-marker:v1` with image id `sha256:9abb228a5a4c232d20bf38e33a806f15d4bf62ff61128502349fdf39d70e3a9e`, inherited stability label `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`, and diagnostic label `qwen38.r25=init-model-boundary-v1`.

The dedicated live-harness preflight also passed:

- `R25B_IMAGE_PREFLIGHT=PASS`;
- `R24_PREFLIGHT=PASS`;
- `R25B_LIVE_PREFLIGHT=PASS`;
- `R25B_PREFLIGHT_AND_NONMUTATION=PASS`;
- predecessor age `40516.906 s` vs minimum `2700 s`;
- two required direct-RM probe targets available;
- KV fixed at `17179869184` bytes;
- unique container `qwen38-hybrid-r25b-init-marker`;
- unique evidence path `/tmp/orcarouter-hybrid-r25b-init-model-boundary-01-20261005`;
- preserved R24 evidence remains `/tmp/orcarouter-hybrid-r24-kv16-rm-mitigation-01-20261004`;
- managed container ID and `StartedAt` unchanged before/after preflight;
- no model restart, managed-service mutation, or persistent VM tuning during preflight.

The R25b live measured run is therefore the current authorized next experiment. It must be invoked through the dedicated wrapper with explicit `run` mode and `ORCA_R25B_LIVE_ACK=YES`.

The RM trace remains narrow: `nv_alloc_pages`, `nv_alloc_system_pages`, plus optional static NVIDIA Xid if available. Do not broaden back to UVM, generic page allocation, scheduler, function graph, CUDA API blanket tracing, or generic Python profiling.

The post-run analyzer will classify the already-known order-4 episode relative to the exact begin/end markers as one of:

- `RM_ORDER4_WITHIN_INITIALIZE_MODEL`;
- `RM_ORDER4_STARTS_BEFORE_INITIALIZE_MODEL`;
- `RM_ORDER4_EXTENDS_AFTER_INITIALIZE_MODEL`;
- `RM_ORDER4_STRADDLES_INITIALIZE_MODEL`.

If nearly all activity lies inside `initialize_model()`, the next discriminator should target CUDA-side model/parameter/storage construction. H11 then becomes potentially relevant because it changes packed expert parameter construction. H12 remains lower priority because it changes a later post-load wrapping path.

## Historical evidence

All earlier R9–R24 plan/result documents and allocator-conditioning experiments remain preserved in this directory. Conditioning, compaction, mmap, and related host-state manipulations remain measurement controls/discriminators, not accepted production mitigations.

PR #244 remains intentionally open and must not be merged before mitigation/Hybrid closure and explicit merge timing.
