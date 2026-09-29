#!/usr/bin/env bash
# Build/validate the installer-facing OrcaRouter hybrid H6 checkpoint chain.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
IMAGE="${HYBRID_BUILDER_IMAGE:-vllm-orcarouter-v029:v1}"
BASE="${ORCAROUTER_MODEL_DIR:-$HOME/models/qwen3.8-flash-next-orcarouter}"
OVERLAY="${MAZINB_MODEL_DIR:-$HOME/models/qwen3.8-flash-next-mazinb}"
H3="${HYBRID_QUANT_LAYOUT_MODEL_DIR:-$HOME/models/qwen3.8-hybrid-quant-layout}"
H4="${H4_ORCA_ALL_MODEL_DIR:-$HOME/models/qwen3.8-h4-orca-all}"
H5="${H5_NEUTRAL_INPUT_MODEL_DIR:-$HOME/models/qwen3.8-h5-neutral-input-scale}"
OUTPUT="${H6_W4A16_MODEL_DIR:-$HOME/models/qwen3.8-h6-modelopt-w4a16}"
H3_TOOL="${ROOT}/scripts/model/prepare-quant-layout-hybrid-checkpoint.py"
H4_TOOL="${ROOT}/scripts/model/prepare-h4-expert-ab.py"
H5_TOOL="${ROOT}/scripts/model/prepare-h5-input-scale.py"
H6_TOOL="${ROOT}/scripts/model/prepare-h6-w4a16.py"
VALIDATOR="${ROOT}/scripts/model/validate-orcarouter-hybrid.py"
ACTION="${1:-validate}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/model/prepare-orcarouter-hybrid.sh build
  bash scripts/model/prepare-orcarouter-hybrid.sh validate
  bash scripts/model/prepare-orcarouter-hybrid.sh reuse-check

The installer-facing hybrid is the proven H6 ModelOpt W4A16 checkpoint:
  OrcaRouter + mazinb -> H3 quant-layout -> H4 orca-all -> H5 input_scale=1 -> H6 W4A16.

A complete H3 with pinned OrcaRouter/mazinb provenance can replace the mazinb
build-time source for reuse of H3 and later stages. Clean hosts without that H3
still require the pinned mazinb source checkpoint.

Existing complete stages are reused. A non-empty incomplete stage is never
deleted automatically; clean it explicitly after inspection before retrying.
EOF
}

model_revision() {
  python3 - "$1/.qwen38-model-manifest.json" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
data = json.loads(p.read_text(encoding="utf-8"))
if data.get("status") != "complete" or not data.get("revision"):
    raise SystemExit(1)
print(data["revision"])
PY
}

overlay_source_available() {
  [[ -r "${OVERLAY}/.qwen38-model-manifest.json" && -f "${OVERLAY}/model.safetensors.index.json" ]]
}

reuse_h3_ok() {
  python3 "${VALIDATOR}" \
    --h3-source-reuse-check \
    --h3-dir "${H3}" >/dev/null
}

run_validator() {
  local stage="${1:-h6}"
  local args=(
    --through "${stage}"
    --base-dir "${BASE}"
    --h3-dir "${H3}"
    --h4-dir "${H4}"
    --h5-dir "${H5}"
    --model-dir "${OUTPUT}"
  )
  if overlay_source_available; then
    args+=(--overlay-dir "${OVERLAY}")
  else
    args+=(--runtime-only)
  fi
  python3 "${VALIDATOR}" "${args[@]}"
}

stage_ok() {
  local path="$1" stage="$2"
  [[ -r "${path}/.qwen38-hybrid-manifest.json" ]] || return 1
  run_validator "${stage}" >/dev/null
}

require_source() {
  local path="$1" label="$2"
  [[ -r "${path}/.qwen38-model-manifest.json" && -f "${path}/model.safetensors.index.json" ]] || {
    printf 'ERROR: %s source checkpoint is missing or incomplete: %s\n' "${label}" "${path}" >&2
    exit 1
  }
}

