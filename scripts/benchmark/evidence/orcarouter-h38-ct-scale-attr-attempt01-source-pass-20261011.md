# H38 CT input-scale postconstruction weight-loader attribute source audit — Attempt 01 PASS (2026-10-11)

## Provenance and scope

- Source: operator's DGX Spark terminal transcript pasted into this conversation on 2026-10-11. This file preserves material reported fields, not a byte-exact independently retrieved `/tmp` file; the operator logfile SHA256 has **not** been collected independently.
- Operator logfile path: `/tmp/h38-ct-scale-attrs-attempt01-20261011.txt` (reported, not independently inspected).
- Branch: `feat/h38-managed-integration`; operator `git fetch` and `git merge --ff-only` successfully fast-forwarded `5fa4265..1865521` before execution. Exact clean target/HEAD: `1865521c2ff58add7bddeed6735c76803a3e3637`.
- Guarded command: `H38_CT_SCALE_ATTR_TARGET_SHA=1865521c2ff58add7bddeed6735c76803a3e3637 bash scripts/benchmark/check-h38-ct-scale-attr-provenance.sh`.
- Guarded H38 image ID: `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`; read-only/runc, no network/GPU/checkpoint payload/model runtime.
- The new source-only inspector is distinct from the earlier 8-parameter CT/Layerwise/RoutedExperts **Attempt 03 PASS_SOURCE_CONTRACT_ONLY** at commit `5fa4265d394255744f8886b857804a28c433cf3f`. Both source inspections succeeded independently at their respective exact HEADs.

## Exact reported terminal result

```text
H38_CT_SCALE_ATTR_PREFLIGHT=BEGIN
checkout_sha=1865521c2ff58add7bddeed6735c76803a3e3637
image_id=sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc
scope=exact_installed_source_only_no_checkpoint_no_gpu_no_model_no_network
H38_CT_SCALE_ATTR_SOURCE=PASS_SOURCE_SITES_ONLY
"classification": "EXACT_IMAGE_SOURCE_SITES_ONLY_NOT_RUNTIME_QUALIFICATION"
"attrs_helper_digest_status": "IMAGE_ID_GUARDED_OBSERVATION_NOT_PREPINNED"
"effective_runtime_attr_value": "UNVERIFIED"
"torch_dispatch_scale_copy_credit": "UNVERIFIED"
"complete_loaded_experts_and_scales": "UNVERIFIED"
"gpu_or_model_runtime": "NOT_EXECUTED"
"image_or_host_mutation": "NOT_PERFORMED"
image_identity_unchanged=YES
gpu_or_model_load=NO
checkpoint_payload_read=NO
managed_service_mutation=NO
host_protection_changed=NO
ct_meta_patch_implemented=NO
H38_CT_SCALE_ATTR_PREFLIGHT=PASS_SOURCE_SITES_ONLY
HEAD=1865521c2ff58add7bddeed6735c76803a3e3637
source_check_rc=0
evidence_log=/tmp/h38-ct-scale-attrs-attempt01-20261011.txt
```

## Actual CT input scale setter sites (source only)

| Parameter name | Registered variable | register line | TENSOR quant_method update line | set_weight_attrs line |
|---|---|---:|---:|---:|
| `w13_input_global_scale` | `w13_input_scale` | 183 | 184 | 187 |
| `w2_input_global_scale` | `w2_input_scale` | 192 | 193 | 196 |

Each registration is followed by the relevant `extra_weight_attrs.update({"quant_method": FusedMoeWeightScaleSupported.TENSOR.value})` source expression and then `set_weight_attrs(var, extra_weight_attrs)`. The inspector requires these call sites, symbolic ordering, and existing loader origin syntax `extra_weight_attrs.get('weight_loader')`. The corresponding constructor source was previously confirmed to use plain `torch.nn.Parameter` with no explicit constructor `weight_loader` keyword.

