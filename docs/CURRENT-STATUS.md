# Current project status

This document is the canonical short-form status entry point for the repository.
Dated benchmark/evidence documents preserve what was known at the time of each run;
use this file plus `scripts/benchmark/evidence/README.md` when deciding what is true
**now**.

Last synchronized: 2026-10-07. The version on `main` is authoritative; do not encode a
specific "last documentation PR" or commit SHA here because the synchronization change
itself would make that marker stale as soon as it is merged.

Current-facing repository documentation (`README.md`, `OPERATIONS.md`,
`docs/ARCHITECTURE.md`, `scripts/model/README.md`, and
`scripts/runtime/README.md`) should agree with this status. Dated evidence remains
historical even when it contains then-current words such as `pending`, `next`, or
`current`.

## Physical DGX B4: exact image/container and memory pre-start snapshot (2026-10-13)

The operator completed a clean exact-SHA (`b35d0f3d7840d00c55f4c633813e88ac367c6373`) B4 **read-only** pre-start snapshot with `M1_PRESTART_READONLY=COLLECTED`. Immutable `current` still resolved to `ff67bab3`; legacy OrcaRouter `vllm-skinny-tp1:v1` image and retained Docker container matched; existing container ID `f6bfee5a4217...` was EXITED/exit0/non-OOM; rollback name absent; monitor/protect remained `1`; MemAvailable approximately **118.2 GiB**, SwapFree approximately **143.1 GiB**, PLE swap file active, systemd inactive/dead/success. This is **B4=COLLECTED_PRESTART_READONLY**, NOT a successful model start or strict RM host-stability measurement. [Exact operator B4 evidence and installed-release code review](../scripts/benchmark/evidence/dgx-b4-m1-prestart-readonly-20261013.md).

The installed `ff67bab3` legacy service restart is **not an in-place Docker restart**: the previous container is renamed to rollback and removed on successful candidate commit; general failure recovery may start an intentionally stopped predecessor. Thus it is only reversible in the managed logical sense, *not preserving the exact original container ID*. Preserve the existing Docker object if exact-ID retention is required; the B4 observation alone does not authorize a live start. Current release monitor logic also differs from the archived candidate's swap-growth trigger, so keep version-specific semantics separate. **M1 live NOT_QUALIFIED, M2 NOT_RUN, M3 NOT_QUALIFIED, M4/H38 BLOCKED, D0 NOT_GRANTED, PR #259 Draft/Open/Unmerged.**

## Physical DGX B3 completed: exited managed runtime and all state markers absent (2026-10-13)

On exact clean operator checkout `b35d0f3d7840d00c55f4c633813e88ac367c6373`, the **existing read-only runtime-offline collector completed all three probes rc=0** with final `MANAGED_RUNTIME_OFFLINE=COLLECTED_READ_ONLY`; the subsequent full service unit and eight state-marker existence checks also reached `IMMUTABLE_SERVICE_INSPECTION=COLLECTED_READ_ONLY`. Docker predecessor EXITED/ExitCode=0/OOMKilled=false, configured `127.0.0.1:8888` bind exists but running port map empty, systemd loaded/inactive/dead with `Result=success`, service unit runs immutable `current`, and `runtime-commit.env`, `runtime-stop.env`, `monitor.pid` plus four transition markers and the adoption marker are ABSENT. This **supersedes only the B3 partial collection status** documented later below, not the earlier B2 Doctor failures. [Complete operator evidence and installed-release safety review](../scripts/benchmark/evidence/dgx-b3-readonly-runtime-unit-complete-20261013.md).

The historical Oct 7 monitor-protected managed candidate abort / predecessor left stopped remains the best-supported lineage. Source of the **installed** immutable `ff67bab3` release confirms protected abort leaves a stopped predecessor, but **ordinary rollback/recover may start the predecessor** and its unit uses direct Docker-name `ExecStop` rather than newer attested stop helper. No blind legacy `systemctl restart` is authorized by B3. First review exact installed service identity, preflight, rollback/stop, container ownership and protection invariants; only then construct a bounded reversible legacy OrcaRouter M1 plan. **B3=COLLECTED_READ_ONLY; M1 NOT_QUALIFIED; M2 NOT_RUN; M3 NOT_QUALIFIED; M4 H38 BLOCKED; D0 NOT_GRANTED; PR #259 Draft/Unmerged.**

**Cross-session continuity:** [stable handoff prompt template](SESSION-HANDOFF-PROMPT.md); at the start of every session read this status and fresh GitHub CI/PR metadata. Do not freeze a feature HEAD in the template.

## Physical DGX stage B2: read-only Doctor collected, stopped baseline (2026-10-13)

Operator-supplied exact-SHA `b35d0f3d7840d00c55f4c633813e88ac367c6373` lifecycle inventory found **7 successful read-only sections** and Doctor **5 FAIL / 2 WARN** (`doctor_readonly rc=1`; final `PARTIAL_CHECK_FAILURE`). Manifest complete, OrcaRouter selected, four transaction states idle, 18 checkpoint shards complete and memory protection enabled. Container remained EXITED, systemd INACTIVE, attestation MISSING, monitor PID absent and health unreachable. Non-CMA available **118 GiB**, free **79,620 MiB**, swap free **143 GiB**, model filesystem free **104 GiB**. This is **B2=COLLECTED_PARTIAL**, not M1 live health. The missing published port was observed on an exited container; it is not on its own a host-bind configuration failure. [Full exact-source B2 operator evidence](../scripts/benchmark/evidence/dgx-b2-readonly-lifecycle-doctor-partial-20261013.md).

The existing October 7 managed candidate protected abort / stopped-predecessor lineage remains relevant, but a new healthy live runtime, an intentional current stop, and strict RM stability are **not** proven by B2. First review installed immutable release and service identity, rollback/stop bounds, and historical protection evidence; only then consider a reversible **legacy OrcaRouter** baseline using the existing managed service path with protection unchanged. Do not use a raw Docker start, rewrite attestation, silently refresh image defaults, or conflate this with H38. M1/M3 remain NOT_QUALIFIED, M2/D1-D5 NOT_RUN, H38/M4 BLOCKED, D0 NOT_GRANTED and PR #259 Draft/Unmerged.

## Actual DGX release-path and legacy service-unit interpretation (2026-10-13)

After B2, the operator inspected the already-verified DGX checkout `b35d0f3`. The immutable `current` release was `ff67bab3` with previous `a8aeca47`, but `install.env` retained a mutable checkout for `INSTALL_ROOT`. A one-off comparison printed `MISMATCH_STOP`; **this comparison is not a valid generic gate** because the installed `ff67bab3` release updater supports an explicit immutable `--runtime-root` service override and its runtime runner derives execution root from the installed script. The observed unit starts from immutable `current`; the B2 Doctor previously verified release integrity and unit path. The observed `ExecStop` was the legacy direct Docker-name stop, consistent with the exact installed release but not the latest feature branch's attestation-checked service stop. Output ended in a `systemctl` pager before state markers and completion marker; follow-up status is **PARTIAL_READONLY**, not an installation failure or new live qualification. [Dated physical-DGX evidence and source-level interpretation](../scripts/benchmark/evidence/dgx-b3-release-path-and-systemd-partial-20261013.md).

Use `--no-pager` and the existing read-only offline diagnostic for the remaining information. Do not alter the manifest or systemd unit just to force equality. Live M1 NOT_QUALIFIED, H38/M4 BLOCKED; PR #259 Draft/Open/Unmerged.

## Managed model profiles

| Profile | Registry status | Managed state | Current host-stability interpretation |
|---|---|---|---|
| `orcarouter` | stable/default/installable | primary managed profile; 16 GiB KV resilience default | stable project default; strict RM evidence remains authoritative for any new run |
| `nvidia` | experimental/installable | optional comparison path | not promoted to stable |
| `mazinb` | experimental/installable | live managed activation exercised; 16 GiB KV resilience value | managed readiness can pass while strict RM evidence still makes the run HOST-STABILITY FAIL |
| `orcarouter-hybrid` | experimental/installable/generated H6 | warm/reuse and managed round-trip functionally validated | FUNCTIONAL PASS / HOST-STABILITY FAIL under strict RM semantics |
| `lychee888` | planned/non-installable | no qualified managed path | not selectable |

Installability is an implementation property, not a qualification claim.

## Strict host-stability rule

FUNCTIONAL and HOST-STABILITY classifications are separate.

> Any confirmed NVIDIA RM `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` in a valid
> measured run is HOST-STABILITY FAIL, even when fallback recovers and the runtime
> reaches READY.

A 16 GiB KV cache is a resilience/default setting for the relevant managed profiles.
It is **not** a proven fix for the NVIDIA RM system-memory allocation mechanism.

## R9–R32 allocator/localization closure

The current engineering closure is indexed in
`scripts/benchmark/evidence/README.md`, ending at
`orcarouter-r23-r32-allocation-localization-closure-20261006.md`.

The supported chain is:

```text
first model construction / repeated decoder construction
  -> direct NVIDIA RM system-memory allocation
  -> 64 KiB / order-4 physical-page demand
  -> node0 Normal / Unmovable pressure with Movable fallback/pageblock stealing
  -> failed high-order acquisition
  -> rollback
  -> immediate order-0 fallback
  -> recoverable NV_ERR_NO_MEMORY
```

Important boundaries:

- R21/R22: common early physical-page burst is roughly 75 GiB over about five seconds;
  later PLE/swap pressure is separable from this burst.
- R23: the measured endpoint is direct NVIDIA RM system allocation through
  `nv_alloc_pages` / `nv_alloc_system_pages`; selected UVM allocation boundaries do
  not own the measured burst.
- R24: H6 W4A16 plus forced 16 GiB KV does not remove the structural burst.
- R25–R28: the burst localizes to first model construction, then predominantly to the
  Qwen4Exp decoder construction cadence rather than long checkpoint fill.
- R29/R29b: repeated `800 MiB -> 400 MiB` RM pairs form a strict adjacent cadence.
- R30: all 48 repeated 400 MiB events localize exactly to packed `w13_weight`
  construction.
- R31: each paired 800 MiB event occurs before ModelOpt-MoE create-weights begins.
- R32: exact-image source inspection finds no separate explicit direct pre-create
  model-weight allocation that can be promoted as the 800 MiB owner.

The best-supported interpretation for the 800 MiB family is therefore a discrete
lower/global CUDA/NVIDIA-RM backing/reservation growth event temporally induced by the
repeated decoder construction cycle. This is a mechanism-level inference, not proof of
the exact proprietary lower allocator call.

Do not restart model-prefix/Linear/attention/hyper-connection marker expansion for the
800 MiB ownership question unless a new actionable hypothesis invalidates the closure.

## H38 determinism track

The H38 decoder-only runtime is separately qualified through
`scripts/runtime/orcarouter-v029.sh` and summarized in `docs/H38-DETERMINISM.md`.

That historical qualification is **not** the same as transactional
installer/systemd managed-service qualification. The current H38 integration branch
implements the candidate `orcarouter` managed image/defaults, clean-host H38 image
construction, H38 runtime controls, preflight/doctor provenance checks, asset
inventory, and an atomic cross-release same-profile refresh transaction.

The earlier two-stage assumption — update immutable code, require the persisted
legacy CPU-offload runtime to become READY, then refresh the profile image — is
superseded. The matched PR-base-main control reproduced the same memory-protection
stop in that legacy intermediate state, so it is not a valid H38 discriminator.
The new `release-profile-refresh-transition.sh` path binds the qualified target
release and H38 candidate manifest before the single managed-service replacement.
The service runner writes target attestation while deferring runtime-transition commit,
so the previous rollback container remains available until the outer lifecycle commit.
Recovery therefore owns the release-pointer + manifest + runtime tuple rather than only
release and manifest state. Rollback is also identity-safe at the service boundary:
`ExecStop` stops only the attested container ID, a still-running restored predecessor
is reattached without replacement, and a safety-stopped predecessor is left stopped
instead of being cold-started merely to recover service state. Startup interruption
recovery also consumes the restored-runtime handoff inside the already-running target
runner, so changing `current` back to the previous release cannot cause a blind
systemd retry into an older runner before adoption completes.

This is **implementation state only**. The hardened atomic transaction now also
quiesces the candidate monitor before predecessor restoration, proves rollback topology
before mutation, restores the predecessor monitor from the restored release policy, and
uses a guarded post-migration follow-up runner. The latest implementation/test head
`acb69b83e28b593e434d2e5e51b7f9b4584b6aad` passed GitHub Actions
`37622310894`: shell syntax, ShellCheck, Python compilation, **581/581 unit tests**,
and whitespace all passed. Live managed H38 acceptance remains a separate gate. The guarded migration entry is
`scripts/benchmark/run-h38-managed-migration-gate.sh`; it requires an exact clean
target SHA and does not use the retired legacy-READY intermediate. After that gate
passes, `scripts/run-h38-managed-followup-gates.sh` binds the same migration evidence
baseline to managed-alias determinism, the >=90% decode-performance gate, a supported
managed-service replacement/restart, doctor/attestation checks, and one strict RM
follow-up window. The first live run through the new atomic transaction was executed on exact branch head
`05748a9c9a2b206a536b454dc5d662d7750913db`. It reached the H38 managed
candidate directly (PLE mmap, exact QSA, decoder-scope image) but memory protection
stopped the candidate during startup before READY. The guarded gate therefore recorded
`FUNCTIONAL=NOT_REACHED`, `HOST_STABILITY=INCONCLUSIVE`,
`kernel_window_rc=0`, `rm_oom_count=0`, and `protected_stop=1`. Recovery restored
the previous release + manifest + runtime tuple while preserving the safety-stopped
runtime instead of forcing a legacy cold restart. This is not a managed-H38 pass and
does not authorize the follow-up determinism/performance/restart gate. The terminal
summary did not retain the exact monitor threshold samples, so the gate now also extracts
the monitor start/warning/protection lines into a compact evidence file without changing
any protection threshold or strict RM classification rule.

The preserved trigger lines were subsequently recovered. Across the counted protection
window, non-CMA available rose from `27111 MiB` to `29909 MiB`, non-CMA free stayed
around `0.9-1.15 GiB`, swap growth increased from `654 MiB` to about `3.46 GiB`,
and swap-free remained above 139 GiB. The 10 GiB absolute available gate therefore did
not trigger; the stop came from the swap-growth arm while reclaimable available memory
was increasing. This matches the monitor condition family already known to create a
normal-cold-load false positive, but historical RM failures can also begin with high
available + low free. The current evidence is therefore classified as a **monitor
heuristic collision**, not a proof that the H38 candidate was safe to continue.

H38 must not be described as promoted into the managed runtime until
lifecycle/restart/doctor, managed-alias determinism, performance, and strict RM
host-stability gates in
`scripts/benchmark/evidence/orcarouter-h38-managed-integration-plan-20261007.md`
are recorded as passing.

## Memory monitor caveat

The current runtime monitor is CMA-aware and implements the repository's present
protection heuristic. In particular, low non-CMA free memory can become
protection-significant when non-CMA available is low or swap consumption since monitor
start increases by the configured gate (currently 256 MiB in the helper defaults).

This heuristic is **not a proven discriminator for RM failure**. Live Hybrid cold-load
evidence has shown that the 256 MiB swap-growth arm can produce a false-positive
protected stop during otherwise normal startup. The first atomic H38 managed attempt
reproduced the same signal family: low non-CMA free plus swap growth while non-CMA
available increased through the counted window, with `rm_oom_count=0`. Historical
PR #245 evidence also shows that real RM failures can occur while reclaimable available
memory is still initially high, so high available alone cannot suppress protection.
Treat the current state as a heuristic collision requiring a stronger discriminator,
not as justification to disable or simply raise the swap-growth gate. The next isolated
A/B keeps the protective monitor and H38 runtime identity unchanged but disables
speculative MTP only (`SPEC=none`) to test whether the later MTP materialization is what
crosses the protection boundary. The runner requires the recovered managed predecessor
to remain stopped, so it does not cold-start the legacy runtime merely to establish an
experiment baseline. This is a mechanism discriminator, not a production configuration. The isolated runner passed static CI on
`3d4eadcf2ce60c55b600d9e3ecd4143d061355de` in run `37633676272` with
**587/587 tests**. The first 2026-10-08 operator invocation was setup-invalid before
candidate start because the harness incorrectly equated manifest `INSTALL_ROOT` with
the immutable current-release root. The installer records the source repository root in
`INSTALL_ROOT`; immutable runtime identity is the separate verified release pointer.
The harness was corrected without changing runtime or protection policy. No live SPEC=none result has yet been recorded. A second 2026-10-08 invocation was
also setup-invalid before candidate start: the final negative Docker-existence guard
in the baseline function returned 1 in the required "container absent" state, and
top-level `set -e` exited silently. The harness now uses explicit conditional guards
and an explicit successful return. Attempt 03 then reached candidate creation but exposed a here-document control-flow
bug in the post-start identity validator: the intended shell `fail` line was consumed
as Python stdin, so exact candidate identity was not proven. That attempt is harness
invalid regardless of any later runtime outcome. The validator is now explicit
`if ! python3 ...; then fail; fi`, and `VALID_CLEAN` additionally requires a
persisted successful identity proof. Strict RM kernel evidence remains the classification
source of truth.

Attempt 03 also retained a useful non-gating diagnostic sequence: the launched
candidate reported `SPEC=none`, completed all 18 main checkpoint shards, and then
recorded four strict RM `_memdescAllocInternal / NV_ERR_NO_MEMORY` events. The first
RM event occurred before the monitor's first counted protection sample; protection
stopped the candidate only afterward. This materially weakens MTP materialization as
the sole cause and distinguishes this run from the earlier no-RM monitor-heuristic
collision. Because exact identity was not attested, one corrected rerun is still
required before rejecting MTP causation formally.

The corrected attempt 04 now provides the formal MTP-discriminator result. Exact
candidate identity passed (`identity_validated=1`), `SPEC=none` was confirmed, but
the unchanged monitor again stopped the candidate during early shard loading.
`rm_oom_count=0`, `protected_stop=1`, and the result is
`PROTECTED_STOP`: FUNCTIONAL NOT REACHED / HOST-STABILITY INCONCLUSIVE. non-CMA
available stayed about 40-45 GiB while low non-CMA free plus several GiB of swap growth
armed protection. Therefore MTP materialization is **not sufficient to explain the
managed-H38 protected-stop boundary**. The next step is offline/read-only trajectory
comparison against preserved strict-RM failures before any monitor-policy change.

## H38 allocator/protection observability — 2026-10-08

The valid MTP-off discriminator attempt 04 established that removing MTP
is insufficient to avoid the H38 protected-stop boundary. The exact
production-shape `SPEC=mtp k=2` allocator/protection attempt 01
also yielded a valid `PROTECTED_STOP` at `2026-10-08 11:06:47 KST`:
`FUNCTIONAL=NOT_REACHED`, `HOST-STABILITY=INCONCLUSIVE`,
`rm_oom_count=0`, `OOMKilled=false`, collector and kernel window valid.
The external memory protection policy was not changed. The managed
predecessor remains stopped.

The operator's **complete raw archive** was subsequently analyzed
offline; canonical result:
`scripts/benchmark/evidence/orcarouter-h38-allocator-protection-offline-analysis-20261008.md`.
The read-only analysis uses 502 pre-event 1 s fast samples and 101
pre-event 5 s slow samples, explicitly excluding 40/8 post-event samples.
The dominant Normal order-4+ collapse was
**-74,508.750 MiB** from `01:59:02.196334Z` to
`01:59:07.196252Z` (same window global MemFree
**-75,157.664 MiB**, node0 Normal free **-75,157.254 MiB**,
MemAvailable **-76,158.621 MiB**, SwapFree **0.000 MiB**).
Using the deliberately non-overlapping R21/R22 meminfo category set,
conventional resident growth was **+396.148 MiB**, giving an
approximate **+74,761.516 MiB core-unexplained physical-page loss**.
The identical-scale R21/R22 maxima were +75,174.387 and +75,138.043 MiB
over five seconds. This establishes a reproducible early-host-pressure
pattern but does **not** attribute exact NVIDIA RM/UVM page ownership
or authorize a safety threshold change.

The full timestamped phase log corrects an earlier summary: only
**14/18 shards were logged complete BEFORE the protection event**;
`15/18` was logged `6.95 s AFTER` protection had triggered.
The dominant physical-page burst occurs around the initial `0/18`
startup marker and before the first shard completion, not at shard 15.
The previous excerpt-only report is superseded by this full-history
phase correlation.

Original live runner exit-summary consistency was fixed and CI
`37718076547` succeeded with 596/596 tests; documentation
synchronization CI `37718270884` likewise passed 596/596.
A separate archived-evidence offline analyzer and regressions make
the full-history result reproducible. The analysis is read-only and
requires no new DGX experiment.
The full-history offline analyzer and synthetic regressions were committed
at `a9f4ec6658653b49cf908b567aea608e831313d6` and qualified by
GitHub Actions `37744164668` **SUCCESS, 599/599 unit tests**, shell syntax,
ShellCheck, Python compile and whitespace PASS.

