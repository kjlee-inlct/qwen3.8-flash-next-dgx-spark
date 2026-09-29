#!/usr/bin/env bash
# Shared terminal UI helpers for interactive installer/uninstaller flows.
# Sourced by lifecycle scripts; no host mutations.

WIZARD_BLUE=""
WIZARD_GREEN=""
WIZARD_YELLOW=""
WIZARD_RED=""
WIZARD_BOLD=""
WIZARD_RESET=""

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
  printf '\n%s%s[%s/%s] %s%s\n\n'     "${WIZARD_BLUE}" "${WIZARD_BOLD}" "${current}" "${total}" "${title}" "${WIZARD_RESET}"
}

wizard_info() {
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
  printf '  %s) %s\n' "${number}" "${title}"
  [[ -z "${detail}" ]] || printf '     %s\n' "${detail}"
}

wizard_read_raw() {
  local variable="$1" prompt="$2" secret="${3:-0}" answer=""
  if [[ -t 0 && -r /dev/tty ]]; then
    if [[ "${secret}" == 1 ]]; then
      IFS= read -r -s -p "${prompt}" answer </dev/tty
      printf '\n' >/dev/tty
    else
      IFS= read -r -p "${prompt}" answer </dev/tty
    fi
  else
    if [[ "${secret}" == 1 ]]; then
      IFS= read -r -s -p "${prompt}" answer
      printf '\n'
    else
      IFS= read -r -p "${prompt}" answer
    fi
  fi
  printf -v "${variable}" '%s' "${answer}"
}

wizard_input() {
  local variable="$1" prompt="$2" default="${3:-}" answer=""
  wizard_read_raw answer "${WIZARD_BLUE}${prompt}${WIZARD_RESET} [${default}]: "
  printf -v "${variable}" '%s' "${answer:-${default}}"
}

wizard_secret() {
  local variable="$1" prompt="$2" answer=""
  wizard_read_raw answer "${WIZARD_BLUE}${prompt}${WIZARD_RESET}: " 1
  printf -v "${variable}" '%s' "${answer}"
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
