#!/usr/bin/env bash
# Shared, side-effect-free checkpoint profile registry.
#
# Stability policy:
#   stable       qualified default path
#   experimental installable/non-default; qualification level is profile-specific
#   in-progress  integration/qualification is actively underway; not installable yet
#   planned      tracked roadmap item; not installable yet

list_model_profiles() {
  # Installable profiles only.
  printf '%s\n' orcarouter nvidia mazinb orcarouter-hybrid
}

list_model_candidates() {
  printf '%s\n' lychee888
}

describe_model_profile() {
  case "$1" in
    orcarouter)
      PROFILE_STATUS="stable"
      PROFILE_DISPLAY_NAME="OrcaRouter Uncensored"
      PROFILE_DEFAULT=1
      PROFILE_INSTALLABLE=1
      PROFILE_REPO="orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      PROFILE_DESCRIPTION="Primary qualified OrcaRouter profile; 16 GiB managed KV resilience default"
      PROFILE_DESCRIPTION_KO="기본 검증 OrcaRouter 프로필; 관리형 KV 복원력 기본값 16 GiB"
      ;;
    nvidia)
      PROFILE_STATUS="experimental"
      PROFILE_DISPLAY_NAME="NVIDIA Official NVFP4"
      PROFILE_DEFAULT=0
      PROFILE_INSTALLABLE=1
      PROFILE_REPO="nvidia/Qwen3.8-Flash-Next-NVFP4"
      PROFILE_DESCRIPTION="Optional NVIDIA comparison profile"
      PROFILE_DESCRIPTION_KO="선택형 NVIDIA 비교 프로필"
      ;;
    mazinb)
      PROFILE_STATUS="experimental"
      PROFILE_DISPLAY_NAME="mazinb NVFP4"
      PROFILE_DEFAULT=0
      PROFILE_INSTALLABLE=1
      PROFILE_REPO="mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      PROFILE_DESCRIPTION="Optional mazinb profile; 16 GiB managed KV resilience mitigation validated"
      PROFILE_DESCRIPTION_KO="선택형 mazinb 프로필; 관리형 KV 복원력 완화 설정 16 GiB 검증"
      ;;
    orcarouter-hybrid)
      PROFILE_STATUS="experimental"
      PROFILE_DISPLAY_NAME="OrcaRouter Hybrid H6"
      PROFILE_DEFAULT=0
      PROFILE_INSTALLABLE=1
      PROFILE_REPO="local/orcarouter-mazinb-h6-w4a16"
      PROFILE_DESCRIPTION="Generated H6 hybrid (OrcaRouter + mazinb experts, W4A16 NVFP4)"
      PROFILE_DESCRIPTION_KO="생성형 H6 hybrid (OrcaRouter + mazinb experts, W4A16 NVFP4)"
      ;;
    lychee888)
      PROFILE_STATUS="planned"
      PROFILE_DISPLAY_NAME="lychee888 FP8-PLE"
      PROFILE_DEFAULT=0
      PROFILE_INSTALLABLE=0
      PROFILE_REPO="lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE"
      PROFILE_DESCRIPTION="Planned OrcaRouter-derived FP8-PLE profile"
      PROFILE_DESCRIPTION_KO="계획 중인 OrcaRouter 파생 FP8-PLE 프로필"
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
  local model_root="${QWEN38_MODEL_ROOT:-${HOME}/models}"
  PROFILE_LOCAL_BUILD=0
  PROFILE_BASE_PROFILE=""
  PROFILE_OVERLAY_PROFILE=""

  case "$1" in
    orcarouter)
      PROFILE_REVISION="c1209bda15a6bbc4c68b585e93d40c0d85f50306"
      PROFILE_MODEL_DIR="${model_root}/qwen3.8-flash-next-orcarouter"
      PROFILE_IMAGE="vllm-orcarouter-v029-h38-decoder-scope:v1"
      PROFILE_SERVED_NAME="orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      PROFILE_GATED=1
      PROFILE_CONFIG_OVERRIDE=1
      ;;
    nvidia)
      PROFILE_REVISION="fc694b54fb0174e0913e6adf86691ef85a4ead47"
      PROFILE_MODEL_DIR="${model_root}/qwen3.8-flash-next-nvidia"
      PROFILE_IMAGE="vllm-nv-mixed:v2"
      PROFILE_SERVED_NAME="qwen3.8-flash-next"
      PROFILE_GATED=0
      PROFILE_CONFIG_OVERRIDE=0
      ;;
    mazinb)
      # Short immutable Hugging Face commit ID verified for the qualified checkpoint.
      # download-weights.sh records the resolved full SHA in its local manifest.
      PROFILE_REVISION="f2c21eb"
      PROFILE_MODEL_DIR="${model_root}/qwen3.8-flash-next-mazinb"
      PROFILE_IMAGE="vllm-orcarouter-v029:v1"
      PROFILE_SERVED_NAME="mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      PROFILE_GATED=0
      PROFILE_CONFIG_OVERRIDE=0
      ;;
    orcarouter-hybrid)
      PROFILE_REVISION="h6-modelopt-w4a16-v1"
      PROFILE_MODEL_DIR="${model_root}/qwen3.8-h6-modelopt-w4a16"
      PROFILE_IMAGE="vllm-orcarouter-v029:v1"
      PROFILE_SERVED_NAME="orcarouter-hybrid/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      PROFILE_GATED=1
      PROFILE_CONFIG_OVERRIDE=0
      PROFILE_LOCAL_BUILD=1
      PROFILE_BASE_PROFILE="orcarouter"
      PROFILE_OVERLAY_PROFILE="mazinb"
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
