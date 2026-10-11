# H38 CT expert/shard destination source audit — Attempt 01 PASS (2026-10-11)

## Scope and provenance

**Observed in the operator-supplied DGX Spark terminal transcript; source-branch syntax PASS, not runtime or checkpoint qualification.** This Markdown captures the material reported console results; it is not a byte-for-byte copy of the `/tmp` log. The `/tmp` file and SHA256 were not independently retrieved.

- Repo `kjlee-inlct/qwen3.8-flash-next-dgx-spark`; branch `feat/h38-managed-integration`.
- Local checkout fast-forwarded `1865521..fd4221b`, then exact clean checkout and wrapper target SHA: `fd4221b5bdb2b95ad83f94255ee2740cea842c9e`.
- Executed `H38_CT_EXPERT_DESTINATION_TARGET_SHA=fd4221b5bdb2b95ad83f94255ee2740cea842c9e bash scripts/benchmark/check-h38-ct-expert-destination-source.sh`.
- Operator-reported logfile: `/tmp/h38-ct-expert-destination-attempt01-20261011.txt`.
- H38 pinned image ID before and after: `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`.
- Guarded source-only execution: `--runtime runc --pull never --network none --read-only --cap-drop ALL --security-opt no-new-privileges --user 65534:65534 --memory 512m --memory-swap 512m --cpus 1 --pids-limit 64`. Inspector imports Python stdlib only and does not read checkpoint payloads or execute torch/vLLM/model/GPU.

## Operator-reported terminal markers

```text
H38_CT_EXPERT_DESTINATION_PREFLIGHT=BEGIN
checkout_sha=fd4221b5bdb2b95ad83f94255ee2740cea842c9e
image_id=sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc
scope=exact_installed_source_only_no_checkpoint_no_gpu_no_model_no_network
H38_CT_EXPERT_DESTINATION_SOURCE=PASS_SOURCE_BRANCHES_ONLY
classification=PINNED_SOURCE_BRANCHES_ONLY_NO_REAL_EXPERT_COVERAGE
image_identity_unchanged=YES
gpu_or_model_load=NO
checkpoint_payload_read=NO
managed_service_mutation=NO
host_protection_changed=NO
ct_meta_patch_implemented=NO
H38_CT_EXPERT_DESTINATION_PREFLIGHT=PASS_SOURCE_BRANCHES_ONLY
HEAD=fd4221b5bdb2b95ad83f94255ee2740cea842c9e
source_check_rc=0
evidence_log=/tmp/h38-ct-expert-destination-attempt01-20261011.txt
```

## Exact installed source SHA256 checks

All four files were already pinned by earlier source audits and **matched again in this operator run**:

| Source key | SHA256 |
|---|---|
| `ct` | `d7b47e442cee1a333753143cbd727eac857c6bbdb27d6cd8107bd6210e98e9d2` |
| `layerwise` | `9f37db893446d1f8ddc654a3bbcc3addf4b3020565920c56ef0c1ae29fd32a4a` |
| `meta` | `87a98fe340f7e39a7ba3ed136506bf5e3eef463f9215420cce5ddeb5d25a2b9c` |
| `routed` | `5206219da6b78315d6b35bee89fd0caa783681846affbf6917f430ef7f2481b5` |

## All source anchor groups PASS

The pinned image AST inspector reported **29/29 source branch predicates true**. These are branch presences/source-expression correspondences only.

**Expert mapping: 11/11**
```text
expert_mapping_builder
full_load_branch
global_scale_exception_guard
global_to_local_expert_mapping
load_weights_callback
load_weights_fused_tensor_split
load_weights_get_mapping
load_weights_name_match
load_weights_per_expert_fused_split
nonlocal_skip_with_global_sf_exception
shard_id_validation
```

**Packed/group paths: 7/7**
```text
group_packed_common_w13_w2_delegate
w13_explicit_copy
w13_group_scale_parameter_shape
w13_logical_first_half
w13_logical_second_half
w13_packed_parameter_shape
w2_explicit_copy
```

**Input/tensor scale paths: 11/11**
```text
compressed_input_scale_conflict_check
group_quantization_dispatch
input_scale_branch_priority
input_scale_global_expert_id_conditional
input_scale_scalar_helper_call
input_scale_single_value_full_row_assignment
modelopt_separate_input_w1_w3_conditional
tensor_quantization_dispatch
tensor_scale_destination_by_expert_and_index
tensor_scale_w1_w3_indices
tensor_scale_w2_destination
```

