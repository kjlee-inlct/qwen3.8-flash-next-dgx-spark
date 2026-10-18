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

## 2026-10-18 — OrcaRouter-first recovery decision against actual historical failures

**Operator objective update:** repair **OrcaRouter first** using this
reference, not only apply the reference to lychee888.
This is a source-only differential assessment; a new GPU/Docker
trial or pull requires a separately reviewed proposal and consent.

### Existing direct DGX results supersede assumptions of `never ran`

- [2026-10-03 strict 24/16GiB controlled A/B](../scripts/benchmark/evidence/orcarouter-kv-ab-adverse-state-20261003.md):
  legacy OrcaRouter 24GiB failed under the adverse state,
  but 16GiB reached READY, API 200 and 180s soak with
  **functional/host-stability PASS/PASS** in that specific run.
  A subsequent managed 16GiB promotion reached READY yet
  recorded six recoverable `NV_ERR_NO_MEMORY` events:
  functional PASS, **strict host-stability FAIL**.
- [2026-10-04 R22 v0.29 mmap](../scripts/benchmark/evidence/orcarouter-managed-rmsys-r22-v029-mmap-result-20261004.md):
  `api_ready=1`, no protected stop, **one strict RM
  sysmem OOM**, host-stability FAIL. Replacing CPU PLE
  with mmap reduced sustained swapping but did **not**
  fix a common early memory allocation burst.
- [R23–R32 mechanism closure](../scripts/benchmark/evidence/orcarouter-r23-r32-allocation-localization-closure-20261006.md):
  around 75–77GiB NVIDIA RM order-4 system-page
  allocation activity during early model construction
  before the long weight-shard fill; 48 x 400MiB linked
  to packed MoE `w13_weight`; the interleaved
  800MiB family is pre-`create_weights`, not
  proven owned by a separate model tensor.
  This is not proof that the external CUDA 13.0
  image changes those allocation semantics.
- [2026-10-13 Legacy A physical stop](../scripts/benchmark/evidence/dgx-orcarouter-legacy-a-protection-confirmed-20261013.md):
  during early shard loading, sustained swap growth and
  non-CMA immediate free at **914MiB** triggered the
  project's **required** monitor `PROTECT 5/5`.
  `ExitCode=137`, `OOMKilled=false`; this is
  monitor protection, **not a demonstrated Docker OOM**.
  Neither API READY nor benchmark was reached in A.

### Parity: which published flags are already implemented?

The maintained [`scripts/serve.sh`](../scripts/serve.sh)
sets `EXECUTOR=mp` by default,
`VLLM_PLE_CPU_OFFLOAD=1` for legacy
`PLE_MODE=cpu-offload`,
`VLLM_PLE_OFFLOAD_READY_TIMEOUT=1800`,
`DEFAULT_NSPEC=2`, `--max-model-len 262144`,
`DEFAULT_MAXSEQS=3`, disabled prefix cache,
disabled async scheduling, FlashInfer autotune disabled
and `--gpu-memory-utilization 0.85` for legacy.
This explicitly includes the upstream
[`TP=1` CPU-offload uniproc hang workaround](https://github.com/vllm-project/vllm/issues/53960)
(`--distributed-executor-backend mp`).
Changing only those already-set options is therefore
not a plausible independent remediation.

Our project's **16 GiB** KV default is deliberately
different from the peer's **24 GiB**: prior controlled
on-host testing found 24 GiB less resilient.
Do **NOT** raise to 24 GiB on a forum analogy.
The v0.29 mmap case is a different loader image/flag
set, not automatically interchangeable with the
stock `--kv-cache-memory` semantics.

### Real deltas to research

1. **Official image implementation**: external
   `vllm/vllm-openai:qwen38-flash-next-arm64-cu130`
   is not any of our preinstalled
   `vllm-skinny-tp1:v1` or
   `vllm-orcarouter-v029:v1` images. The official
   external manifest
   `sha256:3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e`
   is linux/arm64, CUDA 13.0.
   Manifest ID is **remote source**; it is
   NOT evidence the image was pulled, present or
   used on the user's DGX. Exact embedded vLLM
   source revisions/quant modules, memory/graph
   behavior, PLE worker and config compatibility
   must be source-attested before making claims.
2. **Checkpoint/config identity**: peer explicitly
   binds its own rewritten `config.json`.
   It contains two compressed-tensors groups,
   300 + 1 targets and 753 excluded entries,
   but whether those rewrites equal our
   `prepare_config.py` layer-type-only conversion
   has **not been proved**. Inspect existing
   source config/override **read-only** with the
   maintained checkpoint inspector first.
   Do not replace or overwrite either original.
3. **Memory ownership**: the peer's reported
   118.4/122GB (97.3%) is **not stability
   headroom proof**. GB10 shared system memory,
   pageable/PINNED PLE, and early large RM allocations
   make replay sensitive to page/allocator state.
   Do not interpret its benchmark as evidence
   our historical `NV_ERR_NO_MEMORY` disappears.
4. **Externally documented deadlock**:
   vLLM [#53960](https://github.com/vllm-project/vllm/issues/53960)
   shows TP=1 CPU PLE offload can hang if the
   single-process executor never spawns a PLE
   worker. Using MP was the workaround. It is
   **already our default**, so this is a
   closed flag-parity lead, not a new fix.

### Safe sequential diagnosis and future candidate design

**Step A — no mutation now:** verify exact local
branch/source/CI, protected container/image identities
from existing Docker-read-only tooling, manifest
checkpoint path/revision, pinned original config
versus the already-created override via the
maintained `inspect_model.py` (read-only local
headers may be inspected only on approved existing files);
current memory/swap snapshots and presence of the
external image tag only via `docker image inspect`
(no `pull`, `create`, `run`, `cp`, `rm`).

**Step B — source only:** inspect image-specific
vLLM model construction/quantization allocation
behavior, metadata/config differences,
offload/graph flags and direct compile/runtime
dependencies without assuming the official
image is installed or safe. Show exact
immutable image/source provenance and reproducible
offline/synthetic validations.

**Step C — not authorized yet:** if Steps A/B reveal
a materially different plausible root-cause
path, design a new **separately approved**
Wizard-managed, protected, rollback-safe
single-candidate experiment with explicit exact
image/checkpoint ID, 16GiB KV first, strict RM
monitors unchanged, no old-container overwrite,
clear automatic STOP and postchecks.
Only after physical READY + API smoke +
bounded soak + zero strict RM errors should
llama-benchy/performance testing be considered.
Do not run the peer's direct `docker run --rm`
or relax safety protections.

**Decision:** `ORCAROUTER_RECOVERY=SOURCE_REVIEW_ACTIVE`,
`COMMUNITY_CONFIG_FLAGS=ALREADY_MOSTLY_MATCHED`,
`OFFICIAL_IMAGE_DELTA=UNQUALIFIED`,
`STRICT_HOST_STABILITY=NOT_QUALIFIED`,
`NO_NEW_DGX_MUTATION`.
