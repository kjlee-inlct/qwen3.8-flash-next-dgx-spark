#!/usr/bin/env bash
# Probe-only R9 preflight for the H6 16 GiB RM sysmem investigation.
#
# No model is started. This validates:
#   - full nv_alloc_pages policy-argument capture on aarch64;
#   - nv_alloc_system_pages entry/return probes;
#   - order-4 mm_page_alloc/mm_page_free filters;
#   - the retained compaction/reclaim/extfrag trace profile;
#   - current monitor CLI no longer using the historical swap-activity option.

set -Eeuo pipefail

RUN_USER="${SUDO_USER:-$(id -un)}"
RUN_HOME="$(getent passwd "$RUN_USER" | cut -d: -f6)"
FIXED_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

TRACEFS="/sys/kernel/tracing"
if [[ ! -e "$TRACEFS/kprobe_events" ]]; then
    TRACEFS="/sys/kernel/debug/tracing"
fi
KPROBE_EVENTS="$TRACEFS/kprobe_events"
GROUP="r9_rmsys"

PROBE_EVENTS=(
    "nv_alloc_pages_entry"
    "nv_alloc_pages_ret"
    "nv_alloc_system_pages_entry"
    "nv_alloc_system_pages_ret"
)

fail() {
    echo "R9_PREFLIGHT_ERROR: $*" >&2
    exit 2
}

require_sudo() {
    sudo -n true >/dev/null 2>&1 ||
        fail "sudo timestamp unavailable; run sudo -v first"
}

write_kprobe_commands() {
    local source_file="$1"

    sudo -n python3 - "$KPROBE_EVENTS" "$source_file" <<'PY'
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
    sudo -n python3 - "$TRACEFS" "$GROUP" <<'PY'
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
            f"DISABLE_FAIL path={target} errno={exc.errno} "
            f"message={exc.strerror}",
            file=sys.stderr,
        )
PY
}

cleanup_probes() {
    local tmp event
    tmp="$(mktemp /tmp/h6-r9-kprobe-cleanup.XXXXXX)"

    disable_probe_events || true
    for event in "${PROBE_EVENTS[@]}"; do
        printf '%s\n' "-:${GROUP}/${event}" >>"$tmp"
    done

    sudo -n python3 - "$KPROBE_EVENTS" "$tmp" <<'PY' >/dev/null 2>&1 || true
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
                f"cleanup failed for {command!r}: "
                f"errno={exc.errno} {exc.strerror}",
                file=sys.stderr,
            )
PY

    rm -f "$tmp"
}

create_probes() {
    local tmp
    cleanup_probes

    if sudo -n cat "$KPROBE_EVENTS" | grep -Fq "$GROUP/"; then
        fail "stale $GROUP probes remain after cleanup"
    fi

    tmp="$(mktemp /tmp/h6-r9-kprobe-create.XXXXXX)"
    cat >"$tmp" <<'EOF'
p:r9_rmsys/nv_alloc_pages_entry nv_alloc_pages page_count=$arg2:u32 page_size=$arg3:u64 contiguous=$arg4:u8 cache_type=$arg5:u32 zeroed=$arg6:u8 unencrypted=$arg7:u8 node_id=$arg8:s32
r:r9_rmsys/nv_alloc_pages_ret nv_alloc_pages ret=$retval:u32
p:r9_rmsys/nv_alloc_system_pages_entry nv_alloc_system_pages at=$arg2:u64
r:r9_rmsys/nv_alloc_system_pages_ret nv_alloc_system_pages ret=$retval:u32
EOF

    if ! write_kprobe_commands "$tmp"; then
        rm -f "$tmp"
        fail "failed to install R9 kprobe definitions"
    fi
    rm -f "$tmp"
}

verify_probes() {
    local event field format
    local fields=(
        page_count
        page_size
        contiguous
        cache_type
        zeroed
        unencrypted
        node_id
    )

    echo "=== active R9 kprobe definitions ==="
    sudo -n cat "$KPROBE_EVENTS" | grep -F "$GROUP/" || true
    echo

    for event in "${PROBE_EVENTS[@]}"; do
        format="$TRACEFS/events/$GROUP/$event/format"
        sudo -n cat "$format" >/dev/null 2>&1 ||
            fail "probe format unreadable: $format"
        echo "PRESENT $GROUP:$event"
    done

    format="$TRACEFS/events/$GROUP/nv_alloc_pages_entry/format"
    echo
    echo "=== nv_alloc_pages captured fields ==="
    sudo -n awk '
        /field:/ &&
        ($0 ~ /page_count/ || $0 ~ /page_size/ || $0 ~ /contiguous/ ||
         $0 ~ /cache_type/ || $0 ~ /zeroed/ || $0 ~ /unencrypted/ ||
         $0 ~ /node_id/) {print}
    ' "$format"

    for field in "${fields[@]}"; do
        sudo -n grep -Eq "field:.*[[:space:]]${field};" "$format" ||
            fail "nv_alloc_pages probe format missing captured field: $field"
    done
}