The **R11/R23–R32-to-H38 mechanism transfer review** is now recorded at
`scripts/benchmark/evidence/orcarouter-h38-r23-r32-allocator-mechanism-transfer-20261008.md`.
R23 directly localized its historical same-scale burst to NVIDIA RM
`nv_alloc_pages` / `nv_alloc_system_pages`: 74,537.938 MiB logical
order-4 activity over a 75,083.652 MiB physical residual (99.273191%)
**in that R23 measurement**. H38's similar 74,761.516 MiB early
residual supports transfer of the **RM/backing-growth mechanism
hypothesis**, but **H38 did not capture its own RM call trace** and
the H38 physical residual is not driver-owned bytes. R30/R31 closed
the repeated 400 MiB (packed w13) and pre-MoE 800 MiB request
positions; R32's negative direct-allocation source check covered an
exact R28 image, not the H38 image. H38 carries H11/H12 patched
compressed-tensors semantics, so an exact-H38-image source check
requires separate evidence if a concrete mitigation warrants it.
The R23–R32 line of model-component prefix tracing stays closed;
**no new live R33 is authorized**.

The **exact-H38-installed-image source check has now been executed**
on the DGX Spark, using the guarded SHA
`1a4416581f4064baa110fc83947c442c360c4689` and the
`vllm-orcarouter-v029-h38-decoder-scope:v1` image
(`sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`).
Operator output closed `H38_EXACT_IMAGE_SOURCE_PREFLIGHT=PASS`,
`H38_EXACT_IMAGE_SOURCE_CONTRACT=PASS`, `source_check_rc=0`,
and `image_identity_unchanged=YES`.
Canonical DGX result:
`scripts/benchmark/evidence/orcarouter-h38-exact-image-source-contract-result-20261008.md`.
The original guarded preflight and static-check plan remains at
`scripts/benchmark/evidence/orcarouter-h38-exact-image-source-contract-plan-20261008.md`.

The H38 installed source retained both packed `torch.empty`
allocations under H11 `ModelWeightParameter`, H12 object-preserving
post-load rename, H38 Humming/Marlin controls and **the R32 precreate
source contract now replayed on the exact H38 image**.
The direct precreate allocation syntax count was **0** in both
inspected factory/routed scopes. This only rules out the checker's
specific explicit syntax, not indirect allocations. There was no
GPU/model load, managed-service replacement or protection change.
**This is a source-contract PASS only. RM mitigation is unproven;
the original H38 protected stop remains FUNCTIONAL NOT_REACHED /
HOST-STABILITY INCONCLUSIVE.** The checker CI `37747053983` and
docs CI `37747347746` both passed **606/606 tests**.
No R33 live trace or managed promotion is authorized.

## H38 CT deferred-w13 feasibility — 2026-10-08

The historical M1 branch `exp/m1-deferred-meta-w13`
(`4d72f8750e8a7beaec96a869e2dbfeaa7d4c747a`) is a
**ModelOpt/H6/R28 prototype**, not a tested H38 CT mitigation.
It defers the `ModelOptNvFp4FusedMoE.w13_weight` allocation with
`device="meta"` and native layerwise processing. The current H38
production image instead uses H11/H12
`CompressedTensorsW4A4Nvfp4MoEMethod` with
`w13_weight_packed` and post-load aliases. A direct M1 patch
transplant is invalid.

The implementation passed GitHub Actions `37778807130`:
**SUCCESS, 613/613 unit tests**, shell syntax, ShellCheck,
Python compilation and whitespace PASS.

**H38 CT Meta static prerequisites: VALID DGX SOURCE PASS.** The
operator ran the unmodified guarded checker at
`ac58309620ace2213df68ebf06b2c18b9592f394` on
`vllm-orcarouter-v029-h38-decoder-scope:v1` image ID
`sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`.
Both `H38_CT_META_STATIC_PREREQUISITES=PASS` and
`H38_CT_META_SOURCE_PREFLIGHT=PASS` were observed; image
identity unchanged, no model/GPU launch, service/protection change.
Canonical result:
`scripts/benchmark/evidence/orcarouter-h38-ct-meta-w13-source-prerequisites-result-20261009.md`.
Installed CT class `uses_meta_device` direct declaration was
**NO**; base-loader/layerwise wrapper/materialization functions were
`SOURCE_PRESENT`; original H11 packed `torch.empty` persists,
H12 aliases pass. **No actual CT meta patch/materialization or RM
reduction is established.** The checker and synchronization static
CI `37778807130` / `37779107553` passed **613/613** tests.

The metadata tool implementation was statically qualified at
`b476441899d07d04e9db3669ccd881f4351ef15e`: GitHub Actions
`37822913604` **SUCCESS, 620/620 unit tests**, shell syntax,
ShellCheck, Python compilation and whitespace PASS.
The production checkpoint metadata attempt 01 on
`551da2c603f2e83c6aedb4668e831e67dae82da6` was
**PREFLIGHT INVALID** before any shard result, due to Python
`No usable temporary directory`. Canonical record:
`scripts/benchmark/evidence/orcarouter-h38-checkpoint-metadata-order-attempt01-invalid-tempfile-20261009.md`.
The private `/tmp` 64 MiB `tmpfs` repair passed
static CI `37882840040` and `37883026595`,
**622/622 tests**.

**Attempt 02: VALID METADATA ANALYSIS / ORDER_GATE FAIL** on
`eadaaeefbc23abf428e880890537ca26ea162f9d`,
with the same pinned H38 image
`sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`.
The isolated tempdir worked. The index mapped **18 files: 17 numbered
`model-XXXXX-of-00017.safetensors` shards plus
`model-mtp.safetensors`**, 223,046 tensor keys, 221,186 routed keys,
all 48 routed layers. However, layers **0, 8, 11 were revisited**
and the maximum routed interval overlap was **3**.
The strict metadata-order gate is **FAIL**, not checkpoint
corruption or runtime materialization failure; canonical result:
`scripts/benchmark/evidence/orcarouter-h38-checkpoint-metadata-order-attempt02-gate-fail-20261009.md`.
Routed disk bytes total **72,981,184,512**; both theoretical
release-at-last-routed and release-at-last-layer-key scenarios
reported **6,448,748,544** bytes. These are **not**
observed runtime RAM/GPU peaks.

The outer runner previously misclassified a completed
`H38_CKPT_METADATA_ORDER_GATE=FAIL` as
`H38_CKPT_METADATA_PREFLIGHT=INVALID` because the
Docker command's non-zero exit was collapsed. The follow-up
classifier will preserve exit **3 = ORDER_GATE_FAIL**, while retaining
**2/infrastructure failure = INVALID**. Header-only diagnostics
will report the concrete first/last shard positions of the 0/8/11
revisits and separate numbered model files from auxiliary MTP.
The follow-up source/diagnostic commit
`51850e28230c760dadac8fd86268d949b7623345` passed
GitHub Actions `37883805274`: **SUCCESS / 624 of 624 tests**,
shell syntax, ShellCheck, Python compilation and whitespace PASS.
**Attempt 03: actual DGX revisit diagnostic observed**, running
`f875aa2ea141e004fe2c0b37174bd275d9df39a1` against the
unchanged H38 image and canonical OrcaRouter checkpoint.
`H38_CKPT_METADATA_ORDER_GATE=FAIL` and
`H38_CKPT_METADATA_PREFLIGHT=ORDER_GATE_FAIL` were correctly
reported; exit code **3**. The exact source and run spans are in
`scripts/benchmark/evidence/orcarouter-h38-checkpoint-metadata-order-attempt03-revisit-ownership-20261009.md`.
**Base-model layer 0** resides in numbered shard 1; the
second layer-0 run is actually the distinct **MTP module namespace**
(`mtp.layers.0`) in `model-mtp.safetensors`.
Independent **base-model layer 8** runs across numbered shards
4→5, and **layer 11** runs across numbered shards 5→6.
Base-only revisit diagnostic is **[8,11]**, so the strict
contiguous routed-layer condition fails even without the
MTP numeric-layer classifier collision.

Observed index: **17 numbered base-model shards plus
1 MTP file**, 223,046 keys, 221,186 routed keys, 48 routed
layers, maximum overlap **3**. Both hypothetical routed-byte
retention cases reported **6,448,748,544 bytes**; these
are on-disk metadata estimates and **not measured RSS/RM/GPU
peaks**. Image ID unchanged, no model/GPU launch.
The per-shard revisit attribution question is **closed** for
the tested assumed key-order model; **actual H38 installed loader
order and materialization lifecycle remain unverified**.
No new identical checkpoint recheck is authorized: next
engineering gate is exact-installed-loader source inspection,
not re-running unchanged metadata.

The full 18-file acceptance gate **cannot be overridden**
by omitting MTP. The actual H38 loader stream order, scales and
peak buffered-memory behavior remain unverified. No CT meta patch,
checkpoint contents modification, new GPU model test, R33,
monitor relaxation or managed promotion is authorized.


## H38 exact-installed weight-loader source-contract gate — 2026-10-09

The checkpoint Attempt 03 source/namespace attribution is **closed**
but exact H38 runtime loader order remains **unverified**. vLLM
**upstream v0.29.0 source** independently contains the default
index-filtered safetensors iterator, natural file sort,
`safe_open.keys()` and `get_tensor`; Qwen4Exp CausalLM and
ConditionalGeneration `load_weights()` pass
`orig_to_new_substr={"mtp.": None}` through `WeightsMapper`.
The mapper skips **model assignment** of MTP names, but source
order alone does **not** show that MTP data was excluded before
`get_tensor`. Native layerwise `load_numel` completion buffers
args and replays loaders through meta materialization; this source
structure does **not** prove safe CT-scale/packed-weight completion
for split routed layers 8 and 11.

Implementation commit `1e4aadaa029937a61007e225c173239079481a16`
passed GitHub Actions `37889474895`: **SUCCESS, 633/633
unit tests**, shell syntax, ShellCheck, Python compile and
whitespace PASS. This is **checker implementation CI only**,
not an actual image-source observation.

**Real DGX H38 installed-loader source inspection completed: PASS.**
The operator ran exact clean checkout
`b85f506a4f3f6e7a1272f6e5b37a137a5f57a5f9` against immutable
image ID
`sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`
in a no-network/no-GPU, read-only, UID 65534 runc inspector.
Observed `H38_LOADER_STATIC_CONTRACT=PASS`,
`H38_LOADER_SOURCE_PREFLIGHT=PASS`, unchanged image identity,
no checkpoint payload read or managed-service mutation. Eight
exact installed source SHA256 fingerprints and all observed
`SOURCE_PRESENT` conditions are in:
`scripts/benchmark/evidence/orcarouter-h38-installed-loader-source-contract-result-20261009.md`.

**Source proof only:** default indexed file selection, natural sorted
safetensors + `safe_open.keys()` + `get_tensor`, Qwen4Exp
`mtp.` name mapper, alternative loader routes, native layerwise
numel-based buffer/replay and H11/H12 CT aliases are present.
An `mtp.` model-mapping skip does **not** establish a pre-read
checkpoint payload skip. Actual selected H38 load format/strategy,
prefetch/multithread, EP filter, MTP model path and split
layer 8/11 packed-scale completion are **UNVERIFIED**.
The 18-file checkpoint `ORDER_GATE=FAIL` remains unmodified,
with 17 numbered base files + MTP, layer 8/11 base shard revisits
and no verified safe buffering bound. No CT meta patch,
RM reduction, functional or host stability qualification results.

The previously staged source-only checker is:

`scripts/benchmark/inspect-h38-installed-loader-source.py`,
`scripts/benchmark/check-h38-installed-loader-source.sh`, and
`tests/test_h38_installed_loader_source.py`.
It checks eight installed vLLM source files and fingerprints
their SHA256; exact H38 image ID, H11/H12/H38 labels, SHA, clean
checkout, no GPU/model/network, read-only inspector mount,
unprivileged runc and private 32 MiB `/tmp` are guarded.
Canonical protocol:
`scripts/benchmark/evidence/orcarouter-h38-installed-loader-source-contract-plan-20261009.md`.
**This is a staged source audit only**: no selected H38 config
path, runtime MTP I/O, buffer bound, memory reduction or stability
qualification has been measured. The 18-file checkpoint strict
contiguous-layer `ORDER_GATE=FAIL` remains authoritative.
No CT `device="meta"` patch or unchanged checkpoint replay is
justified.

## H38 preserved launch loader-config attestation — 2026-10-09

Exact H38 installed loader source check **PASS** does not attest
which loader settings were active during earlier protected candidate
launches. The valid **MTP SPEC=none Attempt 04** source
(`scripts/benchmark/evidence/orcarouter-h38-managed-mtp-startup-discriminator-attempt04-20261008.md`)
recorded an exact runtime identity match and **PROTECTED_STOP**,
`FUNCTIONAL=NOT_REACHED`, `HOST-STABILITY=INCONCLUSIVE`.
**Actual DGX Attempt 04 historical archive attestation completed:
PASS_ARCHIVED_LAUNCH_FLAGS_ONLY.** The operator ran the offline
parser at exact clean checkout
`1bc76cb12cc8df9d9512de0d0cd29e49120c1233`,
using the unchanged captured archive:
`/tmp/orcarouter-h38-mtp-none-attempt04-20261007T232026Z`.
Captured Docker image tag/ID, `candidate-inspect.json` command
versus `candidate-cmd.json`, H38 env lineage and model mount all
matched. The explicitly captured CLI was
**`--load-format safetensors`, executor `mp`, TP=1**.
`--safetensors-load-strategy`, model-loader extra config,
expert-parallel enable/disable, prefetch num threads/block size,
pipeline parallel size and `--speculative-config` were all
**NOT_EXPLICIT**, not inferred defaults. The **same archived
Attempt 04 startup log** contained the marker
`Auto-prefetch is disabled`. This is an observed startup message,
**not** a complete effective `LoadConfig` record.

Canonical operator result:
`scripts/benchmark/evidence/orcarouter-h38-preserved-loader-config-result-20261009.md`.
Source-only code quality CI: implementation
`0a71beb7fdd64ed06e9879c4349acb681e11f99f`,
GitHub Actions `37892699414` **SUCCESS, 641/641 tests**
(and documentation-sync CI `37892894955` **SUCCESS,
641/641 tests**). No Docker command/model/GPU work or host
protection change was performed by this archived-file analysis.

The guarded **read-only offline capture inspector** is:
`scripts/benchmark/inspect-h38-preserved-loader-config.py`,
guard `scripts/benchmark/check-h38-preserved-loader-config.sh`,
regression `tests/test_h38_preserved_loader_config.py`,
and canonical protocol
`scripts/benchmark/evidence/orcarouter-h38-preserved-loader-config-plan-20261009.md`.
It reads only preserved launch identity/CLI fields, redacts
secret environment and host paths, and prints `NOT_EXPLICIT`
for absent options — **never infers effective vLLM defaults**.
The same-archive prefetch marker **was observed** in
Attempt 04. The archived CLI and source checks **do not**
prove exact resolved `LoadConfig`, tensor delivery,
CT scale-completion or bounded buffers. Checkpoint
`ORDER_GATE=FAIL`, split base layers 8/11, and MTP
I/O ambiguity remain. CT Meta and runtime promotion stay blocked.

**PR #259 stays Draft/Open.** Managed migration and performance,
determinism, restart, promotion, and merge remain blocked. The
next useful work is code/evidence-level attribution of the **early
common ~75 GiB allocation burst**, not an unchanged live rerun,
compaction, drop-caches, sysctl or protection weakening.


## Historical evidence semantics

Dated evidence files are intentionally historical. Preserve their measured facts and
then-known decisions, including invalid attempts and superseded next-step plans.
When an older file contains words such as `current`, `pending`, `next`, or an old PR
merge instruction, read them in that dated context unless the file is explicitly marked
as a current index/closure.

Repository-facing current-state documents should point back here or to the evidence
index instead of duplicating volatile experiment-state text.

## Deferred mitigation work

The M1 mitigation prototype was intentionally excluded from PR #244 and is not part of
the R9–R32 canonical merge. Do not describe it as qualified or merged until its own
measurement/acceptance gates are completed.

## H38 CT layerwise-accounting source discriminator — 2026-10-09

The Draft PR #259 branch now stages a new exact-image, read-only AST CT packed/scale accounting inspector and guarded CPU-only wrapper:

- `scripts/benchmark/inspect-h38-ct-layerwise-accounting.py`
- `scripts/benchmark/check-h38-ct-layerwise-accounting.sh`
- `tests/test_h38_ct_layerwise_accounting.py`
- `scripts/benchmark/evidence/orcarouter-h38-ct-layerwise-accounting-source-plan-20261009.md`

The inspector pins the earlier verified H38 installed source digests and checks two packed H11 `ModelWeightParameter` registrations, six component scale registrations, H12 object aliases and the layerwise count/buffer/finalizer source anchors. The repository H11 patch supplies explicit packed `uint8` shape formulas. Upstream vLLM v0.29 per-invocation `get_numel_loaded` capping does not prove per-parameter lifetime deduplication or that all 512 experts and scales have arrived at a layerwise completion boundary.

