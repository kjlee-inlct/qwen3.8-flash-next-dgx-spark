# Script layout

This directory keeps stable operator entry points at `scripts/*.sh` while moving
internal implementations into role-specific subdirectories. Existing public
paths remain compatibility shims until a deliberate breaking-change release.

## Stable entry points

The following top-level paths are treated as stable operator/API entry points
and should not be moved without a compatibility shim:

- `doctor.sh`
- `serve.sh`
- `manage-service.sh`
- `manage-proxy.sh`
- `manage-swap.sh`
- `release-manager.sh`
- `update-release.sh`

## Canonical internal categories

- `lib/`: reusable Python helpers used by lifecycle/runtime scripts.
- `diagnostics/`: read-only diagnostic helpers sourced by operator commands.
- future `runtime/`, `lifecycle/`, `model/`, and `build/` categories should be
  introduced incrementally, with tests and compatibility paths updated in the
  same change.

Current canonical implementations moved in the first layout phase:

- `lib/state_file.py`
- `lib/release_manifest.py`
- `diagnostics/doctor-observability.sh`

The old top-level paths remain executable/importable compatibility shims.

## Upstream/fork provenance

Files retained from an upstream or forked source must keep their original
source-tree location. This layout refactor applies only to repository-specific
scripts that were added here; it must not reorganize upstream `files/`,
`deployment/`, or other source locations merely for cosmetic consistency.

## CI rule

Shell syntax and ShellCheck must recurse into script subdirectories. Python
compilation already recurses through `scripts/`.
