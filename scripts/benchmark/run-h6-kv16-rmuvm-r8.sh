#!/usr/bin/env bash
# H6 16 GiB R8: R7 light allocator trace + narrow NVIDIA RM/UVM kretprobes.
#
# Modes:
#   --preflight   Create/validate/remove dynamic probes only. No model run.
#   (default)     Clone the preserved local R7 child, change only run identity
#                 (container/port/evidence labels), then execute under the same
#                 light Linux allocator trace plus four narrow RM/UVM probes.
#
# Requires:
#   sudo -v
#   /tmp/run-h6-kv16-trace-r7.sh
#
# This script never deletes prior experiment evidence.

set -Eeuo pipefail

MODE="${1:-run}"

R7_CHILD="/tmp/run-h6-kv16-trace-r7.sh"
R8_CHILD="/tmp/run-h6-kv16-rmuvm-r8.sh"

CTRL_NAME="qwen38-h6-kv16-rmuvm-r8"
CTRL_PORT=8903
CTRL_KV=17179869184
OUT="/tmp/hybrid-6.17-kv16-rmuvm-r8-20261001"

RUN_USER="${SUDO_USER:-$(id -un)}"
RUN_GROUP="$(id -gn "$RUN_USER")"
RUN_HOME="$(getent passwd "$RUN_USER" | cut -d: -f6)"
FIXED_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

TRACEFS="/sys/kernel/tracing"
if [[ ! -e "$TRACEFS/kprobe_events" ]]; then
    TRACEFS="/sys/kernel/debug/tracing"
fi
KPROBE_EVENTS="$TRACEFS/kprobe_events"
GROUP="r8_rmuvm"

PROBE_EVENTS=(
    "nv_alloc_pages_entry"
    "nv_alloc_pages_ret"
    "pma_alloc_entry"
    "pma_alloc_ret"
    "uvm_dma_alloc_entry"
    "uvm_dma_alloc_ret"
    "uvm_pmm_alloc_entry"
    "uvm_pmm_alloc_ret"
)

cleanup_probes() {
    local event
    for event in "${PROBE_EVENTS[@]}"; do
        printf '%s\n' "-:${GROUP}/${event}" |
            sudo -n tee "$KPROBE_EVENTS" >/dev/null 2>&1 || true
    done
}

die() {
    echo "R8_ERROR: $*" >&2
    exit 2
}

require_root_timestamp() {
    sudo -n true >/dev/null 2>&1 ||
        die "sudo timestamp unavailable; run sudo -v first"
}

add_probe() {
    local spec="$1"
    printf '%s\n' "$spec" | sudo -n tee "$KPROBE_EVENTS" >/dev/null
}

create_probes() {
    cleanup_probes

    add_probe 'p:r8_rmuvm/nv_alloc_pages_entry nv_alloc_pages page_count=$arg2:u32 page_size=$arg3:u64 contiguous=$arg4:u8'
    add_probe 'r:r8_rmuvm/nv_alloc_pages_ret nv_alloc_pages ret=$retval:u32'

    add_probe 'p:r8_rmuvm/pma_alloc_entry nvUvmInterfacePmaAllocPages page_count=$arg2:u64 page_size=$arg3:u64'
    add_probe 'r:r8_rmuvm/pma_alloc_ret nvUvmInterfacePmaAllocPages ret=$retval:u32'

    add_probe 'p:r8_rmuvm/uvm_dma_alloc_entry uvm_gpu_dma_alloc size=$arg1:u64 gfp=$arg3:u64'
    add_probe 'r:r8_rmuvm/uvm_dma_alloc_ret uvm_gpu_dma_alloc ret=$retval:u32'

    add_probe 'p:r8_rmuvm/uvm_pmm_alloc_entry uvm_pmm_gpu_alloc_kernel num_chunks=$arg2:u64 chunk_size=$arg3:u64 flags=$arg4:u32'
    add_probe 'r:r8_rmuvm/uvm_pmm_alloc_ret uvm_pmm_gpu_alloc_kernel ret=$retval:u32'
}