verify_static_events() {
    local path format
    local events=(
        "compaction/mm_compaction_try_to_compact_pages"
        "compaction/mm_compaction_begin"
        "compaction/mm_compaction_end"
        "vmscan/mm_vmscan_direct_reclaim_begin"
        "vmscan/mm_vmscan_direct_reclaim_end"
        "kmem/mm_page_alloc_extfrag"
        "kmem/mm_page_alloc"
        "kmem/mm_page_free"
    )

    echo
    echo "=== required static trace events ==="
    for path in "${events[@]}"; do
        format="$TRACEFS/events/$path/format"
        if sudo -n cat "$format" >/dev/null 2>&1; then
            echo "PRESENT $path"
        else
            echo "TRACE_EVENT_LOOKUP basename=${path##*/}" >&2
            sudo -n find "$TRACEFS/events" -maxdepth 2 -type d \
                -name "${path##*/}" -print 2>/dev/null >&2 || true
            fail "static trace event format unreadable or absent: $path"
        fi
    done
}

verify_monitor_cli() {
    local help
    help="$(bash scripts/runtime/monitor-runtime.sh --help)"

    echo
    echo "=== current monitor CLI ==="
    if grep -Fq -- '--swap-activity-gate-mib' <<<"$help"; then
        echo "legacy_swap_activity_gate=PRESENT"
    else
        echo "legacy_swap_activity_gate=ABSENT"
    fi

    for arg in \
        --container \
        --min-available-gib \
        --min-free-gib \
        --free-gate-gib \
        --min-swap-free-gib \
        --consecutive \
        --interval \
        --heartbeat \
        --protect
    do
        grep -Fq -- "$arg" <<<"$help" ||
            fail "current monitor CLI missing expected argument: $arg"
    done
}

smoke_trace() {
    local smoke_dir smoke log rc
    smoke_dir="$(mktemp -d /tmp/h6-r9-rmsys-smoke.XXXXXX)"
    smoke="$smoke_dir/trace.dat"
    log="$smoke_dir/trace-cmd.log"

    echo
    echo "=== R9 trace-cmd smoke ==="
    echo "smoke.dir=$smoke_dir"

    set +e
    sudo -n trace-cmd record \
        -C mono \
        -o "$smoke" \
        -e compaction:mm_compaction_try_to_compact_pages \
        -e compaction:mm_compaction_begin \
        -e compaction:mm_compaction_end \
        -e vmscan:mm_vmscan_direct_reclaim_begin \
        -e vmscan:mm_vmscan_direct_reclaim_end \
        -e kmem:mm_page_alloc_extfrag -f 'alloc_order >= 4' \
        -e kmem:mm_page_alloc -f 'order == 4' \
        -e kmem:mm_page_free -f 'order == 4' \
        -e "$GROUP:nv_alloc_pages_entry" \
        -e "$GROUP:nv_alloc_pages_ret" \
        -e "$GROUP:nv_alloc_system_pages_entry" \
        -e "$GROUP:nv_alloc_system_pages_ret" \
        --user "$RUN_USER" \
        -- env -i \
            HOME="$RUN_HOME" \
            USER="$RUN_USER" \
            LOGNAME="$RUN_USER" \
            PATH="$FIXED_PATH" \
            true 2>&1 | tee "$log"
    rc=${PIPESTATUS[0]}
    set -e

    echo "trace-cmd.smoke.rc=$rc"
    if [[ "$rc" != 0 ]]; then
        echo "R9_PREFLIGHT_SMOKE_DIR=$smoke_dir"
        fail "trace-cmd R9 smoke failed: rc=$rc"
    fi

    rm -rf "$smoke_dir"
}

require_sudo
[[ -e "$KPROBE_EVENTS" ]] || fail "kprobe_events unavailable"
trap cleanup_probes EXIT

verify_monitor_cli
create_probes
verify_probes
verify_static_events
smoke_trace

echo
echo "R9_RMSYS_PROBE_PREFLIGHT=PASS"
echo "tracefs=$TRACEFS"
echo "dynamic_probe_count=${#PROBE_EVENTS[@]}"
echo "order4_page_alloc_trace=YES"
echo "order4_page_free_trace=YES"
