# OrcaRouter R26 — model-construction / ModelOpt-MoE RM boundary plan — 2026-10-05

## Status

**COMPLETED — VALID_MEASURED — FUNCTIONAL PASS / HOST-STABILITY FAIL — `RM_ORDER4_MIXED_WITHIN_MODEL_CONSTRUCTOR`**

Canonical result:

- `scripts/benchmark/evidence/orcarouter-r26-construction-boundary-result-20261005.md`

R25b had localized `76,846.250 MiB` of `77,405.938 MiB` total 64 KiB direct-NVIDIA-RM order-4 activity (`99.276945%`) inside the first `initialize_model()` interval, with `559.688 MiB` before the marker and `0.000 MiB` after it. R26 moved inward observationally and split that constructor interval into top-level construction, ModelOpt NVFP4 routed-expert creation, and packed w13/w2 allocation boundaries.

R26 did not alter parameter classes, tensor shapes, dtypes, quantization behavior, allocator behavior, runtime flags, PLE mmap, exact QSA, KV size, model length, speculative decode, or VM policy.

## Question

Within the first `initialize_model()` call, is the approximately 76.8 GiB main RM burst concentrated in:

1. the top-level vLLM model constructor;
2. `ModelOptNvFp4FusedMoE.create_weights()` for routed experts; and, if so,
3. the large packed `w13_weight` / `w2_weight` storage allocations specifically?

This was a localization discriminator, not a mitigation test.

## Pinned vLLM v0.29 path

The v0.29 model-loader `initialize_model()` resolves/configures the model class and executes the new-style constructor:

`model = model_class(vllm_config=vllm_config, prefix=prefix)`

inside `set_current_vllm_config(...)`.

The H6 matched-control checkpoint declares `W4A16_NVFP4`. vLLM v0.29 routes NVFP4 MoE construction through `ModelOptNvFp4FusedMoE.create_weights()`, which creates routed-expert `w13_weight` and `w2_weight` `ModelWeightParameter` objects from `torch.empty(...)` before scales/metadata.

## Diagnostic implementation

Repository components:

- `scripts/patch-v029-r26-construction-markers.py`
- `scripts/Dockerfile.v029-r26-construction-markers`
- `scripts/benchmark/check-orcarouter-r26-construction-image.sh`
- `scripts/benchmark/analyze-orcarouter-r26-construction-overlap.py`
- `scripts/benchmark/run-orcarouter-r26-construction-boundary.sh`

Image:

`vllm-orcarouter-v029-r26-construction-marker:v1`

Built image id:

`sha256:568d0ac6917b324eef6c29e5f06b0a1ba182b5db043052b13296fe7d3c5428aa`

The image derives from `vllm-orcarouter-v029-r25-init-marker:v1`, preserving the outer R25 `QWEN38_R25_INIT_MODEL_BEGIN/END` markers.

R26 adds INFO markers around:

- top-level new-style `model_class(...)` constructor begin/end;
- `ModelOptNvFp4FusedMoE.create_weights()` begin/end with a process-local sequence number;
- `w13_weight` allocation begin/end;
- `w2_weight` allocation begin/end.

## Static image gate — CLOSED / PASS

Canonical result:

- `scripts/benchmark/evidence/orcarouter-r26-construction-image-preflight-result-20261005.md`

Observed DGX result:

```text
R26_BUILD_RC=0
r25_inherited_marker_contract=PASS
r26_model_constructor_contract=PASS
r26_modelopt_moe_contract=PASS
R26_IMAGE_PREFLIGHT=PASS
R26_STATIC_PREFLIGHT_RC=0
R26_BUILD_AND_STATIC_PREFLIGHT=PASS
```

Managed service remained active and exact container ID `e5422a909bf4e9b8c84bfa1a864b9ddeedac4686de5c449eb6aaf0a645add2cd` plus `StartedAt=2026-10-05T05:42:55.476327457Z` were unchanged before/after. Exact served identity remained `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`, `max_model_len=262144`.

## Harness preflight gate — CLOSED / PASS

Canonical result:

- `scripts/benchmark/evidence/orcarouter-r26-live-harness-preflight-result-20261005.md`

Observed preflight:

```text
stale_probe_groups=NONE
r25_inherited_marker_contract=PASS
r26_model_constructor_contract=PASS
r26_modelopt_moe_contract=PASS
R26_IMAGE_PREFLIGHT=PASS
r26_probe_definition_contract=PASS
R24_PREFLIGHT=PASS
R26_LIVE_PREFLIGHT=PASS
predecessor_age_s=9373.825
minimum_predecessor_age_s=2700
predecessor_age_ok=1
rm_probe_target_count=2
R26_HARNESS_PREFLIGHT_RC=0
R26_HARNESS_PREFLIGHT_AND_NONMUTATION=PASS
```

Matched-control identity remained H6 ModelOpt W4A16 with forced `17179869184`-byte KV and the same narrow RM probe targets.

## Live measured run — CLOSED / VALID

The single authorized live run used repository head:

