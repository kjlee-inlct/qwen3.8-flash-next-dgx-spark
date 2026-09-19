#!/usr/bin/env bash
# Shared, side-effect-free checkpoint profile registry.

list_model_profiles() {
  printf '%s\n' orcarouter nvidia
}

load_model_profile() {
  case "$1" in
    orcarouter)
      PROFILE_REPO="orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      PROFILE_REVISION="c1209bda15a6bbc4c68b585e93d40c0d85f50306"
      PROFILE_MODEL_DIR="${HOME}/models/qwen3.8-flash-next-orcarouter"
      PROFILE_IMAGE="vllm-skinny-tp1:v1"
      PROFILE_SERVED_NAME="orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      PROFILE_GATED=1
      PROFILE_CONFIG_OVERRIDE=1
      ;;
    nvidia)
      PROFILE_REPO="nvidia/Qwen3.8-Flash-Next-NVFP4"
      PROFILE_REVISION="fc694b54fb0174e0913e6adf86691ef85a4ead47"
      PROFILE_MODEL_DIR="${HOME}/models/qwen3.8-flash-next-nvidia"
      PROFILE_IMAGE="vllm-nv-mixed:v2"
      PROFILE_SERVED_NAME="qwen3.8-flash-next"
      PROFILE_GATED=0
      PROFILE_CONFIG_OVERRIDE=0
      ;;
    *)
      printf 'ERROR: unknown model profile: %s (expected orcarouter or nvidia)\n' "$1" >&2
      return 2
      ;;
  esac
}