**Status: STAGED / SYNTHETIC TESTS / NO NEW ACTUAL DGX RESULT YET.** Exact installed H38 tool execution and per-expert completeness, layer 8/11 shard-split finalization, subclass/alias materialization, effective iterator and simultaneous buffer peaks are still unverified. The earlier `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `FUNCTIONAL=NOT_REACHED`, `HOST-STABILITY=INCONCLUSIVE`, and `RM_MITIGATION=UNPROVEN` remain unchanged. H38 GPU/model rerun and PR #259 Ready/merge remain BLOCKED; no host protection modification is authorized.


## H38 CT accounting boundary — synthetic proof scope, 2026-10-09

The branch now also includes stronger installed-source AST shape/dtype checks (two packed ModelWeightParameter uint8 tensors, two float8 group scales and four float32 global/input scales; all eight symbolic size formulas), loadable-tensor exclusions, late size refresh, post-completion rejection, and meta parameter-class/attribute-preserving source markers.

A separate pure-stdlib synthetic suite demonstrates why a layerwise aggregate copied-element threshold does **not by itself prove unique per-parameter coverage**. In a toy model with eight names and only 20 total elements, repeating packed w13 copies can satisfy the aggregate target with missing scales (20 credited, 12 unique), or with a missing half of w13 (20 credited, 16 unique). A separate toy split-shard case leaves 16/20 elements and exposes the non-attention partial-finalizer branch. These are logical counterexamples, **not observations of real H38 repeated calls, unsafe postload or memory footprint**. Historical layer 8/11 shard revisits remain independently observed metadata-only facts.

Implementation and coverage:
- scripts/benchmark/inspect-h38-ct-layerwise-accounting.py
- scripts/benchmark/simulate-h38-ct-layerwise-completion.py
- tests/test_h38_ct_layerwise_accounting.py
- tests/test_h38_ct_layerwise_completion_cases.py
- scripts/benchmark/evidence/orcarouter-h38-ct-layerwise-accounting-source-plan-20261009.md

**Do not promote SOURCE_ONLY/SYNTHETIC into actual installed-image execution or model qualification.** The guarded exact H38 CPU-only inspector still requires an operator-side run and its output; real CT loader completeness and finite simultaneous buffer lifetime are UNVERIFIED. CHECKPOINT_METADATA_ORDER_GATE=FAIL; FUNCTIONAL=NOT_REACHED; HOST-STABILITY=INCONCLUSIVE; RM mitigation UNPROVEN; H38 model/GPU rerun BLOCKED; PR #259 DRAFT/OPEN and MERGE BLOCKED. All host memory protection stays unchanged.


## H38 RoutedExperts dispatch source prerequisite — 2026-10-09

The staged H38 CT source inspector now also requires the earlier installed-image SHA256 fingerprint of RoutedExperts (5206219da6b78315d6b35bee89fd0caa783681846affbf6917f430ef7f2481b5), alongside the existing CT, layerwise, meta and reload-utils fingerprints. Synthetic regression fixtures cover the exact inspected *source* contract, missing indexed-scale writes, missing nonlocal-expert skip, and the overloaded weight_loader concrete implementation.

Public upstream vLLM v0.29.0 RoutedExperts source shows explicit .copy_() in routed weight helpers, but indexed Tensor assignments for scalar/tensor input and global-scale helpers; scale dispatch can depend on GROUP/TENSOR tags, global/local expert remapping and nonlocal expert filtering. Exact TorchDispatchMode operations from these indexed assignments are **not certified by AST source**. In particular, it remains unjustified to treat every syntactic Tensor assignment as a CopyCounter count or to infer complete unique destination coverage for CT scales.

**State: SOURCE_ONLY CODE STAGED; exact H38 installed-source execution PENDING.** The bounded interpreter output is pending DGX operator evidence and can confirm only the exact source anchors and digests. No model/accelerator run, H38 image/source/checkpoint modification or host safety change was made. CT_COPYCOUNTER_SCALE_COVERAGE=UNVERIFIED; CT_WEIGHT_COMPLETENESS=UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE=FAIL; HOST-STABILITY=INCONCLUSIVE; PR #259 remains DRAFT/OPEN and MERGE BLOCKED. The separate source-plan result is recorded in scripts/benchmark/evidence/orcarouter-h38-ct-layerwise-accounting-source-plan-20261009.md.


## H38 installed-source Attempt 01 — checker wrapper mismatch, 2026-10-09

The DGX operator **executed** the exact clean source-only wrapper at Git HEAD b9db2c901676ebc974c22f5ee65b37bc6c208c72 against H38 image sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc. Preflight reached BEGIN; CT AST validation stopped with H38_CT_ACCOUNTING_SOURCE=INVALID reason=unsupported_CT_parameter_wrapper:PerTensorScaleParameter and source_check_rc=2. All five source SHA256 checks occur before the failing allocation AST, but the inspector did not complete validation or issue a PASS result.

**Classification: STATIC CHECKER CONTRACT INVALID / NOT MODEL DEFECT.** This is the first actual operator source-inspection attempt, not an H38 model/GPU run. The CT allocation AST checker previously allowed only ModelWeightParameter and torch.nn.Parameter and was incomplete for vLLM scale subclasses. The follow-up correction admits recognized PerTensorScaleParameter/GroupQuantScaleParameter only in appropriate scale classes while retaining shape/dtype/loader/source digest guards and negative regression tests. The original operator error did NOT specify which parameter was PerTensorScaleParameter or the tensor shape, and the correction is **not independently passed on the exact image yet**. Exact output is recorded in scripts/benchmark/evidence/orcarouter-h38-ct-layerwise-accounting-attempt01-invalid-20261009.md.

**Next gate:** after the corrected commit passes GitHub CI, rerun the guarded source-only image checker on the operator DGX from that exact clean SHA; preserve the full result. CT_SOURCE_CONTRACT=INVALID_ATTEMPT01; CT_SCALE_SOURCE_SEMANTICS=UNVERIFIED; CT_WEIGHT_COMPLETENESS=UNVERIFIED; COPYCOUNTER_SCALE_CREDIT=UNVERIFIED; FUNCTIONAL=NOT_REACHED; HOST_STABILITY=INCONCLUSIVE. Do not modify the H38 image, run the model/GPU, weaken host protection, or mark PR #259 Ready/Merge.


## H38 CT AST source-inspection fallback diagnostics — 2026-10-09

Following operator Attempt 01 (INVALID: unsupported PerTensorScaleParameter), the CI-qualified remediation now has a **fail-closed diagnostic fallback** for a later read-only exact-image AST run. If source-contract validation fails, the inspector first reports the original reason and returns code 2; it additionally re-verifies **all five installed-source SHA256 pins** and, only if those match, emits bounded syntax summaries of all eight expected CT packed/scale registrations. Each entry includes the registration name and line, constructor, initializer expression, symbolic torch.empty dimensions/dtype/device, source weight_loader argument and available keywords. These are **source expressions, not tensors or measured memory**.

This design minimizes blind repeated DGX runs that discover one unsupported constructor at a time. Diagnostics explicitly classify as PINNED_CT_SOURCE_SYNTAX_ONLY_NOT_A_PASS and cannot convert INVALID into PASS. If source hashes drift, no CT AST fallback output is qualified. The wrapper's GPU/no-network/no-pull/sandbox restrictions are unchanged.

**Execution status:** No DGX Attempt 02 result has been provided. Attempt 01 remains the only actual source-check execution observed: INVALID / inspector contract mismatch, not a model failure. Subsequent AST diagnostic code and synthetic tests are repository-side only pending any exact-image invocation. PR #259 remains Draft/Open, no H38 model/GPU run or host-protection change, no CT deferred-meta implementation, no Ready/Merge.


## H38 exact-image CT AST Attempt 02 — eight-parameter source closure pending PASS, 2026-10-10

The operator executed the guarded exact H38 source-only inspector on clean HEAD 88e8a0509676ddfa87780a556d26a82d6ac95a74 and pinned H38 image sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc. The wrapper began and the **SHA-pinned diagnostic fallback** enumerated exactly 8 expected registration sites with no missing names after an AST contract error:

- w13_weight_packed and w2_weight_packed: ModelWeightParameter / uint8.
- w13_weight_scale and w2_weight_scale: **ModelWeightParameter / float8_e4m3fn**, not the previous static checker's allowed torch.nn.Parameter or GroupQuantScaleParameter.
- w13_weight_global_scale and w2_weight_global_scale: PerTensorScaleParameter / float32.
- w13_input_global_scale and w2_input_global_scale: torch.nn.Parameter / float32; the constructor itself has no explicit weight_loader keyword (post-construction attribute paths NOT resolved by this output).
- All eight initializer torch.empty forms have no explicit device keyword, and symbolic shapes match the eight registered names in the operator source diagnostics.

Observed H38_CT_ACCOUNTING_SOURCE=INVALID reason=incorrect_CT_parameter_wrapper:w13_weight_scale:ModelWeightParameter; return code 2. The original failure is **AST CHECKER CLASS-EXPECTATION MISMATCH**, not observed model failure. The fallback checks all five installed source SHA256 digests before returning the diagnostic; neither the complete AST PASS nor the wrapper's final post-success image-identity check was reached.

Canonical immutable result: scripts/benchmark/evidence/orcarouter-h38-ct-layerwise-accounting-attempt02-invalid-20261010.md. The inspector/test source contract is corrected to the **eight exact observed constructor types** with retained shape/dtype/weight-loader and digest guards, not a permissive class-wide allowlist. Pending an independent source-only rerun, CT_SOURCE_CONTRACT remains INVALID_ATTEMPT02 / PASS_PENDING. CI tests are source/synthetic evidence only.

CopyCounter indexed scale write credit, per-expert unique coverage, live split-shard 8/11 finalization/buffer lifetime, peak memory, postload completeness, functional startup, and host stability remain UNVERIFIED. GPU_MODEL_RERUN=BLOCKED; HOST_PROTECTION=UNCHANGED; CT_META_PATCH=BLOCKED; PR_259=DRAFT_OPEN / MERGE=BLOCKED.


## H38 CT installed-image source audit — Attempt 03 PASS (2026-10-11)

**Current authoritative source-only disposition supersedes the earlier PENDING/INVALID status sections; historical Attempt 01/02 logs are retained unchanged.**

The DGX operator successfully fast-forwarded the clean branch to exact HEAD 5fa4265d394255744f8886b857804a28c433cf3f and executed the previously CI-qualified guarded H38 source-only inspector against pinned image sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc. The supplied complete console transcript reports H38_CT_ACCOUNTING_SOURCE=PASS_SOURCE_CONTRACT_ONLY, H38_CT_ACCOUNTING_PREFLIGHT=PASS_SOURCE_CONTRACT_ONLY, source_check_rc=0, image_identity_unchanged=YES; gpu_or_model_load=NO, checkpoint_payload_read=NO, host_protection_changed=NO, managed_service_mutation=NO and ct_meta_patch_implemented=NO. All five pinned installed source SHA256 values passed.

Static source confirmation is now established for eight CT parameter registrations (four ModelWeightParameter: two uint8 packed + two FP8 group scales; two PerTensorScaleParameter float32 global weight scales; two plain torch.nn.Parameter float32 input scales), symbolic shape/dtype/source keyword contracts, the H12 packed→weight same-object alias syntax, 21 Layerwise/CopyCounter/materialization AST anchors and 14 RoutedExperts write-path AST anchors. The two plain input-scale constructors do not explicitly accept a weight_loader keyword; this does NOT establish absence of post-construction setter attributes.

This **does not** establish real TorchDispatchMode credit for indexed scale assignment, all 512-expert unique loaded element coverage, complete shard 8/11 replay, finite peak buffer bounds, functioning H38 inference or host safety. Indexed assignment sites in source remain distinct from observed aten.copy_.default dispatch events. Earlier toy counterexamples remain hypothetical and were not reproduced on H38.

Canonical source result: scripts/benchmark/evidence/orcarouter-h38-ct-layerwise-accounting-attempt03-source-pass-20261011.md. Original operator /tmp logfile and its hash were not independently obtained; provenance is the supplied terminal transcript. This result belongs to the **old checked source HEAD** 5fa4265d394255744f8886b857804a28c433cf3f, not a later documentation-only commit.

Current gates: CT_INSTALLED_SOURCE_CONTRACT=PASS_SOURCE_CONTRACT_ONLY; CT_WEIGHT_COMPLETENESS=UNVERIFIED; CT_COPYCOUNTER_SCALE_CREDIT=UNVERIFIED; CT_SCALE_PARAMETER_SEMANTICS=UNVERIFIED; SHARD_8_11_COMPLETENESS=UNVERIFIED; PEAK_BUFFER_BYTES=UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE=FAIL; FUNCTIONAL=NOT_REACHED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; CT_META_IMPLEMENTATION=BLOCKED; GPU_MODEL_RERUN=BLOCKED; HOST_PROTECTION=UNCHANGED; PR_259=DRAFT_OPEN / MERGE=BLOCKED.

Next bounded plan: inspect post-construction attribute binding of input scales, then consider a strictly isolated, tiny synthetic CPU TorchDispatchMode witness for indexed writes **only if resource and service safety are validated**, followed by source-driven shard 8/11 ownership analysis. No automatic model startup, image rebuild, host resource relaxation, or PR Ready/Merge.


## H38 input-scale postconstruction loader attributes — source-only staging (2026-10-11)

After the real installed-image CT source audit **Attempt 03 PASS_SOURCE_CONTRACT_ONLY**, a separate, read-only **CT scale attribute provenance** inspector, guarded launcher and stdlib synthetic regression tests were staged in the GitHub PR #259 branch. This does not change or rescind the earlier qualified pinned-image CT registration/source result.

The narrow question is why w13_input_global_scale and w2_input_global_scale are constructed as plain torch.nn.Parameter without an explicit constructor weight_loader. Public upstream vLLM v0.29.0 source shows a later set_weight_attrs(variable, extra_weight_attrs) call and a TENSOR quant_method tag; the same upstream common helper sets attributes using setattr after an overwrite guard. A source expression in upstream does **not** by itself prove that the exact installed H38 image contains the same helper semantics or that its runtime assignment succeeds.

New repository tools:
- scripts/benchmark/inspect-h38-ct-scale-attr-provenance.py — stdlib-only AST reader, pins exact CT/RoutedExperts/layerwise installed-source hashes, captures the previously unpinned installed-image model_executor/utils.py helper digest, verifies both registered input-scale setter source sites, H11 extra attrs loader origin, RoutedExperts loader export and layerwise wrapper syntax. The utility digest is a new image-ID-guarded observation, NOT a preapproved SHA pin.
- scripts/benchmark/check-h38-ct-scale-attr-provenance.sh — immutable image-ID/label verification, clean exact HEAD requirement, unprivileged no-network/no-GPU/read-only limited runc; no model/checkpoint read, Docker image edit, managed service or host protection change.
- tests/test_h38_ct_scale_attr_provenance.py — synthetic AST success/fail-close regression only.
- Canonical stage plan: scripts/benchmark/evidence/orcarouter-h38-ct-scale-attr-source-plan-20261011.md.

**Current result is STAGED / not yet executed on DGX**; no PASS of this new attribute-site inspector has been claimed. The existing CT_INSTALLED_SOURCE_CONTRACT=PASS_SOURCE_CONTRACT_ONLY still applies only to the 2026-10-11 Attempt 03 source audit. A future attribute-site source PASS cannot establish effective runtime callback, actual aten.copy_ counting on indexed scales, expert-completeness, shard 8/11 buffer release, inference correctness or host memory stability. GPU_MODEL_RERUN=BLOCKED; HOST_PROTECTION=UNCHANGED; PR_259=DRAFT_OPEN; MERGE=BLOCKED.


## H38 input-scale postconstruction source audit — operator Attempt 01 PASS (2026-10-11)

**This newer confirmed result supersedes the preceding STAGED/PENDING entry for the attribute-site inspector, without enlarging its source-only qualification.** The operator fetched and fast-forwarded the clean branch to exact HEAD 1865521c2ff58add7bddeed6735c76803a3e3637 and executed scripts/benchmark/check-h38-ct-scale-attr-provenance.sh against the original, unchanged H38 pinned image sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc.

Reported verdict: H38_CT_SCALE_ATTR_SOURCE=PASS_SOURCE_SITES_ONLY; H38_CT_SCALE_ATTR_PREFLIGHT=PASS_SOURCE_SITES_ONLY; source_check_rc=0; image_identity_unchanged=YES; gpu_or_model_load=NO; checkpoint_payload_read=NO; managed_service_mutation=NO; host_protection_changed=NO; ct_meta_patch_implemented=NO.

Both CT input-scale registration→quant_method=TENSOR source update→postconstruction set_weight_attrs(variable, extra_weight_attrs) source sequences are verified: w13_input_global_scale registration line 183, TENSOR update 184, setter 187; w2_input_global_scale registration line 192, TENSOR update 193, setter 196. H11 extra_weight_attrs.get('weight_loader') and RoutedExperts loader export, layerwise original-loader reference/reassignment, and the helper guarded setattr source syntax also passed AST source checks.

The image-ID-guarded **newly observed** vllm/model_executor/utils.py source SHA256 is f208310647a012797e0b0e9631d3498135c7f9aef831e35e42e96eceb7623f89. This was NOT pre-pinned or independently preapproved before the run and must NOT be retroactively reported as preverified. The three other source SHA256 values (CT, RoutedExperts, layerwise) matched their earlier independently pinned values. The operator-reported logfile /tmp/h38-ct-scale-attrs-attempt01-20261011.txt was not independently materialized or hashed.

This is evidence that **source setter sites and helper code exist**, not evidence of the actual runtime value of a weight_loader attribute, a callback invocation, real scale copy counter credit, all 512 experts loaded, shard 8/11 ownership completion or finite peak memory. Canonical record: scripts/benchmark/evidence/orcarouter-h38-ct-scale-attr-attempt01-source-pass-20261011.md. The earlier source-audit Attempt 03 PASS_SOURCE_CONTRACT_ONLY remains a separate qualified result.

Current gates: CT_INSTALLED_SOURCE_CONTRACT=PASS_SOURCE_CONTRACT_ONLY; CT_SCALE_ATTR_SOURCE_SITES=PASS_SOURCE_SITES_ONLY; CT_EFFECTIVE_LOADER_RUNTIME=UNVERIFIED; CT_COPYCOUNTER_SCALE_CREDIT=UNVERIFIED; CT_WEIGHT_COMPLETENESS=UNVERIFIED; SHARD_8_11_COMPLETENESS=UNVERIFIED; PEAK_BUFFER_BYTES=UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE=FAIL; FUNCTIONAL=NOT_REACHED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; GPU_MODEL_RERUN=BLOCKED; CT_META_IMPLEMENTATION=BLOCKED; HOST_PROTECTION=UNCHANGED; PR_259=DRAFT_OPEN / MERGE=BLOCKED.

Next engineering decision is a separately provenance-labeled, tightly scoped tiny CPU-only PyTorch TorchDispatchMode indexed-assignment vs explicit copy_ experiment (only in a safe, bounded environment), followed by genuinely checkpoint-aware shard/expert source mapping. Neither requires or authorizes an H38 GPU/model run.


## Isolated external CPU TorchDispatchMode tiny write witness — 2026-10-11

A separate **assistant-side isolated Python environment** (NOT DGX/H38 image, NOT vLLM runtime) was used for a tiny CPU-only PyTorch 2.10.0+cpu experiment, without host or service mutation. Direct Tensor index assignment in this distinct runtime triggered torch.ops.aten.copy_.default under TorchDispatchMode for the tested synthetic scalar and row writes. A synthetic 3x2 tensor with writes to [0,1], row 1, row 2, then a second write to [0,1] credited 1+2+2+1=6 copied elements across four calls, even though only 5 of 6 destination elements were uniquely touched. Repeated writes can therefore satisfy a toy aggregate threshold without complete unique coverage.

**Critical provenance limitation:** this result was obtained on an external CPU PyTorch runtime with version 2.10.0+cpu, **not** in the pinned H38 vLLM v0.29 installation on DGX Spark. It does not prove actual H38 TorchDispatchMode events, loader callback counts, 512-expert completeness or wrong postload timing. It also shows that claiming indexed assignment can never be counted would be incorrect for at least this separate PyTorch stack. In H38, live scale CopyCounter credit and destination uniqueness remain UNVERIFIED, and no in-image torch CPU probe is approved yet.

Canonical, reproducible operations and scoped output: scripts/benchmark/evidence/h38-ct-copycounter-indexed-write-external-cpu-toy-20261011.md. The operator-installed CT source and input-scale attribute source PASS results remain separate and authoritative only for their syntax. PR #259 remains Draft/Open and merge blocked; H38 image/checkpoint/GPU/model/host protection unchanged. No new DGX execution is required merely to document this external synthetic observation.


## H38 CT expert/shard destination-map source gate — staged 2026-10-11

After the successful installed-image CT eight-parameter source Attempt 03 and input-scale attribute source Attempt 01, the next high-discrimination evidence target is **expert/shard destination identity**, not rerunning the same CT constructor/attribute checks. A new Python **stdlib AST-only** source inspector and protected runc wrapper were staged in PR #259:

- scripts/benchmark/inspect-h38-ct-expert-destination-source.py: requires the four previously qualified pinned H38 CT/RoutedExperts/Layerwise/meta SHA256 digests; emits source-branch predicates for get_expert_mapping/include_fused name matching, global-to-local expert mapping, nonlocal skip, conditional global scale, fused checkpoint handling, w13 first/second projection halves, w2 copies, grouped/tensor-scale dispatch and input-scale generic row vs ModelOpt-specific index-write branches. Also emits an eight-parameter source-conditioned destination hypothesis table.
- scripts/benchmark/check-h38-ct-expert-destination-source.sh: clean exact Git HEAD, fixed H38 image ID/H11-H12-H38 label gates, no network/no pull/no GPU, read-only unprivileged runc with CPU/memory/PID limits, and final image-ID comparison.
- tests/test_h38_ct_expert_destination_source.py: stdlib-only fake-source positive and negative tests for missing routing/callback, expert-id map, nonlocal skip, fused split, w1/w3 tensor-scale indices, input row write, separate ModelOpt path, projection-half displacement, and pinned digest failure.
- scripts/benchmark/evidence/orcarouter-h38-ct-expert-destination-source-plan-20261011.md: canonical planned source-only gate and evidence boundaries.

A critical conditional: the generic input-scale helper source writes param_data[expert_id] = loaded_weight while the per-tensor global-weight-scale helper has distinct w1/w3 indices; a ModelOpt-specific branch may instead write per-shard input cells. **This is only static control-flow syntax.** Actual H38 quant method, shape compatibility, input-scale equality checks, global/local expert resolution, TP slicing, checkpoint name mapping, occurrence count, and unique destination coverage remain UNVERIFIED. In particular, the existence of a generic row-write site is NOT proof of a repeated or successful row write in real H38.

**Status: SOURCE INSPECTOR/TINY TESTS STAGED; exact image execution PENDING.** A future H38_CT_EXPERT_DESTINATION_PREFLIGHT=PASS_SOURCE_BRANCHES_ONLY can qualify only those pinned source branch anchors, not actual loading, CopyCounter credit, layer 8/11 metadata order/buffer lifetime, functional startup or a finite memory peak. Existing CT_INSTALLED_SOURCE_CONTRACT=PASS_SOURCE_CONTRACT_ONLY; CT_SCALE_ATTR_SOURCE_SITES=PASS_SOURCE_SITES_ONLY; CT_WEIGHT_COMPLETENESS=UNVERIFIED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; GPU_MODEL_RERUN=BLOCKED; HOST_PROTECTION=UNCHANGED; CT_META_PATCH=BLOCKED; PR_259=DRAFT_OPEN; MERGE=BLOCKED.


## H38 CT Expert/Shard Destination — actual DGX operator Attempt 01 PASS (2026-10-11)

**This authoritative observation supersedes the earlier staged/PENDING expert-destination entry above, without extending its qualification to runtime loading.** On the clean exact Git checkout fd4221b5bdb2b95ad83f94255ee2740cea842c9e (fast-forwarded from 1865521) the operator executed the dedicated no-GPU/no-checkpoint/no-model guarded image-source audit. It reported H38_CT_EXPERT_DESTINATION_SOURCE=PASS_SOURCE_BRANCHES_ONLY; H38_CT_EXPERT_DESTINATION_PREFLIGHT=PASS_SOURCE_BRANCHES_ONLY; source_check_rc=0; image_identity_unchanged=YES; gpu_or_model_load=NO; checkpoint_payload_read=NO; managed_service_mutation=NO; host_protection_changed=NO; ct_meta_patch_implemented=NO.

All **29/29 AST source predicates** passed: 11 expert-name/global-to-local mapping, fused/full, callback/nonlocal/global-scale branches; 7 packed/group source destinations and w13 first/second halves; 11 input/TENSOR scale branches, including general full-row input assignment vs ModelOpt-specific per-index assignment and the compressed input-scale conflict-check source site. All four pre-pinned CT/RoutedExperts/layerwise/meta source SHA256 values matched the unmodified H38 image sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc.

**Source branching is not event coverage.** The installed image may take different branches depending on actual input/fused checkpoint naming, expert parallel mapping, optional global scale, model backend/quant method, TP dimensions and values. The output specifically retains real_checkpoint_name_to_parameter_matches, real_expert_id_mapping, real_copy_dispatch_numel, unique_real_destination_coverage, actual_input_scale_values_or_conflict, and layer_8_11_shard_revisit_or_buffer_lifetime as UNVERIFIED. No actual H38 torch import, model/GPU, checkpoint payload reading, memory peak, 512-expert copy trace or host stability test occurred.

**Separate conditional source risk**, not a model error observation: in the image-SHA-identical RoutedExperts source, the compressed input-scale conflict-check predicate can attempt Python boolean evaluation of param.data[expert_id] != 1. For a 2-element w13 input-scale row and if that branch is executed, this raises a potential ambiguous multi-element Tensor truth-value concern. The branch condition and exact H38 runtime shape/expert/method must be established before treating this as a defect. PR #259 source-crosscheck discussion comment 6105299781 retains that distinction.

Canonical newly observed evidence: scripts/benchmark/evidence/orcarouter-h38-ct-expert-destination-attempt01-source-pass-20261011.md. Operator console transcript is source; /tmp/h38-ct-expert-destination-attempt01-20261011.txt itself and its SHA256 have not been independently copied/hashed. The previous exact H38 CT registration Attempt 03 PASS_SOURCE_CONTRACT_ONLY and input-scale attribute Attempt 01 PASS_SOURCE_SITES_ONLY remain separate, successful bounded source-only gates.

Current gates: CT_INSTALLED_SOURCE_CONTRACT=PASS_SOURCE_CONTRACT_ONLY; CT_SCALE_ATTR_SOURCE_SITES=PASS_SOURCE_SITES_ONLY; CT_EXPERT_DESTINATION_SOURCE_BRANCHES=PASS_SOURCE_BRANCHES_ONLY; CT_REAL_DESTINATION_COVERAGE=UNVERIFIED; CT_COPYCOUNTER_SCALE_CREDIT=UNVERIFIED; SHARD_8_11_COMPLETENESS=UNVERIFIED; PEAK_BUFFER_BYTES=UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE=FAIL; FUNCTIONAL=NOT_REACHED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; GPU_MODEL_RERUN=BLOCKED; CT_META_PATCH=BLOCKED; HOST_PROTECTION=UNCHANGED; PR_259=DRAFT_OPEN; MERGE=BLOCKED.

Next bounded engineering gate: review existing checkpoint metadata-only inventory tooling and qualification before deriving a real key-to-expert/shard/parameter mapping. Design synthetic fixture coverage before any additional DGX action; do not assume source-only PASS proves actual coverage or justifies GPU/model loading.


## H38 OrcaRouter CT 48×512×9 checkpoint KEY mapping — index-only stage (2026-10-11)

**Next bounded gate after the exact-image Expert Destination source Attempt 01 PASS_SOURCE_BRANCHES_ONLY**: reconcile real checkpoint key names and shard owners with the six CT packed/group/global-weight-scale registration families identified in pinned H38 source. Do not repeat the prior 18-file safetensors full-header order scan: the previous validated header-only Attempt 03 already established 17 numbered base shards + 1 MTP, 223,046 indexed keys, 221,186 routed-classified keys including 2 in MTP, 48 base layers, and base layer 8 numbered shard 4→5 / layer 11 5→6, with strict ORDER_GATE=FAIL. This source/header provenance is documented in scripts/benchmark/evidence/orcarouter-h38-checkpoint-metadata-order-attempt03-revisit-ownership-20261009.md.

The new pure-stdlib scripts/benchmark/inspect-h38-ct-checkpoint-key-map.py reuses the existing metadata inspector's resolve_shards() shard/index guard, then reads **only model.safetensors.index.json** as JSON names→filenames. It does NOT call scan_checkpoint(), safetensors.safe_open(), read_header(), get_tensor(), torch or vLLM. The protected runner scripts/benchmark/check-h38-ct-checkpoint-key-map.sh mounts checkpoint and both inspectors read-only in immutable, image-ID-pinned unprivileged no-GPU/no-network/no-model runc with <=1GiB memory, <=1CPU, 64MiB private tmpfs, and clean exact Git HEAD guard. Tests/test_h38_ct_checkpoint_key_map.py provides 11 positive/fail-closed synthetic cases.

The source-driven **candidate** schema contains exactly nine names per expert: (gate_proj, up_proj, down_proj) × (weight, weight_scale, weight_global_scale) for a hypothesized 48 layers × 512 experts = 221,184 base routed keys. The earlier indexed routed count was 221,186 including 2 MTP classifier keys, but **the new 9-key grid has NOT yet been compared to the real index**. Code gates missing or unexpected names, semantic duplicate slots, expert-ID/layer bounds and reports per-shard splits without claiming real callbacks.

These 9 checkpoint name categories map conditionally to only **SIX** of the **EIGHT** H38 CT registration families: w13/w2_weight_packed, w13/w2_weight_scale and w13/w2_weight_global_scale. The two input-global-scale registrations w13_input_global_scale and w2_input_global_scale have **NO proved corresponding checkpoint key or initialization contract** under this schema. Even if the 9-key metadata grid passes, input scale data sourcing and actual loader results remain UNVERIFIED.

Canonical implementation/qualification and planned operator gate: scripts/benchmark/evidence/orcarouter-h38-ct-checkpoint-key-map-plan-20261011.md. The new real checkpoint **INDEX-ONLY** operator result is PENDING; do not claim that repo CI or old header-only metadata ORDER_GATE=FAIL is its result. A possible PASS_BASE_KEY_SCHEMA_ONLY concerns index names, not runtime element coverage; FAIL_KEY_SCHEMA is a classifier mismatch, not proof of corrupt checkpoint. The earlier ORDER_GATE=FAIL remains unchanged.

Gates remain CT_INSTALLED_SOURCE_CONTRACT=PASS_SOURCE_CONTRACT_ONLY; CT_SCALE_ATTR_SOURCE_SITES=PASS_SOURCE_SITES_ONLY; CT_EXPERT_DESTINATION_SOURCE_BRANCHES=PASS_SOURCE_BRANCHES_ONLY; CT_REAL_KEY_MAP=UNVERIFIED; CT_INPUT_SCALE_DATA_SOURCE=UNVERIFIED; CT_UNIQUE_DESTINATION_ELEMENT_COVERAGE=UNVERIFIED; CT_COPYCOUNTER_CREDIT=UNVERIFIED; LAYER_8_11_BUFFER_LIFETIME=UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE=FAIL; FUNCTIONAL=NOT_REACHED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; GPU_MODEL_RERUN=BLOCKED; HOST_PROTECTION=UNCHANGED; CT_META_PATCH=BLOCKED; PR_259=DRAFT_OPEN; MERGE=BLOCKED.


## H38 CT checkpoint key-map Attempt 01 — VALID KEY_SCHEMA_FAIL, not checkpoint fault (2026-10-11)

**This actual DGX observation supersedes the previously STAGED/PENDING index-only key-map record above, without changing prior source-only successes or the independent checkpoint ORDER_GATE=FAIL.** At exact clean operator checkout 1ed66b602c55534af432bba404b8eb0e6eb9db0e, fixed unmodified H38 image sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc, the safe index-only script returned H38_CKPT_CT_KEY_MAP_GATE=FAIL_KEY_SCHEMA, H38_CKPT_CT_KEY_MAP_PREFLIGHT=KEY_SCHEMA_FAIL, key_map_rc=3 and image_identity_unchanged=YES. It reported no tensor payload/header re-read, GPU or model execution.

Root cause is **a real checkpoint key naming mismatch against our analyzer's original assumption**, NOT observed missing packed checkpoint weights: actual keys are gate_proj/up_proj/down_proj.weight_packed; the analyzer originally required *.weight. Thus 73,728 (48 layers ×512 experts ×3 projections) packed-weight candidate keys were unclassified and also marked missing slots, showing incomplete_expert_grid_count=24,576 under the outdated schema. All four group/global scale categories had recognized counts (w13: 49,152 per scale family; w2: 24,576 per scale family). Total candidate base keys=221,184 and indexed total=223,046 across 18 shards; 31 keys have mtp. namespace. The observed index SHA256 is 188d5905df195dd2dca4dbf2f9c029bb79328d0c85fd9772d73f72d881561866. Crucially, indexed key names containing input_scale or input_global_scale=**0**, so the two input-global-scale CT parameter initialization/source questions remain UNVERIFIED, not "initialized".

13 (layer, expert) metadata key groups have multiple shard owners, including layer 8/expert 235 shards 4→5 and layer 11/expert 409 shards 5→6. The earlier per-shard counts in this incomplete parser covered only **3,072 recognized scale keys/layer**, not complete 4,608-key distributions. Neither key indices nor source branch ASTs establish live callback count, copied numel, destination completeness, shard buffer release or host safety.

The checker has been narrowly corrected to require the observed `weight_packed` suffix, and synthetic fail-closed tests now cover production-scale **hypothetical** 48×512×9 nine-slot grids, rejection of unsuffixed `weight`, scale omissions and unknown mappings. **Attempt 01 is permanently FAIL_KEY_SCHEMA**; real Attempt 02 against the new exact CI-qualified Git SHA is pending. Do not claim that new fixture PASS closes it. Canonical immutable result scripts/benchmark/evidence/orcarouter-h38-ct-checkpoint-key-map-attempt01-schema-fail-20261011.md. The original pre-correction operator /tmp log was not independently acquired or byte-hashed; provenance is the provided terminal transcript.

Current gates: CT_CHECKPOINT_KEY_MAP_ATTEMPT01=FAIL_KEY_SCHEMA; CT_INSTALLED_SOURCE_CONTRACT=PASS_SOURCE_CONTRACT_ONLY; CT_SCALE_ATTR_SOURCE_SITES=PASS_SOURCE_SITES_ONLY; CT_EXPERT_DESTINATION_BRANCHES=PASS_SOURCE_BRANCHES_ONLY; REAL_CHECKPOINT_CT_KEY_GRID=UNVERIFIED; CT_INPUT_SCALE_DATA_SOURCE=UNVERIFIED; CT_WEIGHT_COMPLETENESS=UNVERIFIED; CT_COPYCOUNTER_CREDIT=UNVERIFIED; LAYER_8_11_BUFFER_LIFETIME=UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE=FAIL; FUNCTIONAL=NOT_REACHED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; GPU_MODEL_RERUN=BLOCKED; HOST_PROTECTION=UNCHANGED; CT_META_PATCH=BLOCKED; PR_259=DRAFT_OPEN; MERGE=BLOCKED.


## H38 CT checkpoint key-map — real DGX Attempt 02 PASS_BASE_KEY_SCHEMA_ONLY (2026-10-11)

**This is the latest authoritative INDEX-ONLY key-name outcome, superseding earlier statements that Attempt 02 was PENDING.** The original Attempt 01 at source HEAD 1ed66b602c55534af432bba404b8eb0e6eb9db0e remains **FAIL_KEY_SCHEMA/rc3 as historical checker mismatch** (it incorrectly expected unsuffixed *.weight keys). The updated, CI-qualified checker was executed on clean exact HEAD **2426b9a9ac4234865176fc12c5e34a79d0bbfd1d** with the same immutable H38 image sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc, and the same checkpoint index SHA256 **188d5905df195dd2dca4dbf2f9c029bb79328d0c85fd9772d73f72d881561866**.

Actual operator output: H38_CKPT_CT_KEY_MAP_GATE=PASS_BASE_KEY_SCHEMA_ONLY; H38_CKPT_CT_KEY_MAP_PREFLIGHT=PASS_BASE_KEY_SCHEMA_ONLY; key_map_rc=0; image_identity_unchanged=YES; tensor_payload_read=NO; headers_reread=NO; model_or_gpu_load=NO; managed_service_mutation=NO; monitor_protection_changed=NO; meta_w13_patch_implemented=NO.

All **48 base routed layers × 512 experts × 9 index name slots = 221,184** are present under explicit gate_proj/up_proj/down_proj × weight_packed/weight_scale/weight_global_scale classifier: incomplete_expert_grid_count=0, missing_canonical_slot_count=0, no unclassified base routed key samples, no duplicate semantic slot samples and no out-of-range samples. Candidate CT key family counts: w13_weight_packed=49,152; w2_weight_packed=24,576; w13_weight_scale=49,152; w2_weight_scale=24,576; w13_weight_global_scale=49,152; w2_weight_global_scale=24,576. **These are checkpoint index names, not observed parameter callback/data loading.**

Full layer 8 index key file counts are shard4=2,119 and shard5=2,489 (4,608); layer 11 shard5=3,685 and shard6=923 (4,608). **13** candidate (layer, expert) pairs have indexed keys in multiple files; only **12** bounded samples were printed. Total index entries 223,046 across 18 files (17 numbered + 1 auxiliary MTP). The simple mtp. namespace count is **31**; that does not conflict with the previous independent analyzer's two MTP routed-classified keys, because the two counts use distinct predicates.

**Critical qualification:** There are **ZERO** checkpoint index key names containing 'input_scale' or 'input_global_scale'. This provides no evidence that the two registered H38 CT input-global-scale parameters have valid initialization or values. The passed 9-key index grid corresponds conditionally to only **6 of 8 CT registered parameter families**. Real global→local expert mapping, `weight_loader` callbacks, TorchDispatchMode/CopyCounter credit, unique copied destination elements, input scales, shard 8/11 runtime replay/buffer release and peak bytes all remain UNVERIFIED. The earlier strict CHECKPOINT_METADATA_ORDER_GATE remains **FAIL**, not corrected by index-name completeness.

Canonical genuine operator evidence: scripts/benchmark/evidence/orcarouter-h38-ct-checkpoint-key-map-attempt02-index-pass-20261011.md. The original /tmp logfile SHA256 is not independently established; provenance is the provided terminal transcript. Prior actual source-only gates (8 CT registrations, input-scale postconstruction source, 29 expert destination branch predicates) still have bounded SOURCE_ONLY PASS classifications. Prior external tiny PyTorch CPU toy is not H38 runtime qualification.

Current gates: CT_CHECKPOINT_KEY_MAP_ATTEMPT01=FAIL_KEY_SCHEMA [HISTORICAL]; CT_CHECKPOINT_KEY_MAP_ATTEMPT02=PASS_BASE_KEY_SCHEMA_ONLY; CT_INPUT_SCALE_DATA_SOURCE=UNVERIFIED; CT_EFFECTIVE_LOADER_CALLBACKS=UNVERIFIED; CT_UNIQUE_DESTINATION_ELEMENT_COVERAGE=UNVERIFIED; CT_COPYCOUNTER_SCALE_CREDIT=UNVERIFIED; CT_WEIGHT_COMPLETENESS=UNVERIFIED; SHARD_8_11_BUFFER_LIFETIME=UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE=FAIL; FUNCTIONAL=NOT_REACHED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; GPU_MODEL_RERUN=BLOCKED; HOST_PROTECTION=UNCHANGED; CT_META_PATCH=BLOCKED; PR_259=DRAFT_OPEN; MERGE=BLOCKED.

**Next:** avoid repeating a completed index grid audit. Trace installed H38 CT source handling of two input-global-scale parameters and whether defaults are deterministic vs value-load dependent; separately analyze the 13 cross-shard expert index ownership cases and any interaction with counted load completion using bounded source-only/synthetic evidence before planning additional DGX actions. No model/GPU, checkpoint tensor payload, host-defense relaxation, image rebuild, service change or PR Ready/Merge.


## H38 CT input-global-scale lifecycle / Layerwise numel-threshold — next source-only gate STAGED (2026-10-11)

After the genuine index-only checkpoint key-map Attempt 02 PASS_BASE_KEY_SCHEMA_ONLY (221,184/221,184 base routed keys and zero input_scale-substring names), the next question is **whether the two source-registered input-global-scale Parameters are initialized with effective values and whether cumulative loaded-numel is a safe proxy for unique destination-element completion**. Neither is resolved by the index key PASS.

Staged source-only tools: scripts/benchmark/inspect-h38-ct-input-scale-lifecycle.py, scripts/benchmark/check-h38-ct-input-scale-lifecycle.sh, tests/test_h38_ct_input_scale_lifecycle.py; canonical plan scripts/benchmark/evidence/orcarouter-h38-ct-input-scale-lifecycle-source-plan-20261011.md. They verify four already pinned installed-H38 CT/layerwise/meta/reload-utils source digests; use AST-only Python stdlib; check two plain torch.nn.Parameter(torch.empty(...)) constructor call sites, postconstructor set_weight_attrs, input-global-scale references in CT process_weights_after_loading, and Layerwise make_online_process_loader count-buffer-threshold syntax, with actual source line references and (if present) inverse-divide uses. Guarded read-only unprivileged runc image at exact clean Git HEAD, no network, GPU, model or checkpoint reading; image ID and H11/H12/H38 label gates unchanged.

**No installed-image run of this NEW source-lifecycle audit has occurred yet; repository code and synthetic tests are not a DGX PASS.** Public vLLM v0.29.0 CT has postload reciprocal use of w13/w2_input_global_scale, but public CT and exact installed-H38 CT hashes differ. A future verified source PASS may establish similar syntax in the actual installed image, not effective runtime values, safe defaults, completed CopyCounter events or successful model inference. The direct `torch.empty` allocations have **no explicit constructor fill values**; this is source syntax, not proof of reading undefined values in H38. The index source absence of input-scale keys remains independent actual DGX evidence.

**Layerwise accounting concern:** aggregate `info.load_numel` reaching `info.load_numel_total` is not a source guarantee of unique destination-element coverage if writes overlap or repeated callbacks occur. A bounded external CPU PyTorch synthetic witness established the logical possibility, not a real H38 event. Actual Layerwise closure/counter syntax is the scope of the new source gate, not a model load.

States unchanged: CT_CHECKPOINT_KEY_MAP_ATTEMPT02=PASS_BASE_KEY_SCHEMA_ONLY; CT_INPUT_SCALE_SOURCE_LIFECYCLE=STAGED_NOT_OBSERVED; CT_INPUT_SCALE_EFFECTIVE_VALUES=UNVERIFIED; CT_WEIGHT_COMPLETENESS=UNVERIFIED; CT_COPYCOUNTER_CREDIT=UNVERIFIED; CT_UNIQUE_DESTINATION_COVERAGE=UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE=FAIL; SHARD_8_11_BUFFER_LIFETIME=UNVERIFIED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; GPU_MODEL_RERUN=BLOCKED; HOST_PROTECTION=UNCHANGED; CT_META_PATCH=BLOCKED; PR_259=DRAFT_OPEN; MERGE=BLOCKED.

## H38 input-global-scale source lifecycle — actual DGX Attempt 01 PASS_SOURCE_ONLY (2026-10-11)

**This observed installed-image result supersedes the earlier STAGED/PENDING lifecycle source audit above**, without qualifying actual tensor values or real model loading. Operator ran exact clean checkout **5456809ab701dd38ef947afdc15bc88a32b22a13**, fixed H38 image sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc. Result: H38_CT_INPUT_SCALE_LIFECYCLE=PASS_SOURCE_ONLY; H38_CT_INPUT_SCALE_LIFECYCLE_PREFLIGHT=PASS_SOURCE_ONLY; source_check_rc=0; image_identity_unchanged=YES; gpu_or_model_load=NO; checkpoint_payload_read=NO; managed_service_mutation=NO; host_protection_changed=NO; ct_meta_patch_implemented=NO. Four previously pinned CT/layerwise/meta/reload-utils SHA256 files matched.

The exact installed H38 CT source has **w13_input_global_scale** torch.nn.Parameter(torch.empty(...)) constructor at line 179, registration at 183, set_weight_attrs at 187 and postload inverse division **1.0 / layer.w13_input_global_scale at line 238**. **w2_input_global_scale** analogously constructor at 189, registration 192, setter 196 and inverse division **1.0 / layer.w2_input_global_scale at 242**. Both constructors have **no explicit fill value and no explicit device**. Reported source_or_runtime_default_proven=NO means **the source inspector found no proven default**, not that every possible later initialization or alternate source has been excluded. effective_initial_value, actual_postload_invocation, checkpoint_load_event_for_this_parameter and effective_input_scale_values remain UNVERIFIED. Prior actual index-only checkpoint key-map Attempt02 showed zero input_scale-substring names among 223,046 indexed names; this does not establish that these parameters are invalid or uninitialized at runtime.

Installed Layerwise make_online_process_loader (line 149) passed **5/5 AST anchors**: buffer input arguments, get_numel_loaded(original_loader, bound_args), info.load_numel += num_loaded, threshold info.load_numel >= info.load_numel_total, and _layerwise_process invocation. This source supports the distinction between accumulated copy credit and unique Tensor destination coverage; it does **not** prove repeats, early completion or failed actual model loading.

Canonical independent observation scripts/benchmark/evidence/orcarouter-h38-ct-input-scale-lifecycle-attempt01-source-pass-20261011.md transcribes the supplied console output; the original /tmp/h38-ct-input-scale-lifecycle-attempt01-20261011.txt has not been separately byte-hashed. The earlier checkpoint key-map Attempt01 FAIL_KEY_SCHEMA stays historically immutable; Attempt02 PASS_BASE_KEY_SCHEMA_ONLY and CHECKPOINT_METADATA_ORDER_GATE=FAIL are independent.

Gate vector: CT_INPUT_SCALE_LIFECYCLE_SOURCE_ATTEMPT01=PASS_SOURCE_ONLY; CT_INPUT_SCALE_EFFECTIVE_VALUES=UNVERIFIED; CT_INPUT_SCALE_DEFAULT_GUARANTEE=UNVERIFIED; CT_INPUT_SCALE_ACTUAL_LOADER_EVENT=UNVERIFIED; CT_REAL_WEIGHT_COMPLETENESS=UNVERIFIED; CT_COPYCOUNTER_CREDIT=UNVERIFIED; CT_UNIQUE_DESTINATION_COVERAGE=UNVERIFIED; SHARD_8_11_BUFFER_LIFETIME=UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE=FAIL; FUNCTIONAL=NOT_REACHED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; GPU_MODEL_RERUN=BLOCKED; HOST_PROTECTION=UNCHANGED; CT_META_PATCH=BLOCKED; PR_259=DRAFT_OPEN; MERGE=BLOCKED.

**Next:** bounded source-only investigation of whether any deterministic default, alias or alternate-name loader write supplies both input scales *before* the postload inverse, retaining unresolved cases; separately prove whether counted numel can be connected to real per-expert unique destination events. No checkpoint payload, H38 torch/model/GPU, image rebuild, host protection/service mutation, CT meta patch or PR Ready/Merge.

## H38 CT input-global-scale counted-numel target — source-only inspector STAGED (2026-10-11)

The actual pinned H38 input-global-scale lifecycle source inspection **PASS_SOURCE_ONLY** and actual checkpoint-index 48×512×9 key-grid **PASS_BASE_KEY_SCHEMA_ONLY** are complete independent source/index checks, not a model-load qualification. Installed CT source has two torch.nn.Parameter(torch.empty(...)) input-global-scale registrations and CT postload reciprocal consumers; checkpoint index contains **zero input_scale-substring tensor key names**, while the Layerwise source has a counted-numel completion threshold. Their interaction is the next discriminator, not repeating those earlier PASS inspections.

**New code staged, NOT YET RUN on DGX:** scripts/benchmark/inspect-h38-ct-load-target-input-scale.py, scripts/benchmark/check-h38-ct-load-target-input-scale.sh, tests/test_h38_ct_load_target_input_scale.py. The stdlib-only AST gate requires four previously pinned CT/meta/reload-utils/layerwise source SHA256 values and verifies: skip-list SKIP_LOAD_TENSORS contents, registered input-global-scale shapes, get_layer_tensors(layer) parameter/buffer union, get_layer_size(layer) per-tensor numel and skip predicate, w13_num_shards = 2 if self.moe.is_act_and_mul else 1, Layerwise initialization/late refresh and accumulated >= threshold. The wrapper pins exact clean Git HEAD and original H38 image ID/labels, uses unprivileged no-network read-only runc limited to 512MiB/1CPU/64PIDs, no torch import, checkpoint, GPU/model or host changes. Canonical next-gate plan scripts/benchmark/evidence/orcarouter-h38-ct-input-scale-numel-target-source-plan-20261011.md.

**Illustrative source arithmetic ONLY** if actual num_experts=512, registrations exist when get_layer_size runs and input-global-scale names are not skipped: per-layer input-scale target contribution is 512×(w13_num_shards+1), hence 1,536 if w13_num_shards=2 or 1,024 if w13_num_shards=1. Across 48 independent layers this is 73,728 or 49,152 respectively. The real runtime layer's physical/local expert count and exact branch, input-scale callbacks, copied numel, initialization, unique destination coverage and any real threshold deficit are **UNVERIFIED**. Do not report these numbers as measured missing elements or a memory allocation peak.

Current gates: CT_INPUT_SCALE_LIFECYCLE_SOURCE_ATTEMPT01=PASS_SOURCE_ONLY; CT_CHECKPOINT_KEY_MAP_ATTEMPT02=PASS_BASE_KEY_SCHEMA_ONLY; CT_INPUT_SCALE_TARGET_SOURCE=STAGED_NOT_OBSERVED; CT_INPUT_SCALE_EFFECTIVE_VALUES=UNVERIFIED; CT_REAL_LOAD_NUMEL_DEFICIT=UNVERIFIED; CT_COPYCOUNTER_CREDIT=UNVERIFIED; CT_UNIQUE_DESTINATION_COVERAGE=UNVERIFIED; SHARD_8_11_BUFFER_LIFETIME=UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE=FAIL; FUNCTIONAL=NOT_REACHED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; GPU_MODEL_RERUN=BLOCKED; HOST_PROTECTION=UNCHANGED; CT_META_PATCH=BLOCKED; PR_259=DRAFT_OPEN; MERGE=BLOCKED. No image rebuild, checkpoint payload reads, H38 torch/model/GPU, managed service/host protection changes or PR Ready/Merge.

## H38 CT Input-scale numel-target contribution — real DGX source Attempt 01 PASS (2026-10-12)

**This actual, operator-supplied exact-image SOURCE-ONLY result supersedes the previous STAGED_NOT_OBSERVED status for this gate.** On clean DGX checkout **956ee0cd2db2a3ca607acd0516d6d35d62f09891**, unchanged fixed H38 image `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`, and all four previously pinned installed CT/layerwise/meta/utils SHA256 checks matching, the guarded inspector returned `H38_CT_INPUT_TARGET_GAP=PASS_SOURCE_POTENTIAL_ONLY`, `H38_CT_INPUT_TARGET_GAP_PREFLIGHT=PASS_SOURCE_POTENTIAL_ONLY`, `source_check_rc=0`, `image_identity_unchanged=YES`. It reported `gpu_or_model_load=NO`, `checkpoint_payload_read=NO`, `managed_service_mutation=NO`, `host_protection_changed=NO` and `ct_meta_patch_implemented=NO`.

All **9/9 source predicates** were true: registered parameter/buffer enumeration, no-None check, `get_layer_tensors` parameter/buffer union, `get_layer_size` `tensor.numel()` and SKIP exclusion, Layerwise initial/refresh count target, aggregated increment and `>=` completion predicate. The actual installed `SKIP_LOAD_TENSORS` literal does **not** include `w13_input_global_scale` or `w2_input_global_scale`. The registered source shapes are `(num_experts,w13_num_shards)` and `(num_experts,)` respectively. **Only if** they are registered at `get_layer_size` enumeration time do they contribute a potential `num_experts * (w13_num_shards+1)` elements to its count target. If there were 512 runtime registered expert rows and `is_act_and_mul` is true, the illustrative contribution is 1,536 per layer / 73,728 across 48 layers; otherwise 1,024 / 49,152. These are hypothetical arithmetic bounds under explicitly stated conditions, **NOT actual missing loader credits, source initialization values or measured memory**.

The prior actual input-scale reciprocal-consumer source `PASS_SOURCE_ONLY` and checkpoint-index `PASS_BASE_KEY_SCHEMA_ONLY` (221,184 base key names, 0 index keys containing `input_scale`) remain separate evidence. No actual runtime expert count, alternative input-scale writes/defaults, copied element uniqueness, `CopyCounter` credit, layer8/11 buffer lifetime or postload runtime invocation was established. The historical checkpoint index classifier Attempt01 `FAIL_KEY_SCHEMA` remains immutable; **`CHECKPOINT_METADATA_ORDER_GATE=FAIL`** remains FAIL. Canonical actual-console source evidence: `scripts/benchmark/evidence/orcarouter-h38-ct-input-scale-numel-target-attempt01-source-pass-20261012.md`; original user-reported `/tmp/h38-ct-input-target-gap-attempt01-20261011.txt` not independently byte-hashed.

Current gates: `CT_INPUT_SCALE_LOAD_TARGET_SOURCE_ATTEMPT01=PASS_SOURCE_POTENTIAL_ONLY`; `CT_INPUT_SCALE_LIFECYCLE_SOURCE_ATTEMPT01=PASS_SOURCE_ONLY`; `CT_CHECKPOINT_KEY_MAP_ATTEMPT02=PASS_BASE_KEY_SCHEMA_ONLY`; `CT_INPUT_SCALE_EFFECTIVE_VALUES=UNVERIFIED`; `CT_INPUT_SCALE_ALTERNATE_INITIALIZER=UNVERIFIED`; `CT_ACTUAL_LAYERWISE_TARGET_DEFICIT=UNVERIFIED`; `CT_COPYCOUNTER_CREDIT=UNVERIFIED`; `CT_UNIQUE_DESTINATION_COVERAGE=UNVERIFIED`; `SHARD_8_11_BUFFER_LIFETIME=UNVERIFIED`; `CHECKPOINT_METADATA_ORDER_GATE=FAIL`; `FUNCTIONAL=NOT_REACHED`; `HOST_STABILITY=INCONCLUSIVE`; `RM_MITIGATION=UNPROVEN`; `GPU_MODEL_RERUN=BLOCKED`; `HOST_PROTECTION=UNCHANGED`; `CT_META_PATCH=BLOCKED`; `PR_259=DRAFT_OPEN`; `MERGE=BLOCKED`.

**Next:** do not repeat prior key/source gate runs. Bound one more exact-source-only investigation of alternate initialization/alias/assignment and nuanced CopyCounter source credit; then formally decide whether H38 remains deferred while shifting engineering work to non-destructive installer/uninstaller/profile-switch acceptance. No H38 model/GPU, tensor payload, image rebuild, host/service protection relaxation, CT meta patch or PR Ready/Merge.

## Managed lifecycle acceptance — operator focus after H38 source-only closure (2026-10-12)

**Engineering focus shifts to the installer, uninstaller, and managed model-profile selector/transaction, without promoting H38 runtime.** Canonical acceptance matrix: `docs/MANAGED-LIFECYCLE-ACCEPTANCE.md`. Detailed operator steps remain in `OPERATIONS.md`; the matrix strictly separates simulation/CI from historical live runs, and from currently unqualified live/destructive scenarios.

Implemented (code paths exist): bilingual six-stage fresh install and completed-install management wizard, model registry/listing, selectable OrcaRouter/NVIDIA/mazinb/Hybrid H6 profiles, settings/default refresh, transactional profile switch and recovery, normal/purged uninstall wizard, persistent cumulative asset ownership and dependency-based refusal. `lychee888` remains non-installable. Existing independent test groups include `tests/test_installer_profile_manager.py`, `tests/test_model_profiles.py`, `tests/test_installer_plan_parity.py`, `tests/test_profile_switch_transition.py`, `tests/test_settings_transition.py`, `tests/test_asset_ownership.py`, `tests/test_release_profile_refresh_transition.py`, and `tests/test_operation_lock.py`. **Implementation is not a live all-path qualification.**

New `tests/test_uninstall_wizard_preview.py` runs the actual bilingual `uninstall.sh --dry-run` CLI against disposable HOME/XDG/manifests and verifies normal preserve, selected purge preview, full purge preview and byte-identical model/release/manifest state. A full purge preview without a cumulative registry correctly reports **no registry**; it does not fabricate an owned-asset list. These are synthetic **non-destructive** tests and do not confirm real uninstall would succeed or that live files can be safely deleted. Full live clean-host install→service→doctor→uninstall→reinstall→purge E2E remains NOT QUALIFIED. The historical Hybrid→OrcaRouter→Hybrid switch has a FUNCTIONAL PASS but strict HOST-STABILITY FAIL, not a blanket switch-all-pairs success. mazinb has live readiness but strict RM HOST-STABILITY FAIL; H38 managed runtime stays NOT_REACHED/INCONCLUSIVE and blocked.

The latest real fixed-image Input-scale load-target source Attempt01 `PASS_SOURCE_POTENTIAL_ONLY` already proved nine source predicates on original DGX SHA `956ee0cd2db2a3ca607acd0516d6d35d62f09891`. Do **not** repeat the same H38 source inspection to delay lifecycle work. H38 alternative input-scale default/alias and CopyCounter actual unique coverage remain UNVERIFIED; `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `GPU_MODEL_RERUN=BLOCKED`, `HOST_PROTECTION=UNCHANGED` and `PR_259=DRAFT_OPEN / MERGE=BLOCKED`. No H38 GPU/model, checkpoint payload, image rebuild, CT meta or service/protection change is authorized by lifecycle documentation/tests.

