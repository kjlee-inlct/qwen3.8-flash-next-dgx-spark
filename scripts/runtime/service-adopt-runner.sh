#!/usr/bin/env bash
# One-shot supervisor used only to attach systemd to an already-restored runtime.
set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_FILE="${QWEN38_STATE_FILE:-${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark/install.env}"
STATE_DIR="$(dirname -- "${STATE_FILE}")"
STATE_PARSER="${SCRIPT_ROOT}/scripts/lib/state_file.py"
ADOPT_FILE="${STATE_DIR}/runtime-adopt.env"
RUNTIME_COMMIT_FILE="${STATE_DIR}/runtime-commit.env"
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
[[ -f "${ADOPT_FILE}" && ! -L "${ADOPT_FILE}" ]] || die "runtime adoption marker is missing or unsafe"

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

parse_into_vars install-service-runtime "${STATE_FILE}" LIVE_ || die "install manifest failed strict parsing"
parse_into_vars runtime-adopt "${ADOPT_FILE}" ADOPT_ || die "runtime adoption marker failed strict parsing"

[[ "${LIVE_PHASE}" == complete ]] || die "runtime adoption requires a complete restored manifest"
[[ "${ADOPT_RUNTIME_ROOT}" == "${RUNTIME_ROOT}" ]] || die "runtime adoption root mismatch"
[[ "${ADOPT_RUNTIME_CONTAINER_NAME}" == "${CONTAINER_NAME}" ]] || die "runtime adoption container-name mismatch"
[[ "${ADOPT_EXPECTED_IMAGE}" == "${LIVE_VLLM_IMAGE}" ]] || die "runtime adoption image does not match manifest"
[[ "${ADOPT_SERVED_NAME}" == "${LIVE_SERVED_NAME}" ]] || die "runtime adoption served identity does not match manifest"

container_id="$(docker inspect --format '{{.Id}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
image="$(docker inspect --format '{{.Config.Image}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
running="$(docker inspect --format '{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
oom="$(docker inspect --format '{{.State.OOMKilled}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
model_mount="$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/model"}}{{.Source}}{{end}}{{end}}' "${CONTAINER_NAME}" 2>/dev/null || true)"

[[ -n "${container_id}" && "${container_id}" == "${ADOPT_RUNTIME_CONTAINER_ID}" ]] || die "runtime adoption container ID mismatch"
[[ "${image}" == "${LIVE_VLLM_IMAGE}" ]] || die "runtime adoption container image mismatch"
[[ "${running}" == true ]] || die "runtime adoption container is not running"
[[ "${oom}" == false ]] || die "runtime adoption container reports OOMKilled=true"
[[ -n "${model_mount}" ]] || die "runtime adoption model mount is missing"
[[ "$(realpath -m -- "${model_mount}")" == "$(realpath -m -- "${LIVE_MODEL_DIR}")" ]] || die "runtime adoption model mount mismatch"

curl -fsS --max-time 3 http://127.0.0.1:8888/health >/dev/null || die "runtime adoption health endpoint is not ready"
models="$(curl -fsS --max-time 15 http://127.0.0.1:8888/v1/models)"
python3 -c 'import json,sys; expected=sys.argv[1]; data=json.load(sys.stdin); assert any(item.get("id") == expected for item in data.get("data", [])), expected'   "${LIVE_SERVED_NAME}" <<<"${models}" || die "runtime adoption served model identity mismatch"

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

printf 'Existing runtime adopted without replacement (container=%s, root=%s).\n' "${container_id}" "${RUNTIME_ROOT}"
docker logs --follow --since 0s "${CONTAINER_NAME}" &
log_pid=$!
trap 'kill "${log_pid}" 2>/dev/null || true' EXIT

# The service now owns the restored container through the attestation above.
# Remove the one-shot marker only after the supervisor is fully attached.
rm -f -- "${ADOPT_FILE}" "${ADOPT_FILE}.tmp"

container_status="$(docker wait "${CONTAINER_NAME}")"
rm -f -- "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"
printf 'Adopted inference container stopped (exit %s); marking service failed.\n' "${container_status}" >&2
exit 1
