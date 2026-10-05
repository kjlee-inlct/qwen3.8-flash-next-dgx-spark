#!/usr/bin/env bash
# Corrected managed OrcaRouter RM-sysmem trace after the invalid R10 child-env run.
#
# R10b fixes two experiment-validity problems:
#   - run the traced child under an explicit clean environment with a known PATH;
#   - record the managed child exit code independently of trace-cmd's exit code.
#
# The currently healthy managed OrcaRouter runtime is restarted exactly once through
# the normal managed service entry point. Existing R10 evidence is never overwritten.

set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"
CURRENT_LINK="${DATA_HOME}/current"
STATE_FILE="${STATE_HOME}/install.env"
UNIT="qwen38-flash-next.service"
CONTAINER="qwen38-flash-next"
OUT="${ORCA_R10B_OUT:-/tmp/orcarouter-managed-rmsys-r10b-20261003}"
ANALYZER="${SCRIPT_ROOT}/scripts/benchmark/analyze-h6-r9-rmsys.py"
RELEASE_MANAGER="${SCRIPT_ROOT}/scripts/release-manager.sh"
UPDATE_TRANSITION="${SCRIPT_ROOT}/scripts/update-transition.sh"
RUNTIME_TRANSITION="${SCRIPT_ROOT}/scripts/runtime-transition.sh"
PROFILE_TRANSITION="${SCRIPT_ROOT}/scripts/profile-switch-transition.sh"

RUN_USER="${SUDO_USER:-$(id -un)}"
RUN_GROUP="$(id -gn "${RUN_USER}")"
RUN_HOME="$(getent passwd "${RUN_USER}" | cut -d: -f6)"
FIXED_PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

TRACEFS="/sys/kernel/tracing"
if [[ ! -e "${TRACEFS}/kprobe_events" ]]; then
    TRACEFS="/sys/kernel/debug/tracing"
fi
KPROBE_EVENTS="${TRACEFS}/kprobe_events"
GROUP="r10b_orca_rmsys"
PROBE_EVENTS=(
    "nv_alloc_pages_entry"
    "nv_alloc_pages_ret"
    "nv_alloc_system_pages_entry"
    "nv_alloc_system_pages_ret"
)

SUDO_KEEPALIVE_PID=""
TRACE_ACTIVE=0

fail() {
    printf 'ORCA_R10B_ERROR: %s\n' "$*" >&2
    exit 2
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || fail "required command not found: $1"
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
    if written != len(command) + 1:
        raise SystemExit(f"short kprobe control write: {written}/{len(command) + 1}")
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
paths = [group_dir / "enable"]
if group_dir.is_dir():
    paths.extend(sorted(group_dir.glob("*/enable")))
for path in paths:
    if not path.exists():
        continue
    try:
        fd = os.open(path, os.O_WRONLY)
        try:
            os.write(fd, b"0\n")
        finally:
            os.close(fd)
    except OSError as exc:
        print(f"DISABLE_FAIL path={path} errno={exc.errno} message={exc.strerror}", file=sys.stderr)
PY
}

cleanup_probes() {
    local tmp event
    tmp="$(mktemp /tmp/orca-r10b-kprobe-cleanup.XXXXXX)"
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
            print(f"cleanup failed: {command!r}: errno={exc.errno} {exc.strerror}", file=sys.stderr)
PY
    rm -f -- "${tmp}"
}

create_probes() {
    local tmp event format
    cleanup_probes
    if sudo -n cat "${KPROBE_EVENTS}" | grep -Fq "${GROUP}/"; then
        fail "stale ${GROUP} probes remain after cleanup"
    fi

    tmp="$(mktemp /tmp/orca-r10b-kprobe-create.XXXXXX)"
    cat >"${tmp}" <<'EOF'
p:r10b_orca_rmsys/nv_alloc_pages_entry nv_alloc_pages page_count=$arg2:u32 page_size=$arg3:u64 contiguous=$arg4:u8 cache_type=$arg5:u32 zeroed=$arg6:u8 unencrypted=$arg7:u8 node_id=$arg8:s32
r:r10b_orca_rmsys/nv_alloc_pages_ret nv_alloc_pages ret=$retval:u32
p:r10b_orca_rmsys/nv_alloc_system_pages_entry nv_alloc_system_pages at=$arg2:u64
r:r10b_orca_rmsys/nv_alloc_system_pages_ret nv_alloc_system_pages ret=$retval:u32
EOF
    write_kprobe_commands "${tmp}" || {
        rm -f -- "${tmp}"
        fail "failed to install R10b dynamic probes"
    }
    rm -f -- "${tmp}"

    for event in "${PROBE_EVENTS[@]}"; do
        format="${TRACEFS}/events/${GROUP}/${event}/format"
        sudo -n cat "${format}" >/dev/null 2>&1 ||
            fail "probe event not materialized: ${GROUP}:${event}"
    done
}

