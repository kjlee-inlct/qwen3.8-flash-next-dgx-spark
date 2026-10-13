# H38 CT checkpoint index-only key map — operator Attempt 01 KEY_SCHEMA_FAIL (2026-10-11)

## Authoritative outcome

**Completed index-only analysis / FAIL_KEY_SCHEMA / exit 3, NOT invalid infrastructure and NOT evidence that the actual checkpoint is missing packed weights.** This is the first real DGX Spark operator execution of the 48×512×9 checkpoint-key classification gate. The checker expected bare `weight` names but the actual checkpoint uses `weight_packed` names. The earlier source-only expert/shard branches PASS and metadata stream ORDER_GATE=FAIL remain independent results.

The evidence source is the user-supplied DGX Spark terminal transcript (pasted/uploaded to conversation, original console output). The operator-reported log `/tmp/h38-ct-checkpoint-key-map-attempt01-20261011.txt` and its SHA256 were **not independently retrieved**; this document is a structured transcription, not a byte-identical log.

- Repo / branch: `kjlee-inlct/qwen3.8-flash-next-dgx-spark` / `feat/h38-managed-integration`.
- Operator clean fast-forward: `fd4221b..1ed66b6`.
- **Executed checker SHA**: `1ed66b602c55534af432bba404b8eb0e6eb9db0e`.
- Pinned H38 image ID: `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`.
- Index SHA256 observed: `188d5905df195dd2dca4dbf2f9c029bb79328d0c85fd9772d73f72d881561866`.
- Guarded scope `index_only_no_header_reread_no_tensor_data_no_gpu_no_model` with a capped private 64MiB tmpfs, read-only checkpoint mounts and pinned image; no GPU/model runtime.
- Reported exit: `H38_CKPT_CT_KEY_MAP_GATE=FAIL_KEY_SCHEMA`, `H38_CKPT_CT_KEY_MAP_PREFLIGHT=KEY_SCHEMA_FAIL`, `key_map_rc=3`, `image_identity_unchanged=YES`.

## Key excerpts from operator output

```text
H38_CKPT_CT_KEY_MAP_PREFLIGHT=BEGIN
checkout_sha=1ed66b602c55534af432bba404b8eb0e6eb9db0e
image_id=sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc
scope=index_only_no_header_reread_no_tensor_data_no_gpu_no_model
H38_CKPT_CT_KEY_MAP=BEGIN
"status": "FAIL_KEY_SCHEMA"
"base_routed_key_candidates": 221184
"expected_base_routed_keys": 221184
"index_total_tensor_key_count": 223046
"index_file_shard_count": 18
"auxiliary_mtp_namespace_key_count": 31
"incomplete_expert_grid_count": 24576
"missing_canonical_slot_count": 73728
"checkpoint_key_names_with_input_scale_substring": 0
"expert_with_keys_in_multiple_shards_count": 13
"checkpoint_tensor_payload_read": "NO"
"safetensors_headers_reread": "NO"
"ct_input_scale_initialization_or_loading": "UNVERIFIED"
"unique_destination_element_coverage": "UNVERIFIED"
"h38_parameter_loader_event_count": "UNVERIFIED"
"split_layer_8_11_runtime_buffer_lifetime": "UNVERIFIED"
H38_CKPT_CT_KEY_MAP=END
H38_CKPT_CT_KEY_MAP_GATE=FAIL_KEY_SCHEMA
image_identity_unchanged=YES
H38_CKPT_CT_KEY_MAP_PREFLIGHT=KEY_SCHEMA_FAIL
HEAD=1ed66b602c55534af432bba404b8eb9db0e
key_map_rc=3
evidence_log=/tmp/h38-ct-checkpoint-key-map-attempt01-20261011.txt
```

Observed `unclassified_base_routed_key_samples` include the exact suffix `.weight_packed` for all three projections:

```text
model.language_model.layers.0.mlp.experts.0.down_proj.weight_packed
model.language_model.layers.0.mlp.experts.0.gate_proj.weight_packed
model.language_model.layers.0.mlp.experts.0.up_proj.weight_packed
```

