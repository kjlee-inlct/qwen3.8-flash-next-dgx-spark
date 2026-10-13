#!/usr/bin/env bash
# OrcaRouter image A/B information ONLY; no Docker/model/host mutation.
set -Eeuo pipefail
IMAGE=""
while (( $# )); do
  case "$1" in
    --installed-image) (( $# >= 2 )) || exit 2; IMAGE="$2"; shift 2 ;;
    --help|-h) printf 'Usage: orcarouter-ab-plan.sh --installed-image IMAGE\n'; exit 0 ;;
    *) printf 'ERROR unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done
case "${IMAGE}" in
  vllm-skinny-tp1:v1|vllm-orcarouter-v029:v1|vllm-orcarouter-v029-h38-decoder-scope:v1|vllm/vllm-openai:qwen38-flash-next-arm64-cu130) ;;
  *) printf 'ERROR unsupported OrcaRouter image: %s\n' "${IMAGE:-unset}" >&2; exit 2 ;;
esac
cat <<EOF
ORCAROUTER_AB_MODE=PLAN_ONLY
NO_RUNTIME_STARTED=YES
NO_MODEL_OR_DOCKER_MUTATION=YES
MODEL=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4
REVISION=c1209bda15a6bbc4c68b585e93d40c0d85f50306
INSTALLED_IMAGE=${IMAGE}
A_IMAGE=vllm-skinny-tp1:v1
A_PLE=cpu-offload
B_IMAGE=vllm-orcarouter-v029:v1
B_PLE=mmap
KV_CACHE_BYTES=17179869184
RUN_ORDER=SEQUENTIAL_NOT_SIMULTANEOUS
WIZARD_ISOLATED_START=NOT_IMPLEMENTED
API_IDENTITY=NOT_VERIFIED
HOST_RM_STABILITY=NOT_VERIFIED
BENCHMARK_STATUS=NOT_MEASURED
EOF
