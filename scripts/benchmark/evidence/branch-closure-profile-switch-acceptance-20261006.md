# Branch closure — `docs/live-profile-switch-acceptance-20260930` — 2026-10-06

Status: **FROZEN FOR NEW PRODUCT/INSTALLER FEATURE WORK — EVIDENCE/ACCEPTANCE SCOPE CLOSED**

## Purpose of this branch

This branch accumulated the live DGX Spark profile-switch acceptance work and the host-stability / NVIDIA RM allocator investigation through the R23–R32 localization closure.

Canonical allocator/localization closure:

- `orcarouter-r23-r32-allocation-localization-closure-20261006.md`

The branch also contains the first static implementation of the follow-on mitigation candidate M1:

- `orcarouter-m1-deferred-meta-w13-plan-20261006.md`

M1 is **static-only / not live-qualified**. Its presence on this branch is a carry-forward seed, not a completed mitigation result.

## Closed work on this branch

The following work is considered complete for branch-scope purposes:

- managed profile-switch transaction/recovery acceptance;
- exact OrcaRouter managed restoration checks;
- R9–R23 lower allocator / direct NVIDIA RM ownership closure;
- R24 H6 rejection as a burst mitigation;
- R25–R32 userspace/model-construction localization;
- exact `400 MiB x48` packed-w13 event localization;
- closure of model-prefix ownership investigation for the `800 MiB x48` family;
- evidence indexing and strict FUNCTIONAL vs HOST-STABILITY classification rules.

## Work explicitly not completed here

The following must not be presented as completed on this branch:

- M1 live validation;
- production qualification of any new allocator mitigation;
- installer/wizard product UX redesign;
- universal CLI/Wizard option symmetry;
- model-manager / one-click install-and-switch UX;
- new installable model profiles beyond the current registry;
- PR #244 merge.

## Freeze rule

After this closure, do **not** add unrelated installer/product feature work to this branch.

Only the following changes are acceptable here if absolutely necessary:

1. corrections to already-recorded evidence;
2. fixes needed to preserve the validity of an already-recorded branch result;
3. final branch/PR metadata documentation.

New installer/profile-manager work must move to a dedicated follow-up branch.

## Follow-up product branch scope

The next product branch should focus on the actual operator goal:

> One DGX Spark can install, retain, inspect, switch, and safely operate multiple qualified Qwen3.8-Flash-Next profiles with minimal clicks.

The product-level invariant should be:

- every persistent/runtime selection exposed by the Wizard has an equivalent CLI option;
- every normal operator CLI option has a corresponding Wizard selection where interactive use makes sense;
- profile installation and profile switching use the same registry and validation rules;
- existing downloaded models are reused rather than purged during switches;
- switch/recovery remains transactional;
- `--model PROFILE` remains a non-interactive direct-selection path;
- the Wizard must expose profile switching for an existing installation instead of silently treating it only as resume;
- maintenance-only/debug actions such as `--dry-run` may remain CLI-only if explicitly classified as non-operator settings rather than pretending full symmetry.

## Current installable profile registry at freeze

The current registry declares four installable profiles:

- `orcarouter` — stable/default;
- `nvidia` — experimental;
- `mazinb` — experimental;
- `orcarouter-hybrid` — experimental/generated H6.

`lychee888` remains planned/non-installable.

This is a registry statement, not a claim that all four profiles have equal production qualification.

## M1 carry-forward rule

M1 repository implementation may be copied/cherry-picked into a later mitigation branch if needed, but no live M1 run is authorized merely because the static implementation exists here.

The current M1 target remains narrow:

- defer only packed `w13_weight` materialization;
- keep w2/scales/checkpoint values/shapes/ModelOpt post-load/kernel unchanged;
- reject generic CPU-offload/direct-UVA as substitutes;
- require static image + checkpoint-order + managed-nonmutation gates before any live candidate.

## PR policy

PR #244 remains intentionally **OPEN / UNMERGED** until explicit merge timing is chosen by the operator.

Do not merge it automatically as part of branch cleanup.
