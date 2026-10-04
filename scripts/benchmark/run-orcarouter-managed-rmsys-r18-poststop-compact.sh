#!/usr/bin/env bash
# R18: test one-shot compaction after fully stopping an aged OrcaRouter
# predecessor and before starting the replacement runtime.

set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"
CURRENT_LINK="${DATA_HOME}/current"
STATE_FILE="${STATE_HOME}/install.env"
UNIT="qwen38-flash-next.service"
CONTAINER="qwen38-flash-next"
OUT="${ORCA_R18_OUT:-/tmp/orcarouter-managed-rmsys-r18-poststop-compact-20261004}"
STATE_OUT="${OUT}/allocator-state"
STOP_FILE="${OUT}/collector.stop"
COLLECTOR="${SCRIPT_ROOT}/scripts/benchmark/collect-linux-allocator-state.py"
RELEASE_MANAGER="${SCRIPT_ROOT}/scripts/release-manager.sh"
UPDATE_TRANSITION="${SCRIPT_ROOT}/scripts/update-transition.sh"
RUNTIME_TRANSITION="${SCRIPT_ROOT}/scripts/runtime-transition.sh"
PROFILE_TRANSITION="${SCRIPT_ROOT}/scripts/profile-switch-transition.sh"
MIN_PREDECESSOR_AGE_S="${ORCA_R18_MIN_PREDECESSOR_AGE_S:-2700}"

RUN_USER="${SUDO_USER:-$(id -un)}"
RUN_GROUP="$(id -gn "${RUN_USER}")"
COLLECTOR_PID=""
COLLECTOR_RC=125
MANAGED_RC=125
SERVICE_STOPPED=0

fail() {
    printf 'ORCA_R18_ERROR: %s\n' "$*" >&2
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

for command in sudo python3 bash systemctl docker curl journalctl date grep awk find wc cat tee seq sleep mkdir; do
    command -v "${command}" >/dev/null 2>&1 || fail "required command not found: ${command}"
done
sudo -n true >/dev/null 2>&1 || fail "sudo timestamp unavailable; run sudo -v first"
[[ -r "${STATE_FILE}" ]] || fail "installation state missing: ${STATE_FILE}"
[[ -r "${COLLECTOR}" ]] || fail "allocator-state collector missing: ${COLLECTOR}"
[[ -L "${CURRENT_LINK}" ]] || fail "immutable current release link missing: ${CURRENT_LINK}"
[[ ! -e "${OUT}" ]] || fail "evidence already exists: ${OUT}"

grep -qx 'MODEL_PROFILE=orcarouter' "${STATE_FILE}" || fail "managed profile is not OrcaRouter"
[[ ! -e /run/systemd/system/qwen38-flash-next.service.d/kv16-ab.conf ]] || fail "temporary KV override is still present"
grep -qx 'UPDATE_STATE=idle' < <(bash "${UPDATE_TRANSITION}" status) || fail "update transition is not idle"
grep -qx 'TRANSACTION_STATE=idle' < <(bash "${RUNTIME_TRANSITION}" status) || fail "runtime transition is not idle"
grep -qx 'PROFILE_SWITCH_STATE=idle' < <(bash "${PROFILE_TRANSITION}" status) || fail "profile-switch transition is not idle"
systemctl is-active --quiet "${UNIT}" || fail "managed service is not active"
curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null || fail "managed API is not healthy"

CURRENT_RELEASE="$(bash "${RELEASE_MANAGER}" status | awk -F= '$1=="CURRENT_RELEASE" {print $2}')"
[[ -n "${CURRENT_RELEASE}" && "${CURRENT_RELEASE}" != none ]] || fail "no immutable current release"
MANAGE_SERVICE="${CURRENT_LINK}/scripts/manage-service.sh"
SERVE="${CURRENT_LINK}/scripts/serve.sh"
[[ -x "${MANAGE_SERVICE}" ]] || fail "managed service helper missing from current release"
[[ -r "${SERVE}" ]] || fail "serve helper missing from current release"
ORCA_BLOCK="$(awk '/^  orcarouter\)/,/^  nvidia\)/' "${SERVE}")"
grep -Fq 'DEFAULT_KV_MEM=17179869184' <<<"${ORCA_BLOCK}" || fail "current immutable release does not default OrcaRouter to 16 GiB"

PRE_CONTAINER_ID="$(docker inspect --format '{{.Id}}' "${CONTAINER}" 2>/dev/null || true)"
PRE_CONTAINER_STARTED="$(docker inspect --format '{{.State.StartedAt}}' "${CONTAINER}" 2>/dev/null || true)"
[[ -n "${PRE_CONTAINER_ID}" && -n "${PRE_CONTAINER_STARTED}" ]] || fail "managed predecessor container is unavailable"
PREDECESSOR_AGE_S="$(python3 - "${PRE_CONTAINER_STARTED}" <<'PY'
import datetime as dt
import sys
started = dt.datetime.fromisoformat(sys.argv[1].replace('Z', '+00:00'))
now = dt.datetime.now(dt.timezone.utc)
print(f"{(now - started).total_seconds():.3f}")
PY
)"
python3 - "${PREDECESSOR_AGE_S}" "${MIN_PREDECESSOR_AGE_S}" <<'PY' || fail "predecessor runtime is younger than required R18 minimum"
import sys
age = float(sys.argv[1])
minimum = float(sys.argv[2])
raise SystemExit(0 if age >= minimum else 1)
PY

