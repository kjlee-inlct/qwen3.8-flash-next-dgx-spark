# OrcaRouter R21 allocator collapse onset — 2026-10-04

## Scope

This document records the read-only full-history and exact live-log correlation for the R21 allocator collapse. R21 itself remains `VALID_RM_OOM` (FUNCTIONAL PASS / strict HOST-STABILITY FAIL).

The purpose is to locate when the prepared Normal-zone high-order reservoir collapsed and correlate that interval with the runtime startup path without claiming per-page ownership that the evidence does not provide.

## Timing

- post-stop compaction completed: `2026-10-04T15:22:38+09:00` (`06:22:38Z`)
- strict RM event: `2026-10-04T06:35:00.611065+00:00`
- compact-to-event duration: `742.611 s`

Prepared state at the beginning of the scan:

- Normal Unmovable order-4+: `104613.938 MiB`
- aggregate Normal order-4+: `119742.938 MiB`

## First threshold crossings

Normal Unmovable order-4+:

- below 50% (`52306.969 MiB`): `06:23:23.990990Z`, value `29280.688 MiB`
- below 10% (`10461.394 MiB`): `06:23:28.990563Z`, value `6248.688 MiB`
- below 1% (`1046.139 MiB`): `06:23:34.003006Z`, value `0 MiB`
- below 1 GiB / 100 MiB / 10 MiB: the same `06:23:34.003006Z` sample, value `0 MiB`

Aggregate Normal order-4+:

- below 50% (`59871.469 MiB`): `06:23:22.990282Z`, value `50375.875 MiB`
- below 10% (`11974.294 MiB`): `06:23:28.990290Z`, value `6266.250 MiB`
- below 1% (`1197.429 MiB`): `06:23:29.995656Z`, value `0.438 MiB`
- below 1 GiB / 100 MiB / 10 MiB: the same `06:23:29.995656Z` sample, value `0.438 MiB`

Therefore the prepared high-order state collapses almost completely within roughly 45-56 seconds after compaction and more than eleven minutes before the final RM OOM event.

## Steepest observed drain

Largest consecutive 5-second Unmovable drop:

- interval: approximately `06:23:18.991Z -> 06:23:23.991Z`
- `104162.625 -> 29280.688 MiB`
- delta: `-74881.938 MiB` in `5.000 s`

Largest consecutive 5-second Movable drop:

- interval: approximately `06:23:23.991Z -> 06:23:28.991Z`
- `8921.438 -> 6.750 MiB`
- delta: `-8914.688 MiB` in `5.000 s`

Largest consecutive 1-second aggregate Normal order-4+ drop:

- interval: approximately `06:23:21.990Z -> 06:23:22.990Z`
- `76771.000 -> 50375.875 MiB`
- delta: `-26395.125 MiB` in about `1.000 s`

This is not a slow monotonic drain spread across the whole ~12 minute startup. The dominant collapse occurs near the beginning of model startup.

## Exact startup-log correlation

The live container ID was checked before collecting the historical Docker log window and still matched the R21 candidate, so these lines belong to the measured R21 replacement.

Relevant startup events:

- `06:23:17.005849Z`: main worker logs `PleOffload: spawning worker`
- `06:23:20.324583Z`: main worker logs `Loading model from scratch...`
- `06:23:21.449516Z`: `PleOffloadWorker` distributed initialization begins
- `06:23:21.623236Z`: PLE worker distributed environment initialized
- `06:23:21.623303Z`: PLE worker logs `Initializing model structure for PLE weight discovery ...`
- `06:23:23.757579Z`: PLE worker reports one discovered PLE layer
- `06:23:23.829814Z`: main worker reports checkpoint size `170.88 GiB`, available RAM `39.44 GiB`
- `06:23:23.830634Z`: main checkpoint safetensor loading is at `0/18`
- `06:23:23.935605Z`: PLE worker reports checkpoint size `170.88 GiB`, available RAM `39.43 GiB`
- `06:23:23.936012Z`: PLE-offload safetensor loading is at `0/18`
- `06:23:25.827678Z`: PLE-offload reaches `1/18` (`6%`)

The largest measured Unmovable drain spans approximately `06:23:18.991Z -> 06:23:23.991Z`. That interval begins after the PLE worker is spawned, contains main-model startup and PLE worker initialization/weight discovery, and ends just after both the main worker and PLE worker enter safetensor loading at `0/18`.

