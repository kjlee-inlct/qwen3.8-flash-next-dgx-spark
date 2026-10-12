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
