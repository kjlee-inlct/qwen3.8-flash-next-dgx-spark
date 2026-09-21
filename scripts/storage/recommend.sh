#!/usr/bin/env bash
# Read-only ranked storage recovery recommendations.
set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/install.env"
STATE_PARSER="${SCRIPT_ROOT}/scripts/lib/state_file.py"
HF_CACHE="${HF_HOME:-$HOME/.cache/huggingface}"

ACTIVE_MODEL=""
ACTIVE_IMAGE=""
ACTIVE_PROFILE=""
if [[ -r "${STATE_FILE}" && -r "${STATE_PARSER}" ]]; then
  parsed="$(mktemp)"
  trap 'rm -f -- "${parsed:-}"' EXIT
  if python3 "${STATE_PARSER}" install-maintenance "${STATE_FILE}" >"${parsed}" 2>/dev/null; then
    while IFS= read -r -d '' key && IFS= read -r -d '' value; do
      case "${key}" in
        MODEL_DIR) ACTIVE_MODEL="${value}" ;;
        VLLM_IMAGE) ACTIVE_IMAGE="${value}" ;;
        MODEL_PROFILE) ACTIVE_PROFILE="${value}" ;;
      esac
    done <"${parsed}"
  fi
  rm -f -- "${parsed}"
  trap - EXIT
fi

human_du() {
  local path="$1"
  if [[ -e "${path}" || -L "${path}" ]]; then
    du -sh -- "${path}" 2>/dev/null | awk '{print $1}'
  else
    printf '%s' '-'
  fi
}

bytes_du() {
  local path="$1"
  if [[ -e "${path}" || -L "${path}" ]]; then
    du -sb -- "${path}" 2>/dev/null | awk '{print $1}'
  else
    printf '0'
  fi
}

human_bytes() {
  local bytes="$1"
  if [[ "${bytes}" =~ ^[0-9]+$ ]]; then
    numfmt --to=iec-i --suffix=B "${bytes}" 2>/dev/null || printf '%sB' "${bytes}"
  else
    printf '%s' '?'
  fi
}

managed_model_candidates() {
  declare -A seen=()
  local -a roots=("${HOME}/models" "${SCRIPT_ROOT}/model")
  local root path canonical manifest
  [[ -n "${ACTIVE_MODEL}" ]] && roots+=("${ACTIVE_MODEL}")
  for root in "${roots[@]}"; do
    [[ -e "${root}" ]] || continue
    if [[ -f "${root}/.qwen38-model-manifest.json" ]]; then
      canonical="$(realpath -m -- "${root}")"
      if [[ -z "${seen[${canonical}]:-}" ]]; then
        seen["${canonical}"]=1
        printf '%s\n' "${canonical}"
      fi
      continue
    fi
    [[ -d "${root}" ]] || continue
    while IFS= read -r manifest; do
      [[ -n "${manifest}" ]] || continue
      path="$(dirname -- "${manifest}")"
      canonical="$(realpath -m -- "${path}")"
      [[ -n "${seen[${canonical}]:-}" ]] && continue
      seen["${canonical}"]=1
      printf '%s\n' "${canonical}"
    done < <(find "${root}" -mindepth 1 -maxdepth 2 -type f -name .qwen38-model-manifest.json -print 2>/dev/null | sort)
  done
}

inactive_managed_models() {
  local path canonical_active=""
  [[ -z "${ACTIVE_MODEL}" ]] || canonical_active="$(realpath -m -- "${ACTIVE_MODEL}")"
  while IFS= read -r path; do
    [[ -n "${path}" ]] || continue
    [[ "$(realpath -m -- "${path}")" == "${canonical_active}" ]] && continue
    printf '%s\n' "${path}"
  done < <(managed_model_candidates)
}

hf_cache_top() {
  [[ -d "${HF_CACHE}" ]] || return 0
  find "${HF_CACHE}" -mindepth 1 -maxdepth 1 -type d -print0 2>/dev/null |
    while IFS= read -r -d '' path; do
      printf '%s\t%s\n' "$(bytes_du "${path}")" "${path}"
    done | sort -nr | head -n 12
}

printf 'Qwen3.8 storage recovery recommendations\n\n'

printf '[1. Inactive managed checkpoints]\n'
found=0
while IFS= read -r path; do
  [[ -n "${path}" ]] || continue
  found=1
  bytes="$(bytes_du "${path}")"
  printf '  %12s  %s\n' "$(human_bytes "${bytes}")" "${path}"
  printf '    review: ./scripts/manage-models.sh remove %q --dry-run\n' "${path}"
done < <(inactive_managed_models)
[[ "${found}" == 1 ]] || printf '  none\n'

printf '\n[2. Docker reclaimable]\n'
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  docker system df || true
  printf '  safe experiment cleanup: ./scripts/manage-storage.sh prune --experiments --dry-run\n'
  printf '  note: tagged unused baseline/optional images are reported by Docker but not removed by default prune.\n'
else
  printf '  Docker unavailable\n'
fi

printf '\n[3. Hugging Face cache - report only]\n'
printf '  total: %s (%s)\n' "${HF_CACHE}" "$(human_du "${HF_CACHE}")"
found=0
while IFS=$'\t' read -r bytes path; do
  [[ -n "${path}" ]] || continue
  found=1
  printf '  %12s  %s\n' "$(human_bytes "${bytes}")" "${path}"
done < <(hf_cache_top)
[[ "${found}" == 1 ]] || printf '  no top-level cache directories found\n'
printf '  normal prune preserves HF cache; inspect with: ./scripts/manage-storage.sh hf-cache list\n'
printf '  remove one selected model cache with: ./scripts/manage-storage.sh hf-cache remove models--ORG--MODEL --dry-run\n'

printf '\n[4. Protected large allocations]\n'
printf '  profile      : %s\n' "${ACTIVE_PROFILE:-none}"
printf '  active model : %s (%s)\n' "${ACTIVE_MODEL:-none}" "$([[ -n "${ACTIVE_MODEL}" ]] && human_du "${ACTIVE_MODEL}" || printf '-')"
printf '  active image : %s\n' "${ACTIVE_IMAGE:-none}"
if [[ -e /swap-ple.img ]]; then
  printf '  PLE swap     : /swap-ple.img (%s disk use; active runtime dependency)\n' "$(human_du /swap-ple.img)"
else
  printf '  PLE swap     : not present\n'
fi

printf '\nRecommended order: inactive checkpoints -> disposable Docker assets -> inspect HF cache.\n'
