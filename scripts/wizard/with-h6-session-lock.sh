#!/usr/bin/env bash
# Terminal B: exact H6 supervised-session admission and benchmark locks.
set -Eeuo pipefail
[[ "${1:-}" == -- ]] && shift
if (( $# == 0 )); then
  printf 'Usage: bash scripts/wizard/with-h6-session-lock.sh -- COMMAND [ARGS...]\n' >&2
  exit 2
fi
for utility in flock stat id python3; do
  command -v "$utility" >/dev/null || { echo "H6_BENCH_LOCK=INVALID missing=$utility" >&2; exit 2; }
done
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE="${XDG_STATE_HOME:-${HOME}/.local/state}/qwen38-spark"
LOCK="$STATE/operation.lock"
TRIAL="$STATE/hybrid-h6-m1"
BENCH_LOCK="$TRIAL/benchmark.lock"
for path in "$STATE" "$TRIAL"; do
  [[ -d "$path" && ! -L "$path" && "$(stat -c %u "$path")" == "$(id -u)" ]] || {
    echo "H6_BENCH_LOCK=INVALID state_dir_untrusted" >&2
    exit 2
  }
done
for path in "$LOCK" "$BENCH_LOCK"; do
  [[ -f "$path" && ! -L "$path" && "$(stat -c %u "$path")" == "$(id -u)" ]] || {
    echo "H6_BENCH_LOCK=INVALID lock_untrusted" >&2
    exit 2
  }
done
exec {H6_OPERATION_FD}<"$LOCK"
flock -n -s "$H6_OPERATION_FD" || { echo "H6_BENCH_LOCK=LIFECYCLE_BUSY" >&2; exit 3; }
exec {H6_BENCHMARK_FD}<"$BENCH_LOCK"
flock -n -x "$H6_BENCHMARK_FD" || { echo "H6_BENCH_LOCK=OTHER_BENCH_RUNNING" >&2; exit 3; }
python3 -B "$ROOT/scripts/wizard/hybrid-h6-m1.py" bench-admission || {
  echo "H6_BENCH_LOCK=BLOCKED_SESSION_NOT_READY" >&2
  exit 2
}
echo "H6_BENCH_LOCK=ACQUIRED_EXACT_SESSION" >&2
echo "H6_BENCH_MODEL_START=NOT_PERFORMED_BY_WRAPPER" >&2
rc=0
"$@" || rc=$?
echo "H6_BENCH_COMMAND_RC=$rc" >&2
exit "$rc"
