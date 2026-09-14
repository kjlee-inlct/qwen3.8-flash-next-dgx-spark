#!/usr/bin/env bash
# Interactive installer for OrcaRouter Qwen3.8-Flash-Next on one DGX Spark.
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/install.env"
MODEL_DIR="${MODEL_DIR:-$HOME/models/qwen3.8-flash-next-orcarouter}"
SWAP_FILE="${SWAP_FILE:-/swap-ple.img}"
IMAGE="${VLLM_IMAGE:-vllm/vllm-openai:qwen38-flash-next-arm64-cu130}"
CONFIG_OVERRIDE="${CONFIG_OVERRIDE:-}"
REPO="orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4"
REVISION="c1209bda15a6bbc4c68b585e93d40c0d85f50306"
YES=0; START=1

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
expand_user_path() {
  case "$1" in
    "~") printf '%s\n' "${HOME}" ;;
    "~/"*) printf '%s/%s\n' "${HOME}" "${1:2}" ;;
    *) printf '%s\n' "$1" ;;
  esac
}
usage() { printf 'Usage: ./install.sh [--yes] [--no-start]\n'; }
ask_yes_no() {
  local prompt="$1" answer
  [[ "${YES}" == 1 ]] && return 0
  read -r -p "${prompt} [Y/n]: " answer
  [[ -z "${answer}" || "${answer}" == y || "${answer}" == Y ]]
}
while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes) YES=1 ;; --no-start) START=0 ;; -h|--help) usage; exit 0 ;; *) die "unknown argument: $1" ;;
  esac
  shift
done

printf 'Qwen3.8 Flash Next — DGX Spark installer\n\n'
[[ ! -e "${STATE_FILE}" ]] || die "installation manifest already exists; run ./uninstall.sh or inspect ${STATE_FILE}"
[[ "$(uname -m)" == aarch64 ]] || printf 'WARNING: expected aarch64, found %s\n' "$(uname -m)"
for command in python3 curl docker sudo hf; do command -v "${command}" >/dev/null || die "${command} is required"; done
docker info >/dev/null 2>&1 || die "Docker daemon unavailable or user lacks permission"
hf auth whoami >/dev/null 2>&1 || die "Hugging Face login required: run 'hf auth login' after accepting the model terms"
if [[ "${YES}" != 1 ]]; then
  read -r -p "Model directory [${MODEL_DIR}]: " answer; MODEL_DIR="${answer:-${MODEL_DIR}}"
  if [[ -n "${CONFIG_OVERRIDE}" ]]; then
    read -r -p "Use the configured config.json override (${CONFIG_OVERRIDE})? [Y/n]: " answer
    [[ "${answer}" == n || "${answer}" == N ]] && CONFIG_OVERRIDE=""
  else
    read -r -p "Use a separate config.json override? [y/N]: " answer
    if [[ "${answer}" == y || "${answer}" == Y ]]; then
      read -r -p "Absolute path or ~/path/to/config.json: " CONFIG_OVERRIDE
      [[ -n "${CONFIG_OVERRIDE}" ]] || die "config override path cannot be empty"
    fi
  fi
fi
MODEL_DIR="$(expand_user_path "${MODEL_DIR}")"
[[ -z "${CONFIG_OVERRIDE}" ]] || CONFIG_OVERRIDE="$(expand_user_path "${CONFIG_OVERRIDE}")"
MODEL_DIR="$(realpath -m -- "${MODEL_DIR}")"
[[ -z "${CONFIG_OVERRIDE}" ]] || CONFIG_OVERRIDE="$(realpath -m -- "${CONFIG_OVERRIDE}")"
printf 'Installation plan\n  model       : %s\n  revision    : %s\n  directory   : %s\n' "${REPO}" "${REVISION}" "${MODEL_DIR}"
printf '  PLE swap    : %s (128 GiB; existing swap preserved)\n  image       : %s\n\n' "${SWAP_FILE}" "${IMAGE}"
[[ -z "${CONFIG_OVERRIDE}" || -f "${CONFIG_OVERRIDE}" ]] || die "config override does not exist: ${CONFIG_OVERRIDE}"
ask_yes_no "Continue?" || die "cancelled"

printf '\nChecking gated access, pinned revision and disk capacity...\n'
MODEL_PROFILE=orcarouter REPO="${REPO}" REVISION="${REVISION}" DEST="${MODEL_DIR}" \
  "${ROOT_DIR}/scripts/download-weights.sh" --check

if ! "${ROOT_DIR}/scripts/manage-swap.sh" status --file "${SWAP_FILE}" | grep -q 'active     : yes'; then
  printf '\nCreating dedicated PLE swap...\n'
  swap_args=(create --file "${SWAP_FILE}" --size-gib 128 --persist)
  [[ "${YES}" == 1 ]] && swap_args+=(--yes)
  sudo "${ROOT_DIR}/scripts/manage-swap.sh" "${swap_args[@]}"
fi

printf '\nDownloading and verifying pinned checkpoint...\n'
MODEL_PROFILE=orcarouter REPO="${REPO}" REVISION="${REVISION}" DEST="${MODEL_DIR}" \
  "${ROOT_DIR}/scripts/download-weights.sh"
printf '\nInspecting checkpoint tensor headers...\n'
inspect_args=(--offline --model-dir "${MODEL_DIR}")
[[ -n "${CONFIG_OVERRIDE}" ]] && inspect_args+=(--config-override "${CONFIG_OVERRIDE}")
python3 "${ROOT_DIR}/scripts/inspect-model.py" "${inspect_args[@]}"
printf '\nPreparing vLLM image...\n'
docker pull "${IMAGE}"

mkdir -p "${STATE_DIR}"; umask 077
{
  printf 'INSTALL_ROOT=%q\n' "${ROOT_DIR}"; printf 'MODEL_PROFILE=%q\n' orcarouter
  printf 'MODEL_REPO=%q\n' "${REPO}"; printf 'MODEL_REVISION=%q\n' "${REVISION}"
  printf 'MODEL_DIR=%q\n' "${MODEL_DIR}"; printf 'SWAP_FILE=%q\n' "${SWAP_FILE}"
  printf 'VLLM_IMAGE=%q\n' "${IMAGE}"; printf 'CONTAINER_NAME=%q\n' qwen38-flash-next
  printf 'CONFIG_OVERRIDE=%q\n' "${CONFIG_OVERRIDE}"
} > "${STATE_FILE}"

if [[ "${START}" == 1 ]]; then
  printf '\nStarting service...\n'
  MODEL_PROFILE=orcarouter MODEL_DIR="${MODEL_DIR}" VLLM_IMAGE="${IMAGE}" \
    CONFIG_OVERRIDE="${CONFIG_OVERRIDE}" "${ROOT_DIR}/scripts/serve.sh"
fi
printf '\nInstallation completed.\n  manifest: %s\n  logs: docker logs -f qwen38-flash-next\n' "${STATE_FILE}"
