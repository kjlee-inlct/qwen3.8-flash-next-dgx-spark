# H38 exact installed vLLM loader and CT completion source gate — 2026-10-09

Status: **SOURCE-ONLY IMPLEMENTATION STAGED / NOT EXECUTED ON DGX**.
This gate will not launch a model, read safetensors payloads, change the
checkpoint, implement `device="meta"`, change GPU allocator behavior or
qualify host stability.

## Trigger: checkpoint order Attempt 03 (observed)

The exact 18-indexed-file OrcaRouter header-only check completed on
`f875aa2ea141e004fe2c0b37174bd275d9df39a1`, image
`sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`,
with **`ORDER_GATE=FAIL` and `metadata_check_rc=3`**, not INVALID.

- `model-mtp.safetensors` contributes **two distinct
  `mtp.layers.0.mlp.experts` keys** that the prior inspector counted
  as a second numeric layer 0. That is a **name-namespace collision**
  and not proof of duplicated base-model layer 0 weights.
- Base-model routed layer 8 is split across numbered shards **4→5**.
- Base-model routed layer 11 is split across numbered shards **5→6**.
- Base-only revisit diagnostic remains **[8,11]**; the previous strict
  one-contiguous-run checkpoint-order gate **still fails** even if MTP
  is excluded *for diagnostic display only*.
- The two static hypothetical routed-byte retention peaks were
  **6,448,748,544 bytes**. This is NOT observed resident RAM,
  pinned RAM, GPU bytes, or RM allocation volume.

Exact terminal evidence:
`orcarouter-h38-checkpoint-metadata-order-attempt03-revisit-ownership-20261009.md`.

**Decision:** stop rescanning the unchanged checkpoint. The remaining
question is the **actual installed H38 vLLM loader source** and its
selected stream / ModelWeightParameter completion semantics.

## Background: upstream vLLM v0.29.0 source, not yet installed-H38 proof

The parent container ancestry starts at `vllm/vllm-openai:v0.29.0`
(`scripts/Dockerfile.v029-orcarouter`) and applies H11/H12/H38 code
patches. Upstream code inspection helps target a safe exact-installed
check but is NOT a substitute for executing it.

- `DefaultModelLoader._prepare_weights` references
  `filter_duplicate_safetensors_files` (index weight_map);
  `_get_weights_iterator` can select default single-thread,
  multi-thread, fastsafetensors or InstantTensor load paths, depending
  on configuration. Upstream source:
  https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/model_executor/model_loader/default_loader.py
- Upstream `safetensors_weights_iterator` naturally sorts paths,
  then calls `safe_open(...).keys()` and `get_tensor(name)` in the
  lazy/default branch. It also has eager, torchao, prefetch and
  local-expert-skip alternatives:
  https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/model_executor/model_loader/weight_utils.py
- Upstream `Qwen4ExpForCausalLM.load_weights` and
  `Qwen4ExpForConditionalGeneration.load_weights` use
  `WeightsMapper(orig_to_new_substr={"mtp.": None})`. Upstream
  `WeightsMapper.apply` drops names mapped to None, and
  `AutoWeightsLoader.load_weights` applies the mapper to the
  incoming iterator:
  https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/models/qwen4_exp/nvidia/model.py
  https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/model_executor/models/utils.py
- **Important order distinction:** when the default iterator path is
  selected, `get_tensor(name)` is called upstream of
  `AutoWeightsLoader`'s name mapping. Thus a source-level rule
  dropping `mtp.` model assignment is **not evidence** that the
  MTP file is excluded before disk/tensor materialization. Whether
  actual H38 loaded those tensors, and with what lifetime, is
  **unverified** without exact config/event evidence.
- Upstream `make_online_process_loader` buffers bound loader args
  in `info.loaded_weights`, updates `load_numel`, and triggers
  `_layerwise_process` at `load_numel >= load_numel_total`.
  `_layerwise_process` materializes meta tensors and replays the
  original weight loaders before CT post-load processing. The
  correct completion count and scale behavior for H38 CT **are
  not proven** by this syntactic presence alone:
  https://github.com/vllm-project/vllm/blob/v0.29.0/vllm/model_executor/model_loader/reload/layerwise.py

## New guarded exact installed-H38 source probe

