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
    hybrid-h10-ct-global-scale
}

describe_model_asset() {
  local profile="$1"
  MODEL_ASSET_PROFILE="$profile"
  MODEL_ASSET_CHECKPOINT=""
  MODEL_ASSET_CONTAINER=""
  MODEL_ASSET_IMAGE=""
  MODEL_ASSET_RETIRE_CHECKPOINT=0
  MODEL_ASSET_RETIRE_IMAGE=0
  MODEL_ASSET_DEPENDS_ON=""

  case "$profile" in
    orcarouter)
      MODEL_ASSET_CHECKPOINT="${SCRIPT_ROOT}/model"
      MODEL_ASSET_CONTAINER="qwen38-flash-next"
      MODEL_ASSET_IMAGE="vllm-skinny-tp1:v1"
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
      ;;
    hybrid-h4-all)
      MODEL_ASSET_CHECKPOINT="${HOME}/models/qwen3.8-h4-orca-all"
      MODEL_ASSET_CONTAINER="qwen38-h4-all-v029"
      MODEL_ASSET_IMAGE="vllm-orcarouter-v029:v1"
      MODEL_ASSET_RETIRE_CHECKPOINT=1
      MODEL_ASSET_DEPENDS_ON="hybrid-quant-layout"
      ;;
    hybrid-h5-neutral-input)
      MODEL_ASSET_CHECKPOINT="${HOME}/models/qwen3.8-h5-neutral-input-scale"
      MODEL_ASSET_CONTAINER="qwen38-h5-neutral-input-v029"
      MODEL_ASSET_IMAGE="vllm-orcarouter-v029:v1"
      MODEL_ASSET_RETIRE_CHECKPOINT=1
      MODEL_ASSET_DEPENDS_ON="hybrid-h4-all hybrid-quant-layout"
      ;;
    hybrid-h6-w4a16)
      MODEL_ASSET_CHECKPOINT="${HOME}/models/qwen3.8-h6-modelopt-w4a16"
      MODEL_ASSET_CONTAINER="qwen38-h6-w4a16-v029"
      MODEL_ASSET_IMAGE="vllm-orcarouter-v029:v1"
      MODEL_ASSET_RETIRE_CHECKPOINT=1
      MODEL_ASSET_DEPENDS_ON="hybrid-h5-neutral-input hybrid-h4-all hybrid-quant-layout"
      ;;
    hybrid-h7-group-metadata)
      MODEL_ASSET_CHECKPOINT="${HOME}/models/qwen3.8-h6-modelopt-w4a16"
      MODEL_ASSET_CONTAINER="qwen38-h7-group-metadata-v029"
      MODEL_ASSET_IMAGE="vllm-orcarouter-v029-h7-group:v1"
      MODEL_ASSET_RETIRE_IMAGE=1
      MODEL_ASSET_DEPENDS_ON="hybrid-h6-w4a16"
      ;;
    hybrid-h8-ct-block)
      MODEL_ASSET_CHECKPOINT="${SCRIPT_ROOT}/model"
      MODEL_ASSET_CONTAINER="qwen38-h8-ct-block-v029"
      MODEL_ASSET_IMAGE="vllm-orcarouter-v029-h8-ct-block:v1"
      MODEL_ASSET_RETIRE_IMAGE=1
      MODEL_ASSET_DEPENDS_ON="orcarouter"
      ;;
    hybrid-h9-ct-modelweight)
      MODEL_ASSET_CHECKPOINT="${SCRIPT_ROOT}/model"
      MODEL_ASSET_CONTAINER="qwen38-h9-ct-modelweight-v029"
      MODEL_ASSET_IMAGE="vllm-orcarouter-v029-h9-ct-modelweight:v1"
      MODEL_ASSET_RETIRE_IMAGE=0
      MODEL_ASSET_DEPENDS_ON="orcarouter"
      ;;
    hybrid-h10-ct-global-scale)
      MODEL_ASSET_CHECKPOINT="${SCRIPT_ROOT}/model"
      MODEL_ASSET_CONTAINER="qwen38-h10-ct-global-scale-v029"
      MODEL_ASSET_IMAGE="vllm-orcarouter-v029-h10-ct-global-scale:v1"
      MODEL_ASSET_RETIRE_IMAGE=1
      MODEL_ASSET_DEPENDS_ON="hybrid-h9-ct-modelweight orcarouter"
      ;;
    *)
      return 2
      ;;
  esac
}

model_asset_dependents() {
  local wanted="$1" profile dep
  while IFS= read -r profile; do
    describe_model_asset "$profile" || continue
    for dep in $MODEL_ASSET_DEPENDS_ON; do
      [[ "$dep" == "$wanted" ]] && printf '%s\n' "$profile"
    done
  done < <(model_asset_profiles)
}
