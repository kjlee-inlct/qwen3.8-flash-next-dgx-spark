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
