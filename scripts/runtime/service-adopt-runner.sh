#!/usr/bin/env bash
# One-shot supervisor used only to attach systemd to an already-restored runtime.
set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_FILE="${QWEN38_STATE_FILE:-${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark/install.env}"
STATE_DIR="$(dirname -- "${STATE_FILE}")"
STATE_PARSER="${SCRIPT_ROOT}/scripts/lib/state_file.py"
ADOPT_FILE="${STATE_DIR}/runtime-adopt.env"
RUNTIME_COMMIT_FILE="${STATE_DIR}/runtime-commit.env"
MONITOR_PID_FILE="${STATE_DIR}/monitor.pid"
MONITOR_LOG="${STATE_DIR}/monitor.log"
CONTAINER_NAME="qwen38-flash-next"
RUNTIME_ROOT=""

die() { printf 'FATAL: %s\n' "$*" >&2; exit 1; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --runtime-root)
      [[ $# -ge 2 ]] || die "--runtime-root requires a path"
      RUNTIME_ROOT="$2"
      shift
      ;;
    *) die "unknown argument: $1" ;;
  esac
  shift
done

[[ -n "${RUNTIME_ROOT}" && "${RUNTIME_ROOT}" == /* ]] || die "runtime root is required"
RUNTIME_ROOT="$(realpath -e -- "${RUNTIME_ROOT}")"
[[ -r "${STATE_PARSER}" ]] || die "state parser is unavailable: ${STATE_PARSER}"
[[ -f "${STATE_FILE}" && ! -L "${STATE_FILE}" ]] || die "install manifest is missing or unsafe"

parse_into_vars() {
  local schema="$1" path="$2" prefix="$3" parsed key value
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" "${schema}" "${path}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    printf -v "${prefix}${key}" '%s' "${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
}

runtime_monitor_process() {
  MONITOR_PID=""
  MONITOR_CMDLINE=""
  [[ -f "${MONITOR_PID_FILE}" && ! -L "${MONITOR_PID_FILE}" ]] || return 1
  IFS= read -r MONITOR_PID <"${MONITOR_PID_FILE}" || return 1
  [[ "${MONITOR_PID}" =~ ^[0-9]+$ && -r "/proc/${MONITOR_PID}/cmdline" ]] || return 1
  MONITOR_CMDLINE="$(tr '\0' ' ' <"/proc/${MONITOR_PID}/cmdline")"
  [[ "${MONITOR_CMDLINE}" == *monitor-runtime.sh* &&
     "${MONITOR_CMDLINE}" == *"--container ${CONTAINER_NAME}"* ]]
}

runtime_monitor_matches_restored() {
  local monitor_helper="${RUNTIME_ROOT}/scripts/monitor-runtime.sh"
  runtime_monitor_process || return 1
  [[ "${MONITOR_CMDLINE}" == *"${monitor_helper}"* ]] || return 1
  [[ "${MONITOR_CMDLINE}" == *"--min-available-gib ${LIVE_MONITOR_MIN_AVAILABLE_GIB}"* ]] || return 1
  [[ "${MONITOR_CMDLINE}" == *"--min-free-gib ${LIVE_MONITOR_MIN_FREE_GIB}"* ]] || return 1
  [[ "${MONITOR_CMDLINE}" == *"--free-gate-gib ${LIVE_MONITOR_FREE_GATE_GIB}"* ]] || return 1
  [[ "${MONITOR_CMDLINE}" == *"--min-swap-free-gib ${LIVE_MONITOR_MIN_SWAP_FREE_GIB}"* ]] || return 1
  [[ "${MONITOR_CMDLINE}" == *"--consecutive ${LIVE_MONITOR_CONSECUTIVE}"* ]] || return 1
  [[ "${MONITOR_CMDLINE}" == *"--heartbeat ${LIVE_MONITOR_HEARTBEAT}"* ]] || return 1
  if [[ "${LIVE_MONITOR_PROTECT}" == 1 ]]; then
    [[ "${MONITOR_CMDLINE}" == *"--protect"* ]] || return 1
  else
    [[ "${MONITOR_CMDLINE}" != *"--protect"* ]] || return 1
  fi
}

stop_mismatched_runtime_monitor() {
  local attempt
  runtime_monitor_process || {
    rm -f -- "${MONITOR_PID_FILE}"
    return 0
  }
  printf 'Replacing mismatched runtime monitor before restored-runtime adoption (pid=%s).\n' "${MONITOR_PID}" >&2
  kill "${MONITOR_PID}" 2>/dev/null || true
  for attempt in $(seq 1 20); do
    [[ ! -r "/proc/${MONITOR_PID}/cmdline" ]] && break
    sleep 0.1
  done
  [[ ! -r "/proc/${MONITOR_PID}/cmdline" ]] ||
    die "mismatched runtime monitor did not exit: pid=${MONITOR_PID}"
  rm -f -- "${MONITOR_PID_FILE}"
}

ensure_runtime_monitor() {
  local monitor_helper="${RUNTIME_ROOT}/scripts/monitor-runtime.sh" pid
  local -a monitor_args
  if [[ "${LIVE_MONITOR_ENABLED}" != 1 ]]; then
    if runtime_monitor_process; then
      stop_mismatched_runtime_monitor
      printf 'Removed stale runtime monitor because the restored manifest disables monitoring.\n'
    else
      rm -f -- "${MONITOR_PID_FILE}"
    fi
    return 0
  fi

  [[ -x "${monitor_helper}" ]] || die "restored runtime has no executable monitor helper: ${monitor_helper}"
  if runtime_monitor_matches_restored; then
    printf 'Existing runtime monitor already matches restored release policy (pid=%s).\n' "${MONITOR_PID}"
    return 0
  fi
  stop_mismatched_runtime_monitor

  monitor_args=(
    --container "${CONTAINER_NAME}"
    --min-available-gib "${LIVE_MONITOR_MIN_AVAILABLE_GIB}"
    --min-free-gib "${LIVE_MONITOR_MIN_FREE_GIB}"
    --free-gate-gib "${LIVE_MONITOR_FREE_GATE_GIB}"
    --min-swap-free-gib "${LIVE_MONITOR_MIN_SWAP_FREE_GIB}"
    --consecutive "${LIVE_MONITOR_CONSECUTIVE}"
    --heartbeat "${LIVE_MONITOR_HEARTBEAT}"
  )
  [[ "${LIVE_MONITOR_PROTECT}" != 1 ]] || monitor_args+=(--protect)
  nohup "${monitor_helper}" "${monitor_args[@]}" >>"${MONITOR_LOG}" 2>&1 &
  pid=$!
  printf '%s\n' "${pid}" >"${MONITOR_PID_FILE}"
  sleep 1
  runtime_monitor_matches_restored || die "restored runtime monitor failed exact-policy attachment"
  printf 'Restored runtime monitor attached (protect=%s, pid=%s).\n' "${LIVE_MONITOR_PROTECT}" "${pid}"
}

parse_into_vars install-service-runtime "${STATE_FILE}" LIVE_ || die "install manifest failed strict parsing"
[[ "${LIVE_PHASE}" == complete ]] || die "runtime adoption requires a complete restored manifest"

container_id="$(docker inspect --format '{{.Id}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
if [[ -z "${container_id}" ]]; then
  rm -f -- "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"
  previous_runner="${RUNTIME_ROOT}/scripts/service-runner.sh"
  [[ -x "${previous_runner}" ]] || die "restored runtime root has no executable service runner"
  printf 'Adoption supervisor found no canonical container; delegating to restored runtime root.\n'
  exec bash "${previous_runner}"
fi

running="$(docker inspect --format '{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
if [[ "${running}" != true ]]; then
  rm -f -- "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"
  printf 'Restored runtime container is stopped; preserving stopped state instead of cold-starting it.\n'
  exit 0
fi

adoption_source=""
if [[ -e "${ADOPT_FILE}" || -L "${ADOPT_FILE}" ]]; then
  [[ -f "${ADOPT_FILE}" && ! -L "${ADOPT_FILE}" ]] || die "runtime adoption marker is unsafe"
  parse_into_vars runtime-adopt "${ADOPT_FILE}" ADOPT_ || die "runtime adoption marker failed strict parsing"
  [[ "${ADOPT_RUNTIME_ROOT}" == "${RUNTIME_ROOT}" ]] || die "runtime adoption root mismatch"
  [[ "${ADOPT_RUNTIME_CONTAINER_NAME}" == "${CONTAINER_NAME}" ]] || die "runtime adoption container-name mismatch"
  [[ "${ADOPT_RUNTIME_CONTAINER_ID}" == "${container_id}" ]] || die "runtime adoption container ID mismatch"
  [[ "${ADOPT_EXPECTED_IMAGE}" == "${LIVE_VLLM_IMAGE}" ]] || die "runtime adoption image does not match manifest"
  [[ "${ADOPT_SERVED_NAME}" == "${LIVE_SERVED_NAME}" ]] || die "runtime adoption served identity does not match manifest"
  adoption_source="marker"
elif [[ -f "${RUNTIME_COMMIT_FILE}" && ! -L "${RUNTIME_COMMIT_FILE}" ]]; then
  parse_into_vars runtime-commit "${RUNTIME_COMMIT_FILE}" ATTEST_ || die "runtime adoption attestation failed strict parsing"
  [[ "${ATTEST_RUNTIME_ROOT}" == "${RUNTIME_ROOT}" ]] || die "runtime adoption attestation root mismatch"
  [[ "${ATTEST_RUNTIME_CONTAINER_NAME}" == "${CONTAINER_NAME}" ]] || die "runtime adoption attestation container-name mismatch"
  [[ "${ATTEST_RUNTIME_CONTAINER_ID}" == "${container_id}" ]] || die "runtime adoption attestation container ID mismatch"
  adoption_source="attestation"
else
  die "running restored runtime has neither a valid adoption marker nor matching attestation"
fi

image="$(docker inspect --format '{{.Config.Image}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
oom="$(docker inspect --format '{{.State.OOMKilled}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
model_mount="$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/model"}}{{.Source}}{{end}}{{end}}' "${CONTAINER_NAME}" 2>/dev/null || true)"

[[ "${image}" == "${LIVE_VLLM_IMAGE}" ]] || die "runtime adoption container image mismatch"
[[ "${oom}" == false ]] || die "runtime adoption container reports OOMKilled=true"
[[ -n "${model_mount}" ]] || die "runtime adoption model mount is missing"
[[ "$(realpath -m -- "${model_mount}")" == "$(realpath -m -- "${LIVE_MODEL_DIR}")" ]] || die "runtime adoption model mount mismatch"

curl -fsS --max-time 3 http://127.0.0.1:8888/health >/dev/null || die "runtime adoption health endpoint is not ready"
models="$(curl -fsS --max-time 15 http://127.0.0.1:8888/v1/models)"
python3 -c 'import json,sys; expected=sys.argv[1]; data=json.load(sys.stdin); assert any(item.get("id") == expected for item in data.get("data", [])), expected'   "${LIVE_SERVED_NAME}" <<<"${models}" || die "runtime adoption served model identity mismatch"

ensure_runtime_monitor

umask 077
{
  printf 'RUNTIME_COMMIT_SCHEMA_VERSION=1\n'
  printf 'RUNTIME_ROOT=%s\n' "${RUNTIME_ROOT}"
  printf 'RUNTIME_CONTAINER_NAME=%s\n' "${CONTAINER_NAME}"
  printf 'RUNTIME_CONTAINER_ID=%s\n' "${container_id}"
  printf 'COMMITTED_AT=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
} >"${RUNTIME_COMMIT_FILE}.tmp"
python3 "${STATE_PARSER}" runtime-commit "${RUNTIME_COMMIT_FILE}.tmp" >/dev/null
mv -- "${RUNTIME_COMMIT_FILE}.tmp" "${RUNTIME_COMMIT_FILE}"

printf 'Existing runtime supervised without replacement (source=%s, container=%s, root=%s).\n'   "${adoption_source}" "${container_id}" "${RUNTIME_ROOT}"
docker logs --follow --since 0s "${CONTAINER_NAME}" &
log_pid=$!
trap 'kill "${log_pid}" 2>/dev/null || true' EXIT

if [[ "${adoption_source}" == marker ]]; then
  # The service now owns the restored container through the attestation above.
  # Remove the one-shot marker only after the supervisor is fully attached.
  rm -f -- "${ADOPT_FILE}" "${ADOPT_FILE}.tmp"
fi

container_status="$(docker wait "${CONTAINER_NAME}")"
rm -f -- "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"
printf 'Adopted inference container stopped (exit %s); marking service failed.\n' "${container_status}" >&2
exit 1
