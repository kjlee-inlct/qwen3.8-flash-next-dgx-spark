# Script layout

This directory keeps upstream-derived paths and stable operator entry points at
`scripts/*` while moving only repository-specific internal implementations into
role-specific subdirectories.

## Upstream provenance

The canonical upstream for this repository is:

- `dolf3131/qwen3.8-flash-next-dgx-spark`

The following files exist in upstream under the same `scripts/` paths and must
remain at those paths in this fork. Some are still byte-identical to upstream;
others have been extended locally but retain upstream provenance:

- `Dockerfile.nv-mixed`
- `Dockerfile.skinny-gemm`
- `bench-prefill.py`
- `download-weights.sh`
- `patch-nv-mixed.py`
- `patch-skinny-gemm-tp1.py`
- `serve.sh`

These files are not candidates for cosmetic relocation. If internal code later
needs different organization, keep the upstream-derived entry path stable and
add repository-specific helpers elsewhere rather than moving the upstream file.

## Stable local entry points

The following repository-specific top-level paths are also treated as stable
operator/API entry points and should not be moved without a compatibility shim:

- `doctor.sh`
- `manage-service.sh`
- `manage-proxy.sh`
- `manage-swap.sh`
- `release-manager.sh`
- `update-release.sh`

## Canonical internal categories

Only helpers added by this repository are reorganized into these categories:

- `lib/`: reusable Python helpers used by lifecycle/runtime scripts.
- `diagnostics/`: read-only diagnostic helpers sourced by operator commands.
- future `runtime/`, `lifecycle/`, `model/`, and `service/` categories may be
  introduced incrementally only for repository-specific helpers, with tests and
  compatibility paths updated in the same change.

Current canonical implementations moved in the first layout phase:

- `lib/state_file.py`
- `lib/release_manifest.py`
- `diagnostics/doctor-observability.sh`

The old top-level paths remain executable/importable compatibility shims.

## CI rule

Shell syntax and ShellCheck must recurse into script subdirectories. Python
compilation already recurses through `scripts/`.
