#!/usr/bin/env bash
# Run the managed-H38 post-migration acceptance gates on one DGX Spark.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"
STATE_FILE="${STATE_HOME}/install.env"
RUNTIME_COMMIT_FILE="${STATE_HOME}/runtime-commit.env"
RUNTIME_ADOPT_FILE="${STATE_HOME}/runtime-adopt.env"
MONITOR_LOG="${STATE_HOME}/monitor.log"
CURRENT_LINK="${DATA_HOME}/current"
UNIT="qwen38-flash-next.service"
CONTAINER="qwen38-flash-next"
MODEL="orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4"
H38_IMAGE="vllm-orcarouter-v029-h38-decoder-scope:v1"
H38_SCOPE="decoder-v1"
H38_CACHE="/root/.cache/vllm/h38-marlin-canonical-decoder-managed-v1"
TARGET_SHA="${H38_MANAGED_TARGET_SHA:-${1:-}}"
MIGRATION_EVIDENCE="${H38_MANAGED_MIGRATION_EVIDENCE:-${2:-}}"
OUT="${H38_MANAGED_FOLLOWUP_OUT:-/tmp/orcarouter-h38-managed-followup-$(date -u '+%Y%m%dT%H%M%SZ')}"

STATE_PARSER="${ROOT}/scripts/state_file.py"
RELEASE_MANAGER="${ROOT}/scripts/release-manager.sh"
UPDATE_TRANSITION="${ROOT}/scripts/update-transition.sh"
RUNTIME_TRANSITION="${ROOT}/scripts/runtime-transition.sh"
PROFILE_TRANSITION="${ROOT}/scripts/profile-switch-transition.sh"
REFRESH_TRANSITION="${ROOT}/scripts/release-profile-refresh-transition.sh"
DOCTOR="${ROOT}/scripts/doctor.sh"
MANAGE_SERVICE="${ROOT}/scripts/manage-service.sh"
BENCHMARK="${ROOT}/scripts/benchmark/run.py"
DET_GATE="${ROOT}/scripts/benchmark/run-h38-production-gate.sh"

SETTINGS_PHASE_FILE="${STATE_HOME}/settings-transition.phase"
SETTINGS_START_FILE="${STATE_HOME}/settings-transition.start"
SETTINGS_NO_START_FILE="${STATE_HOME}/settings-transition.no-start"
SETTINGS_PREV_SERVICE_FILE="${STATE_HOME}/settings-transition.previous-service-active"
SETTINGS_PREV_CONTAINER_FILE="${STATE_HOME}/settings-transition.previous-container-running"
SETTINGS_BACKUP="${STATE_FILE}.settings-backup"
SETTINGS_TARGET="${STATE_FILE}.settings-candidate"
SETTINGS_BACKUP_SHA="${SETTINGS_BACKUP}.sha256"
SETTINGS_TARGET_SHA="${SETTINGS_TARGET}.sha256"

OUT_READY=0
WINDOW_STARTED=0
WINDOW_CAPTURED=0
FINALIZED=0
MONITOR_LINES_BEFORE=0
KERNEL_WINDOW_RC=125
RM_OOM_COUNT=0
PROTECTED_STOP=0
DETERMINISM="NOT_REACHED"
PERFORMANCE="NOT_REACHED"
RESTART_ATTESTATION="NOT_REACHED"
HOST_STABILITY="INCONCLUSIVE"
BASELINE_MEDIAN=""
CANDIDATE_MEDIAN=""
PERFORMANCE_RATIO=""
FAIL_REASON=""
START_JOURNAL=""
END_JOURNAL=""

usage() {
  cat <<'EOF'
Usage:
  H38_MANAGED_TARGET_SHA=<exact-40-char-sha> \
  H38_MANAGED_MIGRATION_EVIDENCE=/path/to/passing/migration-evidence \
    bash scripts/run-h38-managed-followup-gates.sh

Optional:
  H38_MANAGED_FOLLOWUP_OUT=/path/to/new/evidence-dir

This runner is valid only after run-h38-managed-migration-gate.sh produced
FUNCTIONAL=PASS and HOST_STABILITY=PASS for the same exact target SHA.
It runs managed-alias determinism, the >=90% matched decode-performance gate,
one supported managed-service replacement/restart, doctor/attestation checks,
and one strict NVIDIA-RM/monitor evidence window spanning all follow-up gates.
EOF
}

