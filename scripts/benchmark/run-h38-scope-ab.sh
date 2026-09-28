#!/usr/bin/env bash
# Run the matched H38 canonicalization-scope determinism matrix against an already-ready runtime.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
RUNNER="${ROOT}/scripts/benchmark/run.py"

SCOPE="${1:-}"
CYCLE="${2:-}"

case "${SCOPE}" in
  all)
    MODEL="hybrid-h38-all-scope/Qwen3.8-Flash-Next-Uncensored-NVFP4"
    ;;
  decoder)
    MODEL="hybrid-h38-decoder-scope/Qwen3.8-Flash-Next-Uncensored-NVFP4"
    ;;
  *)
    printf 'usage: %s all|decoder <cycle-label>\n' "$0" >&2
    exit 2
    ;;
esac

[[ -n "${CYCLE}" ]] || {
  printf 'ERROR: cycle label is required (for example cycle1)\n' >&2
  exit 2
}

OUT="${ROOT}/scripts/benchmark/results/local/h38-scope-ab"
mkdir -p "${OUT}"

python3 "${RUNNER}" determinism   --model "${MODEL}"   --determinism-prompt-tokens 1024   --determinism-output-tokens 128   --determinism-repeats 20   --output "${OUT}/${SCOPE}-${CYCLE}-det-1024-20x.json"

python3 "${RUNNER}" determinism   --model "${MODEL}"   --determinism-prompt-tokens 32768   --determinism-output-tokens 128   --determinism-repeats 10   --output "${OUT}/${SCOPE}-${CYCLE}-det-32768-10x.json"

python3 "${RUNNER}" qsa-determinism   --model "${MODEL}"   --qsa-determinism-sizes 1024,2048,4096,8192,32768   --determinism-output-tokens 128   --determinism-repeats 5   --output "${OUT}/${SCOPE}-${CYCLE}-qsa-forward.json"

python3 "${RUNNER}" qsa-determinism   --model "${MODEL}"   --qsa-determinism-sizes 32768,8192,4096,2048,1024   --determinism-output-tokens 128   --determinism-repeats 5   --output "${OUT}/${SCOPE}-${CYCLE}-qsa-reverse.json"
