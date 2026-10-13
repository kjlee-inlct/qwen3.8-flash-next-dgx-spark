#!/usr/bin/env bash
# Read-only exact-SHA physical byte-accounting for the known six DGX model trees.
# Does NOT classify any model safe-to-delete, load a model or modify assets.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
TARGET="${QWEN38_RECLAIM_AUDIT_SHA:-}"
MODELS_ROOT="${QWEN38_RECLAIM_MODELS_ROOT:-}"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
MANIFEST="$STATE_DIR/install.env"
OWNERSHIP="$STATE_DIR/asset-ownership.json"
CURRENT="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark/current"

stop() { printf 'RECLAIM_BLOCK_ACCOUNTING=INVALID reason=%s\n' "$*" >&2; exit 2; }
[[ $# -eq 0 ]] || stop unexpected_arguments
[[ "$TARGET" =~ ^[0-9a-f]{40}$ ]] || stop exact_checkout_sha_required
[[ "$MODELS_ROOT" == /* && -d "$MODELS_ROOT" && ! -L "$MODELS_ROOT" ]] ||
  stop explicit_real_models_root_required
for bin in git du find stat realpath readlink sha256sum awk; do
  command -v "$bin" >/dev/null 2>&1 || stop "missing_command:$bin"
done
[[ "$(git -C "$ROOT" rev-parse HEAD)" == "$TARGET" ]] ||
  stop checkout_sha_mismatch
[[ -z "$(git -C "$ROOT" status --porcelain=v1 --untracked-files=all)" ]] ||
  stop dirty_checkout
MODELS_ROOT="$(realpath -e -- "$MODELS_ROOT")"
[[ ! -L "$MANIFEST" && -f "$MANIFEST" ]] || stop missing_non_symlink_manifest
[[ ! -L "$OWNERSHIP" ]] || stop unsafe_ownership_symlink
[[ -L "$CURRENT" ]] || stop current_immutable_release_link_missing

# Never interpret a temporary source-worktree's model/ symlink as the true
# active installed model root. Caller must supply the real path explicitly.
dirs=(
  "$MODELS_ROOT/qwen3.8-flash-next-orcarouter"
  "$MODELS_ROOT/qwen3.8-flash-next-mazinb"
  "$MODELS_ROOT/qwen3.8-hybrid-quant-layout"
  "$MODELS_ROOT/qwen3.8-h4-orca-all"
  "$MODELS_ROOT/qwen3.8-h5-neutral-input-scale"
  "$MODELS_ROOT/qwen3.8-h6-modelopt-w4a16"
)
for path in "${dirs[@]}"; do
  [[ -d "$path" && ! -L "$path" ]] || stop "missing_non_symlink_candidate:$(basename -- "$path")"
  [[ -f "$path/.qwen38-model-manifest.json" ||
     -f "$path/.qwen38-hybrid-manifest.json" ]] ||
    stop "missing_candidate_manifest:$(basename -- "$path")"
done
fingerprint() {
  if [[ -f "$1" ]]; then sha256sum -- "$1" | awk '{print $1}'
  elif [[ -e "$1" || -L "$1" ]]; then printf NOT_REGULAR
  else printf ABSENT
  fi
}
manifest_before="$(fingerprint "$MANIFEST")"
ownership_before="$(fingerprint "$OWNERSHIP")"
release_before="$(readlink -f -- "$CURRENT")"

printf 'RECLAIM_BLOCK_ACCOUNTING=BEGIN\nSOURCE_SHA=%s\n' "$TARGET"
printf 'MODEL_ROOT=%s\nHOST_MUTATION=NO\nMODEL_START=NO\n' "$MODELS_ROOT"
printf 'PROVENANCE_WARNING=BLOCK_COUNTS_ARE_NOT_CERTIFIED_RECLAIMABLE_BYTES\n'
printf 'BENCHMARK_EVIDENCE=NOT_VERIFIED\n'
printf '\n=== PER_DIRECTORY_ALLOCATED_BLOCKS_BYTES ===\n'
for path in "${dirs[@]}"; do
  printf 'MODEL_DIR=%s\n' "$(basename -- "$path")"
  du -sxB1 -- "$path"
  printf 'FILE_HARDLINK_ENTRIES='
  find "$path" -xdev -type f -links +1 -printf . | wc -c
  printf 'SYMLINK_ENTRIES='
  find "$path" -xdev -type l -printf . | wc -c
  printf 'MODEL_DIR_RESULT=COLLECTED\n'
done
printf '\n=== MULTI_PATH_DEDUPLICATED_BY_INODE_WITHIN_SELECTED_TREES ===\n'
# du counts hard links across all arguments once but cannot detect filesystem
# copy-on-write shared extents, snapshots, reflinks or external references.
du -scxB1 -- "${dirs[@]}"
printf '\n=== FILESYSTEM_DEVICE_IDENTITIES ===\n'
for path in "${dirs[@]}"; do
  stat -c 'FS_DEVICE=%d MODEL_DIR=%n' -- "$path"
done
[[ "$(fingerprint "$MANIFEST")" == "$manifest_before" ]] ||
  stop manifest_changed
[[ "$(fingerprint "$OWNERSHIP")" == "$ownership_before" ]] ||
  stop ownership_changed
[[ "$(readlink -f -- "$CURRENT")" == "$release_before" ]] ||
  stop immutable_release_changed
[[ "$(git -C "$ROOT" rev-parse HEAD)" == "$TARGET" ]] ||
  stop source_changed
[[ -z "$(git -C "$ROOT" status --porcelain=v1 --untracked-files=all)" ]] ||
  stop dirty_checkout_after

printf 'RECLAIM_BLOCK_ACCOUNTING=COLLECTED_READ_ONLY\n'
printf 'BENCHMARK_BEFORE_RECLAIM=REQUIRED\n'
printf 'MODEL_DELETION=BLOCKED_PENDING_DEPENDENCY_AND_EVIDENCE_REVIEW\n'
