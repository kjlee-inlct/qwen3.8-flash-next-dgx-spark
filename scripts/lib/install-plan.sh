#!/usr/bin/env bash
# Canonical installer plan snapshot used after CLI/Wizard input collection.
# This file is sourced by wizard-ui.sh only for install.sh; it performs no host mutation.

install_plan_expand_user_path() {
  case "$1" in
    "~") printf '%s\n' "${HOME}" ;;
    "~/"*) printf '%s/%s\n' "${HOME}" "${1:2}" ;;
    *) printf '%s\n' "$1" ;;
  esac
}

install_plan_apply_snapshot() {
  [[ "${INSTALL_PLAN_READY:-0}" == 1 ]] || return 1
  [[ "${PLAN_SCHEMA_VERSION}" == 1 ]] || return 1
  case "${PLAN_CONFIG_MODE}" in
    path|automatic|checkpoint) ;;
    *) return 1 ;;
  esac

  MODEL_PROFILE="${PLAN_MODEL_PROFILE}"
  REPO="${PLAN_MODEL_REPO}"
  REVISION="${PLAN_MODEL_REVISION}"
  MODEL_ROOT="${PLAN_MODEL_ROOT}"
  MODEL_ROOT_SOURCE="${PLAN_MODEL_ROOT_SOURCE}"
  MODEL_DIR="${PLAN_MODEL_DIR}"
  IMAGE="${PLAN_IMAGE}"
  SERVED_NAME="${PLAN_SERVED_NAME}"
  CONFIG_OVERRIDE="${PLAN_CONFIG_OVERRIDE}"
  SWAP_FILE="${PLAN_SWAP_FILE}"
  MONITOR_ENABLED="${PLAN_MONITOR_ENABLED}"
  MONITOR_PROTECT="${PLAN_MONITOR_PROTECT}"
  MONITOR_MIN_AVAILABLE_GIB="${PLAN_MONITOR_MIN_AVAILABLE_GIB}"
  MONITOR_MIN_FREE_GIB="${PLAN_MONITOR_MIN_FREE_GIB}"
  MONITOR_FREE_GATE_GIB="${PLAN_MONITOR_FREE_GATE_GIB}"
  MONITOR_MIN_SWAP_FREE_GIB="${PLAN_MONITOR_MIN_SWAP_FREE_GIB}"
  MONITOR_CONSECUTIVE="${PLAN_MONITOR_CONSECUTIVE}"
  MONITOR_HEARTBEAT="${PLAN_MONITOR_HEARTBEAT}"
  API_ACCESS_MODE="${PLAN_API_ACCESS_MODE}"
  API_DOCKER_PORT="${PLAN_API_DOCKER_PORT}"
  API_LAN_ADDRESS="${PLAN_API_LAN_ADDRESS}"
  API_LAN_PORT="${PLAN_API_LAN_PORT}"
  PROXY_ENABLED="${PLAN_PROXY_ENABLED}"
  PROXY_PORT="${PLAN_PROXY_PORT}"
  SERVICE_ENABLED="${PLAN_SERVICE_ENABLED}"
  PROFILE_SWITCH="${PLAN_PROFILE_SWITCH}"
  SWITCH_FROM_PROFILE="${PLAN_SWITCH_FROM_PROFILE}"
  START="${PLAN_START}"
  DRY_RUN="${PLAN_DRY_RUN}"
  REFRESH_PROFILE_DEFAULTS="${PLAN_REFRESH_PROFILE_DEFAULTS}"
  UI_LANG="${PLAN_UI_LANG}"

  if [[ "${PLAN_PROFILE_LOCAL_BUILD}" == 1 ]]; then
    HYBRID_BASE_DIR="${PLAN_HYBRID_BASE_DIR}"
    HYBRID_OVERLAY_DIR="${PLAN_HYBRID_OVERLAY_DIR}"
    HYBRID_H3_DIR="${PLAN_HYBRID_H3_DIR}"
    HYBRID_H4_DIR="${PLAN_HYBRID_H4_DIR}"
    HYBRID_H5_DIR="${PLAN_HYBRID_H5_DIR}"
    HYBRID_REUSE_H3="${PLAN_HYBRID_REUSE_H3}"
  fi

  export QWEN38_MODEL_ROOT="${MODEL_ROOT}"
}

