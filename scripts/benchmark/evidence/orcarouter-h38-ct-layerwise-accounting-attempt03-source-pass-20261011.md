# H38 CT layerwise accounting — operator Attempt 03 SOURCE CONTRACT PASS, 2026-10-11

## Provenance and qualification

**Observed first successful exact-image source-only audit; not a runtime or memory qualification.**

- Evidence origin: user's pasted DGX Spark terminal transcript attached to this conversation, containing full reported standard output through final exit code. This document transcribes verified fields; it is **not** a byte-identical materialization of the operator's /tmp logfile, and no independent SHA256 was obtained for that logfile.
- Operator-reported logfile path: `/tmp/h38-ct-accounting-attempt03-20261011.txt`; independent file presence and SHA256 are **not** established.
- Repository: `kjlee-inlct/qwen3.8-flash-next-dgx-spark`, branch `feat/h38-managed-integration`.
- Initial local HEAD was behind `origin/feat/h38-managed-integration`. The operator fetched and successfully fast-forwarded `88e8a05..5fa4265`; exact checked-out HEAD after update: `5fa4265d394255744f8886b857804a28c433cf3f`.
- Image label: `vllm-orcarouter-v029-h38-decoder-scope:v1`.
- Image ID reported and checked before/after execution: `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`.
- Guarded program: `scripts/benchmark/check-h38-ct-layerwise-accounting.sh`, invoking `scripts/benchmark/inspect-h38-ct-layerwise-accounting.py` in the pinned read-only/no-network/no-GPU/no-model/unprivileged runc source-only container. No checkpoint payload scan.

## Key operator output (as provided)

```text
H38_CT_ACCOUNTING_PREFLIGHT=BEGIN
checkout_sha=5fa4265d394255744f8886b857804a28c433cf3f
image_id=sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc
scope=exact_installed_source_only_no_checkpoint_no_gpu_no_model_no_network
H38_CT_ACCOUNTING_SOURCE=PASS_SOURCE_CONTRACT_ONLY
"classification": "SOURCE_CONTRACT_ONLY_NOT_RUNTIME_QUALIFICATION"
"actual_scale_copy_counter_credit": "UNVERIFIED"
"complete_parameter_coverage": "UNVERIFIED"
"per_expert_loader_mapping": "UNVERIFIED"
"peak_buffer_bytes": "UNVERIFIED"
"scale_parameter_class_semantics": "UNVERIFIED"
"shard_split_8_11_completion": "UNVERIFIED"
"meta_patch_or_host_mitigation": "NOT_IMPLEMENTED"
image_identity_unchanged=YES
gpu_or_model_load=NO
checkpoint_payload_read=NO
managed_service_mutation=NO
host_protection_changed=NO
ct_meta_patch_implemented=NO
H38_CT_ACCOUNTING_PREFLIGHT=PASS_SOURCE_CONTRACT_ONLY
HEAD=5fa4265d394255744f8886b857804a28c433cf3f
source_check_rc=0
evidence_log=/tmp/h38-ct-accounting-attempt03-20261011.txt
```

## Five exact installed-image source pins — independently checked by inspector

| Source file key | SHA256 |
|---|---|
| ct | `d7b47e442cee1a333753143cbd727eac857c6bbdb27d6cd8107bd6210e98e9d2` |
| layerwise | `9f37db893446d1f8ddc654a3bbcc3addf4b3020565920c56ef0c1ae29fd32a4a` |
| meta | `87a98fe340f7e39a7ba3ed136506bf5e3eef463f9215420cce5ddeb5d25a2b9c` |
| routed | `5206219da6b78315d6b35bee89fd0caa783681846affbf6917f430ef7f2481b5` |
| utils | `9421654170a04244d9ad702ba8c81dcf6c09a3c8bfe7e04ccbe099baf57b63a1` |

These hashes were checked under the pinned image source and match the tool's expected values. The source-only PASS is specific to this image ID and these file contents, not arbitrary image versions.

## Eight source registration contracts — all reported

