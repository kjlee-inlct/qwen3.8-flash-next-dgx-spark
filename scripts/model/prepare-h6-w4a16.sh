#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
TOOL="${ROOT}/scripts/model/prepare-h6-w4a16.py"
IMAGE="${H6_BUILDER_IMAGE:-vllm-orcarouter-v029:v1}"
PARENT="${H5_NEUTRAL_INPUT_MODEL_DIR:-$HOME/models/qwen3.8-h5-neutral-input-scale}"
OUTPUT="${H6_W4A16_MODEL_DIR:-$HOME/models/qwen3.8-h6-modelopt-w4a16}"
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
  bash scripts/model/prepare-h6-w4a16.sh plan
  bash scripts/model/prepare-h6-w4a16.sh build [--force]
EOF
}

[[ -d "${PARENT}" ]] || { printf 'ERROR: H5 parent missing: %s\n' "${PARENT}" >&2; exit 1; }
docker image inspect "${IMAGE}" >/dev/null 2>&1 || { printf 'ERROR: image missing: %s\n' "${IMAGE}" >&2; exit 1; }

case "${ACTION}" in
  plan)
    exec docker run --pull=never --rm       --user "$(id -u):$(id -g)" -e HOME=/tmp       -v "${PARENT}:/h5-parent:ro"       -v "${TOOL}:/tool.py:ro"       --entrypoint python3 "${IMAGE}"       /tool.py plan --parent /h5-parent --output /output
    ;;
  build)
    owner="$(docker ps --filter publish=8888 --format '{{.Names}}' 2>/dev/null | paste -sd, -)"
    [[ -z "${owner}" ]] || { printf 'ERROR: stop the runtime before H6 build; port 8888 is owned by: %s\n' "${owner}" >&2; exit 1; }
    mkdir -p "${OUTPUT}"
    args=(--pull=never --rm --user "$(id -u):$(id -g)" -e HOME=/tmp
      -v "${PARENT}:/h5-parent:ro"
      -v "${OUTPUT}:/output"
      -v "${TOOL}:/tool.py:ro"
      --entrypoint python3 "${IMAGE}"
      /tool.py build --parent /h5-parent --output /output)
    [[ "${FORCE}" == 1 ]] && args+=(--force)
    exec docker run "${args[@]}"
    ;;
  help|-h|--help) usage ;;
  *) usage >&2; exit 2 ;;
esac
