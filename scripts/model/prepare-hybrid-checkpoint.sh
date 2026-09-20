#!/usr/bin/env bash
# Plan/build the residual-BF16 OrcaRouter/mazinb hybrid without host HF/Python deps.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_FILE="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark/install.env"
STATE_PARSER="${ROOT}/scripts/lib/state_file.py"
TOOL="${ROOT}/scripts/model/prepare-hybrid-checkpoint.py"
OVERLAY="${HYBRID_OVERLAY_DIR:-$HOME/models/qwen3.8-flash-next-mazinb}"
OUTPUT="${HYBRID_OUTPUT_DIR:-$HOME/models/qwen3.8-hybrid-residual-bf16}"
IMAGE="${HYBRID_BUILDER_IMAGE:-vllm-orcarouter-v029:v1}"
ACTION="${1:-plan}"
shift || true

FORCE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) FORCE=1 ;;
    -h|--help)
      ACTION=help
      ;;
    *)
      printf 'ERROR: unknown argument: %s\n' "$1" >&2
      exit 2
      ;;
  esac
  shift
done

usage() {
  cat <<'EOF'
Usage:
  bash scripts/model/prepare-hybrid-checkpoint.sh plan
  bash scripts/model/prepare-hybrid-checkpoint.sh build [--force]

Environment overrides:
  HYBRID_OVERLAY_DIR   mazinb checkpoint directory
  HYBRID_OUTPUT_DIR    hybrid output directory
  HYBRID_BUILDER_IMAGE image containing torch+safetensors

The build is local/experimental only. It never edits the installed OrcaRouter
checkpoint or the mazinb candidate. A build requires the shared API runtime to
be stopped so RAM is available for shard rewriting.
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

overlay_revision() {
  python3 - "${OVERLAY}/.qwen38-model-manifest.json" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
if not p.is_file():
    raise SystemExit("ERROR: mazinb model manifest is missing")
data = json.loads(p.read_text(encoding="utf-8"))
if data.get("status") != "complete" or not data.get("revision"):
    raise SystemExit("ERROR: mazinb model manifest is incomplete")
print(data["revision"])
PY
}

port_owner() {
  docker ps --filter publish=8888 --format '{{.Names}}' 2>/dev/null | paste -sd, -
}

load_install
OVERLAY_REVISION="$(overlay_revision)"

case "${ACTION}" in
  plan)
    exec python3 "${TOOL}" plan       --base "${BASE}"       --overlay "${OVERLAY}"       --output "${OUTPUT}"       --base-revision "${BASE_REVISION}"       --overlay-revision "${OVERLAY_REVISION}"
    ;;
  build)
    owner="$(port_owner)"
    if [[ -n "${owner}" ]]; then
      printf 'ERROR: stop the runtime before hybrid build; port 8888 is owned by: %s\n' "${owner}" >&2
      exit 1
    fi
    docker image inspect "${IMAGE}" >/dev/null 2>&1 || {
      printf 'ERROR: builder image missing: %s\n' "${IMAGE}" >&2
      exit 1
    }
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
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
