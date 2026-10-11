#!/usr/bin/env bash
# Stop only the exact container attested to the current managed service instance.
set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_FILE="${QWEN38_STATE_FILE:-${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark/install.env}"
STATE_DIR="$(dirname -- "${STATE_FILE}")"
RUNTIME_COMMIT_FILE="${STATE_DIR}/runtime-commit.env"
STATE_PARSER="${SCRIPT_ROOT}/scripts/lib/state_file.py"
CONTAINER_NAME="qwen38-flash-next"

[[ -r "${STATE_PARSER}" ]] || exit 0
[[ -f "${RUNTIME_COMMIT_FILE}" && ! -L "${RUNTIME_COMMIT_FILE}" ]] || {
  printf 'Managed service stop: no runtime attestation; preserving any canonical container.\n'
  exit 0
}

parsed="$(mktemp)"
trap 'rm -f -- "${parsed}"' EXIT
if ! python3 "${STATE_PARSER}" runtime-commit "${RUNTIME_COMMIT_FILE}" >"${parsed}"; then
  printf 'Managed service stop: invalid runtime attestation; preserving any canonical container.\n' >&2
  exit 0
fi
attested_name=""
attested_id=""
while IFS= read -r -d '' key && IFS= read -r -d '' value; do
  case "${key}" in
    RUNTIME_CONTAINER_NAME) attested_name="${value}" ;;
    RUNTIME_CONTAINER_ID) attested_id="${value}" ;;
  esac
done <"${parsed}"

[[ "${attested_name}" == "${CONTAINER_NAME}" && -n "${attested_id}" ]] || {
  printf 'Managed service stop: attestation does not name the canonical container; preserving runtime.\n' >&2
  exit 0
}

current_id="$(docker inspect --format '{{.Id}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
if [[ -z "${current_id}" ]]; then
  rm -f -- "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"
  exit 0
fi
if [[ "${current_id}" != "${attested_id}" ]]; then
  printf 'Managed service stop: canonical container changed (attested=%s current=%s); preserving restored runtime.\n'     "${attested_id}" "${current_id}" >&2
  rm -f -- "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"
  exit 0
fi

docker stop --timeout 30 "${CONTAINER_NAME}" >/dev/null 2>&1 || true
rm -f -- "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"
