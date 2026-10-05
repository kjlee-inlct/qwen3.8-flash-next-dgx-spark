#!/usr/bin/env bash
# R23: trace only the early managed OrcaRouter startup burst at RM/UVM ownership
# boundaries. This is an ownership experiment, not a VM-tuning experiment.

set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"
CURRENT_LINK="${DATA_HOME}/current"
STATE_FILE="${STATE_HOME}/install.env"
UNIT="qwen38-flash-next.service"
CONTAINER="qwen38-flash-next"
OUT="${ORCA_R23_OUT:-/tmp/orcarouter-managed-rmsys-r23-early-burst-ownership-01-20261004}"
STATE_OUT="${OUT}/allocator-state"
STOP_FILE="${OUT}/collector.stop"
COLLECTOR="${SCRIPT_ROOT}/scripts/benchmark/collect-linux-allocator-state.py"
ANALYZER="${SCRIPT_ROOT}/scripts/benchmark/analyze-orcarouter-r23-ownership.py"
RELEASE_MANAGER="${SCRIPT_ROOT}/scripts/release-manager.sh"
UPDATE_TRANSITION="${SCRIPT_ROOT}/scripts/update-transition.sh"
RUNTIME_TRANSITION="${SCRIPT_ROOT}/scripts/runtime-transition.sh"
PROFILE_TRANSITION="${SCRIPT_ROOT}/scripts/profile-switch-transition.sh"
MIN_PREDECESSOR_AGE_S="${ORCA_R23_MIN_PREDECESSOR_AGE_S:-2700}"
TRACE_ARM_DELAY_S=20
TRACE_DURATION_S=50
GROUP="r23_own"

RUN_USER="${SUDO_USER:-$(id -un)}"
RUN_GROUP="$(id -gn "${RUN_USER}")"
RUN_HOME="$(getent passwd "${RUN_USER}" | cut -d: -f6)"
FIXED_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
COLLECTOR_PID=""
MANAGED_PID=""
TRACE_PID=""
SUDO_KEEPALIVE_PID=""
COLLECTOR_RC=125
MANAGED_RC=125
TRACE_RC=125
REPORT_RC=125
ANALYZER_RC=125
SERVICE_RECOVERY_ARMED=0

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
    pma_alloc_entry
    pma_alloc_ret
    uvm_dma_alloc_entry
    uvm_dma_alloc_ret
    uvm_mem_alloc_entry
    uvm_mem_alloc_ret
    uvm_pmm_alloc_entry
    uvm_pmm_alloc_ret
)

TARGETS=(
    "nv_alloc_pages:nvidia"
    "nv_alloc_system_pages:nvidia"
    "nvUvmInterfacePmaAllocPages:nvidia"
    "uvm_gpu_dma_alloc:nvidia_uvm"
    "uvm_mem_alloc:nvidia_uvm"
    "uvm_pmm_gpu_alloc_kernel:nvidia_uvm"
)

