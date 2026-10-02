#!/bin/bash
# Serve supported Qwen3.8-Flash-Next profiles on one DGX Spark (GB10 / sm_121a).
#
# PLE handling is profile-specific:
#   - orcarouter / nvidia keep the legacy CPU-offload managed path;
#   - mazinb and orcarouter-hybrid use the validated vLLM v0.29 PLE mmap path
#     and exact-QSA fallback.
#
# Keep profile defaults explicit below. Do not silently make experimental runtime flags
# global because the published checkpoints differ in PLE representation and runtime image.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# vllm-nv-mixed:v2 = skinny-GEMM + patch-nv-mixed.py. Both are required: the official
# checkpoint declares quant_algo=MIXED_PRECISION, which the pinned image cannot load
# (PLE) and cannot draft with (FP8_PB_WO MTP). Build both Dockerfiles in scripts/ first.
MODEL_PROFILE="${MODEL_PROFILE:-nvidia}"
MODEL_ROOT="${QWEN38_MODEL_ROOT:-${HOME}/models}"
DEFAULT_QSA_EXACT_TOPK=0
PLE_MODE=cpu-offload
KV_MEMORY_FLAG=--kv-cache-memory
VLLM_CACHE_DIR="${HOME}/.cache/vllm-qwen38"
FLASHINFER_CACHE_DIR="${HOME}/.cache/flashinfer"
HYBRID_MOUNTS=()
case "${MODEL_PROFILE}" in
  orcarouter)
    IMAGE="${VLLM_IMAGE:-vllm/vllm-openai:qwen38-flash-next-arm64-cu130}"
    MODEL_DIR="${MODEL_DIR:-${MODEL_ROOT}/qwen3.8-flash-next-orcarouter}"
    DEFAULT_MAXLEN=262144; DEFAULT_NSPEC=2; DEFAULT_INDEX_SHARE=0
    DEFAULT_GPU_UTIL=0.85; DEFAULT_KV_MEM=25769803776; DEFAULT_MAXSEQS=3; DEFAULT_AUTOTUNE=0
    SERVED_NAME="${SERVED_NAME:-orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4}"
    ;;
  nvidia)
    IMAGE="${VLLM_IMAGE:-vllm-nv-mixed:v2}"
    MODEL_DIR="${MODEL_DIR:-${MODEL_ROOT}/qwen3.8-flash-next-nvidia}"
    DEFAULT_MAXLEN=524288; DEFAULT_NSPEC=3; DEFAULT_INDEX_SHARE=1
    DEFAULT_GPU_UTIL=0.78; DEFAULT_KV_MEM=16106127360; DEFAULT_MAXSEQS=8; DEFAULT_AUTOTUNE=1
    SERVED_NAME="${SERVED_NAME:-qwen3.8-flash-next}"
    ;;
  mazinb)
    IMAGE="${VLLM_IMAGE:-vllm-orcarouter-v029:v1}"
    MODEL_DIR="${MODEL_DIR:-${MODEL_ROOT}/qwen3.8-flash-next-mazinb}"
    DEFAULT_MAXLEN=262144; DEFAULT_NSPEC=2; DEFAULT_INDEX_SHARE=0
    # 2026-10-02 controlled A/B: 16 GiB passed strict readiness/soak/host checks;
    # 24 GiB reproduced RM NV_ERR_NO_MEMORY and a five-sample protected stop.
    DEFAULT_GPU_UTIL=0.80; DEFAULT_KV_MEM=17179869184; DEFAULT_MAXSEQS=3; DEFAULT_AUTOTUNE=0
    DEFAULT_QSA_EXACT_TOPK=1
    PLE_MODE=mmap
    KV_MEMORY_FLAG=--kv-cache-memory-bytes
    VLLM_CACHE_DIR="${HOME}/.cache/vllm-qwen38-v029"
    FLASHINFER_CACHE_DIR="${HOME}/.cache/flashinfer-v029"
    SERVED_NAME="${SERVED_NAME:-mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4}"
    ;;
  orcarouter-hybrid)
    IMAGE="${VLLM_IMAGE:-vllm-orcarouter-v029:v1}"
    MODEL_DIR="${MODEL_DIR:-${MODEL_ROOT}/qwen3.8-h6-modelopt-w4a16}"
    DEFAULT_MAXLEN=262144; DEFAULT_NSPEC=2; DEFAULT_INDEX_SHARE=0
    DEFAULT_GPU_UTIL=0.80; DEFAULT_KV_MEM=25769803776; DEFAULT_MAXSEQS=3; DEFAULT_AUTOTUNE=0
    DEFAULT_QSA_EXACT_TOPK=1
    PLE_MODE=mmap
    KV_MEMORY_FLAG=--kv-cache-memory-bytes
    VLLM_CACHE_DIR="${HOME}/.cache/vllm-qwen38-v029"
    FLASHINFER_CACHE_DIR="${HOME}/.cache/flashinfer-v029"
    HYBRID_MODEL_ROOT="${QWEN38_MODEL_ROOT:-$(dirname -- "${MODEL_DIR}")}"
    HYBRID_BASE_DIR="${ORCAROUTER_MODEL_DIR:-${HYBRID_MODEL_ROOT}/qwen3.8-flash-next-orcarouter}"
    HYBRID_H3_DIR="${HYBRID_QUANT_LAYOUT_MODEL_DIR:-${HYBRID_MODEL_ROOT}/qwen3.8-hybrid-quant-layout}"
    HYBRID_H4_DIR="${H4_ORCA_ALL_MODEL_DIR:-${HYBRID_MODEL_ROOT}/qwen3.8-h4-orca-all}"
    HYBRID_H5_DIR="${H5_NEUTRAL_INPUT_MODEL_DIR:-${HYBRID_MODEL_ROOT}/qwen3.8-h5-neutral-input-scale}"
    for hybrid_dir in "${HYBRID_BASE_DIR}" "${HYBRID_H3_DIR}" "${HYBRID_H4_DIR}" "${HYBRID_H5_DIR}"; do
      [[ -d "${hybrid_dir}" ]] || { echo "FATAL: hybrid parent checkpoint missing: ${hybrid_dir}" >&2; exit 1; }
    done
    HYBRID_MOUNTS=(
      -v "${HYBRID_BASE_DIR}:/base-model:ro"
      -v "${HYBRID_H3_DIR}:/h3-model:ro"
      -v "${HYBRID_H4_DIR}:/h4-all:ro"
      -v "${HYBRID_H5_DIR}:/h5-parent:ro"
    )
    SERVED_NAME="${SERVED_NAME:-orcarouter-hybrid/Qwen3.8-Flash-Next-Uncensored-NVFP4}"
    ;;
  *) echo "FATAL: unknown MODEL_PROFILE=${MODEL_PROFILE}" >&2; exit 2 ;;
