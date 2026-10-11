# H38 CT input-global-scale lifecycle / Layerwise numel threshold — operator Attempt 01 PASS_SOURCE_ONLY (2026-10-11)

## Result and provenance

**Actual operator-supplied pinned-image source-only inspection PASS.** This establishes existence of specific AST construction, postload consumer and counted-numel condition sites in the installed source. It does **NOT** establish effective tensor values, successful postload execution, default initialization, callback delivery, loaded bytes, all experts written, unique destination coverage, memory peak or functional H38 startup.

- Repo / branch: `kjlee-inlct/qwen3.8-flash-next-dgx-spark` / `feat/h38-managed-integration`.
- Operator fast-forward: `2426b9a..5456809`, exact clean executed Git HEAD `5456809ab701dd38ef947afdc15bc88a32b22a13`.
- Executed `H38_CT_INPUT_SCALE_LIFECYCLE_TARGET_SHA=5456809ab701dd38ef947afdc15bc88a32b22a13 bash scripts/benchmark/check-h38-ct-input-scale-lifecycle.sh`.
- Fixed H38 image ID `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`, checked unmodified before/after.
- Operator-reported logfile `/tmp/h38-ct-input-scale-lifecycle-attempt01-20261011.txt`. The complete console transcript was provided in chat; the original `/tmp` logfile and its SHA256 were **not independently retrieved or verified**. This Markdown is a structured, evidence-grounded transcription, **not a byte-for-byte copy** of the original logfile.
- Scope `exact_installed_source_only_no_checkpoint_no_gpu_no_model_no_network` on immutable, no-network, read-only, unprivileged, bounded `runc`; no tensor loads, torch/vLLM import, GPU/model startup, service or host protections mutation.

### Exact console verdict

```text
H38_CT_INPUT_SCALE_LIFECYCLE_PREFLIGHT=BEGIN
checkout_sha=5456809ab701dd38ef947afdc15bc88a32b22a13
image_id=sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc
scope=exact_installed_source_only_no_checkpoint_no_gpu_no_model_no_network
H38_CT_INPUT_SCALE_LIFECYCLE=PASS_SOURCE_ONLY
"classification": "PINNED_CT_INPUT_SCALE_LIFECYCLE_AND_COUNTER_SOURCE_ONLY"
"effective_input_scale_values": "UNVERIFIED"
"source_or_runtime_default_proven": "NO"
"actual_checkpoint_loader_callback": "UNVERIFIED"
"actual_copycounter_credit": "UNVERIFIED"
"unique_destination_element_completion": "UNVERIFIED"
"shard_8_11_buffer_lifetime": "UNVERIFIED"
"gpu_model_or_checkpoint_read": "NOT_EXECUTED"
image_identity_unchanged=YES
gpu_or_model_load=NO
checkpoint_payload_read=NO
managed_service_mutation=NO
host_protection_changed=NO
ct_meta_patch_implemented=NO
H38_CT_INPUT_SCALE_LIFECYCLE_PREFLIGHT=PASS_SOURCE_ONLY
HEAD=5456809ab701dd38ef947afdc15bc88a32b22a13
source_check_rc=0
evidence_log=/tmp/h38-ct-input-scale-lifecycle-attempt01-20261011.txt
```

## Exact source identity reverified in this run

| Installed source key | Reported verified SHA256 |
|---|---|
| CT NVFP4 | `d7b47e442cee1a333753143cbd727eac857c6bbdb27d6cd8107bd6210e98e9d2` |
| reload/layerwise | `9f37db893446d1f8ddc654a3bbcc3addf4b3020565920c56ef0c1ae29fd32a4a` |
| reload/meta | `87a98fe340f7e39a7ba3ed136506bf5e3eef463f9215420cce5ddeb5d25a2b9c` |
| reload/utils | `9421654170a04244d9ad702ba8c81dcf6c09a3c8bfe7e04ccbe099baf57b63a1` |

All are previously pinned installed-H38 source SHA256 values and matched on this inspection. Do not transfer a result from a SHA-different public upstream CT file into this image.

## Input-global-scale lifecycle source observations

| Registered input-scale | `torch.nn.Parameter(torch.empty(...))` constructor | Registration | `set_weight_attrs` | CT `process_weights_after_loading` reciprocal consumer |
|---|---:|---:|---:|---|
| `w13_input_global_scale` | line **179** | **183** | **187** | line **238**, `1.0 / layer.w13_input_global_scale` |
| `w2_input_global_scale` | line **189** | **192** | **196** | line **242**, `1.0 / layer.w2_input_global_scale` |

