#!/usr/bin/env bash
# Compare installed OrcaRouter and downloaded mazinb checkpoint structure/metadata.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_FILE="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark/install.env"
STATE_PARSER="${ROOT}/scripts/lib/state_file.py"
MODEL_REGISTRY="${ROOT}/scripts/model-profiles.sh"
TOOL="${ROOT}/scripts/model/inspect-checkpoint-diff.py"
IMAGE="${CHECKPOINT_DIFF_IMAGE:-vllm-orcarouter-v029:v1}"
OUTPUT="${CHECKPOINT_DIFF_OUTPUT:-${ROOT}/scripts/benchmark/results/local/orcarouter-vs-mazinb-structure.json}"

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
[[ -d "${BASE}" ]] || { printf 'ERROR: base model missing: %s\n' "${BASE}" >&2; exit 1; }

# shellcheck source=scripts/model-profiles.sh
source "${MODEL_REGISTRY}"
load_download_profile mazinb
CANDIDATE="${PROFILE_MODEL_DIR}"
[[ -d "${CANDIDATE}" ]] || { printf 'ERROR: mazinb checkpoint missing: %s\n' "${CANDIDATE}" >&2; exit 1; }

docker image inspect "${IMAGE}" >/dev/null 2>&1 || { printf 'ERROR: image missing: %s\n' "${IMAGE}" >&2; exit 1; }
mkdir -p "$(dirname -- "${OUTPUT}")"
touch "${OUTPUT}"

exec docker run --pull=never --rm \
  --user "$(id -u):$(id -g)" \
  -v "${BASE}:/base:ro" \
  -v "${CANDIDATE}:/candidate:ro" \
  -v "${TOOL}:/tool.py:ro" \
  -v "${OUTPUT}:/report.json" \
  --entrypoint python3 \
  "${IMAGE}" \
  /tool.py \
  --base /base \
  --candidate /candidate \
  --json-output /report.json