require_empty_or_stage() {
  local path="$1" stage="$2" variant="$3"
  if stage_ok "${path}" "${stage}"; then
    printf 'reuse %-8s %s\n' "${variant}" "${path}"
    return 0
  fi
  if [[ -d "${path}" ]] && find "${path}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
    printf 'ERROR: generated stage is non-empty, invalid, or stale: %s\n' "${path}" >&2
    printf 'Inspect/remove that generated stage explicitly before retrying; it will not be overwritten.\n' >&2
    exit 1
  fi
  return 1
}

port_owner() {
  docker ps --filter publish=8888 --format '{{.Names}}' 2>/dev/null | paste -sd, -
}

validate_final() {
  run_validator h6
}

case "${ACTION}" in
  reuse-check)
    python3 "${VALIDATOR}" \
      --h3-source-reuse-check \
      --h3-dir "${H3}"
    ;;
  validate)
    validate_final
    ;;
  build)
    require_source "${BASE}" OrcaRouter
    if reuse_h3_ok; then
      printf 'reuse pinned mazinb provenance from H3: %s\n' "${H3}"
    else
      require_source "${OVERLAY}" mazinb
    fi
    if validate_final >/dev/null 2>&1; then
      printf 'reuse complete OrcaRouter hybrid H6 chain: %s\n' "${OUTPUT}"
      validate_final
      exit 0
    fi
    docker image inspect "${IMAGE}" >/dev/null 2>&1 || {
      printf 'ERROR: hybrid builder image is missing: %s\n' "${IMAGE}" >&2
      exit 1
    }
    owner="$(port_owner)"
    [[ -z "${owner}" ]] || {
      printf 'ERROR: stop the runtime before hybrid build; port 8888 is owned by: %s\n' "${owner}" >&2
      exit 1
    }
    BASE_REVISION="$(model_revision "${BASE}")"

    if reuse_h3_ok; then
      require_empty_or_stage "${H3}" h3 quant-layout-mazinb-experts
    else
      OVERLAY_REVISION="$(model_revision "${OVERLAY}")"
      if ! require_empty_or_stage "${H3}" h3 quant-layout-mazinb-experts; then
        mkdir -p "${H3}"
        docker run --pull=never --rm \
          --user "$(id -u):$(id -g)" -e HOME=/tmp \
          -v "${BASE}:/base:ro" -v "${OVERLAY}:/overlay:ro" -v "${H3}:/output" \
          -v "${H3_TOOL}:/tool.py:ro" --entrypoint python3 "${IMAGE}" \
          /tool.py build --base /base --overlay /overlay --output /output \
          --base-revision "${BASE_REVISION}" --overlay-revision "${OVERLAY_REVISION}"
      fi
    fi

    if ! require_empty_or_stage "${H4}" h4 h4-orca-all; then
      mkdir -p "${H4}"
      docker run --pull=never --rm         --user "$(id -u):$(id -g)" -e HOME=/tmp         -v "${BASE}:/base:ro" -v "${H3}:/h3:ro" -v "${H4}:/output"         -v "${H4_TOOL}:/tool.py:ro" --entrypoint python3 "${IMAGE}"         /tool.py build --variant orca-all --base /base --h3 /h3 --output /output
    fi

    if ! require_empty_or_stage "${H5}" h5 h5-neutral-input-scale; then
      mkdir -p "${H5}"
      docker run --pull=never --rm         --user "$(id -u):$(id -g)" -e HOME=/tmp         -v "${H4}:/h4-all:ro" -v "${H3}:/h3-model:ro" -v "${H5}:/output"         -v "${H5_TOOL}:/tool.py:ro" --entrypoint python3 "${IMAGE}"         /tool.py build --parent /h4-all --output /output
    fi

    if ! require_empty_or_stage "${OUTPUT}" h6 h6-modelopt-w4a16; then
      mkdir -p "${OUTPUT}"
      docker run --pull=never --rm         --user "$(id -u):$(id -g)" -e HOME=/tmp         -v "${H5}:/h5-parent:ro" -v "${OUTPUT}:/output"         -v "${H6_TOOL}:/tool.py:ro" --entrypoint python3 "${IMAGE}"         /tool.py build --parent /h5-parent --output /output
    fi

    validate_final
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
