#!/usr/bin/env bash
# Persist and recover managed model-profile switches across process or host interruption.
set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
INSTALL_STATE_FILE="${QWEN38_STATE_FILE:-${STATE_HOME}/install.env}"
STATE_FILE="${QWEN38_PROFILE_SWITCH_STATE_FILE:-${STATE_HOME}/profile-switch-transition.env}"
BACKUP_MANIFEST_DEFAULT="${INSTALL_STATE_FILE}.profile-switch-backup"
TARGET_MANIFEST_DEFAULT="${INSTALL_STATE_FILE}.profile-switch-candidate"
RUNTIME_TRANSITION_FILE="${QWEN38_RUNTIME_TRANSITION_STATE_FILE:-${STATE_HOME}/runtime-transition.env}"
RUNTIME_COMMIT_FILE="${QWEN38_RUNTIME_COMMIT_FILE:-${STATE_HOME}/runtime-commit.env}"
RUNTIME_TRANSITION="${QWEN38_RUNTIME_TRANSITION_HELPER:-${SCRIPT_ROOT}/scripts/runtime/runtime-transition.sh}"
CURRENT_RELEASE_LINK="${QWEN38_CURRENT_RELEASE_LINK:-${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark/current}"
STATE_PARSER="${SCRIPT_ROOT}/scripts/lib/state_file.py"
OPERATION_LOCK_LIB="${SCRIPT_ROOT}/scripts/lib/operation-lock.sh"

usage() {
  printf 'Usage: %s prepare FROM_PROFILE TO_PROFILE|activate|runtime-committed|commit|rollback|recover|service-recover|status\n' "$0"
}
die() { printf 'FATAL: %s\n' "$*" >&2; exit 1; }

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

parse_manifest_runtime() {
  local path="$1" prefix="$2" parsed key value
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" install-service-runtime "${path}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    printf -v "${prefix}_${key}" '%s' "${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
}

parse_manifest_maintenance() {
  local path="$1" prefix="$2" parsed key value
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" install-maintenance "${path}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    printf -v "${prefix}_${key}" '%s' "${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
}

sha256_file() {
  python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$1"
}

write_state() {
  local phase="$1" from_profile="$2" to_profile="$3" backup="$4" target="$5" backup_sha="$6" target_sha="$7"
  mkdir -p -- "${STATE_HOME}"
  umask 077
  {
    printf 'PROFILE_SWITCH_SCHEMA_VERSION=1\n'
    printf 'PROFILE_SWITCH_STATE=%s\n' "${phase}"
    printf 'FROM_PROFILE=%s\n' "${from_profile}"
    printf 'TO_PROFILE=%s\n' "${to_profile}"
    printf 'BACKUP_MANIFEST=%s\n' "${backup}"
    printf 'TARGET_MANIFEST=%s\n' "${target}"
    printf 'BACKUP_SHA256=%s\n' "${backup_sha}"
    printf 'TARGET_SHA256=%s\n' "${target_sha}"
    printf 'UPDATED_AT=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  } >"${STATE_FILE}.tmp"
  python3 "${STATE_PARSER}" profile-switch "${STATE_FILE}.tmp" >/dev/null
  mv -- "${STATE_FILE}.tmp" "${STATE_FILE}"
}

load_state() {
  [[ -f "${STATE_FILE}" && ! -L "${STATE_FILE}" ]] || die 'no profile-switch transition is active'
  unset PROFILE_SWITCH_SCHEMA_VERSION PROFILE_SWITCH_STATE FROM_PROFILE TO_PROFILE
  unset BACKUP_MANIFEST TARGET_MANIFEST BACKUP_SHA256 TARGET_SHA256 UPDATED_AT
  parse_state_into_vars profile-switch "${STATE_FILE}" || die "invalid profile-switch transition state: ${STATE_FILE}"
  [[ "${BACKUP_MANIFEST}" == "${BACKUP_MANIFEST_DEFAULT}" ]] || die 'profile-switch backup path does not match the installation manifest'
  [[ "${TARGET_MANIFEST}" == "${TARGET_MANIFEST_DEFAULT}" ]] || die 'profile-switch candidate path does not match the installation manifest'
}

clear_state() { rm -f -- "${STATE_FILE}" "${STATE_FILE}.tmp"; }

atomic_copy() {
  local source="$1" destination="$2"
  [[ -f "${source}" && ! -L "${source}" ]] || die "unsafe or missing source file: ${source}"
  cp -p -- "${source}" "${destination}.tmp"
  mv -- "${destination}.tmp" "${destination}"
}

acquire_transition_lock() {
  local label="$1"
  [[ -r "${OPERATION_LOCK_LIB}" ]] || die "operation lock helper is unavailable: ${OPERATION_LOCK_LIB}"
  # shellcheck source=scripts/lib/operation-lock.sh
  source "${OPERATION_LOCK_LIB}"
  acquire_operation_lock "${STATE_HOME}" "${label}" || exit $?
}

operation_lock_busy() {
  local lock_file="${QWEN38_OPERATION_LOCK_FILE:-${STATE_HOME}/operation.lock}" probe_fd
  [[ -f "${lock_file}" && ! -L "${lock_file}" ]] || return 1
  command -v flock >/dev/null 2>&1 || return 1
  exec {probe_fd}<>"${lock_file}" || return 1
  if flock -n "${probe_fd}"; then
    flock -u "${probe_fd}" || true
    exec {probe_fd}>&-
    return 1
  fi
  exec {probe_fd}>&-
  return 0
}

# Compare runtime-relevant fields through the strict parser; PHASE may differ after recovery finalizes the target.\nmanifest_runtime_equal() {
  python3 - "${STATE_PARSER}" "$1" "$2" <<'PY'
import importlib.util
import pathlib
import sys

spec = importlib.util.spec_from_file_location("qwen38_state_file", sys.argv[1])
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
left = module.parse_install(pathlib.Path(sys.argv[2]), "install-service-runtime")
right = module.parse_install(pathlib.Path(sys.argv[3]), "install-service-runtime")
left.pop("PHASE", None)
right.pop("PHASE", None)
raise SystemExit(0 if left == right else 1)
PY
}

