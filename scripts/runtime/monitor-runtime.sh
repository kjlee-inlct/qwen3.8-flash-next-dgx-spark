#!/usr/bin/env bash
# Monitor DGX Spark unified memory; stopping the container is opt-in.
set -euo pipefail

CONTAINER="qwen38-flash-next"
MIN_AVAILABLE_GIB=6
MIN_FREE_GIB=2
FREE_GATE_GIB=10
MIN_SWAP_FREE_GIB=8
CONSECUTIVE=5
INTERVAL=2
HEARTBEAT=60
PROTECT=0
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STOP_REASON_FILE="${STATE_DIR}/runtime-stop.env"

usage() {
  cat <<'EOF'
Usage: ./scripts/monitor-runtime.sh [options]
  --container NAME             Container to monitor (default: qwen38-flash-next)
  --min-available-gib N        MemAvailable warning floor (default: 6)
  --min-free-gib N             MemFree warning floor (default: 2)
  --free-gate-gib N            Apply MemFree floor below this MemAvailable (default: 10)
  --min-swap-free-gib N        SwapFree warning floor (default: 8)
  --consecutive N              Consecutive low samples before protection (default: 5)
  --interval N                 Sampling interval in seconds (default: 2)
  --heartbeat N                Healthy status interval in seconds; 0 disables (default: 60)
  --protect                    Stop the container after consecutive low samples

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
    --consecutive) [[ $# -ge 2 ]] || die "$1 requires a value"; CONSECUTIVE="$2"; shift ;;
    --interval) [[ $# -ge 2 ]] || die "$1 requires a value"; INTERVAL="$2"; shift ;;
    --heartbeat) [[ $# -ge 2 ]] || die "$1 requires a value"; HEARTBEAT="$2"; shift ;;
    --protect) PROTECT=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
  shift
done
[[ -n "${CONTAINER}" && "${CONTAINER}" != */* ]] || die "invalid container name"
for value in "${MIN_AVAILABLE_GIB}" "${MIN_FREE_GIB}" "${FREE_GATE_GIB}" "${MIN_SWAP_FREE_GIB}" "${CONSECUTIVE}" "${INTERVAL}"; do
  positive_integer "${value}" || die "thresholds and intervals must be positive integers"
done
nonnegative_integer "${HEARTBEAT}" || die "heartbeat must be a non-negative integer"
command -v docker >/dev/null || die "docker is required"
[[ -r /proc/meminfo ]] || die "/proc/meminfo is unavailable"
docker inspect "${CONTAINER}" >/dev/null 2>&1 || die "container not found: ${CONTAINER}"

available_floor=$((MIN_AVAILABLE_GIB * 1048576))
free_floor=$((MIN_FREE_GIB * 1048576))
free_gate=$((FREE_GATE_GIB * 1048576))
swap_free_floor=$((MIN_SWAP_FREE_GIB * 1048576))
low_count=0
mode="warn-only"; [[ "${PROTECT}" == 1 ]] && mode="protect"
printf '%s monitor started: container=%s mode=%s available=%sGiB free=%sGiB/%sGiB gate swapfree=%sGiB\n' \
  "$(date '+%F %T')" "${CONTAINER}" "${mode}" "${MIN_AVAILABLE_GIB}" "${MIN_FREE_GIB}" "${FREE_GATE_GIB}" "${MIN_SWAP_FREE_GIB}"
next_heartbeat=$((SECONDS + HEARTBEAT))

while [[ "$(docker inspect -f '{{.State.Running}}' "${CONTAINER}" 2>/dev/null || true)" == true ]]; do
  mem_available="$(awk '$1=="MemAvailable:" {print $2}' /proc/meminfo)"
  mem_free="$(awk '$1=="MemFree:" {print $2}' /proc/meminfo)"
  swap_free="$(awk '$1=="SwapFree:" {print $2}' /proc/meminfo)"
  if (( mem_available < available_floor || swap_free < swap_free_floor || (mem_free < free_floor && mem_available < free_gate) )); then
    low_count=$((low_count + 1))
    printf '%s WARNING memory margin low %d/%d: available=%dMiB free=%dMiB swapfree=%dMiB\n' \
      "$(date '+%F %T')" "${low_count}" "${CONSECUTIVE}" \
      "$((mem_available / 1024))" "$((mem_free / 1024))" "$((swap_free / 1024))"
    if [[ "${PROTECT}" == 1 && "${low_count}" -ge "${CONSECUTIVE}" ]]; then
      printf '%s PROTECT stopping %s gracefully to preserve host stability\n' "$(date '+%F %T')" "${CONTAINER}" >&2
      docker logs --tail 1000 "${CONTAINER}" 2>&1 || true
      container_id="$(docker inspect --format '{{.Id}}' "${CONTAINER}")"
      write_stop_reason "${container_id}"
      if ! docker stop --timeout 30 "${CONTAINER}" >/dev/null; then
        rm -f -- "${STOP_REASON_FILE}"
        die "failed to stop protected container"
      fi
      exit 2
    fi
  else
    if (( low_count > 0 )); then
      printf '%s memory margin recovered: available=%dMiB free=%dMiB\n' \
        "$(date '+%F %T')" "$((mem_available / 1024))" "$((mem_free / 1024))"
    fi
    low_count=0
    if (( HEARTBEAT > 0 && SECONDS >= next_heartbeat )); then
      printf '%s HEARTBEAT healthy: available=%dMiB free=%dMiB swapfree=%dMiB\n' \
        "$(date '+%F %T')" "$((mem_available / 1024))" "$((mem_free / 1024))" "$((swap_free / 1024))"
      next_heartbeat=$((SECONDS + HEARTBEAT))
    fi
  fi
  sleep "${INTERVAL}"
done
printf '%s container is no longer running; monitor exiting\n' "$(date '+%F %T')"
