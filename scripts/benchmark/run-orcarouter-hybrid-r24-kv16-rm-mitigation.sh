#!/usr/bin/env bash
# R24: compare H6 ModelOpt W4A16 Hybrid against the canonical R22 16 GiB
# v0.29/PLE-mmap control. Ownership is already closed by R23; trace RM only.

set -Eeuo pipefail

MODE="${1:-run}"
[[ "${MODE}" == run || "${MODE}" == --preflight ]] || {
    echo "usage: $0 [--preflight]" >&2
    exit 2
}

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"
STATE_FILE="${STATE_HOME}/install.env"
STATE_PARSER="${SCRIPT_ROOT}/scripts/state_file.py"
CURRENT_LINK="${DATA_HOME}/current"
UNIT="qwen38-flash-next.service"
MANAGED_CONTAINER="qwen38-flash-next"
EXPERIMENT_CONTAINER="qwen38-hybrid-r24-kv16"
SERVE="${SCRIPT_ROOT}/scripts/serve.sh"
IMAGE="${ORCA_R24_IMAGE:-vllm-orcarouter-v029:v1}"
EXPECTED_IMAGE_LABEL="v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla"
KV_BYTES=17179869184
MIN_PREDECESSOR_AGE_S="${ORCA_R24_MIN_PREDECESSOR_AGE_S:-2700}"
TRACE_ARM_DELAY_S=20
TRACE_DURATION_S=50
OUT="${ORCA_R24_OUT:-/tmp/orcarouter-hybrid-r24-kv16-rm-mitigation-01-20261004}"
STATE_OUT="${OUT}/allocator-state"
STOP_FILE="${OUT}/collector.stop"
COLLECTOR="${SCRIPT_ROOT}/scripts/benchmark/collect-linux-allocator-state.py"
ANALYZER="${SCRIPT_ROOT}/scripts/benchmark/analyze-orcarouter-hybrid-r24-rm-mitigation.py"
MONITOR="${SCRIPT_ROOT}/scripts/monitor-runtime.sh"
WAIT_READY="${SCRIPT_ROOT}/scripts/wait-ready.sh"
RELEASE_MANAGER="${SCRIPT_ROOT}/scripts/release-manager.sh"
UPDATE_TRANSITION="${SCRIPT_ROOT}/scripts/update-transition.sh"
RUNTIME_TRANSITION="${SCRIPT_ROOT}/scripts/runtime-transition.sh"
PROFILE_TRANSITION="${SCRIPT_ROOT}/scripts/profile-switch-transition.sh"
GROUP="r24_rm"

RUN_USER="${SUDO_USER:-$(id -un)}"
RUN_GROUP="$(id -gn "${RUN_USER}")"
RUN_HOME="$(getent passwd "${RUN_USER}" | cut -d: -f6)"
FIXED_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

COLLECTOR_PID=""
MONITOR_PID=""
SUDO_KEEPALIVE_PID=""
SERVICE_STOPPED=0
EXPERIMENT_STARTED=0
COLLECTOR_RC=125
START_RC=125
READY_RC=125
TRACE_RC=125
REPORT_RC=125
ANALYZER_RC=125

MODEL_PROFILE=""
BASE_MODEL_DIR=""
BASE_SERVED_NAME=""
MODEL_ROOT=""
H3_MODEL_DIR=""
H4_MODEL_DIR=""
H5_MODEL_DIR=""
H6_MODEL_DIR=""
H6_SERVED_NAME="orcarouter-hybrid/Qwen3.8-Flash-Next-Uncensored-NVFP4"

TRACEFS="/sys/kernel/tracing"
if [[ ! -e "${TRACEFS}/kprobe_events" ]]; then
    TRACEFS="/sys/kernel/debug/tracing"
fi
KPROBE_EVENTS="${TRACEFS}/kprobe_events"
PROBE_EVENTS=(
    nv_alloc_pages_entry
    nv_alloc_pages_ret
    nv_alloc_system_pages_entry
    nv_alloc_system_pages_ret
)

fail() {
    printf 'ORCA_R24_ERROR: %s\n' "$*" >&2
    exit 2
}

mono_ns() {
    python3 - <<'PY'
import time
print(time.monotonic_ns())
PY
}

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
            MODEL_DIR) BASE_MODEL_DIR="${value}" ;;
            SERVED_NAME) BASE_SERVED_NAME="${value}" ;;
        esac
    done <"${parsed}"
    rm -f -- "${parsed}"
}

