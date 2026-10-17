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
