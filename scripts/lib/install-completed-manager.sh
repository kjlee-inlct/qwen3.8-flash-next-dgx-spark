#!/usr/bin/env bash
# Installer-only completed-install management UI.
#
# This helper is sourced by wizard-ui.sh only when the caller is install.sh. It
# stages settings in memory and reapplies them immediately before the shared 6/6
# normalized-plan boundary. It performs no host mutation and creates no state.

INSTALL_COMPLETED_ACTION=""
INSTALL_COMPLETED_SUPPRESS_PROFILE_SELECTION=0
INSTALL_COMPLETED_PENDING_SETTINGS=0
INSTALL_COMPLETED_SETTINGS_PREVIEW_ONLY=0

install_completed_bool_default() {
  [[ "$1" == 1 ]] && printf 'yes\n' || printf 'no\n'
}

install_completed_current_config_label() {
  if [[ -n "${CONFIG_OVERRIDE:-}" ]]; then
    printf '%s\n' "${CONFIG_OVERRIDE}"
  elif [[ "${PROFILE_CONFIG_OVERRIDE:-0}" == 1 ]]; then
    [[ "${UI_LANG:-ko}" == ko ]] && printf '자동 profile override\n' || printf 'automatic profile override\n'
  else
    [[ "${UI_LANG:-ko}" == ko ]] && printf '체크포인트 기본 설정\n' || printf 'checkpoint config\n'
  fi
}

