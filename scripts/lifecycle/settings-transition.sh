#!/usr/bin/env bash
# Transactionally apply settings-only changes to a complete managed installation.
# Manifests remain the source of truth and are parsed only through state_file.py.
set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
INSTALL_STATE_FILE="${QWEN38_STATE_FILE:-${STATE_HOME}/install.env}"
STATE_PARSER="${SCRIPT_ROOT}/scripts/lib/state_file.py"
OPERATION_LOCK_LIB="${SCRIPT_ROOT}/scripts/lib/operation-lock.sh"
PROFILE_SWITCH_STATE="${STATE_HOME}/profile-switch-transition.env"
UPDATE_STATE="${STATE_HOME}/update-transition.env"
RUNTIME_STATE="${STATE_HOME}/runtime-transition.env"
RUNTIME_COMMIT_FILE="${STATE_HOME}/runtime-commit.env"
CURRENT_RELEASE_LINK="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark/current"
MANAGE_PROXY="${SCRIPT_ROOT}/scripts/manage-proxy.sh"
MANAGE_SERVICE="${SCRIPT_ROOT}/scripts/manage-service.sh"
RUNTIME_TRANSITION="${SCRIPT_ROOT}/scripts/runtime/runtime-transition.sh"
WAIT_READY="${SCRIPT_ROOT}/scripts/runtime/wait-ready.sh"

PHASE_FILE="${STATE_HOME}/settings-transition.phase"
START_MARKER="${STATE_HOME}/settings-transition.start"
NO_START_MARKER="${STATE_HOME}/settings-transition.no-start"
PREV_SERVICE_ACTIVE_MARKER="${STATE_HOME}/settings-transition.previous-service-active"
PREV_CONTAINER_RUNNING_MARKER="${STATE_HOME}/settings-transition.previous-container-running"
BACKUP_MANIFEST="${INSTALL_STATE_FILE}.settings-backup"
TARGET_MANIFEST="${INSTALL_STATE_FILE}.settings-candidate"
BACKUP_SHA_FILE="${BACKUP_MANIFEST}.sha256"
TARGET_SHA_FILE="${TARGET_MANIFEST}.sha256"

usage() {
  cat <<EOF
Usage: $0 prepare CANDIDATE START|apply|commit|rollback|recover|status

prepare validates a complete settings-only candidate and records the previous state.
apply activates the candidate, applies proxy/service/runtime resources, and validates them.
commit finalizes a successfully applied target. rollback/recover restore the previous manifest
and managed resources after failure or interruption.
EOF
}
die() { printf 'FATAL: %s\n' "$*" >&2; exit 1; }
sha256_file() { sha256sum "$1" | awk '{print $1}'; }
container_running() { [[ "$(docker inspect -f '{{.State.Running}}' qwen38-flash-next 2>/dev/null || true)" == true ]]; }

