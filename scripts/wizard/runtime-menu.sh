#!/usr/bin/env bash
# No service or configuration mutations in migration stage 1.
wizard_runtime_menu() {
  local choice
  while true; do
    wizard_header 'Runtime / API / Service'
    wizard_menu_option 1 'Managed service status / 서비스 상태'
    wizard_menu_option 2 'Doctor / 정밀 진단'
    wizard_menu_option 3 'Manifest summary / 설치 요약'
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
      0|q|Q) return 0 ;;
      *) wizard_warning 'Invalid selection / 잘못된 선택입니다.' ;;
    esac
  done
}