write_kprobe_commands() {
    local source_file="$1"
    sudo -n python3 - "${KPROBE_EVENTS}" "${source_file}" <<'PY'
import os
import pathlib
import sys
path = sys.argv[1]
for raw in pathlib.Path(sys.argv[2]).read_bytes().splitlines():
    command = raw.strip()
    if not command:
        continue
    fd = os.open(path, os.O_WRONLY)
    try:
        written = os.write(fd, command + b"\n")
    finally:
        os.close(fd)
    if written != len(command) + 1:
        raise SystemExit(f"short kprobe control write: {written}/{len(command)+1}")
PY
}

disable_probe_events() {
    sudo -n python3 - "${TRACEFS}" "${GROUP}" <<'PY'
import os
import pathlib
import sys
group_dir = pathlib.Path(sys.argv[1]) / "events" / sys.argv[2]
targets = [group_dir / "enable"]
if group_dir.is_dir():
    targets.extend(sorted(group_dir.glob("*/enable")))
for target in targets:
    if not target.exists():
        continue
    try:
        fd = os.open(target, os.O_WRONLY)
        try:
            os.write(fd, b"0\n")
        finally:
            os.close(fd)
    except OSError:
        pass
PY
}

cleanup_probes() {
    local tmp event
    [[ -e "${KPROBE_EVENTS}" ]] || return 0
    tmp="$(mktemp /tmp/r24-rm-kprobe-cleanup.XXXXXX)"
    disable_probe_events || true
    for event in "${PROBE_EVENTS[@]}"; do
        printf '%s\n' "-:${GROUP}/${event}" >>"${tmp}"
    done
    write_kprobe_commands "${tmp}" >/dev/null 2>&1 || true
    rm -f -- "${tmp}"
}

create_probes() {
    local definitions="${OUT}/probe-definitions.txt"
    cleanup_probes
    sudo -n cat "${KPROBE_EVENTS}" | grep -Fq "${GROUP}/" && \
        fail "stale ${GROUP} probes remain after cleanup"
    cat >"${definitions}" <<'EOF'
p:r24_rm/nv_alloc_pages_entry nv_alloc_pages page_count=$arg2:u32 page_size=$arg3:u64 contiguous=$arg4:u8 cache_type=$arg5:u32 zeroed=$arg6:u8 unencrypted=$arg7:u8 node_id=$arg8:s32
r:r24_rm/nv_alloc_pages_ret nv_alloc_pages ret=$retval:u32
p:r24_rm/nv_alloc_system_pages_entry nv_alloc_system_pages at=$arg2:u64
r:r24_rm/nv_alloc_system_pages_ret nv_alloc_system_pages ret=$retval:u32
EOF
    write_kprobe_commands "${definitions}" || fail "failed to install R24 RM probes"
    for event in "${PROBE_EVENTS[@]}"; do
        sudo -n cat "${TRACEFS}/events/${GROUP}/${event}/format" >/dev/null 2>&1 || \
            fail "probe event not materialized: ${GROUP}:${event}"
    done
    local format="${TRACEFS}/events/${GROUP}/nv_alloc_pages_entry/format"
    for field in page_count page_size contiguous cache_type zeroed unencrypted node_id; do
        sudo -n grep -Eq "field:.*[[:space:]]${field};" "${format}" || \
            fail "missing nv_alloc_pages field: ${field}"
    done
}

validate_h6_manifest() {
    local manifest="${H6_MODEL_DIR}/.qwen38-hybrid-manifest.json"
    [[ -r "${manifest}" ]] || fail "H6 manifest missing: ${manifest}"
    python3 - "${manifest}" <<'PY' || exit 1
import json
import sys
with open(sys.argv[1], encoding="utf-8") as handle:
    data = json.load(handle)
expected = {
    "status": "complete",
    "variant": "h6-modelopt-w4a16",
    "parent_variant": "h5-neutral-input-scale",
    "expert_value_source": "orcarouter-h4-all",
    "input_scale_source": "h5-neutral-1.0",
    "quant_algo_before": "NVFP4",
    "quant_algo_after": "W4A16_NVFP4",
    "safetensor_bytes_changed": 0,
    "mtp_tensors_changed": 0,
}
bad = {key: (data.get(key), value) for key, value in expected.items() if data.get(key) != value}
if bad:
    print(f"H6 manifest mismatch: {bad}", file=sys.stderr)
    raise SystemExit(1)
PY
}

