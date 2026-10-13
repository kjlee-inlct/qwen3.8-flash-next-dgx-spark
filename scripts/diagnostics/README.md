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

- `check-legacy-orcarouter-b5-readonly.sh`: exact-SHA/installed
  release/retained stopped Docker ID and monitor/swap assertions;
  read-only actual-DGX M1 prestart snapshot, not a service start
  or authorization to discard the Docker predecessor.
- `check-wizard-dgx-readonly.sh`: exact-SHA real DGX wizard inventory,
  four install/switch target **dry-run** previews and bilingual-independent
  uninstall **dry-run** previews, synthetic fixture tests and state
  fingerprints; never activates or purges a model.
- `doctor-observability.sh`: doctor-specific observability checks.
- `runtime-commit-observability.sh`: runtime attestation observability.
- `collect-diagnostics.sh`: bounded support-bundle implementation.
- `h20-nvfp4-moe.py`: canonical H20/H38 NVFP4 MoE capture, parsing, and
  decision helper used to localize routed-expert/Marlin divergence. Historical
  instrumentation failures and superseded hypotheses must remain distinguishable
  from numerical results.

Top-level diagnostic commands in `scripts/` remain stable operator or compatibility entry points and should delegate here where appropriate.
