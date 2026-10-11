# Benchmark evidence index

This directory preserves canonical evidence for live DGX Spark runtime, profile-switch, host-stability, allocator, ownership, mitigation-discriminator, and userspace-localization experiments. Historical per-run documents remain immutable in meaning: later documents may add closure links, but must not rewrite what an earlier run actually observed.

## H38 managed-service integration

The managed H38 candidate is tracked separately from the historical H38
experiment-runtime closure and from the R9-R32 RM allocator investigation.

- plan: `orcarouter-h38-managed-integration-plan-20261007.md`
- static result: `orcarouter-h38-managed-integration-static-result-20261007.md`
- live Gate A attempt 01: `orcarouter-h38-managed-gate-a-attempt01-20261007.md`
- live Gate A attempt 02: `orcarouter-h38-managed-gate-a-attempt02-20261007.md`
- live Gate A attempt 03: `orcarouter-h38-managed-gate-a-attempt03-20261007.md`
- live Gate A attempt 04: `orcarouter-h38-managed-gate-a-attempt04-20261007.md`
- Gate A matched base-main control: `orcarouter-h38-managed-gate-a-base-control-20261007.md`
- atomic cross-release transaction implementation: `orcarouter-h38-managed-atomic-refresh-implementation-20261007.md`
- first atomic live migration attempt: `orcarouter-h38-managed-atomic-gate-attempt01-20261007.md`
- production-shape allocator/protection discriminator plan: `orcarouter-h38-allocator-protection-discriminator-plan-20261008.md` (unchanged protection; static CI `37713578855` PASS / 595 tests)
- production-shape allocator/protection attempt 01: `orcarouter-h38-allocator-protection-discriminator-attempt01-20261008.md` (**VALID PROTECTED_STOP** at 11:06:47 KST; exact MTP k2 identity; last pre-event shard 14/18; strict RM 0; NOT_REACHED / INCONCLUSIVE); runner summary fix CI `37718076547` SUCCESS, 596/596
- **completed full-history offline finding**: `orcarouter-h38-allocator-protection-offline-analysis-20261008.md` (archive SHA256 recorded; corrected R21/R22-equivalent physical-page residual **+74,761.516 MiB** over 5 s, **SwapFree delta 0**, 40 fast/8 slow post-event samples excluded; 15/18 phase line actually AFTER protected stop)
- **R11/R23–R32-to-H38 mechanism transfer and stop-conditions review**: `orcarouter-h38-r23-r32-allocator-mechanism-transfer-20261008.md` (R23 direct RM endpoint versus H38 physically observed burst, 400/800 MiB evidence, exact-R28 versus H38 image scope, NO R33/live run authorized)
- **H38 CT meta-w13 source prerequisites — actual DGX PASS**: `orcarouter-h38-ct-meta-w13-source-prerequisites-result-20261009.md` (exact checkout `ac58309620ace2213df68ebf06b2c18b9592f394`, H38 image ID unchanged, native layerwise source functions present, CT `uses_meta_device` declaration NO; **not** CT meta implementation or RM memory mitigation).
- Original M1-to-H38 feasibility plan: `orcarouter-h38-ct-meta-w13-feasibility-plan-20261008.md`; scanner `scripts/benchmark/check-h38-ct-meta-prerequisites.sh`, `inspect-h38-ct-meta-prerequisites.py`, tests `tests/test_h38_ct_meta_prerequisites.py`, CI `37778807130` / `37779107553` SUCCESS, 613/613.
- **H38 historical Attempt 04 launch configuration — actual DGX archive PASS (2026-10-09)**: `orcarouter-h38-preserved-loader-config-result-20261009.md`. Guarded offline inspection at clean `1bc76cb12cc8df9d9512de0d0cd29e49120c1233` matched preserved image tag/ID, `candidate-inspect.json` versus `candidate-cmd.json`, H38 env lineage and model mount. Explicit CLI `load_format=safetensors`, `executor=mp`, `tensor_parallel_size=1`. Loader strategy, model-loader-extra, prefetch/thread details, EP and pipeline parallel flag all `NOT_EXPLICIT`. **Same Attempt 04 startup log** contained `Auto-prefetch is disabled`. PASS is archived launch flags only, **not resolved vLLM config, runtime loader iterator or CT buffer lifetime**.
- **H38 archived candidate launch configuration — implementation/source CI qualified (DGX actual result above)** (implementation `0a71beb7fdd64ed06e9879c4349acb681e11f99f`; CI `37892699414` **SUCCESS, 641/641 tests**): `orcarouter-h38-preserved-loader-config-plan-20261009.md`. Offline `scripts/benchmark/inspect-h38-preserved-loader-config.py`, read-only exact-SHA runner `scripts/benchmark/check-h38-preserved-loader-config.sh`, regressions `tests/test_h38_preserved_loader_config.py`. Reads preserved Attempt 04 `candidate-inspect.json` / `candidate-cmd.json` and optional startup-phase only, rejects mismatched image/command, redacts secrets, treats missing flags as `NOT_EXPLICIT`; cannot prove effective vLLM defaults or actual tensor delivery.
- **H38 exact-installed loader source contract — actual DGX PASS (2026-10-09)**: `orcarouter-h38-installed-loader-source-contract-result-20261009.md` (clean checkout `b85f506a4f3f6e7a1272f6e5b37a137a5f57a5f9`; pinned H38 image ID unchanged; eight installed source hashes; default safetensors sorting and get_tensor-before-model-mapper, Qwen4Exp MTP name drop, layerwise numel/replay and H11/H12 CT aliases all SOURCE_PRESENT; selected runtime load path and packed-scale completion **NOT proven**).
- **H38 exact-installed loader source audit — implementation CI green, DGX PASS now independently recorded** (implementation `1e4aadaa029937a61007e225c173239079481a16`, CI `37889474895` **SUCCESS, 633/633 tests**): `orcarouter-h38-installed-loader-source-contract-plan-20261009.md`; CPU-only inspector `scripts/benchmark/inspect-h38-installed-loader-source.py`, guarded runner `scripts/benchmark/check-h38-installed-loader-source.sh`, unit tests `tests/test_h38_installed_loader_source.py`. Audits upstream-v0.29-derived index/natural safetensors iterator, Qwen4Exp MTP name mapper, layerwise buffer/replay and CT alias contract **on exact H38 installed source**; may not infer selected runtime config, skipped I/O, or safe memory peak from a source-only PASS.
- **H38 checkpoint metadata attempt 03 — DGX observed, correct exit 3, strict ORDER_GATE FAIL**: `orcarouter-h38-checkpoint-metadata-order-attempt03-revisit-ownership-20261009.md` (layer 0 revisit is distinct MTP layer 0 in `model-mtp.safetensors`; independent numbered-model shard layer 8 splits 4→5 and layer 11 splits 5→6; `base_model_only_revisited_layers_diagnostic=[8,11]`; 17 numbered shards + MTP, max overlap 3; all 48 routed layers present; no runtime memory or loader equivalence verified).
- **H38 checkpoint gate-classification / bounded revisit-diagnostic fix**: commit `51850e28230c760dadac8fd86268d949b7623345`; GitHub Actions `37883805274` SUCCESS, **624/624 tests**. New exact-file revisit evidence **not yet collected** from DGX; original full-order FAIL remains intact.
- **H38 checkpoint metadata attempt 02 — VALID ORDER GATE FAIL**: `orcarouter-h38-checkpoint-metadata-order-attempt02-gate-fail-20261009.md` (actual H38 image, index PASS; 17 numbered model shards + `model-mtp.safetensors`; 223,046 total / 221,186 routed tensor keys, 48 layers; revisits **0,8,11**, max overlap **3**; routed disk 72,981,184,512 bytes; two hypothetical peaks 6,448,748,544 bytes). Completed metadata output's `ORDER_GATE=FAIL` is authoritative; old outer `PREFLIGHT=INVALID` was an exit-code classification bug. New narrowly scoped diagnostic tool reports bounded revisit shard positions; **no CT meta experiment authorized**.
- **H38 18-shard checkpoint metadata attempt 01 — INVALID before scan (2026-10-09)**: `orcarouter-h38-checkpoint-metadata-order-attempt01-invalid-tempfile-20261009.md` (actual H38 image/checkout confirmed; no usable Python tempdir under UID 65534 + read-only root; no 18-shard/layer/buffer result). Corrected runner supplies only isolated 64 MiB /tmp tmpfs; **not yet live revalidated**. Fix commit `d3ff823d3b7c183bb84c53079e25984e321a23e0`, CI `37882840040` SUCCESS, 622/622 tests.
- **H38 18-shard checkpoint metadata-order source gate (actual checkpoint not measured)** (implementation commit `b476441899d07d04e9db3669ccd881f4351ef15e`; CI `37822913604` SUCCESS, 620/620 tests): `orcarouter-h38-checkpoint-metadata-order-plan-20261009.md`, analyzer `scripts/benchmark/inspect-h38-checkpoint-metadata-order.py`, safe CPU-only read-only runner `scripts/benchmark/check-h38-checkpoint-metadata-order.sh`, regression `tests/test_h38_checkpoint_metadata_order.py`. Reads only safetensors headers and safe_open key names; strict 18-shard index/48-layer checks and two hypothetical routed-byte buffer scenarios. Even a PASS is not an exact H38 loader-semantics or live-memory safety result.
- **H38 exact-image source contract — DGX observed PASS**: `orcarouter-h38-exact-image-source-contract-result-20261008.md` (original checkout `1a4416581f4064baa110fc83947c442c360c4689`, H38 image ID `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`, `source_check_rc=0`, H11 packed `torch.empty` retained, H12 aliases PASS, H38 Humming/Marlin PASS, R32 precreate direct syntax 0 on actual H38 installed source; **not a host/RM mitigation PASS**)
- exact-image source preflight plan: `orcarouter-h38-exact-image-source-contract-plan-20261008.md`; guarded runner `scripts/benchmark/check-h38-exact-image-source.sh`, inspector `scripts/benchmark/inspect-h38-exact-image-source.py`, regression `tests/test_h38_exact_image_source.py`; static CI `37747053983` and `37747347746` SUCCESS, 606/606. CPU-only transient runc inspector, no GPU/model.
- archived-evidence offline analyzer: `scripts/benchmark/analyze-h38-allocator-attempt-archive.py` (read-only tar parser, meminfo+buddy accounting, phase/event strict alignment); regression: `tests/test_h38_allocator_attempt_archive.py`; CI `37744164668` SUCCESS, 599/599 tests

