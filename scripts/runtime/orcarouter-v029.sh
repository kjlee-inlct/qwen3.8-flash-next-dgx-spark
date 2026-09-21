#!/usr/bin/env bash
# Controlled OrcaRouter experiment on the official vLLM v0.29 release line.
# This never mutates the managed installation, service, proxy, swap, or release pointers.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
STATE_FILE="${STATE_DIR}/install.env"
STATE_PARSER="${ROOT}/scripts/lib/state_file.py"
MODEL_REGISTRY="${ROOT}/scripts/model-profiles.sh"
SERVICE="qwen38-flash-next.service"
IMAGE="vllm-orcarouter-v029:v1"
PORT=8888
ACTION="${1:-status}"
PROFILE_CASE="orcarouter"
shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) [[ $# -ge 2 ]] || { printf 'ERROR: --profile requires orcarouter, mazinb, hybrid-residual, hybrid-group0, hybrid-quant-layout, hybrid-h4-down, hybrid-h4-gate-up, hybrid-h4-all, hybrid-h5-neutral-input, hybrid-h6-w4a16, hybrid-h7-group-metadata, hybrid-h8-ct-block, or hybrid-h9-ct-modelweight\n' >&2; exit 2; }; PROFILE_CASE="$2"; shift ;;
    -h|--help) ACTION=help ;;
    *) printf 'ERROR: unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
  shift
done
case "${PROFILE_CASE}" in
  orcarouter) NAME="qwen38-orca-v029" ;;
  mazinb) NAME="qwen38-mazinb-v029" ;;
  hybrid-residual) NAME="qwen38-hybrid-residual-v029" ;;
  hybrid-group0) NAME="qwen38-hybrid-group0-v029" ;;
  hybrid-quant-layout) NAME="qwen38-hybrid-quant-layout-v029" ;;
  hybrid-h4-down) NAME="qwen38-h4-down-v029" ;;
  hybrid-h4-gate-up) NAME="qwen38-h4-gate-up-v029" ;;
  hybrid-h4-all) NAME="qwen38-h4-all-v029" ;;
  hybrid-h5-neutral-input) NAME="qwen38-h5-neutral-input-v029" ;;
  hybrid-h6-w4a16) NAME="qwen38-h6-w4a16-v029" ;;
  hybrid-h7-group-metadata) NAME="qwen38-h7-group-metadata-v029"; IMAGE="vllm-orcarouter-v029-h7-group:v1" ;;
  hybrid-h8-ct-block) NAME="qwen38-h8-ct-block-v029"; IMAGE="vllm-orcarouter-v029-h8-ct-block:v1" ;;
  hybrid-h9-ct-modelweight) NAME="qwen38-h9-ct-modelweight-v029"; IMAGE="vllm-orcarouter-v029-h9-ct-modelweight:v1" ;;
  *) printf 'ERROR: --profile must be orcarouter, mazinb, hybrid-residual, hybrid-group0, hybrid-quant-layout, hybrid-h4-down, hybrid-h4-gate-up, hybrid-h4-all, hybrid-h5-neutral-input, hybrid-h6-w4a16, hybrid-h7-group-metadata, hybrid-h8-ct-block, or hybrid-h9-ct-modelweight\n' >&2; exit 2 ;;
esac

