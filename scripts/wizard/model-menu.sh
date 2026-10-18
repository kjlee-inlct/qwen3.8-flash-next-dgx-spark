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

wizard_orcarouter_backend_status() {
  wizard_header 'OrcaRouter backend compatibility / 실행 백엔드 호환성'
  wizard_info 'P0: select checkpoint and backend in the install/switch Wizard after qualification.'
  wizard_info 'Checkpoint profile: orcarouter (one model, multiple possible runtime backends).'
  wizard_info 'Registry configured backend: vllm-orcarouter-v029:v1 (implementation entry exists).'
  wizard_warning 'A registry entry does not prove the currently installed runtime is READY.'
  wizard_warning 'Official ARM64 C: image digest/package versions verified; CPU-only CLI help failed before printing options.'
  wizard_warning 'Failure: DeviceConfig could not infer GPU type in deliberately GPU-hidden probe.'
  wizard_warning 'CLI options, PLE, KV16GiB, MTP, model READY and host stability remain UNQUALIFIED.'
  wizard_warning 'Official C cannot be selected for ordinary install/switch; historical A/B preserved.'
  wizard_info 'Saved traceback: Advanced -> Official ARM64 C saved CLI result (read-only).'
  printf '%s\n' \
    'ORCAROUTER_PROFILE=orcarouter' \
    'ORCAROUTER_V029_BACKEND=REGISTRY_IMPLEMENTED_NOT_LIVE_ATTESTED_HERE' \
    'ORCAROUTER_OFFICIAL_ARM64_C=BLOCKED_PRE_RUNTIME_DEVICE_INFERENCE_CPU_ONLY' \
    'ORCAROUTER_OFFICIAL_ARM64_C_INSTALL_SWITCH=DISABLED_UNQUALIFIED' \
    'WIZARD_MUTATION=NONE'
}

wizard_mazinb_source_reclaim() {
  local confirmed
  wizard_header 'mazinb original checkpoint reclamation / 원본 모델 정리'
  wizard_warning 'Only the original mazinb checkpoint is a candidate.'
  wizard_warning 'Protected OrcaRouter, shared images, archived research logs and benchmark reports MUST remain.'
  wizard_warning 'Removing the model makes stopped mazinb trials non-restartable until the model is re-downloaded.'
  wizard_info 'Checking benchmark archive checksums, stopped journal and protected-asset dependencies (read-only).'
  if ! bash "${ROOT_DIR}/scripts/manage-models.sh" reclaim-mazinb --dry-run; then
    wizard_warning 'Reclaim BLOCKED; no model files deleted. Review evidence and dependencies.'
    return 0
  fi
  wizard_yes_no 'Permanently delete ONLY this verified mazinb source checkpoint? / 원본 모델만 삭제합니까?' no ||
    return 0
  wizard_input confirmed 'Type DELETE_MAZINB_SOURCE_CHECKPOINT exactly / 정확히 입력' ''
  [[ "${confirmed}" == DELETE_MAZINB_SOURCE_CHECKPOINT ]] || {
    wizard_warning 'Exact approval mismatch; mazinb preserved.'
    return 0
  }
  if bash "${ROOT_DIR}/scripts/manage-models.sh" reclaim-mazinb --yes; then
    wizard_success 'Original mazinb checkpoint removed; exact post-check completed.'
    bash "${ROOT_DIR}/scripts/manage-models.sh" assets ||
      wizard_warning 'Post-reclaim model inventory unavailable.'
  else
    wizard_warning 'Reclaim FAILED or was BLOCKED. Inspect output; never retry without rechecking state.'
  fi
}

