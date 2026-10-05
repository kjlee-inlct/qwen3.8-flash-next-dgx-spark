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
8. `orcarouter-r27-linear-residual-plan-20261005.md`
9. `orcarouter-r27-linear-image-preflight-result-20261005.md`
10. `orcarouter-r27-live-harness-preflight-result-20261005.md`

Supporting R25b/R26 gate history remains canonical:

- `orcarouter-r25b-init-model-boundary-plan-20261005.md`
- `orcarouter-r25b-init-model-image-preflight-result-20261005.md`
- `orcarouter-r25b-live-harness-preflight-result-20261005.md`
- `orcarouter-r25b-live-attempt01-probe-group-invalid-20261005.md`
- `orcarouter-r25b-recovery-corrected-preflight-result-20261005.md`
- `orcarouter-r26-construction-boundary-plan-20261005.md`
- `orcarouter-r26-construction-image-preflight-result-20261005.md`
- `orcarouter-r26-live-harness-preflight-result-20261005.md`

Strict classification policy remains:

> Any confirmed `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` in a valid measured run is HOST-STABILITY FAIL even if fallback recovers and the runtime reaches READY.

FUNCTIONAL and HOST-STABILITY classifications must remain separate.

RM logical requested bytes remain allocation activity volume, not exact resident ownership. Userspace marker alignment remains temporal localization, not causal proof.

## R9–R23 allocator / ownership closure

R11 closes the lower-level mechanism to node0 Normal-zone Unmovable order-4 demand, Movable fallback/pageblock stealing, failed high-order acquisition, rollback, and immediate order-0 retry.

R21/R22 establish a common early physical-page burst of about 75 GiB over roughly five seconds. mmap materially reduces later PLE swap/residency pressure but does not remove the common early burst or strict RM failure.

R23 closes the observed driver-level endpoint to direct NVIDIA RM system-memory allocation (`nv_alloc_pages` / `nv_alloc_system_pages`) rather than the selected UVM allocation boundaries. In the independently selected R23 five-second window, 64 KiB RM activity is `74537.938 MiB` versus `75083.652 MiB` residual growth (`99.273191%`); selected UVM coverage is `0.000000%`.

Canonical lower-level evidence:

- `r9-acceptance-gate-20261002.md`
- `r9-rm-sysmem-root-cause-20261002.md`
- `orcarouter-managed-rmsys-r10b-02-rm-oom-20261003.md`
- `orcarouter-managed-rmsys-r11-allocator-state-20261003.md`
- `orcarouter-managed-rmsys-r21-pagecache-reclaim-result-20261004.md`
- `orcarouter-managed-rmsys-r22-v029-mmap-result-20261004.md`
- `orcarouter-managed-rmsys-r21-r22-mmap-comparison-20261004.md`
- `orcarouter-managed-rmsys-r23-early-burst-ownership-result-20261004.md`
- `orcarouter-managed-rmsys-r23-ownership-closure-20261004.md`

## Conditioning / rejected broad mitigations

Canonical conditioning experiments:

- `orcarouter-managed-rmsys-r12-precompact-20261003.md`
- `orcarouter-managed-rmsys-r13-proactive80-20261003.md`
- `orcarouter-managed-rmsys-r14-watermark100-20261003.md`
- `orcarouter-managed-rmsys-r14-watermark-comparison-20261003.md`
- `orcarouter-managed-rmsys-r15-paired-watermark-20261003.md`
- `orcarouter-managed-rmsys-r16-reverse-watermark-20261004.md`
- `orcarouter-managed-rmsys-r17-baseline-repeat-20261004.md`
- `orcarouter-managed-rmsys-r18-poststop-compact-20261004.md`
- `orcarouter-managed-rmsys-r19-stoponly-control-20261004.md`
- `orcarouter-managed-rmsys-r20-poststop-compact-invalid-20261004.md`

These collectively reject broad watermark/compaction/drop-cache/swap/static-high-order-state tuning as a deterministic production fix. Conditioning remains a measurement control.

