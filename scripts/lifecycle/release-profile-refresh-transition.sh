#!/usr/bin/env bash
# Atomically refresh an immutable release and the same-profile runtime manifest.
#
# This coordinator is intentionally the sole owner of the release pointers and
# install manifest during a cross-release H38 refresh. It must not be composed
# from update-transition.sh + profile-switch-transition.sh because independent
# recovery owners can restore mismatched release/manifest pairs.
set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
RELEASES_DIR="${QWEN38_RELEASES_DIR:-${DATA_HOME}/releases}"
CURRENT_LINK="${QWEN38_CURRENT_RELEASE_LINK:-${DATA_HOME}/current}"
PREVIOUS_LINK="${QWEN38_PREVIOUS_RELEASE_LINK:-${DATA_HOME}/previous}"
QUALIFIED_DIR="${QWEN38_QUALIFIED_DIR:-${DATA_HOME}/qualified}"
INSTALL_STATE_FILE="${QWEN38_STATE_FILE:-${STATE_HOME}/install.env}"
STATE_FILE="${QWEN38_RELEASE_PROFILE_REFRESH_STATE_FILE:-${STATE_HOME}/release-profile-refresh-transition.env}"
BACKUP_MANIFEST="${INSTALL_STATE_FILE}.release-profile-refresh-backup"
TARGET_MANIFEST="${INSTALL_STATE_FILE}.release-profile-refresh-candidate"
RUNTIME_COMMIT_FILE="${STATE_HOME}/runtime-commit.env"
RUNTIME_TRANSITION_FILE="${STATE_HOME}/runtime-transition.env"
UPDATE_STATE_FILE="${STATE_HOME}/update-transition.env"
PROFILE_SWITCH_STATE_FILE="${STATE_HOME}/profile-switch-transition.env"
SETTINGS_PHASE_FILE="${STATE_HOME}/settings-transition.phase"
ASSET_OWNERSHIP_FILE="${STATE_HOME}/asset-ownership.json"
RELEASE_MANAGER="${SCRIPT_ROOT}/scripts/release-manager.sh"
QUALIFY_RELEASE="${SCRIPT_ROOT}/scripts/lifecycle/qualify-release.sh"
STATE_PARSER="${SCRIPT_ROOT}/scripts/lib/state_file.py"
QUALIFICATION_PARSER="${SCRIPT_ROOT}/scripts/lib/qualification_marker.py"
OPERATION_LOCK_LIB="${SCRIPT_ROOT}/scripts/lib/operation-lock.sh"
TARGET_H38_IMAGE="vllm-orcarouter-v029-h38-decoder-scope:v1"
TARGET_H38_SCOPE="decoder-v1"
TARGET_PROFILE="orcarouter"
DRY_RUN=0

usage() {
  cat <<EOF
Usage:
  $0 apply RELEASE_ID [--profile orcarouter] [--dry-run]
  $0 recover
  $0 service-recover
  $0 status

apply performs one release+manifest transaction. The managed service is restarted
only after both the qualified target release and H38 target manifest are active.
recover restores the exact previous release-pointer pair and manifest.
service-recover is called by service-runner after an interrupted host/process run.
EOF
}

die() { printf 'FATAL: %s\n' "$*" >&2; exit 1; }
sha256_file() {
  python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$1"
}
read_link_id() {
  local link="$1" target
  [[ -L "${link}" ]] || return 1
  target="$(readlink -f -- "${link}")"
  [[ "${target}" == "${RELEASES_DIR}/"* ]] || die "unsafe release pointer: ${link}"
  basename -- "${target}"
}
atomic_link() {
  local target="$1" link="$2" tmp="${2}.tmp.$$"
  mkdir -p -- "$(dirname -- "${link}")"
  ln -s -- "${target}" "${tmp}"
  mv -Tf -- "${tmp}" "${link}"
}
clear_link() { [[ ! -e "$1" && ! -L "$1" ]] || rm -f -- "$1"; }
atomic_copy() {
  local source="$1" destination="$2"
  [[ -f "${source}" && ! -L "${source}" ]] || die "unsafe or missing source file: ${source}"
  cp -p -- "${source}" "${destination}.tmp"
  mv -- "${destination}.tmp" "${destination}"
}

parse_state_into_vars() {
  local schema="$1" path="$2" prefix="${3:-}" parsed key value
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" "${schema}" "${path}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    printf -v "${prefix}${key}" '%s' "${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
}

parse_manifest() {
  local path="$1" prefix="$2"
  parse_state_into_vars install-maintenance "${path}" "${prefix}_"
}