fail() {
  FAIL_REASON="$*"
  printf 'H38_FOLLOWUP_ERROR: %s\n' "$*" >&2
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
  parse_state install-maintenance "$1" "$2"
}

assert_idle() {
  grep -qx 'UPDATE_STATE=idle' < <(bash "${UPDATE_TRANSITION}" status) ||
    fail 'update transition is not idle'
  grep -qx 'TRANSACTION_STATE=idle' < <(bash "${RUNTIME_TRANSITION}" status) ||
    fail 'runtime transition is not idle'
  grep -qx 'PROFILE_SWITCH_STATE=idle' < <(bash "${PROFILE_TRANSITION}" status) ||
    fail 'profile-switch transition is not idle'
  grep -qx 'RELEASE_PROFILE_REFRESH_STATE=idle' < <(bash "${REFRESH_TRANSITION}" status) ||
    fail 'release-profile refresh transition is not idle'
  [[ ! -e "${RUNTIME_ADOPT_FILE}" && ! -L "${RUNTIME_ADOPT_FILE}" ]] ||
    fail "runtime adoption marker is still pending: ${RUNTIME_ADOPT_FILE}"

  local path
  for path in     "${SETTINGS_PHASE_FILE}" "${SETTINGS_START_FILE}" "${SETTINGS_NO_START_FILE}"     "${SETTINGS_PREV_SERVICE_FILE}" "${SETTINGS_PREV_CONTAINER_FILE}"     "${SETTINGS_BACKUP}" "${SETTINGS_TARGET}" "${SETTINGS_BACKUP_SHA}" "${SETTINGS_TARGET_SHA}"
  do
    [[ ! -e "${path}" && ! -L "${path}" ]] ||
      fail "settings transaction is not idle or has stale artifact: ${path}"
  done
}

assert_model_id() {
  local output
  output="$(curl -fsS --max-time 15 http://127.0.0.1:8888/v1/models)" ||
    fail 'managed model list is unavailable'
  python3 -c 'import json,sys; expected=sys.argv[1]; data=json.load(sys.stdin); raise SystemExit(0 if any(item.get("id") == expected for item in data.get("data", [])) else 1)'     "${MODEL}" <<<"${output}" || fail "served model identity mismatch: expected=${MODEL}"
}

