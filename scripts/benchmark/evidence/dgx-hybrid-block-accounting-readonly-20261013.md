# S2 actual DGX hybrid block-accounting audit — 2026-10-13

**Evidence class: ACTUAL_DGX (operator-supplied terminal output; not a GitHub-hosted run).**
Physical operator log: `~/dgx-hybrid-blocks-20261013-135405.log` (log filename timestamp 13:54:05 KST).
Source detached worktree: `14c67135f94b3c507a90c3a0702c83b9f3bfcda7`.
Original model tree: `$HOME/Workspace/llm/qwen3.8-flash-next-dgx-spark/models`.
Exact SHA GitHub Actions CI: [38347956896](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38347956896) — **SUCCESS** (separate `GITHUB_CI` evidence).

The operator ran `scripts/diagnostics/inspect-hybrid-reclaim-blocks.sh` using
`QWEN38_RECLAIM_AUDIT_SHA` and explicit `QWEN38_RECLAIM_MODELS_ROOT`.
The posted terminal log includes both beginning and completion markers:

```text
RECLAIM_BLOCK_ACCOUNTING=BEGIN
SOURCE_SHA=14c67135f94b3c507a90c3a0702c83b9f3bfcda7
HOST_MUTATION=NO
MODEL_START=NO
BENCHMARK_EVIDENCE=NOT_VERIFIED
RECLAIM_BLOCK_ACCOUNTING=COLLECTED_READ_ONLY
BENCHMARK_BEFORE_RECLAIM=REQUIRED
MODEL_DELETION=BLOCKED_PENDING_DEPENDENCY_AND_EVIDENCE_REVIEW
```

## Exact measurements (du allocated blocks, B1)

| Directory beneath models/ | `du -sxB1` allocated bytes | GiB (2^30) | Hardlink file entries (`-links +1`) | Symlink entries |
|---|---:|---:|---:|---:|
| `qwen3.8-flash-next-orcarouter` | 183535857664 | 170.931 | 0 | 0 |
| `qwen3.8-flash-next-mazinb` | 186449989632 | 173.645 | 0 | 0 |
| `qwen3.8-hybrid-quant-layout` (H3) | 77543333888 | 72.218 | 0 | 13 |
| `qwen3.8-h4-orca-all` (H4) | 68014092288 | 63.343 | 0 | 76 |
| `qwen3.8-h5-neutral-input-scale` (H5) | 44912640 | 0.042 | 0 | 91 |
| `qwen3.8-h6-modelopt-w4a16` (H6) | 35475456 | 0.033 | 0 | 139 |
| **Combined, de-duplicated by inode for these selected arguments** | **515623661568** | **480.212** | **0 observed** | **319** |

All six directory `stat -c %d` device identities are `66306`.
The output of `du -scxB1` equals the table sum. H3+H4 allocation is
`145557426176` bytes (135.561 GiB) **not proven independently reclaimable**.
No hardlinks were observed in these six directory traversals; this alone
does not exclude reflink/CoW extents, external references, filesystem
snapshots, binder/mount dependency, or orphaned indirect consumers.

## Interpretation and explicit safety boundaries

Source review at the audit SHA: the H3–H6 checkpoint builders intentionally
produce absolute **container-runtime mount alias** symlinks (e.g.,
`/base-model`, `/h3-model`, `/h4-all`, `/h5-parent`).
A symlink that does not resolve on the *host* is not automatically corrupted:
it may be resolved by the specific container's bind mount layout.
**Actual symlink destinations and safetensors index target files were NOT
enumerated by S2**, and their runtime bind mounts were NOT proven.
Existing asset registry explicitly records H6->H5/H4/H3/OrcaRouter.
A small H6 directory is NOT an independent 34 MiB runnable model.

The script itself checks source cleanliness/identity and before/after
manifest/ownership/current-release fingerprints. Its completion marker
does not verify every weight byte or prove no concurrent host activity.
No model start, deletion, Docker prune, swap manipulation, or benchmark
is evidenced by this run. Five per-profile llama-benchy reports remain
`NOT_MEASURED`. M1 live, M3 live pairs, M4 H38 and destructive M2/D0
gates remain unchanged.

## Required next gate: S3 read-only runtime-alias/index reference survey

1. Inspect `readlink` targets under H3/H4/H5/H6 without dereferencing
   virtual Docker mount paths as host filesystem paths.
2. Compare every unique `model.safetensors.index.json.weight_map`
   shard filename against the corresponding direct file or symlink,
   without loading tensor payloads; preserve per-stage provenance.
3. Read source-declared bind mount alias wiring and distinguish
   host-resolvable links from container-only expected aliases,
   unknown targets and genuinely missing dependencies.
4. Inspect filesystem type/reflink/snapshot capability separately;
   block totals do not certify extents or final free-space delta.
5. Before any candidate cleanup: benchmark preservation, external
   SHA256-verified evidence copy, exact ownership/dependency check,
   model/host qualification, per-object dry-run, and explicit owner approval.

**S2=PASS_READ_ONLY; S3=NOT_RUN; BENCHMARK=NOT_MEASURED;
MODEL_DELETION=NOT_PERFORMED; PR #259=Draft/Open/Unmerged.**
