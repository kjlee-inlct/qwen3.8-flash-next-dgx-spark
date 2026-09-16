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

The following repository-specific top-level paths are treated as stable
operator/API or compatibility entry points and must remain available even when
their implementation moves internally:

- `doctor.sh`
- `manage-service.sh`
- `manage-proxy.sh`
- `manage-swap.sh`
- `release-manager.sh`
- `update-release.sh`
- `runtime-transition.sh`
- `update-transition.sh`
- `preflight-runtime.sh`
- `service-runner.sh`

Stable top-level compatibility paths are intentional. Existing systemd units,
operator commands, immutable releases, and external automation may continue to
reference them.

## Canonical internal categories

Only helpers added by this repository are reorganized into these categories:

- `lib/`: reusable Python helpers used by lifecycle/runtime scripts.
- `diagnostics/`: read-only diagnostic helpers sourced by operator commands.
- `runtime/`: internal runtime cutover, preflight, and service lifecycle logic.
- `lifecycle/`: internal immutable-release/update transaction logic.
- future `model/` and `service/` categories may be introduced incrementally only
  for repository-specific helpers, with tests and compatibility paths updated in
  the same change.

Canonical implementations currently include:

- `lib/state_file.py`
- `lib/release_manifest.py`
- `diagnostics/doctor-observability.sh`
- `runtime/runtime-transition.sh`
- `runtime/preflight-runtime.sh`
- `runtime/service-runner.sh`
- `lifecycle/update-transition.sh`

The old top-level paths remain compatibility shims. Internal canonical code
should prefer canonical `lib/`, `runtime/`, and `lifecycle/` paths so new code
does not grow dependencies on the shims.

## Layout rules

1. Do not relocate upstream-derived paths from `dolf3131/qwen3.8-flash-next-dgx-spark`.
2. Move repository-specific implementation only when an explicit category adds
   operational clarity.
3. Preserve existing top-level operator/API paths with small compatibility shims.
4. Update internal references, tests, documentation, and CI in the same change.
5. Do not combine a layout refactor with unrelated runtime behaviour changes.

## CI rule

Shell syntax and ShellCheck must recurse into script subdirectories. Python
compilation must recurse through `scripts/`, `bench/`, and `tests/`.
