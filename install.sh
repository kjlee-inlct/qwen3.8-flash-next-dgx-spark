#!/usr/bin/env bash
# Interactive installer for OrcaRouter Qwen3.8-Flash-Next on one DGX Spark.
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/model-profiles.sh
source "${ROOT_DIR}/scripts/model-profiles.sh"
PROFILE_MANAGER="${ROOT_DIR}/scripts/model/profile-manager.sh"
[[ -r "${PROFILE_MANAGER}" ]] || { printf 'ERROR: profile manager helper missing: %s\n' "${PROFILE_MANAGER}" >&2; exit 1; }
# shellcheck source=scripts/model/profile-manager.sh
source "${PROFILE_MANAGER}"
BACKEND_REGISTRY="${ROOT_DIR}/scripts/backend/backends.sh"
# shellcheck source=scripts/backend/backends.sh
source "${BACKEND_REGISTRY}"
OPTION_REGISTRY="${ROOT_DIR}/scripts/lib/install-options.sh"
[[ -r "${OPTION_REGISTRY}" ]] || { printf 'ERROR: installer option registry missing: %s\n' "${OPTION_REGISTRY}" >&2; exit 1; }
# shellcheck source=scripts/lib/install-options.sh
source "${OPTION_REGISTRY}"
WIZARD_UI="${ROOT_DIR}/scripts/lib/wizard-ui.sh"
[[ -r "${WIZARD_UI}" ]] || { printf 'ERROR: wizard UI helper missing: %s\n' "${WIZARD_UI}" >&2; exit 1; }
# shellcheck source=scripts/lib/wizard-ui.sh
source "${WIZARD_UI}"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/install.env"
STATE_PARSER="${ROOT_DIR}/scripts/lib/state_file.py"
ASSET_OWNERSHIP_TOOL="${ROOT_DIR}/scripts/lib/asset_ownership.py"
ASSET_OWNERSHIP_FILE="${STATE_DIR}/asset-ownership.json"
PROFILE_SWITCH_TRANSITION="${ROOT_DIR}/scripts/lifecycle/profile-switch-transition.sh"
PROFILE_SWITCH_STATE="${STATE_DIR}/profile-switch-transition.env"
OPERATION_LOCK_LIB="${ROOT_DIR}/scripts/lib/operation-lock.sh"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"
CURRENT_RELEASE_LINK="${DATA_HOME}/current"
SWAP_FILE="${SWAP_FILE:-/swap-ple.img}"
CONFIG_OVERRIDE="${CONFIG_OVERRIDE:-}"
CONFIG_OVERRIDE_CLI=""
CONFIG_OVERRIDE_CLI_SET=0
MODEL_PROFILE="${MODEL_PROFILE:-orcarouter}"
MODEL_CLI=""
YES=0; START=1; DRY_RUN=0; MIGRATE_MANIFEST=0; REFRESH_PROFILE_DEFAULTS=0; CONFIG_OWNED=0
PROFILE_SWITCH=0; PROFILE_SWITCH_COMMITTED=0; SWITCH_FROM_PROFILE=""; SWITCH_MODEL_ROOT=""
PROFILE_SWITCH_BACKUP="${STATE_FILE}.profile-switch-backup"
PROFILE_SWITCH_CANDIDATE="${STATE_FILE}.profile-switch-candidate"
STATE_WRITE_FILE="${STATE_FILE}"
LIST_MODELS=0; LIST_BACKENDS=0
MONITOR_ENABLED_ENV_SET="${MONITOR_ENABLED+x}"
MONITOR_PROTECT_ENV_SET="${MONITOR_PROTECT+x}"
MONITOR_ENABLED="${MONITOR_ENABLED:-}"
MONITOR_PROTECT="${MONITOR_PROTECT:-0}"
MONITOR_MIN_AVAILABLE_GIB="${MONITOR_MIN_AVAILABLE_GIB:-6}"
MONITOR_MIN_FREE_GIB="${MONITOR_MIN_FREE_GIB:-2}"
MONITOR_FREE_GATE_GIB="${MONITOR_FREE_GATE_GIB:-10}"
MONITOR_MIN_SWAP_FREE_GIB="${MONITOR_MIN_SWAP_FREE_GIB:-8}"
MONITOR_CONSECUTIVE="${MONITOR_CONSECUTIVE:-5}"
MONITOR_HEARTBEAT="${MONITOR_HEARTBEAT:-60}"
# PROXY_* are retained as compatibility fields for schema <=3 and uninstall/doctor consumers.
PROXY_ENABLED="${PROXY_ENABLED:-0}"; PROXY_OWNED=0; PROXY_PORT="${PROXY_PORT:-8000}"
API_ACCESS_MODE="${API_ACCESS_MODE:-}"
API_DOCKER_PORT="${API_DOCKER_PORT:-${PROXY_PORT}}"
API_LAN_ADDRESS="${API_LAN_ADDRESS:-}"
API_LAN_PORT="${API_LAN_PORT:-8001}"
API_ACCESS_CLI=""; API_DOCKER_PORT_CLI=""; API_LAN_ADDRESS_CLI=""; API_LAN_PORT_CLI=""
SERVICE_ENABLED="${SERVICE_ENABLED:-1}"; SERVICE_OWNED=0; SERVICE_CLI=""
CLI_LANG=""; UI_LANG="${UI_LANG:-}"
MODEL_ROOT_CLI=""
MODEL_ROOT_ENV="${QWEN38_MODEL_ROOT:-}"
MODEL_ROOT=""
MODEL_ROOT_SOURCE=""
MONITOR_ENABLED_CLI=""; MONITOR_PROTECT_CLI=""; MONITOR_MIN_AVAILABLE_CLI=""
MONITOR_MIN_FREE_CLI=""; MONITOR_FREE_GATE_CLI=""; MONITOR_MIN_SWAP_FREE_CLI=""
MONITOR_CONSECUTIVE_CLI=""; MONITOR_HEARTBEAT_CLI=""

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
ensure_operation_lock() {
  [[ -r "${OPERATION_LOCK_LIB}" ]] || die "operation lock helper is unavailable: ${OPERATION_LOCK_LIB}"
  if ! declare -F acquire_operation_lock >/dev/null 2>&1; then
    # shellcheck source=scripts/lib/operation-lock.sh
    source "${OPERATION_LOCK_LIB}"
  fi
  acquire_operation_lock "${STATE_DIR}" "install" || exit $?
}
sudo_with_operation_lock() {
  sudo env \
    QWEN38_STATE_HOME="${XDG_STATE_HOME:-$HOME/.local/state}" \
    QWEN38_OPERATION_LOCK_HELD="${QWEN38_OPERATION_LOCK_HELD}" \
    QWEN38_OPERATION_LOCK_FILE="${QWEN38_OPERATION_LOCK_FILE}" \
    QWEN38_OPERATION_LOCK_OWNER_PID="${QWEN38_OPERATION_LOCK_OWNER_PID}" \
    "$@"
}
asset_bootstrap_install() {
  [[ -r "${ASSET_OWNERSHIP_TOOL}" ]] || die "asset ownership helper is unavailable: ${ASSET_OWNERSHIP_TOOL}"
  python3 "${ASSET_OWNERSHIP_TOOL}" bootstrap-install "${ASSET_OWNERSHIP_FILE}" "${STATE_FILE}" "${STATE_PARSER}"
}
asset_model_owned() {
  [[ -f "${ASSET_OWNERSHIP_FILE}" && ! -L "${ASSET_OWNERSHIP_FILE}" ]] || return 1
  python3 "${ASSET_OWNERSHIP_TOOL}" owns-model "${ASSET_OWNERSHIP_FILE}" "$1"
}
asset_image_owned() {
  [[ -f "${ASSET_OWNERSHIP_FILE}" && ! -L "${ASSET_OWNERSHIP_FILE}" ]] || return 1
  python3 "${ASSET_OWNERSHIP_TOOL}" owns-image "${ASSET_OWNERSHIP_FILE}" "$1"
}
asset_track_model() {
  local path="$1" root="$2" owned="$3"
  shift 3
  local args=(track-model "${ASSET_OWNERSHIP_FILE}" "${path}" "${root}" --owned "${owned}") dependency
  for dependency in "$@"; do
    args+=(--depends "${dependency}")
  done
  python3 "${ASSET_OWNERSHIP_TOOL}" "${args[@]}"
}
asset_track_image() {
  local image="$1" owned="$2"
  shift 2
  local args=(track-image "${ASSET_OWNERSHIP_FILE}" "${image}" --owned "${owned}") dependency
  for dependency in "$@"; do
    args+=(--depends "${dependency}")
  done
  python3 "${ASSET_OWNERSHIP_TOOL}" "${args[@]}"
}
asset_model_ownership_for_path() {
  local path="$1"
  if asset_model_owned "${path}"; then
    printf '1\n'
  elif [[ ! -e "${path}" && ! -L "${path}" ]]; then
    printf '1\n'
  else
    printf '0\n'
  fi
}
asset_image_ownership_for_name() {
  local image="$1"
  if asset_image_owned "${image}"; then
    printf '1\n'
  elif ! docker image inspect "${image}" >/dev/null 2>&1; then
    printf '1\n'
  else
    printf '0\n'
  fi
}
asset_track_profile_models() {
  local owned
  if [[ "${PROFILE_LOCAL_BUILD:-0}" == 1 ]]; then
    owned="$(asset_model_ownership_for_path "${HYBRID_BASE_DIR}")"
    asset_track_model "${HYBRID_BASE_DIR}" "$(dirname -- "${HYBRID_BASE_DIR}")" "${owned}"

    if [[ "${HYBRID_REUSE_H3}" != 1 ]]; then
      owned="$(asset_model_ownership_for_path "${HYBRID_OVERLAY_DIR}")"
      asset_track_model "${HYBRID_OVERLAY_DIR}" "$(dirname -- "${HYBRID_OVERLAY_DIR}")" "${owned}"
    fi

    owned="$(asset_model_ownership_for_path "${HYBRID_H3_DIR}")"
    asset_track_model "${HYBRID_H3_DIR}" "$(dirname -- "${HYBRID_H3_DIR}")" "${owned}" \
      "${HYBRID_BASE_DIR}"

    owned="$(asset_model_ownership_for_path "${HYBRID_H4_DIR}")"
    asset_track_model "${HYBRID_H4_DIR}" "$(dirname -- "${HYBRID_H4_DIR}")" "${owned}" \
      "${HYBRID_BASE_DIR}" "${HYBRID_H3_DIR}"

    owned="$(asset_model_ownership_for_path "${HYBRID_H5_DIR}")"
    asset_track_model "${HYBRID_H5_DIR}" "$(dirname -- "${HYBRID_H5_DIR}")" "${owned}" \
      "${HYBRID_BASE_DIR}" "${HYBRID_H3_DIR}" "${HYBRID_H4_DIR}"

    owned="$(asset_model_ownership_for_path "${MODEL_DIR}")"
    asset_track_model "${MODEL_DIR}" "$(dirname -- "${MODEL_DIR}")" "${owned}" \
      "${HYBRID_BASE_DIR}" "${HYBRID_H3_DIR}" "${HYBRID_H4_DIR}" "${HYBRID_H5_DIR}"
  else
    owned="$(asset_model_ownership_for_path "${MODEL_DIR}")"
    asset_track_model "${MODEL_DIR}" "$(dirname -- "${MODEL_DIR}")" "${owned}"
  fi

  if asset_model_owned "${MODEL_DIR}"; then MODEL_OWNED=1; else MODEL_OWNED=0; fi
}

