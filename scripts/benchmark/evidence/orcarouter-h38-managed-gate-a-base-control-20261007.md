# OrcaRouter H38 Gate A matched base-main control — 2026-10-07

Status: BASELINE PROTECTED-STOP REPRODUCED

## Purpose

This control isolates whether Gate A attempt 04's protected legacy-runtime restart was
introduced by the H38 branch or already present in the PR-base runtime/lifecycle policy.

The control commit is:

- branch: `exp/h38-gate-a-base-control`
- commit: `d75c24ca496286e0b62db5e8f1d88480ed30e137`
- parent: exact PR base main `a7c563705edba780747bf815278f6b77c8a41b08`
- only content delta from the parent: the previously proven hermetic
  `tests/test_settings_transition.py` fixture repair

Therefore the runtime/service/monitor payload is PR-base-main-equivalent and contains no
H38 integration runtime change.

## Initial state

The managed installation started from:

- `PHASE=complete`
- profile `orcarouter`
- image `vllm-skinny-tp1:v1`
- current release `ff67bab3c94d6992f61b9535836df97f03b9c022`
- update/runtime/profile-switch transactions idle
- service installed/enabled/active
- exact served alias present
- container running with `oom=false`

## Qualification

The matched control passed host qualification:

```text
Ran 527 tests in 31.343s

OK
Release qualified for cutover: d75c24ca496286e0b62db5e8f1d88480ed30e137
```

The manifest-bound update dry-run also passed.

## Matched cutover result

The base-main-equivalent target release was activated and began the same persisted legacy
OrcaRouter CPU-offload startup.

The current base-main memory monitor then recorded:

```text
16:34:31 protect=0/5 noncmafree=1065MiB swapgrowth=0MiB
16:34:46 protect=1/5 noncmafree=898MiB  swapgrowth=3310MiB
16:34:49 protect=2/5 noncmafree=898MiB  swapgrowth=6801MiB
16:34:51 protect=3/5 noncmafree=898MiB  swapgrowth=10171MiB
16:34:54 protect=4/5 noncmafree=898MiB  swapgrowth=14022MiB
16:34:56 protect=5/5 noncmafree=898MiB  swapgrowth=17602MiB
16:34:56 PROTECT stopping qwen38-flash-next gracefully to preserve host stability
```

The update failed readiness, rolled the release pointer back, and restored the previous
installed release.

The previous `ff67bab...` release then restarted with its older monitor policy and
eventually returned to the committed healthy state.

## Kernel window

The measured control summary was:

```text
control_rc     : 1
current_before : ff67bab3c94d6992f61b9535836df97f03b9c022
current_after  : ff67bab3c94d6992f61b9535836df97f03b9c022
protect_count  : 1
rm_oom_count   : 0
BASE_CONTROL_RESULT=PROTECTED_STOP_REPRODUCED
```

No `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` line was found in the captured
kernel window. This is **not** a HOST-STABILITY PASS classification because the candidate
was intentionally stopped by protection before readiness and did not complete a valid
functional measured run.

## Attribution

The matched control reproduces Gate A attempt 04 without the H38 runtime delta.

Therefore the attempt-04 protected stop is attributed to a pre-existing compatibility
boundary:

> old installed release `ff67bab...` -> current PR-base-main memory-protection policy
> while retaining the legacy OrcaRouter CPU-offload image.

It is not evidence of an H38 runtime regression.

The two-stage acceptance assumption that a new immutable release must first reach READY
on the persisted legacy image is no longer a valid discriminating gate: PR base itself
cannot satisfy that requirement under the current host-protection policy.

## Classification

- matched-control qualification: PASS (527/527)
- matched-control dry-run: PASS
- base-main-equivalent legacy replacement start: REACHED
- base-main-equivalent legacy READY: FAIL / protected stop
- release cutover: rolled back
- kernel RM OOM observed: 0
- HOST-STABILITY PASS: **not claimable**
- H38 runtime reached: NO

## Required redesign

Do not weaken or disable memory protection to make the legacy intermediate state pass.

The production migration must avoid requiring that unsafe/non-viable intermediate state.
The preferred next design is one transactional operation that couples:

1. qualification/staging of the new immutable release,
2. H38 image preparation and provenance validation,
3. shadow/candidate manifest with the H38 image,
4. release + manifest activation,
5. managed H38 READY/model/attestation validation,
6. commit of both lifecycle boundaries only after validation,
7. symmetric rollback of both release and manifest/runtime on failure.

Until that path is implemented and qualified, Gate B is not authorized.