**Next admissible operator gate:** after a fresh CI-qualified exact HEAD, gather **read-only** live inventory via `./install.sh --list-models`, `./install.sh --list-backends`, the four transaction `status` paths and `./scripts/doctor.sh`; avoid real installer/uninstaller execution. This provides an operator state snapshot, not full E2E acceptance. Run destructive full purge only on an independent disposable target after a separate approval and safety preflight, never on the active single Spark.

## Lifecycle acceptance M1 implementation — synthetic wizard previews and read-only snapshot (2026-10-12)

**Latest focus:** staged `docs/MANAGED-LIFECYCLE-ACCEPTANCE.md` separates managed installer/uninstaller/model-switch implementation from CI/disposable-fixture verification, historical Hybrid↔OrcaRouter FUNCTIONAL PASS / strict HOST-STABILITY FAIL, and still-unqualified full live clean-host E2E. `lychee888` remains planned/non-installable. The H38 managed path remains BLOCKED and the independent strict checkpoint metadata ORDER_GATE stays FAIL.

New `tests/test_uninstall_wizard_preview.py` invokes the actual `uninstall.sh --dry-run` CLI in a disposable HOME/XDG with a realistic synthetic installed manifest and sentinel model/release data. Five cases check English/Korean normal-preserve previews, selected model/image/swap purge preview, full-purge preview, no mutation and no need for live Docker/sudo. Full-purge preview with **no** cumulative ownership registry correctly reports an absent registry, NOT an invented owned-asset list; an initial expectation error in the new test was corrected to that exact CLI behavior. **This is synthetic only: no real uninstall or removal was run.**

