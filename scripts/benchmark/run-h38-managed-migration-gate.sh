#!/usr/bin/env bash
# Guarded live gate for the atomic legacy-OrcaRouter -> managed H38 migration.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"
STATE_FILE="${STATE_HOME}/install.env"
RUNTIME_COMMIT_FILE="${STATE_HOME}/runtime-commit.env"
MONITOR_LOG="${STATE_HOME}/monitor.log"
CURRENT_LINK="${DATA_HOME}/current"
UNIT="qwen38-flash-next.service"
CONTAINER="qwen38-flash-next"
MODEL="orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4"
H38_IMAGE="vllm-orcarouter-v029-h38-decoder-scope:v1"
H38_SCOPE="decoder-v1"
H38_CACHE="/root/.cache/vllm/h38-marlin-canonical-decoder-managed-v1"
TARGET_SHA="${H38_MANAGED_TARGET_SHA:-${1:-}}"
OUT="${H38_MANAGED_MIGRATION_OUT:-/tmp/orcarouter-h38-managed-migration-$(date -u '+%Y%m%dT%H%M%SZ')}"
RELEASE_MANAGER="${ROOT}/scripts/release-manager.sh"
UPDATE_RELEASE="${ROOT}/scripts/update-release.sh"
UPDATE_TRANSITION="${ROOT}/scripts/update-transition.sh"
RUNTIME_TRANSITION="${ROOT}/scripts/runtime-transition.sh"
PROFILE_TRANSITION="${ROOT}/scripts/profile-switch-transition.sh"
REFRESH_TRANSITION="${ROOT}/scripts/release-profile-refresh-transition.sh"
STATE_PARSER="${ROOT}/scripts/state_file.py"
BENCHMARK="${ROOT}/scripts/benchmark/run.py"
DOCTOR="${ROOT}/scripts/doctor.sh"
SETTINGS_PHASE_FILE="${STATE_HOME}/settings-transition.phase"
SETTINGS_START_FILE="${STATE_HOME}/settings-transition.start"
SETTINGS_NO_START_FILE="${STATE_HOME}/settings-transition.no-start"
SETTINGS_PREV_SERVICE_FILE="${STATE_HOME}/settings-transition.previous-service-active"
SETTINGS_PREV_CONTAINER_FILE="${STATE_HOME}/settings-transition.previous-container-running"
SETTINGS_BACKUP="${STATE_FILE}.settings-backup"
SETTINGS_TARGET="${STATE_FILE}.settings-candidate"
SETTINGS_BACKUP_SHA="${SETTINGS_BACKUP}.sha256"
SETTINGS_TARGET_SHA="${SETTINGS_TARGET}.sha256"

MEASURE_STARTED=0
WINDOW_CAPTURED=0
OUT_READY=0
FINALIZED=0
MONITOR_LINES_BEFORE=0
MIGRATION_RC=125
DOCTOR_RC=125
FUNCTIONAL="NOT_REACHED"
HOST_STABILITY="INCONCLUSIVE"
RM_OOM_COUNT=0
PROTECTED_STOP=0
FAIL_REASON=""
START_JOURNAL=""
END_JOURNAL=""

usage() {
  cat <<'EOF'
Usage:
  H38_MANAGED_TARGET_SHA=<exact-40-char-sha> \
    bash scripts/benchmark/run-h38-managed-migration-gate.sh

Optional:
  H38_MANAGED_MIGRATION_OUT=/path/to/new/evidence-dir

This gate requires the checkout itself to be the exact target SHA and clean. It
measures a fresh legacy decode baseline, then executes only the atomic
release+same-profile H38 refresh path. It does not run determinism/restart gates.
EOF
}

