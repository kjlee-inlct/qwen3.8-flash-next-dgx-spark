#!/usr/bin/env bash
# Controlled OrcaRouter experiment on the official vLLM v0.29 release line.
# This never mutates the managed installation, service, proxy, swap, or release pointers.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/install.env"
STATE_PARSER="${ROOT}/scripts/lib/state_file.py"
SERVICE="qwen38-flash-next.service"
IMAGE="vllm-orcarouter-v029:v1"
NAME="qwen38-orca-v029"
PORT=8888
ACTION="${1:-status}"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/runtime/orcarouter-v029.sh preflight
  ./scripts/runtime/orcarouter-v029.sh start
  ./scripts/runtime/orcarouter-v029.sh stop
  ./scripts/runtime/orcarouter-v029.sh status

Experiment controls:
  checkpoint        current installed OrcaRouter checkpoint
  base image        vllm/vllm-openai:v0.29.0
  PLE               mmap from /model, no CPU-offload worker
  QSA               exact torch.topk
  GB10 FLA fix      enabled
  MTP               k=2
  context           262144
  prefix cache      disabled
  max sequences     3
  KV cache          24 GiB
  API               127.0.0.1:8888

Build:
  docker build -t vllm-orcarouter-v029:v1     -f scripts/Dockerfile.v029-orcarouter scripts/

This helper is experimental and does not modify install.env or the stable runtime.
EOF
}

load_manifest() {
  local parsed key value
  [[ -r "${STATE_FILE}" ]] || { printf 'ERROR: installation manifest missing: %s\n' "${STATE_FILE}" >&2; return 1; }
  [[ -r "${STATE_PARSER}" ]] || { printf 'ERROR: state parser missing: %s\n' "${STATE_PARSER}" >&2; return 1; }
  parsed="$(mktemp)"
  trap 'rm -f -- "${parsed}"' RETURN
  python3 "${STATE_PARSER}" install-maintenance "${STATE_FILE}" >"${parsed}"
  MODEL_PROFILE=""; MODEL_DIR=""; SERVED_NAME=""; MODEL_REPO=""; MODEL_REVISION=""
  while IFS= read -r -d '' key && IFS= read -r -d '' value; do
    case "${key}" in
      MODEL_PROFILE) MODEL_PROFILE="${value}" ;;
      MODEL_DIR) MODEL_DIR="${value}" ;;
      SERVED_NAME) SERVED_NAME="${value}" ;;
      MODEL_REPO) MODEL_REPO="${value}" ;;
      MODEL_REVISION) MODEL_REVISION="${value}" ;;
    esac
  done <"${parsed}"
  rm -f -- "${parsed}"
  trap - RETURN
  [[ "${MODEL_PROFILE}" == orcarouter ]] || { printf 'ERROR: installed profile must be orcarouter\n' >&2; return 1; }
  [[ -n "${MODEL_DIR}" && -n "${SERVED_NAME}" ]] || { printf 'ERROR: incomplete OrcaRouter manifest\n' >&2; return 1; }
}

service_active() {
  command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet "${SERVICE}" 2>/dev/null
}

container_running() {
  local name="$1"
  [[ "$(docker inspect --format '{{.State.Running}}' "${name}" 2>/dev/null || true)" == true ]]
}

preflight() {
  local failures=0
  load_manifest || return 1
  printf 'OrcaRouter vLLM v0.29 preflight\n'
  printf '  model repo      : %s\n' "${MODEL_REPO}"
  printf '  model revision  : %s\n' "${MODEL_REVISION}"
  if [[ -f "${MODEL_DIR}/model.safetensors.index.json" ]]; then
    printf '  weights         : ready (%s)\n' "${MODEL_DIR}"
  else
    printf '  weights         : missing (%s)\n' "${MODEL_DIR}"
    failures=1
  fi
  if docker image inspect "${IMAGE}" >/dev/null 2>&1; then
    printf '  image           : ready (%s)\n' "${IMAGE}"
  else
    printf '  image           : missing (%s)\n' "${IMAGE}"
    printf '    build with    : docker build -t %s -f scripts/Dockerfile.v029-orcarouter scripts/\n' "${IMAGE}"
    failures=1
  fi
  printf '  managed service : '
  if service_active; then printf 'active (stop it before experiment)\n'; else printf 'inactive\n'; fi
  printf '  canonical       : '
  if container_running qwen38-flash-next; then printf 'running (stop managed service first)\n'; else printf 'not running\n'; fi
  printf '  experiment      : '
  if docker inspect "${NAME}" >/dev/null 2>&1; then
    docker inspect --format 'running={{.State.Running}} status={{.State.Status}} image={{.Config.Image}}' "${NAME}"
  else
    printf 'absent\n'
  fi
  return "${failures}"
}

