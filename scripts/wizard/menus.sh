#!/usr/bin/env bash
# Top-level UX and safe delegation, not lifecycle mutation.
# shellcheck source=scripts/wizard/candidate-metadata-menu.sh
source "${ROOT_DIR}/scripts/wizard/candidate-metadata-menu.sh"
# shellcheck source=scripts/wizard/model-menu.sh
source "${ROOT_DIR}/scripts/wizard/model-menu.sh"
# shellcheck source=scripts/wizard/runtime-menu.sh
source "${ROOT_DIR}/scripts/wizard/runtime-menu.sh"
# shellcheck source=scripts/wizard/benchmark-menu.sh
source "${ROOT_DIR}/scripts/wizard/benchmark-menu.sh"
# shellcheck source=scripts/wizard/storage-menu.sh
source "${ROOT_DIR}/scripts/wizard/storage-menu.sh"

wizard_install_entry() {
  wizard_read_manifest
  if [[ "${WIZARD_MANIFEST_STATE}" == invalid ]]; then
    wizard_error 'Invalid install manifest / 설치 상태 파일 검증 실패'
    return 0
  fi
  if [[ "${WIZARD_MANIFEST_STATE}" == valid && "${WIZARD_PHASE}" == complete ]]; then
    wizard_warning 'Already installed: use management menus / 설치 완료: 관리 메뉴를 사용하세요.'
    return 0
  fi
  wizard_info 'Existing installer retains recovery and final review safeguards.'
  wizard_yes_no 'Open installation/resume flow? / 설치 절차를 시작합니까?' no || return 0
  bash "${ROOT_DIR}/install.sh" --lang "${UI_LANG}"
}

wizard_uninstall_entry() {
  local choice
  while true; do
    wizard_header 'Uninstall / 프로젝트 제거'
    wizard_warning 'Full-project removal is NOT qualified. Existing experiments and evidence may remain.'
    wizard_menu_option 1 'Full-project resource inventory (READ ONLY) / 전체 잔여 자산 조사'
    wizard_menu_option 2 'Existing managed uninstaller (confirmation required) / 기존 설치 자산 제거'
    wizard_menu_option 0 'Back / 이전'
    wizard_input choice 'Select / 선택' 0
    case "${choice}" in
      1) python3 -B "${ROOT_DIR}/scripts/lifecycle/uninstall-inventory.py" plan ||
           wizard_warning 'Inventory partial/blocked. No resources were changed.' ;;
      2)
        wizard_read_manifest
        if [[ "${WIZARD_MANIFEST_STATE}" != valid ]]; then
          wizard_warning 'Valid managed manifest required to use existing uninstaller.'
          continue
        fi
        wizard_warning 'This uninstaller does NOT delete all research Docker, cached weights or evidence.'
        wizard_yes_no 'Open existing managed uninstaller? / 기존 제거 절차를 시작합니까?' no || continue
        bash "${ROOT_DIR}/uninstall.sh" --lang "${UI_LANG}" ||
          wizard_warning 'Uninstall blocked/failed; verify live state before another attempt.'
        ;;
      0|q|Q) return 0 ;;
      *) wizard_warning 'Invalid selection / 잘못된 선택입니다.' ;;
    esac
  done
}

wizard_advanced_menu() {
  local choice
  while true; do
    wizard_header 'Advanced / 고급'
    wizard_menu_option 1 'OrcaRouter A/B status (read-only) / 기록 상태'
    wizard_menu_option 2 'Evidence index / 증거 목록'
    wizard_menu_option 3 'Official ARM64 OrcaRouter C plan (source-only) / C 계획'
    wizard_menu_option 4 'Official ARM64 OrcaRouter C preflight (read-only) / C 사전 점검'
    wizard_menu_option 5 'Official ARM64 OrcaRouter C host snapshot (read-only) / C 호스트 확인'
    wizard_menu_option 6 'Official ARM64 C saved CLI result (read-only) / C 호환성 검사 결과'
    wizard_menu_option 0 'Back / 이전'
    wizard_input choice 'Select / 선택' 0
    case "${choice}" in
      1) python3 "${ROOT_DIR}/scripts/runtime/orcarouter-ab-trial.py" status ||
        wizard_warning 'Status unavailable.' ;;
      2) printf 'Evidence index: %s\n' "${ROOT_DIR}/scripts/benchmark/evidence/README.md" ;;
      3) python3 -B "${ROOT_DIR}/scripts/runtime/orcarouter-peer-c-readonly.py" plan ||
        wizard_warning 'C plan unavailable.' ;;
      4) python3 -B "${ROOT_DIR}/scripts/runtime/orcarouter-peer-c-readonly.py" preflight ||
        wizard_warning 'C preflight BLOCKED; this does not authorize image pull or GPU start.' ;;
      5) python3 -B "${ROOT_DIR}/scripts/runtime/orcarouter-peer-c-readonly.py" host-check ||
        wizard_warning 'C host snapshot BLOCKED; no Docker create or GPU start was attempted.' ;;
      6) python3 -B "${ROOT_DIR}/scripts/runtime/orcarouter-peer-c-cli-probe.py" report ||
           wizard_warning 'Saved C CLI diagnostic unavailable. No new Docker probe was started.' ;;
      0|q|Q) return 0 ;;
      *) wizard_warning 'Invalid selection / 잘못된 선택입니다.' ;;
    esac
  done
}

wizard_main_menu() {
  local choice
  while true; do
    wizard_header 'Qwen3.8 Flash Next — DGX Spark Manager'
    wizard_status_summary
    if [[ "${UI_LANG}" == ko ]]; then
      wizard_menu_option 1 '모델 설치 / 재개'
      wizard_menu_option 2 '제거'
      wizard_menu_option 3 '모델 / 전환 미리보기'
      wizard_menu_option 4 '런타임 / API / 포트 / 서비스'
      wizard_menu_option 5 '벤치마크 / 사전 점검'
      wizard_menu_option 6 '저장 공간 / 정리 계획'
      wizard_menu_option 7 '진단'
      wizard_menu_option 8 '고급 / 연구 기록'
      wizard_menu_option 0 '종료'
      wizard_input choice '선택' 0
    else
      wizard_menu_option 1 'Install / resume'
      wizard_menu_option 2 'Uninstall'
      wizard_menu_option 3 'Models / switch preview'
      wizard_menu_option 4 'Runtime / API / ports / service'
      wizard_menu_option 5 'Benchmark / preflight'
      wizard_menu_option 6 'Storage / cleanup plan'
      wizard_menu_option 7 'Diagnostics'
      wizard_menu_option 8 'Advanced / research'
      wizard_menu_option 0 'Exit'
      wizard_input choice 'Select' 0
    fi
    case "${choice}" in
      1) wizard_install_entry ;;
      2) wizard_uninstall_entry ;;
      3) wizard_model_menu ;;
      4) wizard_runtime_menu ;;
      5) wizard_benchmark_menu ;;
      6) wizard_storage_menu ;;
      7) bash "${ROOT_DIR}/scripts/doctor.sh" ||
        wizard_warning 'Diagnostics reported warnings or errors.' ;;
      8) wizard_advanced_menu ;;
      0|q|Q) return 0 ;;
      *) wizard_warning 'Invalid selection / 잘못된 선택입니다.' ;;
    esac
  done
}
