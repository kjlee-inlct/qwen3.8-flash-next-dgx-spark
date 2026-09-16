#!/usr/bin/env bash
# Compatibility source path. Canonical implementation lives under scripts/model/.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/model/model-profiles.sh
source "${SCRIPT_DIR}/model/model-profiles.sh"