start_runtime() {
  load_manifest
  command -v docker >/dev/null 2>&1 || { printf 'ERROR: docker is required\n' >&2; exit 1; }
  service_active && { printf 'ERROR: %s is active; stop it before this experiment\n' "${SERVICE}" >&2; exit 1; }
  container_running qwen38-flash-next && { printf 'ERROR: canonical runtime is still running\n' >&2; exit 1; }
  docker inspect "${NAME}" >/dev/null 2>&1 && { printf 'ERROR: experiment container already exists: %s\n' "${NAME}" >&2; exit 1; }
  docker image inspect "${IMAGE}" >/dev/null 2>&1 || { printf 'ERROR: image missing: %s\n' "${IMAGE}" >&2; exit 1; }

  local split
  split='["vllm::unified_attention_with_output","vllm::unified_mla_attention_with_output","vllm::mamba_mixer2","vllm::mamba_mixer","vllm::short_conv","vllm::qwen4_exp_compute_ple_ngram_ids","vllm::qwen4_exp_ple_short_conv","vllm::qwen4_exp_qsa_with_output","vllm::linear_attention","vllm::qwen_gdn_attention_core","vllm::qwen_gdn_attention_core_fused_norm_packed","vllm::sparse_attn_indexer","vllm::ple_mmap_lookup_ids"]'

  mkdir -p "${HOME}/.cache/vllm-qwen38-v029" "${HOME}/.cache/flashinfer-v029"

  docker run -d     --name "${NAME}"     --init     --user root     --restart no     --gpus all     --ipc host     --shm-size=32g     --ulimit memlock=-1:-1     --ulimit stack=67108864     -p "127.0.0.1:${PORT}:8000"     -e VLLM_TARGET_DEVICE=cuda     -e CUTE_DSL_ARCH=sm_121a     -e VLLM_PLE_MMAP=1     -e VLLM_PLE_MMAP_DIR=/model     -e VLLM_PLE_MMAP_WORKERS=32     -e VLLM_PLE_MMAP_PREWARM=0     -e VLLM_PLE_MMAP_MADVISE=random     -e VLLM_PLE_MMAP_FAST_ROWS=0     -e VLLM_QSA_EXACT_TOPK=1     -e QWEN38_VLLM_BASE=v0.29     -e QWEN38_GB10_FLA_FIX=1     -e QWEN38_PLE_MMAP=1     -e FLASHINFER_DISABLE_VERSION_CHECK=1     -v "${MODEL_DIR}:/model:ro"     -v "${HOME}/.cache/vllm-qwen38-v029:/root/.cache/vllm"     -v "${HOME}/.cache/flashinfer-v029:/root/.cache/flashinfer"     "${IMAGE}"     /model       --served-model-name "${SERVED_NAME}"       --host 0.0.0.0       --port 8000       --load-format safetensors       --max-model-len 262144       --max-num-seqs 3       --gpu-memory-utilization 0.80       --kv-cache-memory-bytes 25769803776       --kv-cache-dtype auto       --no-enable-prefix-caching       --enable-chunked-prefill       --max-num-batched-tokens 8192       -cc.cudagraph_mode=PIECEWISE       "-cc.splitting_ops=${split}"       --no-enable-flashinfer-autotune       --enable-auto-tool-choice       --tool-call-parser qwen3_coder       --reasoning-parser qwen3       --speculative-config '{"method":"mtp","num_speculative_tokens":2}'

  sleep 8
  local state
  state="$(docker inspect --format '{{.State.Status}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' "${NAME}" 2>/dev/null || true)"
  if [[ "${state}" != running* ]]; then
    printf 'ERROR: %s failed to stay running (%s)\n' "${NAME}" "${state}" >&2
    docker logs --tail 80 "${NAME}" 2>&1 >&2 || true
    return 1
  fi

  printf 'started %s (vLLM v0.29, OrcaRouter, PLE mmap, exact QSA, GB10 FLA fix, MTP k=2)\n' "${NAME}"
  printf 'wait with: ./scripts/wait-ready.sh --container %s --model %s\n' "${NAME}" "${SERVED_NAME}"
}

case "${ACTION}" in
  preflight)
    [[ $# -eq 1 ]] || { usage >&2; exit 2; }
    preflight
    ;;
  start)
    [[ $# -eq 1 ]] || { usage >&2; exit 2; }
    start_runtime
    ;;
  stop)
    [[ $# -eq 1 ]] || { usage >&2; exit 2; }
    if docker inspect "${NAME}" >/dev/null 2>&1; then
      docker rm -f "${NAME}" >/dev/null
      printf 'removed experimental container: %s\n' "${NAME}"
    else
      printf 'experimental container is absent: %s\n' "${NAME}"
    fi
    ;;
  status)
    [[ $# -eq 1 ]] || { usage >&2; exit 2; }
    printf 'Managed service active: '
    if service_active; then printf 'yes\n'; else printf 'no\n'; fi
    docker inspect --format '{{.Name}} running={{.State.Running}} status={{.State.Status}} image={{.Config.Image}}' "${NAME}" 2>/dev/null || printf 'experiment absent\n'
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    usage >&2
    exit 2
    ;;
esac