fail() {
  FAIL_REASON="$*"
  printf 'H38_MIGRATION_ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

parse_state() {
  local schema="$1" path="$2" prefix="$3" parsed key value
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" "${schema}" "${path}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    printf -v "${prefix}_${key}" '%s' "${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
}

load_install() {
  local path="$1" prefix="$2"
  parse_state install-maintenance "${path}" "${prefix}"
}

assert_idle() {
  grep -qx 'UPDATE_STATE=idle' < <(bash "${UPDATE_TRANSITION}" status) ||
    fail 'update transition is not idle'
  grep -qx 'TRANSACTION_STATE=idle' < <(bash "${RUNTIME_TRANSITION}" status) ||
    fail 'runtime transition is not idle'
  grep -qx 'PROFILE_SWITCH_STATE=idle' < <(bash "${PROFILE_TRANSITION}" status) ||
    fail 'profile-switch transition is not idle'
  local settings_artifact
  for settings_artifact in     "${SETTINGS_PHASE_FILE}" "${SETTINGS_START_FILE}" "${SETTINGS_NO_START_FILE}"     "${SETTINGS_PREV_SERVICE_FILE}" "${SETTINGS_PREV_CONTAINER_FILE}"     "${SETTINGS_BACKUP}" "${SETTINGS_TARGET}" "${SETTINGS_BACKUP_SHA}" "${SETTINGS_TARGET_SHA}"
  do
    [[ ! -e "${settings_artifact}" && ! -L "${settings_artifact}" ]] ||
      fail "settings transaction is not idle or has stale artifact: ${settings_artifact}"
  done
  grep -qx 'RELEASE_PROFILE_REFRESH_STATE=idle' < <(bash "${REFRESH_TRANSITION}" status) ||
    fail 'release-profile refresh transition is not idle'
}

assert_model_id() {
  local expected="$1" output
  output="$(curl -fsS --max-time 15 http://127.0.0.1:8888/v1/models)" ||
    fail 'managed model list is unavailable'
  python3 -c 'import json,sys; expected=sys.argv[1]; data=json.load(sys.stdin); raise SystemExit(0 if any(item.get("id") == expected for item in data.get("data", [])) else 1)'     "${expected}" <<<"${output}" || fail "served model identity mismatch: expected=${expected}"
  printf '%s\n' "${output}" >"${OUT}/models.json"
}

snapshot_lifecycle() {
  local suffix="$1"
  bash "${RELEASE_MANAGER}" status >"${OUT}/release-${suffix}.txt" 2>&1 || true
  bash "${UPDATE_TRANSITION}" status >"${OUT}/update-transition-${suffix}.txt" 2>&1 || true
  bash "${RUNTIME_TRANSITION}" status >"${OUT}/runtime-transition-${suffix}.txt" 2>&1 || true
  bash "${PROFILE_TRANSITION}" status >"${OUT}/profile-transition-${suffix}.txt" 2>&1 || true
  if [[ -f "${SETTINGS_PHASE_FILE}" && ! -L "${SETTINGS_PHASE_FILE}" ]]; then
    printf 'SETTINGS_TRANSITION_STATE=' >"${OUT}/settings-transition-${suffix}.txt"
    cat "${SETTINGS_PHASE_FILE}" >>"${OUT}/settings-transition-${suffix}.txt"
  else
    printf 'SETTINGS_TRANSITION_STATE=idle\n' >"${OUT}/settings-transition-${suffix}.txt"
  fi
  bash "${REFRESH_TRANSITION}" status >"${OUT}/release-profile-refresh-${suffix}.txt" 2>&1 || true
}

snapshot_runtime() {
  local suffix="$1"
  systemctl status "${UNIT}" --no-pager >"${OUT}/service-${suffix}.txt" 2>&1 || true
  docker inspect "${CONTAINER}" >"${OUT}/container-${suffix}.json" 2>&1 || true
  docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "${CONTAINER}"     >"${OUT}/container-env-${suffix}.txt" 2>&1 || true
  docker inspect --format '{{json .Config.Cmd}}' "${CONTAINER}"     >"${OUT}/container-cmd-${suffix}.json" 2>&1 || true
  [[ ! -f "${STATE_FILE}" ]] || cp -p -- "${STATE_FILE}" "${OUT}/install-${suffix}.env"
  [[ ! -f "${RUNTIME_COMMIT_FILE}" ]] || cp -p -- "${RUNTIME_COMMIT_FILE}" "${OUT}/runtime-commit-${suffix}.env"
  cp -p -- /proc/meminfo "${OUT}/meminfo-${suffix}.txt" 2>/dev/null || true
  swapon --show >"${OUT}/swapon-${suffix}.txt" 2>&1 || true
}

capture_measured_window() {
  local monitor_total=0 start_line=1
  [[ "${MEASURE_STARTED}" == 1 ]] || return 0
  [[ "${WINDOW_CAPTURED}" == 0 ]] || return 0
  sleep 2
  END_JOURNAL="$(date '+%Y-%m-%d %H:%M:%S')"
  WINDOW_CAPTURED=1
  printf '%s\n' "${END_JOURNAL}" >"${OUT}/measured-window-end.txt"

  sudo -n journalctl -k     --since "${START_JOURNAL}"     --until "${END_JOURNAL}"     -o short-iso-precise --no-pager     >"${OUT}/kernel-window.txt" 2>"${OUT}/kernel-window.stderr" || true

  grep -Ei 'NV_ERR_NO_MEMORY|_memdescAllocInternal|NVRM:.*Xid|Xid \(PCI|GPU has fallen off the bus|oom-kill:|Out of memory:|Killed process '     "${OUT}/kernel-window.txt" >"${OUT}/kernel-errors.txt" || true
  RM_OOM_COUNT="$(grep -Ec 'NV_ERR_NO_MEMORY|_memdescAllocInternal' "${OUT}/kernel-errors.txt" 2>/dev/null || true)"
  [[ "${RM_OOM_COUNT}" =~ ^[0-9]+$ ]] || RM_OOM_COUNT=0

  if [[ -f "${MONITOR_LOG}" ]]; then
    monitor_total="$(wc -l <"${MONITOR_LOG}")"
    start_line=$((MONITOR_LINES_BEFORE + 1))
    if (( monitor_total >= start_line )); then
      sed -n "${start_line},${monitor_total}p" "${MONITOR_LOG}" >"${OUT}/monitor-window.log"
    else
      : >"${OUT}/monitor-window.log"
    fi
  else
    : >"${OUT}/monitor-window.log"
  fi
  grep -q 'PROTECT stopping' "${OUT}/monitor-window.log" 2>/dev/null && PROTECTED_STOP=1 || PROTECTED_STOP=0
}

write_summary() {
  local rc="$1"
  {
    printf 'target_sha=%s\n' "${TARGET_SHA:-unset}"
    printf 'migration_rc=%s\n' "${MIGRATION_RC}"
    printf 'doctor_rc=%s\n' "${DOCTOR_RC}"
    printf 'functional=%s\n' "${FUNCTIONAL}"
    printf 'host_stability=%s\n' "${HOST_STABILITY}"
    printf 'rm_oom_count=%s\n' "${RM_OOM_COUNT}"
    printf 'protected_stop=%s\n' "${PROTECTED_STOP}"
    printf 'fail_reason=%s\n' "${FAIL_REASON:-none}"
    printf 'script_rc=%s\n' "${rc}"
  } >"${OUT}/summary.txt"
}

finalize() {
  local rc="$?"
  [[ "${FINALIZED}" == 0 ]] || exit "${rc}"
  FINALIZED=1
  trap - EXIT INT TERM
  set +e
  if [[ "${OUT_READY}" != 1 || ! -d "${OUT}" ]]; then
    printf 'H38_MANAGED_FUNCTIONAL=%s\n' "${FUNCTIONAL}"
    printf 'H38_MANAGED_HOST_STABILITY=%s\n' "${HOST_STABILITY}"
    exit "${rc}"
  fi

  capture_measured_window
  snapshot_lifecycle after
  snapshot_runtime after
  journalctl -u "${UNIT}" --since "${START_JOURNAL:-today}" --no-pager     >"${OUT}/service-window.txt" 2>&1 || true

  if (( RM_OOM_COUNT > 0 )); then
    HOST_STABILITY="FAIL"
  elif [[ "${FUNCTIONAL}" == PASS && "${PROTECTED_STOP}" == 0 ]]; then
    HOST_STABILITY="PASS"
  else
    HOST_STABILITY="INCONCLUSIVE"
  fi
  write_summary "${rc}"

  {
    printf '===== summary =====\n'
    cat "${OUT}/summary.txt"
    for evidence_file in       migration-command.log doctor-strict.txt h38-image-verify.txt kernel-errors.txt       release-before.txt release-after.txt runtime-transition-after.txt       release-profile-refresh-after.txt service-window.txt
    do
      [[ -f "${OUT}/${evidence_file}" ]] || continue
      printf '\n===== %s =====\n' "${evidence_file}"
      cat "${OUT}/${evidence_file}"
    done
  } >"${OUT}/upload-summary.txt"

  printf '\n===== H38 managed migration summary =====\n'
  cat "${OUT}/summary.txt"
  printf '%s\n' '--- kernel errors ---'
  cat "${OUT}/kernel-errors.txt" 2>/dev/null || true
  printf 'evidence=%s\n' "${OUT}"
  printf 'upload_summary=%s\n' "${OUT}/upload-summary.txt"
  if (( RM_OOM_COUNT > 0 )); then
    printf 'H38_MANAGED_HOST_STABILITY=FAIL\n'
  else
    printf 'H38_MANAGED_HOST_STABILITY=%s\n' "${HOST_STABILITY}"
  fi
  printf 'H38_MANAGED_FUNCTIONAL=%s\n' "${FUNCTIONAL}"
  exit "${rc}"
}
trap finalize EXIT INT TERM

[[ "${TARGET_SHA}" =~ ^[0-9a-f]{40}$ ]] || {
  usage >&2
  fail 'H38_MANAGED_TARGET_SHA must be the exact 40-character target commit SHA'
}

for command in   bash git python3 docker systemctl curl journalctl date grep awk sed cp stat   sha256sum tee sudo swapon wc mktemp sleep
do
  require_command "${command}"
done

ACTUAL_SHA="$(git -C "${ROOT}" rev-parse HEAD)"
[[ "${ACTUAL_SHA}" == "${TARGET_SHA}" ]] ||
  fail "checkout SHA mismatch: expected=${TARGET_SHA} actual=${ACTUAL_SHA}"
[[ -z "$(git -C "${ROOT}" status --porcelain=v1 --untracked-files=all)" ]] ||
  fail 'working tree is dirty; preserve local changes before live acceptance'
[[ ! -e "${OUT}" && ! -L "${OUT}" ]] || fail "evidence path already exists: ${OUT}"
mkdir -p -- "${OUT}"
OUT_READY=1
exec > >(tee -a "${OUT}/run.log") 2>&1

printf '%s\n' "${TARGET_SHA}" >"${OUT}/target-sha.txt"
git -C "${ROOT}" branch --show-current >"${OUT}/branch.txt"
git -C "${ROOT}" status --porcelain=v1 --untracked-files=all >"${OUT}/git-status.txt"
sudo -n true >/dev/null 2>&1 || fail 'sudo timestamp unavailable; run sudo -v before this gate'

[[ -f "${STATE_FILE}" && ! -L "${STATE_FILE}" ]] || fail "installation manifest is missing or unsafe: ${STATE_FILE}"
[[ -r "${STATE_PARSER}" ]] || fail "strict state parser is unavailable: ${STATE_PARSER}"
[[ -L "${CURRENT_LINK}" ]] || fail "immutable current release pointer is missing: ${CURRENT_LINK}"
assert_idle

load_install "${STATE_FILE}" PRE || fail 'current installation manifest failed strict parsing'
[[ "${PRE_PHASE}" == complete ]] || fail "current installation phase is not complete: ${PRE_PHASE}"
[[ "${PRE_MODEL_PROFILE}" == orcarouter ]] || fail "current managed profile is not orcarouter: ${PRE_MODEL_PROFILE}"
[[ "${PRE_SERVED_NAME}" == "${MODEL}" ]] || fail "current served alias is unexpected: ${PRE_SERVED_NAME}"
case "${PRE_VLLM_IMAGE}" in
  vllm-skinny-tp1:v1|vllm/vllm-openai:qwen38-flash-next-arm64-cu130) ;;
  "${H38_IMAGE}") fail 'managed H38 image is already active; this migration gate is not a rerun gate' ;;
  *) fail "unsupported pre-H38 OrcaRouter image: ${PRE_VLLM_IMAGE}" ;;
