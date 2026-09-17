#!/usr/bin/env bash
# Install, inspect, or remove the managed systemd runtime service.
set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
UNIT="qwen38-flash-next.service"
UNIT_FILE="/etc/systemd/system/${UNIT}"
MARKER="Managed qwen38-spark runtime service"
ACTION="${1:-status}"
[[ $# -eq 0 ]] || shift
START=1
YES=0
RUNTIME_ROOT_OVERRIDE=""
OPERATION_LOCK_LIB="${SCRIPT_ROOT}/scripts/lib/operation-lock.sh"

usage() {
  printf 'Usage: sudo ./scripts/manage-service.sh create [--start|--no-start] [--runtime-root PATH] [--yes]\n'
  printf '       sudo ./scripts/manage-service.sh remove [--yes]\n'
  printf '       ./scripts/manage-service.sh status\n'
}
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
managed_file() { [[ -f "$1" && ! -L "$1" ]] && grep -Fq "${MARKER}" "$1"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --start) START=1 ;;
    --no-start) START=0 ;;
    --runtime-root)
      [[ $# -ge 2 ]] || die "--runtime-root requires a path"
      RUNTIME_ROOT_OVERRIDE="$2"
      shift
      ;;
    --yes) YES=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
  shift
done

if [[ "${ACTION}" == status ]]; then
  installed=no; enabled=no; active=no
  managed_file "${UNIT_FILE}" && installed=yes
  if [[ "${installed}" == yes ]] && command -v systemctl >/dev/null 2>&1; then
    systemctl is-enabled --quiet "${UNIT}" 2>/dev/null && enabled=yes
    systemctl is-active --quiet "${UNIT}" 2>/dev/null && active=yes
  fi
  printf 'Qwen runtime service status\n  installed : %s\n  enabled   : %s\n  active    : %s\n' "${installed}" "${enabled}" "${active}"
  [[ "${installed}" == yes ]]
  exit
fi

[[ ${EUID:-$(id -u)} -eq 0 ]] || die "create/remove requires sudo"
for command in systemctl install grep getent cut stat mktemp realpath docker curl python3 seq flock awk; do command -v "${command}" >/dev/null 2>&1 || die "${command} is required"; done

SERVICE_USER="${SUDO_USER:-${QWEN38_SERVICE_USER:-$(id -un)}}"
[[ "${SERVICE_USER}" != root ]] || die "run through sudo from the user who owns the installation, or set QWEN38_SERVICE_USER"
USER_ENTRY="$(getent passwd "${SERVICE_USER}")"
[[ -n "${USER_ENTRY}" ]] || die "cannot resolve service user: ${SERVICE_USER}"
SERVICE_UID="$(cut -d: -f3 <<<"${USER_ENTRY}")"
SERVICE_GID="$(cut -d: -f4 <<<"${USER_ENTRY}")"
SERVICE_HOME="$(cut -d: -f6 <<<"${USER_ENTRY}")"
SERVICE_GROUP="$(getent group "${SERVICE_GID}" | cut -d: -f1)"
[[ -n "${SERVICE_GROUP}" && -d "${SERVICE_HOME}" ]] || die "cannot resolve service home/group"

CALLER_STATE_HOME="${QWEN38_STATE_HOME:-${SERVICE_HOME}/.local/state}"
STATE_DIR="${CALLER_STATE_HOME}/qwen38-spark"
[[ -r "${OPERATION_LOCK_LIB}" ]] || die "operation lock helper is unavailable: ${OPERATION_LOCK_LIB}"
# shellcheck source=scripts/lib/operation-lock.sh
source "${OPERATION_LOCK_LIB}"
acquire_operation_lock "${STATE_DIR}" "managed service ${ACTION}" "${SERVICE_UID}" "${SERVICE_GID}" || exit $?

if [[ "${ACTION}" == remove ]]; then
  if [[ ! -e "${UNIT_FILE}" ]]; then printf 'Managed runtime service is not installed.\n'; exit 0; fi
  managed_file "${UNIT_FILE}" || die "refusing to remove unmanaged unit: ${UNIT_FILE}"
  [[ "${YES}" == 1 ]] || { read -r -p 'Remove the managed Qwen runtime service? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] || exit 0; }
  systemctl disable --now "${UNIT}" 2>/dev/null || true
  rm -f -- "${UNIT_FILE}"
  systemctl daemon-reload
  systemctl reset-failed "${UNIT}" 2>/dev/null || true
  printf 'Managed Qwen runtime service removed.\n'
  exit 0
fi
[[ "${ACTION}" == create ]] || { usage >&2; exit 2; }

STATE_FILE="${STATE_DIR}/install.env"
RUNTIME_COMMIT_FILE="${STATE_DIR}/runtime-commit.env"
INSTALL_STATE_PARSER="${SCRIPT_ROOT}/scripts/lib/state_file.py"
[[ -f "${STATE_FILE}" && ! -L "${STATE_FILE}" ]] || die "installation manifest is missing or unsafe: ${STATE_FILE}"
[[ "$(stat -c %u "${STATE_FILE}")" == "${SERVICE_UID}" ]] || die "installation manifest is not owned by ${SERVICE_USER}"
[[ -r "${INSTALL_STATE_PARSER}" ]] || die "install state parser is unavailable: ${INSTALL_STATE_PARSER}"

parse_install_service() {
  local parsed key value
  parsed="$(mktemp)"
  if ! python3 "${INSTALL_STATE_PARSER}" install-service "${STATE_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  INSTALL_ROOT=""; SERVED_NAME=""; CONTAINER_NAME=""
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    case "${key}" in
      SCHEMA_VERSION) [[ "${value}" == 3 || "${value}" == 4 ]] || { rm -f -- "${parsed}"; return 1; } ;;
      PHASE) [[ "${value}" == complete ]] || { rm -f -- "${parsed}"; return 1; } ;;
      INSTALL_ROOT) INSTALL_ROOT="${value}" ;;
      SERVED_NAME) SERVED_NAME="${value}" ;;
      CONTAINER_NAME) CONTAINER_NAME="${value}" ;;
      *) rm -f -- "${parsed}"; return 1 ;;
    esac
  done <"${parsed}"
  rm -f -- "${parsed}"
  [[ -n "${INSTALL_ROOT}" && -n "${SERVED_NAME}" && "${CONTAINER_NAME}" == qwen38-flash-next ]]
}
parse_install_service || die "installation manifest failed strict service parsing: ${STATE_FILE}"

