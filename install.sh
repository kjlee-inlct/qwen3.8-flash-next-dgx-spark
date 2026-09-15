#!/usr/bin/env bash
# Interactive installer for OrcaRouter Qwen3.8-Flash-Next on one DGX Spark.
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/model-profiles.sh
source "${ROOT_DIR}/scripts/model-profiles.sh"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/install.env"
SWAP_FILE="${SWAP_FILE:-/swap-ple.img}"
CONFIG_OVERRIDE="${CONFIG_OVERRIDE:-}"
MODEL_PROFILE="${MODEL_PROFILE:-orcarouter}"
MODEL_CLI=""
YES=0; START=1; DRY_RUN=0; MONITOR_PROTECT="${MONITOR_PROTECT:-0}"; CONFIG_OWNED=0
PROXY_ENABLED="${PROXY_ENABLED:-0}"; PROXY_OWNED=0; PROXY_PORT="${PROXY_PORT:-8000}"
SERVICE_ENABLED="${SERVICE_ENABLED:-1}"; SERVICE_OWNED=0; SERVICE_CLI=""
CLI_LANG=""; UI_LANG="${UI_LANG:-}"

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
expand_user_path() {
  case "$1" in
    "~") printf '%s\n' "${HOME}" ;;
    "~/"*) printf '%s/%s\n' "${HOME}" "${1:2}" ;;
    *) printf '%s\n' "$1" ;;
  esac
}
write_state() {
  local phase="$1"
  mkdir -p "${STATE_DIR}"; umask 077
  {
    printf 'SCHEMA_VERSION=%q\n' 2; printf 'PHASE=%q\n' "${phase}"
    printf 'INSTALL_ROOT=%q\n' "${ROOT_DIR}"; printf 'MODEL_PROFILE=%q\n' "${MODEL_PROFILE}"
    printf 'MODEL_REPO=%q\n' "${REPO}"; printf 'MODEL_REVISION=%q\n' "${REVISION}"
    printf 'MODEL_DIR=%q\n' "${MODEL_DIR}"; printf 'MODEL_OWNED=%q\n' "${MODEL_OWNED}"
    printf 'SWAP_FILE=%q\n' "${SWAP_FILE}"; printf 'SWAP_OWNED=%q\n' "${SWAP_OWNED}"
    printf 'VLLM_IMAGE=%q\n' "${IMAGE}"; printf 'IMAGE_OWNED=%q\n' "${IMAGE_OWNED}"
    printf 'SERVED_NAME=%q\n' "${SERVED_NAME}"
    printf 'CONTAINER_NAME=%q\n' qwen38-flash-next; printf 'CONFIG_OVERRIDE=%q\n' "${CONFIG_OVERRIDE}"
    printf 'CONFIG_OWNED=%q\n' "${CONFIG_OWNED}"
    printf 'MONITOR_PROTECT=%q\n' "${MONITOR_PROTECT}"
    printf 'PROXY_ENABLED=%q\n' "${PROXY_ENABLED}"; printf 'PROXY_OWNED=%q\n' "${PROXY_OWNED}"
    printf 'PROXY_PORT=%q\n' "${PROXY_PORT}"
    printf 'SERVICE_ENABLED=%q\n' "${SERVICE_ENABLED}"; printf 'SERVICE_OWNED=%q\n' "${SERVICE_OWNED}"
    printf 'SERVICE_UNIT=%q\n' qwen38-flash-next.service
    printf 'UI_LANG=%q\n' "${UI_LANG}"
  } > "${STATE_FILE}.tmp"
  mv -- "${STATE_FILE}.tmp" "${STATE_FILE}"
}
usage() {
  printf 'Usage: ./install.sh [--model orcarouter|nvidia] [--lang en|ko] [--yes] [--no-start] [--service|--no-service] [--dry-run]\n'
  printf '       ./install.sh  # interactive English/Korean wizard (default)\n'
}
ask_yes_no() {
  local prompt="$1" answer
  [[ "${YES}" == 1 ]] && return 0
  read -r -p "${prompt} [Y/n]: " answer
  [[ -z "${answer}" || "${answer}" == y || "${answer}" == Y ]]
}
while [[ $# -gt 0 ]]; do
  case "$1" in
    --lang) [[ $# -ge 2 ]] || die "--lang requires en or ko"; CLI_LANG="$2"; shift ;;
    --model) [[ $# -ge 2 ]] || die "--model requires orcarouter or nvidia"; MODEL_CLI="$2"; shift ;;
    --yes) YES=1 ;; --no-start) START=0 ;; --service) SERVICE_CLI=1 ;; --no-service) SERVICE_CLI=0 ;;
    --dry-run) DRY_RUN=1 ;; -h|--help) usage; exit 0 ;; *) die "unknown argument: $1" ;;
  esac
  shift
done

