# OrcaRouter R26 — model-construction / ModelOpt-MoE RM boundary result — 2026-10-05

## Status

**COMPLETED — VALID_MEASURED — FUNCTIONAL PASS / HOST-STABILITY FAIL — MIXED WITHIN MODEL CONSTRUCTOR**

R26 completed one guarded live measured run after both prerequisite gates had closed PASS. The run was valid, the marker/RM trace was complete, managed restoration returned the exact OrcaRouter model to READY, and the final command returned zero.

The main result is that the approximately 75–77 GiB direct-NVIDIA-RM order-4 episode remains almost entirely inside the first top-level model constructor, but it is **not dominated by `ModelOptNvFp4FusedMoE.create_weights()`**. ModelOpt routed-expert construction accounts for about 44.3% of total RM activity, while about 42.55 GiB remains elsewhere in the constructor.

The strict R26 discriminator is:

`RM_ORDER4_MIXED_WITHIN_MODEL_CONSTRUCTOR`

This is temporal localization, not causal proof. RM logical bytes are allocation activity volume, not exact resident ownership.

## Repository / candidate identity

The DGX live command pinned repository head:

`fd71744f9663b6dd29d09abfdd00cf4d3b8254a2`

Candidate image:

- tag: `vllm-orcarouter-v029-r26-construction-marker:v1`
- image id: `sha256:568d0ac6917b324eef6c29e5f06b0a1ba182b5db043052b13296fe7d3c5428aa`
- stability label: `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`
- inherited R25 label: `init-model-boundary-v1`
- R26 label: `construction-boundary-v1`

Matched candidate configuration remained:

- profile: `orcarouter-hybrid`
- checkpoint: `models/qwen3.8-h6-modelopt-w4a16`
- forced KV bytes: `17179869184`
- preserved historical R24 evidence: `/tmp/orcarouter-hybrid-r24-kv16-rm-mitigation-01-20261004`
- R26 evidence: `/tmp/orcarouter-hybrid-r26-construction-boundary-01-20261005`
- experiment container: `qwen38-hybrid-r26-construction-marker`

## Live setup validity

The live gate revalidated all setup controls before candidate launch:

```text
stale_probe_groups=NONE
r25_inherited_marker_contract=PASS
r26_model_constructor_contract=PASS
r26_modelopt_moe_contract=PASS
R26_IMAGE_PREFLIGHT=PASS
r26_probe_definition_contract=PASS
predecessor_age_s=10694.992
minimum_predecessor_age_s=2700
predecessor_age_ok=1
rm_probe_target_count=2
R24_PREFLIGHT=PASS
R26_LIVE_PREFLIGHT=PASS
R26_LIVE_GATE=OPEN
```

The managed runtime was READY before the run with exact served identity:

`orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`

and `max_model_len=262144`.

Therefore this is not a setup-invalid attempt.

## Underlying R24-matched measurement validity

