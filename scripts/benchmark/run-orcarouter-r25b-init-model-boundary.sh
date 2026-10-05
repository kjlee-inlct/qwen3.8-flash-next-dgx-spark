#!/usr/bin/env bash
# R25b: reuse the validated R24 H6/R22-matched harness with a marker-only image
# and a unique experiment container/evidence path. Default mode is preflight.
set -Eeuo pipefail

MODE="${1:---preflight}"
[[ "${MODE}" == --preflight || "${MODE}" == run ]] || {
    echo "usage: $0 [--preflight|run]" >&2
    exit 2
}

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
R24_HARNESS="${SCRIPT_ROOT}/scripts/benchmark/run-orcarouter-hybrid-r24-kv16-rm-mitigation.sh"
IMAGE_CHECK="${SCRIPT_ROOT}/scripts/benchmark/check-orcarouter-r25b-init-model-image.sh"
ANALYZER="${SCRIPT_ROOT}/scripts/benchmark/analyze-orcarouter-r25b-init-model-overlap.py"
WAIT_READY="${SCRIPT_ROOT}/scripts/wait-ready.sh"
IMAGE="${ORCA_R25B_IMAGE:-vllm-orcarouter-v029-r25-init-marker:v1}"
EXPERIMENT_CONTAINER="${ORCA_R25B_CONTAINER:-qwen38-hybrid-r25b-init-marker}"
OUT="${ORCA_R25B_OUT:-/tmp/orcarouter-hybrid-r25b-init-model-boundary-01-20261005}"
PRESERVED_R24="${ORCA_R25B_PRESERVED_R24:-/tmp/orcarouter-hybrid-r24-kv16-rm-mitigation-01-20261004}"
TMP_HARNESS=""

fail() {
    printf 'ORCA_R25B_ERROR: %s\n' "$*" >&2
    exit 2
}

cleanup() {
    local rc=$?
    trap - EXIT INT TERM
    [[ -z "${TMP_HARNESS}" ]] || rm -f -- "${TMP_HARNESS}" >/dev/null 2>&1 || true
    exit "${rc}"
}
trap cleanup EXIT INT TERM

for command in bash python3 docker systemctl curl mktemp grep; do
    command -v "${command}" >/dev/null 2>&1 || fail "required command not found: ${command}"
done

