#!/usr/bin/env bash
# Keep the Docker inference container attached to a systemd service lifecycle.
set -Eeuo pipefail

STATE_FILE="${QWEN38_STATE_FILE:-${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark/install.env}"
[[ -r "${STATE_FILE}" ]] || { printf 'FATAL: installation manifest is not readable: %s\n' "${STATE_FILE}" >&2; exit 1; }
# The installer writes shell-escaped values with mode 600.
# shellcheck disable=SC1090
source "${STATE_FILE}"

CONFIG_OVERRIDE="${CONFIG_OVERRIDE:-}"
MONITOR_PROTECT="${MONITOR_PROTECT:-0}"

[[ "${MODEL_PROFILE:-}" == orcarouter ]] || { printf 'FATAL: service requires the OrcaRouter profile\n' >&2; exit 1; }
[[ -x "${INSTALL_ROOT:-}/scripts/serve.sh" ]] || { printf 'FATAL: invalid INSTALL_ROOT in manifest\n' >&2; exit 1; }
[[ "${CONTAINER_NAME:-}" == qwen38-flash-next ]] || { printf 'FATAL: unexpected container name\n' >&2; exit 1; }

export MODEL_PROFILE MODEL_DIR VLLM_IMAGE CONFIG_OVERRIDE MONITOR_PROTECT
export NAME="${CONTAINER_NAME}"
export RESTART_POLICY=no
export PUBLISH_HOST=127.0.0.1

"${INSTALL_ROOT}/scripts/serve.sh"

ready=0
for attempt in $(seq 1 180); do
  if curl -fsS --max-time 3 http://127.0.0.1:8888/health >/dev/null 2>&1; then
    ready=1
    break
  fi
  state="$(docker inspect --format '{{.State.Status}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
  [[ "${state}" == running ]] || { printf 'FATAL: container stopped during startup (state=%s)\n' "${state:-missing}" >&2; exit 1; }
  if (( attempt % 6 == 0 )); then
    printf 'Waiting for Qwen readiness: %d/1800 seconds\n' "$((attempt * 10))"
  fi
  sleep 10
done
[[ "${ready}" == 1 ]] || { printf 'FATAL: API did not become healthy within 30 minutes\n' >&2; exit 1; }

models="$(curl -fsS --max-time 15 http://127.0.0.1:8888/v1/models)"
python3 -c 'import json,sys; expected=sys.argv[1]; data=json.load(sys.stdin); assert any(item.get("id") == expected for item in data.get("data", [])), expected' \
  "${SERVED_NAME:-orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4}" <<<"${models}"

printf 'Qwen API is ready; following container logs.\n'
docker logs --follow --since 0s "${CONTAINER_NAME}" &
log_pid=$!
trap 'kill "${log_pid}" 2>/dev/null || true' EXIT
container_status="$(docker wait "${CONTAINER_NAME}")"
printf 'Inference container stopped (exit %s); marking service failed.\n' "${container_status}" >&2
exit 1
