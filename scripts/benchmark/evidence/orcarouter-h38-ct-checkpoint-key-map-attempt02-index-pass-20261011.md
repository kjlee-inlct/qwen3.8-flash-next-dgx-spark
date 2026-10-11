# H38 CT OrcaRouter checkpoint index key-map — operator Attempt 02 PASS_BASE_KEY_SCHEMA_ONLY (2026-10-11)

## Authoritative result and provenance

**ACTUAL DGX Spark operator-supplied index-only execution: PASS_BASE_KEY_SCHEMA_ONLY, exit 0. This is index-key naming and shard ownership evidence only, NOT an H38 runtime or checkpoint tensor value/weight completeness qualification.**

- Origin: user's full pasted DGX terminal output in this conversation; this document transcribes supported fields, not a byte-identical file materialization. Operator's logfile path `/tmp/h38-ct-checkpoint-key-map-attempt02-20261011.txt` was reported but its SHA256 and independent file existence have not been established here.
- Repo `kjlee-inlct/qwen3.8-flash-next-dgx-spark`, branch `feat/h38-managed-integration`. Clean local fast-forward `1ed66b6..2426b9a`; exact **executed checker HEAD** `2426b9a9ac4234865176fc12c5e34a79d0bbfd1d`.
- Fixed H38 image ID (checked before and after): `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`.
- Script: `scripts/benchmark/check-h38-ct-checkpoint-key-map.sh` with `H38_CKPT_CT_KEY_MAP_TARGET_SHA` and `H38_CKPT_CT_KEY_MAP_MODEL_DIR` to the local OrcaRouter checkpoint.
- Actual checkpoint index SHA256 `188d5905df195dd2dca4dbf2f9c029bb79328d0c85fd9772d73f72d881561866`; this is **identical to observed Attempt 01 index SHA256**, indicating the same index contents were classified across the correction.
- Guarded scope: `index_only_no_header_reread_no_tensor_data_no_gpu_no_model`, capped `/tmp` private 64MiB tmpfs, read-only checkpoint mount, immutable image and unprivileged no-network/runc resource caps. Exit `key_map_rc=0`; no tensor payload/header re-read, no torch/model/GPU, no service/host monitor protection/CT meta change was reported.

## Exact reported acceptance markers

```text
H38_CKPT_CT_KEY_MAP_PREFLIGHT=BEGIN
checkout_sha=2426b9a9ac4234865176fc12c5e34a79d0bbfd1d
image_id=sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc
scope=index_only_no_header_reread_no_tensor_data_no_gpu_no_model
H38_CKPT_CT_KEY_MAP=BEGIN
"status": "PASS_BASE_KEY_SCHEMA_ONLY"
"classification": "INDEX_NAMES_ONLY_NOT_RUNTIME_OR_CT_8_PARAMETER_COVERAGE"
"base_routed_key_candidates": 221184
"expected_base_routed_keys": 221184
"missing_canonical_slot_count": 0
"incomplete_expert_grid_count": 0
"duplicate_semantic_slot_samples": []
"unclassified_base_routed_key_samples": []
"out_of_range_base_routed_key_samples": []
"unique_destination_element_coverage": "UNVERIFIED"
"ct_input_scale_initialization_or_loading": "UNVERIFIED"
"h38_parameter_loader_event_count": "UNVERIFIED"
"split_layer_8_11_runtime_buffer_lifetime": "UNVERIFIED"
H38_CKPT_CT_KEY_MAP=END
H38_CKPT_CT_KEY_MAP_GATE=PASS_BASE_KEY_SCHEMA_ONLY
image_identity_unchanged=YES
tensor_payload_read=NO
headers_reread=NO
model_or_gpu_load=NO
managed_service_mutation=NO
monitor_protection_changed=NO
meta_w13_patch_implemented=NO
H38_CKPT_CT_KEY_MAP_PREFLIGHT=PASS_BASE_KEY_SCHEMA_ONLY
HEAD=2426b9a9ac4234865176fc12c5e34a79d0bbfd1d
key_map_rc=0
evidence_log=/tmp/h38-ct-checkpoint-key-map-attempt02-20261011.txt
```

## Qualified index-only name cardinalities

The checker recognizes a complete **48 base routed layers × 512 experts × 9 key names = 221,184 indexed key slots**. The nine candidates are `gate_proj/up_proj/down_proj × weight_packed/weight_scale/weight_global_scale`. **No missing canonical slot**, no incomplete expert name-grid, and no unclassified, duplicate-semantic, or out-of-range base expert key were reported.

| Candidate CT parameter family | Indexed checkpoint key count |
|---|---:|
| `w13_weight_packed` | 49,152 |
| `w2_weight_packed` | 24,576 |
| `w13_weight_scale` | 49,152 |
| `w2_weight_scale` | 24,576 |
| `w13_weight_global_scale` | 49,152 |
| `w2_weight_global_scale` | 24,576 |
| **Total** | **221,184** |

These are **index name→candidate CT parameter mappings**, not a trace of actual `RoutedExperts.load_weights`, `weight_loader` callbacks, physical/local expert placement, loaded bytes, or verified per-element destination coverage. All six identified families are names: they do **not** prove six registered parameter objects were completely loaded.