[[ -r "${R24_HARNESS}" ]] || fail "R24 harness missing: ${R24_HARNESS}"
[[ -r "${IMAGE_CHECK}" ]] || fail "R25b image checker missing: ${IMAGE_CHECK}"
[[ -r "${ANALYZER}" ]] || fail "R25b analyzer missing: ${ANALYZER}"
[[ -r "${WAIT_READY}" ]] || fail "readiness waiter missing: ${WAIT_READY}"
[[ -d "${PRESERVED_R24}" ]] || fail "preserved R24 evidence missing: ${PRESERVED_R24}"
[[ "${OUT}" != "${PRESERVED_R24}" ]] || fail "R25b output must not reuse preserved R24 evidence"
[[ "${EXPERIMENT_CONTAINER}" != qwen38-hybrid-r24-kv16 ]] || fail "R25b must not reuse the R24 experiment container"
[[ "${EXPERIMENT_CONTAINER}" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || fail "invalid experiment container name"
[[ ! -e "${OUT}" ]] || fail "R25b evidence path already exists: ${OUT}"
if docker inspect "${EXPERIMENT_CONTAINER}" >/dev/null 2>&1; then
    fail "R25b experiment container already exists: ${EXPERIMENT_CONTAINER}"
fi

ORCA_R25B_IMAGE="${IMAGE}" bash "${IMAGE_CHECK}"

TMP_HARNESS="$(mktemp /tmp/r25b-r24-harness.XXXXXX.sh)"
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
        line = 'SCRIPT_ROOT="${ORCA_R25B_SCRIPT_ROOT:?ORCA_R25B_SCRIPT_ROOT required}"'
        counts["root"] += 1
    elif line.startswith("EXPERIMENT_CONTAINER="):
        line = f'EXPERIMENT_CONTAINER="{container}"'
        counts["container"] += 1
    elif line.startswith("GROUP="):
        line = 'GROUP="r25b_rm"'
        counts["group"] += 1

    if "r24_rm/" in line:
        counts["probe_defs"] += line.count("r24_rm/")
        line = line.replace("r24_rm/", "r25b_rm/")
    out.append(line)

expected = {"root": 1, "container": 1, "group": 1, "probe_defs": 4}
if counts != expected:
    raise SystemExit(f"R24 harness transform contract changed: {counts} != {expected}")
rendered = "\n".join(out) + "\n"
if "r24_rm/" in rendered:
    raise SystemExit("R25b transformed harness still contains r24_rm probe definitions")
if rendered.count("r25b_rm/") != 4:
    raise SystemExit("R25b transformed harness must contain exactly four r25b_rm probe definitions")
target.write_text(rendered, encoding="utf-8")
PY
chmod 700 "${TMP_HARNESS}"

grep -Fq 'GROUP="r25b_rm"' "${TMP_HARNESS}" || fail "R25b probe group transform missing"
[[ "$(grep -Fc 'r25b_rm/' "${TMP_HARNESS}")" == 4 ]] || fail "R25b probe definition transform count mismatch"
if grep -Fq 'r24_rm/' "${TMP_HARNESS}"; then
    fail "R24 probe definitions leaked into transformed R25b harness"
fi
printf 'r25b_probe_definition_contract=PASS\n'

run_underlying_preflight() {
    ORCA_R25B_SCRIPT_ROOT="${SCRIPT_ROOT}" \
    ORCA_R24_IMAGE="${IMAGE}" \
    ORCA_R24_OUT="${OUT}" \
    bash "${TMP_HARNESS}" --preflight
}

set +e
run_underlying_preflight
PREFLIGHT_RC=$?
set -e
if [[ "${PREFLIGHT_RC}" != 0 ]]; then
    printf 'R25B_LIVE_PREFLIGHT=FAIL underlying_rc=%s\n' "${PREFLIGHT_RC}" >&2
    exit "${PREFLIGHT_RC}"
fi

printf 'R25B_LIVE_PREFLIGHT=PASS\n'
printf 'candidate_image=%s\n' "${IMAGE}"
printf 'experiment_container=%s\n' "${EXPERIMENT_CONTAINER}"
printf 'evidence=%s\n' "${OUT}"
printf 'preserved_r24_evidence=%s\n' "${PRESERVED_R24}"
printf 'model_restart=NO\n'
printf 'managed_service_mutation=NO\n'
printf 'persistent_vm_tuning=NO\n'

if [[ "${MODE}" == --preflight ]]; then
    exit 0
fi

[[ "${ORCA_R25B_LIVE_ACK:-}" == YES ]] || fail "live run requires ORCA_R25B_LIVE_ACK=YES"
printf 'R25B_LIVE_GATE=OPEN\n'
printf 'model_restart=YES\n'
printf 'preserved_r24_evidence_reuse=NO\n'

set +e
ORCA_R25B_SCRIPT_ROOT="${SCRIPT_ROOT}" \
ORCA_R24_IMAGE="${IMAGE}" \
ORCA_R24_OUT="${OUT}" \
bash "${TMP_HARNESS}" run
HARNESS_RC=$?
set -e

ANALYZER_RC=125
if [[ -r "${OUT}/candidate-container.log" && -r "${OUT}/rm-trace.txt" ]]; then
    set +e
    python3 "${ANALYZER}" "${OUT}" >"${OUT}/r25b-init-model-overlap.txt"
    ANALYZER_RC=$?
    set -e
    printf '%s\n' "${ANALYZER_RC}" >"${OUT}/r25b-analyzer.rc"
fi

RESTORE_RC=125
if [[ -d "${OUT}" ]]; then
    set +e
    bash "${WAIT_READY}" --container qwen38-flash-next --timeout 1800 --interval 10 \
        >"${OUT}/managed-restore-wait-ready.log" 2>&1
    RESTORE_RC=$?
    set -e
    printf '%s\n' "${RESTORE_RC}" >"${OUT}/managed-restore-wait-ready.rc"
    curl -fsS --max-time 5 http://127.0.0.1:8888/v1/models \
        >"${OUT}/managed-restored-models.json" 2>"${OUT}/managed-restored-models.err" || true
fi

printf '\n===== R25b summary =====\n'
printf 'underlying_harness_rc=%s\n' "${HARNESS_RC}"
printf 'r25b_analyzer_rc=%s\n' "${ANALYZER_RC}"
printf 'managed_restore_ready_rc=%s\n' "${RESTORE_RC}"
if [[ -r "${OUT}/r24-summary.txt" ]]; then
    grep -E '^(run_valid|functional_class|host_stability_class|rm_oom_count|event_snapshot_count|predecessor_age_s|kv_bytes)=' \
        "${OUT}/r24-summary.txt" || true
fi
if [[ -r "${OUT}/r25b-init-model-overlap.txt" ]]; then
    cat "${OUT}/r25b-init-model-overlap.txt"
fi
printf 'evidence=%s\n' "${OUT}"

if [[ "${HARNESS_RC}" != 0 || "${ANALYZER_RC}" != 0 || "${RESTORE_RC}" != 0 ]]; then
    printf 'ORCA_R25B_RESULT=INVALID\n'
    exit 1
fi
printf 'ORCA_R25B_RESULT=VALID_MEASURED\n'