`fd71744f9663b6dd29d09abfdd00cf4d3b8254a2`

Final validity/classification:

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
ORCA_R24_RESULT=VALID_RM_OOM
ORCA_R26_RESULT=VALID_MEASURED
R26_COMMAND_RC=0
```

Two strict `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` events were observed, so HOST-STABILITY remains FAIL even though functional readiness and restoration succeeded.

The matched burst remained unchanged:

```text
baseline.r22_largest_5s_residual_mib=75138.043
candidate.largest_5s.delta_mib=+77940.164
candidate_to_r22_burst_pct=103.729297
candidate_burst_reduction_pct=-3.729297
burst_band=BURST_UNCHANGED
nv_alloc_pages.order4_calls.total=526
nv_alloc_pages.order4_activity_mib.total=77405.938
```

H6 therefore remains rejected as a host-stability mitigation.

## R26 localization result

Top-level constructor alignment:

```text
clock_offset_spread_ms=5.052328
classification_tolerance_s=0.025000
model_ctor.duration_s=3.130943
rm_order4.total_activity_mib=77405.938
rm_order4.before_model_ctor_activity_mib=559.688
rm_order4.inside_model_ctor_activity_mib=76846.250
rm_order4.after_model_ctor_activity_mib=0.000
rm_order4.inside_model_ctor_pct=99.276945
```

This reproduces R25b at the tighter constructor boundary: the primary burst is model construction, not later checkpoint filling.

ModelOpt-MoE contribution:

```text
modelopt_moe.marker_pair_count_total=48
modelopt_moe.selected_call_count=48
modelopt_moe.activity_mib=34292.000
modelopt_moe.pct_of_total=44.301511
modelopt_moe.pct_of_model_ctor=44.624168
```

Packed expert allocation split:

```text
modelopt_w13.activity_mib=19200.000
modelopt_w2.activity_mib=10776.000
modelopt_packed_w13_w2.activity_mib=29976.000
modelopt_packed_w13_w2.pct_of_total=38.725711
modelopt_packed_w13_w2.pct_of_modelopt_moe=87.413974
modelopt_moe_nonpacked.activity_mib=4316.000
```

Residual constructor activity outside ModelOpt-MoE:

```text
model_ctor_outside_modelopt_moe.activity_mib=42554.250
```

Final discriminator:

`RM_ORDER4_MIXED_WITHIN_MODEL_CONSTRUCTOR`

## Interpretation

R26 answers the original question as follows:

1. **Yes** — the main episode remains almost entirely inside top-level model construction (`99.276945%`).
2. **No** — ModelOpt routed-expert `create_weights()` is not the dominant explanation of the whole episode (`44.301511%` of total).
3. **Within the ModelOpt-MoE contribution, yes** — packed w13+w2 intervals explain `87.413974%` of ModelOpt-MoE activity, but only `38.725711%` of total activity.
4. A larger `42554.250 MiB` constructor component remains outside ModelOpt-MoE.

Therefore the R26 plan's low-MoE-coverage branch is taken: **do not apply H11 yet**. H11 may affect a meaningful ~30 GiB expert-storage component, but it cannot currently explain the larger residual constructor activity and would confound localization if applied now.

RM bytes remain allocation activity volume rather than exact resident ownership. Marker overlap remains temporal localization rather than causal proof.

## Managed restoration — CLOSED / PASS

The wrapper reported:

`managed_restore_ready_rc=0`

The managed runtime returned READY after `879 s` with exact identity:

- `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`
- `max_model_len=262144`

A final independent readiness check returned READY immediately and the service was active.

## Next discriminator

Do not repeat H6 or R26, do not apply H11 yet, and do not broaden kernel/VM tracing.

The next observational discriminator should partition the `42554.250 MiB` constructor activity outside ModelOpt-MoE. Highest-information boundaries are:

- ModelOpt W4A16 linear `create_weights()` allocations outside routed experts;
- Qwen3Next layer-family construction boundaries (linear-attention/full-attention and other non-expert components);
- the matched PLE / N-gram embedding construction or mmap boundary if source inspection confirms it is entered inside the selected constructor interval.

Before another live run, inspect the exact pinned PLE/N-gram construction path and add only the minimum stable INFO markers required to account for this residual. Keep the `559.688 MiB` pre-constructor precursor separate.

## Gate sequence

1. repository CI — **CLOSED / PASS**;
2. R26 image build — **CLOSED / PASS**;
3. static R26 image contract — **CLOSED / PASS**;
4. static managed non-mutation — **CLOSED / PASS**;
5. canonical static result — **CLOSED / PASS**;
6. guarded R26 harness preflight — **CLOSED / PASS**;
7. harness managed non-mutation — **CLOSED / PASS**;
8. canonical harness-preflight result — **CLOSED / PASS**;
9. one guarded R26 live measured run — **CLOSED / VALID_MEASURED**;
10. canonical R26 live result — **CLOSED / PASS**;
11. next residual-constructor discriminator — **NEXT**.

PR #244 remains open. No merge is implied or authorized.
