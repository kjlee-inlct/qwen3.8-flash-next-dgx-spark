#!/usr/bin/env bash
# The sole interactive front door. Each module retains its own safety gates.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
STATE="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark/install.env"
UI_LANG="${UI_LANG:-ko}"

usage() {
  cat <<'EOF'
Usage: ./wizard.sh
       ./wizard.sh --install [install.sh options]
       ./wizard.sh --manage [install.sh manager options]
       ./wizard.sh --uninstall [uninstall.sh options]
       ./wizard.sh --benchmark
       ./wizard.sh --storage
       ./wizard.sh --help

install.sh installs/resumes only. Completed model switching and settings use
--manage, which delegates to the existing transactional management engine.
Benchmark menu is read-only until measured-run safety gates are implemented.
EOF
}
require_complete() {
  [[ -f "$STATE" && ! -L "$STATE" ]] || {
    echo "WIZARD_MANAGE=BLOCKED missing_or_unsafe_manifest" >&2
    exit 2
  }
  python3 - "$ROOT" "$STATE" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / "scripts/lib"))
from state_file import parse_install
try:
    values = parse_install(Path(sys.argv[2]), "install-maintenance")
except Exception as exc:
    print(f"WIZARD_MANAGE=BLOCKED invalid_manifest: {exc}", file=sys.stderr)
    sys.exit(2)
if values.get("PHASE") != "complete":
    print("WIZARD_MANAGE=BLOCKED installation_not_complete", file=sys.stderr)
    sys.exit(2)
PY
}
run_action() {
  local action="$1"
  shift
  case "$action" in
    install) exec "$ROOT/install.sh" "$@" ;;
    manage)
      require_complete
      exec env QWEN38_WIZARD_MANAGEMENT=1 bash "$ROOT/scripts/install/engine.sh" "$@"
      ;;
    uninstall) exec "$ROOT/uninstall.sh" "$@" ;;
    benchmark) exec bash "$ROOT/scripts/wizard/benchmark.sh" "$@" ;;
    storage) exec bash "$ROOT/scripts/manage-storage.sh" status ;;
    *) echo "ERROR: unknown wizard action: $action" >&2; exit 2 ;;
  esac
}
if (($#)); then
  action="$1"; shift
  case "$action" in
    --install) run_action install "$@" ;;
    --manage) run_action manage "$@" ;;
    --uninstall) run_action uninstall "$@" ;;
    --benchmark) run_action benchmark "$@" ;;
    --storage) run_action storage "$@" ;;
    --help|-h) usage; exit 0 ;;
    *) usage >&2; exit 2 ;;
  esac
fi

# Source UI primitives without installer-only hooks (this is a pure dispatcher).
source "$ROOT/scripts/lib/wizard-ui.sh"
wizard_header "Qwen3.8 Flash Next — DGX Spark"
wizard_menu_option 1 'Install / 새 설치·재개'
wizard_menu_option 2 'Manage / 모델 전환·설정'
wizard_menu_option 3 'Benchmark / 벤치마크 현황'
wizard_menu_option 4 'Storage / 저장 공간 현황'
wizard_menu_option 5 'Uninstall / 제거'
wizard_menu_option 6 'Exit / 종료'
wizard_input selection '선택 / Select' 6
case "$selection" in
  1) run_action install ;;
  2) run_action manage ;;
  3) run_action benchmark ;;
  4) run_action storage ;;
  5) run_action uninstall ;;
  6|q|Q|exit|cancel) echo 'WIZARD_CANCELLED'; exit 0 ;;
  *) echo 'ERROR: invalid menu selection (1-6)' >&2; exit 2 ;;
esac
