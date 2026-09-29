#!/usr/bin/env bash
# Remove only resources recorded by install.sh.
set -euo pipefail

SCRIPT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STATE_PARSER="${SCRIPT_ROOT}/scripts/lib/state_file.py"
ASSET_OWNERSHIP_TOOL="${SCRIPT_ROOT}/scripts/lib/asset_ownership.py"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/install.env"
ASSET_OWNERSHIP_FILE="${STATE_DIR}/asset-ownership.json"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark"
RUNTIME_TRANSITION_FILE="${STATE_DIR}/runtime-transition.env"
UPDATE_TRANSITION_FILE="${STATE_DIR}/update-transition.env"
PROFILE_SWITCH_TRANSITION_FILE="${STATE_DIR}/profile-switch-transition.env"
PROFILE_SWITCH_BACKUP="${STATE_FILE}.profile-switch-backup"
PROFILE_SWITCH_CANDIDATE="${STATE_FILE}.profile-switch-candidate"
STOP_REASON_FILE="${STATE_DIR}/runtime-stop.env"
RUNTIME_COMMIT_FILE="${STATE_DIR}/runtime-commit.env"
OPERATION_LOCK_LIB="${SCRIPT_ROOT}/scripts/lib/operation-lock.sh"
PURGE_MODEL=0; PURGE_SWAP=0; PURGE_IMAGE=0; PURGE_SELECTED=0; PURGE_ALL=0; YES=0; DRY_RUN=0
CLI_LANG=""
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
usage() {
  printf 'Usage: ./uninstall.sh [--lang en|ko] [--purge-model] [--purge-swap] [--purge-image] [--purge-all] [--yes] [--dry-run]\n'
  printf '       ./uninstall.sh  # interactive English/Korean wizard (default)\n'
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
  if [[ -f "${ASSET_OWNERSHIP_FILE}" && ! -L "${ASSET_OWNERSHIP_FILE}" ]]; then
    python3 "${ASSET_OWNERSHIP_TOOL}" owns-model "${ASSET_OWNERSHIP_FILE}" "$1"
  else
    return 1
  fi
}
asset_image_owned() {
  if [[ -f "${ASSET_OWNERSHIP_FILE}" && ! -L "${ASSET_OWNERSHIP_FILE}" ]]; then
    python3 "${ASSET_OWNERSHIP_TOOL}" owns-image "${ASSET_OWNERSHIP_FILE}" "$1"
  else
    return 1
  fi
}
asset_forget() {
  python3 "${ASSET_OWNERSHIP_TOOL}" forget "${ASSET_OWNERSHIP_FILE}" "$1" "$2"
}
image_referenced_by_external_container() {
  local image="$1" name
  while IFS= read -r name; do
    [[ -n "${name}" ]] || continue
    [[ "${name}" == "${CONTAINER_NAME}" ]] && continue
    printf '%s\n' "${name}"
  done < <(docker ps -a --filter "ancestor=${image}" --format '{{.Names}}' 2>/dev/null)
}

asset_preflight_full_purge() {
  [[ -f "${ASSET_OWNERSHIP_FILE}" && ! -L "${ASSET_OWNERSHIP_FILE}" ]] || return 0
  python3 "${ASSET_OWNERSHIP_TOOL}" preflight-purge "${ASSET_OWNERSHIP_FILE}" --kind all
  local kind locator refs
  while IFS=$'\t' read -r kind locator; do
    [[ "${kind}" == image ]] || continue
    refs="$(image_referenced_by_external_container "${locator}")"
    if [[ -n "${refs}" ]]; then
      die "refusing image purge; ${locator} is referenced by other containers: ${refs}"
    fi
  done < <(python3 "${ASSET_OWNERSHIP_TOOL}" plan-purge "${ASSET_OWNERSHIP_FILE}" --kind all)
}

asset_apply_full_purge() {
  [[ -f "${ASSET_OWNERSHIP_FILE}" && ! -L "${ASSET_OWNERSHIP_FILE}" ]] || return 0
  local kind locator
  while IFS=$'\t' read -r kind locator; do
    case "${kind}" in
      model)
        if [[ -e "${locator}" || -L "${locator}" ]]; then
          rm -rf --one-file-system -- "${locator}"
          printf 'Removed owned model asset: %s\n' "${locator}"
        fi
        asset_forget model "${locator}"
        ;;
      image)
        if docker image inspect "${locator}" >/dev/null 2>&1; then
          docker image rm "${locator}" || die "owned image is still in use: ${locator}"
          printf 'Removed owned image asset: %s\n' "${locator}"
        fi
        asset_forget image "${locator}"
        ;;
      *) die "invalid asset purge plan kind: ${kind}" ;;
    esac
  done < <(python3 "${ASSET_OWNERSHIP_TOOL}" plan-purge "${ASSET_OWNERSHIP_FILE}" --kind all)
}
mark_manifest_uninstalled() {
  python3 - "${STATE_FILE}" <<'PY'
import os
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()
matches = [i for i, line in enumerate(lines) if line.startswith("PHASE=")]
if len(matches) != 1:
    raise SystemExit("installation manifest must contain exactly one PHASE field")
lines[matches[0]] = "PHASE=uninstalled"
temporary = path.with_name(path.name + ".tmp")
temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
os.chmod(temporary, path.stat().st_mode & 0o777)
os.replace(temporary, path)
PY
}

parse_install_manifest() {
  local parsed key value
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" install-uninstall "${STATE_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    printf -v "${key}" '%s' "${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lang) [[ $# -ge 2 ]] || die "--lang requires en or ko"; CLI_LANG="$2"; shift ;;
    --purge-model) PURGE_MODEL=1; PURGE_SELECTED=1 ;; --purge-swap) PURGE_SWAP=1; PURGE_SELECTED=1 ;; --purge-image) PURGE_IMAGE=1; PURGE_SELECTED=1 ;;
    --purge-all) PURGE_MODEL=1; PURGE_SWAP=1; PURGE_IMAGE=1; PURGE_SELECTED=1; PURGE_ALL=1 ;; --yes) YES=1 ;; --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;; *) die "unknown argument: $1" ;;
  esac
  shift
done
[[ -r "${STATE_FILE}" ]] || die "installation manifest not found: ${STATE_FILE}"
[[ -r "${STATE_PARSER}" ]] || die "strict state parser is unavailable: ${STATE_PARSER}"
parse_install_manifest || die "installation manifest failed strict uninstall parsing: ${STATE_FILE}"
[[ -z "${CLI_LANG}" ]] || UI_LANG="${CLI_LANG}"
if [[ -z "${UI_LANG:-}" ]]; then
  if [[ "${YES}" == 0 && -t 0 ]]; then
    read -r -p 'Language / 언어 [1: English, 2: 한국어] (2): ' answer
    [[ "${answer}" == 1 || "${answer}" == en ]] && UI_LANG=en || UI_LANG=ko
  elif [[ "${LANG:-}" == ko_* ]]; then UI_LANG=ko; else UI_LANG=en; fi