- allocator observer runner: `scripts/benchmark/run-h38-allocator-protection-discriminator.sh` (production SPEC=mtp k=2, same protect thresholds)
- trajectory analyzer: `scripts/benchmark/analyze-h38-allocator-protection-trajectory.py` (pre-event-only T-60/T-30/T-10/T-5/T-1/T0 samples, optional strict-RM reference; no post-failure rollback contamination or inferred threshold); pre-event hardening CI `37713396361` SUCCESS (595/595)
- MTP startup discriminator plan: `orcarouter-h38-managed-mtp-startup-discriminator-plan-20261007.md`
- MTP startup discriminator attempt 01 (setup invalid): `orcarouter-h38-managed-mtp-startup-discriminator-attempt01-20261008.md`
- MTP startup discriminator attempt 02 (setup invalid): `orcarouter-h38-managed-mtp-startup-discriminator-attempt02-20261008.md`
- MTP startup discriminator attempt 03 (harness invalid): `orcarouter-h38-managed-mtp-startup-discriminator-attempt03-20261008.md`
- MTP startup discriminator attempt 04 (valid PROTECTED_STOP): `orcarouter-h38-managed-mtp-startup-discriminator-attempt04-20261008.md`
- MTP startup discriminator runner: `scripts/benchmark/run-h38-mtp-startup-discriminator.sh` (repository-relative); valid live closure is attempt 04 = `PROTECTED_STOP`, exact identity PASS, `rm_oom_count=0`, `protected_stop=1`; removing MTP is not sufficient to avoid the H38 protection boundary
- guarded atomic migration runner: `scripts/benchmark/run-h38-managed-migration-gate.sh` (repository-relative)
- implementation branch: `feat/h38-managed-integration`
- state: earlier H38 implementation/static CI passed, while attempts 01/02 fixed host-dependent qualification fixtures and attempt 03 fixed the branch file-mode regression; attempt 04 plus matched base-main control `d75c24ca496286e0b62db5e8f1d88480ed30e137` reproduced the same protected legacy CPU-offload restart with `rm_oom_count=0`, proving that intermediate READY requirement is a pre-existing base-main compatibility boundary; the branch now contains a dedicated atomic release + same-profile H38 manifest refresh transaction that avoids starting that legacy intermediate and preserves the previous runtime rollback container until the outer lifecycle commit; the first live run through that atomic path on `05748a9c9a2b206a536b454dc5d662d7750913db` reached the H38 candidate but protection stopped it before READY, yielding `FUNCTIONAL=NOT_REACHED`, `HOST_STABILITY=INCONCLUSIVE`, `rm_oom_count=0`, and `protected_stop=1`; recovered monitor samples show non-CMA available rising from `27111 MiB` to `29909 MiB` while low free + swap growth accumulated, classifying the stop as a monitor-heuristic collision rather than a strict RM failure or a host-stability pass; valid SPEC=none attempt 04 reproduced the protected-stop boundary with exact identity and no strict RM event, formally closing MTP as an insufficient explanation for that boundary; follow-up managed determinism/performance/restart gates remain unauthorized until a migration run passes
- promotion rule: do not merge the runtime-impacting default change until
  managed lifecycle/restart/doctor, determinism, performance, and strict RM
  host-stability gates are recorded.

