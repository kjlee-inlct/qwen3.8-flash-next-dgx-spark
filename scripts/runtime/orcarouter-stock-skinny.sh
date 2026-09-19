#!/usr/bin/env bash
# Launch controlled OrcaRouter stock-vs-skinny runtime experiments without mutating the managed install.
set -Eeuo pipefail

RUNTIME_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
SERVE="${RUNTIME_ROOT}/scripts/serve.sh"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/install.env"
STATE_PARSER="${RUNTIME_ROOT}/scripts/lib/state_file.py"
SERVICE="qwen38-flash-next.service"
ACTION="${1:-plan}"
CASE_ID="${2:-}"

STOCK_IMAGE="vllm/vllm-openai:qwen38-flash-next-arm64-cu130"
SKINNY_IMAGE="vllm-skinny-tp1:v1"
SKINNY_DET_IMAGE="vllm-skinny-qsa-det:v1"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/runtime/orcarouter-stock-skinny.sh plan
  ./scripts/runtime/orcarouter-stock-skinny.sh preflight
  ./scripts/runtime/orcarouter-stock-skinny.sh start STOCK|STOCK-NOSPEC|SKINNY|SKINNY-NOSPEC|SKINNY-DET
  ./scripts/runtime/orcarouter-stock-skinny.sh stop [STOCK|STOCK-NOSPEC|SKINNY|SKINNY-NOSPEC|SKINNY-DET]
  ./scripts/runtime/orcarouter-stock-skinny.sh status

Cases:
  STOCK          stock Qwen3.8 vLLM image + MTP k=2
  STOCK-NOSPEC   stock Qwen3.8 vLLM image + no speculative decoding
  SKINNY         skinny-GEMM image + MTP k=2
  SKINNY-NOSPEC  skinny-GEMM image + no speculative decoding
  SKINNY-DET     skinny-GEMM image + deterministic QSA top-k + MTP k=2

Fixed controls:
  MODEL_PROFILE=orcarouter
  NSPEC=2
  MAXLEN=262144
  KV_MEM=25769803776
  MAXSEQS=3
  PREFIX_CACHE=0
  INDEX_SHARE=0
  AUTOTUNE=0
  SPEC=mtp except *-NOSPEC cases
  QSA_DET_TOPK=1 only for SKINNY-DET
  RESTART_POLICY=no
  MONITOR_ENABLED=0
  loopback port 8888

The helper reads MODEL_DIR, CONFIG_OVERRIDE, and SERVED_NAME from the current
installation manifest. It never edits the manifest, service, proxy, model files,
swap, or immutable release pointers.
EOF
}

load_manifest() {
  local parsed key value
  [[ -r "${STATE_FILE}" ]] || { printf 'ERROR: installation manifest missing: %s\n' "${STATE_FILE}" >&2; return 1; }
  [[ -r "${STATE_PARSER}" ]] || { printf 'ERROR: strict state parser missing: %s\n' "${STATE_PARSER}" >&2; return 1; }
  parsed="$(mktemp)"
  if ! python3 "${STATE_PARSER}" install-maintenance "${STATE_FILE}" >"${parsed}"; then
    rm -f -- "${parsed}"
    return 1
  fi
  MODEL_PROFILE=""; MODEL_DIR=""; CONFIG_OVERRIDE=""; SERVED_NAME=""; MODEL_REPO=""; MODEL_REVISION=""
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    case "${key}" in
      MODEL_PROFILE) MODEL_PROFILE="${value}" ;;
      MODEL_DIR) MODEL_DIR="${value}" ;;
      CONFIG_OVERRIDE) CONFIG_OVERRIDE="${value}" ;;
      SERVED_NAME) SERVED_NAME="${value}" ;;
      MODEL_REPO) MODEL_REPO="${value}" ;;
      MODEL_REVISION) MODEL_REVISION="${value}" ;;
    esac
  done <"${parsed}"
  rm -f -- "${parsed}"
  [[ "${MODEL_PROFILE}" == orcarouter ]] || { printf 'ERROR: installed profile must be orcarouter\n' >&2; return 1; }
  [[ -n "${MODEL_DIR}" && -n "${SERVED_NAME}" && -n "${MODEL_REPO}" && -n "${MODEL_REVISION}" ]] || {
    printf 'ERROR: OrcaRouter manifest is incomplete\n' >&2; return 1; }
}