fi
[[ "${UI_LANG}" == en || "${UI_LANG}" == ko ]] || die "--lang must be en or ko"
[[ -n "${INSTALL_ROOT:-}" && -d "${INSTALL_ROOT}" ]] || die "invalid INSTALL_ROOT in manifest"
[[ -n "${CONTAINER_NAME:-}" && "${CONTAINER_NAME}" != */* ]] || die "invalid container name"
MONITOR_PID_FILE="${STATE_DIR}/monitor.pid"

if [[ "${YES}" == 0 && "${PURGE_SELECTED}" == 0 ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    read -r -p '다운로드한 모델도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_MODEL=1
    read -r -p '전용 PLE swap도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_SWAP=1
    read -r -p 'vLLM Docker image도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_IMAGE=1
  else
    read -r -p 'Remove the downloaded model too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_MODEL=1
    read -r -p 'Remove the dedicated PLE swap too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_SWAP=1
    read -r -p 'Remove the vLLM Docker image too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_IMAGE=1
  fi
fi

if [[ "${UI_LANG}" == ko ]]; then
  printf 'Qwen3.8 Flash Next 제거 마법사\n\n  container: %s (제거)\n' "${CONTAINER_NAME}"
  printf '  model    : %s (%s)\n' "${MODEL_DIR}" "$([[ "${PURGE_MODEL}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  PLE swap : %s (%s)\n' "${SWAP_FILE}" "$([[ "${PURGE_SWAP}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  image    : %s (%s)\n' "${VLLM_IMAGE}" "$([[ "${PURGE_IMAGE}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  service  : %s\n' "$([[ "${SERVICE_OWNED}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  releases : %s\n' "$([[ "${PURGE_ALL}" == 1 ]] && printf '전체 제거' || printf '보존')"
else
  printf 'Qwen3.8 Flash Next uninstaller wizard\n\n  container: %s (remove)\n' "${CONTAINER_NAME}"
  printf '  model    : %s (%s)\n' "${MODEL_DIR}" "$([[ "${PURGE_MODEL}" == 1 ]] && printf remove || printf keep)"
  printf '  PLE swap : %s (%s)\n' "${SWAP_FILE}" "$([[ "${PURGE_SWAP}" == 1 ]] && printf remove || printf keep)"
  printf '  image    : %s (%s)\n' "${VLLM_IMAGE}" "$([[ "${PURGE_IMAGE}" == 1 ]] && printf remove || printf keep)"
  printf '  service  : %s\n' "$([[ "${SERVICE_OWNED}" == 1 ]] && printf remove || printf keep)"
  printf '  releases : %s\n' "$([[ "${PURGE_ALL}" == 1 ]] && printf purge || printf keep)"
fi
if [[ "${DRY_RUN}" == 1 ]]; then
  if [[ "${PURGE_ALL}" == 1 ]]; then
    if [[ -f "${ASSET_OWNERSHIP_FILE}" && ! -L "${ASSET_OWNERSHIP_FILE}" && -r "${ASSET_OWNERSHIP_TOOL}" ]]; then
      printf '\nCumulative installer-owned assets selected by --purge-all:\n'
      python3 "${ASSET_OWNERSHIP_TOOL}" plan-purge "${ASSET_OWNERSHIP_FILE}" --kind all 2>/dev/null || \
        printf '  ownership registry is invalid; real purge would stop before deletion\n'
    else
      printf '\nNo cumulative ownership registry exists yet; a real purge can migrate only the current manifest ownership flags.\n'
    fi
  fi
  if [[ "${UI_LANG}" == ko ]]; then
    printf '\nDRY-RUN 완료: container, monitor, proxy, release, 모델, swap, image 및 manifest를 변경하지 않았습니다.\n'
  else
    printf '\nDRY-RUN complete: no container, monitor, proxy, release, model, swap, image, or manifest changes were made.\n'
  fi
  exit 0
fi

[[ -r "${OPERATION_LOCK_LIB}" ]] || die "operation lock helper is unavailable: ${OPERATION_LOCK_LIB}"
# shellcheck source=scripts/lib/operation-lock.sh
source "${OPERATION_LOCK_LIB}"
acquire_operation_lock "${STATE_DIR}" "uninstall" || exit $?

[[ ! -e "${UPDATE_TRANSITION_FILE}" && ! -L "${UPDATE_TRANSITION_FILE}" ]] || \
  die "an update transition is active; recover or roll it back before uninstalling"
[[ ! -e "${RUNTIME_TRANSITION_FILE}" && ! -L "${RUNTIME_TRANSITION_FILE}" ]] || \
  die "a runtime transition is active; recover or roll it back before uninstalling"
[[ ! -e "${PROFILE_SWITCH_TRANSITION_FILE}" && ! -L "${PROFILE_SWITCH_TRANSITION_FILE}" ]] || \
  die "a profile-switch transition is active; run scripts/profile-switch-transition.sh recover before uninstalling"
[[ ! -e "${PROFILE_SWITCH_BACKUP}" && ! -L "${PROFILE_SWITCH_BACKUP}" &&
   ! -e "${PROFILE_SWITCH_CANDIDATE}" && ! -L "${PROFILE_SWITCH_CANDIDATE}" ]] || \
  die "profile-switch artifacts exist without an active transaction; run doctor before uninstalling"

# Migrate the current manifest's legacy single-asset ownership into the cumulative
# registry before any destructive decision. This cannot infer assets whose
# ownership was already lost by older profile switches.
asset_bootstrap_install
if [[ "${PURGE_ALL}" == 1 ]]; then
  asset_preflight_full_purge
else
  if [[ "${PURGE_MODEL}" == 1 ]]; then
    python3 "${ASSET_OWNERSHIP_TOOL}" preflight-one "${ASSET_OWNERSHIP_FILE}" model "${MODEL_DIR}" || \
      die "refusing model deletion: active model is not safely recorded as installer-owned"
  fi
  if [[ "${PURGE_IMAGE}" == 1 ]]; then
    python3 "${ASSET_OWNERSHIP_TOOL}" preflight-one "${ASSET_OWNERSHIP_FILE}" image "${VLLM_IMAGE}" || \
      die "refusing image deletion: active image is not safely recorded as installer-owned"
    image_refs="$(image_referenced_by_external_container "${VLLM_IMAGE}")"
    if [[ -n "${image_refs}" ]]; then
      die "refusing image deletion; ${VLLM_IMAGE} is referenced by other containers: ${image_refs}"
    fi
  fi
fi

if [[ "${SERVICE_OWNED}" != 1 ]] && "${INSTALL_ROOT}/scripts/manage-service.sh" status >/dev/null 2>&1; then
  die "a managed runtime service exists but is not owned by this manifest; rerun install.sh to adopt it or remove it explicitly"
fi
if [[ "${YES}" != 1 ]]; then
  [[ "${UI_LANG}" == ko ]] && prompt='계속하려면 DELETE를 입력하십시오: ' || prompt='Type DELETE to continue: '
  read -r -p "${prompt}" answer
  [[ "${answer}" == DELETE ]] || die "$([[ "${UI_LANG}" == ko ]] && printf 취소됨 || printf cancelled)"
fi
if [[ -r "${MONITOR_PID_FILE}" ]]; then
  monitor_pid="$(<"${MONITOR_PID_FILE}")"
  if [[ "${monitor_pid}" =~ ^[0-9]+$ && -r "/proc/${monitor_pid}/cmdline" ]] && \
     tr '\0' ' ' < "/proc/${monitor_pid}/cmdline" | grep -Fq 'monitor-runtime.sh'; then
    kill "${monitor_pid}" 2>/dev/null || true
  fi
  rm -f -- "${MONITOR_PID_FILE}"
fi
if [[ "${SERVICE_OWNED}" == 1 ]]; then
  sudo_with_operation_lock "${INSTALL_ROOT}/scripts/manage-service.sh" remove --yes
fi
if [[ "${PROXY_OWNED}" == 1 ]]; then
  sudo "${INSTALL_ROOT}/scripts/manage-proxy.sh" remove --yes
fi
docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
rm -f -- "${STOP_REASON_FILE}" "${STOP_REASON_FILE}.tmp" "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"

if [[ "${PURGE_ALL}" == 1 ]]; then
  asset_apply_full_purge
elif [[ "${PURGE_MODEL}" == 1 ]]; then
  if [[ -e "${MODEL_DIR}" || -L "${MODEL_DIR}" ]]; then
    rm -rf --one-file-system -- "${MODEL_DIR}"
    printf 'Removed model directory: %s\n' "${MODEL_DIR}"
  fi
  asset_forget model "${MODEL_DIR}"
fi
if [[ "${PURGE_SWAP}" == 1 ]]; then
  [[ "${SWAP_OWNED}" == 1 ]] || die "refusing swap deletion: swap was not created by this installer"
  if [[ -e "${SWAP_FILE}" ]]; then
    swap_args=(remove --file "${SWAP_FILE}"); [[ "${YES}" == 1 ]] && swap_args+=(--yes)
    sudo "${INSTALL_ROOT}/scripts/manage-swap.sh" "${swap_args[@]}"
  fi
fi
if [[ "${PURGE_ALL}" != 1 && "${PURGE_IMAGE}" == 1 ]]; then
  if docker image inspect "${VLLM_IMAGE}" >/dev/null 2>&1; then
    docker image rm "${VLLM_IMAGE}" || die "image is still in use"
  fi
  asset_forget image "${VLLM_IMAGE}"
fi
if [[ "${PURGE_ALL}" == 1 ]]; then
  [[ "${DATA_HOME}" == "${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark" ]] || die "refusing unsafe release-data purge path: ${DATA_HOME}"
  if [[ "${CONFIG_OWNED}" == 1 && "${CONFIG_OVERRIDE:-}" == "${STATE_DIR}/config.vllm.json" ]]; then
    rm -f -- "${CONFIG_OVERRIDE}"
  fi
  rm -rf --one-file-system -- "${DATA_HOME}"
  rm -f -- "${STATE_DIR}/monitor.log" "${STATE_DIR}/monitor.pid" \
    "${STATE_DIR}/runtime-stop.env" "${STATE_DIR}/runtime-stop.env.tmp" \
    "${STATE_DIR}/runtime-commit.env" "${STATE_DIR}/runtime-commit.env.tmp" \
    "${STATE_DIR}/runtime-transition.env" "${STATE_DIR}/runtime-transition.env.tmp" \
    "${STATE_DIR}/update-transition.env" "${STATE_DIR}/update-transition.env.tmp" \
    "${STATE_DIR}/profile-switch-transition.env" "${STATE_DIR}/profile-switch-transition.env.tmp" \
    "${STATE_FILE}.profile-switch-backup" "${STATE_FILE}.profile-switch-candidate" "${STATE_FILE}.profile-switch-candidate.tmp" \
    "${ASSET_OWNERSHIP_FILE}"
  rm -f -- "${STATE_FILE}"
  rmdir --ignore-fail-on-non-empty "${STATE_DIR}" 2>/dev/null || true
  [[ "${UI_LANG}" == ko ]] && printf '전체 제거 완료; immutable release 데이터와 설치 manifest를 삭제했습니다.\n' || \
    printf 'Full uninstall completed; immutable release data and installation manifest removed.\n'
else
  mark_manifest_uninstalled
  if [[ "${UI_LANG}" == ko ]]; then
    printf '제거 완료. manifest를 uninstalled 상태로 보존했습니다. 다음 install.sh 실행에서 새 모델 프로필을 선택할 수 있습니다: %s\n' "${STATE_FILE}"
  else
    printf 'Uninstall completed. The manifest is retained in the uninstalled state; the next install.sh run may select a new model profile: %s\n' "${STATE_FILE}"
  fi
fi
\t' read -r kind locator; do
    [[ "${kind}" == image ]] || continue
    refs="$(image_referenced_by_external_container "${locator}")"
    [[ -z "${refs}" ]] || die "refusing image purge; ${locator} is referenced by other containers: ${refs//
mark_manifest_uninstalled() {
  python3 - "${STATE_FILE}" <<'PY'
import os
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()
matches = [i for i, line in enumerate(lines) if line.startswith("PHASE=")]
if len(matches) != 1:
    raise SystemExit("installation manifest must contain exactly one PHASE field")
lines[matches[0]] = "PHASE=uninstalled"
temporary = path.with_name(path.name + ".tmp")
temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
os.chmod(temporary, path.stat().st_mode & 0o777)
os.replace(temporary, path)
PY
}

parse_install_manifest() {
  local parsed key value
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" install-uninstall "${STATE_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    printf -v "${key}" '%s' "${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lang) [[ $# -ge 2 ]] || die "--lang requires en or ko"; CLI_LANG="$2"; shift ;;
    --purge-model) PURGE_MODEL=1; PURGE_SELECTED=1 ;; --purge-swap) PURGE_SWAP=1; PURGE_SELECTED=1 ;; --purge-image) PURGE_IMAGE=1; PURGE_SELECTED=1 ;;
    --purge-all) PURGE_MODEL=1; PURGE_SWAP=1; PURGE_IMAGE=1; PURGE_SELECTED=1; PURGE_ALL=1 ;; --yes) YES=1 ;; --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;; *) die "unknown argument: $1" ;;
  esac
  shift
done
[[ -r "${STATE_FILE}" ]] || die "installation manifest not found: ${STATE_FILE}"
[[ -r "${STATE_PARSER}" ]] || die "strict state parser is unavailable: ${STATE_PARSER}"
parse_install_manifest || die "installation manifest failed strict uninstall parsing: ${STATE_FILE}"
[[ -z "${CLI_LANG}" ]] || UI_LANG="${CLI_LANG}"
if [[ -z "${UI_LANG:-}" ]]; then
  if [[ "${YES}" == 0 && -t 0 ]]; then
    read -r -p 'Language / 언어 [1: English, 2: 한국어] (2): ' answer
    [[ "${answer}" == 1 || "${answer}" == en ]] && UI_LANG=en || UI_LANG=ko
  elif [[ "${LANG:-}" == ko_* ]]; then UI_LANG=ko; else UI_LANG=en; fi
fi
[[ "${UI_LANG}" == en || "${UI_LANG}" == ko ]] || die "--lang must be en or ko"
[[ -n "${INSTALL_ROOT:-}" && -d "${INSTALL_ROOT}" ]] || die "invalid INSTALL_ROOT in manifest"
[[ -n "${CONTAINER_NAME:-}" && "${CONTAINER_NAME}" != */* ]] || die "invalid container name"
MONITOR_PID_FILE="${STATE_DIR}/monitor.pid"