sudo_keepalive() {
    while sudo -n true >/dev/null 2>&1; do
        sleep 60
    done
}

cleanup() {
    local rc=$?
    trap - EXIT INT TERM
    set +e
    cleanup_probes
    if [[ -n "${SUDO_KEEPALIVE_PID}" ]]; then
        kill "${SUDO_KEEPALIVE_PID}" >/dev/null 2>&1 || true
        wait "${SUDO_KEEPALIVE_PID}" 2>/dev/null || true
    fi
    if [[ "${TRACE_ACTIVE}" == 1 ]]; then
        echo "WARNING: trace-cmd child may still be active; inspect processes before retrying." >&2
    fi
    exit "${rc}"
}
trap cleanup EXIT INT TERM

for command in sudo trace-cmd docker curl systemctl journalctl python3 grep awk getent date tee stat; do
    require_command "${command}"
done
require_sudo
[[ -e "${KPROBE_EVENTS}" ]] || fail "kprobe_events unavailable"
[[ -r "${STATE_FILE}" ]] || fail "installation state missing: ${STATE_FILE}"
[[ -x "${ANALYZER}" ]] || fail "R9 analyzer unavailable: ${ANALYZER}"
[[ -L "${CURRENT_LINK}" ]] || fail "immutable current release link missing: ${CURRENT_LINK}"
[[ ! -e "${OUT}" ]] || fail "evidence already exists: ${OUT}"

grep -qx 'MODEL_PROFILE=orcarouter' "${STATE_FILE}" ||
    fail "managed profile is not OrcaRouter"
[[ ! -e /run/systemd/system/qwen38-flash-next.service.d/kv16-ab.conf ]] ||
    fail "temporary KV override is still present"

CURRENT_RELEASE="$(bash "${RELEASE_MANAGER}" status | awk -F= '$1=="CURRENT_RELEASE" {print $2}')"
[[ -n "${CURRENT_RELEASE}" && "${CURRENT_RELEASE}" != none ]] || fail "no immutable current release"
MANAGE_SERVICE="${CURRENT_LINK}/scripts/manage-service.sh"
SERVE="${CURRENT_LINK}/scripts/serve.sh"
[[ -x "${MANAGE_SERVICE}" ]] || fail "managed service helper missing from current release"
[[ -r "${SERVE}" ]] || fail "serve helper missing from current release"
ORCA_BLOCK="$(awk '/^  orcarouter\)/,/^  nvidia\)/' "${SERVE}")"
grep -Fq 'DEFAULT_KV_MEM=17179869184' <<<"${ORCA_BLOCK}" ||
    fail "current immutable release does not default OrcaRouter to 16 GiB"

grep -qx 'UPDATE_STATE=idle' < <(bash "${UPDATE_TRANSITION}" status) || fail "update transition is not idle"
grep -qx 'TRANSACTION_STATE=idle' < <(bash "${RUNTIME_TRANSITION}" status) || fail "runtime transition is not idle"
grep -qx 'PROFILE_SWITCH_STATE=idle' < <(bash "${PROFILE_TRANSITION}" status) || fail "profile-switch transition is not idle"
systemctl is-active --quiet "${UNIT}" || fail "managed service is not active"
curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null || fail "managed API is not healthy before trace restart"

PRE_CONTAINER_ID="$(docker inspect --format '{{.Id}}' "${CONTAINER}" 2>/dev/null || true)"
PRE_CONTAINER_STARTED="$(docker inspect --format '{{.State.StartedAt}}' "${CONTAINER}" 2>/dev/null || true)"
[[ -n "${PRE_CONTAINER_ID}" ]] || fail "managed container missing before trace restart"

mkdir -p -- "${OUT}"
printf '%s\n' "${CURRENT_RELEASE}" >"${OUT}/release-before.txt"
printf '%s\n' "${PRE_CONTAINER_ID}" >"${OUT}/container-id-before.txt"
printf '%s\n' "${PRE_CONTAINER_STARTED}" >"${OUT}/container-started-before.txt"
START_ISO="$(date --iso-8601=seconds)"
START_EPOCH="$(date +%s.%N)"
printf '%s\n' "${START_ISO}" >"${OUT}/start-iso.txt"
printf '%s\n' "${START_EPOCH}" >"${OUT}/start-epoch.txt"

