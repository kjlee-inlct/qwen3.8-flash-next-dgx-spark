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


### Pinned H38 CT expert/shard destination — **actual DGX Attempt 01 PASS_SOURCE_BRANCHES_ONLY** (2026-10-11)

- [**Actual pinned-image source audit PASS — 29/29 expert/shard source anchors**](orcarouter-h38-ct-expert-destination-attempt01-source-pass-20261011.md) at clean exact operator HEAD fd4221b5bdb2b95ad83f94255ee2740cea842c9e (after 1865521..fd4221b fast-forward), fixed image sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc and four pre-pinned installed source hashes; source_check_rc=0 and image_identity_unchanged=YES. No model/GPU/checkpoint payload read, service or host protection change.
- 11 expert routing/fused callbacks, 7 packed/group first-/second-half writes and 11 tensor/input scale branch predicates checked. The 8-family destination map lists conditional **source branch possibilities**, NOT observed OrcaRouter checkpoint name/expert/scale copies, loaded unique bytes or destination indices. Real input-scale values, expert-ID mapping, copy-counter dispatch, layer 8/11 lifetime, peak buffer, function and host safety remain UNVERIFIED.
- [Source plan updated with observed PASS and next safe metadata-only gate](orcarouter-h38-ct-expert-destination-source-plan-20261011.md). The independent prior CT registration source Attempt 03 and input-attribute source Attempt 01 PASS records remain unmodified. PR #259 remains Draft/Open and merge BLOCKED.


### H38 OrcaRouter CT checkpoint index key→expert/shard coverage — synthetic-first stage (2026-10-11)

