#!/usr/bin/env bash
# R11: keep the proven R10b RM trace contract and add Linux allocator-state
# fingerprinting around the managed OrcaRouter restart.

set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
R10B="${SCRIPT_ROOT}/scripts/benchmark/run-orcarouter-managed-rmsys-r10b.sh"
COLLECTOR="${SCRIPT_ROOT}/scripts/benchmark/collect-linux-allocator-state.py"
OUT="${ORCA_R11_OUT:-/tmp/orcarouter-managed-rmsys-r11-20261003}"
R10B_OUT="${OUT}/r10b"
STATE_OUT="${OUT}/allocator-state"
STOP_FILE="${OUT}/collector.stop"
UNIT="qwen38-flash-next.service"

RUN_USER="${SUDO_USER:-$(id -un)}"
RUN_GROUP="$(id -gn "${RUN_USER}")"
COLLECTOR_PID=""
COLLECTOR_RC=125
R10B_RC=125

fail() {
    printf 'ORCA_R11_ERROR: %s\n' "$*" >&2
    exit 2
}

cleanup() {
    local rc=$?
    trap - EXIT INT TERM
    set +e
    touch "${STOP_FILE}" 2>/dev/null || true
    if [[ -n "${COLLECTOR_PID}" ]]; then
        if kill -0 "${COLLECTOR_PID}" >/dev/null 2>&1; then
            wait "${COLLECTOR_PID}" >/dev/null 2>&1 || true
        fi
    fi
    exit "${rc}"
}
trap cleanup EXIT INT TERM

for command in sudo python3 bash systemctl curl date grep find wc; do
    command -v "${command}" >/dev/null 2>&1 || fail "required command not found: ${command}"
done
sudo -n true >/dev/null 2>&1 || fail "sudo timestamp unavailable; run sudo -v first"
[[ -r "${R10B}" ]] || fail "R10b runner is not readable: ${R10B}"
[[ -r "${COLLECTOR}" ]] || fail "allocator-state collector missing: ${COLLECTOR}"
[[ ! -e "${OUT}" ]] || fail "evidence already exists: ${OUT}"
systemctl is-active --quiet "${UNIT}" || fail "managed service is not active"
curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null || fail "managed API is not healthy"

mkdir -p -- "${OUT}"
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/r11-start-iso.txt"

# Run the state collector as root so pagetype/zone state remains readable on
# hardened kernels. The output is returned to the invoking user after capture.
sudo -n /usr/bin/python3 "${COLLECTOR}" \
    --output "${STATE_OUT}" \
    --stop-file "${STOP_FILE}" \
    --fast-interval 1 \
    --slow-interval 5 \
    >"${OUT}/collector.log" 2>&1 &
COLLECTOR_PID=$!
printf '%s\n' "${COLLECTOR_PID}" >"${OUT}/collector.pid"

sleep 2
kill -0 "${COLLECTOR_PID}" >/dev/null 2>&1 || {
    cat "${OUT}/collector.log" >&2 || true
    fail "allocator-state collector exited before managed restart"
}

set +e
ORCA_R10B_OUT="${R10B_OUT}" bash "${R10B}" \
    2>&1 | tee "${OUT}/r10b-control.log"
R10B_RC=${PIPESTATUS[0]}
set -e
printf '%s\n' "${R10B_RC}" >"${OUT}/r10b.rc"

touch "${STOP_FILE}"
set +e
wait "${COLLECTOR_PID}"
COLLECTOR_RC=$?
set -e
COLLECTOR_PID=""
printf '%s\n' "${COLLECTOR_RC}" >"${OUT}/collector.rc"

sudo -n chown -R "${RUN_USER}:${RUN_GROUP}" "${STATE_OUT}" "${OUT}/collector.log" 2>/dev/null || true
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/r11-end-iso.txt"

RUN_VALID="$(cat "${R10B_OUT}/run-valid.txt" 2>/dev/null || printf '0')"
RM_OOM_COUNT="$(grep -Ec 'NV_ERR_NO_MEMORY|_memdescAllocInternal' "${R10B_OUT}/kernel-errors.txt" 2>/dev/null || true)"
EVENT_SNAPSHOT_COUNT="$(find "${STATE_OUT}/events" -mindepth 1 -maxdepth 1 -type d -name 'rm-oom-*' 2>/dev/null | wc -l)"
FAST_SAMPLE_COUNT="$(grep -c '^===== sample ' "${STATE_OUT}/fast-state.txt" 2>/dev/null || true)"
SLOW_SAMPLE_COUNT="$(grep -c '^===== sample ' "${STATE_OUT}/slow-state.txt" 2>/dev/null || true)"

{
    printf 'r10b_rc=%s\n' "${R10B_RC}"
    printf 'collector_rc=%s\n' "${COLLECTOR_RC}"
    printf 'run_valid=%s\n' "${RUN_VALID}"
    printf 'rm_oom_count=%s\n' "${RM_OOM_COUNT}"
    printf 'event_snapshot_count=%s\n' "${EVENT_SNAPSHOT_COUNT}"
    printf 'fast_sample_count=%s\n' "${FAST_SAMPLE_COUNT}"
    printf 'slow_sample_count=%s\n' "${SLOW_SAMPLE_COUNT}"
} >"${OUT}/r11-summary.txt"

printf '\n===== R11 summary =====\n'
cat "${OUT}/r11-summary.txt"
printf 'evidence=%s\n' "${OUT}"
printf '%s\n' '--- R10b RM analysis ---'
cat "${R10B_OUT}/rmsys-analysis.txt" 2>/dev/null || true

if [[ "${R10B_RC}" != 0 || "${COLLECTOR_RC}" != 0 || "${RUN_VALID}" != 1 ]]; then
    printf 'ORCA_R11_RESULT=INVALID\n'
    exit 1
fi

printf 'ORCA_R11_RESULT=VALID\n'
