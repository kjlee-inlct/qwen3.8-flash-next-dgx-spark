#!/usr/bin/env bash
# R22: preserve R21 preconditioning, then replace the legacy managed OrcaRouter
# startup with the existing vLLM v0.29 PLE-mmap candidate at a matched 16 GiB KV.
# This is a mechanism-discrimination experiment, not a production promotion.

set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"
STATE_FILE="${STATE_HOME}/install.env"
STATE_PARSER="${SCRIPT_ROOT}/scripts/lib/state_file.py"
CURRENT_LINK="${DATA_HOME}/current"
UNIT="qwen38-flash-next.service"
MANAGED_CONTAINER="qwen38-flash-next"
EXPERIMENT_CONTAINER="qwen38-orca-v029-r22"
IMAGE="${ORCA_R22_IMAGE:-vllm-orcarouter-v029:v1}"
EXPECTED_IMAGE_LABEL="v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla"
KV_BYTES="${ORCA_R22_KV_BYTES:-17179869184}"
MIN_PREDECESSOR_AGE_S="${ORCA_R22_MIN_PREDECESSOR_AGE_S:-2700}"
OUT="${ORCA_R22_OUT:-/tmp/orcarouter-managed-rmsys-r22-v029-mmap-01-20261004}"
STATE_OUT="${OUT}/allocator-state"
STOP_FILE="${OUT}/collector.stop"
COLLECTOR="${SCRIPT_ROOT}/scripts/benchmark/collect-linux-allocator-state.py"
MONITOR="${SCRIPT_ROOT}/scripts/runtime/monitor-runtime.sh"
WAIT_READY="${SCRIPT_ROOT}/scripts/wait-ready.sh"
RELEASE_MANAGER="${SCRIPT_ROOT}/scripts/release-manager.sh"
UPDATE_TRANSITION="${SCRIPT_ROOT}/scripts/update-transition.sh"
RUNTIME_TRANSITION="${SCRIPT_ROOT}/scripts/runtime-transition.sh"
PROFILE_TRANSITION="${SCRIPT_ROOT}/scripts/profile-switch-transition.sh"

RUN_USER="${SUDO_USER:-$(id -un)}"
RUN_GROUP="$(id -gn "${RUN_USER}")"
COLLECTOR_PID=""
MONITOR_PID=""
SUDO_KEEPALIVE_PID=""
COLLECTOR_RC=125
START_RC=125
READY_RC=125
SERVICE_STOPPED=0
EXPERIMENT_STARTED=0
MODEL_DIR=""
SERVED_NAME=""
MODEL_PROFILE=""
MODEL_REVISION=""
MODEL_REPO=""

fail() {
    printf 'ORCA_R22_ERROR: %s\n' "$*" >&2
    exit 2
}

cleanup() {
    local rc=$?
    trap - EXIT INT TERM
    set +e
    touch "${STOP_FILE}" 2>/dev/null || true
    if [[ -n "${COLLECTOR_PID}" ]] && kill -0 "${COLLECTOR_PID}" >/dev/null 2>&1; then
        wait "${COLLECTOR_PID}" >/dev/null 2>&1 || true
    fi
    if [[ -n "${MONITOR_PID}" ]] && kill -0 "${MONITOR_PID}" >/dev/null 2>&1; then
        kill "${MONITOR_PID}" >/dev/null 2>&1 || true
        wait "${MONITOR_PID}" >/dev/null 2>&1 || true
    fi
    if [[ -n "${SUDO_KEEPALIVE_PID}" ]] && kill -0 "${SUDO_KEEPALIVE_PID}" >/dev/null 2>&1; then
        kill "${SUDO_KEEPALIVE_PID}" >/dev/null 2>&1 || true
        wait "${SUDO_KEEPALIVE_PID}" >/dev/null 2>&1 || true
    fi
    if [[ "${EXPERIMENT_STARTED}" == 1 ]] && [[ "$(docker inspect --format '{{.State.Running}}' "${EXPERIMENT_CONTAINER}" 2>/dev/null || true)" == true ]]; then
        docker stop --timeout 30 "${EXPERIMENT_CONTAINER}" >/dev/null 2>&1 || true
    fi
    if [[ "${SERVICE_STOPPED}" == 1 ]] && ! systemctl is-active --quiet "${UNIT}"; then
        sudo -n systemctl start "${UNIT}" >/dev/null 2>&1 || true
    fi
    exit "${rc}"
}
trap cleanup EXIT INT TERM