## R24 — H6 W4A16 mitigation discriminator

Canonical:

- `orcarouter-hybrid-r24-kv16-rm-mitigation-plan-20261004.md`
- `orcarouter-hybrid-r24-kv16-rm-mitigation-result-20261005.md`

R24 is **VALID_RM_OOM — FUNCTIONAL PASS / HOST-STABILITY FAIL — H6 NO RM MITIGATION**.

Under R22-matched v0.29 PLE-mmap/exact-QSA controls and forced 16 GiB KV:

- largest five-second residual: `77937.680 MiB`;
- R22 ratio: `103.725991%`;
- same-window order-4 RM activity: `77405.938 MiB`;
- strict RM OOM count: `1`;
- burst band: `BURST_UNCHANGED`.

Managed restoration is CLOSED/PASS.

## R25 — coarse userspace load-phase localization

Canonical:

- `orcarouter-r25-load-phase-localization-plan-20261005.md`
- `orcarouter-r25-load-phase-localization-result-20261005.md`

R25 is a completed read-only post-hoc localization. The RM order-4 episode lasts only about `3.217673 s`, while checkpoint filling continues for `522.10 s`. `99.276945%` of traced activity lies between the coarse model-start and weight-load-completion markers, and the first `559.688 MiB` begins before the old model-start log. This excluded post-load/CUDA-graph timing as the primary location and prioritized exact model-construction boundaries.

## R25b — exact initialize_model boundary

Canonical sequence:

- `orcarouter-r25b-init-model-boundary-plan-20261005.md`
- `orcarouter-r25b-init-model-image-preflight-result-20261005.md`
- `orcarouter-r25b-live-harness-preflight-result-20261005.md`
- `orcarouter-r25b-live-attempt01-probe-group-invalid-20261005.md`
- `orcarouter-r25b-recovery-corrected-preflight-result-20261005.md`
- `orcarouter-r25b-init-model-boundary-result-20261005.md`

Attempt 01 is permanently **SETUP INVALID / NO MEASUREMENT CLAIM**. Attempt 02 is **COMPLETED — VALID_MEASURED — FUNCTIONAL PASS / HOST-STABILITY FAIL**.

Exact R25b alignment:

- total order-4 RM activity: `77405.938 MiB`;
- before selected `initialize_model()`: `559.688 MiB`;
- inside: `76846.250 MiB`;
- after: `0.000 MiB`;
- inside fraction: `99.276945%`;
- init duration: `3.161066 s`;
- RM episode duration: `3.468940 s`;
- strict discriminator: `RM_ORDER4_STARTS_BEFORE_INITIALIZE_MODEL`.

The strict label reflects a real small pre-init precursor. Engineering closure is that the primary approximately 75–77 GiB episode occurs during first-model construction, not the long checkpoint-fill phase.

## R26 — constructor / ModelOpt-MoE split

Canonical sequence:

- `orcarouter-r26-construction-boundary-plan-20261005.md`
- `orcarouter-r26-construction-image-preflight-result-20261005.md`
- `orcarouter-r26-live-harness-preflight-result-20261005.md`
- `orcarouter-r26-construction-boundary-result-20261005.md`

R26 is **COMPLETED — VALID_MEASURED — FUNCTIONAL PASS / HOST-STABILITY FAIL**.

Matched mechanism:

- largest five-second residual: `77940.164 MiB`;
- R22 ratio: `103.729297%`;
- burst band: `BURST_UNCHANGED`;
- order-4 calls/activity: `526` / `77405.938 MiB`;
- strict RM OOM count: `2`.

Constructor split:

- before constructor: `559.688 MiB`;
- inside constructor: `76846.250 MiB` (`99.276945%`);
- after constructor: `0.000 MiB`;
- ModelOpt-MoE create-weights: `34292.000 MiB`;
- packed w13+w2: `29976.000 MiB`;
- constructor activity outside ModelOpt-MoE: `42554.250 MiB`.

Final discriminator:

