# Community single-Spark OrcaRouter PLE CPU-offload report — external reference only

**Source:** https://arca.live/b/alpaca/181506470 (full article + operator-supplied Docker
command, benchmark excerpt, and full `config.json` pasted in conversation
2026-10-18). This is **third-party operator-reported evidence**,
not our physical DGX result, not our source image, and not a certified
long-term benchmark. The source was parsed as supplied text; images or
hidden attachments were not authenticated.

## Reported working configuration, faithfully scoped

- Checkpoint: `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`;
  **NOT** the planned pinned `lychee888/...-NVFP4-FP8PLE`.
- Image: `vllm/vllm-openai:qwen38-flash-next-arm64-cu130`;
  not our installed `vllm-skinny-tp1:v1` immutable
  `sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4`.
  Docker Hub publishes the external linux/arm64 image tag
  https://hub.docker.com/layers/vllm/vllm-openai/qwen38-flash-next-arm64-cu130/images/sha256-3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e
- One-GPU TP=1; `VLLM_PLE_CPU_OFFLOAD=1`,
  `VLLM_PLE_OFFLOAD_READY_TIMEOUT=1800`,
  `--distributed-executor-backend mp`,
  `--gpu-memory-utilization 0.85`,
  `--kv-cache-memory 25769803776` (**24 GiB**),
  `--max-model-len 262144`, `--max-num-seqs 3`,
  `--speculative-config '{"method":"mtp","num_speculative_tokens":2}'`,
  chunked prefill, prefix caching disabled.
- Memory: article says **118.4/122 GB (97.3%)** and rises to ~119 GB
  on calls. Those are writer observations, not independently
  verified pressure/peak/soak receipts.
- Benchmarks: the author reports 12/12 requests succeeded in each of
  three scenarios. Prefill input 8192, output 32, concurrency 1:
  **1561.8 input tok/s**, median TTFT **3.87s**;
  decode input 128, output 512, concurrency 1:
  **27.8 output tok/s**, median TTFT **236 ms**;
  mixed input 1024, output 256, concurrency 3:
  **52.4 aggregate output tok/s**, median TTFT **697 ms**.
  MTP acceptance ~50% (author reported).
  The advertised `max-model-len=262144` is a
  **configured maximum**; these samples do not prove an
  actual 262K-input run, a long soak, safe repeatability,
  or the same throughput for different models.

**The reported Docker command is NOT an approved project command.**
It uses `--network host`, `--ipc host`,
`--gpus all`, `--cap-add=SYS_PTRACE`,
`--cap-add=IPC_LOCK`, `--trust-remote-code`,
`--rm`, and external-model binds. Do not transplant
its flags or try a new Docker container under our consumed
one-temp-source-probe approval.

## Exact configuration detail from the pasted `config.json`

Parsed the top-level JSON object, not a search excerpt:

| Source property | Observed |
|---|---|
| `architectures` | `Qwen4ExpForConditionalGeneration` |
| `model_type` | `qwen4_exp` |
| `quant_method` | `compressed-tensors` |
| `quantization_config.format` | `mixed-precision` |
| `config_groups` | **2** |
| `group_0` | `naive-quantized`, float 8-bit, channel strategy, **300 explicit target entries** |
| `group_1` | `nvfp4-pack-quantized`, 4-bit, group size 16, **1 MoE projection regex target** |
| `ignore` | **753** string entries, **2** containing `.ple.`: layer 1 PLE key_proj/value_proj |
| `config_groups` direct PLE-string targets | **0** |
| `text_config.ple_embedding_dtype` | **not specified** |
| `text_config.split_ngram_parts` | 128 |
| `text_config.max_position_embeddings` | 262144 |
| `text_config.ple_embed_dim` | 2560 |

A lack of a PLE-target string in these CT groups does not
prove the PLE method is unquantized or the actual tensor dtype,
but **this config does not explicitly show the lychee888 FP8
PLE override, nor a recorded loaded global BF16 FP8 scale**.
The two ignored PLE entries are key/value projections, not
a verified special treatment for the n-gram table.
The excerpt cannot qualify an OrcaRouter and lychee888
weight/loader interchange.

## What it proves — and does not

A credible third-party *reported* TP=1 API startup with
OrcaRouter NVFP4 and PLE CPU offload is directly relevant:
a supported Qwen4Exp-derived image, MP backend, IPC permissions,
MTP n=2 and KV=24GiB can operate on one Spark with very
little remaining memory headroom.

