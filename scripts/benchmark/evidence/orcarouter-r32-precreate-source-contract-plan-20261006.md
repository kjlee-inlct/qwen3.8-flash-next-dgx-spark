# R32 — exact-image pre-create source contract

Status: **COMPLETED — ATTEMPT03 PASS — STATIC / READ-ONLY — NO RUNTIME CAUSAL CLAIM**

Canonical result:

- `orcarouter-r32-precreate-source-contract-result-20261006.md`

Invalid checker attempts remain preserved separately:

- `orcarouter-r32-attempt01-static-checker-invalid-20261006.md`
- `orcarouter-r32-attempt02-static-checker-invalid-20261006.md`

## Question

R31 proved that all 48 repeated `800 MiB` RM requests occur before `ModelOptNvFp4FusedMoE.create_weights()` begins. R30 proved each is the immediately preceding RM request before the corresponding exact `400 MiB` w13 allocation.

R32 asks whether the exact installed vLLM source contains any **direct tensor-allocation syntax** in the pre-`create_weights()` path that could plausibly represent a separate model-weight owner for the 800 MiB family.

## Exact source inspected

Inside the already validated R28 diagnostic image:

- `vllm/models/qwen4_exp/nvidia/model.py`
- `vllm/model_executor/models/qwen3_next.py`
- `vllm/model_executor/layers/fused_moe/layer.py`
- `vllm/model_executor/layers/fused_moe/routed_experts.py`

The inspector verifies constructor order and counts direct calls such as `torch.empty`, `torch.zeros`, `torch.ones`, `torch.full`, and `Parameter` before `RoutedExperts.quant_method.create_weights()`.

## Completed source contract

Attempt03 on exact R28 image `sha256:54c1ae1ba05fc34ec10881db4e5a333895eebf5472a5d282fefa354fe39a762f` passed:

- attention constructors precede `self.mlp = Qwen4ExpSparseMoeBlock(...)`;
- hyper-connection constructors follow MLP construction;
- installed Sparse-MoE gate is `ReplicatedLinear` at line 170;
- installed shared-expert gate is `ReplicatedLinear` at line 178;
- `FusedMoEFactory(...)` follows at line 215;
- RoutedExperts resolves quant method and rounds sizes before calling `quant_method.create_weights()`;
- direct allocation syntax before RoutedExperts construction: `0`;
- direct allocation syntax in RoutedExperts before quant-method `create_weights()`: `0`;
- `direct_precreate_tensor_alloc_syntax=ABSENT`.

Final discriminator:

`R32_NO_DIRECT_PRECREATE_WEIGHT_ALLOCATION_SUPPORTS_ALLOCATOR_BACKING_GROWTH`

## Interpretation rule

R32 does **not** prove that helper constructors allocate nothing. It shows that there is no separate explicit pre-create weight allocation matching the repeated 800 MiB family. Combined with R28b/R29/R30/R31, this closes model-prefix/component ownership localization for the 800 MiB family and prioritizes allocator/backing-growth semantics.

The 400 MiB family remains directly localized to packed w13 construction. The 800 MiB family is best treated as a discrete CUDA/NVIDIA RM backing/reservation growth event temporally induced by the repeated decoder-layer construction cycle, not as a distinct explicit model-weight owner.

No additional model-prefix markers are justified. A new live R33 is not automatically authorized; it is only justified if a mitigation decision requires identifying the exact lower-level allocator transition.

H11 remains deferred. PR #244 remains open/unmerged.