The threshold crossings line up with the same startup sequence:

- aggregate Normal 50% crossing: `06:23:22.990Z`
- Unmovable 50% crossing: `06:23:23.991Z`
- PLE-offload `0/18`: `06:23:23.936Z`
- first visible PLE-offload `1/18`: `06:23:25.828Z`
- Unmovable 10% crossing: `06:23:28.991Z`
- aggregate Normal effectively zero: `06:23:29.996Z`
- Unmovable effectively zero: `06:23:34.003Z`

This is substantially stronger than correlation with the later 6% progress line alone: the collapse begins after the legacy PLE worker is spawned and overlaps its structure initialization and weight-discovery path before visible shard progress.

It still does **not** prove that the PLE process owns every page represented by the buddy/pagetype collapse. Main-model initialization is active in the same interval and the allocator samples are system-wide.

The later `Using MoEPrepareAndFinalizeNoDPEPModular` marker at `06:34:48.381Z` occurs long after Unmovable capacity was already exhausted and is not the onset cause.

## Runtime-path context

The captured R21 container environment confirms:

- `VLLM_PLE_CPU_OFFLOAD=1`
- `VLLM_PLE_OFFLOAD_READY_TIMEOUT=1800`
- exact-QSA fallback disabled in the managed path
- CUDA `13.0.1`
- managed image `local/vllm-openai:dev`

The managed OrcaRouter path therefore used the legacy CPU-offload PLE implementation during the measured collapse.

Repository implementation notes for this path state that loading the PLE table places about `95.37 GiB` into the offload process and that most of it is subsequently pushed to swap. The magnitude and timing are structurally consistent with R21's initial high-order collapse and later large swap consumption, but this remains implementation-context evidence rather than direct page ownership proof.

## Existing mmap comparison path

The repository already contains an experimental OrcaRouter path on vLLM v0.29 that replaces resident/CPU-offloaded PLE table storage with NVMe-backed mmap/page-cache access. That image keeps the same OrcaRouter checkpoint and includes the required GB10 FLA and QSA compatibility fixes.

The mmap implementation replaces the giant PLE embedding with a small placeholder, drops the PLE shard tensors during `load_weights`, and opens the corresponding safetensor ranges as memory maps. With prewarm disabled, it does not intentionally stream the complete PLE table into RAM during startup.

This existing path is therefore the highest-value next mechanism discriminator. It is **not** a pure one-variable A/B against the managed path because the vLLM runtime line, QSA fallback, and GB10 FLA fixes also differ. Any R22 result must preserve that limitation explicitly.

## Interpretation

R21 now separates three stages:

1. post-stop reclaim/compaction creates a strong initial allocator state;
2. the initial model/legacy-PLE initialization interval destroys almost all Normal high-order capacity within ~45-56 seconds after compaction;
3. much later, temporary Movable high-order capacity reforms and is drained again near the final RM allocation failure.

Therefore:

- a static pre-start allocator eligibility gate cannot solve this mechanism;
- one-shot post-stop reclaim/compaction cannot preserve the reservoir through startup;
- the late MoE marker is not the collapse onset;
- legacy PLE CPU-offload is now the leading startup-pressure source to discriminate experimentally, but causal ownership is not yet proven;
- production integration of cache reclaim/compaction is not justified.

## Next experiment

R22 should reuse R21's preconditioning and evidence collection but replace the startup path with the repository's existing OrcaRouter v0.29 PLE-mmap candidate.

To preserve comparability, R22 should pin:

- the installed OrcaRouter checkpoint and served model identity;
- `16 GiB` KV, matching the current managed OrcaRouter default rather than the older v0.29 helper's historical `24 GiB` value;
- `max_model_len=262144`, `max_num_seqs=3`;
- host VM defaults and the same protection thresholds;
- `sync -> drop_caches=1 -> compact_memory` after full predecessor teardown;
- 1-second buddy/meminfo and 5-second pagetype collection;
- strict RM signature counting.

R22 is a mechanism-discrimination experiment, not production acceptance. A clean mmap run would strongly implicate the legacy resident CPU-offload startup path, but because the runtime stack also changes it would not by itself prove a single-variable causal fix or justify promotion.