asset_track_profile_images() {
  local owned
  owned="$(asset_image_ownership_for_name "${IMAGE}")"
  asset_track_image "${IMAGE}" "${owned}"
  if [[ "${MODEL_PROFILE}" == nvidia ]]; then
    owned="$(asset_image_ownership_for_name vllm-skinny-tp1:v1)"
    asset_track_image vllm-skinny-tp1:v1 "${owned}"
  fi
  if asset_image_owned "${IMAGE}"; then IMAGE_OWNED=1; else IMAGE_OWNED=0; fi
}
parse_install_manifest() {
  local parsed key value
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" install-maintenance "${STATE_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    printf -v "${key}" '%s' "${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
}
read_manifest_profile() {
  local parsed key value profile=""
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" install-maintenance "${STATE_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    [[ "${key}" == MODEL_PROFILE ]] && profile="${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
  printf '%s' "${profile}"
}

read_manifest_phase() {
  local parsed key value phase=""
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" install-maintenance "${STATE_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    [[ "${key}" == PHASE ]] && phase="${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
  printf '%s' "${phase}"
}
expand_user_path() {
  case "$1" in
    "~") printf '%s\n' "${HOME}" ;;
    "~/"*) printf '%s/%s\n' "${HOME}" "${1:2}" ;;
    *) printf '%s\n' "$1" ;;
  esac
}

model_root_has_complete_assets() {
  local root="$1" manifest
  [[ -d "${root}" ]] || return 1
  while IFS= read -r manifest; do
    [[ -n "${manifest}" ]] || continue
    grep -Eq '"status"[[:space:]]*:[[:space:]]*"complete"' "${manifest}" && return 0
  done < <(
    find "${root}" -mindepth 1 -maxdepth 2 -type f \
      \( -name .qwen38-model-manifest.json -o -name .qwen38-hybrid-manifest.json \) \
      -print 2>/dev/null
  )
  return 1
}

choose_default_model_root() {
  if [[ -n "${MODEL_ROOT_CLI}" ]]; then
    MODEL_ROOT="$(realpath -m -- "$(expand_user_path "${MODEL_ROOT_CLI}")")"
    MODEL_ROOT_SOURCE=cli
  elif [[ -n "${MODEL_ROOT_ENV}" ]]; then
    MODEL_ROOT="$(realpath -m -- "$(expand_user_path "${MODEL_ROOT_ENV}")")"
    MODEL_ROOT_SOURCE=environment
  elif model_root_has_complete_assets "${HOME}/models"; then
    MODEL_ROOT="$(realpath -m -- "${HOME}/models")"
    MODEL_ROOT_SOURCE=existing-home
  else
    MODEL_ROOT="$(realpath -m -- "${ROOT_DIR}/models")"
    MODEL_ROOT_SOURCE=repo-default
  fi
  export QWEN38_MODEL_ROOT="${MODEL_ROOT}"
}

reload_profile_for_model_root() {
  export QWEN38_MODEL_ROOT="${MODEL_ROOT}"
  load_model_profile "${MODEL_PROFILE}" || return
  REPO="${PROFILE_REPO}"
  REVISION="${PROFILE_REVISION}"
  MODEL_DIR="${PROFILE_MODEL_DIR}"
  IMAGE="${PROFILE_IMAGE}"
  SERVED_NAME="${PROFILE_SERVED_NAME}"
}

discover_hf_token() {
  local token="${HF_TOKEN:-${HUGGING_FACE_HUB_TOKEN:-}}"
  if [[ -n "${token}" ]]; then
    printf '%s' "${token}"
    return 0
  fi
  if [[ -r "${HOME}/.cache/huggingface/token" ]]; then
    cat "${HOME}/.cache/huggingface/token"
    return 0
  fi
  python3 - <<'PY' 2>/dev/null || true
try:
    from huggingface_hub import get_token
    print(get_token() or "", end="")
except ImportError:
    pass
PY
}