snapshot_proc() {
    local target="$1"
    mkdir -p -- "${target}"
    sudo -n cat /proc/buddyinfo >"${target}/proc-buddyinfo.txt"
    sudo -n cat /proc/pagetypeinfo >"${target}/proc-pagetypeinfo.txt"
    sudo -n cat /proc/zoneinfo >"${target}/proc-zoneinfo.txt"
    sudo -n cat /proc/meminfo >"${target}/proc-meminfo.txt"
    sudo -n cat /proc/vmstat >"${target}/proc-vmstat.txt"
    sudo -n cat /proc/pressure/memory >"${target}/proc-pressure-memory.txt"
}

load_install_state() {
    local parsed key value
    parsed="$(mktemp)"
    python3 "${STATE_PARSER}" install-maintenance "${STATE_FILE}" >"${parsed}"
    while IFS= read -r -d '' key && IFS= read -r -d '' value; do
        case "${key}" in
            MODEL_PROFILE) MODEL_PROFILE="${value}" ;;
            MODEL_DIR) MODEL_DIR="${value}" ;;
            SERVED_NAME) SERVED_NAME="${value}" ;;
            MODEL_REPO) MODEL_REPO="${value}" ;;
            MODEL_REVISION) MODEL_REVISION="${value}" ;;
        esac
    done <"${parsed}"
    rm -f -- "${parsed}"
}

for command in sudo python3 bash systemctl docker curl journalctl date grep awk find wc cat tee seq sleep mkdir sync mktemp; do
    command -v "${command}" >/dev/null 2>&1 || fail "required command not found: ${command}"
done
sudo -n true >/dev/null 2>&1 || fail "sudo timestamp unavailable; run sudo -v first"
(
    while sleep 60; do
        sudo -n -v >/dev/null 2>&1 || exit 0
    done
) &
SUDO_KEEPALIVE_PID=$!

[[ -r "${STATE_FILE}" ]] || fail "installation state missing: ${STATE_FILE}"
[[ -r "${STATE_PARSER}" ]] || fail "state parser missing: ${STATE_PARSER}"
[[ -r "${COLLECTOR}" ]] || fail "allocator-state collector missing: ${COLLECTOR}"
[[ -x "${MONITOR}" ]] || fail "runtime monitor missing: ${MONITOR}"
[[ -x "${WAIT_READY}" ]] || fail "readiness waiter missing: ${WAIT_READY}"
[[ -L "${CURRENT_LINK}" ]] || fail "immutable current release link missing: ${CURRENT_LINK}"
[[ ! -e "${OUT}" ]] || fail "evidence already exists: ${OUT}"

grep -qx 'UPDATE_STATE=idle' < <(bash "${UPDATE_TRANSITION}" status) || fail "update transition is not idle"
grep -qx 'TRANSACTION_STATE=idle' < <(bash "${RUNTIME_TRANSITION}" status) || fail "runtime transition is not idle"
grep -qx 'PROFILE_SWITCH_STATE=idle' < <(bash "${PROFILE_TRANSITION}" status) || fail "profile-switch transition is not idle"
systemctl is-active --quiet "${UNIT}" || fail "managed service is not active"
curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null || fail "managed API is not healthy"

load_install_state
[[ "${MODEL_PROFILE}" == orcarouter ]] || fail "installed managed profile is not OrcaRouter"
[[ -n "${MODEL_DIR}" && -d "${MODEL_DIR}" ]] || fail "installed OrcaRouter model directory is unavailable"
[[ -f "${MODEL_DIR}/model.safetensors.index.json" ]] || fail "checkpoint index missing from installed OrcaRouter model"
[[ -n "${SERVED_NAME}" ]] || fail "served model identity missing from installation state"
[[ "${KV_BYTES}" == 17179869184 ]] || fail "R22 must use the managed OrcaRouter 16 GiB KV value"