**Root cause: inspector classification contract mismatch.** The initial parser recognized `(weight|weight_scale|weight_global_scale)` instead of the observed `(weight_packed|weight_scale|weight_global_scale)`. For the known candidate base grid, 48 layers × 512 experts × 3 projections = **73,728 packed-weight key slots** were misclassified unknown, and 24,576 experts (48×512) were thus marked incomplete by the checker. This does **NOT** prove those checkpoint tensors are missing; the opposite is evidenced by their explicitly observed `weight_packed` key samples. Distinguish a false-negative parser from checkpoint corruption or runtime loader behavior.

The original analyzer recognized four scale families:

| Candidate CT registration | Reported recognized keys |
|---|---:|
| `w13_weight_scale` | 49,152 |
| `w2_weight_scale` | 24,576 |
| `w13_weight_global_scale` | 49,152 |
| `w2_weight_global_scale` | 24,576 |

The `w13_weight_packed` and `w2_weight_packed` counts were absent solely under the old parser. The `w13_input_global_scale` and `w2_input_global_scale` CT registrations remain outside the nine-slot schema. The observed index contains **zero key names with `input_scale` or `input_global_scale` substring**. This does **not** establish either that the input scale is unnecessary, or that its runtime value is valid or initialized.

## Index-based split-shard details (do not mistake for runtime buffer observations)

The pre-fix checker reported **13** `(layer, expert)` candidates with names belonging to multiple shard files, with bounded 12 examples. Among reported examples:

- Layer 8 expert 235: `model-00004-of-00017.safetensors` and `model-00005-of-00017.safetensors`.
- Layer 11 expert 409: `model-00005-of-00017.safetensors` and `model-00006-of-00017.safetensors`.

It also reported *recognized scale keys only* in the shard distributions:

| Layer | First shard recognized keys | Second shard recognized keys |
|---|---:|---:|
| 8 | shard 4 = 1,413 | shard 5 = 1,659 |
| 11 | shard 5 = 2,457 | shard 6 = 615 |

Those sums equal **3,072 recognized scale keys per split layer**, not the full 4,608-key packed+scale grid. It would be incorrect to report these counts as complete per-layer shard key counts. **A fixed checker must recalculate the shard distribution** instead of extrapolating a filename split from these values. The prior independent full-header order gate still reports base layer 8 shard 4→5 and layer 11 shard 5→6, and remains FAIL.

## Narrow correction and strict next gate

The next checker implementation should accept exactly the observed `.weight_packed` suffix while preserving `weight_scale`, `weight_global_scale`, nine slots/expert, all fail-closed unknown/duplicate/out-of-range/missing logic. Regressions should deliberately reject an unsuffixed `.weight` and demonstrate the complete 48×512×9 **synthetic** grid (never confuse synthetic PASS with actual OrcaRouter run).

The checker implementation, tests and plan may be updated in later commits, but **this Attempt 01 remains immutable `FAIL_KEY_SCHEMA`**. A subsequent separate, pinned DGX index-only Attempt 02 is needed to establish any real `PASS_BASE_KEY_SCHEMA_ONLY`. Even a real key-grid PASS can only establish checkpoint **names/file ownership for six CT registration families**, not execution of their callbacks, the two input-scale data sources, `aten.copy_` events, unique destination element loading, layer 8/11 buffering, functionality or host safety.

**Gates retained:** `CT_EXPERT_DESTINATION_SOURCE_BRANCHES=PASS_SOURCE_BRANCHES_ONLY`, `CT_CHECKPOINT_KEY_MAP_ATTEMPT01=FAIL_KEY_SCHEMA`, `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `CT_INPUT_SCALE_DATA_SOURCE=UNVERIFIED`, `CT_WEIGHT_COMPLETENESS=UNVERIFIED`, `CT_COPYCOUNTER_CREDIT=UNVERIFIED`, `HOST_STABILITY=INCONCLUSIVE`, `RM_MITIGATION=UNPROVEN`, `GPU_MODEL_RERUN=BLOCKED`, `HOST_PROTECTION=UNCHANGED`, `PR_259=DRAFT_OPEN / MERGE=BLOCKED`.
