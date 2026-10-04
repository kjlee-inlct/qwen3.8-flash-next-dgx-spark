# OrcaRouter managed RM-sysmem R9–R22 allocator closure — 2026-10-04

## Purpose

This document is the current canonical summary for the R9–R22 host-memory / NVIDIA RM investigation on the measured DGX Spark stack. It does not replace the per-run evidence files; it records how their conclusions compose and which hypotheses are closed, weakened, or still open.

Strict policy remains unchanged: any confirmed `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` in a valid measured run is HOST-STABILITY FAIL even if the runtime recovers and reaches READY.

## Lower-level mechanism: R9–R11

R9/R10b/R11 established the exact lower-level failure path for NVIDIA driver `580.178.04`.

Observed properties:

- logical RM requests use non-contiguous 64 KiB chunks;
- Linux receives the request as order-4 page allocation;
- R11 directly maps the demand to node0 Normal zone;
- all captured order-4 allocation events use migratetype Unmovable;
- when compatible high-order supply is insufficient, Linux falls back into larger Movable blocks;
- captured extfrag events are Unmovable -> Movable, usually with pageblock ownership change;
- RM can accumulate many order-4 chunks, fail one chunk, roll back previously accumulated same-order pages, return `NV_ERR_NO_MEMORY`, and immediately retry the same logical request at 4 KiB/order 0 successfully.

This excludes several simpler explanations:

- not total-memory exhaustion;
- not swap exhaustion;
- not a fixed logical-request-size threshold;
- not an order-0 allocation failure.

Canonical lower-level evidence:

- `r9-acceptance-gate-20261002.md`
- `orcarouter-managed-rmsys-r10b-02-rm-oom-20261003.md`
- `orcarouter-managed-rmsys-r11-allocator-state-20261003.md`

## Conditioning experiments: R12–R17

R12–R17 tested whether broad Linux VM conditioning could make the failure deterministic or eliminate it.

| Run | Treatment | Result | Interpretation |
|---|---|---|---|
| R12 | one-shot pre-start `compact_memory` | valid, RM OOM x2 | pre-teardown/one-shot compaction insufficient |
| R13 | `compaction_proactiveness=80` during startup | valid, RM OOM x1 | proactive compaction insufficient |
| R14 | `watermark_scale_factor=100` | one clean run | useful observation, not causal proof |
| R15 | paired 10 -> 100 | first fail / second clean | apparent forward effect |
| R16 | reverse 100 -> 10 | first fail / second clean | reverses R15 implication |
| R17 | 10 -> 10 repeat | first fail / second clean | same policy can fail then clean |

R15/R16/R17 show that static watermark policy and aggregate high-order state are not sufficient discriminators. Runtime age / predecessor residency correlated better with first-leg failure, but age is a proxy for evolving host state, not a validated causal threshold.

## Full-stop controls: R18–R20

### R18 — STOP -> compact -> START

- predecessor age: ~319.5 min
- valid clean replacement
- RM OOM: 0
- FUNCTIONAL PASS / HOST-STABILITY PASS

This showed that post-stop compaction can produce a clean run.

### R19 — STOP only

- valid replacement
- RM OOM x5
- FUNCTIONAL PASS / HOST-STABILITY FAIL

Full stop alone is insufficient.

### R20 — STOP -> compact replication

- compaction executed and materially moved buddy capacity;
- candidate was stopped by host memory protection before readiness;
- benchmark treatment classification: INVALID;
- actual candidate startup observation: FUNCTIONAL FAIL / HOST-STABILITY FAIL due protected stop;
- RM OOM count before protected stop: 0, which is not a host-pass classification.

R18/R20 comparison showed that aggregate post-compaction order-4+ gain is insufficient. R20 had more Movable high-order but substantially less Unmovable high-order and about 11 GiB less immediately free RAM, almost entirely represented by reclaimable file cache.

## Page-cache conditioning: R21

R21 tested:

`STOP -> sync -> drop_caches=1 -> compact_memory -> START`

The treatment was effective at changing allocator state:

