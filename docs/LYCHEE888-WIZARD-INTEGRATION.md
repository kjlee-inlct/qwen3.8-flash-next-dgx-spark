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
