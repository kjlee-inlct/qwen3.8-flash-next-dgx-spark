#!/usr/bin/env bash
# Candidate checkpoint investigations. Only remote JSON metadata is requested.
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

wizard_candidate_metadata_menu() {
  local choice
  while true; do
    wizard_header 'Candidate metadata / 후보 모델 메타데이터 조사'
    wizard_info 'No checkpoint installation, large download, GPU execution, or Docker mutation.'
    wizard_info 'lychee888 existing pinned L0 evidence is preserved; this menu does not repeat that test.'
    wizard_menu_option 1 'catplusplus pinned inventory summary / 파일·용량 요약'
    wizard_menu_option 2 'catplusplus full JSON file inventory / 전체 파일 목록 출력'
    wizard_menu_option 0 'Back / 이전'
    wizard_input choice 'Select / 선택' 0
    case "${choice}" in
      1) wizard_catplusplus_metadata_check summary ;;
      2) wizard_catplusplus_metadata_check full ;;
      0|q|Q) return 0 ;;
      *) wizard_warning 'Invalid selection / 잘못된 선택입니다.' ;;
    esac
  done
}