CURRENT_RELEASE="$(bash "${RELEASE_MANAGER}" status | awk -F= '$1=="CURRENT_RELEASE" {print $2}')"
[[ -n "${CURRENT_RELEASE}" && "${CURRENT_RELEASE}" != none ]] || fail "no immutable current release"
SERVE="${CURRENT_LINK}/scripts/serve.sh"
[[ -r "${SERVE}" ]] || fail "serve helper missing from current release"
ORCA_BLOCK="$(awk '/^  orcarouter\)/,/^  nvidia\)/' "${SERVE}")"
grep -Fq 'DEFAULT_KV_MEM=17179869184' <<<"${ORCA_BLOCK}" || fail "managed immutable release no longer defaults OrcaRouter to 16 GiB"
[[ ! -e /run/systemd/system/qwen38-flash-next.service.d/kv16-ab.conf ]] || fail "temporary KV override is still present"

IMAGE_LABEL="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.stability-candidate" }}' 2>/dev/null || true)"
[[ "${IMAGE_LABEL}" == "${EXPECTED_IMAGE_LABEL}" ]] || fail "required v0.29 PLE-mmap image is missing or stale: ${IMAGE}"
if docker inspect "${EXPERIMENT_CONTAINER}" >/dev/null 2>&1; then
    fail "experiment container already exists; preserve/remove it explicitly before R22: ${EXPERIMENT_CONTAINER}"
fi

PRE_CONTAINER_ID="$(docker inspect --format '{{.Id}}' "${MANAGED_CONTAINER}" 2>/dev/null || true)"
PRE_CONTAINER_STARTED="$(docker inspect --format '{{.State.StartedAt}}' "${MANAGED_CONTAINER}" 2>/dev/null || true)"
[[ -n "${PRE_CONTAINER_ID}" && -n "${PRE_CONTAINER_STARTED}" ]] || fail "managed predecessor container is unavailable"
PREDECESSOR_AGE_S="$(python3 - "${PRE_CONTAINER_STARTED}" <<'PY'
import datetime as dt
import sys
started = dt.datetime.fromisoformat(sys.argv[1].replace('Z', '+00:00'))
now = dt.datetime.now(dt.timezone.utc)
print(f"{(now - started).total_seconds():.3f}")
PY
)"
python3 - "${PREDECESSOR_AGE_S}" "${MIN_PREDECESSOR_AGE_S}" <<'PY' || fail "predecessor runtime is younger than required R22 minimum"
import sys
raise SystemExit(0 if float(sys.argv[1]) >= float(sys.argv[2]) else 1)
PY

mkdir -p -- "${OUT}"
printf '%s\n' "${CURRENT_RELEASE}" >"${OUT}/release-before.txt"
printf '%s\n' "${PRE_CONTAINER_ID}" >"${OUT}/container-id-before.txt"
printf '%s\n' "${PRE_CONTAINER_STARTED}" >"${OUT}/container-started-before.txt"
printf '%s\n' "${PREDECESSOR_AGE_S}" >"${OUT}/predecessor-age-s.txt"
printf '%s\n' "${MIN_PREDECESSOR_AGE_S}" >"${OUT}/minimum-predecessor-age-s.txt"
printf '%s\n' "${IMAGE}" >"${OUT}/candidate-image.txt"
printf '%s\n' "${IMAGE_LABEL}" >"${OUT}/candidate-image-label.txt"
printf '%s\n' "${MODEL_DIR}" >"${OUT}/model-dir.txt"
printf '%s\n' "${MODEL_REPO}" >"${OUT}/model-repo.txt"
printf '%s\n' "${MODEL_REVISION}" >"${OUT}/model-revision.txt"
printf '%s\n' "${SERVED_NAME}" >"${OUT}/served-name.txt"
printf '%s\n' "${KV_BYTES}" >"${OUT}/kv-bytes.txt"
START_ISO="$(date --iso-8601=seconds)"
START_EPOCH="$(date +%s.%N)"
printf '%s\n' "${START_ISO}" >"${OUT}/start-iso.txt"
printf '%s\n' "${START_EPOCH}" >"${OUT}/start-epoch.txt"

