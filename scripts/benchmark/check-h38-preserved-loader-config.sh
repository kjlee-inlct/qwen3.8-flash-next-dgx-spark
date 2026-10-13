#!/usr/bin/env bash
# Historical launch-configuration inspection ONLY; no Docker/model invocation.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
INSPECTOR="${ROOT}/scripts/benchmark/inspect-h38-preserved-loader-config.py"
TARGET="${H38_PRESERVED_LOADER_TARGET_SHA:-}"
ARCHIVE_DIR="${H38_PRESERVED_LOADER_ARCHIVE_DIR:-}"

fail() {
  printf 'H38_PRESERVED_LOADER_PREFLIGHT=INVALID reason=%s\n' "$*" >&2
  exit 2
}
[[ "$#" == 0 ]] || fail 'unexpected_arguments'
[[ "${TARGET}" =~ ^[0-9a-f]{40}$ ]] || fail 'exact_checkout_sha_required'
[[ -n "${ARCHIVE_DIR}" && "${ARCHIVE_DIR}" == /* ]] ||
  fail 'absolute_preserved_archive_dir_required'
[[ -r "${INSPECTOR}" ]] || fail 'inspector_missing'
command -v git >/dev/null 2>&1 || fail 'git_missing'
command -v python3 >/dev/null 2>&1 || fail 'python3_missing'
[[ "$(git -C "${ROOT}" rev-parse HEAD)" == "${TARGET}" ]] ||
  fail 'checkout_sha_mismatch'
[[ -z "$(git -C "${ROOT}" status --porcelain=v1 --untracked-files=all)" ]] ||
  fail 'dirty_checkout'
[[ -d "${ARCHIVE_DIR}" && ! -L "${ARCHIVE_DIR}" ]] ||
  fail 'preserved_archive_not_available'

printf 'H38_PRESERVED_LOADER_PREFLIGHT=BEGIN\n'
printf 'repository_sha=%s\n' "${TARGET}"
printf 'scope=existing_archive_only_no_docker_no_model_no_gpu_no_service\n'
python3 -B "${INSPECTOR}" --archive-dir "${ARCHIVE_DIR}" ||
  fail 'archived_launch_identity_or_source_invalid'
printf 'H38_PRESERVED_LOADER_PREFLIGHT=PASS_ARCHIVED_LAUNCH_FLAGS_ONLY\n'
