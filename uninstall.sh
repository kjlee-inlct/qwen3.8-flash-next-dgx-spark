#!/usr/bin/env bash
# Remove only resources recorded by install.sh.
set -euo pipefail

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/install.env"
PURGE_MODEL=0; PURGE_SWAP=0; PURGE_IMAGE=0; PURGE_SELECTED=0; YES=0; DRY_RUN=0
CLI_LANG=""
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
usage() {
  printf 'Usage: ./uninstall.sh [--lang en|ko] [--purge-model] [--purge-swap] [--purge-image] [--purge-all] [--yes] [--dry-run]\n'
  printf '       ./uninstall.sh  # interactive English/Korean wizard (default)\n'
}
while [[ $# -gt 0 ]]; do
  case "$1" in
    --lang) [[ $# -ge 2 ]] || die "--lang requires en or ko"; CLI_LANG="$2"; shift ;;
    --purge-model) PURGE_MODEL=1; PURGE_SELECTED=1 ;; --purge-swap) PURGE_SWAP=1; PURGE_SELECTED=1 ;; --purge-image) PURGE_IMAGE=1; PURGE_SELECTED=1 ;;
    --purge-all) PURGE_MODEL=1; PURGE_SWAP=1; PURGE_IMAGE=1; PURGE_SELECTED=1 ;; --yes) YES=1 ;; --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;; *) die "unknown argument: $1" ;;
  esac
  shift
done
[[ -r "${STATE_FILE}" ]] || die "installation manifest not found: ${STATE_FILE}"
# Created by install.sh with shell-escaped values and mode 600.
# shellcheck disable=SC1090
source "${STATE_FILE}"
[[ -z "${CLI_LANG}" ]] || UI_LANG="${CLI_LANG}"
if [[ -z "${UI_LANG:-}" ]]; then
  if [[ "${YES}" == 0 && -t 0 ]]; then
    read -r -p 'Language / 언어 [1: English, 2: 한국어] (2): ' answer
    [[ "${answer}" == 1 || "${answer}" == en ]] && UI_LANG=en || UI_LANG=ko
  elif [[ "${LANG:-}" == ko_* ]]; then UI_LANG=ko; else UI_LANG=en; fi
