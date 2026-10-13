#!/usr/bin/env bash
# Read-only model inventory and no-apply profile-switch preview.
wizard_profile_preview() {
  local target
  wizard_read_manifest
  if [[ "${WIZARD_MANIFEST_STATE}" != valid || "${WIZARD_PHASE}" != complete ]]; then
    wizard_warning 'A valid completed installation is required for switch preview.'
    return 0
  fi
  # shellcheck source=scripts/model-profiles.sh
  source "${ROOT_DIR}/scripts/model-profiles.sh"
  wizard_input target 'Profile / 프로필 이름' ''
  [[ -n "${target}" ]] || { wizard_warning 'Empty profile: cancelled.'; return 0; }
  if ! list_model_profiles | grep -Fxq -- "${target}"; then
    wizard_warning 'Unsupported or not-installable profile / 지원되지 않는 프로필'
    return 0
  fi
  [[ "${target}" != "${WIZARD_PROFILE}" ]] ||
    { wizard_info 'Already selected / 이미 선택된 프로필'; return 0; }
  wizard_info 'Preview only: no managed Docker or release changes.'
  bash "${ROOT_DIR}/install.sh" --lang "${UI_LANG}" --model "${target}" --dry-run
  wizard_warning 'Live switching not yet connected in the modular controller.'
}

wizard_model_menu() {
  local choice
  while true; do
    wizard_header 'Model management / 모델 관리'
    wizard_menu_option 1 'Supported profiles / 지원 프로필'
    wizard_menu_option 2 'Model assets / 자산 상태'
    wizard_menu_option 3 'Switch preview only / 전환 미리보기'
    wizard_menu_option 0 'Back / 이전'
    wizard_input choice 'Select / 선택' 0
    case "${choice}" in
      1) bash "${ROOT_DIR}/install.sh" --list-models ;;
      2) bash "${ROOT_DIR}/scripts/manage-models.sh" assets ;;
      3) wizard_profile_preview ;;
      0|q|Q) return 0 ;;
      *) wizard_warning 'Invalid selection / 잘못된 선택입니다.' ;;
    esac
  done
}