- Cached: `-8221.984 MiB`
- MemFree: `+8490.176 MiB`
- Normal Unmovable order-4+: `+5766.688 MiB` after the page-cache reclaim step
- final post-compaction Normal order-4+: `119743.188 MiB`
- final post-compaction Unmovable order-4+: `104607.312 MiB`

The replacement reached READY but recorded one strict RM OOM.

Classification:

- R21 = `VALID_RM_OOM`
- FUNCTIONAL PASS
- HOST-STABILITY FAIL

Therefore page-cache reclaim solves part of the R20 protection-conditioning problem but is not sufficient to eliminate the RM fallback.

## R21 collapse timing

R21's prepared high-order state is destroyed near the beginning of startup, not immediately before the final RM event.

Prepared Unmovable order-4+: about `104614 MiB`.

- below 50%: ~46 s after compaction
- below 10%: ~51 s
- effectively zero: ~56 s
- largest 5 s Unmovable drop: `-74881.938 MiB`
- largest 1 s aggregate Normal order-4+ drop: `-26395.125 MiB`

Preserved logs align that interval with main-model startup plus legacy PLE worker spawn, structure initialization/weight discovery, and entry into safetensor loading. The later MoE prepare marker is far too late to be the collapse onset.

This correlation motivated R22, but did not establish PLE-only ownership.

## R22 mmap discriminator

R22 used the existing vLLM v0.29 PLE-mmap candidate with:

- same OrcaRouter checkpoint / served identity;
- 16 GiB KV;
- same R21 conditioning family;
- same protection thresholds.

Observed:

- valid run;
- candidate READY;
- no protected stop;
- one strict RM OOM;
- FUNCTIONAL PASS / HOST-STABILITY FAIL.

The initial catastrophic high-order collapse still occurs under mmap. Therefore the legacy CPU-offload worker is not necessary for the initial collapse or strict RM fallback.

However, mmap materially changes the later trajectory:

- R21 reaches near-zero Unmovable within about one minute;
- R22 reaches 10% only after ~262 s and 1% after ~337 s;
- R21 SwapFree falls by about `101285 MiB` by the RM event;
- R22 SwapFree falls by only about `3163 MiB`.

Thus legacy PLE CPU-offload is a major sustained-pressure/swap amplifier, but not the common lower-level cause.

## Common physical-page accounting closure

Post-compaction -> RM event:

### R21

- MemFree loss: `120639.027 MiB`
- MemAvailable loss: `91942.395 MiB`
- node0 Normal free-page loss: `120609.535 MiB`
- global `nr_free_pages` loss: `120638.160 MiB`
- node0 Normal managed pages: unchanged at `31725420`
- non-overlapping core accounted growth: `31173.844 MiB`
- approximate unexplained physical-page loss: `89465.184 MiB`

### R22

- MemFree loss: `118173.609 MiB`
- MemAvailable loss: `93169.719 MiB`
- node0 Normal free-page loss: `118161.762 MiB`
- global `nr_free_pages` loss: `118174.477 MiB`
- node0 Normal managed pages: unchanged at `31725420`
- non-overlapping core accounted growth: `28172.840 MiB`
- approximate unexplained physical-page loss: `90000.770 MiB`

Full `/proc/meminfo` inspection found no conventional category of comparable scale. CMA, per-CPU, hugetlb/hugepages, vmalloc, anon, slab, shmem, page tables, locked memory, and related fields are individually far too small to explain the roughly 90 GiB residual.

The residual is **not** an exact NVIDIA-owned-page measurement. It is a conservative accounting remainder. Nevertheless, almost the entire free-page loss occurs in node0 Normal with unchanged managed capacity, and the result is strongly consistent with the direct RM/kernel buddy-allocation mechanism already traced in R11.

## Common early allocation burst

The one-second unexplained-residual trajectory provides the strongest R21/R22 common-path result.

### R21

- final residual: `89465.184 MiB`
- 25% crossing: `+43.991 s`
- 50% crossing: `+44.990 s`
- 75% crossing: `+45.991 s`
- largest 1 s increase: `+26754.824 MiB`
- largest 5 s increase: `+75174.387 MiB`

