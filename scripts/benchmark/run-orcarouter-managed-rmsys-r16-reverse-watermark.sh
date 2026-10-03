#!/usr/bin/env bash
# R16: reverse-order paired watermark-scale validation.
#
# Leg A runs the proven R14 treatment first:
#   vm.watermark_scale_factor: 10 -> 100 -> 10
#   vm.compaction_proactiveness=20 throughout
#
# Leg B then runs the proven R11/R10b managed trace at the restored baseline:
#   vm.watermark_scale_factor=10
#   vm.compaction_proactiveness=20
#
# This reverses R15 ordering to test whether its A-fail/B-clean result can be
# explained by sequential allocator carry-over rather than the watermark policy.

set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
R11="${SCRIPT_ROOT}/scripts/benchmark/run-orcarouter-managed-rmsys-r11.sh"
R14="${SCRIPT_ROOT}/scripts/benchmark/run-orcarouter-managed-rmsys-r14-watermark100.sh"
OUT="${ORCA_R16_OUT:-/tmp/orcarouter-managed-rmsys-r16-reverse-watermark-20261003}"
LEG_A_OUT="${OUT}/leg-a-watermark100"
LEG_B_OUT="${OUT}/leg-b-baseline10"
UNIT="qwen38-flash-next.service"
WATERMARK_TUNABLE="/proc/sys/vm/watermark_scale_factor"
COMPACTION_TUNABLE="/proc/sys/vm/compaction_proactiveness"
EXPECTED_WATERMARK=10
EXPECTED_COMPACTION=20

fail() {
    printf 'ORCA_R16_ERROR: %s\n' "$*" >&2
    exit 2
}

read_summary_value() {
    local file="$1"
    local key="$2"
    grep -E "^${key}=" "${file}" 2>/dev/null | tail -1 | cut -d= -f2 || true
}

check_host_baseline() {
    local watermark compaction
    watermark="$(cat "${WATERMARK_TUNABLE}")"
    compaction="$(cat "${COMPACTION_TUNABLE}")"
    [[ "${watermark}" =~ ^[0-9]+$ ]] || fail "invalid watermark_scale_factor: ${watermark}"
    [[ "${compaction}" =~ ^[0-9]+$ ]] || fail "invalid compaction_proactiveness: ${compaction}"
    [[ "${watermark}" -eq "${EXPECTED_WATERMARK}" ]] ||
        fail "expected watermark_scale_factor=${EXPECTED_WATERMARK}, found ${watermark}"
    [[ "${compaction}" -eq "${EXPECTED_COMPACTION}" ]] ||
        fail "expected compaction_proactiveness=${EXPECTED_COMPACTION}, found ${compaction}"
    systemctl is-active --quiet "${UNIT}" || fail "managed service is not active"
    curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null || fail "managed API is not healthy"
}

for command in sudo bash systemctl curl date cat grep tail cut tee; do
    command -v "${command}" >/dev/null 2>&1 || fail "required command not found: ${command}"
done

sudo -n true >/dev/null 2>&1 || fail "sudo timestamp unavailable; run sudo -v first"
[[ -r "${R11}" ]] || fail "R11 runner missing: ${R11}"
[[ -r "${R14}" ]] || fail "R14 runner missing: ${R14}"
[[ -r "${WATERMARK_TUNABLE}" ]] || fail "watermark_scale_factor unavailable"
[[ -r "${COMPACTION_TUNABLE}" ]] || fail "compaction_proactiveness unavailable"
[[ ! -e "${OUT}" ]] || fail "evidence already exists: ${OUT}"
[[ ! -e /run/systemd/system/qwen38-flash-next.service.d/kv16-ab.conf ]] ||
    fail "temporary KV override is present"

check_host_baseline
mkdir -p -- "${OUT}"
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/r16-start-iso.txt"
printf '%s\n' "${EXPECTED_WATERMARK}" >"${OUT}/baseline-watermark-scale-factor.txt"
printf '%s\n' "${EXPECTED_COMPACTION}" >"${OUT}/baseline-compaction-proactiveness.txt"

printf '\n===== R16 leg A: watermark_scale_factor=100 treatment =====\n'
set +e
ORCA_R14_OUT="${LEG_A_OUT}" bash "${R14}" 2>&1 | tee "${OUT}/leg-a-control.log"
LEG_A_RC=${PIPESTATUS[0]}
set -e
printf '%s\n' "${LEG_A_RC}" >"${OUT}/leg-a.rc"

LEG_A_VALID="$(read_summary_value "${LEG_A_OUT}/r14-summary.txt" run_valid)"
LEG_A_RM="$(read_summary_value "${LEG_A_OUT}/r14-summary.txt" rm_oom_count)"
LEG_A_RESTORED="$(read_summary_value "${LEG_A_OUT}/r14-summary.txt" watermark_scale_factor_restored)"
LEG_A_VALID="${LEG_A_VALID:-0}"
LEG_A_RM="${LEG_A_RM:-0}"
LEG_A_RESTORED="${LEG_A_RESTORED:-0}"