settings_phase_valid() {
  case "$1" in preparing|activated|resources-applied|committing|rolling-back) return 0 ;; *) return 1 ;; esac
}
write_phase() {
  local phase="$1" temporary="${PHASE_FILE}.tmp"
  settings_phase_valid "${phase}" || die "invalid settings transaction phase: ${phase}"
  mkdir -p -- "${STATE_HOME}"
  umask 077
  printf '%s\n' "${phase}" >"${temporary}"
  mv -- "${temporary}" "${PHASE_FILE}"
}
load_phase() {
  [[ -f "${PHASE_FILE}" && ! -L "${PHASE_FILE}" ]] || die 'no settings transaction is active'
  IFS= read -r SETTINGS_PHASE <"${PHASE_FILE}" || die 'cannot read settings transaction phase'
  settings_phase_valid "${SETTINGS_PHASE}" || die "invalid settings transaction phase: ${SETTINGS_PHASE}"
  [[ "$(wc -l <"${PHASE_FILE}")" == 1 ]] || die 'settings transaction phase file has unexpected content'
}
read_start_policy() {
  local start_present=0 no_start_present=0
  [[ -f "${START_MARKER}" && ! -L "${START_MARKER}" ]] && start_present=1
  [[ -f "${NO_START_MARKER}" && ! -L "${NO_START_MARKER}" ]] && no_start_present=1
  [[ $((start_present + no_start_present)) == 1 ]] || die 'settings transaction start policy is missing or ambiguous'
  [[ "${start_present}" == 1 ]] && SETTINGS_START=1 || SETTINGS_START=0
}
clear_transaction() {
  rm -f -- \
    "${PHASE_FILE}" "${PHASE_FILE}.tmp" \
    "${START_MARKER}" "${NO_START_MARKER}" \
    "${PREV_SERVICE_ACTIVE_MARKER}" "${PREV_CONTAINER_RUNNING_MARKER}" \
    "${BACKUP_MANIFEST}" "${TARGET_MANIFEST}" \
    "${BACKUP_SHA_FILE}" "${TARGET_SHA_FILE}"
}
atomic_copy() {
  local source="$1" destination="$2"
  [[ -f "${source}" && ! -L "${source}" ]] || die "unsafe or missing source file: ${source}"
  cp -p -- "${source}" "${destination}.tmp"
  mv -- "${destination}.tmp" "${destination}"
}
read_digest() {
  local path="$1" value
  [[ -f "${path}" && ! -L "${path}" ]] || die "missing transaction digest: ${path}"
  IFS= read -r value <"${path}" || die "cannot read transaction digest: ${path}"
  [[ "${value}" =~ ^[0-9a-f]{64}$ ]] || die "invalid transaction digest: ${path}"
  printf '%s\n' "${value}"
}
verify_artifacts() {
  [[ -f "${BACKUP_MANIFEST}" && ! -L "${BACKUP_MANIFEST}" ]] || die 'settings backup manifest is missing or unsafe'
  [[ -f "${TARGET_MANIFEST}" && ! -L "${TARGET_MANIFEST}" ]] || die 'settings target manifest is missing or unsafe'
  BACKUP_SHA="$(read_digest "${BACKUP_SHA_FILE}")"
  TARGET_SHA="$(read_digest "${TARGET_SHA_FILE}")"
  [[ "$(sha256_file "${BACKUP_MANIFEST}")" == "${BACKUP_SHA}" ]] || die 'settings backup manifest digest mismatch'
  [[ "$(sha256_file "${TARGET_MANIFEST}")" == "${TARGET_SHA}" ]] || die 'settings target manifest digest mismatch'
  read_start_policy
}

parse_manifest() {
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
manifest_value() { local name="$1_$2"; printf '%s' "${!name:-}"; }

validate_settings_pair() {
  local key left right
  parse_manifest "$1" BASE || die "invalid current settings manifest: $1"
  parse_manifest "$2" CANDIDATE || die "invalid candidate settings manifest: $2"
  [[ "${BASE_PHASE}" == complete && "${CANDIDATE_PHASE}" == complete ]] || die 'settings transaction requires complete manifests'
  for key in INSTALL_ROOT MODEL_PROFILE MODEL_REPO MODEL_REVISION MODEL_DIR MODEL_OWNED SWAP_FILE SWAP_OWNED VLLM_IMAGE IMAGE_OWNED SERVED_NAME CONTAINER_NAME; do
    left="$(manifest_value BASE "${key}")"; right="$(manifest_value CANDIDATE "${key}")"
    [[ "${left}" == "${right}" ]] || die "settings-only candidate changes immutable/runtime identity field: ${key}"
  done
  case "${CANDIDATE_API_ACCESS_MODE}" in
    local)
      [[ "${CANDIDATE_PROXY_ENABLED}" == 0 && "${CANDIDATE_PROXY_OWNED}" == 0 ]] || die 'local API target must not claim proxy ownership'
      ;;
    docker|lan)
      [[ "${CANDIDATE_PROXY_ENABLED}" == 1 && "${CANDIDATE_PROXY_OWNED}" == 1 ]] || die 'non-local API target must claim managed proxy ownership'
      ;;
    *) die 'invalid candidate API access mode' ;;
  esac
  [[ "${CANDIDATE_SERVICE_ENABLED}" == "${CANDIDATE_SERVICE_OWNED}" ]] || die 'settings target service ownership must match service enablement'
}