- [**Next INDEX-ONLY checkpoint key map and safety plan**](orcarouter-h38-ct-checkpoint-key-map-plan-20261011.md): new stdlib inspector reuses existing qualified \`resolve_shards\` guard but analyzes only \`model.safetensors.index.json\` names→file owners; no safetensors header reread, no tensor payload, torch, vLLM or GPU. Requires clean exact Git SHA, pinned H38 image, read-only unprivileged runc with 1GiB/1CPU caps. Synthetic tests protect classifier exceptions, duplicate/missing slots, JSON duplicate fields and non-mutating wrapper.
- Tentative **base expert grid**: 48 layers × 512 experts × 9 candidate keys (gate/up/down × weight, weight_scale, weight_global_scale) = 221,184 names. Previous real header-only audit classified 221,186 routed names **including two auxiliary MTP keys**; the new per-name 9-key checkpoint grid has **NOT** been actually qualified on DGX. A future PASS_BASE_KEY_SCHEMA_ONLY will be index-name evidence, not a per-expert Torch copy or coverage guarantee.
- This schema conditionally corresponds to **6/8 CT registered parameter families**, not the two input-global-scale registrations. Their source, initialization, callback and unique load coverage remain UNVERIFIED. Existing [real expert/shard source Attempt 01 PASS](orcarouter-h38-ct-expert-destination-attempt01-source-pass-20261011.md) and [checkpoint metadata ORDER_GATE FAIL](orcarouter-h38-checkpoint-metadata-order-attempt03-revisit-ownership-20261009.md) remain distinct, unaltered. No H38 GPU/model, host protection change, image rebuild, CT meta patch or PR Ready/Merge.


### Actual H38 checkpoint CT key-map Attempt 01 — **KEY_SCHEMA_FAIL / exit 3** (2026-10-11)

- [**Operator observed exact-image index-only key classifier FAIL and root cause**](orcarouter-h38-ct-checkpoint-key-map-attempt01-schema-fail-20261011.md): exact original HEAD 1ed66b602c55534af432bba404b8eb0e6eb9db0e, H38 fixed-image ID, index SHA256 188d5905df195dd2dca4dbf2f9c029bb79328d0c85fd9772d73f72d881561866; index-only check completed \`FAIL_KEY_SCHEMA\` / rc 3 with image identity unchanged and no checkpoint tensor payload/header re-read.
- **The analyzer was wrong about the packed suffix:** expected \`*.weight\`, actual checkpoint samples show \`*.weight_packed\`. Its 73,728 "missing" slots are **false-negative classifier results**, not evidence of missing checkpoint weights; 147,456 group/global-scale names were separately recognized. Index has 221,184 base candidate names, 31 MTP namespace names, zero names containing \`input_scale\`, and 13 expert candidates spanning different numbered shards. Split-layer 8/11 scale-only per-shard counters are not whole-layer counts.
- The parser was corrected to the observed \`weight_packed\` component with focused synthetic regression tests; the previous failing operator result is immutable and does not become PASS merely from new code or CI. The [key-map plan](orcarouter-h38-ct-checkpoint-key-map-plan-20261011.md) and status document distinguish real Attempt01 FAIL from a **pending actual Attempt02**. No GPU/model, image/host protection changes or PR Ready/Merge.


### H38 CT real DGX checkpoint index-only Attempt 02 — **PASS_BASE_KEY_SCHEMA_ONLY** (2026-10-11)

- [**Actual Attempt 02 operator index-only PASS**](orcarouter-h38-ct-checkpoint-key-map-attempt02-index-pass-20261011.md) on clean exact HEAD 2426b9a9ac4234865176fc12c5e34a79d0bbfd1d and unchanged H38 image ID, fixed indexed checkpoint SHA256 188d5905df195dd2dca4dbf2f9c029bb79328d0c85fd9772d73f72d881561866; key_map_rc=0, image_identity_unchanged=YES; no safetensors header re-read, tensor payload, GPU/model or host service/protection changes.
- Real base expert name-grid: **48 layers × 512 experts × 9 gate/up/down×weight_packed/weight_scale/weight_global_scale names = 221,184**; zero missing canonical slots/incomplete expert name grids/unclassified, duplicate semantic, or out-of-range samples. Six candidate CT registration families have counts w13_weight_packed=49,152, w2_weight_packed=24,576, w13_weight_scale=49,152, w2_weight_scale=24,576, w13_weight_global_scale=49,152, w2_weight_global_scale=24,576.
- The entire index contains **0 input_scale key names**: two separately registered CT input-global-scale parameter families remain outside this key schema and their runtime initialization/value source is **UNVERIFIED**. PASS only covers index names/file owners, **NOT** 8/8 CT parameter completion, actual callbacks, unique tensor contents, CopyCounter credit, runtime buffer peak or model/host stability.
- Full split-layer key owners: layer8 shard4 2,119 + shard5 2,489 =4,608; layer11 shard5 3,685 + shard6 923=4,608. **13** (layer,expert) candidate groups span shard files (tool prints 12 samples). Total index 223,046 entries across 18 files; 31 \`mtp.\` prefix keys (not synonymous with two previously *routed-classified* MTP keys).
- [Historical immutable Attempt 01 FAIL](orcarouter-h38-ct-checkpoint-key-map-attempt01-schema-fail-20261011.md): old checker expected unsuffixed weight names; its false-negative KEY_SCHEMA_FAIL/rc3 remains preserved and is not reclassified. The independent metadata **CHECKPOINT_METADATA_ORDER_GATE=FAIL** remains FAIL. [Reconciled source/safety plan](orcarouter-h38-ct-checkpoint-key-map-plan-20261011.md). No H38 model/GPU, image rebuild, host defense modification, CT meta patch, PR Ready/Merge.


### H38 CT input-global-scale lifecycle and Layerwise counted-numel completion — NEW source-only stage (2026-10-11)

- [**Pinned H38 CT input-scale consumer and Layerwise numel threshold plan**](orcarouter-h38-ct-input-scale-lifecycle-source-plan-20261011.md): pure stdlib AST-only inspector checks exact qualified installed-H38 CT/layerwise/meta/reload-utils SHA256 pins, two input-global-scale source constructions \`torch.nn.Parameter(torch.empty(...))\`, registration+postconstructor attributes, postload source references, and Layerwise \`get_numel_loaded\`→\`info.load_numel += num_loaded\`→\`load_numel >= load_numel_total\` logic. The wrapper requires clean exact Git SHA and pinned immutable image and runs read-only no-network/no-GPU/no-model/no-checkpoint with unprivileged bounded runc.
- Existing [actual key map Attempt02 PASS](orcarouter-h38-ct-checkpoint-key-map-attempt02-index-pass-20261011.md) proved **0 input_scale substring key names**, despite two source-registered input-scale Parameters. This does not prove absent runtime initialization, invalid values, or that such params are needed with the actual H38 configuration. Exact installed CT postload source audit **not yet run**; public vLLM v0.29 CT shares concepts but is SHA-different. Do not assert the actual installed code consumes or fails to consume these scales until verified.
- Counted numel reaching a threshold is not evidence of **unique destination-element coverage** without additional loader witnesses. H38 actual callbacks, CopyCounter credit, 8/11 shard lifetime and host stability remain UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE still FAIL, PR #259 Draft/Open and Merge blocked.

### Real H38 CT input-global-scale postload source lifecycle — Attempt 01 PASS_SOURCE_ONLY (2026-10-11)

- [Actual pinned-image source-only Attempt 01 PASS](orcarouter-h38-ct-input-scale-lifecycle-attempt01-source-pass-20261011.md) at clean operator SHA 5456809ab701dd38ef947afdc15bc88a32b22a13 with four pre-pinned CT/layerwise/meta/reload-utils SHA256 matches, unmodified H38 image and no GPU/model/checkpoint payload/host changes.
- Exact installed CT source: w13_input_global_scale torch.nn.Parameter(torch.empty(...)) constructor line 179, registration 183, setter 187 and postload reciprocal 1.0 / layer.w13_input_global_scale at 238; w2_input_global_scale constructor 189, registration 192, setter 196 and reciprocal at 242. Neither constructor explicitly fills a value; **actual initialization, loader callback and consumed values remain UNVERIFIED**. Prior real [checkpoint index-only Attempt02](orcarouter-h38-ct-checkpoint-key-map-attempt02-index-pass-20261011.md) counted zero input_scale-substring names; lack of such names alone does not prove no alternative initialization.
- Layerwise source confirmed five AST sites for buffered weights, original-loader numel accounting, += aggregation, >= completion threshold and _layerwise_process. This is a **source-counter contract** rather than actual CopyCounter or unique destination completion evidence.
- [Updated original source-gate plan](orcarouter-h38-ct-input-scale-lifecycle-source-plan-20261011.md) preserves the independent historical key-map Attempt01 FAIL_KEY_SCHEMA and strict checkpoint metadata ORDER_GATE=FAIL. No actual H38 runtime qualification, host-protection changes, CT meta patch, PR Ready or Merge.

### H38 CT two input-global-scale Parameters in the Layerwise numel target — next source gate (2026-10-11)

- [**New exact-source target-contribution audit and conditional arithmetic**](orcarouter-h38-ct-input-scale-numel-target-source-plan-20261011.md): stdlib-only AST analysis of pinned CT/meta/reload-utils/layerwise installed sources. Verifies two CT input-global-scale registration shapes, SKIP_LOAD_TENSORS literal categories, registered parameter/buffer enumeration and counted-numel Layerwise target/refresh/completion expression. Guarded pinned image/clean Git SHA, no GPU/model, checkpoint, torch import, network or host changes. **Actual operator DGX image run PENDING; repo CI is not an image PASS.**
- Conditional arithmetic for 512 hypothetical registered expert rows: input-scale potential get_layer_size() target contribution 1,536 elements/layer if w13_num_shards=2, or 1,024 if w13_num_shards=1; across 48 layers 73,728 or 49,152. **Not observed missing copy credit, not actual physical expert count, not measured peak memory**. Effective runtime loader, input-scale defaults, duplicate copy counts, layer 8/11 buffers and host stability UNVERIFIED.
- Earlier real [Input-scale reciprocal consumer source Attempt01 PASS](orcarouter-h38-ct-input-scale-lifecycle-attempt01-source-pass-20261011.md) and [Checkpoint index 221,184-key Attempt02 PASS](orcarouter-h38-ct-checkpoint-key-map-attempt02-index-pass-20261011.md) remain independently qualified. Prior `CHECKPOINT_METADATA_ORDER_GATE=FAIL` remains unchanged; PR #259 Draft/Open and Merge BLOCKED.

### H38 CT input-global-scale Layerwise numel target — real DGX SOURCE Attempt 01 PASS (2026-10-12)

- [**Actual operator pinned H38 source-only Attempt01 PASS_SOURCE_POTENTIAL_ONLY**](orcarouter-h38-ct-input-scale-numel-target-attempt01-source-pass-20261012.md): exact executed clean HEAD `956ee0cd2db2a3ca607acd0516d6d35d62f09891`, pinned unchanged H38 image, 4/4 CT/layerwise/meta/utils SHA matches, `source_check_rc=0`, 9/9 static numel-target predicates true. No GPU/model, checkpoint payload or managed/host changes. The prior staging/PENDING text is superseded.
- Source registered `w13_input_global_scale` shape `(num_experts,w13_num_shards)`, `w2_input_global_scale` shape `(num_experts,)`. Neither is in literal `SKIP_LOAD_TENSORS`; Layerwise uses registered param/buffer counts and `load_numel >= load_numel_total`. If 512 runtime registered expert rows, possible counted-target contribution = **1,536/layer (73,728/48) or 1,024/layer (49,152/48)**, conditional on W13 shard branch and registration at enumeration time. These are **NOT** observed deficits, unique writes, loaded values or memory peaks.
- Prior actual [input-scale reciprocal consumer source PASS](orcarouter-h38-ct-input-scale-lifecycle-attempt01-source-pass-20261011.md) and real [221,184-key index-only PASS](orcarouter-h38-ct-checkpoint-key-map-attempt02-index-pass-20261011.md) remain independent. The data source of both input scales, alternative default/write paths, real CopyCounter callbacks, shard 8/11 lifetime and host stability remain UNVERIFIED; strict `CHECKPOINT_METADATA_ORDER_GATE=FAIL` persists. No H38 GPU/model, image rebuild, host protection changes, CT meta patch or PR Ready/Merge.

### Managed lifecycle acceptance M1 — synthetic uninstall preview / read-only DGX inventory staged (2026-10-12)

- [**Current-facing managed lifecycle acceptance matrix**](../../../docs/MANAGED-LIFECYCLE-ACCEPTANCE.md) separates implemented install/uninstall/profile-switch wizard paths, synthetic/CI results, historical Hybrid↔OrcaRouter functional roundtrip, unresolved all-profile/clean-host/destructive E2E and strict RM host stability. The operator runbook is [OPERATIONS.md](../../../OPERATIONS.md).
- `tests/test_uninstall_wizard_preview.py`: actual `uninstall.sh --dry-run` CLI with disposable manifests, English/Korean normal-preserve, selected model/image/swap purge and full-purge **preview**. Model, release and manifest files remain byte-identical. A missing ownership registry yields its documented **no-registry** warning; dry-run is not a live deletion preflight or full-purge authorization. `tests/test_managed_lifecycle_readonly_snapshot.py` checks that new `scripts/lifecycle/inspect-readonly-lifecycle.sh` has exact checkout preflight and only inventory/status/doctor (no install/purge/GPU).
- Existing independent synthetic suites cover fresh/completed install wizard, profile selection, CLI/wizard plan parity, settings and profile-switch transaction recovery, durable ownership and release refresh. This is repo CI and simulation, **not** real DGX snapshot or live all-pairs testing. Implementation CI [38150986080](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38150986080) **SUCCESS, 748/748 tests**; the final docs HEAD CI must be independently checked.
- **Next requested operator evidence:** exact-SHA `QWEN38_LIFECYCLE_AUDIT_TARGET_SHA` + `bash scripts/lifecycle/inspect-readonly-lifecycle.sh` on DGX, which reads model/backend inventory, four transaction statuses and Doctor only. The result is not yet observed. H38 managed runtime remains `FUNCTIONAL=NOT_REACHED`, `HOST_STABILITY=INCONCLUSIVE`; strict checkpoint ORDER_GATE=FAIL and model/GPU rerun BLOCKED. No destructive action, host-monitor change, PR Ready or Merge.

### Real DGX managed lifecycle M1 read-only Attempt 01 — PARTIAL_CHECK_FAILURE, Doctor 5 FAIL 2 WARN (2026-10-12)

- [**Actual operator evidence**](managed-lifecycle-readonly-attempt01-doctor-partial-20261012.md): clean `bbeceaf16c0c4bba4385c38cfead32e5dc243769`; inventory/profile registry and backend listing rc0, four transitions `idle` rc0; **Doctor rc1 (five failures/two warnings)**. Final `MANAGED_LIFECYCLE_READONLY=PARTIAL_CHECK_FAILURE`, `lifecycle_audit_rc=3`, live E2E NOT_QUALIFIED. This **supersedes** previous "read-only snapshot not executed" text.
- Actual failures: `runtime-commit.env` missing or unsafe, Docker container exited, `docker port` no published port, missing enabled monitor PID, health endpoint unresponsive; warnings: legacy OrcaRouter image and enabled but inactive systemd service. Current+previous immutable release/ownership/18 model shards/pinned manifest checks PASS, resource headroom point-in-time healthy. The stopped container could explain some downstream failures, but **stop cause, intended protection and actual configured port bindings remain UNVERIFIED**.
- [Managed lifecycle acceptance matrix](../../../docs/MANAGED-LIFECYCLE-ACCEPTANCE.md): M1 CI/simulation PASS but current DGX Doctor NOT QUALIFIED; M2 destructive live E2E NOT RUN, M3 all-pairs unqualified, M4 H38 blocked. New pinned `scripts/lifecycle/inspect-readonly-runtime-offline.sh` and `tests/test_managed_runtime_offline_readonly.py` stage follow-up **offline read-only** container state/systemd/state-file metadata (no restart, purge, monitor modification, image rebuild or H38 GPU/model). The diagnostic **has not been run yet**; no claim of runtime restored, host-stability PASS, or live E2E completion.

### Actual DGX offline runtime metadata — exit0, Docker OOM false and correct declared loopback (2026-10-12)

- [**Actual offline Attempt 01 source-of-truth evidence**](managed-runtime-offline-attempt01-exit0-no-oom-20261012.md): clean executed `6ce45561640f4069d534cbe04f5064a39095a88a`, offline inspector `COLLECTED_READ_ONLY`, rc0. Docker `exited`, `exit_code=0`, `oom_killed=false`, empty Docker state error, finished **2026-10-07 22:08:34 KST**. `HostConfig.PortBindings` correctly sets `8888/tcp` to **`127.0.0.1:8888`**, whereas `NetworkSettings.Ports={}` while stopped; prior Doctor "no published port" remains readiness FAIL, not proven misconfiguration.
- Systemd `Result=success`, `ExecMainCode=1` (**exited class**, not error code 1), `ExecMainStatus=0`, `inactive/dead`; ActiveEnter **22:08:29 KST**, InactiveEnter **22:18:17 KST**. `runtime-commit.env`, `runtime-stop.env`, `monitor.pid` all ABSENT in later snapshot. **Stop requester/cause, possible protective event, earlier state-file cleanup not proven.** This replaces earlier "offline probe still pending" status in historical index entry.
- Initial actual [M1 inventory+Doctor](managed-lifecycle-readonly-attempt01-doctor-partial-20261012.md) **5 FAIL / 2 WARN** remains unresolved, as does `M1_HOST_HEALTH=NOT_QUALIFIED`. New bounded read-only journal helper (see `OPERATIONS.md`) and synthetic test review only Oct 07 **21:55–22:25 KST** `qwen38-flash-next.service` (≤160 lines, exact clean SHA). Operator journal has **NOT been run yet**; no model/GPU, restart, attestation reconstruction, host protection change or PR Ready/Merge.

### Actual Oct07 managed-runtime unit journal — memory-protection candidate abort CONFIRMED (2026-10-12)

- [**Actual operator source journal Attempt01**](managed-runtime-stop-journal-attempt01-protected-abort-20261012.md): clean DGX `efafe36fcc2e477e9d0cd110e4db275ba40dc489`; bounded historic unit journal `COLLECTED_READ_ONLY`, rc0. **Earlier previous runtime** processed HTTP 200 `/health`, `/v1/models`, and chat shortly before graceful stop. At **22:08:30 KST** it was explicitly stopped for transition; at **22:08:35** candidate started with monitor `protect=1` and previous-container rollback backup, and its readiness check waited through **540/1800s**.
- **22:18:16**: exact `Candidate runtime was stopped by memory protection during startup; leaving managed runtime stopped.` **22:18:17**: `Previous runtime container restored but left stopped after memory protection` and `Runtime transition aborted by memory protection (state=idle)`. This confirms a **protection-triggered managed transition abort and deliberate stopped rollback**, explaining the earlier Doctor inactive/attestation/port/health observation. Earlier Docker exited `exit_code=0`, OOMKilled=false was the **gracefully stopped previous container**, not proof about candidate or safe kernel behavior. The monitor trigger criterion itself and any false-positive remain UNVERIFIED.
- The inspection script output `RUNTIME_STOP_CAUSE=NOT_YET_CLASSIFIED` by design because it only **collects** logs; the evidence document records explicit human-classified source messages without rewriting prior output. Original log bytes and digest not independently captured. The source monitor heuristic could stop after repeated low free with high swap growth; **not proven as the actual Oct07 trigger**.
- One final bounded monitor numeric-sample follow-up is staged, guarded at exact clean SHA and limited to ≤120 selected local Oct07 monitor lines with a ≤64MiB regular-file gate; it excludes arbitrary model/Docker log text. **No operator result yet.** Do not restart service/model, modify protection, fabricate runtime attestation or run destructive uninstall. `M1_HOST_HEALTH=NOT_QUALIFIED`, `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `GPU_MODEL_RERUN=BLOCKED`, `PR_259=DRAFT_OPEN/MERGE_BLOCKED`.

