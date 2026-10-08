#!/usr/bin/env bash
# H38 allocator protection discriminator.
#
# Observe the exact H38 production startup SPEC=mtp k=2 using a read-only
# allocator collector. No release/profile/lifecycle mutation. The managed
# predecessor remains stopped and current protection policy stays unchanged.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"
STATE_FILE="${STATE_HOME}/install.env"
CURRENT_LINK="${DATA_HOME}/current"
UNIT="qwen38-flash-next.service"
MANAGED_CONTAINER="qwen38-flash-next"
ROLLBACK_CONTAINER="qwen38-flash-next.rollback"
EXPERIMENT_CONTAINER="qwen38-h38-allocator-protection"
MODEL="orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4"
H38_IMAGE="vllm-orcarouter-v029-h38-decoder-scope:v1"
H38_SCOPE="decoder-v1"
KV_BYTES="17179869184"
TARGET_SHA="${H38_ALLOCATOR_DISCRIMINATOR_TARGET_SHA:-${1:-}}"
OUT="${H38_ALLOCATOR_DISCRIMINATOR_OUT:-/tmp/orcarouter-h38-allocator-protection-$(date -u '+%Y%m%dT%H%M%SZ')}"

STATE_PARSER="${ROOT}/scripts/state_file.py"
SERVE="${ROOT}/scripts/serve.sh"
PREPARE_CONFIG="${ROOT}/scripts/prepare-config.py"
PREPARE_H38="${ROOT}/scripts/prepare-h38-image.sh"
MONITOR="${ROOT}/scripts/monitor-runtime.sh"
UPDATE_TRANSITION="${ROOT}/scripts/update-transition.sh"
RUNTIME_TRANSITION="${ROOT}/scripts/runtime-transition.sh"
PROFILE_TRANSITION="${ROOT}/scripts/profile-switch-transition.sh"
REFRESH_TRANSITION="${ROOT}/scripts/release-profile-refresh-transition.sh"
RELEASE_MANAGER="${ROOT}/scripts/release-manager.sh"
COLLECTOR="${ROOT}/scripts/benchmark/collect-linux-allocator-state.py"
ANALYZER="${ROOT}/scripts/benchmark/analyze-h38-allocator-protection-trajectory.py"
STATE_OUT="${OUT}/allocator-state"
COLLECTOR_STOP="${OUT}/collector.stop"

SETTINGS_PHASE_FILE="${STATE_HOME}/settings-transition.phase"
SETTINGS_START_FILE="${STATE_HOME}/settings-transition.start"
SETTINGS_NO_START_FILE="${STATE_HOME}/settings-transition.no-start"
SETTINGS_PREV_SERVICE_FILE="${STATE_HOME}/settings-transition.previous-service-active"
SETTINGS_PREV_CONTAINER_FILE="${STATE_HOME}/settings-transition.previous-container-running"
SETTINGS_BACKUP="${STATE_FILE}.settings-backup"
SETTINGS_TARGET="${STATE_FILE}.settings-candidate"
SETTINGS_BACKUP_SHA="${SETTINGS_BACKUP}.sha256"
SETTINGS_TARGET_SHA="${SETTINGS_TARGET}.sha256"
RUNTIME_ADOPT_FILE="${STATE_HOME}/runtime-adopt.env"
LOCK_FILE="${STATE_HOME}/operation.lock"

MODEL_PROFILE=""
MODEL_DIR=""
SERVED_NAME=""
INSTALL_PHASE=""
INSTALL_ROOT=""
MANAGED_IMAGE=""
CURRENT_RELEASE=""
CURRENT_ROOT=""
MANAGED_CONTAINER_ID=""
MONITOR_PID=""
SUDO_KEEPALIVE_PID=""
LOCK_FD=""
OUT_READY=0
EXPERIMENT_STARTED=0
WINDOW_STARTED=0
WINDOW_CAPTURED=0
FINALIZED=0
START_JOURNAL=""
END_JOURNAL=""
KERNEL_WINDOW_RC=125
RM_OOM_COUNT=0
PROTECTED_STOP=0
START_RC=125
READY_RC=125
API_READY=0
OOM_KILLED="unknown"
FUNCTIONAL="NOT_REACHED"
HOST_STABILITY="INCONCLUSIVE"
RESULT="INVALID"
FAIL_REASON=""
IDENTITY_VALIDATED=0
RUN_COMPLETED=0
COLLECTOR_PID=""
COLLECTOR_RC=125
COLLECTOR_HEALTHY=0
ANALYSIS_RC=125