| Name | Constructor | Declared dtype | Source line |
|---|---|---|---:|
| w13_weight_packed | ModelWeightParameter | torch.uint8 | 103 |
| w2_weight_packed | ModelWeightParameter | torch.uint8 | 117 |
| w13_weight_scale | ModelWeightParameter | torch.float8_e4m3fn | 133 |
| w2_weight_scale | ModelWeightParameter | torch.float8_e4m3fn | 151 |
| w13_weight_global_scale | PerTensorScaleParameter | torch.float32 | 162 |
| w2_weight_global_scale | PerTensorScaleParameter | torch.float32 | 172 |
| w13_input_global_scale | torch.nn.Parameter | torch.float32 | 183 |
| w2_input_global_scale | torch.nn.Parameter | torch.float32 | 192 |

The PASS covers the detailed symbolic dimensions and constructor keyword source contracts specified by the inspector, including `ModelWeightParameter(input_dim=1, output_dim=2, weight_loader=weight_loader)`, explicit PerTensorScaleParameter constructor weight_loader, and unchanged H12 object-alias syntax. The plain input global-scale parameters were not constructed with an explicit weight_loader keyword; **subsequent attribute assignment and effective loader behavior remain unproven by that fact alone**.

The inspected CT method reports `create_weights` at line 77 and `process_weights_after_loading` at line 198, with H12 alias syntax `PRESENT`.

## Layerwise accounting and RoutedExperts static paths

- All **21** inspected Layerwise/CopyCounter/materialization/source anchors returned `true` (including aggregate numel threshold, per-call cap, `aten.copy_.default` counter, deferred replay, partial finalization, late parameter re-wrapping, materialization class/attribute syntax, and H12 post-load method call).
- All **14** RoutedExperts AST dispatch anchors returned `true` (global→local map, local-expert skipping, GROUP/TENSOR tags, explicit packed/group copies, input/tensor scale indexed assignment sites).
- Routed helper counts reported `input_global_scale_helper=1` and `tensor_global_scale_helper=2` syntactic indexed assignment sites. Source-level classification: `MIXED_EXPLICIT_COPY_AND_INDEXED_ASSIGNMENT`.
- **Do not map these syntactic assignment counts onto TorchDispatchMode `aten.copy_` invocations** without dynamic, properly isolated evidence. The exact number of loaded expert or scale elements and whether any invocation repeats/revisits destination memory are not observed here.

## Disposition and next admissible gate

Historical attempts stay immutable: Attempt 01 INVALID due to checker unsupported PerTensorScaleParameter; Attempt 02 INVALID because group scales used ModelWeightParameter where the checker expected other classes. **Attempt 03 closes only these static inspector source-contract mismatches** and supports `CT_INSTALLED_SOURCE_CONTRACT=PASS_SOURCE_CONTRACT_ONLY`.

Next bounded engineering questions, **not yet qualified by this audit**:

1. Trace static input-scale parameter attribute setup and actual `weight_loader` binding through `set_weight_attrs` / RoutedExperts, while distinguishing constructor kwargs from post-construction registration.
2. Characterize CPU-only TorchDispatchMode copy event semantics for indexed global/input-scale writes on tiny synthetic tensors, without H38 model/checkpoint/GPU, and without extrapolating event count into unique lifetime coverage.
3. Determine expert shard mapping and last-shard source ordering/retention for actual layer 8 and 11; derive any finite memory bound only from real loader behavior or bounded, properly qualified evidence, not hypothetical byte-count extrapolation.
4. Preserve the current real-execution safety gate: no H38 GPU/model rerun, no CT meta storage patch, no Docker image rebuild, no host protection/service changes, no PR #259 Ready/Merge.

**Final classification:** CT_INSTALLED_SOURCE_CONTRACT=PASS_SOURCE_CONTRACT_ONLY; CT_WEIGHT_COMPLETENESS=UNVERIFIED; CT_COPYCOUNTER_SCALE_CREDIT=UNVERIFIED; CT_SCALE_PARAMETER_SEMANTICS=UNVERIFIED; SHARD_8_11_COMPLETENESS=UNVERIFIED; PEAK_BUFFER_BYTES=UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE=FAIL; FUNCTIONAL=NOT_REACHED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; PR_259=DRAFT_OPEN; MERGE=BLOCKED.
