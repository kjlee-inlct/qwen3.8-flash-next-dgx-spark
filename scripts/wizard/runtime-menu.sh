#!/usr/bin/env bash
# No service or configuration mutations in migration stage 1.
wizard_installed_api_settings_entry() {
  wizard_read_manifest
  if [[ "${WIZARD_MANIFEST_STATE}" != valid || "${WIZARD_PHASE}" != complete ]]; then
    wizard_warning 'A valid completed installation is required to edit API/port settings.'
    return 0
  fi
  wizard_info 'Existing installed-settings editor; keeps the active model and checkpoint.'
  wizard_info 'Current ports, API exposure mode and service policy are shown in its plan.'
  wizard_warning 'No changes are applied without a separate default-NO approval and final plan review.'
  # This is the installer’s EXISTING recoverable settings transition, not a
  # second proxy or service reconfiguration implementation.
  if ! bash "${ROOT_DIR}/install.sh" --lang "${UI_LANG}" --manage-settings; then
    wizard_warning 'Installed settings editor failed/cancelled. Examine output before retrying.'
  fi
}

wizard_runtime_menu() {
  local choice
  while true; do
    wizard_header 'Runtime / API / Service'
    wizard_menu_option 1 'Managed service status / 서비스 상태'
    wizard_menu_option 2 'Doctor / 정밀 진단'
    wizard_menu_option 3 'Manifest summary / 설치 요약'
    wizard_menu_option 4 'API access / Docker & LAN ports / 포트 설정 변경'
    wizard_menu_option 5 'API proxy status (read-only) / 프록시 상태 조회'
    wizard_menu_option 0 'Back / 이전'
    wizard_input choice 'Select / 선택' 0
    case "${choice}" in
      1)
        if bash "${ROOT_DIR}/scripts/manage-service.sh" status; then
          :
        else
          wizard_warning 'Service not installed or status unavailable.'
        fi ;;
      2) bash "${ROOT_DIR}/scripts/doctor.sh" ||
        wizard_warning 'Doctor reported warnings/errors.' ;;
      3) wizard_status_summary ;;
      4) wizard_installed_api_settings_entry ;;
      5) if bash "${ROOT_DIR}/scripts/manage-proxy.sh" status; then
           :
         else
           wizard_warning 'Managed proxy not installed or status unavailable.'
         fi ;;
      0|q|Q) return 0 ;;
      *) wizard_warning 'Invalid selection / 잘못된 선택입니다.' ;;
    esac
  done
}