container_matches_manifest() {
  local manifest="$1" image model_mount cmd served_name expected_model actual_model
  command -v docker >/dev/null 2>&1 || return 1
  parse_manifest_runtime "${manifest}" MATCH || return 1
  docker inspect "${MATCH_CONTAINER_NAME}" >/dev/null 2>&1 || return 1
  image="$(docker inspect --format '{{.Config.Image}}' "${MATCH_CONTAINER_NAME}" 2>/dev/null || true)"
  [[ "${image}" == "${MATCH_VLLM_IMAGE}" ]] || return 1
  model_mount="$(docker inspect --format '{{range .Mounts}}{{if eq .Destination "/model"}}{{.Source}}{{end}}{{end}}' "${MATCH_CONTAINER_NAME}" 2>/dev/null || true)"
  expected_model="$(realpath -m -- "${MATCH_MODEL_DIR}")"
  actual_model=""
  [[ -z "${model_mount}" ]] || actual_model="$(realpath -m -- "${model_mount}")"
  [[ -n "${actual_model}" && "${actual_model}" == "${expected_model}" ]] || return 1
  cmd="$(docker inspect --format '{{json .Config.Cmd}}' "${MATCH_CONTAINER_NAME}" 2>/dev/null || true)"
  served_name="$(python3 -c 'import json,sys; cmd=json.loads(sys.stdin.read()); i=cmd.index("--served-model-name"); print(cmd[i+1])' <<<"${cmd}" 2>/dev/null || true)"
  [[ "${served_name}" == "${MATCH_SERVED_NAME}" ]]
}

runtime_attestation_matches_current() {
  local current_id current_root
  [[ -f "${RUNTIME_COMMIT_FILE}" && ! -L "${RUNTIME_COMMIT_FILE}" ]] || return 1
  unset RUNTIME_COMMIT_SCHEMA_VERSION RUNTIME_ROOT RUNTIME_CONTAINER_NAME RUNTIME_CONTAINER_ID COMMITTED_AT
  parse_state_into_vars runtime-commit "${RUNTIME_COMMIT_FILE}" || return 1
  [[ "${RUNTIME_CONTAINER_NAME}" == qwen38-flash-next ]] || return 1
  current_id="$(docker inspect --format '{{.Id}}' "${RUNTIME_CONTAINER_NAME}" 2>/dev/null || true)"
  [[ -n "${current_id}" && "${current_id}" == "${RUNTIME_CONTAINER_ID}" ]] || return 1
  [[ -L "${CURRENT_RELEASE_LINK}" ]] || return 1
  current_root="$(readlink -f -- "${CURRENT_RELEASE_LINK}" 2>/dev/null || true)"
  [[ -n "${current_root}" && "${current_root}" == "${RUNTIME_ROOT}" ]]
}

