#!/usr/bin/env bash
# Remove only resources recorded by install.sh.
set -euo pipefail

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/install.env"
PURGE_MODEL=0; PURGE_SWAP=0; PURGE_IMAGE=0; YES=0
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
usage() {
  printf 'Usage: ./uninstall.sh [--purge-model] [--purge-swap] [--purge-image] [--purge-all] [--yes]\n'
}
while [[ $# -gt 0 ]]; do
  case "$1" in
    --purge-model) PURGE_MODEL=1 ;; --purge-swap) PURGE_SWAP=1 ;; --purge-image) PURGE_IMAGE=1 ;;
    --purge-all) PURGE_MODEL=1; PURGE_SWAP=1; PURGE_IMAGE=1 ;; --yes) YES=1 ;;
    -h|--help) usage; exit 0 ;; *) die "unknown argument: $1" ;;
  esac
  shift
done
[[ -r "${STATE_FILE}" ]] || die "installation manifest not found: ${STATE_FILE}"
# shellcheck disable=SC1090 -- created by install.sh with shell-escaped values and mode 600.
source "${STATE_FILE}"
[[ -n "${INSTALL_ROOT:-}" && -d "${INSTALL_ROOT}" ]] || die "invalid INSTALL_ROOT in manifest"
[[ -n "${CONTAINER_NAME:-}" && "${CONTAINER_NAME}" != */* ]] || die "invalid container name"
MODEL_OWNED="${MODEL_OWNED:-0}"; SWAP_OWNED="${SWAP_OWNED:-0}"; IMAGE_OWNED="${IMAGE_OWNED:-0}"
CONFIG_OWNED="${CONFIG_OWNED:-0}"
PROXY_OWNED="${PROXY_OWNED:-0}"
MONITOR_PID_FILE="${STATE_DIR}/monitor.pid"

printf 'Qwen3.8 Flash Next uninstaller\n\n  container: %s (remove)\n' "${CONTAINER_NAME}"
printf '  model    : %s (%s)\n' "${MODEL_DIR}" "$([[ "${PURGE_MODEL}" == 1 ]] && printf remove || printf keep)"
printf '  PLE swap : %s (%s)\n' "${SWAP_FILE}" "$([[ "${PURGE_SWAP}" == 1 ]] && printf remove || printf keep)"
printf '  image    : %s (%s)\n' "${VLLM_IMAGE}" "$([[ "${PURGE_IMAGE}" == 1 ]] && printf remove || printf keep)"
if [[ "${YES}" != 1 ]]; then
  read -r -p 'Type DELETE to continue: ' answer; [[ "${answer}" == DELETE ]] || die "cancelled"
fi
if [[ -r "${MONITOR_PID_FILE}" ]]; then
  monitor_pid="$(<"${MONITOR_PID_FILE}")"
  if [[ "${monitor_pid}" =~ ^[0-9]+$ && -r "/proc/${monitor_pid}/cmdline" ]] && \
     tr '\0' ' ' < "/proc/${monitor_pid}/cmdline" | grep -Fq 'monitor-runtime.sh'; then
    kill "${monitor_pid}" 2>/dev/null || true
  fi
  rm -f -- "${MONITOR_PID_FILE}"
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
  printf 'Full uninstall completed; installation manifest removed.\n'
else
  printf 'Uninstall completed. Manifest retained so preserved resources can be purged later: %s\n' "${STATE_FILE}"
fi