if [[ "${YES}" == 0 && "${PURGE_SELECTED}" == 0 ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    read -r -p '다운로드한 모델도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_MODEL=1
    read -r -p '전용 PLE swap도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_SWAP=1
    read -r -p 'vLLM Docker image도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_IMAGE=1
  else
    read -r -p 'Remove the downloaded model too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_MODEL=1
    read -r -p 'Remove the dedicated PLE swap too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_SWAP=1
    read -r -p 'Remove the vLLM Docker image too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_IMAGE=1
  fi
fi

if [[ "${UI_LANG}" == ko ]]; then
  printf 'Qwen3.8 Flash Next 제거 마법사\n\n  container: %s (제거)\n' "${CONTAINER_NAME}"
  printf '  model    : %s (%s)\n' "${MODEL_DIR}" "$([[ "${PURGE_MODEL}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  PLE swap : %s (%s)\n' "${SWAP_FILE}" "$([[ "${PURGE_SWAP}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  image    : %s (%s)\n' "${VLLM_IMAGE}" "$([[ "${PURGE_IMAGE}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  service  : %s\n' "$([[ "${SERVICE_OWNED}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  releases : %s\n' "$([[ "${PURGE_ALL}" == 1 ]] && printf '전체 제거' || printf '보존')"
else
  printf 'Qwen3.8 Flash Next uninstaller wizard\n\n  container: %s (remove)\n' "${CONTAINER_NAME}"
  printf '  model    : %s (%s)\n' "${MODEL_DIR}" "$([[ "${PURGE_MODEL}" == 1 ]] && printf remove || printf keep)"
  printf '  PLE swap : %s (%s)\n' "${SWAP_FILE}" "$([[ "${PURGE_SWAP}" == 1 ]] && printf remove || printf keep)"
  printf '  image    : %s (%s)\n' "${VLLM_IMAGE}" "$([[ "${PURGE_IMAGE}" == 1 ]] && printf remove || printf keep)"
  printf '  service  : %s\n' "$([[ "${SERVICE_OWNED}" == 1 ]] && printf remove || printf keep)"
  printf '  releases : %s\n' "$([[ "${PURGE_ALL}" == 1 ]] && printf purge || printf keep)"
fi
if [[ "${DRY_RUN}" == 1 ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    printf '\nDRY-RUN 완료: container, monitor, proxy, release, 모델, swap, image 및 manifest를 변경하지 않았습니다.\n'
  else
    printf '\nDRY-RUN complete: no container, monitor, proxy, release, model, swap, image, or manifest changes were made.\n'
  fi
  exit 0
fi

[[ -r "${OPERATION_LOCK_LIB}" ]] || die "operation lock helper is unavailable: ${OPERATION_LOCK_LIB}"
# shellcheck source=scripts/lib/operation-lock.sh
source "${OPERATION_LOCK_LIB}"
acquire_operation_lock "${STATE_DIR}" "uninstall" || exit $?

[[ ! -e "${UPDATE_TRANSITION_FILE}" && ! -L "${UPDATE_TRANSITION_FILE}" ]] || \
  die "an update transition is active; recover or roll it back before uninstalling"
[[ ! -e "${RUNTIME_TRANSITION_FILE}" && ! -L "${RUNTIME_TRANSITION_FILE}" ]] || \
  die "a runtime transition is active; recover or roll it back before uninstalling"
[[ ! -e "${PROFILE_SWITCH_TRANSITION_FILE}" && ! -L "${PROFILE_SWITCH_TRANSITION_FILE}" ]] || \
  die "a profile-switch transition is active; run scripts/profile-switch-transition.sh recover before uninstalling"
[[ ! -e "${PROFILE_SWITCH_BACKUP}" && ! -L "${PROFILE_SWITCH_BACKUP}" &&
   ! -e "${PROFILE_SWITCH_CANDIDATE}" && ! -L "${PROFILE_SWITCH_CANDIDATE}" ]] || \
  die "profile-switch artifacts exist without an active transaction; run doctor before uninstalling"

if [[ "${SERVICE_OWNED}" != 1 ]] && "${INSTALL_ROOT}/scripts/manage-service.sh" status >/dev/null 2>&1; then
  die "a managed runtime service exists but is not owned by this manifest; rerun install.sh to adopt it or remove it explicitly"
fi
if [[ "${YES}" != 1 ]]; then
  [[ "${UI_LANG}" == ko ]] && prompt='계속하려면 DELETE를 입력하십시오: ' || prompt='Type DELETE to continue: '
  read -r -p "${prompt}" answer
  [[ "${answer}" == DELETE ]] || die "$([[ "${UI_LANG}" == ko ]] && printf 취소됨 || printf cancelled)"
fi
if [[ -r "${MONITOR_PID_FILE}" ]]; then
  monitor_pid="$(<"${MONITOR_PID_FILE}")"
  if [[ "${monitor_pid}" =~ ^[0-9]+$ && -r "/proc/${monitor_pid}/cmdline" ]] && \
     tr '\0' ' ' < "/proc/${monitor_pid}/cmdline" | grep -Fq 'monitor-runtime.sh'; then
    kill "${monitor_pid}" 2>/dev/null || true
  fi
  rm -f -- "${MONITOR_PID_FILE}"
fi
if [[ "${SERVICE_OWNED}" == 1 ]]; then
  sudo_with_operation_lock "${INSTALL_ROOT}/scripts/manage-service.sh" remove --yes
fi
if [[ "${PROXY_OWNED}" == 1 ]]; then
  sudo "${INSTALL_ROOT}/scripts/manage-proxy.sh" remove --yes
fi
docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
rm -f -- "${STOP_REASON_FILE}" "${STOP_REASON_FILE}.tmp" "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"

if [[ "${PURGE_MODEL}" == 1 ]]; then
  [[ "${MODEL_OWNED}" == 1 ]] || die "refusing model deletion: directory was not created by this installer"
  if [[ -e "${MODEL_DIR}" ]]; then
    if [[ ! -f "${MODEL_DIR}/.qwen38-model-manifest.json" && ! -f "${MODEL_DIR}/.qwen38-hybrid-manifest.json" ]]; then
      die "refusing model deletion: managed model/hybrid manifest missing"
    fi
    if [[ "${MODEL_DIR}" != "${HOME}/models/"* && "${MODEL_DIR}" != "${INSTALL_ROOT}/model" ]]; then
      die "refusing model deletion outside ${HOME}/models or the install root's model directory"
    fi
    rm -rf --one-file-system -- "${MODEL_DIR}"
    printf 'Removed model directory: %s\n' "${MODEL_DIR}"
  fi
fi
if [[ "${PURGE_SWAP}" == 1 ]]; then
  [[ "${SWAP_OWNED}" == 1 ]] || die "refusing swap deletion: swap was not created by this installer"
  if [[ -e "${SWAP_FILE}" ]]; then
    swap_args=(remove --file "${SWAP_FILE}"); [[ "${YES}" == 1 ]] && swap_args+=(--yes)
    sudo "${INSTALL_ROOT}/scripts/manage-swap.sh" "${swap_args[@]}"
  fi
fi
if [[ "${PURGE_IMAGE}" == 1 ]]; then
  [[ "${IMAGE_OWNED}" == 1 ]] || die "refusing image deletion: image existed before this installation"
  if docker image inspect "${VLLM_IMAGE}" >/dev/null 2>&1; then
    docker image rm "${VLLM_IMAGE}" || die "image is still in use"
  fi
fi
if [[ "${PURGE_ALL}" == 1 ]]; then
  [[ "${DATA_HOME}" == "${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark" ]] || die "refusing unsafe release-data purge path: ${DATA_HOME}"
  if [[ "${CONFIG_OWNED}" == 1 && "${CONFIG_OVERRIDE:-}" == "${STATE_DIR}/config.vllm.json" ]]; then
    rm -f -- "${CONFIG_OVERRIDE}"
  fi
  rm -rf --one-file-system -- "${DATA_HOME}"
  rm -f -- "${STATE_DIR}/monitor.log" "${STATE_DIR}/monitor.pid" \
    "${STATE_DIR}/runtime-stop.env" "${STATE_DIR}/runtime-stop.env.tmp" \
    "${STATE_DIR}/runtime-commit.env" "${STATE_DIR}/runtime-commit.env.tmp" \
    "${STATE_DIR}/runtime-transition.env" "${STATE_DIR}/runtime-transition.env.tmp" \
    "${STATE_DIR}/update-transition.env" "${STATE_DIR}/update-transition.env.tmp" \
    "${STATE_DIR}/profile-switch-transition.env" "${STATE_DIR}/profile-switch-transition.env.tmp" \
    "${STATE_FILE}.profile-switch-backup" "${STATE_FILE}.profile-switch-candidate" "${STATE_FILE}.profile-switch-candidate.tmp"
  rm -f -- "${STATE_FILE}"
  rmdir --ignore-fail-on-non-empty "${STATE_DIR}" 2>/dev/null || true
  [[ "${UI_LANG}" == ko ]] && printf '전체 제거 완료; immutable release 데이터와 설치 manifest를 삭제했습니다.\n' || \
    printf 'Full uninstall completed; immutable release data and installation manifest removed.\n'
else
  mark_manifest_uninstalled
  if [[ "${UI_LANG}" == ko ]]; then
    printf '제거 완료. manifest를 uninstalled 상태로 보존했습니다. 다음 install.sh 실행에서 새 모델 프로필을 선택할 수 있습니다: %s\n' "${STATE_FILE}"
  else
    printf 'Uninstall completed. The manifest is retained in the uninstalled state; the next install.sh run may select a new model profile: %s\n' "${STATE_FILE}"
  fi
fi
\n'/, }"
  done < <(python3 "${ASSET_OWNERSHIP_TOOL}" plan-purge "${ASSET_OWNERSHIP_FILE}" --kind all)
}

asset_apply_full_purge() {
  [[ -f "${ASSET_OWNERSHIP_FILE}" && ! -L "${ASSET_OWNERSHIP_FILE}" ]] || return 0
  local kind locator
  while IFS=
mark_manifest_uninstalled() {
  python3 - "${STATE_FILE}" <<'PY'
import os
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()
matches = [i for i, line in enumerate(lines) if line.startswith("PHASE=")]
if len(matches) != 1:
    raise SystemExit("installation manifest must contain exactly one PHASE field")
lines[matches[0]] = "PHASE=uninstalled"
temporary = path.with_name(path.name + ".tmp")
temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
os.chmod(temporary, path.stat().st_mode & 0o777)
os.replace(temporary, path)
PY
}

parse_install_manifest() {
  local parsed key value
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" install-uninstall "${STATE_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    printf -v "${key}" '%s' "${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lang) [[ $# -ge 2 ]] || die "--lang requires en or ko"; CLI_LANG="$2"; shift ;;
    --purge-model) PURGE_MODEL=1; PURGE_SELECTED=1 ;; --purge-swap) PURGE_SWAP=1; PURGE_SELECTED=1 ;; --purge-image) PURGE_IMAGE=1; PURGE_SELECTED=1 ;;
    --purge-all) PURGE_MODEL=1; PURGE_SWAP=1; PURGE_IMAGE=1; PURGE_SELECTED=1; PURGE_ALL=1 ;; --yes) YES=1 ;; --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;; *) die "unknown argument: $1" ;;
  esac
  shift
done
[[ -r "${STATE_FILE}" ]] || die "installation manifest not found: ${STATE_FILE}"
[[ -r "${STATE_PARSER}" ]] || die "strict state parser is unavailable: ${STATE_PARSER}"
parse_install_manifest || die "installation manifest failed strict uninstall parsing: ${STATE_FILE}"
[[ -z "${CLI_LANG}" ]] || UI_LANG="${CLI_LANG}"
if [[ -z "${UI_LANG:-}" ]]; then
  if [[ "${YES}" == 0 && -t 0 ]]; then
    read -r -p 'Language / 언어 [1: English, 2: 한국어] (2): ' answer
    [[ "${answer}" == 1 || "${answer}" == en ]] && UI_LANG=en || UI_LANG=ko
  elif [[ "${LANG:-}" == ko_* ]]; then UI_LANG=ko; else UI_LANG=en; fi