predecessor_age() {
    local started="$1"
    python3 - "${started}" <<'PY'
import datetime as dt
import sys
started = dt.datetime.fromisoformat(sys.argv[1].replace("Z", "+00:00"))
now = dt.datetime.now(dt.timezone.utc)
print(f"{(now - started).total_seconds():.3f}")
PY
}

validate_candidate_identity() {
    docker inspect "${EXPERIMENT_CONTAINER}" >"${OUT}/candidate-docker-inspect.json"
    docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' \
        "${EXPERIMENT_CONTAINER}" >"${OUT}/candidate-env.txt"
    python3 - \
        "${OUT}/candidate-docker-inspect.json" \
        "${IMAGE}" "${H6_MODEL_DIR}" "${BASE_MODEL_DIR}" \
        "${H3_MODEL_DIR}" "${H4_MODEL_DIR}" "${H5_MODEL_DIR}" \
        "${H6_SERVED_NAME}" "${KV_BYTES}" <<'PY'
import json
import os
import sys
(
    inspect_path,
    expected_image,
    h6,
    base,
    h3,
    h4,
    h5,
    served,
    kv,
) = sys.argv[1:]
obj = json.load(open(inspect_path, encoding="utf-8"))[0]
if obj["Config"]["Image"] != expected_image:
    raise SystemExit("candidate image mismatch")
env = set(obj["Config"].get("Env") or [])
for required in ("VLLM_PLE_MMAP=1", "VLLM_QSA_EXACT_TOPK=1"):
    if required not in env:
        raise SystemExit(f"missing env {required}")
if "VLLM_PLE_CPU_OFFLOAD=1" in env:
    raise SystemExit("legacy CPU offload unexpectedly enabled")
cmd = obj["Config"].get("Cmd") or []
def value(flag):
    try:
        return cmd[cmd.index(flag) + 1]
    except (ValueError, IndexError):
        raise SystemExit(f"missing command flag {flag}")
if value("--served-model-name") != served:
    raise SystemExit("served model mismatch")
if value("--kv-cache-memory-bytes") != kv:
    raise SystemExit("KV mismatch")
if value("--max-model-len") != "262144" or value("--max-num-seqs") != "3":
    raise SystemExit("runtime shape mismatch")
mounts = {mount["Destination"]: os.path.realpath(mount["Source"]) for mount in obj.get("Mounts", [])}
expected = {
    "/model": os.path.realpath(h6),
    "/base-model": os.path.realpath(base),
    "/h3-model": os.path.realpath(h3),
    "/h4-all": os.path.realpath(h4),
    "/h5-parent": os.path.realpath(h5),
}
for dest, source in expected.items():
    if mounts.get(dest) != source:
        raise SystemExit(f"mount mismatch {dest}: {mounts.get(dest)!r} != {source!r}")
PY
}

cleanup() {
    local rc=$?
    trap - EXIT INT TERM
    set +e
    cleanup_probes
    touch "${STOP_FILE}" 2>/dev/null || true
    if [[ -n "${COLLECTOR_PID}" ]] && kill -0 "${COLLECTOR_PID}" >/dev/null 2>&1; then
        wait "${COLLECTOR_PID}" >/dev/null 2>&1 || true
    fi
    if [[ -n "${MONITOR_PID}" ]] && kill -0 "${MONITOR_PID}" >/dev/null 2>&1; then
        kill "${MONITOR_PID}" >/dev/null 2>&1 || true
        wait "${MONITOR_PID}" >/dev/null 2>&1 || true
    fi
    if [[ "${EXPERIMENT_STARTED}" == 1 ]] && \
       [[ "$(docker inspect --format '{{.State.Running}}' "${EXPERIMENT_CONTAINER}" 2>/dev/null || true)" == true ]]; then
        docker stop --timeout 30 "${EXPERIMENT_CONTAINER}" >/dev/null 2>&1 || true
    fi
    if [[ "${SERVICE_STOPPED}" == 1 ]] && ! systemctl is-active --quiet "${UNIT}"; then
        sudo -n systemctl start "${UNIT}" >/dev/null 2>&1 || true
    fi
    if [[ -n "${SUDO_KEEPALIVE_PID}" ]] && kill -0 "${SUDO_KEEPALIVE_PID}" >/dev/null 2>&1; then
        kill "${SUDO_KEEPALIVE_PID}" >/dev/null 2>&1 || true
        wait "${SUDO_KEEPALIVE_PID}" >/dev/null 2>&1 || true
    fi
    exit "${rc}"
}
trap cleanup EXIT INT TERM