mkdir -p -- "${OUT}"
printf '%s\n' "${CURRENT_RELEASE}" >"${OUT}/release-before.txt"
printf '%s\n' "${PRE_CONTAINER_ID}" >"${OUT}/container-id-before.txt"
printf '%s\n' "${PRE_CONTAINER_STARTED}" >"${OUT}/container-started-before.txt"
printf '%s\n' "${PREDECESSOR_AGE_S}" >"${OUT}/predecessor-age-s.txt"
printf '%s\n' "${MIN_PREDECESSOR_AGE_S}" >"${OUT}/minimum-predecessor-age-s.txt"
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
if [[ "$(docker inspect --format '{{.State.Running}}' "${CONTAINER}" 2>/dev/null || printf false)" == true ]]; then
    fail "predecessor container is still running after service stop"
fi
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/stop-complete-iso.txt"

snapshot_proc "${OUT}/poststop-before-compact"
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/compact-started-iso.txt"
sudo -n /bin/sh -c 'printf 1 > /proc/sys/vm/compact_memory'
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/compact-complete-iso.txt"
snapshot_proc "${OUT}/poststop-after-compact"

set +e
sudo -n /bin/bash "${MANAGE_SERVICE}" create --runtime-root "${CURRENT_LINK}" --start --yes \
    2>&1 | tee "${OUT}/managed-control.log"
MANAGED_RC=${PIPESTATUS[0]}
set -e
printf '%s\n' "${MANAGED_RC}" >"${OUT}/managed-command.rc"
SERVICE_STOPPED=0

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
sudo -n journalctl -k --since "${START_JOURNAL}" --until "${END_JOURNAL}" -o short-iso-precise --no-pager >"${OUT}/kernel-window.txt"
ERROR_RE='NV_ERR_NO_MEMORY|_memdescAllocInternal|NVRM:.*Xid|Xid \(PCI|GPU has fallen off the bus|oom-kill:|Out of memory:|Killed process '
grep -Ei "${ERROR_RE}" "${OUT}/kernel-window.txt" >"${OUT}/kernel-errors.txt" || true
RM_OOM_COUNT="$(grep -Ec 'NV_ERR_NO_MEMORY|_memdescAllocInternal' "${OUT}/kernel-errors.txt" 2>/dev/null || true)"
EVENT_SNAPSHOT_COUNT="$(find "${STATE_OUT}/events" -mindepth 1 -maxdepth 1 -type d -name 'rm-oom-*' 2>/dev/null | wc -l)"

POST_CONTAINER_ID="$(docker inspect --format '{{.Id}}' "${CONTAINER}" 2>/dev/null || true)"
POST_CONTAINER_STARTED="$(docker inspect --format '{{.State.StartedAt}}' "${CONTAINER}" 2>/dev/null || true)"
printf '%s\n' "${POST_CONTAINER_ID}" >"${OUT}/container-id-after.txt"
printf '%s\n' "${POST_CONTAINER_STARTED}" >"${OUT}/container-started-after.txt"
RESTART_OBSERVED=0
if [[ -n "${POST_CONTAINER_ID}" && "${POST_CONTAINER_ID}" != "${PRE_CONTAINER_ID}" ]]; then
    RESTART_OBSERVED=1
fi
printf '%s\n' "${RESTART_OBSERVED}" >"${OUT}/restart-observed.txt"

API_READY=0
if systemctl is-active --quiet "${UNIT}" && curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null 2>&1; then
    API_READY=1
fi
printf '%s\n' "${API_READY}" >"${OUT}/api-ready.txt"

RUN_VALID=1
if [[ "${MANAGED_RC}" != 0 || "${COLLECTOR_RC}" != 0 || "${RESTART_OBSERVED}" != 1 || "${API_READY}" != 1 ]]; then
    RUN_VALID=0
fi
printf '%s\n' "${RUN_VALID}" >"${OUT}/run-valid.txt"

sudo -n chown -R "${RUN_USER}:${RUN_GROUP}" "${OUT}" 2>/dev/null || true

{
    printf 'run_valid=%s\n' "${RUN_VALID}"
    printf 'managed_rc=%s\n' "${MANAGED_RC}"
    printf 'collector_rc=%s\n' "${COLLECTOR_RC}"
    printf 'restart_observed=%s\n' "${RESTART_OBSERVED}"
    printf 'api_ready=%s\n' "${API_READY}"
    printf 'predecessor_age_s=%s\n' "${PREDECESSOR_AGE_S}"
    printf 'minimum_predecessor_age_s=%s\n' "${MIN_PREDECESSOR_AGE_S}"
    printf 'rm_oom_count=%s\n' "${RM_OOM_COUNT}"
    printf 'event_snapshot_count=%s\n' "${EVENT_SNAPSHOT_COUNT}"
} >"${OUT}/r18-summary.txt"

printf '\n===== R18 summary =====\n'
cat "${OUT}/r18-summary.txt"
printf '%s\n' '--- kernel errors ---'
cat "${OUT}/kernel-errors.txt" || true
printf 'evidence=%s\n' "${OUT}"

if [[ "${RUN_VALID}" != 1 ]]; then
    printf 'ORCA_R18_RESULT=INVALID\n'
    exit 1
fi
if [[ "${RM_OOM_COUNT}" == 0 ]]; then
    printf 'ORCA_R18_RESULT=VALID_CLEAN\n'
else
    printf 'ORCA_R18_RESULT=VALID_RM_OOM\n'
fi