esac
[[ "${PRE_SERVICE_ENABLED}" == 1 && "${PRE_SERVICE_OWNED}" == 1 ]] ||
  fail 'managed service must be enabled and installer-owned'

CURRENT_STATUS="$(bash "${RELEASE_MANAGER}" status)"
CURRENT_RELEASE="$(awk -F= '$1=="CURRENT_RELEASE" {print $2}' <<<"${CURRENT_STATUS}")"
[[ -n "${CURRENT_RELEASE}" && "${CURRENT_RELEASE}" != none ]] || fail 'no immutable current release is registered'
[[ "${CURRENT_RELEASE}" != "${TARGET_SHA}" ]] || fail 'target release is already current before migration'
CURRENT_ROOT="$(readlink -f -- "${CURRENT_LINK}")"
[[ "${CURRENT_ROOT}" == "${DATA_HOME}/releases/${CURRENT_RELEASE}" ]] ||
  fail "current release pointer does not match release-manager status: ${CURRENT_ROOT}"

systemctl is-active --quiet "${UNIT}" || fail 'managed service is not active before migration'
PRE_CONTAINER_ID="$(docker inspect --format '{{.Id}}' "${CONTAINER}" 2>/dev/null || true)"
PRE_CONTAINER_IMAGE="$(docker inspect --format '{{.Config.Image}}' "${CONTAINER}" 2>/dev/null || true)"
PRE_CONTAINER_RUNNING="$(docker inspect --format '{{.State.Running}}' "${CONTAINER}" 2>/dev/null || true)"
PRE_CONTAINER_OOM="$(docker inspect --format '{{.State.OOMKilled}}' "${CONTAINER}" 2>/dev/null || true)"
[[ -n "${PRE_CONTAINER_ID}" && "${PRE_CONTAINER_RUNNING}" == true ]] || fail 'previous managed runtime is not running'
[[ "${PRE_CONTAINER_IMAGE}" == "${PRE_VLLM_IMAGE}" ]] || fail 'previous runtime image does not match install manifest'
[[ "${PRE_CONTAINER_OOM}" == false ]] || fail 'previous managed runtime is OOMKilled'
docker inspect "${CONTAINER}.rollback" >/dev/null 2>&1 &&
  fail 'stale runtime rollback container exists before migration'
curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null ||
  fail 'previous managed API is not healthy'
assert_model_id "${MODEL}"

[[ -f "${RUNTIME_COMMIT_FILE}" && ! -L "${RUNTIME_COMMIT_FILE}" ]] ||
  fail 'previous runtime commit attestation is missing'
parse_state runtime-commit "${RUNTIME_COMMIT_FILE}" PRE_ATTEST ||
  fail 'previous runtime commit attestation failed strict parsing'
[[ "${PRE_ATTEST_RUNTIME_ROOT}" == "${CURRENT_ROOT}" ]] ||
  fail 'previous runtime attestation does not match immutable current release'
[[ "${PRE_ATTEST_RUNTIME_CONTAINER_NAME}" == "${CONTAINER}" &&
   "${PRE_ATTEST_RUNTIME_CONTAINER_ID}" == "${PRE_CONTAINER_ID}" ]] ||
  fail 'previous runtime attestation does not match the live container'

snapshot_lifecycle before
snapshot_runtime before
printf '%s\n' "${CURRENT_RELEASE}" >"${OUT}/release-before-id.txt"
printf '%s\n' "${PRE_VLLM_IMAGE}" >"${OUT}/image-before.txt"
printf '%s\n' "${PRE_CONTAINER_ID}" >"${OUT}/container-id-before.txt"