if [[ "${LEG_A_RC}" != 0 || "${LEG_A_VALID}" != 1 ]]; then
    {
        printf 'leg_a_rc=%s\n' "${LEG_A_RC}"
        printf 'leg_a_run_valid=%s\n' "${LEG_A_VALID}"
        printf 'leg_a_rm_oom_count=%s\n' "${LEG_A_RM}"
        printf 'leg_a_watermark_restored=%s\n' "${LEG_A_RESTORED}"
        printf 'leg_b_rc=NOT_RUN\n'
        printf 'leg_b_run_valid=0\n'
        printf 'leg_b_rm_oom_count=NOT_RUN\n'
        printf 'watermark_scale_factor_final=%s\n' "$(cat "${WATERMARK_TUNABLE}")"
        printf 'compaction_proactiveness_final=%s\n' "$(cat "${COMPACTION_TUNABLE}")"
    } >"${OUT}/r16-summary.txt"
    printf 'ORCA_R16_RESULT=INVALID_LEG_A\n'
    exit 1
fi

[[ "${LEG_A_RESTORED}" -eq "${EXPECTED_WATERMARK}" ]] ||
    fail "R14 did not report watermark restoration to ${EXPECTED_WATERMARK}"

# The baseline leg must start only after the treatment helper has restored all
# tested host policy and left the managed service healthy.
check_host_baseline
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/leg-b-start-iso.txt"

printf '\n===== R16 leg B: baseline watermark_scale_factor=10 =====\n'
set +e
ORCA_R11_OUT="${LEG_B_OUT}" bash "${R11}" 2>&1 | tee "${OUT}/leg-b-control.log"
LEG_B_RC=${PIPESTATUS[0]}
set -e
printf '%s\n' "${LEG_B_RC}" >"${OUT}/leg-b.rc"

LEG_B_VALID="$(read_summary_value "${LEG_B_OUT}/r11-summary.txt" run_valid)"
LEG_B_RM="$(read_summary_value "${LEG_B_OUT}/r11-summary.txt" rm_oom_count)"
LEG_B_VALID="${LEG_B_VALID:-0}"
LEG_B_RM="${LEG_B_RM:-0}"

FINAL_WATERMARK="$(cat "${WATERMARK_TUNABLE}")"
FINAL_COMPACTION="$(cat "${COMPACTION_TUNABLE}")"

{
    printf 'leg_a_rc=%s\n' "${LEG_A_RC}"
    printf 'leg_a_run_valid=%s\n' "${LEG_A_VALID}"
    printf 'leg_a_rm_oom_count=%s\n' "${LEG_A_RM}"
    printf 'leg_a_watermark_restored=%s\n' "${LEG_A_RESTORED}"
    printf 'leg_a_evidence=%s\n' "${LEG_A_OUT}"
    printf 'leg_b_rc=%s\n' "${LEG_B_RC}"
    printf 'leg_b_run_valid=%s\n' "${LEG_B_VALID}"
    printf 'leg_b_rm_oom_count=%s\n' "${LEG_B_RM}"
    printf 'leg_b_evidence=%s\n' "${LEG_B_OUT}"
    printf 'watermark_scale_factor_final=%s\n' "${FINAL_WATERMARK}"
    printf 'compaction_proactiveness_final=%s\n' "${FINAL_COMPACTION}"
} >"${OUT}/r16-summary.txt"

printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/r16-end-iso.txt"

printf '\n===== R16 reverse-pair summary =====\n'
cat "${OUT}/r16-summary.txt"

if [[ "${LEG_B_RC}" != 0 || "${LEG_B_VALID}" != 1 ]]; then
    printf 'ORCA_R16_RESULT=INVALID_LEG_B\n'
    exit 1
fi

[[ "${FINAL_WATERMARK}" -eq "${EXPECTED_WATERMARK}" ]] ||
    fail "final watermark_scale_factor is ${FINAL_WATERMARK}, expected ${EXPECTED_WATERMARK}"
[[ "${FINAL_COMPACTION}" -eq "${EXPECTED_COMPACTION}" ]] ||
    fail "final compaction_proactiveness is ${FINAL_COMPACTION}, expected ${EXPECTED_COMPACTION}"

if [[ "${LEG_A_RM}" =~ ^[0-9]+$ && "${LEG_B_RM}" =~ ^[0-9]+$ ]]; then
    if (( LEG_A_RM == 0 && LEG_B_RM > 0 )); then
        printf 'ORCA_R16_RESULT=VALID_A_CLEAN_B_RM\n'
    elif (( LEG_A_RM == 0 && LEG_B_RM == 0 )); then
        printf 'ORCA_R16_RESULT=VALID_BOTH_CLEAN\n'
    elif (( LEG_A_RM > 0 && LEG_B_RM == 0 )); then
        printf 'ORCA_R16_RESULT=VALID_A_RM_B_CLEAN\n'
    else
        printf 'ORCA_R16_RESULT=VALID_BOTH_RM\n'
    fi
else
    printf 'ORCA_R16_RESULT=INVALID_RM_COUNTS\n'
    exit 1
fi

printf 'ORCA_R16_EVIDENCE=%s\n' "${OUT}"