acquire_transition_lock() {
  export QWEN38_SETTINGS_TRANSACTION_CONTEXT=1
  [[ -r "${OPERATION_LOCK_LIB}" ]] || die "operation lock helper is unavailable: ${OPERATION_LOCK_LIB}"
  # shellcheck source=scripts/lib/operation-lock.sh
  source "${OPERATION_LOCK_LIB}"
  acquire_operation_lock "${STATE_HOME}" "settings transaction" || exit $?
}
sudo_locked() {
  sudo env \
    QWEN38_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}" \
    QWEN38_OPERATION_LOCK_HELD="${QWEN38_OPERATION_LOCK_HELD}" \
    QWEN38_OPERATION_LOCK_FILE="${QWEN38_OPERATION_LOCK_FILE}" \
    QWEN38_OPERATION_LOCK_OWNER_PID="${QWEN38_OPERATION_LOCK_OWNER_PID}" \
    QWEN38_SETTINGS_TRANSACTION_CONTEXT=1 \
    "$@"
}
proxy_installed() { "${MANAGE_PROXY}" status >/dev/null 2>&1; }
service_status_text() { "${MANAGE_SERVICE}" status 2>/dev/null || true; }
service_installed() { grep -Fq 'installed : yes' <<<"$(service_status_text)"; }
service_active() { systemctl is-active --quiet qwen38-flash-next.service 2>/dev/null; }

preflight_current_resources() {
  parse_manifest "${INSTALL_STATE_FILE}" LIVE || die 'live installation manifest failed strict maintenance parsing'
  if proxy_installed; then
    [[ "${LIVE_PROXY_OWNED}" == 1 ]] || die 'managed proxy resources exist but the live manifest does not own them'
  elif [[ "${LIVE_PROXY_OWNED}" == 1 ]]; then
    die 'live manifest owns proxy resources but managed proxy resources are missing'
  fi
  if service_installed; then
    [[ "${LIVE_SERVICE_OWNED}" == 1 ]] || die 'managed service exists but the live manifest does not own it'
  elif [[ "${LIVE_SERVICE_OWNED}" == 1 ]]; then
    die 'live manifest owns the managed service but the unit is missing'
  fi
  if service_active && [[ "${LIVE_SERVICE_ENABLED}" != 1 ]]; then
    die 'managed service is active while the live manifest says service is disabled'
  fi
}

proxy_args_for_prefix() {
  local prefix="$1" mode docker_port lan_address lan_port
  mode="$(manifest_value "${prefix}" API_ACCESS_MODE)"
  docker_port="$(manifest_value "${prefix}" API_DOCKER_PORT)"
  lan_address="$(manifest_value "${prefix}" API_LAN_ADDRESS)"
  lan_port="$(manifest_value "${prefix}" API_LAN_PORT)"
  PROXY_ARGS=(create --docker-port "${docker_port}" --backend-port 8888 --yes)
  [[ "${mode}" != lan ]] || PROXY_ARGS+=(--lan-address "${lan_address}" --lan-port "${lan_port}")
}

apply_proxy_for_prefix() {
  local desired="$1" current="$2" mode desired_owned current_owned
  mode="$(manifest_value "${desired}" API_ACCESS_MODE)"
  desired_owned="$(manifest_value "${desired}" PROXY_OWNED)"
  current_owned="$(manifest_value "${current}" PROXY_OWNED)"
  if [[ "${mode}" == local ]]; then
    if proxy_installed; then
      [[ "${current_owned}" == 1 ]] || die 'refusing to remove proxy resources not owned by the current manifest'
      sudo_locked "${MANAGE_PROXY}" remove --yes
    fi
    return 0
  fi
  [[ "${desired_owned}" == 1 ]] || die 'non-local API target must own its proxy resources'
  if proxy_installed; then
    [[ "${current_owned}" == 1 ]] || die 'refusing to replace proxy resources not owned by the current manifest'
  fi
  proxy_args_for_prefix "${desired}"
  sudo_locked "${MANAGE_PROXY}" "${PROXY_ARGS[@]}"
}

