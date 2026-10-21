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

## 2026-10-16 actual DGX FP8-PLE source gate result and installed-image source admission

**Physical operator evidence:** [DGX lychee888 fixed-revision source-gate transcript](../scripts/benchmark/evidence/dgx-lychee888-fp8ple-source-gate-physical-20261016.md).
The owner fast-forwarded a clean checkout to
`aea42fa4e7e768b4fd6603a13638d11c33976dbd` and used
Wizard **3 → 7 → 3**. On the real DGX, Hub JSON/index returned
`INDEX_STRUCTURE_PASS_METADATA_ONLY`, exactly 223,047 index keys,
128 FP8 PLE shard keys across ten files and one scale key at immutable
lychee888 SHA `1b3c3cedc14fb3bee4294dea5e3515af74b8268a`.
The actual pinned config reports **`quant_method=compressed-tensors`**
and **`format=mixed-precision`**, `quant_algo=None`,
`ple_embedding_dtype=float8_e4m3fn`.
The checker correctly returned
`nvidia_patch_source_dispatch=NOT_APPLICABLE` and
`SOURCE_ONLY_LOADER_UNQUALIFIED`. The installed manifest indicated
`vllm-skinny-tp1:v1` but **neither its digest nor actual internal
`ple_layer.py` source was verified**. The check did not download
weights or execute any GPU/Docker action. This **ACTUAL_DGX** gate
supersedes the earlier `NOT_CAPTURED` source-probe status, but does
not supersede the outstanding runtime/TP=1 blockers.

### Source-level FP8-PLE contract — external reference, not an installed patch