target_runtime_committed() {
  [[ -f "${INSTALL_STATE_FILE}" && ! -L "${INSTALL_STATE_FILE}" ]] || return 1
  parse_manifest_runtime "${INSTALL_STATE_FILE}" LIVE || return 1
  [[ "${LIVE_MODEL_PROFILE}" == "${TO_PROFILE}" ]] || return 1
  if [[ -f "${TARGET_MANIFEST}" && ! -L "${TARGET_MANIFEST}" ]]; then
    manifest_runtime_equal "${INSTALL_STATE_FILE}" "${TARGET_MANIFEST}" || return 1
    [[ -z "${TARGET_SHA256}" || "$(sha256_file "${TARGET_MANIFEST}")" == "${TARGET_SHA256}" ]] || return 1
  elif [[ "${PROFILE_SWITCH_STATE}" != committing ]]; then
    return 1
  fi
  container_matches_manifest "${INSTALL_STATE_FILE}" || return 1
  runtime_attestation_matches_current
}

set_live_manifest_complete() {
  local temporary="${INSTALL_STATE_FILE}.profile-switch-complete.tmp"
  python3 - "${INSTALL_STATE_FILE}" "${temporary}" <<'PY'
import pathlib
import sys

source = pathlib.Path(sys.argv[1])
target = pathlib.Path(sys.argv[2])
lines = source.read_text(encoding="utf-8").splitlines()
matches = [i for i, line in enumerate(lines) if line.startswith("PHASE=")]
if len(matches) != 1:
    raise SystemExit("installation manifest must contain exactly one PHASE field")
lines[matches[0]] = "PHASE=complete"
target.write_text("\n".join(lines) + "\n", encoding="utf-8")
target.chmod(source.stat().st_mode & 0o777)
PY
  python3 "${STATE_PARSER}" install-runtime "${temporary}" >/dev/null
  mv -- "${temporary}" "${INSTALL_STATE_FILE}"
}

restore_backup_manifest() {
  [[ -f "${BACKUP_MANIFEST}" && ! -L "${BACKUP_MANIFEST}" ]] || die "profile-switch backup manifest is unavailable: ${BACKUP_MANIFEST}"
  parse_manifest_runtime "${BACKUP_MANIFEST}" BACKUP || die 'profile-switch backup manifest failed strict parsing'
  [[ "${BACKUP_MODEL_PROFILE}" == "${FROM_PROFILE}" ]] || die 'profile-switch backup profile does not match FROM_PROFILE'
  [[ -z "${BACKUP_SHA256}" || "$(sha256_file "${BACKUP_MANIFEST}")" == "${BACKUP_SHA256}" ]] || die 'profile-switch backup digest mismatch'
  atomic_copy "${BACKUP_MANIFEST}" "${INSTALL_STATE_FILE}"
}

finish_target_commit() {
  target_runtime_committed || die 'target runtime commit cannot be proven; refusing profile-switch commit'
  set_live_manifest_complete
  write_state committing "${FROM_PROFILE}" "${TO_PROFILE}" "${BACKUP_MANIFEST}" "${TARGET_MANIFEST}" "${BACKUP_SHA256}" "${TARGET_SHA256}"
  rm -f -- "${TARGET_MANIFEST}" "${TARGET_MANIFEST}.tmp" "${BACKUP_MANIFEST}"
  clear_state
  printf 'Profile switch committed and recovered to a complete target manifest (%s).\n' "${TO_PROFILE}"
}

rollback_to_previous() {
  if [[ -e "${RUNTIME_TRANSITION_FILE}" || -L "${RUNTIME_TRANSITION_FILE}" ]]; then
    [[ -r "${RUNTIME_TRANSITION}" ]] || die "runtime transition helper is unavailable: ${RUNTIME_TRANSITION}"
    bash "${RUNTIME_TRANSITION}" recover
  fi
  if [[ -f "${BACKUP_MANIFEST}" && ! -L "${BACKUP_MANIFEST}" ]]; then
    container_matches_manifest "${BACKUP_MANIFEST}" || die 'previous runtime cannot be proven from the backup manifest; refusing ambiguous rollback'
    restore_backup_manifest
  else
    parse_manifest_maintenance "${INSTALL_STATE_FILE}" CURRENT || die 'live installation manifest failed strict maintenance parsing'
    [[ "${CURRENT_MODEL_PROFILE}" == "${FROM_PROFILE}" ]] || die 'backup is missing and live manifest is not the previous profile'
  fi
  rm -f -- "${TARGET_MANIFEST}" "${TARGET_MANIFEST}.tmp" "${BACKUP_MANIFEST}"
  clear_state
  printf 'Profile switch rolled back to previous profile (%s).\n' "${FROM_PROFILE}"
}

