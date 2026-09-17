#!/usr/bin/env bash
# Shared advisory lock for lifecycle mutations that must not overlap.

operation_lock_die() {
  printf 'ERROR: %s\n' "$*" >&2
  return 1
}

acquire_operation_lock() {
  local state_dir="$1" label="${2:-lifecycle operation}" owner_uid="${3:-$(id -u)}" owner_gid="${4:-$(id -g)}"
  local lock_file probe_fd current_uid

  command -v flock >/dev/null 2>&1 || operation_lock_die "flock is required for lifecycle locking" || return 1
  command -v stat >/dev/null 2>&1 || operation_lock_die "stat is required for lifecycle locking" || return 1

  mkdir -p -- "${state_dir}" || return 1
  lock_file="${QWEN38_OPERATION_LOCK_FILE:-${state_dir}/operation.lock}"
  [[ "${lock_file}" == /* ]] || operation_lock_die "operation lock path must be absolute: ${lock_file}" || return 1
  [[ ! -L "${lock_file}" ]] || operation_lock_die "refusing symlinked operation lock: ${lock_file}" || return 1

  if [[ ! -e "${lock_file}" ]]; then
    if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
      command -v install >/dev/null 2>&1 || operation_lock_die "install is required to create the lifecycle lock" || return 1
      install -o "${owner_uid}" -g "${owner_gid}" -m 0600 /dev/null "${lock_file}" || return 1
    else
      (umask 077; : >"${lock_file}") || return 1
    fi
  fi
  [[ -f "${lock_file}" && ! -L "${lock_file}" ]] || operation_lock_die "operation lock is not a regular file: ${lock_file}" || return 1
  current_uid="$(stat -c %u "${lock_file}")"
  [[ "${current_uid}" == "${owner_uid}" ]] || operation_lock_die "operation lock is not owned by expected uid ${owner_uid}: ${lock_file}" || return 1

  if [[ "${QWEN38_OPERATION_LOCK_HELD:-0}" == 1 ]]; then
    [[ "${QWEN38_OPERATION_LOCK_FILE:-}" == "${lock_file}" ]] || operation_lock_die "inherited lifecycle lock path mismatch" || return 1
    exec {probe_fd}<>"${lock_file}" || return 1
    if flock -n "${probe_fd}"; then
      flock -u "${probe_fd}" || true
      exec {probe_fd}>&-
      operation_lock_die "inherited lifecycle lock marker is set but no outer lock is held" || return 1
    fi
    exec {probe_fd}>&-
    return 0
  fi

  exec {QWEN38_OPERATION_LOCK_FD}<>"${lock_file}" || return 1
  if ! flock -n "${QWEN38_OPERATION_LOCK_FD}"; then
    operation_lock_die "another Qwen3.8 lifecycle operation is active; retry after it finishes (${lock_file})" || return 1
  fi
  QWEN38_OPERATION_LOCK_HELD=1
  QWEN38_OPERATION_LOCK_FILE="${lock_file}"
  export QWEN38_OPERATION_LOCK_HELD QWEN38_OPERATION_LOCK_FILE
  printf 'Lifecycle operation lock acquired: %s (%s)\n' "${label}" "${lock_file}" >&2
}
