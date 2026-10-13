#!/usr/bin/env bash
# Serializes future measured benchmarks against the existing wizard lifecycle lock.
# This script never starts a model, installs packages or qualifies host safety.
set -Eeuo pipefail

usage() {
  printf '%s\n' 'Usage: ./scripts/benchmark/with-wizard-lock.sh [--m1-benchmark] -- COMMAND [ARGS...]' 'Default: exclusive lifecycle lock; M1: shared lifecycle lock plus exclusive benchmark lock and pinned session attestation.'
}

if [[ "${1:-}" == --help || "${1:-}" == -h ]]; then usage; exit 0; fi
M1_BENCHMARK=0
if [[ "${1:-}" == --m1-benchmark ]]; then M1_BENCHMARK=1; shift; fi
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
if [[ "${M1_BENCHMARK}" == 1 ]]; then
  if ! flock -n -s "$BENCH_LOCK_FD"; then
    echo "BENCH_WIZARD_LOCK=BUSY lifecycle_mutation_active" >&2
    exit 3
  fi
  M1_STATE="$STATE_DIR/mazinb-m1"
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
  python3 "$CONTROLLER" bench-admission || { echo "BENCH_M1=BLOCKED attestation_failed" >&2; exit 2; }
  echo "BENCH_M1=ATTESTED_SHARED_LIFECYCLE_EXCLUSIVE_BENCH" >&2
else
  if ! flock -n -x "$BENCH_LOCK_FD"; then
    echo "BENCH_WIZARD_LOCK=BUSY wizard_or_benchmark_active" >&2
    exit 3
  fi
  echo "BENCH_WIZARD_LOCK=ACQUIRED" >&2
fi
echo "BENCH_MODEL_START=NOT_PERFORMED_BY_WRAPPER" >&2
echo "BENCH_READY_AND_HOST_SAFETY=EXTERNAL_PREREQUISITES" >&2
rc=0
"$@" || rc=$?
if [[ "${M1_BENCHMARK}" == 1 ]]; then
  if ! python3 "$CONTROLLER" bench-admission; then
    echo "BENCH_M1=POST_RUN_ATTESTATION_FAILED" >&2
    rc=2
  fi
fi
echo "BENCH_COMMAND_RC=$rc" >&2
exit "$rc"
