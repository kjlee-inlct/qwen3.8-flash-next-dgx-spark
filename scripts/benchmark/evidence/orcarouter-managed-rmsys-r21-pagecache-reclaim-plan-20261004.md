# OrcaRouter R21 page-cache reclaim + post-stop compaction plan — 2026-10-04

## Motivation

R18 and R20 reached materially different post-stop allocator states even though both executed one explicit post-teardown compaction pass.

The read-only R18/R20 comparison showed:

- R20 post-compaction MemFree was ~11081 MiB lower than R18 while MemAvailable differed by only ~17 MiB.
- R20 had ~11114 MiB more Cached memory, dominated by ~10939 MiB more Inactive(file).
- Anonymous and slab differences were negligible relative to that gap.
- R20 also had ~11324 MiB less node-0 Normal-zone Unmovable order-4+ free capacity.
- R20's compaction increased aggregate high-order free capacity but decreased the directly relevant Unmovable order-4+ reservoir.

The exact files responsible for the extra file cache are not known from the historical proc snapshots and are not assumed.

## Hypothesis

A file-cache-heavy post-stop state can keep immediately free pages and the relevant Unmovable high-order reservoir lower even while MemAvailable remains high. Reclaiming page cache before one-shot compaction may move the allocator state toward the successful R18 condition and may avoid both recoverable RM sysmem fallback and the independent startup memory-protection boundary.

## Controlled sequence

R21 uses the same immutable OrcaRouter 16 GiB managed release and the same >=2700 s predecessor-age guard:

1. verify managed OrcaRouter is active/healthy and transitions are idle
2. verify predecessor age >=2700 s
3. start allocator-state collection
4. fully stop the managed service and verify the predecessor container is no longer running
5. capture the post-stop pre-reclaim proc snapshot
6. run `sync`
7. capture the post-sync proc snapshot
8. write `1` once to `vm.drop_caches` to reclaim page cache only
9. capture the post-drop-caches proc snapshot
10. write `1` once to `vm.compact_memory`
11. capture the post-compaction proc snapshot
12. start the same immutable managed release
13. apply the existing readiness/host-protection path
14. collect strict RM/kernel evidence and classify validity separately from host stability

No persistent VM knob is changed. The existing memory-protection policy is not relaxed.

## Classification

- `VALID_CLEAN`: valid replacement, API ready, collector successful, zero strict RM OOM signatures
- `VALID_RM_OOM`: valid replacement/API readiness but strict RM OOM signature observed
- `INVALID`: replacement/readiness contract not completed, including a protected stop

Any `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` remains HOST-STABILITY FAIL under the existing strict policy.

## Live attempt 01 — partial result

The first live R21 attempt used an aged predecessor of 5943 s (~99.05 min), with the managed OrcaRouter release, transitions, and VM defaults all in the expected baseline state.

The allocator treatment itself produced a strong and internally consistent shift:

- before reclaim: Cached ~8424.0 MiB, Inactive(file) ~6371.3 MiB, MemFree ~113793.2 MiB, Unmovable order-4+ ~100231.9 MiB
- after `sync`: effectively unchanged
- after `drop_caches=1`: Cached ~202.4 MiB, Inactive(file) ~48.2 MiB, MemFree ~122278.4 MiB, Unmovable order-4+ ~105998.9 MiB
- after `compact_memory`: MemFree ~122314.6 MiB, aggregate Normal order-4+ ~119743.2 MiB, Unmovable order-4+ ~104607.3 MiB, Movable order-4+ ~15083.7 MiB

Key deltas:

- `sync -> drop_caches`: Cached -8221.984 MiB, Inactive(file) -6323.301 MiB, MemFree +8490.176 MiB, Unmovable order-4+ +5766.688 MiB, aggregate Normal order-4+ +14486.062 MiB
- `drop_caches -> compact_memory`: aggregate Normal order-4+ +2496.000 MiB, but Unmovable order-4+ -1391.562 MiB while Movable order-4+ +3875.500 MiB
- pre-treatment -> post-compaction: MemFree +8521.332 MiB, Cached -8221.598 MiB, Unmovable order-4+ +4375.438 MiB, aggregate Normal order-4+ +16984.250 MiB

The managed replacement then reached the service's committed-and-healthy state and the service remained active. No RM/OOM text was present in the shell-level `kernel RM/OOM` display.

However, the runner did not write `r21-summary.txt`. The long managed startup consumed the existing sudo timestamp, and the first late `sudo -n journalctl -k ...` evidence-finalization step failed with `sudo: a password is required`. Because strict kernel-window capture, restart/API validity files, and the canonical summary were not completed, attempt 01 must not be promoted directly to `VALID_CLEAN` from the live console output alone.

Current classification before post-hoc finalization: **INVALID / incomplete harness finalization**, with a successful treatment-state transformation and apparently healthy replacement runtime.

## Harness correction

The R21 runner now keeps the existing sudo timestamp alive during long managed startup so that late kernel-evidence collection cannot fail solely because the timestamp expires.

A separate `finalize-orcarouter-r21-incomplete.sh` helper can complete attempt 01 without another restart. It reconstructs the exact kernel-journal window from the already-written start/end epochs, requires the current replacement container to have started inside the recorded R21 run window, recomputes strict RM signatures, and writes the missing validity/summary evidence. This prevents a later unrelated restart from being misclassified as the R21 candidate.

## Interpretation boundaries

The partial live result directly supports the page-cache-conditioning mechanism: reclaiming page cache converted ~8.2 GiB of cache into ~8.5 GiB additional free memory and increased the directly relevant Unmovable high-order reservoir by ~5.8 GiB before compaction.

It also shows again that one-shot compaction primarily moves the buddy distribution toward larger Movable blocks; in this run, Unmovable order-4+ fell by ~1.39 GiB during the compaction step itself. Therefore a future eligibility rule still cannot be based on aggregate high-order growth alone.

A final `VALID_CLEAN` classification still requires successful post-hoc strict kernel-window capture plus replacement/readiness/collector validation. No permanent numerical allocator threshold is accepted from this run.
