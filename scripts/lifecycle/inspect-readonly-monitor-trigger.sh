#!/usr/bin/env bash
# Read only bounded local monitor.log numeric trigger samples from Oct 7.
# Does not import model code, start services, modify runtime state, or
# classify a true host OOM from a heuristic protected-stop signal.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
TARGET="${QWEN38_MONITOR_TRIGGER_TARGET_SHA:-}"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
LOG_FILE="${STATE_DIR}/monitor.log"
MAX_BYTES=$((64 * 1024 * 1024))

invalid() {
  printf 'MONITOR_TRIGGER_READONLY_PREFLIGHT=INVALID reason=%s\n' "$*" >&2
  exit 2
}

[[ "$#" == 0 ]] || invalid 'unexpected_arguments'
[[ "${TARGET}" =~ ^[0-9a-f]{40}$ ]] || invalid 'exact_checkout_sha_required'
command -v git >/dev/null 2>&1 || invalid 'git_missing'
command -v stat >/dev/null 2>&1 || invalid 'stat_missing'
command -v awk >/dev/null 2>&1 || invalid 'awk_missing'
[[ "$(git -C "${ROOT}" rev-parse HEAD)" == "${TARGET}" ]] ||
  invalid 'checkout_sha_mismatch'
[[ -z "$(git -C "${ROOT}" status --porcelain=v1 --untracked-files=all)" ]] ||
  invalid 'dirty_checkout'
[[ -f "${LOG_FILE}" && ! -L "${LOG_FILE}" && -r "${LOG_FILE}" ]] ||
  invalid 'monitor_log_absent_unsafe_or_unreadable'
size="$(stat -c %s -- "${LOG_FILE}")"
[[ "${size}" =~ ^[0-9]+$ ]] || invalid 'monitor_log_size_invalid'
(( size <= MAX_BYTES )) || invalid 'monitor_log_too_large_for_bounded_read'

printf 'MONITOR_TRIGGER_READONLY_PREFLIGHT=BEGIN\n'
printf 'checkout_sha=%s\n' "${TARGET}"
printf 'scope=oct07_local_monitor_numeric_trigger_lines_max_120_no_host_or_service_mutation\n'
printf 'source_bytes=%s\n' "${size}"
printf 'host_service_or_protection_mutation=NO\n'
printf 'gpu_or_model_launch=NO\n'
printf 'checkpoint_payload_read=NO\n'
printf '\n=== bounded_monitor_trigger_samples ===\n'

# Only monitor-runtime.sh's structured diagnostic messages; exclude arbitrary
# docker logs that may contain prompts, IDs, environment values or secrets.
# The monitor writes local "YYYY-MM-DD HH:MM:SS" timestamps (KST on DGX).
rc=0
awk '
  /^2026-10-07 22:(08|09|1[0-9]):[0-9][0-9] / &&
  / (monitor started:|WARNING memory margin low |HEARTBEAT healthy:|memory margin recovered:|PROTECT stopping |container is no longer running; monitor exiting)/ {
    if (++matched <= 120) print
  }
  END {
    printf "monitor_matching_lines=%d\n", matched+0
    if (matched == 0) exit 4
    if (matched > 120) printf "monitor_output_truncated=YES\n"
  }
' "${LOG_FILE}" || rc="$?"

printf '\n=== FINAL RESULT ===\n'
printf 'HEAD=%s\n' "$(git -C "${ROOT}" rev-parse HEAD)"
printf 'monitor_read_rc=%s\n' "${rc}"
printf 'MEMORY_PROTECTION_EVENT=ALREADY_CONFIRMED_BY_SERVICE_JOURNAL\n'
printf 'PROTECTION_THRESHOLD_CAUSE=NOT_YET_CLASSIFIED\n'
printf 'RUNTIME_RESTART_OR_MODEL_LAUNCH=BLOCKED\n'
printf 'MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED\n'
if (( rc == 0 )); then
  printf 'MONITOR_TRIGGER_READONLY=COLLECTED_READ_ONLY\n'
  exit 0
fi
printf 'MONITOR_TRIGGER_READONLY=INCONCLUSIVE_OR_READ_FAILURE\n'
exit 3
