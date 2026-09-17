#!/usr/bin/env bash
# Transactionally switch immutable code-release pointers before runtime cutover.
set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${QWEN38_UPDATE_STATE_FILE:-${STATE_HOME}/update-transition.env}"
RELEASES_DIR="${QWEN38_RELEASES_DIR:-${DATA_HOME}/releases}"
CURRENT_LINK="${QWEN38_CURRENT_RELEASE_LINK:-${DATA_HOME}/current}"
PREVIOUS_LINK="${QWEN38_PREVIOUS_RELEASE_LINK:-${DATA_HOME}/previous}"
QUALIFIED_DIR="${QWEN38_QUALIFIED_DIR:-${DATA_HOME}/qualified}"
RELEASE_MANAGER="${SCRIPT_ROOT}/scripts/release-manager.sh"
STATE_PARSER="${SCRIPT_ROOT}/scripts/lib/state_file.py"
OPERATION_LOCK_LIB="${SCRIPT_ROOT}/scripts/lib/operation-lock.sh"

usage() {
  printf 'Usage: %s prepare RELEASE_ID|commit|rollback|recover|status\n' "$0"
}
die() { printf 'FATAL: %s\n' "$*" >&2; exit 1; }
validate_release_id() { [[ "$1" =~ ^[0-9a-f]{12,40}$ ]] || die "invalid release id: $1"; }
read_link_id() {
  local link="$1" target
  [[ -L "${link}" ]] || return 1
  target="$(readlink -f -- "${link}")"
  [[ "${target}" == "${RELEASES_DIR}/"* ]] || die "unsafe release pointer: ${link}"
  basename -- "${target}"
}
atomic_link() {
  local target link tmp
  target="$1"
  link="$2"
  tmp="${link}.tmp.$$"
  mkdir -p -- "$(dirname -- "${link}")"
  ln -s -- "${target}" "${tmp}"
  mv -Tf -- "${tmp}" "${link}"
}
clear_link() { [[ ! -e "$1" && ! -L "$1" ]] || rm -f -- "$1"; }
parse_state_into_vars() {
  local schema="$1" path="$2" parsed key value
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" "${schema}" "${path}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    printf -v "${key}" '%s' "${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
}
write_state() {
  local phase="$1" target="$2" old_current="$3" old_previous="$4"
  mkdir -p -- "${STATE_HOME}"; umask 077
  {
    printf 'UPDATE_SCHEMA_VERSION=%s\n' 1
    printf 'UPDATE_STATE=%s\n' "${phase}"
    printf 'TARGET_RELEASE=%s\n' "${target}"
    printf 'OLD_CURRENT_RELEASE=%s\n' "${old_current}"
    printf 'OLD_PREVIOUS_RELEASE=%s\n' "${old_previous}"
    printf 'UPDATED_AT=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  } >"${STATE_FILE}.tmp"
  mv -- "${STATE_FILE}.tmp" "${STATE_FILE}"
}
load_state() {
  [[ -r "${STATE_FILE}" ]] || die 'no update transition is active'
  unset UPDATE_SCHEMA_VERSION UPDATE_STATE TARGET_RELEASE OLD_CURRENT_RELEASE OLD_PREVIOUS_RELEASE UPDATED_AT
  parse_state_into_vars update "${STATE_FILE}" || die 'invalid update transition state file'
}
verify_qualified() {
  local release_id marker
  release_id="$1"
  marker="${QUALIFIED_DIR}/${release_id}.env"
  bash "${RELEASE_MANAGER}" verify "${release_id}"
  [[ -f "${marker}" && ! -L "${marker}" ]] || die "release is not qualified: ${release_id}"
  unset QUALIFICATION_SCHEMA_VERSION QUALIFIED_RELEASE QUALIFIED_AT
  parse_state_into_vars qualification "${marker}" || die "invalid qualification marker: ${release_id}"
  [[ "${QUALIFIED_RELEASE}" == "${release_id}" ]] || die "qualification marker mismatch: ${release_id}"
}
restore_pointer() {
  local link="$1" release_id="$2"
  if [[ -n "${release_id}" ]]; then
    bash "${RELEASE_MANAGER}" verify "${release_id}" >/dev/null
    atomic_link "${RELEASES_DIR}/${release_id}" "${link}"
  else
    clear_link "${link}"
  fi
}
restore_old_pointers() {
  restore_pointer "${CURRENT_LINK}" "${OLD_CURRENT_RELEASE:-}"
  restore_pointer "${PREVIOUS_LINK}" "${OLD_PREVIOUS_RELEASE:-}"
}
acquire_transition_lock() {
  local label="$1"
  [[ -r "${OPERATION_LOCK_LIB}" ]] || die "operation lock helper is unavailable: ${OPERATION_LOCK_LIB}"
  # shellcheck source=scripts/lib/operation-lock.sh
  source "${OPERATION_LOCK_LIB}"
  acquire_operation_lock "${STATE_HOME}" "${label}" || exit $?
}

[[ $# -ge 1 ]] || { usage >&2; exit 2; }
action="$1"; shift

case "${action}" in
  prepare)
    [[ $# -eq 1 ]] || { usage >&2; exit 2; }
    acquire_transition_lock "update transition prepare"
    [[ ! -e "${STATE_FILE}" ]] || die 'an update transition is already active'
    target="$1"; validate_release_id "${target}"; verify_qualified "${target}"
    old_current="$(read_link_id "${CURRENT_LINK}" 2>/dev/null || true)"
    old_previous="$(read_link_id "${PREVIOUS_LINK}" 2>/dev/null || true)"
    write_state preparing "${target}" "${old_current}" "${old_previous}"
    bash "${RELEASE_MANAGER}" activate "${target}"
    write_state staged "${target}" "${old_current}" "${old_previous}"
    printf 'Update release staged for runtime cutover: %s\n' "${target}"
    ;;
  commit)
    [[ $# -eq 0 ]] || { usage >&2; exit 2; }
    acquire_transition_lock "update transition commit"
    load_state
    [[ "${UPDATE_STATE:-}" == staged ]] || die "cannot commit update state: ${UPDATE_STATE:-unknown}"
    current="$(read_link_id "${CURRENT_LINK}" 2>/dev/null || true)"
    [[ "${current}" == "${TARGET_RELEASE}" ]] || die 'current release no longer matches target'
    verify_qualified "${TARGET_RELEASE}"
    rm -f -- "${STATE_FILE}" "${STATE_FILE}.tmp"
    printf 'Update release committed: %s\n' "${TARGET_RELEASE}"
    ;;
  rollback)
    [[ $# -eq 0 ]] || { usage >&2; exit 2; }
    acquire_transition_lock "update transition rollback"
    load_state
    restore_old_pointers
    rm -f -- "${STATE_FILE}" "${STATE_FILE}.tmp"
    printf 'Update release pointers rolled back.\n'
    ;;
  recover)
    [[ $# -eq 0 ]] || { usage >&2; exit 2; }
    acquire_transition_lock "update transition recover"
    if [[ ! -e "${STATE_FILE}" ]]; then
      printf 'UPDATE_STATE=idle\n'
      exit 0
    fi
    load_state
    restore_old_pointers
    rm -f -- "${STATE_FILE}" "${STATE_FILE}.tmp"
    printf 'Interrupted update transition recovered to previous pointers.\n'
    ;;
  status)
    [[ $# -eq 0 ]] || { usage >&2; exit 2; }
    if [[ -r "${STATE_FILE}" ]]; then cat "${STATE_FILE}"; else printf 'UPDATE_STATE=idle\n'; fi
    ;;
  -h|--help) usage ;;
  *) usage >&2; exit 2 ;;
esac
