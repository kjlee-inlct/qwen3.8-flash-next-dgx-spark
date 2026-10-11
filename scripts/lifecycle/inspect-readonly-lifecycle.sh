#!/usr/bin/env bash
# Collect only read-only managed install/profile/transaction diagnostics.
# No installation, purge, service restart, GPU/model launch or host edits.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
TARGET="${QWEN38_LIFECYCLE_AUDIT_TARGET_SHA:-}"

invalid() {
  printf 'MANAGED_LIFECYCLE_READONLY_PREFLIGHT=INVALID reason=%s\n' "$*" >&2
  exit 2
}

[[ "$#" == 0 ]] || invalid 'unexpected_arguments'
[[ "${TARGET}" =~ ^[0-9a-f]{40}$ ]] || invalid 'exact_checkout_sha_required'
command -v git >/dev/null 2>&1 || invalid 'git_missing'
[[ "$(git -C "${ROOT}" rev-parse HEAD)" == "${TARGET}" ]] ||
  invalid 'checkout_sha_mismatch'
[[ -z "$(git -C "${ROOT}" status --porcelain=v1 --untracked-files=all)" ]] ||
  invalid 'dirty_checkout'

declare -ra COMMANDS=(
  "${ROOT}/install.sh"
  "${ROOT}/scripts/doctor.sh"
  "${ROOT}/scripts/profile-switch-transition.sh"
  "${ROOT}/scripts/runtime-transition.sh"
  "${ROOT}/scripts/update-transition.sh"
  "${ROOT}/scripts/release-profile-refresh-transition.sh"
)
for item in "${COMMANDS[@]}"; do
  [[ -r "${item}" ]] || invalid "missing_script:${item}"
done

printf 'MANAGED_LIFECYCLE_READONLY_PREFLIGHT=BEGIN\n'
printf 'checkout_sha=%s\n' "${TARGET}"
printf 'scope=read_only_inventory_transaction_status_doctor_no_mutation\n'
printf 'host_mutation=NO\nmodel_or_gpu_launch=NO\n'
printf 'no_install_uninstall_or_purge=YES\n'

overall=0
check() {
  local name="$1" rc=0
  shift
  printf '\n=== %s ===\n' "${name}"
  "$@" || rc="$?"
  printf 'READONLY_CHECK=%s rc=%s\n' "${name}" "${rc}"
  if [[ "${rc}" -ne 0 ]]; then
    overall=1
  fi
}

check model_inventory bash "${ROOT}/install.sh" --list-models
check backend_registry bash "${ROOT}/install.sh" --list-backends
check profile_switch_status bash "${ROOT}/scripts/profile-switch-transition.sh" status
check runtime_transition_status bash "${ROOT}/scripts/runtime-transition.sh" status
check update_transition_status bash "${ROOT}/scripts/update-transition.sh" status
check release_profile_refresh_status bash "${ROOT}/scripts/release-profile-refresh-transition.sh" status
check doctor_readonly bash "${ROOT}/scripts/doctor.sh"

printf '\n=== FINAL RESULT ===\n'
printf 'HEAD=%s\n' "$(git -C "${ROOT}" rev-parse HEAD)"
if [[ "${overall}" == 0 ]]; then
  printf 'MANAGED_LIFECYCLE_READONLY=COLLECTED_READ_ONLY\n'
  printf 'MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED\n'
  exit 0
fi
printf 'MANAGED_LIFECYCLE_READONLY=PARTIAL_CHECK_FAILURE\n'
printf 'MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED\n'
exit 3