write_state() {
  local phase="$1" target_sha="${2:-${TARGET_MANIFEST_SHA256:-}}"
  mkdir -p -- "${STATE_HOME}"
  umask 077
  {
    printf 'RELEASE_PROFILE_REFRESH_SCHEMA_VERSION=1\n'
    printf 'RELEASE_PROFILE_REFRESH_STATE=%s\n' "${phase}"
    printf 'TARGET_RELEASE=%s\n' "${TARGET_RELEASE}"
    printf 'OLD_CURRENT_RELEASE=%s\n' "${OLD_CURRENT_RELEASE}"
    printf 'OLD_PREVIOUS_RELEASE=%s\n' "${OLD_PREVIOUS_RELEASE:-}"
    printf 'RELEASE_MANIFEST_SHA256=%s\n' "${RELEASE_MANIFEST_SHA256}"
    printf 'BACKUP_MANIFEST=%s\n' "${BACKUP_MANIFEST}"
    printf 'BACKUP_SHA256=%s\n' "${BACKUP_SHA256}"
    printf 'TARGET_MANIFEST=%s\n' "${TARGET_MANIFEST}"
    printf 'TARGET_MANIFEST_SHA256=%s\n' "${target_sha}"
    printf 'PROFILE=%s\n' "${PROFILE}"
    printf 'OLD_IMAGE=%s\n' "${OLD_IMAGE}"
    printf 'TARGET_IMAGE=%s\n' "${TARGET_IMAGE}"
    printf 'SERVED_NAME=%s\n' "${TARGET_SERVED_NAME}"
    printf 'UPDATED_AT=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  } >"${STATE_FILE}.tmp"
  python3 "${STATE_PARSER}" release-profile-refresh "${STATE_FILE}.tmp" >/dev/null
  mv -- "${STATE_FILE}.tmp" "${STATE_FILE}"
}

load_state() {
  [[ -f "${STATE_FILE}" && ! -L "${STATE_FILE}" ]] || die 'no release-profile refresh transaction is active'
  unset RELEASE_PROFILE_REFRESH_SCHEMA_VERSION RELEASE_PROFILE_REFRESH_STATE
  unset TARGET_RELEASE OLD_CURRENT_RELEASE OLD_PREVIOUS_RELEASE RELEASE_MANIFEST_SHA256
  unset BACKUP_SHA256 TARGET_MANIFEST_SHA256 PROFILE OLD_IMAGE TARGET_IMAGE SERVED_NAME UPDATED_AT
  parse_state_into_vars release-profile-refresh "${STATE_FILE}" || die "invalid release-profile refresh state: ${STATE_FILE}"
  [[ "${BACKUP_MANIFEST}" == "${INSTALL_STATE_FILE}.release-profile-refresh-backup" ]] || die 'refresh backup path mismatch'
  [[ "${TARGET_MANIFEST}" == "${INSTALL_STATE_FILE}.release-profile-refresh-candidate" ]] || die 'refresh candidate path mismatch'
  TARGET_SERVED_NAME="${SERVED_NAME}"
}

clear_transaction() {
  rm -f -- "${STATE_FILE}" "${STATE_FILE}.tmp" "${BACKUP_MANIFEST}" "${BACKUP_MANIFEST}.tmp"     "${TARGET_MANIFEST}" "${TARGET_MANIFEST}.tmp"
}

acquire_transition_lock() {
  local label="$1"
  export QWEN38_RELEASE_PROFILE_REFRESH_CONTEXT=1
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

sudo_with_operation_lock() {
  sudo env     QWEN38_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}"     QWEN38_OPERATION_LOCK_HELD="${QWEN38_OPERATION_LOCK_HELD}"     QWEN38_OPERATION_LOCK_FILE="${QWEN38_OPERATION_LOCK_FILE}"     QWEN38_OPERATION_LOCK_OWNER_PID="${QWEN38_OPERATION_LOCK_OWNER_PID}"     QWEN38_RELEASE_PROFILE_REFRESH_CONTEXT=1     "$@"
}

verify_no_conflicting_transactions() {
  local path
  for path in     "${UPDATE_STATE_FILE}"     "${PROFILE_SWITCH_STATE_FILE}"     "${RUNTIME_TRANSITION_FILE}"     "${SETTINGS_PHASE_FILE}"     "${INSTALL_STATE_FILE}.profile-switch-backup"     "${INSTALL_STATE_FILE}.profile-switch-candidate"     "${INSTALL_STATE_FILE}.settings-backup"     "${INSTALL_STATE_FILE}.settings-candidate"; do
    [[ ! -e "${path}" && ! -L "${path}" ]] || die "conflicting or stale lifecycle artifact exists: ${path}"
  done
}

verify_bound_qualification() {
  local release_id="$1" marker manifest_path parsed key value qualified="" digest="" observed=""
  marker="${QUALIFIED_DIR}/${release_id}.env"
  manifest_path="${RELEASES_DIR}/${release_id}/.release-manifest.json"
  bash "${RELEASE_MANAGER}" verify "${release_id}" >/dev/null
  [[ -f "${marker}" && ! -L "${marker}" ]] || die "release is not qualified: ${release_id}"
  [[ -f "${manifest_path}" && ! -L "${manifest_path}" ]] || die "release manifest is unavailable: ${release_id}"
  parsed="$(mktemp)"
  if ! python3 "${QUALIFICATION_PARSER}" "${marker}" --require-bound >"${parsed}"; then
    rm -f -- "${parsed}"
    die "qualification marker is invalid or not manifest-bound: ${release_id}"
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    case "${key}" in
      QUALIFIED_RELEASE) qualified="${value}" ;;
      RELEASE_MANIFEST_SHA256) digest="${value}" ;;
    esac
  done <"${parsed}"
  rm -f -- "${parsed}"
  [[ "${qualified}" == "${release_id}" ]] || die "qualification marker release mismatch: ${release_id}"
  observed="$(sha256_file "${manifest_path}")"
  [[ "${digest}" == "${observed}" ]] || die "qualification manifest digest mismatch: ${release_id}"
  RELEASE_MANIFEST_SHA256="${observed}"
}

