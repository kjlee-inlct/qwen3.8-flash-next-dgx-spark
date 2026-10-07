#!/usr/bin/env bash
# Registry-backed profile presentation and local inventory helper.
#
# This file does not define profile identity. model-profiles.sh remains authoritative
# for availability/installability/default/repository/runtime metadata. This helper
# only combines that registry metadata with read-only local checkpoint/image state.

PROFILE_MANAGER_REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"

profile_manager_roots() {
  local -A seen=()
  local candidate canonical

  for candidate in \
    "${QWEN38_MODEL_ROOT:-}" \
    "${MODEL_DIR:+$(dirname -- "${MODEL_DIR}")}" \
    "${PROFILE_MANAGER_REPO_ROOT}/models" \
    "${HOME}/models"
  do
    [[ -n "${candidate}" ]] || continue
    canonical="$(realpath -m -- "${candidate}")"
    [[ -z "${seen[${canonical}]:-}" ]] || continue
    seen["${canonical}"]=1
    printf '%s\n' "${canonical}"
  done
}

profile_manager_manifest_state() {
  local path="$1" manifest found=0
  for manifest in \
    "${path}/.qwen38-model-manifest.json" \
    "${path}/.qwen38-hybrid-manifest.json"
  do
    [[ -f "${manifest}" && ! -L "${manifest}" ]] || continue
    found=1
    if grep -Eq '"status"[[:space:]]*:[[:space:]]*"complete"' "${manifest}"; then
      printf 'installed\n'
      return 0
    fi
  done
  [[ "${found}" == 0 ]] || { printf 'incomplete\n'; return 0; }
  return 1
}

profile_manager_entry() (
  local profile="$1" active_profile="${2:-}"
  local display status default installable repo description description_ko
  local root checkpoint="" first_checkpoint="" manifest_state="" local_state=absent image="" image_state=unavailable

  describe_model_profile "${profile}" || exit $?
  display="${PROFILE_DISPLAY_NAME}"
  status="${PROFILE_STATUS}"
  default="${PROFILE_DEFAULT}"
  installable="${PROFILE_INSTALLABLE}"
  repo="${PROFILE_REPO}"
  description="${PROFILE_DESCRIPTION}"
  description_ko="${PROFILE_DESCRIPTION_KO:-${PROFILE_DESCRIPTION}}"

  if [[ "${installable}" == 1 ]]; then
    while IFS= read -r root; do
      [[ -n "${root}" ]] || continue
      export QWEN38_MODEL_ROOT="${root}"
      load_download_profile "${profile}" >/dev/null || exit $?
      [[ -n "${first_checkpoint}" ]] || first_checkpoint="${PROFILE_MODEL_DIR}"
      image="${PROFILE_IMAGE}"

      manifest_state="$(profile_manager_manifest_state "${PROFILE_MODEL_DIR}" 2>/dev/null || true)"
      if [[ "${manifest_state}" == installed ]]; then
        checkpoint="${PROFILE_MODEL_DIR}"
        local_state=installed
        break
      fi
      if [[ "${manifest_state}" == incomplete ]]; then
        [[ "${local_state}" == installed ]] || {
          checkpoint="${PROFILE_MODEL_DIR}"
          local_state=incomplete
        }
      elif [[ "${local_state}" == absent && ( -e "${PROFILE_MODEL_DIR}" || -L "${PROFILE_MODEL_DIR}" ) ]]; then
        checkpoint="${PROFILE_MODEL_DIR}"
        local_state=unmanaged
      fi
    done < <(profile_manager_roots)

    [[ -n "${checkpoint}" ]] || checkpoint="${first_checkpoint}"

    if command -v docker >/dev/null 2>&1; then
      if docker image inspect "${image}" >/dev/null 2>&1; then
        image_state=present
      else
        image_state=absent
      fi
    fi
  else
    local_state=not-installable
    image_state=not-applicable
  fi

  local active=no
  [[ "${profile}" != "${active_profile}" ]] || active=yes

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "${profile}" "${display}" "${status}" "${installable}" "${default}" \
    "${local_state}" "${active}" "${image_state}" "${repo}" "${checkpoint}" "${description}" "${description_ko}"
)

profile_manager_load() {
  local profile="$1" active_profile="${2:-}"
  IFS=  [[ -n "${PM_PROFILE:-}" ]]
}

profile_manager_loaded_detail() {
  local lang="${1:-en}"
  local -a labels=()
  local joined="" label description

  if [[ "${lang}" == ko ]]; then
    case "${PM_STATUS}" in
      stable) labels+=("안정") ;;
      experimental) labels+=("실험") ;;
      in-progress) labels+=("진행 중") ;;
      planned) labels+=("계획") ;;
      *) labels+=("${PM_STATUS}") ;;
    esac
    [[ "${PM_INSTALLABLE}" == 1 ]] && labels+=("설치 가능") || labels+=("설치 불가")
    case "${PM_LOCAL_STATE}" in
      installed) labels+=("설치됨") ;;
      incomplete) labels+=("불완전") ;;
      unmanaged) labels+=("비관리 로컬 경로") ;;
      *) labels+=("미설치") ;;
    esac
    [[ "${PM_DEFAULT}" != 1 ]] || labels+=("기본")
    [[ "${PM_ACTIVE}" != yes ]] || labels+=("활성")
    case "${PM_IMAGE_STATE}" in
      present) labels+=("이미지 있음") ;;
      absent) labels+=("이미지 없음") ;;
    esac
    description="${PM_DESCRIPTION_KO}"
  else
    labels+=("${PM_STATUS}")
    [[ "${PM_INSTALLABLE}" == 1 ]] && labels+=("installable") || labels+=("not installable")
    case "${PM_LOCAL_STATE}" in
      installed) labels+=("installed") ;;
      incomplete) labels+=("incomplete") ;;
      unmanaged) labels+=("local path unmanaged") ;;
      *) labels+=("not installed") ;;
    esac
    [[ "${PM_DEFAULT}" != 1 ]] || labels+=("default")
    [[ "${PM_ACTIVE}" != yes ]] || labels+=("active")
    case "${PM_IMAGE_STATE}" in
      present) labels+=("image present") ;;
      absent) labels+=("image absent") ;;
    esac
    description="${PM_DESCRIPTION}"
  fi

  for label in "${labels[@]}"; do
    [[ -z "${joined}" ]] || joined+=" / "
    joined+="${label}"
  done
  printf '%s — %s\n' "${joined}" "${description}"
}

