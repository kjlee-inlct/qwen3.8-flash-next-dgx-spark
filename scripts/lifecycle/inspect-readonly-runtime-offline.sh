#!/usr/bin/env bash
# Read-only failure discrimination after a stopped managed runtime Doctor.
# Never starts a container/service, reads model weights, changes monitor state,
# or treats missing runtime-commit attestation as permission to fabricate it.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
TARGET="${QWEN38_OFFLINE_DIAGNOSTIC_TARGET_SHA:-}"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
CONTAINER="qwen38-flash-next"
UNIT="qwen38-flash-next.service"

invalid() {
  printf 'MANAGED_RUNTIME_OFFLINE_PREFLIGHT=INVALID reason=%s\n' "$*" >&2
  exit 2
}

[[ "$#" == 0 ]] || invalid 'unexpected_arguments'
[[ "${TARGET}" =~ ^[0-9a-f]{40}$ ]] || invalid 'exact_checkout_sha_required'
command -v git >/dev/null 2>&1 || invalid 'git_missing'
[[ "$(git -C "${ROOT}" rev-parse HEAD)" == "${TARGET}" ]] ||
  invalid 'checkout_sha_mismatch'
[[ -z "$(git -C "${ROOT}" status --porcelain=v1 --untracked-files=all)" ]] ||
  invalid 'dirty_checkout'
for command_name in docker systemctl stat; do
  command -v "${command_name}" >/dev/null 2>&1 ||
    invalid "missing_readonly_command:${command_name}"
done

printf 'MANAGED_RUNTIME_OFFLINE_PREFLIGHT=BEGIN\n'
printf 'checkout_sha=%s\n' "${TARGET}"
printf 'scope=readonly_container_state_service_state_file_metadata_no_restart\n'
printf 'gpu_or_model_launch=NO\n'
printf 'install_uninstall_purge=NO\n'
printf 'host_service_or_protection_mutation=NO\n'

overall=0
check() {
  local name="$1" rc=0
  shift
  printf '\n=== %s ===\n' "${name}"
  "$@" || rc="$?"
  printf 'OFFLINE_CHECK=%s rc=%s\n' "${name}" "${rc}"
  if (( rc != 0 )); then overall=1; fi
}

check container_state docker inspect \
  --format 'status={{.State.Status}} exit_code={{.State.ExitCode}} oom_killed={{.State.OOMKilled}} started={{.State.StartedAt}} finished={{.State.FinishedAt}} state_error={{json .State.Error}}' \
  "${CONTAINER}"
check container_declared_bindings docker inspect \
  --format 'port_bindings={{json .HostConfig.PortBindings}} runtime_port_map={{json .NetworkSettings.Ports}}' \
  "${CONTAINER}"
check service_unit systemctl show "${UNIT}" --no-pager \
  --property=LoadState,ActiveState,SubState,Result,ExecMainCode,ExecMainStatus,InactiveEnterTimestamp,ActiveEnterTimestamp

printf '\n=== lifecycle_state_file_metadata ===\n'
for name in runtime-commit.env runtime-stop.env monitor.pid; do
  file="${STATE_DIR}/${name}"
  if [[ -e "${file}" || -L "${file}" ]]; then
    stat -c "state_file=${name} type=%F size=%s modified=%y" -- "${file}" ||
      overall=1
  else
    printf 'state_file=%s status=ABSENT\n' "${name}"
  fi
done

printf '\n=== FINAL RESULT ===\n'
printf 'HEAD=%s\n' "$(git -C "${ROOT}" rev-parse HEAD)"
printf 'RUNTIME_ATTESTATION_VALIDITY=NOT_PROVEN\n'
printf 'RUNTIME_STOP_REASON=NOT_YET_PROVEN\n'
printf 'H38_MODEL_GPU_RERUN=BLOCKED\n'
printf 'MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED\n'
if (( overall == 0 )); then
  printf 'MANAGED_RUNTIME_OFFLINE=COLLECTED_READ_ONLY\n'
  exit 0
fi
printf 'MANAGED_RUNTIME_OFFLINE=PARTIAL_READ_FAILURE\n'
exit 3