fail() {
    printf 'ORCA_R23_ERROR: %s\n' "$*" >&2
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

write_kprobe_commands() {
    local source_file="$1"
    sudo -n python3 - "${KPROBE_EVENTS}" "${source_file}" <<'PY'
import os
import pathlib
import sys

path = sys.argv[1]
source = pathlib.Path(sys.argv[2])
for raw in source.read_bytes().splitlines():
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

tracefs = pathlib.Path(sys.argv[1])
group_dir = tracefs / "events" / sys.argv[2]
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
    except OSError as exc:
        print(
            f"DISABLE_FAIL path={target} errno={exc.errno} message={exc.strerror}",
            file=sys.stderr,
        )
PY
}

cleanup_probes() {
    local tmp event
    tmp="$(mktemp /tmp/r23-ownership-kprobe-cleanup.XXXXXX)"
    disable_probe_events || true
    for event in "${PROBE_EVENTS[@]}"; do
        printf '%s\n' "-:${GROUP}/${event}" >>"${tmp}"
    done
    sudo -n python3 - "${KPROBE_EVENTS}" "${tmp}" <<'PY' >/dev/null 2>&1 || true
import errno
import os
import pathlib
import sys

path = sys.argv[1]
for raw in pathlib.Path(sys.argv[2]).read_bytes().splitlines():
    command = raw.strip()
    if not command:
        continue
    try:
        fd = os.open(path, os.O_WRONLY)
        try:
            os.write(fd, command + b"\n")
        finally:
            os.close(fd)
    except OSError as exc:
        if exc.errno != errno.ENOENT:
            print(
                f"cleanup failed: {command!r}: errno={exc.errno} {exc.strerror}",
                file=sys.stderr,
            )
PY
    rm -f -- "${tmp}"
}

verify_target_presence() {
    local aff="$1" item fn module
    : >"${OUT}/probe-targets.txt"
    for item in "${TARGETS[@]}"; do
        IFS=: read -r fn module <<<"${item}"
        if grep -Eq "^${fn}([[:space:]].*)?[[:space:]]\\[${module}\\]$" "${aff}"; then
            printf 'PRESENT function=%s module=%s\n' "${fn}" "${module}" \
                >>"${OUT}/probe-targets.txt"
        else
            fail "required R23 probe target disappeared: ${fn} [${module}]"
        fi
    done
}

create_probes() {
    local definitions="${OUT}/probe-definitions.txt"
    cleanup_probes
    if sudo -n cat "${KPROBE_EVENTS}" | grep -Fq "${GROUP}/"; then
        fail "stale ${GROUP} probes remain after cleanup"
    fi
    cat >"${definitions}" <<'EOF'
p:r23_own/nv_alloc_pages_entry nv_alloc_pages page_count=$arg2:u32 page_size=$arg3:u64 contiguous=$arg4:u8 cache_type=$arg5:u32 zeroed=$arg6:u8 unencrypted=$arg7:u8 node_id=$arg8:s32
r:r23_own/nv_alloc_pages_ret nv_alloc_pages ret=$retval:u32
p:r23_own/nv_alloc_system_pages_entry nv_alloc_system_pages at=$arg2:u64
r:r23_own/nv_alloc_system_pages_ret nv_alloc_system_pages ret=$retval:u32
p:r23_own/pma_alloc_entry nvUvmInterfacePmaAllocPages page_count=$arg2:u64 page_size=$arg3:u64
r:r23_own/pma_alloc_ret nvUvmInterfacePmaAllocPages ret=$retval:u32
p:r23_own/uvm_dma_alloc_entry uvm_gpu_dma_alloc size=$arg1:u64 gfp=$arg3:u64
r:r23_own/uvm_dma_alloc_ret uvm_gpu_dma_alloc ret=$retval:u32
p:r23_own/uvm_mem_alloc_entry uvm_mem_alloc
r:r23_own/uvm_mem_alloc_ret uvm_mem_alloc raw_ret=$retval:u64
p:r23_own/uvm_pmm_alloc_entry uvm_pmm_gpu_alloc_kernel num_chunks=$arg2:u64 chunk_size=$arg3:u64 flags=$arg4:u32
r:r23_own/uvm_pmm_alloc_ret uvm_pmm_gpu_alloc_kernel ret=$retval:u32
EOF
    write_kprobe_commands "${definitions}" || fail "failed to install R23 probes"
}

verify_probe_formats() {
    local event format field
    local nv_fields=(
        page_count page_size contiguous cache_type zeroed unencrypted node_id
    )
    : >"${OUT}/probe-formats.txt"
    for event in "${PROBE_EVENTS[@]}"; do
        format="${TRACEFS}/events/${GROUP}/${event}/format"
        sudo -n cat "${format}" >/dev/null 2>&1 || \
            fail "probe format unreadable: ${format}"
        printf 'PRESENT %s:%s\n' "${GROUP}" "${event}" \
            >>"${OUT}/probe-formats.txt"
    done
    format="${TRACEFS}/events/${GROUP}/nv_alloc_pages_entry/format"
    for field in "${nv_fields[@]}"; do
        sudo -n grep -Eq "field:.*[[:space:]]${field};" "${format}" || \
            fail "missing nv_alloc_pages field: ${field}"
    done
}

stop_background_pid() {
    local pid="$1"
    [[ -n "${pid}" ]] || return 0
    if kill -0 "${pid}" >/dev/null 2>&1; then
        kill "${pid}" >/dev/null 2>&1 || true
        wait "${pid}" >/dev/null 2>&1 || true
    fi
}

cleanup() {
    local rc=$?
    trap - EXIT INT TERM
    set +e

    stop_background_pid "${TRACE_PID}"
    cleanup_probes

    touch "${STOP_FILE}" 2>/dev/null || true
    if [[ -n "${COLLECTOR_PID}" ]] && kill -0 "${COLLECTOR_PID}" >/dev/null 2>&1; then
        wait "${COLLECTOR_PID}" >/dev/null 2>&1 || true
    fi

    # During asynchronous managed startup keep recovery armed until the service
    # has returned successfully. If the wrapper is still running on an error or
    # signal, stop it first; sudo forwards the signal to the managed child.
    stop_background_pid "${MANAGED_PID}"

    if [[ "${SERVICE_RECOVERY_ARMED}" == 1 ]] && \
       ! systemctl is-active --quiet "${UNIT}"; then
        sudo -n systemctl start "${UNIT}" >/dev/null 2>&1 || true
    fi

    stop_background_pid "${SUDO_KEEPALIVE_PID}"
    exit "${rc}"
}
trap cleanup EXIT INT TERM

for command in \
    sudo python3 bash systemctl docker curl journalctl date grep awk find wc cat \
    tee seq sleep mkdir sync getconf trace-cmd stat mktemp env
 do
    command -v "${command}" >/dev/null 2>&1 || \
        fail "required command not found: ${command}"
done

sudo -n true >/dev/null 2>&1 || \
    fail "sudo timestamp unavailable; run sudo -v first"
(
    while sleep 60; do
        sudo -n -v >/dev/null 2>&1 || exit 0
    done
) &
SUDO_KEEPALIVE_PID=$!

[[ -e "${KPROBE_EVENTS}" ]] || fail "kprobe_events unavailable under ${TRACEFS}"
[[ -r "${STATE_FILE}" ]] || fail "installation state missing: ${STATE_FILE}"
[[ -r "${COLLECTOR}" ]] || fail "allocator collector missing: ${COLLECTOR}"
[[ -r "${ANALYZER}" ]] || fail "R23 analyzer missing: ${ANALYZER}"
[[ -L "${CURRENT_LINK}" ]] || \
    fail "immutable current release link missing: ${CURRENT_LINK}"
[[ ! -e "${OUT}" ]] || fail "evidence already exists: ${OUT}"

grep -qx 'MODEL_PROFILE=orcarouter' "${STATE_FILE}" || \
    fail "managed profile is not OrcaRouter"
[[ ! -e /run/systemd/system/qwen38-flash-next.service.d/kv16-ab.conf ]] || \
    fail "temporary KV override is still present"
grep -qx 'UPDATE_STATE=idle' < <(bash "${UPDATE_TRANSITION}" status) || \
    fail "update transition is not idle"
grep -qx 'TRANSACTION_STATE=idle' < <(bash "${RUNTIME_TRANSITION}" status) || \
    fail "runtime transition is not idle"
grep -qx 'PROFILE_SWITCH_STATE=idle' < <(bash "${PROFILE_TRANSITION}" status) || \
    fail "profile-switch transition is not idle"
systemctl is-active --quiet "${UNIT}" || fail "managed service is not active"
curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null || \
    fail "managed API is not healthy"

CURRENT_RELEASE="$(
    bash "${RELEASE_MANAGER}" status |
        awk -F= '$1=="CURRENT_RELEASE" {print $2}'
)"
[[ -n "${CURRENT_RELEASE}" && "${CURRENT_RELEASE}" != none ]] || \
    fail "no immutable current release"