wizard_mazinb_docker_retire() {
  local confirmed
  wizard_header 'mazinb stopped Docker retirement / mazinb Docker 종료 컨테이너 정리'
  wizard_warning 'This is separate from source checkpoint deletion (already completed).'
  wizard_warning 'Exactly five stopped mazinb experiment containers are candidates; all other Docker objects stay.'
  wizard_warning 'Original container logs and metadata will be archived privately and SHA256-verified BEFORE any Docker removal.'
  wizard_warning 'Shared vLLM image, volumes, M1 journals, OrcaRouter and benchmark evidence are protected.'
  if ! bash "${ROOT_DIR}/scripts/manage-models.sh" retire-mazinb-containers --dry-run; then
    wizard_warning 'Docker cleanup BLOCKED; no containers removed. Review the evidence and exact IDs.'
    return 0
  fi
  wizard_yes_no 'Permanently delete ONLY these five stopped mazinb containers after log archival? / 5개만 제거합니까?' no ||
    return 0
  wizard_input confirmed 'Type DELETE_FIVE_MAZINB_CONTAINERS exactly / 정확히 입력' ''
  [[ "${confirmed}" == DELETE_FIVE_MAZINB_CONTAINERS ]] || {
    wizard_warning 'Exact approval mismatch; Docker containers preserved.'
    return 0
  }
  if bash "${ROOT_DIR}/scripts/manage-models.sh" retire-mazinb-containers --yes; then
    wizard_success 'Five exact mazinb containers removed; archive verified and other objects preserved.'
    bash "${ROOT_DIR}/scripts/manage-models.sh" assets ||
      wizard_warning 'Post-retirement model inventory unavailable.'
    wizard_mazinb_retirement_audit
  else
    wizard_warning 'Cleanup BLOCKED or PARTIAL; inspect output and saved archives before any retry.'
  fi
}

wizard_mazinb_retirement_audit() {
  wizard_header 'mazinb full post-removal audit / mazinb 서비스·프록시 포함 정리 검증'
  wizard_info 'Read-only: Docker archive, historical journal, dedicated system/user units, shared proxy/runtime and port 18889.'
  if python3 -B "${ROOT_DIR}/scripts/verify-mazinb-retirement.py"; then
    wizard_success 'mazinb-only Docker and service/proxy remnants absent; managed OrcaRouter shared assets preserved.'
  else
    wizard_warning 'INCONCLUSIVE/BLOCKED: inspect service, proxy and endpoint evidence; do not claim fully removed.'
  fi
}

wizard_model_menu() {
  local choice
  while true; do
    wizard_header 'Model management / 모델 관리'
    wizard_menu_option 1 'Supported profiles / 지원 프로필'
    wizard_menu_option 2 'Model assets / 자산 상태'
    wizard_menu_option 3 'Switch preview only / 전환 미리보기'
    wizard_menu_option 4 'Reclaim mazinb source checkpoint (evidence gated) / mazinb 원본 정리'
    wizard_menu_option 5 'Retire five mazinb Docker containers (archive first) / mazinb Docker 정리'
    wizard_menu_option 6 'Audit services, proxy, ports and Docker retirement (read-only) / 최종 정리 검증'
    wizard_menu_option 7 'Candidate Hub metadata (read-only) / 후보 모델 파일·용량 조사'
    wizard_menu_option 8 'OrcaRouter backend compatibility (read-only) / 백엔드 선택 가능 상태'
    wizard_menu_option 0 'Back / 이전'
    wizard_input choice 'Select / 선택' 0
    case "${choice}" in
      1) bash "${ROOT_DIR}/install.sh" --list-models ;;
      2) bash "${ROOT_DIR}/scripts/manage-models.sh" assets ;;
      3) wizard_profile_preview ;;
      4) wizard_mazinb_source_reclaim ;;
      5) wizard_mazinb_docker_retire ;;
      6) wizard_mazinb_retirement_audit ;;
      7) wizard_candidate_metadata_menu ;;
      8) wizard_orcarouter_backend_status ;;
      0|q|Q) return 0 ;;
      *) wizard_warning 'Invalid selection / 잘못된 선택입니다.' ;;
    esac
  done
}
