# Lifecycle helpers

This directory contains canonical immutable-release qualification, bootstrap, and update-transaction logic.

## Responsibilities

- Bootstrap and qualify immutable releases.
- Manage update-transition state and cutover transaction boundaries.
- Enforce fail-closed qualification and lifecycle serialization rules.

## Dependencies

- May use shared parsers, release-manifest validation, and operation locking from `../lib/`.
- May call stable operator entry points needed to apply a qualified release.
- May coordinate runtime replacement, but runtime container validation/rollback mechanics remain owned by `../runtime/`.

## Non-responsibilities

- Do not implement model inspection/config preparation.
- Do not implement runtime health/monitoring internals.
- Do not own diagnostics or benchmark workloads.

## Canonical files

- `bootstrap-release.sh`
- `qualify-release.sh`
- `update-transition.sh`

Top-level compatibility paths such as `scripts/qualify-release.sh` should remain thin delegators.