CHILD_WRAPPER="${OUT}/managed-child.sh"
CHILD_RC_FILE="${OUT}/managed-command.rc"
CHILD_STARTED_FILE="${OUT}/managed-child-started.txt"
cat >"${CHILD_WRAPPER}" <<'EOF'
#!/usr/bin/env bash
set +e
manage_service="$1"
current_link="$2"
rc_file="$3"
started_file="$4"
printf '%s\n' "$(date --iso-8601=seconds)" >"${started_file}"
/bin/bash "${manage_service}" create --runtime-root "${current_link}" --start --yes
rc=$?
printf '%s\n' "${rc}" >"${rc_file}"
exit "${rc}"
EOF
chmod 0700 "${CHILD_WRAPPER}"

create_probes
sudo_keepalive &
SUDO_KEEPALIVE_PID=$!

echo "============================================================"
echo "START ORCAROUTER MANAGED RM SYS TRACE R10b"
echo "============================================================"
echo "current_release=${CURRENT_RELEASE}"
echo "output=${OUT}"
echo "probe_group=${GROUP}"
echo "kv_default_bytes=17179869184"
echo "pre_container_id=${PRE_CONTAINER_ID}"
echo

set +e
TRACE_ACTIVE=1
sudo -n trace-cmd record \
    -C mono \
    -o "${OUT}/allocator-trace.dat" \
    -e compaction:mm_compaction_try_to_compact_pages \
    -e compaction:mm_compaction_begin \
    -e compaction:mm_compaction_end \
    -e vmscan:mm_vmscan_direct_reclaim_begin \
    -e vmscan:mm_vmscan_direct_reclaim_end \
    -e kmem:mm_page_alloc_extfrag -f 'alloc_order >= 4' \
    -e kmem:mm_page_alloc -f 'order == 4' \
    -e kmem:mm_page_free -f 'order == 4' \
    -e "${GROUP}:nv_alloc_pages_entry" \
    -e "${GROUP}:nv_alloc_pages_ret" \
    -e "${GROUP}:nv_alloc_system_pages_entry" \
    -e "${GROUP}:nv_alloc_system_pages_ret" \
    -- /usr/bin/env -i \
        HOME="${RUN_HOME}" \
        USER="${RUN_USER}" \
        LOGNAME="${RUN_USER}" \
        SUDO_USER="${RUN_USER}" \
        PATH="${FIXED_PATH}" \
        /bin/bash "${CHILD_WRAPPER}" \
            "${MANAGE_SERVICE}" \
            "${CURRENT_LINK}" \
            "${CHILD_RC_FILE}" \
            "${CHILD_STARTED_FILE}" \
    2>&1 | tee "${OUT}/control.log"
TRACE_RC=${PIPESTATUS[0]}
TRACE_ACTIVE=0
set -e
printf '%s\n' "${TRACE_RC}" >"${OUT}/trace-cmd.rc"

if [[ -r "${CHILD_RC_FILE}" ]]; then
    MANAGED_RC="$(<"${CHILD_RC_FILE}")"
else
    MANAGED_RC=125
    printf '%s\n' "${MANAGED_RC}" >"${CHILD_RC_FILE}"
fi

END_ISO="$(date --iso-8601=seconds)"
END_EPOCH="$(date +%s.%N)"
printf '%s\n' "${END_ISO}" >"${OUT}/end-iso.txt"
printf '%s\n' "${END_EPOCH}" >"${OUT}/end-epoch.txt"
cleanup_probes

sudo -n trace-cmd report -i "${OUT}/allocator-trace.dat" >"${OUT}/allocator-trace.txt" 2>"${OUT}/trace-report.stderr" || true

START_SEC="${START_EPOCH%%.*}"
END_SEC="$(( ${END_EPOCH%%.*} + 2 ))"
START_JOURNAL="$(date -d "@${START_SEC}" '+%Y-%m-%d %H:%M:%S')"
END_JOURNAL="$(date -d "@${END_SEC}" '+%Y-%m-%d %H:%M:%S')"

sudo -n journalctl -k --since "${START_JOURNAL}" --until "${END_JOURNAL}" -o short-iso-precise --no-pager >"${OUT}/kernel-window.txt"
sudo -n journalctl -k --since "${START_JOURNAL}" --until "${END_JOURNAL}" -o short-monotonic --no-pager >"${OUT}/kernel-window-monotonic.txt"
ERROR_RE='NV_ERR_NO_MEMORY|_memdescAllocInternal|NVRM:.*Xid|Xid \(PCI|GPU has fallen off the bus|oom-kill:|Out of memory:|Killed process '
grep -Ei "${ERROR_RE}" "${OUT}/kernel-window.txt" >"${OUT}/kernel-errors.txt" || true
grep -Ei "${ERROR_RE}" "${OUT}/kernel-window-monotonic.txt" >"${OUT}/kernel-errors-monotonic.txt" || true
sudo -n journalctl -u "${UNIT}" --since "${START_JOURNAL}" --until "${END_JOURNAL}" -o short-iso-precise --no-pager >"${OUT}/service-window.txt"
docker logs --timestamps --since "${START_ISO}" "${CONTAINER}" >"${OUT}/container-window.txt" 2>&1 || true