verify_probes() {
    local event format
    for event in "${PROBE_EVENTS[@]}"; do
        format="$TRACEFS/events/$GROUP/$event/format"
        sudo -n test -r "$format" || die "probe format unreadable: $format"
        echo "PRESENT $GROUP:$event"
    done
}

preflight() {
    require_root_timestamp
    [[ -e "$KPROBE_EVENTS" ]] || die "kprobe_events not available"

    trap cleanup_probes EXIT
    create_probes
    verify_probes

    local smoke
    smoke="$(mktemp /tmp/h6-r8-probe-smoke.XXXXXX.dat)"
    set +e
    sudo -n trace-cmd record \
        -C mono \
        -o "$smoke" \
        -e compaction:mm_compaction_try_to_compact_pages \
        -e vmscan:mm_vmscan_direct_reclaim_begin \
        -e kmem:mm_page_alloc_extfrag -f 'alloc_order >= 4' \
        -e nvidia:nvidia_dev_xid \
        -e "$GROUP:nv_alloc_pages_entry" \
        -e "$GROUP:nv_alloc_pages_ret" \
        -e "$GROUP:pma_alloc_entry" \
        -e "$GROUP:pma_alloc_ret" \
        -e "$GROUP:uvm_dma_alloc_entry" \
        -e "$GROUP:uvm_dma_alloc_ret" \
        -e "$GROUP:uvm_pmm_alloc_entry" \
        -e "$GROUP:uvm_pmm_alloc_ret" \
        --user "$RUN_USER" \
        -- env -i \
            HOME="$RUN_HOME" \
            USER="$RUN_USER" \
            LOGNAME="$RUN_USER" \
            PATH="$FIXED_PATH" \
            true >/dev/null 2>&1
    local smoke_rc=$?
    set -e
    rm -f "$smoke"
    [[ "$smoke_rc" == "0" ]] || die "trace-cmd probe smoke test failed: rc=$smoke_rc"

    echo
    echo "R8_PROBE_PREFLIGHT=PASS"
    echo "tracefs=$TRACEFS"
    echo "probe-count=${#PROBE_EVENTS[@]}"
}

if [[ "$MODE" == "--preflight" ]]; then
    preflight
    exit 0
fi

[[ "$MODE" == "run" ]] || die "usage: $0 [--preflight]"

require_root_timestamp
[[ -f "$R7_CHILD" ]] || die "missing preserved R7 child: $R7_CHILD"
[[ -e "$KPROBE_EVENTS" ]] || die "kprobe_events not available"

if [[ -e "$OUT" ]]; then
    die "evidence already exists: $OUT"
fi

if docker ps -a --format '{{.Names}}' | grep -Fxq "$CTRL_NAME"; then
    die "container already exists: $CTRL_NAME"
fi

if ss -ltnH 2>/dev/null | awk '{print $4}' | grep -Eq "[:.]$CTRL_PORT$"; then
    die "port already in use: $CTRL_PORT"
fi

# ----------------------------------------------------------------------
# Derive R8 child from the validated local R7 child.
# Do not reconstruct the model-control logic here.
# ----------------------------------------------------------------------

python3 - "$R7_CHILD" "$R8_CHILD" <<'PY'
from pathlib import Path
import sys

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
text = src.read_text()

replacements = {
    "qwen38-h6-kv16-trace-r7": "qwen38-h6-kv16-rmuvm-r8",
    "CTRL_PORT=8902": "CTRL_PORT=8903",
    "/tmp/hybrid-6.17-kv16-trace-r7-20261001":
        "/tmp/hybrid-6.17-kv16-rmuvm-r8-20261001",
    "KV16TR7_CHILD_RESULT": "KV16R8_CHILD_RESULT",
    "16 GiB TRACE R7": "16 GiB RM/UVM TRACE R8",
}

for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f"required R7 identity not found: {old}")
    text = text.replace(old, new)