## Split shards and complete nine-slot key distribution

The total checkpoint contains **223,046 indexed tensor names** and **18 indexed shard files** (17 numbered base shards + auxiliary MTP file). The literal `mtp.` namespace has **31 indexed names**. Do not conflate those 31 with the previous header analyzer's separate `2` MTP *routed-classified* names; those are different predicates/populations.

| Base layer | First numbered shard | Second numbered shard | Sum |
|---|---:|---:|---:|
| 8 | `model-00004-of-00017.safetensors`: **2,119** | `model-00005-of-00017.safetensors`: **2,489** | **4,608** |
| 11 | `model-00005-of-00017.safetensors`: **3,685** | `model-00006-of-00017.safetensors`: **923** | **4,608** |

The new counts cover **all nine indexed key categories**; the earlier Attempt 01 partial counters summed to 3,072 per layer because the old checker did not classify the three `weight_packed` key categories. Previous immutable Attempt 01 metrics must not be rewritten to these figures.

There are **13** `(layer, expert)` candidate groups with keys across more than one shard. The checker printed **12 bounded examples**, not the complete 13-case list. Reported examples include layer 1/expert 456 (shards 1,3), layer 5/expert 61 (3,4), layer 8/expert 235 (4,5), and layer 11/expert 409 (5,6). The 13-count and these examples are **indexed file ownership**, not proof of simultaneous resident buffers, live shard processing order, or measured memory retention.

## Input scales: key names absent but initialized values unverified

The entire indexed key name set contains **0 key names with `input_scale` or `input_global_scale` substring**. However the exact H38 CT installed source previously showed **eight registered parameter families**, including two `w13_input_global_scale` and `w2_input_global_scale`. This 9-slot checkpoint index schema only maps the other six parameter families. Do not assume the input-scale parameters have no source, are zero or uninitialized, are safe defaults, or are actually loaded: these cases are **not proven** by name absence.

This distinction is relevant to the separate source-level conditional compressed `RoutedExperts` input-scale Tensor truth-value hazard; that source conditional was not executed or reproduced here.

## Historical and next-gate disposition

- **Attempt 01 remains immutable:** `H38_CKPT_CT_KEY_MAP_GATE=FAIL_KEY_SCHEMA`, rc=3, because the **checker expected `*.weight`** but the real index uses `*.weight_packed`. Canonical: [Attempt 01 schema FAIL](orcarouter-h38-ct-checkpoint-key-map-attempt01-schema-fail-20261011.md). That was a false-negative checker name contract, not evidence of missing packed weights.
- **Attempt 02 is a new success** after narrow checker correction and a separate GitHub CI that passed **716/716** tests. The two attempts used the same exact checkpoint index hash and different, identified checker source revisions.
- Previous checkpoint full-header **`CHECKPOINT_METADATA_ORDER_GATE=FAIL` remains FAIL** because the strict loader-revisit order criterion still detects split layer 8 and 11. A complete index key name-grid neither repairs loader ordering nor establishes a memory peak.
- Next admissible engineering work: use existing checked-in source and these **index-name counts** to trace why `input_global_scale` parameters exist without matching keys and whether CT methods give them deterministic defaults or rely on actual loader events; then characterize **metadata-only cross-shard key ownership** (including the 13th case) and callback/CopyCounter **semantics**, each as a distinct gate. Prefer **source-only** and tiny synthetic fixtures; no H38 GPU/model/checkpoint-payload runtime or host protection changes.

**Current gate vector (strict):**
```text
CT_INSTALLED_SOURCE_CONTRACT=PASS_SOURCE_CONTRACT_ONLY
CT_SCALE_ATTR_SOURCE_SITES=PASS_SOURCE_SITES_ONLY
CT_EXPERT_DESTINATION_SOURCE_BRANCHES=PASS_SOURCE_BRANCHES_ONLY
CT_CHECKPOINT_KEY_MAP_ATTEMPT01=FAIL_KEY_SCHEMA [IMMUTABLE HISTORICAL]
CT_CHECKPOINT_KEY_MAP_ATTEMPT02=PASS_BASE_KEY_SCHEMA_ONLY
CHECKPOINT_METADATA_ORDER_GATE=FAIL
CT_INPUT_SCALE_DATA_SOURCE=UNVERIFIED
CT_EFFECTIVE_LOADER_CALLBACKS=UNVERIFIED
CT_WEIGHT_COMPLETENESS=UNVERIFIED
CT_COPYCOUNTER_SCALE_CREDIT=UNVERIFIED
CT_UNIQUE_DESTINATION_ELEMENT_COVERAGE=UNVERIFIED
SHARD_8_11_REPLAY_AND_BUFFER_LIFETIME=UNVERIFIED
PEAK_BUFFER_BYTES=UNVERIFIED
FUNCTIONAL=NOT_REACHED
HOST_STABILITY=INCONCLUSIVE
RM_MITIGATION=UNPROVEN
GPU_MODEL_RERUN=BLOCKED
HOST_PROTECTION=UNCHANGED
CT_META_PATCH=BLOCKED
PR_259=DRAFT_OPEN
MERGE=BLOCKED
```