`RM_ORDER4_MIXED_WITHIN_MODEL_CONSTRUCTOR`

H11 remains deferred because the unlocalized constructor residual is larger than the entire ModelOpt-MoE contribution.

Managed restoration returned exact OrcaRouter READY and is CLOSED/PASS.

## R27 — W4A16-linear / exact Qwen4Exp residual discriminator

Canonical sequence:

- `orcarouter-r27-linear-residual-plan-20261005.md`
- `orcarouter-r27-linear-image-preflight-result-20261005.md`
- `orcarouter-r27-live-harness-preflight-result-20261005.md`

R27 targets the `42554.250 MiB` R26 residual. It instruments the exact v0.29 `Qwen4ExpDecoderLayer` construction path and `ModelOptNvFp4W4A16LinearMethod.create_weights()`, including the packed W4A16 `weight` allocation sub-boundary.

Source inspection closed PLE as a constructor-size false lead: the matched runtime has `VLLM_PLE_MMAP=1`, and the v0.29 patch replaces the giant stock N-gram embedding with a small mmap placeholder during constructor execution.

Repository implementation/CI is green. Static image gate is CLOSED/PASS:

- image: `vllm-orcarouter-v029-r27-linear-marker:v1`;
- image id: `sha256:e9e92c5cb98d443a8410f21345cb0e07c30c9e7c84516cedcc2a6dc213934119`;
- inherited R26 constructor/ModelOpt-MoE contracts: PASS;
- R27 W4A16-linear contract: PASS;
- exact Qwen4Exp-layer contract: PASS;
- PLE-mmap placeholder contract: PASS;
- managed container ID / `StartedAt`: unchanged;
- exact managed OrcaRouter model with `max_model_len=262144`: READY.

Guarded harness preflight is also CLOSED/PASS:

```text
stale_probe_groups_before=NONE
stale_probe_groups=NONE
r27_probe_definition_contract=PASS
R24_PREFLIGHT=PASS
R27_LIVE_PREFLIGHT=PASS
predecessor_age_s=3683.743
minimum_predecessor_age_s=2700
predecessor_age_ok=1
rm_probe_target_count=2
R27_HARNESS_PREFLIGHT_RC=0
stale_probe_groups_after=NONE
R27_HARNESS_PREFLIGHT_GATE=PASS
```

Managed runtime remained unchanged across harness preflight:

- container ID: `cd2d34ec90de03b74a8cb8dc76a2311dd4b90b88bd2700b35026016f9c05f911` before/after;
- `StartedAt=2026-10-05T08:55:17.15500875Z` before/after;
- exact `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4` / `max_model_len=262144`: READY;
- no model restart, managed-service mutation, persistent VM tuning, experiment container, evidence directory, or stale probe state was introduced.

R27 remains observational. Gate sequence:

1. repository CI — **PASS**;
2. marker-only image build — **PASS**;
3. static image/preflight + managed non-mutation — **PASS**;
4. canonical static result — **PASS**;
5. guarded harness preflight + managed non-mutation — **PASS**;
6. canonical harness result — **PASS**;
7. exactly one guarded live R27 measurement — **AUTHORIZED NEXT**.

The live run must use the fresh default evidence path `/tmp/orcarouter-hybrid-r27-linear-boundary-01-20261005`, exact R27 diagnostic image, explicit `ORCA_R27_LIVE_ACK=YES`, and preserved R24/R26 evidence. If evidence is created, preserve it even if the run fails or is invalid.

## Current next engineering direction

Do not repeat H6 or R26, do not apply H11 yet, and do not broaden tracing.

The next highest-information question is whether ordinary ModelOpt W4A16 linear construction explains at least 90% of the R26 `42554.250 MiB` non-MoE residual. If it does, the packed W4A16 weight sub-boundary will indicate whether storage materialization itself dominates. If it does not, Qwen4Exp layer-type/per-layer residual totals will identify the smallest remaining constructor path.

PR #244 remains intentionally open and must not be merged before mitigation/Hybrid closure and explicit merge timing.
