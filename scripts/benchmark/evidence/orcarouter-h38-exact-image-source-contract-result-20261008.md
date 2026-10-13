# H38 exact installed-image source contract — DGX observed result — 2026-10-08

Status: **VALID READ-ONLY SOURCE-CONTRACT PASS** — **NOT** a runtime, RM mitigation, or host-stability qualification.

## Provenance and execution

The DGX Spark operator provided the complete terminal output of the one-time exact-H38-installed-image static checker.

| Provenance field | Recorded result |
|---|---|
| Branch | `feat/h38-managed-integration` |
| Exact executed checkout | `1a4416581f4064baa110fc83947c442c360c4689` |
| Image reference | `vllm-orcarouter-v029-h38-decoder-scope:v1` |
| Image ID (before and after) | `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc` |
| Runner | `scripts/benchmark/check-h38-exact-image-source.sh` |
| Source inspector | `scripts/benchmark/inspect-h38-exact-image-source.py` |
| Historical R32 source inspector reused on **H38 source** | `scripts/benchmark/inspect-orcarouter-r32-precreate-source-contract.py` |
| Host log | `/tmp/h38-exact-image-source-contract.txt` (operator-side path, not independently fetched into repository) |
| `H38_EXACT_IMAGE_SOURCE_PREFLIGHT` | **PASS** |
| `H38_EXACT_IMAGE_SOURCE_CONTRACT` | **PASS** |
| `source_check_rc` | **0** |

The source checker ran in an **ephemeral unprivileged runc container** with GPU-independent `--runtime runc`, `--network none`, `--read-only`, `--pull never`, resource limits and read-only script mounts. Docker briefly created and removed the source-inspection container; that should not be described as literally no container creation.

The runner rejected a dirty or mismatched checkout before source inspection and checked inherited H11/H12 and H38 labels (otherwise it would have aborted before the observed source output). These guards passed in the provided run; the output does **not** contain a separate raw dump of the inherited labels. The inspector made no vLLM/torch/CUDA imports and performed no checkpoint/model loading. The recorded end-of-run assertions were:

```text
image_identity_unchanged=YES
managed_runtime_mutation=NO
gpu_or_model_load=NO
protection_changed=NO
host_stability_qualified=NO
H38_EXACT_IMAGE_SOURCE_PREFLIGHT=PASS
source_check_rc=0
```

These assertions reflect what the checker actually verifies. They are not a new independent managed-service `StartedAt` or kernel-memory-trace measurement.

## Exact installed source identities

The CPU-only inspector computed SHA256 hashes from the installed source files of the exact running image:

| Source file group | SHA256 |
|---|---|
| H11/H12/H38 compressed-tensors MoE (`ct`) | `d7b47e442cee1a333753143cbd727eac857c6bbdb27d6cd8107bd6210e98e9d2` |
| Humming FP8 (`humming`) | `1e20223935b6236f2ed94c04caddb1ae15a6968073443711dddf7c2c0876759e` |
| Marlin MoE (`marlin`) | `3f3598c65a2096f07d42fc458ec42c7fabce6f2553602fdc6ca49e8be8da1d03` |

These hashes capture installed **source identity** for later comparison. They do not certify an RM allocator outcome.

## Observed H11/H12/H38 source contracts

```text
h11_packed_weights=PASS
h11_tensor_allocations_retained=YES
h12_postload_object_alias=PASS
h38_ct_marlin_layer_tag=PASS
h38_humming_fp8_control=PASS
h38_marlin_canonical_scoped=PASS
```

Interpretation:

1. **H11 keeps both original packed `torch.empty` allocations** for `w13_weight` and `w2_weight`, wrapping them in `ModelWeightParameter`. Therefore H11 is not a direct removal of either tensor-creation request.
2. **H12 preserves the post-load parameter object** while changing name/registration behavior; it does not demonstrate reduction of pre-weight-fill host RM allocations.
3. **H38 Humming FP8 and decoder-scoped Marlin patch syntax** is present and structurally consistent with the inspected image. This validates source shape, not live inference correctness or memory consumption.

## R32 source contract replayed on H38 image

The original R32 positive result was verified on the **R28 diagnostic image** and must retain that historical scope. This is now a separate **H38 image source replay** using the original source-only checker.