ensure_qualified_release() {
  local release_id="$1" marker="${QUALIFIED_DIR}/$1.env"
  if [[ ! -d "${RELEASES_DIR}/${release_id}" ]]; then
    bash "${RELEASE_MANAGER}" stage "${release_id}"
  fi
  if [[ ! -f "${marker}" || -L "${marker}" ]]; then
    [[ ! -L "${marker}" ]] || die "qualification marker is unsafe: ${marker}"
    bash "${QUALIFY_RELEASE}" "${release_id}"
  fi
  verify_bound_qualification "${release_id}"
}

verify_recorded_target_release() {
  local expected="${RELEASE_MANIFEST_SHA256}" observed marker parsed key value
  local qualified="" qualified_digest=""
  [[ "${expected}" =~ ^[0-9a-f]{64}$ ]] || {
    printf 'ERROR: recorded target release manifest digest is invalid\n' >&2
    return 1
  }
  bash "${RELEASE_MANAGER}" verify "${TARGET_RELEASE}" >/dev/null || return 1
  observed="$(sha256_file "${RELEASES_DIR}/${TARGET_RELEASE}/.release-manifest.json")" || return 1
  [[ "${observed}" == "${expected}" ]] || {
    printf 'ERROR: target release manifest drift: recorded=%s observed=%s\n' "${expected}" "${observed}" >&2
    return 1
  }
  marker="${QUALIFIED_DIR}/${TARGET_RELEASE}.env"
  [[ -f "${marker}" && ! -L "${marker}" ]] || {
    printf 'ERROR: target release qualification marker is missing or unsafe\n' >&2
    return 1
  }
  parsed="$(mktemp)"
  if ! python3 "${QUALIFICATION_PARSER}" "${marker}" --require-bound >"${parsed}"; then
    rm -f -- "${parsed}"
    printf 'ERROR: target release qualification marker is invalid\n' >&2
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    case "${key}" in
      QUALIFIED_RELEASE) qualified="${value}" ;;
      RELEASE_MANIFEST_SHA256) qualified_digest="${value}" ;;
    esac
  done <"${parsed}"
  rm -f -- "${parsed}"
  [[ "${qualified}" == "${TARGET_RELEASE}" && "${qualified_digest}" == "${expected}" ]] || {
    printf 'ERROR: target release qualification binding drift\n' >&2
    return 1
  }
}

