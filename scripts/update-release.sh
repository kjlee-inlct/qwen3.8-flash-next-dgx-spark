#!/usr/bin/env bash
# Cut over a qualified immutable release and roll back code/service on failure.
set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
CURRENT_LINK="${QWEN38_CURRENT_RELEASE_LINK:-${DATA_HOME}/current}"
RELEASE_MANAGER="${SCRIPT_ROOT}/scripts/release-manager.sh"
UPDATE_TRANSITION="${SCRIPT_ROOT}/scripts/update-transition.sh"
MANAGE_SERVICE="${SCRIPT_ROOT}/scripts/manage-service.sh"
QUALIFICATION_PARSER="${SCRIPT_ROOT}/scripts/lib/qualification_marker.py"
OPERATION_LOCK_LIB="${SCRIPT_ROOT}/scripts/lib/operation-lock.sh"
DRY_RUN=0

usage() {
  printf 'Usage: %s RELEASE_ID [--dry-run]\n' "$0"
}
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
sudo_with_operation_lock() {
  sudo env \
    QWEN38_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}" \
    QWEN38_OPERATION_LOCK_HELD="${QWEN38_OPERATION_LOCK_HELD}" \
    QWEN38_OPERATION_LOCK_FILE="${QWEN38_OPERATION_LOCK_FILE}" \
    QWEN38_OPERATION_LOCK_OWNER_PID="${QWEN38_OPERATION_LOCK_OWNER_PID}" \
    "$@"
}
manifest_digest() {
  python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$1"
}
verify_bound_qualification() {
  local release_id="$1" marker manifest_path parsed key value schema qualified digest observed
  marker="${DATA_HOME}/qualified/${release_id}.env"
  manifest_path="${DATA_HOME}/releases/${release_id}/.release-manifest.json"
  [[ -f "${marker}" && ! -L "${marker}" ]] || die "release is not qualified: ${release_id}"
  [[ -f "${manifest_path}" && ! -L "${manifest_path}" ]] || die "release manifest is unavailable or unsafe: ${release_id}"
  [[ -r "${QUALIFICATION_PARSER}" ]] || die "qualification parser is unavailable: ${QUALIFICATION_PARSER}"
  parsed="$(mktemp)"
  if ! python3 "${QUALIFICATION_PARSER}" "${marker}" --require-bound >"${parsed}"; then
    rm -f -- "${parsed}"
    die "qualification marker is invalid or not manifest-bound: ${release_id}"
  fi
  schema=""; qualified=""; digest=""
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    case "${key}" in
      QUALIFICATION_SCHEMA_VERSION) schema="${value}" ;;
      QUALIFIED_RELEASE) qualified="${value}" ;;
      RELEASE_MANIFEST_SHA256) digest="${value}" ;;
    esac
  done <"${parsed}"
  rm -f -- "${parsed}"
  [[ "${schema}" == 2 && "${qualified}" == "${release_id}" ]] || die "qualification marker mismatch: ${release_id}"
  observed="$(manifest_digest "${manifest_path}")"
  [[ "${digest}" == "${observed}" ]] || die "qualification manifest digest mismatch: ${release_id}"
}

[[ $# -ge 1 ]] || { usage >&2; exit 2; }
target="$1"; shift
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
  shift
done
[[ "${target}" =~ ^[0-9a-f]{12,40}$ ]] || die "invalid release id: ${target}"

if [[ "${DRY_RUN}" != 1 ]]; then
  [[ -r "${OPERATION_LOCK_LIB}" ]] || die "operation lock helper is unavailable: ${OPERATION_LOCK_LIB}"
  # shellcheck source=scripts/lib/operation-lock.sh
  source "${OPERATION_LOCK_LIB}"
  acquire_operation_lock "${STATE_HOME}" "release update to ${target}" || exit $?
fi

status="$(bash "${RELEASE_MANAGER}" status)"
current="$(awk -F= '$1=="CURRENT_RELEASE" {print $2}' <<<"${status}")"
[[ -n "${current}" && "${current}" != none ]] || die "no immutable baseline is registered; run bootstrap-release.sh first"

update_status="$(bash "${UPDATE_TRANSITION}" status)"
grep -qx 'UPDATE_STATE=idle' <<<"${update_status}" || die "an update transition is already active; recover it before starting another cutover"

# Verification is read-only and catches missing/tampered releases before any pointer mutation.
bash "${RELEASE_MANAGER}" verify "${target}"
verify_bound_qualification "${target}"

if [[ "${DRY_RUN}" == 1 ]]; then
  printf 'DRY-RUN: verified manifest-bound qualification for %s\n' "${target}"
  printf 'DRY-RUN: would prepare update transition to %s\n' "${target}"
  printf 'DRY-RUN: would reinstall/restart managed service with runtime root %s\n' "${CURRENT_LINK}"
  printf 'DRY-RUN: would commit update transition after replacement runtime validation\n'
  exit 0
fi

command -v sudo >/dev/null 2>&1 || die "sudo is required for managed service cutover"
cutover_active=0
rollback_cutover() {
  local rc="${1:-1}"
  trap - ERR INT TERM
  set +e
  if [[ "${cutover_active}" == 1 ]]; then
    printf 'Release cutover failed; restoring previous release pointer and service.\n' >&2
    if ! bash "${UPDATE_TRANSITION}" rollback; then
      printf 'FATAL: release pointer rollback failed; manual recovery is required.\n' >&2
      exit 70
    fi
    if ! sudo_with_operation_lock bash "${MANAGE_SERVICE}" create --runtime-root "${CURRENT_LINK}" --start --yes; then
      printf 'FATAL: previous release pointer was restored but service restart failed.\n' >&2
      exit 71
    fi
  fi
  exit "${rc}"
}
trap 'rollback_cutover $?' ERR
trap 'rollback_cutover 130' INT
trap 'rollback_cutover 143' TERM

bash "${UPDATE_TRANSITION}" prepare "${target}"
cutover_active=1
sudo_with_operation_lock bash "${MANAGE_SERVICE}" create --runtime-root "${CURRENT_LINK}" --start --yes
bash "${UPDATE_TRANSITION}" commit
cutover_active=0
trap - ERR INT TERM

printf 'Release update committed: %s\n' "${target}"
