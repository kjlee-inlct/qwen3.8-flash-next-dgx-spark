# H38 CT input-global-scale contribution to Layerwise load-numel target — staged source-only gate (2026-10-11)

## Why this is the next discriminating question

Actual DGX source-only Attempt 01 for CT input-scale lifecycle passed on checked-out SHA `5456809ab701dd38ef947afdc15bc88a32b22a13`, proving the installed CT code registers two `torch.nn.Parameter(torch.empty(...))` input-global-scale parameters and contains reciprocal use in `process_weights_after_loading`. [Actual source-lifecycle PASS evidence](orcarouter-h38-ct-input-scale-lifecycle-attempt01-source-pass-20261011.md). The independent real checkpoint index-only Attempt 02 passed `PASS_BASE_KEY_SCHEMA_ONLY` and showed **zero index tensor key names containing `input_scale`** across 223,046 keys. This says nothing about effective runtime values or alternate initialization paths.

The installed Layerwise code was previously source-verified to accumulate `info.load_numel` and call `_layerwise_process` once a counter meets `info.load_numel_total`; however, it has not been established whether **the two CT input-global-scale parameters contribute to that target at all**. This stage checks *exact registered shape/source inclusion*, not runtime failure or source of data.

## New bounded, fail-closed source analysis

- `scripts/benchmark/inspect-h38-ct-load-target-input-scale.py` reads four previously pinned source files using Python stdlib AST **inside the immutable H38 image**: CT (d7b47e44...), reload/meta (87a98fe3...), reload/utils (94216541...), reload/layerwise (9f37db89...). Mismatched digest, missing or nonliteral SKIP_LOAD_TENSORS, missing CT registrations, unexpected shape, changed w13 shard conditional, changed `get_layer_tensors` union, changed `get_layer_size` exclusion and changed Layerwise target/threshold logic are **INVALID** with diagnostic reason.
- `scripts/benchmark/check-h38-ct-load-target-input-scale.sh` reuses prior exact clean Git SHA, pinned image-ID and H11/H12/H38 labels, `--runtime runc --network none --pull never --read-only`, UID 65534, 512 MiB memory/swap, 1 CPU and 64 PID safety conditions. Source inspector only; no checkpoint headers/index/payload, torch import, H38 model/GPU, managed service/host protection or image mutation.
- `tests/test_h38_ct_load_target_input_scale.py` asserts source contract with synthetic fixture and fail-closed negative tests for input-scale SKIP list, changed constructor/shape/shard condition, changed parameter enumeration, changed count refresh/threshold, source SHA drift and wrapper safeguards. Synthetic tests are **not** installed H38 source observation.

### Conditional mathematical implication — NOT an observed missing load amount

The CT source shape is `(num_experts, w13_num_shards)` for `w13_input_global_scale`, `(num_experts,)` for `w2_input_global_scale`, and `w13_num_shards = 2 if self.moe.is_act_and_mul else 1`. If both registrations **are present when** the Layerwise `get_layer_size` is called, and if the scale names are not in `SKIP_LOAD_TENSORS`, their mathematical *contribution to the counted-numel target* is:

```text
potential_input_scale_target_numel_per_layer = num_experts * (w13_num_shards + 1)

if (num_experts == 512 && is_act_and_mul):
    per_layer = 512 * (2+1) = 1,536
    across_48_independent_routed_layers = 48 * 1,536 = 73,728

if (num_experts == 512 && !is_act_and_mul):
    per_layer = 512 * (1+1) = 1,024
    across_48_independent_routed_layers = 48 * 1,024 = 49,152
```

**This is illustrative conditional arithmetic ONLY.** The 512 experts in the checkpoint *index* does not independently prove the number of **runtime registered local/physical expert rows** on H38 in this Layerwise stage (EP/TP/padding/placement can differ). The number of active routed layers, actual `is_act_and_mul` value, registered parameter lifetime, loaded callbacks, duplicate copy credits, late parameter creation and actual skipped tensor categories must be resolved before inferring any effective `load_numel_total` deficit. A nonzero contribution does **NOT** mean those elements are actually missing or uninitialized: alternate assignments/aliases or other loader names might satisfy them, and `CopyCounter` aggregates can over-credit overlapping destinations.

## Possible installed-image source-only verdict

If source pins and all AST anchors match, an operator read-only run may report `H38_CT_INPUT_TARGET_GAP=PASS_SOURCE_POTENTIAL_ONLY` and `H38_CT_INPUT_TARGET_GAP_PREFLIGHT=PASS_SOURCE_POTENTIAL_ONLY`. The marker does **not** prove:
- real H38 CT input-global-scale loaded/unloaded values or a zero/NaN/divide-by-zero condition;
- a missing real Layerwise target numel or premature/late `_layerwise_process`;
- actual 512 local expert tensors loaded per layer or any uniquely covered element;
- H38 checkpoint payload presence, actual `TorchDispatchMode` events, GPU memory/high-watermark or host stability.

If INVALID, retain first failed AST guard and never weaken digest/image pins just to produce PASS. Only after repo CI and an exact SHA-qualified real operator DGX audit may a new actual source verdict be recorded; **this plan is not that result**.

### Independent gates retained

```text
CT_CHECKPOINT_KEY_MAP_ATTEMPT02=PASS_BASE_KEY_SCHEMA_ONLY
CT_INPUT_SCALE_LIFECYCLE_SOURCE_ATTEMPT01=PASS_SOURCE_ONLY
CT_INPUT_SCALE_LOAD_TARGET_SOURCE=STAGED_NOT_OBSERVED
CT_INPUT_SCALE_EFFECTIVE_VALUES=UNVERIFIED
CT_INPUT_SCALE_ALTERNATE_INITIALIZER=UNVERIFIED
CT_COPYCOUNTER_CREDIT=UNVERIFIED
CT_UNIQUE_DESTINATION_COVERAGE=UNVERIFIED
SHARD_8_11_BUFFER_LIFETIME=UNVERIFIED
CHECKPOINT_METADATA_ORDER_GATE=FAIL
FUNCTIONAL=NOT_REACHED
HOST_STABILITY=INCONCLUSIVE
RM_MITIGATION=UNPROVEN
GPU_MODEL_RERUN=BLOCKED
HOST_PROTECTION=UNCHANGED
CT_META_PATCH=BLOCKED
PR_259=DRAFT_OPEN
MERGE=BLOCKED
```

No H38 runtime, checkpoint read or host mutation is authorized by this source-only gate.
