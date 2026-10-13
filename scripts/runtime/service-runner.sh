#!/usr/bin/env bash
# Keep the Docker inference container attached to a systemd service lifecycle.
set -Eeuo pipefail

RUNTIME_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_FILE="${QWEN38_STATE_FILE:-${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark/install.env}"
STATE_PARSER="${RUNTIME_ROOT}/scripts/lib/state_file.py"
RELEASE_PROFILE_REFRESH_TRANSITION="${RUNTIME_ROOT}/scripts/release-profile-refresh-transition.sh"
PROFILE_SWITCH_TRANSITION="${RUNTIME_ROOT}/scripts/profile-switch-transition.sh"
[[ -r "${RELEASE_PROFILE_REFRESH_TRANSITION}" ]] || { printf 'FATAL: release-profile refresh transition helper is unavailable: %s\n' "${RELEASE_PROFILE_REFRESH_TRANSITION}" >&2; exit 1; }
[[ -r "${PROFILE_SWITCH_TRANSITION}" ]] || { printf 'FATAL: profile-switch transition helper is unavailable: %s\n' "${PROFILE_SWITCH_TRANSITION}" >&2; exit 1; }
# A cross-release refresh owns both the immutable release pointer and canonical
# manifest, so it must recover before any profile-only transaction or manifest
# parsing. During an intentional cutover the outer operation lock is busy and
# service-recover defers; after interruption it restores a deterministic pair.
#
# rc=75 is intentionally special: service-recover has restored a running previous
# container and persisted runtime-adopt.env. Do not return 75 to systemd. The unit's
# ExecStart commonly points through the dynamic current symlink, which now resolves
# to the previous release; a blind restart could therefore enter an older runner
# that does not understand the one-shot adoption marker and cold-replace the exact
# restored container. Finish attachment in this already-running target process.
set +e
bash "${RELEASE_PROFILE_REFRESH_TRANSITION}" service-recover
refresh_recovery_rc=$?
set -e
if [[ "${refresh_recovery_rc}" == 75 ]]; then
  restored_root=""
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" install-service "${STATE_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    printf 'FATAL: restored install manifest failed strict service parsing after refresh recovery\n' >&2
    exit 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    [[ "${key}" != INSTALL_ROOT ]] || restored_root="${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
  [[ -n "${restored_root}" ]] || {
    printf 'FATAL: restored runtime root is missing after refresh recovery\n' >&2
    exit 1
  }
  adopt_runner="${RUNTIME_ROOT}/scripts/runtime/service-adopt-runner.sh"
  [[ -r "${adopt_runner}" ]] || {
    printf 'FATAL: refresh recovery adoption supervisor is unavailable: %s\n' "${adopt_runner}" >&2
    exit 1
  }
  printf 'Refresh recovery restored a running predecessor; attaching it before systemd can restart through current.\n'
  exec bash "${adopt_runner}" --runtime-root "${restored_root}"
elif [[ "${refresh_recovery_rc}" != 0 ]]; then
  exit "${refresh_recovery_rc}"
fi
# During an intentional switch the installer still owns operation.lock, so
# service-recover defers. After a reboot/interruption the lock is free and the
# persisted profile transaction is deterministically recovered before parsing
# the canonical install manifest.
bash "${PROFILE_SWITCH_TRANSITION}" service-recover
[[ -r "${STATE_FILE}" ]] || { printf 'FATAL: installation manifest is not readable: %s\n' "${STATE_FILE}" >&2; exit 1; }
[[ -r "${STATE_PARSER}" ]] || { printf 'FATAL: state parser is unavailable: %s\n' "${STATE_PARSER}" >&2; exit 1; }

delegate_restored_runtime_root() {
  local parsed key value manifest_root="" canonical_root adopt_file adopt_runner previous_runner
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" install-service "${STATE_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    [[ "${key}" != INSTALL_ROOT ]] || manifest_root="${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
  [[ -n "${manifest_root}" ]] || return 1
  canonical_root="$(realpath -e -- "${manifest_root}" 2>/dev/null || true)"
  [[ -n "${canonical_root}" ]] || return 1
  [[ "${canonical_root}" != "${RUNTIME_ROOT}" ]] || return 0

  adopt_file="$(dirname -- "${STATE_FILE}")/runtime-adopt.env"
  if [[ -e "${adopt_file}" || -L "${adopt_file}" ]]; then
    [[ -f "${adopt_file}" && ! -L "${adopt_file}" ]] || {
      printf 'FATAL: runtime adoption marker is unsafe: %s\n' "${adopt_file}" >&2
      return 1
    }
    adopt_runner="${RUNTIME_ROOT}/scripts/runtime/service-adopt-runner.sh"
    [[ -r "${adopt_runner}" ]] || {
      printf 'FATAL: runtime adoption supervisor is unavailable: %s\n' "${adopt_runner}" >&2
      return 1
    }
    exec bash "${adopt_runner}" --runtime-root "${canonical_root}"
  fi

  if docker inspect qwen38-flash-next >/dev/null 2>&1; then
    if [[ "$(docker inspect --format '{{.State.Running}}' qwen38-flash-next 2>/dev/null || true)" == true ]]; then
      printf 'FATAL: restored runtime is already running without an adoption marker; refusing a cold replacement\n' >&2
      return 1
    fi
    printf 'Restored runtime container is intentionally stopped; preserving stopped state instead of cold-starting legacy runtime.\n'
    exit 0
  fi

  previous_runner="${canonical_root}/scripts/service-runner.sh"
  [[ -x "${previous_runner}" ]] || {
    printf 'FATAL: restored runtime root has no executable service runner: %s\n' "${previous_runner}" >&2
    return 1
  }
  printf 'Delegating managed service to restored immutable runtime root: %s\n' "${canonical_root}"
  exec bash "${previous_runner}"
}

delegate_restored_runtime_root || {
  printf 'FATAL: failed to resolve managed runtime root before startup\n' >&2
  exit 1
}

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

# install.env is data, not executable shell input. The strict parser validates
# the closed installer key set and emits only runtime-required fields.
parse_state_into_vars install-service-runtime "${STATE_FILE}" || {
  printf 'FATAL: installation manifest failed strict service-runtime parsing: %s\n' "${STATE_FILE}" >&2
  exit 1
}

STATE_DIR="$(dirname -- "${STATE_FILE}")"
STOP_REASON_FILE="${STATE_DIR}/runtime-stop.env"
RUNTIME_COMMIT_FILE="${STATE_DIR}/runtime-commit.env"
RELEASE_PROFILE_REFRESH_STATE_FILE="${STATE_DIR}/release-profile-refresh-transition.env"
RUNTIME_TRANSITION="${RUNTIME_ROOT}/scripts/runtime/runtime-transition.sh"
RUNTIME_PREFLIGHT="${RUNTIME_ROOT}/scripts/runtime/preflight-runtime.sh"
CONFIG_OVERRIDE="${CONFIG_OVERRIDE:-}"
MONITOR_PROTECT="${MONITOR_PROTECT:-0}"
MONITOR_ENABLED="${MONITOR_ENABLED:-${MONITOR_PROTECT}}"
RUNTIME_PHASE_START_SECONDS="${SECONDS}"

log_runtime_phase() {
  local phase="$1"
  printf 'Runtime phase: %s (elapsed=%ss)\n' "${phase}" "$((SECONDS - RUNTIME_PHASE_START_SECONDS))"
}

protected_stop_matches_container() {
  local container_id="$1"
  [[ -n "${container_id}" && -r "${STOP_REASON_FILE}" ]] || return 1
  unset RUNTIME_STOP_SCHEMA_VERSION STOP_REASON STOP_CONTAINER_NAME STOP_CONTAINER_ID UPDATED_AT
  parse_state_into_vars runtime-stop "${STOP_REASON_FILE}" || return 1
  [[ "${STOP_REASON:-}" == memory-protection &&
     "${STOP_CONTAINER_NAME:-}" == "${CONTAINER_NAME}" &&
     "${STOP_CONTAINER_ID:-}" == "${container_id}" ]]
}

write_runtime_commit_attestation() {
  local container_id="$1" temporary="${RUNTIME_COMMIT_FILE}.tmp"
  [[ "${container_id}" =~ ^[0-9a-f]{12,128}$ ]] || return 1
  [[ "${RUNTIME_ROOT}" == /* && "${RUNTIME_ROOT}" != *[[:space:]]* ]] || return 1
  mkdir -p -- "${STATE_DIR}"
  umask 077
  {
    printf 'RUNTIME_COMMIT_SCHEMA_VERSION=1\n'
    printf 'RUNTIME_ROOT=%s\n' "${RUNTIME_ROOT}"
    printf 'RUNTIME_CONTAINER_NAME=%s\n' "${CONTAINER_NAME}"
    printf 'RUNTIME_CONTAINER_ID=%s\n' "${container_id}"
    printf 'COMMITTED_AT=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  } >"${temporary}"
  python3 "${STATE_PARSER}" runtime-commit "${temporary}" >/dev/null
  mv -- "${temporary}" "${RUNTIME_COMMIT_FILE}"
}

release_profile_refresh_owns_runtime_commit() {
  local parsed key value refresh_state="" target_release="" target_image="" profile=""
  local runtime_release
  [[ -f "${RELEASE_PROFILE_REFRESH_STATE_FILE}" && ! -L "${RELEASE_PROFILE_REFRESH_STATE_FILE}" ]] || return 1
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" release-profile-refresh "${RELEASE_PROFILE_REFRESH_STATE_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    printf 'FATAL: release-profile refresh state failed strict parsing during runtime validation\n' >&2
    return 2
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    case "${key}" in
      RELEASE_PROFILE_REFRESH_STATE) refresh_state="${value}" ;;
      TARGET_RELEASE) target_release="${value}" ;;
      TARGET_IMAGE) target_image="${value}" ;;
      PROFILE) profile="${value}" ;;
    esac
  done <"${parsed}"
  rm -f -- "${parsed}"
  runtime_release="$(basename -- "${RUNTIME_ROOT}")"
  [[ "${refresh_state}" == runtime_validating ]] || return 1
  [[ "${target_release}" == "${runtime_release}" ]] || {
    printf 'FATAL: refresh target release does not match runtime root\n' >&2
    return 2
  }
  [[ "${target_image}" == "${VLLM_IMAGE}" && "${profile}" == "${MODEL_PROFILE}" ]] || {
    printf 'FATAL: refresh target runtime identity does not match service manifest\n' >&2
    return 2
  }
  return 0
}

[[ "${MODEL_PROFILE:-}" == orcarouter || "${MODEL_PROFILE:-}" == nvidia || "${MODEL_PROFILE:-}" == mazinb || "${MODEL_PROFILE:-}" == orcarouter-hybrid ]] || { printf 'FATAL: unsupported model profile\n' >&2; exit 1; }
[[ -x "${RUNTIME_ROOT}/scripts/serve.sh" ]] || { printf 'FATAL: invalid runtime release root\n' >&2; exit 1; }
[[ -r "${RUNTIME_TRANSITION}" ]] || { printf 'FATAL: runtime transition helper is unavailable\n' >&2; exit 1; }
[[ -r "${RUNTIME_PREFLIGHT}" ]] || { printf 'FATAL: runtime preflight helper is unavailable\n' >&2; exit 1; }
[[ "${CONTAINER_NAME:-}" == qwen38-flash-next ]] || { printf 'FATAL: unexpected container name\n' >&2; exit 1; }

export MODEL_PROFILE MODEL_DIR VLLM_IMAGE CONFIG_OVERRIDE MONITOR_ENABLED MONITOR_PROTECT SERVED_NAME
export MONITOR_MIN_AVAILABLE_GIB MONITOR_MIN_FREE_GIB MONITOR_FREE_GATE_GIB
export MONITOR_MIN_SWAP_FREE_GIB MONITOR_CONSECUTIVE MONITOR_HEARTBEAT
export NAME="${CONTAINER_NAME}"
export CONTAINER_NAME
export RESTART_POLICY=no
export PUBLISH_HOST=127.0.0.1

# A previous attestation never proves this process has completed a new commit.
rm -f -- "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"
log_runtime_phase "preflight-start"
bash "${RUNTIME_PREFLIGHT}"
log_runtime_phase "preflight-complete"
bash "${RUNTIME_TRANSITION}" recover
log_runtime_phase "transition-recovery-complete"

transition_active=0
rollback_transition() {
  local rc="${1:-1}"
  trap - ERR INT TERM
  set +e
  rm -f -- "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"
  if [[ "${transition_active}" == 1 ]]; then
    printf 'Candidate runtime failed validation; restoring previous container.\n' >&2
    if ! bash "${RUNTIME_TRANSITION}" rollback; then
      printf 'FATAL: automatic runtime rollback failed; run doctor and inspect Docker state.\n' >&2
      exit 70
    fi
  fi
  exit "${rc}"
}
trap 'rollback_transition $?' ERR
trap 'rollback_transition 130' INT
trap 'rollback_transition 143' TERM

bash "${RUNTIME_TRANSITION}" prepare
transition_active=1
log_runtime_phase "transition-prepared"
"${RUNTIME_ROOT}/scripts/serve.sh"
log_runtime_phase "container-start-command-complete"
bash "${RUNTIME_TRANSITION}" candidate-started
bash "${RUNTIME_TRANSITION}" validating
log_runtime_phase "candidate-validating"

ready=0
for attempt in $(seq 1 180); do
  if curl -fsS --max-time 3 http://127.0.0.1:8888/health >/dev/null 2>&1; then
    ready=1
    break
  fi
  state="$(docker inspect --format '{{.State.Status}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
  if [[ "${state}" != running ]]; then
    candidate_id="$(docker inspect --format '{{.Id}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
    if protected_stop_matches_container "${candidate_id}"; then
      printf 'Candidate runtime was stopped by memory protection during startup; leaving managed runtime stopped.\n' >&2
      bash "${RUNTIME_TRANSITION}" abort-protected
      transition_active=0
      rm -f -- "${STOP_REASON_FILE}"
      trap - ERR INT TERM
      exit 0
    fi
    printf 'FATAL: candidate container stopped during startup (state=%s)\n' "${state:-missing}" >&2
    false
  fi
  if (( attempt % 6 == 0 )); then
    printf 'Waiting for Qwen readiness: %d/1800 seconds\n' "$((attempt * 10))"
  fi
  sleep 10
done
[[ "${ready}" == 1 ]] || { printf 'FATAL: candidate API did not become healthy within 30 minutes\n' >&2; false; }
log_runtime_phase "health-ready"

models="$(curl -fsS --max-time 15 http://127.0.0.1:8888/v1/models)"
python3 -c 'import json,sys; expected=sys.argv[1]; data=json.load(sys.stdin); assert any(item.get("id") == expected for item in data.get("data", [])), expected' \
  "${SERVED_NAME:-orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4}" <<<"${models}"
log_runtime_phase "model-list-validated"

container_id="$(docker inspect --format '{{.Id}}' "${CONTAINER_NAME}")"
refresh_runtime_owner=0
if release_profile_refresh_owns_runtime_commit; then
  refresh_runtime_owner=1
else
  refresh_owner_rc=$?
  [[ "${refresh_owner_rc}" != 2 ]] || false
fi

if [[ "${refresh_runtime_owner}" == 1 ]]; then
  # Keep qwen38-flash-next.rollback until the outer release+manifest coordinator
  # commits. The attestation lets manage-service report READY without destroying
  # the only exact previous runtime that can make rollback symmetric.
  write_runtime_commit_attestation "${container_id}"
  log_runtime_phase "runtime-attestation-written"
  log_runtime_phase "transition-commit-deferred"
  printf 'Qwen API is ready and attested; outer release-profile refresh owns runtime commit.\n'
else
  bash "${RUNTIME_TRANSITION}" commit
  log_runtime_phase "transition-committed"
  # The standalone runtime transaction is now final. Any attestation failure
  # must fail the service/update path, not roll back an already-committed change.
  transition_active=0
  write_runtime_commit_attestation "${container_id}"
  log_runtime_phase "runtime-attestation-written"
  trap - ERR INT TERM
  printf 'Qwen API is ready; runtime transition committed and attested.\n'
fi

printf 'Following container logs.\n'
docker logs --follow --since 0s "${CONTAINER_NAME}" &
log_pid=$!
trap 'kill "${log_pid}" 2>/dev/null || true' EXIT
container_status="$(docker wait "${CONTAINER_NAME}")"
container_id="$(docker inspect --format '{{.Id}}' "${CONTAINER_NAME}" 2>/dev/null || true)"
rm -f -- "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"

if [[ -r "${STOP_REASON_FILE}" ]]; then
  if protected_stop_matches_container "${container_id}"; then
    rm -f -- "${STOP_REASON_FILE}"
    printf 'Inference container stopped intentionally by memory protection; leaving service stopped.\n' >&2
    exit 0
  fi
  printf 'WARNING: ignoring invalid or stale runtime stop marker; container will be treated as failed.\n' >&2
  rm -f -- "${STOP_REASON_FILE}"
fi

printf 'Inference container stopped (exit %s); marking service failed.\n' "${container_status}" >&2
exit 1
