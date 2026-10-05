#!/usr/bin/env bash
# H6 16 GiB R9: narrow RM sysmem trace derived from the validated R7 child.
#
# Requires:
#   sudo -v
#   /tmp/run-h6-kv16-trace-r7.sh
#
# R9 purpose:
#   - capture the full nv_alloc_pages policy inputs;
#   - capture nv_alloc_system_pages entry/return;
#   - count Linux order-4 page alloc/free events;
#   - retain the R6/R7/R8 light compaction/reclaim/extfrag profile;
#   - preserve functional and host-stability classification separately.
#
# This runner never deletes prior experiment evidence and never stops on the
# first RM error. The child is allowed to continue to READY/soak/clean stop.

set -Eeuo pipefail

R7_CHILD="/tmp/run-h6-kv16-trace-r7.sh"
R9_CHILD="/tmp/run-h6-kv16-rmsys-r9.sh"
CTRL_NAME="qwen38-h6-kv16-rmsys-r9"
CTRL_PORT=8904
CTRL_KV=17179869184
OUT="/tmp/hybrid-6.17-kv16-rmsys-r9-20261002"

RUN_USER="${SUDO_USER:-$(id -un)}"
RUN_GROUP="$(id -gn "$RUN_USER")"
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
    echo "R9_ERROR: $*" >&2
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
                f"cleanup failed: {command!r}: "
                f"errno={exc.errno} {exc.strerror}",
                file=sys.stderr,
            )
PY

    rm -f "$tmp"
}

create_probes() {
    local tmp event format

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
    write_kprobe_commands "$tmp" || {
        rm -f "$tmp"
        fail "failed to install R9 dynamic probes"
    }
    rm -f "$tmp"

    for event in "${PROBE_EVENTS[@]}"; do
        format="$TRACEFS/events/$GROUP/$event/format"
        sudo -n cat "$format" >/dev/null 2>&1 ||
            fail "probe event not materialized: $GROUP:$event"
    done
}

prepare_child() {
    [[ -f "$R7_CHILD" ]] || fail "missing preserved R7 child: $R7_CHILD"

    python3 - "$R7_CHILD" "$R9_CHILD" <<'PY'
from pathlib import Path
import re
import sys

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
text = src.read_text()

replacements = {
    "qwen38-h6-kv16-trace-r7": "qwen38-h6-kv16-rmsys-r9",
    "CTRL_PORT=8902": "CTRL_PORT=8904",
    "/tmp/hybrid-6.17-kv16-trace-r7-20261001":
        "/tmp/hybrid-6.17-kv16-rmsys-r9-20261002",
    "KV16TR7_CHILD_RESULT": "KV16R9_CHILD_RESULT",
    "16 GiB TRACE R7": "16 GiB RM SYS TRACE R9",
}

for old, new in replacements.items():
    if old not in text:
        raise SystemExit(f"required R7 identity not found: {old}")
    text = text.replace(old, new)

# R8 proved this historical option is no longer accepted by the current
# monitor CLI. Remove only that option/value line or inline pair.
text = re.sub(
    r"(?m)^[ \t]*--swap-activity-gate-mib[ \t]+[^ \\n]+[ \t]*\\?[ \t]*\n",
    "",
    text,
)
text = re.sub(
    r"[ \t]+--swap-activity-gate-mib[ \t]+[^ \\n]+",
    "",
    text,
)

if "--swap-activity-gate-mib" in text:
    raise SystemExit("stale monitor option remains in R9 child")
if "CTRL_KV=17179869184" not in text:
    raise SystemExit("16 GiB KV identity missing after derivation")

for stale in (
    "qwen38-h6-kv16-trace-r7",
    "CTRL_PORT=8902",
    "/tmp/hybrid-6.17-kv16-trace-r7-20261001",
    "KV16TR7_CHILD_RESULT",
):
    if stale in text:
        raise SystemExit(f"stale R7 identity remains: {stale}")

dst.write_text(text)
dst.chmod(0o755)
PY

    grep -F 'CTRL_NAME="qwen38-h6-kv16-rmsys-r9"' "$R9_CHILD" >/dev/null ||
        fail "R9 container identity verification failed"
    grep -F 'CTRL_PORT=8904' "$R9_CHILD" >/dev/null ||
        fail "R9 port verification failed"
    grep -F 'CTRL_KV=17179869184' "$R9_CHILD" >/dev/null ||
        fail "R9 KV verification failed"
    grep -F 'OUT="/tmp/hybrid-6.17-kv16-rmsys-r9-20261002"' "$R9_CHILD" >/dev/null ||
        fail "R9 evidence verification failed"

    if grep -Eq '(^|[^[:alnum:]_])sudo([^[:alnum:]_]|$)' "$R9_CHILD"; then
        fail "R9 child unexpectedly contains sudo"
    fi
}