MANAGE_SERVICE="${CURRENT_LINK}/scripts/manage-service.sh"
SERVE="${CURRENT_LINK}/scripts/serve.sh"
[[ -x "${MANAGE_SERVICE}" ]] || \
    fail "managed service helper missing from current release"
[[ -r "${SERVE}" ]] || fail "serve helper missing from current release"
ORCA_BLOCK="$(awk '/^  orcarouter\)/,/^  nvidia\)/' "${SERVE}")"
grep -Fq 'DEFAULT_KV_MEM=17179869184' <<<"${ORCA_BLOCK}" || \
    fail "current release no longer defaults OrcaRouter to 16 GiB"

PRE_CONTAINER_ID="$(
    docker inspect --format '{{.Id}}' "${CONTAINER}" 2>/dev/null || true
)"
PRE_CONTAINER_STARTED="$(
    docker inspect --format '{{.State.StartedAt}}' "${CONTAINER}" 2>/dev/null || true
)"
[[ -n "${PRE_CONTAINER_ID}" && -n "${PRE_CONTAINER_STARTED}" ]] || \
    fail "managed predecessor container is unavailable"
PREDECESSOR_AGE_S="$(python3 - "${PRE_CONTAINER_STARTED}" <<'PY'
import datetime as dt
import sys
started = dt.datetime.fromisoformat(sys.argv[1].replace('Z', '+00:00'))
now = dt.datetime.now(dt.timezone.utc)
print(f"{(now - started).total_seconds():.3f}")
PY
)"
python3 - "${PREDECESSOR_AGE_S}" "${MIN_PREDECESSOR_AGE_S}" <<'PY' || \
    fail "predecessor runtime is younger than required R23 minimum"