usage() {
  cat <<'EOF'
Usage:
  sudo -v
  H38_ALLOCATOR_DISCRIMINATOR_TARGET_SHA=<exact-40-char-sha> \
    bash scripts/benchmark/run-h38-allocator-protection-discriminator.sh

Optional:
  H38_ALLOCATOR_DISCRIMINATOR_OUT=/path/to/new/evidence-dir

Required starting state:
  lifecycle idle; managed service inactive; restored predecessor container
  present but stopped after the protected atomic migration attempt.

Exact H38 production shape: SPEC=mtp, k=2.
Read-only allocator collection: 1-second fast and 5-second slow samples.
Protection thresholds, protect mode, H38 image/runtime identity, and strict RM
classification remain unchanged. This is not the managed promotion gate.
EOF
}

fail() {
  FAIL_REASON="$*"
  printf 'H38_ALLOCATOR_DISCRIMINATOR_ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
}

parse_install() {
  local parsed key value
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" install-maintenance "${STATE_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    case "${key}" in
      PHASE) INSTALL_PHASE="${value}" ;;
      INSTALL_ROOT) INSTALL_ROOT="${value}" ;;
      MODEL_PROFILE) MODEL_PROFILE="${value}" ;;
      MODEL_DIR) MODEL_DIR="${value}" ;;
      VLLM_IMAGE) MANAGED_IMAGE="${value}" ;;
      SERVED_NAME) SERVED_NAME="${value}" ;;
    esac
  done <"${parsed}"
  rm -f -- "${parsed}"
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
  for path in \
    "${SETTINGS_PHASE_FILE}" "${SETTINGS_START_FILE}" "${SETTINGS_NO_START_FILE}" \
    "${SETTINGS_PREV_SERVICE_FILE}" "${SETTINGS_PREV_CONTAINER_FILE}" \
    "${SETTINGS_BACKUP}" "${SETTINGS_TARGET}" \
    "${SETTINGS_BACKUP_SHA}" "${SETTINGS_TARGET_SHA}"
  do
    [[ ! -e "${path}" && ! -L "${path}" ]] ||
      fail "settings transaction is not idle or has stale artifact: ${path}"
  done
}

acquire_experiment_lock() {
  mkdir -p -- "${STATE_HOME}"
  [[ ! -L "${LOCK_FILE}" ]] || fail "operation lock is symlinked: ${LOCK_FILE}"
  if [[ ! -e "${LOCK_FILE}" ]]; then
    (umask 077; : >"${LOCK_FILE}")
  fi
  [[ -f "${LOCK_FILE}" ]] || fail "operation lock is not a regular file: ${LOCK_FILE}"
  exec {LOCK_FD}<>"${LOCK_FILE}"
  flock -n "${LOCK_FD}" || fail "another lifecycle operation is active: ${LOCK_FILE}"
  printf 'Lifecycle operation lock acquired for isolated H38 allocator protection discriminator.\n'
}

