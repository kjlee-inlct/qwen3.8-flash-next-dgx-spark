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
