# S4 actual DGX Hybrid all-link closure — 2026-10-13

**Evidence class:** `ACTUAL_DGX`, transcribed from the user's actual DGX terminal
output, not from synthetic CI or a claimed remote-host execution.

- Operator log: `/home/inlc/dgx-hybrid-link-closure-20261013-142413.log`
- Exact detached source SHA: `5a14d169bbca93604b92e52dc1e548ed75cc5569`
- Same-SHA [CI 38350725606](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38350725606):
  **SUCCESS**, 930 Python unit tests and synthetic operator validation PASS.
  CI is **separate SOURCE_CI evidence**; it did not run on the actual DGX.
- Probe: `inspect-hybrid-link-closure.py`, using explicitly supplied model
  root and exact SHA. S4 was run in a detached source worktree.
- Original model directory: under `~/Workspace/llm/qwen3.8-flash-next-dgx-spark/models`
  from the continued S1–S3 workflow; S4 output does not print the root variable.

```text
S4_LINK_CLOSURE=BEGIN
SOURCE_SHA=5a14d169bbca93604b92e52dc1e548ed75cc5569
SOURCE_MOUNT_CONTRACT=STATIC_PASS
HOST_MUTATION=NO
MODEL_START=NO
TENSOR_PAYLOAD_READ=NO
STAGE=base ALL_SYMLINKS=0
STAGE=mazinb ALL_SYMLINKS=0
STAGE=h3 ALL_SYMLINKS=13
LINK_STAGE=h3 LINK_RESOLUTION=REGULAR_FILE COUNT=13
STAGE=h4 ALL_SYMLINKS=76
LINK_STAGE=h4 LINK_RESOLUTION=REGULAR_FILE COUNT=76
STAGE=h5 ALL_SYMLINKS=91
LINK_STAGE=h5 LINK_RESOLUTION=REGULAR_FILE COUNT=91
STAGE=h6 ALL_SYMLINKS=139
LINK_STAGE=h6 LINK_RESOLUTION=REGULAR_FILE COUNT=139
FS_DEVICE=66306
FS_AVAILABLE_BYTES_SNAPSHOT=112103874560
FS_TYPE=ext4
ALL_LINK_REFERENCE_GAPS=0
ACTUAL_DOCKER_BIND_MOUNTS=NOT_VERIFIED
REFLINK_COW_SHARED_EXTENTS=NOT_MEASURED
RECLAIMABLE_BYTES=NOT_CERTIFIED
BENCHMARK_BEFORE_RECLAIM=REQUIRED
MODEL_DELETION=BLOCKED_PENDING_EVIDENCE_AND_DEPENDENCY_REVIEW
S4_LINK_CLOSURE=COLLECTED_READ_ONLY
```

## Interpretation, limited to what the actual probe checked

All **319** Hybrid symlink entries were classified as resolving through
the source-declared container virtual mount aliases to regular files:
H3 13/13, H4 76/76, H5 91/91, H6 139/139. No unexpected or
missing link was detected within the script's covered symlink paths.
The static H6 `:ro` parent-mount declarations and builder alias
constants matched the source. The actual host reported ext4,
filesystem device `66306` and `112103874560` bytes available
(approximately **104.404 GiB**, a point-in-time observation).

This is NOT proof of **actual live Docker bind-mount realization**,
whole-tensor/checkpoint correctness, a bootable H6, NVIDIA RM/memory
stability, raw benchmark measurements, or independence of filesystem
physical extents. The script deliberately did not perform an extent-level
reflink/CoW or snapshot inventory; even on ext4, do not replace
`RECLAIMABLE_BYTES=NOT_CERTIFIED` with a predicted freed-byte total.

## Consolidated outcome and next priority

- S1 actual DGX inventory: PASS_READ_ONLY.
- S2 actual DGX allocated-block/hardlink audit: PASS_READ_ONLY;
  six-tree 515623661568 bytes, H3+H4 145557426176 bytes allocated,
  **not certified reclaimable**.
- S3 actual DGX index-shard virtual reference survey: PASS_READ_ONLY,
  `REFERENCE_GAPS=0`; H6 all 81 indexed shards use ancestor aliases.
- **S4 actual DGX all-symlink source-alias closure: PASS_READ_ONLY,
  `ALL_LINK_REFERENCE_GAPS=0`.**
- Next work is **safe M1 live readiness / approved isolated model startup**
  then verified `/v1/models`, monitored host stability, and
  **real pinned llama-benchy raw JSON + Markdown + SHA256 and separate
  preserved copies**. No new storage diagnosis is required merely
  because this probe succeeded.
- Exact stopped old Docker object `f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`
  and immutable installed release `ff67bab3c94d6992f61b9535836df97f03b9c022`
  remain protected. Existing managed startup could delete the old
  Docker object on commit; generic rollback could restart it.
  **M1 remains NOT_QUALIFIED, and there is NO live-start consent**.
- All five profile reports remain **NOT_MEASURED**. Absent Nvidia /
  lychee888 local checkpoints must not receive invented numeric results.
- H3/H4 and mazinb must NOT be deleted based on source-alias closure;
  no Docker prune or teardown authorized.
- PR #259 remains Draft/Open/Unmerged at time of recording.

This date-scoped result supersedes prior written S4 `NOT_RUN`
statements, while preserving them as historical pre-run plans.
