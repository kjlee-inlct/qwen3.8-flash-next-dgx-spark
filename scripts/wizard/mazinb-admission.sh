#!/usr/bin/env bash
# Read-only, exact-predecessor admission gate for a future isolated mazinb run.
# It does NOT start/stop Docker, alter a manifest, or measure performance.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/install.env"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"
SERVICE=qwen38-flash-next.service
CONTAINER=qwen38-flash-next
EXPECTED_ID=""
REVIEWED_A_ID=""
LOCK_FD=""

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/wizard/mazinb-admission.sh --expected-old-id EXACT_64_HEX \
    [--reviewed-trial-a-id EXACT_HISTORICAL_A_64_HEX]

READ-ONLY admission gate for an isolated mazinb benchmark session.
Checks exact stopped predecessor identity, protected manifest, lifecycle
lock, immutable release, service inactivity, historical mazinb A review
and current mazinb preflight. Does not start, stop, cleanup or benchmark.
A PASS is NOT READY, HOST-STABILITY PASS or benchmark approval.
USAGE
}
die() { printf 'MAZINB_ADMISSION=BLOCKED reason=%s\n' "$*" >&2; exit 2; }

if [[ "${1:-}" == --help || "${1:-}" == -h ]]; then usage; exit 0; fi
while (( $# > 0 )); do
  case "${1}" in
    --expected-old-id)
      (( $# >= 2 )) || { usage >&2; exit 2; }
      [[ -z "${EXPECTED_ID}" ]] || die 'duplicate predecessor ID argument'
      EXPECTED_ID="$2"
      shift 2 ;;
    --reviewed-trial-a-id)
      (( $# >= 2 )) || { usage >&2; exit 2; }
      [[ -z "${REVIEWED_A_ID}" ]] || die 'duplicate reviewed A ID argument'
      REVIEWED_A_ID="$2"
      shift 2 ;;
    *) usage >&2; exit 2 ;;
  esac
done
[[ "${EXPECTED_ID}" =~ ^[a-f0-9]{64}$ ]] || die 'exact predecessor 64-hex ID is required'
[[ -z "${REVIEWED_A_ID}" || "${REVIEWED_A_ID}" =~ ^[a-f0-9]{64}$ ]] ||
  die 'reviewed historical A ID must be exact 64-hex Docker identity'

for executable in docker python3 systemctl sha256sum flock stat readlink; do
  command -v "${executable}" >/dev/null 2>&1 || die "missing tool: ${executable}"
done
[[ -d "${STATE_DIR}" && ! -L "${STATE_DIR}" ]] || die 'state directory missing or unsafe'
[[ -f "${STATE_FILE}" && ! -L "${STATE_FILE}" ]] || die 'install manifest missing or unsafe'
[[ -f "${STATE_DIR}/operation.lock" && ! -L "${STATE_DIR}/operation.lock" ]] ||
  die 'existing operation lock missing or unsafe'
[[ "$(stat -c %u -- "${STATE_DIR}/operation.lock")" == "$(id -u)" ]] ||
  die 'operation lock owner mismatch'
exec {LOCK_FD}<"${STATE_DIR}/operation.lock" || die 'cannot read lifecycle lock'
flock -n -s "${LOCK_FD}" || die 'lifecycle lock currently busy'

for marker in runtime-transition.env update-transition.env profile-switch-transition.env \
    release-profile-refresh-transition.env settings-transition.phase runtime-adopt.env; do
  [[ ! -e "${STATE_DIR}/${marker}" && ! -L "${STATE_DIR}/${marker}" ]] ||
    die "lifecycle marker exists: ${marker}"
done
for marker in "${STATE_FILE}.profile-switch-backup" "${STATE_FILE}.profile-switch-candidate" \
    "${STATE_FILE}.settings-backup" "${STATE_FILE}.settings-candidate"; do
  [[ ! -e "${marker}" && ! -L "${marker}" ]] ||
    die "stale transaction artifact: ${marker}"
done

# Capture strict parsed values. No shell eval/source of the state file.
parsed="$(mktemp)" || die 'cannot create temporary parser output'
trap 'rm -f -- "${parsed}"' EXIT
if ! python3 "${ROOT}/scripts/lib/state_file.py" install-maintenance "${STATE_FILE}" >"${parsed}"; then
  die 'manifest strict parsing failed'
fi
phase="" profile="" monitor="" protect="" image="" service_enabled=""
while IFS= read -r -d '' key && IFS= read -r -d '' value; do
  case "${key}" in
    PHASE) phase="${value}" ;;
    MODEL_PROFILE) profile="${value}" ;;
    MONITOR_ENABLED) monitor="${value}" ;;
    MONITOR_PROTECT) protect="${value}" ;;
    VLLM_IMAGE) image="${value}" ;;
    SERVICE_ENABLED) service_enabled="${value}" ;;
  esac