assert_post_protection_baseline() {
  parse_install || fail 'installation manifest failed strict parsing'
  [[ "${INSTALL_PHASE}" == complete ]] ||
    fail "installation phase is not complete: ${INSTALL_PHASE:-missing}"
  [[ "${MODEL_PROFILE}" == orcarouter ]] ||
    fail "managed profile is not orcarouter: ${MODEL_PROFILE:-missing}"
  [[ "${SERVED_NAME}" == "${MODEL}" ]] ||
    fail "managed served alias mismatch: ${SERVED_NAME:-missing}"
  [[ -n "${MODEL_DIR}" && -f "${MODEL_DIR}/model.safetensors.index.json" ]] ||
    fail 'managed OrcaRouter checkpoint is unavailable'
  [[ -L "${CURRENT_LINK}" ]] || fail "immutable current release pointer is missing: ${CURRENT_LINK}"

  CURRENT_RELEASE="$(bash "${RELEASE_MANAGER}" status | awk -F= '$1=="CURRENT_RELEASE" {print $2}')"
  [[ -n "${CURRENT_RELEASE}" && "${CURRENT_RELEASE}" != none ]] ||
    fail 'no immutable current release is registered'
  CURRENT_ROOT="$(readlink -f -- "${CURRENT_LINK}")"
  [[ "${CURRENT_ROOT}" == "${DATA_HOME}/releases/${CURRENT_RELEASE}" ]] ||
    fail "current release pointer mismatch: ${CURRENT_ROOT}"
  bash "${RELEASE_MANAGER}" verify "${CURRENT_RELEASE}" >/dev/null ||
    fail "restored current release failed manifest verification: ${CURRENT_RELEASE}"

  # INSTALL_ROOT records the repository root from which the installer wrote the
  # canonical manifest. It is not the immutable runtime pointer. A failed
  # release-profile refresh intentionally restores the exact predecessor
  # manifest, so this can legitimately be the operator checkout while
  # CURRENT_LINK points at the verified immutable predecessor release.
  restored_install_root="$(realpath -e -- "${INSTALL_ROOT}" 2>/dev/null || true)"
  [[ -n "${restored_install_root}" && -d "${restored_install_root}" ]] ||
    fail "restored manifest INSTALL_ROOT is unavailable: ${INSTALL_ROOT}"
  [[ -r "${restored_install_root}/scripts/model-profiles.sh" &&
     -r "${restored_install_root}/scripts/release-manager.sh" ]] ||
    fail "restored manifest INSTALL_ROOT is not a repository root: ${restored_install_root}"

  if systemctl is-active --quiet "${UNIT}"; then
    fail 'managed service is active; this discriminator requires the preserved stopped post-protection state'
  fi
  if curl -fsS --max-time 2 http://127.0.0.1:8888/health >/dev/null 2>&1; then
    fail 'port 8888 already exposes a healthy service'
  fi

  MANAGED_CONTAINER_ID="$(docker inspect --format '{{.Id}}' "${MANAGED_CONTAINER}" 2>/dev/null || true)"
  [[ -n "${MANAGED_CONTAINER_ID}" ]] || fail 'restored managed predecessor container is missing'
  [[ "$(docker inspect --format '{{.State.Running}}' "${MANAGED_CONTAINER}")" == false ]] ||
    fail 'restored managed predecessor container is unexpectedly running'
  [[ "$(docker inspect --format '{{.State.OOMKilled}}' "${MANAGED_CONTAINER}")" == false ]] ||
    fail 'restored managed predecessor container reports OOMKilled=true'
  [[ "$(docker inspect --format '{{.Config.Image}}' "${MANAGED_CONTAINER}")" == "${MANAGED_IMAGE}" ]] ||
    fail 'restored managed predecessor image does not match install manifest'

  if docker inspect "${ROLLBACK_CONTAINER}" >/dev/null 2>&1; then
    fail "stale rollback container exists: ${ROLLBACK_CONTAINER}"
  fi
  if docker inspect "${EXPERIMENT_CONTAINER}" >/dev/null 2>&1; then
    fail "experiment container already exists: ${EXPERIMENT_CONTAINER}"
  fi
  return 0
}

capture_kernel_window() {
  [[ "${WINDOW_STARTED}" == 1 && "${WINDOW_CAPTURED}" == 0 ]] || return 0
  sleep 2
  END_JOURNAL="$(date '+%Y-%m-%d %H:%M:%S')"
  WINDOW_CAPTURED=1
  printf '%s\n' "${END_JOURNAL}" >"${OUT}/measured-window-end.txt"

  if sudo -n journalctl -k \
      --since "${START_JOURNAL}" \
      --until "${END_JOURNAL}" \
      -o short-iso-precise --no-pager \
      >"${OUT}/kernel-window.txt" 2>"${OUT}/kernel-window.stderr"
  then
    KERNEL_WINDOW_RC=0
  else
    KERNEL_WINDOW_RC=$?
  fi
  printf '%s\n' "${KERNEL_WINDOW_RC}" >"${OUT}/kernel-window.rc"

  grep -Ei \
    'NV_ERR_NO_MEMORY|_memdescAllocInternal|NVRM:.*Xid|Xid \(PCI|GPU has fallen off the bus|oom-kill:|Out of memory:|Killed process ' \
    "${OUT}/kernel-window.txt" >"${OUT}/kernel-errors.txt" || true
  RM_OOM_COUNT="$(grep -Ec 'NV_ERR_NO_MEMORY|_memdescAllocInternal' "${OUT}/kernel-errors.txt" 2>/dev/null || true)"
  [[ "${RM_OOM_COUNT}" =~ ^[0-9]+$ ]] || RM_OOM_COUNT=0
}

capture_monitor_summary() {
  local log="${OUT}/memory-monitor.log"
  [[ -f "${log}" ]] || return 0
  grep -E \
    'monitor started:|WARNING memory margin low protect=|PROTECT stopping |memory margin recovered:|HEARTBEAT healthy:' \
    "${log}" >"${OUT}/monitor-protection-window.txt" || true
  grep -q 'PROTECT stopping' "${log}" && PROTECTED_STOP=1 || PROTECTED_STOP=0
}

