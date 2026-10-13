#!/usr/bin/env bash
# Read-only benchmark entry. Does not start models, download, or fabricate JSON.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
action="${1:-status}"
case "$action" in
  status)
    echo "=== Benchmark admission (read-only) ==="
    echo "MEASUREMENT=NOT_RUN"
    echo "MODEL_LAUNCH=NOT_PERFORMED"
    echo "MANAGED_INSTALLATION="
    bash "$ROOT/scripts/release-manager.sh" status
    echo "=== Model candidates ==="
    bash "$ROOT/install.sh" --list-models
    echo "=== Active service ==="
    if command -v systemctl >/dev/null 2>&1; then
      systemctl is-active qwen38-flash-next.service || true
    fi
    echo "=== Current Docker ==="
    if command -v docker >/dev/null 2>&1; then
      docker inspect --format 'ID={{.Id}} STATUS={{.State.Status}} IMAGE={{.Image}}' qwen38-flash-next 2>/dev/null ||
        echo 'CONTAINER=ABSENT'
    fi
    echo "=== Existing result files ==="
    local_dir="$ROOT/scripts/benchmark/results/local"
    if [[ -d "$local_dir" ]]; then
      find "$local_dir" -maxdepth 3 -type f \( -name '*.json' -o -name '*.md' \) -print
    else
      echo 'RESULTS=NONE_IN_DEFAULT_DIRECTORY'
    fi
    echo "NEXT=Implement guarded READY/API/host-stability admission and pinned llama-benchy run before enabling measurement."
    ;;
  --help|-h)
    echo "Usage: ./wizard.sh --benchmark  # read-only status, no measurements"
    ;;
  *)
    echo "ERROR: benchmark action is not qualified: $action" >&2
    exit 2
    ;;
esac
