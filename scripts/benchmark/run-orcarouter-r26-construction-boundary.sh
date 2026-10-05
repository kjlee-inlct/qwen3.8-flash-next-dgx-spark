#!/usr/bin/env bash
# R26: reuse the validated R24 H6/R22-matched RM harness with marker-only
# constructor/ModelOpt-MoE instrumentation. Default mode is preflight.
set -Eeuo pipefail

MODE="${1:---preflight}"
[[ "${MODE}" == --preflight || "${MODE}" == run ]] || {
    echo "usage: $0 [--preflight|run]" >&2
    exit 2
}

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
R24_HARNESS="${SCRIPT_ROOT}/scripts/benchmark/run-orcarouter-hybrid-r24-kv16-rm-mitigation.sh"
IMAGE_CHECK="${SCRIPT_ROOT}/scripts/benchmark/check-orcarouter-r26-construction-image.sh"
ANALYZER="${SCRIPT_ROOT}/scripts/benchmark/analyze-orcarouter-r26-construction-overlap.py"
WAIT_READY="${SCRIPT_ROOT}/scripts/wait-ready.sh"
IMAGE="${ORCA_R26_IMAGE:-vllm-orcarouter-v029-r26-construction-marker:v1}"
EXPERIMENT_CONTAINER="${ORCA_R26_CONTAINER:-qwen38-hybrid-r26-construction-marker}"
OUT="${ORCA_R26_OUT:-/tmp/orcarouter-hybrid-r26-construction-boundary-01-20261005}"
PRESERVED_R24="${ORCA_R26_PRESERVED_R24:-/tmp/orcarouter-hybrid-r24-kv16-rm-mitigation-01-20261004}"
MANAGED_SERVED_NAME="${ORCA_R26_MANAGED_SERVED_NAME:-orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4}"
TMP_HARNESS=""

fail() {
    printf 'ORCA_R26_ERROR: %s\n' "$*" >&2
    exit 2
}

cleanup() {
    local rc=$?
    trap - EXIT INT TERM
    [[ -z "${TMP_HARNESS}" ]] || rm -f -- "${TMP_HARNESS}" >/dev/null 2>&1 || true
    exit "${rc}"
}
trap cleanup EXIT INT TERM

for command in bash python3 docker systemctl curl mktemp grep sudo; do
    command -v "${command}" >/dev/null 2>&1 || fail "required command not found: ${command}"
done
sudo -n true >/dev/null 2>&1 || fail "sudo timestamp unavailable; run sudo -v first"

