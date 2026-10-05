#!/usr/bin/env bash
# R14: test a larger kswapd free-page reserve/reclaim margin during the full
# OrcaRouter startup interval after R12/R13 showed compaction-only mitigation
# is insufficient.
#
# Exactly one VM policy is changed temporarily:
#   vm.watermark_scale_factor: 10 -> 100
#
# vm.compaction_proactiveness must remain at the baseline 20. All other VM
# tunables are left untouched. The original watermark value is restored on
# every normal/error/signal exit path. The managed restart and allocator trace
# remain the proven R11/R10b contract.

set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
R11="${SCRIPT_ROOT}/scripts/benchmark/run-orcarouter-managed-rmsys-r11.sh"
R11_ANALYZER="${SCRIPT_ROOT}/scripts/benchmark/analyze-orcarouter-r11-allocator-state.py"
ZONE_ANALYZER="${SCRIPT_ROOT}/scripts/benchmark/analyze-orcarouter-r11-zone-migratetype.py"
OUT="${ORCA_R14_OUT:-/tmp/orcarouter-managed-rmsys-r14-watermark100-20261003}"
R11_OUT="${OUT}/r11"
UNIT="qwen38-flash-next.service"
TUNABLE="/proc/sys/vm/watermark_scale_factor"
COMPACTION_TUNABLE="/proc/sys/vm/compaction_proactiveness"
EXPECTED_ORIGINAL=10
EXPECTED_COMPACTION=20
TARGET=100
ORIGINAL=""
TUNABLE_CHANGED=0

fail() {
    printf 'ORCA_R14_ERROR: %s\n' "$*" >&2
    exit 2
}

write_tunable() {
    local value="$1"
    printf '%s\n' "${value}" | sudo -n tee "${TUNABLE}" >/dev/null
}

restore_tunable() {
    if [[ "${TUNABLE_CHANGED}" == 1 && -n "${ORIGINAL}" ]]; then
        write_tunable "${ORIGINAL}" || return 1
        TUNABLE_CHANGED=0
    fi
}

cleanup() {
    local rc=$?
    trap - EXIT INT TERM
    set +e
    restore_tunable
    exit "${rc}"
}
trap cleanup EXIT INT TERM

capture_vm_tunables() {
    local target="$1"
    local name path
    {
        for name in \
            compaction_proactiveness \
            compact_unevictable_allowed \
            extfrag_threshold \
            min_free_kbytes \
            watermark_boost_factor \
            watermark_scale_factor; do
            path="/proc/sys/vm/${name}"
            if [[ -r "${path}" ]]; then
                printf '%s=' "${name}"
                cat "${path}"
            fi
        done
    } >"${target}"
}

capture_state() {
    local label="$1"
    sudo -n cat /proc/buddyinfo >"${OUT}/${label}-buddyinfo.txt"
    sudo -n cat /proc/pagetypeinfo >"${OUT}/${label}-pagetypeinfo.txt"
    sudo -n cat /proc/zoneinfo >"${OUT}/${label}-zoneinfo.txt"
    cat /proc/meminfo >"${OUT}/${label}-meminfo.txt"
    cat /proc/vmstat >"${OUT}/${label}-vmstat.txt"
    cat /proc/pressure/memory >"${OUT}/${label}-memory-pressure.txt"
}

for command in sudo python3 bash systemctl curl date tee cat grep tail cut; do
    command -v "${command}" >/dev/null 2>&1 || fail "required command not found: ${command}"
done

sudo -n true >/dev/null 2>&1 || fail "sudo timestamp unavailable; run sudo -v first"
[[ -r "${R11}" ]] || fail "R11 runner missing: ${R11}"
[[ -r "${R11_ANALYZER}" ]] || fail "R11 allocator analyzer missing: ${R11_ANALYZER}"
[[ -r "${ZONE_ANALYZER}" ]] || fail "R11 zone/migratetype analyzer missing: ${ZONE_ANALYZER}"
[[ -r "${TUNABLE}" && -e "${TUNABLE}" ]] || fail "watermark_scale_factor is unavailable"
[[ -r "${COMPACTION_TUNABLE}" ]] || fail "compaction_proactiveness is unavailable"
[[ ! -e "${OUT}" ]] || fail "evidence already exists: ${OUT}"
systemctl is-active --quiet "${UNIT}" || fail "managed service is not active"
curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null || fail "managed API is not healthy"

ORIGINAL="$(cat "${TUNABLE}")"
COMPACTION_BASELINE="$(cat "${COMPACTION_TUNABLE}")"
[[ "${ORIGINAL}" =~ ^[0-9]+$ ]] || fail "invalid original watermark_scale_factor: ${ORIGINAL}"
[[ "${COMPACTION_BASELINE}" =~ ^[0-9]+$ ]] || fail "invalid compaction_proactiveness: ${COMPACTION_BASELINE}"
[[ "${ORIGINAL}" -eq "${EXPECTED_ORIGINAL}" ]] ||
    fail "expected watermark_scale_factor=${EXPECTED_ORIGINAL}, found ${ORIGINAL}; refusing to change an unexpected host policy"
[[ "${COMPACTION_BASELINE}" -eq "${EXPECTED_COMPACTION}" ]] ||
    fail "expected compaction_proactiveness=${EXPECTED_COMPACTION}, found ${COMPACTION_BASELINE}; R14 changes only watermark_scale_factor"