runtime_root() {
  [[ -L "${CURRENT_RELEASE_LINK}" ]] || die "immutable current release pointer is missing: ${CURRENT_RELEASE_LINK}"
  readlink -f -- "${CURRENT_RELEASE_LINK}"
}

start_standalone_for_prefix() {
  local prefix="$1" root model_profile model_dir image served config monitor_enabled monitor_protect
  local min_avail min_free free_gate swap_free consecutive heartbeat
  root="$(runtime_root)"
  model_profile="$(manifest_value "${prefix}" MODEL_PROFILE)"
  model_dir="$(manifest_value "${prefix}" MODEL_DIR)"
  image="$(manifest_value "${prefix}" VLLM_IMAGE)"
  served="$(manifest_value "${prefix}" SERVED_NAME)"
  config="$(manifest_value "${prefix}" CONFIG_OVERRIDE)"
  monitor_enabled="$(manifest_value "${prefix}" MONITOR_ENABLED)"
  monitor_protect="$(manifest_value "${prefix}" MONITOR_PROTECT)"
  min_avail="$(manifest_value "${prefix}" MONITOR_MIN_AVAILABLE_GIB)"
  min_free="$(manifest_value "${prefix}" MONITOR_MIN_FREE_GIB)"
  free_gate="$(manifest_value "${prefix}" MONITOR_FREE_GATE_GIB)"
  swap_free="$(manifest_value "${prefix}" MONITOR_MIN_SWAP_FREE_GIB)"
  consecutive="$(manifest_value "${prefix}" MONITOR_CONSECUTIVE)"
  heartbeat="$(manifest_value "${prefix}" MONITOR_HEARTBEAT)"

  bash "${RUNTIME_TRANSITION}" recover
  bash "${RUNTIME_TRANSITION}" prepare
  if ! MODEL_PROFILE="${model_profile}" MODEL_DIR="${model_dir}" VLLM_IMAGE="${image}" SERVED_NAME="${served}" \
    CONFIG_OVERRIDE="${config}" MONITOR_ENABLED="${monitor_enabled}" MONITOR_PROTECT="${monitor_protect}" \
    MONITOR_MIN_AVAILABLE_GIB="${min_avail}" MONITOR_MIN_FREE_GIB="${min_free}" \
    MONITOR_FREE_GATE_GIB="${free_gate}" MONITOR_MIN_SWAP_FREE_GIB="${swap_free}" \
    MONITOR_CONSECUTIVE="${consecutive}" MONITOR_HEARTBEAT="${heartbeat}" \
    "${root}/scripts/serve.sh"; then
    bash "${RUNTIME_TRANSITION}" rollback || true
    return 1
  fi
  bash "${RUNTIME_TRANSITION}" candidate-started
  bash "${RUNTIME_TRANSITION}" validating
  if ! "${WAIT_READY}" --container qwen38-flash-next --model "${served}" --timeout 1800 --interval 10; then
    bash "${RUNTIME_TRANSITION}" rollback || true
    return 1
  fi
  bash "${RUNTIME_TRANSITION}" commit
  rm -f -- "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"
}

apply_service_for_prefix() {
  local desired="$1" current="$2" start="$3" desired_enabled desired_owned current_owned root
  desired_enabled="$(manifest_value "${desired}" SERVICE_ENABLED)"
  desired_owned="$(manifest_value "${desired}" SERVICE_OWNED)"
  current_owned="$(manifest_value "${current}" SERVICE_OWNED)"

  if [[ "${desired_enabled}" == 1 ]]; then
    [[ "${desired_owned}" == 1 ]] || die 'enabled service target must own the managed unit'
    if service_installed; then
      [[ "${current_owned}" == 1 ]] || die 'refusing to replace a managed service not owned by the current manifest'
    fi
    root="$(runtime_root)"
    service_args=(create --runtime-root "${root}" --yes)
    [[ "${start}" == 1 ]] && service_args+=(--start) || service_args+=(--no-start)
    sudo_locked "${MANAGE_SERVICE}" "${service_args[@]}"
    return 0
  fi

  [[ "${desired_owned}" == 0 ]] || die 'disabled service target must not claim service ownership'
  if service_installed; then
    [[ "${current_owned}" == 1 ]] || die 'refusing to remove a managed service not owned by the current manifest'
    sudo_locked "${MANAGE_SERVICE}" remove --yes
  fi
  if [[ "${start}" == 1 ]]; then
    start_standalone_for_prefix "${desired}"
  fi
}