finish_collector() {
  [[ -n "${COLLECTOR_PID}" ]] || return 0
  : >"${COLLECTOR_STOP}"
  if wait "${COLLECTOR_PID}"; then COLLECTOR_RC=0; else COLLECTOR_RC=$?; fi
  COLLECTOR_PID=""
  if [[ "${COLLECTOR_RC}" == 0 &&
        -s "${STATE_OUT}/fast-state.txt" &&
        -s "${STATE_OUT}/slow-state.txt" &&
        -f "${STATE_OUT}/kernel-follow.txt" &&
        -f "${STATE_OUT}/collector-meta.txt" ]] &&
     grep -q '^finished_wall=' "${STATE_OUT}/collector-meta.txt" &&
     ! grep -q 'READ_ERROR' "${STATE_OUT}/fast-state.txt" "${STATE_OUT}/slow-state.txt" &&
     ! grep -Eiq 'permission denied|failed to open|no journal files' "${STATE_OUT}/kernel-follow.txt"; then
    COLLECTOR_HEALTHY=1
  fi
  if python3 "${ANALYZER}" --evidence "${OUT}" \
    --csv "${OUT}/allocator-trajectory.csv" \
    --report "${OUT}/allocator-analysis.txt" >"${OUT}/allocator-analyzer.log" 2>&1; then
    ANALYSIS_RC=0
  else
    ANALYSIS_RC=$?
  fi
}
capture_startup_phase() {
  [[ -f "${OUT}/candidate-container.log" ]] || return 0
  grep -E \
    'Checkpoint size:|Auto-prefetch|Loading safetensors checkpoint shards:|Loading weights took|Model loading took|Draft model|[Ss]peculator|init engine|Starting vLLM server' \
    "${OUT}/candidate-container.log" >"${OUT}/startup-phase.txt" || true
}

stop_experiment() {
  if [[ "${EXPERIMENT_STARTED}" == 1 ]] &&
     [[ "$(docker inspect --format '{{.State.Running}}' "${EXPERIMENT_CONTAINER}" 2>/dev/null || true)" == true ]]; then
    docker stop --timeout 30 "${EXPERIMENT_CONTAINER}" >/dev/null 2>&1 || true
  fi
  if docker inspect "${EXPERIMENT_CONTAINER}" >/dev/null 2>&1; then
    docker rm "${EXPERIMENT_CONTAINER}" >/dev/null 2>&1 || true
  fi
  EXPERIMENT_STARTED=0
}

classify() {
  # Incomplete identity, kernel window, or collector invalidates causal claims.
  if [[ "${RUN_COMPLETED}" != 1 ||
        "${IDENTITY_VALIDATED}" != 1 ||
        "${KERNEL_WINDOW_RC}" != 0 ||
        "${COLLECTOR_HEALTHY}" != 1 ||
        "${ANALYSIS_RC}" != 0 ||
        "${OOM_KILLED}" == unknown ]]; then
    FUNCTIONAL="NOT_REACHED"
    HOST_STABILITY="INCONCLUSIVE"
    RESULT="INVALID"
    return 0
  fi
  if (( RM_OOM_COUNT > 0 )); then
    HOST_STABILITY="FAIL"
    if [[ "${API_READY}" == 1 ]]; then
      FUNCTIONAL="PASS"
      RESULT="FUNCTIONAL_PASS_HOST_FAIL"
    else
      FUNCTIONAL="NOT_REACHED"
      RESULT="FUNCTIONAL_NOT_REACHED_HOST_FAIL"
    fi
  elif [[ "${OOM_KILLED}" == true ]]; then
    FUNCTIONAL="NOT_REACHED"
    HOST_STABILITY="FAIL"
    RESULT="DOCKER_OOM_KILLED"
  elif [[ "${PROTECTED_STOP}" == 1 ]]; then
    FUNCTIONAL="NOT_REACHED"
    HOST_STABILITY="INCONCLUSIVE"
    RESULT="PROTECTED_STOP"
  elif [[ "${KERNEL_WINDOW_RC}" == 0 &&
          "${API_READY}" == 1 &&
          "${OOM_KILLED}" == false &&
          "${IDENTITY_VALIDATED}" == 1 ]]; then
    FUNCTIONAL="PASS"
    HOST_STABILITY="PASS"
    RESULT="VALID_CLEAN"
  else
    FUNCTIONAL="NOT_REACHED"
    HOST_STABILITY="INCONCLUSIVE"
    RESULT="INVALID"
  fi
}

