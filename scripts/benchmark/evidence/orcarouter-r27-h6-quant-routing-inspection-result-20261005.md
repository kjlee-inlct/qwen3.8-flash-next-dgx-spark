# OrcaRouter R27 — H6 quantization-routing read-only inspection result — 2026-10-05

## Status

**COMPLETED — READ-ONLY PASS — ROUTING EXPLAINS ZERO W4A16 DENSE CALLS — MANAGED RUNTIME UNCHANGED**

This inspection followed the completed R27 live measurement. It did not launch a GPU model, restart the managed service, create an RM trace, or modify checkpoint files.

## Repository / managed runtime gate

The DGX updated to repository head:

`0a11fc8493a8e54dcee1fd5f64e2678272c52f39`

Before inspection the managed runtime was active and READY with exact served identity:

- model: `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`
- `max_model_len=262144`
- container ID: `9415187362d6f8b2d118d995aaa307b2c427c22d44d1548a78a166fe2c95812b`
- StartedAt: `2026-10-05T11:05:18.894715967Z`

The same container ID and StartedAt were present after inspection, and exact model readiness returned immediately.

Final non-mutation gate:

```text
R27_H6_READ_ONLY_ROUTING_GATE=PASS
model_restart=NO
managed_service_mutation=NO
gpu_model_launch=NO
rm_trace=NO
```

## H6 checkpoint identity

The read-only inspector reported:

```text
manifest.status=complete
manifest.variant=h6-modelopt-w4a16
manifest.parent_variant=h5-neutral-input-scale
manifest.quant_algo_before=NVFP4
manifest.quant_algo_after=W4A16_NVFP4
manifest.safetensor_bytes_changed=0
quant.quant_method=modelopt
quant.quant_algo=W4A16_NVFP4
quant.pattern_key=ignore
quant.pattern_count=13
quant.config_group_count=1
checkpoint.tensor_count=296474
checkpoint.derived_module_prefix_count=75085
checkpoint.approx_excluded_prefix_count=1321
```

H6 is therefore still the intended config-only W4A16 control. The zero R27 W4A16-linear marker count is not explained by a wrong top-level quantization identity.

## Relevant exclusion families

The inherited ModelOpt `ignore` rules include the two attention families that dominate the R27 non-MoE decoder residual:

```text
*.self_attn.*   -> approx_prefix_count=117
*.linear_attn.* -> approx_prefix_count=252
```

Observed matching checkpoint prefixes include QSA/full-attention projections and indexer modules under `self_attn`, and `conv1d`, input projections, normalization and `out_proj` under `linear_attn`.

Other broad excluded families include:

- `*.mlp.gate*`
- `*.mlp.shared_expert.*`
- `*.mlp.shared_expert_gate*`
- `*hyper_connection*`
- `*.ple.*`
- MTP
- visual modules
- embeddings
- `lm_head`

The checkpoint-name matching is diagnostic/approximate; exact runtime routing additionally uses vLLM packed-module mapping and model-specific overrides.

## Exact source-routing contract

The exact R27 diagnostic image passed all source checks:

```text
linear_none_selects_unquantized=PASS
modelopt_exclusion_selects_unquantized=PASS
modelopt_w4a16_class_selection_exists=PASS
qwen4_modelopt_fp4_optout_helper=PASS
qsa_qkv_uses_modelopt_fp4_optout=PASS
R27_SOURCE_ROUTING_CONTRACT=PASS
```

Therefore:

1. `LinearBase` chooses `UnquantizedLinearMethod` when `quant_config=None`;
2. ModelOpt exclusion can choose `UnquantizedLinearMethod`;
3. `ModelOptNvFp4W4A16LinearMethod` still exists and is available only to non-excluded modules that receive the ModelOpt config;
4. Qwen4Exp has an explicit ModelOpt-FP4 opt-out helper;
5. QSA `qkv_proj` explicitly uses that opt-out.

## Closure of the R27 zero-marker question

R27 observed zero `ModelOptNvFp4W4A16LinearMethod.create_weights()` calls while approximately `39,148.250 MiB` of non-MoE RM order-4 activity remained inside decoder-layer intervals.

The read-only inspection now explains this without another live allocator run: the relevant attention families are excluded from ModelOpt quantization and therefore route through unquantized Linear construction, with an additional explicit QSA qkv opt-out.

Thus the R27 W4A16 zero-call result is treated as a **real routing result**, not a marker failure.

## Important payload-versus-RM caution

Source/config dimensions imply that ordinary BF16 attention Linear parameter payload is only on the order of several GiB, far below the approximately `39.15 GiB` RM activity temporally associated with the decoder non-MoE intervals. RM requested bytes are allocation activity volume, not exact resident ownership, so this difference must not be described as tensor payload size.

The next discriminator must therefore test whether unquantized `torch.empty` parameter construction temporally coincides with disproportionate direct-RM backing/reservation activity.

## Next direction

Do not repeat R27. Do not run a generic all-quant-method dispatch trace. Do not apply H11 yet.

R28 should instrument only `UnquantizedLinearMethod.create_weights()` and preserve inherited R26/R27 markers. It should record prefix, Linear subclass, dimensions and dtype, then aggregate direct-RM order-4 overlap by prefix family (`linear_attn`, `self_attn`, `hyper_connection`, shared-expert/router, PLE, other).

The primary question is whether the union of unquantized Linear construction intervals explains most of the R26 non-MoE constructor residual. This remains temporal localization, not causal proof.

PR #244 remains open. No merge is implied or authorized.
