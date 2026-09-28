#!/usr/bin/env bash
# Validate the H38 decoder-scoped production candidate through its public runtime alias.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
RUNNER="${ROOT}/scripts/benchmark/run.py"
MODEL="hybrid-h38-deterministic/Qwen3.8-Flash-Next-Uncensored-NVFP4"
LABEL="${1:-candidate1}"
OUT="${ROOT}/scripts/benchmark/results/local/h38-production-gate"

mkdir -p "${OUT}"

python3 "${RUNNER}" determinism \
  --model "${MODEL}" \
  --determinism-prompt-tokens 1024 \
  --determinism-output-tokens 128 \
  --determinism-repeats 20 \
  --output "${OUT}/${LABEL}-det-1024-20x.json"

python3 "${RUNNER}" determinism \
  --model "${MODEL}" \
  --determinism-prompt-tokens 32768 \
  --determinism-output-tokens 128 \
  --determinism-repeats 10 \
  --output "${OUT}/${LABEL}-det-32768-10x.json"

python3 "${RUNNER}" qsa-determinism \
  --model "${MODEL}" \
  --qsa-determinism-sizes 1024,2048,4096,8192,32768 \
  --determinism-output-tokens 128 \
  --determinism-repeats 5 \
  --output "${OUT}/${LABEL}-qsa-forward.json"

python3 "${RUNNER}" qsa-determinism \
  --model "${MODEL}" \
  --qsa-determinism-sizes 32768,8192,4096,2048,1024 \
  --determinism-output-tokens 128 \
  --determinism-repeats 5 \
  --output "${OUT}/${LABEL}-qsa-reverse.json"