The existing H38 experimental/runtime results remain historical evidence; this
work does not rewrite those measured results.

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
12. `orcarouter-r29-global-rm-chunk-cadence-result-20261006.md`
13. `orcarouter-r29b-layer-chunk-pairing-result-20261006.md`
14. `orcarouter-r30-pre-w13-800-boundary-result-20261006.md`
15. `orcarouter-r31-pre800-moe-boundary-result-20261006.md`
16. `orcarouter-r32-precreate-source-contract-result-20261006.md`
17. `orcarouter-r23-r32-allocation-localization-closure-20261006.md`

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
- `orcarouter-r29-global-rm-chunk-cadence-plan-20261005.md`
- `orcarouter-r29b-layer-chunk-pairing-plan-20261006.md`
- `orcarouter-r30-pre-w13-800-boundary-plan-20261006.md`
- `orcarouter-r31-pre800-moe-boundary-plan-20261006.md`
- `orcarouter-r32-precreate-source-contract-plan-20261006.md`
- `orcarouter-r32-attempt01-static-checker-invalid-20261006.md`
- `orcarouter-r32-attempt02-static-checker-invalid-20261006.md`

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

This demotes another model-component marker split.

## R29 / R29b — global repeated-chunk cadence

R29 and R29b are **COMPLETED — READ-ONLY POST-HOC PASS**.

