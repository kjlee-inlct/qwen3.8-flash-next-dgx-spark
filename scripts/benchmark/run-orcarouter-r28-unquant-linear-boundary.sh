#!/usr/bin/env bash
# R28: reuse the validated R24 H6/R22-matched RM harness with marker-only
# UnquantizedLinearMethod.create_weights instrumentation. Default is preflight.
set -Eeuo pipefail

MODE="${1:---preflight}"
[[ "${MODE}" == --preflight || "${MODE}" == run ]] || {
    echo "usage: $0 [--preflight|run]" >&2
    exit 2
}

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
R24_HARNESS="${SCRIPT_ROOT}/scripts/benchmark/run-orcarouter-hybrid-r24-kv16-rm-mitigation.sh"
IMAGE_CHECK="${SCRIPT_ROOT}/scripts/benchmark/check-orcarouter-r28-unquant-linear-image.sh"
ANALYZER="${SCRIPT_ROOT}/scripts/benchmark/analyze-orcarouter-r28-unquant-linear-overlap.py"
WAIT_READY="${SCRIPT_ROOT}/scripts/wait-ready.sh"
IMAGE="${ORCA_R28_IMAGE:-vllm-orcarouter-v029-r28-unquant-linear-marker:v1}"
EXPERIMENT_CONTAINER="${ORCA_R28_CONTAINER:-qwen38-hybrid-r28-unquant-linear-marker}"
OUT="${ORCA_R28_OUT:-/tmp/orcarouter-hybrid-r28-unquant-linear-boundary-01-20261005}"
PRESERVED_R24="${ORCA_R28_PRESERVED_R24:-/tmp/orcarouter-hybrid-r24-kv16-rm-mitigation-01-20261004}"
PRESERVED_R26="${ORCA_R28_PRESERVED_R26:-/tmp/orcarouter-hybrid-r26-construction-boundary-01-20261005}"
PRESERVED_R27="${ORCA_R28_PRESERVED_R27:-/tmp/orcarouter-hybrid-r27-linear-boundary-01-20261005}"
MANAGED_SERVED_NAME="${ORCA_R28_MANAGED_SERVED_NAME:-orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4}"
TMP_HARNESS=""