recover_transition() {
  load_state
  case "${PROFILE_SWITCH_STATE}" in
    preparing)
      if [[ -f "${BACKUP_MANIFEST}" && ! -L "${BACKUP_MANIFEST}" ]]; then
        restore_backup_manifest
      else
        parse_manifest_maintenance "${INSTALL_STATE_FILE}" CURRENT || die 'live installation manifest failed strict maintenance parsing'
        [[ "${CURRENT_MODEL_PROFILE}" == "${FROM_PROFILE}" ]] || die 'preparing recovery found neither a usable backup nor the previous live manifest'
      fi
      rm -f -- "${TARGET_MANIFEST}" "${TARGET_MANIFEST}.tmp" "${BACKUP_MANIFEST}"
      clear_state
      printf 'Interrupted profile switch recovered before activation (%s).\n' "${FROM_PROFILE}"
      ;;
    activated)
      if target_runtime_committed; then
        write_state runtime_committed "${FROM_PROFILE}" "${TO_PROFILE}" "${BACKUP_MANIFEST}" "${TARGET_MANIFEST}" "${BACKUP_SHA256}" "${TARGET_SHA256}"
        PROFILE_SWITCH_STATE=runtime_committed
        finish_target_commit
      else
        rollback_to_previous
      fi
      ;;
    runtime_committed|committing)
      finish_target_commit
      ;;
    *)
      die "unsupported profile-switch transition state: ${PROFILE_SWITCH_STATE}"
      ;;
  esac
}

