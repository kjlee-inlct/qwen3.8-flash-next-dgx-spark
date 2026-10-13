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
  local selection trial
  wizard_header 'Past mazinb A/B evidence / 과거 A/B 실험 증거'
  wizard_menu_option 1 'Case A — 24 GiB / 실험 A'
  wizard_menu_option 2 'Case B — 16 GiB / 실험 B'
  wizard_menu_option 3 'Both A and B / A와 B 모두 확인'
  wizard_menu_option 0 'Back / 이전'
  wizard_input selection 'Select evidence / 증거 선택' 0
  case "${selection}" in
    1|A|a) selection=A ;;
    2|B|b) selection=B ;;
    3|AB|ab|both|BOTH) selection=AB ;;
    0|q|Q) return 0 ;;
    *) wizard_warning 'Invalid trial: choose 1=A, 2=B, 3=both or 0=back.'; return 0 ;;
  esac

  local -a cases=()
  if [[ "${selection}" == AB ]]; then
    cases=(A B)
  else
    cases=("${selection}")
  fi
  for trial in "${cases[@]}"; do
    printf '\nMAZINB_EVIDENCE_REVIEW=CASE_%s (historical / read-only)\n' "${trial}"
    if ! bash "${ROOT_DIR}/scripts/runtime/mazinb-kv-ab.sh" evidence "${trial}"; then
      wizard_warning "Case ${trial} evidence inspection failed; nothing modified."
    fi
  done
  wizard_info 'Docker exit=0 does not prove READY, protected host-stability or benchmark.'
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

  # The fixed B name belongs to the previous 2026-10-02 experiment on this host.
  # Do not require a 64-character predecessor acknowledgement before detecting
  # that fresh-B admission is impossible without a separately named M1 trial.
  if docker inspect --format '{{.Id}}' qwen38-mazinb-kv-b >/dev/null 2>&1; then
    wizard_warning 'Historical B container already exists. Preserve its identity, logs, and state.'
    wizard_warning 'Fresh B admission requires a DIFFERENT M1 candidate name; no deletion is authorized.'
    wizard_info 'Review menu 4 (status) and 5 -> 2 (B evidence).'
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

wizard_m1_confirm_old_id() {
  local old_id typed
  WIZARD_M1_EXPECTED_ID=""
  command -v docker >/dev/null 2>&1 || {
    wizard_warning 'Docker unavailable; M1 cancelled.'
    return 1
  }
  old_id="$(docker inspect --format '{{.Id}}' qwen38-flash-next 2>/dev/null)" || {
    wizard_warning 'Canonical predecessor cannot be inspected; M1 blocked.'
    return 1
  }
  [[ "${old_id}" =~ ^[a-f0-9]{64}$ ]] || {
    wizard_warning 'Invalid full predecessor Docker ID; M1 blocked.'
    return 1
  }
  printf 'M1_PROTECTED_PREDECESSOR_ID=%s\n' "${old_id}"
  wizard_input typed 'Re-enter full 64-hex predecessor Docker ID / 기존 Docker ID 재입력' ''
  [[ "${typed}" == "${old_id}" ]] || {
    wizard_warning 'Exact predecessor ID mismatch; M1 cancelled.'
    return 1
  }
  WIZARD_M1_EXPECTED_ID="${old_id}"
}

wizard_m1_authenticate_read_only_kernel() {
  if ! sudo -n true >/dev/null 2>&1; then
    wizard_yes_no 'Authenticate sudo for strict kernel RM evidence? / 읽기용 sudo 인증' no || return 1
    sudo -v || {
      wizard_warning 'Sudo authentication failed; M1 cancelled.'
      return 1
    }
  fi
}

wizard_m1_preflight() {
  wizard_header 'New isolated mazinb M1 / 새 M1 사전 검증'
  wizard_info 'Historical A/B and managed OrcaRouter are preserved.'
  wizard_m1_confirm_old_id || return 0
  wizard_m1_authenticate_read_only_kernel || return 0
  if ! python3 "${ROOT_DIR}/scripts/runtime/mazinb-m1.py" preflight \
      --expected-old-id "${WIZARD_M1_EXPECTED_ID}"; then
    wizard_warning 'M1 fresh admission BLOCKED; no model created or started.'
  fi
}

wizard_m1_run() {
  local consent
  wizard_header 'EXPERIMENTAL mazinb M1 live session / 실 DGX 모델 실행'
  wizard_warning 'This starts a NEW GPU-heavy mazinb Docker. Not previously qualified on the CURRENT DGX.'
  wizard_warning 'Protected managed Docker, old KV-A/B and model assets are NEVER deleted.'
  wizard_warning 'Terminal A stays open until STOP; Terminal B benchmarks only after M1_READY_FOR_BENCH.'
  wizard_yes_no 'Do you explicitly approve this NEW physical model load? / 새 모델 기동 승인' no ||
    return 0
  wizard_m1_confirm_old_id || return 0
  wizard_input consent 'Type exactly START_MAZINB_16G to confirm new GPU startup' ''
  [[ "${consent}" == START_MAZINB_16G ]] || {
    wizard_warning 'Live start confirmation mismatch; M1 cancelled.'
    return 0
  }
  wizard_m1_authenticate_read_only_kernel || return 0
  if ! QWEN38_M1_WIZARD_APPROVED=1 python3 "${ROOT_DIR}/scripts/runtime/mazinb-m1.py" run \
      --expected-old-id "${WIZARD_M1_EXPECTED_ID}"; then
    wizard_warning 'M1 failed or was stopped; inspect read-only M1 status/evidence and watchdog.'
  fi
}

wizard_benchmark_menu() {
  local choice
  while true; do
    wizard_header 'Benchmark / 벤치마크'
    wizard_info 'Old A/B are preserved. M1 is source-implemented; DGX live qualification is pending.'
    wizard_menu_option 1 'mazinb preflight (read-only) / 사전 점검'
    wizard_menu_option 2 'New mazinb B admission (read-only; blocked if B exists)'
    wizard_menu_option 3 'Report tools / 보고서 도구'
    wizard_menu_option 4 'Historical mazinb A/B status / 기존 실험 상태'
    wizard_menu_option 5 'Historical A/B evidence (1=A, 2=B, 3=both) / 기존 증거'
    wizard_menu_option 6 'mazinb M1 plan (no start) / 새로운 M1 계획'
    wizard_menu_option 7 'mazinb M1 status (no mutation) / M1 상태'
    wizard_menu_option 8 'mazinb M1 physical read-only preflight / 신규 M1 사전 검증'
    wizard_menu_option 9 'mazinb M1 experimental live start (explicit approval) / 새 모델 기동'
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
      6) python3 "${ROOT_DIR}/scripts/runtime/mazinb-m1.py" plan ||
           wizard_warning 'M1 plan unavailable.' ;;
      7) python3 "${ROOT_DIR}/scripts/runtime/mazinb-m1.py" status ||
           wizard_warning 'M1 status invalid; forensic investigation required.' ;;
      8) wizard_m1_preflight ;;
      9) wizard_m1_run ;;
      0|q|Q) return 0 ;;
      *) wizard_warning 'Invalid selection / 잘못된 선택입니다.' ;;
    esac
  done
}