printf '\n===== matched legacy decode baseline: 384 tokens x5 =====\n'
python3 "${BENCHMARK}" decode   --model "${MODEL}"   --decode-tokens 384   --decode-repeats 5   --output "${OUT}/baseline-decode.json"

BASELINE_MEDIAN="$(python3 - "${OUT}/baseline-decode.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
print(data["workloads"]["decode"]["decode_tokens_s"]["median"])
PY
)"
printf '%s\n' "${BASELINE_MEDIAN}" >"${OUT}/baseline-decode-median.txt"
printf 'baseline_decode_median_tok_s=%s\n' "${BASELINE_MEDIAN}"

MONITOR_LINES_BEFORE=0
[[ ! -f "${MONITOR_LOG}" ]] || MONITOR_LINES_BEFORE="$(wc -l <"${MONITOR_LOG}")"
START_JOURNAL="$(date '+%Y-%m-%d %H:%M:%S')"
printf '%s\n' "${START_JOURNAL}" >"${OUT}/measured-window-start.txt"
MEASURE_STARTED=1

printf '\n===== atomic cross-release H38 migration =====\n'
set +e
bash "${UPDATE_RELEASE}" "${TARGET_SHA}" --refresh-profile-defaults   >"${OUT}/migration-command.log" 2>&1
MIGRATION_RC=$?
set -e
cat "${OUT}/migration-command.log"
printf 'migration_rc=%s\n' "${MIGRATION_RC}"
[[ "${MIGRATION_RC}" == 0 ]] || fail "atomic H38 migration failed with rc=${MIGRATION_RC}"

