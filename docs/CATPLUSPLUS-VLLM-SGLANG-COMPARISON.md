# catplusplus pinned engine assessment: vLLM first for source review, SGLang parallel

**2026-10-19.** This is a **source/evidence assessment**, not a
successfully executed GB10 checkpoint, loader patch or reproducible
end-to-end benchmark. The owner-approved **mazinb R2 download is
ongoing**. Do not synchronize/overwrite the executing DGX checkout or
run concurrent Docker/GPU/large-source/weight transfers.

## Exact identity and what was actually checked

- Model: `catplusplus/Qwen3.8-Flash-Next-uncensored-NVFP4-mixed`.
- Immutable model revision:
  `3251fd8afbd08f76368a9bfa71132d9aef364813`.
- Owner's prior physical pinned Hub inventory:
  **17,448 paths**, **96 safetensors shards**,
  **188,540,029,444 total repository bytes**, and
  **≈174.8553 GiB root safetensors** (rounded), source metadata only.
- Actual pinned DGX HEAD diagnostic: `resolve` of both selected
  small files replied `307 → HF_SAME_HOST/API_RESOLVE_CACHE`,
  while `raw` replied `200`. GET content audit on the newly
  changed route is **NOT_YET_PHYSICALLY_RUN**.
- Public model card **claims**, as of research date, two
  publisher-modified engines and standalone history bundles
  `extra/packages/vllm-qwen4_exp_sm110.bundle` and
  `extra/packages/sglang-qwen4_exp_sm110.bundle` plus clean source
  copies under `extra/packages/`. The card provides a production
  **SGLang** launcher, not equivalent pinned GB10 vLLM startup
  proof. Source-tree files/bundle git commits at the immutable
  model revision are **NOT_INDEPENDENTLY_INSPECTED**.
- The installed `vllm-orcarouter-v029:v1` benchmark image
  **worked historically for mazinb**, but that image's modelopt
  mixed MXFP8 fused QKVZ tensor loader **has NOT** passed a
  catplusplus check. The project's configured managed image is
  `vllm-skinny-tp1:v1`; this is distinct from the mazinb M1 image.
  No exact publisher image/wheel/patch SHA is qualified.

## Official vLLM PR evidence — independently verified 2026-10-19

These are upstream public vLLM developments, **NOT evidence of
their presence in the installed DGX v0.29 image**.

