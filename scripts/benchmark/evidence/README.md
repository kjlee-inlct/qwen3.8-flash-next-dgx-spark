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
10. `orcarouter-r28-unquant-linear-boundary-plan-20261005.md`

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

R28 is implemented in the repository but **not authorized for a live run yet**.

Files:

- `../patch-v029-r28-unquant-linear-markers.py`
- `../Dockerfile.v029-r28-unquant-linear-markers`
- `../benchmark/check-orcarouter-r28-unquant-linear-image.sh`
- `../benchmark/analyze-orcarouter-r28-unquant-linear-overlap.py`
- `../benchmark/run-orcarouter-r28-unquant-linear-boundary.sh`
- `orcarouter-r28-unquant-linear-boundary-plan-20261005.md`

R28 narrows the next question to `UnquantizedLinearMethod.create_weights()` only. It keeps direct-RM activity and nominal `torch.empty` weight payload as separate quantities, aggregates overlap by exact prefix family, and preserves the inherited R26/R27 boundaries.

Required next gates are repository CI, marker-image build/static preflight, managed non-mutation verification, and guarded harness preflight. Only after those close PASS may one live R28 measurement be considered.

Do not repeat R27, do not apply H11 yet, and do not broaden kernel tracing.

PR #244 remains intentionally open and must not be merged before mitigation/Hybrid closure and explicit merge timing.
