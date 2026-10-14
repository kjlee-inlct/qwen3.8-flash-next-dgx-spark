#!/usr/bin/env bash
# Inventory and plans only. Never remove evidence or assets from this menu.
wizard_storage_menu() {
  local choice
  while true; do
    wizard_header 'Storage / 저장 공간'
    wizard_menu_option 1 'Status (read-only) / 현황'
    wizard_menu_option 2 'Recommendations / 권장'
    wizard_menu_option 3 'Cleanup plan only / 삭제 계획'
    wizard_menu_option 4 'Benchmark archive integrity & reclaim gates (read-only) / 증거 검증'
    wizard_menu_option 0 'Back / 이전'
    wizard_input choice 'Select / 선택' 0
    case "${choice}" in
      1) bash "${ROOT_DIR}/scripts/manage-storage.sh" status ;;
      2) bash "${ROOT_DIR}/scripts/manage-storage.sh" recommend ;;
      3) bash "${ROOT_DIR}/scripts/manage-storage.sh" plan ;;
      4) python3 -B "${ROOT_DIR}/scripts/diagnostics/benchmark-reclaim-readiness.py" ||
            wizard_warning 'Benchmark evidence audit incomplete; cleanup remains blocked.' ;;
      0|q|Q) return 0 ;;
      *) wizard_warning 'Invalid selection / 잘못된 선택입니다.' ;;
    esac
  done
}
