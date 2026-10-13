# H38 CT Input-global-scale Lifecycle and Layerwise threshold — next exact-source gate (2026-10-11)

## Why this bounded gate is next

Three prior independent **actual pinned-image source-only** checks qualified eight CT registration constructors, input-scale postconstruction `set_weight_attrs` and 29 expert/shard destination branches. An actual DGX checkpoint index-only Attempt 02 at clean `2426b9a9ac4234865176fc12c5e34a79d0bbfd1d` proved the 48 × 512 × 9 = 221,184 **base expert key-name slots**, exactly once per recognized name, with **zero** `input_scale` substrings across all 223,046 indexed checkpoint keys. These are names/file owners only. [Canonical index PASS](orcarouter-h38-ct-checkpoint-key-map-attempt02-index-pass-20261011.md). Historical key-map Attempt01 remains `FAIL_KEY_SCHEMA` from the checker expecting unsuffixed `weight`, not checkpoint corruption.

The next question is **whether and where the two declared input-global-scale Parameters are initialized and consumed** and **whether Layerwise completion can be asserted from counted `numel` without tracking unique destination elements**. Neither question can be settled merely by the nine-slot checkpoint index name-grid.

### Separate upstream context — not installed CT proof

Public vLLM tag `v0.29.0` CT `CompressedTensorsW4A4Nvfp4MoEMethod` uses `torch.empty` allocations for both input-global-scale Parameters and postprocessing expressions `1.0 / layer.w13_input_global_scale` and `1.0 / layer.w2_input_global_scale`. **But public CT SHA differs** from the installed pinned H38 CT SHA256 `d7b47e442cee1a333753143cbd727eac857c6bbdb27d6cd8107bd6210e98e9d2`; therefore none of those public postload consumer expressions is yet accepted as the actual installed-H38 source gate result. The previous actual pinned CT registration audit already established both declarations use plain `torch.nn.Parameter(torch.empty(...))`, with no explicit constructor fill value. This does not demonstrate a run-time uninitialized read, because loading/materialization/other initialization is not yet qualified.

Public tag `v0.29.0` `reload/layerwise.py` has `make_online_process_loader` buffering `info.loaded_weights`, calling `get_numel_loaded`, accumulating `info.load_numel`, then testing `info.load_numel >= info.load_numel_total`. The installed H38 layerwise file is pinned separately and this new gate will inspect the actual installed source. Count threshold is **not** an address-uniqueness proof: two calls may copy overlapping destination elements, even if aggregate copied count rises. This is a logical/synthetic concern; no installed H38 loader event count or premature finalization has been observed.

## New repo-only implementation; actual H38 execution PENDING

- `scripts/benchmark/inspect-h38-ct-input-scale-lifecycle.py`: Python standard-library AST-only, requiring the **previously qualified exact source SHA256** for installed CT, reload/layerwise, reload/meta, and reload/utils. Asserts two plain `torch.nn.Parameter(torch.empty(...))` initializers, separate register+postconstruction `set_weight_attrs` ordering, existence of a later reference to each registered input-scale name in `process_weights_after_loading`, and the Layerwise online loader's original-loader counting / accumulated threshold / buffered-arguments syntax. Reports bounded source line numbers and matching `1.0 / ...` divisions if present. A missing consumer produces INVALID, not a claim of source PASS.
- `scripts/benchmark/check-h38-ct-input-scale-lifecycle.sh`: exact clean Git SHA requirement, fixed H38 image ID and H11/H12/H38 label guards, `--runtime runc --pull never --network none --read-only --cap-drop ALL --security-opt no-new-privileges --user 65534:65534 --memory 512m --memory-swap 512m --cpus 1 --pids-limit 64`; source inspector mounted read-only; no GPU, model, checkpoint access, service/image/host protection mutation.
- `tests/test_h38_ct_input_scale_lifecycle.py`: synthetic two-scale consumer/threshold success plus fail-closed cases for missing postload reference, altered initializers, missing attributes, missing registered scales, removed original-loader counting or buffering, changed threshold, SHA drift and shell guard.
- This is an independent gate rather than relabeling earlier Attempt03 registration, input-scale setter Attempt01, expert destination Attempt01 or checkpoint key-map Attempt02. **Repo synthetic CI ≠ actual pinned-H38 source run.**

### Semantics of possible results

