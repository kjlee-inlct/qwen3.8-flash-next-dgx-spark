# Lifecycle helpers

This directory contains canonical immutable-release qualification, bootstrap, update-transaction, managed profile-switch, and atomic cross-release profile-refresh transaction logic.

## Responsibilities

- Bootstrap and qualify immutable releases.
- Manage update-transition state and cutover transaction boundaries.
- Manage persisted managed-profile replacement/recovery boundaries; this remains the
  canonical profile-switch transaction logic.
- Atomically bind a qualified immutable release to a same-profile runtime-image manifest refresh without booting an intermediate legacy runtime.
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
