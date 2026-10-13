#!/usr/bin/env bash
# Only bounded historical systemd unit journal read; does not touch runtime.
# Intended to discriminate an exited legacy runtime, NOT to restart H38.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
TARGET="${QWEN38_STOP_JOURNAL_TARGET_SHA:-}"
UNIT="qwen38-flash-next.service"

invalid() {
  printf 'RUNTIME_STOP_JOURNAL_PREFLIGHT=INVALID reason=%s\n' "$*" >&2
  exit 2
}

[[ "$#" == 0 ]] || invalid 'unexpected_arguments'
[[ "${TARGET}" =~ ^[0-9a-f]{40}$ ]] || invalid 'exact_checkout_sha_required'
command -v git >/dev/null 2>&1 || invalid 'git_missing'
command -v journalctl >/dev/null 2>&1 || invalid 'journalctl_missing'
command -v date >/dev/null 2>&1 || invalid 'date_missing'
[[ "$(git -C "${ROOT}" rev-parse HEAD)" == "${TARGET}" ]] ||
  invalid 'checkout_sha_mismatch'
[[ -z "$(git -C "${ROOT}" status --porcelain=v1 --untracked-files=all)" ]] ||
  invalid 'dirty_checkout'
[[ "$(date +%z)" == +0900 ]] || invalid 'expected_host_timezone_asia_seoul'

printf 'RUNTIME_STOP_JOURNAL_PREFLIGHT=BEGIN\n'
printf 'checkout_sha=%s\n' "${TARGET}"
printf 'timezone=Asia/Seoul(+0900)\n'
printf 'unit=%s\n' "${UNIT}"
printf 'window_kst=2026-10-07T21:55:00+09:00_to_2026-10-07T22:25:00+09:00\n'
printf 'scope=unit_journal_160_lines_max_read_only_no_service_or_model_mutation\n'
printf 'host_service_or_protection_mutation=NO\n'
printf 'gpu_or_model_launch=NO\n'
printf 'checkpoint_payload_read=NO\n'

printf '\n=== bounded_service_journal ===\n'
rc=0
# Capture only the configured unit and 30-minute window. awk streams records
# without temporary files and treats empty output as an inconclusive read.
journalctl --no-pager --quiet --unit "${UNIT}" \
  --since "2026-10-07 21:55:00" --until "2026-10-07 22:25:00" \
  --lines 160 --output short-iso-precise |
  awk '{print} END {if (NR == 0) exit 4}' || rc="$?"

printf '\n=== FINAL RESULT ===\n'
printf 'HEAD=%s\n' "$(git -C "${ROOT}" rev-parse HEAD)"
printf 'journal_read_rc=%s\n' "${rc}"
printf 'RUNTIME_STOP_CAUSE=NOT_YET_CLASSIFIED\n'
printf 'RUNTIME_RESTART_OR_MODEL_LAUNCH=BLOCKED\n'
printf 'MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED\n'
if (( rc == 0 )); then
  printf 'RUNTIME_STOP_JOURNAL=COLLECTED_READ_ONLY\n'
  exit 0
fi
printf 'RUNTIME_STOP_JOURNAL=INCONCLUSIVE_OR_READ_FAILURE\n'
exit 3
