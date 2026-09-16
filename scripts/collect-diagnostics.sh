#!/usr/bin/env bash
# Compatibility entry point. Canonical implementation lives under scripts/diagnostics/.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${SCRIPT_DIR}/diagnostics/collect-diagnostics.sh" "$@"