docker inspect --format \
    'state={{.State.Status}} exit={{.State.ExitCode}} oom_killed={{.State.OOMKilled}} id={{.Id}} started={{.State.StartedAt}} finished={{.State.FinishedAt}} image={{.Config.Image}}' \
    "${CONTAINER}" >"${OUT}/container-state.txt" 2>&1 || true
POST_CONTAINER_ID="$(docker inspect --format '{{.Id}}' "${CONTAINER}" 2>/dev/null || true)"
POST_CONTAINER_STARTED="$(docker inspect --format '{{.State.StartedAt}}' "${CONTAINER}" 2>/dev/null || true)"
printf '%s\n' "${POST_CONTAINER_ID}" >"${OUT}/container-id-after.txt"
printf '%s\n' "${POST_CONTAINER_STARTED}" >"${OUT}/container-started-after.txt"

RESTART_OBSERVED=0
if [[ -n "${POST_CONTAINER_ID}" && "${POST_CONTAINER_ID}" != "${PRE_CONTAINER_ID}" ]]; then
    RESTART_OBSERVED=1
fi
printf '%s\n' "${RESTART_OBSERVED}" >"${OUT}/restart-observed.txt"

{
    bash "${RELEASE_MANAGER}" status
    bash "${UPDATE_TRANSITION}" status
    bash "${RUNTIME_TRANSITION}" status
    bash "${PROFILE_TRANSITION}" status
    systemctl show "${UNIT}" --property=ActiveState,SubState,Result,ExecMainCode,ExecMainStatus --no-pager
} >"${OUT}/managed-state.txt" 2>&1

if curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null 2>&1; then
    printf '%s\n' HEALTH=ready >"${OUT}/api-state.txt"
    curl -fsS --max-time 15 http://127.0.0.1:8888/v1/models >>"${OUT}/api-state.txt" || true
else
    printf '%s\n' HEALTH=not-ready >"${OUT}/api-state.txt"
fi

ANALYZE_RC=0
if grep -Eq 'NV_ERR_NO_MEMORY|_memdescAllocInternal' "${OUT}/kernel-errors-monotonic.txt"; then
    set +e
    python3 "${ANALYZER}" "${OUT}" >"${OUT}/rmsys-analysis.txt" 2>&1
    ANALYZE_RC=$?
    set -e
else
    printf '%s\n' 'RM_SYS_ANALYSIS=NO_RM_OOM_IN_CAPTURE_WINDOW' >"${OUT}/rmsys-analysis.txt"
fi
printf '%s\n' "${ANALYZE_RC}" >"${OUT}/analysis.rc"

RUN_VALID=1
if [[ ! -r "${CHILD_STARTED_FILE}" || "${MANAGED_RC}" != 0 || "${RESTART_OBSERVED}" != 1 ]]; then
    RUN_VALID=0
fi
printf '%s\n' "${RUN_VALID}" >"${OUT}/run-valid.txt"

sudo -n chown -R "${RUN_USER}:${RUN_GROUP}" "${OUT}"

printf '\n===== R10b summary =====\n'
printf 'trace_rc=%s\n' "${TRACE_RC}"
printf 'managed_rc=%s\n' "${MANAGED_RC}"
printf 'restart_observed=%s\n' "${RESTART_OBSERVED}"
printf 'run_valid=%s\n' "${RUN_VALID}"
printf 'analysis_rc=%s\n' "${ANALYZE_RC}"
printf 'current_release=%s\n' "${CURRENT_RELEASE}"
printf 'pre_container_id=%s\n' "${PRE_CONTAINER_ID}"
printf 'post_container_id=%s\n' "${POST_CONTAINER_ID:-NONE}"
printf 'evidence=%s\n' "${OUT}"
printf '%s\n' '--- kernel errors ---'
cat "${OUT}/kernel-errors.txt" || true
printf '%s\n' '--- RM sysmem analysis ---'
cat "${OUT}/rmsys-analysis.txt" || true
printf '%s\n' '--- final managed state ---'
cat "${OUT}/managed-state.txt" || true
printf '%s\n' '--- final container state ---'
cat "${OUT}/container-state.txt" || true
printf '%s\n' '--- API state ---'
cat "${OUT}/api-state.txt" || true
printf 'ORCA_R10B_EVIDENCE=%s\n' "${OUT}"

if [[ "${TRACE_RC}" != 0 ]]; then
    exit "${TRACE_RC}"
fi
if [[ "${RUN_VALID}" != 1 ]]; then
    exit 3
fi
exit "${ANALYZE_RC}"
