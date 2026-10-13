# S3 DGX read-only runtime-link/index-shard survey

S2's actual 2026-10-13 result showed 319 symlinks and no hardlink file entries
across the selected six model directories. See
[dated S2 evidence](../scripts/benchmark/evidence/dgx-hybrid-block-accounting-readonly-20261013.md).
The source Hybrid builders use **container virtual mount aliases**, so the
script must not equate an on-host dangling absolute link to missing runtime
data. The following probe resolves only known builder-declared aliases and
examines **safetensors index JSON**, *not tensor contents*, Docker or GPU.

Run only on the real DGX using a clean **detached source worktree** from a
full 40-character commit SHA with **SUCCESS CI for exactly that SHA**.
Do not modify the production checkout. A successful survey is **not**
permission to delete H3/H4 or launch H6.

```bash
set -Eeuo pipefail
SOURCE="$HOME/Workspace/llm/qwen3.8-flash-next-dgx-spark"
cd "$SOURCE"
test -z "$(git status --porcelain=v1 --untracked-files=all)"
git fetch origin feat/h38-managed-integration
TARGET="<EXACT_40_CHAR_SUCCESS_CI_HEAD>"
test "$(git rev-parse FETCH_HEAD)" = "$TARGET"
AUDIT="$HOME/Workspace/llm/qwen38-s3-audit-$TARGET"
test ! -e "$AUDIT"
git worktree add --detach "$AUDIT" "$TARGET"
cd "$AUDIT"
test "$(git rev-parse HEAD)" = "$TARGET"
test -z "$(git status --porcelain=v1 --untracked-files=all)"
LOG="$HOME/dgx-hybrid-runtime-refs-$(date +%Y%m%d-%H%M%S).log"
QWEN38_RECLAIM_AUDIT_SHA="$TARGET" \
QWEN38_RECLAIM_MODELS_ROOT="$SOURCE/models" \
  python3 -B scripts/diagnostics/inspect-hybrid-runtime-references.py \
  2>&1 | tee "$LOG"
echo "S3_LOG=$LOG"
```

Expected when all staged links and index references match the currently known
container mount-alias model:

```text
S3_REFERENCE_SURVEY=COLLECTED_READ_ONLY
BENCHMARK_BEFORE_RECLAIM=REQUIRED
MODEL_DELETION=BLOCKED_PENDING_EVIDENCE_AND_DEPENDENCY_REVIEW
```

An unknown alias or missing referenced shard is
`COLLECTED_PARTIAL_UNMAPPED_REFERENCES` (exit 3), requiring investigation.
A preflight or concurrent-change failure is `INVALID` (exit 2).
The script does not prove actual Docker bind mounts or reflink/CoW
extent sharing, safetensors tensor integrity, successful model loading, or
host stability. Actual runtime mount contracts, on-disk physical extent
uniqueness, benchmark evidence, ownership, and independent backup
remain separate gates.

## Actual physical result (2026-10-13)

S3 was run successfully on the sole DGX after the exact-source CI succeeded.
`REFERENCE_GAPS=0` and `S3_REFERENCE_SURVEY=COLLECTED_READ_ONLY`;
all 81 H6 indexed shard filenames reached regular files through the known
runtime alias chain. [Actual operator evidence](../scripts/benchmark/evidence/dgx-hybrid-runtime-references-readonly-20261013.md).
The tool did **not** prove every non-index symlink's physical target,
live Docker binds or block independence. This newer evidence supersedes
the generic S3-not-yet-run description above without revising its
historical instructions. No benchmark or cleanup is authorized.