### Actual Oct07 protected stop **numeric trigger branch CONFIRMED** — final bounded monitor sample Attempt01 (2026-10-12)

- [**Actual DGX numeric monitor evidence**](managed-monitor-trigger-attempt01-low-free-swap-growth-pass-20261012.md): exact clean operator HEAD `7e4580bdca4054a788715bdf141e006bbb6b3f59`, `MONITOR_TRIGGER_READONLY=COLLECTED_READ_ONLY`, `monitor_audit_rc=0`, **17** structured messages from 2,242,582-byte local monitor log. **Supersedes previous "monitor inspection pending" / numeric predicate unknown** statements for the historical Oct07 event.
- Monitor actual threshold startup: `noncma-free=2GiB`, `free-gate=10GiB`, `swap-growth=256MiB`, `swapfree=8GiB`, protect count **5**. At **22:17:33 KST**, `noncmafree=2017MiB,swapgrowth=17MiB` → `protect=0/5`. From **22:17:35 to 22:17:43** non-CMA free stayed **below 2GiB** while swap-growth exceeded **256MiB** (`654,1948,2917,3465,3459MiB`) → **1/5–5/5**, then `PROTECT stopping` at **22:17:43**. Non-CMA available stayed **>10GiB** and SwapFree stayed **>8GiB**, so those alternative trigger branches did **not** fire.
- Earlier [service-journal protected abort](managed-runtime-stop-journal-attempt01-protected-abort-20261012.md): **22:18:16** candidate stopped during startup by protection; **22:18:17** previous container restored but stopped and transition aborted `state=idle`. The monitor **policy predicate** is now classified; false-positive-vs-useful protection, NVIDIA RM/kernel OOM, actual H38 readiness and host stability are **UNVERIFIED**. The earlier canonical exited Docker `ExitCode=0 OOMKilled=false` concerned the **previous** gracefully stopped container.
- H38 additional runtime/protection investigation is **closed at this bound**; shift to managed installer/uninstaller/profile switch **non-destructive** acceptance plus separate disposable-host destructive E2E design. M1 live Doctor remains FAIL_5/WARN_2; `M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `GPU_MODEL_RERUN=BLOCKED`, PR #259 Draft/Open and merge blocked. Do not change host monitor thresholds, install/restart models or fabricate attestation.


### Actual DGX offline repeat cross-check and previously confirmed protected rollback (2026-10-12)

- [**Repeated operator DGX offline inspection at checkout `87fb463`**](managed-runtime-offline-repeat-crosscheck-20261012.md): three read-only checks rc0, `MANAGED_RUNTIME_OFFLINE=COLLECTED_READ_ONLY`, **Docker exited/exit 0/OOMKilled=false finished Oct 7 22:08:34.847 KST**, systemd success/inactive 22:18:17 KST, runtime-commit/stop/PID transient files absent. **All observed fields match** the earlier `6ce4556` [offline Attempt 01](managed-runtime-offline-attempt01-exit0-no-oom-20261012.md).
- Combined **previously captured journal** and [numeric monitor samples](managed-monitor-trigger-attempt01-low-free-swap-growth-pass-20261012.md) explain different phases: old predecessor stopped for handover 22:08:30, new candidate started 22:08:35, **protect=5/5** and stop at 22:17:43, managed service abort and **previous container restored STOPPED** at 22:18:16–17. The current Docker exit code and OOM flag describe the restored canonical container (consistent with predecessor), **not the candidate**; neither container identity chain nor kernel/NVIDIA RM OOM is proven by this repeat output.
- This repeat **does not supersede the already resolved historic protected-stop trigger branch** and does not qualify model serving, correctness, host stability or H38. No more H38 runtime or repeated journal hunt is warranted; return to synthetic lifecycle acceptance and an independent disposable-host destructive E2E plan. PR #259 Draft/Open; M1/M2/M3/M4 gates blocked or unqualified.


### Uninstall failure-closed ownership plan and image check — synthetic CI (2026-10-12)

- [**CI-verified source and fixture evidence**](managed-uninstall-fail-closed-purge-plan-docker-20261012.md): partial plan stdout error, partial Docker `ps` error, Docker image inspect daemon outage and explicit image absence semantics. Final **CI #38196834096 SUCCESS 792/792 full and 60/60 synthetic tests**; no DGX local sync at this newer SHA. Prior intermediate CI failures and fixture corrections are recorded.
- [**Independent disposable-host acceptance plan**](../../../docs/DISPOSABLE-LIFECYCLE-E2E-PLAN.md): D0 independent-host guard and D1–D5 full lifecycle and failure/recovery matrix; **NOT_RUN**, no destructive actions on the sole protected DGX.


### Actual DGX operator synthetic uninstall hardening PASS (2026-10-12)

- [**Actual DGX guarded fast-forward and 60/60 synthetic PASS at `02e9c61`**](dgx-synthetic-uninstall-hardening-pass-20261012.md): local Bash syntax PASS; ShellCheck SKIPPED_NOT_INSTALLED; exact SHA and worktree checked. GitHub CI #38197243631 separately PASS 792/792 + ShellCheck. **No live host/service/monitor/installer E2E performed.** The previously reported `87fb463` local baseline is superseded as latest operator-proven local synthetic checkout, but it remains the last actual read-only runtime snapshot.


### Mocked ordered profile-pair switch and rollback matrix — CI only (2026-10-12)

- [**Four-profile 12-ordered-pair transaction matrix**](managed-profile-switch-pair-matrix-synthetic-20261012.md): each pair's noncommitted rollback, correctly attested target finalize, incorrect candidate container-ID refusal then provable previous rollback; identity/no-op and wrong-source rejects. **CI #38204508012 SUCCESS 796/796 full, 70/70 synthetic** including 10 profile-switch methods. **No actual DGX pairwise runtime E2E; M3 NOT_QUALIFIED.**


### Actual DGX profile-pair synthetic 70/70 accepted — 2026-10-12

- [**Operator exact-SHA DGX PASS at `d2e9a1d`**](dgx-profile-pair-synthetic-pass-20261012.md): local 70/70 selected synthetic tests including 10 profile-switch methods and 12 directed profile-pair subtest coverage, with clean checkout and Bash syntax PASS; local ShellCheck SKIPPED_NOT_INSTALLED. Exact-source GitHub CI #38204845533 796/796 full, 70/70 synthetic, ShellCheck PASS. **No live runtime, profile switch or physical host E2E**. Replaces 60/60 `02e9c61` as latest local DGX synthetic acceptance only.


### Actual DGX latest doc-head and profile-switch corruption regression — 2026-10-12

- [**Actual DGX `fb6e0ed` 70/70 synthetic acceptance**](dgx-synthetic-doc-head-pass-20261012.md): guarded clean fast-forward from `d2e9a1d`, Bash syntax PASS, local ShellCheck SKIPPED_NOT_INSTALLED, exact final SHA. This is the latest operator-observed DGX local synthetic checkout.
- [**GitHub-only three profile-switch fault cases**](managed-profile-switch-drift-attestation-synthetic-20261012.md): backup manifest digest mismatch, candidate digest mismatch, and runtime-commit attestation disappearance; **CI #38210907792 799/799 full, 73/73 synthetic PASS**. This latest source has NOT yet been locally run on the DGX. No actual runtime/service/protection change or physical M1/M2/M3/M4 qualification.


### Actual DGX synthetic 73/73, and GitHub source fail-closed orphan-state fix — 2026-10-12

- [**Exact DGX `e18c56a` operator synthetic 73/73 PASS and subsequent orphan-state safety analysis**](dgx-73-and-profile-switch-false-idle-hardening-20261012.md): operator source SHA confirmed, ShellCheck locally SKIPPED; source CI #38212223945 **802/802 full, 76/76 synthetic** for 3 additional valid-idle/orphan/dangling tests and production fail-closed checks. New code not yet tested on the actual DGX; neither synthetic success qualifies a live M1–M4.


### Actual DGX 76/76 local synthetic and prepare-stage artifact preservation (2026-10-12)

- [**Operator exact-SHA DGX `9220624` 76/76 isolated synthetic PASS, followed by source-only fail-closed prepare orphan check**](dgx-76-and-prepare-orphan-guard-20261012.md): guarded clean fast-forward from `e18c56a`, all seven allowlisted modules passed (16 profile-switch methods), Bash syntax PASS, local ShellCheck SKIPPED; exact HEAD/worktree verified. Matching source [CI #38212708550](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38212708550) SUCCESS, 802/802 full + 76/76 synthetic. Subsequent `prepare` guard/test change is **not** part of that actual DGX run and needs separate CI and local verification. No model, service, host protection or live E2E change.


**GitHub follow-up CI confirmation (2026-10-12):** [#38215072213](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38215072213) at exact new source HEAD `51e85f6578ee0694a13964f700f30e854f17c020` passed **803/803 full Python and 77/77 selected synthetic**, with 17 profile-switch tests, Bash syntax, ShellCheck, compilation and whitespace PASS. The sole DGX latest actual *isolated synthetic* evidence remains **76/76 at `9220624`**. No new live M1/M2/M3/M4 acceptance; PR #259 remains Draft/Open/Unmerged.


### New actual DGX 77/77 profile-switch prepare-stage synthetic PASS (2026-10-12)

- [**Operator guarded DGX `1283b1a` exact-SHA 77/77 isolated synthetic PASS**](dgx-77-prepare-orphan-synthetic-pass-20261012.md): actual clean fast-forward from `9220624`, seven selected modules including **17 profile-switch** tests with prepare-stage orphan evidence preservation, Bash syntax PASS, local ShellCheck SKIPPED_NOT_INSTALLED, final `DGX_PREPARE_ORPHAN_SYNTHETIC_COMPLETE` and clean exact HEAD. Same-source CI #38215504822 SUCCESS 803/803 full, 77/77 synthetic plus ShellCheck. Supersedes prior local synthetic 76/76 as latest, **not** any real M1–M4 acceptance or host protection disposition.


## Disposable D0 offline evidence precheck — code staged, not host-qualified (2026-10-12)

A new **offline-only** reviewer, `disposable-d0-preflight.py`, validates two
explicit operator-provided JSON files using Python stdlib only. It never reads
live Docker, systemd, host identity, Git or model state; it never runs commands
on any host. Required policy: exact SHA and repository, **nonempty protected
machine-id hash and Docker daemon denysets**, forbidden production roots.
Required inventory: separately identified disposable machine/daemon, clean
exact SHA + origin, owner disposable declaration, restore point, isolated
non-default Docker context without external users, nonoverlapping throwaway
model/log/work roots, bounded owned synthetic model, non-production service
unit, and no pending lifecycle transactions.

Run **only against an independently assembled, reviewed inventory**:
`python3 disposable-d0-preflight.py --policy <policy.json> --inventory <inventory.json>`.
No real protected machine IDs, daemon IDs, credentials or private mount
inventories belong in Git history or CI logs. Inputs are treated as
**untrusted assertions**: success prints
`D0_STATIC_REVIEW=READY_FOR_INDEPENDENT_REVIEW` but always
`D0_ADMISSION=NOT_GRANTED` and `D0_LIVE_E2E=NOT_AUTHORIZED`.
Any incomplete/mismatched evidence fails closed with exit 2. A passing
offline check is **not** permission for D1–D5; independent operator
attestation, read-only on-host cross-check and explicit disposable-host
authorization remain mandatory. Neither current DGX nor M1/M2/M3/M4
qualification is changed.


### D0 independent-host offline policy review — synthetic CI only (2026-10-12)

- [**D0 offline preflight source and nine fail-closed fixture regressions**](disposable-d0-offline-preflight-ci-20261012.md): [CI #38217170909](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38217170909) **SUCCESS 812/812 full and 77/77 selected**, shell/Python/whitespace PASS. Reads only supplied JSON and **never grants live admission**. No disposable real-host D0 attestation or D1–D5 E2E has run; DGX protection and M1–M4 unchanged.


## D0 independent-host on-host read-only cross-check (source only; 2026-10-12)

A new conservative `disposable-d0-readonly-crosscheck.py` requires the
`--ack-independent-disposable-host` flag plus the existing strict
`--policy` and `--inventory` JSON. The **sole protected DGX is not a
permitted target**. It first validates the offline D0 policy and compares a
hashed real machine identity against the inventory and protected denyset
**before** any Docker/systemd calls. It then performs bounded read-only
Git HEAD/origin/worktree, candidate path realpath and mountpoint, Docker
context/daemon/empty-container, and dedicated disposable service-unit checks.

The collector does not probe without the explicit independent-host
acknowledgement, does not ask for sudo, does not modify files or host
configuration, and never installs/uninstalls or starts models. Its JSON
output excludes raw host identities, secrets, mounts and container IDs.
The output is `ON_HOST_READ_ONLY_ASSERTION_CROSSCHECK`, with
`d0_admission=NOT_GRANTED` and `d1_d5=NOT_AUTHORIZED` **even after
all observed fields match**. A missing daemon, unknown service response,
realpath/mount drift, protected identity or unclean Git state fails closed.

This cross-check **does not independently prove** owner consent, absence of
external Docker users, isolation of the underlying daemon, mount sources
outside the selected roots, or restoration/snapshot viability. Independent
D0 trust review and explicit authorization remain necessary. Current status:
**source and fixture tests only; not executed on any physical disposable
host or the protected DGX; M1–M4 and D1–D5 unchanged**.

### D0 on-host read-only policy cross-check — mocked GitHub CI (2026-10-12)

- [**Read-only D0 crosscheck implementation, 12 fixture cases and first-failure correction**](d0-onhost-readonly-crosscheck-ci-20261012.md): first CI #38218386709 **FAIL 1/824** (fake Docker-outage exception type), corrected CI #38218663210 **SUCCESS 824/824 full and 77/77 bounded synthetic** with shell/Python/static PASS. No real disposable host collection, and none on the protected DGX. D0 live admission remains NOT_GRANTED; D1–D5 NOT_RUN.


### D0 parent mount and Docker endpoint trust-boundary hardening (2026-10-12)

- [**D0 parent-mount, Docker context/socket, and Git optional-lock refusal evidence**](d0-parent-mount-docker-endpoint-guards-20261012.md): source CI [#38266470002](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38266470002) **SUCCESS 828/828 full, 77/77 selected**, follow-up CI [#38267015272](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38267015272) **SUCCESS 829/829 full, 77/77 selected**; 17 D0 fixture methods in full CI only. No actual disposable host observed, no DGX source synchronization, and no M1–M4 promotion.


### Git/Systemd environment and Docker socket D0 trust boundaries — 2026-10-13

- [**Source-only D0 observation redirection and protected-socket refusal evidence**](d0-env-redirection-and-socket-boundaries-20261013.md): [GitHub CI #38315552300](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38315552300) **SUCCESS 834/834 full, 77/77 selected**, 22/22 D0 fixture methods, shell/compile/whitespace PASS. Does not qualify D0 on a real independent disposable host or the single protected DGX.


### D0 exact JSON receipt binding — 2026-10-13

- [**D0 receipt SHA256 binding, no-follow parser and explicit replay limitations**](d0-receipt-input-binding-ci-20261013.md): [GitHub source CI #38316973840](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38316973840) **SUCCESS 845/845 full Python, 77/77 selected synthetic**; 11 new offline fixture tests. No real-host identity attestation, signed approval, DGX run or D1–D5 E2E.


### D0 external owner/isolation/restore assertion chain — 2026-10-13

- [**Source-only D0 owner, Docker exclusivity and restore proof hash-review evidence**](d0-external-owner-isolation-restore-evidence-ci-20261013.md): [GitHub CI #38317915217](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38317915217) **SUCCESS 860/860 full, 77/77 bounded synthetic**; 15 new external-evidence fixture tests. Identity authenticity, independent daemon isolation and actual restore remain unverified, no live D0 approval.