fi
[[ "${UI_LANG}" == en || "${UI_LANG}" == ko ]] || die "--lang must be en or ko"
[[ -n "${INSTALL_ROOT:-}" && -d "${INSTALL_ROOT}" ]] || die "invalid INSTALL_ROOT in manifest"
[[ -n "${CONTAINER_NAME:-}" && "${CONTAINER_NAME}" != */* ]] || die "invalid container name"
MONITOR_PID_FILE="${STATE_DIR}/monitor.pid"

if [[ "${YES}" == 0 && "${PURGE_SELECTED}" == 0 ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    read -r -p '다운로드한 모델도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_MODEL=1
    read -r -p '전용 PLE swap도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_SWAP=1
    read -r -p 'vLLM Docker image도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_IMAGE=1
  else
    read -r -p 'Remove the downloaded model too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_MODEL=1
    read -r -p 'Remove the dedicated PLE swap too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_SWAP=1
    read -r -p 'Remove the vLLM Docker image too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_IMAGE=1
  fi
fi

if [[ "${UI_LANG}" == ko ]]; then
  printf 'Qwen3.8 Flash Next 제거 마법사\n\n  container: %s (제거)\n' "${CONTAINER_NAME}"
  printf '  model    : %s (%s)\n' "${MODEL_DIR}" "$([[ "${PURGE_MODEL}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  PLE swap : %s (%s)\n' "${SWAP_FILE}" "$([[ "${PURGE_SWAP}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  image    : %s (%s)\n' "${VLLM_IMAGE}" "$([[ "${PURGE_IMAGE}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  service  : %s\n' "$([[ "${SERVICE_OWNED}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  releases : %s\n' "$([[ "${PURGE_ALL}" == 1 ]] && printf '전체 제거' || printf '보존')"
else
  printf 'Qwen3.8 Flash Next uninstaller wizard\n\n  container: %s (remove)\n' "${CONTAINER_NAME}"
  printf '  model    : %s (%s)\n' "${MODEL_DIR}" "$([[ "${PURGE_MODEL}" == 1 ]] && printf remove || printf keep)"
  printf '  PLE swap : %s (%s)\n' "${SWAP_FILE}" "$([[ "${PURGE_SWAP}" == 1 ]] && printf remove || printf keep)"
  printf '  image    : %s (%s)\n' "${VLLM_IMAGE}" "$([[ "${PURGE_IMAGE}" == 1 ]] && printf remove || printf keep)"
  printf '  service  : %s\n' "$([[ "${SERVICE_OWNED}" == 1 ]] && printf remove || printf keep)"
  printf '  releases : %s\n' "$([[ "${PURGE_ALL}" == 1 ]] && printf purge || printf keep)"
fi
if [[ "${DRY_RUN}" == 1 ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    printf '\nDRY-RUN 완료: container, monitor, proxy, release, 모델, swap, image 및 manifest를 변경하지 않았습니다.\n'
  else
    printf '\nDRY-RUN complete: no container, monitor, proxy, release, model, swap, image, or manifest changes were made.\n'
  fi
  exit 0
fi

[[ -r "${OPERATION_LOCK_LIB}" ]] || die "operation lock helper is unavailable: ${OPERATION_LOCK_LIB}"
# shellcheck source=scripts/lib/operation-lock.sh
source "${OPERATION_LOCK_LIB}"
acquire_operation_lock "${STATE_DIR}" "uninstall" || exit $?

[[ ! -e "${UPDATE_TRANSITION_FILE}" && ! -L "${UPDATE_TRANSITION_FILE}" ]] || \
  die "an update transition is active; recover or roll it back before uninstalling"
[[ ! -e "${RUNTIME_TRANSITION_FILE}" && ! -L "${RUNTIME_TRANSITION_FILE}" ]] || \
  die "a runtime transition is active; recover or roll it back before uninstalling"
[[ ! -e "${PROFILE_SWITCH_TRANSITION_FILE}" && ! -L "${PROFILE_SWITCH_TRANSITION_FILE}" ]] || \
  die "a profile-switch transition is active; run scripts/profile-switch-transition.sh recover before uninstalling"
[[ ! -e "${PROFILE_SWITCH_BACKUP}" && ! -L "${PROFILE_SWITCH_BACKUP}" &&
   ! -e "${PROFILE_SWITCH_CANDIDATE}" && ! -L "${PROFILE_SWITCH_CANDIDATE}" ]] || \
  die "profile-switch artifacts exist without an active transaction; run doctor before uninstalling"

if [[ "${SERVICE_OWNED}" != 1 ]] && "${INSTALL_ROOT}/scripts/manage-service.sh" status >/dev/null 2>&1; then
  die "a managed runtime service exists but is not owned by this manifest; rerun install.sh to adopt it or remove it explicitly"
fi
if [[ "${YES}" != 1 ]]; then
  [[ "${UI_LANG}" == ko ]] && prompt='계속하려면 DELETE를 입력하십시오: ' || prompt='Type DELETE to continue: '
  read -r -p "${prompt}" answer
  [[ "${answer}" == DELETE ]] || die "$([[ "${UI_LANG}" == ko ]] && printf 취소됨 || printf cancelled)"
fi
if [[ -r "${MONITOR_PID_FILE}" ]]; then
  monitor_pid="$(<"${MONITOR_PID_FILE}")"
  if [[ "${monitor_pid}" =~ ^[0-9]+$ && -r "/proc/${monitor_pid}/cmdline" ]] && \
     tr '\0' ' ' < "/proc/${monitor_pid}/cmdline" | grep -Fq 'monitor-runtime.sh'; then
    kill "${monitor_pid}" 2>/dev/null || true
  fi
  rm -f -- "${MONITOR_PID_FILE}"
fi
if [[ "${SERVICE_OWNED}" == 1 ]]; then
  sudo_with_operation_lock "${INSTALL_ROOT}/scripts/manage-service.sh" remove --yes
fi
if [[ "${PROXY_OWNED}" == 1 ]]; then
  sudo "${INSTALL_ROOT}/scripts/manage-proxy.sh" remove --yes
fi
docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
rm -f -- "${STOP_REASON_FILE}" "${STOP_REASON_FILE}.tmp" "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"

if [[ "${PURGE_MODEL}" == 1 ]]; then
  [[ "${MODEL_OWNED}" == 1 ]] || die "refusing model deletion: directory was not created by this installer"
  if [[ -e "${MODEL_DIR}" ]]; then
    if [[ ! -f "${MODEL_DIR}/.qwen38-model-manifest.json" && ! -f "${MODEL_DIR}/.qwen38-hybrid-manifest.json" ]]; then
      die "refusing model deletion: managed model/hybrid manifest missing"
    fi
    if [[ "${MODEL_DIR}" != "${HOME}/models/"* && "${MODEL_DIR}" != "${INSTALL_ROOT}/model" ]]; then
      die "refusing model deletion outside ${HOME}/models or the install root's model directory"
    fi
    rm -rf --one-file-system -- "${MODEL_DIR}"
    printf 'Removed model directory: %s\n' "${MODEL_DIR}"
  fi
fi
if [[ "${PURGE_SWAP}" == 1 ]]; then
  [[ "${SWAP_OWNED}" == 1 ]] || die "refusing swap deletion: swap was not created by this installer"
  if [[ -e "${SWAP_FILE}" ]]; then
    swap_args=(remove --file "${SWAP_FILE}"); [[ "${YES}" == 1 ]] && swap_args+=(--yes)
    sudo "${INSTALL_ROOT}/scripts/manage-swap.sh" "${swap_args[@]}"
  fi
fi
if [[ "${PURGE_IMAGE}" == 1 ]]; then
  [[ "${IMAGE_OWNED}" == 1 ]] || die "refusing image deletion: image existed before this installation"
  if docker image inspect "${VLLM_IMAGE}" >/dev/null 2>&1; then
    docker image rm "${VLLM_IMAGE}" || die "image is still in use"
  fi
fi
if [[ "${PURGE_ALL}" == 1 ]]; then
  [[ "${DATA_HOME}" == "${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark" ]] || die "refusing unsafe release-data purge path: ${DATA_HOME}"
  if [[ "${CONFIG_OWNED}" == 1 && "${CONFIG_OVERRIDE:-}" == "${STATE_DIR}/config.vllm.json" ]]; then
    rm -f -- "${CONFIG_OVERRIDE}"
  fi
  rm -rf --one-file-system -- "${DATA_HOME}"
  rm -f -- "${STATE_DIR}/monitor.log" "${STATE_DIR}/monitor.pid" \
    "${STATE_DIR}/runtime-stop.env" "${STATE_DIR}/runtime-stop.env.tmp" \
    "${STATE_DIR}/runtime-commit.env" "${STATE_DIR}/runtime-commit.env.tmp" \
    "${STATE_DIR}/runtime-transition.env" "${STATE_DIR}/runtime-transition.env.tmp" \
    "${STATE_DIR}/update-transition.env" "${STATE_DIR}/update-transition.env.tmp" \
    "${STATE_DIR}/profile-switch-transition.env" "${STATE_DIR}/profile-switch-transition.env.tmp" \
    "${STATE_FILE}.profile-switch-backup" "${STATE_FILE}.profile-switch-candidate" "${STATE_FILE}.profile-switch-candidate.tmp"
  rm -f -- "${STATE_FILE}"
  rmdir --ignore-fail-on-non-empty "${STATE_DIR}" 2>/dev/null || true
  [[ "${UI_LANG}" == ko ]] && printf '전체 제거 완료; immutable release 데이터와 설치 manifest를 삭제했습니다.\n' || \
    printf 'Full uninstall completed; immutable release data and installation manifest removed.\n'
else
  mark_manifest_uninstalled
  if [[ "${UI_LANG}" == ko ]]; then
    printf '제거 완료. manifest를 uninstalled 상태로 보존했습니다. 다음 install.sh 실행에서 새 모델 프로필을 선택할 수 있습니다: %s\n' "${STATE_FILE}"
  else
    printf 'Uninstall completed. The manifest is retained in the uninstalled state; the next install.sh run may select a new model profile: %s\n' "${STATE_FILE}"
  fi
fi
\t' read -r kind locator; do
    case "${kind}" in
      model)
        if [[ -e "${locator}" || -L "${locator}" ]]; then
          rm -rf --one-file-system -- "${locator}"
          printf 'Removed owned model asset: %s\n' "${locator}"
        fi
        asset_forget model "${locator}"
        ;;
      image)
        if docker image inspect "${locator}" >/dev/null 2>&1; then
          docker image rm "${locator}" || die "owned image is still in use: ${locator}"
          printf 'Removed owned image asset: %s\n' "${locator}"
        fi
        asset_forget image "${locator}"
        ;;
      *) die "invalid asset purge plan kind: ${kind}" ;;
    esac
  done < <(python3 "${ASSET_OWNERSHIP_TOOL}" plan-purge "${ASSET_OWNERSHIP_FILE}" --kind all)
}

mark_manifest_uninstalled() {
  python3 - "${STATE_FILE}" <<'PY'
import os
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()
matches = [i for i, line in enumerate(lines) if line.startswith("PHASE=")]
if len(matches) != 1:
    raise SystemExit("installation manifest must contain exactly one PHASE field")
lines[matches[0]] = "PHASE=uninstalled"
temporary = path.with_name(path.name + ".tmp")
temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
os.chmod(temporary, path.stat().st_mode & 0o777)
os.replace(temporary, path)
PY
}

parse_install_manifest() {
  local parsed key value
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" install-uninstall "${STATE_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    printf -v "${key}" '%s' "${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lang) [[ $# -ge 2 ]] || die "--lang requires en or ko"; CLI_LANG="$2"; shift ;;
    --purge-model) PURGE_MODEL=1; PURGE_SELECTED=1 ;; --purge-swap) PURGE_SWAP=1; PURGE_SELECTED=1 ;; --purge-image) PURGE_IMAGE=1; PURGE_SELECTED=1 ;;
    --purge-all) PURGE_MODEL=1; PURGE_SWAP=1; PURGE_IMAGE=1; PURGE_SELECTED=1; PURGE_ALL=1 ;; --yes) YES=1 ;; --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;; *) die "unknown argument: $1" ;;
  esac
  shift
done
[[ -r "${STATE_FILE}" ]] || die "installation manifest not found: ${STATE_FILE}"
[[ -r "${STATE_PARSER}" ]] || die "strict state parser is unavailable: ${STATE_PARSER}"
parse_install_manifest || die "installation manifest failed strict uninstall parsing: ${STATE_FILE}"
[[ -z "${CLI_LANG}" ]] || UI_LANG="${CLI_LANG}"
if [[ -z "${UI_LANG:-}" ]]; then
  if [[ "${YES}" == 0 && -t 0 ]]; then
    read -r -p 'Language / 언어 [1: English, 2: 한국어] (2): ' answer
    [[ "${answer}" == 1 || "${answer}" == en ]] && UI_LANG=en || UI_LANG=ko
  elif [[ "${LANG:-}" == ko_* ]]; then UI_LANG=ko; else UI_LANG=en; fi
fi
[[ "${UI_LANG}" == en || "${UI_LANG}" == ko ]] || die "--lang must be en or ko"
[[ -n "${INSTALL_ROOT:-}" && -d "${INSTALL_ROOT}" ]] || die "invalid INSTALL_ROOT in manifest"
[[ -n "${CONTAINER_NAME:-}" && "${CONTAINER_NAME}" != */* ]] || die "invalid container name"
MONITOR_PID_FILE="${STATE_DIR}/monitor.pid"

