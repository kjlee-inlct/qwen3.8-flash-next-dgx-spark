#!/usr/bin/env bash
# Safe, selective Hugging Face model-cache inspection and removal.
set -Eeuo pipefail

HF_CACHE="${HF_HOME:-$HOME/.cache/huggingface}"
HF_HUB="${HF_CACHE}/hub"
ACTION="${1:-list}"
TARGET="${2:-}"
YES=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage:
  hf-cache.sh list
  hf-cache.sh remove models--ORG--MODEL [--dry-run] [--yes]

Only direct model-cache directories under $HF_HOME/hub named models--* are eligible.
The helper never deletes the whole Hugging Face cache, never follows a symlink target,
and never invokes sudo. A cache containing files not owned by the current user is
refused before deletion to avoid a partial cleanup.
EOF
}

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

case "${ACTION}" in
  list)
    shift || true
    ;;
  remove)
    [[ -n "${TARGET}" ]] || die "remove requires a cache directory name"
    shift 2
    ;;
  -h|--help|help)
    usage
    exit 0
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes) YES=1 ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
  shift
done

human_du() {
  local path="$1"
  du -sh -- "$path" 2>/dev/null | awk '{print $1}' || printf '?'
}

list_models() {
  printf 'Hugging Face model cache directories\n'
  printf '  root: %s\n' "${HF_HUB}"
  [[ -d "${HF_HUB}" ]] || { printf '  (hub cache not present)\n'; return 0; }

  local found=0 path name
  while IFS= read -r -d '' path; do
    found=1
    name="$(basename -- "$path")"
    printf '  %8s  %s\n' "$(human_du "$path")" "$name"
  done < <(find "${HF_HUB}" -mindepth 1 -maxdepth 1 -type d -name 'models--*' -print0 2>/dev/null | sort -z)
  [[ "${found}" == 1 ]] || printf '  (none found)\n'
}

validate_target() {
  [[ "${TARGET}" == models--* ]] || die "target must be a direct models--* cache directory name"
  [[ "${TARGET}" != */* && "${TARGET}" != *..* ]] || die "target must not contain path traversal"
  CACHE_PATH="${HF_HUB}/${TARGET}"
  [[ -e "${CACHE_PATH}" || -L "${CACHE_PATH}" ]] || die "cache target not found: ${CACHE_PATH}"
  [[ ! -L "${CACHE_PATH}" ]] || die "refusing symlink cache target: ${CACHE_PATH}"
  [[ -d "${CACHE_PATH}" ]] || die "cache target is not a directory: ${CACHE_PATH}"

  local canonical_hub canonical_target
  canonical_hub="$(realpath -m -- "${HF_HUB}")"
  canonical_target="$(realpath -m -- "${CACHE_PATH}")"
  [[ "${canonical_target}" == "${canonical_hub}/"* ]] || die "cache target escapes Hugging Face hub"
  [[ "$(dirname -- "${canonical_target}")" == "${canonical_hub}" ]] || die "cache target must be directly under the Hugging Face hub"
  CACHE_PATH="${canonical_target}"
}

check_ownership() {
  local foreign
  foreign="$(find "${CACHE_PATH}" -xdev ! -uid "$(id -u)" -print -quit 2>/dev/null || true)"
  if [[ -n "${foreign}" ]]; then
    printf 'ERROR: cache contains entries not owned by uid %s; refusing partial deletion.\n' "$(id -u)" >&2
    printf '  first foreign-owned entry: %s\n' "${foreign}" >&2
    printf '  inspect ownership first; this helper never invokes sudo.\n' >&2
    exit 1
  fi
}

remove_model() {
  validate_target
  check_ownership
  printf 'Hugging Face cache removal candidate\n'
  printf '  name : %s\n' "${TARGET}"
  printf '  path : %s\n' "${CACHE_PATH}"
  printf '  size : %s\n' "$(human_du "${CACHE_PATH}")"

  if [[ "${DRY_RUN}" == 1 ]]; then
    printf 'DRY-RUN: rm -rf --one-file-system -- %q\n' "${CACHE_PATH}"
    return 0
  fi

  if [[ "${YES}" != 1 ]]; then
    read -r -p 'Type DELETE to permanently remove this Hugging Face model cache: ' answer
    [[ "${answer}" == DELETE ]] || die "cancelled"
  fi

  rm -rf --one-file-system -- "${CACHE_PATH}"
  [[ ! -e "${CACHE_PATH}" ]] || die "cache path still exists after removal: ${CACHE_PATH}"
  printf 'Removed Hugging Face model cache: %s\n' "${CACHE_PATH}"
}

case "${ACTION}" in
  list) list_models ;;
  remove) remove_model ;;
esac
