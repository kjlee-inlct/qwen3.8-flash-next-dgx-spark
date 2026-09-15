#!/usr/bin/env bash
# Transactionally preserve the current runtime container while a replacement is validated.
set -euo pipefail

CONTAINER="${CONTAINER_NAME:-qwen38-flash-next}"
ROLLBACK_CONTAINER="${ROLLBACK_CONTAINER_NAME:-${CONTAINER}.rollback}"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/runtime-transition.env"

usage() {
  printf 'Usage: %s prepare|candidate-started|validating|commit|rollback|recover|status\n' "$0"
}
die() { printf 'FATAL: %s\n' "$*" >&2; exit 1; }
container_exists() { docker inspect "$1" >/dev/null 2>&1; }
container_running() { [[ "$(docker inspect -f '{{.State.Running}}' "$1" 2>/dev/null || true)" == true ]]; }
write_state() {
  local phase="$1" had_previous="$2"
  mkdir -p "${STATE_DIR}"
  umask 077
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
clear_state() { rm -f -- "${STATE_FILE}" "${STATE_FILE}.tmp"; }
load_state() {
  local expected_container="${CONTAINER}"
  local expected_rollback_container="${ROLLBACK_CONTAINER}"
  [[ -r "${STATE_FILE}" ]] || die 'no runtime transition is active'
  # shellcheck disable=SC1090
  source "${STATE_FILE}"
  [[ "${RUNTIME_SCHEMA_VERSION:-}" == 1 ]] || die 'unsupported runtime transition schema'
  [[ "${CURRENT_CONTAINER:-}" == "${expected_container}" ]] || die 'runtime transition current-container mismatch'
  [[ "${ROLLBACK_CONTAINER:-}" == "${expected_rollback_container}" ]] || die 'runtime transition rollback-container mismatch'
  [[ "${HAD_PREVIOUS:-}" == 0 || "${HAD_PREVIOUS:-}" == 1 ]] || die 'invalid HAD_PREVIOUS in runtime transition state'
  # The state file is descriptive, not authoritative for which Docker objects this
  # invocation is allowed to mutate. Restore the validated invocation-scoped names.
  CONTAINER="${expected_container}"
  ROLLBACK_CONTAINER="${expected_rollback_container}"
}
restore_previous() {
  container_exists "${ROLLBACK_CONTAINER}" || die "rollback container is missing: ${ROLLBACK_CONTAINER}"
  if container_exists "${CONTAINER}"; then
    docker rm -f "${CONTAINER}" >/dev/null
  fi
  docker rename "${ROLLBACK_CONTAINER}" "${CONTAINER}"
  if ! container_running "${CONTAINER}"; then
    docker start "${CONTAINER}" >/dev/null
  fi
  printf 'Previous runtime container restored and started.\n'
}

[[ $# == 1 ]] || { usage >&2; exit 2; }
command -v docker >/dev/null 2>&1 || die 'docker is required'
case "$1" in
  prepare)
    [[ ! -e "${STATE_FILE}" ]] || die 'runtime transition state already exists; run recover first'
    container_exists "${ROLLBACK_CONTAINER}" && die "stale rollback container exists: ${ROLLBACK_CONTAINER}; run recover first"
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
    write_state previous_preserved "${had_previous}"
    printf 'Runtime transition prepared (previous=%s).\n' "${had_previous}"
    ;;
  candidate-started)
    load_state
    [[ "${TRANSACTION_STATE:-}" == previous_preserved ]] || die "unexpected transition state: ${TRANSACTION_STATE:-missing}"
    container_running "${CONTAINER}" || die "candidate container is not running: ${CONTAINER}"
    write_state candidate_started "${HAD_PREVIOUS}"
    ;;
  validating)
    load_state
    [[ "${TRANSACTION_STATE:-}" == candidate_started ]] || die "unexpected transition state: ${TRANSACTION_STATE:-missing}"
    container_running "${CONTAINER}" || die "candidate container is not running: ${CONTAINER}"
    write_state validating "${HAD_PREVIOUS}"
    ;;
  commit)
    load_state
    [[ "${TRANSACTION_STATE:-}" == validating ]] || die "unexpected transition state: ${TRANSACTION_STATE:-missing}"
    container_running "${CONTAINER}" || die "candidate container is not running: ${CONTAINER}"
    if [[ "${HAD_PREVIOUS}" == 1 ]]; then
      container_exists "${ROLLBACK_CONTAINER}" || die 'rollback container disappeared before commit'
      docker rm -f "${ROLLBACK_CONTAINER}" >/dev/null
    fi
    clear_state
    printf 'Runtime transition committed.\n'
    ;;
  rollback)
    [[ -r "${STATE_FILE}" ]] || { printf 'No runtime transition to roll back.\n'; exit 0; }
    load_state
    write_state rolling_back "${HAD_PREVIOUS}"
    if [[ "${HAD_PREVIOUS}" == 1 ]]; then
      restore_previous
    else
      if container_exists "${CONTAINER}"; then
        docker rm -f "${CONTAINER}" >/dev/null
      fi
    fi
    clear_state
    ;;
  recover)
    current_exists=0
    rollback_exists=0
    container_exists "${CONTAINER}" && current_exists=1
    container_exists "${ROLLBACK_CONTAINER}" && rollback_exists=1

    if [[ ! -r "${STATE_FILE}" ]]; then
      if [[ "${current_exists}" == 0 && "${rollback_exists}" == 1 ]]; then
        printf 'Recovering orphaned rollback container.\n' >&2
        docker rename "${ROLLBACK_CONTAINER}" "${CONTAINER}"
        container_running "${CONTAINER}" || docker start "${CONTAINER}" >/dev/null
      elif [[ "${current_exists}" == 1 && "${rollback_exists}" == 1 ]]; then
        die 'both current and rollback containers exist without transaction state; refusing ambiguous recovery'
      fi
      printf 'Runtime transition recovery complete (state=idle).\n'
      exit 0
    fi

    load_state
    printf 'Recovering interrupted runtime transition (state=%s, previous=%s).\n' "${TRANSACTION_STATE:-unknown}" "${HAD_PREVIOUS}"
    if [[ "${HAD_PREVIOUS}" == 1 ]]; then
      current_exists=0
      rollback_exists=0
      container_exists "${CONTAINER}" && current_exists=1
      container_exists "${ROLLBACK_CONTAINER}" && rollback_exists=1
      if [[ "${rollback_exists}" == 1 ]]; then
        restore_previous
      elif [[ "${current_exists}" == 1 && "${TRANSACTION_STATE:-}" == preparing ]]; then
        # The interruption happened before rename. The original container still owns the canonical name.
        container_running "${CONTAINER}" || docker start "${CONTAINER}" >/dev/null
        printf 'Original runtime container recovered before preservation completed.\n'
      else
        die 'cannot recover previous runtime: rollback container is unavailable'
      fi
    else
      # There was no previous known-good runtime. Remove any uncommitted candidate.
      if container_exists "${CONTAINER}"; then
        docker rm -f "${CONTAINER}" >/dev/null
      fi
      container_exists "${ROLLBACK_CONTAINER}" && die 'unexpected rollback container exists for a no-previous transaction'
    fi
    clear_state
    printf 'Runtime transition recovery complete (state=idle).\n'
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