install_plan_render_cli_preview() {
  [[ "${INSTALL_PLAN_READY:-0}" == 1 ]] || return 1
  [[ "${PLAN_SCHEMA_VERSION:-}" == 1 ]] || return 1
  declare -F install_option_flag >/dev/null 2>&1 || {
    printf 'ERROR: normalized CLI rendering requires the installer option registry\n' >&2
    return 1
  }

  local monitor_variant service_variant arg quoted rendered=""
  local -a args=("./install.sh")

  args+=(
    "$(install_option_flag language)" "${PLAN_UI_LANG}"
    "$(install_option_flag confirmation)"
    "$(install_option_flag dry_run)"
    "$(install_option_flag profile)" "${PLAN_MODEL_PROFILE}"
    "$(install_option_flag model_root)" "${PLAN_MODEL_ROOT}"
  )

  if [[ -n "${PLAN_CONFIG_OVERRIDE}" ]]; then
    args+=("$(install_option_flag config_override config-override)" "${PLAN_CONFIG_OVERRIDE}")
  else
    args+=("$(install_option_flag config_override no-config-override)")
  fi

  if [[ "${PLAN_MONITOR_ENABLED}" == 0 ]]; then
    monitor_variant=no-monitor
  elif [[ "${PLAN_MONITOR_PROTECT}" == 1 ]]; then
    monitor_variant=protect
  else
    monitor_variant=monitor
  fi
  args+=("$(install_option_flag monitor_mode "${monitor_variant}")")
  args+=(
    "$(install_option_flag monitor_min_available)" "${PLAN_MONITOR_MIN_AVAILABLE_GIB}"
    "$(install_option_flag monitor_min_free)" "${PLAN_MONITOR_MIN_FREE_GIB}"
    "$(install_option_flag monitor_free_gate)" "${PLAN_MONITOR_FREE_GATE_GIB}"
    "$(install_option_flag monitor_min_swap_free)" "${PLAN_MONITOR_MIN_SWAP_FREE_GIB}"
    "$(install_option_flag monitor_consecutive)" "${PLAN_MONITOR_CONSECUTIVE}"
    "$(install_option_flag monitor_heartbeat)" "${PLAN_MONITOR_HEARTBEAT}"
    "$(install_option_flag api_access)" "${PLAN_API_ACCESS_MODE}"
    "$(install_option_flag api_docker_port)" "${PLAN_API_DOCKER_PORT}"
    "$(install_option_flag api_lan_port)" "${PLAN_API_LAN_PORT}"
  )
  if [[ -n "${PLAN_API_LAN_ADDRESS}" ]]; then
    args+=("$(install_option_flag api_lan_address)" "${PLAN_API_LAN_ADDRESS}")
  fi

  [[ "${PLAN_SERVICE_ENABLED}" == 1 ]] && service_variant=service || service_variant=no-service
  args+=("$(install_option_flag service_mode "${service_variant}")")

  [[ "${PLAN_START}" != 0 ]] || args+=("$(install_option_flag start_policy)")
  [[ "${PLAN_REFRESH_PROFILE_DEFAULTS}" != 1 ]] || args+=("$(install_option_flag refresh_profile_defaults)")

  for arg in "${args[@]}"; do
    printf -v quoted '%q' "${arg}"
    [[ -z "${rendered}" ]] || rendered+=" "
    rendered+="${quoted}"
  done
  printf '%s\n' "${rendered}"
}