profile_manager_detail() {
  local profile="$1" active_profile="${2:-}"
  profile_manager_load "${profile}" "${active_profile}" || return
  profile_manager_loaded_detail "${3:-en}"
}

print_profile_manager() {
  local active_profile="${1:-}" profile
  printf 'Qwen3.8 profile manager\n'
  printf '%-20s %-13s %-11s %-11s %-7s %-11s %s\n' \
    PROFILE STATUS INSTALLABLE LOCAL ACTIVE IMAGE NAME

  while IFS= read -r profile; do
    [[ -n "${profile}" ]] || continue
    profile_manager_load "${profile}" "${active_profile}" || return
    printf '%-20s %-13s %-11s %-11s %-7s %-11s %s\n' \
      "${PM_PROFILE}" "${PM_STATUS}" yes "${PM_LOCAL_STATE}" "${PM_ACTIVE}" "${PM_IMAGE_STATE}" "${PM_DISPLAY_NAME}"
    printf '  repo=%s%s\n' "${PM_REPO}" "${PM_CHECKPOINT:+ checkpoint=${PM_CHECKPOINT}}"
  done < <(list_model_profiles)

  while IFS= read -r profile; do
    [[ -n "${profile}" ]] || continue
    profile_manager_load "${profile}" "${active_profile}" || return
    printf '%-20s %-13s %-11s %-11s %-7s %-11s %s\n' \
      "${PM_PROFILE}" "${PM_STATUS}" no "${PM_LOCAL_STATE}" "${PM_ACTIVE}" "${PM_IMAGE_STATE}" "${PM_DISPLAY_NAME}"
    printf '  repo=%s\n' "${PM_REPO}"
  done < <(list_model_candidates)
}
\t' read -r \
    PM_PROFILE PM_DISPLAY_NAME PM_STATUS PM_INSTALLABLE PM_DEFAULT \
    PM_LOCAL_STATE PM_ACTIVE PM_IMAGE_STATE PM_REPO PM_CHECKPOINT \
    PM_DESCRIPTION PM_DESCRIPTION_KO \
    < <(profile_manager_entry "${profile}" "${active_profile}")
  [[ -n "${PM_PROFILE:-}" ]]
}

profile_manager_loaded_detail() {
  local -a labels=()
  local joined="" label

  labels+=("${PM_STATUS}")
  [[ "${PM_INSTALLABLE}" == 1 ]] && labels+=("installable") || labels+=("not installable")
  case "${PM_LOCAL_STATE}" in
    installed) labels+=("installed") ;;
    incomplete) labels+=("incomplete") ;;
    unmanaged) labels+=("local path unmanaged") ;;
    *) labels+=("not installed") ;;
  esac
  [[ "${PM_DEFAULT}" != 1 ]] || labels+=("default")
  [[ "${PM_ACTIVE}" != yes ]] || labels+=("active")
  case "${PM_IMAGE_STATE}" in
    present) labels+=("image present") ;;
    absent) labels+=("image absent") ;;
  esac

  for label in "${labels[@]}"; do
    [[ -z "${joined}" ]] || joined+=" / "
    joined+="${label}"
  done
  printf '%s — %s\n' "${joined}" "${PM_DESCRIPTION}"
}

profile_manager_detail() {
  local profile="$1" active_profile="${2:-}"
  profile_manager_load "${profile}" "${active_profile}" || return
  profile_manager_loaded_detail
}

print_profile_manager() {
  local active_profile="${1:-}" profile
  printf 'Qwen3.8 profile manager\n'
  printf '%-20s %-13s %-11s %-11s %-7s %-11s %s\n' \
    PROFILE STATUS INSTALLABLE LOCAL ACTIVE IMAGE NAME

  while IFS= read -r profile; do
    [[ -n "${profile}" ]] || continue
    profile_manager_load "${profile}" "${active_profile}" || return
    printf '%-20s %-13s %-11s %-11s %-7s %-11s %s\n' \
      "${PM_PROFILE}" "${PM_STATUS}" yes "${PM_LOCAL_STATE}" "${PM_ACTIVE}" "${PM_IMAGE_STATE}" "${PM_DISPLAY_NAME}"
    printf '  repo=%s%s\n' "${PM_REPO}" "${PM_CHECKPOINT:+ checkpoint=${PM_CHECKPOINT}}"
  done < <(list_model_profiles)

  while IFS= read -r profile; do
    [[ -n "${profile}" ]] || continue
    profile_manager_load "${profile}" "${active_profile}" || return
    printf '%-20s %-13s %-11s %-11s %-7s %-11s %s\n' \
      "${PM_PROFILE}" "${PM_STATUS}" no "${PM_LOCAL_STATE}" "${PM_ACTIVE}" "${PM_IMAGE_STATE}" "${PM_DISPLAY_NAME}"
    printf '  repo=%s\n' "${PM_REPO}"
  done < <(list_model_candidates)
}
