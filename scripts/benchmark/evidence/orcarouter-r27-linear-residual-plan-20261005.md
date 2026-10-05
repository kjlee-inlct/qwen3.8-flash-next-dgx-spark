# OrcaRouter R27 — W4A16-linear / Qwen4Exp residual-constructor plan — 2026-10-05

## Status

**COMPLETED — VALID_MEASURED — FUNCTIONAL PASS / HOST-STABILITY FAIL — `RM_ORDER4_R26_RESIDUAL_MIXED_WITHIN_QWEN4_LAYERS`**

Canonical sequence:

- `scripts/benchmark/evidence/orcarouter-r26-construction-boundary-result-20261005.md`
- `scripts/benchmark/evidence/orcarouter-r27-linear-image-preflight-result-20261005.md`
- `scripts/benchmark/evidence/orcarouter-r27-live-harness-preflight-result-20261005.md`
- `scripts/benchmark/evidence/orcarouter-r27-linear-residual-result-20261005.md`

R27 has no remaining live authorization. The one authorized measurement was consumed and completed validly.

## Closed prerequisite gates

Repository CI, marker-only image build, static image contract, managed non-mutation, guarded harness preflight, exact four-probe transform, stale-probe guard, predecessor-age gate, and managed restoration all closed PASS.

Diagnostic image:

`vllm-orcarouter-v029-r27-linear-marker:v1`

Image id:

`sha256:e9e92c5cb98d443a8410f21345cb0e07c30c9e7c84516cedcc2a6dc213934119`

Live evidence:

`/tmp/orcarouter-hybrid-r27-linear-boundary-01-20261005`

## Valid-run classification

```text
run_valid=1
functional_class=PASS
host_stability_class=FAIL
rm_oom_count=2
event_snapshot_count=2
ORCA_R24_RESULT=VALID_RM_OOM
ORCA_R27_RESULT=VALID_MEASURED
R27_COMMAND_RC=0
```

Strict project policy remains unchanged: any valid-run NVIDIA RM `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` event is HOST-STABILITY FAIL even if fallback and managed restoration succeed.

## Matched mechanism

R27 reproduced the same H6/R22 mechanism:

```text
candidate.largest_5s.delta_mib=+77858.105
candidate_to_r22_burst_pct=103.620087
candidate_burst_reduction_pct=-3.620087
burst_band=BURST_UNCHANGED
nv_alloc_pages.order4_calls.total=526
nv_alloc_pages.order4_activity_mib.total=77405.938
```

H6 therefore remains **NO RM MITIGATION**.

## Constructor / R26 residual reproduction

```text
rm_order4.before_model_ctor_activity_mib=559.688
rm_order4.inside_model_ctor_activity_mib=76846.250
rm_order4.after_model_ctor_activity_mib=0.000
rm_order4.inside_model_ctor_pct=99.276945
r26_modelopt_moe.activity_mib=34292.000
r26_residual_outside_moe.activity_mib=42554.250
```

R27 preserved the R25b/R26 localization exactly.

## Primary R27 result

The intended dense ModelOpt-W4A16 path was not invoked:

```text
w4a16_linear.marker_pair_count_total=0
w4a16_linear.selected_call_count=0
w4a16_linear.activity_mib=0.000
w4a16_linear.pct_of_r26_residual=0.000000
w4a16_weight.activity_mib=0.000
```

The static checker had already proved the markers were installed in `ModelOptNvFp4W4A16LinearMethod.create_weights()`. Qwen4Exp layer markers from the same candidate process were observed. Therefore the correct result is that this specific quant method was not selected during the primary constructor, not that dense linear allocation was absent.

## Qwen4Exp layer localization

```text
qwen4_layer.selected_layer_count=48
qwen4_layer.activity_mib=73440.250
qwen4_layer.pct_of_model_ctor=95.567773
model_ctor_outside_qwen4_layers.activity_mib=3406.000
```

Non-MoE layer activity:

```text
linear_attention = 20150.250 MiB
qwen_sparse_attention = 18998.000 MiB
sum = 39148.250 MiB
```

The sum is `91.996099%` of the R26 `42554.250 MiB` residual. Only `8.003901%` remains outside the selected Qwen4 decoder layers.

The decoder-layer non-MoE split is nearly balanced:

- linear attention: `51.471649%`;
- qwen sparse attention: `48.528351%`.

Final discriminator:

`RM_ORDER4_R26_RESIDUAL_MIXED_WITHIN_QWEN4_LAYERS`

## Source-level implication

H6 changes only the checkpoint `quant_algo` to `W4A16_NVFP4`; it does not force every dense module to use `ModelOptNvFp4W4A16LinearMethod`.

In vLLM v0.29, `LinearBase` uses `UnquantizedLinearMethod` when `quant_config is None`, and ModelOpt exclusions can also return the unquantized method. Qwen4Exp explicitly removes ModelOpt-FP4 quantization from selected subpaths such as QSA `qkv_proj` through `without_modelopt_fp4(...)`.

The next step must inspect actual quantization routing rather than assume another dense quant class.

## Managed restoration

Exact managed OrcaRouter returned READY after `832 s`:

```text
id=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4
max_model_len=262144
```

Managed restoration is CLOSED/PASS.

## Next action

1. Perform a **read-only H6 quantization-routing inspection** of `config.json`, ModelOpt ignore/exclude rules, and checkpoint index. No model restart.
2. Record the inspection result canonically.
3. Only if the config/source inspection cannot close the routing question, create R28 as a marker-only generic `LinearBase` dispatcher measurement. R28 should log actual prefix, LinearBase subclass, selected `quant_method.__class__.__name__`, dimensions/dtype, and create-weights begin/end intervals.
4. Do not repeat R27, do not apply H11 yet, and do not broaden kernel tracing.

PR #244 remains open. No merge is implied or authorized.