if [[ "${YES}" == 0 && "${PURGE_SELECTED}" == 0 ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    read -r -p '다운로드한 모델도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_MODEL=1
    read -r -p '전용 PLE swap도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_SWAP=1
    read -r -p 'vLLM Docker image도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_IMAGE=1
  else
    read -r -p 'Remove the downloaded model too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_MODEL=1
    read -r -p 'Remove the dedicated PLE swap too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_SWAP=1
    read -r -p 'Remove the vLLM Docker image too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_IMAGE=1
  fi
fi

if [[ "${UI_LANG}" == ko ]]; then
  printf 'Qwen3.8 Flash Next 제거 마법사\n\n  container: %s (제거)\n' "${CONTAINER_NAME}"
  printf '  model    : %s (%s)\n' "${MODEL_DIR}" "$([[ "${PURGE_MODEL}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  PLE swap : %s (%s)\n' "${SWAP_FILE}" "$([[ "${PURGE_SWAP}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  image    : %s (%s)\n' "${VLLM_IMAGE}" "$([[ "${PURGE_IMAGE}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  service  : %s\n' "$([[ "${SERVICE_OWNED}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  releases : %s\n' "$([[ "${PURGE_ALL}" == 1 ]] && printf '전체 제거' || printf '보존')"
else
  printf 'Qwen3.8 Flash Next uninstaller wizard\n\n  container: %s (remove)\n' "${CONTAINER_NAME}"
  printf '  model    : %s (%s)\n' "${MODEL_DIR}" "$([[ "${PURGE_MODEL}" == 1 ]] && printf remove || printf keep)"
  printf '  PLE swap : %s (%s)\n' "${SWAP_FILE}" "$([[ "${PURGE_SWAP}" == 1 ]] && printf remove || printf keep)"
  printf '  image    : %s (%s)\n' "${VLLM_IMAGE}" "$([[ "${PURGE_IMAGE}" == 1 ]] && printf remove || printf keep)"
  printf '  service  : %s\n' "$([[ "${SERVICE_OWNED}" == 1 ]] && printf remove || printf keep)"
  printf '  releases : %s\n' "$([[ "${PURGE_ALL}" == 1 ]] && printf purge || printf keep)"
fi
if [[ "${DRY_RUN}" == 1 ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    printf '\nDRY-RUN 완료: container, monitor, proxy, release, 모델, swap, image 및 manifest를 변경하지 않았습니다.\n'
  else
    printf '\nDRY-RUN complete: no container, monitor, proxy, release, model, swap, image, or manifest changes were made.\n'
  fi
  exit 0
fi

[[ -r "${OPERATION_LOCK_LIB}" ]] || die "operation lock helper is unavailable: ${OPERATION_LOCK_LIB}"
# shellcheck source=scripts/lib/operation-lock.sh
source "${OPERATION_LOCK_LIB}"
acquire_operation_lock "${STATE_DIR}" "uninstall" || exit $?

[[ ! -e "${UPDATE_TRANSITION_FILE}" && ! -L "${UPDATE_TRANSITION_FILE}" ]] || \
  die "an update transition is active; recover or roll it back before uninstalling"
[[ ! -e "${RUNTIME_TRANSITION_FILE}" && ! -L "${RUNTIME_TRANSITION_FILE}" ]] || \
  die "a runtime transition is active; recover or roll it back before uninstalling"
[[ ! -e "${PROFILE_SWITCH_TRANSITION_FILE}" && ! -L "${PROFILE_SWITCH_TRANSITION_FILE}" ]] || \
  die "a profile-switch transition is active; run scripts/profile-switch-transition.sh recover before uninstalling"
[[ ! -e "${PROFILE_SWITCH_BACKUP}" && ! -L "${PROFILE_SWITCH_BACKUP}" &&
   ! -e "${PROFILE_SWITCH_CANDIDATE}" && ! -L "${PROFILE_SWITCH_CANDIDATE}" ]] || \
  die "profile-switch artifacts exist without an active transaction; run doctor before uninstalling"

if [[ "${SERVICE_OWNED}" != 1 ]] && "${INSTALL_ROOT}/scripts/manage-service.sh" status >/dev/null 2>&1; then
  die "a managed runtime service exists but is not owned by this manifest; rerun install.sh to adopt it or remove it explicitly"
fi
if [[ "${YES}" != 1 ]]; then
  [[ "${UI_LANG}" == ko ]] && prompt='계속하려면 DELETE를 입력하십시오: ' || prompt='Type DELETE to continue: '
  read -r -p "${prompt}" answer
  [[ "${answer}" == DELETE ]] || die "$([[ "${UI_LANG}" == ko ]] && printf 취소됨 || printf cancelled)"
fi
if [[ -r "${MONITOR_PID_FILE}" ]]; then
  monitor_pid="$(<"${MONITOR_PID_FILE}")"
  if [[ "${monitor_pid}" =~ ^[0-9]+$ && -r "/proc/${monitor_pid}/cmdline" ]] && \
     tr '\0' ' ' < "/proc/${monitor_pid}/cmdline" | grep -Fq 'monitor-runtime.sh'; then
    kill "${monitor_pid}" 2>/dev/null || true
  fi
  rm -f -- "${MONITOR_PID_FILE}"
fi
if [[ "${SERVICE_OWNED}" == 1 ]]; then
  sudo_with_operation_lock "${INSTALL_ROOT}/scripts/manage-service.sh" remove --yes
fi
if [[ "${PROXY_OWNED}" == 1 ]]; then
  sudo "${INSTALL_ROOT}/scripts/manage-proxy.sh" remove --yes
fi
docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
rm -f -- "${STOP_REASON_FILE}" "${STOP_REASON_FILE}.tmp" "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"

if [[ "${PURGE_MODEL}" == 1 ]]; then
  [[ "${MODEL_OWNED}" == 1 ]] || die "refusing model deletion: directory was not created by this installer"
  if [[ -e "${MODEL_DIR}" ]]; then
    if [[ ! -f "${MODEL_DIR}/.qwen38-model-manifest.json" && ! -f "${MODEL_DIR}/.qwen38-hybrid-manifest.json" ]]; then
      die "refusing model deletion: managed model/hybrid manifest missing"
    fi
    if [[ "${MODEL_DIR}" != "${HOME}/models/"* && "${MODEL_DIR}" != "${INSTALL_ROOT}/model" ]]; then
      die "refusing model deletion outside ${HOME}/models or the install root's model directory"
    fi
    rm -rf --one-file-system -- "${MODEL_DIR}"
    printf 'Removed model directory: %s\n' "${MODEL_DIR}"
  fi
fi
if [[ "${PURGE_SWAP}" == 1 ]]; then
  [[ "${SWAP_OWNED}" == 1 ]] || die "refusing swap deletion: swap was not created by this installer"
  if [[ -e "${SWAP_FILE}" ]]; then
    swap_args=(remove --file "${SWAP_FILE}"); [[ "${YES}" == 1 ]] && swap_args+=(--yes)
    sudo "${INSTALL_ROOT}/scripts/manage-swap.sh" "${swap_args[@]}"
  fi
fi
if [[ "${PURGE_IMAGE}" == 1 ]]; then
  [[ "${IMAGE_OWNED}" == 1 ]] || die "refusing image deletion: image existed before this installation"
  if docker image inspect "${VLLM_IMAGE}" >/dev/null 2>&1; then
    docker image rm "${VLLM_IMAGE}" || die "image is still in use"
  fi
fi
if [[ "${PURGE_ALL}" == 1 ]]; then
  [[ "${DATA_HOME}" == "${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark" ]] || die "refusing unsafe release-data purge path: ${DATA_HOME}"
  if [[ "${CONFIG_OWNED}" == 1 && "${CONFIG_OVERRIDE:-}" == "${STATE_DIR}/config.vllm.json" ]]; then
    rm -f -- "${CONFIG_OVERRIDE}"
  fi
  rm -rf --one-file-system -- "${DATA_HOME}"
  rm -f -- "${STATE_DIR}/monitor.log" "${STATE_DIR}/monitor.pid" \
    "${STATE_DIR}/runtime-stop.env" "${STATE_DIR}/runtime-stop.env.tmp" \
    "${STATE_DIR}/runtime-commit.env" "${STATE_DIR}/runtime-commit.env.tmp" \
    "${STATE_DIR}/runtime-transition.env" "${STATE_DIR}/runtime-transition.env.tmp" \
    "${STATE_DIR}/update-transition.env" "${STATE_DIR}/update-transition.env.tmp" \
    "${STATE_DIR}/profile-switch-transition.env" "${STATE_DIR}/profile-switch-transition.env.tmp" \
    "${STATE_FILE}.profile-switch-backup" "${STATE_FILE}.profile-switch-candidate" "${STATE_FILE}.profile-switch-candidate.tmp"
  rm -f -- "${STATE_FILE}"
  rmdir --ignore-fail-on-non-empty "${STATE_DIR}" 2>/dev/null || true
  [[ "${UI_LANG}" == ko ]] && printf '전체 제거 완료; immutable release 데이터와 설치 manifest를 삭제했습니다.\n' || \
    printf 'Full uninstall completed; immutable release data and installation manifest removed.\n'
else
  mark_manifest_uninstalled
  if [[ "${UI_LANG}" == ko ]]; then
    printf '제거 완료. manifest를 uninstalled 상태로 보존했습니다. 다음 install.sh 실행에서 새 모델 프로필을 선택할 수 있습니다: %s\n' "${STATE_FILE}"
  else
    printf 'Uninstall completed. The manifest is retained in the uninstalled state; the next install.sh run may select a new model profile: %s\n' "${STATE_FILE}"
  fi
fi
\n'/, }"
  fi
fi

if [[ "${SERVICE_OWNED}" != 1 ]] && "${INSTALL_ROOT}/scripts/manage-service.sh" status >/dev/null 2>&1; then
  die "a managed runtime service exists but is not owned by this manifest; rerun install.sh to adopt it or remove it explicitly"
fi
if [[ "${YES}" != 1 ]]; then
  [[ "${UI_LANG}" == ko ]] && prompt='계속하려면 DELETE를 입력하십시오: ' || prompt='Type DELETE to continue: '
  read -r -p "${prompt}" answer
  [[ "${answer}" == DELETE ]] || die "$([[ "${UI_LANG}" == ko ]] && printf 취소됨 || printf cancelled)"
fi
if [[ -r "${MONITOR_PID_FILE}" ]]; then
  monitor_pid="$(<"${MONITOR_PID_FILE}")"
  if [[ "${monitor_pid}" =~ ^[0-9]+$ && -r "/proc/${monitor_pid}/cmdline" ]] && \
     tr '\0' ' ' < "/proc/${monitor_pid}/cmdline" | grep -Fq 'monitor-runtime.sh'; then
    kill "${monitor_pid}" 2>/dev/null || true
  fi
  rm -f -- "${MONITOR_PID_FILE}"
fi
if [[ "${SERVICE_OWNED}" == 1 ]]; then
  sudo_with_operation_lock "${INSTALL_ROOT}/scripts/manage-service.sh" remove --yes
fi
if [[ "${PROXY_OWNED}" == 1 ]]; then
  sudo "${INSTALL_ROOT}/scripts/manage-proxy.sh" remove --yes
fi
docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
rm -f -- "${STOP_REASON_FILE}" "${STOP_REASON_FILE}.tmp" "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"

if [[ "${PURGE_MODEL}" == 1 ]]; then
  [[ "${MODEL_OWNED}" == 1 ]] || die "refusing model deletion: directory was not created by this installer"
  if [[ -e "${MODEL_DIR}" ]]; then
    if [[ ! -f "${MODEL_DIR}/.qwen38-model-manifest.json" && ! -f "${MODEL_DIR}/.qwen38-hybrid-manifest.json" ]]; then
      die "refusing model deletion: managed model/hybrid manifest missing"
    fi
    if [[ "${MODEL_DIR}" != "${HOME}/models/"* && "${MODEL_DIR}" != "${INSTALL_ROOT}/model" ]]; then
      die "refusing model deletion outside ${HOME}/models or the install root's model directory"
    fi
    rm -rf --one-file-system -- "${MODEL_DIR}"
    printf 'Removed model directory: %s\n' "${MODEL_DIR}"
  fi
fi
if [[ "${PURGE_SWAP}" == 1 ]]; then
  [[ "${SWAP_OWNED}" == 1 ]] || die "refusing swap deletion: swap was not created by this installer"
  if [[ -e "${SWAP_FILE}" ]]; then
    swap_args=(remove --file "${SWAP_FILE}"); [[ "${YES}" == 1 ]] && swap_args+=(--yes)
    sudo "${INSTALL_ROOT}/scripts/manage-swap.sh" "${swap_args[@]}"
  fi
fi
if [[ "${PURGE_IMAGE}" == 1 ]]; then
  [[ "${IMAGE_OWNED}" == 1 ]] || die "refusing image deletion: image existed before this installation"
  if docker image inspect "${VLLM_IMAGE}" >/dev/null 2>&1; then
    docker image rm "${VLLM_IMAGE}" || die "image is still in use"
  fi
fi
if [[ "${PURGE_ALL}" == 1 ]]; then
  [[ "${DATA_HOME}" == "${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark" ]] || die "refusing unsafe release-data purge path: ${DATA_HOME}"
  if [[ "${CONFIG_OWNED}" == 1 && "${CONFIG_OVERRIDE:-}" == "${STATE_DIR}/config.vllm.json" ]]; then
    rm -f -- "${CONFIG_OVERRIDE}"
  fi
  rm -rf --one-file-system -- "${DATA_HOME}"
  rm -f -- "${STATE_DIR}/monitor.log" "${STATE_DIR}/monitor.pid" \
    "${STATE_DIR}/runtime-stop.env" "${STATE_DIR}/runtime-stop.env.tmp" \
    "${STATE_DIR}/runtime-commit.env" "${STATE_DIR}/runtime-commit.env.tmp" \
    "${STATE_DIR}/runtime-transition.env" "${STATE_DIR}/runtime-transition.env.tmp" \
    "${STATE_DIR}/update-transition.env" "${STATE_DIR}/update-transition.env.tmp" \
    "${STATE_DIR}/profile-switch-transition.env" "${STATE_DIR}/profile-switch-transition.env.tmp" \
    "${STATE_FILE}.profile-switch-backup" "${STATE_FILE}.profile-switch-candidate" "${STATE_FILE}.profile-switch-candidate.tmp"
  rm -f -- "${STATE_FILE}"
  rmdir --ignore-fail-on-non-empty "${STATE_DIR}" 2>/dev/null || true
  [[ "${UI_LANG}" == ko ]] && printf '전체 제거 완료; immutable release 데이터와 설치 manifest를 삭제했습니다.\n' || \
    printf 'Full uninstall completed; immutable release data and installation manifest removed.\n'
else
  mark_manifest_uninstalled
  if [[ "${UI_LANG}" == ko ]]; then
    printf '제거 완료. manifest를 uninstalled 상태로 보존했습니다. 다음 install.sh 실행에서 새 모델 프로필을 선택할 수 있습니다: %s\n' "${STATE_FILE}"
  else
    printf 'Uninstall completed. The manifest is retained in the uninstalled state; the next install.sh run may select a new model profile: %s\n' "${STATE_FILE}"
  fi
fi
\t' read -r kind locator; do
    [[ "${kind}" == image ]] || continue
    refs="$(image_referenced_by_external_container "${locator}")"
    [[ -z "${refs}" ]] || die "refusing image purge; ${locator} is referenced by other containers: ${refs//
mark_manifest_uninstalled() {
  python3 - "${STATE_FILE}" <<'PY'
import os
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()
matches = [i for i, line in enumerate(lines) if line.startswith("PHASE=")]
if len(matches) != 1:
    raise SystemExit("installation manifest must contain exactly one PHASE field")
lines[matches[0]] = "PHASE=uninstalled"
temporary = path.with_name(path.name + ".tmp")
temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
os.chmod(temporary, path.stat().st_mode & 0o777)
os.replace(temporary, path)
PY
}

parse_install_manifest() {
  local parsed key value
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" install-uninstall "${STATE_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    printf -v "${key}" '%s' "${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lang) [[ $# -ge 2 ]] || die "--lang requires en or ko"; CLI_LANG="$2"; shift ;;
    --purge-model) PURGE_MODEL=1; PURGE_SELECTED=1 ;; --purge-swap) PURGE_SWAP=1; PURGE_SELECTED=1 ;; --purge-image) PURGE_IMAGE=1; PURGE_SELECTED=1 ;;
    --purge-all) PURGE_MODEL=1; PURGE_SWAP=1; PURGE_IMAGE=1; PURGE_SELECTED=1; PURGE_ALL=1 ;; --yes) YES=1 ;; --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;; *) die "unknown argument: $1" ;;
  esac
  shift
