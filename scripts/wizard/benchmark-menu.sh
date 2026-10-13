#!/usr/bin/env bash
# Wizard-only operator workflow for mazinb evidence and read-only admission.
# Protected model startup/benchmark remains a separate M1 lifecycle task.

wizard_mazinb_status() {
  wizard_header 'mazinb historical experiments / 과거 실험'
  bash "${ROOT_DIR}/scripts/runtime/mazinb-kv-ab.sh" status ||
    wizard_warning 'Read-only mazinb status unavailable / 상태 조회 실패'
  wizard_info 'Existing trial containers/evidence are preserved; no cleanup is offered.'
}

wizard_mazinb_evidence() {
  local trial
  wizard_input trial 'Review case A or B / 확인할 실험 A 또는 B' A
  case "${trial}" in
    A|a|B|b)
      bash "${ROOT_DIR}/scripts/runtime/mazinb-kv-ab.sh" evidence "${trial^^}" ||
        wizard_warning 'Evidence inspection failed; nothing was modified.'
      ;;
    *) wizard_warning 'Invalid trial: choose A or B.' ;;
  esac
}

wizard_mazinb_admission() {
  local predecessor_id acknowledged_id trial_a_id reviewed_a_id="" trial_a_state=""
  wizard_header 'mazinb isolated B admission / B 실험 사전 검증'
  wizard_info 'This only verifies permission/readiness to test; it does NOT start mazinb.'
  wizard_info 'The old managed container, prior A evidence and immutable releases remain untouched.'
  if ! command -v docker >/dev/null 2>&1; then
    wizard_warning 'Docker missing. Admission cancelled.'
    return 0
  fi

  predecessor_id="$(docker inspect --format '{{.Id}}' qwen38-flash-next 2>/dev/null)" || {
    wizard_warning 'Managed predecessor not inspectable. Admission cancelled.'
    return 0
  }
  [[ "${predecessor_id}" =~ ^[a-f0-9]{64}$ ]] || {
    wizard_warning 'Invalid predecessor Docker identity; admission cancelled.'
    return 0
  }
  printf 'Stopped predecessor (verify before continuing): %s\n' "${predecessor_id}"
  wizard_input acknowledged_id 'Re-enter complete predecessor Docker ID / 기존 Docker ID 확인' ''
  [[ "${acknowledged_id}" == "${predecessor_id}" ]] || {
    wizard_warning 'Docker ID mismatch or cancelled; no action taken.'
    return 0
  }

  if docker inspect --format '{{.Id}}' qwen38-mazinb-kv-b >/dev/null 2>&1; then
    wizard_warning 'Prior B exists: preserve/review with menu 4 or 5 before another B run.'
    return 0
  fi
  if docker inspect --format '{{.Id}}' qwen38-mazinb-kv-a >/dev/null 2>&1; then
    trial_a_state="$(docker inspect --format '{{.Id}}|{{.Name}}|{{.State.Status}}|{{.State.Running}}' qwen38-mazinb-kv-a 2>/dev/null)" || {
      wizard_warning 'Cannot inspect historical A. Admission cancelled.'
      return 0
    }
    local trial_name trial_status trial_running
    IFS='|' read -r trial_a_id trial_name trial_status trial_running <<<"${trial_a_state}"
    printf 'Historical A: id=%s name=%s status=%s running=%s\n' \
      "${trial_a_id}" "${trial_name}" "${trial_status}" "${trial_running}"
    [[ "${trial_name}" == /qwen38-mazinb-kv-a &&
       "${trial_status}" == exited && "${trial_running}" == false ]] || {
      wizard_warning 'Historical A is not safely stopped. Admission cancelled.'
      return 0
    }
    wizard_yes_no 'Review preserved A evidence before continuing? / A 실험 증거를 확인합니까?' no ||
      return 0
    if ! bash "${ROOT_DIR}/scripts/runtime/mazinb-kv-ab.sh" evidence A; then
      wizard_warning 'Cannot read A evidence. Admission cancelled.'
      return 0
    fi
    wizard_info 'Acknowledgement DOES NOT delete or change historical A.'
    wizard_input reviewed_a_id 'Re-enter FULL historical A Docker ID to acknowledge review / A ID 재입력' ''
    [[ "${reviewed_a_id}" == "${trial_a_id}" ]] || {
      wizard_warning 'Historical A identity not acknowledged. Admission cancelled.'
      return 0
    }
  fi
  wizard_yes_no 'Run READ-ONLY mazinb admission now? / 읽기 전용 검증을 실행합니까?' no ||
    return 0
  if ! sudo -n true >/dev/null 2>&1; then
    wizard_yes_no 'Acquire sudo credentials for kernel-log read-only preflight? / sudo 인증을 진행합니까?' no ||
      return 0
    sudo -v || {
      wizard_warning 'Sudo credentials unavailable. Admission cancelled.'
      return 0
    }
  fi
  local -a args=(--expected-old-id "${predecessor_id}")
  if [[ -n "${reviewed_a_id}" ]]; then
    args+=(--reviewed-trial-a-id "${reviewed_a_id}")
  fi
  if bash "${ROOT_DIR}/scripts/wizard/mazinb-admission.sh" "${args[@]}"; then
    wizard_success 'READ_ONLY admission passed; model NOT STARTED, no benchmark performed.'
    wizard_info 'Protected M1 candidate start through Wizard remains NOT IMPLEMENTED.'
  else
    wizard_warning 'Admission BLOCKED. Preserve evidence; do not delete assets to bypass it.'
  fi
}

wizard_benchmark_menu() {
  local choice
  while true; do
    wizard_header 'Benchmark / 벤치마크'
    wizard_info 'mazinb historical evidence and admission are read-only. Actual start awaits M1.'
    wizard_menu_option 1 'mazinb preflight (read-only) / 사전 점검'
    wizard_menu_option 2 'mazinb B guarded admission (read-only) / 검증'
    wizard_menu_option 3 'Report tools / 보고서 도구'
    wizard_menu_option 4 'Historical mazinb A/B status / 기존 실험 상태'
    wizard_menu_option 5 'Historical A/B evidence / 기존 실험 증거'
    wizard_menu_option 0 'Back / 이전'
    wizard_input choice 'Select / 선택' 0
    case "${choice}" in
      1)
        bash "${ROOT_DIR}/scripts/runtime/mazinb-kv-ab.sh" preflight ||
          wizard_warning 'Preflight failed; no runtime started by this menu.' ;;
      2) wizard_mazinb_admission ;;
      3)
        printf 'Report index: %s\n' "${ROOT_DIR}/docs/model-reports/README.md"
        printf 'Converter   : %s\n' "${ROOT_DIR}/scripts/benchmark/llama-benchy-report.py"
        printf 'Metrics     : NOT_MEASURED without actual DGX evidence.\n' ;;
      4) wizard_mazinb_status ;;
      5) wizard_mazinb_evidence ;;
      0|q|Q) return 0 ;;
      *) wizard_warning 'Invalid selection / 잘못된 선택입니다.' ;;
    esac
  done
}
