#!/usr/bin/env bash
# Candidate checkpoint investigations: remote metadata and read-only source audit.
# This menu NEVER admits a candidate for install, downloads weights, or starts GPU/Docker.

wizard_catplusplus_metadata_check() {
  local mode="${1:-summary}"
  local -a arguments=()
  if [[ "${mode}" == full ]]; then
    arguments+=(--json)
  fi
  wizard_header 'catplusplus pinned Hub inventory / 고정 리비전 메타데이터'
  wizard_info 'Research-only: fixed revision 3251fd8afbd08f76368a9bfa71132d9aef364813.'
  wizard_info 'Hugging Face JSON only; no safetensors payload, GPU start, or Docker/service changes.'
  if python3 -B "${ROOT_DIR}/scripts/model/inspect_catplusplus_metadata.py" "${arguments[@]}"; then
    wizard_success 'Metadata inventory complete; checkpoint tensor/loader/GPU support NOT verified.'
  else
    wizard_warning 'Metadata inventory failed or incomplete; DO NOT infer model incompatibility or download weights.'
  fi
  wizard_warning 'catplusplus remains research-only and NOT installable.'
}

wizard_lychee888_source_gate() {
  wizard_header 'lychee888 FP8-PLE source gate / 소스 호환성 점검'
  wizard_info 'Fixed HF revision 1b3c3cedc14fb3bee4294dea5e3515af74b8268a; pinned JSON + local source only.'
  wizard_info 'Rechecks L0 structure as a dependency. No safetensors payload, Docker build, GPU start or service changes.'
  if python3 -B "${ROOT_DIR}/scripts/model/assess_lychee888_loader.py"; then
    wizard_warning 'SOURCE inspection completed. FP8-PLE loader and single-GB10 TP=1 are NOT qualified.'
  else
    wizard_warning 'SOURCE inspection FAILED or incomplete. Do not infer runtime compatibility or installability.'
  fi
  wizard_warning 'lychee888 remains planned and NOT installable.'
}

wizard_installed_ple_source_audit() {
  wizard_header 'Existing image PLE loader source / 설치 이미지 PLE 소스 점검'
  wizard_info 'Read-only Docker inspect/copy from the existing managed container; a PLE bind source may be read locally.'
  wizard_info 'No container creation, start, GPU use, downloads, model data or service changes.'
  if python3 -B "${ROOT_DIR}/scripts/model/audit_installed_ple_image.py"; then
    wizard_warning 'Installed image SOURCE signatures captured; this is NOT a lychee888 loader/TP=1 qualification.'
  else
    wizard_warning 'Installed image source is INCONCLUSIVE or unavailable; NO managed resources were changed.'
  fi
  wizard_warning 'lychee888 remains NOT installable. Runtime adapter and memory admission are still blocked.'
}

wizard_candidate_metadata_menu() {
  local choice
  while true; do
    wizard_header 'Candidate metadata / 후보 모델 메타데이터 조사'
    wizard_info 'No checkpoint installation, large download, GPU execution, or Docker mutation.'
    wizard_info 'lychee888 L0 history is preserved; source gate revalidates pinned JSON without weights.'
    wizard_menu_option 1 'catplusplus pinned inventory summary / 파일·용량 요약'
    wizard_menu_option 2 'catplusplus full JSON file inventory / 전체 파일 목록 출력'
    wizard_menu_option 3 'lychee888 pinned FP8-PLE source gate / FP8-PLE 로더 소스 점검'
    wizard_menu_option 4 'Existing image PLE loader source (read-only) / 기존 이미지 PLE 소스 검사'
    wizard_menu_option 0 'Back / 이전'
    wizard_input choice 'Select / 선택' 0
    case "${choice}" in
      1) wizard_catplusplus_metadata_check summary ;;
      2) wizard_catplusplus_metadata_check full ;;
      3) wizard_lychee888_source_gate ;;
      4) wizard_installed_ple_source_audit ;;
      0|q|Q) return 0 ;;
      *) wizard_warning 'Invalid selection / 잘못된 선택입니다.' ;;
    esac
  done
}
