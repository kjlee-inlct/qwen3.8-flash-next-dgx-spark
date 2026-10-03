#!/usr/bin/env bash
# R17: repeat the exact baseline VM policy twice to isolate restart ordinal / allocator carry-over.
#
# Leg A: watermark_scale_factor=10, compaction_proactiveness=20
# Leg B: watermark_scale_factor=10, compaction_proactiveness=20
#
# No VM policy is changed. Each leg must independently prove a real managed restart through R11/R10b.

set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
R11="${SCRIPT_ROOT}/scripts/benchmark/run-orcarouter-managed-rmsys-r11.sh"
OUT="${ORCA_R17_OUT:-/tmp/orcarouter-managed-rmsys-r17-baseline-repeat-20261004}"
LEG_A_OUT="${OUT}/leg-a-baseline10"
LEG_B_OUT="${OUT}/leg-b-baseline10"
UNIT="qwen38-flash-next.service"
WATERMARK_TUNABLE="/proc/sys/vm/watermark_scale_factor"
COMPACTION_TUNABLE="/proc/sys/vm/compaction_proactiveness"
EXPECTED_WATERMARK=10
EXPECTED_COMPACTION=20

fail() {
    printf 'ORCA_R17_ERROR: %s\n' "$*" >&2
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
    [[ "${watermark}" == "${EXPECTED_WATERMARK}" ]] || fail "expected watermark_scale_factor=${EXPECTED_WATERMARK}, found ${watermark}"
    [[ "${compaction}" == "${EXPECTED_COMPACTION}" ]] || fail "expected compaction_proactiveness=${EXPECTED_COMPACTION}, found ${compaction}"
    systemctl is-active --quiet "${UNIT}" || fail "managed service is not active"
    curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null || fail "managed API is not healthy"
}

for command in sudo bash systemctl curl date cat grep tail cut tee; do
    command -v "${command}" >/dev/null 2>&1 || fail "required command not found: ${command}"
done

sudo -n true >/dev/null 2>&1 || fail "sudo timestamp unavailable; run sudo -v first"
[[ -r "${R11}" ]] || fail "R11 runner missing: ${R11}"
[[ -r "${WATERMARK_TUNABLE}" ]] || fail "watermark_scale_factor unavailable"
[[ -r "${COMPACTION_TUNABLE}" ]] || fail "compaction_proactiveness unavailable"
[[ ! -e "${OUT}" ]] || fail "evidence already exists: ${OUT}"
[[ ! -e /run/systemd/system/qwen38-flash-next.service.d/kv16-ab.conf ]] || fail "temporary KV override is present"

check_host_baseline
mkdir -p -- "${OUT}"
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/r17-start-iso.txt"

printf '\n===== R17 leg A: baseline10 =====\n'
set +e
ORCA_R11_OUT="${LEG_A_OUT}" bash "${R11}" 2>&1 | tee "${OUT}/leg-a-control.log"
LEG_A_RC=${PIPESTATUS[0]}
set -e
printf '%s\n' "${LEG_A_RC}" >"${OUT}/leg-a.rc"

LEG_A_VALID="$(read_summary_value "${LEG_A_OUT}/r11-summary.txt" run_valid)"
LEG_A_RM="$(read_summary_value "${LEG_A_OUT}/r11-summary.txt" rm_oom_count)"
LEG_A_VALID="${LEG_A_VALID:-0}"
LEG_A_RM="${LEG_A_RM:-0}"

if [[ "${LEG_A_RC}" != 0 || "${LEG_A_VALID}" != 1 ]]; then
    {
        printf 'leg_a_rc=%s\n' "${LEG_A_RC}"
        printf 'leg_a_run_valid=%s\n' "${LEG_A_VALID}"
        printf 'leg_a_rm_oom_count=%s\n' "${LEG_A_RM}"
        printf 'leg_b_rc=NOT_RUN\n'
        printf 'leg_b_run_valid=0\n'
        printf 'leg_b_rm_oom_count=NOT_RUN\n'
    } >"${OUT}/r17-summary.txt"
    printf 'ORCA_R17_RESULT=INVALID_LEG_A\n'
    exit 1
fi

check_host_baseline
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/leg-b-start-iso.txt"

printf '\n===== R17 leg B: baseline10 repeat =====\n'
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
    printf 'leg_a_evidence=%s\n' "${LEG_A_OUT}"
    printf 'leg_b_rc=%s\n' "${LEG_B_RC}"
    printf 'leg_b_run_valid=%s\n' "${LEG_B_VALID}"
    printf 'leg_b_rm_oom_count=%s\n' "${LEG_B_RM}"
    printf 'leg_b_evidence=%s\n' "${LEG_B_OUT}"
    printf 'watermark_scale_factor_final=%s\n' "${FINAL_WATERMARK}"
    printf 'compaction_proactiveness_final=%s\n' "${FINAL_COMPACTION}"
} >"${OUT}/r17-summary.txt"

printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/r17-end-iso.txt"

printf '\n===== R17 baseline-repeat summary =====\n'
cat "${OUT}/r17-summary.txt"

if [[ "${LEG_B_RC}" != 0 || "${LEG_B_VALID}" != 1 ]]; then
    printf 'ORCA_R17_RESULT=INVALID_LEG_B\n'
    exit 1
fi

[[ "${FINAL_WATERMARK}" == "${EXPECTED_WATERMARK}" ]] || fail "final watermark_scale_factor=${FINAL_WATERMARK}"
[[ "${FINAL_COMPACTION}" == "${EXPECTED_COMPACTION}" ]] || fail "final compaction_proactiveness=${FINAL_COMPACTION}"

if [[ "${LEG_A_RM}" =~ ^[0-9]+$ && "${LEG_B_RM}" =~ ^[0-9]+$ ]]; then
    if (( LEG_A_RM > 0 && LEG_B_RM == 0 )); then
        printf 'ORCA_R17_RESULT=VALID_A_RM_B_CLEAN\n'
    elif (( LEG_A_RM == 0 && LEG_B_RM == 0 )); then
        printf 'ORCA_R17_RESULT=VALID_BOTH_CLEAN\n'
    elif (( LEG_A_RM == 0 && LEG_B_RM > 0 )); then
        printf 'ORCA_R17_RESULT=VALID_A_CLEAN_B_RM\n'
    else
        printf 'ORCA_R17_RESULT=VALID_BOTH_RM\n'
    fi
else
    printf 'ORCA_R17_RESULT=INVALID_RM_COUNTS\n'
    exit 1
fi

printf 'ORCA_R17_EVIDENCE=%s\n' "${OUT}"
