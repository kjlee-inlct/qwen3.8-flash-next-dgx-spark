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


## Synthetic M3 coverage versus remaining disposable-host admission

The four-profile **12 directed pair** synthetic transaction matrix has now
passed [CI #38204508012](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38204508012)
(796/796 full, 70/70 allowlisted tests). It checks uncommitted rollback,
attested target finalize, incorrect attestation refusal, and same/wrong
source guards using fake Docker identity. These do **not** satisfy
D0-D5 or live M3: every actual service transition, model readiness,
release handover and stop/rollback on an independent disposable host
remains **NOT_RUN**.


## Synthetic boundary update — 2026-10-12

Three further temporary-manifest transaction regression tests (backup
SHA mismatch, target candidate drift and attestation loss after
runtime-commit state) passed GitHub CI #38210907792, **799/799 full and
73/73 synthetic**. The latest actual DGX local synthetic acceptance is
separate: **70/70 at `fb6e0ed`**. These checks neither exercise real
Docker/systemd transitions nor satisfy D0–D5 or M3 live qualifications.


## Additional interrupted idle-state case — 2026-10-12

The synthetic profile-switch helper now refuses a false idle state when
transaction state is a dangling symlink or when backup/candidate and
staging `.tmp` artifacts survive without a published transaction.
GitHub CI #38212223945 passed 802/802 full, 76/76 synthetic.
Extend any future independent disposable-host profile-switch
interruption trial to check these stranded-file startup/status/rollback
paths; they remain unqualified on real Docker/systemd.


## DGX bounded synthetic source parity and prepare-stage admission — 2026-10-12

The sole DGX's latest **isolated synthetic** operator evidence now shows **76/76 PASS at `9220624`**; GitHub CI #38212708550 separately passed 802/802 full, 76/76 synthetic. Neither qualifies D0–D5 or M3 live runtime transitions.

A new source-level safety hardening makes profile-switch `prepare` reject orphan state/manifest staging `.tmp` files and dangling links, using the same fail-closed guard as recovery. The associated disposable fixture test must remain classified as synthetic. On a future independently qualified D0 host, explicitly inject orphan staging **before prepare** and verify it aborts without overwriting evidence; do not run that destructive trial on the protected Spark.


**GitHub follow-up CI confirmation (2026-10-12):** [#38215072213](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38215072213) at exact new source HEAD `51e85f6578ee0694a13964f700f30e854f17c020` passed **803/803 full Python and 77/77 selected synthetic**, with 17 profile-switch tests, Bash syntax, ShellCheck, compilation and whitespace PASS. The sole DGX latest actual *isolated synthetic* evidence remains **76/76 at `9220624`**. No new live M1/M2/M3/M4 acceptance; PR #259 remains Draft/Open/Unmerged.


## Latest DGX local isolated-synthetic source confirmation (2026-10-12)

The operator-provided DGX transcript now verifies exact checkout `1283b1a9252f1ff53d51659049ca42f9449e5ccd`: **77/77 selected synthetic tests PASS**, including 17 profile-switch fixture tests and the `prepare` orphan-artifact refusal; Bash syntax PASS, local ShellCheck SKIPPED_NOT_INSTALLED. GitHub [CI #38215504822](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38215504822) separately passed 803/803 full, 77/77 selected, ShellCheck and static checks. D0–D5 and actual 12-pair Docker/systemd live switching remain NOT_RUN or NOT_QUALIFIED. Do not execute destructive validation on the sole protected DGX. PR #259 remains Draft/Open/Unmerged.


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
