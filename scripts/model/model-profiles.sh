#!/usr/bin/env bash
# Shared, side-effect-free checkpoint profile registry.
#
# Stability policy:
#   stable       qualified default path
#   experimental qualified/installable, but not the default
#   in-progress  integration/qualification is actively underway; not installable yet
#   planned      tracked roadmap item; not installable yet

list_model_profiles() {
  # Installable profiles only.
  printf '%s\n' orcarouter nvidia mazinb
}

list_model_candidates() {
  printf '%s\n' orcarouter-hybrid lychee888
}

describe_model_profile() {
  case "$1" in
    orcarouter)
      PROFILE_STATUS="stable"
      PROFILE_DEFAULT=1
      PROFILE_INSTALLABLE=1
      PROFILE_REPO="orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      PROFILE_DESCRIPTION="Primary qualified OrcaRouter profile"
      ;;
    nvidia)
      PROFILE_STATUS="experimental"
      PROFILE_DEFAULT=0
      PROFILE_INSTALLABLE=1
      PROFILE_REPO="nvidia/Qwen3.8-Flash-Next-NVFP4"
      PROFILE_DESCRIPTION="Optional NVIDIA comparison profile"
      ;;
    mazinb)
      PROFILE_STATUS="experimental"
      PROFILE_DEFAULT=0
      PROFILE_INSTALLABLE=1
      PROFILE_REPO="mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      PROFILE_DESCRIPTION="Qualified optional experts-only NVFP4 + BF16 PLE profile"
      ;;
    orcarouter-hybrid)
      PROFILE_STATUS="in-progress"
      PROFILE_DEFAULT=0
      PROFILE_INSTALLABLE=0
      PROFILE_REPO="TBD"
      PROFILE_DESCRIPTION="OrcaRouter hybrid installer profile; integration and qualification in progress"
      ;;
    lychee888)
      PROFILE_STATUS="planned"
      PROFILE_DEFAULT=0
      PROFILE_INSTALLABLE=0
      PROFILE_REPO="lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE"
      PROFILE_DESCRIPTION="Planned OrcaRouter-derived FP8-PLE profile"
      ;;
    *)
      printf 'ERROR: unknown model profile: %s\n' "$1" >&2
      return 2
      ;;
  esac
}

print_model_profiles() {
  local profile
  printf '%-12s %-14s %-11s %-8s %s\n' PROFILE STATUS INSTALLABLE DEFAULT REPOSITORY
  for profile in orcarouter nvidia mazinb orcarouter-hybrid lychee888; do
    describe_model_profile "${profile}" || return
    printf '%-12s %-14s %-11s %-8s %s\n' \
      "${profile}" "${PROFILE_STATUS}" "${PROFILE_INSTALLABLE}" "${PROFILE_DEFAULT}" "${PROFILE_REPO}"
  done
}

load_download_profile() {
  describe_model_profile "$1" || return

  case "$1" in
    orcarouter)
      PROFILE_REVISION="c1209bda15a6bbc4c68b585e93d40c0d85f50306"
      PROFILE_MODEL_DIR="${HOME}/models/qwen3.8-flash-next-orcarouter"
      PROFILE_IMAGE="vllm-skinny-tp1:v1"
      PROFILE_SERVED_NAME="orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      PROFILE_GATED=1
      PROFILE_CONFIG_OVERRIDE=1
      ;;
    nvidia)
      PROFILE_REVISION="fc694b54fb0174e0913e6adf86691ef85a4ead47"
      PROFILE_MODEL_DIR="${HOME}/models/qwen3.8-flash-next-nvidia"
      PROFILE_IMAGE="vllm-nv-mixed:v2"
      PROFILE_SERVED_NAME="qwen3.8-flash-next"
      PROFILE_GATED=0
      PROFILE_CONFIG_OVERRIDE=0
      ;;
    mazinb)
      # Short immutable Hugging Face commit ID verified for the qualified checkpoint.
      # download-weights.sh records the resolved full SHA in its local manifest.
      PROFILE_REVISION="f2c21eb"
      PROFILE_MODEL_DIR="${HOME}/models/qwen3.8-flash-next-mazinb"
      PROFILE_IMAGE="vllm-orcarouter-v029:v1"
      PROFILE_SERVED_NAME="mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      PROFILE_GATED=0
      PROFILE_CONFIG_OVERRIDE=0
      ;;
    orcarouter-hybrid)
      printf 'ERROR: model profile %s is still in progress and has no qualified download/runtime path yet\n' "$1" >&2
      return 2
      ;;
    lychee888)
      printf 'ERROR: model profile %s is planned and has no qualified download/runtime path yet\n' "$1" >&2
      return 2
      ;;
  esac
}

load_model_profile() {
  describe_model_profile "$1" || return
  if [[ "${PROFILE_INSTALLABLE}" != 1 ]]; then
    printf 'ERROR: model profile %s is a %s profile and is not installable yet\n' "$1" "${PROFILE_STATUS}" >&2
    return 2
  fi
  load_download_profile "$1"
}
