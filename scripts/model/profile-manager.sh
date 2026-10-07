#!/usr/bin/env bash
# Registry-backed profile presentation and local inventory helper.
#
# This file does not define profile identity. model-profiles.sh remains authoritative
# for availability/installability/default/repository/runtime metadata. This helper
# only combines that registry metadata with read-only local checkpoint/image state.

PROFILE_MANAGER_REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"

profile_manager_root_has_managed() {
  local root="$1"
  [[ -d "${root}" ]] || return 1
  find "${root}" -mindepth 1 -maxdepth 2 -type f \
    \( -name .qwen38-model-manifest.json -o -name .qwen38-hybrid-manifest.json \) \
    -print -quit 2>/dev/null | grep -q .
}

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

profile_manager_manifest_present() {
  local path="$1"
  [[ -f "${path}/.qwen38-model-manifest.json" || -f "${path}/.qwen38-hybrid-manifest.json" ]]
}

profile_manager_entry() (
  local profile="$1" active_profile="${2:-}"
  local display status default installable repo description
  local root checkpoint="" first_checkpoint="" local_state=absent image="" image_state=unavailable

  describe_model_profile "${profile}" || exit $?
  display="${PROFILE_DISPLAY_NAME}"
  status="${PROFILE_STATUS}"
  default="${PROFILE_DEFAULT}"
  installable="${PROFILE_INSTALLABLE}"
  repo="${PROFILE_REPO}"
  description="${PROFILE_DESCRIPTION}"

  if [[ "${installable}" == 1 ]]; then
    while IFS= read -r root; do
      [[ -n "${root}" ]] || continue
      export QWEN38_MODEL_ROOT="${root}"
      load_download_profile "${profile}" >/dev/null || exit $?
      [[ -n "${first_checkpoint}" ]] || first_checkpoint="${PROFILE_MODEL_DIR}"
      image="${PROFILE_IMAGE}"

      if profile_manager_manifest_present "${PROFILE_MODEL_DIR}"; then
        checkpoint="${PROFILE_MODEL_DIR}"
        local_state=installed
        break
      fi
      if [[ "${local_state}" == absent && ( -e "${PROFILE_MODEL_DIR}" || -L "${PROFILE_MODEL_DIR}" ) ]]; then
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

  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "${profile}" "${display}" "${status}" "${installable}" "${default}" \
    "${local_state}" "${active}" "${image_state}" "${repo}" "${checkpoint}" "${description}"
)

profile_manager_load() {
  local profile="$1" active_profile="${2:-}"
  IFS=$'\t' read -r \
    PM_PROFILE PM_DISPLAY_NAME PM_STATUS PM_INSTALLABLE PM_DEFAULT \
    PM_LOCAL_STATE PM_ACTIVE PM_IMAGE_STATE PM_REPO PM_CHECKPOINT PM_DESCRIPTION \
    < <(profile_manager_entry "${profile}" "${active_profile}")
  [[ -n "${PM_PROFILE:-}" ]]
}

profile_manager_detail() {
  local profile="$1" active_profile="${2:-}" -a labels=()
  profile_manager_load "${profile}" "${active_profile}" || return

  labels+=("${PM_STATUS}")
  [[ "${PM_INSTALLABLE}" == 1 ]] && labels+=("installable") || labels+=("not installable")
  case "${PM_LOCAL_STATE}" in
    installed) labels+=("installed") ;;
    unmanaged) labels+=("local path unmanaged") ;;
    not-installable) labels+=("not installed") ;;
    *) labels+=("not installed") ;;
  esac
  [[ "${PM_DEFAULT}" != 1 ]] || labels+=("default")
  [[ "${PM_ACTIVE}" != yes ]] || labels+=("active")
  case "${PM_IMAGE_STATE}" in
    present) labels+=("image present") ;;
    absent) labels+=("image absent") ;;
  esac

  local joined="" label
  for label in "${labels[@]}"; do
    [[ -z "${joined}" ]] || joined+=" / "
    joined+="${label}"
  done
  printf '%s — %s\n' "${joined}" "${PM_DESCRIPTION}"
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