usage() {
  cat <<'EOF'
Usage:
  ./scripts/runtime/orcarouter-v029.sh preflight [--profile orcarouter|mazinb|hybrid-residual|hybrid-group0|hybrid-quant-layout|hybrid-h4-down|hybrid-h4-gate-up|hybrid-h4-all|hybrid-h5-neutral-input|hybrid-h6-w4a16|hybrid-h7-group-metadata|hybrid-h8-ct-block|hybrid-h9-ct-modelweight]
  ./scripts/runtime/orcarouter-v029.sh start [--profile orcarouter|mazinb|hybrid-residual|hybrid-group0|hybrid-quant-layout|hybrid-h4-down|hybrid-h4-gate-up|hybrid-h4-all|hybrid-h5-neutral-input|hybrid-h6-w4a16|hybrid-h7-group-metadata|hybrid-h8-ct-block|hybrid-h9-ct-modelweight]
  ./scripts/runtime/orcarouter-v029.sh stop [--profile orcarouter|mazinb|hybrid-residual|hybrid-group0|hybrid-quant-layout|hybrid-h4-down|hybrid-h4-gate-up|hybrid-h4-all|hybrid-h5-neutral-input|hybrid-h6-w4a16|hybrid-h7-group-metadata|hybrid-h8-ct-block|hybrid-h9-ct-modelweight]
  ./scripts/runtime/orcarouter-v029.sh status [--profile orcarouter|mazinb|hybrid-residual|hybrid-group0|hybrid-quant-layout|hybrid-h4-down|hybrid-h4-gate-up|hybrid-h4-all|hybrid-h5-neutral-input|hybrid-h6-w4a16|hybrid-h7-group-metadata|hybrid-h8-ct-block|hybrid-h9-ct-modelweight]

Experiment controls:
  checkpoint        installed OrcaRouter, downloaded mazinb, or local BF16 hybrid
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

load_source() {
  BASE_MODEL_DIR=""
  BASE_MODEL_REVISION=""
  if [[ "${PROFILE_CASE}" == orcarouter || "${PROFILE_CASE}" == hybrid-h8-ct-block || "${PROFILE_CASE}" == hybrid-h9-ct-modelweight ]]; then
    load_manifest || return 1
    BASE_MODEL_DIR="${MODEL_DIR}"
    BASE_MODEL_REVISION="${MODEL_REVISION}"
    if [[ "${PROFILE_CASE}" == hybrid-h8-ct-block ]]; then
      MODEL_PROFILE="hybrid-h8-ct-block"
      SERVED_NAME="hybrid-h8-ct-block/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      MODEL_REPO="local/h8-ct-block-over-orcarouter"
      MODEL_REVISION="runtime-control"
    elif [[ "${PROFILE_CASE}" == hybrid-h9-ct-modelweight ]]; then
      MODEL_PROFILE="hybrid-h9-ct-modelweight"
      SERVED_NAME="hybrid-h9-ct-modelweight/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      MODEL_REPO="local/h9-ct-modelweight-over-orcarouter"
      MODEL_REVISION="runtime-control"
    fi
    return 0
  fi

  if [[ "${PROFILE_CASE}" == hybrid-residual || "${PROFILE_CASE}" == hybrid-group0 || "${PROFILE_CASE}" == hybrid-quant-layout || "${PROFILE_CASE}" == hybrid-h4-down || "${PROFILE_CASE}" == hybrid-h4-gate-up || "${PROFILE_CASE}" == hybrid-h4-all || "${PROFILE_CASE}" == hybrid-h5-neutral-input || "${PROFILE_CASE}" == hybrid-h6-w4a16 || "${PROFILE_CASE}" == hybrid-h7-group-metadata ]]; then
    load_manifest || return 1
    BASE_MODEL_DIR="${MODEL_DIR}"
    BASE_MODEL_REVISION="${MODEL_REVISION}"
    if [[ "${PROFILE_CASE}" == hybrid-h7-group-metadata ]]; then
      MODEL_PROFILE="hybrid-h7-group-metadata"
      MODEL_DIR="${H6_W4A16_MODEL_DIR:-$HOME/models/qwen3.8-h6-modelopt-w4a16}"
      SERVED_NAME="hybrid-h7-group-metadata/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      MODEL_REPO="local/h7-modelopt-group-metadata"
    elif [[ "${PROFILE_CASE}" == hybrid-h6-w4a16 ]]; then
      MODEL_PROFILE="hybrid-h6-w4a16"
      MODEL_DIR="${H6_W4A16_MODEL_DIR:-$HOME/models/qwen3.8-h6-modelopt-w4a16}"
      SERVED_NAME="hybrid-h6-w4a16/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      MODEL_REPO="local/h6-modelopt-w4a16"
    elif [[ "${PROFILE_CASE}" == hybrid-h5-neutral-input ]]; then
      MODEL_PROFILE="hybrid-h5-neutral-input"
      MODEL_DIR="${H5_NEUTRAL_INPUT_MODEL_DIR:-$HOME/models/qwen3.8-h5-neutral-input-scale}"
      SERVED_NAME="hybrid-h5-neutral-input/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      MODEL_REPO="local/h5-neutral-input-scale"
    elif [[ "${PROFILE_CASE}" == hybrid-h4-all ]]; then
      MODEL_PROFILE="hybrid-h4-all"
      MODEL_DIR="${H4_ORCA_ALL_MODEL_DIR:-$HOME/models/qwen3.8-h4-orca-all}"
      SERVED_NAME="hybrid-h4-all/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      MODEL_REPO="local/h4-orca-all"
    elif [[ "${PROFILE_CASE}" == hybrid-h4-down ]]; then
      MODEL_PROFILE="hybrid-h4-down"
      MODEL_DIR="${H4_ORCA_DOWN_MODEL_DIR:-$HOME/models/qwen3.8-h4-orca-down}"
      SERVED_NAME="hybrid-h4-down/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      MODEL_REPO="local/h4-orca-down"
    elif [[ "${PROFILE_CASE}" == hybrid-h4-gate-up ]]; then
      MODEL_PROFILE="hybrid-h4-gate-up"
      MODEL_DIR="${H4_ORCA_GATE_UP_MODEL_DIR:-$HOME/models/qwen3.8-h4-orca-gate-up}"
      SERVED_NAME="hybrid-h4-gate-up/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      MODEL_REPO="local/h4-orca-gate-up"
    elif [[ "${PROFILE_CASE}" == hybrid-quant-layout ]]; then
      MODEL_PROFILE="hybrid-quant-layout"
      MODEL_DIR="${HYBRID_QUANT_LAYOUT_MODEL_DIR:-$HOME/models/qwen3.8-hybrid-quant-layout}"
      SERVED_NAME="hybrid-quant-layout/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      MODEL_REPO="local/orcarouter-mazinb-quant-layout"
    elif [[ "${PROFILE_CASE}" == hybrid-group0 ]]; then
      MODEL_PROFILE="hybrid-group0"
      MODEL_DIR="${HYBRID_GROUP0_MODEL_DIR:-$HOME/models/qwen3.8-hybrid-group0-bf16}"
      SERVED_NAME="hybrid-group0/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      MODEL_REPO="local/orcarouter-mazinb-group0-bf16"
    else
      MODEL_PROFILE="hybrid-residual"
      MODEL_DIR="${HYBRID_MODEL_DIR:-$HOME/models/qwen3.8-hybrid-residual-bf16}"
      SERVED_NAME="hybrid-residual/Qwen3.8-Flash-Next-Uncensored-NVFP4"
      MODEL_REPO="local/orcarouter-mazinb-residual-bf16"
    fi
    MODEL_REVISION="hybrid"
    return 0
  fi

  [[ -r "${MODEL_REGISTRY}" ]] || { printf 'ERROR: model registry missing: %s\n' "${MODEL_REGISTRY}" >&2; return 1; }
  # shellcheck source=scripts/model-profiles.sh
  source "${MODEL_REGISTRY}"
  load_download_profile mazinb || return 1
  MODEL_PROFILE="mazinb"
  MODEL_DIR="${PROFILE_MODEL_DIR}"
  SERVED_NAME="${PROFILE_SERVED_NAME}"
  MODEL_REPO="${PROFILE_REPO}"
  MODEL_REVISION="${PROFILE_REVISION}"
}


h9_image_ok() {
  [[ "${PROFILE_CASE}" != hybrid-h9-ct-modelweight ]] && return 0
  local label
  label="$(docker image inspect "${IMAGE}" --format '{{ index .Config.Labels "qwen38.h9" }}' 2>/dev/null || true)"
  [[ "${label}" == "compressed-tensors-nvfp4-scale-modelweight-block-v2" ]]
}

source_manifest_ok() {
  if [[ "${PROFILE_CASE}" == hybrid-h8-ct-block || "${PROFILE_CASE}" == hybrid-h9-ct-modelweight ]]; then
    return 0
  fi

  if [[ "${PROFILE_CASE}" == mazinb ]]; then
    local manifest="${MODEL_DIR}/.qwen38-model-manifest.json"
    [[ -r "${manifest}" ]] || return 1
    python3 - "${manifest}" "${MODEL_REPO}" <<'PY' >/dev/null
import json, sys
path, expected_repo = sys.argv[1:]
data = json.load(open(path, encoding="utf-8"))
ok = data.get("status") == "complete" and data.get("repository") == expected_repo and bool(data.get("revision"))
raise SystemExit(0 if ok else 1)
PY
    return
  fi





  if [[ "${PROFILE_CASE}" == hybrid-h7-group-metadata ]]; then
    local manifest="${MODEL_DIR}/.qwen38-hybrid-manifest.json"
    [[ -r "${manifest}" ]] || return 1
    python3 - "${manifest}" <<'PY' >/dev/null
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
ok = (
    data.get("status") == "complete"
    and data.get("variant") == "h6-modelopt-w4a16"
    and data.get("parent_variant") == "h5-neutral-input-scale"
    and data.get("quant_algo_after") == "W4A16_NVFP4"
    and data.get("safetensor_bytes_changed") == 0
    and data.get("mtp_tensors_changed") == 0
)
raise SystemExit(0 if ok else 1)
PY
    return
  fi

  if [[ "${PROFILE_CASE}" == hybrid-h6-w4a16 ]]; then
    local manifest="${MODEL_DIR}/.qwen38-hybrid-manifest.json"
    [[ -r "${manifest}" ]] || return 1
    python3 - "${manifest}" <<'PY' >/dev/null
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
ok = (
    data.get("status") == "complete"
    and data.get("variant") == "h6-modelopt-w4a16"
    and data.get("parent_variant") == "h5-neutral-input-scale"
    and data.get("expert_value_source") == "orcarouter-h4-all"
    and data.get("input_scale_source") == "h5-neutral-1.0"
    and data.get("quant_algo_before") == "NVFP4"
    and data.get("quant_algo_after") == "W4A16_NVFP4"
    and data.get("safetensor_bytes_changed") == 0
    and data.get("mtp_tensors_changed") == 0
)
raise SystemExit(0 if ok else 1)
PY
    return
  fi

  if [[ "${PROFILE_CASE}" == hybrid-h5-neutral-input ]]; then
    local manifest="${MODEL_DIR}/.qwen38-hybrid-manifest.json"
    [[ -r "${manifest}" ]] || return 1
    python3 - "${manifest}" <<'PY' >/dev/null
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
ok = (
    data.get("status") == "complete"
    and data.get("variant") == "h5-neutral-input-scale"
    and data.get("parent_variant") == "h4-orca-all"
    and data.get("input_scale_tensors_changed") == 73728
    and data.get("input_scale_value") == 1.0
    and data.get("expert_value_source") == "orcarouter-h4-all"
    and data.get("quantization_config_source") == "mazinb-modelopt-nvfp4"
    and data.get("mtp_tensors_changed") == 0
)
raise SystemExit(0 if ok else 1)
PY
    return
  fi

  if [[ "${PROFILE_CASE}" == hybrid-h4-down || "${PROFILE_CASE}" == hybrid-h4-gate-up || "${PROFILE_CASE}" == hybrid-h4-all ]]; then
    local manifest="${MODEL_DIR}/.qwen38-hybrid-manifest.json"
    [[ -r "${manifest}" ]] || return 1
    python3 - "${manifest}" "${PROFILE_CASE}" <<'PY' >/dev/null
import json, sys
path, profile = sys.argv[1:]
data = json.load(open(path, encoding="utf-8"))
expected = {
    "hybrid-h4-down": ("h4-orca-down", 24576, 73728),
    "hybrid-h4-gate-up": ("h4-orca-gate-up", 49152, 147456),
    "hybrid-h4-all": ("h4-orca-all", 73728, 221184),
}[profile]
variant, modules, tensors = expected
ok = (
    data.get("status") == "complete"
    and data.get("variant") == variant
    and data.get("parent_variant") == "quant-layout-mazinb-experts"
    and data.get("orca_modules_normalized") == modules
    and data.get("normalized_tensors") == tensors
    and data.get("input_scale_source") == "mazinb-h3"
    and data.get("quantization_config_source") == "mazinb-modelopt-nvfp4"
    and data.get("mtp_tensors_changed") == 0
)
raise SystemExit(0 if ok else 1)
PY
    return
  fi

  if [[ "${PROFILE_CASE}" == hybrid-quant-layout ]]; then
    local manifest="${MODEL_DIR}/.qwen38-hybrid-manifest.json"
    [[ -r "${manifest}" ]] || return 1
    python3 - "${manifest}" "${BASE_MODEL_REVISION}" <<'PY' >/dev/null
import json, sys
path, expected_base = sys.argv[1:]
data = json.load(open(path, encoding="utf-8"))
ok = (
    data.get("status") == "complete"
    and data.get("variant") == "quant-layout-mazinb-experts"
    and data.get("base_revision") == expected_base
    and bool(data.get("overlay_revision"))
    and data.get("group0_bf16_weights") == 300
    and data.get("group0_fp8_scales_removed") == 300
    and data.get("base_expert_tensors_removed") == 221184
    and data.get("overlay_expert_tensors_added") == 294912
    and data.get("quantization_config_source") == "mazinb-modelopt-nvfp4"
    and data.get("mtp_tensors_changed") == 0
)
raise SystemExit(0 if ok else 1)
PY
    return
  fi

  if [[ "${PROFILE_CASE}" == hybrid-residual || "${PROFILE_CASE}" == hybrid-group0 ]]; then
    local manifest="${MODEL_DIR}/.qwen38-hybrid-manifest.json"
    [[ -r "${manifest}" ]] || return 1
    python3 - "${manifest}" "${BASE_MODEL_REVISION}" "${PROFILE_CASE}" <<'PY' >/dev/null
import json, sys
path, expected_base, profile = sys.argv[1:]
data = json.load(open(path, encoding="utf-8"))
expected = (
    ("group0-bf16", 300, 0)
    if profile == "hybrid-group0"
    else ("residual-bf16", 96, 204)
)
variant, count, remaining = expected
selected = data.get("selected_modules", data.get("residual_modules"))
ok = (
    data.get("status") == "complete"
    and data.get("variant") == variant
    and data.get("base_revision") == expected_base
    and bool(data.get("overlay_revision"))
    and selected == count
    and data.get("fp8_targets_removed") == count
    and data.get("fp8_scales_removed") == count
    and data.get("bf16_weights_overlaid") == count
    and data.get("mtp_tensors_changed") == 0
    and data.get("remaining_fp8_group0_targets") == remaining
)
raise SystemExit(0 if ok else 1)
PY
    return
  fi

  return 0
}

service_active() {
  command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet "${SERVICE}" 2>/dev/null
}

container_running() {
  local name="$1"
  [[ "$(docker inspect --format '{{.State.Running}}' "${name}" 2>/dev/null || true)" == true ]]
}

port_owner() {
  docker ps --filter "publish=${PORT}" --format '{{.Names}}' 2>/dev/null | paste -sd, -
}

port_in_use() {
  local owner
  owner="$(port_owner)"
  [[ -n "${owner}" ]] && return 0
  command -v ss >/dev/null 2>&1 || return 1
  ss -H -ltn 2>/dev/null | awk -v suffix=":${PORT}" '$4 ~ suffix "$" {found=1} END {exit !found}'
}

preflight() {
  local failures=0
  load_source || return 1
  printf 'vLLM v0.29 checkpoint preflight (%s)\n' "${PROFILE_CASE}"
  printf '  model repo      : %s\n' "${MODEL_REPO}"
  printf '  model revision  : %s\n' "${MODEL_REVISION}"
  if [[ -f "${MODEL_DIR}/model.safetensors.index.json" ]] && source_manifest_ok; then
    printf '  weights         : ready (%s)\n' "${MODEL_DIR}"
  else
    printf '  weights         : missing (%s)\n' "${MODEL_DIR}"
    failures=1
  fi
  if docker image inspect "${IMAGE}" >/dev/null 2>&1; then
    printf '  image           : ready (%s)\n' "${IMAGE}"
  else
    printf '  image           : missing (%s)\n' "${IMAGE}"
    if [[ "${PROFILE_CASE}" == hybrid-h9-ct-modelweight ]]; then
      printf '    build with    : docker build --no-cache -t %s -f scripts/Dockerfile.v029-h9-ct-modelweight-scale scripts/\n' "${IMAGE}"
    else
      printf '    build with    : docker build -t %s -f scripts/Dockerfile.v029-orcarouter scripts/\n' "${IMAGE}"
    fi
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
  printf '  API port %s     : ' "${PORT}"
  if port_in_use; then
    owner="$(port_owner)"
    if [[ -n "${owner}" ]]; then
      printf 'occupied by %s\n' "${owner}"
    else
      printf 'occupied by another listener\n'
    fi
    failures=1
  else
    printf 'free\n'
  fi
  return "${failures}"
}

start_runtime() {
  load_source
  command -v docker >/dev/null 2>&1 || { printf 'ERROR: docker is required\n' >&2; exit 1; }
  service_active && { printf 'ERROR: %s is active; stop it before this experiment\n' "${SERVICE}" >&2; exit 1; }
  container_running qwen38-flash-next && { printf 'ERROR: canonical runtime is still running\n' >&2; exit 1; }
  docker inspect "${NAME}" >/dev/null 2>&1 && { printf 'ERROR: experiment container already exists: %s\n' "${NAME}" >&2; exit 1; }
  if port_in_use; then
    owner="$(port_owner)"
    if [[ -n "${owner}" ]]; then
      printf 'ERROR: 127.0.0.1:%s is already published by container(s): %s\n' "${PORT}" "${owner}" >&2
    else
      printf 'ERROR: 127.0.0.1:%s is already in use by another listener\n' "${PORT}" >&2
    fi
    exit 1
  fi
  docker image inspect "${IMAGE}" >/dev/null 2>&1 || { printf 'ERROR: image missing: %s\n' "${IMAGE}" >&2; exit 1; }
  h9_image_ok || { printf 'ERROR: stale or incompatible H9 image: %s; rebuild from current main\n' "${IMAGE}" >&2; exit 1; }
  [[ -f "${MODEL_DIR}/model.safetensors.index.json" ]] || { printf 'ERROR: checkpoint index missing: %s\n' "${MODEL_DIR}" >&2; exit 1; }
  source_manifest_ok || { printf 'ERROR: checkpoint manifest is incomplete or inconsistent for profile %s\n' "${PROFILE_CASE}" >&2; exit 1; }

  local split
  split='["vllm::unified_attention_with_output","vllm::unified_mla_attention_with_output","vllm::mamba_mixer2","vllm::mamba_mixer","vllm::short_conv","vllm::qwen4_exp_compute_ple_ngram_ids","vllm::qwen4_exp_ple_short_conv","vllm::qwen4_exp_qsa_with_output","vllm::linear_attention","vllm::qwen_gdn_attention_core","vllm::qwen_gdn_attention_core_fused_norm_packed","vllm::sparse_attn_indexer","vllm::ple_mmap_lookup_ids"]'

  mkdir -p "${HOME}/.cache/vllm-qwen38-v029" "${HOME}/.cache/flashinfer-v029"

  extra_mount=()
  if [[ "${PROFILE_CASE}" == hybrid-h7-group-metadata || "${PROFILE_CASE}" == hybrid-h6-w4a16 ]]; then
    H5_MODEL_DIR="${H5_NEUTRAL_INPUT_MODEL_DIR:-$HOME/models/qwen3.8-h5-neutral-input-scale}"
    H4_ALL_MODEL_DIR="${H4_ORCA_ALL_MODEL_DIR:-$HOME/models/qwen3.8-h4-orca-all}"
    H3_MODEL_DIR="${HYBRID_QUANT_LAYOUT_MODEL_DIR:-$HOME/models/qwen3.8-hybrid-quant-layout}"
    [[ -d "${BASE_MODEL_DIR}" ]] || { printf 'ERROR: OrcaRouter base model directory missing: %s\n' "${BASE_MODEL_DIR}" >&2; exit 1; }
    [[ -d "${H5_MODEL_DIR}" ]] || { printf 'ERROR: H5 parent missing: %s\n' "${H5_MODEL_DIR}" >&2; exit 1; }
    [[ -d "${H4_ALL_MODEL_DIR}" ]] || { printf 'ERROR: H4 all parent missing: %s\n' "${H4_ALL_MODEL_DIR}" >&2; exit 1; }
    [[ -d "${H3_MODEL_DIR}" ]] || { printf 'ERROR: H3 parent model directory missing: %s\n' "${H3_MODEL_DIR}" >&2; exit 1; }
    extra_mount=(
      -v "${BASE_MODEL_DIR}:/base-model:ro"
      -v "${H3_MODEL_DIR}:/h3-model:ro"
      -v "${H4_ALL_MODEL_DIR}:/h4-all:ro"
      -v "${H5_MODEL_DIR}:/h5-parent:ro"
    )
  elif [[ "${PROFILE_CASE}" == hybrid-h5-neutral-input ]]; then
    H4_ALL_MODEL_DIR="${H4_ORCA_ALL_MODEL_DIR:-$HOME/models/qwen3.8-h4-orca-all}"
    H3_MODEL_DIR="${HYBRID_QUANT_LAYOUT_MODEL_DIR:-$HOME/models/qwen3.8-hybrid-quant-layout}"
    [[ -d "${BASE_MODEL_DIR}" ]] || { printf 'ERROR: OrcaRouter base model directory missing: %s\n' "${BASE_MODEL_DIR}" >&2; exit 1; }
    [[ -d "${H4_ALL_MODEL_DIR}" ]] || { printf 'ERROR: H4 all parent missing: %s\n' "${H4_ALL_MODEL_DIR}" >&2; exit 1; }
    [[ -d "${H3_MODEL_DIR}" ]] || { printf 'ERROR: H3 parent model directory missing: %s\n' "${H3_MODEL_DIR}" >&2; exit 1; }
    extra_mount=(
      -v "${BASE_MODEL_DIR}:/base-model:ro"
      -v "${H4_ALL_MODEL_DIR}:/h4-all:ro"
      -v "${H3_MODEL_DIR}:/h3-model:ro"
    )
  elif [[ "${PROFILE_CASE}" == hybrid-h4-down || "${PROFILE_CASE}" == hybrid-h4-gate-up || "${PROFILE_CASE}" == hybrid-h4-all ]]; then
    H3_MODEL_DIR="${HYBRID_QUANT_LAYOUT_MODEL_DIR:-$HOME/models/qwen3.8-hybrid-quant-layout}"
    [[ -d "${BASE_MODEL_DIR}" ]] || { printf 'ERROR: hybrid base model directory missing: %s\n' "${BASE_MODEL_DIR}" >&2; exit 1; }
    [[ -d "${H3_MODEL_DIR}" ]] || { printf 'ERROR: H3 parent model directory missing: %s\n' "${H3_MODEL_DIR}" >&2; exit 1; }
    extra_mount=(-v "${BASE_MODEL_DIR}:/base-model:ro" -v "${H3_MODEL_DIR}:/h3-model:ro")
  elif [[ "${PROFILE_CASE}" == hybrid-residual || "${PROFILE_CASE}" == hybrid-group0 || "${PROFILE_CASE}" == hybrid-quant-layout ]]; then
    [[ -d "${BASE_MODEL_DIR}" ]] || { printf 'ERROR: hybrid base model directory missing: %s\n' "${BASE_MODEL_DIR}" >&2; exit 1; }
    extra_mount=(-v "${BASE_MODEL_DIR}:/base-model:ro")
  fi

  docker run -d     --name "${NAME}"     --init     --user root     --restart no     --gpus all     --ipc host     --shm-size=32g     --ulimit memlock=-1:-1     --ulimit stack=67108864     -p "127.0.0.1:${PORT}:8000"     -e VLLM_TARGET_DEVICE=cuda     -e CUTE_DSL_ARCH=sm_121a     -e VLLM_PLE_MMAP=1     -e VLLM_PLE_MMAP_DIR=/model     -e VLLM_PLE_MMAP_WORKERS=32     -e VLLM_PLE_MMAP_PREWARM=0     -e VLLM_PLE_MMAP_MADVISE=random     -e VLLM_PLE_MMAP_FAST_ROWS=0     -e VLLM_QSA_EXACT_TOPK=1     -e QWEN38_VLLM_BASE=v0.29     -e QWEN38_GB10_FLA_FIX=1     -e QWEN38_PLE_MMAP=1     -e FLASHINFER_DISABLE_VERSION_CHECK=1     "${extra_mount[@]}"     -v "${MODEL_DIR}:/model:ro"     -v "${HOME}/.cache/vllm-qwen38-v029:/root/.cache/vllm"     -v "${HOME}/.cache/flashinfer-v029:/root/.cache/flashinfer"     "${IMAGE}"     /model       --served-model-name "${SERVED_NAME}"       --host 0.0.0.0       --port 8000       --load-format safetensors       --max-model-len 262144       --max-num-seqs 3       --gpu-memory-utilization 0.80       --kv-cache-memory-bytes 25769803776       --kv-cache-dtype auto       --no-enable-prefix-caching       --enable-chunked-prefill       --max-num-batched-tokens 8192       -cc.cudagraph_mode=PIECEWISE       "-cc.splitting_ops=${split}"       --no-enable-flashinfer-autotune       --enable-auto-tool-choice       --tool-call-parser qwen3_coder       --reasoning-parser qwen3       --speculative-config '{"method":"mtp","num_speculative_tokens":2}'

  sleep 8
  local state
  state="$(docker inspect --format '{{.State.Status}} exit={{.State.ExitCode}} oom={{.State.OOMKilled}}' "${NAME}" 2>/dev/null || true)"
  if [[ "${state}" != running* ]]; then
    printf 'ERROR: %s failed to stay running (%s)\n' "${NAME}" "${state}" >&2
    docker logs --tail 80 "${NAME}" 2>&1 >&2 || true
    return 1
  fi

  printf 'container started; readiness pending: %s (profile=%s, vLLM v0.29, PLE mmap, exact QSA, GB10 FLA fix, MTP k=2)\n' "${NAME}" "${PROFILE_CASE}"
  printf 'wait with: ./scripts/wait-ready.sh --container %s --model %s\n' "${NAME}" "${SERVED_NAME}"
}

case "${ACTION}" in
  preflight)
    preflight
    ;;
  start)
    start_runtime
    ;;
  stop)
    if docker inspect "${NAME}" >/dev/null 2>&1; then
      docker rm -f "${NAME}" >/dev/null
      printf 'removed experimental container: %s\n' "${NAME}"
    else
      printf 'experimental container is absent: %s\n' "${NAME}"
    fi
    ;;
  status)
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
