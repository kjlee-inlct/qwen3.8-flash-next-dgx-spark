#!/usr/bin/env bash
# Compatibility entry point. Canonical implementation lives under scripts/runtime/.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${SCRIPT_DIR}/runtime/service-runner.sh" "$@"
