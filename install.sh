#!/usr/bin/env bash
# Interactive installer for OrcaRouter Qwen3.8-Flash-Next on one DGX Spark.
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/model-profiles.sh
source "${ROOT_DIR}/scripts/model-profiles.sh"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/install.env"
STATE_PARSER="${ROOT_DIR}/scripts/lib/state_file.py"
OPERATION_LOCK_LIB="${ROOT_DIR}/scripts/lib/operation-lock.sh"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"
CURRENT_RELEASE_LINK="${DATA_HOME}/current"
SWAP_FILE="${SWAP_FILE:-/swap-ple.img}"
CONFIG_OVERRIDE="${CONFIG_OVERRIDE:-}"
MODEL_PROFILE="${MODEL_PROFILE:-orcarouter}"
MODEL_CLI=""
YES=0; START=1; DRY_RUN=0; MIGRATE_MANIFEST=0; CONFIG_OWNED=0
MONITOR_ENABLED="${MONITOR_ENABLED:-}"
MONITOR_PROTECT="${MONITOR_PROTECT:-0}"
MONITOR_MIN_AVAILABLE_GIB="${MONITOR_MIN_AVAILABLE_GIB:-6}"
MONITOR_MIN_FREE_GIB="${MONITOR_MIN_FREE_GIB:-2}"
MONITOR_FREE_GATE_GIB="${MONITOR_FREE_GATE_GIB:-10}"
MONITOR_MIN_SWAP_FREE_GIB="${MONITOR_MIN_SWAP_FREE_GIB:-8}"
MONITOR_CONSECUTIVE="${MONITOR_CONSECUTIVE:-5}"
MONITOR_HEARTBEAT="${MONITOR_HEARTBEAT:-60}"
# PROXY_* are retained as compatibility fields for schema <=3 and uninstall/doctor consumers.
PROXY_ENABLED="${PROXY_ENABLED:-0}"; PROXY_OWNED=0; PROXY_PORT="${PROXY_PORT:-8000}"
API_ACCESS_MODE="${API_ACCESS_MODE:-}"
API_DOCKER_PORT="${API_DOCKER_PORT:-${PROXY_PORT}}"
API_LAN_ADDRESS="${API_LAN_ADDRESS:-}"
API_LAN_PORT="${API_LAN_PORT:-8001}"
API_ACCESS_CLI=""; API_DOCKER_PORT_CLI=""; API_LAN_ADDRESS_CLI=""; API_LAN_PORT_CLI=""
SERVICE_ENABLED="${SERVICE_ENABLED:-1}"; SERVICE_OWNED=0; SERVICE_CLI=""
CLI_LANG=""; UI_LANG="${UI_LANG:-}"
MONITOR_ENABLED_CLI=""; MONITOR_PROTECT_CLI=""; MONITOR_MIN_AVAILABLE_CLI=""
MONITOR_MIN_FREE_CLI=""; MONITOR_FREE_GATE_CLI=""; MONITOR_MIN_SWAP_FREE_CLI=""
MONITOR_CONSECUTIVE_CLI=""; MONITOR_HEARTBEAT_CLI=""

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
ensure_operation_lock() {
  [[ -r "${OPERATION_LOCK_LIB}" ]] || die "operation lock helper is unavailable: ${OPERATION_LOCK_LIB}"
  if ! declare -F acquire_operation_lock >/dev/null 2>&1; then
    # shellcheck source=scripts/lib/operation-lock.sh
    source "${OPERATION_LOCK_LIB}"
  fi
  acquire_operation_lock "${STATE_DIR}" "install" || exit $?
}
sudo_with_operation_lock() {
  sudo env \
    QWEN38_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}" \
    QWEN38_OPERATION_LOCK_HELD="${QWEN38_OPERATION_LOCK_HELD}" \
    QWEN38_OPERATION_LOCK_FILE="${QWEN38_OPERATION_LOCK_FILE}" \
    QWEN38_OPERATION_LOCK_OWNER_PID="${QWEN38_OPERATION_LOCK_OWNER_PID}" \
    "$@"
}
parse_install_manifest() {
  local parsed key value
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" install-maintenance "${STATE_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    printf -v "${key}" '%s' "${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
}
read_manifest_profile() {
  local parsed key value profile=""
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" install-maintenance "${STATE_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    [[ "${key}" == MODEL_PROFILE ]] && profile="${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
  printf '%s' "${profile}"
}
expand_user_path() {
  case "$1" in
    "~") printf '%s\n' "${HOME}" ;;
    "~/"*) printf '%s/%s\n' "${HOME}" "${1:2}" ;;
    *) printf '%s\n' "$1" ;;
  esac
}
detect_lan_ipv4() {
  command -v ip >/dev/null 2>&1 || return 0
  ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i=1; i<=NF; i++) if ($i=="src" && i<NF) {print $(i+1); exit}}'
}
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
sync_legacy_proxy_fields() {
  case "${API_ACCESS_MODE}" in
    local) PROXY_ENABLED=0 ;;
    docker|lan) PROXY_ENABLED=1 ;;
    *) die "API_ACCESS_MODE must be local, docker, or lan" ;;
  esac
  PROXY_PORT="${API_DOCKER_PORT}"
}
validate_api_access_settings() {
  [[ "${API_ACCESS_MODE}" == local || "${API_ACCESS_MODE}" == docker || "${API_ACCESS_MODE}" == lan ]] || \
    die "API access mode must be local, docker, or lan"
  valid_port "${API_DOCKER_PORT}" || die "API Docker port must be between 1 and 65535"
  if [[ "${API_ACCESS_MODE}" == lan ]]; then
    valid_ipv4 "${API_LAN_ADDRESS}" || die "LAN API requires a specific IPv4 address"
    [[ "${API_LAN_ADDRESS}" != 0.0.0.0 && "${API_LAN_ADDRESS}" != 127.* ]] || die "LAN API address must be non-loopback"
    valid_port "${API_LAN_PORT}" || die "LAN API port must be between 1 and 65535"
  fi
  sync_legacy_proxy_fields
}
write_state() {
  local phase="$1"
  mkdir -p "${STATE_DIR}"; umask 077
  {
    printf 'SCHEMA_VERSION=%q\n' 4; printf 'PHASE=%q\n' "${phase}"
    printf 'INSTALL_ROOT=%q\n' "${ROOT_DIR}"; printf 'MODEL_PROFILE=%q\n' "${MODEL_PROFILE}"
    printf 'MODEL_REPO=%q\n' "${REPO}"; printf 'MODEL_REVISION=%q\n' "${REVISION}"
    printf 'MODEL_DIR=%q\n' "${MODEL_DIR}"; printf 'MODEL_OWNED=%q\n' "${MODEL_OWNED}"
    printf 'SWAP_FILE=%q\n' "${SWAP_FILE}"; printf 'SWAP_OWNED=%q\n' "${SWAP_OWNED}"
    printf 'VLLM_IMAGE=%q\n' "${IMAGE}"; printf 'IMAGE_OWNED=%q\n' "${IMAGE_OWNED}"
    printf 'SERVED_NAME=%q\n' "${SERVED_NAME}"
    printf 'CONTAINER_NAME=%q\n' qwen38-flash-next; printf 'CONFIG_OVERRIDE=%q\n' "${CONFIG_OVERRIDE}"
    printf 'CONFIG_OWNED=%q\n' "${CONFIG_OWNED}"
    printf 'MONITOR_PROTECT=%q\n' "${MONITOR_PROTECT}"
    printf 'MONITOR_ENABLED=%q\n' "${MONITOR_ENABLED}"
    printf 'MONITOR_MIN_AVAILABLE_GIB=%q\n' "${MONITOR_MIN_AVAILABLE_GIB}"
    printf 'MONITOR_MIN_FREE_GIB=%q\n' "${MONITOR_MIN_FREE_GIB}"
    printf 'MONITOR_FREE_GATE_GIB=%q\n' "${MONITOR_FREE_GATE_GIB}"
    printf 'MONITOR_MIN_SWAP_FREE_GIB=%q\n' "${MONITOR_MIN_SWAP_FREE_GIB}"
    printf 'MONITOR_CONSECUTIVE=%q\n' "${MONITOR_CONSECUTIVE}"
    printf 'MONITOR_HEARTBEAT=%q\n' "${MONITOR_HEARTBEAT}"
    printf 'API_ACCESS_MODE=%q\n' "${API_ACCESS_MODE}"
    printf 'API_DOCKER_PORT=%q\n' "${API_DOCKER_PORT}"
    printf 'API_LAN_ADDRESS=%q\n' "${API_LAN_ADDRESS}"
    printf 'API_LAN_PORT=%q\n' "${API_LAN_PORT}"
    printf 'PROXY_ENABLED=%q\n' "${PROXY_ENABLED}"; printf 'PROXY_OWNED=%q\n' "${PROXY_OWNED}"
    printf 'PROXY_PORT=%q\n' "${PROXY_PORT}"
    printf 'SERVICE_ENABLED=%q\n' "${SERVICE_ENABLED}"; printf 'SERVICE_OWNED=%q\n' "${SERVICE_OWNED}"
    printf 'SERVICE_UNIT=%q\n' qwen38-flash-next.service
    printf 'UI_LANG=%q\n' "${UI_LANG}"
  } > "${STATE_FILE}.tmp"
  mv -- "${STATE_FILE}.tmp" "${STATE_FILE}"
}
usage() {
  printf 'Usage: ./install.sh [--model PROFILE] [--lang en|ko] [--yes] [--no-start] [--service|--no-service] [--monitor|--no-monitor] [--protect] [--monitor-heartbeat N] [--api-access local|docker|lan] [--api-docker-port N] [--api-lan-address IPv4] [--api-lan-port N] [--migrate-manifest] [--dry-run]\n'
  printf '       ./install.sh  # interactive English/Korean wizard (default)\n'
}
ask_yes_no() {
  local prompt="$1" answer
  [[ "${YES}" == 1 ]] && return 0
  read -r -p "${prompt} [Y/n]: " answer
  [[ -z "${answer}" || "${answer}" == y || "${answer}" == Y ]]
}
positive_integer() { [[ "$1" =~ ^[1-9][0-9]*$ ]]; }
nonnegative_integer() { [[ "$1" =~ ^[0-9]+$ ]]; }
validate_monitor_settings() {
  local value
  for value in "${MONITOR_MIN_AVAILABLE_GIB}" "${MONITOR_MIN_FREE_GIB}" "${MONITOR_FREE_GATE_GIB}" \
    "${MONITOR_MIN_SWAP_FREE_GIB}" "${MONITOR_CONSECUTIVE}"; do
    positive_integer "${value}" || die "monitor thresholds must be positive integers"
  done
  nonnegative_integer "${MONITOR_HEARTBEAT}" || die "monitor heartbeat must be a non-negative integer"
  [[ "${MONITOR_ENABLED}" == 0 || "${MONITOR_ENABLED}" == 1 ]] || die "MONITOR_ENABLED must be 0 or 1"
  [[ "${MONITOR_PROTECT}" == 0 || "${MONITOR_PROTECT}" == 1 ]] || die "MONITOR_PROTECT must be 0 or 1"
  [[ "${MONITOR_ENABLED}" == 1 || "${MONITOR_PROTECT}" == 0 ]] || die "protection requires the monitor"
}
while [[ $# -gt 0 ]]; do
  case "$1" in
    --lang) [[ $# -ge 2 ]] || die "--lang requires en or ko"; CLI_LANG="$2"; shift ;;
    --model) [[ $# -ge 2 ]] || die "--model requires orcarouter or nvidia"; MODEL_CLI="$2"; shift ;;
    --monitor) MONITOR_ENABLED_CLI=1; MONITOR_PROTECT_CLI=0 ;;
    --no-monitor) MONITOR_ENABLED_CLI=0; MONITOR_PROTECT_CLI=0 ;;
    --protect) MONITOR_ENABLED_CLI=1; MONITOR_PROTECT_CLI=1 ;;
    --monitor-min-available-gib) [[ $# -ge 2 ]] || die "$1 requires a value"; MONITOR_MIN_AVAILABLE_CLI="$2"; shift ;;
    --monitor-min-free-gib) [[ $# -ge 2 ]] || die "$1 requires a value"; MONITOR_MIN_FREE_CLI="$2"; shift ;;
    --monitor-free-gate-gib) [[ $# -ge 2 ]] || die "$1 requires a value"; MONITOR_FREE_GATE_CLI="$2"; shift ;;
    --monitor-min-swap-free-gib) [[ $# -ge 2 ]] || die "$1 requires a value"; MONITOR_MIN_SWAP_FREE_CLI="$2"; shift ;;
    --monitor-consecutive) [[ $# -ge 2 ]] || die "$1 requires a value"; MONITOR_CONSECUTIVE_CLI="$2"; shift ;;
    --monitor-heartbeat) [[ $# -ge 2 ]] || die "$1 requires a value"; MONITOR_HEARTBEAT_CLI="$2"; shift ;;
    --api-access) [[ $# -ge 2 ]] || die "$1 requires local, docker, or lan"; API_ACCESS_CLI="$2"; shift ;;
    --api-docker-port) [[ $# -ge 2 ]] || die "$1 requires a value"; API_DOCKER_PORT_CLI="$2"; shift ;;
    --api-lan-address) [[ $# -ge 2 ]] || die "$1 requires a value"; API_LAN_ADDRESS_CLI="$2"; shift ;;
    --api-lan-port) [[ $# -ge 2 ]] || die "$1 requires a value"; API_LAN_PORT_CLI="$2"; shift ;;
    --migrate-manifest) MIGRATE_MANIFEST=1 ;;
    --yes) YES=1 ;; --no-start) START=0 ;; --service) SERVICE_CLI=1 ;; --no-service) SERVICE_CLI=0 ;;
    --dry-run) DRY_RUN=1 ;; -h|--help) usage; exit 0 ;; *) die "unknown argument: $1" ;;
  esac
  shift
done

if [[ "${DRY_RUN}" != 1 ]]; then
  ensure_operation_lock
fi

RESUME=0
if [[ -r "${STATE_FILE}" ]]; then
  [[ -r "${STATE_PARSER}" ]] || die "strict state parser is unavailable: ${STATE_PARSER}"
  manifest_profile="$(read_manifest_profile)" || die "installation manifest failed strict maintenance parsing: ${STATE_FILE}"
  if [[ -n "${MODEL_CLI}" && "${MODEL_CLI}" != "${manifest_profile}" ]]; then
    [[ "${DRY_RUN}" == 1 ]] || \
      die "installed profile is ${manifest_profile}; uninstall it before selecting ${MODEL_CLI}"
  else
    parse_install_manifest || die "installation manifest failed strict maintenance parsing: ${STATE_FILE}"
    RESUME=1
  fi
fi
MONITOR_ENABLED="${MONITOR_ENABLED:-${MONITOR_PROTECT:-0}}"
[[ -z "${MONITOR_ENABLED_CLI}" ]] || MONITOR_ENABLED="${MONITOR_ENABLED_CLI}"
[[ -z "${MONITOR_PROTECT_CLI}" ]] || MONITOR_PROTECT="${MONITOR_PROTECT_CLI}"
[[ -z "${MONITOR_MIN_AVAILABLE_CLI}" ]] || MONITOR_MIN_AVAILABLE_GIB="${MONITOR_MIN_AVAILABLE_CLI}"
[[ -z "${MONITOR_MIN_FREE_CLI}" ]] || MONITOR_MIN_FREE_GIB="${MONITOR_MIN_FREE_CLI}"
[[ -z "${MONITOR_FREE_GATE_CLI}" ]] || MONITOR_FREE_GATE_GIB="${MONITOR_FREE_GATE_CLI}"
[[ -z "${MONITOR_MIN_SWAP_FREE_CLI}" ]] || MONITOR_MIN_SWAP_FREE_GIB="${MONITOR_MIN_SWAP_FREE_CLI}"
[[ -z "${MONITOR_CONSECUTIVE_CLI}" ]] || MONITOR_CONSECUTIVE="${MONITOR_CONSECUTIVE_CLI}"
[[ -z "${MONITOR_HEARTBEAT_CLI}" ]] || MONITOR_HEARTBEAT="${MONITOR_HEARTBEAT_CLI}"
validate_monitor_settings
[[ -z "${MODEL_CLI}" ]] || MODEL_PROFILE="${MODEL_CLI}"
load_model_profile "${MODEL_PROFILE}" || exit $?
REPO="${PROFILE_REPO}"; REVISION="${PROFILE_REVISION}"
MODEL_DIR="${MODEL_DIR:-${PROFILE_MODEL_DIR}}"
IMAGE="${VLLM_IMAGE:-${PROFILE_IMAGE}}"
SERVED_NAME="${SERVED_NAME:-${PROFILE_SERVED_NAME}}"
if [[ "${RESUME}" == 1 ]]; then
  [[ "${MODEL_REPO:-}" == "${REPO}" && "${MODEL_REVISION:-}" == "${REVISION}" ]] || \
    die "existing manifest belongs to a different model or revision: ${STATE_FILE}"
  IMAGE="${VLLM_IMAGE}"; SERVED_NAME="${SERVED_NAME:-${PROFILE_SERVED_NAME}}"
fi

# Schema <=3 recorded only docker0 proxy state. Preserve that meaning during migration.
if [[ -z "${API_ACCESS_MODE}" ]]; then
  [[ "${PROXY_ENABLED:-0}" == 1 ]] && API_ACCESS_MODE=docker || API_ACCESS_MODE=local
fi
API_DOCKER_PORT="${API_DOCKER_PORT:-${PROXY_PORT:-8000}}"
API_LAN_ADDRESS="${API_LAN_ADDRESS:-}"
API_LAN_PORT="${API_LAN_PORT:-8001}"
[[ -z "${API_ACCESS_CLI}" ]] || API_ACCESS_MODE="${API_ACCESS_CLI}"
[[ -z "${API_DOCKER_PORT_CLI}" ]] || API_DOCKER_PORT="${API_DOCKER_PORT_CLI}"
[[ -z "${API_LAN_ADDRESS_CLI}" ]] || API_LAN_ADDRESS="${API_LAN_ADDRESS_CLI}"
[[ -z "${API_LAN_PORT_CLI}" ]] || API_LAN_PORT="${API_LAN_PORT_CLI}"

[[ -z "${CLI_LANG}" ]] || UI_LANG="${CLI_LANG}"
if [[ -z "${UI_LANG}" ]]; then
  if [[ "${YES}" == 0 && -t 0 ]]; then
    read -r -p 'Language / 언어 [1: English, 2: 한국어] (2): ' answer
    [[ "${answer}" == 1 || "${answer}" == en ]] && UI_LANG=en || UI_LANG=ko
  elif [[ "${LANG:-}" == ko_* ]]; then UI_LANG=ko; else UI_LANG=en; fi
fi
[[ "${UI_LANG}" == en || "${UI_LANG}" == ko ]] || die "--lang must be en or ko"
if [[ "${UI_LANG}" == ko ]]; then
  printf 'Qwen3.8 Flash Next — DGX Spark 설치 마법사\n\n'
  [[ "${RESUME}" == 0 ]] || printf '설치 재개 단계: %s\n' "${PHASE:-알 수 없음}"
else
  printf 'Qwen3.8 Flash Next — DGX Spark installer wizard\n\n'
  [[ "${RESUME}" == 0 ]] || printf 'Resuming installation from phase: %s\n' "${PHASE:-unknown}"
fi
if [[ "${YES}" != 1 && "${RESUME}" != 1 && -z "${MODEL_CLI}" ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    read -r -p '모델 [1: OrcaRouter Uncensored, 2: NVIDIA 공식 NVFP4] (1): ' answer
  else
    read -r -p 'Model [1: OrcaRouter Uncensored, 2: official NVIDIA NVFP4] (1): ' answer
  fi
  [[ "${answer}" == 2 || "${answer}" == nvidia ]] && MODEL_PROFILE=nvidia || MODEL_PROFILE=orcarouter
  load_model_profile "${MODEL_PROFILE}" || exit $?
  REPO="${PROFILE_REPO}"; REVISION="${PROFILE_REVISION}"
  [[ -n "${MODEL_DIR:-}" && "${MODEL_DIR}" != "$HOME/models/qwen3.8-flash-next-orcarouter" ]] || MODEL_DIR="${PROFILE_MODEL_DIR}"
  IMAGE="${PROFILE_IMAGE}"; SERVED_NAME="${PROFILE_SERVED_NAME}"
fi
MODEL_OWNED="${MODEL_OWNED:-0}"; SWAP_OWNED="${SWAP_OWNED:-0}"; IMAGE_OWNED="${IMAGE_OWNED:-0}"
CONFIG_OWNED="${CONFIG_OWNED:-0}"
PROXY_ENABLED="${PROXY_ENABLED:-0}"; PROXY_OWNED="${PROXY_OWNED:-0}"; PROXY_PORT="${PROXY_PORT:-8000}"
SERVICE_ENABLED="${SERVICE_ENABLED:-1}"; SERVICE_OWNED="${SERVICE_OWNED:-0}"
[[ -z "${SERVICE_CLI}" ]] || SERVICE_ENABLED="${SERVICE_CLI}"
if [[ "${MIGRATE_MANIFEST}" == 1 ]]; then
  [[ "${RESUME}" == 1 ]] || die "--migrate-manifest requires an existing installation manifest"
  validate_api_access_settings
  if [[ "${DRY_RUN}" == 1 ]]; then
    printf 'DRY-RUN: installation manifest is valid and would be migrated to schema 4: %s\n' "${STATE_FILE}"
    exit 0
  fi
  write_state "${PHASE:-complete}"
  printf 'Installation manifest migrated to schema 4: %s\n' "${STATE_FILE}"
  exit 0
fi
[[ "$(uname -m)" == aarch64 ]] || printf 'WARNING: expected aarch64, found %s\n' "$(uname -m)"
if [[ "${YES}" != 1 && "${RESUME}" != 1 ]]; then
  [[ "${UI_LANG}" == ko ]] && prompt="모델 디렉터리 [${MODEL_DIR}]: " || prompt="Model directory [${MODEL_DIR}]: "
  read -r -p "${prompt}" answer; MODEL_DIR="${answer:-${MODEL_DIR}}"
  if [[ -n "${CONFIG_OVERRIDE}" ]]; then
    [[ "${UI_LANG}" == ko ]] && prompt="설정된 config.json override를 사용합니까 (${CONFIG_OVERRIDE})? [Y/n]: " || prompt="Use the configured config.json override (${CONFIG_OVERRIDE})? [Y/n]: "
    read -r -p "${prompt}" answer
    [[ "${answer}" == n || "${answer}" == N ]] && CONFIG_OVERRIDE=""
  else
    [[ "${UI_LANG}" == ko ]] && prompt="별도의 config.json override를 사용합니까? [y/N]: " || prompt="Use a separate config.json override? [y/N]: "
    read -r -p "${prompt}" answer
    if [[ "${answer}" == y || "${answer}" == Y ]]; then
      [[ "${UI_LANG}" == ko ]] && prompt='절대 경로 또는 ~/path/to/config.json: ' || prompt='Absolute path or ~/path/to/config.json: '
      read -r -p "${prompt}" CONFIG_OVERRIDE
      [[ -n "${CONFIG_OVERRIDE}" ]] || die "config override path cannot be empty"
    fi
  fi
  [[ "${UI_LANG}" == ko ]] && prompt='런타임 메모리 모니터를 활성화합니까? [Y/n]: ' || prompt='Enable the runtime memory monitor? [Y/n]: '
  read -r -p "${prompt}" answer
  [[ "${answer}" == n || "${answer}" == N ]] && MONITOR_ENABLED=0 || MONITOR_ENABLED=1
  if [[ "${MONITOR_ENABLED}" == 1 ]]; then
    [[ "${UI_LANG}" == ko ]] && prompt='지속적인 저메모리 상태에서 컨테이너를 안전하게 중지합니까? [y/N]: ' || prompt='Stop the container safely after sustained low memory? [y/N]: '
    read -r -p "${prompt}" answer
    [[ "${answer}" == y || "${answer}" == Y ]] && MONITOR_PROTECT=1 || MONITOR_PROTECT=0
    [[ "${UI_LANG}" == ko ]] && prompt='권장 모니터 임계값과 heartbeat를 변경합니까? [y/N]: ' || prompt='Customize the recommended monitor thresholds and heartbeat? [y/N]: '
    read -r -p "${prompt}" answer
    if [[ "${answer}" == y || "${answer}" == Y ]]; then
      read -r -p "MemAvailable GiB [${MONITOR_MIN_AVAILABLE_GIB}]: " answer; MONITOR_MIN_AVAILABLE_GIB="${answer:-${MONITOR_MIN_AVAILABLE_GIB}}"
      read -r -p "MemFree GiB [${MONITOR_MIN_FREE_GIB}]: " answer; MONITOR_MIN_FREE_GIB="${answer:-${MONITOR_MIN_FREE_GIB}}"
      read -r -p "MemAvailable gate GiB [${MONITOR_FREE_GATE_GIB}]: " answer; MONITOR_FREE_GATE_GIB="${answer:-${MONITOR_FREE_GATE_GIB}}"
      read -r -p "SwapFree GiB [${MONITOR_MIN_SWAP_FREE_GIB}]: " answer; MONITOR_MIN_SWAP_FREE_GIB="${answer:-${MONITOR_MIN_SWAP_FREE_GIB}}"
      read -r -p "Consecutive samples [${MONITOR_CONSECUTIVE}]: " answer; MONITOR_CONSECUTIVE="${answer:-${MONITOR_CONSECUTIVE}}"
      read -r -p "Heartbeat seconds, 0 disables [${MONITOR_HEARTBEAT}]: " answer; MONITOR_HEARTBEAT="${answer:-${MONITOR_HEARTBEAT}}"
    fi
  else
    MONITOR_PROTECT=0
  fi

  if [[ "${UI_LANG}" == ko ]]; then
    printf '\nAPI 접근 방식\n  1) 이 PC에서만 사용 (127.0.0.1:8888)\n  2) Docker 앱에서도 사용 (예: OpenWebUI, 기본 8000)\n  3) Docker 앱 + LAN의 다른 PC에서도 사용\n'
    read -r -p '선택 (2): ' answer
  else
    printf '\nAPI access\n  1) This PC only (127.0.0.1:8888)\n  2) Also available to Docker apps (for example OpenWebUI, default 8000)\n  3) Docker apps + other PCs on the LAN\n'
    read -r -p 'Select (2): ' answer
  fi
  case "${answer:-2}" in
    1|local) API_ACCESS_MODE=local ;;
    2|docker) API_ACCESS_MODE=docker ;;
    3|lan) API_ACCESS_MODE=lan ;;
    *) die "invalid API access selection" ;;
  esac
  if [[ "${API_ACCESS_MODE}" == docker || "${API_ACCESS_MODE}" == lan ]]; then
    [[ "${UI_LANG}" == ko ]] && prompt="Docker 앱 API 포트 [${API_DOCKER_PORT}]: " || prompt="Docker-app API port [${API_DOCKER_PORT}]: "
    read -r -p "${prompt}" answer; API_DOCKER_PORT="${answer:-${API_DOCKER_PORT}}"
  fi
  if [[ "${API_ACCESS_MODE}" == lan ]]; then
    detected_lan="$(detect_lan_ipv4)"
    [[ "${UI_LANG}" == ko ]] && prompt="LAN에서 사용할 DGX IPv4 주소 [${detected_lan}]: " || prompt="DGX IPv4 address to expose on the LAN [${detected_lan}]: "
    read -r -p "${prompt}" answer; API_LAN_ADDRESS="${answer:-${detected_lan}}"
    if [[ "${UI_LANG}" == ko ]]; then
      read -r -p "LAN API 포트 [${API_LAN_PORT}] (신규 권장 8001, 기존 URL 호환은 8000): " answer
    else
      read -r -p "LAN API port [${API_LAN_PORT}] (8001 recommended for new installs; use 8000 for legacy URL compatibility): " answer
    fi
    API_LAN_PORT="${answer:-${API_LAN_PORT}}"
  else
    API_LAN_ADDRESS=""
  fi

  [[ "${UI_LANG}" == ko ]] && prompt='부팅 시 자동 시작되는 systemd 서비스를 등록합니까? [Y/n]: ' || prompt='Install a systemd service that starts at boot? [Y/n]: '
  read -r -p "${prompt}" answer
  [[ "${answer}" == n || "${answer}" == N ]] && SERVICE_ENABLED=0 || SERVICE_ENABLED=1
fi
validate_monitor_settings
validate_api_access_settings
MODEL_DIR="$(expand_user_path "${MODEL_DIR}")"
[[ -z "${CONFIG_OVERRIDE}" ]] || CONFIG_OVERRIDE="$(expand_user_path "${CONFIG_OVERRIDE}")"
MODEL_DIR="$(realpath -m -- "${MODEL_DIR}")"
[[ -z "${CONFIG_OVERRIDE}" ]] || CONFIG_OVERRIDE="$(realpath -m -- "${CONFIG_OVERRIDE}")"
[[ "${UI_LANG}" == ko ]] && heading='설치 계획' || heading='Installation plan'
printf '%s\n  model       : %s\n  revision    : %s\n  directory   : %s\n' "${heading}" "${REPO}" "${REVISION}" "${MODEL_DIR}"
printf '  profile     : %s\n' "${MODEL_PROFILE}"
printf '  PLE swap    : %s (128 GiB; existing swap preserved)\n  image       : %s\n\n' "${SWAP_FILE}" "${IMAGE}"
printf '  config      : %s\n' "${CONFIG_OVERRIDE:-automatic vLLM compatibility override}"
printf '  protection  : %s\n\n' "$([[ "${MONITOR_PROTECT}" == 1 ]] && printf enabled || printf warn-only/manual)"
printf '  monitor     : %s (available=%s GiB, free=%s/%s GiB gate, swapfree=%s GiB, %s samples, heartbeat=%ss)\n\n' \
  "$([[ "${MONITOR_ENABLED}" == 1 ]] && printf enabled || printf disabled)" "${MONITOR_MIN_AVAILABLE_GIB}" \
  "${MONITOR_MIN_FREE_GIB}" "${MONITOR_FREE_GATE_GIB}" "${MONITOR_MIN_SWAP_FREE_GIB}" \
  "${MONITOR_CONSECUTIVE}" "${MONITOR_HEARTBEAT}"
case "${API_ACCESS_MODE}" in
  local) api_plan='local only: 127.0.0.1:8888' ;;
  docker) api_plan="Docker apps: ${API_DOCKER_PORT} -> 127.0.0.1:8888" ;;
  lan) api_plan="Docker apps: ${API_DOCKER_PORT}; LAN: ${API_LAN_ADDRESS}:${API_LAN_PORT} -> 127.0.0.1:8888" ;;
