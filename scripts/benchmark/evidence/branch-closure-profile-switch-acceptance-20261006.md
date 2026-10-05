# Branch closure — `docs/live-profile-switch-acceptance-20260930` — 2026-10-06

Status: **CLOSED — READY FOR FINAL CI / SQUASH MERGE — NO NEW PRODUCT FEATURE WORK**

## Purpose

This branch records the live DGX Spark profile-switch acceptance work and the host-stability / NVIDIA RM allocator investigation through the R23–R32 localization closure.

Canonical allocator/localization closure:

- `orcarouter-r23-r32-allocation-localization-closure-20261006.md`

## Closed work on this branch

The following work is complete for this branch:

- managed profile-switch transaction/recovery acceptance;
- exact OrcaRouter managed restoration checks;
- R9–R23 lower allocator / direct NVIDIA RM ownership closure;
- R24 H6 rejection as a burst mitigation;
- R25–R32 userspace/model-construction localization;
- exact `400 MiB x48` packed-w13 event localization;
- closure of model-prefix ownership investigation for the `800 MiB x48` family;
- evidence indexing and strict FUNCTIONAL vs HOST-STABILITY classification rules.

## R23–R32 engineering closure

The repeated large RM families are now separated:

- `400 MiB x48` is directly and exactly localized to packed `w13_weight` construction;
- `800 MiB x48` is not supported as a distinct explicit model-component weight owner;
- the best-supported 800 MiB mechanism is discrete CUDA/NVIDIA RM backing/reservation growth induced by the repeated decoder-layer construction cycle;
- this remains a mechanism-level inference, not proof of the exact lower allocator call or exact resident ownership.

Do not add further model-prefix / Linear / attention / hyper-connection markers for the 800 MiB ownership question.

## Strict host-stability policy

Any confirmed `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` in a valid measured run remains **HOST-STABILITY FAIL**, even when fallback succeeds and the runtime reaches READY.

FUNCTIONAL and HOST-STABILITY classifications remain separate.

RM requested bytes remain allocation activity volume, not exact resident ownership.

## Follow-up mitigation work

The first deferred/meta-w13 mitigation prototype (M1) is intentionally **not part of this merge closure**.

It is preserved on the dedicated follow-up branch:

- `exp/m1-deferred-meta-w13`

M1 remains static-only / not live-qualified. No production mitigation claim follows from its existence.

Future mitigation qualification must happen independently of this PR.

## Follow-up installer/product work

Installer/Wizard/profile-manager improvements are explicitly outside this branch.

The next product branch should target the operator goal:

> One DGX Spark can install, retain, inspect, switch, and safely operate multiple qualified Qwen3.8-Flash-Next profiles with minimal clicks.

Product invariants should include:

- profile installation and profile switching use one registry;
- normal operator Wizard selections and CLI options are symmetric;
- existing downloaded assets are reused during switches;
- switches remain transactional and recoverable;
- `--model PROFILE` remains a direct non-interactive path;
- an existing installation can choose another profile in the Wizard instead of being forced into resume-only UX.

## Installable profile registry at closure

The registry declares four installable profiles:

- `orcarouter` — stable/default;
- `nvidia` — experimental;
- `mazinb` — experimental;
- `orcarouter-hybrid` — experimental/generated H6.

`lychee888` remains planned/non-installable.

This is a registry statement, not a claim of equal production qualification.

## Merge boundary

No additional allocator experiment, M1 experiment, or installer/product feature is required before merging this branch.

Required final gate:

1. final branch CI is green;
2. PR #244 remains mergeable;
3. squash merge into `main`;
4. start installer/profile-manager and M1 qualification from separate follow-up branches.