write_summary() {
  local rc="$1"
  {
    printf 'target_sha=%s\n' "${TARGET_SHA}"
    printf 'current_release=%s\n' "${CURRENT_RELEASE}"
    printf 'managed_container_id=%s\n' "${MANAGED_CONTAINER_ID}"
    printf 'candidate_image=%s\n' "${H38_IMAGE}"
    printf 'spec=mtp_k2\n'
    printf 'kv_bytes=%s\n' "${KV_BYTES}"
    printf 'start_rc=%s\n' "${START_RC}"
    printf 'wait_ready_rc=%s\n' "${READY_RC}"
    printf 'api_ready=%s\n' "${API_READY}"
    printf 'oom_killed=%s\n' "${OOM_KILLED}"
    printf 'functional=%s\n' "${FUNCTIONAL}"
    printf 'host_stability=%s\n' "${HOST_STABILITY}"
    printf 'kernel_window_rc=%s\n' "${KERNEL_WINDOW_RC}"
    printf 'rm_oom_count=%s\n' "${RM_OOM_COUNT}"
    printf 'protected_stop=%s\n' "${PROTECTED_STOP}"
    printf 'identity_validated=%s\n' "${IDENTITY_VALIDATED}"
    printf 'run_completed=%s\n' "${RUN_COMPLETED}"
    printf 'collector_rc=%s\n' "${COLLECTOR_RC}"
    printf 'collector_healthy=%s\n' "${COLLECTOR_HEALTHY}"
    printf 'analysis_rc=%s\n' "${ANALYSIS_RC}"
    printf 'result=%s\n' "${RESULT}"
    printf 'fail_reason=%s\n' "${FAIL_REASON:-none}"
    printf 'script_rc=%s\n' "${rc}"
  } >"${OUT}/summary.txt"
}

write_upload_summary() {
  {
    printf '===== summary =====\n'
    cat "${OUT}/summary.txt"
    for f in \
      monitor-protection-window.txt kernel-errors.txt startup-phase.txt \
      allocator-analysis.txt collector.log allocator-analyzer.log \
      candidate-start.stdout candidate-start.stderr
    do
      [[ -f "${OUT}/${f}" ]] || continue
      printf '\n===== %s =====\n' "${f}"
      cat "${OUT}/${f}"
    done
  } >"${OUT}/upload-summary.txt"
}

finalize() {
  local rc="$?"
  [[ "${FINALIZED}" == 0 ]] || exit "${rc}"
  FINALIZED=1
  trap - EXIT INT TERM
  set +e

  if [[ "${OUT_READY}" == 1 && -d "${OUT}" ]]; then
    if [[ -n "${MONITOR_PID}" ]] && kill -0 "${MONITOR_PID}" >/dev/null 2>&1; then
      kill "${MONITOR_PID}" >/dev/null 2>&1 || true
      wait "${MONITOR_PID}" >/dev/null 2>&1 || true
    fi
    MONITOR_PID=""
    capture_monitor_summary

    if docker inspect "${EXPERIMENT_CONTAINER}" >/dev/null 2>&1; then
      OOM_KILLED="$(docker inspect --format '{{.State.OOMKilled}}' "${EXPERIMENT_CONTAINER}" 2>/dev/null || printf unknown)"
      docker inspect "${EXPERIMENT_CONTAINER}" >"${OUT}/candidate-inspect-final.json" 2>&1 || true
      docker logs --timestamps "${EXPERIMENT_CONTAINER}" >"${OUT}/candidate-container.log" 2>&1 || true
      capture_startup_phase
    fi

    finish_collector
    capture_kernel_window
    classify
    stop_experiment
    write_summary "${rc}"
    write_upload_summary
    printf '\n===== H38 allocator protection discriminator summary =====\n'
    cat "${OUT}/summary.txt"
    printf 'evidence=%s\n' "${OUT}"
    printf 'upload_summary=%s\n' "${OUT}/upload-summary.txt"
    printf 'Managed predecessor remains in its original stopped post-protection state.\n'
  fi

  if [[ -n "${SUDO_KEEPALIVE_PID}" ]] && kill -0 "${SUDO_KEEPALIVE_PID}" >/dev/null 2>&1; then
    kill "${SUDO_KEEPALIVE_PID}" >/dev/null 2>&1 || true
    wait "${SUDO_KEEPALIVE_PID}" >/dev/null 2>&1 || true
  fi
  exit "${rc}"
}
trap finalize EXIT INT TERM

[[ "${TARGET_SHA}" =~ ^[0-9a-f]{40}$ ]] || {
  usage >&2
  fail 'H38_ALLOCATOR_DISCRIMINATOR_TARGET_SHA must be the exact 40-character target commit SHA'
}

