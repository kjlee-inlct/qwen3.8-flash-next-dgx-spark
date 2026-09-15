#!/usr/bin/env bash
# Fail before a service restart when essential files or host reserves are unsafe.
set -euo pipefail

STATE_FILE="${QWEN38_STATE_FILE:-${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark/install.env}"
[[ -r "${STATE_FILE}" && ! -L "${STATE_FILE}" ]] || { printf 'FATAL: unsafe or missing manifest: %s\n' "${STATE_FILE}" >&2; exit 1; }
# shellcheck disable=SC1090
source "${STATE_FILE}"

MIN_START_MEMORY_GIB="${MIN_START_MEMORY_GIB:-2}"
MIN_START_SWAP_FREE_GIB="${MIN_START_SWAP_FREE_GIB:-2}"
MIN_START_DISK_FREE_GIB="${MIN_START_DISK_FREE_GIB:-5}"

[[ -f "${MODEL_DIR:-}/model.safetensors.index.json" ]] || { printf 'FATAL: model index is missing\n' >&2; exit 1; }
docker image inspect "${VLLM_IMAGE:-}" >/dev/null 2>&1 || { printf 'FATAL: runtime image is missing: %s\n' "${VLLM_IMAGE:-unset}" >&2; exit 1; }
swapon --show=NAME --noheadings | awk '{$1=$1};1' | grep -Fxq "${SWAP_FILE:-}" || { printf 'FATAL: dedicated PLE swap is inactive\n' >&2; exit 1; }

mem_available_kib="$(awk '$1=="MemAvailable:" {print $2}' /proc/meminfo)"
swap_free_kib="$(awk '$1=="SwapFree:" {print $2}' /proc/meminfo)"
disk_available_kib="$(df -Pk "${MODEL_DIR}" | awk 'NR==2 {print $4}')"

(( mem_available_kib >= MIN_START_MEMORY_GIB * 1048576 )) || { printf 'FATAL: less than %s GiB memory is available\n' "${MIN_START_MEMORY_GIB}" >&2; exit 1; }
(( swap_free_kib >= MIN_START_SWAP_FREE_GIB * 1048576 )) || { printf 'FATAL: less than %s GiB swap is free\n' "${MIN_START_SWAP_FREE_GIB}" >&2; exit 1; }
(( disk_available_kib >= MIN_START_DISK_FREE_GIB * 1048576 )) || { printf 'FATAL: less than %s GiB disk is free\n' "${MIN_START_DISK_FREE_GIB}" >&2; exit 1; }

printf 'Runtime preflight passed: memory=%s MiB swapfree=%s MiB diskfree=%s MiB\n' \
  "$((mem_available_kib / 1024))" "$((swap_free_kib / 1024))" "$((disk_available_kib / 1024))"
