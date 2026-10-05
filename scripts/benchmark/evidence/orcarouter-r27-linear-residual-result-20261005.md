# OrcaRouter R27 — W4A16-linear / Qwen4Exp residual result — 2026-10-05

## Status

**COMPLETED — VALID_MEASURED — FUNCTIONAL PASS / HOST-STABILITY FAIL**

Final discriminator:

`RM_ORDER4_R26_RESIDUAL_MIXED_WITHIN_QWEN4_LAYERS`

R27 completed the one authorized live measurement. The matched harness, R27 analyzer, exact managed restoration, and final command all returned success. RM logical bytes remain allocation activity volume, not exact resident ownership; marker overlap remains temporal localization, not causal proof.

## Identity and validity

Repository head: `30120d9a60edf153352c1b79a9739fc53c945be8`

Candidate image: `vllm-orcarouter-v029-r27-linear-marker:v1`

Evidence: `/tmp/orcarouter-hybrid-r27-linear-boundary-01-20261005`

Console: `/tmp/r27-live-20261005-195030.log`

Live prerequisites passed:

```text
stale_probe_groups=NONE
r26_inherited_constructor_contract=PASS
r26_inherited_modelopt_moe_contract=PASS
r27_w4a16_linear_contract=PASS
r27_qwen4_layer_contract=PASS
r27_ple_mmap_placeholder_contract=PASS
R27_IMAGE_PREFLIGHT=PASS
r27_probe_definition_contract=PASS
predecessor_age_s=6913.870
minimum_predecessor_age_s=2700
predecessor_age_ok=1
rm_probe_target_count=2
R24_PREFLIGHT=PASS
R27_LIVE_PREFLIGHT=PASS
R27_LIVE_GATE=OPEN
```

Matched-run validity:

```text
run_valid=1
candidate_start_rc=0
collector_rc=0
trace_rc=0
trace_report_rc=0
analyzer_rc=0
wait_ready_rc=0
api_ready=1
protected_stop=0
trace_window_valid=1
candidate_identity_valid=1
functional_class=PASS
host_stability_class=FAIL
rm_oom_count=2
event_snapshot_count=2
```

Underlying result: `ORCA_R24_RESULT=VALID_RM_OOM`.

## Matched mechanism

```text
candidate.largest_5s.delta_mib=+77858.105
candidate_to_r22_burst_pct=103.620087
candidate_burst_reduction_pct=-3.620087
burst_band=BURST_UNCHANGED
nv_alloc_pages.order4_calls.total=526
nv_alloc_pages.order4_activity_mib.total=77405.938
strict_rm_oom_count=2
```

Two valid-run `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` events were captured. Strict project policy therefore keeps **HOST-STABILITY FAIL** independently of functional recovery.

## Constructor and R26 split

```text
clock_offset_spread_ms=30.171394
classification_tolerance_s=0.060343
model_ctor.duration_s=3.179674
rm_order4.total_activity_mib=77405.938
rm_order4.before_model_ctor_activity_mib=559.688
rm_order4.inside_model_ctor_activity_mib=76846.250
rm_order4.after_model_ctor_activity_mib=0.000
rm_order4.inside_model_ctor_pct=99.276945
r26_modelopt_moe.activity_mib=34292.000
r26_modelopt_moe.pct_of_total=44.301511
r26_residual_outside_moe.activity_mib=42554.250
```

The R25b/R26 constructor localization and R26 residual reproduce exactly.

## W4A16-linear result

```text
w4a16_linear.marker_pair_count_total=0
w4a16_linear.selected_call_count=0
w4a16_linear.activity_mib=0.000
w4a16_linear.pct_of_r26_residual=0.000000
w4a16_weight.activity_mib=0.000
```

The static image contract had already verified the R27 marker code inside `ModelOptNvFp4W4A16LinearMethod.create_weights()`, while Qwen4Exp layer markers from the same candidate log were observed normally. The measured result is therefore that this specific dense W4A16 method was not selected during the primary constructor.

This does **not** mean no dense linear weights were allocated; it means the assumed W4A16 implementation did not own them.

## Qwen4Exp layer localization

```text
qwen4_layer.marker_pair_count_total=49
qwen4_layer.selected_layer_count=48
qwen4_layer.activity_mib=73440.250
qwen4_layer.pct_of_model_ctor=95.567773
model_ctor_outside_qwen4_layers.activity_mib=3406.000
```

Layer-type non-MoE activity:

```text
linear_attention.non_moe_activity_mib=20150.250
qwen_sparse_attention.non_moe_activity_mib=18998.000
```

Together these equal `39148.250 MiB`, approximately `91.996099%` of the R26 `42554.250 MiB` residual. Only about `8.003901%` of that residual remains outside selected Qwen4 decoder layers.

The non-MoE layer residual is nearly balanced between linear attention (`51.471649%`) and qwen-sparse attention (`48.528351%`), so neither layer type alone explains it.

Largest observed non-MoE intervals include layer 3 qwen-sparse-attention at `2198.000 MiB`, layer 1 linear-attention at `1730.250 MiB`, and repeated qwen-sparse-attention layers at `1600.000 MiB`.

## Interpretation

R27 decisively rejects the proposed branch that ordinary `ModelOptNvFp4W4A16LinearMethod.create_weights()` explains the R26 residual. The correct remaining scope is inside Qwen4 decoder-layer construction.

H6 is a config-only control: tensor bytes remain unchanged and only `quant_algo` is changed. That does not guarantee every dense module selects the W4A16 ModelOpt method. vLLM can select `UnquantizedLinearMethod` when `quant_config` is absent or a module is excluded, and Qwen4Exp also explicitly removes ModelOpt-FP4 quantization from selected paths such as QSA `qkv_proj`.

The next discriminator must therefore observe actual per-linear routing rather than guessing a specific quant class.

## Restoration

```text
managed_restore_ready_rc=0
READY after 832s
id=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4
max_model_len=262144
```

Final independent check returned service active and exact model READY.

Final tokens:

```text
ORCA_R27_RESULT=VALID_MEASURED
R27_COMMAND_RC=0
```

## Next action

Do not repeat R27 and do not apply H11 yet.

First perform a read-only H6 quantization-routing inspection of `config.json`, ignore/exclude patterns, and checkpoint index. If another live discriminator is needed, R28 should instrument generic `LinearBase` create-weights dispatch by actual prefix, LinearBase subclass, selected `quant_method.__class__.__name__`, dimensions, and dtype.

PR #244 remains open. No merge is implied or authorized.
