#!/usr/bin/env bash
# Monitor DGX Spark unified memory with CMA-aware host-protection margins.
set -euo pipefail

CONTAINER="qwen38-flash-next"
MIN_AVAILABLE_GIB=6
MIN_FREE_GIB=2
FREE_GATE_GIB=10
MIN_SWAP_FREE_GIB=8
SWAP_ACTIVITY_GATE_MIB=256
CONSECUTIVE=5
INTERVAL=2
HEARTBEAT=60
PROTECT=0
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STOP_REASON_FILE="${STATE_DIR}/runtime-stop.env"
MEMINFO_PATH="${QWEN38_MEMINFO_PATH:-/proc/meminfo}"
EXPECTED_ID=""
WAIT_RUNNING=0
ARMED_FILE=""
HEARTBEAT_FILE=""
TRIAL_ARMED=0
TRIAL_RUNTIME_LIMIT=3600  # 60-minute upper bound; only enforced for pinned trials
TRIAL_RUNNING_START=0

# A pinned trial must not outlive its *own* monitor on a catchable exit.
# Normal managed monitor sessions without --expected-id are unchanged.
trial_fail_closed_on_monitor_exit() {
  local previous_rc=$? snapshot="" attempt
  trap - EXIT
  [[ "${TRIAL_ARMED}" == 1 && -n "${EXPECTED_ID}" ]] || return 0
  for attempt in 1 2 3; do
    snapshot="$(docker inspect --format '{{.Id}}|{{.State.Running}}|{{index .Config.Labels "qwen38.abtrial"}}|{{index .Config.Labels "qwen38.predecessor"}}' "${EXPECTED_ID}" 2>/dev/null || true)"
    [[ -n "${snapshot}" ]] && break
    sleep 1
  done
  if [[ "${snapshot}" == "${EXPECTED_ID}|true|orcarouter|"* ||
      "${snapshot}" == "${EXPECTED_ID}|true|mazinb|"* ]]; then
    printf '%s TRIAL WATCHDOG EXIT (rc=%s): stopping exact candidate %s, preserving Docker object\n' "$(date '+%F %T')" "${previous_rc}" "${EXPECTED_ID}" >&2
    if ! docker stop --timeout 30 "${EXPECTED_ID}" >/dev/null; then
      printf 'ERROR: pinned trial stop failed after watchdog exited; immediate manual intervention required for ID %s\n' "${EXPECTED_ID}" >&2
    fi
  elif [[ -z "${snapshot}" ]]; then
    printf 'ERROR: pinned watchdog exit could not inspect candidate ID %s; manually verify Docker state now\n' "${EXPECTED_ID}" >&2
  fi
}
trap trial_fail_closed_on_monitor_exit EXIT
trap 'exit 143' TERM
trap 'exit 130' INT