Both source constructor checks reported `constructor_explicit_device=false`, `constructor_has_explicit_fill_value=false`, `effective_initial_value=UNVERIFIED`, `checkpoint_load_event_for_this_parameter=UNVERIFIED`, and `actual_postload_invocation=UNVERIFIED`.

**Important source-level risk interpretation:** the exact installed H38 source *contains* postloading reciprocal-use expressions on input-scale Parameters allocated by `torch.empty` without an explicit constructor fill. Separately, [real checkpoint index-only Attempt02](orcarouter-h38-ct-checkpoint-key-map-attempt02-index-pass-20261011.md) verified **zero index key names containing the substring `input_scale`** across 223,046 names, and proved 221,184 base routed name slots corresponding conditionally to only the other six CT registration families. This conjunction establishes an **unresolved provenance/default-initialization risk**, not proven runtime uninitialized reads, incorrect scale values, division by zero, model failure or memory corruption. An assignment under a different name, non-checkpoint default, aliasing or a skipped branch was not excluded.

`source_or_runtime_default_proven=NO` means **no default was proven by this inspector**, not proof that all possible default mechanisms are absent. `constructor_has_explicit_fill_value=false` concerns the constructor call only, not later writes.

## Layerwise counted-numel completion syntax (5/5 source anchors true)

Installed `make_online_process_loader` begins at line **149**. Five exact source anchor checks all passed:

- `buffers_weight_arguments`: `info.loaded_weights.append(...)` source present.
- `copy_count_from_original_loader`: `get_numel_loaded(original_loader, bound_args)` source present.
- `count_accumulation`: `info.load_numel += num_loaded` source present.
- `completion_on_accumulated_threshold`: `info.load_numel >= info.load_numel_total` condition present.
- `online_processing_call`: `_layerwise_process(layer, info)` source present.

These confirm **the source uses an aggregate count threshold**, not a proven unique-destination-element bitmap or actual comprehensive expert completion check. The separate [external CPU tiny indexed-write witness](h38-ct-copycounter-indexed-write-external-cpu-toy-20261011.md) demonstrated a *possible* aggregate-copy-credit vs unique-slot mismatch in another PyTorch CPU environment; it did not observe actual installed H38 `TorchDispatchMode` events, repeated writes, copy-counter scale credits or early processing.

## Historical gates and next safe question

Independent existing checks, none reclassified by this pass:

- Actual CT eight-parameter registration/Layerwise/RoutedExperts AST `PASS_SOURCE_CONTRACT_ONLY`.
- Actual postconstruction input-scale attribute sites `PASS_SOURCE_SITES_ONLY`.
- Actual expert/shard source destinations (29/29 predicates) `PASS_SOURCE_BRANCHES_ONLY`.
- Actual index-only checkpoint key-map Attempt01 historical `FAIL_KEY_SCHEMA` due to old checker suffix mismatch; Attempt02 `PASS_BASE_KEY_SCHEMA_ONLY`.
- Strict checkpoint metadata ordering `CHECKPOINT_METADATA_ORDER_GATE=FAIL` (layer 8 spans numbered shard4→5; layer11 spans 5→6).

**Next gate:** inspect exact installed CT source and surrounding H38 model/quantization/loader functions to establish whether the input scales are ever assigned *a deterministic source value* before the reciprocal postload consumer; check default/alias/load pathways and any optional quantization branch. Source-only assertions must be scoped to the source files actually examined and should fail closed if a claimed proof requires other files. Separately relate the 13 checkpoint index cross-shard expert ownership groups to source buffering rules. Use tiny synthetic test fixtures before any additional DGX action. No H38 torch import, tensor payload scan, GPU/model run, image rebuild, host protection modification, CT meta patch, PR Ready or Merge.

```text
CT_INPUT_SCALE_LIFECYCLE_SOURCE_ATTEMPT01=PASS_SOURCE_ONLY
CT_INPUT_SCALE_EFFECTIVE_VALUES=UNVERIFIED
CT_INPUT_SCALE_DEFAULT_GUARANTEE=UNVERIFIED
CT_INPUT_SCALE_CHECKPOINT_LOADER_EVENT=UNVERIFIED
CT_COPYCOUNTER_CREDIT=UNVERIFIED
CT_UNIQUE_DESTINATION_COMPLETENESS=UNVERIFIED
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
