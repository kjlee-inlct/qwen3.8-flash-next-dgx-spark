# Benchmark first — selective DGX model/Docker reclamation

## Actual S2 allocation and link results (2026-10-13)

[Physical-DGX S2 exact-byte audit](../scripts/benchmark/evidence/dgx-hybrid-block-accounting-readonly-20261013.md) **PASS_READ_ONLY** at SHA `14c67135f94b3c507a90c3a0702c83b9f3bfcda7`. Combined six-tree `du` allocated blocks: `515623661568` bytes; H3+H4: `145557426176` bytes (135.561 GiB); 0 hardlink file entries and 319 symlinks (13/76/91/139 from H3/H4/H5/H6). Filesystem device 66306 for all six. **No deletions, model load or benchmark.** H3/H4 cannot yet be retired: H6's configured ancestor chain and container-only symlink targets require an S3 link/index/mount map, and extent sharing/CoW remain unknown. All five report templates remain `NOT_MEASURED`; exact ownership, verified off-host evidence copies, per-object dry-run and owner authorization are still mandatory. `du` is not a certificate of reclaimable bytes.


Date: 2026-10-13. Operator preference: benchmark each available candidate
before deleting its checkpoint, Docker image or important experiment artifact.

**No deletion, model startup or runtime switch is authorized by this plan.**
Physical B5 snapshot: 105 GiB disk free, 88% filesystem utilization,
managed OrcaRouter container exited, old container object and immutable
release intact, monitor/protect both 1. The external lychee888 card claims
approximately 123.25 GiB checkpoint size (larger than current free space
even before temporary files or safety reserve); L0 JSON passed, not weights
or loader qualification.

## Run read-only inventory on the actual DGX now

Use a NEW detached source worktree, not the installed immutable release.
Execute only after the new exact SHA has SUCCESS CI:

~~~bash
set -Eeuo pipefail
SOURCE="$HOME/Workspace/llm/qwen3.8-flash-next-dgx-spark"
cd "$SOURCE"
test -z "$(git status --porcelain=v1 --untracked-files=all)"
git fetch origin feat/h38-managed-integration
TARGET='__EXACT_SUCCESS_CI_SHA__'
test "$(git rev-parse FETCH_HEAD)" = "$TARGET"
AUDIT="$HOME/Workspace/llm/qwen38-storage-audit-$TARGET"
test ! -e "$AUDIT"
git worktree add --detach "$AUDIT" "$TARGET"
cd "$AUDIT"
test "$(git rev-parse HEAD)" = "$TARGET"
test -z "$(git status --porcelain=v1 --untracked-files=all)"
LOG="$HOME/dgx-bench-before-reclaim-$(date +%Y%m%d-%H%M%S).log"
QWEN38_RECLAIM_AUDIT_SHA="$TARGET" \
  bash scripts/diagnostics/inspect-bench-before-reclaim.sh \
  2>&1 | tee "$LOG"
echo "RECLAIM_AUDIT_LOG=$LOG"
~~~

The audit uses only existing read-only actions:
- scripts/manage-storage.sh status
- scripts/manage-storage.sh recommend
- scripts/manage-storage.sh plan (preview, NOT prune)
- scripts/manage-models.sh assets
- Docker system df -v, image ls --digests, ps -a, and df.

Do not run destructive subcommands or assume every displayed
reclaimable image byte can actually be freed (shared layers/tags).
Review/redact local host paths and Docker names before publication.
Expected final output is RECLAIM_READONLY=COLLECTED and
MODEL_OR_DOCKER_DELETION=BLOCKED_PENDING_MODEL_EVIDENCE_AND_ASSET_REVIEW.
Failure/partial results trigger investigation, not automatic repair.

## Evidence-preserving decision sequence

1. Inventory sizes, actual Docker IDs/digests and which image/layer
   is referenced by ANY running or stopped container. Record model
   directory manifests, ownership/dependencies and active profile.