esac
NAME="${NAME:-qwen38-flash-next}"
PORT="${PORT:-8888}"
CONFIG_OVERRIDE="${CONFIG_OVERRIDE:-}"
MONITOR_PROTECT="${MONITOR_PROTECT:-0}"
MONITOR_ENABLED="${MONITOR_ENABLED:-${MONITOR_PROTECT}}"
MONITOR_MIN_AVAILABLE_GIB="${MONITOR_MIN_AVAILABLE_GIB:-6}"
MONITOR_MIN_FREE_GIB="${MONITOR_MIN_FREE_GIB:-2}"
MONITOR_FREE_GATE_GIB="${MONITOR_FREE_GATE_GIB:-10}"
MONITOR_MIN_SWAP_FREE_GIB="${MONITOR_MIN_SWAP_FREE_GIB:-8}"
MONITOR_CONSECUTIVE="${MONITOR_CONSECUTIVE:-5}"
MONITOR_HEARTBEAT="${MONITOR_HEARTBEAT:-60}"
STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/qwen38-spark"
MONITOR_PID_FILE="${STATE_DIR}/monitor.pid"
MONITOR_LOG="${STATE_DIR}/monitor.log"
RESTART_POLICY="${RESTART_POLICY:-on-failure:3}"
PUBLISH_HOST="${PUBLISH_HOST:-127.0.0.1}"
[[ "${MONITOR_PROTECT}" == 0 || "${MONITOR_PROTECT}" == 1 ]] || {
  echo "FATAL: MONITOR_PROTECT must be 0 or 1" >&2; exit 2; }