done <"${parsed}"
[[ "${phase}" == complete && "${profile}" == orcarouter ]] ||
  die "expected installed OrcaRouter predecessor (phase=${phase} profile=${profile})"
[[ "${monitor}" == 1 && "${protect}" == 1 ]] ||
  die 'managed memory monitor/protection must remain enabled'
[[ "${service_enabled}" == 1 ]] || die 'expected managed systemd predecessor'
manifest_before="$(sha256sum -- "${STATE_FILE}")"
manifest_before="${manifest_before%% *}"

# A stopped service must be explicitly proven, not inferred from an error exit.
service_state="$(systemctl is-active "${SERVICE}" 2>/dev/null || true)"
[[ "${service_state}" == inactive ]] ||
  die "managed service must be explicitly inactive (actual=${service_state:-unknown})"

old_state="$(docker inspect --format '{{.Id}}|{{.State.Status}}|{{.State.Running}}|{{.State.OOMKilled}}|{{.Image}}' "${CONTAINER}" 2>/dev/null)" ||
  die 'canonical Docker object cannot be inspected'
IFS='|' read -r old_id old_status old_running old_oom old_image <<<"${old_state}"
[[ "${old_id}" == "${EXPECTED_ID}" ]] || die 'canonical Docker exact ID mismatch'
[[ "${old_status}" == exited && "${old_running}" == false && "${old_oom}" == false ]] ||
  die "predecessor is not cleanly stopped (status=${old_status} running=${old_running} oom=${old_oom})"
[[ "${old_image}" == sha256:* ]] || die 'cannot prove exact immutable predecessor image ID'

# Case B is the future first-run target, so its name/state must be free.
# Case A is a different *historical* experiment. Its stopped Docker and
# evidence must be preserved, not deleted merely to make B admissible.
if docker inspect --format '{{.Id}}' qwen38-mazinb-kv-b >/dev/null 2>&1; then
  die 'target B Docker name already exists; review and preserve B evidence first'
fi
b_evidence="${HOME}/.local/state/qwen38-mazinb-kv-b"
[[ ! -e "${b_evidence}" && ! -L "${b_evidence}" ]] ||
  die 'target B state/evidence directory already exists; preserve/review before a new run'
historical_a=ABSENT
if docker inspect --format '{{.Id}}' qwen38-mazinb-kv-a >/dev/null 2>&1; then
  a_state="$(docker inspect --format '{{.Id}}|{{.Name}}|{{.State.Status}}|{{.State.Running}}' qwen38-mazinb-kv-a 2>/dev/null)" ||
    die 'cannot inspect historical case A'
  IFS='|' read -r a_id a_name a_status a_running <<<"${a_state}"
  [[ "${a_name}" == /qwen38-mazinb-kv-a && "${a_status}" == exited &&
     "${a_running}" == false ]] ||
    die "historical A is not safely stopped (status=${a_status} running=${a_running})"
  [[ "${REVIEWED_A_ID}" == "${a_id}" ]] ||
    die 'historical A must be reviewed through Wizard and its exact 64-hex ID acknowledged'
  a_evidence="${HOME}/.local/state/qwen38-mazinb-kv-a/qwen38-spark"
  [[ -d "${a_evidence}" && ! -L "${a_evidence}" &&
     -f "${a_evidence}/experiment.env" && ! -L "${a_evidence}/experiment.env" &&
     -f "${a_evidence}/monitor.log" && ! -L "${a_evidence}/monitor.log" ]] ||
    die 'historical A experiment or monitor evidence is absent/unsafe; preserve and investigate'
  historical_a="PRESERVED_REVIEWED:${a_id}"