sudo -n /usr/bin/python3 "${COLLECTOR}" \
    --output "${STATE_OUT}" \
    --stop-file "${STOP_FILE}" \
    --fast-interval 1 \
    --slow-interval 5 \
    >"${OUT}/collector.log" 2>&1 &
COLLECTOR_PID=$!
printf '%s\n' "${COLLECTOR_PID}" >"${OUT}/collector.pid"
sleep 2
kill -0 "${COLLECTOR_PID}" >/dev/null 2>&1 || fail "allocator-state collector exited before teardown"

printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/stop-started-iso.txt"
sudo -n systemctl stop "${UNIT}"
SERVICE_STOPPED=1
for _ in $(seq 1 120); do
    systemctl is-active --quiet "${UNIT}" || break
    sleep 1
done
systemctl is-active --quiet "${UNIT}" && fail "managed service did not stop"
if [[ "$(docker inspect --format '{{.State.Running}}' "${MANAGED_CONTAINER}" 2>/dev/null || printf false)" == true ]]; then
    fail "predecessor container is still running after service stop"
fi
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/stop-complete-iso.txt"

snapshot_proc "${OUT}/poststop-before-reclaim"
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/sync-started-iso.txt"
sudo -n sync
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/sync-complete-iso.txt"
snapshot_proc "${OUT}/poststop-after-sync"

printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/drop-caches-started-iso.txt"
sudo -n /bin/sh -c 'printf 1 > /proc/sys/vm/drop_caches'
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/drop-caches-complete-iso.txt"
snapshot_proc "${OUT}/poststop-after-drop-caches"

printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/compact-started-iso.txt"
sudo -n /bin/sh -c 'printf 1 > /proc/sys/vm/compact_memory'
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/compact-complete-iso.txt"
snapshot_proc "${OUT}/poststop-after-compact"

mkdir -p "${HOME}/.cache/vllm-qwen38-v029" "${HOME}/.cache/flashinfer-v029"
SPLIT='["vllm::unified_attention_with_output","vllm::unified_mla_attention_with_output","vllm::mamba_mixer2","vllm::mamba_mixer","vllm::short_conv","vllm::qwen4_exp_compute_ple_ngram_ids","vllm::qwen4_exp_ple_short_conv","vllm::qwen4_exp_qsa_with_output","vllm::linear_attention","vllm::qwen_gdn_attention_core","vllm::qwen_gdn_attention_core_fused_norm_packed","vllm::sparse_attn_indexer","vllm::ple_mmap_lookup_ids"]'

printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/candidate-started-iso.txt"
set +e
docker run -d \
    --name "${EXPERIMENT_CONTAINER}" \
    --init \
    --user root \
    --restart no \
    --gpus all \
    --ipc host \
    --shm-size=32g \
    --ulimit memlock=-1:-1 \
    --ulimit stack=67108864 \
    -p 127.0.0.1:8888:8000 \
    -e VLLM_TARGET_DEVICE=cuda \
    -e CUTE_DSL_ARCH=sm_121a \
    -e VLLM_PLE_MMAP=1 \
    -e VLLM_PLE_MMAP_DIR=/model \
    -e VLLM_PLE_MMAP_WORKERS=32 \
    -e VLLM_PLE_MMAP_PREWARM=0 \
    -e VLLM_PLE_MMAP_MADVISE=random \
    -e VLLM_PLE_MMAP_FAST_ROWS=0 \
    -e VLLM_QSA_EXACT_TOPK=1 \
    -e QWEN38_VLLM_BASE=v0.29 \
    -e QWEN38_GB10_FLA_FIX=1 \
    -e QWEN38_PLE_MMAP=1 \
    -e FLASHINFER_DISABLE_VERSION_CHECK=1 \
    -v "${MODEL_DIR}:/model:ro" \
    -v "${HOME}/.cache/vllm-qwen38-v029:/root/.cache/vllm" \
    -v "${HOME}/.cache/flashinfer-v029:/root/.cache/flashinfer" \
    "${IMAGE}" \
    /model \
    --served-model-name "${SERVED_NAME}" \
    --host 0.0.0.0 \
    --port 8000 \
    --load-format safetensors \
    --max-model-len 262144 \
    --max-num-seqs 3 \
    --gpu-memory-utilization 0.80 \
    --kv-cache-memory-bytes "${KV_BYTES}" \
    --kv-cache-dtype auto \
    --no-enable-prefix-caching \
    --enable-chunked-prefill \
    --max-num-batched-tokens 8192 \
    -cc.cudagraph_mode=PIECEWISE \
    "-cc.splitting_ops=${SPLIT}" \
    --no-enable-flashinfer-autotune \
    --enable-auto-tool-choice \
    --tool-call-parser qwen3_coder \
    --reasoning-parser qwen3 \
    --speculative-config '{"method":"mtp","num_speculative_tokens":2}' \
    >"${OUT}/docker-run.stdout" 2>"${OUT}/docker-run.stderr"
