# OrcaRouter H38 atomic cross-release refresh implementation — 2026-10-07

Status: IMPLEMENTED ON BRANCH — STATIC CI REVALIDATION PENDING — LIVE ACCEPTANCE NOT REACHED

## Purpose

The matched PR-base-main control proved that the previous acceptance sequence

`new immutable code -> persisted legacy CPU-offload READY -> H38 image refresh`

is not a valid discriminator. PR-base-equivalent code reproduced the same protected
legacy restart with `rm_oom_count=0`. The safety monitor remains enabled; this change
removes the invalid intermediate lifecycle requirement rather than weakening protection.

## Repository provenance

- repository: `kjlee-inlct/qwen3.8-flash-next-dgx-spark`
- branch: `feat/h38-managed-integration`
- draft PR: `#259`
- PR base: `a7c563705edba780747bf815278f6b77c8a41b08`
- matched base-main control: `d75c24ca496286e0b62db5e8f1d88480ed30e137`
- first coordinator commit: `e783bf2a62f998b500f7f54491be950f348d0cea`
- executable entrypoint mode repair: `afa99afd655cc6ca928ac23774cc89ca7745e703`
- latest implementation/test head before documentation-only follow-up: `dcb47cd8238b9658f311cdc962809a0da03c76d0`

## Implemented transaction surface

Canonical coordinator:

`lifecycle/release-profile-refresh-transition.sh` (relative to `scripts/`)

Stable entry point:

`scripts/release-profile-refresh-transition.sh`

Operator update route:

`scripts/update-release.sh RELEASE_ID --refresh-profile-defaults`

The coordinator is the sole owner of the combined cross-release boundary. It does not
nest `update-transition.sh` and `profile-switch-transition.sh`, because two
independent recovery owners could restore a mismatched release/manifest pair.

The serialized operation performs:

1. validate current complete OrcaRouter managed installation;
2. reject active/stale update, runtime, profile-switch and settings transactions;
3. stage/verify and manifest-bind qualification of the exact target immutable release;
4. load the target OrcaRouter profile from that qualified release;
5. require unchanged checkpoint repo, revision, model directory and served alias;
6. build/reuse the v0.29 -> H9 -> H10 -> H11 -> H12 -> H38 image chain;
7. preserve operator-owned image ownership while claiming only installer-created assets;
8. verify H38 image provenance/label;
9. persist the exact old current/previous release IDs and old install manifest digest;
10. prepare a strict `service_ready` target manifest with the H38 image and target
    immutable `INSTALL_ROOT`;
11. activate the target release pointer and H38 manifest under one persisted transaction;
12. start the managed service only after both target identities are visible;
13. require health/model readiness, runtime-commit attestation, exact target runtime root,
    exact H38 image, running container, `OOMKilled=false`, and H38 scope label;
14. convert the target manifest to `PHASE=complete` only after runtime proof;
15. clear transaction artifacts only after the target proof is rechecked.

There is no managed service start between target release activation and H38 candidate
manifest activation. The invalid legacy CPU-offload intermediate READY state is no longer
part of the path.

## Recovery semantics

The strict `release-profile-refresh` state schema records:

- target release;
- old current and old previous releases;
- target release-manifest SHA-256;
- backup and target install-manifest paths/digests;
- same-profile identity;
- old and target images;
- served model identity;
- transaction phase;
- update timestamp.

Activation records `activating` before pointer/manifest mutation. Failure or
interruption before runtime commit restores the exact previous current/previous release
pair plus the digest-verified previous canonical install manifest.

If a runtime transition is active, its canonical recovery runs before the outer
release/manifest restoration. A protected startup stop therefore remains a failed
candidate and triggers rollback; it is not converted into PASS.

`service-runner.sh` performs release-profile refresh startup recovery before
profile-switch recovery and before canonical manifest parsing. During an intentional
cutover the outer operation lock is still held, so startup recovery defers. After a
process/host interruption, recovery either proves the committed target or restores the
previous pair and forces a systemd retry on the restored release.

Ambiguous state, missing backup evidence, digest mismatch, unsafe release pointers, or
stale transaction artifacts fail closed.

## Operation lock and diagnostics

`lib/operation-lock.sh` (relative to `scripts/`) now blocks unrelated lifecycle mutation while a
release-profile refresh state exists, except for the trusted inherited refresh context.

`doctor.sh` reports incomplete/malformed refresh state or orphan refresh
backup/candidate artifacts and requires the refresh lifecycle to be idle for a clean
result.

The stable refresh entry point is stored as Git mode `100755`; this is explicitly
regression-tested because immutable releases are produced from the Git tree.

## Test/CI history during implementation

An intermediate CI run `37597793527` reached:

- shell syntax: PASS;
- ShellCheck: PASS;
- Python compile: PASS;
- unit tests: FAIL, 2 layout-policy assertions.

The failures were dependency-boundary regressions, not runtime-safety failures:
the new lifecycle coordinator directly referenced `model/`, and the runtime runner
directly referenced `lifecycle/`. They were fixed without changing the dependency
policy: lifecycle now uses the stable top-level model-profile source entry point, and
runtime uses the stable top-level refresh entry point.

A fresh CI run is required on the final documentation-inclusive head before this
implementation may be classified STATIC/CI PASS.

## Acceptance boundary

No DGX H38 managed migration has been executed through this new transaction yet.

Current classification:

- atomic transaction implementation: IMPLEMENTED ON BRANCH
- shell/ShellCheck/Python compile on intermediate implementation: PASS
- final full CI on current head: PENDING
- managed H38 FUNCTIONAL: NOT REACHED
- managed H38 DETERMINISM: NOT REACHED
- managed H38 PERFORMANCE: NOT REACHED
- managed restart/attestation: NOT REACHED
- managed doctor strict: NOT REACHED
- managed HOST-STABILITY: NOT REACHED

Historical dedicated H38 success does not satisfy any of those managed gates.

Any confirmed `_memdescAllocInternal` or `NV_ERR_NO_MEMORY` in a valid future
measured acceptance window remains HOST-STABILITY FAIL regardless of functional,
determinism, performance, or restart success.

PR #259 must remain Draft and must not be merged until the full live acceptance chain is
recorded.