RUNTIME_ROOT="${RUNTIME_ROOT_OVERRIDE:-${INSTALL_ROOT}}"
[[ "${RUNTIME_ROOT}" == /* ]] || die "runtime root must be an absolute path"
[[ -x "${RUNTIME_ROOT}/scripts/service-runner.sh" ]] || die "runtime root has no service runner: ${RUNTIME_ROOT}"
[[ -x "${RUNTIME_ROOT}/scripts/serve.sh" ]] || die "runtime root has no serve helper: ${RUNTIME_ROOT}"
[[ -r "${RUNTIME_ROOT}/scripts/runtime-transition.sh" ]] || die "runtime root has no transition helper: ${RUNTIME_ROOT}"
[[ "${RUNTIME_ROOT}" != *[[:space:]]* && "${STATE_FILE}" != *[[:space:]]* ]] || die "service paths cannot contain whitespace"
EXPECTED_RUNTIME_ROOT="$(realpath -e -- "${RUNTIME_ROOT}")"
RUNTIME_STATE_PARSER="${EXPECTED_RUNTIME_ROOT}/scripts/lib/state_file.py"
[[ -r "${RUNTIME_STATE_PARSER}" ]] || die "runtime root has no state parser: ${EXPECTED_RUNTIME_ROOT}"

parse_runtime_commit() {
  local parsed key value
  parsed="$(mktemp)"
  if ! python3 "${RUNTIME_STATE_PARSER}" runtime-commit "${RUNTIME_COMMIT_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  ATTESTED_RUNTIME_ROOT=""; ATTESTED_CONTAINER_NAME=""; ATTESTED_CONTAINER_ID=""; ATTESTED_COMMITTED_AT=""
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    case "${key}" in
      RUNTIME_COMMIT_SCHEMA_VERSION) [[ "${value}" == 1 ]] || { rm -f -- "${parsed}"; return 1; } ;;
      RUNTIME_ROOT) ATTESTED_RUNTIME_ROOT="${value}" ;;
      RUNTIME_CONTAINER_NAME) ATTESTED_CONTAINER_NAME="${value}" ;;
      RUNTIME_CONTAINER_ID) ATTESTED_CONTAINER_ID="${value}" ;;
      COMMITTED_AT) ATTESTED_COMMITTED_AT="${value}" ;;
      *) rm -f -- "${parsed}"; return 1 ;;
    esac
  done <"${parsed}"
  rm -f -- "${parsed}"
  [[ -n "${ATTESTED_RUNTIME_ROOT}" && -n "${ATTESTED_CONTAINER_NAME}" && -n "${ATTESTED_CONTAINER_ID}" && -n "${ATTESTED_COMMITTED_AT}" ]]
}

runtime_commit_matches() {
  local expected_container_id="$1"
  [[ -f "${RUNTIME_COMMIT_FILE}" && ! -L "${RUNTIME_COMMIT_FILE}" ]] || return 1
  parse_runtime_commit || die "runtime commit attestation is invalid: ${RUNTIME_COMMIT_FILE}"
  [[ "${ATTESTED_RUNTIME_ROOT}" == "${EXPECTED_RUNTIME_ROOT}" ]] || return 1
  [[ "${ATTESTED_CONTAINER_NAME}" == "${CONTAINER_NAME}" ]] || return 1
  [[ "${ATTESTED_CONTAINER_ID}" == "${expected_container_id}" ]] || return 1
}

print_readiness_progress() {
  local elapsed="$1" candidate_container_id="$2"
  local active_state sub_state container_state health_state attestation_state log_line

  active_state="$(systemctl show "${UNIT}" --property=ActiveState --value 2>/dev/null || printf unknown)"
  sub_state="$(systemctl show "${UNIT}" --property=SubState --value 2>/dev/null || printf unknown)"

  container_state=missing
  if [[ -n "${candidate_container_id}" ]]; then
    container_state="$(docker inspect --format '{{.State.Status}}' "${CONTAINER_NAME}" 2>/dev/null || printf unknown)"
  fi

  health_state=waiting
  if curl -fsS --max-time 3 http://127.0.0.1:8888/health >/dev/null 2>&1; then
    health_state=ready
  fi

  attestation_state=missing
  if [[ -f "${RUNTIME_COMMIT_FILE}" && ! -L "${RUNTIME_COMMIT_FILE}" ]]; then
    if parse_runtime_commit; then
      if [[ -n "${candidate_container_id}" &&
            "${ATTESTED_RUNTIME_ROOT}" == "${EXPECTED_RUNTIME_ROOT}" &&
            "${ATTESTED_CONTAINER_NAME}" == "${CONTAINER_NAME}" &&
            "${ATTESTED_CONTAINER_ID}" == "${candidate_container_id}" ]]; then
        attestation_state=matching
      else
        attestation_state=present-mismatch
      fi
    else
      attestation_state=invalid
    fi
  fi

  log_line="$(journalctl -u "${UNIT}" -n 1 --no-pager -o cat 2>/dev/null | tail -n 1 || true)"
  [[ -n "${log_line}" ]] || log_line="(no service log yet)"

  printf 'Waiting for committed replacement runtime attestation: %d/1800 seconds\n' "${elapsed}"
  printf '  service     : %s/%s\n' "${active_state}" "${sub_state}"
  printf '  container   : %s%s\n' "${container_state}" "${candidate_container_id:+ (${candidate_container_id})}"
  printf '  health      : %s\n' "${health_state}"
  printf '  attestation : %s\n' "${attestation_state}"
  printf '  latest log  : %s\n' "${log_line}"
}

if [[ -e "${UNIT_FILE}" ]]; then
  managed_file "${UNIT_FILE}" || die "refusing to replace unmanaged unit: ${UNIT_FILE}"
fi
[[ "${YES}" == 1 ]] || { read -r -p "Install ${UNIT} for ${SERVICE_USER}? [Y/n]: " answer; [[ -z "${answer}" || "${answer}" == y || "${answer}" == Y ]] || exit 0; }

tmp_dir="$(mktemp -d)"
trap 'rm -rf -- "${tmp_dir}"' EXIT
cat >"${tmp_dir}/${UNIT}" <<EOF
# ${MARKER}; installed by scripts/manage-service.sh
[Unit]
Description=Qwen3.8 Flash Next service on one DGX Spark
Requires=docker.service
Wants=network-online.target
After=docker.service network-online.target
StartLimitIntervalSec=3600
StartLimitBurst=2

[Service]
Type=simple
User=${SERVICE_USER}
Group=${SERVICE_GROUP}
WorkingDirectory=${RUNTIME_ROOT}
Environment=HOME=${SERVICE_HOME}
Environment=QWEN38_STATE_FILE=${STATE_FILE}
ExecStart=/bin/bash ${RUNTIME_ROOT}/scripts/service-runner.sh
ExecStop=-/usr/bin/docker stop --timeout 30 ${CONTAINER_NAME}
Restart=on-failure
RestartSec=60
TimeoutStartSec=infinity
TimeoutStopSec=180
KillMode=control-group

[Install]
WantedBy=multi-user.target
EOF

install -o root -g root -m 0644 "${tmp_dir}/${UNIT}" "${UNIT_FILE}"
systemctl daemon-reload
systemctl enable "${UNIT}"
if [[ "${START}" == 1 ]]; then
  previous_container_id="$(docker inspect --format '{{.Id}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
  rm -f -- "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"
  systemctl reset-failed "${UNIT}" 2>/dev/null || true
  systemctl stop "${UNIT}" 2>/dev/null || true
  systemctl start "${UNIT}"
  ready=0
  for attempt in $(seq 1 180); do
    unit_state="$(systemctl show "${UNIT}" --property=ActiveState --value)"
    case "${unit_state}" in active|activating|reloading) ;; *) die "service stopped before readiness (state=${unit_state})" ;; esac
    candidate_container_id="$(docker inspect --format '{{.Id}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
    if [[ -n "${candidate_container_id}" && "${candidate_container_id}" != "${previous_container_id}" ]] && \
       curl -fsS --max-time 3 http://127.0.0.1:8888/health >/dev/null 2>&1 && \
       runtime_commit_matches "${candidate_container_id}"; then
      ready=1
      break
    fi
    if (( attempt % 6 == 0 )); then printf 'Waiting for committed replacement runtime attestation: %d/1800 seconds\n' "$((attempt * 10))"; fi
    sleep 10
  done
  [[ "${ready}" == 1 ]] || die "replacement runtime did not commit and attest within 30 minutes"
  models="$(curl -fsS --max-time 15 http://127.0.0.1:8888/v1/models)"
  python3 -c 'import json,sys; expected=sys.argv[1]; data=json.load(sys.stdin); assert any(item.get("id") == expected for item in data.get("data", [])), expected' \
    "${SERVED_NAME}" <<<"${models}" || die "served model ID validation failed"
  runtime_commit_matches "${candidate_container_id}" || die "runtime commit attestation changed after model validation"
  systemctl is-active --quiet "${UNIT}" || die "service became inactive after committed readiness"
  printf 'Runtime service is enabled, committed, and healthy. Logs:\n  journalctl -fu %s\n' "${UNIT}"
else
  printf 'Runtime service installed and enabled; current runtime was not restarted.\n'
fi