R29 selected-constructor stream:

- order-4 request count: `464`;
- order-4 activity: `76846.375 MiB`;
- repeated large requests: `400 MiB x48`, `800 MiB x48`, `1214 MiB x2`;
- 400 MiB median interarrival: `52.194 ms`;
- 800 MiB median interarrival: `52.182 ms`.

R29 strict discriminator:

`R29_REPEATED_LARGE_RM_CHUNKS_SPAN_MULTIPLE_CONSTRUCTOR_BOUNDARIES`

R29b then proved all 48 ordinal pairs are `800 MiB -> 400 MiB`, all are adjacent in the RM stream, and the median pair delta is `24.925 ms`.

The original analyzer discriminator name used `PER_DECODER_LAYER`, but the raw output showed non-unique 800-layer marker placement. Canonical semantic correction:

`R29B_STRICT_800_THEN_400_ADJACENT_ORDINAL_CADENCE_WITH_NONUNIQUE_800_LAYER_PLACEMENT`

## R30 — exact w13 / 400 MiB closure

R30 is **COMPLETED — READ-ONLY POST-HOC PASS**.

The 400 MiB family is closed event-by-event to packed-expert w13 construction:

- selected w13 intervals: `48`;
- constructor 400 MiB requests: `48`;
- exactly one 400 MiB request in every w13 interval: `48/48`;
- no constructor 400 MiB requests outside w13 intervals;
- `400 MiB * 48 = 19200 MiB`, exactly matching R26 `modelopt_w13.activity_mib`.