for stale in (
    "qwen38-h6-kv16-trace-r7",
    "CTRL_PORT=8902",
    "/tmp/hybrid-6.17-kv16-trace-r7-20261001",
    "KV16TR7_CHILD_RESULT",
):
    if stale in text:
        raise SystemExit(f"stale R7 identity remains: {stale}")

if "CTRL_KV=17179869184" not in text:
    raise SystemExit("16 GiB KV identity missing after derivation")

dst.write_text(text)
dst.chmod(0o755)
PY

echo "============================================================"
echo "R8 CHILD IDENTITY"
echo "============================================================"
grep -E '^(CTRL_NAME|CTRL_PORT|CTRL_KV|OUT|POST_READY_SOAK)=' "$R8_CHILD" || true

grep -F 'CTRL_NAME="qwen38-h6-kv16-rmuvm-r8"' "$R8_CHILD" >/dev/null ||
    die "R8 container identity verification failed"
grep -F 'CTRL_PORT=8903' "$R8_CHILD" >/dev/null ||
    die "R8 port verification failed"
grep -F 'CTRL_KV=17179869184' "$R8_CHILD" >/dev/null ||
    die "R8 KV verification failed"
grep -F 'OUT="/tmp/hybrid-6.17-kv16-rmuvm-r8-20261001"' "$R8_CHILD" >/dev/null ||
    die "R8 evidence verification failed"

if grep -Eq '(^|[^[:alnum:]_])sudo([^[:alnum:]_]|$)' "$R8_CHILD"; then
    die "R8 child unexpectedly contains sudo"
fi

TMP="$(mktemp -d /tmp/h6-kv16-r8-outer.XXXXXX)"

SUDO_KEEPALIVE_PID=""

sudo_keepalive() {
    while sudo -n true >/dev/null 2>&1; do
        sleep 60
    done
}

cleanup_outer() {
    cleanup_probes

    if [[ -n "$SUDO_KEEPALIVE_PID" ]]; then
        kill "$SUDO_KEEPALIVE_PID" >/dev/null 2>&1 || true
        wait "$SUDO_KEEPALIVE_PID" 2>/dev/null || true
    fi

    echo "R8_OUTER_EVIDENCE_PRESERVED=$TMP"
}

trap cleanup_outer EXIT

sudo_keepalive &
SUDO_KEEPALIVE_PID=$!

START_EPOCH="$(date +%s.%N)"
printf '%s\n' "$START_EPOCH" >"$TMP/start-epoch.txt"

create_probes
verify_probes

echo
echo "============================================================"
echo "START H6 16 GiB RM/UVM TRACE R8"
echo "============================================================"
echo "container=$CTRL_NAME"
echo "port=$CTRL_PORT"
echo "kv=$CTRL_KV"
echo "outer_tmp=$TMP"
echo "probe_group=$GROUP"
echo

set +e
sudo -n trace-cmd record     -C mono     -o "$TMP/allocator-trace.dat"     -e compaction:mm_compaction_try_to_compact_pages     -e compaction:mm_compaction_begin     -e compaction:mm_compaction_end     -e vmscan:mm_vmscan_direct_reclaim_begin     -e vmscan:mm_vmscan_direct_reclaim_end     -e kmem:mm_page_alloc_extfrag -f 'alloc_order >= 4'     -e nvidia:nvidia_dev_xid     -e "$GROUP:nv_alloc_pages_entry"     -e "$GROUP:nv_alloc_pages_ret"     -e "$GROUP:pma_alloc_entry"     -e "$GROUP:pma_alloc_ret"     -e "$GROUP:uvm_dma_alloc_entry"     -e "$GROUP:uvm_dma_alloc_ret"     -e "$GROUP:uvm_pmm_alloc_entry"     -e "$GROUP:uvm_pmm_alloc_ret"     --user "$RUN_USER"     -- env -i         HOME="$RUN_HOME"         USER="$RUN_USER"         LOGNAME="$RUN_USER"         PATH="$FIXED_PATH"         bash "$R8_CHILD"     2>&1 | tee "$TMP/control.log"
TRACE_RC=${PIPESTATUS[0]}
set -e