import sys
raise SystemExit(0 if float(sys.argv[1]) >= float(sys.argv[2]) else 1)
PY

mkdir -p -- "${OUT}"
printf '%s\n' "${CURRENT_RELEASE}" >"${OUT}/release-before.txt"
printf '%s\n' "${PRE_CONTAINER_ID}" >"${OUT}/container-id-before.txt"
printf '%s\n' "${PRE_CONTAINER_STARTED}" >"${OUT}/container-started-before.txt"
printf '%s\n' "${PREDECESSOR_AGE_S}" >"${OUT}/predecessor-age-s.txt"
printf '%s\n' "${MIN_PREDECESSOR_AGE_S}" >"${OUT}/minimum-predecessor-age-s.txt"
printf '%s\n' "${TRACE_ARM_DELAY_S}" >"${OUT}/trace-arm-delay-s.txt"
printf '%s\n' "${TRACE_DURATION_S}" >"${OUT}/trace-duration-requested-s.txt"
getconf PAGESIZE >"${OUT}/host-page-size.txt"
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
kill -0 "${COLLECTOR_PID}" >/dev/null 2>&1 || \
    fail "allocator collector exited before teardown"

printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/stop-started-iso.txt"
sudo -n systemctl stop "${UNIT}"
SERVICE_RECOVERY_ARMED=1
for _ in $(seq 1 120); do
    systemctl is-active --quiet "${UNIT}" || break
    sleep 1
