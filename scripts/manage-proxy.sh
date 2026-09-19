#!/usr/bin/env bash
# Manage Docker-app and optional LAN access to the loopback-only vLLM endpoint.
set -euo pipefail

ACTION="${1:-status}"
[[ $# -eq 0 ]] || shift
DOCKER_PORT=8000
LAN_ADDRESS=""
LAN_PORT=8001
BACKEND_PORT=8888
YES=0
PROXY_SOCKET_UNIT="qwen38-openwebui-proxy.socket"
PROXY_SERVICE_UNIT="qwen38-openwebui-proxy.service"
PROXY_SOCKET_FILE="/etc/systemd/system/${PROXY_SOCKET_UNIT}"
PROXY_SERVICE_FILE="/etc/systemd/system/${PROXY_SERVICE_UNIT}"
# Keep the legacy marker/unit names so existing managed installations can be adopted/updated safely.
MARKER="Managed qwen38-spark OpenWebUI proxy"

if [[ "${ACTION}" == -h || "${ACTION}" == --help ]]; then ACTION=help; fi

usage() {
  cat <<'EOF'
Usage: sudo ./scripts/manage-proxy.sh create [--docker-port 8000] [--lan-address IPv4] [--lan-port 8001] [--backend-port 8888] [--yes]
       sudo ./scripts/manage-proxy.sh create [--listen-port 8000] ...   # legacy alias for --docker-port
       sudo ./scripts/manage-proxy.sh remove [--yes]
       ./scripts/manage-proxy.sh status
       ./scripts/manage-proxy.sh adopt

The managed API access service always exposes the loopback vLLM backend to Docker
applications through docker0. When --lan-address is supplied, it also exposes the
same backend on that exact host IPv4 address. Wildcard listeners such as 0.0.0.0
are intentionally unsupported.
EOF
}
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
valid_port() { [[ "$1" =~ ^[0-9]+$ ]] && (( 10#$1 >= 1 && 10#$1 <= 65535 )); }
valid_ipv4() {
  local ip="$1" IFS=. octets index
  [[ "${ip}" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 1
  read -r -a octets <<<"${ip}"
  [[ ${#octets[@]} -eq 4 ]] || return 1
  for index in 0 1 2 3; do
    (( 10#${octets[$index]} >= 0 && 10#${octets[$index]} <= 255 )) || return 1
  done
}
managed_file() { [[ -f "$1" && ! -L "$1" ]] && grep -Fq "${MARKER}" "$1"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --docker-port|--listen-port) [[ $# -ge 2 ]] || die "$1 requires a value"; DOCKER_PORT="$2"; shift ;;
    --lan-address) [[ $# -ge 2 ]] || die "$1 requires a value"; LAN_ADDRESS="$2"; shift ;;
    --lan-port) [[ $# -ge 2 ]] || die "$1 requires a value"; LAN_PORT="$2"; shift ;;
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
  if managed_file "${PROXY_SOCKET_FILE}" && managed_file "${PROXY_SERVICE_FILE}"; then installed=yes; fi
  if [[ "${installed}" == yes ]] && command -v systemctl >/dev/null && \
     systemctl is-active --quiet "${PROXY_SOCKET_UNIT}" 2>/dev/null; then active=yes; fi
  printf 'Qwen API access status\n  installed : %s\n  active    : %s\n' "${installed}" "${active}"
  if [[ "${installed}" == yes ]]; then
    awk -F= '$1=="ListenStream" {printf "  listener  : %s\n", $2}' "${PROXY_SOCKET_FILE}"
  fi
  [[ "${installed}" == yes ]]
  exit
fi

if [[ "${ACTION}" == adopt ]]; then
  STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
  STATE_FILE="${STATE_DIR}/install.env"
  for command in awk chmod grep id ip mktemp mv stat; do command -v "${command}" >/dev/null || die "${command} is required"; done
  [[ ${EUID:-$(id -u)} -ne 0 ]] || die "run adopt as the installation user, without sudo"
  [[ -f "${STATE_FILE}" && ! -L "${STATE_FILE}" ]] || die "installation manifest not found or unsafe: ${STATE_FILE}"
  [[ "$(stat -c %u "${STATE_FILE}")" == "$(id -u)" ]] || die "installation manifest is not owned by the current user"
  [[ "$(stat -c %a "${STATE_FILE}")" == 600 ]] || die "installation manifest must have mode 600"
  managed_file "${PROXY_SOCKET_FILE}" && managed_file "${PROXY_SERVICE_FILE}" || die "managed API access units are not installed"
  [[ "$(stat -c %u "${PROXY_SOCKET_FILE}")" == 0 && "$(stat -c %u "${PROXY_SERVICE_FILE}")" == 0 ]] || die "API access units are not root-owned"

  docker_host="$(ip -4 -o addr show dev docker0 scope global 2>/dev/null | awk 'NR==1 {split($4,a,"/"); print a[1]}')"
  [[ -n "${docker_host}" ]] || die "docker0 has no IPv4 address"
  recorded_docker_port=""
  recorded_lan_address=""
  recorded_lan_port=""
  while IFS= read -r listener; do
    address="${listener%:*}"
    port="${listener##*:}"
    valid_port "${port}" || die "invalid managed listener port: ${listener}"
    if [[ "${address}" == "${docker_host}" ]]; then
      [[ -z "${recorded_docker_port}" ]] || die "multiple docker0 listeners are unsupported"
      recorded_docker_port="${port}"
    else
      [[ -z "${recorded_lan_address}" ]] || die "multiple LAN listeners are unsupported"
      recorded_lan_address="${address}"
      recorded_lan_port="${port}"
    fi
  done < <(awk -F= '$1=="ListenStream" {print $2}' "${PROXY_SOCKET_FILE}")
  valid_port "${recorded_docker_port}" || die "cannot determine Docker-app API port"

  # install.sh writes shell-escaped values to a user-owned mode-600 file.
  # shellcheck disable=SC1090
  source "${STATE_FILE}"
  [[ -n "${INSTALL_ROOT:-}" && -d "${INSTALL_ROOT}" ]] || die "invalid installation manifest"
  temporary="$(mktemp "${STATE_FILE}.XXXXXX")"
  trap 'rm -f -- "${temporary}"' EXIT
  grep -Ev '^(SCHEMA_VERSION|PROXY_(ENABLED|OWNED|PORT)|API_(ACCESS_MODE|DOCKER_PORT|LAN_ADDRESS|LAN_PORT))=' "${STATE_FILE}" > "${temporary}"
  {
    printf 'SCHEMA_VERSION=%q\n' 4
    printf 'PROXY_ENABLED=%q\n' 1
    printf 'PROXY_OWNED=%q\n' 1
    printf 'PROXY_PORT=%q\n' "${recorded_docker_port}"
    if [[ -n "${recorded_lan_address}" ]]; then
      printf 'API_ACCESS_MODE=%q\n' lan
      printf 'API_LAN_ADDRESS=%q\n' "${recorded_lan_address}"
      printf 'API_LAN_PORT=%q\n' "${recorded_lan_port}"
    else
      printf 'API_ACCESS_MODE=%q\n' docker
      printf 'API_LAN_ADDRESS=%q\n' ''
      printf 'API_LAN_PORT=%q\n' 8001
    fi
    printf 'API_DOCKER_PORT=%q\n' "${recorded_docker_port}"
  } >> "${temporary}"
  chmod 600 "${temporary}"
  mv -- "${temporary}" "${STATE_FILE}"
  trap - EXIT
  printf 'Managed API access adopted by installation manifest: %s\n' "${STATE_FILE}"
  exit 0
fi

[[ ${EUID:-$(id -u)} -eq 0 ]] || die "run create/remove with sudo"
for command in systemctl grep stat; do command -v "${command}" >/dev/null || die "${command} is required"; done

if [[ "${ACTION}" == remove ]]; then
  for path in "${PROXY_SOCKET_FILE}" "${PROXY_SERVICE_FILE}"; do
    if [[ -e "${path}" || -L "${path}" ]]; then
      [[ -f "${path}" && ! -L "${path}" && "$(stat -c %u "${path}")" == 0 ]] || die "unsafe unit file: ${path}"
      grep -Fq "${MARKER}" "${path}" || die "refusing unmanaged unit: ${path}"
    fi
  done
  [[ "${YES}" == 1 ]] || { read -r -p 'Remove the managed Qwen API access endpoints? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] || exit 0; }
  systemctl disable --now "${PROXY_SOCKET_UNIT}" 2>/dev/null || true
  systemctl stop "${PROXY_SERVICE_UNIT}" 2>/dev/null || true
  rm -f -- "${PROXY_SOCKET_FILE}" "${PROXY_SERVICE_FILE}"
  systemctl daemon-reload
  systemctl reset-failed "${PROXY_SOCKET_UNIT}" "${PROXY_SERVICE_UNIT}" 2>/dev/null || true
  printf 'Managed Qwen API access endpoints removed.\n'
  exit 0
fi

valid_port "${DOCKER_PORT}" || die "invalid Docker-app port: ${DOCKER_PORT}"
valid_port "${BACKEND_PORT}" || die "invalid backend port: ${BACKEND_PORT}"
[[ "${DOCKER_PORT}" != "${BACKEND_PORT}" ]] || die "Docker-app and backend ports must differ"
if [[ -n "${LAN_ADDRESS}" ]]; then
  valid_ipv4 "${LAN_ADDRESS}" || die "invalid LAN IPv4 address: ${LAN_ADDRESS}"
  valid_port "${LAN_PORT}" || die "invalid LAN port: ${LAN_PORT}"
  [[ "${LAN_PORT}" != "${BACKEND_PORT}" ]] || die "LAN and backend ports must differ"
  [[ "${LAN_ADDRESS}" != 0.0.0.0 && "${LAN_ADDRESS}" != 127.* ]] || die "LAN address must be a specific non-loopback IPv4 address"
fi
for command in ip ss awk install mktemp; do command -v "${command}" >/dev/null || die "${command} is required"; done
PROXY_BIN="$(command -v systemd-socket-proxyd 2>/dev/null || true)"
for candidate in /usr/lib/systemd/systemd-socket-proxyd /lib/systemd/systemd-socket-proxyd; do
  [[ -x "${candidate}" ]] && PROXY_BIN="${candidate}" && break
done
[[ -x "${PROXY_BIN}" ]] || die "systemd-socket-proxyd was not found"
DOCKER_HOST="$(ip -4 -o addr show dev docker0 scope global 2>/dev/null | awk 'NR==1 {split($4,a,"/"); print a[1]}')"
[[ -n "${DOCKER_HOST}" && "${DOCKER_HOST}" != 0.0.0.0 && "${DOCKER_HOST}" != 127.* ]] || die "docker0 has no safe IPv4 address"
if [[ -n "${LAN_ADDRESS}" ]]; then
  [[ "${LAN_ADDRESS}" != "${DOCKER_HOST}" ]] || die "LAN address must not be the docker0 address"
  ip -4 -o addr show scope global | awk '{split($4,a,"/"); print a[1]}' | grep -Fxq "${LAN_ADDRESS}" || \
    die "LAN address is not assigned to this host: ${LAN_ADDRESS}"
fi

managed_existing=0
if [[ -e "${PROXY_SOCKET_FILE}" || -e "${PROXY_SERVICE_FILE}" ]]; then
  managed_file "${PROXY_SOCKET_FILE}" && managed_file "${PROXY_SERVICE_FILE}" || die "refusing unmanaged or partial API access units"
  managed_existing=1
fi
if [[ "${managed_existing}" == 0 ]]; then
  ss -H -ltn | awk '{print $4}' | grep -Fqx "${DOCKER_HOST}:${DOCKER_PORT}" && die "${DOCKER_HOST}:${DOCKER_PORT} is already in use"
  if [[ -n "${LAN_ADDRESS}" ]]; then
    ss -H -ltn | awk '{print $4}' | grep -Fqx "${LAN_ADDRESS}:${LAN_PORT}" && die "${LAN_ADDRESS}:${LAN_PORT} is already in use"
  fi
fi

if [[ "${YES}" != 1 ]]; then
  prompt="Create Docker-app API ${DOCKER_HOST}:${DOCKER_PORT} -> 127.0.0.1:${BACKEND_PORT}"
  [[ -z "${LAN_ADDRESS}" ]] || prompt+=" and LAN API ${LAN_ADDRESS}:${LAN_PORT}"
  read -r -p "${prompt}? [y/N]: " answer
  [[ "${answer}" == y || "${answer}" == Y ]] || exit 0
fi

temporary="$(mktemp -d)"; trap 'rm -rf -- "${temporary}"' EXIT
staged_socket="${temporary}/$(basename -- "${PROXY_SOCKET_FILE}")"
staged_service="${temporary}/$(basename -- "${PROXY_SERVICE_FILE}")"
[[ "${staged_socket}" == "${temporary}/"* && "${staged_service}" == "${temporary}/"* ]] || \
  die "unsafe proxy staging path"
{
  cat <<EOF
# ${MARKER}
[Unit]
Description=Qwen3.8 managed API access socket
After=docker.service
Requires=docker.service

[Socket]
ListenStream=${DOCKER_HOST}:${DOCKER_PORT}
EOF
  [[ -z "${LAN_ADDRESS}" ]] || printf 'ListenStream=%s:%s\n' "${LAN_ADDRESS}" "${LAN_PORT}"
  cat <<'EOF'
NoDelay=true

[Install]
WantedBy=sockets.target
EOF
} >"${staged_socket}"
cat >"${staged_service}" <<EOF
# ${MARKER}
[Unit]
Description=Qwen3.8 managed API access service

[Service]
ExecStart=${PROXY_BIN} 127.0.0.1:${BACKEND_PORT}
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
NoNewPrivileges=true
EOF
systemctl stop "${PROXY_SOCKET_UNIT}" "${PROXY_SERVICE_UNIT}" 2>/dev/null || true
install -o root -g root -m 0644 "${staged_socket}" "${PROXY_SOCKET_FILE}"
install -o root -g root -m 0644 "${staged_service}" "${PROXY_SERVICE_FILE}"
systemctl daemon-reload
systemctl enable --now "${PROXY_SOCKET_UNIT}"
printf 'Docker-app API ready: http://host.docker.internal:%s/v1 (%s:%s -> 127.0.0.1:%s)\n' \
  "${DOCKER_PORT}" "${DOCKER_HOST}" "${DOCKER_PORT}" "${BACKEND_PORT}"
if [[ -n "${LAN_ADDRESS}" ]]; then
  printf 'LAN API ready: http://%s:%s/v1 -> 127.0.0.1:%s\n' "${LAN_ADDRESS}" "${LAN_PORT}" "${BACKEND_PORT}"
fi
if [[ -n "${SUDO_USER:-}" && "${SUDO_USER}" != root ]]; then
  printf 'To let uninstall.sh manage manually created API access endpoints, run without sudo:\n'
  printf '  ./scripts/manage-proxy.sh adopt\n'
fi
