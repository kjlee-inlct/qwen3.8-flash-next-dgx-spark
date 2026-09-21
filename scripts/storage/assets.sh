#!/usr/bin/env bash
# Side-effect-free Docker asset registry for Qwen3.8 storage management.
#
# Classes:
#   stable      current default/runtime image family; never auto-pruned by class
#   baseline    reference/control image used for A/B validation
#   optional    installable optional profile image
#   experiment  disposable experiment image, removable only with --experiments

list_storage_images() {
  printf '%s\n' \
    vllm-skinny-tp1:v1 \
    vllm/vllm-openai:qwen38-flash-next-arm64-cu130 \
    vllm-nv-mixed:v2 \
    vllm-skinny-qsa-det:v1 \
    vllm-skinny-qsa-exact:v1 \
    vllm-skinny-stable-candidate:v1 \
    vllm-orcarouter-v029:v1 \
    vllm-orcarouter-v029-h7-group:v1 \
    vllm-orcarouter-v029-h8-ct-block:v1 \
    vllm-orcarouter-v029-h9-ct-modelweight:v1 \
    vllm-orcarouter-v029-h10-ct-global-scale:v1
}

describe_storage_image() {
  case "$1" in
    vllm-skinny-tp1:v1)
      STORAGE_IMAGE_CLASS="stable"
      STORAGE_IMAGE_DISPOSABLE=0
      STORAGE_IMAGE_DESCRIPTION="Primary OrcaRouter vLLM image"
      ;;
    vllm/vllm-openai:qwen38-flash-next-arm64-cu130)
      STORAGE_IMAGE_CLASS="baseline"
      STORAGE_IMAGE_DISPOSABLE=0
      STORAGE_IMAGE_DESCRIPTION="Stock vLLM control image for A/B validation"
      ;;
    vllm-nv-mixed:v2)
      STORAGE_IMAGE_CLASS="optional"
      STORAGE_IMAGE_DISPOSABLE=0
      STORAGE_IMAGE_DESCRIPTION="Optional NVIDIA profile image"
      ;;
    vllm-skinny-qsa-det:v1)
      STORAGE_IMAGE_CLASS="experiment"
      STORAGE_IMAGE_DISPOSABLE=1
      STORAGE_IMAGE_DESCRIPTION="Deterministic QSA kernel experiment"
      ;;
    vllm-skinny-qsa-exact:v1)
      STORAGE_IMAGE_CLASS="experiment"
      STORAGE_IMAGE_DISPOSABLE=1
      STORAGE_IMAGE_DESCRIPTION="Exact QSA top-k experiment"
      ;;
    vllm-skinny-stable-candidate:v1)
      STORAGE_IMAGE_CLASS="experiment"
      STORAGE_IMAGE_DISPOSABLE=1
      STORAGE_IMAGE_DESCRIPTION="OrcaRouter correctness candidate: exact QSA + GB10 FLA + guarded Mamba"
      ;;
    vllm-orcarouter-v029:v1)
      STORAGE_IMAGE_CLASS="experiment"
      STORAGE_IMAGE_DISPOSABLE=0
      STORAGE_IMAGE_DESCRIPTION="Shared vLLM v0.29 experiment base; keep"
      ;;
    vllm-orcarouter-v029-h7-group:v1)
      STORAGE_IMAGE_CLASS="experiment"
      STORAGE_IMAGE_DISPOSABLE=1
      STORAGE_IMAGE_DESCRIPTION="H7 ModelOpt GROUP metadata control"
      ;;
    vllm-orcarouter-v029-h8-ct-block:v1)
      STORAGE_IMAGE_CLASS="experiment"
      STORAGE_IMAGE_DISPOSABLE=1
      STORAGE_IMAGE_DESCRIPTION="H8 compressed-tensors BLOCK metadata control"
      ;;
    vllm-orcarouter-v029-h9-ct-modelweight:v1)
      STORAGE_IMAGE_CLASS="experiment"
      STORAGE_IMAGE_DISPOSABLE=0
      STORAGE_IMAGE_DESCRIPTION="H9 compressed-tensors scale-parameter control; H10 parent"
      ;;
    vllm-orcarouter-v029-h10-ct-global-scale:v1)
      STORAGE_IMAGE_CLASS="experiment"
      STORAGE_IMAGE_DISPOSABLE=0
      STORAGE_IMAGE_DESCRIPTION="Current H10 compressed-tensors global-scale control"
      ;;
    *)
      printf 'ERROR: unknown storage image: %s\n' "$1" >&2
      return 2
      ;;
  esac
}

list_disposable_storage_images() {
  local image
  while IFS= read -r image; do
    [[ -n "$image" ]] || continue
    describe_storage_image "$image" || return
    [[ "$STORAGE_IMAGE_DISPOSABLE" == 1 ]] && printf '%s\n' "$image"
  done < <(list_storage_images)
}
