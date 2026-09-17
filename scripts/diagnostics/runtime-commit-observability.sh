#!/usr/bin/env bash
# Read-only runtime commit attestation checks sourced by doctor observability.
# Requires pass(), fail(), STATE_DIR, SCRIPT_DIR, RUNTIME_CONTAINER, OBS_CURRENT_LINK.

OBS_RUNTIME_COMMIT_FILE="${STATE_DIR}/runtime-commit.env"
OBS_RUNTIME_STATE_PARSER="${STATE_PARSER:-${SCRIPT_DIR}/lib/state_file.py}"

obs_parse_runtime_commit() {
  local parsed key value
  parsed="$(mktemp)"
  if ! python3 "${OBS_RUNTIME_STATE_PARSER}" runtime-commit "${OBS_RUNTIME_COMMIT_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  OBS_ATTESTED_RUNTIME_ROOT=""
  OBS_ATTESTED_CONTAINER_NAME=""
  OBS_ATTESTED_CONTAINER_ID=""
  OBS_ATTESTED_COMMITTED_AT=""
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    case "${key}" in
      RUNTIME_COMMIT_SCHEMA_VERSION) [[ "${value}" == 1 ]] || { rm -f -- "${parsed}"; return 1; } ;;
      RUNTIME_ROOT) OBS_ATTESTED_RUNTIME_ROOT="${value}" ;;
      RUNTIME_CONTAINER_NAME) OBS_ATTESTED_CONTAINER_NAME="${value}" ;;
      RUNTIME_CONTAINER_ID) OBS_ATTESTED_CONTAINER_ID="${value}" ;;
      COMMITTED_AT) OBS_ATTESTED_COMMITTED_AT="${value}" ;;
      *) rm -f -- "${parsed}"; return 1 ;;
    esac
  done <"${parsed}"
  rm -f -- "${parsed}"
  [[ -n "${OBS_ATTESTED_RUNTIME_ROOT}" && -n "${OBS_ATTESTED_CONTAINER_NAME}" && \
     -n "${OBS_ATTESTED_CONTAINER_ID}" && -n "${OBS_ATTESTED_COMMITTED_AT}" ]]
}

if [[ ! -f "${OBS_RUNTIME_COMMIT_FILE}" || -L "${OBS_RUNTIME_COMMIT_FILE}" ]]; then
  fail "runtime commit attestation is missing or unsafe (${OBS_RUNTIME_COMMIT_FILE})"
elif [[ ! -r "${OBS_RUNTIME_STATE_PARSER}" ]]; then
  fail "runtime commit state parser is unavailable (${OBS_RUNTIME_STATE_PARSER})"
elif ! obs_parse_runtime_commit; then
  fail "runtime commit attestation failed strict parsing (${OBS_RUNTIME_COMMIT_FILE})"
else
  pass "runtime commit attestation is strictly parsed"
  obs_expected_runtime_root="$(readlink -f -- "${OBS_CURRENT_LINK}" 2>/dev/null || true)"
  if [[ -n "${obs_expected_runtime_root}" && "${OBS_ATTESTED_RUNTIME_ROOT}" == "${obs_expected_runtime_root}" ]]; then
    pass "runtime commit root matches current immutable release (${obs_expected_runtime_root})"
  else
    fail "runtime commit root mismatch: attested=${OBS_ATTESTED_RUNTIME_ROOT:-missing}, current=${obs_expected_runtime_root:-missing}"
  fi

  if [[ "${OBS_ATTESTED_CONTAINER_NAME}" == "${RUNTIME_CONTAINER}" ]]; then
    pass "runtime commit container name matches managed runtime"
  else
    fail "runtime commit container-name mismatch: attested=${OBS_ATTESTED_CONTAINER_NAME:-missing}, expected=${RUNTIME_CONTAINER}"
  fi

  if command -v docker >/dev/null 2>&1 && docker inspect "${RUNTIME_CONTAINER}" >/dev/null 2>&1; then
    obs_running_container_id="$(docker inspect --format '{{.Id}}' "${RUNTIME_CONTAINER}" 2>/dev/null || true)"
    obs_running_container_state="$(docker inspect --format '{{.State.Status}}' "${RUNTIME_CONTAINER}" 2>/dev/null || true)"
    if [[ -n "${obs_running_container_id}" && "${OBS_ATTESTED_CONTAINER_ID}" == "${obs_running_container_id}" ]]; then
      pass "runtime commit container ID matches running container (${obs_running_container_id})"
    else
      fail "runtime commit container-ID mismatch: attested=${OBS_ATTESTED_CONTAINER_ID:-missing}, running=${obs_running_container_id:-missing}"
    fi
    if [[ "${obs_running_container_state}" == running ]]; then
      pass "attested runtime container is running"
    else
      fail "attested runtime container is not running (state=${obs_running_container_state:-unknown})"
    fi
  else
    fail "attested runtime container is unavailable (${RUNTIME_CONTAINER})"
  fi
fi
