# H38 CT input-scale Layerwise numel-target source inspection — actual Attempt 01 (2026-10-12)

## Verdict: PASS_SOURCE_POTENTIAL_ONLY (exact installed source, not runtime)

The operator supplied complete DGX Spark console output for a guarded **source-only** audit. Exact original DGX checkout: `956ee0cd2db2a3ca607acd0516d6d35d62f09891` (`feat/h38-managed-integration`). The operator fast-forwarded from `5456809` to `956ee0c`, verified clean target checkout and executed `scripts/benchmark/check-h38-ct-load-target-input-scale.sh` with `H38_CT_INPUT_TARGET_GAP_TARGET_SHA` bound to that exact commit.

```text
H38_CT_INPUT_TARGET_GAP_PREFLIGHT=BEGIN
checkout_sha=956ee0cd2db2a3ca607acd0516d6d35d62f09891
image_id=sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc
scope=exact_installed_source_only_no_checkpoint_no_gpu_no_model_no_network
H38_CT_INPUT_TARGET_GAP=PASS_SOURCE_POTENTIAL_ONLY
"classification": "PINNED_SOURCE_POTENTIAL_INPUT_SCALE_NUMEL_TARGET_ONLY"
"input_scale_names_in_skip_load_tensors": []
"actual_layerwise_threshold_deficit": "UNVERIFIED"
"actual_h38_runtime_num_experts": "UNVERIFIED"
"real_input_scale_loader_events": "UNVERIFIED"
"alternative_initialization_or_default": "UNVERIFIED"
"parameter_unique_element_coverage": "UNVERIFIED"
"actual_shard_8_11_release": "UNVERIFIED"
"model_gpu_checkpoint_runtime": "NOT_EXECUTED"
image_identity_unchanged=YES
gpu_or_model_load=NO
checkpoint_payload_read=NO
managed_service_mutation=NO
host_protection_changed=NO
ct_meta_patch_implemented=NO
H38_CT_INPUT_TARGET_GAP_PREFLIGHT=PASS_SOURCE_POTENTIAL_ONLY
HEAD=956ee0cd2db2a3ca607acd0516d6d35d62f09891
source_check_rc=0
evidence_log=/tmp/h38-ct-input-target-gap-attempt01-20261011.txt
```

This Markdown faithfully summarizes the user-supplied console log; **the original `/tmp` log bytes and log SHA256 have not been independently retrieved/verified**. A successful wrapper guard reported image unchanged and no GPU, model, checkpoint payload, or service/host protection/CT meta modifications.

## Exact pinned source SHA256 matched on the DGX image

| Source | SHA256 |
|---|---|
| `ct` | `d7b47e442cee1a333753143cbd727eac857c6bbdb27d6cd8107bd6210e98e9d2` |
| `layerwise` | `9f37db893446d1f8ddc654a3bbcc3addf4b3020565920c56ef0c1ae29fd32a4a` |
| `meta` | `87a98fe340f7e39a7ba3ed136506bf5e3eef463f9215420cce5ddeb5d25a2b9c` |
| `utils` | `9421654170a04244d9ad702ba8c81dcf6c09a3c8bfe7e04ccbe099baf57b63a1` |

## Positive source predicates, precisely scoped

All **9/9** `numel_target_source_checks` were `true`:
1. `get_layer_tensors_returns_param_buffer_union`
2. `layerwise_accumulates_credit`
3. `layerwise_initializes_total_from_layer_size`
4. `layerwise_refreshes_total`
5. `layerwise_triggers_at_threshold`
6. `no_none_parameters`
7. `registered_parameters_enumerated`
8. `size_enumerates_registered_tensors`
9. `size_excludes_skip_names_only`

`SKIP_LOAD_TENSORS` was the installed-source literal at line 27:
```text
_expert_map
e_score_correction_bias
expert_global_to_physical
expert_local_to_global
expert_mask
expert_physical_to_global
```
Neither `w13_input_global_scale` nor `w2_input_global_scale` belongs to that exclusion set in the inspected source. Their **registration shapes**, not runtime sampled tensors, were:

| Parameter | Source `torch.empty` dimensions | Registration line |
|---|---|---:|
| `w13_input_global_scale` | `(num_experts, w13_num_shards)` | 183 |
| `w2_input_global_scale` | `(num_experts,)` | 192 |

Their participation in `get_layer_size` follows **only if these CT parameters have been registered and remain in the inspected layer at the time of enumeration**. The installed Layerwise target obtains `get_layer_size(layer)`, refreshes it, and uses aggregated loaded-numel threshold. The AST checks do not establish effective runtime call order, expert placement, loaded scale values, unique element coverage, or whether that threshold is reached.

Conditional arithmetic, **not a measured deficit or memory peak**:

```text
potential scale contribution per layer = num_experts * (w13_num_shards + 1)

if 512 registered expert rows and is_act_and_mul=True:
    1,536 potential target elements per layer; 73,728 across 48

if 512 registered expert rows and is_act_and_mul=False:
    1,024 potential target elements per layer; 49,152 across 48
```

The 512 expert identifiers counted in the independent checkpoint index do **not** prove 512 physical/local runtime expert rows per instantiated layer. A potential counted target also does **not** prove any corresponding loader event is absent or that the runtime over/under-counts; alternate initialization/load names, overlapping copy credit, actual parameter materialization and Layerwise ownership remain unverified.

## Relationship to earlier completed gates and next action

- Earlier exact installed CT input-scale reciprocal-use source Attempt 01: **PASS_SOURCE_ONLY**, showing `torch.empty` constructors and `1.0 / layer.{w13,w2}_input_global_scale` postload code. Does not prove effective initialized values.
- Earlier real checkpoint index-only Attempt 02: **PASS_BASE_KEY_SCHEMA_ONLY**; complete 221,184 base key-name grid, zero `input_scale` substring keys in 223,046 index names. This is a name-based observation, not evidence of absent runtime writes.
- Original index checker Attempt 01: immutable historical **FAIL_KEY_SCHEMA** due to incorrect `*.weight` expectation. Previous strict metadata **CHECKPOINT_METADATA_ORDER_GATE=FAIL** remains FAIL.
- **This Attempt 01 load-target source result:** `H38_CT_INPUT_TARGET_GAP=PASS_SOURCE_POTENTIAL_ONLY`, actual operator `source_check_rc=0`. This closes only the *potential target-inclusion source-site* question.

**Remaining:** `CT_INPUT_SCALE_EFFECTIVE_VALUES=UNVERIFIED`; `CT_ALTERNATIVE_INITIALIZATION=UNVERIFIED`; `CT_ACTUAL_LAYERWISE_TARGET_DEFICIT=UNVERIFIED`; `CT_COPYCOUNTER_CREDIT=UNVERIFIED`; `CT_UNIQUE_DESTINATION_COVERAGE=UNVERIFIED`; `SHARD_8_11_BUFFER_LIFETIME=UNVERIFIED`; `FUNCTIONAL=NOT_REACHED`; `HOST_STABILITY=INCONCLUSIVE`; `RM_MITIGATION=UNPROVEN`.

**Bounded next step:** source-only trace of writes/aliases/defaults for the two input-global-scale Parameters and review of aggregated counter semantics (tiny synthetic tests where helpful), followed by a go/no-go decision for further H38 runtime attempts. Meanwhile installer/uninstaller/profile-switch **non-destructive** dry-run, owner-inventory and safe rollback validation can progress without H38 GPU reruns. No checkpoint payload, H38 torch/model/GPU, image rebuild, host protection modification, managed service mutation, CT meta patch, PR Ready or Merge.