It does **not** establish:
- compatibility with our older pinned skinny image's
  `NATIVE_FP8_CONFIG_ONLY_SOURCE` (physical source SHA
  `a71144c1d36e06f22a2da1b1ada900076597fe5e824a911e7ada86249a0993e7`);
- a `CompressedTensorsConfig` to FP8 PLE method dispatch,
  exact n-gram shard weight dtype/shape, or global scale
  registration, loading and actual application for
  **lychee888**;
- the lychee888 pinned revision `1b3c3cedc14fb3bee4294dea5e3515af74b8268a`
  `metadata.total_size=132279699754` bytes
  fitting one DGX Spark's nominal 128GB unified memory;
- GPU resident bytes, file cache, stable offload residency,
  leak-free idle-to-load-to-stop, or 262K context
  real performance.

**Critical GB10 UMA caution:** moving a PLE tensor from
CUDA to pinned **CPU memory is not moving it to a separate
RAM bank** on a GB10 unified-memory system. It may free a
CUDA allocation/accounting budget but can still occupy
roughly the same physical 128GB pool and may leave little
reclaimable space. NVIDIA's fused Qwen4Exp PLE storage PR
#54371 explicitly describes `cpu_offload=true` as
pinned host memory. Repo https://github.com/vllm-project/vllm/pull/54371
is merged, but our pinned installed image is not attested
to contain that code. The article's memory ~97% is
therefore a **warning** as well as a success anecdote.

## Higher-value follow-up: file-backed PLE, not simply CPU offload

As of 2026-10-18, the following external upstream PR
statuses were verified via the GitHub API:

- [#58439](https://github.com/vllm-project/vllm/pull/58439),
  **OPEN, UNMERGED**: opt-in
  `--engram-config '{"checkpoint_mapped":true}'`.
  On a GB10 with pageable GPU host page-table support,
  intended to map safetensors FP8 PLE shards read-only
  without the whole table being a pinned anonymous
  allocation. Reports important concurrency/race and
  page-preload constraints; not available in our image.
- [#58815](https://github.com/vllm-project/vllm/pull/58815),
  **OPEN, UNMERGED**: opt-in
  `--engram-config '{"host_file_gather":true}'`,
  reads selected rows via host file-backed cache and
  bounded staging rather than holding an entire PLE
  table. It has its own correctness/cold-cache criteria.
  Not available or qualified on our pinned image.
- [#53899](https://github.com/vllm-project/vllm/pull/53899):
  **CLOSED UNMERGED**. Its PLE-offload validation was
  GB200 TP2/TP4, NOT direct GB10 TP=1 qualification.
- [#54882](https://github.com/vllm-project/vllm/pull/54882):
  **MERGED** for **ModelOpt** mixed precision FP8 PLE,
  not automatically a `compressed-tensors` adapter.

These new candidate storage paths can make the
**file-backed active working set** smaller than full
132.28-GB index bytes. This does not prove peak
GB10 use, safe page-cache pressure, the correct
compressed-tensors PLE adapter, or permission to run.

## Concrete source-only next gates

1. Compare pinned lychee888 `config_groups` targets,
   ignore patterns, FP8 PLE declaration and global
   `weight_scale` index shape against this pasted
   OrcaRouter config; preserve checkpoint/revision
   provenance and do not transfer tensor data.
2. Analyze #54371, #58439 and #58815 source paths
   against **a reproducible exact version** of our
   installed-image PLE source. Full original source
   bytes were not archived; only image SHA+static AST
   receipt exists, so do not assert patch clean-apply.
3. Treat FP8 PLE dispatch, BF16 global scale load,
   checkpoint-mapped/file-gather verification,
   tensor shape/header and peak memory as independent
   mandatory gates. Document acceptance tests with
   synthetic fixtures; no physical GPU experiment
   without separately reviewed authorization.
4. lychee888 registry stays
   `PROFILE_INSTALLABLE=0`, `TP1=NOT_QUALIFIED`.
   Draft PRs stay unmerged.

**Evidence classification:** `EXTERNAL_THIRD_PARTY_REPORT_ONLY`,
`ORCAROUTER_TP1_REPORTED`,
`LYCHEE888_FP8_PLE_UNVERIFIED`,
`LYCHEE888_GB10_FIT_UNVERIFIED`,
`NO_DGX_MUTATION`.