verify_target_manifest_binding() {
  [[ -f "${TARGET_MANIFEST}" && ! -L "${TARGET_MANIFEST}" ]] || {
    printf 'ERROR: target refresh manifest is missing or unsafe\n' >&2
    return 1
  }
  [[ -f "${INSTALL_STATE_FILE}" && ! -L "${INSTALL_STATE_FILE}" ]] || {
    printf 'ERROR: live install manifest is missing or unsafe\n' >&2
    return 1
  }
  [[ "$(sha256_file "${TARGET_MANIFEST}")" == "${TARGET_MANIFEST_SHA256}" ]] || {
    printf 'ERROR: target refresh manifest digest drift\n' >&2
    return 1
  }
  python3 - "${STATE_PARSER}" "${TARGET_MANIFEST}" "${INSTALL_STATE_FILE}" <<'PY'
import importlib.util
import pathlib
import sys

parser_path, candidate_path, live_path = sys.argv[1:]
spec = importlib.util.spec_from_file_location("qwen38_state_file", parser_path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
candidate = module.parse_install(pathlib.Path(candidate_path), "install-maintenance")
live = module.parse_install(pathlib.Path(live_path), "install-maintenance")
if candidate["PHASE"] != "service_ready":
    raise SystemExit("target refresh manifest is not service_ready")
if live["PHASE"] not in {"service_ready", "complete"}:
    raise SystemExit("live refresh manifest has invalid phase")
expected = dict(candidate)
expected["PHASE"] = live["PHASE"]
if live != expected:
    raise SystemExit("live install manifest drifted from target refresh manifest")
PY
}

load_target_profile_defaults() {
  local target_root="$1" model_root
  [[ -r "${target_root}/scripts/model-profiles.sh" ]] || die 'target release has no model profile registry'
  model_root="$(dirname -- "${CURRENT_MODEL_DIR}")"
  export QWEN38_MODEL_ROOT="${model_root}"
  # The file is inside a manifest-bound qualified immutable release.
  # shellcheck disable=SC1090
  source "${target_root}/scripts/model-profiles.sh"
  load_model_profile "${PROFILE}" || die "target release cannot load profile: ${PROFILE}"
  TARGET_REPO="${PROFILE_REPO}"
  TARGET_REVISION="${PROFILE_REVISION}"
  TARGET_MODEL_DIR="${PROFILE_MODEL_DIR}"
  TARGET_IMAGE="${PROFILE_IMAGE}"
  TARGET_SERVED_NAME="${PROFILE_SERVED_NAME}"
  [[ "${TARGET_IMAGE}" == "${TARGET_H38_IMAGE}" ]] || die "target profile image is not managed H38: ${TARGET_IMAGE}"
  [[ "${CURRENT_MODEL_REPO}" == "${TARGET_REPO}" ]] || die 'same-profile refresh cannot change MODEL_REPO'
  [[ "${CURRENT_MODEL_REVISION}" == "${TARGET_REVISION}" ]] || die 'same-profile refresh cannot change MODEL_REVISION'
  [[ "$(realpath -m -- "${CURRENT_MODEL_DIR}")" == "$(realpath -m -- "${TARGET_MODEL_DIR}")" ]] || die 'same-profile refresh cannot change MODEL_DIR'
  [[ "${CURRENT_SERVED_NAME}" == "${TARGET_SERVED_NAME}" ]] || die 'same-profile refresh cannot change served model identity'
}

track_h38_assets() {
  local target_root="$1" tool="${target_root}/scripts/lib/asset_ownership.py"
  local image dependency="" owned
  local -a chain=(
    vllm-orcarouter-v029:v1
    vllm-orcarouter-v029-h9-ct-modelweight:v1
    vllm-orcarouter-v029-h10-ct-global-scale:v1
    vllm-orcarouter-v029-h11-ct-packed-modelweight:v1
    vllm-orcarouter-v029-h12-ct-postload-preserve:v1
    vllm-orcarouter-v029-h38-decoder-scope:v1
  )
  [[ -r "${tool}" ]] || die 'target release has no asset ownership helper'
  python3 "${tool}" bootstrap-install "${ASSET_OWNERSHIP_FILE}" "${INSTALL_STATE_FILE}" "${target_root}/scripts/lib/state_file.py"
  for image in "${chain[@]}"; do
    if python3 "${tool}" owns-image "${ASSET_OWNERSHIP_FILE}" "${image}" >/dev/null 2>&1; then
      owned=1
    elif docker image inspect "${image}" >/dev/null 2>&1; then
      owned=0
    else
      owned=1
    fi
    H38_OWNERSHIP["${image}"]="${owned}"
    args=(track-image "${ASSET_OWNERSHIP_FILE}" "${image}" --owned "${owned}")
    [[ -z "${dependency}" ]] || args+=(--depends "${dependency}")
    python3 "${tool}" "${args[@]}"
    dependency="${image}"
  done
}

finalize_h38_assets() {
  local target_root="$1" tool="${target_root}/scripts/lib/asset_ownership.py"
  local image dependency="" owned
  local -a chain=(
    vllm-orcarouter-v029:v1
    vllm-orcarouter-v029-h9-ct-modelweight:v1
    vllm-orcarouter-v029-h10-ct-global-scale:v1
    vllm-orcarouter-v029-h11-ct-packed-modelweight:v1
    vllm-orcarouter-v029-h12-ct-postload-preserve:v1
    vllm-orcarouter-v029-h38-decoder-scope:v1
  )
  for image in "${chain[@]}"; do
    owned="${H38_OWNERSHIP[${image}]}"
    args=(track-image "${ASSET_OWNERSHIP_FILE}" "${image}" --owned "${owned}")
    [[ -z "${dependency}" ]] || args+=(--depends "${dependency}")
    python3 "${tool}" "${args[@]}"
    dependency="${image}"
  done
}

build_target_manifest() {
  local target_root="$1" image_owned="$2"
  python3 - "${STATE_PARSER}" "${INSTALL_STATE_FILE}" "${TARGET_MANIFEST}.tmp"     "${target_root}" "${TARGET_IMAGE}" "${TARGET_SERVED_NAME}" "${image_owned}" <<'PY'
import importlib.util
import pathlib
import shlex
import sys

parser_path, source_path, target_path, install_root, image, served_name, image_owned = sys.argv[1:]
spec = importlib.util.spec_from_file_location("qwen38_state_file", parser_path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
source = pathlib.Path(source_path)
target = pathlib.Path(target_path)
values = module.parse_install(source, "install-maintenance")
if values["PHASE"] != "complete":
    raise SystemExit("source install manifest must be complete")
values["PHASE"] = "service_ready"
values["INSTALL_ROOT"] = install_root
values["VLLM_IMAGE"] = image
values["IMAGE_OWNED"] = image_owned
values["SERVED_NAME"] = served_name
ordered_keys = [key for _, key, _ in module.read_assignments(source)]
if set(ordered_keys) != set(values):
    raise SystemExit("install manifest key set changed during refresh")
target.write_text(
    "".join(f"{key}={shlex.quote(values[key])}\n" for key in ordered_keys),
    encoding="utf-8",
)
target.chmod(source.stat().st_mode & 0o777)
module.parse_install(target, "install-service-runtime")
PY
  mv -- "${TARGET_MANIFEST}.tmp" "${TARGET_MANIFEST}"
}

set_live_manifest_complete() {
  local temporary="${INSTALL_STATE_FILE}.release-profile-refresh-complete.tmp"
  python3 - "${STATE_PARSER}" "${INSTALL_STATE_FILE}" "${temporary}" <<'PY'
import importlib.util
import pathlib
import shlex
import sys

parser_path, source_path, target_path = sys.argv[1:]
spec = importlib.util.spec_from_file_location("qwen38_state_file", parser_path)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)
source = pathlib.Path(source_path)
target = pathlib.Path(target_path)
module.parse_install(source, "install-service-runtime")
values = module.parse_install(source, "install-maintenance")
values["PHASE"] = "complete"
ordered_keys = [key for _, key, _ in module.read_assignments(source)]
target.write_text(
    "".join(f"{key}={shlex.quote(values[key])}\n" for key in ordered_keys),
    encoding="utf-8",
)
target.chmod(source.stat().st_mode & 0o777)
module.parse_install(target, "install-runtime")
PY
  mv -- "${temporary}" "${INSTALL_STATE_FILE}"
}

activate_pair() {
  write_state activating "${TARGET_MANIFEST_SHA256}"
  atomic_link "${RELEASES_DIR}/${OLD_CURRENT_RELEASE}" "${PREVIOUS_LINK}"
  atomic_link "${RELEASES_DIR}/${TARGET_RELEASE}" "${CURRENT_LINK}"
  atomic_copy "${TARGET_MANIFEST}" "${INSTALL_STATE_FILE}"
  write_state activated "${TARGET_MANIFEST_SHA256}"
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

restore_previous_pair() {
  local runtime_helper="${RELEASES_DIR}/${TARGET_RELEASE}/scripts/runtime/runtime-transition.sh"
  [[ -f "${BACKUP_MANIFEST}" && ! -L "${BACKUP_MANIFEST}" ]] || die 'refresh backup manifest is missing'
  [[ "$(sha256_file "${BACKUP_MANIFEST}")" == "${BACKUP_SHA256}" ]] || die 'refresh backup manifest digest mismatch'
  [[ -r "${runtime_helper}" ]] || die 'target runtime recovery helper is unavailable'
  bash "${runtime_helper}" recover
  verify_previous_runtime_restored
  restore_pointer "${CURRENT_LINK}" "${OLD_CURRENT_RELEASE}"
  restore_pointer "${PREVIOUS_LINK}" "${OLD_PREVIOUS_RELEASE:-}"
  atomic_copy "${BACKUP_MANIFEST}" "${INSTALL_STATE_FILE}"
  rm -f -- "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"
}

target_runtime_committed() {
  local target_root="${RELEASES_DIR}/${TARGET_RELEASE}" current_root container_id image scope
  verify_recorded_target_release || return 1
  verify_target_manifest_binding || return 1
  python3 "${STATE_PARSER}" install-service-runtime "${INSTALL_STATE_FILE}" >/dev/null || return 1
  parse_manifest "${INSTALL_STATE_FILE}" LIVE || return 1
  [[ "${LIVE_PHASE}" == service_ready || "${LIVE_PHASE}" == complete ]] || return 1
  [[ "${LIVE_MODEL_PROFILE}" == "${PROFILE}" ]] || return 1
  [[ "${LIVE_VLLM_IMAGE}" == "${TARGET_IMAGE}" ]] || return 1
  [[ "${LIVE_SERVED_NAME}" == "${TARGET_SERVED_NAME}" ]] || return 1
  [[ "$(realpath -m -- "${LIVE_INSTALL_ROOT}")" == "$(realpath -m -- "${target_root}")" ]] || return 1
  [[ -f "${RUNTIME_COMMIT_FILE}" && ! -L "${RUNTIME_COMMIT_FILE}" ]] || return 1
  parse_state_into_vars runtime-commit "${RUNTIME_COMMIT_FILE}" ATTEST_ || return 1
  current_root="$(readlink -f -- "${CURRENT_LINK}" 2>/dev/null || true)"
  [[ "${current_root}" == "${target_root}" && "${ATTEST_RUNTIME_ROOT}" == "${target_root}" ]] || return 1
  container_id="$(docker inspect --format '{{.Id}}' qwen38-flash-next 2>/dev/null || true)"
  [[ -n "${container_id}" && "${container_id}" == "${ATTEST_RUNTIME_CONTAINER_ID}" ]] || return 1
  image="$(docker inspect --format '{{.Config.Image}}' qwen38-flash-next 2>/dev/null || true)"
  [[ "${image}" == "${TARGET_IMAGE}" ]] || return 1
  [[ "$(docker inspect --format '{{.State.Running}}' qwen38-flash-next 2>/dev/null || true)" == true ]] || return 1
  [[ "$(docker inspect --format '{{.State.OOMKilled}}' qwen38-flash-next 2>/dev/null || true)" == false ]] || return 1
  scope="$(docker image inspect --format '{{ index .Config.Labels "qwen38.h38scope" }}' "${TARGET_IMAGE}" 2>/dev/null || true)"
  [[ "${scope}" == "${TARGET_H38_SCOPE}" ]]
}

verify_previous_runtime_baseline() {
  local old_root="${RELEASES_DIR}/${OLD_CURRENT_RELEASE}" container_id image running oom models
  [[ -f "${RUNTIME_COMMIT_FILE}" && ! -L "${RUNTIME_COMMIT_FILE}" ]] || die 'previous runtime attestation is missing'
  parse_state_into_vars runtime-commit "${RUNTIME_COMMIT_FILE}" PREVIOUS_ATTEST_ || die 'previous runtime attestation is invalid'
  container_id="$(docker inspect --format '{{.Id}}' qwen38-flash-next 2>/dev/null || true)"
  [[ -n "${container_id}" && "${container_id}" == "${PREVIOUS_ATTEST_RUNTIME_CONTAINER_ID}" ]] || die 'previous runtime container does not match its attestation'
  [[ "${PREVIOUS_ATTEST_RUNTIME_ROOT}" == "${old_root}" ]] || die 'previous runtime attestation is not bound to the current immutable release'
  image="$(docker inspect --format '{{.Config.Image}}' qwen38-flash-next 2>/dev/null || true)"
  [[ "${image}" == "${OLD_IMAGE}" ]] || die "previous runtime image drift: expected=${OLD_IMAGE} observed=${image:-missing}"
  running="$(docker inspect --format '{{.State.Running}}' qwen38-flash-next 2>/dev/null || true)"
  oom="$(docker inspect --format '{{.State.OOMKilled}}' qwen38-flash-next 2>/dev/null || true)"
  [[ "${running}" == true ]] || die 'previous runtime is not running before atomic refresh'
  [[ "${oom}" == false ]] || die 'previous runtime is OOMKilled before atomic refresh'
  curl -fsS --max-time 3 http://127.0.0.1:8888/health >/dev/null || die 'previous runtime health endpoint is not ready'
  models="$(curl -fsS --max-time 15 http://127.0.0.1:8888/v1/models)" || die 'previous runtime model list is unavailable'
  python3 -c 'import json,sys; expected=sys.argv[1]; data=json.load(sys.stdin); assert any(item.get("id") == expected for item in data.get("data", [])), expected'     "${CURRENT_SERVED_NAME}" <<<"${models}" || die 'previous runtime served model identity mismatch'
}

verify_previous_runtime_restored() {
  local image oom
  image="$(docker inspect --format '{{.Config.Image}}' qwen38-flash-next 2>/dev/null || true)"
  [[ "${image}" == "${OLD_IMAGE}" ]] || die "previous runtime cannot be proven after rollback: expected=${OLD_IMAGE} observed=${image:-missing}"
  oom="$(docker inspect --format '{{.State.OOMKilled}}' qwen38-flash-next 2>/dev/null || true)"
  [[ "${oom}" == false ]] || die 'restored previous runtime is OOMKilled'
  docker inspect qwen38-flash-next.rollback >/dev/null 2>&1 && die 'rollback container remains after previous runtime restoration'
}

commit_deferred_runtime_transition() {
  local runtime_helper="${RELEASES_DIR}/${TARGET_RELEASE}/scripts/runtime/runtime-transition.sh"
  local parsed key value state="" current="" rollback="" had_previous=""
  [[ -r "${runtime_helper}" ]] || die 'target runtime transition helper is unavailable'
  if [[ -f "${RUNTIME_TRANSITION_FILE}" && ! -L "${RUNTIME_TRANSITION_FILE}" ]]; then
    parsed="$(mktemp)"
    if ! python3 "${STATE_PARSER}" runtime-transition "${RUNTIME_TRANSITION_FILE}" >"${parsed}"; then
      rm -f -- "${parsed}"
      die 'deferred runtime transition state is invalid'
    fi
    while IFS= read -r -d '' key && IFS= read -r -d '' value; do
      case "${key}" in
        TRANSACTION_STATE) state="${value}" ;;
        CURRENT_CONTAINER) current="${value}" ;;
        ROLLBACK_CONTAINER) rollback="${value}" ;;
        HAD_PREVIOUS) had_previous="${value}" ;;
      esac
    done <"${parsed}"
    rm -f -- "${parsed}"
    [[ "${state}" == validating && "${current}" == qwen38-flash-next &&
       "${rollback}" == qwen38-flash-next.rollback && "${had_previous}" == 1 ]] ||       die 'deferred runtime transition is not the expected validating replacement'
    docker inspect qwen38-flash-next.rollback >/dev/null 2>&1 || die 'deferred runtime rollback container is missing'
    bash "${runtime_helper}" commit
  elif docker inspect qwen38-flash-next.rollback >/dev/null 2>&1; then
    die 'orphan rollback container exists without deferred runtime transaction state'
  fi
  [[ ! -e "${RUNTIME_TRANSITION_FILE}" && ! -L "${RUNTIME_TRANSITION_FILE}" ]] || die 'runtime transition did not commit'
  docker inspect qwen38-flash-next.rollback >/dev/null 2>&1 && die 'runtime rollback container survived commit'
}

