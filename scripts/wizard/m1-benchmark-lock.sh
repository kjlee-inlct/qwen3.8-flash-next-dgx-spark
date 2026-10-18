#!/usr/bin/env bash
# Wizard-owned M1 shared lifecycle lock and exclusive benchmark lease; no runtime start.
# This script never starts a model or changes its configuration.
set -Eeuo pipefail

usage() {
  printf '%s\n' 'Usage: ./scripts/wizard/m1-benchmark-lock.sh -- COMMAND [ARGS...]' 'M1 session-specific shared lifecycle and exclusive benchmark lock with exact admission.'
}

if [[ "${1:-}" == --help || "${1:-}" == -h ]]; then usage; exit 0; fi
SLOT=historical
if [[ "${1:-}" == --session-slot ]]; then
  [[ "${2:-}" == reinstall ]] || {
    echo 'BENCH_M1=BLOCKED_INVALID_SESSION_SLOT' >&2; exit 2;
  }
  SLOT=reinstall
  shift 2
fi
if [[ "${1:-}" == -- ]]; then shift; fi
if (( $# == 0 )); then usage >&2; exit 2; fi

for tool in flock stat id; do
  command -v "$tool" >/dev/null 2>&1 || { echo "BENCH_WIZARD_LOCK=INVALID missing=$tool" >&2; exit 2; }
done

STATE_DIR="${XDG_STATE_HOME:-${HOME}/.local/state}/qwen38-spark"
LOCK="$STATE_DIR/operation.lock"
if [[ ! -d "$STATE_DIR" || -L "$STATE_DIR" || ! -f "$LOCK" || -L "$LOCK" || ! -r "$LOCK" ]]; then
  echo "BENCH_WIZARD_LOCK=INVALID unsafe_or_missing_existing_lock" >&2
  exit 2
fi
if [[ "$(stat -c %u -- "$LOCK")" != "$(id -u)" ]]; then
  echo "BENCH_WIZARD_LOCK=INVALID lock_owner_mismatch" >&2
  exit 2
fi

exec {BENCH_LOCK_FD}<"$LOCK"
if ! flock -n -s "$BENCH_LOCK_FD"; then
    echo "BENCH_WIZARD_LOCK=BUSY lifecycle_mutation_active" >&2
    exit 3
fi
M1_STATE="$STATE_DIR/mazinb-m1"
[[ "$SLOT" != reinstall ]] || M1_STATE="$STATE_DIR/mazinb-m1-reinstall"
M1_EXCLUSIVE="$M1_STATE/benchmark.lock"
if [[ ! -d "$M1_STATE" || -L "$M1_STATE" || "$(stat -c %u -- "$M1_STATE")" != "$(id -u)" ]]; then
    echo "BENCH_M1=BLOCKED unsafe_session_directory" >&2
    exit 2
fi
if [[ -L "$M1_EXCLUSIVE" || ( -e "$M1_EXCLUSIVE" && ! -f "$M1_EXCLUSIVE" ) ]]; then
    echo "BENCH_M1=BLOCKED unsafe_benchmark_lock" >&2
    exit 2
fi
if [[ ! -e "$M1_EXCLUSIVE" ]]; then
    (umask 077; set -C; : >"$M1_EXCLUSIVE") || { echo "BENCH_M1=BLOCKED lock_create_failed" >&2; exit 2; }
fi
  [[ "$(stat -c %u -- "$M1_EXCLUSIVE")" == "$(id -u)" ]] || {
    echo "BENCH_M1=BLOCKED benchmark_lock_owner_mismatch" >&2
    exit 2
  }
exec {BENCH_M1_FD}<"$M1_EXCLUSIVE"
if ! flock -n -x "$BENCH_M1_FD"; then
    echo "BENCH_M1=BUSY another_benchmark_active" >&2
    exit 3
fi
CONTROLLER="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)/scripts/runtime/mazinb-m1.py"
python3 "$CONTROLLER" bench-admission --session-slot "$SLOT" || { echo "BENCH_M1=BLOCKED attestation_failed" >&2; exit 2; }
export QWEN38_M1_BENCH_LEASE_HELD=1 QWEN38_M1_BENCH_SLOT="$SLOT"
echo "BENCH_M1=ATTESTED_SHARED_LIFECYCLE_EXCLUSIVE_BENCH" >&2
echo "BENCH_MODEL_START=NOT_PERFORMED_BY_WRAPPER" >&2
echo "BENCH_READY_AND_HOST_SAFETY=EXTERNAL_PREREQUISITES" >&2
rc=0
"$@" || rc=$?
if ! python3 "$CONTROLLER" bench-admission --session-slot "$SLOT"; then
  echo "BENCH_M1=POST_RUN_ATTESTATION_FAILED" >&2
  rc=2
fi
echo "BENCH_COMMAND_RC=$rc" >&2
exit "$rc"
