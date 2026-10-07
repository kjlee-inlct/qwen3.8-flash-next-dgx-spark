# OrcaRouter H38 atomic cross-release refresh implementation — 2026-10-07

Status: STATIC/CI PASS — LIVE ACCEPTANCE NOT REACHED

## Purpose

The matched PR-base-main control proved that the previous acceptance sequence

`new immutable code -> persisted legacy CPU-offload READY -> H38 image refresh`

is not a valid discriminator. PR-base-equivalent code reproduced the same protected
legacy restart with `rm_oom_count=0`. The memory monitor and strict NVIDIA RM rules
remain unchanged. This implementation removes the invalid intermediate lifecycle state
rather than weakening host-safety protection.

## Repository provenance

- repository: `kjlee-inlct/qwen3.8-flash-next-dgx-spark`
- branch: `feat/h38-managed-integration`
- draft PR: `#259`
- PR base: `a7c563705edba780747bf815278f6b77c8a41b08`
- matched base-main control: `d75c24ca496286e0b62db5e8f1d88480ed30e137`
- first coordinator commit: `e783bf2a62f998b500f7f54491be950f348d0cea`
- runtime commit deferral: `950d0a6944d3d9b72fff8596816a25e07c033d0e`
- symmetric runtime rollback preservation: `602fe8157a8d0cc7b9fc7a97e24ade0fee5ebd94`
- negative Docker-guard return fix: `c42ec5e426e4a0ab6face3171f5d9dd42cad0090`
- guarded live migration gate introduction: `948a3c4186254a1c285b7c5c79e379b4201ea991`
- live gate executable-mode repair: `b3f91460612d46e79ca241f18156354978013049`
- guarded gate contract test: `dd8f47b0690c24cda95dc0400096cf144102e79a`
- atomic live-plan replacement: `76f2e83457933b38a002c4399b0dd0a70ea6d541`
- identity-aware service stop helper: `f9f873637db9c09de137dee6835c6f9132d6661a`
- restored-runtime adoption path: `8f4844bcfcceb68eee2cb9c33b41733cbaf70fd9`
- cold-restart refusal / restored-root delegation: `91bf2d8f5eed323633e4fa94027a5130f4069906`
- rollback service-ownership restoration: `283c73009f03f3c203b65658950710c086ba8439`
- identity-safe rollback regression coverage: `40cf5f8a2d13d3b30b6ae0f71cffb4fdfdd3512b`

Later commits may advance the branch; the exact live acceptance target must always be the
then-current PR head, not one of the intermediate SHAs above.

## Implemented transaction surface

Canonical coordinator:

`lifecycle/release-profile-refresh-transition.sh` (under `scripts/`)

Stable operator entry point:

`scripts/release-profile-refresh-transition.sh`

Operator update route:

`scripts/update-release.sh RELEASE_ID --refresh-profile-defaults`

The coordinator is the sole owner of the combined cross-release release-pointer +
canonical-manifest boundary. It intentionally does not nest `update-transition.sh`
and `profile-switch-transition.sh`, because independent recovery owners could restore
a mismatched release/manifest pair.

The serialized operation now performs:

1. validate the complete existing OrcaRouter managed installation;
2. reject active/stale update, runtime, profile-switch and settings transactions;
3. prove the exact previous immutable current release and runtime attestation;
4. require the previous container to match the manifest image, be running, healthy,
   exact-model READY, and `OOMKilled=false`;
5. stage/verify and manifest-bind qualification of the exact target immutable release;
6. load target OrcaRouter defaults from that qualified immutable release;
7. require unchanged checkpoint repository, revision, model directory and served alias;
8. build/reuse the v0.29 -> H9 -> H10 -> H11 -> H12 -> H38 image chain;
9. preserve operator-owned image ownership and claim only installer-created stages;
10. re-prove the exact previous runtime immediately before crossing the activation
    boundary because image preparation may be long-running;
11. persist the old current/previous release IDs, release-manifest digest, backup
    install-manifest digest, target manifest digest, old/target image and served identity;
