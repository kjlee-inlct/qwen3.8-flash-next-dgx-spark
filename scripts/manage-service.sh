#!/usr/bin/env bash
# Install, inspect, or remove the managed systemd runtime service.
set -Eeuo pipefail

UNIT="qwen38-flash-next.service"
UNIT_FILE="/etc/systemd/system/${UNIT}"
MARKER="Managed qwen38-spark runtime service"
ACTION="${1:-status}"
[[ $# -eq 0 ]] || shift
START=1
YES=0
RUNTIME_ROOT_OVERRIDE=""

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
for command in systemctl install grep getent cut stat mktemp docker curl python3 seq; do command -v "${command}" >/dev/null 2>&1 || die "${command} is required"; done

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

SERVICE_USER="${SUDO_USER:-$(id -un)}"
[[ "${SERVICE_USER}" != root ]] || die "run through sudo from the user who owns the installation"
USER_ENTRY="$(getent passwd "${SERVICE_USER}")"
[[ -n "${USER_ENTRY}" ]] || die "cannot resolve service user: ${SERVICE_USER}"
SERVICE_UID="$(cut -d: -f3 <<<"${USER_ENTRY}")"
SERVICE_GID="$(cut -d: -f4 <<<"${USER_ENTRY}")"
SERVICE_HOME="$(cut -d: -f6 <<<"${USER_ENTRY}")"
SERVICE_GROUP="$(getent group "${SERVICE_GID}" | cut -d: -f1)"
[[ -n "${SERVICE_GROUP}" && -d "${SERVICE_HOME}" ]] || die "cannot resolve service home/group"

CALLER_STATE_HOME="${QWEN38_STATE_HOME:-${SERVICE_HOME}/.local/state}"
STATE_FILE="${CALLER_STATE_HOME}/qwen38-spark/install.env"
[[ -f "${STATE_FILE}" && ! -L "${STATE_FILE}" ]] || die "installation manifest is missing or unsafe: ${STATE_FILE}"
[[ "$(stat -c %u "${STATE_FILE}")" == "${SERVICE_UID}" ]] || die "installation manifest is not owned by ${SERVICE_USER}"
# The installer writes shell-escaped values with mode 600.
# shellcheck disable=SC1090
source "${STATE_FILE}"
[[ "${INSTALL_ROOT:-}" == /* ]] || die "invalid install root in manifest"
[[ "${CONTAINER_NAME:-}" == qwen38-flash-next ]] || die "unexpected container name in manifest"

RUNTIME_ROOT="${RUNTIME_ROOT_OVERRIDE:-${INSTALL_ROOT}}"
[[ "${RUNTIME_ROOT}" == /* ]] || die "runtime root must be an absolute path"
[[ -x "${RUNTIME_ROOT}/scripts/service-runner.sh" ]] || die "runtime root has no service runner: ${RUNTIME_ROOT}"
[[ -x "${RUNTIME_ROOT}/scripts/serve.sh" ]] || die "runtime root has no serve helper: ${RUNTIME_ROOT}"
[[ -r "${RUNTIME_ROOT}/scripts/runtime-transition.sh" ]] || die "runtime root has no transition helper: ${RUNTIME_ROOT}"
[[ "${RUNTIME_ROOT}" != *[[:space:]]* && "${STATE_FILE}" != *[[:space:]]* ]] || die "service paths cannot contain whitespace"

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
  systemctl reset-failed "${UNIT}" 2>/dev/null || true
  systemctl stop "${UNIT}" 2>/dev/null || true
  systemctl start "${UNIT}"
  ready=0
  for attempt in $(seq 1 180); do
    unit_state="$(systemctl show "${UNIT}" --property=ActiveState --value)"
    case "${unit_state}" in active|activating|reloading) ;; *) die "service stopped before readiness (state=${unit_state})" ;; esac
    candidate_container_id="$(docker inspect --format '{{.Id}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
    if [[ -n "${candidate_container_id}" && "${candidate_container_id}" != "${previous_container_id}" ]] && \
       curl -fsS --max-time 3 http://127.0.0.1:8888/health >/dev/null 2>&1; then
      ready=1
      break
    fi
    if (( attempt % 6 == 0 )); then printf 'Waiting for committed replacement runtime: %d/1800 seconds\n' "$((attempt * 10))"; fi
    sleep 10
  done
  [[ "${ready}" == 1 ]] || die "replacement runtime did not become healthy within 30 minutes"
  models="$(curl -fsS --max-time 15 http://127.0.0.1:8888/v1/models)"
  python3 -c 'import json,sys; expected=sys.argv[1]; data=json.load(sys.stdin); assert any(item.get("id") == expected for item in data.get("data", [])), expected' \
    "${SERVED_NAME:-orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4}" <<<"${models}" || die "served model ID validation failed"
  systemctl is-active --quiet "${UNIT}" || die "service became inactive after readiness"
  printf 'Runtime service is enabled and healthy. Logs:\n  journalctl -fu %s\n' "${UNIT}"
else
  printf 'Runtime service installed and enabled; current runtime was not restarted.\n'
fi