usage() {
  cat <<'EOF'
Usage: ./scripts/monitor-runtime.sh [options]
  --container NAME             Container to monitor (default: qwen38-flash-next)
  --min-available-gib N        Non-CMA available warning floor (default: 6)
  --min-free-gib N             Non-CMA free protection floor (default: 2)
  --free-gate-gib N            Non-CMA available gate for immediate low-free protection (default: 10)
  --min-swap-free-gib N        SwapFree protection floor (default: 8)
  --swap-activity-gate-mib N   Swap consumption since monitor start that arms high-available low-free protection (default: 256)
  --consecutive N              Consecutive low samples before protection (default: 5)
  --interval N                 Sampling interval in seconds (default: 2)
  --heartbeat N                Healthy status interval in seconds; 0 disables (default: 60)
  --protect                    Stop the container after consecutive low samples
  --expected-id ID             Pin exact 64-character trial Docker ID
  --wait-running N             Arm while created trial is not yet running
  --state-dir PATH             Separate absolute forensic state directory
  --armed-file PATH            Atomic arm confirmation file
  --heartbeat-file PATH        Atomic sample timestamp file
  --trial-max-seconds N        Stop pinned trial after N seconds (default: 3600; max: 7200)

Without --protect this tool only reports warnings and never changes the container.
EOF
}
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
positive_integer() { [[ "$1" =~ ^[1-9][0-9]*$ ]]; }
nonnegative_integer() { [[ "$1" =~ ^[0-9]+$ ]]; }
write_stop_reason() {
  local container_id="$1"
  mkdir -p "${STATE_DIR}"
  umask 077
  {
    printf 'RUNTIME_STOP_SCHEMA_VERSION=%q\n' 1
    printf 'STOP_REASON=%q\n' memory-protection
    printf 'STOP_CONTAINER_NAME=%q\n' "${CONTAINER}"
    printf 'STOP_CONTAINER_ID=%q\n' "${container_id}"
    printf 'UPDATED_AT=%q\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  } >"${STOP_REASON_FILE}.tmp"
  mv -- "${STOP_REASON_FILE}.tmp" "${STOP_REASON_FILE}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --container) [[ $# -ge 2 ]] || die "$1 requires a value"; CONTAINER="$2"; shift ;;
    --min-available-gib) [[ $# -ge 2 ]] || die "$1 requires a value"; MIN_AVAILABLE_GIB="$2"; shift ;;
    --min-free-gib) [[ $# -ge 2 ]] || die "$1 requires a value"; MIN_FREE_GIB="$2"; shift ;;
    --free-gate-gib) [[ $# -ge 2 ]] || die "$1 requires a value"; FREE_GATE_GIB="$2"; shift ;;
    --min-swap-free-gib) [[ $# -ge 2 ]] || die "$1 requires a value"; MIN_SWAP_FREE_GIB="$2"; shift ;;
    --swap-activity-gate-mib) [[ $# -ge 2 ]] || die "$1 requires a value"; SWAP_ACTIVITY_GATE_MIB="$2"; shift ;;
    --consecutive) [[ $# -ge 2 ]] || die "$1 requires a value"; CONSECUTIVE="$2"; shift ;;
    --interval) [[ $# -ge 2 ]] || die "$1 requires a value"; INTERVAL="$2"; shift ;;
    --heartbeat) [[ $# -ge 2 ]] || die "$1 requires a value"; HEARTBEAT="$2"; shift ;;
    --protect) PROTECT=1 ;;
    --expected-id) [[ $# -ge 2 ]] || die "$1 requires ID"; EXPECTED_ID="$2"; shift ;;
    --wait-running) [[ $# -ge 2 ]] || die "$1 requires seconds"; WAIT_RUNNING="$2"; shift ;;
    --state-dir) [[ $# -ge 2 ]] || die "$1 requires path"; STATE_DIR="$2"; STOP_REASON_FILE="${STATE_DIR}/runtime-stop.env"; shift ;;
    --armed-file) [[ $# -ge 2 ]] || die "$1 requires path"; ARMED_FILE="$2"; shift ;;
    --heartbeat-file) [[ $# -ge 2 ]] || die "$1 requires path"; HEARTBEAT_FILE="$2"; shift ;;
    --trial-max-seconds) [[ $# -ge 2 ]] || die "$1 requires seconds"; TRIAL_RUNTIME_LIMIT="$2"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
  shift
done
[[ -n "${CONTAINER}" && "${CONTAINER}" != */* ]] || die "invalid container name"
for value in "${MIN_AVAILABLE_GIB}" "${MIN_FREE_GIB}" "${FREE_GATE_GIB}" "${MIN_SWAP_FREE_GIB}" "${SWAP_ACTIVITY_GATE_MIB}" "${CONSECUTIVE}" "${INTERVAL}"; do
  positive_integer "${value}" || die "thresholds and intervals must be positive integers"
done
nonnegative_integer "${HEARTBEAT}" || die "heartbeat must be a non-negative integer"
nonnegative_integer "${WAIT_RUNNING}" || die "wait-running must be a non-negative integer"
positive_integer "${TRIAL_RUNTIME_LIMIT}" || die "trial runtime limit must be a positive integer"
(( TRIAL_RUNTIME_LIMIT <= 7200 )) || die "trial runtime limit must be at most 7200 seconds"
[[ -z "${EXPECTED_ID}" || "${EXPECTED_ID}" =~ ^[a-f0-9]{64}$ ]] || die "invalid expected trial ID"
if [[ -n "${EXPECTED_ID}" ]]; then
  [[ -n "${ARMED_FILE}" && -n "${HEARTBEAT_FILE}" && "${WAIT_RUNNING}" -gt 0 && "${PROTECT}" == 1 ]] ||
    die "pinned trial monitor requires arm, heartbeat, wait-running and protect"
fi
for path in "${STATE_DIR}" "${ARMED_FILE}" "${HEARTBEAT_FILE}"; do
  [[ -z "${path}" || "${path}" == /* ]] || die "monitor state path must be absolute"
  [[ -z "${path}" || ! -L "${path}" ]] || die "monitor state path cannot be symlink"
done
command -v docker >/dev/null || die "docker is required"
[[ -r "${MEMINFO_PATH}" ]] || die "meminfo is unavailable: ${MEMINFO_PATH}"
docker inspect "${CONTAINER}" >/dev/null 2>&1 || die "container not found: ${CONTAINER}"
if [[ -n "${EXPECTED_ID}" ]]; then
  actual_id="$(docker inspect --format '{{.Id}}' "${CONTAINER}")"
  [[ "${actual_id}" == "${EXPECTED_ID}" ]] || die "trial container ID drift before arm"
  [[ -d "${STATE_DIR}" && ! -L "${STATE_DIR}" ]] || die "separate monitor state directory missing or unsafe"
fi
if [[ -n "${ARMED_FILE}" ]]; then
  umask 077
  printf '%s\n' "${EXPECTED_ID}" >"${ARMED_FILE}.tmp"
  mv -- "${ARMED_FILE}.tmp" "${ARMED_FILE}"
  TRIAL_ARMED=1
  printf 'AB_MONITOR_ARMED_ID=%s\n' "${EXPECTED_ID}"
fi
if (( WAIT_RUNNING > 0 )); then
  for (( count=0; count<WAIT_RUNNING; count++ )); do
    [[ -z "${EXPECTED_ID}" || "$(docker inspect --format '{{.Id}}' "${CONTAINER}" 2>/dev/null || true)" == "${EXPECTED_ID}" ]] ||
      die "trial ID drift while waiting for start"
    [[ "$(docker inspect -f '{{.State.Running}}' "${CONTAINER}" 2>/dev/null || true)" != true ]] || break
    sleep 1
  done
  [[ "$(docker inspect -f '{{.State.Running}}' "${CONTAINER}" 2>/dev/null || true)" == true ]] ||
    die "trial never became running while monitor armed"
fi

available_floor=$((MIN_AVAILABLE_GIB * 1048576))
free_floor=$((MIN_FREE_GIB * 1048576))
free_gate=$((FREE_GATE_GIB * 1048576))
swap_free_floor=$((MIN_SWAP_FREE_GIB * 1048576))
swap_activity_gate=$((SWAP_ACTIVITY_GATE_MIB * 1024))
initial_swap_free="$(awk '$1=="SwapFree:" {print $2}' "${MEMINFO_PATH}")"
[[ -n "${initial_swap_free}" ]] || die "SwapFree is missing from ${MEMINFO_PATH}"
low_count=0
warning_active=0
mode="warn-only"; [[ "${PROTECT}" == 1 ]] && mode="protect"
TRIAL_RUNNING_START="${SECONDS}"
printf '%s monitor started: container=%s mode=%s available-warn=%sGiB noncma-free=%sGiB free-gate=%sGiB swap-growth=%sMiB swapfree=%sGiB\n' \
  "$(date '+%F %T')" "${CONTAINER}" "${mode}" "${MIN_AVAILABLE_GIB}" "${MIN_FREE_GIB}" "${FREE_GATE_GIB}" "${SWAP_ACTIVITY_GATE_MIB}" "${MIN_SWAP_FREE_GIB}"
next_heartbeat=$((SECONDS + HEARTBEAT))

while [[ "$(docker inspect -f '{{.State.Running}}' "${CONTAINER}" 2>/dev/null || true)" == true ]]; do
  if [[ -n "${EXPECTED_ID}" ]] && (( SECONDS - TRIAL_RUNNING_START >= TRIAL_RUNTIME_LIMIT )); then
    printf 'TRIAL_RUNTIME_LIMIT_REACHED=%s (stop exact ID %s)\n' "${TRIAL_RUNTIME_LIMIT}" "${EXPECTED_ID}" >&2
    exit 3
  fi
  if [[ -n "${EXPECTED_ID}" && "$(docker inspect --format '{{.Id}}' "${CONTAINER}" 2>/dev/null || true)" != "${EXPECTED_ID}" ]]; then
    die "trial Docker ID drift while monitoring"
  fi
  if [[ -n "${HEARTBEAT_FILE}" ]]; then
    printf '%s\n' "$(date +%s)" >"${HEARTBEAT_FILE}.tmp"
    mv -- "${HEARTBEAT_FILE}.tmp" "${HEARTBEAT_FILE}"
  fi
  mem_available="$(awk '$1=="MemAvailable:" {print $2}' "${MEMINFO_PATH}")"
  mem_free="$(awk '$1=="MemFree:" {print $2}' "${MEMINFO_PATH}")"
  cma_free="$(awk '$1=="CmaFree:" {print $2}' "${MEMINFO_PATH}")"
  swap_free="$(awk '$1=="SwapFree:" {print $2}' "${MEMINFO_PATH}")"
  cma_free="${cma_free:-0}"
  (( mem_free >= cma_free )) && noncma_free=$((mem_free - cma_free)) || noncma_free=0
  (( mem_available >= cma_free )) && noncma_available=$((mem_available - cma_free)) || noncma_available=0
  warning_low=0
  protection_low=0
  swap_consumed=0
  if (( initial_swap_free > swap_free )); then
    swap_consumed=$((initial_swap_free - swap_free))
  fi
  (( noncma_available < available_floor )) && warning_low=1
  (( swap_free < swap_free_floor )) && warning_low=1 && protection_low=1
  # Low immediately-free non-CMA memory occurs transiently during large shard
  # loading. It becomes protection-significant when reclaimable available
  # memory is also low, or when swap consumption since monitor start shows that
  # the workload has entered sustained unified-memory pressure. This preserves
  # normal checkpoint loading while covering the 2026-09-30 RM allocation
  # failures that appeared after swap activity began.
  if (( noncma_free < free_floor )); then
    warning_low=1
    if (( noncma_available < free_gate || swap_consumed >= swap_activity_gate )); then
      protection_low=1
    fi
  fi

  if (( warning_low == 1 )); then
    previous_low_count="${low_count}"
    if (( protection_low == 1 )); then
      low_count=$((low_count + 1))
    else
      low_count=0
    fi

    should_log_warning=0
    if (( protection_low == 1 || warning_active == 0 || previous_low_count > 0 )); then
      should_log_warning=1
    elif (( HEARTBEAT > 0 && SECONDS >= next_heartbeat )); then
      should_log_warning=1
    fi

    if (( should_log_warning == 1 )); then
      printf '%s WARNING memory margin low protect=%d/%d: available=%dMiB noncma_available=%dMiB free=%dMiB cmafree=%dMiB noncmafree=%dMiB swapfree=%dMiB swapgrowth=%dMiB\n' \
        "$(date '+%F %T')" "${low_count}" "${CONSECUTIVE}" \
        "$((mem_available / 1024))" "$((noncma_available / 1024))" "$((mem_free / 1024))" \
        "$((cma_free / 1024))" "$((noncma_free / 1024))" "$((swap_free / 1024))" "$((swap_consumed / 1024))"
      warning_active=1
      if (( HEARTBEAT > 0 )); then
        next_heartbeat=$((SECONDS + HEARTBEAT))
      fi
    fi

    if [[ "${PROTECT}" == 1 && "${protection_low}" == 1 && "${low_count}" -ge "${CONSECUTIVE}" ]]; then
      printf '%s PROTECT stopping %s gracefully to preserve host stability\n' "$(date '+%F %T')" "${CONTAINER}" >&2
      docker logs --tail 1000 "${CONTAINER}" 2>&1 || true
      container_id="$(docker inspect --format '{{.Id}}' "${CONTAINER}")"
      [[ -z "${EXPECTED_ID}" || "${container_id}" == "${EXPECTED_ID}" ]] ||
        die "trial ID drift on protected stop"
      write_stop_reason "${container_id}"
      stop_target="${CONTAINER}"
      [[ -z "${EXPECTED_ID}" ]] || stop_target="${EXPECTED_ID}"
      if ! docker stop --timeout 30 "${stop_target}" >/dev/null; then
        rm -f -- "${STOP_REASON_FILE}"
        die "failed to stop protected container"
      fi
      exit 2
    fi
  else
    if (( warning_active == 1 || low_count > 0 )); then
      printf '%s memory margin recovered: available=%dMiB noncma_available=%dMiB free=%dMiB cmafree=%dMiB noncmafree=%dMiB\n' \
        "$(date '+%F %T')" "$((mem_available / 1024))" "$((noncma_available / 1024))" \
        "$((mem_free / 1024))" "$((cma_free / 1024))" "$((noncma_free / 1024))"
    fi
    low_count=0
    warning_active=0
    if (( HEARTBEAT > 0 && SECONDS >= next_heartbeat )); then
      printf '%s HEARTBEAT healthy: available=%dMiB noncma_available=%dMiB free=%dMiB cmafree=%dMiB noncmafree=%dMiB swapfree=%dMiB\n' \
        "$(date '+%F %T')" "$((mem_available / 1024))" "$((noncma_available / 1024))" \
        "$((mem_free / 1024))" "$((cma_free / 1024))" "$((noncma_free / 1024))" "$((swap_free / 1024))"
      next_heartbeat=$((SECONDS + HEARTBEAT))
    fi
  fi
  sleep "${INTERVAL}"
done
printf '%s container is no longer running; monitor exiting\n' "$(date '+%F %T')"