12. activate the qualified target release pointer and H38 `service_ready` manifest
    before the single managed-service replacement;
13. start the target H38 runtime directly; no new-code + legacy-image runtime is started;
14. require target health/model readiness and write target runtime attestation;
15. **defer `runtime-transition commit`** so the previous
    `qwen38-flash-next.rollback` container remains available while the outer
    release-profile transaction is still reversible;
16. prove exact target release/manifest/container/image/label/attestation and
    `OOMKilled=false`;
17. commit the deferred runtime transition, then convert the target manifest to
    `PHASE=complete`, re-prove the target, and only then clear outer transaction state.

The old invalid legacy CPU-offload intermediate READY state is not part of this path.

## Recovery and interruption semantics

The strict `release-profile-refresh` state records:

- transaction schema and phase;
- exact target release;
- old current and old previous release;
- exact predecessor Docker container ID;
- target release-manifest SHA-256;
- backup and target install-manifest paths/digests;
- same-profile identity;
- old and target image;
- served model identity;
- update timestamp.

Important durability rule:

> Target API READY is not enough to destroy the previous runtime.

During `runtime_validating`, the target may be healthy and attested while the
runtime transaction deliberately remains in `validating`. The rollback container is
kept until the outer coordinator decides to commit.

Recovery behavior:

- before activation: remove transaction artifacts without touching the live old tuple;
- activation/runtime-validation before target proof: recover the runtime transition
  first, require the restored Docker container ID to equal the predecessor ID persisted
  before mutation, then restore the exact old current/previous release pointers and
  digest-verified old manifest;
- target is fully attested while outer state is still `activated` or
  `runtime_validating`: finish the target commit instead of destroying a proven
  successful candidate;
- crash after runtime-transition commit but before outer lifecycle commit: if the
  target is still fully provable, finish the outer commit idempotently;
- `runtime_committed`/`committing` with incomplete target proof: fail closed.
  Previous runtime evidence may already have been intentionally destroyed, so recovery
  must not pretend that rollback is still symmetric;
- protected startup stop remains a failed candidate/safety intervention and is not
  converted into PASS;
- rollback never relies on an unconditional legacy service restart. The managed unit's
  stop helper stops only the exact container ID covered by the current runtime
  attestation, so a just-restored predecessor container is not accidentally stopped by
  the failed candidate service's `ExecStop`;
- when the predecessor container is still running, a strict one-shot
  `runtime-adopt.env` marker lets systemd attach to that exact container ID, image,
  model mount and served identity without replacing it. The previous release's normal
  unit definition is then restored with `--no-start`;
- when safety protection has left the predecessor container stopped, recovery preserves
  that stopped state instead of cold-starting the legacy runtime merely to make systemd
  active again;
- malformed/missing digest evidence, unsafe pointers, stale adoption state, image
  mismatch, release-manifest drift, or ambiguous container state fail closed.

`service-runner.sh` invokes release-profile refresh startup recovery before
profile-switch recovery and before parsing the canonical install manifest. During an
intentional cutover the outer lifecycle lock is active and startup recovery defers.
After interruption with no outer lock, recovery either finishes a fully proven target
or restores the previous tuple. A running restored predecessor is reattached by exact
container identity; a stopped predecessor remains stopped. The service runner also
refuses to cold-replace an already-restored legacy container when no valid adoption
marker is present.

## Operation lock, diagnostics, and entry points

`lib/operation-lock.sh` (under `scripts/`) blocks unrelated lifecycle mutation while a
release-profile refresh state exists, except for the trusted inherited refresh context.

`scripts/doctor.sh` fails on incomplete/malformed refresh state, orphan refresh
backup/candidate artifacts, or a pending/malformed one-shot runtime-adoption marker.
The global operation lock likewise blocks unrelated lifecycle mutation while adoption
is pending.

Stable entry points now include:

- `scripts/release-profile-refresh-transition.sh`
- `scripts/prepare-h38-image.sh`

