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
construction, explicit legacy-image -> H38 profile-default migration, H38 runtime
controls, preflight/doctor provenance checks, and asset inventory. Existing installs
remain two-stage: immutable code update first with the legacy manifest still bootable,
then `--refresh-profile-defaults` performs the H38 runtime migration.

This remains an implementation candidate, not a qualification result. H38 must not be
described as promoted into the managed runtime until lifecycle/restart/doctor,
managed-alias determinism, performance, and strict RM host-stability gates in
`scripts/benchmark/evidence/orcarouter-h38-managed-integration-plan-20261007.md`
are recorded as passing.

## Memory monitor caveat

The current runtime monitor is CMA-aware and implements the repository's present
protection heuristic. In particular, low non-CMA free memory can become
protection-significant when non-CMA available is low or swap consumption since monitor
start increases by the configured gate (currently 256 MiB in the helper defaults).

This heuristic is **not a proven discriminator for RM failure**. Live Hybrid cold-load
evidence has shown that the 256 MiB swap-growth arm can produce a false-positive
protected stop during otherwise normal startup. Treat the monitor as a safety heuristic,
not as the canonical host-stability classifier. Strict RM kernel evidence remains the
classification source of truth.

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