install_completed_stage_settings() {
  local answer monitor_default protect_default service_default api_default detected_lan

  INSTALL_COMPLETED_CONFIG_OVERRIDE="${CONFIG_OVERRIDE:-}"
  INSTALL_COMPLETED_CONFIG_OWNED="${CONFIG_OWNED:-0}"
  INSTALL_COMPLETED_MONITOR_ENABLED="${MONITOR_ENABLED:-0}"
  INSTALL_COMPLETED_MONITOR_PROTECT="${MONITOR_PROTECT:-0}"
  INSTALL_COMPLETED_MONITOR_MIN_AVAILABLE_GIB="${MONITOR_MIN_AVAILABLE_GIB:-6}"
  INSTALL_COMPLETED_MONITOR_MIN_FREE_GIB="${MONITOR_MIN_FREE_GIB:-2}"
  INSTALL_COMPLETED_MONITOR_FREE_GATE_GIB="${MONITOR_FREE_GATE_GIB:-10}"
  INSTALL_COMPLETED_MONITOR_MIN_SWAP_FREE_GIB="${MONITOR_MIN_SWAP_FREE_GIB:-8}"
  INSTALL_COMPLETED_MONITOR_CONSECUTIVE="${MONITOR_CONSECUTIVE:-5}"
  INSTALL_COMPLETED_MONITOR_HEARTBEAT="${MONITOR_HEARTBEAT:-60}"
  INSTALL_COMPLETED_API_ACCESS_MODE="${API_ACCESS_MODE:-local}"
  INSTALL_COMPLETED_API_DOCKER_PORT="${API_DOCKER_PORT:-8000}"
  INSTALL_COMPLETED_API_LAN_ADDRESS="${API_LAN_ADDRESS:-}"
  INSTALL_COMPLETED_API_LAN_PORT="${API_LAN_PORT:-8001}"
  INSTALL_COMPLETED_SERVICE_ENABLED="${SERVICE_ENABLED:-1}"

  if [[ "${UI_LANG}" == ko ]]; then
    wizard_info "현재 config: $(install_completed_current_config_label)"
    wizard_menu_option 1 '현재 config 설정 유지'
    wizard_menu_option 2 'custom config.json 경로 설정 / 변경'
    wizard_menu_option 3 'custom override 해제'
    wizard_input answer 'config 선택' 1
  else
    wizard_info "Current config: $(install_completed_current_config_label)"
    wizard_menu_option 1 'Keep current config setting'
    wizard_menu_option 2 'Set / replace custom config.json path'
    wizard_menu_option 3 'Clear custom override'
    wizard_input answer 'Config selection' 1
  fi
  case "${answer}" in
    1) ;;
    2)
      if [[ "${UI_LANG}" == ko ]]; then
        wizard_input INSTALL_COMPLETED_CONFIG_OVERRIDE '절대 경로 또는 ~/path/to/config.json' "${CONFIG_OVERRIDE:-}"
      else
        wizard_input INSTALL_COMPLETED_CONFIG_OVERRIDE 'Absolute path or ~/path/to/config.json' "${CONFIG_OVERRIDE:-}"
      fi
      [[ -n "${INSTALL_COMPLETED_CONFIG_OVERRIDE}" ]] || die "config override path cannot be empty"
      INSTALL_COMPLETED_CONFIG_OWNED=0
      ;;
    3)
      INSTALL_COMPLETED_CONFIG_OVERRIDE=""
      INSTALL_COMPLETED_CONFIG_OWNED=0
      ;;
    *) die "invalid completed-install config selection" ;;
  esac

  monitor_default="$(install_completed_bool_default "${MONITOR_ENABLED:-0}")"
  if [[ "${UI_LANG}" == ko ]]; then
    wizard_yes_no '런타임 메모리 모니터를 활성화합니까?' "${monitor_default}" && INSTALL_COMPLETED_MONITOR_ENABLED=1 || INSTALL_COMPLETED_MONITOR_ENABLED=0
  else
    wizard_yes_no 'Enable the runtime memory monitor?' "${monitor_default}" && INSTALL_COMPLETED_MONITOR_ENABLED=1 || INSTALL_COMPLETED_MONITOR_ENABLED=0
  fi

  if [[ "${INSTALL_COMPLETED_MONITOR_ENABLED}" == 1 ]]; then
    protect_default="$(install_completed_bool_default "${MONITOR_PROTECT:-0}")"
    if [[ "${UI_LANG}" == ko ]]; then
      wizard_yes_no '지속적인 저메모리 상태에서 컨테이너를 안전하게 중지합니까?' "${protect_default}" && INSTALL_COMPLETED_MONITOR_PROTECT=1 || INSTALL_COMPLETED_MONITOR_PROTECT=0
      if wizard_yes_no '현재 모니터 임계값과 heartbeat를 변경합니까?' no; then
        wizard_input INSTALL_COMPLETED_MONITOR_MIN_AVAILABLE_GIB 'MemAvailable GiB' "${MONITOR_MIN_AVAILABLE_GIB}"
        wizard_input INSTALL_COMPLETED_MONITOR_MIN_FREE_GIB 'MemFree GiB' "${MONITOR_MIN_FREE_GIB}"
        wizard_input INSTALL_COMPLETED_MONITOR_FREE_GATE_GIB 'MemAvailable gate GiB' "${MONITOR_FREE_GATE_GIB}"
        wizard_input INSTALL_COMPLETED_MONITOR_MIN_SWAP_FREE_GIB 'SwapFree GiB' "${MONITOR_MIN_SWAP_FREE_GIB}"
        wizard_input INSTALL_COMPLETED_MONITOR_CONSECUTIVE 'Consecutive samples' "${MONITOR_CONSECUTIVE}"
        wizard_input INSTALL_COMPLETED_MONITOR_HEARTBEAT 'Heartbeat seconds (0 disables)' "${MONITOR_HEARTBEAT}"
      fi
    else
      wizard_yes_no 'Stop the container safely after sustained low memory?' "${protect_default}" && INSTALL_COMPLETED_MONITOR_PROTECT=1 || INSTALL_COMPLETED_MONITOR_PROTECT=0
      if wizard_yes_no 'Change the current monitor thresholds and heartbeat?' no; then
        wizard_input INSTALL_COMPLETED_MONITOR_MIN_AVAILABLE_GIB 'MemAvailable GiB' "${MONITOR_MIN_AVAILABLE_GIB}"
        wizard_input INSTALL_COMPLETED_MONITOR_MIN_FREE_GIB 'MemFree GiB' "${MONITOR_MIN_FREE_GIB}"
        wizard_input INSTALL_COMPLETED_MONITOR_FREE_GATE_GIB 'MemAvailable gate GiB' "${MONITOR_FREE_GATE_GIB}"
        wizard_input INSTALL_COMPLETED_MONITOR_MIN_SWAP_FREE_GIB 'SwapFree GiB' "${MONITOR_MIN_SWAP_FREE_GIB}"
        wizard_input INSTALL_COMPLETED_MONITOR_CONSECUTIVE 'Consecutive samples' "${MONITOR_CONSECUTIVE}"
        wizard_input INSTALL_COMPLETED_MONITOR_HEARTBEAT 'Heartbeat seconds (0 disables)' "${MONITOR_HEARTBEAT}"
      fi
    fi
  else
    INSTALL_COMPLETED_MONITOR_PROTECT=0
  fi

  case "${API_ACCESS_MODE:-local}" in
    local) api_default=1 ;;
    docker) api_default=2 ;;
    lan) api_default=3 ;;
    *) api_default=1 ;;
  esac
  if [[ "${UI_LANG}" == ko ]]; then
    wizard_menu_option 1 '이 PC에서만 사용' '127.0.0.1:8888'
    wizard_menu_option 2 'Docker 앱에서도 사용' "현재 Docker 포트 ${API_DOCKER_PORT:-8000}"
    wizard_menu_option 3 'Docker 앱 + LAN의 다른 PC에서도 사용'
    wizard_input answer 'API 접근 선택' "${api_default}"
  else
    wizard_menu_option 1 'This PC only' '127.0.0.1:8888'
    wizard_menu_option 2 'Also available to Docker apps' "current Docker port ${API_DOCKER_PORT:-8000}"
    wizard_menu_option 3 'Docker apps + other PCs on the LAN'
    wizard_input answer 'API access selection' "${api_default}"
  fi
  case "${answer}" in
    1|local) INSTALL_COMPLETED_API_ACCESS_MODE=local ;;
    2|docker) INSTALL_COMPLETED_API_ACCESS_MODE=docker ;;
    3|lan) INSTALL_COMPLETED_API_ACCESS_MODE=lan ;;
    *) die "invalid completed-install API access selection" ;;
  esac

  if [[ "${INSTALL_COMPLETED_API_ACCESS_MODE}" == docker || "${INSTALL_COMPLETED_API_ACCESS_MODE}" == lan ]]; then
    if [[ "${UI_LANG}" == ko ]]; then
      wizard_input INSTALL_COMPLETED_API_DOCKER_PORT 'Docker 앱 API 포트' "${API_DOCKER_PORT:-8000}"
    else
      wizard_input INSTALL_COMPLETED_API_DOCKER_PORT 'Docker-app API port' "${API_DOCKER_PORT:-8000}"
    fi
  fi
  if [[ "${INSTALL_COMPLETED_API_ACCESS_MODE}" == lan ]]; then
    detected_lan="${API_LAN_ADDRESS:-}"
    [[ -n "${detected_lan}" ]] || detected_lan="$(detect_lan_ipv4)"
    if [[ "${UI_LANG}" == ko ]]; then
      wizard_input INSTALL_COMPLETED_API_LAN_ADDRESS 'LAN에서 사용할 DGX IPv4 주소' "${detected_lan}"
      wizard_input INSTALL_COMPLETED_API_LAN_PORT 'LAN API 포트' "${API_LAN_PORT:-8001}"
    else
      wizard_input INSTALL_COMPLETED_API_LAN_ADDRESS 'DGX IPv4 address to expose on the LAN' "${detected_lan}"
      wizard_input INSTALL_COMPLETED_API_LAN_PORT 'LAN API port' "${API_LAN_PORT:-8001}"
    fi
  else
    INSTALL_COMPLETED_API_LAN_ADDRESS=""
  fi

  service_default="$(install_completed_bool_default "${SERVICE_ENABLED:-1}")"
  if [[ "${UI_LANG}" == ko ]]; then
    wizard_yes_no '부팅 시 자동 시작되는 systemd 서비스를 사용합니까?' "${service_default}" && INSTALL_COMPLETED_SERVICE_ENABLED=1 || INSTALL_COMPLETED_SERVICE_ENABLED=0
  else
    wizard_yes_no 'Use the systemd service that starts at boot?' "${service_default}" && INSTALL_COMPLETED_SERVICE_ENABLED=1 || INSTALL_COMPLETED_SERVICE_ENABLED=0
  fi

  # Until the apply transaction for settings-only changes lands, this UI is
  # deliberately preview-only. That prevents stale proxy/service resources from
  # being left behind when switching LAN -> local or service -> no-service.
  DRY_RUN=1
  INSTALL_COMPLETED_SETTINGS_PREVIEW_ONLY=1
  INSTALL_COMPLETED_PENDING_SETTINGS=1
}