done
[[ -r "${STATE_FILE}" ]] || die "installation manifest not found: ${STATE_FILE}"
[[ -r "${STATE_PARSER}" ]] || die "strict state parser is unavailable: ${STATE_PARSER}"
parse_install_manifest || die "installation manifest failed strict uninstall parsing: ${STATE_FILE}"
[[ -z "${CLI_LANG}" ]] || UI_LANG="${CLI_LANG}"
if [[ -z "${UI_LANG:-}" ]]; then
  if [[ "${YES}" == 0 && -t 0 ]]; then
    read -r -p 'Language / 언어 [1: English, 2: 한국어] (2): ' answer
    [[ "${answer}" == 1 || "${answer}" == en ]] && UI_LANG=en || UI_LANG=ko
  elif [[ "${LANG:-}" == ko_* ]]; then UI_LANG=ko; else UI_LANG=en; fi
fi
[[ "${UI_LANG}" == en || "${UI_LANG}" == ko ]] || die "--lang must be en or ko"
[[ -n "${INSTALL_ROOT:-}" && -d "${INSTALL_ROOT}" ]] || die "invalid INSTALL_ROOT in manifest"
[[ -n "${CONTAINER_NAME:-}" && "${CONTAINER_NAME}" != */* ]] || die "invalid container name"
MONITOR_PID_FILE="${STATE_DIR}/monitor.pid"

if [[ "${YES}" == 0 && "${PURGE_SELECTED}" == 0 ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    read -r -p '다운로드한 모델도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_MODEL=1
    read -r -p '전용 PLE swap도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_SWAP=1
    read -r -p 'vLLM Docker image도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_IMAGE=1
  else
    read -r -p 'Remove the downloaded model too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_MODEL=1
    read -r -p 'Remove the dedicated PLE swap too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_SWAP=1
    read -r -p 'Remove the vLLM Docker image too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_IMAGE=1
  fi
fi

if [[ "${UI_LANG}" == ko ]]; then
  printf 'Qwen3.8 Flash Next 제거 마법사\n\n  container: %s (제거)\n' "${CONTAINER_NAME}"
  printf '  model    : %s (%s)\n' "${MODEL_DIR}" "$([[ "${PURGE_MODEL}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  PLE swap : %s (%s)\n' "${SWAP_FILE}" "$([[ "${PURGE_SWAP}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  image    : %s (%s)\n' "${VLLM_IMAGE}" "$([[ "${PURGE_IMAGE}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  service  : %s\n' "$([[ "${SERVICE_OWNED}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  releases : %s\n' "$([[ "${PURGE_ALL}" == 1 ]] && printf '전체 제거' || printf '보존')"
else
  printf 'Qwen3.8 Flash Next uninstaller wizard\n\n  container: %s (remove)\n' "${CONTAINER_NAME}"
  printf '  model    : %s (%s)\n' "${MODEL_DIR}" "$([[ "${PURGE_MODEL}" == 1 ]] && printf remove || printf keep)"
  printf '  PLE swap : %s (%s)\n' "${SWAP_FILE}" "$([[ "${PURGE_SWAP}" == 1 ]] && printf remove || printf keep)"
  printf '  image    : %s (%s)\n' "${VLLM_IMAGE}" "$([[ "${PURGE_IMAGE}" == 1 ]] && printf remove || printf keep)"
  printf '  service  : %s\n' "$([[ "${SERVICE_OWNED}" == 1 ]] && printf remove || printf keep)"
  printf '  releases : %s\n' "$([[ "${PURGE_ALL}" == 1 ]] && printf purge || printf keep)"
fi
if [[ "${DRY_RUN}" == 1 ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    printf '\nDRY-RUN 완료: container, monitor, proxy, release, 모델, swap, image 및 manifest를 변경하지 않았습니다.\n'
  else
    printf '\nDRY-RUN complete: no container, monitor, proxy, release, model, swap, image, or manifest changes were made.\n'
  fi
  exit 0
fi

[[ -r "${OPERATION_LOCK_LIB}" ]] || die "operation lock helper is unavailable: ${OPERATION_LOCK_LIB}"
# shellcheck source=scripts/lib/operation-lock.sh
source "${OPERATION_LOCK_LIB}"
acquire_operation_lock "${STATE_DIR}" "uninstall" || exit $?

[[ ! -e "${UPDATE_TRANSITION_FILE}" && ! -L "${UPDATE_TRANSITION_FILE}" ]] || \
  die "an update transition is active; recover or roll it back before uninstalling"
[[ ! -e "${RUNTIME_TRANSITION_FILE}" && ! -L "${RUNTIME_TRANSITION_FILE}" ]] || \
  die "a runtime transition is active; recover or roll it back before uninstalling"
[[ ! -e "${PROFILE_SWITCH_TRANSITION_FILE}" && ! -L "${PROFILE_SWITCH_TRANSITION_FILE}" ]] || \
  die "a profile-switch transition is active; run scripts/profile-switch-transition.sh recover before uninstalling"
[[ ! -e "${PROFILE_SWITCH_BACKUP}" && ! -L "${PROFILE_SWITCH_BACKUP}" &&
   ! -e "${PROFILE_SWITCH_CANDIDATE}" && ! -L "${PROFILE_SWITCH_CANDIDATE}" ]] || \
  die "profile-switch artifacts exist without an active transaction; run doctor before uninstalling"

if [[ "${SERVICE_OWNED}" != 1 ]] && "${INSTALL_ROOT}/scripts/manage-service.sh" status >/dev/null 2>&1; then
  die "a managed runtime service exists but is not owned by this manifest; rerun install.sh to adopt it or remove it explicitly"
fi
if [[ "${YES}" != 1 ]]; then
  [[ "${UI_LANG}" == ko ]] && prompt='계속하려면 DELETE를 입력하십시오: ' || prompt='Type DELETE to continue: '
  read -r -p "${prompt}" answer
  [[ "${answer}" == DELETE ]] || die "$([[ "${UI_LANG}" == ko ]] && printf 취소됨 || printf cancelled)"
fi
if [[ -r "${MONITOR_PID_FILE}" ]]; then
  monitor_pid="$(<"${MONITOR_PID_FILE}")"
  if [[ "${monitor_pid}" =~ ^[0-9]+$ && -r "/proc/${monitor_pid}/cmdline" ]] && \
     tr '\0' ' ' < "/proc/${monitor_pid}/cmdline" | grep -Fq 'monitor-runtime.sh'; then
    kill "${monitor_pid}" 2>/dev/null || true
  fi
  rm -f -- "${MONITOR_PID_FILE}"
fi
if [[ "${SERVICE_OWNED}" == 1 ]]; then
  sudo_with_operation_lock "${INSTALL_ROOT}/scripts/manage-service.sh" remove --yes
fi
if [[ "${PROXY_OWNED}" == 1 ]]; then
  sudo "${INSTALL_ROOT}/scripts/manage-proxy.sh" remove --yes
fi
docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
rm -f -- "${STOP_REASON_FILE}" "${STOP_REASON_FILE}.tmp" "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"

if [[ "${PURGE_MODEL}" == 1 ]]; then
  [[ "${MODEL_OWNED}" == 1 ]] || die "refusing model deletion: directory was not created by this installer"
  if [[ -e "${MODEL_DIR}" ]]; then
    if [[ ! -f "${MODEL_DIR}/.qwen38-model-manifest.json" && ! -f "${MODEL_DIR}/.qwen38-hybrid-manifest.json" ]]; then
      die "refusing model deletion: managed model/hybrid manifest missing"
    fi
    if [[ "${MODEL_DIR}" != "${HOME}/models/"* && "${MODEL_DIR}" != "${INSTALL_ROOT}/model" ]]; then
      die "refusing model deletion outside ${HOME}/models or the install root's model directory"
    fi
    rm -rf --one-file-system -- "${MODEL_DIR}"
    printf 'Removed model directory: %s\n' "${MODEL_DIR}"
  fi
fi
if [[ "${PURGE_SWAP}" == 1 ]]; then
  [[ "${SWAP_OWNED}" == 1 ]] || die "refusing swap deletion: swap was not created by this installer"
  if [[ -e "${SWAP_FILE}" ]]; then
    swap_args=(remove --file "${SWAP_FILE}"); [[ "${YES}" == 1 ]] && swap_args+=(--yes)
    sudo "${INSTALL_ROOT}/scripts/manage-swap.sh" "${swap_args[@]}"
  fi
fi
if [[ "${PURGE_IMAGE}" == 1 ]]; then
  [[ "${IMAGE_OWNED}" == 1 ]] || die "refusing image deletion: image existed before this installation"
  if docker image inspect "${VLLM_IMAGE}" >/dev/null 2>&1; then
    docker image rm "${VLLM_IMAGE}" || die "image is still in use"
  fi
fi
if [[ "${PURGE_ALL}" == 1 ]]; then
  [[ "${DATA_HOME}" == "${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark" ]] || die "refusing unsafe release-data purge path: ${DATA_HOME}"
  if [[ "${CONFIG_OWNED}" == 1 && "${CONFIG_OVERRIDE:-}" == "${STATE_DIR}/config.vllm.json" ]]; then
    rm -f -- "${CONFIG_OVERRIDE}"
  fi
  rm -rf --one-file-system -- "${DATA_HOME}"
  rm -f -- "${STATE_DIR}/monitor.log" "${STATE_DIR}/monitor.pid" \
    "${STATE_DIR}/runtime-stop.env" "${STATE_DIR}/runtime-stop.env.tmp" \
    "${STATE_DIR}/runtime-commit.env" "${STATE_DIR}/runtime-commit.env.tmp" \
    "${STATE_DIR}/runtime-transition.env" "${STATE_DIR}/runtime-transition.env.tmp" \
    "${STATE_DIR}/update-transition.env" "${STATE_DIR}/update-transition.env.tmp" \
    "${STATE_DIR}/profile-switch-transition.env" "${STATE_DIR}/profile-switch-transition.env.tmp" \
    "${STATE_FILE}.profile-switch-backup" "${STATE_FILE}.profile-switch-candidate" "${STATE_FILE}.profile-switch-candidate.tmp"
  rm -f -- "${STATE_FILE}"
  rmdir --ignore-fail-on-non-empty "${STATE_DIR}" 2>/dev/null || true
  [[ "${UI_LANG}" == ko ]] && printf '전체 제거 완료; immutable release 데이터와 설치 manifest를 삭제했습니다.\n' || \
    printf 'Full uninstall completed; immutable release data and installation manifest removed.\n'
else
  mark_manifest_uninstalled
  if [[ "${UI_LANG}" == ko ]]; then
    printf '제거 완료. manifest를 uninstalled 상태로 보존했습니다. 다음 install.sh 실행에서 새 모델 프로필을 선택할 수 있습니다: %s\n' "${STATE_FILE}"
  else
    printf 'Uninstall completed. The manifest is retained in the uninstalled state; the next install.sh run may select a new model profile: %s\n' "${STATE_FILE}"
  fi
fi
\n'/, }"
  done < <(python3 "${ASSET_OWNERSHIP_TOOL}" plan-purge "${ASSET_OWNERSHIP_FILE}" --kind all)
}

asset_apply_full_purge() {
  [[ -f "${ASSET_OWNERSHIP_FILE}" && ! -L "${ASSET_OWNERSHIP_FILE}" ]] || return 0
  local kind locator
  while IFS=
mark_manifest_uninstalled() {
  python3 - "${STATE_FILE}" <<'PY'
import os
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()
matches = [i for i, line in enumerate(lines) if line.startswith("PHASE=")]
if len(matches) != 1:
    raise SystemExit("installation manifest must contain exactly one PHASE field")
lines[matches[0]] = "PHASE=uninstalled"
temporary = path.with_name(path.name + ".tmp")
temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
os.chmod(temporary, path.stat().st_mode & 0o777)
os.replace(temporary, path)
PY
}

parse_install_manifest() {
  local parsed key value
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" install-uninstall "${STATE_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    printf -v "${key}" '%s' "${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lang) [[ $# -ge 2 ]] || die "--lang requires en or ko"; CLI_LANG="$2"; shift ;;
    --purge-model) PURGE_MODEL=1; PURGE_SELECTED=1 ;; --purge-swap) PURGE_SWAP=1; PURGE_SELECTED=1 ;; --purge-image) PURGE_IMAGE=1; PURGE_SELECTED=1 ;;
    --purge-all) PURGE_MODEL=1; PURGE_SWAP=1; PURGE_IMAGE=1; PURGE_SELECTED=1; PURGE_ALL=1 ;; --yes) YES=1 ;; --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;; *) die "unknown argument: $1" ;;
  esac
  shift
done
[[ -r "${STATE_FILE}" ]] || die "installation manifest not found: ${STATE_FILE}"
[[ -r "${STATE_PARSER}" ]] || die "strict state parser is unavailable: ${STATE_PARSER}"
parse_install_manifest || die "installation manifest failed strict uninstall parsing: ${STATE_FILE}"
[[ -z "${CLI_LANG}" ]] || UI_LANG="${CLI_LANG}"
if [[ -z "${UI_LANG:-}" ]]; then
  if [[ "${YES}" == 0 && -t 0 ]]; then
    read -r -p 'Language / 언어 [1: English, 2: 한국어] (2): ' answer
    [[ "${answer}" == 1 || "${answer}" == en ]] && UI_LANG=en || UI_LANG=ko
  elif [[ "${LANG:-}" == ko_* ]]; then UI_LANG=ko; else UI_LANG=en; fi
fi
[[ "${UI_LANG}" == en || "${UI_LANG}" == ko ]] || die "--lang must be en or ko"
[[ -n "${INSTALL_ROOT:-}" && -d "${INSTALL_ROOT}" ]] || die "invalid INSTALL_ROOT in manifest"
[[ -n "${CONTAINER_NAME:-}" && "${CONTAINER_NAME}" != */* ]] || die "invalid container name"
MONITOR_PID_FILE="${STATE_DIR}/monitor.pid"