for command in sudo python3 bash systemctl docker curl journalctl date grep awk find wc cat tee seq sleep mkdir sync mktemp getconf trace-cmd git; do
    command -v "${command}" >/dev/null 2>&1 || fail "required command not found: ${command}"
done
sudo -n true >/dev/null 2>&1 || fail "sudo timestamp unavailable; run sudo -v first"

[[ -r "${STATE_FILE}" ]] || fail "installation state missing: ${STATE_FILE}"
[[ -r "${STATE_PARSER}" ]] || fail "state parser missing: ${STATE_PARSER}"
[[ -r "${COLLECTOR}" ]] || fail "allocator collector missing: ${COLLECTOR}"
[[ -r "${ANALYZER}" ]] || fail "R24 analyzer missing: ${ANALYZER}"
[[ -x "${MONITOR}" ]] || fail "runtime monitor missing: ${MONITOR}"
[[ -x "${WAIT_READY}" ]] || fail "readiness waiter missing: ${WAIT_READY}"
[[ -r "${SERVE}" ]] || fail "serve helper missing: ${SERVE}"
[[ -L "${CURRENT_LINK}" ]] || fail "immutable current release link missing: ${CURRENT_LINK}"
[[ -e "${KPROBE_EVENTS}" ]] || fail "kprobe_events unavailable under ${TRACEFS}"

grep -qx 'UPDATE_STATE=idle' < <(bash "${UPDATE_TRANSITION}" status) || fail "update transition is not idle"
grep -qx 'TRANSACTION_STATE=idle' < <(bash "${RUNTIME_TRANSITION}" status) || fail "runtime transition is not idle"
grep -qx 'PROFILE_SWITCH_STATE=idle' < <(bash "${PROFILE_TRANSITION}" status) || fail "profile-switch transition is not idle"
systemctl is-active --quiet "${UNIT}" || fail "managed service is not active"
curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null || fail "managed API is not healthy"

load_install_state
[[ "${MODEL_PROFILE}" == orcarouter ]] || fail "installed managed profile is not OrcaRouter"
[[ -n "${BASE_MODEL_DIR}" && -d "${BASE_MODEL_DIR}" ]] || fail "managed OrcaRouter checkpoint unavailable"
[[ -n "${BASE_SERVED_NAME}" ]] || fail "managed served identity missing"
MODEL_ROOT="$(dirname -- "${BASE_MODEL_DIR}")"
H3_MODEL_DIR="${ORCA_R24_H3_MODEL_DIR:-${MODEL_ROOT}/qwen3.8-hybrid-quant-layout}"
H4_MODEL_DIR="${ORCA_R24_H4_MODEL_DIR:-${MODEL_ROOT}/qwen3.8-h4-orca-all}"
H5_MODEL_DIR="${ORCA_R24_H5_MODEL_DIR:-${MODEL_ROOT}/qwen3.8-h5-neutral-input-scale}"
H6_MODEL_DIR="${ORCA_R24_H6_MODEL_DIR:-${MODEL_ROOT}/qwen3.8-h6-modelopt-w4a16}"
for checkpoint in "${BASE_MODEL_DIR}" "${H3_MODEL_DIR}" "${H4_MODEL_DIR}" "${H5_MODEL_DIR}" "${H6_MODEL_DIR}"; do
    [[ -d "${checkpoint}" ]] || fail "required checkpoint missing: ${checkpoint}"
done
[[ -f "${H6_MODEL_DIR}/model.safetensors.index.json" ]] || fail "H6 checkpoint index missing"
validate_h6_manifest || fail "H6 manifest validation failed"

IMAGE_LABEL="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.stability-candidate" }}' 2>/dev/null || true)"
[[ "${IMAGE_LABEL}" == "${EXPECTED_IMAGE_LABEL}" ]] || fail "required v0.29 image is missing or stale: ${IMAGE}"
HYBRID_BLOCK="$(awk '/^  orcarouter-hybrid\)/,/^  \*\)/' "${SERVE}")"
grep -Fq 'DEFAULT_KV_MEM=25769803776' <<<"${HYBRID_BLOCK}" || fail "Hybrid default identity changed; R24 override contract must be reviewed"
[[ ! -e /run/systemd/system/qwen38-flash-next.service.d/kv16-ab.conf ]] || fail "temporary managed KV override is still present"
if docker inspect "${EXPERIMENT_CONTAINER}" >/dev/null 2>&1; then
    fail "R24 experiment container already exists; preserve/remove it explicitly first"