- `scripts/benchmark/inspect-h38-installed-loader-source.py`:
  Python **stdlib-only AST reader**, installed-source SHA256 fingerprints,
  no imports of vLLM, torch, safetensors, CUDA or model code.
- `scripts/benchmark/check-h38-installed-loader-source.sh`:
  requires an exact 40-hex clean checkout SHA, unchanged installed
  image ID
  `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`
  and inherited H11/H12/H38 labels. Uses ephemeral CPU-only
  unprivileged runc, read-only rootfs, no network/pull/GPU,
  `--cap-drop ALL`, no-new-privileges and a **private capped 32 MiB
  `/tmp` tmpfs** (avoids the previous no-tempdir failure).
  Bind-mounts only the inspector **read-only**, NOT the checkpoint.
- `tests/test_h38_installed_loader_source.py`:
  synthetic positive/negative source contracts, fail-closed
  mismatch detection and runner safety guard tests.

The inspector fingerprints/AST-checks eight **installed image** source
files covering `DefaultModelLoader`, `weight_utils`,
`WeightsMapper`/`AutoWeightsLoader`, Qwen4Exp model classes,
`reload/layerwise.py`, `reload/meta.py`, `base_loader.py`
and H11/H12 CT W4A4 NVFP4.

Expected source-only facts IF it passes:
- index-referenced file selection and primary/secondary sources;
- natural-sort + per-file `safe_open.keys()` / `get_tensor`
  in the installed single-thread safetensors path;
- presence of multiple alternative load paths;
- causal and conditional Qwen4Exp `mtp.` mapping and
  `WeightsMapper` drop semantics;
- layerwise buffer/completion/meta replay and packed CT aliases.

**A PASS does not tell us** which load format/strategy, EP filtering,
MTP architecture, selected loader, active H38 runtime configuration,
thread/pre-fetch mode, actual number of copied Tensors or host memory
was used. The probe explicitly emits the negative fields
`exact_h38_active_loader_config_verified=NO`,
`runtime_file_and_mtp_iteration_proven=NO`,
`shard_split_layer_8_11_buffer_peak_bounded=NO` and
`host_stability_qualified=NO`. A static test must not be used to
override the earlier checkpoint `ORDER_GATE=FAIL`.

## One-time host source check after CI passes

```bash
(
  set -Eeuo pipefail
  cd ~/Workspace/llm/qwen3.8-flash-next-dgx-spark
  git fetch --prune origin
  git switch feat/h38-managed-integration
  git pull --ff-only origin feat/h38-managed-integration

  TARGET="REPLACE_WITH_EXACT_REVIEWED_CI_GREEN_SHA"
  test "$(git rev-parse HEAD)" = "$TARGET"
  test -z "$(git status --porcelain=v1 --untracked-files=all)"

  H38_LOADER_SOURCE_TARGET_SHA="$TARGET" \
    bash scripts/benchmark/check-h38-installed-loader-source.sh \
    2>&1 | tee /tmp/h38-installed-loader-source-contract.txt
)
```

No model checkpoint mount is needed. Preserve the exact source SHA256
and print fields from the execution. If the inspector fails due to
source drift, do not force a PASS or silently switch image versions:
inspect the pinned installed code and correct the source contract
with CI before any retry.

## Next decisions, explicit stop conditions

Only after the actual installed-image source probe:
1. Distinguish **source capability** from **selected runtime branch**.
   If actual load-format and `safetensors_load_strategy` are not
   independently attested, preserve `runtime_file_order=UNVERIFIED`.
2. Determine CT-specific **completion accounting** and actual
   weight-loader scale arrival for split layers 8/11; explicitly
   model or reject simultaneous buffers before implementing meta.
   MTP may be filtered from model registration yet fetched earlier.
3. Do not transplant M1 ModelOpt/H6's `device="meta"` patch to
   the H38 CT class or assume the stored **6,448,748,544 bytes**
   is a safe bound.
4. Keep `FUNCTIONAL=NOT_REACHED`,
   `HOST-STABILITY=INCONCLUSIVE`, strict RM/protection, and
   PR #259 **Draft/Open**. No model/GPU run, R33, source image
   patch, checkpoint mutation, host tuning, Ready or merge.
