#!/usr/bin/env bash
# Hybrid retirement guidance: read-only, separate from generic model menu.
wizard_hybrid_retirement_guide() {
  local choice stage missing=0
  wizard_header 'Hybrid retirement / Hybrid 연구 자산 정리'
  wizard_warning 'Evidence first, then exact stopped containers, then model stages, then verification.'
  wizard_warning 'Historical exact-17 scripts are NOT reusable for new Hybrid experiments.'
  wizard_info 'This screen is read-only. It never removes models, containers, volumes or images.'
  while true; do
    wizard_menu_option 1 'Current Hybrid inventory and retired stages / 모델 잔존 상태'
    wizard_menu_option 2 'Check archived 17-container evidence (historical only) / 과거 증거 검증'
    wizard_menu_option 3 'Check active/retained Docker Hybrid references / 컨테이너 참조 확인'
    wizard_menu_option 4 'Review safe retirement workflow / 단계별 삭제 절차'
    wizard_menu_option 0 'Back / 이전'
    wizard_input choice 'Select / 선택' 0
    case "${choice}" in
      1)
        missing=0
        for stage in qwen3.8-hybrid-quant-layout qwen3.8-h4-orca-all \
                     qwen3.8-h5-neutral-input-scale qwen3.8-h6-modelopt-w4a16; do
          if [[ -e "${ROOT_DIR}/models/${stage}" || -L "${ROOT_DIR}/models/${stage}" ]]; then
            wizard_warning "PRESENT / 존재: ${stage}"
          else
            wizard_info "ABSENT / 없음: ${stage}"
            ((missing+=1))
          fi
        done
        if [[ -d "${ROOT_DIR}/models/qwen3.8-flash-next-orcarouter" ]]; then
          wizard_success 'Protected OrcaRouter path present / 원본 경로 존재'
        else
          wizard_warning 'Protected OrcaRouter path missing / 원본 경로 확인 필요'
        fi
        wizard_info "Absent Hybrid stages: ${missing}/4 (absence alone does not verify protected data integrity)."
        ;;
      2)
        if python3 -B "${ROOT_DIR}/scripts/model/hybrid-archive-git-summary.py"; then
          wizard_success 'Historical archive checksum and metadata PASS.'
        else
          wizard_warning 'Historical archive not present or invalid; no deletion is authorized.'
        fi
        ;;
      3)
        if python3 -B "${ROOT_DIR}/scripts/model/hybrid-docker-inventory.py"; then
          wizard_info 'Read-only candidates listed; inspect ALL retained Docker objects before deletion.'
        else
          wizard_warning 'Docker inventory unavailable; no deletion is authorized.'
        fi
        ;;
      4)
        wizard_info '1. Inventory all Hybrid stages, aliases and Docker references.'
        wizard_info '2. Archive stopped-container logs/metadata privately and verify SHA256.'
        wizard_info '3. Commit sanitized findings and manifest digest; raw logs need secrets review.'
        wizard_info '4. Pin exact container IDs; dry-run, approve, remove and audit survivors.'
        wizard_info '5. Recheck model tree, symlink namespaces, protected assets and mounts.'
        wizard_info '6. Dry-run, approve explicit model stages, then independently audit disk and evidence.'
        wizard_warning 'Old exact-17/H3-H6 scripts describe ONE completed historical cleanup, not a generic approval.'
        ;;
      0|q|Q) return 0 ;;
      *) wizard_warning 'Invalid selection / 잘못된 선택입니다.' ;;
    esac
  done
}