New `scripts/lifecycle/inspect-readonly-lifecycle.sh` plus `tests/test_managed_lifecycle_readonly_snapshot.py` stage a strictly bounded operator audit requiring a clean exact SHA, and run **only** the model/backend inventory commands, four transaction status queries, and read-only Doctor. Output `MANAGED_LIFECYCLE_READONLY=COLLECTED_READ_ONLY` means **snapshot collection**, never host-stability, full E2E or profile-switch success; individual exit codes and `PARTIAL_CHECK_FAILURE` are retained for issues. This new DGX on-host audit **has not yet been executed**. The uninstaller's `--dry-run` exits before real-operation transaction locks and destructive preflights, so it must not be used as evidence that real purge is eligible. No real purge or full live install is authorized.

Next after CI: operator runs exact-SHA read-only lifecycle snapshot on the existing Spark and returns complete stdout/exit; we then file immutable evidence and close **M1 at the snapshot/simulated level only**. Full M2 destructive install→uninstall→reinstall acceptance must run on a separate disposable host; M3 all-profile live switches remain PARTIAL, M4 H38 BLOCKED. Existing single Spark state/monitor/service must not be disrupted. PR #259 DRAFT_OPEN / MERGE BLOCKED until independent H38 conditions change.

## Managed lifecycle DGX read-only Attempt 01 — PARTIAL_CHECK_FAILURE / Doctor 5 FAIL + 2 WARN (2026-10-12)

**This actual operator DGX result supersedes the earlier "M1 snapshot not yet executed" description above.** On clean exact `feat/h38-managed-integration` HEAD `bbeceaf16c0c4bba4385c38cfead32e5dc243769`, the pinned `scripts/lifecycle/inspect-readonly-lifecycle.sh` reported `MANAGED_LIFECYCLE_READONLY=PARTIAL_CHECK_FAILURE`, `MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED`, `lifecycle_audit_rc=3` without host mutation, uninstall/install/purge, GPU or model launch.

**Read-only PASS:** installed and active OrcaRouter model/image; local mazinb + Hybrid H6 model/images installed but inactive; NVIDIA model/image absent (experimental/installable); lychee888 planned/non-installable. Backend vllm stable/installable, sglang planned/non-installable. **Four lifecycle states idle**, with each command rc=0: PROFILE_SWITCH_STATE, TRANSACTION_STATE, UPDATE_STATE and RELEASE_PROFILE_REFRESH_STATE. Doctor passed installation complete, current+previous immutable releases and qualification digest, ownership registry, 18-shard checkpoint/index/config, model mount/name/image consistency, enabled systemd unit, API access sockets, active PLE swap, memory/swap/disk margins and lack of recorded incomplete lifecycle transitions.

**Exactly 5 Doctor FAIL:** (1) `runtime-commit.env` missing **or unsafe**; (2) Docker runtime `exited`; (3) `docker port` returned **no published port**, so loopback-only API check failed; (4) enabled memory monitor `monitor.pid` missing; (5) loopback health endpoint unresponsive. **Exactly 2 WARN:** legacy OrcaRouter image selected, and systemd managed-service unit installed/enabled but **inactive**. Doctor `rc=1`. Several failures plausibly follow from the runtime's stopped/inactive state; their causal order, intentional protective stop vs startup failure, and old/new release provenance are **UNVERIFIED**. Do not recategorize the stopped runtime as a bad port binding, proven memory-protection trip or an H38 startup failure. Real current+previous immutable release ids `ff67bab3c94d6992f61b9535836df97f03b9c022` and `a8aeca47433dc4033b3f1f995eb59023467222ce` passed, respectively. Host point-in-time snapshot: non-CMA available 118 GiB, non-CMA free 80,045 MiB, swap free 143 GiB, model disk 104 GiB; **not an RM-host-stability qualification**.

Canonical actual operator-console evidence: `scripts/benchmark/evidence/managed-lifecycle-readonly-attempt01-doctor-partial-20261012.md`; user-reported `/tmp/managed-lifecycle-readonly-attempt01-20261012.txt` bytes and SHA256 not independently verified. M1 tests/CI `PASS` but **M1 host Doctor FAIL**; no M1 healthy/safe-live approval. M2 destructive install/uninstall/reinstall NOT RUN, M3 complete cross-profile E2E NOT QUALIFIED, M4 H38 managed BLOCKED. Strict H38 `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `FUNCTIONAL=NOT_REACHED`, `HOST_STABILITY=INCONCLUSIVE`, `GPU_MODEL_RERUN=BLOCKED`, `HOST_PROTECTION=UNCHANGED`, `PR_259=DRAFT_OPEN`, `MERGE=BLOCKED` unchanged.

**Next safe discriminator:** staged `scripts/lifecycle/inspect-readonly-runtime-offline.sh` and associated source-only guard tests ask for **stopped container ExitCode/OOMKilled/StartedAt/FinishedAt, declared Docker port bindings, systemd ActiveState/SubState/Result/ExecMainStatus and file type/existence for runtime-commit.env/runtime-stop.env/monitor.pid** on an exact clean CI-qualified SHA. It cannot restart/repair anything; it explicitly retains RUNTIME_STOP_REASON=NOT_YET_PROVEN. Do not start/restart the legacy runtime or H38, edit/delete attestation or stop-marker, force a transition commit, relax monitor, or run destructive purge to clear Doctor failures.

## Managed runtime offline metadata Attempt 01 — exit0, no Docker OOM, correct loopback binding (2026-10-12)

**Actual operator read-only DGX observation supersedes the earlier "offline probe not yet executed" statement.** On clean HEAD `6ce45561640f4069d534cbe04f5064a39095a88a`, `scripts/lifecycle/inspect-readonly-runtime-offline.sh` produced `MANAGED_RUNTIME_OFFLINE=COLLECTED_READ_ONLY`, `offline_diagnostic_rc=0`, `H38_MODEL_GPU_RERUN=BLOCKED`, no runtime/service/protection mutation. Its successful rc means **data collection only**, not healthy model or M1 live acceptance.

Actual Docker state: `exited`, `ExitCode=0`, `OOMKilled=false`, `State.Error=""`, started 2026-10-07 07:35:45.800732164 UTC (**16:35:45 KST**), finished 2026-10-07 13:08:34.847184942 UTC (**22:08:34 KST**). Docker `HostConfig.PortBindings` declared the **correct** loopback-only `8888/tcp → 127.0.0.1:8888`, while runtime `NetworkSettings.Ports={}` because stopped. Earlier Doctor's `no published port` remains a **readiness/active-port check failure**, NOT evidence of misconfigured HostConfig. Systemd `Result=success`, `ExecMainCode=1` (process-exited classification, **not process status 1**), `ExecMainStatus=0`, service `inactive/dead` with ActiveEnterTimestamp **2026-10-07 22:08:29 KST**, InactiveEnterTimestamp **22:18:17 KST**. Container finished ~5.85 seconds after unit active entry, unit became inactive ~9m42s after container finish. These temporal relations **do not identify** the stop requester or intent; `exit_code=0` and no Docker OOM do not prove a safe, intentional/protective, fully stable shutdown.

At this later probe `runtime-commit.env`, `runtime-stop.env`, and `monitor.pid` were **all ABSENT**; the prior Doctor's `missing or unsafe` attestation failure is now narrowed to **currently absent**, without proving historical file write/deletion reasons or whether a transient protective stop ever occurred. The earlier live Doctor **5 FAIL / 2 WARN** classification and `M1_HOST_HEALTH=NOT_QUALIFIED` stand. Strict H38 checkpoint `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `FUNCTIONAL=NOT_REACHED`, `HOST_STABILITY=INCONCLUSIVE`, `RM_MITIGATION=UNPROVEN`, `GPU_MODEL_RERUN=BLOCKED`, `HOST_PROTECTION=UNCHANGED`, `PR_259=DRAFT_OPEN`, `MERGE=BLOCKED` remain.

