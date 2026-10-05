# Benchmark evidence index

This directory preserves canonical evidence for live DGX Spark runtime, profile-switch, host-stability, allocator, ownership, mitigation-discriminator, and userspace-localization experiments. Historical per-run documents remain immutable in meaning: later documents may add closure links, but must not rewrite what an earlier run actually observed.

## Current host-stability / RM allocator chain

Read the current closure in this order:

1. `orcarouter-managed-rmsys-r9-r22-allocator-closure-20261004.md`
2. `orcarouter-managed-rmsys-r23-early-burst-ownership-result-20261004.md`
3. `orcarouter-managed-rmsys-r23-ownership-closure-20261004.md`
4. `orcarouter-hybrid-r24-kv16-rm-mitigation-result-20261005.md`
5. `orcarouter-r25-load-phase-localization-result-20261005.md`
6. `orcarouter-r25b-init-model-boundary-result-20261005.md`
7. `orcarouter-r26-construction-boundary-result-20261005.md`
8. `orcarouter-r27-linear-residual-result-20261005.md`
9. `orcarouter-r27-h6-quant-routing-inspection-result-20261005.md`
10. `orcarouter-r28-unquant-linear-boundary-result-20261005.md`
11. `orcarouter-r28b-unquant-call-pattern-result-20261005.md`
12. `orcarouter-r29-global-rm-chunk-cadence-plan-20261005.md`

Supporting gate history remains canonical:

- `orcarouter-r25b-init-model-boundary-plan-20261005.md`
- `orcarouter-r25b-init-model-image-preflight-result-20261005.md`
- `orcarouter-r25b-live-harness-preflight-result-20261005.md`
- `orcarouter-r25b-live-attempt01-probe-group-invalid-20261005.md`
- `orcarouter-r25b-recovery-corrected-preflight-result-20261005.md`
- `orcarouter-r26-construction-boundary-plan-20261005.md`
- `orcarouter-r26-construction-image-preflight-result-20261005.md`
- `orcarouter-r26-live-harness-preflight-result-20261005.md`
- `orcarouter-r27-linear-residual-plan-20261005.md`
- `orcarouter-r27-linear-image-preflight-result-20261005.md`
- `orcarouter-r27-live-harness-preflight-result-20261005.md`
- `orcarouter-r27-h6-quant-routing-inspection-plan-20261005.md`
- `orcarouter-r28-unquant-linear-boundary-plan-20261005.md`
- `orcarouter-r28-repository-gate-result-20261005.md`
- `orcarouter-r28-unquant-linear-image-preflight-result-20261005.md`
- `orcarouter-r28-unquant-linear-live-harness-preflight-result-20261005.md`
- `orcarouter-r28b-unquant-call-pattern-plan-20261005.md`

Strict classification policy remains:

> Any confirmed `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` in a valid measured run is HOST-STABILITY FAIL even if fallback recovers and the runtime reaches READY.

FUNCTIONAL and HOST-STABILITY classifications remain separate. RM logical requested bytes are allocation activity volume, not exact resident ownership. Userspace marker alignment is temporal localization, not causal proof.

## R9–R23 — allocator / ownership closure

R11 closes the lower-level mechanism to node0 Normal-zone Unmovable order-4 demand, Movable fallback/pageblock stealing, failed high-order acquisition, rollback, and immediate order-0 retry.

R21/R22 establish a common early physical-page burst of about 75 GiB over roughly five seconds. mmap materially reduces later PLE swap/residency pressure but does not remove the common early burst or strict RM failure.

R23 closes the observed driver-level endpoint to direct NVIDIA RM system-memory allocation (`nv_alloc_pages` / `nv_alloc_system_pages`) rather than selected UVM allocation boundaries. Same-window 64 KiB RM activity is `74537.938 MiB` versus `75083.652 MiB` residual growth (`99.273191%`); selected UVM coverage is `0.000000%`.

Broad watermark/compaction/drop-cache/swap/static-high-order-state tuning was rejected as a deterministic production fix. Conditioning remains a measurement control.

## R24 — H6 W4A16 mitigation discriminator

R24 is **VALID_RM_OOM — FUNCTIONAL PASS / HOST-STABILITY FAIL — H6 NO RM MITIGATION**.

Under R22-matched v0.29 PLE-mmap/exact-QSA controls and forced 16 GiB KV:

