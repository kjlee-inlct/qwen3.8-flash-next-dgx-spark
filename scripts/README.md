# Script layout

This directory preserves upstream-derived paths and stable operator entry points at
`scripts/*` while keeping repository-specific implementations in role-specific
subdirectories.

## Upstream provenance

The canonical upstream for this repository is:

- `dolf3131/qwen3.8-flash-next-dgx-spark`

The following files exist upstream under the same `scripts/` paths and must remain
at those paths in this fork. Some are byte-identical to upstream; others have been
extended locally but retain upstream provenance:

- `Dockerfile.nv-mixed`
- `Dockerfile.skinny-gemm`
- `bench-prefill.py`
- `download-weights.sh`
- `patch-nv-mixed.py`
- `patch-skinny-gemm-tp1.py`
- `serve.sh`

These files are not candidates for cosmetic relocation.

## Stable operator entry points

The following repository-specific top-level paths are stable commands or service
entry points and remain directly available:

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

## Compatibility entry points

Several older top-level helper paths are retained as thin compatibility shims so
existing releases, tests, scripts, and automation do not break while canonical
implementations live under role-specific directories:

- `bootstrap-release.sh` -> `lifecycle/bootstrap-release.sh`
- `qualify-release.sh` -> `lifecycle/qualify-release.sh`
- `collect-diagnostics.sh` -> `diagnostics/collect-diagnostics.sh`
- `monitor-runtime.sh` -> `runtime/monitor-runtime.sh`
- `validate-runtime.py` -> `runtime/validate_runtime.py`
- `model-profiles.sh` -> `model/model-profiles.sh`
- `inspect-model.py` -> `model/inspect_model.py`
- `prepare-config.py` -> `model/prepare_config.py`
- `state_file.py` -> `lib/state_file.py`
- `release_manifest.py` -> `lib/release_manifest.py`
- `doctor-observability.sh` -> `diagnostics/doctor-observability.sh`

Compatibility shims are intentionally small. New internal code should use the
canonical path rather than adding new dependencies on a shim.

## Canonical internal categories

Repository-specific implementations are organized as follows:

- `lib/`: reusable Python helpers shared by lifecycle/runtime scripts.
- `diagnostics/`: read-only diagnostics and support-bundle implementation.
- `runtime/`: runtime transition, preflight, service runner, monitor, and runtime validation.
- `lifecycle/`: immutable-release bootstrap, qualification, and update transaction logic.
- `model/`: model profile, checkpoint inspection, and config preparation helpers.

Canonical implementations include:

- `lib/state_file.py`
- `lib/release_manifest.py`
- `diagnostics/doctor-observability.sh`
- `diagnostics/collect-diagnostics.sh`
- `runtime/runtime-transition.sh`
- `runtime/preflight-runtime.sh`
- `runtime/service-runner.sh`
- `runtime/monitor-runtime.sh`
- `runtime/validate_runtime.py`
- `lifecycle/update-transition.sh`
- `lifecycle/bootstrap-release.sh`
- `lifecycle/qualify-release.sh`
- `model/model-profiles.sh`
- `model/inspect_model.py`
- `model/prepare_config.py`

## Benchmark layout

The repository benchmark harness lives under top-level `bench/`:

- `bench/run.py` is the stable benchmark CLI.
- `bench/lib/` contains implementation helpers used by the CLI.
- `bench/common.py` is a compatibility import for older code/tests.
- `scripts/bench-prefill.py` stays in `scripts/` because it is upstream-derived;
  it is not the canonical benchmark harness for this fork.

## Layout rules

1. Do not relocate upstream-derived paths from `dolf3131/qwen3.8-flash-next-dgx-spark`.
2. Keep operator/service entry points stable.
3. Put repository-specific implementation under an explicit role directory.
4. Preserve older helper paths with small compatibility shims when removing them
   would break existing releases, tests, or automation.
5. Update internal references, tests, documentation, and CI in the same change.
6. Do not combine layout refactors with unrelated runtime behavior changes.

## CI rule

Shell syntax and ShellCheck must recurse into script subdirectories. Python
compilation must recurse through `scripts/`, `bench/`, and `tests/`.