fi

PRE_CONTAINER_ID="$(docker inspect --format '{{.Id}}' "${MANAGED_CONTAINER}" 2>/dev/null || true)"
PRE_CONTAINER_STARTED="$(docker inspect --format '{{.State.StartedAt}}' "${MANAGED_CONTAINER}" 2>/dev/null || true)"
[[ -n "${PRE_CONTAINER_ID}" && -n "${PRE_CONTAINER_STARTED}" ]] || fail "managed predecessor container unavailable"
PREDECESSOR_AGE_S="$(predecessor_age "${PRE_CONTAINER_STARTED}")"

AFF="$(mktemp /tmp/r24-available-functions.XXXXXX)"
sudo -n cat "${TRACEFS}/available_filter_functions" >"${AFF}"
for target in 'nv_alloc_pages.*\[nvidia\]' 'nv_alloc_system_pages.*\[nvidia\]'; do
    grep -Eq "^${target}$" "${AFF}" || { rm -f "${AFF}"; fail "required RM probe target missing: ${target}"; }
done
rm -f "${AFF}"

if [[ "${MODE}" == --preflight ]]; then
    AGE_OK="$(python3 - "${PREDECESSOR_AGE_S}" "${MIN_PREDECESSOR_AGE_S}" <<'PY'
import sys
print(1 if float(sys.argv[1]) >= float(sys.argv[2]) else 0)
PY
)"
    printf 'R24_PREFLIGHT=BEGIN\n'
    printf 'profile=orcarouter-hybrid\n'
    printf 'candidate_checkpoint=%s\n' "${H6_MODEL_DIR}"
    printf 'candidate_image=%s\n' "${IMAGE}"
    printf 'candidate_image_label=%s\n' "${IMAGE_LABEL}"
    printf 'kv_bytes=%s\n' "${KV_BYTES}"
    printf 'predecessor_age_s=%s\n' "${PREDECESSOR_AGE_S}"
    printf 'minimum_predecessor_age_s=%s\n' "${MIN_PREDECESSOR_AGE_S}"
    printf 'predecessor_age_ok=%s\n' "${AGE_OK}"
    printf 'rm_probe_target_count=2\n'
    printf 'model_restart=NO\n'
    printf 'persistent_vm_tuning=NO\n'
    if [[ "${AGE_OK}" == 1 ]]; then
        printf 'R24_PREFLIGHT=PASS\n'
        exit 0
    fi
    printf 'R24_PREFLIGHT=BLOCKED_PREDECESSOR_AGE\n'
    exit 3
fi

python3 - "${PREDECESSOR_AGE_S}" "${MIN_PREDECESSOR_AGE_S}" <<'PY' || fail "predecessor runtime is younger than required R24 minimum"
import sys
raise SystemExit(0 if float(sys.argv[1]) >= float(sys.argv[2]) else 1)
PY
[[ ! -e "${OUT}" ]] || fail "evidence already exists: ${OUT}"

(
    while sleep 60; do
        sudo -n -v >/dev/null 2>&1 || exit 0
    done
) &
SUDO_KEEPALIVE_PID=$!

mkdir -p -- "${OUT}"
printf '%s\n' "$(git -C "${SCRIPT_ROOT}" rev-parse HEAD)" >"${OUT}/repository-head.txt"
printf '%s\n' "${PRE_CONTAINER_ID}" >"${OUT}/container-id-before.txt"
printf '%s\n' "${PRE_CONTAINER_STARTED}" >"${OUT}/container-started-before.txt"
printf '%s\n' "${PREDECESSOR_AGE_S}" >"${OUT}/predecessor-age-s.txt"
printf '%s\n' "${MIN_PREDECESSOR_AGE_S}" >"${OUT}/minimum-predecessor-age-s.txt"
printf '%s\n' "${IMAGE}" >"${OUT}/candidate-image.txt"
printf '%s\n' "${IMAGE_LABEL}" >"${OUT}/candidate-image-label.txt"
printf '%s\n' "${H6_MODEL_DIR}" >"${OUT}/candidate-model-dir.txt"
printf '%s\n' "${H6_SERVED_NAME}" >"${OUT}/candidate-served-name.txt"
printf '%s\n' "${KV_BYTES}" >"${OUT}/kv-bytes.txt"
printf '%s\n' "${TRACE_ARM_DELAY_S}" >"${OUT}/trace-arm-delay-s.txt"
printf '%s\n' "${TRACE_DURATION_S}" >"${OUT}/trace-duration-requested-s.txt"
getconf PAGESIZE >"${OUT}/host-page-size.txt"
START_ISO="$(date --iso-8601=seconds)"
START_EPOCH="$(date +%s.%N)"
printf '%s\n' "${START_ISO}" >"${OUT}/start-iso.txt"
printf '%s\n' "${START_EPOCH}" >"${OUT}/start-epoch.txt"