require_sudo
[[ -e "$KPROBE_EVENTS" ]] || fail "kprobe_events unavailable"
[[ ! -e "$OUT" ]] || fail "evidence already exists: $OUT"

if docker ps -a --format '{{.Names}}' | grep -Fxq "$CTRL_NAME"; then
    fail "container already exists: $CTRL_NAME"
fi
if ss -ltnH 2>/dev/null | awk '{print $4}' | grep -Eq "[:.]${CTRL_PORT}$"; then
    fail "port already in use: $CTRL_PORT"
fi

prepare_child
create_probes

TMP="$(mktemp -d /tmp/h6-kv16-r9-outer.XXXXXX)"
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
    echo "R9_OUTER_EVIDENCE_PRESERVED=$TMP"
}
trap cleanup_outer EXIT

sudo_keepalive &
SUDO_KEEPALIVE_PID=$!

START_EPOCH="$(date +%s.%N)"
printf '%s\n' "$START_EPOCH" >"$TMP/start-epoch.txt"

echo "============================================================"
echo "START H6 16 GiB RM SYS TRACE R9"
echo "============================================================"
echo "container=$CTRL_NAME"
echo "port=$CTRL_PORT"
echo "kv=$CTRL_KV"
echo "outer_tmp=$TMP"
echo "probe_group=$GROUP"
echo

set +e
sudo -n trace-cmd record \
    -C mono \
    -o "$TMP/allocator-trace.dat" \
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
        bash "$R9_CHILD" \
    2>&1 | tee "$TMP/control.log"
TRACE_RC=${PIPESTATUS[0]}
set -e

END_EPOCH="$(date +%s.%N)"
printf '%s\n' "$END_EPOCH" >"$TMP/end-epoch.txt"
printf '%s\n' "$TRACE_RC" >"$TMP/trace-cmd.rc"
cleanup_probes

if [[ ! -d "$OUT" ]]; then
    mkdir -p "$OUT"
    chown "$RUN_USER:$RUN_GROUP" "$OUT"
fi

for name in start-epoch.txt end-epoch.txt trace-cmd.rc control.log allocator-trace.dat; do
    sudo -n cp "$TMP/$name" "$OUT/$name"
    sudo -n chown "$RUN_USER:$RUN_GROUP" "$OUT/$name"
done

sudo -n trace-cmd report -i "$OUT/allocator-trace.dat" >"$OUT/allocator-trace.txt"

START_SEC="${START_EPOCH%%.*}"
END_SEC="${END_EPOCH%%.*}"
END_SEC="$((END_SEC + 2))"
START_JOURNAL="$(date -d "@$START_SEC" '+%Y-%m-%d %H:%M:%S')"
END_JOURNAL="$(date -d "@$END_SEC" '+%Y-%m-%d %H:%M:%S')"

sudo -n journalctl -k \
    --since "$START_JOURNAL" \
    --until "$END_JOURNAL" \
    -o short-iso-precise --no-pager \
    >"$OUT/kernel-window.txt"

sudo -n journalctl -k \
    --since "$START_JOURNAL" \
    --until "$END_JOURNAL" \
    -o short-monotonic --no-pager \
    >"$OUT/kernel-window-monotonic.txt"