All 48 w13-associated 400 MiB events have an immediately preceding 800 MiB RM request. The 800 MiB event occurs before W13 BEGIN by median `8.100208 ms`; W13 BEGIN to 400 is median `16.894804 ms`.

Preceding-800 userspace placement is mixed:

```text
hyper_connection=32
self_attn=11
linear_attn=1
outside_unquant=4
```

Final discriminator:

`R30_EXACT_W13_400_WITH_IMMEDIATE_PRECEDING_800_MIXED_USERSPACE_PLACEMENT`

## R31 — 800 MiB precedes ModelOpt-MoE create_weights

R31 is **COMPLETED — READ-ONLY POST-HOC PASS**.

Across all 48 exact R30 pairs:

- 800 before ModelOpt-MoE BEGIN: `48/48`;
- 800 inside MoE pre-w13: `0`;
- 800 inside w13: `0`;
- median 800 -> MoE BEGIN: `8.070243 ms`;
- median MoE BEGIN -> W13 BEGIN: `0.028849 ms`.

Final discriminator:

`R31_PRE800_STRICTLY_BEFORE_MODELOPT_MOE_BEGIN`

Therefore the 800 MiB family is not the ModelOpt packed w13/w2 allocation body.

## R32 — exact-image pre-create source contract

R32 is **COMPLETED — ATTEMPT03 PASS — STATIC / READ-ONLY**.

Attempt01 and Attempt02 are permanently retained as **STATIC CHECKER INVALID / NO SOURCE-CLOSURE CLAIM**.

Corrected Attempt03 on exact R28 image passed:

```text
qwen4_decoder_attention_before_mlp=PASS
qwen4_decoder_hyperconnection_after_mlp=PASS
sparse_moe_gate_before_factory=PASS
sparse_moe_gate_call=ReplicatedLinear
sparse_moe_shared_gate_call=ReplicatedLinear
sparse_moe_factory_call=FusedMoEFactory
routed_experts_order_contract=PASS
factory_pre_routed_direct_tensor_alloc_count=0
routed_pre_create_direct_tensor_alloc_count=0
direct_precreate_tensor_alloc_syntax=ABSENT
```

Final discriminator:

`R32_NO_DIRECT_PRECREATE_WEIGHT_ALLOCATION_SUPPORTS_ALLOCATOR_BACKING_GROWTH`

R32 does not prove helper constructors allocate nothing. It does close the absence of a separate explicit direct pre-create model-weight allocation that could be promoted as the repeated 800 MiB owner.

## R23–R32 engineering closure

Canonical closure:

- `orcarouter-r23-r32-allocation-localization-closure-20261006.md`

Final interpretation:

- the **400 MiB** repeated family is directly localized to packed `w13_weight` construction;
- the **800 MiB** repeated family is not supported as a distinct model-component weight owner;
- the best-supported mechanism is a discrete CUDA/NVIDIA RM backing/reservation growth event temporally induced by the repeated decoder-layer construction cycle;
- this remains a mechanism-level inference, not proof of the exact lower allocator call;
- RM bytes remain logical allocation activity, not exact resident ownership.

Model-prefix/component localization is now closed. Do not add more model-prefix, Linear, attention, or hyper-connection markers for the 800 MiB ownership question.

R33 is optional and is **not** automatically authorized. A new live allocator-focused discriminator is justified only if an actionable mitigation requires identifying the exact lower-level transition responsible for the 800 MiB request.

PR #244 was squash-merged into `main` as `5b6ba67eddf1902cdf2daa17ec30f6e043e26fa6` on 2026-10-06. The R9–R32 allocator/localization chain above is therefore the post-merge canonical repository state. The unqualified M1 mitigation prototype was intentionally excluded from that merge and remains a separate follow-up track.

## H38 CT per-parameter layerwise accounting — 2026-10-09 (source discriminator staged)

- [H38 CT packed/scale layerwise source-only accounting plan](orcarouter-h38-ct-layerwise-accounting-source-plan-20261009.md) — pins the H11/H12/installed-source contract, adds a guarded source-only checker plus synthetic regressions, and explicitly retains CT completion, shard-split buffer peak and host stability as unverified. This is a plan and tool implementation, **not an executed DGX result**.


### H38 CT layerwise accounting counterexamples — 2026-10-09