install_completed_apply_staged_settings() {
  [[ "${INSTALL_COMPLETED_PENDING_SETTINGS:-0}" == 1 ]] || return 0

  CONFIG_OVERRIDE="${INSTALL_COMPLETED_CONFIG_OVERRIDE}"
  CONFIG_OWNED="${INSTALL_COMPLETED_CONFIG_OWNED}"
  MONITOR_ENABLED="${INSTALL_COMPLETED_MONITOR_ENABLED}"
  MONITOR_PROTECT="${INSTALL_COMPLETED_MONITOR_PROTECT}"
  MONITOR_MIN_AVAILABLE_GIB="${INSTALL_COMPLETED_MONITOR_MIN_AVAILABLE_GIB}"
  MONITOR_MIN_FREE_GIB="${INSTALL_COMPLETED_MONITOR_MIN_FREE_GIB}"
  MONITOR_FREE_GATE_GIB="${INSTALL_COMPLETED_MONITOR_FREE_GATE_GIB}"
  MONITOR_MIN_SWAP_FREE_GIB="${INSTALL_COMPLETED_MONITOR_MIN_SWAP_FREE_GIB}"
  MONITOR_CONSECUTIVE="${INSTALL_COMPLETED_MONITOR_CONSECUTIVE}"
  MONITOR_HEARTBEAT="${INSTALL_COMPLETED_MONITOR_HEARTBEAT}"
  API_ACCESS_MODE="${INSTALL_COMPLETED_API_ACCESS_MODE}"
  API_DOCKER_PORT="${INSTALL_COMPLETED_API_DOCKER_PORT}"
  API_LAN_ADDRESS="${INSTALL_COMPLETED_API_LAN_ADDRESS}"
  API_LAN_PORT="${INSTALL_COMPLETED_API_LAN_PORT}"
  SERVICE_ENABLED="${INSTALL_COMPLETED_SERVICE_ENABLED}"
}