- largest five-second residual: `77937.680 MiB`;
- R22 ratio: `103.725991%`;
- same-window order-4 RM activity: `77405.938 MiB`;
- strict RM OOM count: `1`;
- burst band: `BURST_UNCHANGED`.

## R25 / R25b — model-load localization

R25 showed the RM order-4 episode lasts only about `3.217673 s` while checkpoint filling continues for hundreds of seconds.

R25b then closed the exact first `initialize_model()` boundary:

- total order-4 RM activity: `77405.938 MiB`;
- before selected init: `559.688 MiB`;
- inside init: `76846.250 MiB`;
- after init: `0.000 MiB`;
- inside fraction: `99.276945%`;
- discriminator: `RM_ORDER4_STARTS_BEFORE_INITIALIZE_MODEL`.

Attempt 01 remains permanently SETUP INVALID. Attempt 02 is the valid measurement.

## R26 — constructor / ModelOpt-MoE split

R26 is **COMPLETED — VALID_MEASURED — FUNCTIONAL PASS / HOST-STABILITY FAIL**.

- order-4 calls/activity: `526` / `77405.938 MiB`;
- strict RM OOM count: `2`;
- before constructor: `559.688 MiB`;
- inside constructor: `76846.250 MiB` (`99.276945%`);
- after constructor: `0.000 MiB`;
- ModelOpt-MoE create-weights: `34292.000 MiB`;
- packed w13+w2: `29976.000 MiB`;
- constructor activity outside ModelOpt-MoE: `42554.250 MiB`.

Final discriminator:

`RM_ORDER4_MIXED_WITHIN_MODEL_CONSTRUCTOR`

## R27 — exact Qwen4Exp residual localization

R27 is **COMPLETED — VALID_MEASURED — FUNCTIONAL PASS / HOST-STABILITY FAIL**.

The matched mechanism reproduced unchanged:

- largest five-second residual: `77858.105 MiB`;
- R22 ratio: `103.620087%`;
- order-4 calls/activity: `526` / `77405.938 MiB`;
- strict RM OOM count: `2`;
- R26 residual outside ModelOpt-MoE: `42554.250 MiB`.

The proposed ordinary dense ModelOpt-W4A16 explanation was rejected by direct runtime observation:

```text
w4a16_linear.marker_pair_count_total=0
w4a16_linear.selected_call_count=0
w4a16_linear.activity_mib=0.000
w4a16_linear.pct_of_r26_residual=0.000000
```

Qwen4Exp decoder-layer localization:

- selected layers: `48`;
- decoder-layer RM activity: `73440.250 MiB`;
- decoder-layer fraction of constructor: `95.567773%`;
- constructor outside selected layers: `3406.000 MiB`;
- linear-attention non-MoE: `20150.250 MiB`;
- qwen sparse/full-attention non-MoE: `18998.000 MiB`;
- selected-layer non-MoE sum: `39148.250 MiB` = `91.996099%` of the R26 residual.

Final discriminator:

`RM_ORDER4_R26_RESIDUAL_MIXED_WITHIN_QWEN4_LAYERS`

Managed restoration returned exact OrcaRouter READY after `832 s`; final command RC was zero.

## R27 routing closure — why W4A16 dense markers were absent

Canonical:

- `orcarouter-r27-h6-quant-routing-inspection-plan-20261005.md`
- `orcarouter-r27-h6-quant-routing-inspection-result-20261005.md`

The completed read-only inspection is **PASS** and did not restart the model, mutate the service, launch a GPU model, or create an RM trace.

H6 remained the intended config-only W4A16 control:

```text
manifest.variant=h6-modelopt-w4a16
manifest.quant_algo_before=NVFP4
manifest.quant_algo_after=W4A16_NVFP4
manifest.safetensor_bytes_changed=0
quant.quant_method=modelopt
quant.quant_algo=W4A16_NVFP4
```

The inherited ignore list includes `*.self_attn.*` and `*.linear_attn.*`, with approximate checkpoint-prefix counts `117` and `252` respectively, plus broad shared-expert/router, hyper-connection, PLE, MTP, visual, embedding and lm-head exclusions.

Exact source checks passed:

```text
linear_none_selects_unquantized=PASS
modelopt_exclusion_selects_unquantized=PASS
modelopt_w4a16_class_selection_exists=PASS
qwen4_modelopt_fp4_optout_helper=PASS
qsa_qkv_uses_modelopt_fp4_optout=PASS
```

