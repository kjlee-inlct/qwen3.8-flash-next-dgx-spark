#!/usr/bin/env bash
# Plan/build thin H4 routed-expert A/B deltas on top of H3.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/install.env"
STATE_PARSER="${ROOT}/scripts/lib/state_file.py"
TOOL="${ROOT}/scripts/model/prepare-h4-expert-ab.py"
IMAGE="${H4_BUILDER_IMAGE:-vllm-orcarouter-v029:v1}"
H3="${HYBRID_QUANT_LAYOUT_MODEL_DIR:-$HOME/models/qwen3.8-hybrid-quant-layout}"

ACTION="${1:-plan}"
VARIANT="${2:-orca-down}"
shift || true
shift || true

case "${VARIANT}" in
  orca-down)
    OUTPUT="${H4_ORCA_DOWN_MODEL_DIR:-$HOME/models/qwen3.8-h4-orca-down}"
    ;;
  orca-gate-up)
    OUTPUT="${H4_ORCA_GATE_UP_MODEL_DIR:-$HOME/models/qwen3.8-h4-orca-gate-up}"
    ;;
  orca-all)
    OUTPUT="${H4_ORCA_ALL_MODEL_DIR:-$HOME/models/qwen3.8-h4-orca-all}"
    ;;
  *)
    printf 'ERROR: variant must be orca-down, orca-gate-up, or orca-all\n' >&2
    exit 2
    ;;
esac

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
  bash scripts/model/prepare-h4-expert-ab.sh plan  orca-down
  bash scripts/model/prepare-h4-expert-ab.sh plan  orca-gate-up
  bash scripts/model/prepare-h4-expert-ab.sh plan  orca-all
  bash scripts/model/prepare-h4-expert-ab.sh build orca-down [--force]
  bash scripts/model/prepare-h4-expert-ab.sh build orca-gate-up [--force]
  bash scripts/model/prepare-h4-expert-ab.sh build orca-all [--force]

H4 is a thin delta over the proven H3 checkpoint:
  orca-down     : normalize all OrcaRouter down_proj expert tensors into ModelOpt names
  orca-gate-up  : normalize all OrcaRouter gate_proj + up_proj expert tensors together
  orca-all      : normalize all OrcaRouter down_proj + gate_proj + up_proj expert tensors

H3 ModelOpt config and mazinb input_scale remain unchanged.
EOF
}

BASE=""
MODEL_PROFILE=""
parsed="$(mktemp)"
trap 'rm -f -- "${parsed}"' EXIT
python3 "${STATE_PARSER}" install-maintenance "${STATE_FILE}" >"${parsed}"
while IFS= read -r -d '' key && IFS= read -r -d '' value; do
  case "${key}" in
    MODEL_DIR) BASE="${value}" ;;
    MODEL_PROFILE) MODEL_PROFILE="${value}" ;;
  esac
done <"${parsed}"

[[ "${MODEL_PROFILE}" == orcarouter ]] || { printf 'ERROR: installed profile must be orcarouter\n' >&2; exit 1; }
[[ -d "${BASE}" ]] || { printf 'ERROR: OrcaRouter base missing: %s\n' "${BASE}" >&2; exit 1; }
[[ -d "${H3}" ]] || { printf 'ERROR: H3 checkpoint missing: %s\n' "${H3}" >&2; exit 1; }
docker image inspect "${IMAGE}" >/dev/null 2>&1 || { printf 'ERROR: image missing: %s\n' "${IMAGE}" >&2; exit 1; }

case "${ACTION}" in
  plan)
    exec docker run --pull=never --rm       --user "$(id -u):$(id -g)"       -e HOME=/tmp       -v "${BASE}:/base:ro"       -v "${H3}:/h3:ro"       -v "${TOOL}:/tool.py:ro"       --entrypoint python3       "${IMAGE}"       /tool.py plan --variant "${VARIANT}" --base /base --h3 /h3 --output /output
    ;;
  build)
    owner="$(docker ps --filter publish=8888 --format '{{.Names}}' 2>/dev/null | paste -sd, -)"
    [[ -z "${owner}" ]] || { printf 'ERROR: stop the runtime before H4 build; port 8888 is owned by: %s\n' "${owner}" >&2; exit 1; }
    mkdir -p "${OUTPUT}"
    args=(
      --pull=never --rm
      --user "$(id -u):$(id -g)"
      -e HOME=/tmp
      -v "${BASE}:/base:ro"
      -v "${H3}:/h3:ro"
      -v "${OUTPUT}:/output"
      -v "${TOOL}:/tool.py:ro"
      --entrypoint python3
      "${IMAGE}"
      /tool.py build
      --variant "${VARIANT}"
      --base /base
      --h3 /h3
      --output /output
    )
    [[ "${FORCE}" == 1 ]] && args+=(--force)
    exec docker run "${args[@]}"
    ;;
  help|-h|--help) usage ;;
  *) usage >&2; exit 2 ;;
esac