install_plan_finalize() {
  declare -F validate_monitor_settings >/dev/null 2>&1 || {
    printf 'ERROR: normalized install plan requires monitor validation\n' >&2
    return 1
  }
  declare -F validate_api_access_settings >/dev/null 2>&1 || {
    printf 'ERROR: normalized install plan requires API validation\n' >&2
    return 1
  }

  validate_monitor_settings
  validate_api_access_settings

  MODEL_ROOT="$(realpath -m -- "$(install_plan_expand_user_path "${MODEL_ROOT}")")"
  MODEL_DIR="$(realpath -m -- "$(install_plan_expand_user_path "${MODEL_DIR}")")"
  if [[ -n "${CONFIG_OVERRIDE}" ]]; then
    CONFIG_OVERRIDE="$(realpath -m -- "$(install_plan_expand_user_path "${CONFIG_OVERRIDE}")")"
  fi

  if [[ "${PROFILE_LOCAL_BUILD:-0}" == 1 ]]; then
    HYBRID_BASE_DIR="$(realpath -m -- "${HYBRID_BASE_DIR}")"
    HYBRID_OVERLAY_DIR="$(realpath -m -- "${HYBRID_OVERLAY_DIR}")"
    HYBRID_H3_DIR="$(realpath -m -- "${HYBRID_H3_DIR}")"
    HYBRID_H4_DIR="$(realpath -m -- "${HYBRID_H4_DIR}")"
    HYBRID_H5_DIR="$(realpath -m -- "${HYBRID_H5_DIR}")"
  fi

  PLAN_SCHEMA_VERSION=1
  PLAN_MODEL_PROFILE="${MODEL_PROFILE}"
  PLAN_MODEL_REPO="${REPO}"
  PLAN_MODEL_REVISION="${REVISION}"
  PLAN_MODEL_ROOT="${MODEL_ROOT}"
  PLAN_MODEL_ROOT_SOURCE="${MODEL_ROOT_SOURCE}"
  PLAN_MODEL_DIR="${MODEL_DIR}"
  PLAN_IMAGE="${IMAGE}"
  PLAN_SERVED_NAME="${SERVED_NAME}"
  PLAN_CONFIG_OVERRIDE="${CONFIG_OVERRIDE}"
  if [[ -n "${CONFIG_OVERRIDE}" ]]; then
    PLAN_CONFIG_MODE=path
  elif [[ "${PROFILE_CONFIG_OVERRIDE:-0}" == 1 ]]; then
    PLAN_CONFIG_MODE=automatic
  else
    PLAN_CONFIG_MODE=checkpoint
  fi

  PLAN_SWAP_FILE="${SWAP_FILE}"
  PLAN_MONITOR_ENABLED="${MONITOR_ENABLED}"
  PLAN_MONITOR_PROTECT="${MONITOR_PROTECT}"
  PLAN_MONITOR_MIN_AVAILABLE_GIB="${MONITOR_MIN_AVAILABLE_GIB}"
  PLAN_MONITOR_MIN_FREE_GIB="${MONITOR_MIN_FREE_GIB}"
  PLAN_MONITOR_FREE_GATE_GIB="${MONITOR_FREE_GATE_GIB}"
  PLAN_MONITOR_MIN_SWAP_FREE_GIB="${MONITOR_MIN_SWAP_FREE_GIB}"
  PLAN_MONITOR_CONSECUTIVE="${MONITOR_CONSECUTIVE}"
  PLAN_MONITOR_HEARTBEAT="${MONITOR_HEARTBEAT}"

  PLAN_API_ACCESS_MODE="${API_ACCESS_MODE}"
  PLAN_API_DOCKER_PORT="${API_DOCKER_PORT}"
  PLAN_API_LAN_ADDRESS="${API_LAN_ADDRESS}"
  PLAN_API_LAN_PORT="${API_LAN_PORT}"
  PLAN_PROXY_ENABLED="${PROXY_ENABLED}"
  PLAN_PROXY_PORT="${PROXY_PORT}"
  PLAN_SERVICE_ENABLED="${SERVICE_ENABLED}"

  PLAN_PROFILE_SWITCH="${PROFILE_SWITCH}"
  PLAN_SWITCH_FROM_PROFILE="${SWITCH_FROM_PROFILE}"
  PLAN_START="${START}"
  PLAN_DRY_RUN="${DRY_RUN}"
  PLAN_REFRESH_PROFILE_DEFAULTS="${REFRESH_PROFILE_DEFAULTS}"
  PLAN_PROFILE_LOCAL_BUILD="${PROFILE_LOCAL_BUILD:-0}"
  PLAN_HYBRID_BASE_DIR="${HYBRID_BASE_DIR:-}"
  PLAN_HYBRID_OVERLAY_DIR="${HYBRID_OVERLAY_DIR:-}"
  PLAN_HYBRID_H3_DIR="${HYBRID_H3_DIR:-}"
  PLAN_HYBRID_H4_DIR="${HYBRID_H4_DIR:-}"
  PLAN_HYBRID_H5_DIR="${HYBRID_H5_DIR:-}"
  PLAN_HYBRID_REUSE_H3="${HYBRID_REUSE_H3:-0}"
  PLAN_UI_LANG="${UI_LANG}"

  INSTALL_PLAN_READY=1
  install_plan_apply_snapshot
}