mkdir -p -- "${OUT}"
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/r14-start-iso.txt"
printf '%s\n' "${ORIGINAL}" >"${OUT}/watermark-scale-factor-original.txt"
printf '%s\n' "${TARGET}" >"${OUT}/watermark-scale-factor-target.txt"
printf '%s\n' "${COMPACTION_BASELINE}" >"${OUT}/compaction-proactiveness-baseline.txt"
capture_vm_tunables "${OUT}/vm-tunables-before.txt"
capture_state before-policy

write_tunable "${TARGET}"
TUNABLE_CHANGED=1
APPLIED="$(cat "${TUNABLE}")"
printf '%s\n' "${APPLIED}" >"${OUT}/watermark-scale-factor-applied.txt"
[[ "${APPLIED}" -eq "${TARGET}" ]] || fail "failed to apply watermark_scale_factor=${TARGET}"
[[ "$(cat "${COMPACTION_TUNABLE}")" -eq "${EXPECTED_COMPACTION}" ]] || fail "compaction_proactiveness changed unexpectedly"

capture_vm_tunables "${OUT}/vm-tunables-during.txt"
capture_state after-policy-write

set +e
ORCA_R11_OUT="${R11_OUT}" bash "${R11}" 2>&1 | tee "${OUT}/r11-control.log"
R11_RC=${PIPESTATUS[0]}
set -e
printf '%s\n' "${R11_RC}" >"${OUT}/r11.rc"

DURING_END="$(cat "${TUNABLE}")"
COMPACTION_END="$(cat "${COMPACTION_TUNABLE}")"
printf '%s\n' "${DURING_END}" >"${OUT}/watermark-scale-factor-during-end.txt"
printf '%s\n' "${COMPACTION_END}" >"${OUT}/compaction-proactiveness-during-end.txt"
[[ "${DURING_END}" -eq "${TARGET}" ]] || fail "watermark_scale_factor changed during experiment: ${DURING_END}"
[[ "${COMPACTION_END}" -eq "${EXPECTED_COMPACTION}" ]] || fail "compaction_proactiveness changed during experiment: ${COMPACTION_END}"

restore_tunable
RESTORED="$(cat "${TUNABLE}")"
printf '%s\n' "${RESTORED}" >"${OUT}/watermark-scale-factor-restored.txt"
[[ "${RESTORED}" -eq "${ORIGINAL}" ]] || fail "failed to restore watermark_scale_factor=${ORIGINAL}"
capture_vm_tunables "${OUT}/vm-tunables-restored.txt"
capture_state restored

RUN_VALID="$(grep -E '^run_valid=' "${R11_OUT}/r11-summary.txt" 2>/dev/null | tail -1 | cut -d= -f2 || true)"
RM_OOM_COUNT="$(grep -E '^rm_oom_count=' "${R11_OUT}/r11-summary.txt" 2>/dev/null | tail -1 | cut -d= -f2 || true)"
RUN_VALID="${RUN_VALID:-0}"
RM_OOM_COUNT="${RM_OOM_COUNT:-0}"

ANALYZER_RC=0
ZONE_ANALYZER_RC=0
if [[ "${RUN_VALID}" == 1 && "${RM_OOM_COUNT}" =~ ^[0-9]+$ && "${RM_OOM_COUNT}" -gt 0 ]]; then
    set +e
    python3 "${R11_ANALYZER}" --evidence "${R11_OUT}" >"${OUT}/allocator-state-analysis.txt" 2>&1
    ANALYZER_RC=$?
    python3 "${ZONE_ANALYZER}" --evidence "${R11_OUT}" >"${OUT}/zone-migratetype-analysis.txt" 2>&1
    ZONE_ANALYZER_RC=$?
    set -e
fi

{
    printf 'r11_rc=%s\n' "${R11_RC}"
    printf 'run_valid=%s\n' "${RUN_VALID}"
    printf 'rm_oom_count=%s\n' "${RM_OOM_COUNT}"
    printf 'watermark_scale_factor_original=%s\n' "${ORIGINAL}"
    printf 'watermark_scale_factor_target=%s\n' "${TARGET}"
    printf 'watermark_scale_factor_restored=%s\n' "${RESTORED}"
    printf 'compaction_proactiveness=%s\n' "${EXPECTED_COMPACTION}"
    printf 'allocator_analyzer_rc=%s\n' "${ANALYZER_RC}"
    printf 'zone_analyzer_rc=%s\n' "${ZONE_ANALYZER_RC}"
} >"${OUT}/r14-summary.txt"

printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/r14-end-iso.txt"

printf '\n===== R14 watermark-scale summary =====\n'
cat "${OUT}/r14-summary.txt"

if [[ "${R11_RC}" != 0 || "${RUN_VALID}" != 1 ]]; then
    printf 'ORCA_R14_RESULT=INVALID\n'
    exit 1
fi

if [[ "${RM_OOM_COUNT}" =~ ^[0-9]+$ && "${RM_OOM_COUNT}" -eq 0 ]]; then
    printf 'ORCA_R14_RESULT=VALID_CLEAN\n'
else
    printf 'ORCA_R14_RESULT=VALID_RM_OOM\n'
fi

printf 'ORCA_R14_EVIDENCE=%s\n' "${OUT}"
