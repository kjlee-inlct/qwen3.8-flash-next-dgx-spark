#!/usr/bin/env bash
# Manage a docker0-only systemd socket proxy to the loopback vLLM endpoint.
set -euo pipefail

ACTION="${1:-status}"
[[ $# -eq 0 ]] || shift
LISTEN_PORT=8000
BACKEND_PORT=8888
YES=0
SOCKET_UNIT="qwen38-openwebui-proxy.socket"
SERVICE_UNIT="qwen38-openwebui-proxy.service"
SOCKET_FILE="/etc/systemd/system/${SOCKET_UNIT}"
SERVICE_FILE="/etc/systemd/system/${SERVICE_UNIT}"
MARKER="Managed qwen38-spark OpenWebUI proxy"

if [[ "${ACTION}" == -h || "${ACTION}" == --help ]]; then ACTION=help; fi

usage() {
  cat <<'EOF'
Usage: sudo ./scripts/manage-proxy.sh create [--listen-port 8000] [--backend-port 8888] [--yes]
       sudo ./scripts/manage-proxy.sh remove [--yes]
       ./scripts/manage-proxy.sh status
       ./scripts/manage-proxy.sh adopt

The proxy listens only on docker0 and forwards to 127.0.0.1. Arbitrary listen
addresses and 0.0.0.0 are intentionally unsupported.
EOF
}
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
valid_port() { [[ "$1" =~ ^[0-9]+$ ]] && (( 10#$1 >= 1 && 10#$1 <= 65535 )); }
managed_file() { [[ -f "$1" && ! -L "$1" ]] && grep -Fq "${MARKER}" "$1"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --listen-port) [[ $# -ge 2 ]] || die "$1 requires a value"; LISTEN_PORT="$2"; shift ;;
    --backend-port) [[ $# -ge 2 ]] || die "$1 requires a value"; BACKEND_PORT="$2"; shift ;;
    --yes) YES=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
  shift
done
[[ "${ACTION}" == help ]] && { usage; exit 0; }
[[ "${ACTION}" == create || "${ACTION}" == remove || "${ACTION}" == status || "${ACTION}" == adopt ]] || die "unknown action: ${ACTION}"

if [[ "${ACTION}" == status ]]; then
  installed=no; active=no
  if managed_file "${SOCKET_FILE}" && managed_file "${SERVICE_FILE}"; then installed=yes; fi
  if [[ "${installed}" == yes ]] && command -v systemctl >/dev/null && \
     systemctl is-active --quiet "${SOCKET_UNIT}" 2>/dev/null; then active=yes; fi
  printf 'OpenWebUI proxy status\n  installed : %s\n  active    : %s\n' "${installed}" "${active}"
  [[ "${installed}" == yes ]]
  exit
fi

if [[ "${ACTION}" == adopt ]]; then
  STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
  STATE_FILE="${STATE_DIR}/install.env"
  for command in awk chmod grep id mktemp mv stat; do command -v "${command}" >/dev/null || die "${command} is required"; done
  [[ ${EUID:-$(id -u)} -ne 0 ]] || die "run adopt as the installation user, without sudo"
  [[ -f "${STATE_FILE}" && ! -L "${STATE_FILE}" ]] || die "installation manifest not found or unsafe: ${STATE_FILE}"
  [[ "$(stat -c %u "${STATE_FILE}")" == "$(id -u)" ]] || die "installation manifest is not owned by the current user"
  [[ "$(stat -c %a "${STATE_FILE}")" == 600 ]] || die "installation manifest must have mode 600"
  managed_file "${SOCKET_FILE}" && managed_file "${SERVICE_FILE}" || die "managed proxy units are not installed"
  [[ "$(stat -c %u "${SOCKET_FILE}")" == 0 && "$(stat -c %u "${SERVICE_FILE}")" == 0 ]] || die "proxy units are not root-owned"
  recorded_port="$(awk -F'[=:]' '$1=="ListenStream" {print $NF}' "${SOCKET_FILE}")"
  valid_port "${recorded_port}" || die "cannot determine proxy listen port"
  # shellcheck disable=SC1090 -- install.sh writes shell-escaped values to a user-owned mode-600 file.
  source "${STATE_FILE}"
  [[ -n "${INSTALL_ROOT:-}" && -d "${INSTALL_ROOT}" ]] || die "invalid installation manifest"
  temporary="$(mktemp "${STATE_FILE}.XXXXXX")"
  trap 'rm -f -- "${temporary}"' EXIT
  grep -Ev '^PROXY_(ENABLED|OWNED|PORT)=' "${STATE_FILE}" > "${temporary}"
  {
    printf 'PROXY_ENABLED=%q\n' 1
    printf 'PROXY_OWNED=%q\n' 1
    printf 'PROXY_PORT=%q\n' "${recorded_port}"
  } >> "${temporary}"
  chmod 600 "${temporary}"
  mv -- "${temporary}" "${STATE_FILE}"
  trap - EXIT
  printf 'Managed proxy adopted by installation manifest: %s (port %s)\n' "${STATE_FILE}" "${recorded_port}"
  exit 0
fi

[[ ${EUID:-$(id -u)} -eq 0 ]] || die "run create/remove with sudo"
for command in systemctl grep stat; do command -v "${command}" >/dev/null || die "${command} is required"; done

if [[ "${ACTION}" == remove ]]; then
  for path in "${SOCKET_FILE}" "${SERVICE_FILE}"; do
    if [[ -e "${path}" || -L "${path}" ]]; then
      [[ -f "${path}" && ! -L "${path}" && "$(stat -c %u "${path}")" == 0 ]] || die "unsafe unit file: ${path}"
      grep -Fq "${MARKER}" "${path}" || die "refusing unmanaged unit: ${path}"
    fi
  done
  [[ "${YES}" == 1 ]] || { read -r -p 'Remove the managed OpenWebUI proxy? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] || exit 0; }
  systemctl disable --now "${SOCKET_UNIT}" 2>/dev/null || true
  systemctl stop "${SERVICE_UNIT}" 2>/dev/null || true
  rm -f -- "${SOCKET_FILE}" "${SERVICE_FILE}"
  systemctl daemon-reload
  systemctl reset-failed "${SOCKET_UNIT}" "${SERVICE_UNIT}" 2>/dev/null || true
  printf 'Managed OpenWebUI proxy removed.\n'
  exit 0
fi

valid_port "${LISTEN_PORT}" || die "invalid listen port: ${LISTEN_PORT}"
valid_port "${BACKEND_PORT}" || die "invalid backend port: ${BACKEND_PORT}"
[[ "${LISTEN_PORT}" != "${BACKEND_PORT}" ]] || die "listen and backend ports must differ"
for command in ip ss awk install mktemp; do command -v "${command}" >/dev/null || die "${command} is required"; done
PROXY_BIN="$(command -v systemd-socket-proxyd 2>/dev/null || true)"
for candidate in /usr/lib/systemd/systemd-socket-proxyd /lib/systemd/systemd-socket-proxyd; do
  [[ -x "${candidate}" ]] && PROXY_BIN="${candidate}" && break
done
[[ -x "${PROXY_BIN}" ]] || die "systemd-socket-proxyd was not found"
LISTEN_HOST="$(ip -4 -o addr show dev docker0 scope global 2>/dev/null | awk 'NR==1 {split($4,a,"/"); print a[1]}')"
[[ -n "${LISTEN_HOST}" && "${LISTEN_HOST}" != 0.0.0.0 && "${LISTEN_HOST}" != 127.* ]] || die "docker0 has no safe IPv4 address"
if [[ -e "${SOCKET_FILE}" || -e "${SERVICE_FILE}" ]]; then
  managed_file "${SOCKET_FILE}" && managed_file "${SERVICE_FILE}" || die "refusing unmanaged or partial proxy units"
elif ss -H -ltn | awk '{print $4}' | grep -Eq "(^|])${LISTEN_HOST}:${LISTEN_PORT}$"; then
  die "${LISTEN_HOST}:${LISTEN_PORT} is already in use"
fi
[[ "${YES}" == 1 ]] || { read -r -p "Create proxy ${LISTEN_HOST}:${LISTEN_PORT} -> 127.0.0.1:${BACKEND_PORT}? [y/N]: " answer; [[ "${answer}" == y || "${answer}" == Y ]] || exit 0; }

temporary="$(mktemp -d)"; trap 'rm -rf -- "${temporary}"' EXIT
cat >"${temporary}/${SOCKET_UNIT}" <<EOF
# ${MARKER}
[Unit]
Description=Qwen3.8 OpenWebUI proxy socket
After=docker.service
Requires=docker.service

[Socket]
ListenStream=${LISTEN_HOST}:${LISTEN_PORT}
NoDelay=true

[Install]
WantedBy=sockets.target
EOF
cat >"${temporary}/${SERVICE_UNIT}" <<EOF
# ${MARKER}
[Unit]
Description=Qwen3.8 OpenWebUI proxy service

[Service]
ExecStart=${PROXY_BIN} 127.0.0.1:${BACKEND_PORT}
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
NoNewPrivileges=true
EOF
systemctl stop "${SOCKET_UNIT}" "${SERVICE_UNIT}" 2>/dev/null || true
install -o root -g root -m 0644 "${temporary}/${SOCKET_UNIT}" "${SOCKET_FILE}"
install -o root -g root -m 0644 "${temporary}/${SERVICE_UNIT}" "${SERVICE_FILE}"
systemctl daemon-reload
systemctl enable --now "${SOCKET_UNIT}"
printf 'OpenWebUI proxy ready: http://host.docker.internal:%s/v1 (%s:%s -> 127.0.0.1:%s)\n' \
  "${LISTEN_PORT}" "${LISTEN_HOST}" "${LISTEN_PORT}" "${BACKEND_PORT}"
if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != root ]]; then
  printf 'To let uninstall.sh manage this manually created proxy, run without sudo:\n'
  printf '  ./scripts/manage-proxy.sh adopt\n'
fi
