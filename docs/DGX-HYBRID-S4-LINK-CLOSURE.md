# S4 read-only all-Hybrid-link closure — actual DGX NOT_RUN

This is the next bounded non-mutating follow-up after
[actual S3](../scripts/benchmark/evidence/dgx-hybrid-runtime-references-readonly-20261013.md).
S3 resolved each indexed safetensors shard; S4 checks **all**
H3/H4/H5/H6 symlinks, including tokenizer/config/other non-index
entries. Unknown absolute symlinks are never traversed. The probe checks
source-declared H6 RO mounts in serve.sh and builder alias constants, plus
collects filesystem type/free bytes. It **does not** verify actual Docker
bind mounts, reflink/CoW extents or reclaimable storage.

Run only after exact-new-HEAD GitHub CI SUCCESS:

~~~bash
set -Eeuo pipefail
SOURCE="$HOME/Workspace/llm/qwen3.8-flash-next-dgx-spark"
cd "$SOURCE"
test -z "$(git status --porcelain=v1 --untracked-files=all)"
git fetch origin feat/h38-managed-integration
TARGET="<VERIFIED_SUCCESS_CI_40_CHARACTER_SHA>"
test "$(git rev-parse FETCH_HEAD)" = "$TARGET"
AUDIT="$HOME/Workspace/llm/qwen38-s4-audit-$TARGET"
test ! -e "$AUDIT"
git worktree add --detach "$AUDIT" "$TARGET"
cd "$AUDIT"
test "$(git rev-parse HEAD)" = "$TARGET"
test -z "$(git status --porcelain=v1 --untracked-files=all)"
LOG="$HOME/dgx-hybrid-link-closure-$(date +%Y%m%d-%H%M%S).log"
QWEN38_RECLAIM_AUDIT_SHA="$TARGET" \
QWEN38_RECLAIM_MODELS_ROOT="$SOURCE/models" \
 python3 -B scripts/diagnostics/inspect-hybrid-link-closure.py \
 2>&1 | tee "$LOG"
echo "S4_LOG=$LOG"
~~~

Expected on complete reference resolution:

~~~text
SOURCE_MOUNT_CONTRACT=STATIC_PASS
ALL_LINK_REFERENCE_GAPS=0
ACTUAL_DOCKER_BIND_MOUNTS=NOT_VERIFIED
REFLINK_COW_SHARED_EXTENTS=NOT_MEASURED
RECLAIMABLE_BYTES=NOT_CERTIFIED
S4_LINK_CLOSURE=COLLECTED_READ_ONLY
MODEL_DELETION=BLOCKED_PENDING_EVIDENCE_AND_DEPENDENCY_REVIEW
~~~

A missing/unknown link gives COLLECTED_PARTIAL (rc 3). A preflight
or static source-contract failure returns INVALID (rc 2). Neither
means automatic repair or permission to delete. Keep H3/H4/mazinb
and the exact historical Docker predecessor, immutable release, swap
and memory protection unchanged. Benchmark raw JSON, reports, SHA256
and independent copy remain required before a separately authorized
selective cleanup.
