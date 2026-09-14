#!/usr/bin/env bash
# Manage the dedicated swap file used by Qwen3.8 PLE offload.
# Existing system swap (for example /swap.img) is never modified.

set -euo pipefail

readonly DEFAULT_SWAP_FILE="/swap-ple.img"
readonly DEFAULT_SIZE_GIB=128
readonly DEFAULT_PRIORITY=10
readonly FSTAB_MARKER="# qwen38-ple-swap"

log() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

usage() {
  cat <<'EOF'
Usage:
  sudo ./scripts/manage-swap.sh create [--size-gib N] [--file PATH]
                                      [--priority N] [--persist] [--yes]
  sudo ./scripts/manage-swap.sh remove [--file PATH] [--yes]
  ./scripts/manage-swap.sh status [--file PATH]

With no command, an interactive setup wizard is started.

Safety:
  - The default target is /swap-ple.img.
  - Existing swap files are never resized, reformatted, or overwritten.
  - Removal is allowed only for a regular file and requires confirmation.
  - Only the exact qwen38-marked /etc/fstab entry is managed.
EOF
}

require_root() {
  [[ "${EUID}" -eq 0 ]] || die "this operation requires sudo"
}

validate_file() {
  local path="$1"
  [[ "${path}" == /* ]] || die "swap path must be absolute: ${path}"
  [[ "${path}" != "/" ]] || die "refusing unsafe target: /"
  [[ "${path}" != "/swap.img" ]] || die "refusing to manage the existing system swap /swap.img"
  [[ "${path}" != *'*'* && "${path}" != *'?'* && "${path}" != *'['* ]] || \
    die "wildcards are not allowed in the swap path"
}

is_active() {
  swapon --show=NAME --noheadings 2>/dev/null | awk '{$1=$1};1' | grep -Fxq "$1"
}

fstab_line() {
  printf '%s none swap sw,pri=%s 0 0 %s' "$1" "$2" "${FSTAB_MARKER}"
}

show_status() {
  local path="$1"
  validate_file "${path}"
  log "PLE swap status"
  log "  target     : ${path}"
  if [[ -e "${path}" ]]; then
    local bytes
    bytes="$(stat -c '%s' -- "${path}")"
    log "  file       : present ($((bytes / 1024 / 1024 / 1024)) GiB)"
  else
    log "  file       : absent"
  fi
  if is_active "${path}"; then
    log "  active     : yes"
  else
    log "  active     : no"
  fi
  if grep -Fq "$(fstab_line "${path}" "${PRIORITY}")" /etc/fstab 2>/dev/null; then
    log "  persistent : yes"
  else
    log "  persistent : no"
  fi
  log ""
  swapon --show || true
}

confirm() {
  local prompt="$1"
  [[ "${ASSUME_YES}" == "1" ]] && return 0
  local answer
  read -r -p "${prompt} [y/N]: " answer
  [[ "${answer}" == "y" || "${answer}" == "Y" ]]
}

create_swap() {
  require_root
  validate_file "${SWAP_FILE}"
  [[ "${SIZE_GIB}" =~ ^[1-9][0-9]*$ ]] || die "--size-gib must be a positive integer"
  [[ "${PRIORITY}" =~ ^-?[0-9]+$ ]] || die "--priority must be an integer"

  if [[ -e "${SWAP_FILE}" ]]; then
    if is_active "${SWAP_FILE}"; then
      log "Dedicated PLE swap is already active; no changes made."
      show_status "${SWAP_FILE}"
      return 0
    fi
    die "${SWAP_FILE} already exists but is not active; refusing to overwrite it"
  fi

  local parent available_bytes required_bytes reserve_bytes
  parent="$(dirname -- "${SWAP_FILE}")"
  [[ -d "${parent}" ]] || die "parent directory does not exist: ${parent}"
  available_bytes="$(df --output=avail -B1 "${parent}" | tail -n1 | tr -d ' ')"
  required_bytes=$((SIZE_GIB * 1024 * 1024 * 1024))
  reserve_bytes=$((32 * 1024 * 1024 * 1024))
  (( available_bytes >= required_bytes + reserve_bytes )) || \
    die "not enough disk space: ${SIZE_GIB} GiB plus a 32 GiB safety reserve is required"

  log "A new dedicated swap file will be created."
  log "  file       : ${SWAP_FILE}"
  log "  size       : ${SIZE_GIB} GiB"
  log "  priority   : ${PRIORITY}"
  log "  persistent : $([[ "${PERSIST}" == "1" ]] && printf yes || printf no)"
  log "  note       : existing swap files will not be changed"
  confirm "Continue?" || die "cancelled"

  fallocate -l "${SIZE_GIB}G" -- "${SWAP_FILE}"
  chmod 600 -- "${SWAP_FILE}"
  mkswap -- "${SWAP_FILE}"
  swapon -p "${PRIORITY}" -- "${SWAP_FILE}"

  if [[ "${PERSIST}" == "1" ]]; then
    local entry
    entry="$(fstab_line "${SWAP_FILE}" "${PRIORITY}")"
    if ! grep -Fqx "${entry}" /etc/fstab; then
      printf '\n%s\n' "${entry}" >> /etc/fstab
    fi
  fi

  log "Dedicated PLE swap created successfully."
  show_status "${SWAP_FILE}"
}

remove_fstab_entry() {
  local path="$1" temporary
  temporary="$(mktemp /etc/fstab.qwen38.XXXXXX)"
  awk -v target="${path}" -v marker="${FSTAB_MARKER}" \
    '!(index($0, target " ") == 1 && index($0, marker) > 0)' /etc/fstab > "${temporary}"
  chmod --reference=/etc/fstab "${temporary}"
  chown --reference=/etc/fstab "${temporary}"
  mv -- "${temporary}" /etc/fstab
}

remove_swap() {
  require_root
  validate_file "${SWAP_FILE}"
  [[ -e "${SWAP_FILE}" ]] || die "swap file does not exist: ${SWAP_FILE}"
  [[ -f "${SWAP_FILE}" && ! -L "${SWAP_FILE}" ]] || die "target must be a regular, non-symlink file"

  log "This will deactivate and permanently delete only: ${SWAP_FILE}"
  log "The existing /swap.img and all other swap devices will remain unchanged."
  confirm "Type y to remove the dedicated PLE swap" || die "cancelled"

  if is_active "${SWAP_FILE}"; then
    swapoff -- "${SWAP_FILE}" || die "swapoff failed; file was not deleted"
  fi
  remove_fstab_entry "${SWAP_FILE}"
  rm -- "${SWAP_FILE}"
  log "Removed ${SWAP_FILE}. This deletion is not recoverable."
}

wizard() {
  log "Qwen3.8 PLE swap setup"
  log "Existing swap devices will be preserved."
  log ""
  read -r -p "Swap file [${DEFAULT_SWAP_FILE}]: " input
  SWAP_FILE="${input:-${DEFAULT_SWAP_FILE}}"
  read -r -p "Size in GiB [${DEFAULT_SIZE_GIB}]: " input
  SIZE_GIB="${input:-${DEFAULT_SIZE_GIB}}"
  read -r -p "Enable automatically at boot? [Y/n]: " input
  [[ "${input}" == "n" || "${input}" == "N" ]] && PERSIST=0 || PERSIST=1
  create_swap
}

COMMAND="${1:-wizard}"
[[ $# -gt 0 ]] && shift
SWAP_FILE="${DEFAULT_SWAP_FILE}"
SIZE_GIB="${DEFAULT_SIZE_GIB}"
PRIORITY="${DEFAULT_PRIORITY}"
PERSIST=0
ASSUME_YES=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --file) [[ $# -ge 2 ]] || die "--file requires a value"; SWAP_FILE="$2"; shift 2 ;;
    --size-gib) [[ $# -ge 2 ]] || die "--size-gib requires a value"; SIZE_GIB="$2"; shift 2 ;;
    --priority) [[ $# -ge 2 ]] || die "--priority requires a value"; PRIORITY="$2"; shift 2 ;;
    --persist) PERSIST=1; shift ;;
    --yes) ASSUME_YES=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

case "${COMMAND}" in
  wizard) wizard ;;
  create) create_swap ;;
  remove) remove_swap ;;
  status) show_status "${SWAP_FILE}" ;;
  help|-h|--help) usage ;;
  *) usage >&2; die "unknown command: ${COMMAND}" ;;
esac