esac
printf '  API access  : %s\n\n' "${api_plan}"
printf '  service     : %s\n\n' "$([[ "${SERVICE_ENABLED}" == 1 ]] && printf 'systemd boot service via immutable current release' || printf 'Docker container via immutable current release')"
[[ -z "${CONFIG_OVERRIDE}" || -f "${CONFIG_OVERRIDE}" ]] || die "config override does not exist: ${CONFIG_OVERRIDE}"
[[ "${UI_LANG}" == ko ]] && continue_prompt='계속 진행합니까?' || continue_prompt='Continue?'
ask_yes_no "${continue_prompt}" || die "$([[ "${UI_LANG}" == ko ]] && printf 취소됨 || printf cancelled)"

if [[ "${DRY_RUN}" == 1 ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    printf '\nDRY-RUN 완료: 다운로드, swap, release, API 접근 설정, service, Docker 및 manifest를 변경하지 않았습니다.\n'
  else
    printf '\nDRY-RUN complete: no download, swap, release, API access, service, Docker, or manifest changes were made.\n'
  fi
  exit 0
fi

for command in python3 curl docker sudo git; do command -v "${command}" >/dev/null || die "${command} is required"; done
docker info >/dev/null 2>&1 || die "Docker daemon unavailable or user lacks permission"
git -C "${ROOT_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "installer must run from a git checkout to create an immutable release baseline"
if [[ "${PROFILE_GATED}" == 1 ]]; then
  command -v hf >/dev/null || die "hf is required for the gated OrcaRouter profile"
  hf auth whoami >/dev/null 2>&1 || die "Hugging Face login required: run 'hf auth login' after accepting the model terms"
fi

if [[ "${RESUME}" != 1 ]]; then
  [[ -e "${MODEL_DIR}" ]] || MODEL_OWNED=1
  docker image inspect "${IMAGE}" >/dev/null 2>&1 || IMAGE_OWNED=1
fi

printf '\nChecking gated access, pinned revision and disk capacity...\n'
MODEL_PROFILE="${MODEL_PROFILE}" REPO="${REPO}" REVISION="${REVISION}" DEST="${MODEL_DIR}" \
  "${ROOT_DIR}/scripts/download-weights.sh" --check
write_state prepared

if ! "${ROOT_DIR}/scripts/manage-swap.sh" status --file "${SWAP_FILE}" | grep -q 'active     : yes'; then
  printf '\nCreating dedicated PLE swap...\n'
  swap_args=(create --file "${SWAP_FILE}" --size-gib 128 --persist)
  [[ "${YES}" == 1 ]] && swap_args+=(--yes)
  sudo "${ROOT_DIR}/scripts/manage-swap.sh" "${swap_args[@]}"
  SWAP_OWNED=1
fi
write_state swap_ready

printf '\nDownloading and verifying pinned checkpoint...\n'
write_state downloading
MODEL_PROFILE="${MODEL_PROFILE}" REPO="${REPO}" REVISION="${REVISION}" DEST="${MODEL_DIR}" \
  "${ROOT_DIR}/scripts/download-weights.sh"
write_state weights_ready
if [[ -z "${CONFIG_OVERRIDE}" && "${PROFILE_CONFIG_OVERRIDE}" == 1 ]]; then
  CONFIG_OVERRIDE="${STATE_DIR}/config.vllm.json"
  printf '\nPreparing vLLM-compatible model config...\n'
  python3 "${ROOT_DIR}/scripts/prepare-config.py" --model-dir "${MODEL_DIR}" --output "${CONFIG_OVERRIDE}"
  CONFIG_OWNED=1
  write_state config_ready
fi
printf '\nInspecting checkpoint tensor headers...\n'
inspect_args=(--offline --repo "${REPO}" --model-dir "${MODEL_DIR}")
[[ -n "${CONFIG_OVERRIDE}" ]] && inspect_args+=(--config-override "${CONFIG_OVERRIDE}")
python3 "${ROOT_DIR}/scripts/inspect-model.py" "${inspect_args[@]}"
write_state inspected
printf '\nPreparing vLLM image...\n'
if [[ "${MODEL_PROFILE}" == nvidia && "${IMAGE}" == vllm-nv-mixed:v2 ]]; then
  if ! docker image inspect "${IMAGE}" >/dev/null 2>&1; then
    docker build -t vllm-skinny-tp1:v1 -f "${ROOT_DIR}/scripts/Dockerfile.skinny-gemm" "${ROOT_DIR}/scripts"
    docker build -t "${IMAGE}" -f "${ROOT_DIR}/scripts/Dockerfile.nv-mixed" "${ROOT_DIR}/scripts"
  fi
else
  docker pull "${IMAGE}"
fi
write_state image_ready

if [[ "${API_ACCESS_MODE}" != local ]]; then
  if ! "${ROOT_DIR}/scripts/manage-proxy.sh" status >/dev/null 2>&1 || [[ "${PROXY_OWNED}" == 1 ]]; then
    printf '\nConfiguring managed API access...\n'
    proxy_args=(create --docker-port "${API_DOCKER_PORT}" --backend-port 8888 --yes)
    if [[ "${API_ACCESS_MODE}" == lan ]]; then
      proxy_args+=(--lan-address "${API_LAN_ADDRESS}" --lan-port "${API_LAN_PORT}")
    fi
    sudo "${ROOT_DIR}/scripts/manage-proxy.sh" "${proxy_args[@]}"
    PROXY_OWNED=1
  fi
  write_state proxy_ready
fi

printf '\nPreparing immutable runtime release...\n'
release_status="$(bash "${ROOT_DIR}/scripts/release-manager.sh" status)"
current_release="$(awk -F= '$1=="CURRENT_RELEASE" {print $2}' <<<"${release_status}")"
if [[ -z "${current_release}" || "${current_release}" == none ]]; then
  baseline_revision="$(git -C "${ROOT_DIR}" rev-parse HEAD)"
  bash "${ROOT_DIR}/scripts/bootstrap-release.sh" "${baseline_revision}"
else
  bash "${ROOT_DIR}/scripts/release-manager.sh" verify "${current_release}"
fi
[[ -L "${CURRENT_RELEASE_LINK}" ]] || die "immutable current release pointer is missing after release preparation"
RUNTIME_ROOT="$(readlink -f -- "${CURRENT_RELEASE_LINK}")"
[[ "${RUNTIME_ROOT}" == "${DATA_HOME}/releases/"* ]] || die "immutable current release pointer is unsafe: ${CURRENT_RELEASE_LINK}"
write_state release_ready

if [[ "${SERVICE_ENABLED}" == 1 ]]; then
  SERVICE_OWNED=1
  write_state service_ready
  service_args=(create --runtime-root "${CURRENT_RELEASE_LINK}" --yes)
  [[ "${START}" == 1 ]] && service_args+=(--start) || service_args+=(--no-start)
  sudo_with_operation_lock "${ROOT_DIR}/scripts/manage-service.sh" "${service_args[@]}"
elif [[ "${START}" == 1 ]]; then
  printf '\nStarting runtime from immutable current release...\n'
  MODEL_PROFILE="${MODEL_PROFILE}" MODEL_DIR="${MODEL_DIR}" VLLM_IMAGE="${IMAGE}" SERVED_NAME="${SERVED_NAME}" \
    CONFIG_OVERRIDE="${CONFIG_OVERRIDE}" MONITOR_ENABLED="${MONITOR_ENABLED}" MONITOR_PROTECT="${MONITOR_PROTECT}" \
    MONITOR_MIN_AVAILABLE_GIB="${MONITOR_MIN_AVAILABLE_GIB}" MONITOR_MIN_FREE_GIB="${MONITOR_MIN_FREE_GIB}" \
    MONITOR_FREE_GATE_GIB="${MONITOR_FREE_GATE_GIB}" MONITOR_MIN_SWAP_FREE_GIB="${MONITOR_MIN_SWAP_FREE_GIB}" \
    MONITOR_CONSECUTIVE="${MONITOR_CONSECUTIVE}" MONITOR_HEARTBEAT="${MONITOR_HEARTBEAT}" \
    "${RUNTIME_ROOT}/scripts/serve.sh"
fi
write_state complete
if [[ "${UI_LANG}" == ko ]]; then
  printf '\n설치가 완료되었습니다.\n  manifest: %s\n  runtime: %s\n' "${STATE_FILE}" "${CURRENT_RELEASE_LINK}"
  [[ "${SERVICE_ENABLED}" == 1 ]] && printf '  logs: journalctl -fu qwen38-flash-next.service\n' || printf '  logs: docker logs -f qwen38-flash-next\n'
else
  printf '\nInstallation completed.\n  manifest: %s\n  runtime: %s\n' "${STATE_FILE}" "${CURRENT_RELEASE_LINK}"
  [[ "${SERVICE_ENABLED}" == 1 ]] && printf '  logs: journalctl -fu qwen38-flash-next.service\n' || printf '  logs: docker logs -f qwen38-flash-next\n'
fi