Detected source method line numbers (installed file syntax): `_map_global_expert_id_to_local_expert_id=295`, `_load_per_tensor_weight_scale=309`, `_load_model_weight_or_group_weight_scale=344`, `_load_w13=477`, `_load_w2=528`, `_load_single_value=563`, `weight_loader=614`, `load_weights=892`, `get_expert_mapping=979`, and CT `create_weights=77`.

## Eight conditional destination families (NOT actual weight copy observations)

| CT parameter | Logical shard candidates | Inspected source helper / potential destination |
|---|---|---|
| `w13_weight_packed` | w1, w3 | `_load_w13`: per-expert first/second packed half |
| `w2_weight_packed` | w2 | `_load_w2`: per-expert down projection |
| `w13_weight_scale` | w1, w3 | `_load_w13`: per-expert first/second grouped-scale half |
| `w2_weight_scale` | w2 | `_load_w2`: per-expert grouped down scale |
| `w13_weight_global_scale` | w1, w3 | `_load_per_tensor_weight_scale`: indices 0/1 if TENSOR branch |
| `w2_weight_global_scale` | w2 | `_load_per_tensor_weight_scale`: per-expert scalar if TENSOR branch |
| `w13_input_global_scale` | w1, w3 | generic expert **full-row** assignment, or ModelOpt-specific 0/1 slot |
| `w2_input_global_scale` | w2 | `_load_single_value`: per-expert scalar/row |

This is a **source-conditioned hypothesis table** from the AST. The actual backend name/method, input/global scale values, tensor shapes, checkpoint names, fusedness, EP/TP rank and loaded parameter targets were not executed or observed.

### Additional conditional source risk (independent PR evidence)

The previously recorded [PR #259 source-crosscheck](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/pull/259#issuecomment-6105299781) shows that the pinned `routed_experts.py` bytes match upstream vLLM v0.29.0 by SHA256. Its compressed input-scale check evaluates `param.data[expert_id] != 1` and other Tensor comparisons as Python `and` conditions. If a relevant 2-element input-scale row is encountered and that predicate evaluates a multi-element Tensor as a Boolean, execution **could** raise ambiguous Tensor truth-value error before loading. The necessary H38 configuration and branch execution **have not been established**. The fact this AST inspection passes the `compressed_input_scale_conflict_check` anchor confirms source **existence**, not absence of this conditional risk.

## Qualification and unverified work

**Qualified in this run:** pinned image identity/source SHA256, branch availability for global/local expert routing, fused-split handling, w1/w3 vs w2 destination helper paths, conditional input/TENSOR scale branches, image unchanged, no H38 torch/model/GPU/checkpoint runtime.

**Explicitly UNVERIFIED in inspector output:** `actual_input_scale_values_or_conflict`, `real_checkpoint_name_to_parameter_matches`, `real_copy_dispatch_numel`, `real_expert_id_mapping`, `unique_real_destination_coverage`, `layer_8_11_shard_revisit_or_buffer_lifetime`. No real CopyCounter result, per-expert element coverage, split-shard completeness, postload timing, peak memory or host stability is inferred.

**Next discriminating evidence:** bounded read-only checkpoint **metadata-only** key-to-parameter/expert/shard reconciliation, if existing scripts and safety guarantees allow it. Before any new script or execution, review a safe no-payload/header-only inventory implementation and test it against tiny synthetic manifests. Analyze CT input-scale branch preconditions separately; do not conflate a potential Tensor boolean failure with observed model failure. Do not execute H38 torch import, actual H38 model/GPU, payload scan, modify installed image, weaken host defenses, change managed service, implement CT meta patch, Ready or Merge PR #259.

`CT_INSTALLED_SOURCE_CONTRACT=PASS_SOURCE_CONTRACT_ONLY`
`CT_SCALE_ATTR_SOURCE_SITES=PASS_SOURCE_SITES_ONLY`
`CT_EXPERT_DESTINATION_SOURCE_BRANCHES=PASS_SOURCE_BRANCHES_ONLY`
`CT_REAL_DESTINATION_COVERAGE=UNVERIFIED`
`CT_COPYCOUNTER_CREDIT=UNVERIFIED`
`SHARD_8_11_REPLAY_AND_BUFFER_LIFETIME=UNVERIFIED`
`CHECKPOINT_METADATA_ORDER_GATE=FAIL`
`FUNCTIONAL=NOT_REACHED`
`HOST_STABILITY=INCONCLUSIVE`
`RM_MITIGATION=UNPROVEN`
`GPU_MODEL_RERUN=BLOCKED`
`PR_259=DRAFT_OPEN`, `MERGE=BLOCKED`
