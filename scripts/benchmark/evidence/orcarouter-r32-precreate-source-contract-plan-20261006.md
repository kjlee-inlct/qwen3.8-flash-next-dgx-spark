# R32 — exact-image pre-create source contract

Status: **IMPLEMENTED — CI REQUIRED — STATIC/READ-ONLY ONLY**

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

## Expected source contract

- attention constructors precede `self.mlp = Qwen4ExpSparseMoeBlock(...)`;
- hyper-connection constructors follow MLP construction;
- Sparse-MoE gate/shared-gate setup precedes `FusedMoEFactory(...)`;
- RoutedExperts resolves quant method and rounds sizes before calling `quant_method.create_weights()`;
- no direct large model-tensor allocation syntax appears in FusedMoEFactory before RoutedExperts creation or in RoutedExperts before quant-method `create_weights()`.

## Interpretation rule

If the exact-image contract passes, it does **not** prove that helper constructors allocate nothing. It does show that there is no separate explicit pre-create weight allocation matching the repeated 800 MiB family. Combined with R28b/R29/R30/R31, this is sufficient to stop assigning the 800 MiB pulse to whichever userspace prefix temporally overlaps it and to prioritize allocator/backing-growth semantics.

Expected discriminator:

`R32_NO_DIRECT_PRECREATE_WEIGHT_ALLOCATION_SUPPORTS_ALLOCATOR_BACKING_GROWTH`

No live run, model restart, GPU model launch, kprobe modification, or behavior-changing experiment is authorized by this plan. H11 remains deferred.