sudo -n /usr/bin/python3 "${COLLECTOR}" \
    --output "${STATE_OUT}" --stop-file "${STOP_FILE}" \
    --fast-interval 1 --slow-interval 5 \
    >"${OUT}/collector.log" 2>&1 &
COLLECTOR_PID=$!
sleep 2
kill -0 "${COLLECTOR_PID}" >/dev/null 2>&1 || fail "allocator collector exited before teardown"

sudo -n systemctl stop "${UNIT}"
SERVICE_STOPPED=1
for _ in $(seq 1 120); do
    systemctl is-active --quiet "${UNIT}" || break
    sleep 1
done
systemctl is-active --quiet "${UNIT}" && fail "managed service did not stop"
[[ "$(docker inspect --format '{{.State.Running}}' "${MANAGED_CONTAINER}" 2>/dev/null || printf false)" != true ]] || fail "managed predecessor still running"

snapshot_proc "${OUT}/poststop-before-reclaim"
sudo -n sync
snapshot_proc "${OUT}/poststop-after-sync"
sudo -n /bin/sh -c 'printf 1 > /proc/sys/vm/drop_caches'
snapshot_proc "${OUT}/poststop-after-drop-caches"
sudo -n /bin/sh -c 'printf 1 > /proc/sys/vm/compact_memory'
printf '%s\n' "$(mono_ns)" >"${OUT}/compact-complete-monotonic-ns.txt"
snapshot_proc "${OUT}/poststop-after-compact"

create_probes
CANDIDATE_REQUEST_ISO="$(date --iso-8601=ns)"
CANDIDATE_REQUEST_NS="$(mono_ns)"
printf '%s\n' "${CANDIDATE_REQUEST_ISO}" >"${OUT}/candidate-request-iso.txt"
printf '%s\n' "${CANDIDATE_REQUEST_NS}" >"${OUT}/candidate-request-monotonic-ns.txt"

set +e
MODEL_PROFILE=orcarouter-hybrid \
MODEL_DIR="${H6_MODEL_DIR}" \
SERVED_NAME="${H6_SERVED_NAME}" \
VLLM_IMAGE="${IMAGE}" \
NAME="${EXPERIMENT_CONTAINER}" \
PORT=8888 \
PUBLISH_HOST=127.0.0.1 \
RESTART_POLICY=no \
MONITOR_ENABLED=0 \
MONITOR_PROTECT=0 \
MAXLEN=262144 \
NSPEC=2 \
INDEX_SHARE=0 \
GPU_UTIL=0.80 \
KV_MEM="${KV_BYTES}" \
MAXSEQS=3 \
AUTOTUNE=0 \
QSA_EXACT_TOPK=1 \
PREFIX_CACHE=0 \
SPEC=mtp \
QWEN38_MODEL_ROOT="${MODEL_ROOT}" \
ORCAROUTER_MODEL_DIR="${BASE_MODEL_DIR}" \
HYBRID_QUANT_LAYOUT_MODEL_DIR="${H3_MODEL_DIR}" \
H4_ORCA_ALL_MODEL_DIR="${H4_MODEL_DIR}" \
H5_NEUTRAL_INPUT_MODEL_DIR="${H5_MODEL_DIR}" \
bash "${SERVE}" >"${OUT}/candidate-start.stdout" 2>"${OUT}/candidate-start.stderr"
START_RC=$?
set -e
printf '%s\n' "${START_RC}" >"${OUT}/candidate-start.rc"
[[ "${START_RC}" == 0 ]] || fail "H6 candidate failed to start"
EXPERIMENT_STARTED=1

CANDIDATE_ID="$(docker inspect --format '{{.Id}}' "${EXPERIMENT_CONTAINER}")"
CANDIDATE_STARTED="$(docker inspect --format '{{.State.StartedAt}}' "${EXPERIMENT_CONTAINER}")"
printf '%s\n' "${CANDIDATE_ID}" >"${OUT}/candidate-container-id.txt"
printf '%s\n' "${CANDIDATE_STARTED}" >"${OUT}/candidate-container-started.txt"
validate_candidate_identity || fail "candidate runtime identity validation failed"
printf '1\n' >"${OUT}/candidate-identity-valid.txt"