Immutable source-of-truth actual operator evidence: `scripts/benchmark/evidence/managed-runtime-offline-attempt01-exit0-no-oom-20261012.md`; original user-reported `/tmp/managed-runtime-offline-attempt01-20261012.txt` not separately byte-hashed.

**Next bounded read-only diagnostic:** `scripts/lifecycle/inspect-readonly-runtime-stop-journal.sh` (+ `tests/test_managed_runtime_stop_journal_readonly.py`) requires exact clean SHA, host timezone +0900 and gathers **at most 160** historical `qwen38-flash-next.service` journal lines within Oct 07 **21:55–22:25 KST** only. This journal diagnostic has **NOT yet run on the operator DGX**. It does not start/restart service/container or inspect checkpoint payload/GPU. Keep stop reason NOT_YET_CLASSIFIED if historical log access is unavailable or ambiguous. Do not change host service/monitor, regenerate attestation, run installer/update or restart H38 just to pass Doctor.

## Oct 07 managed-runtime stop: protection-triggered candidate abort CONFIRMED in actual service journal (2026-10-12)

**This actual DGX operator journal supersedes the earlier `RUNTIME_STOP_REASON=NOT_YET_PROVEN` for the managed transition sequence**, not the separate question of *which numeric monitor threshold fired*. Actual guard checkout **`efafe36fcc2e477e9d0cd110e4db275ba40dc489`**, October 7 service journal limited to **21:55–22:25 KST**, `RUNTIME_STOP_JOURNAL=COLLECTED_READ_ONLY`, `journal_audit_rc=0`, no host/service/protection/GPU/model mutation. The inspector's own `RUNTIME_STOP_CAUSE=NOT_YET_CLASSIFIED` is a deliberately static output marker; **human reading of the actual recorded messages supplies the following independent evidence classification**:

- Immediately before replacement, the **previous** managed vLLM answered HTTP 200 for `/health`, `/v1/models` and chat completions through about **22:08:29 KST**. This proves observed pre-transition endpoint responses, NOT the candidate's readiness or full functional correctness.
- **22:08:29.818**: `Managed service stop: no runtime attestation; preserving any canonical container.` Then `preflight-start`, transition recovery idle, **22:08:30.019** `Stopping current runtime container gracefully: qwen38-flash-next`; **22:08:35.049** transition prepared `previous=1`.
- **22:08:35.485**: new OrcaRouter candidate started with `executor=mp, PLE=mmap, SPEC=mtp k=2, qsa_exact_topk=1`; **memory monitor started (`protect=1`, pid 3127696)** and its log location announced `/home/inlc/.local/state/qwen38-spark/monitor.log`. These are startup assertions, not candidate READY.
- **22:08:35–22:17:26**: `candidate-validating`, readiness waiting through `540/1800 seconds`.
- **22:18:16.743**: exact journal `Candidate runtime was stopped by memory protection during startup; leaving managed runtime stopped.`; **22:18:17.125** `Previous runtime container restored but left stopped after memory protection.`; **22:18:17.125895** `Runtime transition aborted by memory protection (state=idle).` A following unit stop handler said no runtime attestation and preserved any canonical container.

**Thus the managed transition aborted due to a recorded memory-protection candidate stop, and previous runtime was purposefully restored-but-left-stopped.** This directly explains the earlier offline canonical-container `ExitCode=0`, Docker `OOMKilled=false`, systemd inactive/Result=success and the Doctor's unresponsive API; it does NOT prove the candidate's ExitCode or establish a true host/kernel OOM. The existing Docker `HostConfig.PortBindings` loopback `127.0.0.1:8888` was correctly configured and stopped runtime port publication absence remains a readiness failure, not a port-configuration bug.

**Still unknown:** which numeric `monitor-runtime` predicate fired (low non-CMA free + low available, low free + 256MiB-or-more swap growth, or critically low swap free); whether protection was a *false-positive* on normal cold load; actual NVIDIA RM host stability; historical marker cleanup. The current monitor source documents this heuristic but does not supply Oct07 exact samples/configuration. Original journal logfile `/tmp/managed-runtime-stop-journal-attempt01-20261012.txt` is only user-reported, not independently hashed. Canonical source-backed evidence: `scripts/benchmark/evidence/managed-runtime-stop-journal-attempt01-protected-abort-20261012.md`.

**One final strictly bounded optional clarification:** new `scripts/lifecycle/inspect-readonly-monitor-trigger.sh` and `tests/test_managed_monitor_trigger_readonly.py`, exact clean Git SHA, select Oct07 **22:08–22:19 KST** structured monitor numeric lines only (≤120 lines; local log must be regular and ≤64MiB). No service/GPU/host mutation; inspect numeric trigger without dumping embedded Docker prompts/tokens. The operator has **NOT YET** run this monitor-only probe. If log absent, too large, or inconclusive, **stop further recursive H38 diagnostics** and retain trigger UNKNOWN. Continue installer/uninstaller/model-switch M1–M3 **non-destructive** acceptance independently.

Gates: `MANAGED_TRANSITION_CANDIDATE_PROTECTION_ABORT=CONFIRMED_BY_JOURNAL`; `MANAGED_TRANSITION_PREVIOUS_RESTORED_STOPPED=CONFIRMED_BY_JOURNAL`; `MONITOR_TRIGGER_PREDICATE=UNVERIFIED`; `MONITOR_FALSE_POSITIVE=UNVERIFIED`; `M1_HOST_HEALTH=NOT_QUALIFIED`; `M2_DESTRUCTIVE_E2E=NOT_RUN`; `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`; `M4_H38=BLOCKED`; `CHECKPOINT_METADATA_ORDER_GATE=FAIL`; `HOST_STABILITY=INCONCLUSIVE`; `RM_MITIGATION=UNPROVEN`; `GPU_MODEL_RERUN=BLOCKED`; `HOST_PROTECTION=UNCHANGED`; `PR_259=DRAFT_OPEN`; `MERGE=BLOCKED`. No image rebuild, actual H38 model/GPU, host protection/service changes, synthetic success promoted to host readiness, attestation re-creation, PR Ready or Merge.

## Managed candidate memory-protection Oct07 numeric trigger — actual DGX source evidence VERIFIED (2026-10-12)

**This operator-recorded DGX monitor result supersedes the earlier `MONITOR_TRIGGER_PREDICATE=UNVERIFIED` and "numeric probe not yet run" status in historical sections above**, but it does not resolve **whether the monitor's heuristic was appropriately calibrated** for cold loading or guarantee actual NVIDIA RM host stability. The bounded read-only inspector ran on exact clean HEAD `7e4580bdca4054a788715bdf141e006bbb6b3f59`, selected **17** actual Oct07 monitor messages from a **2,242,582-byte** readable source file, and returned `MONITOR_TRIGGER_READONLY=COLLECTED_READ_ONLY`, `monitor_audit_rc=0`. No runtime/model/GPU, checkpoint payload, managed service, host-protection setting or local state was altered. Canonical source data: `scripts/benchmark/evidence/managed-monitor-trigger-attempt01-low-free-swap-growth-pass-20261012.md`; the original reported `/tmp/managed-monitor-trigger-attempt01-20261012.txt` was **not independently hashed**.

**Actual monitored threshold configuration, not assumed defaults:** At **2026-10-07 22:08:35 KST** the new OrcaRouter candidate monitor announced `mode=protect available-warn=6GiB noncma-free=2GiB free-gate=10GiB swap-growth=256MiB swapfree=8GiB`. It logged healthy heartbeats through **22:16:40** and then:
- **22:17:33**: non-CMA free **2,017 MiB < 2,048 MiB**, swapgrowth **17 MiB < 256 MiB**, non-CMA available **26,022 MiB > 10GiB**, swapfree **146,470 MiB > 8GiB** → `protect=0/5` (warning but no protection count).
- **22:17:35**: non-CMA free **1,151 MiB**, swapgrowth **654 MiB** → **`protect=1/5`**. Following ~2-second samples **22:17:37 (2/5)**, **22:17:39 (3/5)**, **22:17:41 (4/5)** and **22:17:43 (5/5)** kept non-CMA free below 2GiB and swapgrowth above 256MiB, while non-CMA available remained ~27–30GiB and swapfree ~140GiB.
- **22:17:43**: monitor explicitly logged `PROTECT stopping qwen38-flash-next gracefully to preserve host stability`. **The triggered branch is low immediate non-CMA free AND sustained swap consumption after monitor start** (consecutive=5), **not** the low-available threshold and **not** critically low SwapFree. The service journal subsequently recorded **22:18:16** the candidate protected abort and **22:18:17** restored-but-stopped old runtime and aborted transition `state=idle`.

This confirms **intended monitor policy logic ran on recorded counter values**, not that the policy's classification was necessarily right for cold-loading PLE/mmap/model behavior. Candidate `Ready`, kernel OOM, NVIDIA `NV_ERR_NO_MEMORY`, exact impact without protection, and false-positive vs correctly protective cutoff remain **UNVERIFIED**. Earlier Docker `ExitCode=0 OOMKilled=false` was the intentionally stopped **previous** canonical runtime, not evidence of candidate success.

