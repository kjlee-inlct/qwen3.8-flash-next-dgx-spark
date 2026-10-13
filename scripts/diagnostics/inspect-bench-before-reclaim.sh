#!/usr/bin/env bash
# Exact-SHA read-only inventory before any benchmark-evidence-preserving reclaim.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
TARGET="${QWEN38_RECLAIM_AUDIT_SHA:-}"
error() { printf 'RECLAIM_READONLY_PREFLIGHT=INVALID reason=%s\n' "$*" >&2; exit 2; }

[[ $# -eq 0 ]] || error unexpected_arguments
[[ "$TARGET" =~ ^[0-9a-f]{40}$ ]] || error exact_checkout_sha_required
for bin in git bash docker df; do
  command -v "$bin" >/dev/null 2>&1 || error "missing_command:$bin"
done
[[ "$(git -C "$ROOT" rev-parse HEAD)" == "$TARGET" ]] || error checkout_sha_mismatch
[[ -z "$(git -C "$ROOT" status --porcelain=v1 --untracked-files=all)" ]] ||
  error dirty_checkout
for file in "$ROOT/scripts/manage-storage.sh" "$ROOT/scripts/manage-models.sh"; do
  [[ -r "$file" ]] || error "missing_existing_manager:$file"
done

printf 'RECLAIM_READONLY=BEGIN\nCHECKOUT_SHA=%s\n' "$TARGET"
printf 'BENCHMARK_STATUS=NOT_ATTESTED\nMODEL_RUNTIME_START=NO\nHOST_DELETION=NO\n'
overall=0
check() {
  local name="$1" rc=0
  shift
  printf '\n=== %s ===\n' "$name"
  "$@" || rc="$?"
  printf 'RECLAIM_CHECK=%s rc=%s\n' "$name" "$rc"
  [[ "$rc" -eq 0 ]] || overall=1
}
check filesystem df -h -- "$HOME"
check storage_status bash "$ROOT/scripts/manage-storage.sh" status
check storage_recommend bash "$ROOT/scripts/manage-storage.sh" recommend
check storage_plan_preview bash "$ROOT/scripts/manage-storage.sh" plan
check managed_model_assets bash "$ROOT/scripts/manage-models.sh" assets
check docker_disk_accounting docker system df -v
check docker_image_identity docker image ls \
  --digests --format '{{.Repository}}:{{.Tag}} {{.ID}} {{.Size}} {{.Digest}}'
check docker_container_identity docker ps -a \
  --format '{{.ID}} {{.Image}} {{.Status}} {{.Names}}'

if [[ "$(git -C "$ROOT" rev-parse HEAD)" != "$TARGET" ]] ||
   [[ -n "$(git -C "$ROOT" status --porcelain=v1 --untracked-files=all)" ]]; then
  error checkout_changed_or_dirty_after
fi
if [[ "$overall" -ne 0 ]]; then
  printf 'RECLAIM_READONLY=PARTIAL_CHECK_FAILURE\nMODEL_OR_DOCKER_DELETION=BLOCKED\n'
  exit 3
fi
printf 'RECLAIM_READONLY=COLLECTED\n'
printf 'BENCHMARK_BEFORE_RECLAIM=REQUIRED\n'
printf 'MODEL_OR_DOCKER_DELETION=BLOCKED_PENDING_MODEL_EVIDENCE_AND_ASSET_REVIEW\n'