verify_proxy_for_prefix() {
  local prefix="$1" mode docker_port lan_address lan_port text listeners
  mode="$(manifest_value "${prefix}" API_ACCESS_MODE)"
  if [[ "${mode}" == local ]]; then
    ! proxy_installed || return 1
    return 0
  fi
  text="$("${MANAGE_PROXY}" status 2>/dev/null)" || return 1
  docker_port="$(manifest_value "${prefix}" API_DOCKER_PORT)"
  grep -Eq "listener  : .*:${docker_port}$" <<<"${text}" || return 1
  listeners="$(grep -c '^  listener  :' <<<"${text}" || true)"
  if [[ "${mode}" == lan ]]; then
    lan_address="$(manifest_value "${prefix}" API_LAN_ADDRESS)"
    lan_port="$(manifest_value "${prefix}" API_LAN_PORT)"
    grep -Fq "listener  : ${lan_address}:${lan_port}" <<<"${text}" || return 1
    [[ "${listeners}" -eq 2 ]] || return 1
  else
    [[ "${listeners}" -eq 1 ]] || return 1
  fi
}

verify_service_for_prefix() {
  local prefix="$1" start="$2" enabled served text
  enabled="$(manifest_value "${prefix}" SERVICE_ENABLED)"
  if [[ "${enabled}" == 1 ]]; then
    text="$(service_status_text)"
    grep -Fq 'installed : yes' <<<"${text}" || return 1
    grep -Fq 'enabled   : yes' <<<"${text}" || return 1
    if [[ "${start}" == 1 ]]; then
      grep -Fq 'active    : yes' <<<"${text}" || return 1
      served="$(manifest_value "${prefix}" SERVED_NAME)"
      "${WAIT_READY}" --container qwen38-flash-next --model "${served}" --timeout 30 --interval 2 >/dev/null
    fi
    return 0
  fi
  service_installed && return 1
  if [[ "${start}" == 1 ]]; then
    served="$(manifest_value "${prefix}" SERVED_NAME)"
    "${WAIT_READY}" --container qwen38-flash-next --model "${served}" --timeout 30 --interval 2 >/dev/null
  fi
}
verify_resources_for_prefix() {
  local prefix="$1" start="$2"
  verify_proxy_for_prefix "${prefix}" || die "settings transaction proxy verification failed for ${prefix}"
  verify_service_for_prefix "${prefix}" "${start}" || die "settings transaction service/runtime verification failed for ${prefix}"
}

restore_backup() {
  local target_loaded=0 restore_start=0
  load_phase
  verify_artifacts
  parse_manifest "${BACKUP_MANIFEST}" BACKUP || die 'backup manifest failed strict parsing during rollback'
  if parse_manifest "${TARGET_MANIFEST}" TARGET; then target_loaded=1; fi
  write_phase rolling-back
  atomic_copy "${BACKUP_MANIFEST}" "${INSTALL_STATE_FILE}"
  if [[ "${target_loaded}" == 1 ]]; then
    apply_proxy_for_prefix BACKUP TARGET
    if [[ "${BACKUP_SERVICE_ENABLED}" == 1 ]]; then
      [[ -f "${PREV_SERVICE_ACTIVE_MARKER}" ]] && restore_start=1 || restore_start=0
    else
      [[ -f "${PREV_CONTAINER_RUNNING_MARKER}" ]] && restore_start=1 || restore_start=0
    fi
    apply_service_for_prefix BACKUP TARGET "${restore_start}"
    verify_resources_for_prefix BACKUP "${restore_start}"
  fi
  clear_transaction
  printf 'Settings transaction rolled back to the previous complete manifest.\n'
}

