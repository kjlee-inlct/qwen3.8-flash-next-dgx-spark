#!/usr/bin/env bash
# Keep the Docker inference container attached to a systemd service lifecycle.
set -Eeuo pipefail

RUNTIME_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
STATE_FILE="${QWEN38_STATE_FILE:-${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark/install.env}"
[[ -r "${STATE_FILE}" ]] || { printf 'FATAL: installation manifest is not readable: %s\n' "${STATE_FILE}" >&2; exit 1; }
# The installation manifest is still a trusted installer-owned shell file; it is
# migrated to strict parsing in a separate compatibility-focused change.
# shellcheck disable=SC1090
source "${STATE_FILE}"

STATE_DIR="$(dirname -- "${STATE_FILE}")"
STOP_REASON_FILE="${STATE_DIR}/runtime-stop.env"
STATE_PARSER="${RUNTIME_ROOT}/scripts/state_file.py"
CONFIG_OVERRIDE="${CONFIG_OVERRIDE:-}"
MONITOR_PROTECT="${MONITOR_PROTECT:-0}"
MONITOR_ENABLED="${MONITOR_ENABLED:-${MONITOR_PROTECT}}"

parse_state_into_vars() {
  local schema="$1" path="$2" parsed key value
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" "${schema}" "${path}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    printf -v "${key}" '%s' "${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
}

[[ "${MODEL_PROFILE:-}" == orcarouter || "${MODEL_PROFILE:-}" == nvidia ]] || { printf 'FATAL: unsupported model profile\n' >&2; exit 1; }
[[ -x "${RUNTIME_ROOT}/scripts/serve.sh" ]] || { printf 'FATAL: invalid runtime release root\n' >&2; exit 1; }
[[ -r "${RUNTIME_ROOT}/scripts/runtime-transition.sh" ]] || { printf 'FATAL: runtime transition helper is unavailable\n' >&2; exit 1; }
[[ -r "${STATE_PARSER}" ]] || { printf 'FATAL: state parser is unavailable\n' >&2; exit 1; }
[[ "${CONTAINER_NAME:-}" == qwen38-flash-next ]] || { printf 'FATAL: unexpected container name\n' >&2; exit 1; }

export MODEL_PROFILE MODEL_DIR VLLM_IMAGE CONFIG_OVERRIDE MONITOR_ENABLED MONITOR_PROTECT SERVED_NAME
export MONITOR_MIN_AVAILABLE_GIB MONITOR_MIN_FREE_GIB MONITOR_FREE_GATE_GIB
export MONITOR_MIN_SWAP_FREE_GIB MONITOR_CONSECUTIVE MONITOR_HEARTBEAT
export NAME="${CONTAINER_NAME}"
export CONTAINER_NAME
export RESTART_POLICY=no
export PUBLISH_HOST=127.0.0.1

"${RUNTIME_ROOT}/scripts/preflight-runtime.sh"
bash "${RUNTIME_ROOT}/scripts/runtime-transition.sh" recover

transition_active=0
rollback_transition() {
  local rc="${1:-1}"
  trap - ERR INT TERM
  set +e
  if [[ "${transition_active}" == 1 ]]; then
    printf 'Candidate runtime failed validation; restoring previous container.\n' >&2
    if ! bash "${RUNTIME_ROOT}/scripts/runtime-transition.sh" rollback; then
      printf 'FATAL: automatic runtime rollback failed; run doctor and inspect Docker state.\n' >&2
      exit 70
    fi
  fi
  exit "${rc}"
}
trap 'rollback_transition $?' ERR
trap 'rollback_transition 130' INT
trap 'rollback_transition 143' TERM

bash "${RUNTIME_ROOT}/scripts/runtime-transition.sh" prepare
transition_active=1
"${RUNTIME_ROOT}/scripts/serve.sh"
bash "${RUNTIME_ROOT}/scripts/runtime-transition.sh" candidate-started
bash "${RUNTIME_ROOT}/scripts/runtime-transition.sh" validating

ready=0
for attempt in $(seq 1 180); do
  if curl -fsS --max-time 3 http://127.0.0.1:8888/health >/dev/null 2>&1; then
    ready=1
    break
  fi
  state="$(docker inspect --format '{{.State.Status}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
  [[ "${state}" == running ]] || { printf 'FATAL: candidate container stopped during startup (state=%s)\n' "${state:-missing}" >&2; false; }
  if (( attempt % 6 == 0 )); then
    printf 'Waiting for Qwen readiness: %d/1800 seconds\n' "$((attempt * 10))"
  fi
  sleep 10
done
[[ "${ready}" == 1 ]] || { printf 'FATAL: candidate API did not become healthy within 30 minutes\n' >&2; false; }

models="$(curl -fsS --max-time 15 http://127.0.0.1:8888/v1/models)"
python3 -c 'import json,sys; expected=sys.argv[1]; data=json.load(sys.stdin); assert any(item.get("id") == expected for item in data.get("data", [])), expected' \
  "${SERVED_NAME:-orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4}" <<<"${models}"

bash "${RUNTIME_ROOT}/scripts/runtime-transition.sh" commit
transition_active=0
trap - ERR INT TERM

printf 'Qwen API is ready; runtime transition committed; following container logs.\n'
docker logs --follow --since 0s "${CONTAINER_NAME}" &
log_pid=$!
trap 'kill "${log_pid}" 2>/dev/null || true' EXIT
container_status="$(docker wait "${CONTAINER_NAME}")"
container_id="$(docker inspect --format '{{.Id}}' "${CONTAINER_NAME}" 2>/dev/null || true)"

if [[ -r "${STOP_REASON_FILE}" ]]; then
  unset RUNTIME_STOP_SCHEMA_VERSION STOP_REASON STOP_CONTAINER_NAME STOP_CONTAINER_ID UPDATED_AT
  if parse_state_into_vars runtime-stop "${STOP_REASON_FILE}" && \
     [[ "${STOP_CONTAINER_NAME:-}" == "${CONTAINER_NAME}" && \
        "${STOP_CONTAINER_ID:-}" == "${container_id}" && -n "${container_id}" ]]; then
    rm -f -- "${STOP_REASON_FILE}"
    printf 'Inference container stopped intentionally by memory protection; leaving service stopped.\n' >&2
    exit 0
  fi
  printf 'WARNING: ignoring invalid or stale runtime stop marker; container will be treated as failed.\n' >&2
  rm -f -- "${STOP_REASON_FILE}"
fi

printf 'Inference container stopped (exit %s); marking service failed.\n' "${container_status}" >&2
exit 1
