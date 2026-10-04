# OrcaRouter R21 vs R22 unexplained physical-page trajectory — 2026-10-04

## Scope

This document closes the time-series follow-up to the R21/R22 physical-page accounting comparison. It uses only the already preserved one-second allocator/meminfo samples from the completed R21 and R22 runs; no additional restart or host mutation is involved.

The comparison tracks the deliberately conservative `core_unexplained_loss` residual from post-compaction startup through the strict RM event. The residual is an approximate amount of physical-page loss not explained by the selected non-overlapping conventional resident accounting. It is **not** an exact NVIDIA-owned-page measurement.

Both source runs remain unchanged:

- R21: `VALID_RM_OOM`, FUNCTIONAL PASS / HOST-STABILITY FAIL, legacy `VLLM_PLE_CPU_OFFLOAD=1` path.
- R22: `VALID_RM_OOM`, FUNCTIONAL PASS / HOST-STABILITY FAIL, v0.29 PLE-mmap discriminator path.

## Final residual

R21:

- compact-to-event duration: `742.611 s`
- final `core_unexplained_loss`: `89465.184 MiB`

R22:

- compact-to-event duration: `721.361 s`
- final `core_unexplained_loss`: `90000.770 MiB`

The final residual differs by only about `535.586 MiB` between the two runs despite radically different swap behavior.

## Early threshold crossings

### R21 legacy CPU-offload

Final residual: `89465.184 MiB`.

- 25% threshold (`22366.296 MiB`): crossed at `+43.991 s` after compaction with residual `37154.699 MiB`.
- 50% threshold (`44732.592 MiB`): crossed at `+44.990 s` with residual `63909.523 MiB`.
- 75% threshold (`67098.888 MiB`): crossed at `+45.991 s` with residual `75885.785 MiB`.
- 90% threshold (`80518.665 MiB`): crossed much later at `+730.991 s`, only `11.620 s` before the RM event, with residual `81927.586 MiB`.

At the early 25/50/75% crossings, SwapFree had changed by only about `+3.668 MiB`; the later roughly 100 GiB legacy swap consumption had not yet occurred.

### R22 mmap

Final residual: `90000.770 MiB`.

- 25% threshold (`22500.192 MiB`): crossed at `+35.638 s` after compaction with residual `39416.078 MiB`.
- 50% threshold (`45000.385 MiB`): crossed at `+36.638 s` with residual `64328.199 MiB`.
- 75% threshold (`67500.577 MiB`): crossed at `+37.638 s` with residual `75189.867 MiB`.
- 90% threshold (`81000.693 MiB`): crossed at `+588.638 s`, `132.723 s` before the RM event, with residual `81546.207 MiB`.

At the early 25/50/75% crossings, SwapFree had changed by only about `+0.203 MiB`. Even at the R22 90% crossing, SwapFree delta was only about `-9.086 MiB`.

## Largest growth windows

The strongest common signal is the nearly identical short startup burst.

R21:

- largest 1 s residual increase: `+26754.824 MiB`
- interval endpoint: `+44.990 s` after compaction
- largest 5 s residual increase: `+75174.387 MiB`
- interval: approximately `+40.991 s -> +45.991 s` after compaction

R22:

- largest 1 s residual increase: `+24912.121 MiB`
- interval endpoint: `+36.638 s` after compaction
- largest 5 s residual increase: `+75138.043 MiB`
- interval: approximately `+32.638 s -> +37.638 s` after compaction

The two largest 5 s increases differ by only `36.344 MiB` out of roughly 75 GiB. Approximately 84% of each run's final unexplained residual is therefore formed in one short early-startup burst.

## Relation to the high-order collapse

The residual burst aligns with the previously measured high-order allocator collapse rather than with the later RM event.

For R21, the largest unexplained-residual interval is approximately `06:23:18.991Z -> 06:23:23.991Z`, the same interval in which the preserved pagetype trajectory recorded the largest Unmovable order-4+ drop (`104162.625 -> 29280.688 MiB`, `-74881.938 MiB`).

R22 also shows its residual 25/50/75% crossings within a three-second span near the beginning of startup, matching the previously observed initial catastrophic high-order collapse under mmap.

This establishes a strong temporal association:

1. a common startup phase consumes roughly 75 GiB of physical pages over about five seconds;
2. conventional non-overlapping Linux resident accounting explains only a small fraction of that burst;
3. node0 Normal high-order free capacity collapses in the same early interval;
4. the strict RM OOM occurs much later, after the host has evolved through additional allocation/reclaim pressure.

## Swap separation

The trajectory directly separates the common physical-page burst from the legacy PLE swap path.

- R21 early 75% residual crossing: SwapFree delta only `+3.668 MiB`.
- R22 early 75% residual crossing: SwapFree delta only `+0.203 MiB`.
- R21 final event: SwapFree delta `-101284.828 MiB`.
- R22 final event: SwapFree delta `-3163.168 MiB`.

Therefore the common roughly 75 GiB early burst is not caused by the later legacy CPU-offload swap churn. The legacy path remains an important sustained-pressure amplifier, but it is a separate layer from the common startup physical footprint.

## Current interpretation

Combined with R11 and the R21/R22 page-accounting closure, the leading model is now:

1. the common startup/model-loading path causes a short, roughly 75 GiB physical-page allocation burst in node0 Normal;
2. that burst is not classified at comparable scale as anon/file/slab/CMA/hugetlb/vmalloc/page-table/etc. by the selected Linux accounting;
3. the same interval destroys the prepared Normal-zone high-order reservoir;
4. a smaller amount of additional unexplained physical footprint accumulates later, producing final residuals around 89.5-90.0 GiB;
5. legacy PLE CPU-offload independently adds about 100 GiB of swap/residency churn and accelerates sustained depletion;
6. both runtime stacks can still reach the lower-level R11 mechanism: Normal-zone Unmovable order-4 RM demand, Movable fallback/pageblock stealing, failed high-order chunk acquisition, rollback, and order-0 retry.

The accounting and timing are **strongly consistent** with direct RM/kernel system-page allocation, but they do not yet identify exact page ownership for the 75-90 GiB footprint.

## Diagnostic direction

No additional watermark, compaction, drop-cache, or swap-tuning experiment is justified from this result.

The next high-value live experiment should narrow observability to the common early allocation burst rather than tracing the entire long startup. The target is the candidate-start/compaction-relative interval that covers approximately the first 30-50 seconds, with emphasis on the five-second burst that forms roughly 75 GiB of residual in both R21 and R22.

The purpose of the next trace is to attribute the common physical allocation to a concrete NVIDIA RM/UVM/model-loading boundary, not to repeat broad host-pressure tuning.

Canonical related evidence:

- `orcarouter-managed-rmsys-r11-allocator-state-20261003.md`
- `orcarouter-managed-rmsys-r21-pagecache-reclaim-result-20261004.md`
- `orcarouter-managed-rmsys-r21-collapse-onset-20261004.md`
- `orcarouter-managed-rmsys-r22-v029-mmap-result-20261004.md`
- `orcarouter-managed-rmsys-r21-r22-mmap-comparison-20261004.md`