START_RC=$?
set -e
printf '%s\n' "${START_RC}" >"${OUT}/candidate-start.rc"
[[ "${START_RC}" == 0 ]] || fail "v0.29 mmap candidate failed to start"
EXPERIMENT_STARTED=1

CANDIDATE_ID="$(docker inspect --format '{{.Id}}' "${EXPERIMENT_CONTAINER}")"
CANDIDATE_STARTED="$(docker inspect --format '{{.State.StartedAt}}' "${EXPERIMENT_CONTAINER}")"
printf '%s\n' "${CANDIDATE_ID}" >"${OUT}/candidate-container-id.txt"
printf '%s\n' "${CANDIDATE_STARTED}" >"${OUT}/candidate-container-started.txt"
docker inspect "${EXPERIMENT_CONTAINER}" >"${OUT}/candidate-docker-inspect.json"
docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "${EXPERIMENT_CONTAINER}" >"${OUT}/candidate-env.txt"
if grep -qx 'VLLM_PLE_CPU_OFFLOAD=1' "${OUT}/candidate-env.txt"; then
    fail "R22 candidate unexpectedly enables legacy PLE CPU offload"
fi
grep -qx 'VLLM_PLE_MMAP=1' "${OUT}/candidate-env.txt" || fail "R22 candidate is missing PLE mmap enable"

XDG_STATE_HOME="${OUT}/monitor-state" bash "${MONITOR}" \
    --container "${EXPERIMENT_CONTAINER}" \
    --min-available-gib 6 \
    --min-free-gib 2 \
    --free-gate-gib 10 \
    --min-swap-free-gib 8 \
    --consecutive 5 \
    --interval 2 \
    --heartbeat 60 \
    --protect \
    >"${OUT}/memory-monitor.log" 2>&1 &
MONITOR_PID=$!

set +e
"${WAIT_READY}" \
    --container "${EXPERIMENT_CONTAINER}" \
    --model "${SERVED_NAME}" \
    --timeout 1800 \
    --interval 10 \
    >"${OUT}/wait-ready.log" 2>&1
READY_RC=$?
set -e
printf '%s\n' "${READY_RC}" >"${OUT}/wait-ready.rc"

END_ISO="$(date --iso-8601=seconds)"
END_EPOCH="$(date +%s.%N)"
printf '%s\n' "${END_ISO}" >"${OUT}/end-iso.txt"
printf '%s\n' "${END_EPOCH}" >"${OUT}/end-epoch.txt"

touch "${STOP_FILE}"
set +e
wait "${COLLECTOR_PID}"
COLLECTOR_RC=$?
set -e
COLLECTOR_PID=""
printf '%s\n' "${COLLECTOR_RC}" >"${OUT}/collector.rc"

if [[ -n "${MONITOR_PID}" ]] && kill -0 "${MONITOR_PID}" >/dev/null 2>&1; then
    kill "${MONITOR_PID}" >/dev/null 2>&1 || true
    wait "${MONITOR_PID}" >/dev/null 2>&1 || true
fi
MONITOR_PID=""
PROTECTED_STOP=0
grep -q 'PROTECT stopping' "${OUT}/memory-monitor.log" 2>/dev/null && PROTECTED_STOP=1
printf '%s\n' "${PROTECTED_STOP}" >"${OUT}/protected-stop.txt"

docker logs --timestamps "${EXPERIMENT_CONTAINER}" >"${OUT}/candidate-container.log" 2>&1 || true

