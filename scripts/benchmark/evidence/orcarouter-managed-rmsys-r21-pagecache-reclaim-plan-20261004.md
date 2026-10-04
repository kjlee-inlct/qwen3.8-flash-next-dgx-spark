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

## Interpretation boundaries

A clean R21 would support page-cache state as an important conditioning variable and would justify comparing the pre/post reclaim snapshots against R18 and R20. It would not by itself establish a permanent numerical allocator threshold or prove that a specific checkpoint file owned the historical R20 cache.

An RM-OOM or protected-stop R21 would show that page-cache reclaim plus compaction is insufficient and would keep the allocator-state mechanism open without weakening the existing safety monitor.
