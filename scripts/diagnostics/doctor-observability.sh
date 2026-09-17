#!/usr/bin/env bash
# Additional read-only lifecycle checks sourced by doctor.sh.
# Requires doctor.sh to define pass(), warn(), fail(), SCRIPT_DIR and RUNTIME_CONTAINER.

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"
OBS_UPDATE_STATE_FILE="${STATE_DIR}/update-transition.env"
OBS_STOP_REASON_FILE="${STATE_DIR}/runtime-stop.env"
OBS_CURRENT_LINK="${DATA_HOME}/current"
OBS_PREVIOUS_LINK="${DATA_HOME}/previous"
OBS_RELEASES_DIR="${DATA_HOME}/releases"
OBS_QUALIFIED_DIR="${DATA_HOME}/qualified"
OBS_RELEASE_MANAGER="${SCRIPT_DIR}/release-manager.sh"
OBS_QUALIFICATION_PARSER="${SCRIPT_DIR}/lib/qualification_marker.py"
OBS_API_SOCKET_UNIT="qwen38-openwebui-proxy.socket"

obs_read_release_id() {
  local link target release_id
  link="$1"
  [[ -L "${link}" ]] || return 1
  target="$(readlink -f -- "${link}" 2>/dev/null || true)"
  [[ -n "${target}" && "${target}" == "${OBS_RELEASES_DIR}/"* ]] || return 2
  release_id="$(basename -- "${target}")"
  [[ "${release_id}" =~ ^[0-9a-f]{12,40}$ ]] || return 2
  printf '%s\n' "${release_id}"
}

obs_manifest_digest() {
  python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$1"
}

obs_parse_qualification() {
  local marker="$1" parsed key value
  parsed="$(mktemp)"
  if ! python3 "${OBS_QUALIFICATION_PARSER}" "${marker}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  unset OBS_QUALIFICATION_SCHEMA_VERSION OBS_QUALIFIED_RELEASE OBS_RELEASE_MANIFEST_SHA256 OBS_QUALIFIED_AT
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    case "${key}" in
      QUALIFICATION_SCHEMA_VERSION) OBS_QUALIFICATION_SCHEMA_VERSION="${value}" ;;
      QUALIFIED_RELEASE) OBS_QUALIFIED_RELEASE="${value}" ;;
      RELEASE_MANIFEST_SHA256) OBS_RELEASE_MANIFEST_SHA256="${value}" ;;
      QUALIFIED_AT) OBS_QUALIFIED_AT="${value}" ;;
      *) rm -f -- "${parsed}"; return 1 ;;
    esac
  done <"${parsed}"
  rm -f -- "${parsed}"
}

obs_check_qualification() {
  local release_id="$1" marker manifest_path observed_digest
  marker="${OBS_QUALIFIED_DIR}/${release_id}.env"
  manifest_path="${OBS_RELEASES_DIR}/${release_id}/.release-manifest.json"
  if [[ ! -f "${marker}" || -L "${marker}" ]]; then
    fail "current immutable release is missing its qualification marker (${release_id})"
    return
  fi
  if [[ ! -r "${OBS_QUALIFICATION_PARSER}" ]] || ! obs_parse_qualification "${marker}"; then
    fail "current immutable release qualification marker is invalid (${release_id})"
    return
  fi
  if [[ "${OBS_QUALIFIED_RELEASE:-}" != "${release_id}" ]]; then
    fail "current immutable release qualification marker mismatches release (${release_id})"
    return
  fi
  if [[ "${OBS_QUALIFICATION_SCHEMA_VERSION:-}" == 1 ]]; then
    warn "current immutable release has legacy unbound qualification; re-qualify before a future cutover (${release_id})"
    return
  fi
  [[ -f "${manifest_path}" && ! -L "${manifest_path}" ]] || {
    fail "current immutable release manifest is unavailable for qualification verification (${release_id})"
    return
  }
  observed_digest="$(obs_manifest_digest "${manifest_path}")"
  if [[ "${OBS_RELEASE_MANIFEST_SHA256:-}" == "${observed_digest}" ]]; then
    pass "current immutable release qualification matches release manifest digest"
  else
    fail "current immutable release qualification manifest digest mismatch (${release_id})"
  fi
}

if [[ -e "${OBS_UPDATE_STATE_FILE}" || -L "${OBS_UPDATE_STATE_FILE}" ]]; then
  update_state="$(awk -F= '$1=="UPDATE_STATE" {print $2; exit}' "${OBS_UPDATE_STATE_FILE}" 2>/dev/null || true)"
  fail "update transition is incomplete (${update_state:-unknown}); run update-transition.sh recover or rollback before maintenance"
else
  pass "no incomplete update transition exists"
fi

current_release=""
if current_release="$(obs_read_release_id "${OBS_CURRENT_LINK}")"; then
  if bash "${OBS_RELEASE_MANAGER}" verify "${current_release}" >/dev/null 2>&1; then
    pass "current immutable release is verified (${current_release})"
  else
    fail "current immutable release failed manifest verification (${current_release})"
  fi
  obs_check_qualification "${current_release}"
else
  rc=$?
  if [[ "${rc}" == 2 ]]; then
    fail "current immutable release pointer is unsafe or dangling (${OBS_CURRENT_LINK})"
  else
    fail "current immutable release pointer is missing (${OBS_CURRENT_LINK})"
  fi
