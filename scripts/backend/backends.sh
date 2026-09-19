#!/usr/bin/env bash
# Side-effect-free serving backend registry.
#
# Keep backend capability separate from checkpoint/model profiles. The installer currently
# implements only vLLM. SGLang is intentionally registered as planned rather than selectable
# so the stable OrcaRouter path cannot accidentally enter an unqualified runtime.

list_serving_backends() {
  printf '%s\n' vllm
}

list_planned_serving_backends() {
  printf '%s\n' sglang
}

describe_serving_backend() {
  case "$1" in
    vllm)
      BACKEND_STATUS="stable"
      BACKEND_INSTALLABLE=1
      BACKEND_DESCRIPTION="Current qualified DGX Spark backend"
      ;;
    sglang)
      BACKEND_STATUS="planned"
      BACKEND_INSTALLABLE=0
      BACKEND_DESCRIPTION="Planned optional backend; runtime/lifecycle integration not implemented yet"
      ;;
    *)
      printf 'ERROR: unknown serving backend: %s\n' "$1" >&2
      return 2
      ;;
  esac
}

print_serving_backends() {
  local backend
  printf '%-10s %-12s %-11s %s\n' BACKEND STATUS INSTALLABLE DESCRIPTION
  for backend in vllm sglang; do
    describe_serving_backend "${backend}" || return
    printf '%-10s %-12s %-11s %s\n' \
      "${backend}" "${BACKEND_STATUS}" "${BACKEND_INSTALLABLE}" "${BACKEND_DESCRIPTION}"
  done
}
