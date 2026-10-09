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

A new **read-only, CPU-only, pinned installed H38 image source
inspector is staged, NOT yet DGX-executed**:
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
