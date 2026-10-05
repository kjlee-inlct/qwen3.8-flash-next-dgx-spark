#!/usr/bin/env bash
# R12: evaluate one-shot Linux compaction as a minimal mitigation for the
# directly traced Normal-zone Unmovable order-4 RM failure.
#
# The experiment intentionally does not persist or change VM sysctl tuning.
# It records allocator state, writes 1 once to /proc/sys/vm/compact_memory,
# records the immediate post-compaction state, then runs the proven R11
# managed restart/trace contract exactly once.

set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
R11="${SCRIPT_ROOT}/scripts/benchmark/run-orcarouter-managed-rmsys-r11.sh"
R11_ANALYZER="${SCRIPT_ROOT}/scripts/benchmark/analyze-orcarouter-r11-allocator-state.py"
ZONE_ANALYZER="${SCRIPT_ROOT}/scripts/benchmark/analyze-orcarouter-r11-zone-migratetype.py"
OUT="${ORCA_R12_OUT:-/tmp/orcarouter-managed-rmsys-r12-precompact-20261003}"
R11_OUT="${OUT}/r11"
UNIT="qwen38-flash-next.service"

fail() {
    printf 'ORCA_R12_ERROR: %s\n' "$*" >&2
    exit 2
}

for command in sudo python3 bash systemctl curl date tee cat grep tail cut; do
    command -v "${command}" >/dev/null 2>&1 || fail "required command not found: ${command}"
done

sudo -n true >/dev/null 2>&1 || fail "sudo timestamp unavailable; run sudo -v first"
[[ -r "${R11}" ]] || fail "R11 runner missing: ${R11}"
[[ -r "${R11_ANALYZER}" ]] || fail "R11 allocator analyzer missing: ${R11_ANALYZER}"
[[ -r "${ZONE_ANALYZER}" ]] || fail "R11 zone/migratetype analyzer missing: ${ZONE_ANALYZER}"
[[ -w /proc/sys/vm/compact_memory || -e /proc/sys/vm/compact_memory ]] || fail "compact_memory is unavailable"
[[ ! -e "${OUT}" ]] || fail "evidence already exists: ${OUT}"
systemctl is-active --quiet "${UNIT}" || fail "managed service is not active"
curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null || fail "managed API is not healthy"

mkdir -p -- "${OUT}"
printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/r12-start-iso.txt"

capture_state() {
    local label="$1"
    sudo -n cat /proc/buddyinfo >"${OUT}/${label}-buddyinfo.txt"
    sudo -n cat /proc/pagetypeinfo >"${OUT}/${label}-pagetypeinfo.txt"
    sudo -n cat /proc/zoneinfo >"${OUT}/${label}-zoneinfo.txt"
    cat /proc/meminfo >"${OUT}/${label}-meminfo.txt"
    cat /proc/vmstat >"${OUT}/${label}-vmstat.txt"
    cat /proc/pressure/memory >"${OUT}/${label}-memory-pressure.txt"
}

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

summarize_buddy() {
    python3 - "$1" "$2" <<'PY'
from __future__ import annotations
import pathlib
import re
import sys

pattern = re.compile(r"^Node\s+(\d+),\s+zone\s+(\S+)\s+(.+)$")


def read(path: str):
    out = {}
    for raw in pathlib.Path(path).read_text().splitlines():
        m = pattern.match(raw.strip())
        if not m:
            continue
        values = [int(x) for x in m.group(3).split()]
        out[(int(m.group(1)), m.group(2))] = values
    return out


def metrics(values):
    order4 = values[4] if len(values) > 4 else 0
    order5plus = sum(values[5:]) if len(values) > 5 else 0
    pages = sum(count * (1 << order) for order, count in enumerate(values) if order >= 4)
    return order4, order5plus, pages * 4096 / 1024 / 1024

for label, path in (("before", sys.argv[1]), ("after", sys.argv[2])):
    zones = read(path)
    for key in sorted(zones):
        node, zone = key
        o4, o5p, mib = metrics(zones[key])
        print(f"{label}_buddy node={node} zone={zone} order4_blocks={o4} order5plus_blocks={o5p} ge4_free_mib={mib:.3f}")
PY
}

capture_vm_tunables "${OUT}/vm-tunables.txt"
capture_state before

printf '%s\n' "$(date +%s.%N)" >"${OUT}/compact-start-epoch.txt"
printf '1\n' | sudo -n tee /proc/sys/vm/compact_memory >/dev/null
printf '%s\n' "$(date +%s.%N)" >"${OUT}/compact-end-epoch.txt"

capture_state after
summarize_buddy "${OUT}/before-buddyinfo.txt" "${OUT}/after-buddyinfo.txt" \
    | tee "${OUT}/precompact-buddy-summary.txt"

set +e
ORCA_R11_OUT="${R11_OUT}" bash "${R11}" 2>&1 | tee "${OUT}/r11-control.log"
R11_RC=${PIPESTATUS[0]}
set -e
printf '%s\n' "${R11_RC}" >"${OUT}/r11.rc"

RUN_VALID="$(grep -E '^run_valid=' "${R11_OUT}/r11-summary.txt" 2>/dev/null | tail -1 | cut -d= -f2 || true)"
RM_OOM_COUNT="$(grep -E '^rm_oom_count=' "${R11_OUT}/r11-summary.txt" 2>/dev/null | tail -1 | cut -d= -f2 || true)"
RUN_VALID="${RUN_VALID:-0}"
RM_OOM_COUNT="${RM_OOM_COUNT:-0}"

ANALYZER_RC=0
if [[ "${RUN_VALID}" == 1 && "${RM_OOM_COUNT}" =~ ^[0-9]+$ && "${RM_OOM_COUNT}" -gt 0 ]]; then
    set +e
    python3 "${R11_ANALYZER}" --evidence "${R11_OUT}" >"${OUT}/allocator-state-analysis.txt" 2>&1
    ANALYZER_RC=$?
    python3 "${ZONE_ANALYZER}" --evidence "${R11_OUT}" >"${OUT}/zone-migratetype-analysis.txt" 2>&1
    ZONE_ANALYZER_RC=$?
    set -e
else
    ZONE_ANALYZER_RC=0
fi

{
    printf 'r11_rc=%s\n' "${R11_RC}"
    printf 'run_valid=%s\n' "${RUN_VALID}"
    printf 'rm_oom_count=%s\n' "${RM_OOM_COUNT}"
    printf 'allocator_analyzer_rc=%s\n' "${ANALYZER_RC}"
    printf 'zone_analyzer_rc=%s\n' "${ZONE_ANALYZER_RC}"
} >"${OUT}/r12-summary.txt"

printf '%s\n' "$(date --iso-8601=seconds)" >"${OUT}/r12-end-iso.txt"

printf '\n===== R12 pre-compaction summary =====\n'
cat "${OUT}/precompact-buddy-summary.txt"
printf '%s\n' '--- R11 result ---'
cat "${OUT}/r12-summary.txt"

if [[ "${R11_RC}" != 0 || "${RUN_VALID}" != 1 ]]; then
    printf 'ORCA_R12_RESULT=INVALID\n'
    exit 1
fi

if [[ "${RM_OOM_COUNT}" =~ ^[0-9]+$ && "${RM_OOM_COUNT}" -eq 0 ]]; then
    printf 'ORCA_R12_RESULT=VALID_CLEAN\n'
else
    printf 'ORCA_R12_RESULT=VALID_RM_OOM\n'
fi

printf 'ORCA_R12_EVIDENCE=%s\n' "${OUT}"