assert_idle
load_install "${STATE_FILE}" POST || fail 'post-migration install manifest failed strict parsing'
[[ "${POST_PHASE}" == complete ]] || fail "post-migration phase is not complete: ${POST_PHASE}"
[[ "${POST_MODEL_PROFILE}" == orcarouter ]] || fail 'post-migration profile changed unexpectedly'
[[ "${POST_VLLM_IMAGE}" == "${H38_IMAGE}" ]] || fail "post-migration image mismatch: ${POST_VLLM_IMAGE}"
[[ "${POST_SERVED_NAME}" == "${MODEL}" ]] || fail "post-migration served alias mismatch: ${POST_SERVED_NAME}"

POST_STATUS="$(bash "${RELEASE_MANAGER}" status)"
POST_RELEASE="$(awk -F= '$1=="CURRENT_RELEASE" {print $2}' <<<"${POST_STATUS}")"
[[ "${POST_RELEASE}" == "${TARGET_SHA}" ]] || fail "current release is not target after migration: ${POST_RELEASE}"
POST_ROOT="$(readlink -f -- "${CURRENT_LINK}")"
[[ "${POST_ROOT}" == "${DATA_HOME}/releases/${TARGET_SHA}" ]] ||
  fail "current release pointer is not exact target: ${POST_ROOT}"
[[ "$(realpath -m -- "${POST_INSTALL_ROOT}")" == "${POST_ROOT}" ]] ||
  fail "install manifest root does not match exact target release: ${POST_INSTALL_ROOT}"

systemctl is-active --quiet "${UNIT}" || fail 'managed service is not active after migration'
curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null ||
  fail 'managed H38 API is not healthy'
assert_model_id "${MODEL}"

POST_CONTAINER_ID="$(docker inspect --format '{{.Id}}' "${CONTAINER}" 2>/dev/null || true)"
POST_CONTAINER_IMAGE="$(docker inspect --format '{{.Config.Image}}' "${CONTAINER}" 2>/dev/null || true)"
POST_CONTAINER_RUNNING="$(docker inspect --format '{{.State.Running}}' "${CONTAINER}" 2>/dev/null || true)"
POST_CONTAINER_OOM="$(docker inspect --format '{{.State.OOMKilled}}' "${CONTAINER}" 2>/dev/null || true)"
[[ -n "${POST_CONTAINER_ID}" && "${POST_CONTAINER_RUNNING}" == true ]] || fail 'managed H38 container is not running'
[[ "${POST_CONTAINER_ID}" != "${PRE_CONTAINER_ID}" ]] || fail 'migration did not replace the managed container'
[[ "${POST_CONTAINER_IMAGE}" == "${H38_IMAGE}" ]] || fail "managed container image mismatch: ${POST_CONTAINER_IMAGE}"
[[ "${POST_CONTAINER_OOM}" == false ]] || fail 'managed H38 container reports OOMKilled=true'
docker inspect "${CONTAINER}.rollback" >/dev/null 2>&1 &&
  fail 'runtime rollback container remains after committed migration'