[[ "${RESTART_POLICY}" =~ ^(no|always|unless-stopped|on-failure(:[1-9][0-9]*)?)$ ]] || {
  echo "FATAL: invalid RESTART_POLICY=${RESTART_POLICY}" >&2; exit 2; }
[[ "${PUBLISH_HOST}" == 127.0.0.1 || "${PUBLISH_HOST}" == 0.0.0.0 ]] || {
  echo "FATAL: unsupported PUBLISH_HOST=${PUBLISH_HOST}" >&2; exit 2; }

# Legacy CPU PLE offload requires the multiproc executor even at TP=1. mazinb's
# v0.29 mmap path does not depend on PleOffloadWorker, but keeping mp as the managed
# default is compatible with the existing service lifecycle and avoids changing another
# runtime variable during installer promotion.
EXECUTOR="${EXECUTOR:-mp}"

# Context. The card documents YaRN to 1M; factor 4.0 x 262144 = 1048576 exactly.
# 524288 is the default here because it is both roomier and FASTER than 1M on this box:
# 1M costs 31.9 GiB of KV against 14-16, and the RAM that frees becomes page cache for
# the PLE table, so n-gram lookups hit RAM more often. Measured 30.0 tok/s at 512K
# against 27.4 at 1M.
MAXLEN="${MAXLEN:-${DEFAULT_MAXLEN}}"
ROPE="${ROPE:-yarn}"
ROPE_ARGS=()
LONG_ENV=()
if [[ "${ROPE}" != "none" && "${MAXLEN}" -gt 262144 ]]; then
  factor=$(python3 -c "print(f'{${MAXLEN}/262144:.1f}')")
  ROPE_ARGS=(--hf-overrides "{\"text_config\":{\"rope_parameters\":{\"mrope_interleaved\":true,\"mrope_section\":[11,11,10],\"rope_type\":\"yarn\",\"rope_theta\":10000000,\"partial_rotary_factor\":0.25,\"factor\":${factor},\"original_max_position_embeddings\":262144}}}")
  LONG_ENV=(-e VLLM_ALLOW_LONG_MAX_MODEL_LEN=1)
fi

# MTP lives in the checkpoint and vLLM derives the draft config from the target.
#
# k IS CHECKPOINT-SPECIFIC. Do not carry a value over from another build. On Inferact,
# k=3 measured net -3.0% against k=2. On the official checkpoint the FP8-block drafter is
# stronger and the whole curve shifts one notch:
#     k=2  13.26 steps/s  acc 2.14  ->  28.31 tok/s
#     k=3  11.90 steps/s  acc 2.78  ->  33.02 tok/s   <-- default
#     k=4  10.37 steps/s  acc 2.76  ->  28.66 tok/s   acceptance saturates, cost does not
#   SPEC=none ./serve.sh    # unspeculated baseline, 17.4 tok/s
NSPEC="${NSPEC:-${DEFAULT_NSPEC}}"
case "${SPEC:-mtp}" in
  mtp)  # INDEX_SHARE maps to set_skip_topk: MTP step 0 picks the QSA sparse indices and
        # later steps reuse them. Profiler puts QSA under 5% of decode, so the ceiling is
        # small; it was enabled alongside k=3 and never measured on its own.
        if [[ "${INDEX_SHARE:-${DEFAULT_INDEX_SHARE}}" == "1" ]]; then
          SPEC_CFG="{\"method\":\"mtp\",\"num_speculative_tokens\":${NSPEC},\"index_share_for_mtp_iteration\":true}"
        else
          SPEC_CFG="{\"method\":\"mtp\",\"num_speculative_tokens\":${NSPEC}}"
        fi ;;
  none) SPEC_CFG='' ;;
  *)    SPEC_CFG="${SPEC}" ;;
esac
SPEC_ARGS=()
[[ -n "${SPEC_CFG}" ]] && SPEC_ARGS=(--speculative-config "${SPEC_CFG}")