finish_proven_target() {
  target_runtime_committed || return 1
  commit_deferred_runtime_transition
  write_state runtime_committed "${TARGET_MANIFEST_SHA256}"
  set_live_manifest_complete
  write_state committing "${TARGET_MANIFEST_SHA256}"
  target_runtime_committed || die 'target runtime proof changed during lifecycle commit'
  clear_transaction
}

restart_previous_service() {
  local manager="${CURRENT_LINK}/scripts/manage-service.sh"
  [[ -r "${manager}" ]] || die 'restored release has no service manager'
  command -v sudo >/dev/null 2>&1 || die 'sudo is required to restore the managed service'
  sudo_with_operation_lock bash "${manager}" create --runtime-root "${CURRENT_LINK}" --start --yes
}

rollback_active_transaction() {
  local restart="${1:-0}"
  load_state
  case "${RELEASE_PROFILE_REFRESH_STATE}" in
    preparing|assets_ready|candidate_prepared)
      clear_transaction
      printf 'Release-profile refresh rolled back before activation.\n'
      ;;
    activating|activated|runtime_validating)
      if target_runtime_committed; then
        finish_proven_target
        printf 'Release-profile refresh recovered fully attested target before rollback.\n'
      else
        write_state rolling_back "${TARGET_MANIFEST_SHA256}"
        restore_previous_pair
        clear_transaction
        if [[ "${restart}" == 1 ]]; then restart_previous_service; fi
        printf 'Release-profile refresh restored previous release + manifest + runtime pair.\n'
      fi
      ;;
    runtime_committed|committing)
      target_runtime_committed || die 'runtime was already committed but target proof is incomplete; refusing ambiguous rollback'
      finish_proven_target
      printf 'Release-profile refresh recovered committed target.\n'
      ;;
    rolling_back)
      restore_previous_pair
      clear_transaction
      if [[ "${restart}" == 1 ]]; then restart_previous_service; fi
      printf 'Interrupted release-profile rollback completed.\n'
      ;;
    *) die "unsupported release-profile refresh state: ${RELEASE_PROFILE_REFRESH_STATE}" ;;
  esac
}