XDG_STATE_HOME="${OUT}/monitor-state" bash "${MONITOR}" \
    --container "${EXPERIMENT_CONTAINER}" \
    --min-available-gib 6 --min-free-gib 2 --free-gate-gib 10 \
    --min-swap-free-gib 8 --consecutive 5 --interval 2 --heartbeat 60 --protect \
    >"${OUT}/memory-monitor.log" 2>&1 &
MONITOR_PID=$!

aim_ns="$((CANDIDATE_REQUEST_NS + TRACE_ARM_DELAY_S * 1000000000))"
remaining_s="$(python3 - "${aim_ns}" <<'PY'
import sys
import time
print(f"{max(0.0, (int(sys.argv[1]) - time.monotonic_ns()) / 1e9):.6f}")
PY
)"
sleep "${remaining_s}"

TRACE_ARGS=(
    -e "${GROUP}:nv_alloc_pages_entry"
    -e "${GROUP}:nv_alloc_pages_ret"
    -e "${GROUP}:nv_alloc_system_pages_entry"
    -e "${GROUP}:nv_alloc_system_pages_ret"
)
if [[ -r "${TRACEFS}/events/nvidia/nvidia_dev_xid/format" ]]; then
    TRACE_ARGS+=( -e nvidia:nvidia_dev_xid )
fi
printf '%s\n' "$(date --iso-8601=ns)" >"${OUT}/trace-window-start-iso.txt"
printf '%s\n' "$(mono_ns)" >"${OUT}/trace-window-start-monotonic-ns.txt"
set +e
sudo -n trace-cmd record -C mono -o "${OUT}/rm-trace.dat" \
    "${TRACE_ARGS[@]}" --user "${RUN_USER}" -- env -i \
    HOME="${RUN_HOME}" USER="${RUN_USER}" LOGNAME="${RUN_USER}" PATH="${FIXED_PATH}" \
    sleep "${TRACE_DURATION_S}" >"${OUT}/rm-trace-cmd.log" 2>&1
TRACE_RC=$?
set -e
printf '%s\n' "$(date --iso-8601=ns)" >"${OUT}/trace-window-end-iso.txt"
printf '%s\n' "$(mono_ns)" >"${OUT}/trace-window-end-monotonic-ns.txt"
printf '%s\n' "${TRACE_RC}" >"${OUT}/trace-command.rc"
cleanup_probes

set +e
sudo -n trace-cmd report -i "${OUT}/rm-trace.dat" >"${OUT}/rm-trace.txt"
REPORT_RC=$?
set -e
printf '%s\n' "${REPORT_RC}" >"${OUT}/trace-report.rc"

set +e
"${WAIT_READY}" --container "${EXPERIMENT_CONTAINER}" --model "${H6_SERVED_NAME}" \
    --timeout 1800 --interval 10 >"${OUT}/wait-ready.log" 2>&1
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
sudo -n journalctl -k --since "${START_JOURNAL}" --until "${END_JOURNAL}" \
    -o short-iso-precise --no-pager >"${OUT}/kernel-window.txt"
ERROR_RE='NV_ERR_NO_MEMORY|_memdescAllocInternal|NVRM:.*Xid|Xid \(PCI|GPU has fallen off the bus|oom-kill:|Out of memory:|Killed process '
grep -Ei "${ERROR_RE}" "${OUT}/kernel-window.txt" >"${OUT}/kernel-errors.txt" || true
RM_OOM_COUNT="$(grep -Ec 'NV_ERR_NO_MEMORY|_memdescAllocInternal' "${OUT}/kernel-errors.txt" 2>/dev/null || true)"
EVENT_SNAPSHOT_COUNT="$(find "${STATE_OUT}/events" -mindepth 1 -maxdepth 1 -type d -name 'rm-oom-*' 2>/dev/null | wc -l)"

set +e
python3 "${ANALYZER}" "${OUT}" >"${OUT}/r24-analysis.txt"
ANALYZER_RC=$?
set -e
printf '%s\n' "${ANALYZER_RC}" >"${OUT}/analyzer.rc"