case_values() {
  case "$1" in
    STOCK)
      IMAGE="${STOCK_IMAGE}"; CONTAINER_NAME="qwen38-orca-stock"; SPEC_VALUE=mtp; QSA_DET_VALUE=0 ;;
    STOCK-NOSPEC)
      IMAGE="${STOCK_IMAGE}"; CONTAINER_NAME="qwen38-orca-stock-nospec"; SPEC_VALUE=none; QSA_DET_VALUE=0 ;;
    SKINNY)
      IMAGE="${SKINNY_IMAGE}"; CONTAINER_NAME="qwen38-orca-skinny"; SPEC_VALUE=mtp; QSA_DET_VALUE=0 ;;
    SKINNY-NOSPEC)
      IMAGE="${SKINNY_IMAGE}"; CONTAINER_NAME="qwen38-orca-skinny-nospec"; SPEC_VALUE=none; QSA_DET_VALUE=0 ;;
    SKINNY-DET)
      IMAGE="${SKINNY_DET_IMAGE}"; CONTAINER_NAME="qwen38-orca-skinny-det"; SPEC_VALUE=mtp; QSA_DET_VALUE=1 ;;
    *)
      printf 'ERROR: case must be STOCK, STOCK-NOSPEC, SKINNY, SKINNY-NOSPEC, or SKINNY-DET\n' >&2
      return 2
      ;;
  esac
}

service_active() {
  command -v systemctl >/dev/null 2>&1 &&
    systemctl is-active --quiet "${SERVICE}" 2>/dev/null
}

container_running() {
  local name="$1"
  [[ "$(docker inspect --format '{{.State.Running}}' "${name}" 2>/dev/null || true)" == true ]]
}

preflight() {
  local failures=0 image
  load_manifest || return 1
  printf 'OrcaRouter stock-vs-skinny preflight\n'
  printf '  model repo      : %s\n' "${MODEL_REPO}"
  printf '  model revision  : %s\n' "${MODEL_REVISION}"

  if [[ -f "${MODEL_DIR}/model.safetensors.index.json" ]]; then
    printf '  weights         : ready (%s)\n' "${MODEL_DIR}"
  else
    printf '  weights         : missing (%s)\n' "${MODEL_DIR}"
    failures=1
  fi

  if [[ -z "${CONFIG_OVERRIDE}" || -f "${CONFIG_OVERRIDE}" ]]; then
    printf '  config override : %s\n' "${CONFIG_OVERRIDE:-automatic}"
  else
    printf '  config override : missing (%s)\n' "${CONFIG_OVERRIDE}"
    failures=1
  fi

  for image in "${STOCK_IMAGE}" "${SKINNY_IMAGE}" "${SKINNY_DET_IMAGE}"; do
    if docker image inspect "${image}" >/dev/null 2>&1; then
      printf '  image           : ready (%s)\n' "${image}"
    else
      printf '  image           : missing (%s)\n' "${image}"
      if [[ "${image}" == "${SKINNY_DET_IMAGE}" ]]; then
        printf '    build with    : docker build -t %s -f scripts/Dockerfile.qsa-det scripts/\n' "${SKINNY_DET_IMAGE}"
      fi
      failures=1
    fi
  done

  if swapon --show=NAME --noheadings 2>/dev/null | grep -Fxq /swap-ple.img; then
    printf '  PLE swap        : ready (/swap-ple.img)\n'
  else
    printf '  PLE swap        : missing (/swap-ple.img)\n'
    failures=1
  fi

  printf '  managed service : '
  if service_active; then printf 'active (stop it before experiments)\n'; else printf 'inactive\n'; fi
  printf '  canonical       : '
  if container_running qwen38-flash-next; then
    printf 'running (stop managed service before experiments)\n'
  else
    printf 'not running\n'
  fi
  return "${failures}"
}