### R22

- final residual: `90000.770 MiB`
- 25% crossing: `+35.638 s`
- 50% crossing: `+36.638 s`
- 75% crossing: `+37.638 s`
- largest 1 s increase: `+24912.121 MiB`
- largest 5 s increase: `+75138.043 MiB`

The largest five-second bursts differ by only `36.344 MiB` out of roughly 75 GiB. About 84% of each final residual is therefore created in a short, common early-startup allocation burst.

At those early crossings SwapFree is essentially unchanged in both runs, so the common burst precedes and is independent of R21's later roughly 100 GiB legacy PLE swap churn.

For R21 the five-second residual burst is aligned with the same interval as the largest Unmovable order-4+ collapse. R22 reproduces the same class of early residual burst without the legacy PLE CPU-offload worker.

## Current causal model

The evidence now supports two layers.

### Layer 1 — common physical allocation path

- shortly after candidate startup, a common model-loading / driver path allocates roughly 75 GiB over about five seconds;
- the selected conventional Linux accounting does not classify that footprint at comparable scale;
- node0 Normal free pages fall correspondingly while managed capacity is unchanged;
- Normal high-order/Unmovable supply collapses in the same early interval;
- the host later reaches the R11 RM order-4 fallback/rollback mechanism.

### Layer 2 — legacy PLE pressure amplifier

- legacy CPU-offload adds about 100 GiB of later swap/residency churn;
- it accelerates sustained high-order depletion;
- mmap removes most of that extra pressure but does not remove Layer 1 or the strict RM OOM.

## Closed / weakened hypotheses

No longer primary explanations:

- total RAM exhaustion;
- swap exhaustion;
- fixed KV/request-size threshold;
- order-0 allocation failure;
- watermark scale as a deterministic fix;
- one-shot compaction as a deterministic fix;
- proactive compaction as a deterministic fix;
- full stop alone;
- aggregate high-order free capacity threshold;
- page cache alone;
- legacy PLE CPU-offload as the sole cause;
- the late MoE prepare marker as collapse onset.

## Open causal question

The remaining high-value question is **ownership and call-path attribution for the common early approximately 75 GiB / five-second physical-page burst**.

The next live trace should be narrow rather than broad:

- focus on approximately the first 30-50 seconds after post-stop compaction / candidate startup;
- retain only the minimum Linux allocator context required to correlate the burst;
- add targeted NVIDIA RM/UVM allocation-boundary observability;
- avoid broad function tracing and broad VM tuning;
- preserve functional and strict host-stability classification separately.

No production reclaim/compaction or mmap promotion is accepted from R9–R22, and no PR merge is implied by this closure.

## Canonical detailed evidence

- `orcarouter-managed-rmsys-r11-allocator-state-20261003.md`
- `orcarouter-managed-rmsys-r12-precompact-20261003.md`
- `orcarouter-managed-rmsys-r13-proactive80-20261003.md`
- `orcarouter-managed-rmsys-r14-watermark-comparison-20261003.md`
- `orcarouter-managed-rmsys-r15-paired-watermark-20261003.md`
- `orcarouter-managed-rmsys-r16-reverse-watermark-20261004.md`
- `orcarouter-managed-rmsys-r17-baseline-repeat-20261004.md`
- `orcarouter-managed-rmsys-r18-poststop-compact-20261004.md`
- `orcarouter-managed-rmsys-r19-stoponly-control-20261004.md`
- `orcarouter-managed-rmsys-r20-poststop-compact-invalid-20261004.md`
- `orcarouter-managed-rmsys-r21-pagecache-reclaim-result-20261004.md`
- `orcarouter-managed-rmsys-r21-collapse-onset-20261004.md`
- `orcarouter-managed-rmsys-r22-v029-mmap-result-20261004.md`
- `orcarouter-managed-rmsys-r21-r22-mmap-comparison-20261004.md`
- `orcarouter-managed-rmsys-r21-r22-unaccounted-trajectory-20261004.md`
