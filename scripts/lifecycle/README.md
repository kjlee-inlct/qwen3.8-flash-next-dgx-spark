# Lifecycle helpers

This directory contains canonical immutable-release qualification, bootstrap, update-transaction, managed profile-switch, and atomic cross-release profile-refresh transaction logic.

## Responsibilities

- Bootstrap and qualify immutable releases.
- Manage update-transition state and cutover transaction boundaries.
- Manage persisted managed-profile replacement/recovery boundaries; this remains the
  canonical profile-switch transaction logic.
- Atomically bind a qualified immutable release to a same-profile runtime-image manifest refresh without booting an intermediate legacy runtime.
- Bind rollback to the exact predecessor container identity and coordinate one-shot service reattachment without forcing a legacy cold restart.
- Enforce fail-closed qualification and lifecycle serialization rules.

## Dependencies

- May use shared parsers, release-manifest validation, and operation locking from `../lib/`.
- May call stable operator entry points needed to apply a qualified release or managed profile.
- May coordinate runtime replacement, but runtime container validation/rollback mechanics remain owned by `../runtime/`.

## Non-responsibilities

- Do not implement model inspection/config preparation.
- Do not implement runtime health/monitoring internals.
- Do not own diagnostics or benchmark workloads.

## Canonical files

- `bootstrap-release.sh`
- `qualify-release.sh`
- `update-transition.sh`
- `profile-switch-transition.sh`
- `release-profile-refresh-transition.sh`

Top-level compatibility paths such as `scripts/qualify-release.sh`,
`scripts/update-transition.sh`, `scripts/profile-switch-transition.sh`, and
`scripts/release-profile-refresh-transition.sh` should remain
thin delegators. Operator-facing transaction recovery/status commands use those stable
paths; new internal code should target the canonical implementation here.

## SHA256-bound full-project uninstall engine (2026-10-20 SOURCE_ONLY)

`full-project-uninstall.py` is the separate three-stage whole-project
`plan`/`apply`/`verify` engine exposed from the main Wizard uninstall
submenu. It delegates read-only discovery to `uninstall-inventory.py`,
binds exact full-ID Docker + image and mounted-volume proofs and safe
filesystem root/inode scope to a canonical SHA256 receipt, and refuses
external image/volume/bind-mount users and active transitions.
Actual delete requires exact receipt and explicit irreversible phrase,
holds the Qwen3.8 operation lock and passes its ownership to the
existing managed service helper. It deletes local research evidence
(no default archive retention) only after Docker/swap removal and
reports leftover candidates via an independent postcheck.
Standalone source/CI fixture tests: `tests/test_full_project_uninstall.py`.
All real DGX destructive M2 tests remain **NOT_RUN/NOT_QUALIFIED**.
See `docs/PROJECT-UNINSTALL-COVERAGE.md` for detailed scope/risks.

## Project uninstall completeness inventory (read-only)

`uninstall-inventory.py` provides an independently testable, non-mutating
full-project candidate inventory and baseline-bound post-removal residual
check. The Wizard's Uninstall → read-only inventory action delegates here.
The module reports exact-ID Docker candidates, registry ownership distinctions,
state/releases, systemd units and status, swap/fstab, model dirs and excluded
shared caches. It never removes an object, issues a GPU command or grants
deletion approval. Real destructive full cleanup remains **NOT IMPLEMENTED**
and M2 host acceptance **NOT QUALIFIED**. See
[project uninstall coverage](../../docs/PROJECT-UNINSTALL-COVERAGE.md) and
`tests/test_uninstall_inventory.py`.

### Read-only checkpoint marker provenance (SOURCE_ONLY)

`python3 -B scripts/lifecycle/uninstall-inventory.py provenance`
uses the bounded live inventory and recorded model marker fingerprints to
report model repository/revision/status, file-entry counts and safe
`lstat`/file-size consistency. `--json` is also supported. It
**does not hash model weights**, label an `owned=False` checkpoint
installer-owned, or grant any delete authority. Result states are
`CONSISTENT_METADATA_NOT_OWNERSHIP`, `REVIEW_REQUIRED`,
`INCOMPLETE` or `NO_MODEL_CANDIDATES`. Synthetic checks are
in `tests/test_uninstall_inventory.py`. See
`docs/PROJECT-UNINSTALL-COVERAGE.md` for specific limits.

