#!/usr/bin/env bash
# Build or verify the managed OrcaRouter H38 decoder-scope runtime image.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
SCRIPTS_DIR="${ROOT}/scripts"
TARGET_IMAGE="vllm-orcarouter-v029-h38-decoder-scope:v1"
EXPECTED_SCOPE="decoder-v1"
ACTION="${1:-build}"

usage() {
  cat <<'EOF'
Usage: bash scripts/runtime/prepare-h38-image.sh [build|verify|plan]

build   Reuse an already valid target image, otherwise build the missing
        v0.29 -> H9 -> H10 -> H11 -> H12 -> H38 chain.
verify  Verify that the target image exists and carries the decoder-scope label.
plan    Print the immutable local image chain without changing Docker state.
EOF
}

image_exists() {
  docker image inspect "$1" >/dev/null 2>&1
}

verify_target() {
  local scope
  image_exists "${TARGET_IMAGE}" || {
    printf 'ERROR: H38 managed image is missing: %s\n' "${TARGET_IMAGE}" >&2
    return 1
  }
  scope="$(docker image inspect --format '{{ index .Config.Labels "qwen38.h38scope" }}' "${TARGET_IMAGE}" 2>/dev/null || true)"
  [[ "${scope}" == "${EXPECTED_SCOPE}" ]] || {
    printf 'ERROR: H38 image label mismatch: image=%s qwen38.h38scope=%s expected=%s\n' "${TARGET_IMAGE}" "${scope:-missing}" "${EXPECTED_SCOPE}" >&2
    return 1
  }
  printf 'H38 managed image verified: %s (qwen38.h38scope=%s)\n' "${TARGET_IMAGE}" "${scope}"
}

print_plan() {
  cat <<'EOF'
vllm-orcarouter-v029:v1 <- Dockerfile.v029-orcarouter
vllm-orcarouter-v029-h9-ct-modelweight:v1 <- Dockerfile.v029-h9-ct-modelweight-scale
vllm-orcarouter-v029-h10-ct-global-scale:v1 <- Dockerfile.v029-h10-ct-global-scale
vllm-orcarouter-v029-h11-ct-packed-modelweight:v1 <- Dockerfile.v029-h11-ct-packed-modelweight
vllm-orcarouter-v029-h12-ct-postload-preserve:v1 <- Dockerfile.v029-h12-ct-postload-preserve
vllm-orcarouter-v029-h38-decoder-scope:v1 <- Dockerfile.v029-h38-decoder-scope
EOF
}

build_stage() {
  local image="$1" dockerfile="$2"
  if image_exists "${image}"; then
    printf 'Reusing image: %s\n' "${image}"
    return 0
  fi
  [[ -r "${SCRIPTS_DIR}/${dockerfile}" ]] || {
    printf 'ERROR: Dockerfile is missing: %s\n' "${SCRIPTS_DIR}/${dockerfile}" >&2
    return 1
  }
  printf 'Building image: %s (%s)\n' "${image}" "${dockerfile}"
  docker build -t "${image}" -f "${SCRIPTS_DIR}/${dockerfile}" "${SCRIPTS_DIR}"
}

case "${ACTION}" in
  plan)
    print_plan
    ;;
  verify)
    command -v docker >/dev/null 2>&1 || { printf 'ERROR: docker is required\n' >&2; exit 1; }
    verify_target
    ;;
  build)
    command -v docker >/dev/null 2>&1 || { printf 'ERROR: docker is required\n' >&2; exit 1; }
    if image_exists "${TARGET_IMAGE}"; then
      verify_target
      exit 0
    fi
    build_stage "vllm-orcarouter-v029:v1" "Dockerfile.v029-orcarouter"
    build_stage "vllm-orcarouter-v029-h9-ct-modelweight:v1" "Dockerfile.v029-h9-ct-modelweight-scale"
    build_stage "vllm-orcarouter-v029-h10-ct-global-scale:v1" "Dockerfile.v029-h10-ct-global-scale"
    build_stage "vllm-orcarouter-v029-h11-ct-packed-modelweight:v1" "Dockerfile.v029-h11-ct-packed-modelweight"
    build_stage "vllm-orcarouter-v029-h12-ct-postload-preserve:v1" "Dockerfile.v029-h12-ct-postload-preserve"
    build_stage "${TARGET_IMAGE}" "Dockerfile.v029-h38-decoder-scope"
    verify_target
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
