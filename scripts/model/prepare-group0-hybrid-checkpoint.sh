#!/usr/bin/env bash
# Convenience wrapper for the full group-0 BF16 hybrid checkpoint.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
export HYBRID_VARIANT=group0-bf16
export HYBRID_OUTPUT_DIR="${HYBRID_OUTPUT_DIR:-$HOME/models/qwen3.8-hybrid-group0-bf16}"
exec bash "${ROOT}/scripts/model/prepare-hybrid-checkpoint.sh" "$@"
