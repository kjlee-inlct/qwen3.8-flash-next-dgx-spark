#!/usr/bin/env bash
# Serializes future measured benchmarks against the existing wizard lifecycle lock.
# This script never starts a model, installs packages or qualifies host safety.
set -Eeuo pipefail

usage() {
  printf '%s\n' 'Usage: ./scripts/benchmark/with-wizard-lock.sh -- COMMAND [ARGS...]' 'Requires the EXISTING wizard operation lock. No model start or readiness test.'
}

if [[ "${1:-}" == --help || "${1:-}" == -h ]]; then usage; exit 0; fi
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
if ! flock -n -x "$BENCH_LOCK_FD"; then
  echo "BENCH_WIZARD_LOCK=BUSY wizard_or_benchmark_active" >&2
  exit 3
fi
echo "BENCH_WIZARD_LOCK=ACQUIRED" >&2
echo "BENCH_MODEL_START=NOT_PERFORMED_BY_WRAPPER" >&2
echo "BENCH_READY_AND_HOST_SAFETY=EXTERNAL_PREREQUISITES" >&2
rc=0
"$@" || rc=$?
echo "BENCH_COMMAND_RC=$rc" >&2
exit "$rc"