assert_h38_runtime() {
  local expected_root="$1" container_id image running oom label
  load_install "${STATE_FILE}" LIVE || fail 'installation manifest failed strict parsing'
  [[ "${LIVE_PHASE}" == complete ]] || fail "installation phase is not complete: ${LIVE_PHASE}"
  [[ "${LIVE_MODEL_PROFILE}" == orcarouter ]] || fail "managed profile is not orcarouter: ${LIVE_MODEL_PROFILE}"
  [[ "${LIVE_VLLM_IMAGE}" == "${H38_IMAGE}" ]] || fail "managed image is not H38: ${LIVE_VLLM_IMAGE}"
  [[ "${LIVE_SERVED_NAME}" == "${MODEL}" ]] || fail "served alias mismatch: ${LIVE_SERVED_NAME}"
  [[ "$(realpath -m -- "${LIVE_INSTALL_ROOT}")" == "$(realpath -m -- "${expected_root}")" ]] ||
    fail "install root does not match target release: ${LIVE_INSTALL_ROOT}"

  systemctl is-active --quiet "${UNIT}" || fail 'managed service is not active'
  curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null ||
    fail 'managed H38 health endpoint is not ready'
  assert_model_id

  container_id="$(docker inspect --format '{{.Id}}' "${CONTAINER}" 2>/dev/null || true)"
  image="$(docker inspect --format '{{.Config.Image}}' "${CONTAINER}" 2>/dev/null || true)"
  running="$(docker inspect --format '{{.State.Running}}' "${CONTAINER}" 2>/dev/null || true)"
  oom="$(docker inspect --format '{{.State.OOMKilled}}' "${CONTAINER}" 2>/dev/null || true)"
  [[ -n "${container_id}" && "${running}" == true ]] || fail 'managed H38 container is not running'
  [[ "${image}" == "${H38_IMAGE}" ]] || fail "managed H38 container image mismatch: ${image:-missing}"
  [[ "${oom}" == false ]] || fail 'managed H38 container reports OOMKilled=true'
  docker inspect "${CONTAINER}.rollback" >/dev/null 2>&1 &&
    fail 'runtime rollback container exists outside a lifecycle transaction'

  label="$(docker image inspect --format '{{ index .Config.Labels "qwen38.h38scope" }}' "${H38_IMAGE}" 2>/dev/null || true)"
  [[ "${label}" == "${H38_SCOPE}" ]] || fail "H38 image label mismatch: ${label:-missing}"

  docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "${CONTAINER}" >"${OUT}/h38-env-current.txt"
  local expected
  for expected in     'VLLM_PLE_MMAP=1'     'VLLM_QSA_EXACT_TOPK=1'     'QWEN38_MARLIN_CANONICAL_ORDER=1'     'QWEN38_MARLIN_CANONICAL_SCOPE=decoder'     "VLLM_CACHE_ROOT=${H38_CACHE}"
  do
    grep -Fxq "${expected}" "${OUT}/h38-env-current.txt" ||
      fail "missing H38 runtime env: ${expected}"
  done

  docker inspect --format '{{json .Config.Cmd}}' "${CONTAINER}" >"${OUT}/h38-cmd-current.json"
  python3 - "${OUT}/h38-cmd-current.json" <<'PY' ||
import json
import sys
cmd = json.load(open(sys.argv[1], encoding="utf-8"))
idx = cmd.index("--kv-cache-memory-bytes")
raise SystemExit(0 if idx + 1 < len(cmd) and cmd[idx + 1] == "17179869184" else 1)
PY
  [[ "$?" == 0 ]] || fail 'managed H38 runtime does not pin the expected 16 GiB KV cache'

  [[ -f "${RUNTIME_COMMIT_FILE}" && ! -L "${RUNTIME_COMMIT_FILE}" ]] ||
    fail 'runtime commit attestation is missing'
  parse_state runtime-commit "${RUNTIME_COMMIT_FILE}" ATTEST ||
    fail 'runtime commit attestation failed strict parsing'
  [[ "${ATTEST_RUNTIME_ROOT}" == "$(realpath -e -- "${expected_root}")" ]] ||
    fail "runtime attestation root mismatch: ${ATTEST_RUNTIME_ROOT}"
  [[ "${ATTEST_RUNTIME_CONTAINER_NAME}" == "${CONTAINER}" &&
     "${ATTEST_RUNTIME_CONTAINER_ID}" == "${container_id}" ]] ||
    fail 'runtime attestation does not match the live container'
}

snapshot() {
  local suffix="$1"
  bash "${RELEASE_MANAGER}" status >"${OUT}/release-${suffix}.txt" 2>&1 || true
  bash "${UPDATE_TRANSITION}" status >"${OUT}/update-transition-${suffix}.txt" 2>&1 || true
  bash "${RUNTIME_TRANSITION}" status >"${OUT}/runtime-transition-${suffix}.txt" 2>&1 || true
  bash "${PROFILE_TRANSITION}" status >"${OUT}/profile-transition-${suffix}.txt" 2>&1 || true
  bash "${REFRESH_TRANSITION}" status >"${OUT}/release-profile-refresh-${suffix}.txt" 2>&1 || true
  systemctl status "${UNIT}" --no-pager >"${OUT}/service-${suffix}.txt" 2>&1 || true
  docker inspect "${CONTAINER}" >"${OUT}/container-${suffix}.json" 2>&1 || true
  [[ ! -f "${STATE_FILE}" ]] || cp -p -- "${STATE_FILE}" "${OUT}/install-${suffix}.env"
  [[ ! -f "${RUNTIME_COMMIT_FILE}" ]] || cp -p -- "${RUNTIME_COMMIT_FILE}" "${OUT}/runtime-commit-${suffix}.env"
  cp -p -- /proc/meminfo "${OUT}/meminfo-${suffix}.txt" 2>/dev/null || true
  swapon --show >"${OUT}/swapon-${suffix}.txt" 2>&1 || true
}