2. PROTECT active OrcaRouter weights/image and retained predecessor
   container ID f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24.
   Existing managed-start commit can DELETE that stopped predecessor;
   rollback may START it. User preference for selective cleanup is
   not approval to sacrifice this exact object.
3. For each proposed removal candidate, preserve valid ACTUAL
   llama-benchy raw JSON, its generated Markdown report, checkpoint
   revision, image ID/digest, service runtime identity, parameters
   and host/RM/monitor outcome. Keep per-model measured results distinct
   from old historical runs. Correctness/host-stability must be
   independently qualified before benchmarking a model.
4. Archive raw JSON and MD plus SHA256 in a separate, protected or
   off-host location NOT in any directory targeted for cleanup.
   Verify the archived copy checksum. Results are NOT preserved if
   the only copy is inside the model directory to be deleted.
5. Only then review EXACT individual models/images with existing
   scripts/manage-models.sh retire PROFILE --dry-run or
   scripts/manage-models.sh remove PATH --dry-run and
   scripts/manage-storage.sh prune --dry-run, with owner/dependency
   and backup checks. No broad Docker system prune, model rm -rf,
   wildcard rmi, swap deletion or uninstaller purge-all.
6. An unbenchmarked or unsafe-to-start model stays HOLD / NOT_MEASURED,
   not 0 tokens/sec. A future explicit exception/waiver must document
   why measurement is unavailable and why deletion is acceptable.
   A cleanup after such a waiver is NOT classified as benchmark-preserved.
7. Any separately authorized actual delete must be followed by
   df/Docker accounting, release/model/monitor/ownership checks and
   verification of preserved benchmark artifact hashes.

## Candidate categories (NOT approved deletions)

| Asset | Provisional decision | Reason |
|---|---|---|
| Active OrcaRouter checkpoint and vllm-skinny-tp1:v1 | PROTECT | Manifest, stopped predecessor, M1 live unqualified |
| Stopped canonical Docker predecessor | PROTECT EXACT ID | Rollback and managed commit semantics |
| mazinb checkpoint/image | HOLD BENCH | Present; H6 base dependency possible |
| Hybrid H6 and parents | HOLD BENCH + DEPENDENCY | Shares OrcaRouter/mazinb and experiment provenance |
| NVIDIA / lychee888 weights | ABSENT | No local checkpoint to reclaim in A5 inventory |
| H7-H20 experiment images | REVIEW | Some disposable, some parent/protected |
| Dangling images/build cache | REVIEW | Lower risk perhaps, but preserve provenance and shared-layer accounting |
| PLE swap, current/previous release, HF cache, named volumes | PROTECT | Existing manager safety invariants |

The five per-model llama-benchy templates remain NOT_MEASURED.
A5 wizard dry-run, B5 readonly and lychee888 JSON-only L0 are actual
DGX PASS; M1 live, M3 profile pairs, H38/M4, destructive M2 and D0
remain unqualified/not authorized.


## Actual S1 physical host result (2026-10-13)

The owner returned all 8 read-only checks PASS from source 5136232.
[Preserved exact-scope evidence](../scripts/benchmark/evidence/dgx-storage-pre-reclaim-readonly-20261013.md).
OrcaRouter 171G active, mazinb 174G, H3 73G, H4 64G,
H5 43M, H6 34M. H6 depends on H5/H4/H3/OrcaRouter.
Neither H3 nor H4 is approved for deletion and neither is
a separate default user-facing llama-benchy model.
An H6 benchmark must never be misread as permission
to delete required H6 checkpoint ancestors.

Docker images 47.22GB but all referenced and 0B currently
reclaimable. About 6.239GB of stopped-container writable layers
may be reclaimable later following evidence preservation.
Nonproject Open WebUI and Portainer services are running.
Next read-only exact-SHA test:
scripts/diagnostics/inspect-hybrid-reclaim-blocks.sh,
requiring QWEN38_RECLAIM_MODELS_ROOT set to the real model root.
The combined directory du and hardlink checks narrow
disk accounting but cannot detect all CoW/reflink shared extents.
