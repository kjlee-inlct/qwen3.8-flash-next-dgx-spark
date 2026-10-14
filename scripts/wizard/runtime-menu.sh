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

wizard_post_benchmark_shutdown() {
  wizard_read_manifest
  if [[ "${WIZARD_MANIFEST_STATE}" != valid || "${WIZARD_PHASE}" != complete ]]; then
    wizard_warning 'Only a verified complete installation can be deactivated.'
    return 0
  fi
  wizard_warning 'This disables and removes the currently managed shared API proxy and boot service.'
  wizard_warning 'The installed model identity, Docker images, stopped containers, evidence and releases remain intact.'
  wizard_warning 'Any OpenWebUI or LAN client using the managed API will lose its endpoint.'
  wizard_info 'No runtime will be started; changes use the installed settings rollback-capable transaction.'
  wizard_yes_no 'Open post-benchmark shutdown plan? / API·서비스 종료 계획을 확인합니까?' no || return 0
  if bash "${ROOT_DIR}/install.sh" --lang "${UI_LANG}" --manage-settings --shutdown-access; then
    wizard_verify_managed_host_idle
  else
    wizard_warning 'Shutdown was cancelled, blocked, or failed. Verify exact status before retrying.'
  fi
}

wizard_verify_managed_host_idle() {
  wizard_header 'Full post-benchmark host idle audit / 서비스·포트·자동기동 검증'
  wizard_info 'Read-only: installed API policy, shared systemd units, Docker and configured ports.'
  if python3 -B "${ROOT_DIR}/scripts/diagnostics/verify-managed-idle.py"; then
    wizard_success 'No managed model runtime, API proxy listener, or auto-boot service remains.'
  else
    wizard_warning 'Host is NOT QUIESCENT or status cannot be verified.'
    wizard_warning 'Do not confuse mazinb-only artifact cleanup PASS with full host-idle PASS.'
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
    wizard_menu_option 6 'Post-benchmark API & boot shutdown / 벤치 후 프록시·자동 기동 해제'
    wizard_menu_option 7 'Verify full host idle (read-only) / 서비스·포트·재부팅 대기 검증'
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
      6) wizard_post_benchmark_shutdown ;;
      7) wizard_verify_managed_host_idle ;;
      0|q|Q) return 0 ;;
      *) wizard_warning 'Invalid selection / 잘못된 선택입니다.' ;;
    esac
  done
}