The publicly reviewed
[MiaAI-Lab dual-Spark PLE source](https://github.com/MiaAI-Lab/Qwen3.8-Flash-Next-Dual-DGX-Sparks/blob/main/files/ple_layer_patched.py)
(current source blob `b86cd6263ddfc77ed200d22271f49c4899c299b3`,
**mutable `main`, not installed image evidence**) demonstrates
separate implementation obligations:

1. **Selection:** the checkpoint-specific
   `text_config.ple_embedding_dtype=float8_e4m3fn` may be used to
   select `Qwen3_8FlashNextPLEFp8EmbeddingMethod` rather than
   relying on the unrelated model-wide
   `isinstance(quant_config, Fp8Config)` check. The historical
   dual-Spark recipe uses `PLE_QUANT_OVERRIDE=fp8`; a later external
   source version uses dtype-driven dispatch. Do not indiscriminately
   force FP8 on BF16 or packed-NVFP4 PLE checkpoints.
2. **Registration/load:** that FP8 method registers
   an FP8 embedding `weight` and global BF16 `weight_scale`.
   Correct file/key mapping (already checked at JSON level) is
   insufficient without verifying that the scale actually gets loaded,
   survives the model's sharded/CPU-offload loader path and is not
   left uninitialized.
3. **Consumption:** the PLE lookup/dequant path must multiply FP8
   embedding values by the global scale in the proper output dtype
   and device, failing closed if the scale is missing. Static code
   presence is not proof of runtime invocation or numerical accuracy.
4. **TP=1/residency:** the external reference is primarily a
   TP=2 dual-Spark recipe, not single Spark admission. The publisher's
   `123.25 GiB` on-disk checkpoint figure is itself greater than
   the Spark's official `128 decimal GB ~=119.21 GiB` unified RAM,
   before runtime/KV/monitor reserve. A safe, actually verified
   mmap/offload/residency model would be required; do not equate
   disk size directly with measured peak resident bytes.

The external recipe is AGPL-licensed; treat it as source/architecture
reference and respect its provenance. Do not copy its implementation
into the maintained backend without separate license and integration
review. The project's existing NVIDIA-only `patch-nv-mixed.py`
must remain unchanged on this evidence.

### Next read-only physical operator gate — Wizard-first

The standalone `scripts/model/audit_installed_ple_image.py` can
inspect an **already-existing, exact matching** managed
`qwen38-flash-next` container associated with local
`vllm-skinny-tp1:v1`. It invokes only bounded
`docker image inspect`, `docker container inspect`, and
`docker cp` read-only operations. It refuses mismatched image IDs,
unexpected source mounts and ambiguous or oversized source archives.
It parses the existing vLLM `ple_layer.py` source in memory and
records its SHA256, FP8 resolver branch signatures, BF16 global scale
registration and dequantization multiplication signatures. It cannot
create a container to fill in missing evidence.

Operator route: `./wizard.sh` → **3 → 7 → 4**
(**Existing image PLE loader source**). If no existing matched
container/source is available, the result is deliberately
`INCONCLUSIVE`; it does not fall back to starting a container,
building/altering the image, changing models or downloading weights.
Even a successful static source extraction is
`STATIC_ONLY_NOT_EXECUTION` and `lychee888_tp1_loader=NOT_QUALIFIED`.
An image-specific, isolated source patch and further synthetic tests
may be considered **only after** this source attestation, separately
from any real GPU qualification.

### 2026-10-16 actual existing-image audit: mount provenance blocked, not loader failed

The owner physically ran Wizard **3 → 7 → 4** and captured
`PLE_IMAGE_AUDIT=INCONCLUSIVE: Mounted vLLM source could differ from
image layer` with `DOCKER_MUTATION=NONE` and
`GPU_RUN=NOT_PERFORMED`. The old inspector treated any mount under
a broad vLLM Python prefix as a blocker; it did **not** report the
specific mount and did **not** prove it covered `ple_layer.py`.
See [physical mounted-source audit](../scripts/benchmark/evidence/dgx-lychee888-existing-ple-mount-audit-20261016.md).
It is not evidence of a failed model load.

**Remediation in the maintained read-only audit module:** when
`docker inspect` identifies a matching existing image and managed
container, only a mount whose destination actually covers the
candidate `ple_layer.py` pathname is relevant. Unrelated ModelOpt
or other vLLM file mounts are no longer blockers. If an exact
PLE file or ancestor directory is bind-mounted, use the Docker
mount's `Source` mapping to inspect the host's existing file
*read-only* with per-component no-symlink-following, bounded size
and stable identity checks; never claim that the bound host file
is part of the original image layer. Report
`source_origin=HOST_BIND_MOUNT_FILE_NOT_IMAGE_LAYER`,
container source pathname, bind destination and the SHA256 of the
bytes actually parsed. If no relevant mount exists, the legacy
`docker cp` source route remains available and is labeled
`EXISTING_CONTAINER_FILESYSTEM_NOT_PROVEN_RUNTIME`.
Ambiguous overlapping mounts, a non-bind source, missing bind file,
symlink, unstable read, unexpected source structure or image/container
ID mismatch still block safely as `INCONCLUSIVE`. Neither path
proves the file was actually imported by a running Python process.

This improvement is **SOURCE/SYNTHETIC CI only** until another
physical Wizard **3 → 7 → 4** run. No mounts, Docker objects,
images or services are changed by the audit; the installed image
digest and lychee888 TP=1 loader remain unqualified until captured.

### 2026-10-17 physical repeat: known PLE loader paths INCONCLUSIVE

The owner selected read-only Wizard **3 → 7 → 4** again and
received `PLE_IMAGE_AUDIT=INCONCLUSIVE: No known PLE loader path in
existing matching container`, `DOCKER_MUTATION=NONE` and
`GPU_RUN=NOT_PERFORMED`. The prior broad mount-blocking symptom
was no longer reported, but **no source was captured**, and the
exact image SHA/container ID and Docker-copy failure details were
not printed. See [exact operator transcript and inference
limits](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).
This does not establish absent FP8 PLE support; it distinguishes
neither packaging/version mismatch nor file-copy permission/layout
failure.

The maintained `audit_installed_ple_image.py` now checks twelve
bounded, fixed Python3.{10,11,12,13,14,15} dist/site-package
source paths, reports the already verified image/container identity
on path failure, and attempts a **small read-only Docker copy** of
the existing image's `qwen3_8_flash_next/nvidia/low_latency_gemm.py`
build reference. The project's skinny TP1 Dockerfile explicitly
asserted that sentinel pathname at build time. A sentinel
`SKINNY_GEMM_REFERENCE_READABLE` only narrows the suspected
layout to missing/relocated PLE source, **not** functional FP8 PLE
loading; `SKINNY_GEMM_REFERENCE_UNAVAILABLE` leaves broader
copy/package uncertainty. Both remain `INCONCLUSIVE` for the
lychee888 adapter, regardless of synthetic/source CI success.

The operator uses the **same** Wizard **3 → 7 → 4** after a clean
GitHub fast-forward; there is no new host mutation, image rebuild,
container exec/start or GPU activity. If all fixed probes are
unavailable, a separately designed read-only source inventory
needs to be qualified, not silently inferred.

### 2026-10-17 actual fixed-path/sentinel DGX output; copy transport UNKNOWN

A subsequent owner-run Wizard **3 → 7 → 4** obtained the exact local
image ID `sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4`
and existing managed container ID
`f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`.
However `PLE_DIAGNOSTIC_PLE_CANDIDATES_CHECKED=12`,
`PLE_DIAGNOSTIC_DOCKER_CP_REFERENCE_STATE=SKINNY_GEMM_REFERENCE_UNAVAILABLE`
and `PLE_DIAGNOSTIC_PLE_SOURCE_FILE=NOT_CAPTURED`.
`INCONCLUSIVE`, `DOCKER_MUTATION=NONE`, `GPU_RUN=NOT_PERFORMED`.
See the [dated physical evidence, second capture](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).
**Do not classify the PLE module as absent**: earlier probes suppressed
all `docker cp` error types (missing path versus daemon/filesystem
copy issue), and no effective import/runtime evidence was collected.

The updated read-only inspector now aggregates only sanitized Docker
copy failure classifications (`SOURCE_PATH_NOT_FOUND`,
`PERMISSION_DENIED`, `DAEMON_UNAVAILABLE`,
`PARENT_NOT_DIRECTORY`, `COPY_FAILED_UNCLASSIFIED`, and bounded
copy timeout/oversize outcomes) for both PLE and GEMM reference
file attempts. Raw Docker stderr, mount sources and user paths are
never printed. It also fetches one small non-model file
`/etc/group` from the existing managed container using `docker cp`
and validates only the bounded in-memory TAR header. This control
can distinguish broad copy-transport failures from package path
failures even when both PLE and GEMM references are missing.
No large directory enumeration, checkpoint access, model download,
container create/start/exec, image build or GPU execution is added.

The correct operator route is unchanged: **Wizard 3 → 7 → 4** after
a clean checkout update and source CI. An accessible generic TAR
means the copy mechanism works for at least that file; it is
**not** a proof that any model source is present, importable or
compatible with lychee888's `compressed-tensors` FP8-PLE format.
The actual new copy-transport diagnostic outcome is still
`NOT_CAPTURED`, not a source-level PASS.

### 2026-10-17 all existing-container Docker cp requests failed (ACTUAL_DGX)

The next actual DGX read-only Wizard **3 → 7 → 4** captured
`COPY_FAILED_UNCLASSIFIED:12` for PLE paths,
`COPY_FAILED_UNCLASSIFIED:12` for the Skinny-GEMM source paths,
and `COPY_FAILED_UNCLASSIFIED` for the generic small
`/etc/group` copy. Image ID remained
`sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4`,
with existing managed container ID
`f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`.
`GPU_RUN=NOT_PERFORMED` and `DOCKER_MUTATION=NONE`.
See [latest actual DGX source-copy evidence](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

**The common Docker-copy/control-file failure now takes priority
over guessing more PLE package paths**. The result still does not
prove that `ple_layer.py` or the GEMM module is absent, nor
that Docker itself is broken: only that this checker received
nonzero/unusable copy results. The installed container's runtime
state and specific daemon error response were not captured.

The source-only diagnostic now prints `PLE_DIAGNOSTIC_CONTAINER_STATE`
from Docker inspect using an allowlisted set and, for the *single*
existing `/etc/group` copy failure, safe details:
`PLE_DIAGNOSTIC_DOCKER_CP_SMALL_FILE_EXIT_CODE`,
`..._STDERR_BYTES`, `..._STDERR_SIGNALS`.
Error signals are only fixed category names, e.g.
`DOCKER_DAEMON_REPLY`, `ARCHIVE`, `OVERLAY`, `MOUNT`,
`FILESYSTEM`, `INVALID_ARGUMENT`, `PERMISSION`.
No raw stderr, mounted host path or file content is exposed.
Expanded known-error classifications remain fail-closed.
The operator route stays **Wizard 3 → 7 → 4**; no start, exec,
copy-to-host, model install, image build, GPU or service change.
The next actual DGX result is **NOT_CAPTURED**. Synthetic CI
only demonstrates the safe parsing/reporting source.

### 2026-10-17 root-cause narrowed: read-only Docker-copy transport on exited container

The latest actual DGX Wizard **3 → 7 → 4** output shows:
`container_state=exited`,
twelve PLE and twelve Skinny GEMM copies all failed as
`FILESYSTEM_READ_ONLY`, and the independent `/etc/group`
control copy failed identically (`exit_code=1`,
`stderr_bytes=76`,
`stderr_signals=DOCKER_DAEMON_REPLY,FILESYSTEM`).
The same known local image SHA256 and protected container ID
were verified; neither PLE source nor effective runtime was
read. See [physical read-only copy evidence](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).
This supports a **common copy-transport blocker**, not missing
source files or failure of lychee888's FP8-PLE loader.

Docker's published `docker cp` CLI supports stopped containers;
a separate `--read-only` container rootfs option exists.
We have **not yet observed** the container's
`HostConfig.ReadonlyRootfs` value or full daemon error text,
so we cannot equate the short sanitized category with either the
rootfs configuration or host filesystem health. No root remount,
daemon restart, image rebuild, container replacement or GPU launch.

The maintained audit now uses a **single small non-model
`/etc/group` copy preflight** after exact image/container checks
and before 24 PLE/GEMM copy attempts. For
`FILESYSTEM_READ_ONLY` or
`CONTAINER_ROOTFS_READ_ONLY`, it immediately returns
`INCONCLUSIVE`, marks source probes
`NOT_ATTEMPTED_PRECHECK_BLOCK`, and records safe,
allowlisted `container_readonly_rootfs=TRUE/FALSE/UNKNOWN`
from existing Docker inspect. This is a read-only inspection
of existing metadata, **not** a change to the setting.
If the control succeeds, targeted file probes proceed as
before; a read-only configuration flag by itself is **not**
used to infer a transport failure.

Next operator run uses unchanged Wizard **3 → 7 → 4**
after source CI. A direct `docker cp` against only
`/etc/group` with output streamed to `/dev/null` can provide
the original Docker error for manual interpretation **after
sanitizing the error message**. This is diagnostic only;
lychee888 remains `SOURCE_ONLY_LOADER_UNQUALIFIED`.


## 2026-10-17 actual DGX Docker-copy preflight result

The owner executed the revised read-only existing-image Wizard **3 → 7 → 4**
on the protected managed image/container. `HostConfig.ReadonlyRootfs=FALSE`
and `State.Status=exited` were observed. The small generic
`/etc/group` copy failed at the Docker-copy transport layer
(`FILESYSTEM_READ_ONLY`, exit 1, stderr 76 bytes,
`DOCKER_DAEMON_REPLY,FILESYSTEM`); the new preflight **skipped
all 24 subsequent PLE/GEMM copies** with
`NOT_ATTEMPTED_PRECHECK_BLOCK`. This is physical evidence for
the auditor's conservative stop, not for a particular Python module
layout or working FP8-PLE implementation. Exact daemon error
provenance and effective image source remain unresolved; do not infer
that Docker is configured with readonly rootfs or that host root
needs a remount. No payload or GPU was used.

[Chronological operator output and interpretation limits](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).
Next gate: a bounded reviewed exact Docker error diagnostic without
changing any Docker object, then source SHA/static FP8 PLE dispatch
and BF16 scale analysis. lychee888 remains non-installable and
single Spark TP=1 unqualified.

## 2026-10-17 exact Docker-copy error: nested model/config bind hypothesis

An actual non-model copy `docker cp qwen38-flash-next:/etc/group -
>/dev/null` failed with `Error response from daemon: openat
model/config.json: read-only file system`, exit 1, on host checkout
`7c93e4db2efd37d0bdc4f2f40748b1fe23d5f360`.
This is no proof that PLE modules are absent. The project's serve
configuration creates nested read-only bind destinations `/model`
and `/model/config.json` when its config override is present;
Moby patched an overlapping-bind-mount `docker cp` failure in
[upstream commit 7420e624](https://github.com/moby/moby/commit/7420e6240935b25644155447a3197a25af703d35).
This suggests Docker's nested-mount replay/write-open mechanics
could account for an error on an **unrequested** path; exact root
cause is still **INCONCLUSIVE** pending physical Mounts inventory
and Docker Engine version.

The SOURCE-only inspector adds a bounded, sanitized read-only
`PLE_DIAGNOSTIC_DOCKER_CP_MODEL_CONFIG_MOUNT_TOPOLOGY` field:
`MODEL_CONFIG_NESTED_RO_BINDS` denotes only the container-inspect
structure, not a confirmed daemon fault or working PLE source.
Run the existing Wizard **3 → 7 → 4** after clean fast-forward
to collect it; no Docker reconfiguration, restart, runtime launch,
model download or loader admission is authorized.

## 2026-10-17 actual DGX nested /model/config.json bind confirmation

Physical operator fast-forwarded to verified HEAD
`cee107d9e47b278d7dede40a8d401ea9c2ccea32` and ran
read-only Wizard **3 → 7 → 4**. Against the same protected image
and managed stopped container, `HostConfig.ReadonlyRootfs=FALSE`
while `MODEL_CONFIG_NESTED_RO_BINDS` **confirms both**
`/model` and `/model/config.json` are separate read-only bind
mount destinations. A `docker cp` of the non-model `/etc/group`
file still failed with `FILESYSTEM_READ_ONLY`, exit code 1;
24 source copies were correctly bypassed by
`NOT_ATTEMPTED_PRECHECK_BLOCK`, no Docker mutation/GPU execution.
The prior daemon stderr `openat model/config.json: read-only file
system` now has corroborating actual mount-topology evidence.

Moby upstream corrected overlapping bind handling in
[2026-09-17 commit 7420e624](https://github.com/moby/moby/commit/7420e6240935b25644155447a3197a25af703d35),
but the installed Docker Engine server version and exact root-cause
match are **NOT_VERIFIED**. This is a Docker copy-path blocker, not
a PLE implementation, checkpoint-integrity or TP=1 result.
The next read-only gate is the Docker **server version**, followed
by a reviewed extraction option that needs no protected container
restart, recreation, remount or image rebuild.

[Complete physical evidence](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

## 2026-10-17 — Docker 29.6.2 official source versus patched 29.8.2

The owner reported **ACTUAL_DGX** `docker version` server
`29.6.2`, API `1.55` and `docker info` storage driver
`overlay2`. Comparing official Moby Docker Engine tags shows
`docker-v29.6.2` still has
`root.Open(relDest)` plus `O_CREATE|O_WRONLY` in
`daemon/containerfs_linux.go`, whereas
`docker-v29.8.2` uses `O_PATH` and `O_EXCL`
to avoid write-opening existing nested bind-mount targets.
[Docker 29.8.2 release notes](https://docs.docker.com/engine/release-notes/29/)
explicitly identify the nested bind mount `docker cp` fix.

The recorded physical `MODEL_CONFIG_NESTED_RO_BINDS`
and `openat model/config.json: read-only file system`
are consistent with that **older upstream code path**.
This is a high-confidence defect match, **not** a claim that
the exact local `dockerd` binary was inspected or that
`overlay2` is damaged. Do not upgrade the protected host
just to complete source inspection. First assess the
availability of an already existing container of the
same immutable image without overlapping bind mounts,
or another carefully reviewed bounded read-only way to
attest image-origin PLE source. Source and single-GB10 TP=1
remain unqualified. See
[actual physical record](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

## 2026-10-17 — Potential existing historical A/B comparison container, not yet qualified

ACTUAL_DGX reported a 20,629,141,958-byte (~19.21 GiB)
`vllm-skinny-tp1:v1` image at the same pinned digest
and two stopped containers from an `ancestor` filter.
One, `qwen38-ab-legacy`
(`57eada965768b01eb412b10826ec4f0be9c4ed352abd87957c4ffbe932f27a56`,
exit 137), might provide a **non-mutating comparison
source view** if its *immutable* `.Image` matches and
it has no blocking nested readonly mounts. This has
**not** been verified; image tags/ancestor filters are
not enough. The other object is the protected managed
`qwen38-flash-next` with the known nested RO config.

The next step is a small, read-only `docker container
inspect qwen38-ab-legacy` bounded to identity, state,
ReadonlyRootfs and non-sensitive mount destination/type/RW.
No historical container deletion/start, Docker configuration
change, bulk `docker image save`, checkpoint access or
GPU execution. A future successful `docker cp` would
attest the historical container filesystem bytes
and SHA256, **not automatically** prove that the bytes
are the original installed image layer or current
managed runtime's effective PLE loader. lychee888
stays non-installable and TP=1 unqualified.

## 2026-10-17 — Historical A/B container exact image match but same nested bind blocker

The physical DGX read-only inspection of historical
`qwen38-ab-legacy` confirms container
`57eada965768b01eb412b10826ec4f0be9c4ed352abd87957c4ffbe932f27a56`,
same exact image SHA256
`01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4`,
`exited`, `ReadonlyRootfs=false`, and **the same pair**
of nested readonly bind destinations `/model` and
`/model/config.json`. Other observed cache mounts are
separate RW binds. The alternative container is **not
a qualified way around the Docker 29.6.2 `docker cp`
pre-fix path**. No historical-container copy was attempted;
its model data and original evidence are preserved.

The current stage remains **L1 local installed-loader source
NOT_CAPTURED**, not a checkpoint loader failure. Candidate-only
source comparisons may proceed with explicit external provenance,
while any local layer extraction must remain bounded and reviewed
rather than assuming `docker save` for the ~20.63-GB image
is free. Protect both containers and do not create/start/restart,
reconfigure Docker, access model weights or admit lychee888.
[Exact physical record](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

## 2026-10-18 — Source acquisition decisions after identical legacy nested binds

**SOURCE-only feasibility planning is implemented** in existing
`scripts/model/audit_installed_ple_image.py` with
`--plan-isolated-source`. This developer/reviewer-only
route does no `docker cp` or Docker mutation. It requires
exact immutable image identity for the managed and historical
containers, stopped/created states, valid fixed nested
mount records, positive declared image size, and checks
image `Config.Volumes`. It outputs sanitized decisions.
An image-declared volume is a hard planning STOP because
Docker `create` can allocate an anonymous volume even when
no explicit `--volume` is given. A no-volume preview is
**review-worthy only**, never an operator authorization.

A future **temporary mountless created-but-never-started**
container could in principle avoid the Docker 29.6.2
nested RO mount replay precondition and let a single bounded
PLE Python file be copied and SHA256-inspected from the
same pinned image ID. This remains **not implemented, not
executed, and not authorized**: before any such action the
operator must separately approve an exact-image create-only
procedure, unique temporary name/label, zero model/GPU/
network exposure, bounded single-file reads, automatic
same-ID cleanup, host disk/I/O cap, protected-container
immutability and explicit STOP/recovery rules. This
limited create/delete changes Docker state even though
no GPU is run. Never use `docker run`, `exec`, daemon
restart or blind `docker save` as an unreviewed shortcut.

### External upstream references — distinct from installed image

- [vLLM PR #53899](https://github.com/vllm-project/vllm/pull/53899)
  (closed **unmerged** 2026-09-21) covers CPU-offload work.
  Its published offload validation is BF16/FP8 on GB200 at
  TP2/TP4 or DP4+EP4, **not** single GB10 TP=1.
  The source tree and file namespace have changed relative
  to this locally built image; do not assert exact-byte
  equivalence.
- [vLLM PR #54882](https://github.com/vllm-project/vllm/pull/54882)
  (merged 2026-09-03) adds an FP8 PLE resolver branch for
  `ModelOptMixedPrecisionConfig`; it does not prove support
  for pinned lychee888's `compressed-tensors` /
  `mixed-precision` quantization dispatch.
- [Community forced-FP8 patch](https://github.com/getrefined/Qwen3.8-Flash-Next-NVFP4-vLLM-DGX-Spark)
  shows a minimal environment override around the resolver,
  but targets a different checkpoint and deployment; it
  does not validate lychee888 expert quantization, BF16
  global PLE scale consumption, TP=1, or memory safety.

**Next source gates:** establish exact image-origin
`ple_layer.py` SHA/code before any runtime adaptation;
map `CompressedTensorsConfig` selection and weight-loader
compatibility independently, then global BF16 PLE scale
registration/use, and finally single-GB10 TP=1 memory and
functional readiness under separate approval. No large
checkpoint transfer or GPU trial is authorized by source
evidence.

## 2026-10-18 actual DGX isolated preview passed without volume declaration

The actual DGX operator fast-forwarded to
`769332111dc4cdfa13e9817544b9166402985f66`,
then executed the independently maintained
`audit_installed_ple_image.py --plan-isolated-source`.
The read-only inspector found the exact expected
`vllm-skinny-tp1:v1` image ID, image metadata
size 20,629,141,958 bytes, both protected/historical
container `MODEL_CONFIG_NESTED_RO_BINDS` and
`DECLARED_IMAGE_VOLUMES=NONE`.
The outcome `REVIEW_CANDIDATE_NOT_AUTHORIZED`
is a **physical metadata preview**, not authorization
to create a temporary object or an indication that the
source can be copied.
It performed exactly three Docker inspect commands,
no copy/create/delete, no payload download or GPU work.

Further review contract is now in
[isolated source-read proposal](LYCHEE888-ISOLATED-SOURCE-READ-PLAN.md):
it requires an exact-image mountless, **created-only**
object, no volumes/network/GPU/model binds, a bounded
single TAR control + source file, exact new-ID owner-label
cleanup and before/after protected-asset checks.
All Docker create/remove instructions are
**NOT IMPLEMENTED / NOT AUTHORIZED**;
the plan must not be interpreted as permission.
Single-GB10 TP=1, FP8 routing and BF16 global scale
remain unqualified.

## 2026-10-18 — exact-ID temp source probe source implemented after owner approval

The owner approved a **single new temporary created-only container**
from the existing exact image ID, one bounded non-model copy control
and fixed PLE source inspections, then ownership-checked
exact-ID-only cleanup. The approved scope excludes protected
containers, checkpoint/GPU use, container starts, daemon changes,
image rebuilds and PR merges. `probe_isolated_ple_source.py`
is the guarded independent research module; it is deliberately
not an ordinary model-install Wizard action.

Source and synthetic tests are committed; no actual DGX Docker
create or copy has been performed by the assistant. Physical
success requires a completed exact HEAD CI success, clean
owner checkout, temporary source path+SHA, cleanup verified
by exact ID and original container postcheck match. Failure
or uncertain cleanup blocks any further repeated attempt.
[Scope and detailed stop/recovery rules](LYCHEE888-ISOLATED-SOURCE-READ-PLAN.md).

## 2026-10-18 — Physical PLE source SHA captured but postcheck FAIL_REVIEW

At exact local SHA `f1bce18ef6ab444ced20f4efed2ba8ec42a250f0`,
the actual DGX owner executed the approved one-shot,
no-mount, unstarted temporary Docker image-source probe.
It captured source
`/usr/local/lib/python3.12/dist-packages/vllm/models/qwen3_8_flash_next/nvidia/ple_layer.py`,
SHA256 `a71144c1d36e06f22a2da1b1ada900076597fe5e824a911e7ada86249a0993e7`.
Source AST reported `NATIVE_FP8_CONFIG_ONLY_SOURCE`,
BF16 global PLE scale registration and scale multiply
`PRESENT`. This resolves the original
`SOURCE_FILE_NOT_CAPTURED` blocker at the **static image
source-snapshot level**. It does **not** demonstrate that
lychee888's `compressed-tensors` / `mixed-precision`
checkpoint would instantiate `Fp8Config`, choose the
FP8 PLE method, or load/use BF16 scale at runtime.

The temporary container was reported removed and missing
by exact ID. **However protected-container postcheck
returned `FAIL_REVIEW`**, so the whole physical
procedure has NOT passed its protected-state gate and no
new temp trial is approved. The output doesn't identify
whether a volatile Docker inspect field or a real
protected-state change caused the mismatch; never assume
either. Next step is narrowly scoped read-only identity,
state, topology and inspect-field-drift diagnosis.
[Full physical transcript](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

## 2026-10-18 — Read-only follow-up to failed protected postcheck without repeated temp creation

The previous one-shot actual DGX source probe achieved a
source SHA256 and reported exact temp removal but
`PLE_TEMP_PROTECTED_POSTCHECK=FAIL_REVIEW` with
unclassified field drift. An isolated read-only
`inspect_ple_postcheck_readonly.py` module and
offline tests now inspect the current protected
containers and pinned image by known IDs/name, plus
temporary name/ID absence. Its sanitized output may
prove current static configuration without claiming
the historical pre/post comparison passed.
**No second temporary probe is authorized.**
[Original transcript and result](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

## 2026-10-18 — Physical postcheck CURRENT_ONLY pass after mount-order classification

A new actual-DGX read-only check at exact clean
`a24cd3a7ce48c7531cabbdfec0139327eefce18a`
and CI 2/2 SUCCESS reports
`PLE_POSTCHECK_CURRENT_STATIC_POSTCHECK=PASS_CURRENT_ONLY`.
The approved one-off temporary Docker object remains
absent by exact ID and name; pinned image and both
stopped protected container identities, rootfs flags,
nested RO mount topology all match. Managed
name/ID full-mount record values match modulo ordering
(`ORDER_ONLY`); historical A/B mount records match
including ordering (`IDENTICAL_ORDER`). All other
original name-vs-ID metadata fields match.
The historical original source-probe `FAIL_REVIEW`
is NOT retroactively cleared; lost pre/post field-level
information precludes definitive explanation.

Installed-image-derived source static snapshot SHA:
`a71144c1d36e06f22a2da1b1ada900076597fe5e824a911e7ada86249a0993e7`,
`NATIVE_FP8_CONFIG_ONLY_SOURCE`, BF16 scale
registration and multiply signatures `PRESENT`.
Next independent L1/L2 source-only gate: investigate
`compressed-tensors` `mixed-precision` to FP8 PLE
dispatch and scale-load contract without runtime
mutation or checkpoint download.
[Physical evidence](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

## 2026-10-18 — installed-source receipt versus compressed-tensors checkpoint dispatch

**Actual image-derived PLE source is known by SHA256/static AST receipt only:**
`/usr/local/lib/python3.12/dist-packages/vllm/models/qwen3_8_flash_next/nvidia/ple_layer.py`
SHA256
`a71144c1d36e06f22a2da1b1ada900076597fe5e824a911e7ada86249a0993e7`.
The bounded AST found
`NATIVE_FP8_CONFIG_ONLY_SOURCE`, a BF16
`weight_scale` registration signature and a scale
multiplication signature. The actual source bytes
are not retained in GitHub; do not infer a complete
installed loader path or method invocation from signatures.

Pinned lychee888 uses `compressed-tensors`
`mixed-precision` (not `modelopt_mixed`),
FP8 PLE dtype metadata, 128 indexed PLE weight
shards and one indexed global scale. The vLLM native
`Fp8Config` selector is **not proved reachable** from
the expected `CompressedTensorsConfig` class. The
NVIDIA MIXED_PRECISION-specific project patch
is **not a tested CT adapter**, and merely
forcing the FP8 selection branch would not yet
prove exact prefix/scheme matching, global scale
`weight_scale` register/load/validate semantics
or checkpoint-specific MoE dispatch.

A maintained source-only gate, `assess_lychee888_loader.py`,
now emits both the pinned checkpoint declaration
and the physical installed source SHA/route,
`NO_DIRECT_NATIVE_FP8_CLASS_MATCH_PROVEN` and
`BLOCKED_SOURCE_ONLY_UNQUALIFIED` with offline
negative/positive-metadata tests. Do not promote
the lychee888 profile to installable.

**External comparator, not installed proof:** newer
[vLLM PLE embedding API](https://docs.vllm.ai/en/latest/api/vllm/models/qwen4_exp/common/ngram_embedding/)
exposes explicit `embedding_dtype=float8_e4m3fn`
and `CompressedTensorsConfig` checks. That implementation
may inform a separately approved adapter design, but
its newer code and runtime assumptions cannot simply
be applied to the pinned 20.63-GB image or a single
DGX Spark TP=1. A future patch must be isolated,
based on verified source bytes, and validated without
changing the protected image/containers; approval
for such modification has **NOT** been given.

## 2026-10-18 — Nominal single-GB10 memory screen independent of loader dispatch

Separate from `compressed-tensors` FP8 PLE method
dispatch, the pinned metadata gate now checks optional
safetensors index `metadata.total_size` against
[DGX Spark's nominal 128 GB unified LPDDR5x](https://docs.nvidia.com/dgx/dgx-spark/hardware.html).
The model card reports 123.25 GiB checkpoint on disk
and `total_size=132279699754` bytes in the index.
If verified from the pinned JSON index, this exceeds
128,000,000,000 nominal memory bytes before Python,
vLLM runner, KV cache or other headroom, meaning a
naively **fully resident, untransformed** checkpoint
has no feasible headroom under that simple comparison.
It is **not** a physical memory-use measurement:
in-memory transforms, mmap, PLE row streaming and
offload can change residency, and none are qualified
for this installed image/lychee888 TP=1.
The new assessor reports `NOT_VERIFIED` when the
index has no positive integer `total_size`; it
never reports a positive fit qualification merely
because indexed bytes are smaller than nominal RAM.
No disk/host/GPU workload was run.

## 2026-10-18 — Pinned physical JSON L0 confirms larger-than-nominal index and CT loader block

The actual DGX owner ran `assess_lychee888_loader.py
--json` at exact clean `b9114544eb35d7275740cf0ca2e9d010134f7cbb`
with 2/2 CI SUCCESS; pinned revision
`1b3c3cedc14fb3bee4294dea5e3515af74b8268a`.
L0 index: 223047 keys, 128 FP8 PLE n-gram shards
in ten expected files, exactly one indexed global
scale, declared FP8 e4m3fn embedding dtype;
`compressed-tensors` / `mixed-precision`.
Pinned index `metadata.total_size=132279699754`
bytes, **4,279,699,754 bytes** above nominal
single Spark 128 GB system-wide unified memory,
without measuring any resident, cached or
transformed allocation. The on-host execution
downloaded no weight shards and launched no GPU
work.

The output reuses the older physically acquired
PLE source SHA and route as **static code constants**:
`a71144c1d36e06f22a2da1b1ada900076597fe5e824a911e7ada86249a0993e7`,
`NATIVE_FP8_CONFIG_ONLY_SOURCE`. It did not
re-audit Docker or execute the installed PLE
quantization method. The native FP8 selector
and `CompressedTensorsConfig` prefix resolution,
the BF16 global scale and TP=1 memory remain
`NOT_QUALIFIED`. Loader cannot be made
installable solely from L0.
[Actual physical transcript](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

## 2026-10-18 — CT group target inventory remains structural, not PLE loader resolution

The maintained pinned JSON-only diagnostic now
exposes `ct_config_groups`, `ct_declared_targets`,
`ct_ple_target_string_mentions`,
`ct_ignore_entries`,
`ct_ple_ignore_string_mentions` and
`ct_target_resolution`. This is only a
**checkpoint configuration structure inventory**:
the CT quantization scheme can name module types,
exact prefixes and regexes and apply ignore
rules; the installed vLLM runtime's full
matching semantics have not been inspected.
Consequently no positive count, even an exact
PLE prefix, proves that
`_get_ple_embedding_quant_method` selects an
FP8 method; zero mention may also coexist
with class-targeted rules.
The independent native `Fp8Config` vs
`compressed-tensors` mismatch and
`BF16_SCALE_LOAD_UNVERIFIED` remain blocked.
No unapproved installation, image rebuild or
GPU run is permitted.

## 2026-10-18 — External OrcaRouter community TP1 offload is not lychee888 FP8 admission

The supplied full Arca report and posted `config.json`
document **third-party claimed** one-DGX-Spark TP=1
OrcaRouter NVFP4 success with
`VLLM_PLE_CPU_OFFLOAD=1`, 24 GiB KV,
MTP=2 and high (~97%) memory usage. The
image `vllm/vllm-openai:qwen38-flash-next-arm64-cu130`
differs from our installed pinned skinny image.
Its posted config has CT `mixed-precision`,
2 groups with 300 explicit FP8 targets plus one
NVFP4 expert regex, 753 ignored entries, but
**no `ple_embedding_dtype` or direct FP8 PLE
ngram target**. It is not a lychee888 FP8-PLE
global-BF16-scale load proof, nor independently
verified long-context/soak evidence.

Newer vLLM PLE pinned-CPU offload shares the
GB10 128GB unified memory pool: it avoids a
GPU-resident table but **does not guarantee a
smaller total physical footprint**.
Checkpoint file-backed approaches in upstream
PR #58439 `checkpoint_mapped` and PR #58815
`host_file_gather` may avoid retaining the
whole FP8 PLE table, but both are as of this
date open/unmerged, and are neither installed
nor certified for lychee888. The project's
index total `132279699754` bytes and
installed FP8 dispatch/scale-load blockers
remain independently unresolved.

[Exact third-party comparison, risk and source
links](COMMUNITY-ORCAROUTER-SPARK-PLE-OFFLOAD-20261018.md).
Further work is SOURCE_ONLY. Do not translate
the posted Docker command, privileges,
external-image tag or checkpoint paths into
a Wizard install/launch action without
specific owner approval and isolation.