**Lifecycle workstream handoff is NOW APPROPRIATE.** No further live H38 source/journal experiments for this issue are requested. Maintain `M1_HOST_HEALTH=NOT_QUALIFIED` from actual Doctor **5 FAIL/2 WARN**; the historical stopped state is explained, not repaired. Continue **M1 synthetic/CLI wizard and ownership-safe cancellation/recovery acceptance**, **M2 independent disposable-host destructive E2E design (NOT_RUN)** and **M3 profile-switch all-pairs simulation (NOT_QUALIFIED)**. H38 `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `FUNCTIONAL=NOT_REACHED`, `HOST_STABILITY=INCONCLUSIVE`, `RM_MITIGATION=UNPROVEN`, `GPU_MODEL_RERUN=BLOCKED`, `HOST_PROTECTION=UNCHANGED`, `CT_META_PATCH=BLOCKED`, `PR_259=DRAFT_OPEN`, `MERGE=BLOCKED`. Do **not** restart a candidate to fix Doctor, relax monitoring, create missing attestation or purge assets on the single active Spark.

New vector: `MONITOR_TRIGGER_SOURCE=PASS_ACTUAL_LOW_FREE_AND_SWAP_GROWTH`; `MONITOR_TRIGGER_CONSECUTIVE=5/5_CONFIRMED`; `MONITOR_POLICY_FALSE_POSITIVE=UNVERIFIED`; `MONITOR_REAL_HOST_OOM=UNVERIFIED`; `M1_HOST_HEALTH=NOT_QUALIFIED`; `GPU_MODEL_RERUN=BLOCKED`.


## Early swap-ownership refusal for destructive uninstall (2026-10-12)

**Safety contract:** `uninstall.sh --purge-swap` and `--purge-all` (which implies swap purge) now reject a manifest with `SWAP_OWNED!=1` **after dry-run preview but before** acquiring the operation lock, bootstrapping asset ownership, stopping Docker/systemd, or deleting any installer data. The former check was positioned after teardown and, for full purge, after owned asset removal; an unowned swap could therefore leave a partially uninstalled deployment before refusing. `--dry-run` remains preview-only and does not certify real purge eligibility.

`tests/test_uninstall_wizard_preview.py::test_unowned_swap_purge_fails_before_host_or_fixture_mutation` exercises the real CLI on disposable HOME/XDG state for selected swap and full purge with daemon-command denial stubs and byte-for-byte fixture preservation. This is a **synthetic fail-closed regression**, not an authorized live DGX uninstall. M2 destructive E2E remains NOT_RUN; M1 actual host Doctor remains NOT_QUALIFIED and H38 runtime remains BLOCKED. PR #259 remains Draft/Open, merge blocked.


## Uninstall final-consent cancellation is read-only before lock/bootstrap (2026-10-12)

The real `uninstall.sh` previously ran `asset_bootstrap_install` and destructive-eligibility preflights before asking the operator to enter `DELETE`. A declined confirmation could create/update `asset-ownership.json` despite no authorized uninstall. The `DELETE` consent check is now **before** `acquire_operation_lock` and cumulative-ownership registry writes, but **after** strict manifest parsing and early unowned-swap refusal. EOF is an explicit cancellation error. `--yes` bypasses only interactive consent; post-lock transaction guards and asset preflights remain mandatory. This is not a guarantee of rollback **after** destructive steps begin.

New `tests/test_uninstall_wizard_preview.py::test_cancel_or_eof_preserves_ownership_and_install_state` calls the real non-dry-run CLI with a disposable HOME/XDG fixture. English default, Korean selected purge, full purge refusal and full purge EOF must reject before host command execution and preserve fixture bytes without creating `asset-ownership.json` or `operation.lock`. External Docker/systemd/sudo/swapoff commands are denied by PATH stubs. Initial [CI 38186275070](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38186275070) SUCCESS (766/766 synthetic tests) at commit `2e86ed4fa75a28bd585ff932cffdd4c4afab59ef`; final CI for the extended pre-existing-registry fixture tracked in PR #259. No actual DGX state was touched. M1 host NOT_QUALIFIED; M2 destructive E2E NOT_RUN; M3 all-profile E2E NOT_QUALIFIED; M4 H38 BLOCKED; PR #259 Draft/Open, Merge BLOCKED.

Existing cumulative-registry preservation is additionally tested by `test_cancel_preserves_existing_ownership_registry_bytes`: a pre-existing valid `asset-ownership.json` must retain its exact bytes on operator cancellation, with an owned-model manifest that would otherwise trigger legacy bootstrap migration. No host-side daemon calls are allowed. A confirmed, actively executing uninstall still requires independent destructive E2E qualification.


## Preflight-staged ownership registry for approved uninstall (2026-10-12)

The approved real `uninstall.sh` previously bootstrapped the **canonical** cumulative ownership registry before `preflight-one`, `preflight-purge`, external-container references and unowned-service checks. A failure could leave an altered `asset-ownership.json` without any authorized teardown. The revised flow, under the existing operation lock, copies the registry into a private same-filesystem `.uninstall-preflight.*` directory, runs the **existing** legacy bootstrap and eligibility checks against that staged copy, and publishes it only if all checks succeed; on a handled failure, an EXIT trap deletes the staged directory. An unchanged original registry is not needlessly replaced. Symlink/non-regular canonical registry paths are rejected. The operation lock file may remain after refusal. A process killed without running EXIT traps may leave a private staging directory for later inspection; no claim of crash-atomicity is made.

The new `test_approved_purge_preflight_failure_preserves_cumulative_registry` uses the real CLI with `--yes` on disposable HOME/XDG synthetic owned base + retained unowned dependent, exercising both `--purge-model` and `--purge-all`. It asserts blocked deletion, identical canonical registry/manifest/model bytes, no external host mutator calls and no left-behind staging directory. The actual DGX was not touched; this is synthetic failure-preflight coverage, not destructive-install/uninstall E2E or proof of post-teardown recovery. M1 live Doctor still NOT_QUALIFIED; M2 destructive E2E NOT_RUN; M3 all-pairs NOT_QUALIFIED; M4 H38 BLOCKED. PR #259 Draft/Open, merge blocked.


An additional `test_external_container_image_refusal_preserves_registry` exercises a synthetic `IMAGE_OWNED=1` with an external Docker-container reference. Read-only Docker image inspection and `ps` are stubbed; `docker rm`, image deletion, sudo/systemctl/swapoff, real host data access and model load are not allowed. The installer-owned image is refused at the **external-container preflight**, and the canonical registry and fixture bytes remain unchanged. This expands synthetic eligibility refusal coverage without asserting successful destructive uninstall.


### Synthetic approved-uninstall preflight result — CI verified (2026-10-12)

Exact tested code HEAD `c332959df7676d3d87a69eb628b94fa5af862e41`: [GitHub Actions CI #38188708849](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38188708849) **SUCCESS, 769/769 Python unit tests**, Bash syntax PASS, ShellCheck PASS, Python compilation PASS, whitespace PASS. Earlier base staging code HEAD `6186294fda78d9fed5d5bac8f35029b52c4a2856`: [CI #38188545527](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38188545527) **SUCCESS, 768/768**. This evidence covers synthetic failure branches for retained dependent model and externally referenced image; it is **not** evidence of successful real deletion or crash-atomicity. No DGX host operations were executed. All M1 host-health, M2 destructive E2E, M3 all-pairs, M4 H38, and PR #259 merge blockers remain.


## Docker removal failure and partial-uninstall retry safety (2026-10-12)

Previously `uninstall.sh` ignored **every** `docker rm -f` failure with `|| true`, risking model/image/release deletion when the Docker daemon or authorization was broken and the managed container could still exist. Now arbitrary Docker errors are **fail-closed before asset purge**; only an exact Docker `No such container: <managed name>` message permits idempotent continuation. `PHASE=complete` remains when service/container removal fails, allowing an operator-directed retry. `asset-ownership.json` may already reflect the successful preflight; the service may already have been disabled or removed. Neither rollback of completed teardown nor crash-atomicity is claimed. Real managed host and H38 model remain untouched. New disposable synthetic fault-injection regressions cover service-remove failure, Docker-remove failure, retry-after-recovery and already-absent Docker container; final CI result to be recorded in PR #259. M1 live host NOT_QUALIFIED, M2 destructive E2E NOT_RUN, M3 profile all-pairs NOT_QUALIFIED, M4 H38 BLOCKED, PR Draft/Open, Merge BLOCKED.


### Post-teardown failure and safe retry: synthetic CI acceptance (2026-10-12)

**Evidence:** [CI #38189466067](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38189466067) **SUCCESS, 771/771** at `09527d81121ad6fe820400382a12eb9a443318b6`; [CI #38189596217](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38189596217) **SUCCESS, 772/772** at `69df950fc4a7f1c6038ab8aff9f5e3ee45dc80b7`, including Bash syntax, ShellCheck, Python compilation and whitespace checks.

A synthetic real-CLI sequence using only disposable HOME/XDG and command denial/stubs shows:
1. Managed service-removal fault => no Docker removal attempt, owned synthetic model intact, manifest `PHASE=complete`.
2. Service removal succeeds, Docker daemon removal fails => script exits nonzero **before** model/image/release purge, records no completed uninstall, owned model and release preserved; published registry retains ownership evidence.
3. After fault clearance, retry completes, removes the **synthetic owned model only**, retains release data and sets `PHASE=uninstalled`.
4. An exact Docker `No such container` diagnostic is idempotent; unowned model and release remain.
5. On `--purge-all`, after **synthetic model and image removal** a simulated swap-remove failure exits nonzero with remaining fake swap and release preserved, manifest still `PHASE=complete` and cumulative registry reflecting completed asset removal. On retry after fault clearance, the script tolerates the already absent owned model/image, removes only the fake swap and synthetic release/manifest, and completes.

This proves bounded **synthetic retry behavior**, NOT rollback of previously removed components, interruption/crash durability, actual systemd/Docker/PLE behavior, independent disposable-host install/remove/reinstall E2E, or single-DGX host qualification. Actual DGX was untouched. M1 actual host NOT_QUALIFIED; M2 destructive E2E NOT_RUN; M3 all-profile E2E NOT_QUALIFIED; M4 H38 BLOCKED. PR #259 remains Draft/Open, Ready/Merge BLOCKED.


## SIGKILL interrupted-uninstall preflight recovery (2026-10-12)

Under the lifecycle operation lock and before creating a staged ownership copy or doing any teardown, `uninstall.sh` now refuses existing `.uninstall-preflight.*` artifacts, including symlinks. A `SIGKILL` or power loss bypasses shell EXIT traps, so these private staging snapshots may survive. Do **not** automatically delete them or treat them as canonical ownership evidence. Inspect each exact stale path, verify ownership and contents, confirm no concurrent lifecycle operation, and handle its removal/quarantine only as a separately authorized maintenance action. No blanket wildcard deletion on the active DGX. This guard is fail-closed: the install manifest and canonical ownership registry remain authoritative, and model/image/swap removal cannot proceed while an unreviewed preflight snapshot exists. Synthetic SIGKILL crash tests and exact GitHub CI evidence are tracked in PR #259; actual power-loss durability is NOT_QUALIFIED. PR remains Draft/Open and merge blocked.


### Interrupted uninstall recovery procedure and validation boundaries (2026-10-12)

**Stop condition:** a `.uninstall-preflight.*` artifact, missing model ownership manifest, drifted registry fingerprint, interrupted model deletion, or a state/host mismatch is **not** permission to resume unattended `uninstall.sh --yes`. Leave all host protection and stopped runtime settings intact.

1. Preserve evidence before any repair: read the canonical `install.env`, `asset-ownership.json`, exact `.uninstall-preflight.*` entries, file owner/mode and applicable logs **without executing the staged file or running host mutators**. The canonical registry is the only ownership authority; staged snapshots are untrusted. Acquire or confirm exclusive lifecycle maintenance ownership before any later mutation.
2. Reconcile actual read-only service/container/swap state with the recorded manifest. `PHASE=complete` after a crash **does not** mean the service is still installed, container still exists, model remains complete or swap is intact. Never infer successful teardown from parent process exit status alone; child deletion commands may outlive a killed parent.
3. For a verified orphan staging directory, document its exact path and integrity, quarantine/clear **only that exact path** after operator review, and rerun preflight before resuming; never use broad `rm -rf` globs or follow symlinks. Unreviewed staging blocks the real uninstaller.
4. For a partially deleted model with a missing/drifted `.qwen38-model-manifest.json` or `.qwen38-hybrid-manifest.json`, keep the original cumulative registry and the surviving model data; **do not invent a marker or weaken preflight**. Recovery requires independent trusted backup/provenance verification, otherwise quarantine and a separately authorized reinstall on an isolated disposable host.
5. If a fully removed owned model is already absent but a dedicated swap/release remains, a repeat purge is eligible **only after** checking the original model path, ownership history, live host state, swap provenance and pending lifecycle artifacts. No automated or live sole-DGX destructive recovery is authorized by the synthetic tests.
6. Preserve an interruption evidence report (files/hashes, timeline, host-command results, whether child process survived, repair decision). Host power-loss filesystem ordering/fsync, SIGKILL of the whole process group, real teardown replay and install→remove→reinstall remain unverified separately.

Synthetic `test_sigkill_during_stage_requires_manual_stale_recovery`, `test_sigkill_partway_through_model_delete_requires_verified_recovery`, and `test_sigkill_at_swap_after_model_purge_can_resume` use the **real** CLI with disposable HOME/XDG, fake owned model/swap and PATH-denied Docker/sudo/systemctl/swapoff. Their SIGKILL is injected from a child stub and the stub must exit immediately rather than completing its own deletion after killing the parent. These tests do not simulate power loss or provide live-host authorization. Previous failing CI attempts due to a child-stub execution bug are retained as historical failures; the corrected commit and its CI outcome are recorded in PR #259. All M1 actual-host/M2 real-destructive/M3 all-profile/H38 gates remain blocked or unqualified; PR #259 remains Draft/Open, Ready/Merge BLOCKED.


## Guarded DGX code synchronization and synthetic-only local verification (2026-10-12)

The previous 775/775 GitHub Actions result was **CI**, not evidence that the operator's single DGX had fetched the latest branch or run any tests locally. To close this handoff gap without touching live host resources, `scripts/lifecycle/verify-synthetic.sh` now validates an explicitly supplied 40-character checkout SHA, clean Git worktree, exact `feat/h38-managed-integration` branch and matching `origin/feat/h38-managed-integration` tracking ref **without any Git mutation**. It then runs bounded Python synthetic lifecycle suites inside a disposable HOME/XDG_STATE_HOME/XDG_DATA_HOME/TMPDIR, with a first-in-PATH deny wrapper for Docker, sudo, systemctl, swapoff/swapon, mount/umount and nvidia-smi. Tests are restricted to installer/uninstaller preview, ownership, operation lock, lifecycle integration and non-mutating lifecycle snapshot tests; no actual install/uninstall, Docker, service change, runtime startup, model download or host Doctor is invoked. The test wrapper is itself exercised on GitHub Actions in `--ci` mode and refuses `--ci` outside `GITHUB_ACTIONS=true`.

**Operator sync procedure, not executed by ChatGPT:** on the actual DGX working checkout, require `git status --porcelain=v1 --untracked-files=all` empty and the expected feature branch already selected; `git fetch --prune origin`; confirm `origin/feat/h38-managed-integration` equals the **exact tested target SHA**; then `git merge --ff-only origin/feat/h38-managed-integration`, confirm HEAD and worktree, and invoke the new verifier with that SHA. No `git reset --hard`, stash/pop, force merge or automatic checkout switching. Sync/test modifies the local Git checkout and disposable test files only; no remote host access or DGX test was performed from ChatGPT. **Report DGX_LOCAL_SYNTHETIC=NOT_RUN until the operator supplies actual local output.** Keep `M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`, PR #259 Draft/Open; Ready/Merge BLOCKED.


### Verified safe Git sync and synthetic-only DGX test handoff (2026-10-12)

[CI #38192014751](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38192014751) **SUCCESS** for code commit `c915f805b7fe7abbc8a260379df69148ef5f54e6`: **780/780** full unit tests, Bash syntax, ShellCheck, Python compilation, whitespace, plus an actual execution of `scripts/lifecycle/verify-synthetic.sh` in the GitHub PR checkout with **48/48** bounded synthetic tests (16 uninstall wizard, 6 asset ownership, 8 operation lock, 14 lifecycle integration, 4 snapshot tests). The GitHub Actions checkout may be a PR merge SHA rather than the feature branch HEAD; the verifier checks the exact SHA **of the checkout it is given**. An earlier [CI #38191976973](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38191976973) failure was a missing-SHA message/test mismatch; corrected in `c915f80` with tests passing.

**DGX operator-only sync/test, not run by ChatGPT**: choose the latest verified GitHub branch head SHA as `TARGET`. Start on branch `feat/h38-managed-integration` with a clean worktree. Confirm remote `origin` points to the expected GitHub repository, fetch only the branch without tags, assert `origin/feat/h38-managed-integration` equals the pinned SHA, and fast-forward only with Git hooks disabled. Never reset/stash/force-overwrite local edits. Then run `bash scripts/lifecycle/verify-synthetic.sh "$TARGET"` to verify the exact local checkout. This tool **does not run fetch/merge**, Docker, service manager, install, uninstall, runtime/host Doctor or any model; it runs only the five synthetic test modules under disposable HOME/XDG/TMPDIR and intercepts host commands through PATH stubs. **PATH interception is not an OS-level sandbox**; tests are allowlisted after source review and GitHub CI qualification. If remote advanced beyond the pinned target or any preflight fails, stop without changing the checkout and reassess the SHA.

`DGX_LOCAL_SYNTHETIC=NOT_RUN` until the operator sends the **actual DGX output** (including exact SHA and `LOCAL_SYNTHETIC_RESULT=PASS`). `M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`, PR #259 Draft/Open and Ready/Merge BLOCKED.


## DGX-selected profile read-only snapshot and ordered operator verification (2026-10-12)

Operator-provided DGX log proves the earlier clean fast-forward through
`0e910a7e0ab6246228857cc9432c19b5787eb812` and the local **48/48
synthetic lifecycle tests PASS**, final `DGX_SYNTHETIC_VALIDATION_COMPLETE`.
The local command printed `SHELLCHECK=SKIPPED_NOT_INSTALLED` (ShellCheck
already passed GitHub CI), and did **not** qualify running model/runtime or
the destructive host E2E. This is historical exact-SHA local evidence only.

New `scripts/lifecycle/inspect-selected-profile.py` gives a compact,
read-only actual-host snapshot separately from the synthetic verifier:
strict `install-maintenance` manifest parsing reports selected model
profile/phase/repository/path/expected image/served name and monitor
protection; four strict transition status files and stale artifacts are
reported; read-only Docker inspect and systemctl show report runtime and
service observations. Docker/systemd probe errors remain UNKNOWN. A running
container with matching image/mount/served command is labeled
`MATCHED_NOT_READINESS`, **never actual serving/health qualified**.
Corrupt manifest or pending transition causes fail-closed nonzero exit.
Synthetic unit tests with temporary HOME/XDG and mocked host commands
verify stopped, missing, uninstalled, invalid, transition pending and
running-but-unqualified cases.

The expanded `inspect-readonly-lifecycle.sh` now prints selected-profile
snapshot **first**, before model inventory, other transitions and Doctor.
Operator sequencing: (1) safe exact-SHA Git synchronization, (2) actual
read-only selected-profile snapshot, (3) disposable synthetic tests, then
(4) optional comprehensive read-only Doctor. The disposable verifier
**must not be mistaken for an actual DGX runtime-status probe**.

Do not invoke install/uninstall, Docker mutation, systemd restart, model/GPU,
swap mutation, host monitor relaxation or H38. New actual-host snapshot
execution is **NOT_RUN** until its operator-provided DGX output is supplied.
M1 live host NOT_QUALIFIED, M2 destructive E2E NOT_RUN,
M3 model all-pairs NOT_QUALIFIED, M4 H38 BLOCKED; PR #259 Draft/Open,
Ready/Merge BLOCKED.


## DGX actual selected-profile and isolated test evidence (2026-10-12)

**Source:** operator-provided actual DGX transcript, fast-forward from `0e910a7`
to exact feature HEAD `87fb463984683f75435302eff5ffc3b3b9f941bf` with clean
post-test checkout and `DGX_PROFILE_AND_SYNTHETIC_VALIDATION_COMPLETE`.
`verify-synthetic.sh` reported `LOCAL_SYNTHETIC_RESULT=PASS` with **56/56**
disposable synthetic tests (16 uninstall, 6 ownership, 8 lock,
14 integration, 8 selected-profile snapshot, 4 read-only snapshot).
Local `BASH_SYNTAX=PASS`; `SHELLCHECK=SKIPPED_NOT_INSTALLED` (separately,
[GitHub CI #38194619518](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38194619518)
SUCCESS: 788/788 full unit tests and ShellCheck PASS). **DGX_LOCAL_SYNTHETIC=PASS at
this exact SHA only.**

Actual read-only DGX `inspect-selected-profile.py` reported:

| Observed field | Reported value / qualification |
|---|---|
| `MANIFEST_STATUS` / `INSTALL_PHASE` | `VALID` / `complete` |
| `SELECTED_PROFILE` | `orcarouter` (configuration intent) |
| `PROFILE_REPOSITORY` | `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4` |
| `EXPECTED_IMAGE` and `CONTAINER_IMAGE` | `vllm-skinny-tp1:v1` (legacy installed tag; H38 not active) |
| `MODEL_PATH_STATUS` | `MARKER_PRESENT_NOT_VERIFIED` (not checksum/integrity) |
| `MONITOR_PROTECT` / `MONITOR_ENABLED` | `1` / `1` (configured, not verified running protection) |
| `PROFILE_SWITCH_STATE`, `RUNTIME_TRANSITION_STATE`, `UPDATE_STATE`, `RELEASE_PROFILE_REFRESH_STATE` | all `IDLE` |
| `STALE_TRANSACTION_ARTIFACTS` | `NONE` (only the configured tracked subset) |
| `CONTAINER_STATE` / `SERVICE_STATE` | `EXITED` / `INACTIVE` |
| `RUNTIME_ATTESTATION` | `MISSING`; do not manufacture it |
| `PROFILE_STATUS_SUMMARY` | `CONTAINER_NOT_RUNNING` |
| `ACTUAL_SERVED_PROFILE` | `NOT_VERIFIED` |
| `HOST_HEALTH_QUALIFICATION` | `NOT_ESTABLISHED_BY_THIS_SNAPSHOT` |

**Interpretation and next priority:** Git code/tests are synchronized and the
selected profile is `orcarouter`, but the runtime is stopped. Its stop cause
is **NOT YET DETERMINED** by this newly submitted output: an exited container
plus inactive service does not prove OOM, a protection-triggered stop,
deliberate administrative shutdown or a runtime error. Runtime commit
attestation is absent; never reconstruct an attestation without verified
provenance. H38 code is not an installed/serving H38 model. Retain host
monitor/protection and all stopped services as observed: **NO restart, H38 GPU
rerun, swap cleanup, reinstall, profile-switch or uninstall**.

**Next existing read-only tool (no new script or additional Git pull is
required at verified SHA `87fb463...`):**
```bash
(
  set -Eeuo pipefail
  cd ~/Workspace/llm/qwen3.8-flash-next-dgx-spark
  TARGET=87fb463984683f75435302eff5ffc3b3b9f941bf
  test "$(git rev-parse HEAD)" = "$TARGET"
  test -z "$(git status --porcelain=v1 --untracked-files=all)"
  QWEN38_OFFLINE_DIAGNOSTIC_TARGET_SHA="$TARGET" \
    bash scripts/lifecycle/inspect-readonly-runtime-offline.sh
)
```
This existing exact-SHA helper reads `docker inspect` (container exit
code, OOMKilled, start/finish timestamp, state error, declared ports),
`systemctl show` (ActiveState/Result/ExecMainCode/ExecMainStatus/timestamps),
and `stat` file metadata for `runtime-commit.env`, `runtime-stop.env` and
`monitor.pid`. It prints `RUNTIME_STOP_REASON=NOT_YET_PROVEN`; the output
is **evidence for triage**, not authorization to restart or proof of cause.
Historical Oct-07 journal/monitor scripts are time-window bound, so only use
them after checking whether the observed `FinishedAt` falls in their
documented window. If the offline command returns 3, preserve its partial
results and do not reinterpret failure as stop-cause evidence.

**Gates:** `DGX_LOCAL_SYNTHETIC=PASS` at specified SHA, but
`M1_HOST_HEALTH=NOT_QUALIFIED`, `HOST_STABILITY=INCONCLUSIVE`,
`M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`,
`M4_H38=BLOCKED`, `HOST_PROTECTION=UNCHANGED`; PR #259 Draft/Open,
Ready/Merge BLOCKED.


## Reconciled DGX offline repeat versus previously resolved Oct 7 protection stop (2026-10-12)

The operator's latest **actual DGX** read-only `inspect-readonly-runtime-offline.sh`
run at a clean exact checkout `87fb463984683f75435302eff5ffc3b3b9f941bf`
completed all three queries (`rc=0`) and returned `MANAGED_RUNTIME_OFFLINE=COLLECTED_READ_ONLY`.
Docker `status=exited exit_code=0 oom_killed=false`, started **2026-10-07
16:35:45.800732 KST**, finished **22:08:34.847185 KST**; correct declared
loopback `127.0.0.1:8888` binding with no active port mapping while stopped.
Systemd `Result=success ExecMainCode=1 ExecMainStatus=0 inactive/dead`,
ActiveEnter **22:08:29 KST**, InactiveEnter **22:18:17 KST**.
`runtime-commit.env`, `runtime-stop.env`, and `monitor.pid` were **ABSENT**
at observation. The repeated values match the older exact-DGX
[offline Attempt 01](../scripts/benchmark/evidence/managed-runtime-offline-attempt01-exit0-no-oom-20261012.md)
recorded at a different checkout, not a new runtime or H38 test.

**Resolve chronology using existing historic evidence, not an additional
monitor experiment.** The already archived
[service journal](../scripts/benchmark/evidence/managed-runtime-stop-journal-attempt01-protected-abort-20261012.md)
explicitly records graceful stop of the **previous** container for candidate
handover **22:08:30**, candidate monitor/start at **22:08:35**, and candidate
abort by memory protection **22:18:16**, then **previous container restored
but left STOPPED 22:18:17**. The separately archived
[numeric monitor samples](../scripts/benchmark/evidence/managed-monitor-trigger-attempt01-low-free-swap-growth-pass-20261012.md)
confirm low non-CMA free memory **below 2 GiB** together with swap growth
**at least 256 MiB**, counted for **5 consecutive protection samples**
and `PROTECT stopping` at **22:17:43**. Thus the stopped canonical container's
`exit_code=0 oom_killed=false` correlates with the previous container's
handover/rollback, **not** with the candidate's unobserved Docker exit.
There is no candidate immutable ID or attestation proof in the new snippet;
no kernel OOM/NVIDIA RM failure, false positive, safe memory peak or
candidate READY may be inferred.

This reconciliation supersedes earlier **intermediate** lines stating the
Oct 7 *managed transition's* stop cause or protection threshold branch were
still wholly undetermined. The inspector itself intentionally emits the
literal `RUNTIME_STOP_REASON=NOT_YET_PROVEN` as a collection marker, and
must remain unchanged. The **managed-service protection-abort sequence
and numeric trigger branch are confirmed by earlier evidence**, while
ultimate kernel/driver/model root cause and protective-policy appropriateness
are still **UNVERIFIED**. No new H38 GPU rerun or additional journal hunt.

Canonical new [repeat cross-check evidence](../scripts/benchmark/evidence/managed-runtime-offline-repeat-crosscheck-20261012.md)
preserves source, timestamps and limits. `DGX_LOCAL_SYNTHETIC=PASS` only
for the earlier 56/56 locally run at `87fb463`; the new docs-only GitHub
HEAD has **not** been pulled/tested on the DGX. Maintain
`M1_HOST_HEALTH=NOT_QUALIFIED`,
`M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`,
`M4_H38=BLOCKED`, `HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`,
PR #259 **DRAFT/OPEN, Ready/Merge BLOCKED**. Primary next engineering
priority is **host-independent installer/uninstaller/profile-switch acceptance**,
then independent disposable-host E2E. Do not restart or mutate the sole DGX.


## Fail-closed uninstall plan, Docker dependency, and image absence (2026-10-12)

GitHub source-only hardening captures an ownership `plan-purge` during staged
preflight with an explicit successful producer exit; partially output
nonzero plans cannot authorize teardown. External `docker ps` must succeed,
not merely return zero results; `docker image inspect` must explicitly
report `No such image/object` to authorize an absent image. Unexpected
Docker command failures stop the purge, including at final image-forget.
Fixture regressions exercise failures before registry publication and retain
the preexisting canonical manifest/registry and unowned assets.

Final qualifying CI for the code at
[GitHub Actions #38196834096](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38196834096)
**SUCCESS 792/792 Python, 60/60 bounded synthetic tests**, plus Bash,
ShellCheck, Python compilation, whitespace. Two intermediate CI failures
were test-stub representation problems, preserved in
[specific evidence](../scripts/benchmark/evidence/managed-uninstall-fail-closed-purge-plan-docker-20261012.md).
The independent [disposable-host E2E plan](DISPOSABLE-LIFECYCLE-E2E-PLAN.md)
is an **acceptance plan, NOT an executed test**.

Current sole DGX checkout was last operator-observed at `87fb463...`, with
56/56 synthetic PASS and service/container intentionally stopped after the
Oct 7 protection-abort sequence; new source not locally synchronized/tested.
`M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`,
`M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`,
`HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`.
Never run destructive lifecycle gates on the sole DGX. PR #259 Draft/Open,
Ready/Merge BLOCKED.


## DGX local synthetic acceptance at exact uninstall-hardening SHA (2026-10-12)

An actual operator-provided DGX terminal log confirms a clean guarded
fast-forward `87fb463 → 02e9c61`, exact checkout
`02e9c61d90c7f15484b0605dc872bbbb21ec253b`, final SHA/worktree
checks, and `DGX_SYNTHETIC_VALIDATION_COMPLETE`. The isolated
`verify-synthetic.sh` tests passed **60/60**:
19 uninstall, 7 asset-ownership, 8 operation-lock, 14 lifecycle integration,
8 selected-profile-readonly and 4 full-readonly-snapshot tests.
`LOCAL_SYNTHETIC_RESULT=PASS`, `BASH_SYNTAX=PASS`,
`LOCAL_SYNTHETIC_SCOPE=DISPOSABLE_FIXTURES_ONLY`, and
`LOCAL_SYNTHETIC_HOST_COMMANDS=PATH_DENY_STUBS` were observed.
Local `SHELLCHECK=SKIPPED_NOT_INSTALLED`; separately
[CI #38197243631](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38197243631)
was **SUCCESS, 792/792 full tests**, **60/60 synthetic**, ShellCheck PASS.
This explicitly upgrades the earlier statement that the uninstall-hardening
code had not been synchronized/tested on the DGX.

See [actual DGX synthetic acceptance evidence](../scripts/benchmark/evidence/dgx-synthetic-uninstall-hardening-pass-20261012.md).
The DGX log **does not contain a new live service/Doctor inspection**;
the prior `orcarouter` selected profile and stopped runtime observation
remain historical, not a new readiness claim. Keep
`M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`,
`M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`,
`HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`,
PR #259 Draft/Open and Ready/Merge BLOCKED.

## Full ordered profile-switch pair matrix — synthetic CI (2026-10-12)

Four state-schema profiles (`orcarouter`, `nvidia`, `mazinb`,
`orcarouter-hybrid`) yield **12 distinct ordered profile switches**. The
synthetic transaction suite now checks all 12 for (1) uncommitted
activation recovering exact source manifest, (2) attested target runtime
finalizing target manifest, and (3) mismatched candidate container-ID
attestation refusing commit then allowing provable source rollback.
Same-profile and wrong-source prepares are also refused for all four
starting profiles. Existing interrupted-state and lock fixtures remain.

[CI #38204508012](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38204508012)
**SUCCESS, 796/796 full tests, 70/70 allowlisted synthetic tests** and
Bash, ShellCheck, Python compile and whitespace PASS. The exact-SHA local
synthetic runner now includes the mocked profile-switch test module
(**10 tests**). [Pair matrix evidence](../scripts/benchmark/evidence/managed-profile-switch-pair-matrix-synthetic-20261012.md)
records subtest coverage and evidence boundaries. It is **NOT** a true
Docker/systemd profile-switch E2E, and does not qualify M3.

The operator's last actual DGX synthetic run was **60/60 at `02e9c61`**;
this newer pair-matrix source has not been synchronized/run locally on
the DGX. Preserve the stopped runtime/protection, do not run live
profile switches or model starts. `M1_HOST_HEALTH=NOT_QUALIFIED`,
`M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`,
`M4_H38=BLOCKED`, `HOST_STABILITY=INCONCLUSIVE`,
`HOST_PROTECTION=UNCHANGED`; PR #259 Draft/Open and Merge BLOCKED.

## Actual DGX 70/70 directed profile-pair synthetic acceptance — 2026-10-12

The operator supplied a successful exact-SHA guarded DGX fast-forward
`02e9c61 → d2e9a1d` and `verify-synthetic.sh` output proving **70/70
selected synthetic tests PASS**, **Bash syntax PASS**, and final exact clean
checkout `d2e9a1dc2b9759bc60915f2a7cda7b0cfd9d4914`. Breakdown:
19 uninstall + 7 assets + 8 locks + 14 lifecycle integration +
**10 profile-switch transaction** + 8 selected-profile snapshot +
4 lifecycle snapshot. Profile-switch synthetic cases include all 12
ordered pair directions with successful target attestation, uncommitted
rollback, and incorrect container-ID rejection/rollback.

DGX `SHELLCHECK=SKIPPED_NOT_INSTALLED`. Separately
[CI #38204845533](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38204845533)
**SUCCESS**, 796/796 full unit tests, 70/70 selected synthetic and
ShellCheck/Bash/Python/whitespace PASS. The previous 60/60 actual-DGX
local synthetic acceptance at `02e9c61` is superseded as **latest**
local synthetic evidence. See the
[actual-DGX 70/70 evidence](../scripts/benchmark/evidence/dgx-profile-pair-synthetic-pass-20261012.md).

This proves neither physical Docker/systemd transition nor readiness,
M1 host health, M2 destructive E2E, M3 actual all-pair qualification or
M4 H38. Selected `orcarouter` and stopped runtime are **historical** read-only
observations, not updated by this test. The current single DGX host's
service/monitor/swap/protection remain untouched. `HOST_STABILITY=INCONCLUSIVE`,
`HOST_PROTECTION=UNCHANGED`; PR #259 DRAFT/OPEN and Ready/Merge BLOCKED.

## New actual DGX 70/70 confirmation and GitHub-only profile-switch drift gates — 2026-10-12

The user-supplied **actual DGX** terminal log confirms exact-SHA
fast-forward `d2e9a1d → fb6e0ed`, final clean checkout
`fb6e0ed4075ac5fa8a3142137d068eb98d65e4bf` and
`verify-synthetic.sh` **70/70 PASS** (7 allowlisted modules including
10 profile-switch tests). The on-host `BASH_SYNTAX=PASS`; local
`SHELLCHECK=SKIPPED_NOT_INSTALLED`. GitHub CI #38207710548 at this
same source had **796/796 full and 70/70 selected PASS**, including
CI ShellCheck, not on-host ShellCheck. This supersedes `d2e9a1d` as
**latest actual DGX locally tested SHA**, without changing host readiness
or previously observed runtime state.

Additionally, GitHub-only source commit `8538c83` added **3
disposable profile-switch fault regressions**: tampered backup SHA
refuses rollback while preserving state; tampered candidate SHA refuses
target commit and can roll back to a provable old runtime; removal of
runtime attestation after a recorded commit refuses finalization until
proof is restored. [CI #38210907792](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38210907792)
**SUCCESS, 799/799 full Python tests, 73/73 synthetic, ShellCheck PASS**.
These 3 cases have **not been run on the actual DGX**.

Evidence: [actual DGX console](../scripts/benchmark/evidence/dgx-synthetic-doc-head-pass-20261012.md)
and [manifest/attestation fault injection](../scripts/benchmark/evidence/managed-profile-switch-drift-attestation-synthetic-20261012.md).
Neither result qualifies live M1, real D0–D5 M2, all-pairs service M3 or
H38 M4. `HOST_STABILITY=INCONCLUSIVE`,
`HOST_PROTECTION=UNCHANGED`. No model/service/swap/GPU change. PR #259
must remain Draft/Open/Unmerged and Ready/Merge BLOCKED.

## Actual DGX 73/73 and fail-closed profile-switch orphan-state hardening — 2026-10-12

Operator-supplied real DGX output confirms a clean, exact guarded
fast-forward `fb6e0ed → e18c56a` and **73/73 local isolated synthetic
tests PASS**, including **13 profile-switch transaction tests**.
`BASH_SYNTAX=PASS`, local `SHELLCHECK=SKIPPED_NOT_INSTALLED`,
`LOCAL_SYNTHETIC_RESULT=PASS` and final
`DGX_PROFILE_RECOVERY_SYNTHETIC_VALIDATION_COMPLETE` were observed.
Latest actual DGX verified SHA is
`e18c56aff008f717ad54ee787ab20c248e987e34`.

Subsequent GitHub-source-only review found a **false-idle fail-open**:
a dangling transition file link or orphan backup/candidate/staging
artifact could be hidden by the no-state branch of `recover`,
`rollback`, `service-recover` or `status`. The new code refuses to
claim idle while any such file or link remains, preserving normal truly
idle behavior. Three new fixture unittest methods exercise the
dangling/orphan/valid-idle matrix. [Source CI #38212223945](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38212223945)
**SUCCESS 802/802 full Python, 76/76 synthetic**, plus Bash,
ShellCheck, compile and whitespace PASS. **This new source is not yet
executed locally on the DGX.**

[Evidence details](../scripts/benchmark/evidence/dgx-73-and-profile-switch-false-idle-hardening-20261012.md).
No live host E2E, Docker/systemd profile changes or H38 reruns.
`M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`,
`M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`,
`HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`,
PR #259 Draft/Open, Ready/Merge BLOCKED.


## New actual DGX 76/76 synthetic acceptance and prepare fail-closed check — 2026-10-12

A newly supplied DGX console transcript confirms exact guarded fast-forward `e18c56a → 9220624` and **76/76 local isolated synthetic methods PASS** on `922062436b71353760c2323103e749ed6eaf6240`, including 16 profile-switch methods. `BASH_SYNTAX=PASS`, local `SHELLCHECK=SKIPPED_NOT_INSTALLED`, clean exact HEAD and worktree, `LOCAL_SYNTHETIC_RESULT=PASS` and final `DGX_PROFILE_IDLE_SAFETY_SYNTHETIC_COMPLETE` were observed. The matching GitHub [CI #38212708550](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38212708550) passed 802/802 full and 76/76 synthetic tests plus ShellCheck. This **supersedes 73/73 as the latest actual DGX local synthetic**, not as any live host qualification.

A subsequent safety review found that `prepare` did not apply the existing orphan `.tmp` fail-closed check used by idle/recovery actions. The source now applies the shared guard before publishing a new transaction, with a new seven-scenario (six artifacts and one dangling symlink) fixture regression method. **The new source change was not part of the completed DGX 76/76 run.** [New-source CI #38215072213](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38215072213) **SUCCESS 803/803 full tests, 77/77 bounded synthetic (17 profile-switch), ShellCheck/Bash/compile/whitespace PASS** at `51e85f6578ee0694a13964f700f30e854f17c020`. This new source has not been tested on DGX.

[New DGX and source review evidence](../scripts/benchmark/evidence/dgx-76-and-prepare-orphan-guard-20261012.md). Actual Docker/systemd E2E, M1/M2/M3/M4 gates and host protection are unchanged: `M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`, `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`; PR #259 stays Draft/Open, Ready/Merge BLOCKED.


## Actual DGX 77/77 profile-switch prepare guard acceptance — 2026-10-12

New operator-provided console evidence confirms guarded fast-forward `9220624 → 1283b1a` and **77/77 isolated local synthetic tests PASS** on exact DGX checkout `1283b1a9252f1ff53d51659049ca42f9449e5ccd`, including **17/17 profile-switch tests** and the new `prepare` orphan-staging preservation regression. Exact final HEAD, `LOCAL_SYNTHETIC_RESULT=PASS` and `DGX_PREPARE_ORPHAN_SYNTHETIC_COMPLETE` were observed. Bash syntax PASS; **local ShellCheck SKIPPED_NOT_INSTALLED**, distinct from [GitHub CI #38215504822](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38215504822) **SUCCESS 803/803 full and 77/77 synthetic, ShellCheck PASS**.

[Canonical 77/77 operator evidence](../scripts/benchmark/evidence/dgx-77-prepare-orphan-synthetic-pass-20261012.md). This updates the latest *DGX-local isolated synthetic* source from `9220624` (76/76) to `1283b1a` (77/77), **not** any real Docker/systemd/model acceptance. `M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`, `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`. PR #259 remains Draft/Open/Unmerged and Ready/Merge BLOCKED; no protected DGX runtime mutation.


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
`python3 scripts/lifecycle/disposable-d0-preflight.py --policy <policy.json> --inventory <inventory.json>`.
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


### D0 offline evidence policy CI acceptance (2026-10-12)

Source `7acd15cc5a2d8f5603bdb82b08b1cee49da7d18a` introduced a stdlib-only JSON D0 policy evaluator and nine fixture regressions. [GitHub CI #38217170909](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38217170909) **SUCCESS 812/812 full tests, 77/77 existing bounded synthetic**, Bash syntax, ShellCheck, Python compile, whitespace PASS. The D0 test methods are **not** yet in the bounded DGX verifier; latest DGX actual local run remains `1283b1a` **77/77**. A policy-consistent response is `D0_STATIC_REVIEW=READY_FOR_INDEPENDENT_REVIEW` with `D0_ADMISSION=NOT_GRANTED`; it is not live host attestation or D0 acceptance. [Permanent source/limitation evidence](../scripts/benchmark/evidence/disposable-d0-offline-preflight-ci-20261012.md). M1/M2/M3/M4 remain NOT_QUALIFIED/NOT_RUN/BLOCKED and PR #259 stays Draft/Open/Unmerged.


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


## D0 independent-host read-only crosscheck — GitHub source CI (2026-10-12)

The new on-host read-only D0 cross-check source was implemented at `b6d3188`. Its first [CI #38218386709](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38218386709) **FAILED 1 of 824 full tests**, because a Docker-outage *fixture* used an `AssertionError` instead of subprocess-style `OSError`. The test fake was corrected without relaxing safety guards. [Source CI #38218663210](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38218663210) **SUCCESS 824/824 full Python, 77/77 existing bounded synthetic**, Bash/ShellCheck/Python compile/whitespace PASS at `b99b510e89cc08d99d683dcbf77c75bb55941b2c`.

The 12 new fixture cases cover protected host/daemon identities, clean Git source, path and mount drift, Docker outage/contamination and nonexclusive service refusal. No actual Docker/systemd on a disposable host was inspected; the collector is **not approved for the sole protected DGX**. Its on-host result always keeps `d0_admission=NOT_GRANTED` and `d1_d5=NOT_AUTHORIZED`, even when supplied host observations match. [Permanent evidence and trust limitations](../scripts/benchmark/evidence/d0-onhost-readonly-crosscheck-ci-20261012.md). Latest *actual DGX local* isolated synthetic remains 77/77 at `1283b1a`. D0 independent real-host review and D1–D5 remain NOT_RUN; M1/M2/M3/M4, strict host protections and PR #259 Draft/Open/Unmerged are unchanged.


## D0 parent-mount and Docker-endpoint fail-closed refinement (2026-10-12)

The source-only read-only host observer now rejects **non-root ancestor mounts** overlapping proposed disposable roots, Docker environment overrides, TCP/SSH and default/shared Unix socket endpoints, aliased/missing sockets, and refuses to use an implicit Docker context for daemon reads. Git command probes set `GIT_OPTIONAL_LOCKS=0` to avoid optional Git index refresh. The four trust-boundary fixture methods and one Git no-optional-locks method extend the read-only D0 module to **17/17 synthetic tests**.

[CI #38266470002](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38266470002) at `4dfc2aed238ce96be0b5f3970256b8a2ce8cadf8` **SUCCESS 828/828 full, 77/77 selected**, and [CI #38267015272](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38267015272) at `b65c0142340d90d681c8f82d05294bb72d813687` **SUCCESS 829/829 full, 77/77 selected** plus Bash/ShellCheck/Python compile/whitespace PASS. [Canonical source evidence](../scripts/benchmark/evidence/d0-parent-mount-docker-endpoint-guards-20261012.md) explains remaining host-attestation gaps. The latest *actual DGX-local* isolated result remains **77/77 at `1283b1a`**. This source has not been run on either actual DGX or independent disposable host. D0 `NOT_GRANTED`; D1–D5 `NOT_RUN`; M1/M2/M3/M4 unchanged; PR #259 Draft/Open/Unmerged, Ready/Merge BLOCKED.


## D0 read-only command environment and protected-socket refusal (2026-10-13)

Source `f4e83d2ae3f17d82c5f7702497138c3431072358` hardens the on-host D0 read-only observer against redirected Git/Systemd/DBus environment selectors; removes unpinned default Docker info/container commands from the allowlist; refuses arbitrary populated Docker environment overrides; and blocks context endpoints inside forbidden production roots or on/under non-root mountpoints. `GIT_OPTIONAL_LOCKS=0` remains enforced. Five new fixture methods confirm refusal before unintended host commands. [GitHub CI #38315552300](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38315552300) **SUCCESS 834/834 full Python, 77/77 existing selected synthetic, 22/22 D0 crosscheck fixtures, ShellCheck/Bash/Python compile/whitespace PASS**.

[Permanent D0 environment and socket-source evidence](../scripts/benchmark/evidence/d0-env-redirection-and-socket-boundaries-20261013.md) records provenance, safety rationale and remaining host-attestation gaps. The **latest actual DGX-local** isolated synthetic result remains **77/77 at `1283b1a`**, not the newer GitHub source. No actual independent disposable host observation or live D0 qualification occurred. `D0_LIVE_ADMISSION=NOT_GRANTED`, `D1_D5=NOT_RUN`, M1/M2/M3/M4 unchanged, and PR #259 Draft/Open/Unmerged with Ready/Merge BLOCKED.


## D0 exact-input digest receipts and offline consistency review (2026-10-13)

At source SHA `e41a34f06887f526d0a7ac7cb605d263c226f8f6`, the strict JSON reader hashes the **same bounded no-symlink file-descriptor bytes it parsed**, the read-only host collector emits `policy_sha256` and `inventory_sha256`, and the new `disposable-d0-receipt-review.py` compares its receipt to the exact supplied policy/inventory JSON. Mismatched files, invalid receipt schema, changed Git SHA and forged admission markers are refused. Consistent input is only `D0_RECEIPT_REVIEW=CONSISTENT_UNTRUSTED`; external attestation and replay freshness remain `NOT_VERIFIED`.

[Source CI #38316973840](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38316973840) **SUCCESS: 845/845 full Python, 77/77 bounded synthetic, Bash/ShellCheck/Python compile/whitespace PASS**. [Permanent fixture evidence](../scripts/benchmark/evidence/d0-receipt-input-binding-ci-20261013.md) and [receipt workflow/limitations](D0-RECEIPT-CHAIN.md) preserve provenance and non-admission semantics. The new 11 tests are **outside** the 77-case bounded DGX synthetic verifier; latest **actual DGX-local** synthetic remains **77/77 at `1283b1a`**. No actual disposable host observation occurred; D0 admission NOT_GRANTED, D1–D5 NOT_RUN, M1/M2/M3/M4 remain unqualified/blocked, PR #259 remains Draft/Open/Unmerged.


## D0 external owner/isolation/restore evidence-chain consistency (2026-10-13)

Source `a52ae7f2985ce0f415134b848b6caeb6aefec348` adds `disposable-d0-external-evidence-review.py`, a strictly offline, read-only and fail-closed review of the previous exact-input D0 receipt and **three separately provided artifacts** for independent-owner consent claims, Docker isolation claims and controlled restore-drill claims. It requires the exact policy, inventory, receipt SHA256, host/daemon identifiers and restore point to match; refused evidence includes missing/overlapping role IDs, altered/missing/empty/symlink proofs, overlapping proof digests, contradictory scopes and forged admission. The artifact contents and claimed reviewer actor IDs are **not authenticated or independently witnessed**; success only reports `STRUCTURALLY_CONSISTENT_UNTRUSTED` and always `D0_ADMISSION=NOT_GRANTED`, `D1_D5=NOT_AUTHORIZED`.

[Exact-source GitHub CI #38317915217](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38317915217) **SUCCESS: 860/860 full Python (15 new external proof methods), 77/77 existing bounded synthetic, Bash/ShellCheck/Python compile/whitespace PASS**. See [permanent evidence](../scripts/benchmark/evidence/d0-external-owner-isolation-restore-evidence-ci-20261013.md) and [external review schema and workflow](D0-EXTERNAL-EVIDENCE-REVIEW.md). The latest **actual DGX-local** fixture acceptance remains `1283b1a` 77/77, not this source; no actual independent disposable host D0 verification or D1–D5 has occurred. M1/M2/M3/M4 and PR #259 Draft/Open/Unmerged gates unchanged.


## DGX staged A/B validation recommendation — 2026-10-13

**Run A now when DGX is quiet**: after review and fast-forward-only Git synchronization to exact successful GitHub SHA, invoke the pre-existing local synthetic verifier, now extended to **134/134** offline fixtures (77 original plus 57 D0). It additionally checks the canonical repository origin and refuses Git environment redirection. After A PASS, B is **real HOME/XDG read-only selected-profile and optional Doctor/status observation**, not an M1 acceptance. **C** D0 admission and destructive D1–D5 belong on a separately owned disposable host only; **D** live H38 on the sole protected DGX remains blocked pending RM/metadata/stability/recovery and explicit approval. Source [CI #38319566009](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38319566009) PASS 863/863 full and 134/134 selected; latest actual DGX remains 77/77 at 1283b1a. [Safe DGX operator instructions](DGX-STAGED-VALIDATION.md); [source evidence](../scripts/benchmark/evidence/dgx-stage-a-expanded-synthetic-ci-20261013.md). D0 NOT_GRANTED, D1–D5 NOT_RUN, M1–M4 unchanged, PR #259 Draft/Open/Unmerged.


## Actual DGX 134/134 PASS and solo-owner test authorization boundary (2026-10-13)

User-supplied terminal evidence establishes **actual local 134/134 bounded synthetic PASS at exact b35d0f3d7840d00c55f4c633813e88ac367c6373** (Bash PASS; ShellCheck SKIPPED_NOT_INSTALLED). The immediately following real-HOME selected-profile snapshot showed a VALID complete OrcaRouter manifest, four transactions IDLE, no stale artifacts, monitor/protection both `1`, Docker container EXITED, service INACTIVE and runtime attestation MISSING. This is **A=PASS and B1=COLLECTED**, not M1 health or H38 acceptance. [Actual operator evidence](../scripts/benchmark/evidence/dgx-local-134-pass-readonly-snapshot-20261013.md).

The sole DGX owner reports testing can occur at any time without disrupting other human users. **Bounded, reversible, owner-approved live runtime tests on this one DGX may be considered after B2 full read-only Doctor and recovery review**; a second physical DGX is not mandatory for every runtime test. This revises the former blanket schedule restriction but does **not** approve deleting resources, assume Docker exclusivity, upgrade independent disposable D0 admission, run destructive D1-D5 on the only host, or launch H38 against the unresolved checkpoint/RM gates. Immediate B2: use the existing read-only lifecycle inspector at the **already checked out b35d0f3**; do not sync Git merely to run it. PR #259 remains Draft/Open/Unmerged; Ready/Merge BLOCKED.