prepare_transaction() {
  local input="$1" start="$2"
  [[ "${start}" == 0 || "${start}" == 1 ]] || die 'prepare START must be 0 or 1'
  [[ -f "${INSTALL_STATE_FILE}" && ! -L "${INSTALL_STATE_FILE}" ]] || die 'complete live install manifest is required'
  [[ -f "${input}" && ! -L "${input}" ]] || die "settings candidate is missing or unsafe: ${input}"
  [[ ! -e "${PHASE_FILE}" && ! -L "${PHASE_FILE}" ]] || die 'a settings transaction is already active; recover it first'
  for stale in "${BACKUP_MANIFEST}" "${TARGET_MANIFEST}" "${BACKUP_SHA_FILE}" "${TARGET_SHA_FILE}" "${START_MARKER}" "${NO_START_MARKER}"; do
    [[ ! -e "${stale}" && ! -L "${stale}" ]] || die "stale settings transaction artifact exists: ${stale}"
  done
  for other in "${PROFILE_SWITCH_STATE}" "${UPDATE_STATE}" "${RUNTIME_STATE}"; do
    [[ ! -e "${other}" && ! -L "${other}" ]] || die "another lifecycle transaction is active: ${other}"
  done
  validate_settings_pair "${INSTALL_STATE_FILE}" "${input}"
  preflight_current_resources

  atomic_copy "${INSTALL_STATE_FILE}" "${BACKUP_MANIFEST}"
  atomic_copy "${input}" "${TARGET_MANIFEST}"
  umask 077
  sha256_file "${BACKUP_MANIFEST}" >"${BACKUP_SHA_FILE}"
  sha256_file "${TARGET_MANIFEST}" >"${TARGET_SHA_FILE}"
  if [[ "${start}" == 1 ]]; then : >"${START_MARKER}"; else : >"${NO_START_MARKER}"; fi
  service_active && : >"${PREV_SERVICE_ACTIVE_MARKER}" || true
  container_running && : >"${PREV_CONTAINER_RUNNING_MARKER}" || true
  write_phase preparing
  rm -f -- "${input}"
  printf 'Settings transaction prepared (start=%s).\n' "${start}"
}

apply_transaction() {
  load_phase
  [[ "${SETTINGS_PHASE}" == preparing ]] || die "cannot apply settings transaction from phase: ${SETTINGS_PHASE}"
  verify_artifacts
  parse_manifest "${BACKUP_MANIFEST}" BACKUP || die 'settings backup manifest failed strict parsing'
  parse_manifest "${TARGET_MANIFEST}" TARGET || die 'settings target manifest failed strict parsing'
  local live_sha
  live_sha="$(sha256_file "${INSTALL_STATE_FILE}")"
  [[ "${live_sha}" == "${BACKUP_SHA}" ]] || die 'live manifest changed after settings transaction prepare'
  atomic_copy "${TARGET_MANIFEST}" "${INSTALL_STATE_FILE}"
  write_phase activated

  rollback_on_error() {
    local rc="$?"
    trap - ERR INT TERM
    set +e
    restore_backup
    local rollback_rc="$?"
    set -e
    if [[ "${rollback_rc}" != 0 ]]; then
      printf 'FATAL: automatic settings rollback failed; transaction state was retained for explicit recovery.\n' >&2
      exit 70
    fi
    exit "${rc}"
  }
  trap 'rollback_on_error' ERR
  trap 'false' INT TERM

  apply_proxy_for_prefix TARGET BACKUP
  apply_service_for_prefix TARGET BACKUP "${SETTINGS_START}"
  verify_resources_for_prefix TARGET "${SETTINGS_START}"
  write_phase resources-applied
  trap - ERR INT TERM
  printf 'Settings resources applied and verified.\n'
}

