#!/bin/bash
# Serve Qwen3.8-Flash-Next NVFP4 on a single DGX Spark (GB10 / sm_121a, 121 GiB unified),
# with the 51B n-gram (PLE) embedding table offloaded to swap.
#
# Updated 2026-09-06 for nvidia/Qwen3.8-Flash-Next-NVFP4. See ../README.md.
#
# The checkpoint is 123.6 GiB on a 121 GiB box. 47.7 GiB of it is one tensor -- the n-gram
# embedding table, FP8 in the official build -- and that tensor is a pure lookup: each
# token reads 18 rows out of 320 million.
# VLLM_PLE_CPU_OFFLOAD=1 hands it to a dedicated CPU process which gathers on CPU and DMAs
# the result to the GPU worker. It is ordinary pageable memory, so the kernel pages the
# cold rows out to swap. Measured cost: ~73 KiB of page-ins per decoded token.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# vllm-nv-mixed:v2 = skinny-GEMM + patch-nv-mixed.py. Both are required: the official
# checkpoint declares quant_algo=MIXED_PRECISION, which the pinned image cannot load
# (PLE) and cannot draft with (FP8_PB_WO MTP). Build both Dockerfiles in scripts/ first.
MODEL_PROFILE="${MODEL_PROFILE:-nvidia}"
case "${MODEL_PROFILE}" in
  orcarouter)
    IMAGE="${VLLM_IMAGE:-vllm/vllm-openai:qwen38-flash-next-arm64-cu130}"
    MODEL_DIR="${MODEL_DIR:-$HOME/models/qwen3.8-flash-next-orcarouter}"
    DEFAULT_MAXLEN=262144; DEFAULT_NSPEC=2; DEFAULT_INDEX_SHARE=0
    DEFAULT_GPU_UTIL=0.85; DEFAULT_KV_MEM=25769803776; DEFAULT_MAXSEQS=3; DEFAULT_AUTOTUNE=0
    SERVED_NAME="${SERVED_NAME:-orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4}"
    ;;
  nvidia)
    IMAGE="${VLLM_IMAGE:-vllm-nv-mixed:v2}"
    MODEL_DIR="${MODEL_DIR:-$HOME/models/qwen3.8-flash-next-nvidia}"
    DEFAULT_MAXLEN=524288; DEFAULT_NSPEC=3; DEFAULT_INDEX_SHARE=1
    DEFAULT_GPU_UTIL=0.78; DEFAULT_KV_MEM=16106127360; DEFAULT_MAXSEQS=8; DEFAULT_AUTOTUNE=1
    SERVED_NAME="${SERVED_NAME:-qwen3.8-flash-next}"
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

# THE ONE THAT COSTS YOU A DAY -----------------------------------------------------
# PLE offload requires the multiproc executor, even at TP=1. spawn_ple_offload() and
# wait_ple_offload_ready() are called from vllm/v1/executor/multiproc_executor.py and
# from nowhere else -- uniproc_executor.py has no such call. vLLM picks uniproc by
# default at TP=1, so the offload worker is never spawned, the GPU side waits forever on
# a peer that does not exist, and the boot hangs after "Graph capturing finished" with
# EngineCore spinning at 90% of one core, no disk I/O, and no /tmp socket. Nothing is
# ever logged. Diagnostic: `docker exec <container> ps -eo pid,rss,comm` -- if there is
# no PleOffloadWorker process, it was never spawned.
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
  mtp)
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

KV_DTYPE="${KV_DTYPE:-}"
KV_ARGS=()
[[ -n "${KV_DTYPE}" ]] && KV_ARGS=(--kv-cache-dtype "${KV_DTYPE}")

GPU_UTIL="${GPU_UTIL:-${DEFAULT_GPU_UTIL}}"
MAXSEQS="${MAXSEQS:-${DEFAULT_MAXSEQS}}"
KV_MEM="${KV_MEM-${DEFAULT_KV_MEM}}"
KVMEM_ARGS=()
[[ -n "${KV_MEM}" ]] && KVMEM_ARGS=(--kv-cache-memory "${KV_MEM}")

PREFIX_CACHE="${PREFIX_CACHE:-0}"
PREFIX_ARGS=(--no-enable-prefix-caching)
[[ "${PREFIX_CACHE}" == "1" ]] && PREFIX_ARGS=(--enable-prefix-caching --mamba-cache-mode align)

PLE_TIMEOUT="${PLE_TIMEOUT:-1800}"
AUTOTUNE_ARGS=(--enable-flashinfer-autotune)
[[ "${AUTOTUNE:-${DEFAULT_AUTOTUNE}}" == "1" ]] || AUTOTUNE_ARGS=(--no-enable-flashinfer-autotune)

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
mkdir -p "${HOME}/.cache/flashinfer" "${HOME}/.cache/vllm-qwen38"

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
  -e VLLM_PLE_CPU_OFFLOAD=1 \
  -e VLLM_PLE_OFFLOAD_READY_TIMEOUT="${PLE_TIMEOUT}" \
  -e FLASHINFER_DISABLE_VERSION_CHECK=1 \
  "${LONG_ENV[@]}" \
  -v "${MODEL_DIR}:/model:ro" \
  "${CONFIG_MOUNT[@]}" \
  -v "${HOME}/.cache/flashinfer:/root/.cache/flashinfer" \
  -v "${HOME}/.cache/vllm-qwen38:/root/.cache/vllm" \
  "${IMAGE}" \
  /model \
    --served-model-name "${SERVED_NAME}" \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --tensor-parallel-size 1 \
    --distributed-executor-backend "${EXECUTOR}" \
    --trust-remote-code \
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

echo "started ${NAME} (profile=${MODEL_PROFILE}, executor=${EXECUTOR}, PLE offload=on, SPEC=${SPEC:-mtp}${SPEC_CFG:+ k=${NSPEC}}, maxlen=${MAXLEN}, util=${GPU_UTIL})"
echo "follow with:  docker logs -f ${NAME}"
echo "watch memory: watch -n5 'free -g; swapon --show'"
echo
echo "Expect ~10 min to load and a further ~3 min of PLE paging before the API answers."
