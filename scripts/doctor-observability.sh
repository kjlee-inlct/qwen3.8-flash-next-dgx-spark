#!/usr/bin/env bash
# Compatibility shim for the categorized diagnostics implementation.
set -Eeuo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=diagnostics/doctor-observability.sh
source "${SCRIPT_DIR}/diagnostics/doctor-observability.sh"
# shellcheck source=diagnostics/runtime-commit-observability.sh
source "${SCRIPT_DIR}/diagnostics/runtime-commit-observability.sh"
