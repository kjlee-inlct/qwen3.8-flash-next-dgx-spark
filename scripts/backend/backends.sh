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

# OrcaRouter vLLM *image/runtime variant* is orthogonal to serving
# backend (vLLM versus planned SGLang) and to the model checkpoint.
# One stable source of status for the normal installation Wizard.
describe_orcarouter_vllm_variant() {
  case "$1" in
    v029)
      ORCA_VARIANT_STATUS=implemented
      ORCA_VARIANT_SELECTABLE=1
      ORCA_VARIANT_DESCRIPTION='Configured OrcaRouter v0.29 image (runtime health is separately verified)'
      ;;
    legacy)
      ORCA_VARIANT_STATUS=experimental
      ORCA_VARIANT_SELECTABLE=1
      ORCA_VARIANT_DESCRIPTION='Legacy CPU PLE image, fresh-install only'
      ;;
    official-arm64-c)
      ORCA_VARIANT_STATUS=unqualified
      ORCA_VARIANT_SELECTABLE=0
      ORCA_VARIANT_DESCRIPTION='Official ARM64 C: CPU-only CLI help failed during device auto-detection; options, PLE, KV16GiB and model READY unverified'
      ;;
    *)
      printf 'ERROR: unknown OrcaRouter vLLM runtime variant: %s\n' "$1" >&2
      return 2
      ;;
  esac
}
