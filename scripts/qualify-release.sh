#!/usr/bin/env bash
# Validate a staged immutable release before it is eligible for service cutover.
set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"
RELEASES_DIR="${QWEN38_RELEASES_DIR:-${DATA_HOME}/releases}"
QUALIFIED_DIR="${DATA_HOME}/qualified"
RELEASE_MANAGER="${SCRIPT_ROOT}/scripts/release-manager.sh"

usage() { printf 'Usage: %s RELEASE_ID\n' "$0"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

[[ $# -eq 1 ]] || { usage >&2; exit 2; }
release_id="$1"
[[ "${release_id}" =~ ^[0-9a-f]{12,40}$ ]] || die "invalid release id: ${release_id}"
release_dir="${RELEASES_DIR}/${release_id}"

bash "${RELEASE_MANAGER}" verify "${release_id}"
[[ -d "${release_dir}" && ! -L "${release_dir}" ]] || die "release is unavailable: ${release_id}"

# The release must be self-contained enough to pass the same syntax and unit
# checks used by CI. Keep Python bytecode out of the immutable payload. A second
# manifest verification below rejects any other test-created artifact as well.
bash -n "${release_dir}/install.sh" "${release_dir}/uninstall.sh" "${release_dir}"/scripts/*.sh
(
  cd "${release_dir}"
  PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
)

# Qualification itself must be observational: the immutable payload must remain
# byte-for-byte identical after all tests finish.
bash "${RELEASE_MANAGER}" verify "${release_id}"

mkdir -p -- "${QUALIFIED_DIR}"
umask 077
marker="${QUALIFIED_DIR}/${release_id}.env"
{
  printf 'QUALIFICATION_SCHEMA_VERSION=%q\n' 1
  printf 'QUALIFIED_RELEASE=%q\n' "${release_id}"
  printf 'QUALIFIED_AT=%q\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
} >"${marker}.tmp"
mv -- "${marker}.tmp" "${marker}"
printf 'Release qualified for cutover: %s\n' "${release_id}"