if [[ "${YES}" == 0 && "${PURGE_SELECTED}" == 0 ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    read -r -p '다운로드한 모델도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_MODEL=1
    read -r -p '전용 PLE swap도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_SWAP=1
    read -r -p 'vLLM Docker image도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_IMAGE=1
  else
    read -r -p 'Remove the downloaded model too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_MODEL=1
    read -r -p 'Remove the dedicated PLE swap too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_SWAP=1
    read -r -p 'Remove the vLLM Docker image too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_IMAGE=1
  fi
fi

if [[ "${UI_LANG}" == ko ]]; then
  printf 'Qwen3.8 Flash Next 제거 마법사\n\n  container: %s (제거)\n' "${CONTAINER_NAME}"
  printf '  model    : %s (%s)\n' "${MODEL_DIR}" "$([[ "${PURGE_MODEL}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  PLE swap : %s (%s)\n' "${SWAP_FILE}" "$([[ "${PURGE_SWAP}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  image    : %s (%s)\n' "${VLLM_IMAGE}" "$([[ "${PURGE_IMAGE}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  service  : %s\n' "$([[ "${SERVICE_OWNED}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  releases : %s\n' "$([[ "${PURGE_ALL}" == 1 ]] && printf '전체 제거' || printf '보존')"
else
  printf 'Qwen3.8 Flash Next uninstaller wizard\n\n  container: %s (remove)\n' "${CONTAINER_NAME}"
  printf '  model    : %s (%s)\n' "${MODEL_DIR}" "$([[ "${PURGE_MODEL}" == 1 ]] && printf remove || printf keep)"
  printf '  PLE swap : %s (%s)\n' "${SWAP_FILE}" "$([[ "${PURGE_SWAP}" == 1 ]] && printf remove || printf keep)"
  printf '  image    : %s (%s)\n' "${VLLM_IMAGE}" "$([[ "${PURGE_IMAGE}" == 1 ]] && printf remove || printf keep)"
  printf '  service  : %s\n' "$([[ "${SERVICE_OWNED}" == 1 ]] && printf remove || printf keep)"
  printf '  releases : %s\n' "$([[ "${PURGE_ALL}" == 1 ]] && printf purge || printf keep)"
fi
if [[ "${DRY_RUN}" == 1 ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    printf '\nDRY-RUN 완료: container, monitor, proxy, release, 모델, swap, image 및 manifest를 변경하지 않았습니다.\n'
  else
    printf '\nDRY-RUN complete: no container, monitor, proxy, release, model, swap, image, or manifest changes were made.\n'
  fi
  exit 0
fi

[[ -r "${OPERATION_LOCK_LIB}" ]] || die "operation lock helper is unavailable: ${OPERATION_LOCK_LIB}"
# shellcheck source=scripts/lib/operation-lock.sh
source "${OPERATION_LOCK_LIB}"
acquire_operation_lock "${STATE_DIR}" "uninstall" || exit $?

[[ ! -e "${UPDATE_TRANSITION_FILE}" && ! -L "${UPDATE_TRANSITION_FILE}" ]] || \
  die "an update transition is active; recover or roll it back before uninstalling"
[[ ! -e "${RUNTIME_TRANSITION_FILE}" && ! -L "${RUNTIME_TRANSITION_FILE}" ]] || \
  die "a runtime transition is active; recover or roll it back before uninstalling"
[[ ! -e "${PROFILE_SWITCH_TRANSITION_FILE}" && ! -L "${PROFILE_SWITCH_TRANSITION_FILE}" ]] || \
  die "a profile-switch transition is active; run scripts/profile-switch-transition.sh recover before uninstalling"
[[ ! -e "${PROFILE_SWITCH_BACKUP}" && ! -L "${PROFILE_SWITCH_BACKUP}" &&
   ! -e "${PROFILE_SWITCH_CANDIDATE}" && ! -L "${PROFILE_SWITCH_CANDIDATE}" ]] || \
  die "profile-switch artifacts exist without an active transaction; run doctor before uninstalling"

if [[ "${SERVICE_OWNED}" != 1 ]] && "${INSTALL_ROOT}/scripts/manage-service.sh" status >/dev/null 2>&1; then
  die "a managed runtime service exists but is not owned by this manifest; rerun install.sh to adopt it or remove it explicitly"
fi
if [[ "${YES}" != 1 ]]; then
  [[ "${UI_LANG}" == ko ]] && prompt='계속하려면 DELETE를 입력하십시오: ' || prompt='Type DELETE to continue: '
  read -r -p "${prompt}" answer
  [[ "${answer}" == DELETE ]] || die "$([[ "${UI_LANG}" == ko ]] && printf 취소됨 || printf cancelled)"
fi
if [[ -r "${MONITOR_PID_FILE}" ]]; then
  monitor_pid="$(<"${MONITOR_PID_FILE}")"
  if [[ "${monitor_pid}" =~ ^[0-9]+$ && -r "/proc/${monitor_pid}/cmdline" ]] && \
     tr '\0' ' ' < "/proc/${monitor_pid}/cmdline" | grep -Fq 'monitor-runtime.sh'; then
    kill "${monitor_pid}" 2>/dev/null || true
  fi
  rm -f -- "${MONITOR_PID_FILE}"
fi
if [[ "${SERVICE_OWNED}" == 1 ]]; then
  sudo_with_operation_lock "${INSTALL_ROOT}/scripts/manage-service.sh" remove --yes
fi
if [[ "${PROXY_OWNED}" == 1 ]]; then
  sudo "${INSTALL_ROOT}/scripts/manage-proxy.sh" remove --yes
fi
docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
rm -f -- "${STOP_REASON_FILE}" "${STOP_REASON_FILE}.tmp" "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"

if [[ "${PURGE_MODEL}" == 1 ]]; then
  [[ "${MODEL_OWNED}" == 1 ]] || die "refusing model deletion: directory was not created by this installer"
  if [[ -e "${MODEL_DIR}" ]]; then
    if [[ ! -f "${MODEL_DIR}/.qwen38-model-manifest.json" && ! -f "${MODEL_DIR}/.qwen38-hybrid-manifest.json" ]]; then
      die "refusing model deletion: managed model/hybrid manifest missing"
    fi
    if [[ "${MODEL_DIR}" != "${HOME}/models/"* && "${MODEL_DIR}" != "${INSTALL_ROOT}/model" ]]; then
      die "refusing model deletion outside ${HOME}/models or the install root's model directory"
    fi
    rm -rf --one-file-system -- "${MODEL_DIR}"
    printf 'Removed model directory: %s\n' "${MODEL_DIR}"
  fi
fi
if [[ "${PURGE_SWAP}" == 1 ]]; then
  [[ "${SWAP_OWNED}" == 1 ]] || die "refusing swap deletion: swap was not created by this installer"
  if [[ -e "${SWAP_FILE}" ]]; then
    swap_args=(remove --file "${SWAP_FILE}"); [[ "${YES}" == 1 ]] && swap_args+=(--yes)
    sudo "${INSTALL_ROOT}/scripts/manage-swap.sh" "${swap_args[@]}"
  fi
fi
if [[ "${PURGE_IMAGE}" == 1 ]]; then
  [[ "${IMAGE_OWNED}" == 1 ]] || die "refusing image deletion: image existed before this installation"
  if docker image inspect "${VLLM_IMAGE}" >/dev/null 2>&1; then
    docker image rm "${VLLM_IMAGE}" || die "image is still in use"
  fi
fi
if [[ "${PURGE_ALL}" == 1 ]]; then
  [[ "${DATA_HOME}" == "${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark" ]] || die "refusing unsafe release-data purge path: ${DATA_HOME}"
  if [[ "${CONFIG_OWNED}" == 1 && "${CONFIG_OVERRIDE:-}" == "${STATE_DIR}/config.vllm.json" ]]; then
    rm -f -- "${CONFIG_OVERRIDE}"
  fi
  rm -rf --one-file-system -- "${DATA_HOME}"
  rm -f -- "${STATE_DIR}/monitor.log" "${STATE_DIR}/monitor.pid" \
    "${STATE_DIR}/runtime-stop.env" "${STATE_DIR}/runtime-stop.env.tmp" \
    "${STATE_DIR}/runtime-commit.env" "${STATE_DIR}/runtime-commit.env.tmp" \
    "${STATE_DIR}/runtime-transition.env" "${STATE_DIR}/runtime-transition.env.tmp" \
    "${STATE_DIR}/update-transition.env" "${STATE_DIR}/update-transition.env.tmp" \
    "${STATE_DIR}/profile-switch-transition.env" "${STATE_DIR}/profile-switch-transition.env.tmp" \
    "${STATE_FILE}.profile-switch-backup" "${STATE_FILE}.profile-switch-candidate" "${STATE_FILE}.profile-switch-candidate.tmp"
  rm -f -- "${STATE_FILE}"
  rmdir --ignore-fail-on-non-empty "${STATE_DIR}" 2>/dev/null || true
  [[ "${UI_LANG}" == ko ]] && printf '전체 제거 완료; immutable release 데이터와 설치 manifest를 삭제했습니다.\n' || \
    printf 'Full uninstall completed; immutable release data and installation manifest removed.\n'
else
  mark_manifest_uninstalled
  if [[ "${UI_LANG}" == ko ]]; then
    printf '제거 완료. manifest를 uninstalled 상태로 보존했습니다. 다음 install.sh 실행에서 새 모델 프로필을 선택할 수 있습니다: %s\n' "${STATE_FILE}"
  else
    printf 'Uninstall completed. The manifest is retained in the uninstalled state; the next install.sh run may select a new model profile: %s\n' "${STATE_FILE}"
  fi
fi
\t' read -r kind locator; do
    case "${kind}" in
      model)
        if [[ -e "${locator}" || -L "${locator}" ]]; then
          rm -rf --one-file-system -- "${locator}"
          printf 'Removed owned model asset: %s\n' "${locator}"
        fi
        asset_forget model "${locator}"
        ;;
      image)
        if docker image inspect "${locator}" >/dev/null 2>&1; then
          docker image rm "${locator}" || die "owned image is still in use: ${locator}"
          printf 'Removed owned image asset: %s\n' "${locator}"
        fi
        asset_forget image "${locator}"
        ;;
      *) die "invalid asset purge plan kind: ${kind}" ;;
    esac
  done < <(python3 "${ASSET_OWNERSHIP_TOOL}" plan-purge "${ASSET_OWNERSHIP_FILE}" --kind all)
}

