#!/usr/bin/env bash
# Never source untrusted install.env as shell.
wizard_read_manifest() {
  local state_file parsed key value
  state_file="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark/install.env"
  WIZARD_MANIFEST_STATE=missing
  WIZARD_PHASE=unknown
  WIZARD_PROFILE=unknown
  WIZARD_IMAGE=unknown
  [[ -e "${state_file}" || -L "${state_file}" ]] || return 0
  if [[ ! -f "${state_file}" || -L "${state_file}" ]]; then
    WIZARD_MANIFEST_STATE=invalid
    return 0
  fi
  parsed="$(mktemp)" || return 1
  if ! python3 "${ROOT_DIR}/scripts/lib/state_file.py" install-maintenance "${state_file}" >"${parsed}" 2>/dev/null; then
    WIZARD_MANIFEST_STATE=invalid
    rm -f -- "${parsed}"
    return 0
  fi
  WIZARD_MANIFEST_STATE=valid
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    case "${key}" in
      PHASE) WIZARD_PHASE="${value}" ;;
      MODEL_PROFILE) WIZARD_PROFILE="${value}" ;;
      VLLM_IMAGE) WIZARD_IMAGE="${value}" ;;
    esac
  done <"${parsed}"
  rm -f -- "${parsed}"
}

wizard_status_summary() {
  wizard_read_manifest || return $?
  printf 'Manifest: %s' "${WIZARD_MANIFEST_STATE}"
  [[ "${WIZARD_MANIFEST_STATE}" != valid ]] || printf ' (phase=%s)' "${WIZARD_PHASE}"
  printf '\n'
  if [[ "${WIZARD_MANIFEST_STATE}" == valid ]]; then
    printf 'Profile : %s\nImage   : %s\n' "${WIZARD_PROFILE}" "${WIZARD_IMAGE}"
  fi
  printf 'Runtime : NOT_PROBED (use Diagnostics / Runtime menu)\n\n'
  [[ "${WIZARD_MANIFEST_STATE}" != invalid ]] ||
    wizard_warning 'Unsafe or malformed manifest: mutation paths must be blocked.'
}
