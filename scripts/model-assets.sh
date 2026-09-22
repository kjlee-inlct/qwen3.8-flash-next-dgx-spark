#!/usr/bin/env bash
# Logical model/profile asset registry.
# Sourced by manage-models.sh. No side effects.

model_asset_profiles() {
  printf '%s\n' \
    orcarouter \
    mazinb \
    hybrid-quant-layout \
    hybrid-h4-all \
    hybrid-h5-neutral-input \
    hybrid-h6-w4a16 \
    hybrid-h7-group-metadata \
    hybrid-h8-ct-block \
    hybrid-h9-ct-modelweight \
    hybrid-h10-ct-global-scale \
    hybrid-h11-ct-packed-modelweight \
    hybrid-h12-ct-postload-preserve \
    hybrid-h13-ct-input-scale \
    hybrid-h14-ct-input-scale-postload \
    hybrid-h15-mtp-off
}

describe_model_asset() {
  local profile="$1"
  MODEL_ASSET_PROFILE="$profile"
  MODEL_ASSET_CHECKPOINT=""
  MODEL_ASSET_CONTAINER=""
  MODEL_ASSET_IMAGE=""
  MODEL_ASSET_RETIRE_CHECKPOINT=0
  MODEL_ASSET_RETIRE_IMAGE=0
  MODEL_ASSET_CHECKPOINT_DEPENDS_ON=""
  MODEL_ASSET_IMAGE_DEPENDS_ON=""

  case "$profile" in
    orcarouter)
      MODEL_ASSET_CHECKPOINT="${SCRIPT_ROOT}/model"
      MODEL_ASSET_CONTAINER="qwen38-flash-next"
      MODEL_ASSET_IMAGE="vllm-skinny-tp1:v1"
      MODEL_ASSET_RETIRE_IMAGE=1
      ;;
    mazinb)
      MODEL_ASSET_CHECKPOINT="${HOME}/models/qwen3.8-flash-next-mazinb"
      MODEL_ASSET_CONTAINER="qwen38-mazinb-v029"
      MODEL_ASSET_IMAGE="vllm-orcarouter-v029:v1"
      MODEL_ASSET_RETIRE_CHECKPOINT=1
      ;;
    hybrid-quant-layout)
      MODEL_ASSET_CHECKPOINT="${HOME}/models/qwen3.8-hybrid-quant-layout"
      MODEL_ASSET_CONTAINER="qwen38-hybrid-quant-layout-v029"
      MODEL_ASSET_IMAGE="vllm-orcarouter-v029:v1"
      MODEL_ASSET_RETIRE_CHECKPOINT=1
      MODEL_ASSET_CHECKPOINT_DEPENDS_ON="orcarouter"
      ;;
    hybrid-h4-all)
      MODEL_ASSET_CHECKPOINT="${HOME}/models/qwen3.8-h4-orca-all"
      MODEL_ASSET_CONTAINER="qwen38-h4-all-v029"
      MODEL_ASSET_IMAGE="vllm-orcarouter-v029:v1"
      MODEL_ASSET_RETIRE_CHECKPOINT=1
      MODEL_ASSET_CHECKPOINT_DEPENDS_ON="hybrid-quant-layout orcarouter"
      ;;
    hybrid-h5-neutral-input)
      MODEL_ASSET_CHECKPOINT="${HOME}/models/qwen3.8-h5-neutral-input-scale"
      MODEL_ASSET_CONTAINER="qwen38-h5-neutral-input-v029"
      MODEL_ASSET_IMAGE="vllm-orcarouter-v029:v1"
      MODEL_ASSET_RETIRE_CHECKPOINT=1
      MODEL_ASSET_CHECKPOINT_DEPENDS_ON="hybrid-h4-all hybrid-quant-layout orcarouter"
      ;;
    hybrid-h6-w4a16)
      MODEL_ASSET_CHECKPOINT="${HOME}/models/qwen3.8-h6-modelopt-w4a16"
      MODEL_ASSET_CONTAINER="qwen38-h6-w4a16-v029"
      MODEL_ASSET_IMAGE="vllm-orcarouter-v029:v1"
      MODEL_ASSET_RETIRE_CHECKPOINT=1
      MODEL_ASSET_CHECKPOINT_DEPENDS_ON="hybrid-h5-neutral-input hybrid-h4-all hybrid-quant-layout orcarouter"
      ;;
    hybrid-h7-group-metadata)
      MODEL_ASSET_CHECKPOINT="${HOME}/models/qwen3.8-h6-modelopt-w4a16"
      MODEL_ASSET_CONTAINER="qwen38-h7-group-metadata-v029"
      MODEL_ASSET_IMAGE="vllm-orcarouter-v029-h7-group:v1"
      MODEL_ASSET_RETIRE_IMAGE=1
      MODEL_ASSET_CHECKPOINT_DEPENDS_ON="hybrid-h6-w4a16"
      ;;
    hybrid-h8-ct-block)
      MODEL_ASSET_CHECKPOINT="${SCRIPT_ROOT}/model"
      MODEL_ASSET_CONTAINER="qwen38-h8-ct-block-v029"
      MODEL_ASSET_IMAGE="vllm-orcarouter-v029-h8-ct-block:v1"
      MODEL_ASSET_RETIRE_IMAGE=1
      MODEL_ASSET_CHECKPOINT_DEPENDS_ON="orcarouter"
      ;;
    hybrid-h9-ct-modelweight)
      MODEL_ASSET_CHECKPOINT="${SCRIPT_ROOT}/model"
      MODEL_ASSET_CONTAINER="qwen38-h9-ct-modelweight-v029"
      MODEL_ASSET_IMAGE="vllm-orcarouter-v029-h9-ct-modelweight:v1"
      MODEL_ASSET_RETIRE_IMAGE=1
      MODEL_ASSET_CHECKPOINT_DEPENDS_ON="orcarouter"
      ;;
    hybrid-h10-ct-global-scale)
      MODEL_ASSET_CHECKPOINT="${SCRIPT_ROOT}/model"
      MODEL_ASSET_CONTAINER="qwen38-h10-ct-global-scale-v029"
      MODEL_ASSET_IMAGE="vllm-orcarouter-v029-h10-ct-global-scale:v1"
      MODEL_ASSET_RETIRE_IMAGE=1
      MODEL_ASSET_CHECKPOINT_DEPENDS_ON="orcarouter"
      MODEL_ASSET_IMAGE_DEPENDS_ON="hybrid-h9-ct-modelweight"
      ;;
    hybrid-h11-ct-packed-modelweight)
      MODEL_ASSET_CHECKPOINT="${SCRIPT_ROOT}/model"
      MODEL_ASSET_CONTAINER="qwen38-h11-ct-packed-modelweight-v029"
      MODEL_ASSET_IMAGE="vllm-orcarouter-v029-h11-ct-packed-modelweight:v1"
      MODEL_ASSET_RETIRE_IMAGE=1
      MODEL_ASSET_CHECKPOINT_DEPENDS_ON="orcarouter"
      MODEL_ASSET_IMAGE_DEPENDS_ON="hybrid-h10-ct-global-scale"
      ;;
    hybrid-h12-ct-postload-preserve)
      MODEL_ASSET_CHECKPOINT="${SCRIPT_ROOT}/model"
      MODEL_ASSET_CONTAINER="qwen38-h12-ct-postload-preserve-v029"
      MODEL_ASSET_IMAGE="vllm-orcarouter-v029-h12-ct-postload-preserve:v1"
      MODEL_ASSET_RETIRE_IMAGE=1
      MODEL_ASSET_CHECKPOINT_DEPENDS_ON="orcarouter"
      MODEL_ASSET_IMAGE_DEPENDS_ON="hybrid-h11-ct-packed-modelweight"
      ;;
    hybrid-h13-ct-input-scale)
      MODEL_ASSET_CHECKPOINT="${SCRIPT_ROOT}/model"
      MODEL_ASSET_CONTAINER="qwen38-h13-ct-input-scale-v029"
      MODEL_ASSET_IMAGE="vllm-orcarouter-v029-h13-ct-input-scale:v1"
      MODEL_ASSET_RETIRE_IMAGE=1
      MODEL_ASSET_CHECKPOINT_DEPENDS_ON="orcarouter"
      MODEL_ASSET_IMAGE_DEPENDS_ON="hybrid-h12-ct-postload-preserve"
      ;;
    hybrid-h14-ct-input-scale-postload)
      MODEL_ASSET_CHECKPOINT="${SCRIPT_ROOT}/model"
      MODEL_ASSET_CONTAINER="qwen38-h14-ct-input-scale-postload-v029"
      MODEL_ASSET_IMAGE="vllm-orcarouter-v029-h14-ct-input-scale-postload:v1"
      MODEL_ASSET_RETIRE_IMAGE=1
      MODEL_ASSET_CHECKPOINT_DEPENDS_ON="orcarouter"
      MODEL_ASSET_IMAGE_DEPENDS_ON="hybrid-h12-ct-postload-preserve"
      ;;
    hybrid-h15-mtp-off)
      MODEL_ASSET_CHECKPOINT="${SCRIPT_ROOT}/model"
      MODEL_ASSET_CONTAINER="qwen38-h15-mtp-off-v029"
      MODEL_ASSET_IMAGE="vllm-orcarouter-v029-h14-ct-input-scale-postload:v1"
      MODEL_ASSET_RETIRE_IMAGE=0
      MODEL_ASSET_CHECKPOINT_DEPENDS_ON="orcarouter"
      MODEL_ASSET_IMAGE_DEPENDS_ON="hybrid-h14-ct-input-scale-postload"
      ;;
    *)
      return 2
      ;;
  esac
}

model_asset_dependents() {
  local wanted="$1" kind="$2" profile dep deps
  while IFS= read -r profile; do
    describe_model_asset "$profile" || continue
    case "$kind" in
      checkpoint) deps="$MODEL_ASSET_CHECKPOINT_DEPENDS_ON" ;;
      image) deps="$MODEL_ASSET_IMAGE_DEPENDS_ON" ;;
      *) return 2 ;;
    esac
    for dep in $deps; do
      [[ "$dep" == "$wanted" ]] && printf '%s\n' "$profile"
    done
  done < <(model_asset_profiles)
}
