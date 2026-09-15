#!/usr/bin/env bash
# Transactionally preserve the current runtime container while a replacement is validated.
set -euo pipefail

CONTAINER="${CONTAINER_NAME:-qwen38-flash-next}"
ROLLBACK_CONTAINER="${ROLLBACK_CONTAINER_NAME:-${CONTAINER}.rollback}"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/runtime-transition.env"

usage() {
  printf 'Usage: %s prepare|commit|rollback|status\n' "$0"
}
die() { printf 'FATAL: %s\n' "$*" >&2; exit 1; }
container_exists() { docker inspect "$1" >/dev/null 2>&1; }
container_running() { [[ "$(docker inspect -f '{{.State.Running}}' "$1" 2>/dev/null || true)" == true ]]; }
write_state() {
  local phase="$1" had_previous="$2"
  mkdir -p "${STATE_DIR}"; umask 077
  {
    printf 'RUNTIME_SCHEMA_VERSION=%q\n' 1
    printf 'TRANSACTION_STATE=%q\n' "${phase}"
    printf 'CURRENT_CONTAINER=%q\n' "${CONTAINER}"
    printf 'ROLLBACK_CONTAINER=%q\n' "${ROLLBACK_CONTAINER}"
    printf 'HAD_PREVIOUS=%q\n' "${had_previous}"
    printf 'UPDATED_AT=%q\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  } >"${STATE_FILE}.tmp"
  mv -- "${STATE_FILE}.tmp" "${STATE_FILE}"
}
clear_state() { rm -f -- "${STATE_FILE}"; }

[[ $# == 1 ]] || { usage >&2; exit 2; }
command -v docker >/dev/null 2>&1 || die 'docker is required'
case "$1" in
  prepare)
    container_exists "${ROLLBACK_CONTAINER}" && die "stale rollback container exists: ${ROLLBACK_CONTAINER}"
    had_previous=0
    if container_exists "${CONTAINER}"; then
      had_previous=1
      write_state preparing "${had_previous}"
      if container_running "${CONTAINER}"; then
        printf 'Stopping current runtime container gracefully: %s\n' "${CONTAINER}"
        docker stop --timeout 30 "${CONTAINER}" >/dev/null
      fi
      docker rename "${CONTAINER}" "${ROLLBACK_CONTAINER}"
    fi
    write_state prepared "${had_previous}"
    printf 'Runtime transition prepared (previous=%s).\n' "${had_previous}"
    ;;
  commit)
    [[ -r "${STATE_FILE}" ]] || die 'no runtime transition is active'
    # shellcheck disable=SC1090
    source "${STATE_FILE}"
    [[ "${TRANSACTION_STATE:-}" == prepared ]] || die "unexpected transition state: ${TRANSACTION_STATE:-missing}"
    container_running "${CONTAINER}" || die "candidate container is not running: ${CONTAINER}"
    if [[ "${HAD_PREVIOUS:-0}" == 1 ]]; then
      container_exists "${ROLLBACK_CONTAINER}" || die 'rollback container disappeared before commit'
      docker rm -f "${ROLLBACK_CONTAINER}" >/dev/null
    fi
    clear_state
    printf 'Runtime transition committed.\n'
    ;;
  rollback)
    [[ -r "${STATE_FILE}" ]] || { printf 'No runtime transition to roll back.\n'; exit 0; }
    # shellcheck disable=SC1090
    source "${STATE_FILE}"
    write_state rolling_back "${HAD_PREVIOUS:-0}"
    if container_exists "${CONTAINER}"; then
      docker rm -f "${CONTAINER}" >/dev/null || true
    fi
    if [[ "${HAD_PREVIOUS:-0}" == 1 ]]; then
      container_exists "${ROLLBACK_CONTAINER}" || die "rollback container is missing: ${ROLLBACK_CONTAINER}"
      docker rename "${ROLLBACK_CONTAINER}" "${CONTAINER}"
      docker start "${CONTAINER}" >/dev/null
      printf 'Previous runtime container restored and started.\n'
    fi
    clear_state
    ;;
  status)
    if [[ -r "${STATE_FILE}" ]]; then
      cat "${STATE_FILE}"
    else
      printf 'TRANSACTION_STATE=idle\n'
    fi
    ;;
  *) usage >&2; exit 2 ;;
esac