# KV dtype is NOT tunable on the stock image: models/qwen3_8_flash_next/nvidia/qsa.py
# declares supported_kv_cache_dtypes = ["auto", "bfloat16"] and raises
# NotImplementedError("Qwen3.8-Flash-Next QSA requires a BF16 main KV cache").
# It is patchable -- see the README's comparison section -- but not from here.
KV_DTYPE="${KV_DTYPE:-}"
KV_ARGS=()
[[ -n "${KV_DTYPE}" ]] && KV_ARGS=(--kv-cache-dtype "${KV_DTYPE}")

# Measured on this box: consumed (weights + non-torch + activation + graphs) settles at
# ~77.5 GiB, so KV = GPU_UTIL x 121.69 - 77.5. KV costs ~28.4 KiB/token with MTP.
# 0.78 -> ~16 GiB of KV, comfortably above the 14.2 GiB one 524288 request needs, and
# leaves ~15 GiB of RAM as PLE page cache. Raising it starves that cache; 0.63 already
# left KV at 0.21 GiB and refused to boot.
GPU_UTIL="${GPU_UTIL:-${DEFAULT_GPU_UTIL}}"
MAXSEQS="${MAXSEQS:-${DEFAULT_MAXSEQS}}"

# Pin the KV pool: vLLM derives it from a runtime measurement that wobbles on unified
# memory (three boots of one config gave 573,862 / 591,889 / 614,423 tokens). 15.0 GiB
# leaves ~5% over the 14.3 GiB one 524288 request needs. KV_MEM= restores the old behaviour.
KV_MEM="${KV_MEM-${DEFAULT_KV_MEM}}"
KVMEM_ARGS=()
[[ -n "${KV_MEM}" ]] && KVMEM_ARGS=("${KV_MEMORY_FLAG}" "${KV_MEM}")

# Prefix caching needs BOTH flags on this hybrid model: without align the GDN state is not
# cacheable and the hit rate is 0 regardless of traffic. With align the attention block
# size becomes 1600 tokens, so only prompts longer than that can hit. Off by default
# because it only pays on repeated prefixes; see the README.
PREFIX_CACHE="${PREFIX_CACHE:-0}"
PREFIX_ARGS=(--no-enable-prefix-caching)
[[ "${PREFIX_CACHE}" == "1" ]] && PREFIX_ARGS=(--enable-prefix-caching --mamba-cache-mode align)

# NEVER enable --async-scheduling with MTP: it makes _prepare_ngram_context read the
# optimistic -1 placeholders speculative decoding writes, so the n-gram context is wrong on
# every decode step. Silent quality loss, no crash. See the README.

# Loading 95.37 GiB into the offload process, most of it straight back out to swap, does
# not finish inside the 600 s default.
PLE_TIMEOUT="${PLE_TIMEOUT:-1800}"

# FlashInfer autotune. The stock setting was off, with no recorded reason. On by default
# now: the MoE backend resolves to FLASHINFER_CUTLASS and its grouped GEMM is 18.7% of
# decode by profiler. Enabled alongside k=3 and never measured on its own. AUTOTUNE=0
# reverts. Costs extra boot time while it sweeps.
AUTOTUNE_ARGS=(--enable-flashinfer-autotune)
[[ "${AUTOTUNE:-${DEFAULT_AUTOTUNE}}" == "1" ]] || AUTOTUNE_ARGS=(--no-enable-flashinfer-autotune)

# Deterministic QSA top-k experiment. The stock image has no deterministic kernel
# extension, so this is opt-in and only valid with an image that contains
# /opt/qwen38/kernel-det/_C_det.so and the qsa.py wiring.
QSA_DET_TOPK="${QSA_DET_TOPK:-0}"
QSA_DET_ENV=(-e VLLM_QSA_DET_TOPK=0)
if [[ "${QSA_DET_TOPK}" == "1" ]]; then
  QSA_DET_ENV=(-e VLLM_QSA_DET_TOPK=1 -e VLLM_QSA_DET_LIB=/opt/qwen38/kernel-det/_C_det.so)
fi

QSA_EXACT_TOPK="${QSA_EXACT_TOPK:-${DEFAULT_QSA_EXACT_TOPK}}"
QSA_EXACT_ENV=(-e VLLM_QSA_EXACT_TOPK="${QSA_EXACT_TOPK}")

