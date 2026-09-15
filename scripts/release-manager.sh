#!/usr/bin/env bash
# Stage and inspect immutable code releases without mutating the active runtime.
set -Eeuo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_ROOT="${QWEN38_SOURCE_ROOT:-${SCRIPT_ROOT}}"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"
RELEASES_DIR="${QWEN38_RELEASES_DIR:-${DATA_HOME}/releases}"
CURRENT_LINK="${QWEN38_CURRENT_RELEASE_LINK:-${DATA_HOME}/current}"
PREVIOUS_LINK="${QWEN38_PREVIOUS_RELEASE_LINK:-${DATA_HOME}/previous}"
MANIFEST_TOOL="${SCRIPT_ROOT}/scripts/release_manifest.py"

usage() {
  cat <<'EOF'
Usage: ./scripts/release-manager.sh stage REVISION
       ./scripts/release-manager.sh verify RELEASE_ID
       ./scripts/release-manager.sh activate RELEASE_ID
       ./scripts/release-manager.sh rollback
       ./scripts/release-manager.sh status

stage     Export tracked files from REVISION into an immutable release directory.
verify    Verify one staged release against its cryptographic manifest.
activate  Atomically move the user-space current pointer; does not restart services.
rollback  Atomically swap current and previous user-space release pointers.
status    Print current/previous release pointers.
EOF
}

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
require_command() { command -v "$1" >/dev/null 2>&1 || die "$1 is required"; }
release_path() { printf '%s/%s\n' "${RELEASES_DIR}" "$1"; }
validate_release_id() { [[ "$1" =~ ^[0-9a-f]{12,40}$ ]] || die "invalid release id: $1"; }
read_link_release_id() {
  local link="$1" target
  [[ -L "${link}" ]] || return 1
  target="$(readlink -f -- "${link}")"
  [[ "${target}" == "${RELEASES_DIR}/"* ]] || die "unsafe release pointer: ${link} -> ${target}"
  basename -- "${target}"
}
verify_release() {
  local release_id="$1" path
  validate_release_id "${release_id}"
  path="$(release_path "${release_id}")"
  [[ -d "${path}" && ! -L "${path}" ]] || die "release does not exist: ${release_id}"
  python3 "${MANIFEST_TOOL}" verify "${path}" --revision "${release_id}"
}
atomic_link() {
  local target="$1" link="$2" tmp="${link}.tmp.$$"
  ln -s -- "${target}" "${tmp}"
  mv -Tf -- "${tmp}" "${link}"
}

[[ $# -ge 1 ]] || { usage >&2; exit 2; }
action="$1"; shift
require_command python3
[[ -f "${MANIFEST_TOOL}" ]] || die "release manifest tool is unavailable: ${MANIFEST_TOOL}"

case "${action}" in
  stage)
    [[ $# -eq 1 ]] || { usage >&2; exit 2; }
    require_command git
    require_command tar
    git -C "${SOURCE_ROOT}" rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "source root is not a git checkout: ${SOURCE_ROOT}"
    requested="$1"
    revision="$(git -C "${SOURCE_ROOT}" rev-parse --verify "${requested}^{commit}" 2>/dev/null)" || die "unknown git revision: ${requested}"
    release_id="${revision}"
    destination="$(release_path "${release_id}")"
    mkdir -p -- "${RELEASES_DIR}"
    if [[ -e "${destination}" || -L "${destination}" ]]; then
      [[ -d "${destination}" && ! -L "${destination}" ]] || die "unsafe existing release path: ${destination}"
      verify_release "${release_id}"
      printf 'Release already staged and verified: %s\n' "${release_id}"
      exit 0
    fi
    staging="${destination}.staging.$$"
    trap 'rm -rf -- "${staging}"' EXIT INT TERM
    mkdir -p -- "${staging}"
    git -C "${SOURCE_ROOT}" archive --format=tar "${revision}" | tar -xf - -C "${staging}"
    python3 "${MANIFEST_TOOL}" build "${staging}" "${release_id}"
    python3 "${MANIFEST_TOOL}" verify "${staging}" --revision "${release_id}"
    mv -- "${staging}" "${destination}"
    trap - EXIT INT TERM
    printf 'Release staged: %s\n' "${release_id}"
    ;;
  verify)
    [[ $# -eq 1 ]] || { usage >&2; exit 2; }
    verify_release "$1"
    ;;
  activate)
    [[ $# -eq 1 ]] || { usage >&2; exit 2; }
    release_id="$1"
    verify_release "${release_id}"
    mkdir -p -- "${DATA_HOME}"
    if current_id="$(read_link_release_id "${CURRENT_LINK}" 2>/dev/null)"; then
      if [[ "${current_id}" == "${release_id}" ]]; then
        printf 'Release is already current: %s\n' "${release_id}"
        exit 0
      fi
      atomic_link "$(release_path "${current_id}")" "${PREVIOUS_LINK}"
    elif [[ -e "${CURRENT_LINK}" ]]; then
      die "current release pointer exists but is not a safe symlink: ${CURRENT_LINK}"
    fi
    atomic_link "$(release_path "${release_id}")" "${CURRENT_LINK}"
    printf 'Current release pointer updated: %s\n' "${release_id}"
    ;;
  rollback)
    [[ $# -eq 0 ]] || { usage >&2; exit 2; }
    current_id="$(read_link_release_id "${CURRENT_LINK}")" || die "no current release is recorded"
    previous_id="$(read_link_release_id "${PREVIOUS_LINK}")" || die "no previous release is recorded"
    verify_release "${current_id}"
    verify_release "${previous_id}"
    atomic_link "$(release_path "${previous_id}")" "${CURRENT_LINK}"
    atomic_link "$(release_path "${current_id}")" "${PREVIOUS_LINK}"
    printf 'Release pointers rolled back: current=%s previous=%s\n' "${previous_id}" "${current_id}"
    ;;
  status)
    [[ $# -eq 0 ]] || { usage >&2; exit 2; }
    current_id="$(read_link_release_id "${CURRENT_LINK}" 2>/dev/null || true)"
    previous_id="$(read_link_release_id "${PREVIOUS_LINK}" 2>/dev/null || true)"
    printf 'CURRENT_RELEASE=%s\n' "${current_id:-none}"
    printf 'PREVIOUS_RELEASE=%s\n' "${previous_id:-none}"
    ;;
  -h|--help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
