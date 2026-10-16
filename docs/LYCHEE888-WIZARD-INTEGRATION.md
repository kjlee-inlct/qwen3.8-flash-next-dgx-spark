# Original model 4: lychee888 FP8-PLE — integration and acceptance

**Stage: research and source-only preparation; NOT installable or live-qualified.**
Product priority is still **simple wizard installation, removal and switching**
on a single DGX Spark, not an independent loader demo.

## 1. Public checkpoint source and evidence limits

- [Model card: lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE](https://huggingface.co/lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE), inspected 2026-10-13. The author describes an OrcaRouter derivative with an FP8 E4M3 PLE n-gram table rather than upstream BF16.
- **Card-reported only:** checkpoint 123.25 GiB, versus OrcaRouter 170.93 GiB (~47.7 GiB smaller); ten FP8 PLE shards and one BF16 `weight_scale` scalar; `text_config.ple_embedding_dtype=float8_e4m3fn`. Neither file counts/hashes nor tensor data were independently verified on DGX. The card says PLE tensors were derived from OrcaRouter and warns against mixing weights from similarly laid out repositories.
- The author's *working recipe* targets **two DGX Sparks** and uses a specific FP8 PLE resolver/override `PLE_QUANT_OVERRIDE=fp8`. The card warns that the wrong PLE loader may allocate the original large BF16 table. **This does not qualify one GB10, tensor-parallel-size=1 or this project's pinned vLLM images.** The proposed single-Spark startup can still fail with NVIDIA RM memory errors despite smaller disk bytes.
- Repository HEAD is mutable. Before candidate registration, discover and pin a real immutable 40-character HF revision SHA. Do not invent or infer its value from the card.

## 2. Actual current implementation gaps (repository source review)

| Layer | Current code | Missing before selectable |
|---|---|---|
| Registry | `scripts/model/model-profiles.sh` lists `lychee888` under planned/non-installable (`PROFILE_INSTALLABLE=0`) | Revision, local path, image, served identity, PLE mode and qualification |
| Download | `scripts/download-weights.sh --candidate` exists, but `load_download_profile lychee888` explicitly errors | Pinned and verified candidate metadata/download route, checksum, provenance, no unqualified installer opt-in |
| Index/header | `scripts/model/inspect_model.py` and `checkpoint_integrity.py` provide metadata/header/index reading without loading weight payloads | FP8 PLE dtype, global scale, index-to-file, ten PLE shards and source-specific assertions |
| Runtime | `scripts/serve.sh` has only orcarouter/nvidia/mazinb/Hybrid profiles; unknown name fails | Compatible FP8 PLE reader in actual single-GB10 backend, tested image and flags |
| Wizard + removal | Generic install/switch/uninstall and ownership framework exists | Model-specific candidate preview, resume/rollback, preserved parents/assets, bilingual UX and fail-closed tests |

## 3. Safe execution order and acceptance gates

**L0 — remote and local metadata only, no model/GPU launch.**
- Inspect remote repo information, immutable SHA, file/hash inventory and `config.json`/`model.safetensors.index.json` without a 123+ GiB download.
- Existing metadata-only command (requires network, does not download weights):
  `python3 scripts/inspect-model.py --repo lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE --json`.
  Its `LOCAL_REQUIRED` warning means exact tensor layout has **not** been validated.
- Once a qualified separate local copy exists, validate index, safetensors **headers only** and sha256 file integrity. Confirm expected FP8 E4M3 tensors and the single global scale. Never assume a model card is verified host evidence.

**L1 — source implementation and isolated synthetic tests.**
- Pin the HF revision; add candidate-only metadata in the existing registry while `PROFILE_INSTALLABLE=0` stays unchanged. Ensure wrong revision, missing shards/scales and unsupported dtypes fail closed.
- Choose an image/runtime that truly supports **single-GB10 TP=1** FP8 PLE and the author's scalar-scale representation. Require source-level PLE loader consumer checks. Do not assume the project H38 image or BF16 CPU offload can read this layout.
- Add simulated wizard tests for selection disabled until admission, explicit cancellation, completed install/switch, ownership and uninstall in disposable HOME/XDG; do not run actual Docker or delete model data.

**L2 — separately approved real-host qualification (future, NOT authorized).**
- Acquire exact release/container/image/manifest identity and adequate storage, non-CMA memory and swap reserve. Plan a monitored, strictly bounded first load with protection ON and NVIDIA RM/kernel event capture; be prepared for the known transient high-order allocation failure.
- Show true health, expected served-model identity, committed managed attestation, strict-RM host-stability window, functional smoke and failure rollback. A two-node recipe or a successful metadata read is insufficient.
- Do not disturb the current stopped OrcaRouter container merely to close L2.

**L3 — product admission.** After positive L0–L2 proof and truthful risk/status review, allow wizard selection and update language/help/tests. Until then, `lychee888` remains **planned, disabled**, even though public checkpoint files exist.

## Independent restrictions

H38/M4 stays blocked by its own loader metadata/order and strict-RM gates. M2/D1–D5 destructive installer acceptance requires an independently disposable host; the only DGX is not one. PR #259 stays Draft/Unmerged until separate release acceptance. Preserve distinctions among **external author claims**, **SOURCE_REVIEW**, **CI/synthetic** and **ACTUAL_DGX** results.

References: [mission](PROJECT-MISSION-AND-MODEL-SCOPE.md),
[acceptance](MANAGED-LIFECYCLE-ACCEPTANCE.md),
[latest status](CURRENT-STATUS.md).


## L0 metadata-only read-only implementation (2026-10-13)

Added `scripts/model/inspect_lychee888_metadata.py` with pure standard-library
Hub JSON fetching and an `--offline-dir` fixture mode. It requests only the
Hub repository/revision metadata, `config.json`, and
`model.safetensors.index.json`; it **never downloads any safetensors weights**.
Remote HEAD is resolved once to a 40-hex commit and later URLs use that
pinned revision. The probe fails closed for a missing FP8 PLE file,
unexpected retained BF16 PLE original shard, incorrect
`text_config.ple_embedding_dtype`, an incomplete 128-shard PLE
index, absent/duplicate/misplaced global scale, bad revision identity or
missing index file references.

Usage in the repository checkout (network read-only; **no GPU/model start**):

```bash
python3 scripts/model/inspect_lychee888_metadata.py
```

For offline JSON fixtures, supply `api.json`, `config.json`,
`index.json` in a directory and run:

```bash
python3 scripts/model/inspect_lychee888_metadata.py --offline-dir /path/to/json-triplet
```

Passing returns **INDEX_STRUCTURE_PASS_METADATA_ONLY**: this verifies
*index key names/file mapping and config claims*, **not** the FP8
dtype/shape inside safetensors file headers, BF16 scale dtype,
file-byte checksums, vLLM image support, TP=1 behavior, or RM stability.
The first commit uses isolated **synthetic** fixture tests. Do not label
L0 complete for the real Hub revision until its actual remote output
has been captured and pinned. Profile `lychee888` stays disabled.


**L0 public source reference, not yet probe output (2026-10-13):**
The Hugging Face model's public commit page exposes a full
40-hex commit `1b3c3cedc14fb3bee4294dea5e3515af74b8268a`
(README update, Sep 4). This is a verified **web commit URL**,
not a completed pinned-Hub API/config/index probe. Do not mark
L0 real file/index verification PASS until the probe emits its
metadata-only verdict from actual fetched JSON. Single-Spark loader
and weight-file gates still remain unverified.


## L0 actual Hub JSON execution — 2026-10-13

The user executed the existing `inspect_lychee888_metadata.py`
against the *actual Hub API* from the physical DGX detached
worktree at `f2674f0`. The resolved pinned source revision was
`1b3c3cedc14fb3bee4294dea5e3515af74b8268a`. It returned
`INDEX_STRUCTURE_PASS_METADATA_ONLY` with 223,047 index keys,
128 numbered PLE shards, 10 referenced FP8 PLE files, one global
scale key and `float8_e4m3fn` in the config.
[Exact scope and output](../scripts/benchmark/evidence/dgx-a5-wizard-and-lychee-l0-result-20261013.md).

**L0_INDEX_JSON_PASS** now has actual-Hub evidence, superseding
the source-only and unexecuted descriptions above. **L0 tensor
headers, scale dtype/shape, weight hash and complete content are
still unverified**, as are the single-GB10 FP8 PLE runtime,
accuracy and strict RM. The original-fourth profile remains
`planned` and disabled. Next L1 is source/fixture adapter
analysis using this immutable checkpoint identity; do not
start a weight download or model load from this metadata PASS.


## 2026-10-16 L1 source review: FP8 PLE dispatcher (no host execution)

**GitHub SOURCE:** The current managed serve.sh only routes orcarouter,
nvidia, mazinb and retired Hybrid profiles. The normal v0.29 PLE mmap
mode is NOT evidence it can instantiate an FP8 E4M3 PLE embedding or
consume a global BF16 scale; the lychee888 registry remains planned
with PROFILE_INSTALLABLE=0. The current download, serve and Wizard
paths do not admit this checkpoint. No image-internal class/loader
inspection at the actual installed image digest has yet been captured.

**Publisher / external implementation (not DGX proof):** The lychee888
card documents the dual-DGX recipe using a patched vLLM PLE resolver
and PLE_QUANT_OVERRIDE=fp8. That resolver dispatches to
Qwen3_8FlashNextPLEFp8EmbeddingMethod; without the override, the
NVFP4 top-level quantization metadata can select a BF16 PLE
allocation instead. The expected checkpoint shape is 128 FP8 shard
weights and one BF16 [1] global weight_scale. The corresponding public
MiaAI-Lab dual-node instructions target TP=2 and are NOT a test of
our single GB10 TP=1 with managed v0.29 image.

**L1 fixture/implementation checks before any download or GPU launch:**
verify that a pinned candidate backend resolves the FP8 embedding
instead of BF16; registers both an FP8 weight and BF16 global scale;
maps all 128 n-gram shard names into the ten FP8 files without reading
an unrelated BF16 PLE shard; respects quantization ignored-layers
handling; and consumes the checkpoint scalar scale in the embedding
lookup. Also check the actual installed image's code/digest, loading
peak memory, TP=1 support and strict RM reserve independently.
A passing synthetic dispatch unit test is source-only; it is not a
physical READY or inference qualification.

**Decision:** No verified single-Spark compatibility yet.
Do not mutate existing image or register lychee888 as installable;
keep the 2026-10-13 real-Hub L0 PASS as the prior completed gate.

## 2026-10-16 follow-on source comparison after catplusplus L0 inventory PASS

The physical DGX catplusplus immutable-revision Hub tree now reconciles
legacy 63.876550574 GiB versus the complete 175.591585640 GiB repository.
This answers **file accounting only**; it does not elevate catplusplus
to loader qualification. Stored catplusplus root weights occupy
174.8553 GiB, well beyond the single Spark's official 128 decimal GB
coherent RAM for a wholly resident unmodified loader. Consequently
catplusplus has a higher source-level residency risk than the
**publisher-reported**, not independently byte-audited,
lychee888 123.25-GiB disk layout. Even lychee888's figure exceeds the
single Spark's 128 *decimal* GB in raw terms; real PLE mmap/offload
and runtime overhead must be verified rather than assumed.

**Existing reusable SOURCE:** `scripts/patch-nv-mixed.py`, delivered by
`scripts/Dockerfile.nv-mixed` for the NVIDIA candidate, patches
`Qwen3_8FlashNextPLEFp8EmbeddingMethod` dispatch **only for**
`ModelOptMixedPrecisionConfig` whose per-prefix
`_resolve_quant_algo(prefix) == "FP8"`. The Dockerfile layers this
over `vllm-skinny-tp1:v1` and creates a distinct target image
`vllm-nv-mixed:v2`. The owner-reported current installed image
`vllm-skinny-tp1:v1` is **not evidence that those modifications
are present** in its runtime. This source code is a useful reference
for the FP8 n-gram embedding method, **not a working lychee888
loader**: the lychee card instead describes NVFP4 model-level
quantization plus `PLE_QUANT_OVERRIDE=fp8` on the *dual-node*
third-party recipe. The exact pinned lychee config/loader binding
must be checked before reusing or adapting this dispatch;
catplusplus's MXFP8 fused projection aliases are yet another
independent requirement.

**Next SOURCE-only gate, no real launch:** inspect pinned lychee
`quantization_config` and relevant constructor/resolver branches;
prove the planned TP=1 image can register 128 FP8 PLE embedding
shards and a single BF16 global `weight_scale`, and actually
apply the scalar in lookup. Check naming and MoE/attention
quantization separately using mock/synthetic source tests.
Do not assume modelopt_mixed and modelopt/NVFP4 are interchangeable,
or that a source patch equals a built/pinned image. Preserve the
existing actual-DGX lychee Hub `INDEX_STRUCTURE_PASS_METADATA_ONLY`
as L0 evidence. No weight downloads, Docker build, GPU trials,
service changes or registry admissions are authorized by this
review.

## 2026-10-16 pinned FP8-PLE SOURCE gate added (not a loader implementation)

The independent `scripts/model/assess_lychee888_loader.py` now exposes a
**read-only, fixed-revision-only** Hub config/index gate. It always
pins `1b3c3cedc14fb3bee4294dea5e3515af74b8268a` before fetching
the revision API, `config.json` and `model.safetensors.index.json`;
no `.safetensors` is downloaded. It reuses the existing 128-shard /
10-file / single-global-scale L0 index checker, then reports the
actual pinned config's `quant_method`, `quant_algo` and `format` against
the maintained `patch-nv-mixed.py` predicate. The NVIDIA-specific patch
requires `ModelOptMixedPrecisionConfig` with per-prefix FP8 lookup;
a different quantization method, including compressed-tensors, must
**not** be treated as compatible merely because the PLE tensor
serialization matches. Even when the config class appears compatible,
the exact PLE prefix and runtime image implementation remain unverified.

Wizard entry: `./wizard.sh` → **3 Models → 7 Candidate Hub metadata →
3 lychee888 pinned FP8-PLE source gate**. Its success message says
SOURCE inspection completed and **NOT qualified**; it does not
register, install, download weights, build an image or start GPU.
The reproducible JSON fixture mode and synthetic tests verify pin
identity, L0 shard/scale mapping, rejected changed patch anchors,
compressed-tensors versus ModelOptMixed route discrimination,
and failure behavior. Actual pinned Hub output from this *new*
L1 gate is **NOT_CAPTURED** until a DGX operator runs it; the older
2026-10-13 pinned L0 PASS is preserved separately.

**Mandatory gates still open:** inspect exact installed image digest
and backend resolver code; verify FP8 embedding module and global
BF16 scale consumption; verify TP=1 partitioning and managed mmap/
offload memory plans without sacrificing NVIDIA RM/watchdog reserve.
The author's validated dual-Spark recipe and `PLE_QUANT_OVERRIDE=fp8`
are **external** implementation evidence, not a qualified single-GB10
managed path. No trial or destructive action is approved.