### Read-only Docker dependency reconciliation (SOURCE_ONLY)

After a separately reviewed clean fast-forward on the physical host,
`python3 -B scripts/lifecycle/uninstall-inventory.py references` checks
external Docker container image-ID/volume/bind dependencies against
the bounded project candidate inventory, including discovered
UNVERIFIED assets. It prints `NO_OBSERVED_CONFLICTS` (exit 0),
`CONFLICTS` (exit 3) or `INCOMPLETE` (exit 2); `--json` is
available. No destructive commands or ownership changes occur.
The inspection is point-in-time and is **not** a deletion authorizer
or substitute for immutable ownership evidence. Synthetic regressions:
`tests/test_uninstall_inventory.py`. Exact scope and limitations:
`docs/PROJECT-UNINSTALL-COVERAGE.md`.

## Exact-SHA isolated local tests

After an independently reviewed **clean, fast-forward-only Git synchronization**, use
`bash scripts/lifecycle/verify-synthetic.sh <exact-40-character-GitHub-HEAD>` on
a checked-out `feat/h38-managed-integration` branch. This helper **never fetches,
pulls, switches branches, installs, uninstalls, invokes host Doctor, launches models
or touches the running service**. It rejects branch/SHA/upstream mismatches and a
dirty worktree; it runs a narrow allowlist of synthetic lifecycle unit tests using
temporary HOME/XDG/TMPDIR and DENY wrappers for Docker/sudo/systemctl/swapoff.
`--ci` is reserved for GitHub Actions detached checkout validation only.
Success does not qualify M1 live host health, M2 destructive E2E, M3 all-pairs,
or H38. See `OPERATIONS.md` for the separate guarded sync commands.

The local result marker `LOCAL_SYNTHETIC_HOST_COMMANDS=PATH_DENY_STUBS` denotes PATH interception only, **not** privileged OS sandbox enforcement. Full operator commands are in `OPERATIONS.md`.


## Compact read-only selected profile (first status item)