commit_transaction() {
  load_phase
  [[ "${SETTINGS_PHASE}" == resources-applied || "${SETTINGS_PHASE}" == committing ]] || die "cannot commit settings transaction from phase: ${SETTINGS_PHASE}"
  verify_artifacts
  parse_manifest "${TARGET_MANIFEST}" TARGET || die 'settings target manifest failed strict parsing'
  [[ "$(sha256_file "${INSTALL_STATE_FILE}")" == "${TARGET_SHA}" ]] || die 'live manifest no longer matches the settings target'
  verify_resources_for_prefix TARGET "${SETTINGS_START}"
  write_phase committing
  clear_transaction
  printf 'Settings transaction committed.\n'
}

recover_transaction() {
  if [[ ! -e "${PHASE_FILE}" && ! -L "${PHASE_FILE}" ]]; then
    for artifact in "${BACKUP_MANIFEST}" "${TARGET_MANIFEST}" "${BACKUP_SHA_FILE}" "${TARGET_SHA_FILE}" "${START_MARKER}" "${NO_START_MARKER}"; do
      [[ ! -e "${artifact}" && ! -L "${artifact}" ]] || die "settings artifacts exist without transaction phase: ${artifact}"
    done
    printf 'SETTINGS_TRANSITION_STATE=idle\n'
    return 0
  fi
  load_phase
  verify_artifacts
  case "${SETTINGS_PHASE}" in
    preparing)
      live_sha="$(sha256_file "${INSTALL_STATE_FILE}")"
      if [[ "${live_sha}" == "${BACKUP_SHA}" ]]; then
        clear_transaction
        printf 'Interrupted settings transaction recovered before activation.\n'
      elif [[ "${live_sha}" == "${TARGET_SHA}" ]]; then
        restore_backup
      else
        die 'cannot recover preparing settings transaction: live manifest matches neither backup nor target'
      fi
      ;;
    activated|resources-applied|rolling-back)
      restore_backup
      ;;
    committing)
      parse_manifest "${TARGET_MANIFEST}" TARGET || die 'settings target manifest failed strict parsing'
      if [[ "$(sha256_file "${INSTALL_STATE_FILE}")" == "${TARGET_SHA}" ]]; then
        verify_resources_for_prefix TARGET "${SETTINGS_START}"
        clear_transaction
        printf 'Interrupted settings commit finalized.\n'
      else
        restore_backup
      fi
      ;;
  esac
}

[[ -r "${STATE_PARSER}" ]] || die "strict state parser is unavailable: ${STATE_PARSER}"
[[ -x "${MANAGE_PROXY}" && -x "${MANAGE_SERVICE}" && -r "${RUNTIME_TRANSITION}" && -x "${WAIT_READY}" ]] || die 'required lifecycle helper is unavailable'
[[ $# -ge 1 ]] || { usage >&2; exit 2; }
action="$1"; shift

case "${action}" in
  status)
    [[ $# -eq 0 ]] || { usage >&2; exit 2; }
    if [[ -f "${PHASE_FILE}" && ! -L "${PHASE_FILE}" ]]; then
      load_phase
      printf 'SETTINGS_TRANSITION_STATE=%s\n' "${SETTINGS_PHASE}"
    else
      printf 'SETTINGS_TRANSITION_STATE=idle\n'
    fi
    ;;
  prepare)
    [[ $# -eq 2 ]] || { usage >&2; exit 2; }
    acquire_transition_lock
    prepare_transaction "$1" "$2"
    ;;
  apply)
    [[ $# -eq 0 ]] || { usage >&2; exit 2; }
    acquire_transition_lock
    apply_transaction
    ;;
  commit)
    [[ $# -eq 0 ]] || { usage >&2; exit 2; }
    acquire_transition_lock
    commit_transaction
    ;;
  rollback)
    [[ $# -eq 0 ]] || { usage >&2; exit 2; }
    acquire_transition_lock
    if [[ ! -e "${PHASE_FILE}" ]]; then printf 'No settings transaction to roll back.\n'; exit 0; fi
    restore_backup
    ;;
  recover)
    [[ $# -eq 0 ]] || { usage >&2; exit 2; }
    acquire_transition_lock
    recover_transaction
    ;;
  -h|--help) usage ;;
  *) usage >&2; exit 2 ;;
esac
