#!/usr/bin/env bash
# Validate a staged immutable release before it is eligible for service cutover.
set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"
RELEASES_DIR="${QWEN38_RELEASES_DIR:-${DATA_HOME}/releases}"
QUALIFIED_DIR="${DATA_HOME}/qualified"
RELEASE_MANAGER="${SCRIPT_ROOT}/scripts/release-manager.sh"
MANIFEST_NAME=".release-manifest.json"

usage() { printf 'Usage: %s RELEASE_ID\n' "$0"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
manifest_digest() {
  python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1], "rb").read()).hexdigest())' "$1"
}

[[ $# -eq 1 ]] || { usage >&2; exit 2; }
release_id="$1"
[[ "${release_id}" =~ ^[0-9a-f]{12,40}$ ]] || die "invalid release id: ${release_id}"
release_dir="${RELEASES_DIR}/${release_id}"
manifest_path="${release_dir}/${MANIFEST_NAME}"

bash "${RELEASE_MANAGER}" verify "${release_id}"
[[ -d "${release_dir}" && ! -L "${release_dir}" ]] || die "release is unavailable: ${release_id}"
[[ -f "${manifest_path}" && ! -L "${manifest_path}" ]] || die "release manifest is unavailable or unsafe: ${manifest_path}"

bash -n "${release_dir}/install.sh" "${release_dir}/uninstall.sh" "${release_dir}"/scripts/*.sh
(
  cd "${release_dir}"
  PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
)

bash "${RELEASE_MANAGER}" verify "${release_id}"
release_manifest_sha256="$(manifest_digest "${manifest_path}")"
[[ "${release_manifest_sha256}" =~ ^[0-9a-f]{64}$ ]] || die "failed to compute release manifest digest"

mkdir -p -- "${QUALIFIED_DIR}"
umask 077
marker="${QUALIFIED_DIR}/${release_id}.env"
{
  printf 'QUALIFICATION_SCHEMA_VERSION=%s\n' 2
  printf 'QUALIFIED_RELEASE=%s\n' "${release_id}"
  printf 'RELEASE_MANIFEST_SHA256=%s\n' "${release_manifest_sha256}"
  printf 'QUALIFIED_AT=%s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
} >"${marker}.tmp"
mv -- "${marker}.tmp" "${marker}"
printf 'Release qualified for cutover: %s (manifest=%s)\n' "${release_id}" "${release_manifest_sha256}"