END_EPOCH="$(date +%s.%N)"
printf '%s\n' "$END_EPOCH" >"$TMP/end-epoch.txt"
printf '%s\n' "$TRACE_RC" >"$TMP/trace-cmd.rc"

cleanup_probes

# The child normally creates OUT. Preserve outer evidence even on child failure.
if [[ ! -d "$OUT" ]]; then
    mkdir -p "$OUT"
    chown "$RUN_USER:$RUN_GROUP" "$OUT"
fi

sudo -n cp "$TMP/start-epoch.txt" "$OUT/start-epoch.txt"
sudo -n cp "$TMP/end-epoch.txt" "$OUT/end-epoch.txt"
sudo -n cp "$TMP/trace-cmd.rc" "$OUT/trace-cmd.rc"
sudo -n cp "$TMP/control.log" "$OUT/control.log"
sudo -n cp "$TMP/allocator-trace.dat" "$OUT/allocator-trace.dat"

sudo -n chown "$RUN_USER:$RUN_GROUP" \
    "$OUT/start-epoch.txt" \
    "$OUT/end-epoch.txt" \
    "$OUT/trace-cmd.rc" \
    "$OUT/control.log" \
    "$OUT/allocator-trace.dat"

sudo -n trace-cmd report -i "$OUT/allocator-trace.dat"     >"$OUT/allocator-trace.txt"

grep -E "$GROUP:" "$OUT/allocator-trace.txt"     >"$OUT/rm-uvm-probes.txt" || true

# ----------------------------------------------------------------------
# Recover the complete privileged kernel window using locale-independent
# whole-second timestamps.
# ----------------------------------------------------------------------

START_SEC="${START_EPOCH%%.*}"
END_SEC="${END_EPOCH%%.*}"
END_SEC="$((END_SEC + 2))"

START_JOURNAL="$(date -d "@$START_SEC" '+%Y-%m-%d %H:%M:%S')"
END_JOURNAL="$(date -d "@$END_SEC" '+%Y-%m-%d %H:%M:%S')"

sudo -n journalctl -k     --since "$START_JOURNAL"     --until "$END_JOURNAL"     -o short-iso-precise --no-pager     >"$OUT/kernel-window.txt"

sudo -n journalctl -k     --since "$START_JOURNAL"     --until "$END_JOURNAL"     -o short-monotonic --no-pager     >"$OUT/kernel-window-monotonic.txt"

ERROR_RE='NV_ERR_NO_MEMORY|_memdescAllocInternal|NVRM:.*Xid|Xid \(PCI|GPU has fallen off the bus|oom-kill:|Out of memory:|Killed process '

grep -Ei "$ERROR_RE" "$OUT/kernel-window.txt"     >"$OUT/kernel-errors.txt" || true
grep -Ei "$ERROR_RE" "$OUT/kernel-window-monotonic.txt"     >"$OUT/kernel-errors-monotonic.txt" || true

# ----------------------------------------------------------------------
# Compact probe summary and RM +/- windows.
# ----------------------------------------------------------------------

python3 - "$OUT" <<'PY'
from collections import Counter
from pathlib import Path
import re
import sys

out = Path(sys.argv[1])
trace = (out / "allocator-trace.txt").read_text(errors="replace")
probe_lines = [
    line for line in trace.splitlines()
    if "r8_rmuvm:" in line
]

events = Counter()
failures = []

for line in probe_lines:
    m = re.search(r"r8_rmuvm:([A-Za-z0-9_]+):", line)
    if m:
        events[m.group(1)] += 1
    if re.search(r"\bret=(?:81|0x0*51)\b", line, re.I):
        failures.append(line)

with (out / "probe-summary.txt").open("w") as f:
    f.write("=== R8 RM/UVM PROBE COUNTS ===\n")
    for name, count in sorted(events.items()):
        f.write(f"{name}={count}\n")
    f.write(f"NV_ERR_NO_MEMORY_RETURNS={len(failures)}\n")
    if failures:
        f.write("\n=== NV_ERR_NO_MEMORY RETURN EVENTS ===\n")
        for line in failures:
            f.write(line + "\n")

