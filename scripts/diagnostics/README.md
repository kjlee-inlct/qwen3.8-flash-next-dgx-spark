# Diagnostic helpers

This directory contains canonical repository-specific read-only diagnostics and support-bundle implementation.

## Responsibilities

- Inspect installation, release, runtime, Docker, API-access, and host-health state.
- Produce bounded, redacted diagnostic output and support bundles.
- Report drift and incomplete lifecycle/runtime state without repairing it.

## Dependencies

- May use parsers and validation helpers from `../lib/`.
- May inspect state produced by `../lifecycle/` and `../runtime/`.
- May invoke stable read-only operator entry points when that preserves the public interface.

## Non-responsibilities

- Must not mutate lifecycle or runtime state.
- Must not restart containers or services as part of diagnosis.
- Must not own model preparation or performance benchmarking.

## Canonical files

- `doctor-observability.sh`: doctor-specific observability checks.
- `runtime-commit-observability.sh`: runtime attestation observability.
- `collect-diagnostics.sh`: bounded support-bundle implementation.

Top-level diagnostic commands in `scripts/` remain stable operator or compatibility entry points and should delegate here where appropriate.
