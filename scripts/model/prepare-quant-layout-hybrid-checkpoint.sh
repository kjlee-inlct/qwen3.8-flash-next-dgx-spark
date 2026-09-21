#!/usr/bin/env bash
# Plan/build the full OrcaRouter -> mazinb quantization-layout isolation checkpoint.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_FILE="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark/install.env"
STATE_PARSER="${ROOT}/scripts/lib/state_file.py"
MODEL_REGISTRY="${ROOT}/scripts/model-profiles.sh"
TOOL="${ROOT}/scripts/model/prepare-quant-layout-hybrid-checkpoint.py"
OUTPUT="${HYBRID_QUANT_LAYOUT_MODEL_DIR:-$HOME/models/qwen3.8-hybrid-quant-layout}"
IMAGE="${HYBRID_BUILDER_IMAGE:-vllm-orcarouter-v029:v1}"
ACTION="${1:-plan}"
shift || true

FORCE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) FORCE=1 ;;
    -h|--help) ACTION=help ;;
    *) printf 'ERROR: unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
  shift
done

usage() {
  cat <<'EOF'
Usage:
  bash scripts/model/prepare-quant-layout-hybrid-checkpoint.sh plan
  bash scripts/model/prepare-quant-layout-hybrid-checkpoint.sh build [--force]

This H3 isolation keeps OrcaRouter outside quantized regions, overlays all 300
group-0 weights from mazinb BF16, replaces routed-expert packed tensors with
mazinb ModelOpt NVFP4 tensors, and switches quantization_config to mazinb.
MTP tensors remain from OrcaRouter.
EOF
}

load_install() {
  local parsed key value
  [[ -r "${STATE_FILE}" ]] || { printf 'ERROR: install manifest missing: %s\n' "${STATE_FILE}" >&2; exit 1; }
  parsed="$(mktemp)"
  trap 'rm -f -- "${parsed}"' RETURN
  python3 "${STATE_PARSER}" install-maintenance "${STATE_FILE}" >"${parsed}"
  BASE=""; BASE_REVISION=""; MODEL_PROFILE=""
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    case "${key}" in
      MODEL_DIR) BASE="${value}" ;;
      MODEL_REVISION) BASE_REVISION="${value}" ;;
      MODEL_PROFILE) MODEL_PROFILE="${value}" ;;
    esac
  done <"${parsed}"
  rm -f -- "${parsed}"
  trap - RETURN
  [[ "${MODEL_PROFILE}" == orcarouter ]] || { printf 'ERROR: installed model profile must be orcarouter\n' >&2; exit 1; }
  [[ -d "${BASE}" ]] || { printf 'ERROR: base model directory missing: %s\n' "${BASE}" >&2; exit 1; }
}

load_overlay() {
  # shellcheck source=scripts/model-profiles.sh
  source "${MODEL_REGISTRY}"
  load_download_profile mazinb
  OVERLAY="${PROFILE_MODEL_DIR}"
  [[ -d "${OVERLAY}" ]] || { printf 'ERROR: mazinb checkpoint missing: %s\n' "${OVERLAY}" >&2; exit 1; }
  local manifest="${OVERLAY}/.qwen38-model-manifest.json"
  [[ -r "${manifest}" ]] || { printf 'ERROR: mazinb manifest missing: %s\n' "${manifest}" >&2; exit 1; }
  OVERLAY_REVISION="$(python3 - "${manifest}" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
if d.get("status") != "complete" or not d.get("revision"):
    raise SystemExit("ERROR: mazinb manifest is incomplete")
print(d["revision"])
PY
)"
}

port_owner() {
  docker ps --filter publish=8888 --format '{{.Names}}' 2>/dev/null | paste -sd, -
}

load_install
load_overlay
docker image inspect "${IMAGE}" >/dev/null 2>&1 || { printf 'ERROR: builder image missing: %s\n' "${IMAGE}" >&2; exit 1; }

case "${ACTION}" in
  plan)
    exec docker run --pull=never --rm \
      --user "$(id -u):$(id -g)" \
      -e HOME=/tmp \
      -v "${BASE}:/base:ro" \
      -v "${OVERLAY}:/overlay:ro" \
      -v "${TOOL}:/tool.py:ro" \
      --entrypoint python3 \
      "${IMAGE}" \
      /tool.py plan \
      --base /base \
      --overlay /overlay \
      --output /output \
      --base-revision "${BASE_REVISION}" \
      --overlay-revision "${OVERLAY_REVISION}"
    ;;
  build)
    owner="$(port_owner)"
    if [[ -n "${owner}" ]]; then
      printf 'ERROR: stop the runtime before H3 build; port 8888 is owned by: %s\n' "${owner}" >&2
      exit 1
    fi
    mkdir -p "${OUTPUT}"
    args=(
      --pull=never --rm
      --user "$(id -u):$(id -g)"
      -e HOME=/tmp
      -v "${BASE}:/base:ro"
      -v "${OVERLAY}:/overlay:ro"
      -v "${OUTPUT}:/output"
      -v "${TOOL}:/tool.py:ro"
      --entrypoint python3
      "${IMAGE}"
      /tool.py build
      --base /base
      --overlay /overlay
      --output /output
      --base-revision "${BASE_REVISION}"
      --overlay-revision "${OVERLAY_REVISION}"
    )
    [[ "${FORCE}" == 1 ]] && args+=(--force)
    exec docker run "${args[@]}"
    ;;
  -h|--help|help) usage ;;
  *) usage >&2; exit 2 ;;
esac