PLE_ENV=(-e VLLM_PLE_CPU_OFFLOAD=1 -e VLLM_PLE_OFFLOAD_READY_TIMEOUT="${PLE_TIMEOUT}")
V029_ARGS=()
if [[ "${PLE_MODE}" == mmap ]]; then
  PLE_ENV=(
    -e VLLM_PLE_MMAP=1
    -e VLLM_PLE_MMAP_DIR=/model
    -e VLLM_PLE_MMAP_WORKERS=32
    -e VLLM_PLE_MMAP_PREWARM=0
    -e VLLM_PLE_MMAP_MADVISE=random
    -e VLLM_PLE_MMAP_FAST_ROWS=0
  )
  V029_SPLITTING_OPS='["vllm::unified_attention_with_output","vllm::unified_mla_attention_with_output","vllm::mamba_mixer2","vllm::mamba_mixer","vllm::short_conv","vllm::qwen4_exp_compute_ple_ngram_ids","vllm::qwen4_exp_ple_short_conv","vllm::qwen4_exp_qsa_with_output","vllm::linear_attention","vllm::qwen_gdn_attention_core","vllm::qwen_gdn_attention_core_fused_norm_packed","vllm::sparse_attn_indexer","vllm::ple_mmap_lookup_ids"]'
  V029_ARGS=(
    --load-format safetensors
    -cc.cudagraph_mode=PIECEWISE
    "-cc.splitting_ops=${V029_SPLITTING_OPS}"
  )
fi

[[ -f "${MODEL_DIR}/model.safetensors.index.json" ]] || {
  echo "FATAL: weights missing at ${MODEL_DIR} -- run ./download-weights.sh first" >&2; exit 1; }
swapon --show=NAME --noheadings | grep -q . || {
  echo "FATAL: no swap is active. The PLE table has nowhere to page out to and the load" >&2
  echo "  will OOM. Add ~128 GiB, e.g.:" >&2
  echo "    sudo fallocate -l 128G /swap-ple.img && sudo chmod 600 /swap-ple.img" >&2
  echo "    sudo mkswap /swap-ple.img && sudo swapon -p 10 /swap-ple.img" >&2
  exit 1; }
docker image inspect "${IMAGE}" >/dev/null 2>&1 || {
  echo "FATAL: image ${IMAGE} not present -- docker pull ${IMAGE}" >&2; exit 1; }

if [[ "${MODEL_PROFILE}" == orcarouter && -z "${CONFIG_OVERRIDE}" ]]; then
  CONFIG_OVERRIDE="${STATE_DIR}/config.vllm.json"
  python3 "${SCRIPT_DIR}/prepare-config.py" --model-dir "${MODEL_DIR}" --output "${CONFIG_OVERRIDE}"
fi

CONFIG_MOUNT=()
if [[ -n "${CONFIG_OVERRIDE}" ]]; then
  [[ -f "${CONFIG_OVERRIDE}" ]] || { echo "FATAL: config override not found: ${CONFIG_OVERRIDE}" >&2; exit 1; }
  CONFIG_MOUNT=(-v "${CONFIG_OVERRIDE}:/model/config.json:ro")
fi
mkdir -p "${FLASHINFER_CACHE_DIR}" "${VLLM_CACHE_DIR}"

# Direct/manual invocation must never destroy an existing canonical runtime. Managed
# replacement first preserves the old container under the rollback name, leaving this
# canonical name free before serve.sh is invoked.
if docker inspect "${NAME}" >/dev/null 2>&1; then
  echo "FATAL: runtime container already exists: ${NAME}; use the managed update/restart path" >&2
  exit 1
fi