for command in \
  bash git python3 docker systemctl curl journalctl date grep awk sed cp \
  realpath sudo swapon wc mktemp sleep tee flock seq
do
  require_command "${command}"
done

ACTUAL_SHA="$(git -C "${ROOT}" rev-parse HEAD)"
[[ "${ACTUAL_SHA}" == "${TARGET_SHA}" ]] ||
  fail "checkout SHA mismatch: expected=${TARGET_SHA} actual=${ACTUAL_SHA}"
[[ -z "$(git -C "${ROOT}" status --porcelain=v1 --untracked-files=all)" ]] ||
  fail 'working tree is dirty; preserve local changes before live discriminator'
sudo -n true >/dev/null 2>&1 ||
  fail 'sudo timestamp unavailable; run sudo -v before this discriminator'

for path in \
  "${STATE_FILE}" "${STATE_PARSER}" "${SERVE}" "${PREPARE_CONFIG}" \
  "${PREPARE_H38}" "${MONITOR}" "${COLLECTOR}" "${ANALYZER}"
do
  [[ -r "${path}" ]] || fail "required path is unavailable: ${path}"
done

assert_idle
assert_post_protection_baseline
acquire_experiment_lock
assert_idle
assert_post_protection_baseline

[[ ! -e "${OUT}" && ! -L "${OUT}" ]] ||
  fail "evidence path already exists: ${OUT}"
mkdir -p -- "${OUT}"
OUT_READY=1
exec > >(tee -a "${OUT}/run.log") 2>&1

(
  while sleep 60; do
    sudo -n -v >/dev/null 2>&1 || exit 0
  done
) &
SUDO_KEEPALIVE_PID=$!

printf '%s\n' "${TARGET_SHA}" >"${OUT}/target-sha.txt"
printf '%s\n' "${CURRENT_RELEASE}" >"${OUT}/current-release.txt"
printf '%s\n' "${CURRENT_ROOT}" >"${OUT}/current-release-root.txt"
printf '%s\n' "${INSTALL_ROOT}" >"${OUT}/manifest-install-root.txt"
printf '%s\n' "${MANAGED_CONTAINER_ID}" >"${OUT}/managed-container-id-before.txt"
printf '%s\n' "${MODEL_DIR}" >"${OUT}/model-dir.txt"
printf '%s\n' "${MODEL}" >"${OUT}/served-model.txt"
cp -p -- "${STATE_FILE}" "${OUT}/install-before.env"
cp -p -- /proc/meminfo "${OUT}/meminfo-before.txt"
swapon --show >"${OUT}/swapon-before.txt" 2>&1 || true

bash "${PREPARE_H38}" verify >"${OUT}/h38-image-verify.txt" 2>&1 ||
  fail 'H38 image provenance verification failed'
H38_LABEL="$(docker image inspect --format '{{ index .Config.Labels "qwen38.h38scope" }}' "${H38_IMAGE}" 2>/dev/null || true)"
[[ "${H38_LABEL}" == "${H38_SCOPE}" ]] ||
  fail "H38 image label mismatch: ${H38_LABEL:-missing}"

python3 "${PREPARE_CONFIG}" \
  --model-dir "${MODEL_DIR}" \
  --output "${OUT}/config.vllm.json"


# Fail closed when the collector cannot sample before candidate startup.
sudo -n journalctl -k -n 1 --no-pager >/dev/null 2>&1 ||
  fail 'kernel journal not readable for allocator sidecar'
sudo -n python3 "${COLLECTOR}" --output "${STATE_OUT}" \
  --stop-file "${COLLECTOR_STOP}" --fast-interval 1 --slow-interval 5 \
  >"${OUT}/collector.log" 2>&1 &
COLLECTOR_PID=$!
for ((poll=0; poll<120; poll++)); do
  [[ -s "${STATE_OUT}/fast-state.txt" &&
     -s "${STATE_OUT}/slow-state.txt" ]] && break
  kill -0 "${COLLECTOR_PID}" 2>/dev/null ||
    fail 'allocator sidecar exited before the first samples'
  sleep 0.5
done
[[ -s "${STATE_OUT}/fast-state.txt" && -s "${STATE_OUT}/slow-state.txt" ]] ||
  fail 'allocator sidecar did not produce fast and slow samples'

START_JOURNAL="$(date '+%Y-%m-%d %H:%M:%S')"
printf '%s\n' "${START_JOURNAL}" >"${OUT}/measured-window-start.txt"
WINDOW_STARTED=1