install_completed_choose_action() {
  local answer

  if [[ "${REFRESH_PROFILE_DEFAULTS:-0}" == 1 ]]; then
    INSTALL_COMPLETED_ACTION=refresh
    INSTALL_COMPLETED_SUPPRESS_PROFILE_SELECTION=1
    return 0
  fi

  printf '\n%s%s[1/1] ' "${WIZARD_BLUE}" "${WIZARD_BOLD}"
  if [[ "${UI_LANG}" == ko ]]; then
    printf '설치 관리%s\n\n' "${WIZARD_RESET}"
    wizard_info "현재 profile: ${MODEL_PROFILE}"
    wizard_menu_option 1 '모델 profile 선택 / 전환'
    wizard_menu_option 2 '런타임 / API / 서비스 설정 미리보기'
    wizard_menu_option 3 '현재 profile 기본값 새로고침'
    wizard_menu_option 4 '취소'
    wizard_input answer '선택' 1
  else
    printf 'Installed setup management%s\n\n' "${WIZARD_RESET}"
    wizard_info "Current profile: ${MODEL_PROFILE}"
    wizard_menu_option 1 'Select / switch model profile'
    wizard_menu_option 2 'Preview runtime / API / service settings'
    wizard_menu_option 3 'Refresh current profile defaults'
    wizard_menu_option 4 'Cancel'
    wizard_input answer 'Select' 1
  fi

  case "${answer}" in
    1)
      INSTALL_COMPLETED_ACTION=profile
      return 1
      ;;
    2)
      INSTALL_COMPLETED_ACTION=settings
      install_completed_stage_settings
      INSTALL_COMPLETED_SUPPRESS_PROFILE_SELECTION=1
      return 0
      ;;
    3)
      INSTALL_COMPLETED_ACTION=refresh
      REFRESH_PROFILE_DEFAULTS=1
      INSTALL_COMPLETED_SUPPRESS_PROFILE_SELECTION=1
      return 0
      ;;
    4)
      [[ "${UI_LANG}" == ko ]] && wizard_info '취소됨' || wizard_info 'Cancelled'
      exit 0
      ;;
    *) die "invalid completed-install action" ;;
  esac
}

# Return 0 when the hook consumes the step, 1 when normal wizard rendering should continue.
install_completed_manager_step_hook() {
  local current="$1" total="$2" title="$3"
  if [[ "${current}" == 1 && "${total}" == 1 && ( "${title}" == 'Model selection' || "${title}" == '모델 선택 / 전환' ) ]]; then
    install_completed_choose_action
    return $?
  fi
  if [[ "${current}" == 6 && "${total}" == 6 ]]; then
    install_completed_apply_staged_settings
  fi
  return 1
}

# Return 0 when the model-selector menu item should be suppressed.
install_completed_manager_menu_option_hook() {
  [[ "${INSTALL_COMPLETED_SUPPRESS_PROFILE_SELECTION:-0}" == 1 ]]
}

# Return 0 when the model-selector input should be auto-filled with its current-profile default.
install_completed_manager_input_hook() {
  local prompt="$1" default="$2"
  if [[ "${INSTALL_COMPLETED_SUPPRESS_PROFILE_SELECTION:-0}" == 1 && ( "${prompt}" == 'Select' || "${prompt}" == '선택' ) ]]; then
    WIZARD_INPUT_HOOK_VALUE="${default}"
    INSTALL_COMPLETED_SUPPRESS_PROFILE_SELECTION=0
    return 0
  fi
  return 1
}

install_completed_manager_info_hook() {
  local message="$1"
  if [[ "${INSTALL_COMPLETED_SUPPRESS_PROFILE_SELECTION:-0}" == 1 && ( "${message}" == Current\ profile:* || "${message}" == 현재\ profile:* ) ]]; then
    return 0
  fi
  return 1
}
