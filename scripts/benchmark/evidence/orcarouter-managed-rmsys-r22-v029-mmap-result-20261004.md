# OrcaRouter R22 v0.29 PLE-mmap result — 2026-10-04

## Scope

R22 is the mechanism-discrimination follow-up to the R21 early allocator-collapse analysis.

It preserves the R21 post-stop conditioning sequence but starts the existing OrcaRouter v0.29 PLE-mmap candidate at the managed `16 GiB` KV setting instead of the legacy resident CPU-offload startup path.

R22 is not a pure single-variable A/B because the candidate also uses the v0.29 runtime line and its existing exact-QSA / GB10 compatibility fixes.

## Run validity

Observed summary:

- `run_valid=1`
- `candidate_start_rc=0`
- `collector_rc=0`
- `wait_ready_rc=0`
- `api_ready=1`
- `protected_stop=0`
- predecessor age: `14282.230 s`
- required minimum predecessor age: `2700 s`
- PLE mode: `mmap`
- KV cache: `17179869184` bytes (`16 GiB`)
- `rm_oom_count=1`
- `event_snapshot_count=1`

Candidate identity:

- image: `vllm-orcarouter-v029:v1`
- image label: `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`

The candidate reached the exact served-model readiness condition under the required memory-protection policy. The experimental container was then stopped and preserved as designed.

The managed OrcaRouter service was subsequently restored and reached READY again; host VM defaults remained `watermark_scale_factor=10` and `compaction_proactiveness=20`.

## Strict RM result

The valid R22 window contains one strict NVIDIA RM sysmem failure:

```text
NVRM: nvCheckOkFailedNoLog: Check failed: Out of memory [NV_ERR_NO_MEMORY] (0x00000051) returned from _memdescAllocInternal(pMemDesc) @ mem_desc.c:1359
```

Timestamp:

- `2026-10-04T19:32:50.919636+09:00`

Therefore:

- R22 result: `VALID_RM_OOM`
- FUNCTIONAL: **PASS**
- HOST-STABILITY: **FAIL** under the current strict policy

The fact that fallback recovered sufficiently for the runtime to become READY does not change the host-stability classification.

## What R22 establishes

R22 rejects the strong form of the previous hypothesis that merely replacing the legacy resident PLE CPU-offload path with the existing v0.29 PLE-mmap startup stack is sufficient to eliminate the strict RM order-4 fallback.

The mmap candidate:

- started successfully;
- was not stopped by host memory protection;
- reached the requested model READY state;
- nevertheless produced the same strict `_memdescAllocInternal / NV_ERR_NO_MEMORY` signature once.

Therefore legacy PLE CPU-offload is not, by itself, a sufficient explanation for the RM fallback.

This does **not** establish that mmap has no allocator benefit. R22 may still materially change the timing, depth, or migratetype composition of the early high-order collapse. That distinction is the next required analysis.

## Relation to R21

R21 legacy startup:

- page-cache reclaim + compaction produced a strong initial allocator state;
- Normal Unmovable order-4+ was roughly `104 GiB` after conditioning;
- the dominant collapse occurred during the first model / legacy-PLE loading interval;
- Unmovable order-4+ reached effectively zero within roughly 56 seconds after compaction;
- one strict RM OOM occurred later;
- result: `VALID_RM_OOM`.

R22 mmap startup:

- uses the same one-shot page-cache reclaim + compaction conditioning family;
- uses the same `16 GiB` KV target as managed OrcaRouter;
- reaches READY without protection;
- still records one strict RM OOM;
- result: `VALID_RM_OOM`.

The remaining high-value discriminator is therefore whether R22 reproduces the R21 **early allocator-collapse shape**.

## Next read-only analysis

Use the preserved R22 allocator evidence to locate:

- initial post-compaction Normal order-4+ and Unmovable order-4+ capacity;
- first 50%, 10%, and 1% threshold crossings;
- first crossing below 1 GiB / 100 MiB / 10 MiB;
- largest consecutive 5-second Unmovable and Movable drops;
- largest consecutive 1-second aggregate Normal order-4+ drop;
- relation of those crossings to the mmap candidate startup log;
- allocator state at the single R22 RM event.

The key comparison is not only `rm_oom_count` (R21 and R22 are both one) but whether mmap changes the early collapse from the R21 pattern.

## Current interpretation boundary

Accepted conclusions:

- static pre-start allocator strength is insufficient;
- page-cache reclaim + compaction is insufficient to eliminate RM fallback;
- legacy CPU-offload removal through the existing v0.29 mmap stack is also insufficient to eliminate RM fallback;
- host protection did not trigger in this R22 run;
- the strict RM failure mechanism persists somewhere in the alternative mmap startup stack.

Not yet accepted:

- that mmap and legacy startup have identical allocator trajectories;
- that PLE is irrelevant to allocator pressure;
- that the main model-loading path alone causes the failure;
- any production promotion or mmap cutover.

No merge or production integration is implied by this result.