After an exact-SHA clean Git fast-forward, **before** running isolated tests, use
\`python3 scripts/lifecycle/inspect-selected-profile.py\` with the normal
operator HOME/XDG environment. This reports the currently selected manifest
\`MODEL_PROFILE\`, install \`PHASE\`, checkpoint-path marker presence,
monitor-protection configuration, pending profile/runtime/update/refresh
transactions, optional read-only Docker container configuration and systemd
service state. \`SELECTED_PROFILE\` is the intended configured profile, **not**
proof that it is running or healthy. \`ACTUAL_SERVED_PROFILE=NOT_VERIFIED\`
remains until independent readiness evidence. Docker/systemd probe errors are
UNKNOWN, not falsely 'absent'.

The synthetic verifier runs in a temporary HOME/XDG and **must not** be used
to infer the DGX's selected profile. Its test allowlist includes isolated
\`test_selected_profile_readonly.py\` fixtures only. The broader
\`inspect-readonly-lifecycle.sh\` places the compact summary before inventory,
transaction details and read-only Doctor; Doctor can report existing
host-health failures without mutating the host.


## Profile-switch pair coverage in the isolated verifier (2026-10-12)

The exact-SHA disposable synthetic verifier now includes
`test_profile_switch_transition.py` in addition to the earlier six
modules. That fixture exercises all 12 directed pairs among four accepted
state-schema profiles, with committed, uncommitted-rollback, and
wrong-container-ID refusal/rollback outcomes. It uses fake Docker inspect
and temporary HOME/XDG, never a production profile switch. CI
[#38204508012](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38204508012)
PASS, **70/70 allowlisted synthetic tests**, but M3 actual all-pairs remains
NOT_QUALIFIED.


## Crash leftovers and false-idle refusal — 2026-10-12

The profile-switch helper's `rollback`, `recover`,
`service-recover` and `status` no longer claim a safe idle state if
transaction state is a dangling symlink, or if a backup, candidate,
staging state `.tmp`, or commit-complete `.tmp` remains without a
transaction. The valid empty-idle path is preserved. Three isolated
regressions raised the profile-switch selected module to **16 cases**
and full allowlisted verifier to **76 cases**. GitHub CI
[#38212223945](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38212223945)
SUCCESS. No true production host startup/rollback or physical M3
acceptance established.


## Prepare-stage orphan admission guard — 2026-10-12

The actual protected DGX locally completed the previous source's **76/76 isolated synthetic** at exact `9220624` (ShellCheck locally skipped). A subsequent code review added a new pre-publication guard: `profile-switch-transition.sh prepare` now refuses orphan backup, candidate, state `.tmp`, manifest-stage `.tmp`, and commit-stage files/symlinks, rather than admitting a new transaction and overwriting retained interrupted evidence. The additional disposable-fixture test covers six file variants and one dangling link. This newer change is not included in that completed DGX run. Evidence: [DGX 76 and prepare admission](../benchmark/evidence/dgx-76-and-prepare-orphan-guard-20261012.md). Live Docker/systemd qualification remains blocked.


**GitHub follow-up CI confirmation (2026-10-12):** [#38215072213](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38215072213) at exact new source HEAD `51e85f6578ee0694a13964f700f30e854f17c020` passed **803/803 full Python and 77/77 selected synthetic**, with 17 profile-switch tests, Bash syntax, ShellCheck, compilation and whitespace PASS. The sole DGX latest actual *isolated synthetic* evidence remains **76/76 at `9220624`**. No new live M1/M2/M3/M4 acceptance; PR #259 remains Draft/Open/Unmerged.


## Actual DGX prepare-artifact guard synthetic acceptance (2026-10-12)

The previously GitHub-only additional `prepare` regression has now passed on the actual DGX via the bounded fixture-only verifier at exact `1283b1a` (**77/77 total, 17/17 profile-switch tests**). The source was fast-forwarded from `9220624`; local Bash syntax PASS and ShellCheck SKIPPED_NOT_INSTALLED. Matching exact-source GitHub CI #38215504822 passed 803/803 full and 77/77 synthetic. [Permanent evidence](../benchmark/evidence/dgx-77-prepare-orphan-synthetic-pass-20261012.md). This is not real service/docker E2E and all host gates remain unchanged.


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

Source `7acd15cc5a2d8f5603bdb82b08b1cee49da7d18a` introduced a stdlib-only JSON D0 policy evaluator and nine fixture regressions. [GitHub CI #38217170909](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38217170909) **SUCCESS 812/812 full tests, 77/77 existing bounded synthetic**, Bash syntax, ShellCheck, Python compile, whitespace PASS. The D0 test methods are **not** yet in the bounded DGX verifier; latest DGX actual local run remains `1283b1a` **77/77**. A policy-consistent response is `D0_STATIC_REVIEW=READY_FOR_INDEPENDENT_REVIEW` with `D0_ADMISSION=NOT_GRANTED`; it is not live host attestation or D0 acceptance. [Permanent source/limitation evidence](../benchmark/evidence/disposable-d0-offline-preflight-ci-20261012.md). M1/M2/M3/M4 remain NOT_QUALIFIED/NOT_RUN/BLOCKED and PR #259 stays Draft/Open/Unmerged.


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

The 12 new fixture cases cover protected host/daemon identities, clean Git source, path and mount drift, Docker outage/contamination and nonexclusive service refusal. No actual Docker/systemd on a disposable host was inspected; the collector is **not approved for the sole protected DGX**. Its on-host result always keeps `d0_admission=NOT_GRANTED` and `d1_d5=NOT_AUTHORIZED`, even when supplied host observations match. [Permanent evidence and trust limitations](../benchmark/evidence/d0-onhost-readonly-crosscheck-ci-20261012.md). Latest *actual DGX local* isolated synthetic remains 77/77 at `1283b1a`. D0 independent real-host review and D1–D5 remain NOT_RUN; M1/M2/M3/M4, strict host protections and PR #259 Draft/Open/Unmerged are unchanged.


## D0 parent-mount and Docker-endpoint fail-closed refinement (2026-10-12)

The source-only read-only host observer now rejects **non-root ancestor mounts** overlapping proposed disposable roots, Docker environment overrides, TCP/SSH and default/shared Unix socket endpoints, aliased/missing sockets, and refuses to use an implicit Docker context for daemon reads. Git command probes set `GIT_OPTIONAL_LOCKS=0` to avoid optional Git index refresh. The four trust-boundary fixture methods and one Git no-optional-locks method extend the read-only D0 module to **17/17 synthetic tests**.

[CI #38266470002](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38266470002) at `4dfc2aed238ce96be0b5f3970256b8a2ce8cadf8` **SUCCESS 828/828 full, 77/77 selected**, and [CI #38267015272](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38267015272) at `b65c0142340d90d681c8f82d05294bb72d813687` **SUCCESS 829/829 full, 77/77 selected** plus Bash/ShellCheck/Python compile/whitespace PASS. [Canonical source evidence](../benchmark/evidence/d0-parent-mount-docker-endpoint-guards-20261012.md) explains remaining host-attestation gaps. The latest *actual DGX-local* isolated result remains **77/77 at `1283b1a`**. This source has not been run on either actual DGX or independent disposable host. D0 `NOT_GRANTED`; D1–D5 `NOT_RUN`; M1/M2/M3/M4 unchanged; PR #259 Draft/Open/Unmerged, Ready/Merge BLOCKED.


## D0 read-only command environment and protected-socket refusal (2026-10-13)

Source `f4e83d2ae3f17d82c5f7702497138c3431072358` hardens the on-host D0 read-only observer against redirected Git/Systemd/DBus environment selectors; removes unpinned default Docker info/container commands from the allowlist; refuses arbitrary populated Docker environment overrides; and blocks context endpoints inside forbidden production roots or on/under non-root mountpoints. `GIT_OPTIONAL_LOCKS=0` remains enforced. Five new fixture methods confirm refusal before unintended host commands. [GitHub CI #38315552300](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38315552300) **SUCCESS 834/834 full Python, 77/77 existing selected synthetic, 22/22 D0 crosscheck fixtures, ShellCheck/Bash/Python compile/whitespace PASS**.

[Permanent D0 environment and socket-source evidence](../benchmark/evidence/d0-env-redirection-and-socket-boundaries-20261013.md) records provenance, safety rationale and remaining host-attestation gaps. The **latest actual DGX-local** isolated synthetic result remains **77/77 at `1283b1a`**, not the newer GitHub source. No actual independent disposable host observation or live D0 qualification occurred. `D0_LIVE_ADMISSION=NOT_GRANTED`, `D1_D5=NOT_RUN`, M1/M2/M3/M4 unchanged, and PR #259 Draft/Open/Unmerged with Ready/Merge BLOCKED.


## D0 exact-input digest receipts and offline consistency review (2026-10-13)

At source SHA `e41a34f06887f526d0a7ac7cb605d263c226f8f6`, the strict JSON reader hashes the **same bounded no-symlink file-descriptor bytes it parsed**, the read-only host collector emits `policy_sha256` and `inventory_sha256`, and the new `disposable-d0-receipt-review.py` compares its receipt to the exact supplied policy/inventory JSON. Mismatched files, invalid receipt schema, changed Git SHA and forged admission markers are refused. Consistent input is only `D0_RECEIPT_REVIEW=CONSISTENT_UNTRUSTED`; external attestation and replay freshness remain `NOT_VERIFIED`.

[Source CI #38316973840](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38316973840) **SUCCESS: 845/845 full Python, 77/77 bounded synthetic, Bash/ShellCheck/Python compile/whitespace PASS**. [Permanent fixture evidence](../benchmark/evidence/d0-receipt-input-binding-ci-20261013.md) and [receipt workflow/limitations](../../docs/D0-RECEIPT-CHAIN.md) preserve provenance and non-admission semantics. The new 11 tests are **outside** the 77-case bounded DGX synthetic verifier; latest **actual DGX-local** synthetic remains **77/77 at `1283b1a`**. No actual disposable host observation occurred; D0 admission NOT_GRANTED, D1–D5 NOT_RUN, M1/M2/M3/M4 remain unqualified/blocked, PR #259 remains Draft/Open/Unmerged.


## D0 external owner/isolation/restore evidence-chain consistency (2026-10-13)

Source `a52ae7f2985ce0f415134b848b6caeb6aefec348` adds `disposable-d0-external-evidence-review.py`, a strictly offline, read-only and fail-closed review of the previous exact-input D0 receipt and **three separately provided artifacts** for independent-owner consent claims, Docker isolation claims and controlled restore-drill claims. It requires the exact policy, inventory, receipt SHA256, host/daemon identifiers and restore point to match; refused evidence includes missing/overlapping role IDs, altered/missing/empty/symlink proofs, overlapping proof digests, contradictory scopes and forged admission. The artifact contents and claimed reviewer actor IDs are **not authenticated or independently witnessed**; success only reports `STRUCTURALLY_CONSISTENT_UNTRUSTED` and always `D0_ADMISSION=NOT_GRANTED`, `D1_D5=NOT_AUTHORIZED`.

[Exact-source GitHub CI #38317915217](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38317915217) **SUCCESS: 860/860 full Python (15 new external proof methods), 77/77 existing bounded synthetic, Bash/ShellCheck/Python compile/whitespace PASS**. See [permanent evidence](../benchmark/evidence/d0-external-owner-isolation-restore-evidence-ci-20261013.md) and [external review schema and workflow](../../docs/D0-EXTERNAL-EVIDENCE-REVIEW.md). The latest **actual DGX-local** fixture acceptance remains `1283b1a` 77/77, not this source; no actual independent disposable host D0 verification or D1–D5 has occurred. M1/M2/M3/M4 and PR #259 Draft/Open/Unmerged gates unchanged.


## DGX staged A/B validation recommendation — 2026-10-13

**Run A now when DGX is quiet**: after review and fast-forward-only Git synchronization to exact successful GitHub SHA, invoke the pre-existing local synthetic verifier, now extended to **134/134** offline fixtures (77 original plus 57 D0). It additionally checks the canonical repository origin and refuses Git environment redirection. After A PASS, B is **real HOME/XDG read-only selected-profile and optional Doctor/status observation**, not an M1 acceptance. **C** D0 admission and destructive D1–D5 belong on a separately owned disposable host only; **D** live H38 on the sole protected DGX remains blocked pending RM/metadata/stability/recovery and explicit approval. Source [CI #38319566009](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38319566009) PASS 863/863 full and 134/134 selected; latest actual DGX remains 77/77 at 1283b1a. [Safe DGX operator instructions](../../docs/DGX-STAGED-VALIDATION.md); [source evidence](../benchmark/evidence/dgx-stage-a-expanded-synthetic-ci-20261013.md). D0 NOT_GRANTED, D1–D5 NOT_RUN, M1–M4 unchanged, PR #259 Draft/Open/Unmerged.


## Actual DGX 134/134 PASS and solo-owner test authorization boundary (2026-10-13)

User-supplied terminal evidence establishes **actual local 134/134 bounded synthetic PASS at exact b35d0f3d7840d00c55f4c633813e88ac367c6373** (Bash PASS; ShellCheck SKIPPED_NOT_INSTALLED). The immediately following real-HOME selected-profile snapshot showed a VALID complete OrcaRouter manifest, four transactions IDLE, no stale artifacts, monitor/protection both `1`, Docker container EXITED, service INACTIVE and runtime attestation MISSING. This is **A=PASS and B1=COLLECTED**, not M1 health or H38 acceptance. [Actual operator evidence](../benchmark/evidence/dgx-local-134-pass-readonly-snapshot-20261013.md).

The sole DGX owner reports testing can occur at any time without disrupting other human users. **Bounded, reversible, owner-approved live runtime tests on this one DGX may be considered after B2 full read-only Doctor and recovery review**; a second physical DGX is not mandatory for every runtime test. This revises the former blanket schedule restriction but does **not** approve deleting resources, assume Docker exclusivity, upgrade independent disposable D0 admission, run destructive D1-D5 on the only host, or launch H38 against the unresolved checkpoint/RM gates. Immediate B2: use the existing read-only lifecycle inspector at the **already checked out b35d0f3**; do not sync Git merely to run it. PR #259 remains Draft/Open/Unmerged; Ready/Merge BLOCKED.