fi
[[ "${UI_LANG}" == en || "${UI_LANG}" == ko ]] || die "--lang must be en or ko"
[[ -n "${INSTALL_ROOT:-}" && -d "${INSTALL_ROOT}" ]] || die "invalid INSTALL_ROOT in manifest"
[[ -n "${CONTAINER_NAME:-}" && "${CONTAINER_NAME}" != */* ]] || die "invalid container name"
MODEL_OWNED="${MODEL_OWNED:-0}"; SWAP_OWNED="${SWAP_OWNED:-0}"; IMAGE_OWNED="${IMAGE_OWNED:-0}"
CONFIG_OWNED="${CONFIG_OWNED:-0}"
PROXY_OWNED="${PROXY_OWNED:-0}"
SERVICE_OWNED="${SERVICE_OWNED:-0}"
MONITOR_PID_FILE="${STATE_DIR}/monitor.pid"

if [[ "${YES}" == 0 && "${PURGE_SELECTED}" == 0 ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    read -r -p '다운로드한 모델도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_MODEL=1
    read -r -p '전용 PLE swap도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_SWAP=1
    read -r -p 'vLLM Docker image도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_IMAGE=1
  else
    read -r -p 'Remove the downloaded model too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_MODEL=1
    read -r -p 'Remove the dedicated PLE swap too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_SWAP=1
    read -r -p 'Remove the vLLM Docker image too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_IMAGE=1
  fi
fi

if [[ "${UI_LANG}" == ko ]]; then
  printf 'Qwen3.8 Flash Next 제거 마법사\n\n  container: %s (제거)\n' "${CONTAINER_NAME}"
  printf '  model    : %s (%s)\n' "${MODEL_DIR}" "$([[ "${PURGE_MODEL}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  PLE swap : %s (%s)\n' "${SWAP_FILE}" "$([[ "${PURGE_SWAP}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  image    : %s (%s)\n' "${VLLM_IMAGE}" "$([[ "${PURGE_IMAGE}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  service  : %s\n' "$([[ "${SERVICE_OWNED}" == 1 ]] && printf 제거 || printf 유지)"
else
  printf 'Qwen3.8 Flash Next uninstaller wizard\n\n  container: %s (remove)\n' "${CONTAINER_NAME}"
  printf '  model    : %s (%s)\n' "${MODEL_DIR}" "$([[ "${PURGE_MODEL}" == 1 ]] && printf remove || printf keep)"
  printf '  PLE swap : %s (%s)\n' "${SWAP_FILE}" "$([[ "${PURGE_SWAP}" == 1 ]] && printf remove || printf keep)"
  printf '  image    : %s (%s)\n' "${VLLM_IMAGE}" "$([[ "${PURGE_IMAGE}" == 1 ]] && printf remove || printf keep)"
  printf '  service  : %s\n' "$([[ "${SERVICE_OWNED}" == 1 ]] && printf remove || printf keep)"
fi
if [[ "${DRY_RUN}" == 1 ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    printf '\nDRY-RUN 완료: container, monitor, proxy, 모델, swap, image 및 manifest를 변경하지 않았습니다.\n'
  else
    printf '\nDRY-RUN complete: no container, monitor, proxy, model, swap, image, or manifest changes were made.\n'
  fi
  exit 0
fi
if [[ "${SERVICE_OWNED}" != 1 ]] && "${INSTALL_ROOT}/scripts/manage-service.sh" status >/dev/null 2>&1; then
  die "a managed runtime service exists but is not owned by this manifest; rerun install.sh to adopt it or remove it explicitly"
fi
if [[ "${YES}" != 1 ]]; then
  [[ "${UI_LANG}" == ko ]] && prompt='계속하려면 DELETE를 입력하십시오: ' || prompt='Type DELETE to continue: '
  read -r -p "${prompt}" answer
  [[ "${answer}" == DELETE ]] || die "$([[ "${UI_LANG}" == ko ]] && printf 취소됨 || printf cancelled)"
fi
if [[ -r "${MONITOR_PID_FILE}" ]]; then
  monitor_pid="$(<"${MONITOR_PID_FILE}")"
  if [[ "${monitor_pid}" =~ ^[0-9]+$ && -r "/proc/${monitor_pid}/cmdline" ]] && \
     tr '\0' ' ' < "/proc/${monitor_pid}/cmdline" | grep -Fq 'monitor-runtime.sh'; then
    kill "${monitor_pid}" 2>/dev/null || true
  fi
  rm -f -- "${MONITOR_PID_FILE}"
fi
if [[ "${SERVICE_OWNED}" == 1 ]]; then
  sudo "${INSTALL_ROOT}/scripts/manage-service.sh" remove --yes
fi
if [[ "${PROXY_OWNED}" == 1 ]]; then
  sudo "${INSTALL_ROOT}/scripts/manage-proxy.sh" remove --yes
fi
docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true

if [[ "${PURGE_MODEL}" == 1 ]]; then
  [[ "${MODEL_OWNED}" == 1 ]] || die "refusing model deletion: directory was not created by this installer"
  if [[ -e "${MODEL_DIR}" ]]; then
    [[ -f "${MODEL_DIR}/.qwen38-model-manifest.json" ]] || die "refusing model deletion: model manifest missing"
    if [[ "${MODEL_DIR}" != "${HOME}/models/"* && "${MODEL_DIR}" != "${INSTALL_ROOT}/model" ]]; then
      die "refusing model deletion outside ${HOME}/models or the install root's model directory"
    fi
    rm -rf --one-file-system -- "${MODEL_DIR}"
    printf 'Removed model directory: %s\n' "${MODEL_DIR}"
  fi
fi
if [[ "${PURGE_SWAP}" == 1 ]]; then
  [[ "${SWAP_OWNED}" == 1 ]] || die "refusing swap deletion: swap was not created by this installer"
  if [[ -e "${SWAP_FILE}" ]]; then
    swap_args=(remove --file "${SWAP_FILE}"); [[ "${YES}" == 1 ]] && swap_args+=(--yes)
    sudo "${INSTALL_ROOT}/scripts/manage-swap.sh" "${swap_args[@]}"
  fi
fi
if [[ "${PURGE_IMAGE}" == 1 ]]; then
  [[ "${IMAGE_OWNED}" == 1 ]] || die "refusing image deletion: image existed before this installation"
  if docker image inspect "${VLLM_IMAGE}" >/dev/null 2>&1; then
    docker image rm "${VLLM_IMAGE}" || die "image is still in use"
  fi
fi
if [[ "${PURGE_MODEL}" == 1 && "${PURGE_SWAP}" == 1 && "${PURGE_IMAGE}" == 1 ]]; then
  if [[ "${CONFIG_OWNED}" == 1 && "${CONFIG_OVERRIDE:-}" == "${STATE_DIR}/config.vllm.json" ]]; then
    rm -f -- "${CONFIG_OVERRIDE}"
  fi
  rm -f -- "${STATE_DIR}/monitor.log"
  rm -f -- "${STATE_FILE}"; rmdir --ignore-fail-on-non-empty "${STATE_DIR}" 2>/dev/null || true
  [[ "${UI_LANG}" == ko ]] && printf '전체 제거 완료; 설치 manifest를 삭제했습니다.\n' || printf 'Full uninstall completed; installation manifest removed.\n'
else
  if [[ "${UI_LANG}" == ko ]]; then
    printf '제거 완료. 유지한 리소스를 나중에 정리할 수 있도록 manifest를 보존했습니다: %s\n' "${STATE_FILE}"
  else
    printf 'Uninstall completed. Manifest retained so preserved resources can be purged later: %s\n' "${STATE_FILE}"
  fi
fi