declare -A H38_OWNERSHIP=()

[[ -r "${STATE_PARSER}" ]] || die "strict state parser is unavailable: ${STATE_PARSER}"
[[ $# -ge 1 ]] || { usage >&2; exit 2; }
action="$1"; shift

case "${action}" in
  apply)
    [[ $# -ge 1 ]] || { usage >&2; exit 2; }
    TARGET_RELEASE="$1"; shift
    PROFILE="${TARGET_PROFILE}"
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --profile) [[ $# -ge 2 ]] || die '--profile requires a value'; PROFILE="$2"; shift ;;
        --dry-run) DRY_RUN=1 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown argument: $1" ;;
      esac
      shift
    done
    [[ "${TARGET_RELEASE}" =~ ^[0-9a-f]{12,40}$ ]] || die "invalid release id: ${TARGET_RELEASE}"
    [[ "${PROFILE}" == "${TARGET_PROFILE}" ]] || die 'cross-release refresh currently supports only the orcarouter H38 target'
    if [[ "${DRY_RUN}" != 1 ]]; then
      acquire_transition_lock "release-profile refresh to ${TARGET_RELEASE}"
    fi
    [[ ! -e "${STATE_FILE}" && ! -L "${STATE_FILE}" ]] || die 'a release-profile refresh is already active; recover it first'
    [[ ! -e "${BACKUP_MANIFEST}" && ! -L "${BACKUP_MANIFEST}" ]] || die "stale refresh backup exists: ${BACKUP_MANIFEST}"
    [[ ! -e "${TARGET_MANIFEST}" && ! -L "${TARGET_MANIFEST}" ]] || die "stale refresh candidate exists: ${TARGET_MANIFEST}"
    verify_no_conflicting_transactions
    [[ -f "${INSTALL_STATE_FILE}" && ! -L "${INSTALL_STATE_FILE}" ]] || die 'installation manifest is missing or unsafe'
    parse_manifest "${INSTALL_STATE_FILE}" CURRENT || die 'installation manifest failed strict maintenance parsing'
    [[ "${CURRENT_PHASE}" == complete ]] || die "refresh requires a complete installation manifest (found ${CURRENT_PHASE})"
    [[ "${CURRENT_MODEL_PROFILE}" == "${PROFILE}" ]] || die "refresh profile does not match live manifest: ${CURRENT_MODEL_PROFILE}"
    [[ "${CURRENT_SERVICE_ENABLED}" == 1 && "${CURRENT_SERVICE_OWNED}" == 1 ]] || die 'refresh requires the owned managed systemd service'
    OLD_CURRENT_RELEASE="$(read_link_id "${CURRENT_LINK}")" || die 'no safe immutable current release is registered'
    OLD_PREVIOUS_RELEASE=""
    if [[ -e "${PREVIOUS_LINK}" || -L "${PREVIOUS_LINK}" ]]; then
      OLD_PREVIOUS_RELEASE="$(read_link_id "${PREVIOUS_LINK}")" || die 'previous release pointer is unsafe'
    fi
    OLD_IMAGE="${CURRENT_VLLM_IMAGE}"

    if [[ "${DRY_RUN}" == 1 ]]; then
      verify_bound_qualification "${TARGET_RELEASE}"
    else
      ensure_qualified_release "${TARGET_RELEASE}"
    fi
    target_root="${RELEASES_DIR}/${TARGET_RELEASE}"
    [[ "$(readlink -f -- "${target_root}" 2>/dev/null || realpath -m -- "${target_root}")" == "${target_root}" ]] || die 'target release path is unsafe'
    load_target_profile_defaults "${target_root}"

    if [[ "${DRY_RUN}" == 1 ]]; then
      printf 'DRY-RUN: qualified target release %s (manifest=%s)\n' "${TARGET_RELEASE}" "${RELEASE_MANIFEST_SHA256}"
      printf 'DRY-RUN: current pair release=%s image=%s\n' "${OLD_CURRENT_RELEASE}" "${OLD_IMAGE}"
      printf 'DRY-RUN: target pair release=%s image=%s profile=%s served=%s\n'         "${TARGET_RELEASE}" "${TARGET_IMAGE}" "${PROFILE}" "${TARGET_SERVED_NAME}"
      printf 'DRY-RUN: no release pointer, manifest, Docker image, service, or transaction state mutated.\n'
      exit 0
    fi

    command -v docker >/dev/null 2>&1 || die 'docker is required'
    command -v sudo >/dev/null 2>&1 || die 'sudo is required'
    command -v curl >/dev/null 2>&1 || die 'curl is required'
    verify_previous_runtime_baseline
    atomic_copy "${INSTALL_STATE_FILE}" "${BACKUP_MANIFEST}"
    BACKUP_SHA256="$(sha256_file "${BACKUP_MANIFEST}")"
    TARGET_MANIFEST_SHA256=""
    write_state preparing ""

    rollback_refresh() {
      local rc="${1:-1}"
      trap - ERR INT TERM EXIT
      set +e
      if [[ -e "${STATE_FILE}" && ! -L "${STATE_FILE}" ]]; then
        printf 'Release-profile refresh failed; recovering transaction.\n' >&2
        if ! rollback_active_transaction 1; then
          printf 'FATAL: automatic cross-release recovery failed; transaction state was retained when possible.\n' >&2
          exit 70
        fi
      fi
      exit "${rc}"
    }
    trap 'rollback_refresh $?' ERR
    trap 'rollback_refresh 130' INT
    trap 'rollback_refresh 143' TERM
    trap 'rollback_refresh $?' EXIT

    track_h38_assets "${target_root}"
    bash "${target_root}/scripts/runtime/prepare-h38-image.sh" build
    bash "${target_root}/scripts/runtime/prepare-h38-image.sh" verify
    finalize_h38_assets "${target_root}"
    target_owned=0
    python3 "${target_root}/scripts/lib/asset_ownership.py" owns-image "${ASSET_OWNERSHIP_FILE}" "${TARGET_IMAGE}" >/dev/null 2>&1 && target_owned=1
    write_state assets_ready ""

    build_target_manifest "${target_root}" "${target_owned}"
    TARGET_MANIFEST_SHA256="$(sha256_file "${TARGET_MANIFEST}")"
    write_state candidate_prepared "${TARGET_MANIFEST_SHA256}"

    # Building the image can take long enough for an unrelated runtime failure.
    # Re-prove the exact previous runtime immediately before crossing the pair boundary.
    verify_previous_runtime_baseline
    activate_pair
    write_state runtime_validating "${TARGET_MANIFEST_SHA256}"
    sudo_with_operation_lock bash "${target_root}/scripts/manage-service.sh" create --runtime-root "${CURRENT_LINK}" --start --yes
    target_runtime_committed || die 'target runtime readiness/identity/attestation proof failed'
    finish_proven_target
    trap - ERR INT TERM EXIT
    printf 'Atomic release-profile refresh committed: release=%s image=%s profile=%s\n'       "${TARGET_RELEASE}" "${TARGET_IMAGE}" "${PROFILE}"
    ;;
  recover)
    [[ $# -eq 0 ]] || { usage >&2; exit 2; }
    acquire_transition_lock "release-profile refresh recovery"
    if [[ ! -e "${STATE_FILE}" && ! -L "${STATE_FILE}" ]]; then
      [[ ! -e "${BACKUP_MANIFEST}" && ! -e "${TARGET_MANIFEST}" ]] || die 'refresh artifacts exist without transaction state; refusing ambiguous recovery'
      printf 'RELEASE_PROFILE_REFRESH_STATE=idle\n'
      exit 0
    fi
    rollback_active_transaction 1
    ;;
  service-recover)
    [[ $# -eq 0 ]] || { usage >&2; exit 2; }
    [[ -e "${STATE_FILE}" || -L "${STATE_FILE}" ]] || exit 0
    if operation_lock_busy; then
      printf 'Release-profile refresh startup recovery deferred: lifecycle lock is active.\n'
      exit 0
    fi
    acquire_transition_lock "release-profile refresh service startup recovery"
    load_state
    case "${RELEASE_PROFILE_REFRESH_STATE}" in
      activating|activated|runtime_validating)
        if target_runtime_committed; then
          finish_proven_target
          printf 'Release-profile refresh startup recovery completed fully attested target.\n'
          exit 0
        fi
        ;;
      runtime_committed|committing)
        target_runtime_committed || die 'committed refresh target cannot be proven during service recovery'
        finish_proven_target
        printf 'Release-profile refresh startup recovery completed committed target.\n'
        exit 0
        ;;
    esac
    write_state rolling_back "${TARGET_MANIFEST_SHA256}"
    restore_previous_pair
    clear_transaction
    printf 'Interrupted release-profile refresh restored previous release + manifest + runtime pair; forcing service retry.\n' >&2
    exit 75
    ;;
  status)
    [[ $# -eq 0 ]] || { usage >&2; exit 2; }
    if [[ -r "${STATE_FILE}" ]]; then
      python3 "${STATE_PARSER}" release-profile-refresh "${STATE_FILE}" >/dev/null || die 'invalid release-profile refresh state'
      cat "${STATE_FILE}"
    else
      printf 'RELEASE_PROFILE_REFRESH_STATE=idle\n'
    fi
    ;;
  -h|--help) usage ;;
  *) usage >&2; exit 2 ;;
esac
