#!/usr/bin/env bash
# Read-only, fail-closed inventory of Hybrid checkpoint references.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
SCRIPT_ROOT="${ROOT}"
# shellcheck source=scripts/model-assets.sh
source "${ROOT}/scripts/model-assets.sh"

usage() { echo "Usage: bash scripts/model/hybrid-retirement-audit.sh PATH"; }
[[ $# == 1 && "$1" != --* ]] || { usage >&2; exit 2; }
target="$(realpath -m -- "$1")"
[[ -d "${target}" && ! -L "${target}" ]] || { echo "AUDIT=BLOCKED_INVALID_TARGET"; exit 3; }
[[ -f "${target}/.qwen38-hybrid-manifest.json" ]] || { echo "AUDIT=BLOCKED_NOT_HYBRID"; exit 3; }
[[ "${target}" == "$(model_asset_root)"/qwen3.8-h* ]] || { echo "AUDIT=BLOCKED_OUTSIDE_MODEL_ROOT"; exit 3; }
command -v docker >/dev/null || { echo "AUDIT=BLOCKED_DOCKER_UNAVAILABLE"; exit 3; }
ids="$(docker ps -aq)" || { echo "AUDIT=BLOCKED_DOCKER_LIST_FAILED"; exit 3; }
blockers=0
echo "HYBRID_AUDIT_TARGET=${target}"
while IFS= read -r profile; do
  [[ -n "${profile}" ]] || continue
  describe_model_asset "${profile}" || { echo "AUDIT=BLOCKED_PROFILE_REGISTRY"; exit 3; }
  [[ "$(realpath -m -- "${MODEL_ASSET_CHECKPOINT}")" != "${target}" ]] || {
    printf 'PROFILE_ALIAS=%s\n' "${profile}"
    blockers=$((blockers+1))
  }
done < <(model_asset_profiles)

# All containers, including exited ones. Inspect failure blocks the entire audit.
while IFS= read -r id; do
  [[ -n "${id}" ]] || continue
  inspect="$(docker inspect --format '{{range .Mounts}}{{println .Source}}{{end}}' "${id}")" || {
    echo "AUDIT=BLOCKED_DOCKER_INSPECT_FAILED id=${id}"
    exit 3
  }
  while IFS= read -r mount; do
    [[ -n "${mount}" ]] || continue
    mount_path="$(realpath -m -- "${mount}")"
    case "${mount_path}" in
      "${target}"|"${target}/"*)
        printf 'DOCKER_REFERENCE=%s source=%s\n' "${id}" "${mount}"
        blockers=$((blockers+1))
        ;;
    esac
  done <<< "${inspect}"
done <<< "${ids}"
printf 'HYBRID_AUDIT_BLOCKER_COUNT=%d\n' "${blockers}"
# Even zero discovered references is not approval to erase immutable evidence.
echo "HYBRID_AUDIT=READ_ONLY_NOT_DELETE_AUTHORIZATION"
[[ "${blockers}" == 0 ]] || exit 3