The pinned RoutedExperts source exposes its `weight_loader` in source via a quantization configuration mapping; pinned layerwise source contains `tensor.weight_loader = make_online_process_loader(layer, name)` and `original_loader = _get_original_loader(param)`; the common helper's source contains an attribute-overwrite guard and `setattr(weight, key, value)`.

**These are AST source sites, not an observed runtime dictionary value, successful setattr, real function call, dispatch event, or per-expert loaded tensor.** The presence of postconstruction setter sites means the earlier constructor-only absence of a loader keyword **cannot** be used to claim input-scale has no loader.

## Source digests

| Pinned H38 installed source | Reported SHA256 | Evidence class |
|---|---|---|
| CT MoE NVFP4 `ct` | `d7b47e442cee1a333753143cbd727eac857c6bbdb27d6cd8107bd6210e98e9d2` | PREPINNED and verified |
| RoutedExperts `routed` | `5206219da6b78315d6b35bee89fd0caa783681846affbf6917f430ef7f2481b5` | PREPINNED and verified |
| reload/layerwise `layerwise` | `9f37db893446d1f8ddc654a3bbcc3addf4b3020565920c56ef0c1ae29fd32a4a` | PREPINNED and verified |
| `vllm/model_executor/utils.py` `attrs_helper` | `f208310647a012797e0b0e9631d3498135c7f9aef831e35e42e96eceb7623f89` | Newly **observed** from image-ID-guarded source; NOT pre-pinned for Attempt 01 |

The new utils.py digest can be used as a pinned baseline for a separate future check only if the provenance distinction above is preserved. It should never be retroactively described as an independently pre-approved source hash for Attempt 01.

## What is and is not qualified

**Qualified:** exact H38 image/source registration-to-setter AST contract for both input scales, TENSOR quant-method source tag, loader origin/export/reassignment/source helper guard syntax, identity unchanged after the run; no GPU, model, checkpoint payload or host protection changes reported.

**Not qualified:** effective post-construction weight_loader callback and instance attribute value; whether TorchDispatchMode counts indexed writes as `aten.copy_.default` events; actual 512-expert weight and scale coverage, deduplication of overlapping copies or correctness of deferred layerwise threshold; split layers 8 and 11 shard replay/retention; finite peak buffer bytes; inference functionality, RM mitigation and host stability.

The operator's source checker stdout explicitly marks `effective_runtime_attr_value`, `torch_dispatch_scale_copy_credit` and `complete_loaded_experts_and_scales` as `UNVERIFIED`; we retain them as such.

## Next safe technical gate

Do not repeat these two successful installed-image AST inspections solely to gather the same source markers. Next useful work:

1. Distinguish static source attribute wiring from actual runtime values. Review `_get_weight_loader`, `_get_original_loader` and the relation of common `set_weight_attrs` to H11 `extra_weight_attrs`, particularly whether callback metadata may be wrapped twice or overwritten.
2. Separately design an **explicitly bounded CPU-only synthetic** probe for PyTorch `TorchDispatchMode` indexed writes vs `aten.copy_.default` (without H38 checkpoint/model/GPU), only when a safe environment and resource cap can be established. A synthetic result is not an H38 loaded-expert completeness proof.
3. Evaluate layer 8 and 11 ownership/order and original buffer lifetime from pinned source/checkpoint metadata only, without full model execution.

**Gates unchanged:** CT_INSTALLED_SOURCE_CONTRACT=PASS_SOURCE_CONTRACT_ONLY; CT_SCALE_ATTR_SOURCE_SITES=PASS_SOURCE_SITES_ONLY; CT_WEIGHT_COMPLETENESS=UNVERIFIED; CT_COPYCOUNTER_SCALE_CREDIT=UNVERIFIED; SHARD_8_11_COMPLETENESS=UNVERIFIED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; CHECKPOINT_METADATA_ORDER_GATE=FAIL; GPU_MODEL_RERUN=BLOCKED; HOST_PROTECTION=UNCHANGED; CT_META_PATCH=BLOCKED; PR_259=DRAFT_OPEN / MERGE=BLOCKED.
