# OrcaRouter R27 — H6 quantization-routing read-only inspection plan — 2026-10-05

## Status

**COMPLETED — READ-ONLY PASS — ROUTING EXPLAINS ZERO W4A16 DENSE CALLS — NO GENERIC R28 DISPATCH RUN NEEDED**

R27 is closed as:

**VALID_MEASURED — FUNCTIONAL PASS / HOST-STABILITY FAIL — `RM_ORDER4_R26_RESIDUAL_MIXED_WITHIN_QWEN4_LAYERS`**

Canonical predecessor/result:

- `scripts/benchmark/evidence/orcarouter-r27-linear-residual-result-20261005.md`
- `scripts/benchmark/evidence/orcarouter-r27-h6-quant-routing-inspection-result-20261005.md`

R27 found zero runtime invocations of `ModelOptNvFp4W4A16LinearMethod.create_weights()` despite the H6 checkpoint declaring `W4A16_NVFP4`, while `91.996099%` of the R26 non-MoE residual remained inside selected Qwen4 decoder layers.

The completed read-only inspection explains that result as routing rather than marker failure.

## Completed observations

H6 remains the intended config-only control:

```text
manifest.variant=h6-modelopt-w4a16
manifest.parent_variant=h5-neutral-input-scale
manifest.quant_algo_before=NVFP4
manifest.quant_algo_after=W4A16_NVFP4
manifest.safetensor_bytes_changed=0
quant.quant_method=modelopt
quant.quant_algo=W4A16_NVFP4
```

The inherited ModelOpt ignore list contains broad decoder families including:

```text
*.self_attn.*
*.linear_attn.*
*.mlp.gate*
*.mlp.shared_expert.*
*.mlp.shared_expert_gate*
*hyper_connection*
*.ple.*
```

Approximate checkpoint-prefix diagnostics found `117` matches under `*.self_attn.*` and `252` under `*.linear_attn.*`.

The exact R27 image source contract passed:

```text
linear_none_selects_unquantized=PASS
modelopt_exclusion_selects_unquantized=PASS
modelopt_w4a16_class_selection_exists=PASS
qwen4_modelopt_fp4_optout_helper=PASS
qsa_qkv_uses_modelopt_fp4_optout=PASS
R27_SOURCE_ROUTING_CONTRACT=PASS
```

Managed runtime identity and StartedAt were unchanged across the inspection. No model launch, restart, RM trace, or persistent tuning occurred.

## Decision closure

The `Config/source routing explains zero W4A16 calls` branch is selected.

Do not perform a generic R28 all-quant-method dispatch run merely to rediscover the same routing. The next useful boundary is narrower: `UnquantizedLinearMethod.create_weights()` only.

This is necessary because the selected decoder non-MoE RM activity (`39,148.250 MiB`) is much larger than ordinary BF16 attention parameter payload. RM logical requested bytes remain activity volume, not exact resident ownership, so direct temporal overlap is required before inferring allocator amplification.

## Next experiment constraint

R28 may instrument only the unquantized Linear create-weights path while inheriting the already validated narrow direct-RM trace and R26/R27 model/layer markers. It should aggregate overlap by exact prefix family and report dimensions/dtype without changing allocation semantics.

No H11 behavior change is authorized yet. Do not broaden into UVM, generic page allocation, scheduler, function-graph, CUDA-API, Python-profiler, or PLE page-fault tracing.

PR #244 remains open. No merge is implied or authorized.
