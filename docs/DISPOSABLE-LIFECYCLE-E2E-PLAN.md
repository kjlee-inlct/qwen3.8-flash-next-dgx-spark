# Independent disposable-host managed lifecycle E2E acceptance plan

> **PLANNED — NOT EXECUTED.** No work in this document authorizes a destructive action
> on the user's sole active DGX Spark. Synthetic GitHub CI and isolated HOME/XDG
> tests cannot satisfy M2 live destructive E2E or M3 all-pairs qualification.

## 1. Scope and ownership

The target is **an independently provisioned, disposable host** with separately
owned Docker images, model fixture data, swap, service units, and empty user
state. It must not share the actual single Spark's volumes, bind mounts,
Docker socket, filesystems, credentials or runtime containers.

A VM/CI with stubbed Docker/systemd can provide **synthetic integration evidence**
but must remain classified as synthetic, even if it performs local filesystem
deletion. True M2 host-destructive E2E requires an isolated host with actual
representative Docker/systemd/swap semantics and an explicitly designated
throwaway dataset; do not mislabel a mock as hardware qualification.

## 2. Independent host gate D0 — mandatory before any mutation

- Independent owner explicitly confirms the machine/container daemon and its
  volumes are disposable; records a unique host ID, OS/architecture, Docker
  context/daemon, filesystem/mount inventory and test account. Abort if any
  production identity or mount is present.
- Start from an exact immutable Git revision that has passing GitHub CI,
  an unchanged worktree and a verified expected GitHub repository origin.
  Record the release and entry-script hashes, date, and expected image ID.
- Use **synthetic tiny model fixtures**, never production checkpoint data.
  Model and hybrid manifest ownership markers must be correctly created by
  the installer or test fixture harness, not fabricated as proof after failure.
- Establish explicit guard conditions: no shared service units, images or
  root directories; bounded log storage, reversion/snapshot mechanism,
  no credentials/secrets in collected output, and operator-owned escape path.
- Dry-run inspection is permitted; do not continue to destructive commands
  until the independent-host safety gate is demonstrably satisfied.

## 3. Ordered acceptance scenarios (D1–D5)

| Gate | Scenario | Required observable result |
|---|---|---|
| D1 | Clean, isolated install of default profile | Correct manifest/schema, asset ownership, release pointer, service/container identity, no unrelated resource mutation |
| D2 | Default uninstall **without asset purge**, then reinstall a different profile | Retained models/images/releases preserved, manifest correctly uninstalled and fresh selection available, no stale lock/transaction leakage |
| D3 | Owned-only full purge after multiple profile lifecycles | All and only installer-owned historical assets deleted in dependency order; unowned/foreign artifacts and Docker consumers intact; complete release/state cleanup |
| D4 | Faults before publication: partial `plan-purge` stdout+error, Docker `ps` partial output+error, image inspect daemon error, manifest/registry drift, unowned swap | No service/container teardown, no irreversible deletion, canonical ownership registry unchanged; inspected stage cleaned or explicitly blocked if SIGKILL |
| D5 | Faults after controlled teardown boundary: permission loss, interrupted file/marker removal, image in-use, swap failure, abrupt SIGKILL | Exact phase and surviving assets documented; no unsafe auto-recovery, no false success, independently verified and safe retry or explicit operator block |

Additional optional M3 (never implied by D1–D5): **every explicitly supported
ordered profile pair** including identity, no-op, switch, failure recovery,
release binding and rollback on a separate qualified disposable environment.
Do not claim M3 from isolated unit fixtures or one profile's D1–D5 results.

## 4. Evidence and pass/fail semantics

Capture for every scenario: immutable commit SHA, test host provenance,
invoked arguments, initial state/ownership registry SHA256 (where applicable),
filesystem/image/container/service inventory **before and after**, command exit
codes, test script SHA256, exact fault injection, and recovery observations.
Classify `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN` separately. Preserve failed
artifacts for postmortem instead of automatically deleting evidence.

Preflight refusal is **PASS only for an intentionally injected unsafe case**;
it does **not** mean the full uninstall succeeded. A simulated SIGKILL is
synthetic evidence unless verified under real disposable-host process-group
and filesystem semantics. Real crash durability and concurrent Docker races
remain unqualified until tested independently.

## 5. Existing current CI coverage and gaps

The source fixes in `uninstall.sh` and `scripts/lib/asset_ownership.py`
require successful, complete ownership plan capture before publication,
require a successful Docker dependency listing, and treat image absence
as real only when Docker explicitly responds with `No such image/object`.
Unexpected daemon and permission errors fail closed, including during an
image's final delete-or-forget decision. These checks are regression-covered
by disposable fixture tests; the outcome **does not** qualify D0–D5.

Maintain `M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`,
`M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`,
`CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `HOST_STABILITY=INCONCLUSIVE`,
`HOST_PROTECTION=UNCHANGED`. PR #259 remains Draft/Open and never Ready/Merged
while gates remain unmet.