- [H38 CT accounting source-only plan and synthetic counterexamples](orcarouter-h38-ct-layerwise-accounting-source-plan-20261009.md) — updated AST inspector now pins all eight CT shapes/dtypes and partial/finalizer paths; the offline synthetic suite demonstrates an aggregate element-count false-completion possibility without asserting it happened in the H38 runtime.
- Tools: scripts/benchmark/inspect-h38-ct-layerwise-accounting.py, scripts/benchmark/simulate-h38-ct-layerwise-completion.py; tests/test_h38_ct_layerwise_accounting.py and tests/test_h38_ct_layerwise_completion_cases.py.
- Test-only evidence (intermediate commit 511bef4c01268e7a4745fad8eae6843a7d1ca3e9): Actions run 37911091805 **SUCCESS / 662 tests** plus syntax/ShellCheck/compile/whitespace. CI and exact SHA must be checked again at the final documentation HEAD.
- Distinction: **SYNTHETIC_ONLY**; exact-image CPU-only inspector execution **PENDING**; real CT completion, shard 8/11 buffer lifetime, actual peak and host stability **UNVERIFIED**. PR #259 stays Draft/Open and is not mergeable under current qualification rules.


### H38 RoutedExperts mixed scale-write syntax — 2026-10-09

- [CT layerwise-accounting source plan and routed dispatch contract](orcarouter-h38-ct-layerwise-accounting-source-plan-20261009.md) — source-only inspector now checks a fifth pinned installed H38 source (RoutedExperts), including expert ID remapping/nonlocal rejection, GROUP/TENSOR/packed loader paths, explicit w13/w2 copy helpers and indexed scale assignment sites.
- Relevant source-only code/test implementation CI: run 37914943450, SUCCESS / 666 unit tests, shell syntax/ShellCheck/Python compile/whitespace PASS. The final canonical docs HEAD requires a fresh CI check.
- Observation is **UPSTREAM SOURCE / CODE CONTRACT ONLY**, not actual pinned-image execution and not a TorchDispatchMode trace. Indexed assignment is not automatically equivalent to counted aten.copy_; actual CT scale copy credit, unique expert coverage and layer 8/11 buffering remain UNVERIFIED. PR #259 is Draft/Open, merge forbidden.


### H38 exact-image accounting Attempt 01 — checker INVALID, 2026-10-09

- [Actual operator source-only Attempt 01 result](orcarouter-h38-ct-layerwise-accounting-attempt01-invalid-20261009.md) — clean checkout b9db2c901676ebc974c22f5ee65b37bc6c208c72, exact pinned H38 image ID preflight, CT AST rejected an installed PerTensorScaleParameter initializer: source_check_rc=2; no PASS claim.
- This is a **source-inspector class allowlist mismatch**. The wrapper never reached the success footer; do NOT call it an H38 model/scale-loading defect or an image identity-unchanged after-check result.
- Remediation on PR #259 extends the inspector to allow scale-specific vLLM wrappers under strict symbolic shape/dtype/weight_loader rules; adds negative synthetic regressions. Exact-image rerun is **PENDING** after CI-qualified HEAD.
- No model/GPU, service or host-protection change. All H38 functional/memory/stability qualification remains blocked and UNVERIFIED.


### H38 CT source checker diagnostic fallback (repo-only, 2026-10-09)

- [CT source plan, current staged fallback contract](orcarouter-h38-ct-layerwise-accounting-source-plan-20261009.md): the exact-image AST checker now prints bounded **all-eight registration source diagnostics** on INVALID, after rechecking all five pinned installed-source SHA256 digests. It preserves original exit code 2; it cannot convert a mismatch into PASS or certify loaded tensors.
- [Attempt 01 original user-provided DGX result](orcarouter-h38-ct-layerwise-accounting-attempt01-invalid-20261009.md): only observed installed-image run so far, INVALID on unsupported PerTensorScaleParameter; unchanged historical result. **Attempt 02 has not been observed**.
- The H38 image, model/checkpoint, GPU, managed service and host protection remain untouched. The branch's CI-tested synthetics do not substitute for DGX operator evidence; retain all CT completeness, scale CopyCounter credit and buffer-lifetime statuses as UNVERIFIED.