mark_manifest_uninstalled() {
  python3 - "${STATE_FILE}" <<'PY'
import os
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
lines = path.read_text(encoding="utf-8").splitlines()
matches = [i for i, line in enumerate(lines) if line.startswith("PHASE=")]
if len(matches) != 1:
    raise SystemExit("installation manifest must contain exactly one PHASE field")
lines[matches[0]] = "PHASE=uninstalled"
temporary = path.with_name(path.name + ".tmp")
temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
os.chmod(temporary, path.stat().st_mode & 0o777)
os.replace(temporary, path)
PY
}

parse_install_manifest() {
  local parsed key value
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" install-uninstall "${STATE_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    printf -v "${key}" '%s' "${value}"
  done <"${parsed}"
  rm -f -- "${parsed}"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lang) [[ $# -ge 2 ]] || die "--lang requires en or ko"; CLI_LANG="$2"; shift ;;
    --purge-model) PURGE_MODEL=1; PURGE_SELECTED=1 ;; --purge-swap) PURGE_SWAP=1; PURGE_SELECTED=1 ;; --purge-image) PURGE_IMAGE=1; PURGE_SELECTED=1 ;;
    --purge-all) PURGE_MODEL=1; PURGE_SWAP=1; PURGE_IMAGE=1; PURGE_SELECTED=1; PURGE_ALL=1 ;; --yes) YES=1 ;; --dry-run) DRY_RUN=1 ;;
    -h|--help) usage; exit 0 ;; *) die "unknown argument: $1" ;;
  esac
  shift
done
[[ -r "${STATE_FILE}" ]] || die "installation manifest not found: ${STATE_FILE}"
[[ -r "${STATE_PARSER}" ]] || die "strict state parser is unavailable: ${STATE_PARSER}"
parse_install_manifest || die "installation manifest failed strict uninstall parsing: ${STATE_FILE}"
[[ -z "${CLI_LANG}" ]] || UI_LANG="${CLI_LANG}"
if [[ -z "${UI_LANG:-}" ]]; then
  if [[ "${YES}" == 0 && -t 0 ]]; then
    read -r -p 'Language / 언어 [1: English, 2: 한국어] (2): ' answer
    [[ "${answer}" == 1 || "${answer}" == en ]] && UI_LANG=en || UI_LANG=ko
  elif [[ "${LANG:-}" == ko_* ]]; then UI_LANG=ko; else UI_LANG=en; fi
fi
[[ "${UI_LANG}" == en || "${UI_LANG}" == ko ]] || die "--lang must be en or ko"
[[ -n "${INSTALL_ROOT:-}" && -d "${INSTALL_ROOT}" ]] || die "invalid INSTALL_ROOT in manifest"
[[ -n "${CONTAINER_NAME:-}" && "${CONTAINER_NAME}" != */* ]] || die "invalid container name"
MONITOR_PID_FILE="${STATE_DIR}/monitor.pid"

if [[ "${YES}" == 0 && "${PURGE_SELECTED}" == 0 ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    read -r -p '다운로드한 모델도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_MODEL=1
    read -r -p '전용 PLE swap도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_SWAP=1
    read -r -p 'vLLM Docker image도 제거합니까? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_IMAGE=1
  else
    read -r -p 'Remove the downloaded model too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_MODEL=1
    read -r -p 'Remove the dedicated PLE swap too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_SWAP=1
    read -r -p 'Remove the vLLM Docker image too? [y/N]: ' answer; [[ "${answer}" == y || "${answer}" == Y ]] && PURGE_IMAGE=1
  fi
fi

if [[ "${UI_LANG}" == ko ]]; then
  printf 'Qwen3.8 Flash Next 제거 마법사\n\n  container: %s (제거)\n' "${CONTAINER_NAME}"
  printf '  model    : %s (%s)\n' "${MODEL_DIR}" "$([[ "${PURGE_MODEL}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  PLE swap : %s (%s)\n' "${SWAP_FILE}" "$([[ "${PURGE_SWAP}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  image    : %s (%s)\n' "${VLLM_IMAGE}" "$([[ "${PURGE_IMAGE}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  service  : %s\n' "$([[ "${SERVICE_OWNED}" == 1 ]] && printf 제거 || printf 유지)"
  printf '  releases : %s\n' "$([[ "${PURGE_ALL}" == 1 ]] && printf '전체 제거' || printf '보존')"
else
  printf 'Qwen3.8 Flash Next uninstaller wizard\n\n  container: %s (remove)\n' "${CONTAINER_NAME}"
  printf '  model    : %s (%s)\n' "${MODEL_DIR}" "$([[ "${PURGE_MODEL}" == 1 ]] && printf remove || printf keep)"
  printf '  PLE swap : %s (%s)\n' "${SWAP_FILE}" "$([[ "${PURGE_SWAP}" == 1 ]] && printf remove || printf keep)"
  printf '  image    : %s (%s)\n' "${VLLM_IMAGE}" "$([[ "${PURGE_IMAGE}" == 1 ]] && printf remove || printf keep)"
  printf '  service  : %s\n' "$([[ "${SERVICE_OWNED}" == 1 ]] && printf remove || printf keep)"
  printf '  releases : %s\n' "$([[ "${PURGE_ALL}" == 1 ]] && printf purge || printf keep)"
fi
if [[ "${DRY_RUN}" == 1 ]]; then
  if [[ "${UI_LANG}" == ko ]]; then
    printf '\nDRY-RUN 완료: container, monitor, proxy, release, 모델, swap, image 및 manifest를 변경하지 않았습니다.\n'
  else
    printf '\nDRY-RUN complete: no container, monitor, proxy, release, model, swap, image, or manifest changes were made.\n'
  fi
  exit 0
fi

[[ -r "${OPERATION_LOCK_LIB}" ]] || die "operation lock helper is unavailable: ${OPERATION_LOCK_LIB}"
# shellcheck source=scripts/lib/operation-lock.sh
source "${OPERATION_LOCK_LIB}"
acquire_operation_lock "${STATE_DIR}" "uninstall" || exit $?

[[ ! -e "${UPDATE_TRANSITION_FILE}" && ! -L "${UPDATE_TRANSITION_FILE}" ]] || \
  die "an update transition is active; recover or roll it back before uninstalling"
[[ ! -e "${RUNTIME_TRANSITION_FILE}" && ! -L "${RUNTIME_TRANSITION_FILE}" ]] || \
  die "a runtime transition is active; recover or roll it back before uninstalling"
[[ ! -e "${PROFILE_SWITCH_TRANSITION_FILE}" && ! -L "${PROFILE_SWITCH_TRANSITION_FILE}" ]] || \
  die "a profile-switch transition is active; run scripts/profile-switch-transition.sh recover before uninstalling"
[[ ! -e "${PROFILE_SWITCH_BACKUP}" && ! -L "${PROFILE_SWITCH_BACKUP}" &&
   ! -e "${PROFILE_SWITCH_CANDIDATE}" && ! -L "${PROFILE_SWITCH_CANDIDATE}" ]] || \
  die "profile-switch artifacts exist without an active transaction; run doctor before uninstalling"

if [[ "${SERVICE_OWNED}" != 1 ]] && "${INSTALL_ROOT}/scripts/manage-service.sh" status >/dev/null 2>&1; then
  die "a managed runtime service exists but is not owned by this manifest; rerun install.sh to adopt it or remove it explicitly"
fi
if [[ "${YES}" != 1 ]]; then
  [[ "${UI_LANG}" == ko ]] && prompt='계속하려면 DELETE를 입력하십시오: ' || prompt='Type DELETE to continue: '
  read -r -p "${prompt}" answer
  [[ "${answer}" == DELETE ]] || die "$([[ "${UI_LANG}" == ko ]] && printf 취소됨 || printf cancelled)"
fi
if [[ -r "${MONITOR_PID_FILE}" ]]; then
  monitor_pid="$(<"${MONITOR_PID_FILE}")"
  if [[ "${monitor_pid}" =~ ^[0-9]+$ && -r "/proc/${monitor_pid}/cmdline" ]] && \
     tr '\0' ' ' < "/proc/${monitor_pid}/cmdline" | grep -Fq 'monitor-runtime.sh'; then
    kill "${monitor_pid}" 2>/dev/null || true
  fi
  rm -f -- "${MONITOR_PID_FILE}"
fi
if [[ "${SERVICE_OWNED}" == 1 ]]; then
  sudo_with_operation_lock "${INSTALL_ROOT}/scripts/manage-service.sh" remove --yes
fi
if [[ "${PROXY_OWNED}" == 1 ]]; then
  sudo "${INSTALL_ROOT}/scripts/manage-proxy.sh" remove --yes
fi
docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
rm -f -- "${STOP_REASON_FILE}" "${STOP_REASON_FILE}.tmp" "${RUNTIME_COMMIT_FILE}" "${RUNTIME_COMMIT_FILE}.tmp"

if [[ "${PURGE_MODEL}" == 1 ]]; then
  [[ "${MODEL_OWNED}" == 1 ]] || die "refusing model deletion: directory was not created by this installer"
  if [[ -e "${MODEL_DIR}" ]]; then
    if [[ ! -f "${MODEL_DIR}/.qwen38-model-manifest.json" && ! -f "${MODEL_DIR}/.qwen38-hybrid-manifest.json" ]]; then
      die "refusing model deletion: managed model/hybrid manifest missing"
    fi
    if [[ "${MODEL_DIR}" != "${HOME}/models/"* && "${MODEL_DIR}" != "${INSTALL_ROOT}/model" ]]; then
      die "refusing model deletion outside ${HOME}/models or the install root's model directory"
    fi
    rm -rf --one-file-system -- "${MODEL_DIR}"
    printf 'Removed model directory: %s\n' "${MODEL_DIR}"
  fi
fi
if [[ "${PURGE_SWAP}" == 1 ]]; then
  [[ "${SWAP_OWNED}" == 1 ]] || die "refusing swap deletion: swap was not created by this installer"
  if [[ -e "${SWAP_FILE}" ]]; then
    swap_args=(remove --file "${SWAP_FILE}"); [[ "${YES}" == 1 ]] && swap_args+=(--yes)
    sudo "${INSTALL_ROOT}/scripts/manage-swap.sh" "${swap_args[@]}"
  fi
fi
if [[ "${PURGE_IMAGE}" == 1 ]]; then
  [[ "${IMAGE_OWNED}" == 1 ]] || die "refusing image deletion: image existed before this installation"
  if docker image inspect "${VLLM_IMAGE}" >/dev/null 2>&1; then
    docker image rm "${VLLM_IMAGE}" || die "image is still in use"
  fi
fi
if [[ "${PURGE_ALL}" == 1 ]]; then
  [[ "${DATA_HOME}" == "${XDG_DATA_HOME:-$HOME/.local/share}/qwen38-spark" ]] || die "refusing unsafe release-data purge path: ${DATA_HOME}"
  if [[ "${CONFIG_OWNED}" == 1 && "${CONFIG_OVERRIDE:-}" == "${STATE_DIR}/config.vllm.json" ]]; then
    rm -f -- "${CONFIG_OVERRIDE}"
  fi
  rm -rf --one-file-system -- "${DATA_HOME}"
  rm -f -- "${STATE_DIR}/monitor.log" "${STATE_DIR}/monitor.pid" \
    "${STATE_DIR}/runtime-stop.env" "${STATE_DIR}/runtime-stop.env.tmp" \
    "${STATE_DIR}/runtime-commit.env" "${STATE_DIR}/runtime-commit.env.tmp" \
    "${STATE_DIR}/runtime-transition.env" "${STATE_DIR}/runtime-transition.env.tmp" \
    "${STATE_DIR}/update-transition.env" "${STATE_DIR}/update-transition.env.tmp" \
    "${STATE_DIR}/profile-switch-transition.env" "${STATE_DIR}/profile-switch-transition.env.tmp" \
    "${STATE_FILE}.profile-switch-backup" "${STATE_FILE}.profile-switch-candidate" "${STATE_FILE}.profile-switch-candidate.tmp"
  rm -f -- "${STATE_FILE}"
  rmdir --ignore-fail-on-non-empty "${STATE_DIR}" 2>/dev/null || true
  [[ "${UI_LANG}" == ko ]] && printf '전체 제거 완료; immutable release 데이터와 설치 manifest를 삭제했습니다.\n' || \
    printf 'Full uninstall completed; immutable release data and installation manifest removed.\n'
else
  mark_manifest_uninstalled
  if [[ "${UI_LANG}" == ko ]]; then
    printf '제거 완료. manifest를 uninstalled 상태로 보존했습니다. 다음 install.sh 실행에서 새 모델 프로필을 선택할 수 있습니다: %s\n' "${STATE_FILE}"
  else
    printf 'Uninstall completed. The manifest is retained in the uninstalled state; the next install.sh run may select a new model profile: %s\n' "${STATE_FILE}"
  fi
fi
