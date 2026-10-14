## 2026-10-14 DGX physical mazinb checkpoint deletion — PASS; five Docker remnants — PENDING

Actual user-provided DGX console from 2026-10-14 18:55 KST (source
`72346806e9e9ed7438245761ae40b606eb6bc941`) shows successful
Wizard **Models → 4** exact scoped deletion of
`models/qwen3.8-flash-next-mazinb`. Five stopped mazinb experiment
containers were intentionally preserved by the source-only implementation.
Source/checkpoint and Hybrid evidence SHA passed independently after deletion.

- MAZINB_RECLAIM_RESULT=`SOURCE_CHECKPOINT_REMOVED_VERIFIED`
- Docker inventory result=`UNCHANGED` (expected for that original action)
- FS before=`110587654144` bytes; after=`297037643776` bytes
- FS available delta=`186449989632` bytes (about **173.65 GiB**)
- H3, H4, H5, H6 all PRESERVED; protected predecessor Docker ID still pinned
- Original `smoke.json`, `mazinb.json`, `mazinb-report.md` SHA all PASS
- Five mazinb stopped IDs: `1ebe723a279171794d7753cdbc3726e8c0db052c7cac02ec3060b8fc23c2700d`, `64a4dfacebc0369887742440b5f1a084420b4ca1dc65c4324de61be5d49a1be3`, `7af3966f3d0cae79f8277eaf9ad003fb04c1e15ea01f86574c2d8eeac396e7a1`, `b47e01628492da3f49d5aca2b677ed66dabde08680ae690df700926a37c0d631`, `e9107e3cbebecea9affe7e92dfaf13f711ebf84f8ed8e6e06b1ba16985c9e647`.

**Correction:** Earlier source-only deletion never offered Docker removal.
The requested new, independent cleanup is `./wizard.sh` → **Models (3)
→ Retire five mazinb Docker containers (5)** or strictly read-only
`./scripts/manage-models.sh retire-mazinb-containers --dry-run`.
The new helper `scripts/model/retire-mazinb-containers.py` requires
exact five 64-hex IDs and names, exit state, restart policies, matching
previous checkpoint bind mount and vLLM image tag; protected predecessor;
complete benchmark original/repo hash verification; M1 stopped journal;
H3-H6 presence; full Docker inventory. An apply requires owner confirmation,
the lifecycle and M1 benchmark locks, reruns the plan, and archives five
sanitized inspect JSON metadata files + five complete bounded Docker logs +
portable SHA256SUMS under private
`~/.local/state/qwen38-spark/retirement-archives/` **before** performing
only `docker rm <exact-container-ID>`. It never uses `-f` or `-v`,
deletes no images/volumes, and checks other Docker object IDs unchanged.
The historical M1 journals remain byte-identical; a separate
`mazinb-m1/retired-docker.json` allows M1 status to report
`M1_DOCKER_REMOVED=YES_ARCHIVED` after verified cleanup.

**PHYSICAL FIVE-CONTAINER DOCKER REMOVAL: NOT_RUN**. Do not conflate
source/CI passage with an actual DGX run. The shared
`vllm-orcarouter-v029:v1` image must stay because H3–H6 and other trials
share it. Docker global prune remains forbidden.

## 2026-10-14: mazinb source checkpoint-only retirement workflow (SOURCE IMPLEMENTED; PHYSICAL RECLAIM NOT_RUN)

The owner requested: after completing the measured mazinb v0.29 M1 benchmark,
reclaim the original mazinb model through the Wizard and verify it. This is
**not** approval for broad container/image/model pruning. Real deletion
is conditional on passing an exact-target admission and a new explicit Wizard
confirmation; do not infer complete mazinb Legacy benchmarking or long-term
host-stability qualification from the v0.29 result.

Current implementation: `./wizard.sh` → **Models (3) → Reclaim mazinb (4)**.
The Wizard performs a default-NO, read-only `manage-models.sh
reclaim-mazinb --dry-run`; an actual apply requires the literal phrase
`DELETE_MAZINB_SOURCE_CHECKPOINT`. It then delegates to the existing
`manage-models.sh` checkpoint removal engine rather than introducing
a second deletion implementation.