ERROR_RE='NV_ERR_NO_MEMORY|_memdescAllocInternal|NVRM:.*Xid|Xid \(PCI|GPU has fallen off the bus|oom-kill:|Out of memory:|Killed process '
grep -Ei "$ERROR_RE" "$OUT/kernel-window.txt" >"$OUT/kernel-errors.txt" || true
grep -Ei "$ERROR_RE" "$OUT/kernel-window-monotonic.txt" >"$OUT/kernel-errors-monotonic.txt" || true

python3 - "$OUT" <<'PY'
from collections import Counter
from pathlib import Path
import re
import sys

out = Path(sys.argv[1])
trace = (out / "allocator-trace.txt").read_text(errors="replace").splitlines()
kernel = (out / "kernel-errors-monotonic.txt").read_text(errors="replace").splitlines()

names = (
    "nv_alloc_pages_entry",
    "nv_alloc_pages_ret",
    "nv_alloc_system_pages_entry",
    "nv_alloc_system_pages_ret",
    "mm_page_alloc",
    "mm_page_free",
    "mm_page_alloc_extfrag",
    "mm_compaction_try_to_compact_pages",
    "mm_vmscan_direct_reclaim_begin",
)
counts = Counter()
ret_status = Counter()
rm_ts = None

for line in kernel:
    if "NV_ERR_NO_MEMORY" in line or "_memdescAllocInternal" in line:
        match = re.search(r"\[\s*([0-9]+(?:\.[0-9]+)?)\]", line)
        if match:
            rm_ts = float(match.group(1))
            break

for line in trace:
    for name in names:
        if re.search(rf"\b{re.escape(name)}:\s", line):
            counts[name] += 1
    if re.search(r"\bnv_alloc_pages_ret:\s", line):
        match = re.search(r"\bret=(?:0x)?([0-9a-fA-F]+)\b", line)
        if match:
            token = match.group(1)
            value = int(token, 16) if any(c in "abcdefABCDEF" for c in token) else int(token)
            ret_status[value] += 1
    if re.search(r"\bnv_alloc_system_pages_ret:\s", line):
        match = re.search(r"\bret=(?:0x)?([0-9a-fA-F]+)\b", line)
        if match:
            token = match.group(1)
            value = int(token, 16) if any(c in "abcdefABCDEF" for c in token) else int(token)
            ret_status[("sys", value)] += 1

summary = []
summary.append("=== R9 OUTER TRACE SUMMARY ===")
summary.append(f"trace_lines={len(trace)}")
summary.append(f"rm_monotonic={rm_ts if rm_ts is not None else 'NONE'}")
for name in names:
    summary.append(f"{name}={counts[name]}")
summary.append(f"nv_alloc_pages_nv_oom_returns={ret_status[81]}")
summary.append(f"nv_alloc_system_pages_nv_oom_returns={ret_status[(\"sys\", 81)]}")

window = []
if rm_ts is not None:
    ts_re = re.compile(r"\s([0-9]+(?:\.[0-9]+)):\s")
    for line in trace:
        match = ts_re.search(line)
        if not match:
            continue
        ts = float(match.group(1))
        if abs(ts - rm_ts) <= 3.0:
            if any(re.search(rf"\b{re.escape(name)}:\s", line) for name in names):
                window.append(line)

(out / "r9-probe-summary.txt").write_text("\n".join(summary) + "\n")
(out / "rm-r9-window.txt").write_text("\n".join(window) + ("\n" if window else ""))
print("\n".join(summary))
PY

echo
echo "=== R9 HOST CLASSIFICATION INPUTS ==="
echo "trace-cmd.rc=$TRACE_RC"
if [[ -s "$OUT/kernel-errors.txt" ]]; then
    echo "kernel.errors=YES"
else
    echo "kernel.errors=NO"
fi
if grep -Eq 'NV_ERR_NO_MEMORY|_memdescAllocInternal' "$OUT/kernel-errors.txt"; then
    echo "rm.error=YES"
else
    echo "rm.error=NO"
fi

if [[ -f "$OUT/final-summary.txt" ]]; then
    echo
    echo "=== CHILD FINAL SUMMARY ==="
    cat "$OUT/final-summary.txt"
fi

echo
echo "R9_EVIDENCE=$OUT"
echo "R9_TRACE_RC=$TRACE_RC"