The inherited matched harness reported:

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
predecessor_age_s=10695.603
kv_bytes=17179869184
rm_oom_count=2
event_snapshot_count=2
```

The underlying result token was:

`ORCA_R24_RESULT=VALID_RM_OOM`

## Matched burst reproduction

R26 reproduced the already-closed H6/R22 mechanism rather than changing it:

```text
baseline.r22_largest_5s_residual_mib=75138.043
candidate.largest_1s.delta_mib=+26727.086
candidate.largest_5s.delta_mib=+77940.164
candidate_to_r22_burst_pct=103.729297
candidate_burst_reduction_pct=-3.729297
burst_band=BURST_UNCHANGED
trace_covers_burst5=1
```

Five-second allocator deltas:

```text
node0_normal_free_delta_mib=-78392.918
nr_free_pages_delta_mib=-78391.809
normal_unmovable_order4plus_mib=106658.188 -> 65984.750
normal_movable_order4plus_mib=8601.500 -> 8075.875
```

Narrow RM trace:

```text
event_count.nv_alloc_pages=575
event_count.nv_alloc_system_pages=538
nv_alloc_pages.order4_calls.total=526
nv_alloc_pages.order4_activity_mib.total=77405.938
nv_alloc_pages.order0_activity_mib.total=1.613
nv_alloc_pages.order4_calls.burst5=526
nv_alloc_pages.order4_activity_mib.burst5=77405.938
boundary.nv_alloc_pages.unmatched_entries=0
boundary.nv_alloc_pages.unmatched_returns=0
boundary.nv_alloc_system_pages.unmatched_entries=0
boundary.nv_alloc_system_pages.unmatched_returns=0
```

The H6 mitigation discriminator therefore remains:

`H6_NO_RM_MITIGATION_HOST_FAIL`

## Strict host-stability classification

Two strict NVIDIA RM OOM events were captured during the valid measured run:

```text
2026-10-05T17:52:50.281563+09:00 ... _memdescAllocInternal(pMemDesc) @ mem_desc.c:1359 ... NV_ERR_NO_MEMORY
2026-10-05T17:54:30.795318+09:00 ... _memdescAllocInternal(pMemDesc) @ mem_desc.c:1359 ... NV_ERR_NO_MEMORY
```

According to the project classification rule, any such event in a valid measured run is **HOST-STABILITY FAIL**, even though fallback/recovery allowed functional readiness.

Final classification:

- FUNCTIONAL: **PASS**
- HOST-STABILITY: **FAIL**
- strict RM OOM count: `2`

## R26 constructor localization

Clock alignment remained tight:

```text
clock_anchor_count=3
clock_offset_spread_ms=5.052328
classification_tolerance_s=0.025000
```

Selected top-level constructor interval:

```text
model_ctor.marker_pair_count=2
model_ctor.begin_monotonic=445060.867577076
model_ctor.end_monotonic=445063.998520136
model_ctor.duration_s=3.130943
```

RM episode:

```text
rm_order4.first_monotonic=445060.455400000
rm_order4.last_monotonic=445063.949211000
rm_order4.total_activity_mib=77405.938
rm_order4.before_model_ctor_activity_mib=559.688
rm_order4.inside_model_ctor_activity_mib=76846.250
rm_order4.after_model_ctor_activity_mib=0.000
rm_order4.inside_model_ctor_pct=99.276945
```

This exactly reproduces the R25b split at the tighter top-level constructor boundary:

- small precursor before constructor marker: `559.688 MiB`;
- main constructor activity: `76846.250 MiB`;
- activity after constructor return: `0.000 MiB`.

The main RM episode is therefore still a model-construction phenomenon.

## ModelOpt routed-expert split

R26 observed 48 ModelOpt-MoE `create_weights()` marker pairs and selected all 48 within the constructor interval:

```text
modelopt_moe.marker_pair_count_total=48
modelopt_moe.selected_call_count=48
modelopt_moe.activity_mib=34292.000
modelopt_moe.pct_of_total=44.301511
modelopt_moe.pct_of_model_ctor=44.624168
```

This is substantial, but it is far below the explicit 90% primary threshold. ModelOpt routed-expert construction is therefore **not the dominant owner of the full burst**.

The five largest individual ModelOpt-MoE calls were:

```text
seq=3  activity_mib=814.000 duration_s=0.050200
seq=47 activity_mib=752.000 duration_s=0.046376
seq=43 activity_mib=752.000 duration_s=0.046195
seq=39 activity_mib=752.000 duration_s=0.047000
seq=35 activity_mib=752.000 duration_s=0.046408
```

## Packed expert w13 / w2 split

Inside the ModelOpt-MoE intervals:

```text
modelopt_w13.activity_mib=19200.000
modelopt_w2.activity_mib=10776.000
modelopt_packed_w13_w2.activity_mib=29976.000
modelopt_packed_w13_w2.pct_of_total=38.725711
modelopt_packed_w13_w2.pct_of_modelopt_moe=87.413974
modelopt_moe_nonpacked.activity_mib=4316.000
```

Therefore the routed-expert contribution itself is mostly explained by the packed w13/w2 allocation boundaries: about 87.4% of ModelOpt-MoE RM activity occurs there.

That is useful evidence for expert storage materialization, but it still explains only about 38.7% of total order-4 activity.

## Remaining constructor activity

The key R26 discriminator is the residual constructor activity outside the selected ModelOpt-MoE intervals:

`model_ctor_outside_modelopt_moe.activity_mib=42554.250`

This approximately 42.55 GiB residual is larger than the 34.29 GiB ModelOpt-MoE contribution.

Accordingly:

`construction_discriminator=RM_ORDER4_MIXED_WITHIN_MODEL_CONSTRUCTOR`

The R26 plan explicitly required that H11 not be applied when constructor coverage remains high but ModelOpt-MoE coverage is low. R26 now satisfies that branch.

## Engineering interpretation

R26 closes the following points:

1. The main ~75–77 GiB RM episode remains localized to first-model construction.
2. ModelOpt NVFP4 routed experts are a major contributor, but not the primary explanation of the whole episode.
3. Within routed experts, packed w13/w2 storage allocation dominates the ModelOpt-MoE contribution.
4. A larger approximately 42.55 GiB component remains elsewhere in the constructor and must be localized before changing H11-like expert parameter semantics.
5. The existing ~559.688 MiB pre-constructor precursor remains separate and is not explained by R26.

Do **not** interpret cumulative RM requested bytes as exact resident ownership and do not infer that the approximately 42.55 GiB residual is a single allocation site without another boundary measurement.

## Managed restoration

The R26 wrapper reported:

```text
managed_restore_ready_rc=0
```

The managed OrcaRouter returned READY after `879 s` with exact identity:

```text
id=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4
max_model_len=262144
```

A final independent readiness check then returned READY immediately and the service was active.

Managed restoration is therefore **CLOSED / PASS**.

## Final tokens

```text
ORCA_R24_RESULT=VALID_RM_OOM
ORCA_R26_RESULT=VALID_MEASURED
R26_COMMAND_RC=0
```

## Next discriminator

Do not repeat R26, do not apply H11 yet, and do not broaden kernel tracing.

The next observational measurement should partition the approximately `42554.250 MiB` constructor activity outside ModelOpt-MoE into the smallest high-value constructor subpaths. The highest-priority candidates are:

- ModelOpt W4A16 linear `create_weights()` allocations outside routed experts;
- Qwen3Next layer-family construction boundaries (linear-attention vs full-attention / non-expert components);
- the PLE / N-gram embedding construction or mapping boundary used by the matched runtime, if it is inside the selected constructor interval.

The next marker design should first verify the exact active PLE/N-gram construction path in the pinned runtime source and then measure it together with non-MoE W4A16 linear construction. H11 remains deferred until this residual constructor component is localized.

PR #244 remains open. No merge is implied or authorized.