| vLLM source | GitHub outcome | Meaning for GB10 |
|---|---|---|
| [Qwen3.8 model #53896](https://github.com/vllm-project/vllm/pull/53896) | MERGED 2026-08-31 | Generic Qwen3.8 model support is real upstream; exact catplusplus mixed tensors not proved |
| [Qwen3.8 UVA PLE #54371](https://github.com/vllm-project/vllm/pull/54371) | MERGED 2026-09-09 | PLE can use CUDA UVA into pinned CPU memory; this **still consumes the GB10 shared physical RAM pool** |
| [Older CPU PLE #53899](https://github.com/vllm-project/vllm/pull/53899) | CLOSED UNMERGED | Its older validation matrix included GB200 TP2/4 and FP8/BF16, not a catplusplus single-GB10 proof |
| [Disk-backed PLE mmap #54129](https://github.com/vllm-project/vllm/pull/54129) | CLOSED UNMERGED 2026-09-26 | Proposed read-only mmap of original safetensors PLE shards; **not safe to treat as shipped/upstream supported** |

The merged [UVA #54371](https://github.com/vllm-project/vllm/pull/54371)
changed `vllm/config/engram.py`,
`vllm/models/qwen4_exp/nvidia/ngram_embedding.py`,
`vllm/models/qwen4_exp/nvidia/ple_layer.py`,
`vllm/models/qwen4_exp/nvidia/model.py`, and model-loader
utilities. The abandoned [mmap #54129](https://github.com/vllm-project/vllm/pull/54129)
contained a different unmerged
`vllm/models/qwen4_exp/nvidia/ple_mmap.py` plus GPU
model-runner changes. Do not silently cherry-pick a closed
PR, and do not equate `VLLM_PLE_CPU_OFFLOAD=1` to
reduction of **total** unified-memory occupancy.

The public vLLM example for stock packages and the publisher's
`pip install vllm` button are not a verification that the
**specific** pinned ModelOpt MIXED_PRECISION tensor inventory
loads with correct output and memory safety.

## Concrete upstream vLLM source review at merged UVA commit

We inspected **the actual public vLLM source files at commit**
[`a2f82acf1fd671c3152cffd49af16a73ed2bc4e4`](https://github.com/vllm-project/vllm/commit/a2f82acf1fd671c3152cffd49af16a73ed2bc4e4)
(MERGED #54371), not just model-card descriptions:

- [`vllm/models/qwen4_exp/nvidia/model.py`](https://github.com/vllm-project/vllm/blob/a2f82acf1fd671c3152cffd49af16a73ed2bc4e4/vllm/models/qwen4_exp/nvidia/model.py#L641-L648)
  contains the actual `packed_modules_mapping`
  `"in_proj_qkvz": ["in_proj_qkv", "in_proj_z"]`.
  This proves a fused-name *mapping* exists upstream, **not**
  that the right MXFP8 per-block scale tensor is allocated,
  loaded, consumed or numerically correct for catplusplus.
- [`vllm/models/qwen4_exp/nvidia/ngram_embedding.py`](https://github.com/vllm-project/vllm/blob/a2f82acf1fd671c3152cffd49af16a73ed2bc4e4/vllm/models/qwen4_exp/nvidia/ngram_embedding.py#L161-L210)
  imports `ModelOptMixedPrecisionConfig`;
  `Qwen4ExpPLEEmbeddingMethod.from_quant_config` explicitly
  selects `Qwen4ExpPLEFp8EmbeddingMethod` when
  `embedding_dtype == "float8_e4m3fn"`, *before*
  its ModelOpt mixed algorithm branch. This proves there is
  an upstream FP8 PLE format selection path, not end-to-end
  correct global PLE weight-scale loading or residency.
- [`vllm/config/engram.py`](https://github.com/vllm-project/vllm/blob/a2f82acf1fd671c3152cffd49af16a73ed2bc4e4/vllm/config/engram.py#L19-L40)
  uses `cpu_offload` with pinned CPU memory and accepts
  legacy `VLLM_PLE_CPU_OFFLOAD`; this is an explicit
  **UVA/pinned-host strategy, not file-backed mmap**.
- The [`ple_layer.py`](https://github.com/vllm-project/vllm/blob/a2f82acf1fd671c3152cffd49af16a73ed2bc4e4/vllm/models/qwen4_exp/nvidia/ple_layer.py#L94-L112)
  constructor instantiates `Qwen4ExpNGramEmbedding` with
  `quant_config` and model `ple_embedding_dtype`, showing
  a model → PLE-format wiring path.

**Confidence upgrade:** Qwen4Exp fused mapping + FP8 PLE
selection + ModelOpt mixed quant config are **present in
that specific upstream source revision**. This is stronger
than a release-note claim, but entirely separate from
proving these specific patches are in our measured v0.29
Docker image, from proving full catplusplus fused MXFP8
tensor/scale correctness, or from qualified GB10 residency.
Actual runtime priority remains undecided.

## Concrete upstream SGLang source review: avoid the temporary PLE GPU table

The corresponding public SGLang issue
[#39841](https://github.com/sgl-project/sglang/issues/39841)
reported that `--ple-offload-embedding` was initially ineffective
for low-free-VRAM devices: construction created the *entire
FP8 PLE table on CUDA* before wrapping it into host/file
storage, causing an allocation spike/OOM **before**
offload could begin.

**Verified upstream resolution:** [PR #39928](https://github.com/sgl-project/sglang/pull/39928)
**MERGED 2026-09-20**, changed
`python/sglang/srt/models/qwen4_exp.py` to instantiate
`VocabParallelEmbedding` in a `torch.device("meta")`
context **when offload is enabled**, then wrap it in
`Qwen4ExpPinnedHostEmbedding`; added a regression
checking the peak CUDA allocation stays below half the
table's size. It preserves a real CUDA `weight_scale`
buffer and verifies CPU pinned backing in that test.
This is *real upstream source-level implementation
evidence*, not a measurement of our particular
publisher SGLang fork or a full catplusplus run.

**Critical pin check:** The publisher's pinned SGLang
fork must contain the equivalent *construct on meta,
offload before materializing CUDA weights* semantics
(or better). If it predates #39928 or uses the original
construct-then-offload sequence, marking
`--ple-offload-embedding` as enabled is **not**
sufficient to admit GB10 load. Even with #39928,
the PLE table backed by **pinned host physical RAM**
still competes with other unified allocations; a
truly NVMe-file-backed path has different semantics
and must separately prove page-residency/RM safety.
No exact publisher image or runtime commit is qualified.

## Engine-by-engine stage-gate comparison

| Evidence / gate | Existing vLLM + publisher patch | Publisher SGLang |
|---|---|---|
| Prior local DGX baseline | mazinb vLLM v0.29 **historically measured**; distinct checkpoint | NO local measured base |
| Publisher engine source | Claimed `extra/packages/vllm` and bundle; fixed revision files **unverified** | Claimed `extra/packages/sglang` and bundle; fixed revision files **unverified** |
| Production configuration | No equivalent pinned catplusplus live script attested | `extra/inference/inference_qwen38_flash_next_sglang.sh` claimed; two-file GET still physically untested |
| Qwen4Exp hybrid architecture | Upstream Qwen3.8 PR merged; precise publisher fork comparison pending | Claimed working on **different** SM110 Thor device; actual files/functions uninspected |
| Mixed NVFP4/MXFP8 fused `linear_attn.in_proj_qkvz` | **BLOCKED** until actual qkvz weight/scale registration and kernel consumed | **BLOCKED** despite publisher's proposed fused scale mapping fix; source not verified |
| Global FP8 PLE | Generic upstream UVA path merged, but shared RAM use remains | Claimed file-backed PLE via launcher flags; real exact backend and RAM consumption unverified |
| Single-GB10 SM121 backend | Exact kernel/image/wheel SHA and support **UNVERIFIED** | Exact SM121 kernel/image/wheel **UNVERIFIED** |
| MTP/NEXTN | Original vLLM speculative decoding does not automatically prove publisher MTP | Launcher exposes NEXTN flags; accurate speculative acceptance unproven on GB10 |
| 128GB nominal shared memory | **BLOCKED** peak-residency and RM safety | **BLOCKED** peak-residency and RM safety |
| Catplusplus live/benchmark | NOT_RUN/NOT_MEASURED | NOT_RUN/NOT_MEASURED |

**Research ordering:** Inspect the vLLM source first because of our
known-good *mazinb* operational tooling, then inspect the
publisher SGLang source in parallel. **Final runtime preference
is UNDECIDED** and must follow actual mixed-scale correctness
and finite physical memory/offload evidence, NOT engine reuse alone.

## Memory threshold: reasons a simple PLE-only strategy is not enough

DGX Spark nominal 128 decimal GB = ≈119.2093 GiB.
Catplusplus safetensors stored size ≈174.8553 GiB.
Publisher claims FP8 PLE occupies ≈47.7 GiB.
Subtracting **that entire unverified estimate** leaves
≈127.1553 GiB stored data, ≈7.95 GiB above *all* nominal
physical RAM before KV, CUDA graphs, GLA recurrent state,
MTP, staging, page cache, OS and watchdog reserve.
This is not an allocation trace nor proof that all
remaining files would have to reside simultaneously.
A source-backed partial-residency/paging design, plus a
separately approved physical safety test, is required.

UVA PLE CPU pinned allocations can solve *GPU-specific*
residency placement, but on a unified-memory single GB10
they do **not** create another independent 47.7-GiB
pool of physical DRAM. True file-backed sparse PLE access
has different paging and I/O tradeoffs and must be audited
independently for each exact engine; neither outcome is
qualified for this checkpoint.

## Next source audit, without fetching package blobs or checkpoints

A new maintained script
`scripts/model/inspect_catplusplus_engine_sources.py` does
**metadata only** GET from one exact pinned Hub API subtree:
`/api/models/{MODEL}/tree/{REVISION}/extra/packages`;
recursive paginated JSON, no redirects, hard size/item/page caps,
full repository/revision/host/query pinning, no code or weights.
It inventories `vllm`/`sglang` source tree file counts,
example Python paths and claimed git-bundle names if actually
present. The result **does not** read any source code or
promote either engine. Offline synthetic tests isolate and
verify pagination constraints, traversal/no-redirect and
no-executable-download behavior.

Operator Wizard: **5 → 23 → 11**, but **DO NOT RUN ON DGX
UNTIL mazinb checkpoint transfer ends**. An incomplete or
blocked inventory is NOT evidence that a backend cannot work.
A complete inventory is only tier L1 *file existence*,
not patch implementation/semantic compatibility.

After that bounded result, create a separately reviewed
exact-path *small-source-file* allowlist, fetch/capture SHA256
for relevant real `vllm/models/qwen4_exp/...`,
`sglang/srt/models/...`, ModelOpt quant config,
PLE offload and scale kernel implementations from
**both pinned forks**. Check function-level differences,
upstream version provenance, ARM64/SM121 build flags,
weight-scale tensor names/shapes and behavior on synthetic
MXFP8 block cases. Large bundles are never executed or
downloaded as an unreviewed dependency. The actual
model shards, any engine builds and GPU startup require
independent capacity and owner approvals.

## Safety

During mazinb restore, **NO** DGX git checkout sync,
catplusplus checkpoint/source-bundle download, pip install,
Docker build/start, cache dropping, public API bind, systemd,
swap or managed-model mutations. Once mazinb is complete,
the first work is read-only pinned-source inspection.
No catplusplus image is declared qualified or installable,
and PR #261 remains Draft/open/unmerged.