Therefore R27's zero W4A16-linear calls are treated as a real routing result, not a marker failure. The relevant decoder attention families route through `UnquantizedLinearMethod`, with an additional explicit QSA qkv ModelOpt-FP4 opt-out.

## R28 — unquantized Linear boundary

R28 is **COMPLETED — VALID_MEASURED — FUNCTIONAL PASS / HOST-STABILITY PASS — BURST_UNCHANGED**.

Canonical:

- `orcarouter-r28-unquant-linear-boundary-plan-20261005.md`
- `orcarouter-r28-repository-gate-result-20261005.md`
- `orcarouter-r28-unquant-linear-image-preflight-result-20261005.md`
- `orcarouter-r28-unquant-linear-live-harness-preflight-result-20261005.md`
- `orcarouter-r28-unquant-linear-boundary-result-20261005.md`

Matched mechanism:

- order-4 calls/activity: `526` / `77405.938 MiB`;
- largest five-second residual: `77923.969 MiB`;
- R22 ratio: `103.707743%`;
- strict RM OOM count: `0`;
- burst band: `BURST_UNCHANGED`.

The clean host-stability classification does not promote H6 to a mitigation: the structural burst remained unchanged.

R28 localization:

- R26 residual outside ModelOpt-MoE: `42554.375 MiB`;
- unquantized Linear overlap: `36752.000 MiB`;
- coverage: `86.364798%`;
- uncovered residual: `5802.375 MiB`;
- nominal unquantized payload: `7879.477 MiB`.

Family activity:

```text
hyper_connection=25600 MiB
self_attn=8928 MiB
linear_attn=820 MiB
other=1374 MiB
ple=30 MiB
shared_expert=0 MiB
router=0 MiB
```

Final discriminator:

`RM_ORDER4_R26_RESIDUAL_MIXED_OUTSIDE_UNQUANTIZED_LINEAR_CONSTRUCTION`

## R28b — sparse per-call RM pattern closure

R28b is **COMPLETED — READ-ONLY POST-HOC PASS**.

Canonical:

- `orcarouter-r28b-unquant-call-pattern-plan-20261005.md`
- `orcarouter-r28b-unquant-call-pattern-result-20261005.md`

Across 678 selected unquantized Linear calls:

- RM-positive: `56` (`8.259587%`);
- RM-zero: `622`;
- positive request histogram: `20 MiB x9`, `30 MiB x1`, `128 MiB x1`, `800 MiB x44`, `1214 MiB x1`;
- payload/RM Pearson: `0.149977822` overall, `-0.035821511` positive-only.

Hyper-connection specifically:

- calls: `194`;
- positive: `32`;
- zero: `162`;
- positive request size: exactly `800 MiB x32`;
- RM activity: `25600 MiB`;
- nominal payload: `1242.500 MiB`.

The same `800 MiB` size appears in other model families and four times in the uncovered R26 residual. The uncovered residual also contains another `1214 MiB` event.

Final discriminator:

`R28B_HYPER_CONNECTION_RM_ACTIVITY_SPARSE_ACROSS_CALLS`

This demotes another model-component marker split. The next discriminator should test the entire constructor RM stream for repeated large chunks spanning multiple inherited boundaries.

## R29 — global RM chunk cadence

R29 is **IMPLEMENTED — READ-ONLY POST-HOC ONLY — CI REQUIRED — NO LIVE RUN AUTHORIZED**.

Canonical plan:

- `orcarouter-r29-global-rm-chunk-cadence-plan-20261005.md`

Analyzer:

- `scripts/benchmark/analyze-orcarouter-r29-global-rm-chunk-cadence.py`

R29 uses only preserved R28 evidence and classifies the full selected-constructor order-4 request stream against:

- R26 ModelOpt-MoE intervals;
- R27 Qwen4Exp layer intervals;
- R28 unquantized Linear intervals;
- other constructor regions.

Repeated large requests are discovered from the data (`>=256 MiB`, count >=2) and compared by region, layer type, interarrival timing and intervening request count.

No Docker launch, model restart, new image, kprobe mutation, or evidence mutation is authorized. H11 remains deferred.

PR #244 remains intentionally open and must not be merged before mitigation/Hybrid closure and explicit merge timing.
