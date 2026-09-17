#!/usr/bin/env bash
# Register one known-good revision as the immutable release baseline.
set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
RELEASE_MANAGER="${SCRIPT_ROOT}/scripts/release-manager.sh"
QUALIFY="${SCRIPT_ROOT}/scripts/lifecycle/qualify-release.sh"
OPERATION_LOCK_LIB="${SCRIPT_ROOT}/scripts/lib/operation-lock.sh"

usage() { printf 'Usage: %s REVISION\n' "$0"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[[ $# -eq 1 ]] || { usage >&2; exit 2; }
revision="$1"
[[ -r "${OPERATION_LOCK_LIB}" ]] || die "operation lock helper is unavailable: ${OPERATION_LOCK_LIB}"
# shellcheck source=scripts/lib/operation-lock.sh
source "${OPERATION_LOCK_LIB}"
acquire_operation_lock "${STATE_HOME}" "release bootstrap" || exit $?

status="$(bash "${RELEASE_MANAGER}" status)"
current="$(awk -F= '$1=="CURRENT_RELEASE" {print $2}' <<<"${status}")"
[[ "${current:-none}" == none ]] || die "release baseline already exists: ${current}"

bash "${RELEASE_MANAGER}" stage "${revision}"
release_id="$(git -C "${SCRIPT_ROOT}" rev-parse --verify "${revision}^{commit}")"
bash "${QUALIFY}" "${release_id}"
bash "${RELEASE_MANAGER}" activate "${release_id}"

printf 'Immutable release baseline registered without restarting the runtime: %s\n' "${release_id}"