H38_LABEL="$(docker image inspect --format '{{ index .Config.Labels "qwen38.h38scope" }}' "${H38_IMAGE}" 2>/dev/null || true)"
[[ "${H38_LABEL}" == "${H38_SCOPE}" ]] || fail "H38 image label mismatch: ${H38_LABEL:-missing}"
bash "${POST_ROOT}/scripts/prepare-h38-image.sh" verify   >"${OUT}/h38-image-verify.txt" 2>&1 || fail 'H38 image provenance verification failed'

docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "${CONTAINER}" >"${OUT}/h38-env.txt"
for expected in   'VLLM_PLE_MMAP=1'   'VLLM_QSA_EXACT_TOPK=1'   'QWEN38_MARLIN_CANONICAL_ORDER=1'   'QWEN38_MARLIN_CANONICAL_SCOPE=decoder'   "VLLM_CACHE_ROOT=${H38_CACHE}"
do
  grep -Fxq "${expected}" "${OUT}/h38-env.txt" || fail "missing H38 runtime env: ${expected}"
done

docker inspect --format '{{json .Config.Cmd}}' "${CONTAINER}" >"${OUT}/h38-cmd.json"
python3 - "${OUT}/h38-cmd.json" <<'PY' || fail 'H38 runtime command does not pin the expected 16 GiB KV cache'
import json
import sys
cmd = json.load(open(sys.argv[1], encoding="utf-8"))
idx = cmd.index("--kv-cache-memory-bytes")
raise SystemExit(0 if idx + 1 < len(cmd) and cmd[idx + 1] == "17179869184" else 1)
PY

parse_state runtime-commit "${RUNTIME_COMMIT_FILE}" POST_ATTEST ||
  fail 'post-migration runtime commit attestation failed strict parsing'
[[ "${POST_ATTEST_RUNTIME_ROOT}" == "${POST_ROOT}" ]] ||
  fail 'post-migration runtime attestation root mismatch'
[[ "${POST_ATTEST_RUNTIME_CONTAINER_NAME}" == "${CONTAINER}" &&
   "${POST_ATTEST_RUNTIME_CONTAINER_ID}" == "${POST_CONTAINER_ID}" ]] ||
  fail 'post-migration runtime attestation container mismatch'

set +e
bash "${DOCTOR}" --strict >"${OUT}/doctor-strict.txt" 2>&1
DOCTOR_RC=$?
set -e
cat "${OUT}/doctor-strict.txt"
[[ "${DOCTOR_RC}" == 0 ]] || fail "doctor --strict failed with rc=${DOCTOR_RC}"

FUNCTIONAL="PASS"
capture_measured_window
if (( RM_OOM_COUNT > 0 )); then
  HOST_STABILITY="FAIL"
  FAIL_REASON="strict NVIDIA RM no-memory evidence observed"
  printf 'H38_MIGRATION_ERROR: %s\n' "${FAIL_REASON}" >&2
  exit 1
fi
if [[ "${PROTECTED_STOP}" != 0 ]]; then
  HOST_STABILITY="INCONCLUSIVE"
  FAIL_REASON="memory protection intervened during measured migration window"
  printf 'H38_MIGRATION_ERROR: %s\n' "${FAIL_REASON}" >&2
  exit 1
fi
HOST_STABILITY="PASS"
printf 'H38_MANAGED_MIGRATION_RESULT=PASS_FOR_FOLLOWUP_GATES\n'
