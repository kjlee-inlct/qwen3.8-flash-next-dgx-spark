#!/usr/bin/env bash
# Modular operator entry point (migration stage 1).
set -Eeuo pipefail
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck source=scripts/lib/wizard-ui.sh
source "${ROOT_DIR}/scripts/lib/wizard-ui.sh"
# shellcheck source=scripts/wizard/status.sh
source "${ROOT_DIR}/scripts/wizard/status.sh"
# shellcheck source=scripts/wizard/menus.sh
source "${ROOT_DIR}/scripts/wizard/menus.sh"

UI_LANG="${UI_LANG:-ko}"
STATUS_ONLY=0
usage() { printf 'Usage: ./wizard.sh [--lang ko|en] [--status] [--help]\n'; }
while (( $# > 0 )); do
  case "$1" in
    --lang)
      (( $# >= 2 )) || { printf 'ERROR: --lang requires ko or en\n' >&2; exit 2; }
      UI_LANG="$2"; shift ;;
    --status) STATUS_ONLY=1 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'ERROR: unknown option: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done
[[ "${UI_LANG}" == ko || "${UI_LANG}" == en ]] || { printf 'ERROR: unsupported language\n' >&2; exit 2; }
wizard_init
if [[ "${STATUS_ONLY}" == 1 ]]; then
  wizard_status_summary
else
  wizard_main_menu
fi