done
systemctl is-active --quiet "${UNIT}" && fail "managed service did not stop"
if [[ "$(
    docker inspect --format '{{.State.Running}}' "${CONTAINER}" 2>/dev/null || \
        printf false
)" == true ]]; then
    fail "predecessor container is still running after service stop"
fi
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/stop-complete-iso.txt"

snapshot_proc "${OUT}/poststop-before-reclaim"
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/sync-started-iso.txt"
sudo -n sync
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/sync-complete-iso.txt"
snapshot_proc "${OUT}/poststop-after-sync"

printf '%s\n' "$(date --iso-8601=seconds)" \
    >"${OUT}/drop-caches-started-iso.txt"
sudo -n /bin/sh -c 'printf 1 > /proc/sys/vm/drop_caches'
printf '%s\n' "$(date --iso-8601=seconds)" \
    >"${OUT}/drop-caches-complete-iso.txt"
snapshot_proc "${OUT}/poststop-after-drop-caches"

printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/compact-started-iso.txt"
sudo -n /bin/sh -c 'printf 1 > /proc/sys/vm/compact_memory'
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/compact-complete-iso.txt"
printf '%s\n' "$(mono_ns)" >"${OUT}/compact-complete-monotonic-ns.txt"
snapshot_proc "${OUT}/poststop-after-compact"
printf '%s\n' "$(mono_ns)" >"${OUT}/conditioned-baseline-monotonic-ns.txt"

AFF="${OUT}/available-filter-functions.txt"
sudo -n cat "${TRACEFS}/available_filter_functions" >"${AFF}"
verify_target_presence "${AFF}"
create_probes
verify_probe_formats

REPLACEMENT_REQUEST_ISO="$(date --iso-8601=ns)"
REPLACEMENT_REQUEST_MONO_NS="$(mono_ns)"
printf '%s\n' "${REPLACEMENT_REQUEST_ISO}" >"${OUT}/replacement-request-iso.txt"
printf '%s\n' "${REPLACEMENT_REQUEST_MONO_NS}" \
    >"${OUT}/replacement-request-monotonic-ns.txt"

# Start the normal managed helper asynchronously so the trace can be armed
# during startup. Keep SERVICE_RECOVERY_ARMED=1 until the helper has completed
# successfully and systemd is active; this protects early-failure paths.
sudo -n /bin/bash "${MANAGE_SERVICE}" \
    create --runtime-root "${CURRENT_LINK}" --start --yes \
    >"${OUT}/managed-control.log" 2>&1 &
MANAGED_PID=$!
printf '%s\n' "${MANAGED_PID}" >"${OUT}/managed-command.pid"

POST_CONTAINER_ID=""
POST_CONTAINER_STARTED=""
for _ in $(seq 1 480); do
    candidate_id="$(
        docker inspect --format '{{.Id}}' "${CONTAINER}" 2>/dev/null || true
    )"
    candidate_running="$(
        docker inspect --format '{{.State.Running}}' "${CONTAINER}" 2>/dev/null || true
    )"
    if [[ -n "${candidate_id}" && \
          "${candidate_id}" != "${PRE_CONTAINER_ID}" && \
          "${candidate_running}" == true ]]; then
        POST_CONTAINER_ID="${candidate_id}"
        POST_CONTAINER_STARTED="$(
            docker inspect --format '{{.State.StartedAt}}' "${CONTAINER}"
        )"
        break
    fi

    if ! kill -0 "${MANAGED_PID}" >/dev/null 2>&1; then
        set +e
        wait "${MANAGED_PID}"
        MANAGED_RC=$?
        set -e
        MANAGED_PID=""
        printf '%s\n' "${MANAGED_RC}" >"${OUT}/managed-command.rc"
        fail "managed start exited before replacement was observed: rc=${MANAGED_RC}"
    fi
    sleep 0.25
done
[[ -n "${POST_CONTAINER_ID}" ]] || \
    fail "replacement container was not observed within 120 seconds"
printf '%s\n' "${POST_CONTAINER_ID}" >"${OUT}/container-id-after.txt"
printf '%s\n' "${POST_CONTAINER_STARTED}" >"${OUT}/container-started-after.txt"
printf '%s\n' "$(date --iso-8601=ns)" >"${OUT}/replacement-observed-iso.txt"
printf '%s\n' "$(mono_ns)" >"${OUT}/replacement-observed-monotonic-ns.txt"

aim_ns="$((REPLACEMENT_REQUEST_MONO_NS + TRACE_ARM_DELAY_S * 1000000000))"
remaining_s="$(python3 - "${aim_ns}" <<'PY'
import sys
import time
remaining = (int(sys.argv[1]) - time.monotonic_ns()) / 1_000_000_000
print(f"{max(0.0, remaining):.6f}")
PY
)"
sleep "${remaining_s}"

TRACE_DAT="${OUT}/ownership-trace.dat"
TRACE_LOG="${OUT}/ownership-trace-cmd.log"
TRACE_ARGS=()
for event in "${PROBE_EVENTS[@]}"; do
    TRACE_ARGS+=( -e "${GROUP}:${event}" )
done
if [[ -r "${TRACEFS}/events/nvidia/nvidia_dev_xid/format" ]]; then
    TRACE_ARGS+=( -e nvidia:nvidia_dev_xid )
    printf '1\n' >"${OUT}/trace-includes-nvidia-xid.txt"