printf '\n===== start isolated H38 candidate with SPEC=mtp =====\n'
set +e
MODEL_PROFILE=orcarouter \
MODEL_DIR="${MODEL_DIR}" \
SERVED_NAME="${MODEL}" \
VLLM_IMAGE="${H38_IMAGE}" \
NAME="${EXPERIMENT_CONTAINER}" \
PORT=8888 \
PUBLISH_HOST=127.0.0.1 \
RESTART_POLICY=no \
MONITOR_ENABLED=0 \
MONITOR_PROTECT=0 \
CONFIG_OVERRIDE="${OUT}/config.vllm.json" \
MAXLEN=262144 \
EXECUTOR=mp \
BATCHED_TOKENS=8192 \
QSA_DET_TOPK=0 \
NSPEC=2 \
INDEX_SHARE=0 \
GPU_UTIL=0.80 \
KV_MEM="${KV_BYTES}" \
MAXSEQS=3 \
AUTOTUNE=0 \
QSA_EXACT_TOPK=1 \
PREFIX_CACHE=0 \
SPEC=mtp \
bash "${SERVE}" >"${OUT}/candidate-start.stdout" 2>"${OUT}/candidate-start.stderr"
START_RC=$?
set -e
[[ "${START_RC}" == 0 ]] ||
  fail "H38 production MTP candidate failed to start rc=${START_RC}"
EXPERIMENT_STARTED=1

EXPERIMENT_ID="$(docker inspect --format '{{.Id}}' "${EXPERIMENT_CONTAINER}")"
printf '%s\n' "${EXPERIMENT_ID}" >"${OUT}/candidate-container-id.txt"
docker inspect "${EXPERIMENT_CONTAINER}" >"${OUT}/candidate-inspect.json"
docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' \
  "${EXPERIMENT_CONTAINER}" >"${OUT}/candidate-env.txt"
docker inspect --format '{{json .Config.Cmd}}' \
  "${EXPERIMENT_CONTAINER}" >"${OUT}/candidate-cmd.json"

if ! python3 - \
  "${OUT}/candidate-inspect.json" \
  "${H38_IMAGE}" "${MODEL_DIR}" "${MODEL}" "${KV_BYTES}" <<'PY'
import json
import os
import sys

path, image, model_dir, served, kv = sys.argv[1:]
obj = json.load(open(path, encoding="utf-8"))[0]
if obj["Config"]["Image"] != image:
    raise SystemExit("image mismatch")

env = set(obj["Config"].get("Env") or [])
required = {
    "VLLM_PLE_MMAP=1",
    "VLLM_QSA_EXACT_TOPK=1",
    "VLLM_QSA_DET_TOPK=0",
    "QWEN38_MARLIN_CANONICAL_ORDER=1",
    "QWEN38_MARLIN_CANONICAL_SCOPE=decoder",
    "VLLM_CACHE_ROOT=/root/.cache/vllm/h38-marlin-canonical-decoder-managed-v1",
}
missing = sorted(required - env)
if missing:
    raise SystemExit(f"missing env: {missing}")
if "VLLM_PLE_CPU_OFFLOAD=1" in env:
    raise SystemExit("legacy CPU offload unexpectedly enabled")

cmd = obj["Config"].get("Cmd") or []
if "--speculative-config" not in cmd:
    raise SystemExit("production MTP candidate missing speculative config")

def value(flag: str) -> str:
    try:
        return cmd[cmd.index(flag) + 1]
    except (ValueError, IndexError):
        raise SystemExit(f"missing flag: {flag}")

spec = json.loads(value("--speculative-config"))
if spec != {"method": "mtp", "num_speculative_tokens": 2}:
    raise SystemExit(f"production MTP k=2 mismatch: {spec}")

if value("--distributed-executor-backend") != "mp":
    raise SystemExit("executor must be mp")
if value("--tensor-parallel-size") != "1":
    raise SystemExit("tensor parallel size mismatch")
if value("--served-model-name") != served:
    raise SystemExit("served name mismatch")
if value("--kv-cache-memory-bytes") != kv:
    raise SystemExit("KV mismatch")
if value("--max-model-len") != "262144":
    raise SystemExit("max model length mismatch")
if value("--max-num-seqs") != "3":
    raise SystemExit("max sequences mismatch")
if value("--gpu-memory-utilization") != "0.80":
    raise SystemExit("GPU utilization mismatch")
if value("--max-num-batched-tokens") != "8192":
    raise SystemExit("max batched tokens mismatch")
