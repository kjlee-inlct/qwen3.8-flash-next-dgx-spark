#!/usr/bin/env bash
# Launch one controlled NVIDIA INDEX_SHARE x AUTOTUNE benchmark runtime at a time.
set -Eeuo pipefail

RUNTIME_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
SERVE="${RUNTIME_ROOT}/scripts/serve.sh"
SERVICE="qwen38-flash-next.service"
ACTION="${1:-plan}"
CASE_ID="${2:-}"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/runtime/nvidia-2x2.sh plan
  ./scripts/runtime/nvidia-2x2.sh start A|B|C|D
  ./scripts/runtime/nvidia-2x2.sh stop [A|B|C|D]
  ./scripts/runtime/nvidia-2x2.sh status

Matrix:
  A  INDEX_SHARE=0  AUTOTUNE=0
  B  INDEX_SHARE=1  AUTOTUNE=0
  C  INDEX_SHARE=0  AUTOTUNE=1
  D  INDEX_SHARE=1  AUTOTUNE=1

Fixed controls:
  MODEL_PROFILE=nvidia
  NSPEC=3
  MAXLEN=524288
  KV_MEM=16106127360
  MAXSEQS=8
  PREFIX_CACHE=0
  RESTART_POLICY=no
  MONITOR_ENABLED=0
  loopback port 8888
EOF
}

case_values() {
  case "$1" in
    A) INDEX_SHARE_VALUE=0; AUTOTUNE_VALUE=0 ;;
    B) INDEX_SHARE_VALUE=1; AUTOTUNE_VALUE=0 ;;
    C) INDEX_SHARE_VALUE=0; AUTOTUNE_VALUE=1 ;;
    D) INDEX_SHARE_VALUE=1; AUTOTUNE_VALUE=1 ;;
    *) printf 'ERROR: case must be A, B, C, or D\n' >&2; return 2 ;;
  esac
  CONTAINER_NAME="qwen38-bench-${1,,}"
}

print_plan() {
  usage
  cat <<'EOF'

Recommended measurement for each case after /health is ready:

  python3 scripts/benchmark/run.py tuning \
    --determinism-prompt-tokens 32768 \
    --determinism-output-tokens 256 \
    --determinism-repeats 3 \
    --decode-tokens 600 \
    --decode-repeats 5 \
    --output scripts/benchmark/results/local/nvidia-2x2-CASE.json

The benchmark report auto-records the running container's vLLM command,
including MTP speculative config, FlashInfer autotune, KV, max length,
max sequences, prefix caching, async scheduling, image, and container name.
EOF
}

service_active() {
  command -v systemctl >/dev/null 2>&1 &&
    systemctl is-active --quiet "${SERVICE}" 2>/dev/null
}

container_running() {
  local name="$1"
  [[ "$(docker inspect --format '{{.State.Running}}' "${name}" 2>/dev/null || true)" == true ]]
}

stop_one() {
  local id="$1"
  case_values "${id}"
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
    print_plan
    ;;
  status)
    [[ $# -eq 1 ]] || { usage >&2; exit 2; }
    printf 'Managed service active: '
    if service_active; then printf 'yes\n'; else printf 'no\n'; fi
    printf 'Canonical runtime: '
    docker inspect --format '{{.Name}} running={{.State.Running}} status={{.State.Status}}' qwen38-flash-next 2>/dev/null || printf 'absent\n'
    for id in A B C D; do
      case_values "${id}"
      docker inspect --format '{{.Name}} running={{.State.Running}} status={{.State.Status}}' "${CONTAINER_NAME}" 2>/dev/null || true
    done
    ;;
  start)
    [[ $# -eq 2 ]] || { usage >&2; exit 2; }
    case_values "${CASE_ID}"
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
    for id in A B C D; do
      case_values "${id}"
      if docker inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
        printf 'ERROR: experimental container already exists: %s; stop it first.\n' "${CONTAINER_NAME}" >&2
        exit 1
      fi
    done
    case_values "${CASE_ID}"

    printf 'Starting NVIDIA 2x2 case %s: INDEX_SHARE=%s AUTOTUNE=%s\n'       "${CASE_ID}" "${INDEX_SHARE_VALUE}" "${AUTOTUNE_VALUE}"

    MODEL_PROFILE=nvidia     NSPEC=3     MAXLEN=524288     KV_MEM=16106127360     MAXSEQS=8     PREFIX_CACHE=0     INDEX_SHARE="${INDEX_SHARE_VALUE}"     AUTOTUNE="${AUTOTUNE_VALUE}"     NAME="${CONTAINER_NAME}"     PORT=8888     PUBLISH_HOST=127.0.0.1     RESTART_POLICY=no     MONITOR_ENABLED=0     MONITOR_PROTECT=0       "${SERVE}"
    ;;
  stop)
    [[ $# -le 2 ]] || { usage >&2; exit 2; }
    if [[ -n "${CASE_ID}" ]]; then
      stop_one "${CASE_ID}"
    else
      for id in A B C D; do stop_one "${id}"; done
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