- `H38_CT_INPUT_SCALE_LIFECYCLE_PREFLIGHT=PASS_SOURCE_ONLY` and `H38_CT_INPUT_SCALE_LIFECYCLE=PASS_SOURCE_ONLY` would confirm that the installed source has these constructor/postprocessing and numel-threshold **syntactic sites**. It does not certify actual inverse computation, allocation contents, whether the input-scale checkpoint data exists under another key, defaults or runtime values, actual `get_numel_loaded` results, expert uniqueness, or a memory bound.
- `H38_CT_INPUT_SCALE_LIFECYCLE=INVALID` requires retention of the first mismatching source contract and source hashes. If the exact H38 postload function differs from upstream, inspect the difference; never weaken image SHA pins or infer actual model failure.
- The source-only inspector itself does **NOT read the checkpoint index**. The zero `input_scale` key count is separate real DGX Attempt02 evidence that may be cited alongside, not used as a hidden assertion about the installed-source scan.

## Blockers unchanged

```text
CT_CHECKPOINT_KEY_MAP_ATTEMPT02=PASS_BASE_KEY_SCHEMA_ONLY
CT_INPUT_GLOBAL_SCALE_EFFECTIVE_VALUES=UNVERIFIED
CT_INPUT_SCALE_ACTUAL_LOADER_EVENT=UNVERIFIED
H38_COPYCOUNTER_CREDIT=UNVERIFIED
UNIQUE_REAL_DESTINATION_COVERAGE=UNVERIFIED
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

No checkpoint payload, torch/vLLM import, GPU/model rerun, H38 image rebuild, host defense/service change, PR Ready or Merge.

## Actual installed-H38 DGX source inspection — Attempt 01 PASS (2026-10-11)

**This observed result supersedes the staged/PENDING status in the original plan above, while retaining SOURCE_ONLY qualification.** On the exact clean branch checkout 5456809ab701dd38ef947afdc15bc88a32b22a13, the operator ran the guarded read-only AST inspector on fixed H38 image sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc. Four previously pinned CT/layerwise/meta/reload-utils SHA256 checks matched. Output: H38_CT_INPUT_SCALE_LIFECYCLE=PASS_SOURCE_ONLY; H38_CT_INPUT_SCALE_LIFECYCLE_PREFLIGHT=PASS_SOURCE_ONLY; source_check_rc=0; image_identity_unchanged=YES; model/GPU/checkpoint payload read NO; image/service/host-protection mutations NO.

Source observations for w13_input_global_scale: ctor torch.nn.Parameter(torch.empty(...)) line 179, register line 183, set_weight_attrs line 187, CT postload reciprocal 1.0 / layer.w13_input_global_scale line 238. For w2_input_global_scale: ctor line 189, register line 192, setter line 196, reciprocal line 242. Neither constructor explicitly supplies device or fill. Real postload invocation, loaded values, default mechanism and write origin are still UNVERIFIED; source_or_runtime_default_proven=NO is an absence of proof, not proof of runtime invalid initialization.

Installed Layerwise make_online_process_loader at line 149 passed all five source checks: buffered arguments, original-loader get_numel_loaded, load_numel accumulation, >= threshold, and processing call. This verifies aggregate-count source syntax, NOT actual TorchDispatch copy counts or uniqueness. The separate real index-only checkpoint Attempt02 already reported zero index key names with input_scale substring; that evidence is not conflated with this source-only AST scan.

Canonical actual-console evidence: [operator Attempt 01 input-scale lifecycle source PASS](orcarouter-h38-ct-input-scale-lifecycle-attempt01-source-pass-20261011.md). The reported original /tmp/h38-ct-input-scale-lifecycle-attempt01-20261011.txt was not independently retrieved or hashed. Never describe the inspection as an actual loaded-value check.

**Next bounded question:** identify whether the exact installed H38 source supplies deterministic input-global-scale defaults or loads those Parameters through an alternative checkpoint name or loader path *before* inverse consumption; separately characterize whether total copied numel can exceed unique destination completion under this loader. Start from source-only and synthetic fixtures with immutable source pins. Do not repeat this completed source inspection to claim runtime correctness; no torch/model/GPU, checkpoint tensor payload, host protection/service change, image rebuild, CT meta patch or PR Ready/Merge.

CHECKPOINT_METADATA_ORDER_GATE=FAIL; CT_INPUT_SCALE_EFFECTIVE_VALUES=UNVERIFIED; CT_COPYCOUNTER_CREDIT=UNVERIFIED; CT_WEIGHT_COMPLETENESS=UNVERIFIED; HOST_STABILITY=INCONCLUSIVE; GPU_MODEL_RERUN=BLOCKED; PR_259=DRAFT_OPEN / MERGE=BLOCKED remain.