The guarded live migration gate is:

`scripts/benchmark/run-h38-managed-migration-gate.sh`

The operator shim and live gate are Git mode `100755`; regression tests protect these
modes because immutable releases are produced with `git archive`.

## Guarded live migration gate

The live gate is intentionally narrower than the entire final acceptance suite. It
performs the dangerous migration boundary and records the evidence needed to decide
whether later determinism/performance/restart gates may proceed.

It requires:

- exact 40-character target SHA equal to checkout HEAD;
- clean worktree including untracked files;
- legacy supported OrcaRouter image, complete manifest, owned/enabled service;
- all lifecycle transactions idle, including stale settings artifacts;
- exact predecessor immutable release and runtime commit attestation;
- healthy running predecessor, `OOMKilled=false`, exact served model;
- fresh 384-token x5 legacy decode baseline.

It then executes only:

`scripts/update-release.sh TARGET_SHA --refresh-profile-defaults`

and verifies exact target release/install root, H38 image/label/env, 16 GiB KV flag,
model ID, runtime attestation, lifecycle idle state, `doctor.sh --strict`, and
`OOMKilled=false`.

A measured kernel window begins immediately before mutation. Any
`_memdescAllocInternal` or `NV_ERR_NO_MEMORY` is HOST-STABILITY FAIL. A monitor
protected stop is a safety intervention and leaves functional acceptance incomplete;
it is not RM OOM and not HOST-STABILITY PASS.

The gate writes a full `run.log`, structured evidence files, and
`upload-summary.txt` for return to the repository engineer.

## CI history during implementation

Historical failures are retained because they found real design or test-harness defects.

- run `37597793527`: shell/ShellCheck/Python passed; unit tests found two category
  dependency violations. The code was redirected through existing stable top-level
  entry points instead of weakening the layout policy.
- run `37602011565`: unit recovery tests exposed missing fake runtime-helper coverage
  plus a stale assertion after stronger fail-closed recovery. Fixtures/assertions were
  corrected; production safety was not relaxed.
- run `37602275529`: unit tests exposed a real Bash `set -e` bug where negative
  Docker existence guards returned nonzero on the normal path. Explicit successful
  returns were added in commit `c42ec5e...`.
- run `37603052374`: shell/ShellCheck/Python passed; one unit layout-policy failure
  found the new benchmark gate directly referencing canonical `lib/`, `lifecycle/`
  and `runtime/` categories. The gate now uses stable top-level entry points; no
  dependency waiver was added.
- atomic implementation/docs CI run `37604211474` on `d44e3ddd53896c7d87b533f5db315a168e65dd59`: **SUCCESS**, including **567/567 unit tests PASS** and whitespace PASS.
- identity-safe rollback/service-adoption hardening CI run `37616889537` on
  `40cf5f8a2d13d3b30b6ae0f71cffb4fdfdd3512b`: **SUCCESS**. Shell syntax,
  ShellCheck, Python compilation, the full unit-test suite, and whitespace checks all
  passed.

## Acceptance boundary

No DGX H38 managed migration has been executed through this new transaction yet.

Current classification:

- atomic transaction implementation: IMPLEMENTED ON BRANCH
- atomic implementation static/CI: PASS, including identity-safe rollback hardening
  (`40cf5f8a2d13d3b30b6ae0f71cffb4fdfdd3512b`, run `37616889537`)
- managed H38 migration FUNCTIONAL: NOT REACHED
- managed H38 migration HOST-STABILITY: NOT REACHED
- managed H38 DETERMINISM: NOT REACHED
- managed H38 PERFORMANCE: NOT REACHED
- managed restart/attestation: NOT REACHED

Historical dedicated H38 success does not satisfy any managed gate.

Any confirmed `_memdescAllocInternal` or `NV_ERR_NO_MEMORY` in any valid future
managed acceptance window remains HOST-STABILITY FAIL regardless of functional,
determinism, performance, or restart success.

PR #259 remains Draft and must not be merged until the full live acceptance chain is
recorded.