else
    printf '0\n' >"${OUT}/trace-includes-nvidia-xid.txt"
fi

(
    trace_start_iso="$(date --iso-8601=ns)"
    trace_start_ns="$(mono_ns)"
    printf '%s\n' "${trace_start_iso}" >"${OUT}/trace-window-start-iso.txt"
    printf '%s\n' "${trace_start_ns}" \
        >"${OUT}/trace-window-start-monotonic-ns.txt"
    set +e
    sudo -n trace-cmd record \
        -C mono \
        -o "${TRACE_DAT}" \
        "${TRACE_ARGS[@]}" \
        --user "${RUN_USER}" \
        -- env -i \
            HOME="${RUN_HOME}" \
            USER="${RUN_USER}" \
            LOGNAME="${RUN_USER}" \
            PATH="${FIXED_PATH}" \
            sleep "${TRACE_DURATION_S}" \
        >"${TRACE_LOG}" 2>&1
    rc=$?
    trace_end_iso="$(date --iso-8601=ns)"
    trace_end_ns="$(mono_ns)"
    printf '%s\n' "${trace_end_iso}" >"${OUT}/trace-window-end-iso.txt"
    printf '%s\n' "${trace_end_ns}" >"${OUT}/trace-window-end-monotonic-ns.txt"
    printf '%s\n' "${rc}" >"${OUT}/trace-command.rc"
    exit "${rc}"
) &
TRACE_PID=$!
printf '%s\n' "${TRACE_PID}" >"${OUT}/trace-command.pid"

set +e
wait "${TRACE_PID}"
TRACE_RC=$?
set -e
TRACE_PID=""
if [[ -f "${OUT}/trace-command.rc" ]]; then
    TRACE_RC="$(cat "${OUT}/trace-command.rc")"
fi
printf '%s\n' "${TRACE_RC}" >"${OUT}/trace-command.rc"

set +e
sudo -n trace-cmd report -i "${TRACE_DAT}" \
    >"${OUT}/ownership-trace.txt" \
    2>"${OUT}/ownership-trace-report.stderr"
REPORT_RC=$?
set -e
printf '%s\n' "${REPORT_RC}" >"${OUT}/trace-report.rc"
stat -c '%s' "${TRACE_DAT}" >"${OUT}/ownership-trace-dat-bytes.txt" \
    2>/dev/null || printf '0\n' >"${OUT}/ownership-trace-dat-bytes.txt"
stat -c '%s' "${OUT}/ownership-trace.txt" \
    >"${OUT}/ownership-trace-text-bytes.txt" \
    2>/dev/null || printf '0\n' >"${OUT}/ownership-trace-text-bytes.txt"

cleanup_probes
if sudo -n cat "${KPROBE_EVENTS}" | grep -Fq "${GROUP}/"; then
    fail "stale ${GROUP} probes remain after live trace"
fi

set +e
wait "${MANAGED_PID}"
MANAGED_RC=$?
set -e
MANAGED_PID=""
printf '%s\n' "${MANAGED_RC}" >"${OUT}/managed-command.rc"
if systemctl is-active --quiet "${UNIT}"; then
    SERVICE_RECOVERY_ARMED=0
fi

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

START_SEC="${START_EPOCH%%.*}"
END_SEC="$(( ${END_EPOCH%%.*} + 2 ))"
START_JOURNAL="$(date -d "@${START_SEC}" '+%Y-%m-%d %H:%M:%S')"
END_JOURNAL="$(date -d "@${END_SEC}" '+%Y-%m-%d %H:%M:%S')"
sudo -n journalctl -k \
    --since "${START_JOURNAL}" \
    --until "${END_JOURNAL}" \
    -o short-iso-precise \
    --no-pager \
    >"${OUT}/kernel-window.txt"
sudo -n journalctl -u "${UNIT}" \
    --since "${START_JOURNAL}" \
    --until "${END_JOURNAL}" \
    -o short-iso-precise \
    --no-pager \
    >"${OUT}/service-window.txt" || true