fail() {
    printf 'ORCA_R28_ERROR: %s\n' "$*" >&2
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
[[ -r "${IMAGE_CHECK}" ]] || fail "R28 image checker missing: ${IMAGE_CHECK}"
[[ -r "${ANALYZER}" ]] || fail "R28 analyzer missing: ${ANALYZER}"
[[ -r "${WAIT_READY}" ]] || fail "readiness waiter missing: ${WAIT_READY}"
for preserved in "${PRESERVED_R24}" "${PRESERVED_R26}" "${PRESERVED_R27}"; do
    [[ -d "${preserved}" ]] || fail "preserved evidence missing: ${preserved}"
    [[ "${OUT}" != "${preserved}" ]] || fail "R28 output must not reuse preserved evidence"
done
for reserved in \
    qwen38-hybrid-r24-kv16 \
    qwen38-hybrid-r25b-init-marker \
    qwen38-hybrid-r26-construction-marker \
    qwen38-hybrid-r27-linear-marker; do
    [[ "${EXPERIMENT_CONTAINER}" != "${reserved}" ]] || fail "R28 must not reuse experiment container: ${reserved}"
done
[[ "${EXPERIMENT_CONTAINER}" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || fail "invalid experiment container name"
[[ ! -e "${OUT}" ]] || fail "R28 evidence path already exists: ${OUT}"
if docker inspect "${EXPERIMENT_CONTAINER}" >/dev/null 2>&1; then
    fail "R28 experiment container already exists: ${EXPERIMENT_CONTAINER}"
fi

TRACEFS="/sys/kernel/tracing"
if [[ ! -e "${TRACEFS}/kprobe_events" ]]; then
    TRACEFS="/sys/kernel/debug/tracing"
fi
[[ -e "${TRACEFS}/kprobe_events" ]] || fail "kprobe_events unavailable"
for stale_group in r24_rm r25b_rm r26_rm r27_rm r28_rm; do
    if sudo -n test -d "${TRACEFS}/events/${stale_group}"; then
        fail "stale kprobe group present: ${stale_group}; clean exact failed-attempt probe state first"
    fi
done
printf 'stale_probe_groups=NONE\n'

ORCA_R28_IMAGE="${IMAGE}" bash "${IMAGE_CHECK}"

TMP_HARNESS="$(mktemp /tmp/r28-r24-harness.XXXXXX.sh)"
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
        line = 'SCRIPT_ROOT="${ORCA_R28_SCRIPT_ROOT:?ORCA_R28_SCRIPT_ROOT required}"'
        counts["root"] += 1
    elif line.startswith("EXPERIMENT_CONTAINER="):
        line = f'EXPERIMENT_CONTAINER="{container}"'
        counts["container"] += 1
    elif line.startswith("GROUP="):
        line = 'GROUP="r28_rm"'
        counts["group"] += 1

    if "r24_rm/" in line:
        counts["probe_defs"] += line.count("r24_rm/")
        line = line.replace("r24_rm/", "r28_rm/")
    out.append(line)

expected = {"root": 1, "container": 1, "group": 1, "probe_defs": 4}
if counts != expected:
    raise SystemExit(f"R24 harness transform contract changed: {counts} != {expected}")
rendered = "\n".join(out) + "\n"
if "r24_rm/" in rendered:
    raise SystemExit("R28 transformed harness still contains r24_rm probe definitions")
if rendered.count("r28_rm/") != 4:
    raise SystemExit("R28 transformed harness must contain exactly four r28_rm probe definitions")
target.write_text(rendered, encoding="utf-8")
PY
chmod 700 "${TMP_HARNESS}"

grep -Fq 'GROUP="r28_rm"' "${TMP_HARNESS}" || fail "R28 probe group transform missing"
[[ "$(grep -Fc 'r28_rm/' "${TMP_HARNESS}")" == 4 ]] || fail "R28 probe definition transform count mismatch"
if grep -Fq 'r24_rm/' "${TMP_HARNESS}"; then
    fail "R24 probe definitions leaked into transformed R28 harness"
fi
printf 'r28_probe_definition_contract=PASS\n'

run_underlying_preflight() {
    ORCA_R28_SCRIPT_ROOT="${SCRIPT_ROOT}" \
    ORCA_R24_IMAGE="${IMAGE}" \
    ORCA_R24_OUT="${OUT}" \
    bash "${TMP_HARNESS}" --preflight
}

set +e
run_underlying_preflight
PREFLIGHT_RC=$?
set -e
if [[ "${PREFLIGHT_RC}" != 0 ]]; then
    printf 'R28_LIVE_PREFLIGHT=FAIL underlying_rc=%s\n' "${PREFLIGHT_RC}" >&2
    exit "${PREFLIGHT_RC}"
fi

printf 'R28_LIVE_PREFLIGHT=PASS\n'
printf 'candidate_image=%s\n' "${IMAGE}"
printf 'experiment_container=%s\n' "${EXPERIMENT_CONTAINER}"
printf 'evidence=%s\n' "${OUT}"
printf 'preserved_r24_evidence=%s\n' "${PRESERVED_R24}"
printf 'preserved_r26_evidence=%s\n' "${PRESERVED_R26}"
printf 'preserved_r27_evidence=%s\n' "${PRESERVED_R27}"
printf 'managed_served_name=%s\n' "${MANAGED_SERVED_NAME}"
printf 'model_restart=NO\n'
printf 'managed_service_mutation=NO\n'
printf 'persistent_vm_tuning=NO\n'

if [[ "${MODE}" == --preflight ]]; then
    exit 0
fi

[[ "${ORCA_R28_LIVE_ACK:-}" == YES ]] || fail "live run requires ORCA_R28_LIVE_ACK=YES"
printf 'R28_LIVE_GATE=OPEN\n'
printf 'model_restart=YES\n'
printf 'preserved_evidence_reuse=NO\n'

set +e
ORCA_R28_SCRIPT_ROOT="${SCRIPT_ROOT}" \
ORCA_R24_IMAGE="${IMAGE}" \
ORCA_R24_OUT="${OUT}" \
bash "${TMP_HARNESS}" run
HARNESS_RC=$?
set -e

ANALYZER_RC=125
if [[ -r "${OUT}/candidate-container.log" && -r "${OUT}/rm-trace.txt" ]]; then
    set +e
    python3 "${ANALYZER}" "${OUT}" >"${OUT}/r28-unquant-linear-overlap.txt"
    ANALYZER_RC=$?
    set -e
    printf '%s\n' "${ANALYZER_RC}" >"${OUT}/r28-analyzer.rc"
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

printf '\n===== R28 summary =====\n'
printf 'underlying_harness_rc=%s\n' "${HARNESS_RC}"
printf 'r28_analyzer_rc=%s\n' "${ANALYZER_RC}"
printf 'managed_restore_ready_rc=%s\n' "${RESTORE_RC}"
if [[ -r "${OUT}/r24-summary.txt" ]]; then
    grep -E '^(run_valid|functional_class|host_stability_class|rm_oom_count|event_snapshot_count|predecessor_age_s|kv_bytes)=' \
        "${OUT}/r24-summary.txt" || true
fi
if [[ -r "${OUT}/r28-unquant-linear-overlap.txt" ]]; then
    cat "${OUT}/r28-unquant-linear-overlap.txt"
fi
printf 'evidence=%s\n' "${OUT}"

if [[ "${HARNESS_RC}" != 0 || "${ANALYZER_RC}" != 0 || "${RESTORE_RC}" != 0 ]]; then
    printf 'ORCA_R28_RESULT=INVALID\n'
    exit 1
fi
printf 'ORCA_R28_RESULT=VALID_MEASURED\n'