RESUME=0
if [[ -r "${STATE_FILE}" ]]; then
  manifest_profile="$({
    # Created by write_state with shell-escaped values and mode 600.
    # shellcheck disable=SC1090
    source "${STATE_FILE}"
    printf '%s' "${MODEL_PROFILE:-}"
  })"
  if [[ -n "${MODEL_CLI}" && "${MODEL_CLI}" != "${manifest_profile}" ]]; then
    [[ "${DRY_RUN}" == 1 ]] || \
      die "installed profile is ${manifest_profile}; uninstall it before selecting ${MODEL_CLI}"
  else
    # shellcheck disable=SC1090
    source "${STATE_FILE}"
    RESUME=1
  fi
fi
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
  [[ "${UI_LANG}" == ko ]] && prompt='자동 저메모리 보호 기능을 활성화합니까? [y/N]: ' || prompt='Enable automatic low-memory protection? [y/N]: '
  read -r -p "${prompt}" answer
  [[ "${answer}" == y || "${answer}" == Y ]] && MONITOR_PROTECT=1 || MONITOR_PROTECT=0
  [[ "${UI_LANG}" == ko ]] && prompt="docker0 전용 OpenWebUI proxy를 ${PROXY_PORT} 포트에 설치합니까? [y/N]: " || prompt="Install docker0-only OpenWebUI proxy on port ${PROXY_PORT}? [y/N]: "
  read -r -p "${prompt}" answer
  [[ "${answer}" == y || "${answer}" == Y ]] && PROXY_ENABLED=1 || PROXY_ENABLED=0
  [[ "${UI_LANG}" == ko ]] && prompt='부팅 시 자동 시작되는 systemd 서비스를 등록합니까? [Y/n]: ' || prompt='Install a systemd service that starts at boot? [Y/n]: '
  read -r -p "${prompt}" answer
  [[ "${answer}" == n || "${answer}" == N ]] && SERVICE_ENABLED=0 || SERVICE_ENABLED=1
fi
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
printf '  proxy       : %s\n\n' "$([[ "${PROXY_ENABLED}" == 1 ]] && printf 'docker0:%s -> loopback:8888' "${PROXY_PORT}" || printf disabled)"
printf '  service     : %s\n\n' "$([[ "${SERVICE_ENABLED}" == 1 ]] && printf 'systemd boot service' || printf 'Docker container only')"
[[ -z "${CONFIG_OVERRIDE}" || -f "${CONFIG_OVERRIDE}" ]] || die "config override does not exist: ${CONFIG_OVERRIDE}"
[[ "${UI_LANG}" == ko ]] && continue_prompt='계속 진행합니까?' || continue_prompt='Continue?'
ask_yes_no "${continue_prompt}" || die "$([[ "${UI_LANG}" == ko ]] && printf 취소됨 || printf cancelled)"

if [[ "${DRY_RUN}" == 1 ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    printf '\nDRY-RUN 완료: 다운로드, swap, proxy, service, Docker 및 manifest를 변경하지 않았습니다.\n'
  else
    printf '\nDRY-RUN complete: no download, swap, proxy, service, Docker, or manifest changes were made.\n'
  fi
  exit 0
fi

for command in python3 curl docker sudo; do command -v "${command}" >/dev/null || die "${command} is required"; done
docker info >/dev/null 2>&1 || die "Docker daemon unavailable or user lacks permission"
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

if [[ "${PROXY_ENABLED}" == 1 ]]; then
  if ! "${ROOT_DIR}/scripts/manage-proxy.sh" status >/dev/null 2>&1; then
    printf '\nInstalling docker0-only OpenWebUI proxy...\n'
    sudo "${ROOT_DIR}/scripts/manage-proxy.sh" create --listen-port "${PROXY_PORT}" --backend-port 8888 --yes
    PROXY_OWNED=1
  fi
  write_state proxy_ready
fi

if [[ "${SERVICE_ENABLED}" == 1 ]]; then
  SERVICE_OWNED=1
  write_state service_ready
  service_args=(create --yes)
  [[ "${START}" == 1 ]] && service_args+=(--start) || service_args+=(--no-start)
  sudo env QWEN38_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}" \
    "${ROOT_DIR}/scripts/manage-service.sh" "${service_args[@]}"
elif [[ "${START}" == 1 ]]; then
  printf '\nStarting service...\n'
  MODEL_PROFILE="${MODEL_PROFILE}" MODEL_DIR="${MODEL_DIR}" VLLM_IMAGE="${IMAGE}" SERVED_NAME="${SERVED_NAME}" \
    CONFIG_OVERRIDE="${CONFIG_OVERRIDE}" MONITOR_PROTECT="${MONITOR_PROTECT}" \
    "${ROOT_DIR}/scripts/serve.sh"
fi
write_state complete
if [[ "${UI_LANG}" == ko ]]; then
  printf '\n설치가 완료되었습니다.\n  manifest: %s\n' "${STATE_FILE}"
  [[ "${SERVICE_ENABLED}" == 1 ]] && printf '  logs: journalctl -fu qwen38-flash-next.service\n' || printf '  logs: docker logs -f qwen38-flash-next\n'
else
  printf '\nInstallation completed.\n  manifest: %s\n' "${STATE_FILE}"
  [[ "${SERVICE_ENABLED}" == 1 ]] && printf '  logs: journalctl -fu qwen38-flash-next.service\n' || printf '  logs: docker logs -f qwen38-flash-next\n'
fi