### Exact H38 CT Attempt 02 source checker INVALID — 2026-10-10

- [Attempt 02 actual DGX source-only diagnostic](orcarouter-h38-ct-layerwise-accounting-attempt02-invalid-20261010.md): exact H38 image/source SHA-pinned fallback reports **8/8 expected CT names**, but the previous AST checker rejects w13_weight_scale:ModelWeightParameter as an unexpected group-scale constructor (source_check_rc=2).
- The exact installed H38 constructors are **4 ModelWeightParameter** (two packed weights plus two group scales), **2 PerTensorScaleParameter** (global weight scales), and **2 torch.nn.Parameter** (input scales). Preserve original shapes, dtype, sharding keywords and source-only limitations.
- [CT source-plan correction](orcarouter-h38-ct-layerwise-accounting-source-plan-20261009.md): stage a narrowly corrected eight-name constructor contract and positive/negative synthetic regression suite. A corrected code/CI pass is not an actual image source PASS.
- Only operator Attempt 01 and Attempt 02 source-only INVALID runs are established. No H38 model/GPU run and no authorization to alter image, host protection, PR readiness or merge. Unique copy/scale coverage and memory peak remain UNVERIFIED.


### H38 CT installed-source Attempt 03 — **PASS_SOURCE_CONTRACT_ONLY**, 2026-10-11

- [**Real DGX Spark pinned-source audit PASS — Attempt 03**](orcarouter-h38-ct-layerwise-accounting-attempt03-source-pass-20261011.md): clean exact local HEAD 5fa4265d394255744f8886b857804a28c433cf3f after fast-forward, fixed H38 image ID, five pinned source SHA256 checks, eight parameter constructor/shape/dtype contracts, H12 same-object alias, 21 Layerwise/meta accounting anchors and 14 RoutedExperts AST anchors; source_check_rc=0 and image_identity_unchanged=YES.
- The H38 source checker printed H38_CT_ACCOUNTING_SOURCE=PASS_SOURCE_CONTRACT_ONLY and H38_CT_ACCOUNTING_PREFLIGHT=PASS_SOURCE_CONTRACT_ONLY. The reported CPU-only/no-checkpoint/no-GPU/no-network execution did **not** change the installed image, host protection or managed service.
- **Current authoritative qualification is only source syntax.** The older Attempt 01/02 INVALID records are immutable historical checker mismatches (not H38 runtime failures). Current input-scale post-construction loader binding, live TorchDispatchMode scale copy credit, 512-expert unique loading, layer 8/11 completion and peak buffer ownership remain UNVERIFIED. H38 model/GPU testing and PR #259 Ready/Merge remain BLOCKED.
- Next source-only work: trace plain input-scale post-construction set_weight_attrs/loader path, then design only bounded, separately-qualified CPU synthetic dispatcher checks where justified. [Reconciled source plan](orcarouter-h38-ct-layerwise-accounting-source-plan-20261009.md).


### H38 CT input-scale weight_loader postconstruction attribute provenance — next source gate, 2026-10-11

- [New source-only input-scale postconstruction attribute plan](orcarouter-h38-ct-scale-attr-source-plan-20261011.md): after the successful exact-image CT registration/Layerwise Attempt 03, the separate checker examines w13/w2 input-scale set_weight_attrs calls and TENSOR quant-method tag, H11 loader argument origin, RoutedExperts loader export, layerwise wrapping and the source syntax of the common guarded setattr helper. Read-only unprivileged runc with exact clean SHA/image ID, no network/GPU/checkpoint/model.
- New inspector, wrapper and tests are repository-only pending CI and **operator exact-image execution**. The common utils.py helper digest is currently **not a preapproved source SHA pin**; a future wrapper will capture it under the pinned image ID. Do not label this as a completed DGX run or claim real callback execution.
- Existing [Attempt 03 source contract PASS](orcarouter-h38-ct-layerwise-accounting-attempt03-source-pass-20261011.md) remains qualified. CT CopyCounter scale credit, unique expert/scale coverage, shard 8/11 lifetime, finite buffer peak and host stability remain UNVERIFIED; PR #259 Draft/Open and Merge BLOCKED.


### Exact H38 CT input-scale postconstruction attribute audit — **PASS_SOURCE_SITES_ONLY**, 2026-10-11

