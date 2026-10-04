#!/usr/bin/env bash
# Probe-only preflight for OrcaRouter R23 early-burst ownership tracing.
#
# No model is started or stopped. No persistent VM setting is changed.
# The script only validates the selected RM/UVM targets, creates the narrow
# dynamic probes, smoke-records them, verifies their formats, then removes them.

set -Eeuo pipefail

OUT="${1:-/tmp/orcarouter-r23-ownership-probe-preflight-$(date +%Y%m%d-%H%M%S)}"
GROUP="r23_own"
RUN_USER="${SUDO_USER:-$(id -un)}"
RUN_HOME="$(getent passwd "${RUN_USER}" | cut -d: -f6)"
FIXED_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

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
    printf 'R23_PROBE_PREFLIGHT_ERROR: %s\n' "$*" >&2
    exit 2
}

require_commands() {
    local command
    for command in sudo python3 trace-cmd grep awk cat find mktemp mkdir date getent id env; do
        command -v "${command}" >/dev/null 2>&1 || fail "required command not found: ${command}"
    done
}

require_sudo() {
    sudo -n true >/dev/null 2>&1 ||
        fail "sudo timestamp unavailable; run sudo -v first"
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
    expected = len(command) + 1
    if written != expected:
        raise SystemExit(
            f"short kprobe control write: {written}/{expected}: "
            f"{command.decode(errors='replace')}"
        )
PY
}

disable_probe_events() {
    sudo -n python3 - "${TRACEFS}" "${GROUP}" <<'PY'
import os
import pathlib
import sys

tracefs = pathlib.Path(sys.argv[1])
group = sys.argv[2]
group_dir = tracefs / "events" / group

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
source = pathlib.Path(sys.argv[2])

for raw in source.read_bytes().splitlines():
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
                f"cleanup failed for {command!r}: errno={exc.errno} {exc.strerror}",
                file=sys.stderr,
            )
PY

    rm -f -- "${tmp}"
}

verify_target_presence() {
    local aff="$1"
    local item fn module

    : >"${OUT}/targets.txt"
    for item in "${TARGETS[@]}"; do
        IFS=: read -r fn module <<<"${item}"
        if grep -Eq "^${fn}([[:space:]].*)?[[:space:]]\\[${module}\\]$" "${aff}"; then
            printf 'PRESENT function=%s module=%s\n' "${fn}" "${module}" | tee -a "${OUT}/targets.txt"
        else
            printf 'MISSING function=%s module=%s\n' "${fn}" "${module}" | tee -a "${OUT}/targets.txt"
            fail "required R23 probe target is not ftrace-visible: ${fn} [${module}]"
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

    write_kprobe_commands "${definitions}" || fail "failed to install R23 dynamic probes"
}

verify_probe_formats() {
    local event format field
    local nv_fields=(page_count page_size contiguous cache_type zeroed unencrypted node_id)

    : >"${OUT}/formats.txt"
    for event in "${PROBE_EVENTS[@]}"; do
        format="${TRACEFS}/events/${GROUP}/${event}/format"
        sudo -n cat "${format}" >/dev/null 2>&1 || fail "probe format unreadable: ${format}"
        printf 'PRESENT %s:%s\n' "${GROUP}" "${event}" | tee -a "${OUT}/formats.txt"
    done

    format="${TRACEFS}/events/${GROUP}/nv_alloc_pages_entry/format"
    for field in "${nv_fields[@]}"; do
        sudo -n grep -Eq "field:.*[[:space:]]${field};" "${format}" ||
            fail "nv_alloc_pages probe format missing captured field: ${field}"
    done

    format="${TRACEFS}/events/${GROUP}/uvm_mem_alloc_ret/format"
    sudo -n grep -Eq 'field:.*[[:space:]]raw_ret;' "${format}" ||
        fail "uvm_mem_alloc return probe is missing raw_ret"
}

smoke_record() {
    local trace="${OUT}/smoke-trace.dat"
    local log="${OUT}/smoke-trace-cmd.log"
    local args=()
    local event

    for event in "${PROBE_EVENTS[@]}"; do
        args+=( -e "${GROUP}:${event}" )
    done

    set +e
    sudo -n trace-cmd record \
        --verbose=debug \
        -C mono \
        -o "${trace}" \
        "${args[@]}" \
        --user "${RUN_USER}" \
        -- env -i \
            HOME="${RUN_HOME}" \
            USER="${RUN_USER}" \
            LOGNAME="${RUN_USER}" \
            PATH="${FIXED_PATH}" \
            true \
        >"${log}" 2>&1
    local rc=$?
    set -e

    printf '%s\n' "${rc}" >"${OUT}/smoke-trace-cmd.rc"
    [[ "${rc}" == 0 ]] || fail "trace-cmd dynamic-probe smoke test failed; see ${log}"
}

main() {
    require_commands
    require_sudo
    [[ -e "${KPROBE_EVENTS}" ]] || fail "kprobe_events not available under ${TRACEFS}"
    [[ ! -e "${OUT}" ]] || fail "preflight evidence already exists: ${OUT}"

    mkdir -p -- "${OUT}"
    trap cleanup_probes EXIT INT TERM

    local aff="${OUT}/available-filter-functions.txt"
    sudo -n cat "${TRACEFS}/available_filter_functions" >"${aff}"

    verify_target_presence "${aff}"
    create_probes
    verify_probe_formats
    smoke_record

    cleanup_probes
    trap - EXIT INT TERM

    if sudo -n cat "${KPROBE_EVENTS}" | grep -Fq "${GROUP}/"; then
        fail "stale ${GROUP} probes remain after successful preflight"
    fi

    {
        printf 'R23_PROBE_PREFLIGHT=PASS\n'
        printf 'tracefs=%s\n' "${TRACEFS}"
        printf 'probe_group=%s\n' "${GROUP}"
        printf 'target_count=%s\n' "${#TARGETS[@]}"
        printf 'event_count=%s\n' "${#PROBE_EVENTS[@]}"
        printf 'model_restart=NO\n'
        printf 'persistent_vm_tuning=NO\n'
        printf 'evidence=%s\n' "${OUT}"
    } | tee "${OUT}/summary.txt"
}

main "$@"