for required_flag in (
    "--no-enable-prefix-caching",
    "--no-enable-flashinfer-autotune",
    "--enable-chunked-prefill",
    "--no-async-scheduling",
):
    if required_flag not in cmd:
        raise SystemExit(f"missing runtime flag: {required_flag}")

mounts = {
    mount["Destination"]: os.path.realpath(mount["Source"])
    for mount in obj.get("Mounts", [])
}
if mounts.get("/model") != os.path.realpath(model_dir):
    raise SystemExit("model mount mismatch")
PY
then
  fail 'H38 production MTP candidate identity validation failed'
fi
IDENTITY_VALIDATED=1
printf '%s\n' "${IDENTITY_VALIDATED}" >"${OUT}/identity-validated.txt"

XDG_STATE_HOME="${OUT}/monitor-state" \
bash "${MONITOR}" \
  --container "${EXPERIMENT_CONTAINER}" \
  --min-available-gib 6 \
  --min-free-gib 2 \
  --free-gate-gib 10 \
  --min-swap-free-gib 8 \
  --swap-activity-gate-mib 256 \
  --consecutive 5 \
  --interval 2 \
  --heartbeat 60 \
  --protect >"${OUT}/memory-monitor.log" 2>&1 &
MONITOR_PID=$!

set +e
for attempt in $(seq 1 180); do
  if curl -fsS --max-time 3 http://127.0.0.1:8888/health >/dev/null 2>&1; then
    models="$(curl -fsS --max-time 15 http://127.0.0.1:8888/v1/models 2>/dev/null || true)"
    if python3 -c 'import json,sys; expected=sys.argv[1]; data=json.load(sys.stdin); raise SystemExit(0 if any(x.get("id")==expected for x in data.get("data", [])) else 1)' \
      "${MODEL}" <<<"${models}" 2>/dev/null
    then
      API_READY=1
      READY_RC=0
      break
    fi
  fi
  state="$(docker inspect --format '{{.State.Status}}' "${EXPERIMENT_CONTAINER}" 2>/dev/null || true)"
  if [[ "${state}" != running ]]; then
    READY_RC=1
    break
  fi
  if (( attempt % 6 == 0 )); then
    printf 'Waiting for H38 SPEC=mtp readiness: %d/1800 seconds\n' "$((attempt * 10))"
  fi
  sleep 10
done
if [[ "${API_READY}" != 1 && "${READY_RC}" == 125 ]]; then
  READY_RC=124
fi
set -e
printf '%s\n' "${READY_RC}" >"${OUT}/wait-ready.rc"

if [[ -n "${MONITOR_PID}" ]] && kill -0 "${MONITOR_PID}" >/dev/null 2>&1; then
  kill "${MONITOR_PID}" >/dev/null 2>&1 || true
  wait "${MONITOR_PID}" >/dev/null 2>&1 || true
fi
MONITOR_PID=""

capture_monitor_summary
finish_collector
OOM_KILLED="$(docker inspect --format '{{.State.OOMKilled}}' "${EXPERIMENT_CONTAINER}" 2>/dev/null || printf unknown)"
docker logs --timestamps "${EXPERIMENT_CONTAINER}" >"${OUT}/candidate-container.log" 2>&1 || true
capture_startup_phase
capture_kernel_window
RUN_COMPLETED=1
classify
stop_experiment
write_summary 0
write_upload_summary

printf '\n===== H38 allocator protection discriminator summary =====\n'
cat "${OUT}/summary.txt"
printf 'evidence=%s\n' "${OUT}"
printf 'upload_summary=%s\n' "${OUT}/upload-summary.txt"
printf 'Managed predecessor remains in its original stopped post-protection state.\n'

case "${RESULT}" in
  VALID_CLEAN)
    printf 'H38_ALLOCATOR_PROTECTION_DISCRIMINATOR=VALID_CLEAN\n'
    exit 0
    ;;
  PROTECTED_STOP)
    printf 'H38_ALLOCATOR_PROTECTION_DISCRIMINATOR=PROTECTED_STOP\n'
    exit 1
    ;;
  FUNCTIONAL_PASS_HOST_FAIL|FUNCTIONAL_NOT_REACHED_HOST_FAIL|DOCKER_OOM_KILLED)
    printf 'H38_ALLOCATOR_PROTECTION_DISCRIMINATOR=STRICT_RM_FAIL\n'
    exit 1
    ;;
  *)
    printf 'H38_ALLOCATOR_PROTECTION_DISCRIMINATOR=INVALID\n'
    exit 1
    ;;
esac