```text
r32_reuse_scope=THIS_IMAGE_SOURCE_ONLY_NOT_R28_RUNTIME_EVENT_TRANSFER
R32_PRECREATE_SOURCE_CONTRACT=BEGIN
semantics=static_exact_image_source_contract_not_runtime_causal_proof
qwen4_decoder_attention_before_mlp=PASS
qwen4_decoder_hyperconnection_after_mlp=PASS
sparse_moe_gate_before_factory=PASS
sparse_moe_gate_line=170
sparse_moe_gate_call=ReplicatedLinear
sparse_moe_shared_gate_line=178
sparse_moe_shared_gate_call=ReplicatedLinear
sparse_moe_factory_line=215
sparse_moe_factory_call=FusedMoEFactory
routed_experts_order_contract=PASS
factory_pre_routed_direct_tensor_alloc_count=0
factory_pre_routed_direct_tensor_allocs=NONE
routed_pre_create_direct_tensor_alloc_count=0
routed_pre_create_direct_tensor_allocs=NONE
direct_precreate_tensor_alloc_syntax=ABSENT
r32_discriminator=R32_NO_DIRECT_PRECREATE_WEIGHT_ALLOCATION_SUPPORTS_ALLOCATOR_BACKING_GROWTH
R32_PRECREATE_SOURCE_CONTRACT=END
```

**Source-structure conclusion:** No *explicit direct* tensor allocation syntax matching the checker's allowlist was found in the inspected H38 factory/routed constructor ranges *before* `quant_method.create_weights()`. This result cannot exclude allocations reached indirectly through helper constructors, general CUDA allocator backing growth, or NVIDIA RM; it does not trace a runtime event, allocate pages, or prove a specific original CUDA caller.

This closes the one outstanding **H38 installed-image source-syntax** verification gap. It does **not** close the **H38-specific driver-call attribution** gap.

## Cross-run memory and safety interpretation

The preserved H38 allocator attempt 01 reported a **74,761.516 MiB** approximate core-unexplained physical-page decrease over its largest pre-protection five-second window, with no corresponding SwapFree change; its host monitor intervened before READY, with **zero strict RM OOM records** in the measured kernel window. R23 separately attributed a same-scale burst primarily to direct NVIDIA RM system-memory allocation (`nv_alloc_pages`, `nv_alloc_system_pages`), but its same-window activity/residual ratio cannot be transplanted into the H38 data as if measured anew.

This source PASS does **not** change any original operational classification:

```text
source_contract=PASS
rm_oom_qualified=NO
allocator_mitigation_proven=NO
exact_original_cuda_caller_identified=NO
managed_h38_functional=NOT_REACHED
managed_h38_host_stability=INCONCLUSIVE
managed_h38_promotion=BLOCKED
```

No new H38 allocator live run, kprobe, NVIDIA driver instrumentation, VM tuning, monitor relaxation, model restart, or managed promotion was executed as part of this source check. PR #259 remains **Draft / Open**, without authorization to mark Ready or merge.

## Next engineering discriminator

The completed R11/R23–R32 evidence supports a discrete RM/CUDA backing-growth hypothesis, with exact packed `w13` request temporal localization and a non-uniquely attributed preceding `800 MiB` family. The actual installed H38 H11/H12 patches **do not remove their packed `torch.empty` tensor creation calls**; therefore recommending H11/H12 again as an already-proven memory mitigation is not justified.

**Next work should be a concrete mitigation design first**, including the exact allocator/backing behavior intended to change and falsifiable acceptance metrics for RM request activity, physical free-page residual, functional READY and strict host stability under unchanged guardrails. Without that hypothesis, do not rerun an unchanged H38 startup or reopen broad R33, UVM, model-prefix, CUDA or VM tracing.

## Evidence provenance limits

This document uses the operator's terminal transcript as its live evidence. The `/tmp/h38-exact-image-source-contract.txt` file has not been independently ingested into GitHub and should not be represented as a repository artifact or as providing new NVIDIA RM event data.

Prior static CI for the checker: `37747053983` and the subsequent source-plan synchronization `37747347746`, both **SUCCESS, 606/606 unit tests**, plus shell syntax, ShellCheck, Python compile and whitespace checks. Those are implementation tests, not the observed installed-image PASS above.
