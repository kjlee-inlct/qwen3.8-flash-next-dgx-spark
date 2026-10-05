#!/usr/bin/env bash
set -Eeuo pipefail

CONTAINER="${CONTAINER:-qwen38-flash-next}"
MIN_AGE="${MIN_AGE:-2700}"
INTERVAL="${INTERVAL:-30}"
REPORT_INTERVAL="${REPORT_INTERVAL:-60}"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/wait-runtime-age.sh [--container NAME] [--min-age SEC] [--interval SEC] [--report-interval SEC]

Wait until one specific running container reaches the requested runtime age.
The waiter pins the initial container ID and StartedAt value; if the container
stops, disappears, or is replaced while waiting, it fails instead of silently
following the replacement.

Defaults:
  container       qwen38-flash-next
  min-age         2700 seconds
  interval        30 seconds
  report-interval 60 seconds
EOF
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --container)
      [[ $# -ge 2 ]] || die "--container requires a value"
      CONTAINER="$2"
      shift
      ;;
    --min-age)
      [[ $# -ge 2 ]] || die "--min-age requires seconds"
      MIN_AGE="$2"
      shift
      ;;
    --interval)
      [[ $# -ge 2 ]] || die "--interval requires seconds"
      INTERVAL="$2"
      shift
      ;;
    --report-interval)
      [[ $# -ge 2 ]] || die "--report-interval requires seconds"
      REPORT_INTERVAL="$2"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
  shift
done

[[ "${MIN_AGE}" =~ ^[0-9]+$ ]] || die "--min-age must be a non-negative integer"
[[ "${INTERVAL}" =~ ^[1-9][0-9]*$ ]] || die "--interval must be a positive integer"
[[ "${REPORT_INTERVAL}" =~ ^[1-9][0-9]*$ ]] || die "--report-interval must be a positive integer"

for command in docker date python3 sleep; do
  command -v "${command}" >/dev/null 2>&1 || die "${command} is required"
done

inspect_container() {
  docker inspect \
    --format '{{.Id}} {{.State.Status}} {{.State.StartedAt}}' \
    "${CONTAINER}" 2>/dev/null
}

if ! read -r initial_id initial_state initial_started < <(inspect_container); then
  die "container not found: ${CONTAINER}"
fi
[[ -n "${initial_id}" && -n "${initial_started}" ]] || die "container inspection returned incomplete state"
[[ "${initial_state}" == running ]] || die "container is not running: ${CONTAINER} state=${initial_state}"

started_epoch="$({ python3 - "${initial_started}" <<'PY'
import datetime as dt
import sys

value = sys.argv[1]
try:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
except ValueError as exc:
    raise SystemExit(f"invalid StartedAt timestamp: {value}: {exc}")
if parsed.tzinfo is None:
    raise SystemExit(f"StartedAt timestamp has no timezone: {value}")
print(int(parsed.timestamp()))
PY
} 2>/dev/null)" || die "cannot parse container StartedAt: ${initial_started}"
[[ "${started_epoch}" =~ ^-?[0-9]+$ ]] || die "invalid parsed StartedAt epoch"

printf 'WAIT_RUNTIME_AGE_BEGIN container=%s id=%s started=%s min_age_s=%s\n' \
  "${CONTAINER}" "${initial_id}" "${initial_started}" "${MIN_AGE}"

next_report_age=0
while :; do
  if ! read -r current_id current_state current_started < <(inspect_container); then
    die "container disappeared while waiting: ${CONTAINER}"
  fi
  [[ "${current_id}" == "${initial_id}" ]] \
    || die "container replaced while waiting: initial=${initial_id} current=${current_id}"
  [[ "${current_started}" == "${initial_started}" ]] \
    || die "container StartedAt changed while waiting: initial=${initial_started} current=${current_started}"
  [[ "${current_state}" == running ]] \
    || die "container stopped while waiting: ${CONTAINER} state=${current_state}"

  now_epoch="$(date +%s)"
  [[ "${now_epoch}" =~ ^[0-9]+$ ]] || die "date +%s returned an invalid value"
  age=$((now_epoch - started_epoch))
  (( age >= 0 )) || die "container StartedAt is in the future"

  if (( age >= MIN_AGE )); then
    printf 'WAIT_RUNTIME_AGE_READY container=%s id=%s age_s=%d min_age_s=%s\n' \
      "${CONTAINER}" "${initial_id}" "${age}" "${MIN_AGE}"
    exit 0
  fi

  remaining=$((MIN_AGE - age))
  if (( age >= next_report_age )); then
    printf 'waiting... container=%s age_s=%d remaining_s=%d target_s=%s\n' \
      "${CONTAINER}" "${age}" "${remaining}" "${MIN_AGE}"
    next_report_age=$((age + REPORT_INTERVAL))
  fi

  sleep_for="${INTERVAL}"
  if (( remaining < sleep_for )); then
    sleep_for="${remaining}"
  fi
  (( sleep_for >= 1 )) || sleep_for=1
  sleep "${sleep_for}"
done