fi

if [[ -e "${OBS_PREVIOUS_LINK}" || -L "${OBS_PREVIOUS_LINK}" ]]; then
  if previous_release="$(obs_read_release_id "${OBS_PREVIOUS_LINK}")"; then
    if bash "${OBS_RELEASE_MANAGER}" verify "${previous_release}" >/dev/null 2>&1; then
      pass "previous immutable release is verified (${previous_release})"
    else
      warn "previous immutable release failed manifest verification (${previous_release})"
    fi
  else
    fail "previous immutable release pointer is unsafe or dangling (${OBS_PREVIOUS_LINK})"
  fi
else
  pass "no previous immutable release is registered"
fi

if [[ -e "${OBS_STOP_REASON_FILE}" || -L "${OBS_STOP_REASON_FILE}" ]]; then
  stop_reason="$(awk -F= '$1=="STOP_REASON" {print $2; exit}' "${OBS_STOP_REASON_FILE}" 2>/dev/null || true)"
  stop_name="$(awk -F= '$1=="STOP_CONTAINER_NAME" {print $2; exit}' "${OBS_STOP_REASON_FILE}" 2>/dev/null || true)"
  stop_id="$(awk -F= '$1=="STOP_CONTAINER_ID" {print $2; exit}' "${OBS_STOP_REASON_FILE}" 2>/dev/null || true)"
  if [[ "${stop_reason}" != memory-protection || "${stop_name}" != "${RUNTIME_CONTAINER}" || -z "${stop_id}" ]]; then
    warn "runtime stop marker is malformed or unexpected (${OBS_STOP_REASON_FILE})"
  elif command -v docker >/dev/null 2>&1 && docker inspect "${RUNTIME_CONTAINER}" >/dev/null 2>&1; then
    observed_id="$(docker inspect --format '{{.Id}}' "${RUNTIME_CONTAINER}" 2>/dev/null || true)"
    observed_state="$(docker inspect --format '{{.State.Status}}' "${RUNTIME_CONTAINER}" 2>/dev/null || true)"
    if [[ "${observed_id}" == "${stop_id}" && "${observed_state}" == running ]]; then
      warn "stale runtime stop marker references the currently running container"
    elif [[ "${observed_id}" == "${stop_id}" ]]; then
      warn "memory-protection stop marker remains for current container (state=${observed_state:-unknown})"
    else
      warn "stale runtime stop marker references an older container"
    fi
  else
    warn "runtime stop marker exists but the referenced runtime is unavailable"
  fi
else
  pass "no stale runtime stop marker exists"
fi

if command -v systemctl >/dev/null 2>&1 && systemctl cat "${SERVICE_UNIT}" >/dev/null 2>&1; then
  unit_text="$(systemctl cat "${SERVICE_UNIT}" 2>/dev/null || true)"
  expected_runtime_root="${DATA_HOME}/current"
  if grep -Fqx "WorkingDirectory=${expected_runtime_root}" <<<"${unit_text}" && \
     grep -Fqx "ExecStart=/bin/bash ${expected_runtime_root}/scripts/service-runner.sh" <<<"${unit_text}"; then
    pass "systemd service uses the immutable current release root"
  else
    fail "systemd service runtime root does not match ${expected_runtime_root}"
  fi
fi

# Schema 4 records user-facing API access intent. Schema <=3 falls back to the
# legacy docker0-only proxy semantics represented by PROXY_ENABLED/PROXY_PORT.
obs_api_mode="${API_ACCESS_MODE:-}"
if [[ -z "${obs_api_mode}" ]]; then
  [[ "${PROXY_ENABLED:-0}" == 1 ]] && obs_api_mode=docker || obs_api_mode=local
fi
obs_docker_port="${API_DOCKER_PORT:-${PROXY_PORT:-8000}}"
obs_lan_address="${API_LAN_ADDRESS:-}"
obs_lan_port="${API_LAN_PORT:-8001}"
if [[ "${obs_api_mode}" == local ]]; then
  pass "API access mode is local-only"
elif command -v systemctl >/dev/null 2>&1 && systemctl cat "${OBS_API_SOCKET_UNIT}" >/dev/null 2>&1; then
  api_unit_text="$(systemctl cat "${OBS_API_SOCKET_UNIT}" 2>/dev/null || true)"
  if systemctl is-active --quiet "${OBS_API_SOCKET_UNIT}" 2>/dev/null; then
    pass "managed API access socket is active"
  else
    fail "managed API access socket is configured but inactive"
  fi
  if grep -Eq "^ListenStream=[^:]+:${obs_docker_port}$" <<<"${api_unit_text}"; then
    pass "Docker-app API listener is configured on port ${obs_docker_port}"
  else
    fail "Docker-app API listener does not match configured port ${obs_docker_port}"
  fi
  if [[ "${obs_api_mode}" == lan ]]; then
    if [[ -n "${obs_lan_address}" ]] && grep -Fqx "ListenStream=${obs_lan_address}:${obs_lan_port}" <<<"${api_unit_text}"; then
      pass "LAN API listener matches ${obs_lan_address}:${obs_lan_port}"
    else
      fail "LAN API listener does not match configured endpoint ${obs_lan_address:-missing}:${obs_lan_port}"
    fi
  fi
else
  fail "managed API access was selected but its socket unit is missing"
fi
