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

## Actual DGX installed-H38 source Attempt 01 — completed PASS_SOURCE_POTENTIAL_ONLY (2026-10-12)

**Supersedes the staged/not-observed status in this original plan.** On clean exact operator HEAD `956ee0cd2db2a3ca607acd0516d6d35d62f09891` in immutable H38 image `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`, all four pinned source SHA256 values matched. The inspector returned `H38_CT_INPUT_TARGET_GAP=PASS_SOURCE_POTENTIAL_ONLY`, preflight `PASS_SOURCE_POTENTIAL_ONLY`, `source_check_rc=0`, and unchanged image identity. No GPU/model, checkpoint payload, managed service, host monitor protection or CT meta mutation was performed/reported.

All nine source predicates for Layerwise input-scale potential count-target inclusion were true. Actual `SKIP_LOAD_TENSORS` line 27 had six other names and neither CT input-global-scale name. The source-registered shapes were `(num_experts,w13_num_shards)` and `(num_experts,)`. The report's 512-expert figures (1,536 per layer / 73,728 across 48 for two W13 shards; or 1,024 per layer / 49,152 for one W13 shard) are **conditional target arithmetic only**, not observed runtime expert rows, a measured missing-copy deficit, actual postload use or bytes resident.

Canonical user-console-derived evidence: [actual pinned H38 input-scale target source Attempt 01 PASS](orcarouter-h38-ct-input-scale-numel-target-attempt01-source-pass-20261012.md). The user-reported original `/tmp/h38-ct-input-target-gap-attempt01-20261011.txt` was not separately copied/hashed. No new DGX run is required to reprove these same source facts.

**Open question / transition decision:** source-only proof should next target deterministic input-global-scale write/alias/default branches and exact CopyCounter credit semantics, bounded to pinned source/synthetic fixtures, then freeze H38 run eligibility at BLOCKED until separately approved. Installer/uninstaller/profile-switch **non-destructive** tests and qualified historical E2E evidence can be advanced independently. Historical checkpoint metadata ORDER_GATE remains FAIL; H38 functional NOT_REACHED and host stability INCONCLUSIVE. PR #259 DRAFT/OPEN, MERGE BLOCKED.