The separate read-only gate `scripts/model/mazinb-reclaim-gate.py` must
verify: complete pinned mazinb model manifest; nonactive completed managed
installation; published physical M1 `smoke.json`, `mazinb.json`,
`mazinb-report.md` SHA256 against **both** repository archived payloads
and original DGX results; H3 pinned provenance and, when present, complete
H3→H6 runtime-only validation; absence of symlinks into the removed
checkpoint; complete Docker inventory with no running project Docker or
restartable stopped mount references; exact protected OrcaRouter predecessor
identity; M1 terminal journal and exact stopped container. The apply path
adds the shared lifecycle and M1 benchmark locks and repeats checks before
deletion. It preserves every existing Docker container, image, logger,
historical M1/KV record, Hybrid stage, immutable release, PLE swap and
benchmarked source evidence. Stopped mazinb containers mounting its
checkpoint become archive-only/nonrestartable without re-download.

After deletion, the manager checks that the exact directory is absent,
Docker object inventory and protected predecessor ID are unchanged,
benchmark archive audit still passes, and records filesystem available
bytes before/after. Actual recovered bytes must come from that physical
output, **not** the historical ~174 GiB directory snapshot.

**Status:** GitHub source/host-free tests only until the owner runs a
version-verified physical DGX Wizard dry-run and checks the result. Physical
apply must remain blocked on any failed gate, stale source SHA, incomplete
Hybrid link references, invalid Docker identity, unverified independent
archive, or user cancellation. No model files have been deleted in this
development session.

See [mazinb source report](model-reports/mazinb.md).

# Benchmark first — selective DGX model/Docker reclamation

## 2026-10-14 operator priority reset: run → benchmark → archive → targeted reclaim

**Primary purpose:** actually test installed user models, record reproducible
performance and stability, archive raw llama-benchy JSON/Markdown/checksums,
and then reclaim disk/memory by removing **specific** superseded model and
experiment assets. Wizard is the instrument, not the goal; background
Supervisor P1a–P1e is OPTIONAL/DEFERRED rather than the next default milestone.

The physical mazinb 16-GiB M1 benchmark and digest checks are already
complete. Physical P1e synthetic simulation and 11/11 standalone tests
passed at `1594f30`. They do not prove an actual background worker.

**New guard:** general `manage-storage.sh prune` cannot delete benchmark
results by file age. `--benchmark-days` is now a **report-only age
threshold**. The Wizard Storage menu includes a read-only checksum/report
readiness audit; this does not certify external backup or authorize deletion.
Historical prune behavior could delete stopped experiment containers.
**The current hardened source now preserves these containers** during broad
prune as well as benchmark files; their logs/evidence are retained until
individually identified, archived, reviewed and explicitly approved.
A future targeted cleanup must verify exact Docker ID and dependent assets.

**Operational next:** run fresh read-only storage inventory (filesystem,
containers/image references, current checkpoint/dependency graph, model
report SHA archive status). Compare against 2026-10-13 S1 105GiB-free
snapshot before proposing precise reclamation. Select the next real
testable installed candidate, run supervised foreground qualification
and llama-benchy in a second terminal, verify archived copy, then
narrow per-asset dry-run. Do not prematurely remove OrcaRouter,
the protected managed predecessor, hybrid H3/H4 ancestors, swap,
immutable releases, benchmark results, or unrelated Docker apps.


## OrcaRouter actual wizard DRY-RUN PASS; performance still unmeasured (2026-10-13)

User's physical wizard session at exact SHA `a61b4569c5a6865dbeb9aa4ba4b21aeea12424e2` showed installed `orcarouter` and legacy `vllm-skinny-tp1:v1` image, monitor and protection enabled, final preview RC=0, original Docker/manifest unchanged. [Evidence](../scripts/benchmark/evidence/dgx-orcarouter-wizard-actual-dry-run-20261013.md). This is NOT a model launch, functional qualification, RM stability or llama-benchy JSON. [Next safe wizard trial design](DGX-ORCAROUTER-WIZARD-TRIAL-DESIGN.md) remains unimplemented; B terminal idle. User holds OrcaRouter deletion for this test only, not forever. Real report + verified external backup, dependency/rollback review and explicit per-target cleanup approval remain prerequisites. Five reports NOT_MEASURED.


## Owner clarification — OrcaRouter hold limited to current test, not permanent (2026-10-13)

**OrcaRouter goes first. During this test, do not remove OrcaRouter
checkpoint, its current needed configuration/dependencies, or
sacrifice measurement/rollback evidence to reclaim disk space.**
This is a **time- and workflow-scoped HOLD**, not a permanent
exemption from future model cleanup. Prior `never delete` wording
and hard-coded OrcaRouter-specific permanent rejection were
incorrect and are superseded.

