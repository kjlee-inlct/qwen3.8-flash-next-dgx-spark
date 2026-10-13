#!/usr/bin/env bash
# No benchmark container start: isolated lifecycle/lock ownership is pending.
wizard_benchmark_menu() {
  local choice
  while true; do
    wizard_header 'Benchmark / 벤치마크'
    wizard_info 'Live benchmark is NOT_AVAILABLE until guarded isolated runtime is implemented.'
    wizard_menu_option 1 'mazinb preflight (no start) / 사전 점검'
    wizard_menu_option 2 'mazinb exact-ID admission (read-only) / 보호 자산 검증'
    wizard_menu_option 3 'Report tools / 보고서 도구'
    wizard_menu_option 0 'Back / 이전'
    wizard_input choice 'Select / 선택' 0
    case "${choice}" in
      1)
        bash "${ROOT_DIR}/scripts/runtime/mazinb-kv-ab.sh" preflight ||
          wizard_warning 'Preflight failed; no runtime started by this menu.' ;;
      2)
        local expected_old_id
        wizard_input expected_old_id 'Expected stopped predecessor Docker ID (64 hex)' ''
        if [[ -z "${expected_old_id}" ]]; then
          wizard_warning 'No Docker ID entered: cancelled.'
        else
          bash "${ROOT_DIR}/scripts/wizard/mazinb-admission.sh" --expected-old-id "${expected_old_id}" ||
            wizard_warning 'Read-only mazinb admission BLOCKED; no model was started.'
        fi
        ;;
      3)
        printf 'Report index: %s\n' "${ROOT_DIR}/docs/model-reports/README.md"
        printf 'Converter   : %s\n' "${ROOT_DIR}/scripts/benchmark/llama-benchy-report.py"
        printf 'Metrics     : NOT_MEASURED without actual DGX evidence.\n' ;;
      0|q|Q) return 0 ;;
      *) wizard_warning 'Invalid selection / 잘못된 선택입니다.' ;;
    esac
  done
}