capture_window() {
  local monitor_total=0 start_line=1
  [[ "${WINDOW_STARTED}" == 1 && "${WINDOW_CAPTURED}" == 0 ]] || return 0
  sleep 2
  END_JOURNAL="$(date '+%Y-%m-%d %H:%M:%S')"
  WINDOW_CAPTURED=1
  printf '%s\n' "${END_JOURNAL}" >"${OUT}/measured-window-end.txt"

  if sudo -n journalctl -k     --since "${START_JOURNAL}" --until "${END_JOURNAL}"     -o short-iso-precise --no-pager     >"${OUT}/kernel-window.txt" 2>"${OUT}/kernel-window.stderr"
  then
    KERNEL_WINDOW_RC=0
  else
    KERNEL_WINDOW_RC=$?
  fi
  printf '%s\n' "${KERNEL_WINDOW_RC}" >"${OUT}/kernel-window.rc"

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
  grep -q 'PROTECT stopping' "${OUT}/monitor-window.log" 2>/dev/null &&
    PROTECTED_STOP=1 || PROTECTED_STOP=0
}

write_summary() {
  local rc="$1"
  {
    printf 'target_sha=%s\n' "${TARGET_SHA}"
    printf 'migration_evidence=%s\n' "${MIGRATION_EVIDENCE}"
    printf 'determinism=%s\n' "${DETERMINISM}"
    printf 'performance=%s\n' "${PERFORMANCE}"
    printf 'restart_attestation=%s\n' "${RESTART_ATTESTATION}"
    printf 'host_stability=%s\n' "${HOST_STABILITY}"
    printf 'baseline_decode_median_tok_s=%s\n' "${BASELINE_MEDIAN:-unset}"
    printf 'candidate_decode_median_tok_s=%s\n' "${CANDIDATE_MEDIAN:-unset}"
    printf 'performance_ratio=%s\n' "${PERFORMANCE_RATIO:-unset}"
    printf 'kernel_window_rc=%s\n' "${KERNEL_WINDOW_RC}"
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
    exit "${rc}"
  fi

  capture_window
  snapshot after
  journalctl -u "${UNIT}" --since "${START_JOURNAL:-today}" --no-pager     >"${OUT}/service-window.txt" 2>&1 || true

  if (( RM_OOM_COUNT > 0 )); then
    HOST_STABILITY="FAIL"
  elif [[ "${KERNEL_WINDOW_RC}" != 0 || "${PROTECTED_STOP}" != 0 ]]; then
    HOST_STABILITY="INCONCLUSIVE"
  elif [[ "${DETERMINISM}" == PASS && "${PERFORMANCE}" == PASS &&
          "${RESTART_ATTESTATION}" == PASS ]]; then
    HOST_STABILITY="PASS"
  else
    HOST_STABILITY="INCONCLUSIVE"
  fi

  if (( RM_OOM_COUNT > 0 )) && [[ "${rc}" == 0 ]]; then
    rc=1
    FAIL_REASON="strict NVIDIA RM no-memory evidence observed"
  elif [[ "${KERNEL_WINDOW_RC}" != 0 && "${rc}" == 0 ]]; then
    rc=1
    FAIL_REASON="kernel evidence window collection failed with rc=${KERNEL_WINDOW_RC}"
  elif [[ "${PROTECTED_STOP}" != 0 && "${rc}" == 0 ]]; then
    rc=1
    FAIL_REASON="memory protection intervened during follow-up acceptance window"
  fi

  write_summary "${rc}"
  {
    printf '===== summary =====\n'
    cat "${OUT}/summary.txt"
    for evidence_file in       determinism.log candidate-decode.json restart.log doctor-strict.txt       kernel-errors.txt monitor-window.log service-window.txt
    do
      [[ -f "${OUT}/${evidence_file}" ]] || continue
      printf '\n===== %s =====\n' "${evidence_file}"
      cat "${OUT}/${evidence_file}"
    done
  } >"${OUT}/upload-summary.txt"

  printf '\n===== H38 managed follow-up summary =====\n'
  cat "${OUT}/summary.txt"
  printf 'evidence=%s\n' "${OUT}"
  printf 'upload_summary=%s\n' "${OUT}/upload-summary.txt"
  exit "${rc}"
}
trap finalize EXIT INT TERM

[[ "${TARGET_SHA}" =~ ^[0-9a-f]{40}$ ]] || {
  usage >&2
  fail 'H38_MANAGED_TARGET_SHA must be the exact 40-character target commit SHA'
}
[[ -n "${MIGRATION_EVIDENCE}" ]] || {
  usage >&2
  fail 'H38_MANAGED_MIGRATION_EVIDENCE is required'
}
[[ -d "${MIGRATION_EVIDENCE}" && ! -L "${MIGRATION_EVIDENCE}" ]] ||
  fail "migration evidence directory is missing or unsafe: ${MIGRATION_EVIDENCE}"

for command in bash git python3 docker systemctl curl journalctl date grep awk sed cp   realpath sudo swapon wc mktemp sleep tee
do
  require_command "${command}"
done

ACTUAL_SHA="$(git -C "${ROOT}" rev-parse HEAD)"
[[ "${ACTUAL_SHA}" == "${TARGET_SHA}" ]] ||
  fail "checkout SHA mismatch: expected=${TARGET_SHA} actual=${ACTUAL_SHA}"
[[ -z "$(git -C "${ROOT}" status --porcelain=v1 --untracked-files=all)" ]] ||
  fail 'working tree is dirty; preserve local changes before live acceptance'
sudo -n true >/dev/null 2>&1 ||
  fail 'sudo timestamp unavailable; run sudo -v before this gate'

migration_target="$(cat "${MIGRATION_EVIDENCE}/target-sha.txt" 2>/dev/null || true)"
[[ "${migration_target}" == "${TARGET_SHA}" ]] ||
  fail "migration evidence target mismatch: ${migration_target:-missing}"
grep -qx 'functional=PASS' "${MIGRATION_EVIDENCE}/summary.txt" ||
  fail 'migration evidence is not FUNCTIONAL PASS'
grep -qx 'host_stability=PASS' "${MIGRATION_EVIDENCE}/summary.txt" ||
  fail 'migration evidence is not HOST-STABILITY PASS'
grep -qx 'script_rc=0' "${MIGRATION_EVIDENCE}/summary.txt" ||
  fail 'migration gate did not complete successfully'
BASELINE_MEDIAN="$(cat "${MIGRATION_EVIDENCE}/baseline-decode-median.txt" 2>/dev/null || true)"
python3 - "${BASELINE_MEDIAN}" <<'PY' || fail 'migration baseline median is missing or invalid'
import math
import sys
try:
    value = float(sys.argv[1])
except ValueError:
    raise SystemExit(1)
raise SystemExit(0 if math.isfinite(value) and value > 0 else 1)
PY

[[ ! -e "${OUT}" && ! -L "${OUT}" ]] || fail "evidence path already exists: ${OUT}"
mkdir -p -- "${OUT}"
OUT_READY=1
exec > >(tee -a "${OUT}/run.log") 2>&1

printf '%s\n' "${TARGET_SHA}" >"${OUT}/target-sha.txt"
printf '%s\n' "${MIGRATION_EVIDENCE}" >"${OUT}/migration-evidence-path.txt"
git -C "${ROOT}" status --porcelain=v1 --untracked-files=all >"${OUT}/git-status.txt"

CURRENT_STATUS="$(bash "${RELEASE_MANAGER}" status)"
CURRENT_RELEASE="$(awk -F= '$1=="CURRENT_RELEASE" {print $2}' <<<"${CURRENT_STATUS}")"
[[ "${CURRENT_RELEASE}" == "${TARGET_SHA}" ]] ||
  fail "current release is not the exact target: ${CURRENT_RELEASE}"
TARGET_ROOT="$(readlink -f -- "${CURRENT_LINK}")"
[[ "${TARGET_ROOT}" == "${DATA_HOME}/releases/${TARGET_SHA}" ]] ||
  fail "current release pointer is not the exact target: ${TARGET_ROOT}"
assert_idle
assert_h38_runtime "${TARGET_ROOT}"

set +e
bash "${DOCTOR}" --strict >"${OUT}/doctor-before.txt" 2>&1
doctor_before_rc=$?
set -e
[[ "${doctor_before_rc}" == 0 ]] || fail "doctor --strict is not clean before follow-up gates (rc=${doctor_before_rc})"

snapshot before
PRE_CONTAINER_ID="$(docker inspect --format '{{.Id}}' "${CONTAINER}")"
printf '%s\n' "${PRE_CONTAINER_ID}" >"${OUT}/container-id-before.txt"
MONITOR_LINES_BEFORE=0
[[ ! -f "${MONITOR_LOG}" ]] || MONITOR_LINES_BEFORE="$(wc -l <"${MONITOR_LOG}")"
START_JOURNAL="$(date '+%Y-%m-%d %H:%M:%S')"
printf '%s\n' "${START_JOURNAL}" >"${OUT}/measured-window-start.txt"
WINDOW_STARTED=1

printf '\n===== managed H38 determinism matrix =====\n'
set +e
H38_GATE_MODEL="${MODEL}" H38_GATE_OUT="${OUT}/determinism"   bash "${DET_GATE}" >"${OUT}/determinism.log" 2>&1
det_rc=$?
set -e
cat "${OUT}/determinism.log"
[[ "${det_rc}" == 0 ]] || fail "managed H38 determinism matrix failed with rc=${det_rc}"
DETERMINISM="PASS"

printf '\n===== managed H38 matched decode performance =====\n'
python3 "${BENCHMARK}" decode   --model "${MODEL}"   --decode-tokens 384   --decode-repeats 5   --output "${OUT}/candidate-decode.json"
CANDIDATE_MEDIAN="$(python3 - "${OUT}/candidate-decode.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
print(data["workloads"]["decode"]["decode_tokens_s"]["median"])
PY
)"
PERFORMANCE_RATIO="$(python3 - "${BASELINE_MEDIAN}" "${CANDIDATE_MEDIAN}" <<'PY'
import math
import sys
baseline = float(sys.argv[1])
candidate = float(sys.argv[2])
ratio = candidate / baseline
if not math.isfinite(ratio):
    raise SystemExit(1)