API_READY=0
if [[ "${READY_RC}" == 0 ]] && \
   [[ "$(docker inspect --format '{{.State.Running}}' "${EXPERIMENT_CONTAINER}" 2>/dev/null || true)" == true ]] && \
   curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null 2>&1; then
    API_READY=1
fi

TRACE_WINDOW_VALID="$(python3 - \
    "${OUT}/candidate-request-monotonic-ns.txt" \
    "${OUT}/trace-window-start-monotonic-ns.txt" \
    "${OUT}/trace-window-end-monotonic-ns.txt" <<'PY'
import pathlib
import sys
request, start, end = [int(pathlib.Path(path).read_text().strip()) for path in sys.argv[1:]]
start_offset = (start - request) / 1e9
duration = (end - start) / 1e9
print(1 if 15.0 <= start_offset <= 30.0 and 45.0 <= duration <= 60.0 else 0)
PY
)"

RUN_VALID=1
if [[ "${START_RC}" != 0 || "${COLLECTOR_RC}" != 0 || "${TRACE_RC}" != 0 || \
      "${REPORT_RC}" != 0 || "${ANALYZER_RC}" != 0 || "${READY_RC}" != 0 || \
      "${API_READY}" != 1 || "${PROTECTED_STOP}" != 0 || "${TRACE_WINDOW_VALID}" != 1 ]]; then
    RUN_VALID=0
fi
FUNCTIONAL_CLASS="INVALID"
HOST_CLASS="INVALID"
if [[ "${RUN_VALID}" == 1 ]]; then
    FUNCTIONAL_CLASS="PASS"
    if [[ "${RM_OOM_COUNT}" == 0 ]]; then HOST_CLASS="PASS"; else HOST_CLASS="FAIL"; fi
fi

if [[ "$(docker inspect --format '{{.State.Running}}' "${EXPERIMENT_CONTAINER}" 2>/dev/null || true)" == true ]]; then
    docker stop --timeout 30 "${EXPERIMENT_CONTAINER}" >/dev/null
fi
EXPERIMENT_STARTED=0
sudo -n systemctl start "${UNIT}"
SERVICE_STOPPED=0

{
    printf 'run_valid=%s\n' "${RUN_VALID}"
    printf 'candidate_start_rc=%s\n' "${START_RC}"
    printf 'collector_rc=%s\n' "${COLLECTOR_RC}"
    printf 'trace_rc=%s\n' "${TRACE_RC}"
    printf 'trace_report_rc=%s\n' "${REPORT_RC}"
    printf 'analyzer_rc=%s\n' "${ANALYZER_RC}"
    printf 'wait_ready_rc=%s\n' "${READY_RC}"
    printf 'api_ready=%s\n' "${API_READY}"
    printf 'protected_stop=%s\n' "${PROTECTED_STOP}"
    printf 'trace_window_valid=%s\n' "${TRACE_WINDOW_VALID}"
    printf 'candidate_identity_valid=1\n'
    printf 'functional_class=%s\n' "${FUNCTIONAL_CLASS}"
    printf 'host_stability_class=%s\n' "${HOST_CLASS}"
    printf 'predecessor_age_s=%s\n' "${PREDECESSOR_AGE_S}"
    printf 'minimum_predecessor_age_s=%s\n' "${MIN_PREDECESSOR_AGE_S}"
    printf 'profile=orcarouter-hybrid\n'
    printf 'kv_bytes=%s\n' "${KV_BYTES}"
    printf 'rm_oom_count=%s\n' "${RM_OOM_COUNT}"
    printf 'event_snapshot_count=%s\n' "${EVENT_SNAPSHOT_COUNT}"
} >"${OUT}/r24-summary.txt"

sudo -n chown -R "${RUN_USER}:${RUN_GROUP}" "${OUT}" 2>/dev/null || true
printf '\n===== R24 summary =====\n'
cat "${OUT}/r24-summary.txt"
printf '%s\n' '--- mitigation analysis ---'
cat "${OUT}/r24-analysis.txt" || true
printf '%s\n' '--- kernel errors ---'
cat "${OUT}/kernel-errors.txt" || true
printf 'evidence=%s\n' "${OUT}"

if [[ "${RUN_VALID}" != 1 ]]; then
    printf 'ORCA_R24_RESULT=INVALID\n'
    exit 1
fi
if [[ "${RM_OOM_COUNT}" == 0 ]]; then
    printf 'ORCA_R24_RESULT=VALID_CLEAN\n'
else
    printf 'ORCA_R24_RESULT=VALID_RM_OOM\n'
fi