[[ -r "${R24_HARNESS}" ]] || fail "R24 harness missing: ${R24_HARNESS}"
[[ -r "${IMAGE_CHECK}" ]] || fail "R26 image checker missing: ${IMAGE_CHECK}"
[[ -r "${ANALYZER}" ]] || fail "R26 analyzer missing: ${ANALYZER}"
[[ -r "${WAIT_READY}" ]] || fail "readiness waiter missing: ${WAIT_READY}"
[[ -d "${PRESERVED_R24}" ]] || fail "preserved R24 evidence missing: ${PRESERVED_R24}"
[[ "${OUT}" != "${PRESERVED_R24}" ]] || fail "R26 output must not reuse preserved R24 evidence"
[[ "${EXPERIMENT_CONTAINER}" != qwen38-hybrid-r24-kv16 ]] || fail "R26 must not reuse the R24 experiment container"
[[ "${EXPERIMENT_CONTAINER}" != qwen38-hybrid-r25b-init-marker ]] || fail "R26 must not reuse the R25b experiment container"
[[ "${EXPERIMENT_CONTAINER}" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || fail "invalid experiment container name"
[[ ! -e "${OUT}" ]] || fail "R26 evidence path already exists: ${OUT}"
if docker inspect "${EXPERIMENT_CONTAINER}" >/dev/null 2>&1; then
    fail "R26 experiment container already exists: ${EXPERIMENT_CONTAINER}"
fi

TRACEFS="/sys/kernel/tracing"
if [[ ! -e "${TRACEFS}/kprobe_events" ]]; then
    TRACEFS="/sys/kernel/debug/tracing"
fi
[[ -e "${TRACEFS}/kprobe_events" ]] || fail "kprobe_events unavailable"
for stale_group in r24_rm r25b_rm r26_rm; do
    if sudo -n test -d "${TRACEFS}/events/${stale_group}"; then
        fail "stale kprobe group present: ${stale_group}; clean exact failed-attempt probe state first"
    fi
done
printf 'stale_probe_groups=NONE\n'

ORCA_R26_IMAGE="${IMAGE}" bash "${IMAGE_CHECK}"

TMP_HARNESS="$(mktemp /tmp/r26-r24-harness.XXXXXX.sh)"
python3 - "${R24_HARNESS}" "${TMP_HARNESS}" "${EXPERIMENT_CONTAINER}" <<'PY'
from __future__ import annotations

import pathlib
import sys

source = pathlib.Path(sys.argv[1])
target = pathlib.Path(sys.argv[2])
container = sys.argv[3]
lines = source.read_text(encoding="utf-8").splitlines()
counts = {"root": 0, "container": 0, "group": 0, "probe_defs": 0}
out: list[str] = []
for line in lines:
    if line.startswith("SCRIPT_ROOT="):
        line = 'SCRIPT_ROOT="${ORCA_R26_SCRIPT_ROOT:?ORCA_R26_SCRIPT_ROOT required}"'
        counts["root"] += 1
    elif line.startswith("EXPERIMENT_CONTAINER="):
        line = f'EXPERIMENT_CONTAINER="{container}"'
        counts["container"] += 1
    elif line.startswith("GROUP="):
        line = 'GROUP="r26_rm"'
        counts["group"] += 1

    if "r24_rm/" in line:
        counts["probe_defs"] += line.count("r24_rm/")
        line = line.replace("r24_rm/", "r26_rm/")
    out.append(line)

expected = {"root": 1, "container": 1, "group": 1, "probe_defs": 4}
if counts != expected:
    raise SystemExit(f"R24 harness transform contract changed: {counts} != {expected}")
rendered = "\n".join(out) + "\n"
if "r24_rm/" in rendered:
    raise SystemExit("R26 transformed harness still contains r24_rm probe definitions")
if rendered.count("r26_rm/") != 4:
    raise SystemExit("R26 transformed harness must contain exactly four r26_rm probe definitions")
target.write_text(rendered, encoding="utf-8")
PY
chmod 700 "${TMP_HARNESS}"

grep -Fq 'GROUP="r26_rm"' "${TMP_HARNESS}" || fail "R26 probe group transform missing"
[[ "$(grep -Fc 'r26_rm/' "${TMP_HARNESS}")" == 4 ]] || fail "R26 probe definition transform count mismatch"
if grep -Fq 'r24_rm/' "${TMP_HARNESS}"; then
    fail "R24 probe definitions leaked into transformed R26 harness"
fi
printf 'r26_probe_definition_contract=PASS\n'

run_underlying_preflight() {
    ORCA_R26_SCRIPT_ROOT="${SCRIPT_ROOT}" \
    ORCA_R24_IMAGE="${IMAGE}" \
    ORCA_R24_OUT="${OUT}" \
    bash "${TMP_HARNESS}" --preflight
}

set +e
run_underlying_preflight
PREFLIGHT_RC=$?
set -e
if [[ "${PREFLIGHT_RC}" != 0 ]]; then
    printf 'R26_LIVE_PREFLIGHT=FAIL underlying_rc=%s\n' "${PREFLIGHT_RC}" >&2
    exit "${PREFLIGHT_RC}"
fi

printf 'R26_LIVE_PREFLIGHT=PASS\n'
printf 'candidate_image=%s\n' "${IMAGE}"
printf 'experiment_container=%s\n' "${EXPERIMENT_CONTAINER}"
printf 'evidence=%s\n' "${OUT}"
printf 'preserved_r24_evidence=%s\n' "${PRESERVED_R24}"
printf 'managed_served_name=%s\n' "${MANAGED_SERVED_NAME}"
printf 'model_restart=NO\n'
printf 'managed_service_mutation=NO\n'
printf 'persistent_vm_tuning=NO\n'

if [[ "${MODE}" == --preflight ]]; then
    exit 0
fi

[[ "${ORCA_R26_LIVE_ACK:-}" == YES ]] || fail "live run requires ORCA_R26_LIVE_ACK=YES"
printf 'R26_LIVE_GATE=OPEN\n'
printf 'model_restart=YES\n'
printf 'preserved_r24_evidence_reuse=NO\n'

set +e
ORCA_R26_SCRIPT_ROOT="${SCRIPT_ROOT}" \
ORCA_R24_IMAGE="${IMAGE}" \
ORCA_R24_OUT="${OUT}" \
bash "${TMP_HARNESS}" run
HARNESS_RC=$?
set -e

ANALYZER_RC=125
if [[ -r "${OUT}/candidate-container.log" && -r "${OUT}/rm-trace.txt" ]]; then
    set +e
    python3 "${ANALYZER}" "${OUT}" >"${OUT}/r26-construction-overlap.txt"
    ANALYZER_RC=$?
    set -e
    printf '%s\n' "${ANALYZER_RC}" >"${OUT}/r26-analyzer.rc"
fi

RESTORE_RC=125
if [[ -d "${OUT}" ]]; then
    set +e
    bash "${WAIT_READY}" \
        --container qwen38-flash-next \
        --model "${MANAGED_SERVED_NAME}" \
        --timeout 1800 \
        --interval 10 \
        >"${OUT}/managed-restore-wait-ready.log" 2>&1
    RESTORE_RC=$?
    set -e
    printf '%s\n' "${RESTORE_RC}" >"${OUT}/managed-restore-wait-ready.rc"
    curl -fsS --max-time 5 http://127.0.0.1:8888/v1/models \
        >"${OUT}/managed-restored-models.json" 2>"${OUT}/managed-restored-models.err" || true
fi

printf '\n===== R26 summary =====\n'
printf 'underlying_harness_rc=%s\n' "${HARNESS_RC}"
printf 'r26_analyzer_rc=%s\n' "${ANALYZER_RC}"
printf 'managed_restore_ready_rc=%s\n' "${RESTORE_RC}"
if [[ -r "${OUT}/r24-summary.txt" ]]; then
    grep -E '^(run_valid|functional_class|host_stability_class|rm_oom_count|event_snapshot_count|predecessor_age_s|kv_bytes)=' \
        "${OUT}/r24-summary.txt" || true
fi
if [[ -r "${OUT}/r26-construction-overlap.txt" ]]; then
    cat "${OUT}/r26-construction-overlap.txt"
fi
printf 'evidence=%s\n' "${OUT}"

if [[ "${HARNESS_RC}" != 0 || "${ANALYZER_RC}" != 0 || "${RESTORE_RC}" != 0 ]]; then
    printf 'ORCA_R26_RESULT=INVALID\n'
    exit 1
fi
printf 'ORCA_R26_RESULT=VALID_MEASURED\n'