[[ -r "${STATE_PARSER}" ]] || die "strict state parser is unavailable: ${STATE_PARSER}"
[[ $# -ge 1 ]] || { usage >&2; exit 2; }
action="$1"; shift

case "${action}" in
  prepare)
    [[ $# -eq 2 ]] || { usage >&2; exit 2; }
    acquire_transition_lock "profile switch prepare"
    [[ ! -e "${STATE_FILE}" && ! -L "${STATE_FILE}" ]] || die 'a profile-switch transition is already active; recover it first'
    [[ ! -e "${BACKUP_MANIFEST_DEFAULT}" && ! -L "${BACKUP_MANIFEST_DEFAULT}" ]] || die "stale profile-switch backup exists: ${BACKUP_MANIFEST_DEFAULT}"
    [[ ! -e "${TARGET_MANIFEST_DEFAULT}" && ! -L "${TARGET_MANIFEST_DEFAULT}" ]] || die "stale profile-switch candidate exists: ${TARGET_MANIFEST_DEFAULT}"
    parse_manifest_maintenance "${INSTALL_STATE_FILE}" CURRENT || die 'installation manifest failed strict maintenance parsing'
    [[ "${CURRENT_MODEL_PROFILE}" == "$1" ]] || die "FROM_PROFILE does not match live manifest: $1"
    [[ "${CURRENT_PHASE}" == complete ]] || die "profile switch requires a complete live installation manifest (found ${CURRENT_PHASE})"
    [[ "$1" != "$2" ]] || die 'profile switch source and target must differ'
    write_state preparing "$1" "$2" "${BACKUP_MANIFEST_DEFAULT}" "${TARGET_MANIFEST_DEFAULT}" "" ""
    printf 'Profile switch transaction prepared: %s -> %s\n' "$1" "$2"
    ;;
  activate)
    [[ $# -eq 0 ]] || { usage >&2; exit 2; }
    acquire_transition_lock "profile switch activate"
    load_state
    [[ "${PROFILE_SWITCH_STATE}" == preparing ]] || die "cannot activate profile-switch state: ${PROFILE_SWITCH_STATE}"
    parse_manifest_runtime "${TARGET_MANIFEST}" TARGET || die 'target candidate manifest is not service-ready'
    [[ "${TARGET_MODEL_PROFILE}" == "${TO_PROFILE}" ]] || die 'target candidate profile mismatch'
    [[ "${TARGET_PHASE}" == service_ready ]] || die "target candidate must be service_ready before activation (found ${TARGET_PHASE})"
    parse_manifest_maintenance "${INSTALL_STATE_FILE}" CURRENT || die 'live installation manifest failed strict maintenance parsing'
    [[ "${CURRENT_MODEL_PROFILE}" == "${FROM_PROFILE}" && "${CURRENT_PHASE}" == complete ]] || die 'live installation manifest changed before profile-switch activation'
    atomic_copy "${INSTALL_STATE_FILE}" "${BACKUP_MANIFEST}"
    backup_sha="$(sha256_file "${BACKUP_MANIFEST}")"
    target_sha="$(sha256_file "${TARGET_MANIFEST}")"
    atomic_copy "${TARGET_MANIFEST}" "${INSTALL_STATE_FILE}"
    write_state activated "${FROM_PROFILE}" "${TO_PROFILE}" "${BACKUP_MANIFEST}" "${TARGET_MANIFEST}" "${backup_sha}" "${target_sha}"
    printf 'Profile switch target manifest activated: %s\n' "${TO_PROFILE}"
    ;;
  runtime-committed)
    [[ $# -eq 0 ]] || { usage >&2; exit 2; }
    acquire_transition_lock "profile switch runtime committed"
    load_state
    [[ "${PROFILE_SWITCH_STATE}" == activated ]] || die "cannot mark runtime committed from state: ${PROFILE_SWITCH_STATE}"
    target_runtime_committed || die 'runtime commit attestation or target runtime does not match the activated profile'
    write_state runtime_committed "${FROM_PROFILE}" "${TO_PROFILE}" "${BACKUP_MANIFEST}" "${TARGET_MANIFEST}" "${BACKUP_SHA256}" "${TARGET_SHA256}"
    printf 'Profile switch runtime commit recorded: %s\n' "${TO_PROFILE}"
    ;;
  commit)
    [[ $# -eq 0 ]] || { usage >&2; exit 2; }
    acquire_transition_lock "profile switch commit"
    load_state
    [[ "${PROFILE_SWITCH_STATE}" == runtime_committed || "${PROFILE_SWITCH_STATE}" == committing ]] || die "cannot commit profile-switch state: ${PROFILE_SWITCH_STATE}"
    finish_target_commit
    ;;
  rollback)
    [[ $# -eq 0 ]] || { usage >&2; exit 2; }
    acquire_transition_lock "profile switch rollback"
    if [[ ! -e "${STATE_FILE}" ]]; then
      printf 'No profile-switch transition to roll back.\n'
      exit 0
    fi
    load_state
    case "${PROFILE_SWITCH_STATE}" in
      preparing)
        if [[ -f "${BACKUP_MANIFEST}" && ! -L "${BACKUP_MANIFEST}" ]]; then restore_backup_manifest; fi
        rm -f -- "${TARGET_MANIFEST}" "${TARGET_MANIFEST}.tmp" "${BACKUP_MANIFEST}"
        clear_state
        printf 'Profile switch rolled back before activation.\n'
        ;;
      activated)
        rollback_to_previous
        ;;
      runtime_committed|committing)
        die 'target runtime is already committed; use recover to finish the target profile instead of rolling back'
        ;;
    esac
    ;;
  recover)
    [[ $# -eq 0 ]] || { usage >&2; exit 2; }
    acquire_transition_lock "profile switch recover"
    if [[ ! -e "${STATE_FILE}" ]]; then
      [[ ! -e "${BACKUP_MANIFEST_DEFAULT}" && ! -e "${TARGET_MANIFEST_DEFAULT}" ]] || die 'profile-switch artifacts exist without transaction state; refusing ambiguous recovery'
      printf 'PROFILE_SWITCH_STATE=idle\n'
      exit 0
    fi
    recover_transition
    ;;
  service-recover)
    [[ $# -eq 0 ]] || { usage >&2; exit 2; }
    if [[ ! -e "${STATE_FILE}" ]]; then exit 0; fi
    if operation_lock_busy; then
      printf 'Profile-switch startup recovery deferred: installer lifecycle lock is active.\n'
      exit 0
    fi
    acquire_transition_lock "profile switch service startup recovery"
    recover_transition
    ;;
  status)
    [[ $# -eq 0 ]] || { usage >&2; exit 2; }
    if [[ -r "${STATE_FILE}" ]]; then
      python3 "${STATE_PARSER}" profile-switch "${STATE_FILE}" >/dev/null || die 'invalid profile-switch transition state'
      cat "${STATE_FILE}"
    else
      printf 'PROFILE_SWITCH_STATE=idle\n'
    fi
    ;;
  -h|--help) usage ;;
  *) usage >&2; exit 2 ;;
esac