docker logs --timestamps "${CONTAINER}" >"${OUT}/container-window.txt" 2>&1 || true
ERROR_RE='NV_ERR_NO_MEMORY|_memdescAllocInternal|NVRM:.*Xid|Xid \(PCI|GPU has fallen off the bus|oom-kill:|Out of memory:|Killed process '
grep -Ei "${ERROR_RE}" "${OUT}/kernel-window.txt" \
    >"${OUT}/kernel-errors.txt" || true
RM_OOM_COUNT="$(
    grep -Ec 'NV_ERR_NO_MEMORY|_memdescAllocInternal' \
        "${OUT}/kernel-errors.txt" 2>/dev/null || true
)"
EVENT_SNAPSHOT_COUNT="$(
    find "${STATE_OUT}/events" \
        -mindepth 1 \
        -maxdepth 1 \
        -type d \
        -name 'rm-oom-*' \
        2>/dev/null | wc -l
)"

FINAL_CONTAINER_ID="$(
    docker inspect --format '{{.Id}}' "${CONTAINER}" 2>/dev/null || true
)"
FINAL_CONTAINER_STARTED="$(
    docker inspect --format '{{.State.StartedAt}}' "${CONTAINER}" 2>/dev/null || true
)"
printf '%s\n' "${FINAL_CONTAINER_ID}" >"${OUT}/container-id-final.txt"
printf '%s\n' "${FINAL_CONTAINER_STARTED}" >"${OUT}/container-started-final.txt"
RESTART_OBSERVED=0
if [[ -n "${FINAL_CONTAINER_ID}" && \
      "${FINAL_CONTAINER_ID}" != "${PRE_CONTAINER_ID}" && \
      "${FINAL_CONTAINER_ID}" == "${POST_CONTAINER_ID}" ]]; then
    RESTART_OBSERVED=1
fi
printf '%s\n' "${RESTART_OBSERVED}" >"${OUT}/restart-observed.txt"

RELEASE_AFTER="$(
    bash "${RELEASE_MANAGER}" status |
        awk -F= '$1=="CURRENT_RELEASE" {print $2}'
)"
printf '%s\n' "${RELEASE_AFTER}" >"${OUT}/release-after.txt"
RELEASE_STABLE=0
[[ "${RELEASE_AFTER}" == "${CURRENT_RELEASE}" ]] && RELEASE_STABLE=1
printf '%s\n' "${RELEASE_STABLE}" >"${OUT}/release-stable.txt"

API_READY=0
if systemctl is-active --quiet "${UNIT}" && \
   curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null 2>&1; then
    API_READY=1
fi
printf '%s\n' "${API_READY}" >"${OUT}/api-ready.txt"

TRACE_WINDOW_VALID="$(python3 - "${OUT}" <<'PY'
import pathlib
import sys

root = pathlib.Path(sys.argv[1])

def n(name):
    return int((root / name).read_text().strip())

try:
    request = n('replacement-request-monotonic-ns.txt')
    start = n('trace-window-start-monotonic-ns.txt')
    end = n('trace-window-end-monotonic-ns.txt')
except Exception:
    print(0)
    raise SystemExit

start_offset = (start - request) / 1e9
duration = (end - start) / 1e9
(root / 'trace-window-start-offset-s.txt').write_text(f'{start_offset:.6f}\n')
(root / 'trace-window-actual-duration-s.txt').write_text(f'{duration:.6f}\n')
print(1 if 15.0 <= start_offset <= 30.0 and 45.0 <= duration <= 60.0 else 0)
PY
)"
printf '%s\n' "${TRACE_WINDOW_VALID}" >"${OUT}/trace-window-valid.txt"

RUN_VALID=1
if [[ "${MANAGED_RC}" != 0 || \
      "${COLLECTOR_RC}" != 0 || \
      "${TRACE_RC}" != 0 || \
      "${REPORT_RC}" != 0 || \
      "${RESTART_OBSERVED}" != 1 || \
      "${RELEASE_STABLE}" != 1 || \
      "${API_READY}" != 1 || \
      "${TRACE_WINDOW_VALID}" != 1 ]]; then
    RUN_VALID=0