START_SEC="${START_EPOCH%%.*}"
END_SEC="$(( ${END_EPOCH%%.*} + 2 ))"
START_JOURNAL="$(date -d "@${START_SEC}" '+%Y-%m-%d %H:%M:%S')"
END_JOURNAL="$(date -d "@${END_SEC}" '+%Y-%m-%d %H:%M:%S')"
sudo -n journalctl -k --since "${START_JOURNAL}" --until "${END_JOURNAL}" -o short-iso-precise --no-pager >"${OUT}/kernel-window.txt"
ERROR_RE='NV_ERR_NO_MEMORY|_memdescAllocInternal|NVRM:.*Xid|Xid \(PCI|GPU has fallen off the bus|oom-kill:|Out of memory:|Killed process '
grep -Ei "${ERROR_RE}" "${OUT}/kernel-window.txt" >"${OUT}/kernel-errors.txt" || true
RM_OOM_COUNT="$(grep -Ec 'NV_ERR_NO_MEMORY|_memdescAllocInternal' "${OUT}/kernel-errors.txt" 2>/dev/null || true)"
EVENT_SNAPSHOT_COUNT="$(find "${STATE_OUT}/events" -mindepth 1 -maxdepth 1 -type d -name 'rm-oom-*' 2>/dev/null | wc -l)"

API_READY=0
if [[ "${READY_RC}" == 0 ]] && [[ "$(docker inspect --format '{{.State.Running}}' "${EXPERIMENT_CONTAINER}" 2>/dev/null || true)" == true ]] && curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null 2>&1; then
    API_READY=1
fi
printf '%s\n' "${API_READY}" >"${OUT}/api-ready.txt"

RUN_VALID=1
if [[ "${START_RC}" != 0 || "${COLLECTOR_RC}" != 0 || "${READY_RC}" != 0 || "${API_READY}" != 1 || "${PROTECTED_STOP}" != 0 ]]; then
    RUN_VALID=0
fi
printf '%s\n' "${RUN_VALID}" >"${OUT}/run-valid.txt"

if [[ "$(docker inspect --format '{{.State.Running}}' "${EXPERIMENT_CONTAINER}" 2>/dev/null || true)" == true ]]; then
    docker stop --timeout 30 "${EXPERIMENT_CONTAINER}" >/dev/null
fi
EXPERIMENT_STARTED=0
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/candidate-stopped-iso.txt"

sudo -n systemctl start "${UNIT}"
SERVICE_STOPPED=0
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/managed-restore-started-iso.txt"

sudo -n chown -R "${RUN_USER}:${RUN_GROUP}" "${OUT}" 2>/dev/null || true

{
    printf 'run_valid=%s\n' "${RUN_VALID}"
    printf 'candidate_start_rc=%s\n' "${START_RC}"
    printf 'collector_rc=%s\n' "${COLLECTOR_RC}"
    printf 'wait_ready_rc=%s\n' "${READY_RC}"
    printf 'api_ready=%s\n' "${API_READY}"
    printf 'protected_stop=%s\n' "${PROTECTED_STOP}"
    printf 'predecessor_age_s=%s\n' "${PREDECESSOR_AGE_S}"
    printf 'minimum_predecessor_age_s=%s\n' "${MIN_PREDECESSOR_AGE_S}"
    printf 'ple_mode=mmap\n'
    printf 'kv_bytes=%s\n' "${KV_BYTES}"
    printf 'rm_oom_count=%s\n' "${RM_OOM_COUNT}"
    printf 'event_snapshot_count=%s\n' "${EVENT_SNAPSHOT_COUNT}"
} >"${OUT}/r22-summary.txt"

printf '\n===== R22 summary =====\n'
cat "${OUT}/r22-summary.txt"
printf '%s\n' '--- kernel errors ---'
cat "${OUT}/kernel-errors.txt" || true
printf 'evidence=%s\n' "${OUT}"

if [[ "${RUN_VALID}" != 1 ]]; then
    printf 'ORCA_R22_RESULT=INVALID\n'
    exit 1
fi
if [[ "${RM_OOM_COUNT}" == 0 ]]; then
    printf 'ORCA_R22_RESULT=VALID_CLEAN\n'
else
    printf 'ORCA_R22_RESULT=VALID_RM_OOM\n'
fi