- [**Actual DGX operator source-only Attempt 01 PASS**](orcarouter-h38-ct-scale-attr-attempt01-source-pass-20261011.md): clean exact HEAD 1865521c2ff58add7bddeed6735c76803a3e3637 after fast-forward, pinned H38 image ID, preverified 3 source SHA256 digests, both input-global-scale registration→TENSOR attribute update→post-construction set_weight_attrs source sites, H11 loader-origin, RoutedExperts exported loader, layerwise wrapper, and source helper guarded setattr syntax. source_check_rc=0; image_identity_unchanged=YES; no GPU/model/checkpoint payload or host changes.
- **New helper digest:** vllm/model_executor/utils.py = f208310647a012797e0b0e9631d3498135c7f9aef831e35e42e96eceb7623f89. This was an **image-ID-guarded new observation**, not independently pre-pinned before Attempt 01.
- Earlier [CT packed/group/global source audit Attempt 03 PASS](orcarouter-h38-ct-layerwise-accounting-attempt03-source-pass-20261011.md) remains a separate source-only success. Effective runtime callback, aten.copy_ scale credit, unique 512-expert loaded coverage, shard 8/11 buffer lifetime, and GB10 host memory safety **remain unverified**; do not promote AST syntax to runtime evidence.
- [Next safe proof plan](orcarouter-h38-ct-scale-attr-source-plan-20261011.md): separately study a strictly bounded external CPU-only toy TorchDispatchMode trace, explicitly label its torch version/environment, then determine which exact H38 runtime evidence would be required. No image rebuild, H38 GPU/model startup, host-protection changes or PR Ready/Merge.


### External CPU TorchDispatchMode indexed-write toy — NOT installed-H38 evidence (2026-10-11)

- [**External isolated CPU PyTorch 2.10.0+cpu indexed assignment trace**](h38-ct-copycounter-indexed-write-external-cpu-toy-20261011.md) — source-independent tiny Tensor operations observed that nested index and row assignments can emit aten.copy_.default. Four writes credited 6 destination elements despite covering only 5 unique slots in a 3x2 synthetic destination; repeated copies must not be conflated with complete unique destination coverage.
- **Provenance distinction:** conducted in the assistant's external CPU Python runtime, not on DGX, not inside H38 pinned Docker image, not with H38 checkpoint/vLLM loader. This toy does not qualify installed-H38 CopyCounter events, actual 512-expert loading, shard 8/11 lifetime, memory peak, function or host stability.
- Preserve the separate real-DGX [CT source Attempt 03 PASS](orcarouter-h38-ct-layerwise-accounting-attempt03-source-pass-20261011.md) and [input-scale attribute source Attempt 01 PASS](orcarouter-h38-ct-scale-attr-attempt01-source-pass-20261011.md). H38 GPU/model experiments, image/host-protection changes and PR Ready/Merge stay prohibited.


### H38 CT expert/shard possible destination-map source audit — staging (2026-10-11)

- [Expert/shard source-only map and next pinned-image acceptance criteria](orcarouter-h38-ct-expert-destination-source-plan-20261011.md): new guarded Python stdlib AST inspector and independent regression suite map **conditional** sources of CT w1/w3 packed/group projections, w2, per-tensor global scales, input-scale generic row writes versus ModelOpt-specific index writes, fused checkpoints, global/local expert mapping and optional global-scale handling. Four existing installed source SHA256 pins are mandatory.
- Repo CI on implementation commit [38107569683](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38107569683) **SUCCESS, 702/702 tests**; the separate operator DGX source-image inspection is NOT yet performed. Any later PASS_SOURCE_BRANCHES_ONLY proves source predicates, **not** real checkpoint names, actual EP/TP configuration, destination coverage, CopyCounter credit, shard 8/11 buffering or memory safety.
- Prior operator [eight-parameter CT Attempt 03 source PASS](orcarouter-h38-ct-layerwise-accounting-attempt03-source-pass-20261011.md) and [input-scale attribute Attempt 01 source PASS](orcarouter-h38-ct-scale-attr-attempt01-source-pass-20261011.md) remain independently qualified. H38 image/GPU/model/host protections are unchanged; PR #259 Draft/Open, Merge BLOCKED.
