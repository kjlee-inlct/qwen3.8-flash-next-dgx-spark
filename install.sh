#!/usr/bin/env bash
# Install/resume only. Completed-install management now belongs to ./wizard.sh.
# Historical engine is retained without changing its transaction/recovery code.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
ENGINE="${ROOT}/scripts/install/engine.sh"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark/install.env"
[[ -r "$ENGINE" ]] || { echo "ERROR: install engine unavailable: $ENGINE" >&2; exit 2; }

# Model/backend discovery and --help do not mutate an existing installation.
INFO=0
for arg in "$@"; do
  case "$arg" in --help|-h|--list-models|--list-backends) INFO=1 ;; esac
done
if [[ "$INFO" == 0 && -e "$STATE" ]]; then
  [[ -f "$STATE" && ! -L "$STATE" ]] || {
    echo "ERROR: unsafe installation manifest: $STATE" >&2; exit 2;
  }
  phase="$(python3 - "$ROOT" "$STATE" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / "scripts/lib"))
from state_file import parse_install
print(parse_install(Path(sys.argv[2]), "install-maintenance").get("PHASE", ""))
PY
  )" || { echo "ERROR: invalid installation manifest; refusing install" >&2; exit 2; }
  if [[ "$phase" == complete ]]; then
    echo "INSTALL_ALREADY_COMPLETE: use ./wizard.sh for profile switching, settings, benchmarking or uninstall." >&2
    exit 2
  fi
fi
exec bash "$ENGINE" "$@"