ensure_profile_auth() {
  [[ "${PROFILE_GATED}" == 1 ]] || return 0
  local token
  token="$(discover_hf_token)"
  if [[ -z "${token}" ]]; then
    if [[ "${YES}" != 1 && -t 0 ]]; then
      if [[ "${UI_LANG}" == ko ]]; then
        printf 'OrcaRouter 계열은 Hugging Face gated 모델입니다. 브라우저에서 모델 이용 약관을 먼저 승인해야 합니다.\n'
        wizard_secret token 'Hugging Face read token (입력 내용은 저장하지 않음)'
      else
        printf 'OrcaRouter-family profiles use a gated Hugging Face model. Accept the model terms in a browser first.\n'
        wizard_secret token 'Hugging Face read token (not stored by this installer)'
      fi
      printf '\n'
    else
      die "gated profile requires HF_TOKEN (or HUGGING_FACE_HUB_TOKEN / existing Hugging Face token cache)"
    fi
  fi
  [[ -n "${token}" ]] || die "Hugging Face token cannot be empty for gated profile"
  export HF_TOKEN="${token}"
}
detect_lan_ipv4() {
  command -v ip >/dev/null 2>&1 || return 0
  ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i=1; i<=NF; i++) if ($i=="src" && i<NF) {print $(i+1); exit}}'
}
valid_port() { [[ "$1" =~ ^[0-9]+$ ]] && (( 10#$1 >= 1 && 10#$1 <= 65535 )); }
valid_ipv4() {
  local ip="$1" IFS=. octets index
  [[ "${ip}" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] || return 1
  read -r -a octets <<<"${ip}"
  [[ ${#octets[@]} -eq 4 ]] || return 1
  for index in 0 1 2 3; do
    (( 10#${octets[$index]} >= 0 && 10#${octets[$index]} <= 255 )) || return 1
  done
}
sync_legacy_proxy_fields() {
  case "${API_ACCESS_MODE}" in
    local) PROXY_ENABLED=0 ;;
    docker|lan) PROXY_ENABLED=1 ;;
    *) die "API_ACCESS_MODE must be local, docker, or lan" ;;
  esac
  PROXY_PORT="${API_DOCKER_PORT}"
}
validate_api_access_settings() {
  [[ "${API_ACCESS_MODE}" == local || "${API_ACCESS_MODE}" == docker || "${API_ACCESS_MODE}" == lan ]] || \
    die "API access mode must be local, docker, or lan"
  valid_port "${API_DOCKER_PORT}" || die "API Docker port must be between 1 and 65535"
  if [[ "${API_ACCESS_MODE}" == lan ]]; then
    valid_ipv4 "${API_LAN_ADDRESS}" || die "LAN API requires a specific IPv4 address"
    [[ "${API_LAN_ADDRESS}" != 0.0.0.0 && "${API_LAN_ADDRESS}" != 127.* ]] || die "LAN API address must be non-loopback"
    valid_port "${API_LAN_PORT}" || die "LAN API port must be between 1 and 65535"
  fi
  sync_legacy_proxy_fields
}
write_state() {
  local phase="$1" target="${STATE_WRITE_FILE:-${STATE_FILE}}"
  mkdir -p "${STATE_DIR}"; umask 077
  {
    printf 'SCHEMA_VERSION=%q\n' 4; printf 'PHASE=%q\n' "${phase}"
    printf 'INSTALL_ROOT=%q\n' "${ROOT_DIR}"; printf 'MODEL_PROFILE=%q\n' "${MODEL_PROFILE}"
    printf 'MODEL_REPO=%q\n' "${REPO}"; printf 'MODEL_REVISION=%q\n' "${REVISION}"
    printf 'MODEL_DIR=%q\n' "${MODEL_DIR}"; printf 'MODEL_OWNED=%q\n' "${MODEL_OWNED}"
    printf 'SWAP_FILE=%q\n' "${SWAP_FILE}"; printf 'SWAP_OWNED=%q\n' "${SWAP_OWNED}"
    printf 'VLLM_IMAGE=%q\n' "${IMAGE}"; printf 'IMAGE_OWNED=%q\n' "${IMAGE_OWNED}"
    printf 'SERVED_NAME=%q\n' "${SERVED_NAME}"
    printf 'CONTAINER_NAME=%q\n' qwen38-flash-next; printf 'CONFIG_OVERRIDE=%q\n' "${CONFIG_OVERRIDE}"
    printf 'CONFIG_OWNED=%q\n' "${CONFIG_OWNED}"
    printf 'MONITOR_PROTECT=%q\n' "${MONITOR_PROTECT}"
    printf 'MONITOR_ENABLED=%q\n' "${MONITOR_ENABLED}"
    printf 'MONITOR_MIN_AVAILABLE_GIB=%q\n' "${MONITOR_MIN_AVAILABLE_GIB}"
    printf 'MONITOR_MIN_FREE_GIB=%q\n' "${MONITOR_MIN_FREE_GIB}"
    printf 'MONITOR_FREE_GATE_GIB=%q\n' "${MONITOR_FREE_GATE_GIB}"
    printf 'MONITOR_MIN_SWAP_FREE_GIB=%q\n' "${MONITOR_MIN_SWAP_FREE_GIB}"
    printf 'MONITOR_CONSECUTIVE=%q\n' "${MONITOR_CONSECUTIVE}"
    printf 'MONITOR_HEARTBEAT=%q\n' "${MONITOR_HEARTBEAT}"
    printf 'API_ACCESS_MODE=%q\n' "${API_ACCESS_MODE}"
    printf 'API_DOCKER_PORT=%q\n' "${API_DOCKER_PORT}"
    printf 'API_LAN_ADDRESS=%q\n' "${API_LAN_ADDRESS}"
    printf 'API_LAN_PORT=%q\n' "${API_LAN_PORT}"
    printf 'PROXY_ENABLED=%q\n' "${PROXY_ENABLED}"; printf 'PROXY_OWNED=%q\n' "${PROXY_OWNED}"
    printf 'PROXY_PORT=%q\n' "${PROXY_PORT}"
    printf 'SERVICE_ENABLED=%q\n' "${SERVICE_ENABLED}"; printf 'SERVICE_OWNED=%q\n' "${SERVICE_OWNED}"
    printf 'SERVICE_UNIT=%q\n' qwen38-flash-next.service
    printf 'UI_LANG=%q\n' "${UI_LANG}"
  } > "${target}.tmp"
  mv -- "${target}.tmp" "${target}"
}

restore_profile_switch_manifest_on_exit() {
  local rc="$?"
  [[ "${PROFILE_SWITCH}" == 1 ]] || return "${rc}"
  [[ -e "${PROFILE_SWITCH_STATE}" && ! -L "${PROFILE_SWITCH_STATE}" ]] || return "${rc}"
  set +e
  if [[ "${PROFILE_SWITCH_COMMITTED}" == 1 ]]; then
    bash "${PROFILE_SWITCH_TRANSITION}" recover
  else
    bash "${PROFILE_SWITCH_TRANSITION}" rollback
  fi
  recovery_rc="$?"
  set -e
  if [[ "${recovery_rc}" != 0 ]]; then
    printf 'Profile switch exit recovery failed; persisted transaction state was retained for explicit recovery.\n' >&2
  fi
  return "${rc}"
}

wizard_choose_model_profile() {
  local current_profile="${1:-}" mode="${2:-fresh}" default_choice=1 answer
  local profile detail selected="" candidate cancel_choice index selection_index
  local -a profiles=()

  mapfile -t profiles < <(list_model_profiles)
  [[ "${#profiles[@]}" -gt 0 ]] || die 'model profile registry has no installable profiles'

  for index in "${!profiles[@]}"; do
    profile="${profiles[${index}]}"
    describe_model_profile "${profile}" || die "invalid model profile registry entry: ${profile}"
    [[ "${PROFILE_INSTALLABLE}" == 1 ]] || die "installable profile list contains non-installable entry: ${profile}"
    if [[ -n "${current_profile}" && "${profile}" == "${current_profile}" ]]; then
      default_choice=$((index + 1))
    elif [[ -z "${current_profile}" && "${PROFILE_DEFAULT}" == 1 ]]; then
      default_choice=$((index + 1))
    fi
  done

  if [[ "${UI_LANG}" == ko ]]; then
    if [[ "${mode}" == existing ]]; then
      wizard_step 1 1 '모델 선택 / 전환'
      wizard_info "현재 profile: ${current_profile}"
    else
      wizard_step 2 6 '모델 선택'
    fi
  else
    if [[ "${mode}" == existing ]]; then
      wizard_step 1 1 'Model selection'
      wizard_info "Current profile: ${current_profile}"
    else
      wizard_step 2 6 'Model selection'
    fi
  fi

  for index in "${!profiles[@]}"; do
    profile="${profiles[${index}]}"
    profile_manager_load "${profile}" "${current_profile}" || die "cannot load profile manager entry: ${profile}"
    detail="$(profile_manager_loaded_detail)"
    wizard_menu_option "$((index + 1))" "${PM_DISPLAY_NAME}" "${detail}"
  done

  while IFS= read -r candidate; do
    [[ -n "${candidate}" ]] || continue
    profile_manager_load "${candidate}" "${current_profile}" || die "cannot load profile candidate: ${candidate}"
    detail="$(profile_manager_loaded_detail)"
    if [[ "${UI_LANG}" == ko ]]; then
      wizard_info "선택 불가: ${PM_DISPLAY_NAME} — ${detail}"
    else
      wizard_info "Not selectable: ${PM_DISPLAY_NAME} — ${detail}"
    fi
  done < <(list_model_candidates)

  cancel_choice=$(("${#profiles[@]}" + 1))
  if [[ "${mode}" == existing ]]; then
    [[ "${UI_LANG}" == ko ]] && wizard_menu_option "${cancel_choice}" '취소' || wizard_menu_option "${cancel_choice}" 'Cancel'
  fi
  [[ "${UI_LANG}" == ko ]] && wizard_input answer '선택' "${default_choice}" || wizard_input answer 'Select' "${default_choice}"

  if [[ "${answer}" =~ ^[0-9]+$ ]]; then
    selection_index=$((10#${answer}))
    if [[ "${mode}" == existing && "${selection_index}" -eq "${cancel_choice}" ]]; then
      [[ "${UI_LANG}" == ko ]] && wizard_info '취소됨' || wizard_info 'Cancelled'
      exit 0
    fi
    if (( selection_index >= 1 && selection_index <= ${#profiles[@]} )); then
      selected="${profiles[selection_index - 1]}"
    fi
  else
    for profile in "${profiles[@]}"; do
      [[ "${answer}" != "${profile}" ]] || selected="${profile}"
    done
  fi

  [[ -n "${selected}" ]] || die "invalid model selection"
  MODEL_PROFILE="${selected}"
}

usage() {
  install_option_usage
}
ask_yes_no() {
  local prompt="$1"
  [[ "${YES}" == 1 ]] && return 0
  wizard_yes_no "${prompt}" yes
}
positive_integer() { [[ "$1" =~ ^[1-9][0-9]*$ ]]; }
nonnegative_integer() { [[ "$1" =~ ^[0-9]+$ ]]; }
validate_monitor_settings() {
  local value
  for value in "${MONITOR_MIN_AVAILABLE_GIB}" "${MONITOR_MIN_FREE_GIB}" "${MONITOR_FREE_GATE_GIB}" \
    "${MONITOR_MIN_SWAP_FREE_GIB}" "${MONITOR_CONSECUTIVE}"; do
    positive_integer "${value}" || die "monitor thresholds must be positive integers"
  done
  nonnegative_integer "${MONITOR_HEARTBEAT}" || die "monitor heartbeat must be a non-negative integer"
  [[ "${MONITOR_ENABLED}" == 0 || "${MONITOR_ENABLED}" == 1 ]] || die "MONITOR_ENABLED must be 0 or 1"
  [[ "${MONITOR_PROTECT}" == 0 || "${MONITOR_PROTECT}" == 1 ]] || die "MONITOR_PROTECT must be 0 or 1"
  [[ "${MONITOR_ENABLED}" == 1 || "${MONITOR_PROTECT}" == 0 ]] || die "protection requires the monitor"
}
while [[ $# -gt 0 ]]; do
  case "$1" in
    --lang) [[ $# -ge 2 ]] || die "--lang requires en or ko"; CLI_LANG="$2"; shift ;;
    --model) [[ $# -ge 2 ]] || die "--model requires an installable profile"; MODEL_CLI="$2"; shift ;;
    --model-root) [[ $# -ge 2 ]] || die "--model-root requires PATH"; MODEL_ROOT_CLI="$2"; shift ;;
    --config-override) [[ $# -ge 2 ]] || die "--config-override requires PATH"; [[ -n "$2" ]] || die "--config-override requires a non-empty PATH"; CONFIG_OVERRIDE_CLI="$2"; CONFIG_OVERRIDE_CLI_SET=1; shift ;;
    --no-config-override) CONFIG_OVERRIDE_CLI=""; CONFIG_OVERRIDE_CLI_SET=1 ;;
    --list-models) LIST_MODELS=1 ;;
    --list-backends) LIST_BACKENDS=1 ;;
    --monitor) MONITOR_ENABLED_CLI=1; MONITOR_PROTECT_CLI=0 ;;
    --no-monitor) MONITOR_ENABLED_CLI=0; MONITOR_PROTECT_CLI=0 ;;
    --protect) MONITOR_ENABLED_CLI=1; MONITOR_PROTECT_CLI=1 ;;
    --monitor-min-available-gib) [[ $# -ge 2 ]] || die "$1 requires a value"; MONITOR_MIN_AVAILABLE_CLI="$2"; shift ;;
    --monitor-min-free-gib) [[ $# -ge 2 ]] || die "$1 requires a value"; MONITOR_MIN_FREE_CLI="$2"; shift ;;
    --monitor-free-gate-gib) [[ $# -ge 2 ]] || die "$1 requires a value"; MONITOR_FREE_GATE_CLI="$2"; shift ;;
    --monitor-min-swap-free-gib) [[ $# -ge 2 ]] || die "$1 requires a value"; MONITOR_MIN_SWAP_FREE_CLI="$2"; shift ;;
    --monitor-consecutive) [[ $# -ge 2 ]] || die "$1 requires a value"; MONITOR_CONSECUTIVE_CLI="$2"; shift ;;
    --monitor-heartbeat) [[ $# -ge 2 ]] || die "$1 requires a value"; MONITOR_HEARTBEAT_CLI="$2"; shift ;;
    --api-access) [[ $# -ge 2 ]] || die "$1 requires local, docker, or lan"; API_ACCESS_CLI="$2"; shift ;;
    --api-docker-port) [[ $# -ge 2 ]] || die "$1 requires a value"; API_DOCKER_PORT_CLI="$2"; shift ;;
    --api-lan-address) [[ $# -ge 2 ]] || die "$1 requires a value"; API_LAN_ADDRESS_CLI="$2"; shift ;;
    --api-lan-port) [[ $# -ge 2 ]] || die "$1 requires a value"; API_LAN_PORT_CLI="$2"; shift ;;
    --migrate-manifest) MIGRATE_MANIFEST=1 ;;
    --refresh-profile-defaults) REFRESH_PROFILE_DEFAULTS=1 ;;
    --yes) YES=1 ;; --no-start) START=0 ;; --service) SERVICE_CLI=1 ;; --no-service) SERVICE_CLI=0 ;;
    --dry-run) DRY_RUN=1 ;; -h|--help) usage; exit 0 ;; *) die "unknown argument: $1" ;;
  esac
  shift
done

if [[ "${LIST_MODELS}" == 1 || "${LIST_BACKENDS}" == 1 ]]; then
  if [[ "${LIST_MODELS}" == 1 ]]; then
    profile_manager_active=""
    if [[ -r "${STATE_FILE}" && -r "${STATE_PARSER}" ]] && parse_install_manifest 2>/dev/null; then
      if [[ -n "${MODEL_DIR:-}" ]]; then
        export QWEN38_MODEL_ROOT
        QWEN38_MODEL_ROOT="$(realpath -m -- "$(dirname -- "${MODEL_DIR}")")"
      fi
      [[ "${PHASE:-}" != complete ]] || profile_manager_active="${MODEL_PROFILE}"
    fi
    print_profile_manager "${profile_manager_active}"
  fi
  if [[ "${LIST_MODELS}" == 1 && "${LIST_BACKENDS}" == 1 ]]; then
    printf '\n'
  fi
  if [[ "${LIST_BACKENDS}" == 1 ]]; then
    print_serving_backends
  fi
  exit 0
fi

if [[ "${DRY_RUN}" != 1 ]]; then
  ensure_operation_lock
fi
if [[ "${DRY_RUN}" != 1 ]]; then
  [[ -r "${PROFILE_SWITCH_TRANSITION}" ]] || die "profile-switch transition helper is unavailable: ${PROFILE_SWITCH_TRANSITION}"
  bash "${PROFILE_SWITCH_TRANSITION}" recover
fi

RESUME=0
if [[ -r "${STATE_FILE}" ]]; then
  [[ -r "${STATE_PARSER}" ]] || die "strict state parser is unavailable: ${STATE_PARSER}"
  manifest_profile="$(read_manifest_profile)" || die "installation manifest failed strict maintenance parsing: ${STATE_FILE}"
  manifest_phase="$(read_manifest_phase)" || die "installation manifest failed strict maintenance parsing: ${STATE_FILE}"
  if [[ "${manifest_phase}" == complete && "${YES}" != 1 && "${MIGRATE_MANIFEST}" != 1 && -z "${MODEL_CLI}" ]]; then
    parse_install_manifest || die "installation manifest failed strict maintenance parsing: ${STATE_FILE}"
    [[ -z "${CLI_LANG}" ]] || UI_LANG="${CLI_LANG}"
    [[ -n "${UI_LANG}" ]] || UI_LANG=ko
    [[ "${UI_LANG}" == en || "${UI_LANG}" == ko ]] || die "--lang must be en or ko"
    [[ "${UI_LANG}" == ko ]] && wizard_header 'Qwen3.8 Flash Next - DGX Spark 설치' || wizard_header 'Qwen3.8 Flash Next - DGX Spark Setup'
    wizard_choose_model_profile "${manifest_profile}" existing
    MODEL_CLI="${MODEL_PROFILE}"
  fi
  if [[ "${manifest_phase}" == uninstalled ]]; then
    # A normal uninstall preserves the manifest so ownership/history are not lost.
    # Treat that state as a fresh profile selection, while retaining shared swap
    # ownership and operator preferences that still apply to the next install.
    parse_install_manifest || die "installation manifest failed strict maintenance parsing: ${STATE_FILE}"
    MODEL_PROFILE="${MODEL_CLI:-orcarouter}"
    MODEL_REPO=""; MODEL_REVISION=""; MODEL_DIR=""; MODEL_OWNED=0
    VLLM_IMAGE=""; IMAGE_OWNED=0; SERVED_NAME=""
    CONFIG_OVERRIDE=""; CONFIG_OWNED=0
    PROXY_OWNED=0; SERVICE_OWNED=0
    UI_LANG=""
    PHASE=""
    RESUME=0
  elif [[ -n "${MODEL_CLI}" && "${MODEL_CLI}" != "${manifest_profile}" ]]; then
    # A profile switch is a runtime replacement, not a model purge. Reuse the
    # existing model root and shared operational settings while selecting fresh
    # model-specific metadata for the requested target profile.
    parse_install_manifest || die "installation manifest failed strict maintenance parsing: ${STATE_FILE}"
    PROFILE_SWITCH=1
    SWITCH_FROM_PROFILE="${MODEL_PROFILE}"
    SWITCH_MODEL_ROOT="$(realpath -m -- "$(dirname -- "${MODEL_DIR}")")"
    MODEL_PROFILE="${MODEL_CLI}"
    MODEL_REPO=""; MODEL_REVISION=""; MODEL_DIR=""; MODEL_OWNED=0
    VLLM_IMAGE=""; IMAGE_OWNED=0; SERVED_NAME=""
    CONFIG_OVERRIDE=""; CONFIG_OWNED=0
    PHASE=""
    RESUME=0
    if [[ "${DRY_RUN}" != 1 ]]; then
      [[ ! -e "${STATE_DIR}/runtime-transition.env" && ! -L "${STATE_DIR}/runtime-transition.env" ]] || \
        die "a runtime transition is active; wait for it to commit or recover it before switching profiles"
      [[ ! -e "${STATE_DIR}/update-transition.env" && ! -L "${STATE_DIR}/update-transition.env" ]] || \
        die "an update transition is active; finish or recover it before switching profiles"
      bash "${PROFILE_SWITCH_TRANSITION}" prepare "${SWITCH_FROM_PROFILE}" "${MODEL_PROFILE}"
      STATE_WRITE_FILE="${PROFILE_SWITCH_CANDIDATE}"
      trap restore_profile_switch_manifest_on_exit EXIT
    fi
  else
    parse_install_manifest || die "installation manifest failed strict maintenance parsing: ${STATE_FILE}"
    RESUME=1
  fi
fi
MONITOR_ENABLED="${MONITOR_ENABLED:-${MONITOR_PROTECT:-0}}"
[[ -z "${MONITOR_ENABLED_CLI}" ]] || MONITOR_ENABLED="${MONITOR_ENABLED_CLI}"
[[ -z "${MONITOR_PROTECT_CLI}" ]] || MONITOR_PROTECT="${MONITOR_PROTECT_CLI}"
[[ -z "${MONITOR_MIN_AVAILABLE_CLI}" ]] || MONITOR_MIN_AVAILABLE_GIB="${MONITOR_MIN_AVAILABLE_CLI}"
[[ -z "${MONITOR_MIN_FREE_CLI}" ]] || MONITOR_MIN_FREE_GIB="${MONITOR_MIN_FREE_CLI}"
[[ -z "${MONITOR_FREE_GATE_CLI}" ]] || MONITOR_FREE_GATE_GIB="${MONITOR_FREE_GATE_CLI}"
[[ -z "${MONITOR_MIN_SWAP_FREE_CLI}" ]] || MONITOR_MIN_SWAP_FREE_GIB="${MONITOR_MIN_SWAP_FREE_CLI}"
[[ -z "${MONITOR_CONSECUTIVE_CLI}" ]] || MONITOR_CONSECUTIVE="${MONITOR_CONSECUTIVE_CLI}"
[[ -z "${MONITOR_HEARTBEAT_CLI}" ]] || MONITOR_HEARTBEAT="${MONITOR_HEARTBEAT_CLI}"
if [[ "${CONFIG_OVERRIDE_CLI_SET}" == 1 ]]; then
  CONFIG_OVERRIDE="${CONFIG_OVERRIDE_CLI}"
  CONFIG_OWNED=0
fi
validate_monitor_settings
[[ -z "${MODEL_CLI}" ]] || MODEL_PROFILE="${MODEL_CLI}"
if [[ "${PROFILE_SWITCH}" == 1 && -z "${MODEL_ROOT_CLI}" && -z "${MODEL_ROOT_ENV}" ]]; then
  MODEL_ROOT="${SWITCH_MODEL_ROOT}"
  MODEL_ROOT_SOURCE=manifest-switch
  export QWEN38_MODEL_ROOT="${MODEL_ROOT}"
elif [[ "${RESUME}" == 1 && -n "${MODEL_DIR:-}" ]]; then
  MODEL_ROOT="$(realpath -m -- "$(dirname -- "${MODEL_DIR}")")"
  MODEL_ROOT_SOURCE=manifest
  export QWEN38_MODEL_ROOT="${MODEL_ROOT}"
else
  choose_default_model_root
fi
load_model_profile "${MODEL_PROFILE}" || exit $?
if [[ "${RESUME}" == 0 && "${PROFILE_SWITCH}" == 0 && "${MODEL_PROFILE}" == orcarouter-hybrid &&
      -z "${MONITOR_ENABLED_ENV_SET}" && -z "${MONITOR_PROTECT_ENV_SET}" &&
      -z "${MONITOR_ENABLED_CLI}" && -z "${MONITOR_PROTECT_CLI}" ]]; then
  # Hybrid H6 can exhaust non-CMA host memory while raw MemFree still looks
  # healthy because CMA pages dominate. Fresh non-interactive installs protect
  # the host by default; operators can opt out with --monitor/--no-monitor.
  MONITOR_ENABLED=1
  MONITOR_PROTECT=1
fi
REPO="${PROFILE_REPO}"; REVISION="${PROFILE_REVISION}"
MODEL_DIR="${MODEL_DIR:-${PROFILE_MODEL_DIR}}"
IMAGE="${VLLM_IMAGE:-${PROFILE_IMAGE}}"
SERVED_NAME="${SERVED_NAME:-${PROFILE_SERVED_NAME}}"
if [[ "${RESUME}" == 1 ]]; then
  [[ "${MODEL_REPO:-}" == "${REPO}" && "${MODEL_REVISION:-}" == "${REVISION}" ]] || \
    die "existing manifest belongs to a different model or revision: ${STATE_FILE}"
  IMAGE="${VLLM_IMAGE}"; SERVED_NAME="${SERVED_NAME:-${PROFILE_SERVED_NAME}}"
  if [[ "${REFRESH_PROFILE_DEFAULTS}" == 1 ]]; then
    OLD_PROFILE_IMAGE="${IMAGE}"
    IMAGE="${PROFILE_IMAGE}"
    IMAGE_OWNED=0
  fi
elif [[ "${REFRESH_PROFILE_DEFAULTS}" == 1 ]]; then
  die "--refresh-profile-defaults requires an existing installation manifest"
fi

# Schema <=3 recorded only docker0 proxy state. Preserve that meaning during migration.
if [[ -z "${API_ACCESS_MODE}" ]]; then
  [[ "${PROXY_ENABLED:-0}" == 1 ]] && API_ACCESS_MODE=docker || API_ACCESS_MODE=local
fi
API_DOCKER_PORT="${API_DOCKER_PORT:-${PROXY_PORT:-8000}}"
API_LAN_ADDRESS="${API_LAN_ADDRESS:-}"
API_LAN_PORT="${API_LAN_PORT:-8001}"
[[ -z "${API_ACCESS_CLI}" ]] || API_ACCESS_MODE="${API_ACCESS_CLI}"
[[ -z "${API_DOCKER_PORT_CLI}" ]] || API_DOCKER_PORT="${API_DOCKER_PORT_CLI}"
[[ -z "${API_LAN_ADDRESS_CLI}" ]] || API_LAN_ADDRESS="${API_LAN_ADDRESS_CLI}"
[[ -z "${API_LAN_PORT_CLI}" ]] || API_LAN_PORT="${API_LAN_PORT_CLI}"

[[ -z "${CLI_LANG}" ]] || UI_LANG="${CLI_LANG}"

if [[ "${RESUME}" == 0 && "${PROFILE_SWITCH}" == 0 && "${YES}" != 1 && -z "${CLI_LANG}" ]]; then
  wizard_header 'Qwen3.8 Flash Next - DGX Spark Setup'
  wizard_step 1 6 '언어 선택 / Language'
  wizard_menu_option 1 '한국어' '기본값 / Default'
  wizard_menu_option 2 'English'
  wizard_input answer '선택 / Select' 1
  case "${answer}" in
    2|en|EN|English|english) UI_LANG=en ;;
    *) UI_LANG=ko ;;
  esac
elif [[ -z "${UI_LANG}" ]]; then
  UI_LANG=ko
fi
[[ "${UI_LANG}" == en || "${UI_LANG}" == ko ]] || die "--lang must be en or ko"

if [[ "${RESUME}" == 1 ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    wizard_header 'Qwen3.8 Flash Next - DGX Spark 설치'
    wizard_info "설치 재개 단계: ${PHASE:-알 수 없음}"
  else
    wizard_header 'Qwen3.8 Flash Next - DGX Spark Setup'
    wizard_info "Resuming installation from phase: ${PHASE:-unknown}"
  fi
elif [[ "${YES}" == 1 || -n "${CLI_LANG}" ]]; then
  [[ "${UI_LANG}" == ko ]] && wizard_header 'Qwen3.8 Flash Next - DGX Spark 설치' || wizard_header 'Qwen3.8 Flash Next - DGX Spark Setup'
fi

if [[ "${YES}" != 1 && "${RESUME}" != 1 && -z "${MODEL_CLI}" ]]; then
  wizard_choose_model_profile "" fresh
  reload_profile_for_model_root || exit $?
fi

if [[ "${YES}" != 1 && "${RESUME}" != 1 && "${PROFILE_SWITCH}" != 1 && -z "${MODEL_ROOT_CLI}" && -z "${MODEL_ROOT_ENV}" ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    wizard_step 3 6 '모델 저장 위치'
  else
    wizard_step 3 6 'Model storage'
  fi

  repo_model_root="$(realpath -m -- "${ROOT_DIR}/models")"
  existing_home_root="$(realpath -m -- "${HOME}/models")"
  if model_root_has_complete_assets "${existing_home_root}" && [[ "${existing_home_root}" != "${repo_model_root}" ]]; then
    if [[ "${UI_LANG}" == ko ]]; then
      wizard_info "기존 검증 모델 저장소 발견: ${existing_home_root}"
      wizard_info "새 설치 기본 위치: ${repo_model_root}"
      wizard_menu_option 1 '기존 모델 저장소 재사용 (권장)' "${existing_home_root}"
      wizard_menu_option 2 '현재 저장소의 models 폴더 사용' "${repo_model_root}"
      wizard_menu_option 3 '직접 입력'
      wizard_input answer '선택' 1
    else
      wizard_info "Existing verified model store found: ${existing_home_root}"
      wizard_info "Fresh-install default: ${repo_model_root}"
      wizard_menu_option 1 'Reuse existing model store (recommended)' "${existing_home_root}"
      wizard_menu_option 2 'Use repository-local models directory' "${repo_model_root}"
      wizard_menu_option 3 'Enter another path'
      wizard_input answer 'Select' 1
    fi
    case "${answer}" in
      2) MODEL_ROOT="${repo_model_root}"; MODEL_ROOT_SOURCE=repo-default ;;
      3)
        [[ "${UI_LANG}" == ko ]] && wizard_input MODEL_ROOT '모델 저장 루트' "${repo_model_root}" || wizard_input MODEL_ROOT 'Model storage root' "${repo_model_root}"
        MODEL_ROOT_SOURCE=custom
        ;;
      *) MODEL_ROOT="${existing_home_root}"; MODEL_ROOT_SOURCE=existing-home ;;
    esac
  else
    if [[ "${UI_LANG}" == ko ]]; then
      wizard_info "모델은 현재 저장소 아래 models 폴더에 저장됩니다."
      wizard_input MODEL_ROOT '모델 저장 루트' "${repo_model_root}"
    else
      wizard_info "Models are stored under the repository-local models directory by default."
      wizard_input MODEL_ROOT 'Model storage root' "${repo_model_root}"
    fi
    MODEL_ROOT_SOURCE=repo-default
  fi
  MODEL_ROOT="$(realpath -m -- "$(expand_user_path "${MODEL_ROOT}")")"
  reload_profile_for_model_root || exit $?
fi

MODEL_OWNED="${MODEL_OWNED:-0}"; SWAP_OWNED="${SWAP_OWNED:-0}"; IMAGE_OWNED="${IMAGE_OWNED:-0}"
CONFIG_OWNED="${CONFIG_OWNED:-0}"
PROXY_ENABLED="${PROXY_ENABLED:-0}"; PROXY_OWNED="${PROXY_OWNED:-0}"; PROXY_PORT="${PROXY_PORT:-8000}"
SERVICE_ENABLED="${SERVICE_ENABLED:-1}"; SERVICE_OWNED="${SERVICE_OWNED:-0}"
[[ -z "${SERVICE_CLI}" ]] || SERVICE_ENABLED="${SERVICE_CLI}"
if [[ "${PROFILE_SWITCH}" == 1 && "${DRY_RUN}" != 1 ]]; then
  [[ "${START}" == 1 ]] || die "transactional profile switch requires runtime startup; omit --no-start"
  [[ "${SERVICE_ENABLED}" == 1 && "${SERVICE_OWNED}" == 1 ]] || \
    die "transactional profile switch requires an owned managed systemd service; uninstall first for unmanaged/no-service installs"
fi
if [[ "${REFRESH_PROFILE_DEFAULTS}" == 1 && "${MIGRATE_MANIFEST}" == 1 ]]; then
  die "--refresh-profile-defaults cannot be combined with --migrate-manifest"
fi
if [[ "${MIGRATE_MANIFEST}" == 1 ]]; then
  [[ "${RESUME}" == 1 ]] || die "--migrate-manifest requires an existing installation manifest"
  validate_api_access_settings
  if [[ "${DRY_RUN}" == 1 ]]; then
    printf 'DRY-RUN: installation manifest is valid and would be migrated to schema 4: %s\n' "${STATE_FILE}"
    exit 0
  fi
  write_state "${PHASE:-complete}"
  printf 'Installation manifest migrated to schema 4: %s\n' "${STATE_FILE}"
  exit 0
fi
[[ "$(uname -m)" == aarch64 ]] || printf 'WARNING: expected aarch64, found %s\n' "$(uname -m)"
if [[ "${YES}" != 1 && "${RESUME}" != 1 && "${PROFILE_SWITCH}" != 1 ]]; then
  [[ "${UI_LANG}" == ko ]] && wizard_step 4 6 '런타임 설정' || wizard_step 4 6 'Runtime settings'
  if [[ -n "${CONFIG_OVERRIDE}" ]]; then
    if [[ "${UI_LANG}" == ko ]]; then
      wizard_yes_no "설정된 config.json override를 사용합니까? (${CONFIG_OVERRIDE})" yes || CONFIG_OVERRIDE=""
    else
      wizard_yes_no "Use the configured config.json override? (${CONFIG_OVERRIDE})" yes || CONFIG_OVERRIDE=""
    fi
  else
    if [[ "${UI_LANG}" == ko ]]; then
      if wizard_yes_no '별도의 config.json override를 사용합니까?' no; then
        wizard_input CONFIG_OVERRIDE '절대 경로 또는 ~/path/to/config.json' ''
        [[ -n "${CONFIG_OVERRIDE}" ]] || die "config override path cannot be empty"
      fi
    else
      if wizard_yes_no 'Use a separate config.json override?' no; then
        wizard_input CONFIG_OVERRIDE 'Absolute path or ~/path/to/config.json' ''
        [[ -n "${CONFIG_OVERRIDE}" ]] || die "config override path cannot be empty"
      fi
    fi
  fi

  if [[ "${UI_LANG}" == ko ]]; then
    wizard_yes_no '런타임 메모리 모니터를 활성화합니까?' yes && MONITOR_ENABLED=1 || MONITOR_ENABLED=0
  else
    wizard_yes_no 'Enable the runtime memory monitor?' yes && MONITOR_ENABLED=1 || MONITOR_ENABLED=0
  fi
  if [[ "${MONITOR_ENABLED}" == 1 ]]; then
    if [[ "${UI_LANG}" == ko ]]; then
      protect_default=no; [[ "${MODEL_PROFILE}" == orcarouter-hybrid ]] && protect_default=yes
      wizard_yes_no '지속적인 저메모리 상태에서 컨테이너를 안전하게 중지합니까?' "${protect_default}" && MONITOR_PROTECT=1 || MONITOR_PROTECT=0
      if wizard_yes_no '권장 모니터 임계값과 heartbeat를 변경합니까?' no; then
        wizard_input MONITOR_MIN_AVAILABLE_GIB 'MemAvailable GiB' "${MONITOR_MIN_AVAILABLE_GIB}"
        wizard_input MONITOR_MIN_FREE_GIB 'MemFree GiB' "${MONITOR_MIN_FREE_GIB}"
        wizard_input MONITOR_FREE_GATE_GIB 'MemAvailable gate GiB' "${MONITOR_FREE_GATE_GIB}"
        wizard_input MONITOR_MIN_SWAP_FREE_GIB 'SwapFree GiB' "${MONITOR_MIN_SWAP_FREE_GIB}"
        wizard_input MONITOR_CONSECUTIVE 'Consecutive samples' "${MONITOR_CONSECUTIVE}"
        wizard_input MONITOR_HEARTBEAT 'Heartbeat seconds (0 disables)' "${MONITOR_HEARTBEAT}"
      fi
    else
      protect_default=no; [[ "${MODEL_PROFILE}" == orcarouter-hybrid ]] && protect_default=yes
      wizard_yes_no 'Stop the container safely after sustained low memory?' "${protect_default}" && MONITOR_PROTECT=1 || MONITOR_PROTECT=0
      if wizard_yes_no 'Customize the recommended monitor thresholds and heartbeat?' no; then
        wizard_input MONITOR_MIN_AVAILABLE_GIB 'MemAvailable GiB' "${MONITOR_MIN_AVAILABLE_GIB}"
        wizard_input MONITOR_MIN_FREE_GIB 'MemFree GiB' "${MONITOR_MIN_FREE_GIB}"
        wizard_input MONITOR_FREE_GATE_GIB 'MemAvailable gate GiB' "${MONITOR_FREE_GATE_GIB}"
        wizard_input MONITOR_MIN_SWAP_FREE_GIB 'SwapFree GiB' "${MONITOR_MIN_SWAP_FREE_GIB}"
        wizard_input MONITOR_CONSECUTIVE 'Consecutive samples' "${MONITOR_CONSECUTIVE}"
        wizard_input MONITOR_HEARTBEAT 'Heartbeat seconds (0 disables)' "${MONITOR_HEARTBEAT}"
      fi
    fi
  else
    MONITOR_PROTECT=0
  fi

  if [[ "${UI_LANG}" == ko ]]; then
    wizard_step 5 6 'API 및 서비스'
    wizard_menu_option 1 '이 PC에서만 사용' '127.0.0.1:8888'
    wizard_menu_option 2 'Docker 앱에서도 사용' 'OpenWebUI 등 / 기본 포트 8000'
    wizard_menu_option 3 'Docker 앱 + LAN의 다른 PC에서도 사용'
    wizard_input answer '선택' 2
  else
    wizard_step 5 6 'API and service'
    wizard_menu_option 1 'This PC only' '127.0.0.1:8888'
    wizard_menu_option 2 'Also available to Docker apps' 'OpenWebUI etc. / default port 8000'
    wizard_menu_option 3 'Docker apps + other PCs on the LAN'
    wizard_input answer 'Select' 2
  fi
  case "${answer:-2}" in
    1|local) API_ACCESS_MODE=local ;;
    2|docker) API_ACCESS_MODE=docker ;;
    3|lan) API_ACCESS_MODE=lan ;;
    *) die "invalid API access selection" ;;
  esac
  if [[ "${API_ACCESS_MODE}" == docker || "${API_ACCESS_MODE}" == lan ]]; then
    [[ "${UI_LANG}" == ko ]] && wizard_input API_DOCKER_PORT 'Docker 앱 API 포트' "${API_DOCKER_PORT}" || wizard_input API_DOCKER_PORT 'Docker-app API port' "${API_DOCKER_PORT}"
  fi
  if [[ "${API_ACCESS_MODE}" == lan ]]; then
    detected_lan="$(detect_lan_ipv4)"
    [[ "${UI_LANG}" == ko ]] && wizard_input API_LAN_ADDRESS 'LAN에서 사용할 DGX IPv4 주소' "${detected_lan}" || wizard_input API_LAN_ADDRESS 'DGX IPv4 address to expose on the LAN' "${detected_lan}"
    if [[ "${UI_LANG}" == ko ]]; then
      wizard_input API_LAN_PORT 'LAN API 포트 (신규 권장 8001, 기존 URL 호환은 8000)' "${API_LAN_PORT}"
    else
      wizard_input API_LAN_PORT 'LAN API port (8001 recommended for new installs; use 8000 for legacy URL compatibility)' "${API_LAN_PORT}"
    fi
  else
    API_LAN_ADDRESS=""
  fi

  if [[ "${UI_LANG}" == ko ]]; then
    wizard_yes_no '부팅 시 자동 시작되는 systemd 서비스를 등록합니까?' yes && SERVICE_ENABLED=1 || SERVICE_ENABLED=0
  else
    wizard_yes_no 'Install a systemd service that starts at boot?' yes && SERVICE_ENABLED=1 || SERVICE_ENABLED=0
  fi
fi
validate_monitor_settings
validate_api_access_settings
MODEL_DIR="$(expand_user_path "${MODEL_DIR}")"
[[ -z "${CONFIG_OVERRIDE}" ]] || CONFIG_OVERRIDE="$(expand_user_path "${CONFIG_OVERRIDE}")"
MODEL_DIR="$(realpath -m -- "${MODEL_DIR}")"
[[ -z "${CONFIG_OVERRIDE}" ]] || CONFIG_OVERRIDE="$(realpath -m -- "${CONFIG_OVERRIDE}")"
HYBRID_BASE_DIR="${ORCAROUTER_MODEL_DIR:-${MODEL_ROOT}/qwen3.8-flash-next-orcarouter}"
HYBRID_OVERLAY_DIR="${MAZINB_MODEL_DIR:-${MODEL_ROOT}/qwen3.8-flash-next-mazinb}"
HYBRID_H3_DIR="${HYBRID_QUANT_LAYOUT_MODEL_DIR:-${MODEL_ROOT}/qwen3.8-hybrid-quant-layout}"
HYBRID_H4_DIR="${H4_ORCA_ALL_MODEL_DIR:-${MODEL_ROOT}/qwen3.8-h4-orca-all}"
HYBRID_H5_DIR="${H5_NEUTRAL_INPUT_MODEL_DIR:-${MODEL_ROOT}/qwen3.8-h5-neutral-input-scale}"
HYBRID_BASE_DIR="$(realpath -m -- "${HYBRID_BASE_DIR}")"
HYBRID_OVERLAY_DIR="$(realpath -m -- "${HYBRID_OVERLAY_DIR}")"
HYBRID_H3_DIR="$(realpath -m -- "${HYBRID_H3_DIR}")"
HYBRID_H4_DIR="$(realpath -m -- "${HYBRID_H4_DIR}")"
HYBRID_H5_DIR="$(realpath -m -- "${HYBRID_H5_DIR}")"
HYBRID_REUSE_H3=0
if [[ "${PROFILE_LOCAL_BUILD:-0}" == 1 ]]; then
  if HYBRID_QUANT_LAYOUT_MODEL_DIR="${HYBRID_H3_DIR}" \
    bash "${ROOT_DIR}/scripts/model/prepare-orcarouter-hybrid.sh" reuse-check >/dev/null 2>&1; then
    HYBRID_REUSE_H3=1
  fi
fi
[[ "${UI_LANG}" == ko ]] && wizard_step 6 6 '설치 계획 확인' || wizard_step 6 6 'Review installation plan'
if [[ -n "${CONFIG_OVERRIDE}" ]]; then
  config_plan="${CONFIG_OVERRIDE}"
elif [[ "${PROFILE_CONFIG_OVERRIDE}" == 1 ]]; then
  [[ "${UI_LANG}" == ko ]] && config_plan='자동 vLLM 호환 설정' || config_plan='automatic vLLM compatibility override'
else
  [[ "${UI_LANG}" == ko ]] && config_plan='체크포인트 기본 설정' || config_plan='checkpoint config'
fi

if [[ "${UI_LANG}" == ko ]]; then
  printf '모델\n'
  printf '  model       : %s\n' "${REPO}"
  printf '  profile     : %s\n' "${MODEL_PROFILE}"
  [[ "${PROFILE_SWITCH}" != 1 ]] || printf '  전환        : %s -> %s\n' "${SWITCH_FROM_PROFILE}" "${MODEL_PROFILE}"
  printf '  저장 루트   : %s\n' "${MODEL_ROOT}"
  printf '  directory   : %s\n' "${MODEL_DIR}"
  printf '  revision    : %s\n' "${REVISION}"
  printf '  image       : %s\n' "${IMAGE}"
else
  printf 'Model\n'
  printf '  model       : %s\n' "${REPO}"
  printf '  profile     : %s\n' "${MODEL_PROFILE}"
  [[ "${PROFILE_SWITCH}" != 1 ]] || printf '  switch      : %s -> %s\n' "${SWITCH_FROM_PROFILE}" "${MODEL_PROFILE}"
  printf '  storage root: %s\n' "${MODEL_ROOT}"
  printf '  directory   : %s\n' "${MODEL_DIR}"
  printf '  revision    : %s\n' "${REVISION}"
  printf '  image       : %s\n' "${IMAGE}"
fi
if [[ "${REFRESH_PROFILE_DEFAULTS}" == 1 && "${OLD_PROFILE_IMAGE:-${IMAGE}}" != "${IMAGE}" ]]; then
  printf '  image change: %s -> %s\n' "${OLD_PROFILE_IMAGE}" "${IMAGE}"
fi
if [[ "${PROFILE_LOCAL_BUILD:-0}" == 1 ]]; then
  printf '  hybrid base : %s\n' "${HYBRID_BASE_DIR}"
  if [[ "${HYBRID_REUSE_H3}" == 1 ]]; then
    [[ "${UI_LANG}" == ko ]] && printf '  hybrid mix  : 기존 H3 provenance 재사용 (mazinb source 다운로드 생략)\n' || printf '  hybrid mix  : reuse pinned H3 provenance (skip mazinb source download)\n'
  else
    printf '  hybrid mix  : %s\n' "${HYBRID_OVERLAY_DIR}"
  fi
fi

printf '\n'
if [[ "${UI_LANG}" == ko ]]; then
  printf '런타임\n'
  printf '  config      : %s\n' "${config_plan}"
  printf '  PLE swap    : %s (128 GiB, 기존 swap 보존)\n' "${SWAP_FILE}"
else
  printf 'Runtime\n'
  printf '  config      : %s\n' "${config_plan}"
  printf '  PLE swap    : %s (128 GiB; existing swap preserved)\n' "${SWAP_FILE}"
fi
printf '  protection  : %s\n' "$([[ "${MONITOR_PROTECT}" == 1 ]] && printf enabled || printf warn-only/manual)"
printf '  monitor     : %s (available=%s GiB warn, free=%s/%s GiB gate, swapfree=%s GiB, %s samples, heartbeat=%ss)\n' \
  "$([[ "${MONITOR_ENABLED}" == 1 ]] && printf enabled || printf disabled)" "${MONITOR_MIN_AVAILABLE_GIB}" \
  "${MONITOR_MIN_FREE_GIB}" "${MONITOR_FREE_GATE_GIB}" "${MONITOR_MIN_SWAP_FREE_GIB}" \
  "${MONITOR_CONSECUTIVE}" "${MONITOR_HEARTBEAT}"

case "${API_ACCESS_MODE}" in
  local) api_plan='local only: 127.0.0.1:8888' ;;
  docker) api_plan="Docker apps: ${API_DOCKER_PORT} -> 127.0.0.1:8888" ;;
  lan) api_plan="Docker apps: ${API_DOCKER_PORT}; LAN: ${API_LAN_ADDRESS}:${API_LAN_PORT} -> 127.0.0.1:8888" ;;
esac
printf '\n'
[[ "${UI_LANG}" == ko ]] && printf '접근 / 서비스\n' || printf 'Access / service\n'
printf '  API access  : %s\n' "${api_plan}"
printf '  service     : %s\n' "$([[ "${SERVICE_ENABLED}" == 1 ]] && printf 'systemd boot service via immutable current release' || printf 'Docker container via immutable current release')"
printf '\n'
[[ -z "${CONFIG_OVERRIDE}" || -f "${CONFIG_OVERRIDE}" ]] || die "config override does not exist: ${CONFIG_OVERRIDE}"
[[ "${UI_LANG}" == ko ]] && continue_prompt='계속 진행합니까?' || continue_prompt='Continue?'
ask_yes_no "${continue_prompt}" || die "$([[ "${UI_LANG}" == ko ]] && printf 취소됨 || printf cancelled)"

if [[ "${DRY_RUN}" == 1 ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    printf '\nDRY-RUN 완료: 다운로드, swap, release, API 접근 설정, service, Docker 및 manifest를 변경하지 않았습니다.\n'
  else
    printf '\nDRY-RUN complete: no download, swap, release, API access, service, Docker, or manifest changes were made.\n'
  fi
  exit 0
fi

for command in python3 curl docker sudo git; do command -v "${command}" >/dev/null || die "${command} is required"; done
docker info >/dev/null 2>&1 || die "Docker daemon unavailable or user lacks permission"
git -C "${ROOT_DIR}" rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "installer must run from a git checkout to create an immutable release baseline"
ensure_profile_auth

# Bootstrap schema-4 MODEL_OWNED/IMAGE_OWNED into the cumulative registry once,
# then derive the active compatibility flags from per-asset ownership. A profile
# switch therefore cannot erase ownership of assets created by earlier profiles.
asset_bootstrap_install
asset_track_profile_models
asset_track_profile_images

printf '\nChecking gated access, pinned revision and disk capacity...\n'
if [[ "${PROFILE_LOCAL_BUILD:-0}" == 1 ]]; then
  if [[ "${HYBRID_REUSE_H3}" == 1 ]]; then
    printf 'Pinned H3 provenance is reusable; mazinb source checkpoint download is not required.\n'
    MODEL_PROFILE=orcarouter REPO= REVISION= DEST="${HYBRID_BASE_DIR}" \
      "${ROOT_DIR}/scripts/download-weights.sh" --check
  else
    base_required_bytes="$(MODEL_PROFILE=orcarouter REPO= REVISION= DEST="${HYBRID_BASE_DIR}" \
      "${ROOT_DIR}/scripts/download-weights.sh" --required-bytes)"
    overlay_required_bytes="$(MODEL_PROFILE=mazinb REPO= REVISION= DEST="${HYBRID_OVERLAY_DIR}" \
      "${ROOT_DIR}/scripts/download-weights.sh" --required-bytes)"

    base_probe="${HYBRID_BASE_DIR}"
    while [[ ! -e "${base_probe}" ]]; do base_probe="$(dirname -- "${base_probe}")"; done
    overlay_probe="${HYBRID_OVERLAY_DIR}"
    while [[ ! -e "${overlay_probe}" ]]; do overlay_probe="$(dirname -- "${overlay_probe}")"; done
    base_fs="$(df --output=source "${base_probe}" | tail -n1 | tr -d ' ')"
    overlay_fs="$(df --output=source "${overlay_probe}" | tail -n1 | tr -d ' ')"

    if [[ "${base_fs}" == "${overlay_fs}" ]]; then
      available_bytes="$(df --output=avail -B1 "${base_probe}" | tail -n1 | tr -d ' ')"
      base_existing_bytes=0
      overlay_existing_bytes=0
      [[ ! -d "${HYBRID_BASE_DIR}" ]] || base_existing_bytes="$(du -sb "${HYBRID_BASE_DIR}" | cut -f1)"
      [[ ! -d "${HYBRID_OVERLAY_DIR}" ]] || overlay_existing_bytes="$(du -sb "${HYBRID_OVERLAY_DIR}" | cut -f1)"
      reserve_bytes=$((20 * 1024 * 1024 * 1024))
      combined_required_bytes=$((base_required_bytes + overlay_required_bytes + reserve_bytes))
      combined_capacity_bytes=$((available_bytes + base_existing_bytes + overlay_existing_bytes))
      if (( combined_capacity_bytes < combined_required_bytes )); then
        shortfall_bytes=$((combined_required_bytes - combined_capacity_bytes))
        die "insufficient disk space for hybrid source checkpoints plus 20 GiB reserve; free an additional $(awk -v n="${shortfall_bytes}" 'BEGIN {printf "%.2f", n/1073741824}') GiB"
      fi
      printf 'Hybrid combined disk preflight passed: %.2f GiB sources + 20 GiB reserve on %s\n' \
        "$(awk -v n="$((base_required_bytes + overlay_required_bytes))" 'BEGIN {printf "%.2f", n/1073741824}')" "${base_fs}"
    fi

    MODEL_PROFILE=orcarouter REPO= REVISION= DEST="${HYBRID_BASE_DIR}" \
      "${ROOT_DIR}/scripts/download-weights.sh" --check
    MODEL_PROFILE=mazinb REPO= REVISION= DEST="${HYBRID_OVERLAY_DIR}" \
      "${ROOT_DIR}/scripts/download-weights.sh" --check
  fi
else
  MODEL_PROFILE="${MODEL_PROFILE}" REPO="${REPO}" REVISION="${REVISION}" DEST="${MODEL_DIR}" \
    "${ROOT_DIR}/scripts/download-weights.sh" --check
fi
write_state prepared

if ! "${ROOT_DIR}/scripts/manage-swap.sh" status --file "${SWAP_FILE}" | grep -q 'active     : yes'; then
  printf '\nCreating dedicated PLE swap...\n'
  swap_args=(create --file "${SWAP_FILE}" --size-gib 128 --persist)
  [[ "${YES}" == 1 ]] && swap_args+=(--yes)
  sudo "${ROOT_DIR}/scripts/manage-swap.sh" "${swap_args[@]}"
  SWAP_OWNED=1
fi
write_state swap_ready

printf '\nDownloading and verifying pinned checkpoint inputs...\n'
write_state downloading
if [[ "${PROFILE_LOCAL_BUILD:-0}" == 1 ]]; then
  MODEL_PROFILE=orcarouter REPO= REVISION= DEST="${HYBRID_BASE_DIR}" \
    "${ROOT_DIR}/scripts/download-weights.sh"
  if [[ "${HYBRID_REUSE_H3}" != 1 ]]; then
    MODEL_PROFILE=mazinb REPO= REVISION= DEST="${HYBRID_OVERLAY_DIR}" \
      "${ROOT_DIR}/scripts/download-weights.sh"
  fi
  if ! docker image inspect vllm-orcarouter-v029:v1 >/dev/null 2>&1; then
    printf '\nPreparing vLLM v0.29 hybrid builder/runtime image...\n'
    docker build -t vllm-orcarouter-v029:v1 -f "${ROOT_DIR}/scripts/Dockerfile.v029-orcarouter" "${ROOT_DIR}/scripts"
  fi
  printf '\nBuilding/reusing OrcaRouter hybrid H3 -> H4-all -> H5 -> H6 chain...\n'
  ORCAROUTER_MODEL_DIR="${HYBRID_BASE_DIR}" \
  MAZINB_MODEL_DIR="${HYBRID_OVERLAY_DIR}" \
  HYBRID_QUANT_LAYOUT_MODEL_DIR="${HYBRID_H3_DIR}" \
  H4_ORCA_ALL_MODEL_DIR="${HYBRID_H4_DIR}" \
  H5_NEUTRAL_INPUT_MODEL_DIR="${HYBRID_H5_DIR}" \
  H6_W4A16_MODEL_DIR="${MODEL_DIR}" \
    bash "${ROOT_DIR}/scripts/model/prepare-orcarouter-hybrid.sh" build
else
  MODEL_PROFILE="${MODEL_PROFILE}" REPO="${REPO}" REVISION="${REVISION}" DEST="${MODEL_DIR}" \
    "${ROOT_DIR}/scripts/download-weights.sh"
fi
# Refresh fingerprints after successful downloads/builds. Claimed assets become
# ready only after their managed model/hybrid manifest exists.
asset_track_profile_models
write_state weights_ready
if [[ -z "${CONFIG_OVERRIDE}" && "${PROFILE_CONFIG_OVERRIDE}" == 1 ]]; then
  CONFIG_OVERRIDE="${STATE_DIR}/config.vllm.json"
  printf '\nPreparing vLLM-compatible model config...\n'
  python3 "${ROOT_DIR}/scripts/prepare-config.py" --model-dir "${MODEL_DIR}" --output "${CONFIG_OVERRIDE}"
  CONFIG_OWNED=1
  write_state config_ready
fi
if [[ "${PROFILE_LOCAL_BUILD:-0}" == 1 ]]; then
  printf '\nValidating generated OrcaRouter hybrid checkpoint chain...\n'
  hybrid_validate_args=(
    --base-dir "${HYBRID_BASE_DIR}"
    --h3-dir "${HYBRID_H3_DIR}"
    --h4-dir "${HYBRID_H4_DIR}"
    --h5-dir "${HYBRID_H5_DIR}"
    --model-dir "${MODEL_DIR}"
  )
  if [[ "${HYBRID_REUSE_H3}" == 1 ]]; then
    hybrid_validate_args+=(--runtime-only)
  else
    hybrid_validate_args+=(--overlay-dir "${HYBRID_OVERLAY_DIR}")
  fi
  python3 "${ROOT_DIR}/scripts/model/validate-orcarouter-hybrid.py" "${hybrid_validate_args[@]}"
else
  printf '\nInspecting checkpoint tensor headers...\n'
  inspect_args=(--offline --repo "${REPO}" --model-dir "${MODEL_DIR}")
  [[ -n "${CONFIG_OVERRIDE}" ]] && inspect_args+=(--config-override "${CONFIG_OVERRIDE}")
  python3 "${ROOT_DIR}/scripts/inspect-model.py" "${inspect_args[@]}"
fi
write_state inspected
printf '\nPreparing vLLM image...\n'
if [[ "${IMAGE}" == vllm-skinny-tp1:v1 ]]; then
  if ! docker image inspect "${IMAGE}" >/dev/null 2>&1; then
    docker build -t "${IMAGE}" -f "${ROOT_DIR}/scripts/Dockerfile.skinny-gemm" "${ROOT_DIR}/scripts"
  fi
elif [[ "${MODEL_PROFILE}" == nvidia && "${IMAGE}" == vllm-nv-mixed:v2 ]]; then
  if ! docker image inspect vllm-skinny-tp1:v1 >/dev/null 2>&1; then
    docker build -t vllm-skinny-tp1:v1 -f "${ROOT_DIR}/scripts/Dockerfile.skinny-gemm" "${ROOT_DIR}/scripts"
  fi
  if ! docker image inspect "${IMAGE}" >/dev/null 2>&1; then
    docker build -t "${IMAGE}" -f "${ROOT_DIR}/scripts/Dockerfile.nv-mixed" "${ROOT_DIR}/scripts"
  fi
elif [[ ( "${MODEL_PROFILE}" == mazinb || "${MODEL_PROFILE}" == orcarouter-hybrid ) && "${IMAGE}" == vllm-orcarouter-v029:v1 ]]; then
  if ! docker image inspect "${IMAGE}" >/dev/null 2>&1; then
    docker build -t "${IMAGE}" -f "${ROOT_DIR}/scripts/Dockerfile.v029-orcarouter" "${ROOT_DIR}/scripts"
  fi
else
  docker pull "${IMAGE}"
fi
# Bind installer ownership to the concrete image IDs now present locally.
asset_track_profile_images
write_state image_ready

if [[ "${API_ACCESS_MODE}" != local ]]; then
  if ! "${ROOT_DIR}/scripts/manage-proxy.sh" status >/dev/null 2>&1 || [[ "${PROXY_OWNED}" == 1 ]]; then
    printf '\nConfiguring managed API access...\n'
    proxy_args=(create --docker-port "${API_DOCKER_PORT}" --backend-port 8888 --yes)
    if [[ "${API_ACCESS_MODE}" == lan ]]; then
      proxy_args+=(--lan-address "${API_LAN_ADDRESS}" --lan-port "${API_LAN_PORT}")
    fi
    sudo "${ROOT_DIR}/scripts/manage-proxy.sh" "${proxy_args[@]}"
    PROXY_OWNED=1
  fi
  write_state proxy_ready
fi

printf '\nPreparing immutable runtime release...\n'
baseline_revision="$(git -C "${ROOT_DIR}" rev-parse HEAD)"
release_status="$(bash "${ROOT_DIR}/scripts/release-manager.sh" status)"
current_release="$(awk -F= '$1=="CURRENT_RELEASE" {print $2}' <<<"${release_status}")"
if [[ -z "${current_release}" || "${current_release}" == none ]]; then
  bash "${ROOT_DIR}/scripts/bootstrap-release.sh" "${baseline_revision}"
elif [[ "${current_release}" == "${baseline_revision}" ]]; then
  bash "${ROOT_DIR}/scripts/release-manager.sh" verify "${current_release}"
elif [[ "${RESUME}" == 0 ]]; then
  # A retained immutable release may survive a normal uninstall. A fresh install
  # must run the code revision that defines the newly selected profile rather than
  # silently reusing the older runtime payload.
  bash "${ROOT_DIR}/scripts/release-manager.sh" verify "${current_release}"
  bash "${ROOT_DIR}/scripts/release-manager.sh" stage "${baseline_revision}"
  bash "${ROOT_DIR}/scripts/lifecycle/qualify-release.sh" "${baseline_revision}"
  bash "${ROOT_DIR}/scripts/release-manager.sh" activate "${baseline_revision}"
  printf 'Immutable runtime release advanced for fresh install: %s -> %s\n'     "${current_release}" "${baseline_revision}"
else
  bash "${ROOT_DIR}/scripts/release-manager.sh" verify "${current_release}"
  die "immutable current release ${current_release} differs from installer revision ${baseline_revision}; recover or finish the existing installation before resuming with different code"
fi
[[ -L "${CURRENT_RELEASE_LINK}" ]] || die "immutable current release pointer is missing after release preparation"
RUNTIME_ROOT="$(readlink -f -- "${CURRENT_RELEASE_LINK}")"
[[ "${RUNTIME_ROOT}" == "${DATA_HOME}/releases/"* ]] || die "immutable current release pointer is unsafe: ${CURRENT_RELEASE_LINK}"
write_state release_ready

if [[ "${SERVICE_ENABLED}" == 1 ]]; then
  SERVICE_OWNED=1
  write_state service_ready
  if [[ "${PROFILE_SWITCH}" == 1 ]]; then
    # Candidate state is service-ready before it becomes canonical. The helper
    # persists the old manifest and activation boundary before systemd cutover.
    bash "${PROFILE_SWITCH_TRANSITION}" activate
    STATE_WRITE_FILE="${STATE_FILE}"
  fi
  service_args=(create --runtime-root "${CURRENT_RELEASE_LINK}" --yes)
  [[ "${START}" == 1 ]] && service_args+=(--start) || service_args+=(--no-start)
  sudo_with_operation_lock "${ROOT_DIR}/scripts/manage-service.sh" "${service_args[@]}"
  if [[ "${PROFILE_SWITCH}" == 1 ]]; then
    # manage-service returns only after the replacement container is healthy,
    # its served model ID matches, and the runtime commit attestation matches.
    bash "${PROFILE_SWITCH_TRANSITION}" runtime-committed
    PROFILE_SWITCH_COMMITTED=1
  fi
elif [[ "${START}" == 1 ]]; then
  printf '\nStarting runtime from immutable current release...\n'
  MODEL_PROFILE="${MODEL_PROFILE}" MODEL_DIR="${MODEL_DIR}" VLLM_IMAGE="${IMAGE}" SERVED_NAME="${SERVED_NAME}" \
    CONFIG_OVERRIDE="${CONFIG_OVERRIDE}" MONITOR_ENABLED="${MONITOR_ENABLED}" MONITOR_PROTECT="${MONITOR_PROTECT}" \
    MONITOR_MIN_AVAILABLE_GIB="${MONITOR_MIN_AVAILABLE_GIB}" MONITOR_MIN_FREE_GIB="${MONITOR_MIN_FREE_GIB}" \
    MONITOR_FREE_GATE_GIB="${MONITOR_FREE_GATE_GIB}" MONITOR_MIN_SWAP_FREE_GIB="${MONITOR_MIN_SWAP_FREE_GIB}" \
    MONITOR_CONSECUTIVE="${MONITOR_CONSECUTIVE}" MONITOR_HEARTBEAT="${MONITOR_HEARTBEAT}" \
    "${RUNTIME_ROOT}/scripts/serve.sh"
fi
write_state complete
if [[ "${PROFILE_SWITCH}" == 1 ]]; then
  bash "${PROFILE_SWITCH_TRANSITION}" commit
  trap - EXIT
fi
if [[ "${UI_LANG}" == ko ]]; then
  printf '\n설치가 완료되었습니다.\n  manifest: %s\n  runtime: %s\n' "${STATE_FILE}" "${CURRENT_RELEASE_LINK}"
  [[ "${SERVICE_ENABLED}" == 1 ]] && printf '  logs: journalctl -fu qwen38-flash-next.service\n' || printf '  logs: docker logs -f qwen38-flash-next\n'
else
  printf '\nInstallation completed.\n  manifest: %s\n  runtime: %s\n' "${STATE_FILE}" "${CURRENT_RELEASE_LINK}"
  [[ "${SERVICE_ENABLED}" == 1 ]] && printf '  logs: journalctl -fu qwen38-flash-next.service\n' || printf '  logs: docker logs -f qwen38-flash-next\n'
fi