print(f"{ratio:.6f}")
raise SystemExit(0 if ratio >= 0.90 else 2)
PY
)" || perf_rc=$?
perf_rc="${perf_rc:-0}"
printf 'baseline_decode_median_tok_s=%s\n' "${BASELINE_MEDIAN}"
printf 'candidate_decode_median_tok_s=%s\n' "${CANDIDATE_MEDIAN}"
printf 'performance_ratio=%s\n' "${PERFORMANCE_RATIO:-invalid}"
[[ "${perf_rc}" == 0 ]] ||
  fail "managed H38 decode performance is below 90% of matched baseline or invalid"
PERFORMANCE="PASS"

printf '\n===== managed H38 service replacement / restart =====\n'
set +e
sudo -n bash "${MANAGE_SERVICE}" create --runtime-root "${CURRENT_LINK}" --start --yes   >"${OUT}/restart.log" 2>&1
restart_rc=$?
set -e
cat "${OUT}/restart.log"
[[ "${restart_rc}" == 0 ]] || fail "managed service replacement failed with rc=${restart_rc}"

POST_CONTAINER_ID="$(docker inspect --format '{{.Id}}' "${CONTAINER}" 2>/dev/null || true)"
[[ -n "${POST_CONTAINER_ID}" && "${POST_CONTAINER_ID}" != "${PRE_CONTAINER_ID}" ]] ||
  fail 'managed restart did not replace the container'
assert_idle
assert_h38_runtime "${TARGET_ROOT}"

set +e
bash "${DOCTOR}" --strict >"${OUT}/doctor-strict.txt" 2>&1
doctor_rc=$?
set -e
cat "${OUT}/doctor-strict.txt"
[[ "${doctor_rc}" == 0 ]] || fail "doctor --strict failed after managed restart with rc=${doctor_rc}"
RESTART_ATTESTATION="PASS"

capture_window
if [[ "${KERNEL_WINDOW_RC}" != 0 ]]; then
  fail "kernel evidence window collection failed with rc=${KERNEL_WINDOW_RC}"
fi
if (( RM_OOM_COUNT > 0 )); then
  fail 'strict NVIDIA RM no-memory evidence observed during follow-up acceptance'
fi
if [[ "${PROTECTED_STOP}" != 0 ]]; then
  fail 'memory protection intervened during follow-up acceptance window'
fi
HOST_STABILITY="PASS"
printf 'H38_MANAGED_FOLLOWUP_RESULT=PASS\n'