When the OrcaRouter test is complete, it can become a **candidate**
for owner-approved targeted cleanup only after its actual raw
llama-benchy JSON, generated report, SHA256 and off-host verified
backup (or a separately approved documented no-benchmark
exception), dependency/ownership analysis, exact pre-deletion
plan and old-container/release recovery impact review. Cleanup
must be requested through the wizard; do not manually bypass it
using raw Docker or manager delete commands. **No actual deletion
is authorized**. The protected stopped predecessor Docker object,
swap and immutable release are separately preserved until an
independent explicit decision. All five reports NOT_MEASURED.

## Owner requires wizard-only lifecycle and separate bench terminal (2026-10-13)

[Two-terminal operating contract](DGX-TWO-TERMINAL-WIZARD-BENCHMARK.md):
A=wizard model install/switch/uninstall, read-only storage planning;
B=pinned llama-benchy on an already wizard-started,
health-checked and host-qualified model. A must **not**
switch/install/remove/prune while B benchmarks. First record actual
model/API/host stability, then raw JSON + report + SHA256 and
independently verified off-host backup, then separately authorize any
narrowly-scoped wizard-mediated cleanup. The current uninstaller
can destroy the protected canonical Docker object, even with default
non-purge behavior; therefore wizard-only is not deletion approval.
An inactive checkpoint not independently accessible in the wizard
is a future UI feature requirement, not permission to invoke
low-level removal tools. All five model reports remain NOT_MEASURED;
actual M1 read-only preflight RC=0 is NOT live qualification.


## S4 actual-DGX complete — move from inventory to evidence-preserving model qualification (2026-10-13)

[Actual S4 physical evidence](../scripts/benchmark/evidence/dgx-hybrid-all-link-closure-readonly-20261013.md):
319/319 H3–H6 symlinks resolve to regular files through known source aliases,
`ALL_LINK_REFERENCE_GAPS=0`, ext4 (device 66306), available bytes
`112103874560`. S1/S2/S3/S4 read-only surveys now complete;
actual live Docker binds, extent-level reclaimability and model
functional/host readiness remain unknown. **No further storage audit is
a prerequisite by default.** Next, preserve the exact stopped Docker
predecessor unless a separate explicit identity-disposition decision
is made, obtain safely monitored M1 live approval, and only benchmark
against a healthy, identity-verified API. Five report templates remain
`NOT_MEASURED`. Raw JSON + Markdown + SHA256 **verified external copy**
must precede any individually approved cleanup. **NO deletion approved.**


## S4 source read-only gate for non-index links (2026-10-13)

After S3 successfully resolved all indexed shard names, S4
[read-only operator check](DGX-HYBRID-S4-LINK-CLOSURE.md) extends
closure to non-index symlink entries and source static bind mounts.
This does not change benchmark-before-delete, exact ownership,
reflink/CoW unknown, external evidence backup or owner approval
requirements. ACTUAL_DGX S4 NOT_RUN pending the next qualified source.


## Actual S3 virtual-mount/shard-index reference result (2026-10-13)

[Physical DGX S3 evidence](../scripts/benchmark/evidence/dgx-hybrid-runtime-references-readonly-20261013.md) at `d14915549667e196356b8511526f9bfd4db42cd6`: all 81 H6 index shard filenames resolve to existing files through configured ancestor aliases (`VIRTUAL_CHAIN=81`); `REFERENCE_GAPS=0`; all 319 known stage symlinks have expected alias categories. **This is not a live Docker mount or tensor integrity check**. H3/H4's S2 135.561 GiB allocated size remains NOT certified reclaimable; neither H3/H4 nor mazinb is approved for deletion. Next: inspect all non-shard symlink targets/host filesystem capabilities and retain benchmark evidence before any individual dry-run or owner-approved reclaim. Five per-model reports remain NOT_MEASURED.


## Source-only S3 dependency inspection tool (2026-10-13)

Added `scripts/diagnostics/inspect-hybrid-runtime-references.py` and
[read-only S3 runbook](DGX-HYBRID-S3-REFERENCES.md). The tool recognizes only
builder-declared container aliases, reports each stage's link counts and unique
safetensors-index shard resolutions, checks exact clean checkout + installed
manifest/ownership/current pointer fingerprints before/after, and fails closed
for unknown references. It never loads weight tensors or starts/removes a
model. Static/synthetic tests are not actual DGX S3 evidence. **S3=NOT_RUN
on physical host** until the new commit's CI succeeds and the operator
returns the exact log. S2 PASS does not change deletion/benchmark gates.


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