docker run -d \
  --name "${NAME}" \
  --init \
  --user root \
  -p "${PUBLISH_HOST}:${PORT}:${PORT}" \
  --restart "${RESTART_POLICY}" \
  --shm-size=32g \
  --ulimit memlock=-1:-1 \
  --ulimit stack=67108864 \
  --cap-add=IPC_LOCK \
  --cap-add=SYS_PTRACE \
  --ipc host \
  --gpus all \
  --workdir /workspace \
  -e VLLM_TARGET_DEVICE=cuda \
  -e CUTE_DSL_ARCH=sm_121a \
  "${PLE_ENV[@]}" \
  -e FLASHINFER_DISABLE_VERSION_CHECK=1 \
  "${QSA_DET_ENV[@]}" \
  "${QSA_EXACT_ENV[@]}" \
  "${LONG_ENV[@]}" \
  "${HYBRID_MOUNTS[@]}" \
  -v "${MODEL_DIR}:/model:ro" \
  "${CONFIG_MOUNT[@]}" \
  -v "${FLASHINFER_CACHE_DIR}:/root/.cache/flashinfer" \
  -v "${VLLM_CACHE_DIR}:/root/.cache/vllm" \
  "${IMAGE}" \
  /model \
    --served-model-name "${SERVED_NAME}" \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --tensor-parallel-size 1 \
    --distributed-executor-backend "${EXECUTOR}" \
    --trust-remote-code \
    "${V029_ARGS[@]}" \
    "${KV_ARGS[@]}" \
    --gpu-memory-utilization "${GPU_UTIL}" \
    "${KVMEM_ARGS[@]}" \
    --max-model-len "${MAXLEN}" \
    "${ROPE_ARGS[@]}" \
    --max-num-seqs "${MAXSEQS}" \
    --max-num-batched-tokens "${BATCHED_TOKENS:-8192}" \
    --enable-chunked-prefill \
    --no-async-scheduling \
    "${PREFIX_ARGS[@]}" \
    "${AUTOTUNE_ARGS[@]}" \
    --enable-auto-tool-choice \
    --tool-call-parser qwen3_coder \
    --reasoning-parser qwen3 \
    --limit-mm-per-prompt '{"image":4}' \
    "${SPEC_ARGS[@]}"

if [[ "${MONITOR_ENABLED}" == 1 ]]; then
  mkdir -p "${STATE_DIR}"
  if [[ -r "${MONITOR_PID_FILE}" ]]; then
    old_pid="$(<"${MONITOR_PID_FILE}")"
    if [[ "${old_pid}" =~ ^[0-9]+$ && -r "/proc/${old_pid}/cmdline" ]] && \
       tr '\0' ' ' < "/proc/${old_pid}/cmdline" | grep -Fq 'monitor-runtime.sh'; then
      kill "${old_pid}" 2>/dev/null || true
    fi
  fi
  monitor_args=(--container "${NAME}" --min-available-gib "${MONITOR_MIN_AVAILABLE_GIB}" \
    --min-free-gib "${MONITOR_MIN_FREE_GIB}" --free-gate-gib "${MONITOR_FREE_GATE_GIB}" \
    --min-swap-free-gib "${MONITOR_MIN_SWAP_FREE_GIB}" --consecutive "${MONITOR_CONSECUTIVE}" \
    --heartbeat "${MONITOR_HEARTBEAT}")
  [[ "${MONITOR_PROTECT}" == 1 ]] && monitor_args+=(--protect)
  nohup "${SCRIPT_DIR}/monitor-runtime.sh" "${monitor_args[@]}" \
    >>"${MONITOR_LOG}" 2>&1 &
  monitor_pid=$!
  printf '%s\n' "${monitor_pid}" > "${MONITOR_PID_FILE}"
  echo "memory monitor started (protect=${MONITOR_PROTECT}, pid=${monitor_pid}, log=${MONITOR_LOG})"
fi

echo "started ${NAME} (profile=${MODEL_PROFILE}, executor=${EXECUTOR}, PLE=${PLE_MODE}, SPEC=${SPEC:-mtp}${SPEC_CFG:+ k=${NSPEC}}, qsa_det_topk=${QSA_DET_TOPK}, qsa_exact_topk=${QSA_EXACT_TOPK}, maxlen=${MAXLEN}, util=${GPU_UTIL})"
echo "follow with:  docker logs -f ${NAME}"
echo "watch memory: watch -n5 'free -g; swapon --show'"
echo
echo "Expect ~10 min to load and a further ~3 min of PLE paging before the API answers."