stop_one() {
  case_values "$1"
  if docker inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
    docker rm -f "${CONTAINER_NAME}" >/dev/null
    printf 'removed experimental container: %s\n' "${CONTAINER_NAME}"
  else
    printf 'experimental container is absent: %s\n' "${CONTAINER_NAME}"
  fi
}

case "${ACTION}" in
  plan)
    [[ $# -eq 1 ]] || { usage >&2; exit 2; }
    usage
    ;;
  preflight)
    [[ $# -eq 1 ]] || { usage >&2; exit 2; }
    preflight
    ;;
  status)
    [[ $# -eq 1 ]] || { usage >&2; exit 2; }
    printf 'Managed service active: '
    if service_active; then printf 'yes\n'; else printf 'no\n'; fi
    printf 'Canonical runtime: '
    docker inspect --format '{{.Name}} running={{.State.Running}} status={{.State.Status}} image={{.Config.Image}}' qwen38-flash-next 2>/dev/null || printf 'absent\n'
    for id in STOCK STOCK-NOSPEC SKINNY SKINNY-NOSPEC SKINNY-DET; do
      case_values "${id}"
      docker inspect --format '{{.Name}} running={{.State.Running}} status={{.State.Status}} image={{.Config.Image}}' "${CONTAINER_NAME}" 2>/dev/null || true
    done
    ;;
  start)
    [[ $# -eq 2 ]] || { usage >&2; exit 2; }
    case_values "${CASE_ID}"
    load_manifest
    [[ -x "${SERVE}" ]] || { printf 'ERROR: serve helper missing: %s\n' "${SERVE}" >&2; exit 1; }
    command -v docker >/dev/null 2>&1 || { printf 'ERROR: docker is required\n' >&2; exit 1; }

    if service_active; then
      printf 'ERROR: %s is active; stop the managed service before an experiment.\n' "${SERVICE}" >&2
      exit 1
    fi
    if container_running qwen38-flash-next; then
      printf 'ERROR: canonical runtime qwen38-flash-next is still running.\n' >&2
      exit 1
    fi
    for id in STOCK STOCK-NOSPEC SKINNY SKINNY-NOSPEC SKINNY-DET; do
      case_values "${id}"
      if docker inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
        printf 'ERROR: experimental container already exists: %s; stop it first.\n' "${CONTAINER_NAME}" >&2
        exit 1
      fi
    done
    case_values "${CASE_ID}"
    docker image inspect "${IMAGE}" >/dev/null 2>&1 || {
      printf 'ERROR: image is missing: %s\n' "${IMAGE}" >&2
      exit 1
    }

    printf 'Starting OrcaRouter case %s with image=%s spec=%s qsa_det_topk=%s\n' "${CASE_ID}" "${IMAGE}" "${SPEC_VALUE}" "${QSA_DET_VALUE}"
    MODEL_PROFILE=orcarouter     MODEL_DIR="${MODEL_DIR}"     VLLM_IMAGE="${IMAGE}"     CONFIG_OVERRIDE="${CONFIG_OVERRIDE}"     SERVED_NAME="${SERVED_NAME}"     NSPEC=2     MAXLEN=262144     KV_MEM=25769803776     MAXSEQS=3     PREFIX_CACHE=0     INDEX_SHARE=0     AUTOTUNE=0     SPEC="${SPEC_VALUE}"     QSA_DET_TOPK="${QSA_DET_VALUE}"     NAME="${CONTAINER_NAME}"     PORT=8888     PUBLISH_HOST=127.0.0.1     RESTART_POLICY=no     MONITOR_ENABLED=0     MONITOR_PROTECT=0       "${SERVE}"
    ;;
  stop)
    [[ $# -le 2 ]] || { usage >&2; exit 2; }
    if [[ -n "${CASE_ID}" ]]; then
      stop_one "${CASE_ID}"
    else
      for id in STOCK STOCK-NOSPEC SKINNY SKINNY-NOSPEC SKINNY-DET; do stop_one "${id}"; done
    fi
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
