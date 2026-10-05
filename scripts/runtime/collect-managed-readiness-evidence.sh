#!/usr/bin/env bash
# Collect read-only evidence for a managed runtime that stopped before readiness.
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
UNIT="qwen38-flash-next.service"
CONTAINER="qwen38-flash-next"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
SINCE="2 hours ago"

usage() {
  cat <<'EOF'
Usage: bash scripts/runtime/collect-managed-readiness-evidence.sh [--since JOURNAL_TIME]

Examples:
  bash scripts/runtime/collect-managed-readiness-evidence.sh
  bash scripts/runtime/collect-managed-readiness-evidence.sh --since '2026-10-02 18:00:00'

The helper is read-only. Run `sudo -v` first if kernel-journal evidence is needed.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --since)
      [[ $# -ge 2 ]] || { printf 'ERROR: --since requires a value\n' >&2; exit 2; }
      SINCE="$2"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'ERROR: unknown argument: %s\n' "$1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

section() {
  printf '\n===== %s =====\n' "$1"
}

section "collection window"
printf 'since=%s\n' "${SINCE}"
printf 'collected_at=%s\n' "$(date --iso-8601=seconds)"

section "lifecycle transitions"
for helper in update-transition.sh runtime-transition.sh profile-switch-transition.sh; do
  printf '%s: ' "${helper}"
  bash "${ROOT_DIR}/scripts/${helper}" status 2>&1 || true
done

section "managed service state"
systemctl show "${UNIT}" \
  --property=ActiveState,SubState,Result,ExecMainCode,ExecMainStatus \
  --no-pager 2>&1 || true

section "managed service journal"
journalctl -u "${UNIT}" --since "${SINCE}" --no-pager -o short-iso 2>&1 | tail -n 300 || true

section "runtime memory monitor"
if [[ -r "${STATE_DIR}/monitor.log" ]]; then
  tail -n 300 "${STATE_DIR}/monitor.log" || true
else
  printf 'monitor log unavailable: %s\n' "${STATE_DIR}/monitor.log"
fi

section "runtime memory monitor signals"
if [[ -r "${STATE_DIR}/monitor.log" ]]; then
  grep -E 'monitor started|WARNING|PROTECT|recovered|HEARTBEAT|no longer running' \
    "${STATE_DIR}/monitor.log" | tail -n 200 || true
fi

section "matching containers"
docker ps -a --filter "name=${CONTAINER}" \
  --format 'table {{.Names}}\t{{.ID}}\t{{.Status}}\t{{.Image}}' 2>&1 || true

section "canonical container state"
if docker inspect "${CONTAINER}" >/dev/null 2>&1; then
  docker inspect --format \
    'name={{.Name}} id={{.Id}} state={{.State.Status}} exit={{.State.ExitCode}} oom_killed={{.State.OOMKilled}} error={{json .State.Error}} started={{.State.StartedAt}} finished={{.State.FinishedAt}} image={{.Config.Image}}' \
    "${CONTAINER}" 2>&1 || true
  printf '%s\n' '--- recent canonical container logs ---'
  docker logs --timestamps --tail 250 "${CONTAINER}" 2>&1 || true
else
  printf 'canonical container unavailable: %s\n' "${CONTAINER}"
fi

section "kernel RM/OOM signals"
if sudo -n true 2>/dev/null; then
  sudo -n journalctl -k --since "${SINCE}" --no-pager 2>&1 |
    grep -E 'NVRM|NV_ERR_NO_MEMORY|_memdescAllocInternal|Out of memory|oom-kill|Killed process' |
    tail -n 200 || true
else
  printf 'sudo credential unavailable; run `sudo -v` and rerun to include kernel evidence.\n'
fi
