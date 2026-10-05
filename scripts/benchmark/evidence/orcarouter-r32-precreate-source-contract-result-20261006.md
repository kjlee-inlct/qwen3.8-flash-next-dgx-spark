# R32 — exact-image pre-create source contract result

Status: **COMPLETED — ATTEMPT03 PASS — STATIC / READ-ONLY — NO RUNTIME CAUSAL CLAIM**

## Scope

R32 tests the exact installed vLLM source in the already validated R28 diagnostic image after R31 established that all 48 repeated `800 MiB` RM requests occur before `ModelOptNvFp4FusedMoE.create_weights()` begins.

Image:

- `vllm-orcarouter-v029-r28-unquant-linear-marker:v1`
- image id `sha256:54c1ae1ba05fc34ec10881db4e5a333895eebf5472a5d282fefa354fe39a762f`

No model launch, GPU access, network access, kprobe change, or evidence mutation occurred.

## Invalid attempts retained

### Attempt01

**SETUP INVALID / NO SOURCE-CLOSURE CLAIM.**

The checker used whole-file `str.find()` ordering for Sparse-MoE assignments, so identical assignment spellings in other classes could produce a false ordering failure.

Canonical invalid record:

- `orcarouter-r32-attempt01-static-checker-invalid-20261006.md`

### Attempt02

**SETUP INVALID / NO SOURCE-CLOSURE CLAIM.**

The checker correctly scoped the lookup to `Qwen3NextSparseMoeBlock.__init__`, but incorrectly required the exact installed `self.gate` RHS class to be `GateLinear`. R32's contract is ordering, not a hard-coded gate implementation class.

Canonical invalid record:

- `orcarouter-r32-attempt02-static-checker-invalid-20261006.md`

Both checker defects were fixed and covered by regression tests before Attempt03.

## Attempt03 exact-image result

Repository head used on the DGX:

`f4861c5ed98031ff5c5776472b62faab76a1942c`

Exact output:

- `qwen4_decoder_attention_before_mlp=PASS`
- `qwen4_decoder_hyperconnection_after_mlp=PASS`
- `sparse_moe_gate_before_factory=PASS`
- `sparse_moe_gate_line=170`
- `sparse_moe_gate_call=ReplicatedLinear`
- `sparse_moe_shared_gate_line=178`
- `sparse_moe_shared_gate_call=ReplicatedLinear`
- `sparse_moe_factory_line=215`
- `sparse_moe_factory_call=FusedMoEFactory`
- `routed_experts_order_contract=PASS`
- `factory_pre_routed_direct_tensor_alloc_count=0`
- `factory_pre_routed_direct_tensor_allocs=NONE`
- `routed_pre_create_direct_tensor_alloc_count=0`
- `routed_pre_create_direct_tensor_allocs=NONE`
- `direct_precreate_tensor_alloc_syntax=ABSENT`
- `r32_discriminator=R32_NO_DIRECT_PRECREATE_WEIGHT_ALLOCATION_SUPPORTS_ALLOCATOR_BACKING_GROWTH`
- `R32_ATTEMPT03_RC=0`
- `R32_ATTEMPT03_SOURCE_CONTRACT=PASS`

## Managed non-mutation

Before and after Attempt03:

- container id: `4ebf6df5860aef7b6e0681792f8b8a58b165dee454a98cc6f4bbb0926d94f321`
- StartedAt: `2026-10-05T12:32:36.149058234Z`
- service: `active`

Therefore the source-only inspection did not restart or replace the managed runtime.

## Interpretation

R32 does **not** prove that helper constructors allocate nothing. It proves a narrower and useful fact: in the exact installed source, the pre-`create_weights()` path contains no separate direct `torch.empty`/`Parameter`-class allocation syntax that can be identified as an explicit 800 MiB model-weight owner.

Combined with earlier evidence:

- R23: the early burst is direct NVIDIA RM system-memory allocation activity, not the selected UVM allocation paths;
- R28b: RM-positive unquantized Linear calls are sparse, repeated positive events are dominated by fixed 800 MiB requests, and nominal payload size poorly explains RM activity;
- R29/R29b: 48 repeated 800 MiB requests form a strict ordinal cadence immediately before 48 repeated 400 MiB requests;
- R30: all 48 400 MiB requests map exactly one-to-one to packed expert `w13` allocation intervals, while the preceding 800 MiB userspace placement is mixed;
- R31: all 48 preceding 800 MiB requests occur before `ModelOptNvFp4FusedMoE.create_weights()` begins;
- R32: no separate direct pre-create weight allocation syntax is present in the exact installed source.

The best-supported engineering interpretation is therefore:

**The 400 MiB family is directly localized to packed w13 construction. The 800 MiB family is not supported as a distinct model-component weight owner; it is best treated as a discrete CUDA/NVIDIA RM backing/reservation growth event temporally induced by the repeated decoder-layer construction cycle.**

This is still a mechanism-level inference, not a user-space causal ownership proof. RM requested bytes remain allocation activity volume and must not be re-labeled as exact resident ownership.

## Direction

Model-component/prefix localization for the 800 MiB family is closed. Do not add more model-prefix markers.

A new live R33 is **not automatically authorized**. It is only justified if a mitigation decision requires distinguishing the exact lower-level allocator transition that emits the 800 MiB RM request. Any such R33 must be narrow and allocator-focused; do not broaden into UVM, generic page-allocation, scheduler, broad CUDA API, or blanket Python tracing.

H11 remains deferred pending the mitigation decision. PR #244 remains open/unmerged.