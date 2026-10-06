#!/usr/bin/env bash
# Shared terminal UI helpers for interactive installer/uninstaller flows.
# Sourced by lifecycle scripts; no host mutations.

WIZARD_BLUE=""
WIZARD_GREEN=""
WIZARD_YELLOW=""
WIZARD_RED=""
WIZARD_BOLD=""
WIZARD_RESET=""

# install.sh has a six-step review boundary shared by CLI and Wizard flows. Load
# installer-only UI/plan helpers only for that caller; uninstall/other UI
# consumers remain independent of installer configuration semantics.
if [[ "${BASH_SOURCE[1]:-}" == */install.sh ]]; then
  WIZARD_LIB_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
  INSTALL_PLAN_HELPER="${WIZARD_LIB_DIR}/install-plan.sh"
  INSTALL_COMPLETED_MANAGER_HELPER="${WIZARD_LIB_DIR}/install-completed-manager.sh"
  [[ -r "${INSTALL_PLAN_HELPER}" ]] || {
    printf 'ERROR: installer plan helper missing: %s\n' "${INSTALL_PLAN_HELPER}" >&2
    return 1
  }
  [[ -r "${INSTALL_COMPLETED_MANAGER_HELPER}" ]] || {
    printf 'ERROR: completed-install manager helper missing: %s\n' "${INSTALL_COMPLETED_MANAGER_HELPER}" >&2
    return 1
  }
  # shellcheck source=install-plan.sh
  source "${INSTALL_PLAN_HELPER}"
  # shellcheck source=install-completed-manager.sh
  source "${INSTALL_COMPLETED_MANAGER_HELPER}"
fi

wizard_init() {
  if [[ -t 1 && -z "${NO_COLOR:-}" ]]; then
    WIZARD_BLUE=$'\033[0;34m'
    WIZARD_GREEN=$'\033[0;32m'
    WIZARD_YELLOW=$'\033[1;33m'
    WIZARD_RED=$'\033[0;31m'
    WIZARD_BOLD=$'\033[1m'
    WIZARD_RESET=$'\033[0m'
  fi
}

wizard_rule() {
  printf '%s\n' '========================================'
}

wizard_header() {
  local title="$1"
  printf '\n%s%s' "${WIZARD_BLUE}" "${WIZARD_BOLD}"
  wizard_rule
  printf ' %s\n' "${title}"
  wizard_rule
  printf '%s\n' "${WIZARD_RESET}"
}

wizard_step() {
  local current="$1" total="$2" title="$3"
  if declare -F install_completed_manager_step_hook >/dev/null 2>&1; then
    if install_completed_manager_step_hook "${current}" "${total}" "${title}"; then
      return 0
    fi
  fi
  if [[ "${current}" == 6 && "${total}" == 6 ]] && declare -F install_plan_finalize >/dev/null 2>&1; then
    install_plan_finalize
  fi
  printf '\n%s%s[%s/%s] %s%s\n\n' \
    "${WIZARD_BLUE}" "${WIZARD_BOLD}" "${current}" "${total}" "${title}" "${WIZARD_RESET}"
}

wizard_info() {
  if declare -F install_completed_manager_info_hook >/dev/null 2>&1; then
    if install_completed_manager_info_hook "$*"; then
      return 0
    fi
  fi
  printf '%sℹ  %s%s\n' "${WIZARD_BLUE}" "$*" "${WIZARD_RESET}"
}

wizard_success() {
  printf '%s✓ %s%s\n' "${WIZARD_GREEN}" "$*" "${WIZARD_RESET}"
}

wizard_warning() {
  printf '%s! %s%s\n' "${WIZARD_YELLOW}" "$*" "${WIZARD_RESET}"
}

wizard_error() {
  printf '%s✗ %s%s\n' "${WIZARD_RED}" "$*" "${WIZARD_RESET}" >&2
}

wizard_menu_option() {
  local number="$1" title="$2" detail="${3:-}"
  if declare -F install_completed_manager_menu_option_hook >/dev/null 2>&1; then
    if install_completed_manager_menu_option_hook "${number}" "${title}" "${detail}"; then
      return 0
    fi
  fi
  printf '  %s) %s\n' "${number}" "${title}"
  [[ -z "${detail}" ]] || printf '     %s\n' "${detail}"
}

wizard_read_raw() {
  local variable="$1" prompt="$2" secret="${3:-0}" raw_value=""
  if [[ -t 0 && -r /dev/tty ]]; then
    if [[ "${secret}" == 1 ]]; then
      IFS= read -r -s -p "${prompt}" raw_value </dev/tty
      printf '\n' >/dev/tty
    else
      IFS= read -r -p "${prompt}" raw_value </dev/tty
    fi
  else
    if [[ "${secret}" == 1 ]]; then
      IFS= read -r -s -p "${prompt}" raw_value
      printf '\n'
    else
      IFS= read -r -p "${prompt}" raw_value
    fi
  fi
  printf -v "${variable}" '%s' "${raw_value}"
}

wizard_input() {
  local variable="$1" prompt="$2" default="${3:-}" input_value=""
  if declare -F install_completed_manager_input_hook >/dev/null 2>&1; then
    WIZARD_INPUT_HOOK_VALUE=""
    if install_completed_manager_input_hook "${prompt}" "${default}"; then
      printf -v "${variable}" '%s' "${WIZARD_INPUT_HOOK_VALUE}"
      return 0
    fi
  fi
  wizard_read_raw input_value "${WIZARD_BLUE}${prompt}${WIZARD_RESET} [${default}]: "
  printf -v "${variable}" '%s' "${input_value:-${default}}"
}

wizard_secret() {
  local variable="$1" prompt="$2" secret_value=""
  wizard_read_raw secret_value "${WIZARD_BLUE}${prompt}${WIZARD_RESET}: " 1
  printf -v "${variable}" '%s' "${secret_value}"
}

wizard_yes_no() {
  local prompt="$1" default="${2:-yes}" answer suffix
  case "${default}" in
    yes|y|Y) suffix='[Y/n]' ;;
    no|n|N) suffix='[y/N]' ;;
    *) return 2 ;;
  esac
  while true; do
    wizard_read_raw answer "${WIZARD_BLUE}${prompt}${WIZARD_RESET} ${suffix}: "
    case "${answer}" in
      y|Y|yes|YES|Yes|예) return 0 ;;
      n|N|no|NO|No|아니오) return 1 ;;
      "")
        [[ "${default}" == yes || "${default}" == y || "${default}" == Y ]]
        return
        ;;
      *) wizard_warning "Please answer y/n (예/아니오)." ;;
    esac
  done
}

wizard_init