elif [[ -n "${REVIEWED_A_ID}" ]]; then
  die 'reviewed A identity was provided but A is absent'
fi

[[ -L "${DATA_HOME}/current" ]] || die 'current release link missing'
current_release="$(readlink -f -- "${DATA_HOME}/current")" ||
  die 'cannot resolve immutable current release'
releases_root="$(readlink -f -- "${DATA_HOME}/releases")" ||
  die 'cannot resolve immutable releases directory'
[[ -n "${releases_root}" && "${current_release}" == "${releases_root}/"* && -d "${current_release}" ]] ||
  die 'unsafe immutable current release target'

printf 'MAZINB_ADMISSION_STAGE=READ_ONLY\n'
printf 'HISTORICAL_A=%s\n' "${historical_a}"
printf 'MANAGED_PREDECESSOR_ID=%s\n' "${old_id}"
printf 'MANAGED_PREDECESSOR_IMAGE_ID=%s\n' "${old_image}"
printf 'MANAGED_PREDECESSOR_IMAGE_TAG=%s\n' "${image}"
printf 'INSTALL_MANIFEST_SHA256=%s\n' "${manifest_before}"
printf 'IMMUTABLE_CURRENT_RELEASE=%s\n' "${current_release}"
printf 'LIFECYCLE_LOCK=AVAILABLE\nSERVICE_STATE=inactive\n'
printf '\n=== Fresh mazinb preflight ===\n'
bash "${ROOT}/scripts/runtime/mazinb-kv-ab.sh" preflight ||
  die 'mazinb runtime preflight failed'

# Revalidate the externally observable predecessor after preflight (TOCTOU).
[[ "$(sha256sum -- "${STATE_FILE}")" == "${manifest_before} "* ]] ||
  die 'manifest changed during admission'
[[ "$(docker inspect --format '{{.Id}}|{{.State.Status}}|{{.State.Running}}|{{.State.OOMKilled}}|{{.Image}}' "${CONTAINER}" 2>/dev/null)" == "${old_state}" ]] ||
  die 'canonical Docker state changed during admission'
[[ "$(readlink -f -- "${DATA_HOME}/current")" == "${current_release}" ]] ||
  die 'immutable release pointer changed during admission'
[[ "$(systemctl is-active "${SERVICE}" 2>/dev/null || true)" == inactive ]] ||
  die 'managed service changed during admission'
if [[ "${historical_a}" == PRESERVED_REVIEWED:* ]]; then
  [[ "$(docker inspect --format '{{.Id}}|{{.Name}}|{{.State.Status}}|{{.State.Running}}' qwen38-mazinb-kv-a 2>/dev/null || true)" == "${a_state}" ]] ||
    die 'reviewed historical A container changed during admission'
elif docker inspect --format '{{.Id}}' qwen38-mazinb-kv-a >/dev/null 2>&1; then
  die 'historical A appeared during admission'
fi
if docker inspect --format '{{.Id}}' qwen38-mazinb-kv-b >/dev/null 2>&1; then
  die 'target B appeared during admission'
fi
[[ ! -e "${b_evidence}" && ! -L "${b_evidence}" ]] ||
  die 'target B state directory appeared during admission'

printf 'MAZINB_ADMISSION=PASS_READ_ONLY\n'
printf 'MAZINB_CANDIDATE_START=NOT_PERFORMED\n'
printf 'MAZINB_FUNCTIONAL=NOT_MEASURED\n'
printf 'MAZINB_HOST_STABILITY=NOT_MEASURED\n'
printf 'MAZINB_BENCHMARK=NOT_MEASURED\n'