kernel_mono = (out / "kernel-errors-monotonic.txt").read_text(errors="replace")
rm = re.search(
    r"\[\s*(\d+(?:\.\d+)?)\].*(?:NV_ERR_NO_MEMORY|_memdescAllocInternal)",
    kernel_mono,
)

if not rm:
    (out / "rm-trace-window.txt").write_text("NO_RM_ERROR\n")
    (out / "rm-trace-window-10s.txt").write_text("NO_RM_ERROR\n")
    raise SystemExit

rm_ts = float(rm.group(1))
(out / "rm-first-monotonic.txt").write_text(f"rm_monotonic={rm_ts:.9f}\n")

line_re = re.compile(r"\s(\d+\.\d+):\s+\S+:")
rows = []
for line in trace.splitlines():
    m = line_re.search(line)
    if m:
        rows.append((float(m.group(1)), line))

for radius, name in (
    (3.0, "rm-trace-window.txt"),
    (10.0, "rm-trace-window-10s.txt"),
):
    selected = [
        line for ts, line in rows
        if rm_ts - radius <= ts <= rm_ts + radius
    ]
    (out / name).write_text(
        "\n".join(selected) + ("\n" if selected else "")
    )
PY

FUNCTIONAL_RESULT="FUNCTIONAL_FAIL"
if grep -Fq 'KV16R8_CHILD_RESULT=FUNCTIONAL_PASS' "$OUT/control.log"; then
    FUNCTIONAL_RESULT="FUNCTIONAL_PASS"
fi
printf '%s\n' "$FUNCTIONAL_RESULT" >"$OUT/functional.result"

HOST_RESULT="HOST_PASS"
if [[ -s "$OUT/kernel-errors.txt" ]]; then
    HOST_RESULT="HOST_FAIL"
fi
printf '%s\n' "$HOST_RESULT" >"$OUT/host.result"

CONTAINER_STATUS="missing"
CONTAINER_EXIT="NA"
CONTAINER_OOM="NA"

if docker inspect "$CTRL_NAME" >/dev/null 2>&1; then
    read -r CONTAINER_STATUS CONTAINER_EXIT CONTAINER_OOM < <(
        docker inspect             --format '{{.State.Status}} {{.State.ExitCode}} {{.State.OOMKilled}}'             "$CTRL_NAME"
    )
fi

FINAL_RESULT="FAIL"
if [[ "$FUNCTIONAL_RESULT" == "FUNCTIONAL_PASS" ]]; then
    if [[ "$HOST_RESULT" == "HOST_FAIL" ]]; then
        FINAL_RESULT="FUNCTIONAL_PASS_HOST_FAIL"
    elif [[ "$TRACE_RC" == "0" &&
            "$CONTAINER_STATUS" == "exited" &&
            "$CONTAINER_EXIT" == "0" &&
            "$CONTAINER_OOM" == "false" ]]; then
        FINAL_RESULT="PASS"
    else
        FINAL_RESULT="PARTIAL"
    fi
fi

{
    echo "============================================================"
    echo "R8 FINAL SUMMARY"
    echo "============================================================"
    echo "functional.result=$FUNCTIONAL_RESULT"
    echo "host.result=$HOST_RESULT"
    echo "trace-cmd.rc=$TRACE_RC"
    echo "container.status=$CONTAINER_STATUS"
    echo "container.exit=$CONTAINER_EXIT"
    echo "container.oomkilled=$CONTAINER_OOM"
    echo "kernel.errors=$([[ -s "$OUT/kernel-errors.txt" ]] && echo YES || echo NO)"
    echo "rm.error=$([[ -f "$OUT/rm-first-monotonic.txt" ]] && echo YES || echo NO)"
    echo "FINAL_RESULT=$FINAL_RESULT"
    echo "evidence=$OUT"
    echo
    cat "$OUT/probe-summary.txt"
} | tee "$OUT/final-summary.txt"