fi
printf '%s\n' "${RUN_VALID}" >"${OUT}/run-valid.txt"

FUNCTIONAL_CLASS="INCOMPLETE"
HOST_CLASS="INCOMPLETE"
if [[ "${RUN_VALID}" == 1 ]]; then
    FUNCTIONAL_CLASS="PASS"
    if [[ "${RM_OOM_COUNT}" == 0 ]]; then
        HOST_CLASS="PASS"
    else
        HOST_CLASS="FAIL"
    fi
fi
printf '%s\n' "${FUNCTIONAL_CLASS}" >"${OUT}/functional-class.txt"
printf '%s\n' "${HOST_CLASS}" >"${OUT}/host-stability-class.txt"

sudo -n chown -R "${RUN_USER}:${RUN_GROUP}" "${OUT}" 2>/dev/null || true

set +e
python3 "${ANALYZER}" "${OUT}" \
    >"${OUT}/ownership-analysis.txt" \
    2>"${OUT}/ownership-analysis.stderr"
ANALYZER_RC=$?
set -e
printf '%s\n' "${ANALYZER_RC}" >"${OUT}/ownership-analyzer.rc"
if [[ "${ANALYZER_RC}" != 0 ]]; then
    RUN_VALID=0
    printf '0\n' >"${OUT}/run-valid.txt"
    FUNCTIONAL_CLASS="INCOMPLETE"
    HOST_CLASS="INCOMPLETE"
    printf '%s\n' "${FUNCTIONAL_CLASS}" >"${OUT}/functional-class.txt"
    printf '%s\n' "${HOST_CLASS}" >"${OUT}/host-stability-class.txt"
fi

{
    printf 'run_valid=%s\n' "${RUN_VALID}"
    printf 'managed_rc=%s\n' "${MANAGED_RC}"
    printf 'collector_rc=%s\n' "${COLLECTOR_RC}"
    printf 'trace_rc=%s\n' "${TRACE_RC}"
    printf 'trace_report_rc=%s\n' "${REPORT_RC}"
    printf 'ownership_analyzer_rc=%s\n' "${ANALYZER_RC}"
    printf 'trace_window_valid=%s\n' "${TRACE_WINDOW_VALID}"
    printf 'restart_observed=%s\n' "${RESTART_OBSERVED}"
    printf 'release_stable=%s\n' "${RELEASE_STABLE}"
    printf 'api_ready=%s\n' "${API_READY}"
    printf 'functional_class=%s\n' "${FUNCTIONAL_CLASS}"
    printf 'host_stability_class=%s\n' "${HOST_CLASS}"
    printf 'predecessor_age_s=%s\n' "${PREDECESSOR_AGE_S}"
    printf 'minimum_predecessor_age_s=%s\n' "${MIN_PREDECESSOR_AGE_S}"
    printf 'trace_arm_delay_s=%s\n' "${TRACE_ARM_DELAY_S}"
    printf 'trace_duration_s=%s\n' "${TRACE_DURATION_S}"
    printf 'rm_oom_count=%s\n' "${RM_OOM_COUNT}"
    printf 'event_snapshot_count=%s\n' "${EVENT_SNAPSHOT_COUNT}"
} >"${OUT}/r23-summary.txt"

printf '\n===== R23 summary =====\n'
cat "${OUT}/r23-summary.txt"
printf '%s\n' '--- ownership analysis ---'
cat "${OUT}/ownership-analysis.txt" || true
printf '%s\n' '--- kernel errors ---'
cat "${OUT}/kernel-errors.txt" || true
printf 'evidence=%s\n' "${OUT}"

if [[ "${RUN_VALID}" != 1 ]]; then
    printf 'ORCA_R23_RESULT=INVALID\n'
    exit 1
fi
if [[ "${RM_OOM_COUNT}" == 0 ]]; then
    printf 'ORCA_R23_RESULT=VALID_CLEAN\n'
else
    printf 'ORCA_R23_RESULT=VALID_RM_OOM\n'
fi
