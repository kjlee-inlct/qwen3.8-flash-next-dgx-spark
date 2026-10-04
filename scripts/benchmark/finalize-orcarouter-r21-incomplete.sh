#!/usr/bin/env bash
# Finalize an R21 run that completed the managed replacement but exited before
# writing kernel-window/validity/summary evidence (for example, sudo expiry).

set -Eeuo pipefail

OUT="${ORCA_R21_OUT:-/tmp/orcarouter-managed-rmsys-r21-pagecache-reclaim-compact-01-20261004}"
UNIT="qwen38-flash-next.service"
CONTAINER="qwen38-flash-next"
STATE_OUT="${OUT}/allocator-state"

fail() {
    printf 'ORCA_R21_FINALIZE_ERROR: %s\n' "$*" >&2
    exit 2
}

for command in sudo systemctl docker curl journalctl date grep find wc python3; do
    command -v "${command}" >/dev/null 2>&1 || fail "required command not found: ${command}"
done
sudo -n true >/dev/null 2>&1 || fail "sudo timestamp unavailable; run sudo -v first"
[[ -d "${OUT}" ]] || fail "R21 evidence directory missing: ${OUT}"

for required in \
    start-epoch.txt \
    end-epoch.txt \
    container-id-before.txt \
    predecessor-age-s.txt \
    minimum-predecessor-age-s.txt \
    managed-command.rc \
    collector.rc; do
    [[ -s "${OUT}/${required}" ]] || fail "required evidence missing: ${OUT}/${required}"
done

START_EPOCH="$(cat "${OUT}/start-epoch.txt")"
END_EPOCH="$(cat "${OUT}/end-epoch.txt")"
PRE_CONTAINER_ID="$(cat "${OUT}/container-id-before.txt")"
PREDECESSOR_AGE_S="$(cat "${OUT}/predecessor-age-s.txt")"
MIN_PREDECESSOR_AGE_S="$(cat "${OUT}/minimum-predecessor-age-s.txt")"
MANAGED_RC="$(cat "${OUT}/managed-command.rc")"
COLLECTOR_RC="$(cat "${OUT}/collector.rc")"

START_SEC="${START_EPOCH%%.*}"
END_SEC="$(( ${END_EPOCH%%.*} + 2 ))"
START_JOURNAL="$(date -d "@${START_SEC}" '+%Y-%m-%d %H:%M:%S')"
END_JOURNAL="$(date -d "@${END_SEC}" '+%Y-%m-%d %H:%M:%S')"

sudo -n journalctl -k --since "${START_JOURNAL}" --until "${END_JOURNAL}" \
    -o short-iso-precise --no-pager >"${OUT}/kernel-window.txt"
ERROR_RE='NV_ERR_NO_MEMORY|_memdescAllocInternal|NVRM:.*Xid|Xid \(PCI|GPU has fallen off the bus|oom-kill:|Out of memory:|Killed process '
grep -Ei "${ERROR_RE}" "${OUT}/kernel-window.txt" >"${OUT}/kernel-errors.txt" || true
RM_OOM_COUNT="$(grep -Ec 'NV_ERR_NO_MEMORY|_memdescAllocInternal' "${OUT}/kernel-errors.txt" 2>/dev/null || true)"
EVENT_SNAPSHOT_COUNT="$(find "${STATE_OUT}/events" -mindepth 1 -maxdepth 1 -type d -name 'rm-oom-*' 2>/dev/null | wc -l)"

POST_CONTAINER_ID="$(docker inspect --format '{{.Id}}' "${CONTAINER}" 2>/dev/null || true)"
POST_CONTAINER_STARTED="$(docker inspect --format '{{.State.StartedAt}}' "${CONTAINER}" 2>/dev/null || true)"
[[ -n "${POST_CONTAINER_ID}" && -n "${POST_CONTAINER_STARTED}" ]] || fail "current managed container is unavailable"

POST_STARTED_EPOCH="$(python3 - "${POST_CONTAINER_STARTED}" <<'PY'
import datetime as dt
import sys
print(dt.datetime.fromisoformat(sys.argv[1].replace('Z', '+00:00')).timestamp())
PY
)"

CANDIDATE_IN_WINDOW="$(python3 - "${POST_STARTED_EPOCH}" "${START_EPOCH}" "${END_EPOCH}" <<'PY'
import sys
started, begin, end = map(float, sys.argv[1:])
print(1 if begin <= started <= end else 0)
PY
)"

printf '%s\n' "${POST_CONTAINER_ID}" >"${OUT}/container-id-after.txt"
printf '%s\n' "${POST_CONTAINER_STARTED}" >"${OUT}/container-started-after.txt"
printf '%s\n' "${CANDIDATE_IN_WINDOW}" >"${OUT}/candidate-started-in-run-window.txt"

RESTART_OBSERVED=0
if [[ "${CANDIDATE_IN_WINDOW}" == 1 && "${POST_CONTAINER_ID}" != "${PRE_CONTAINER_ID}" ]]; then
    RESTART_OBSERVED=1
fi
printf '%s\n' "${RESTART_OBSERVED}" >"${OUT}/restart-observed.txt"

API_READY=0
if [[ "${CANDIDATE_IN_WINDOW}" == 1 ]] \
    && systemctl is-active --quiet "${UNIT}" \
    && curl -fsS --max-time 5 http://127.0.0.1:8888/health >/dev/null 2>&1; then
    API_READY=1
fi
printf '%s\n' "${API_READY}" >"${OUT}/api-ready.txt"

RUN_VALID=1
if [[ "${MANAGED_RC}" != 0 || "${COLLECTOR_RC}" != 0 || "${RESTART_OBSERVED}" != 1 || "${API_READY}" != 1 ]]; then
    RUN_VALID=0
fi
printf '%s\n' "${RUN_VALID}" >"${OUT}/run-valid.txt"

{
    printf 'run_valid=%s\n' "${RUN_VALID}"
    printf 'managed_rc=%s\n' "${MANAGED_RC}"
    printf 'collector_rc=%s\n' "${COLLECTOR_RC}"
    printf 'restart_observed=%s\n' "${RESTART_OBSERVED}"
    printf 'api_ready=%s\n' "${API_READY}"
    printf 'candidate_started_in_run_window=%s\n' "${CANDIDATE_IN_WINDOW}"
    printf 'predecessor_age_s=%s\n' "${PREDECESSOR_AGE_S}"
    printf 'minimum_predecessor_age_s=%s\n' "${MIN_PREDECESSOR_AGE_S}"
    printf 'rm_oom_count=%s\n' "${RM_OOM_COUNT}"
    printf 'event_snapshot_count=%s\n' "${EVENT_SNAPSHOT_COUNT}"
} >"${OUT}/r21-summary.txt"

printf '\n===== R21 finalized summary =====\n'
cat "${OUT}/r21-summary.txt"
printf '%s\n' '--- kernel errors ---'
cat "${OUT}/kernel-errors.txt" || true
printf 'evidence=%s\n' "${OUT}"

if [[ "${RUN_VALID}" != 1 ]]; then
    printf 'ORCA_R21_FINAL_RESULT=INVALID\n'
    exit 1
fi
if [[ "${RM_OOM_COUNT}" == 0 ]]; then
    printf 'ORCA_R21_FINAL_RESULT=VALID_CLEAN\n'
else
    printf 'ORCA_R21_FINAL_RESULT=VALID_RM_OOM\n'
fi
