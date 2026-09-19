# Script layout

This directory preserves upstream-derived paths and stable operator entry points at
`scripts/*` while keeping repository-specific implementations in role-specific
subdirectories.

## Top-level role map

Files directly under `scripts/` fall into one of three intentionally different roles. A path may appear in more than one role when an upstream-derived file is also a stable operator command.

| Role | Purpose | Examples | Relocation policy |
|---|---|---|---|
| Upstream-derived | Preserve provenance and compatibility with the upstream repository layout. | `serve.sh`, `bench-prefill.py`, `download-weights.sh`, `patch-*.py`, `Dockerfile.*` | Keep the upstream path. |
| Stable operator entry point | Human- or service-facing command whose path is part of the operational interface. | `doctor.sh`, `manage-*.sh`, `release-manager.sh`, `update-release.sh`, `runtime-transition.sh` | Keep the public path stable; move implementation only when a thin entry point can preserve compatibility. |
| Compatibility shim | Legacy helper path that forwards to a canonical implementation in a role directory. | `qualify-release.sh`, `collect-diagnostics.sh`, `validate-runtime.py`, `state_file.py` | Keep thin; new internal code must target the canonical path. |

Canonical repository-specific implementation belongs in `scripts/<role>/`, currently:

```text
scripts/
├── benchmark/
├── diagnostics/
├── lifecycle/
├── lib/
├── model/
└── runtime/
```

This distinction is intentional: the goal is not an empty `scripts/` root. The root remains the compatibility and operator surface, while role directories hold canonical internal implementation.

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
- `manage-models.sh`
- `manage-storage.sh`
- `wait-ready.sh`
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
- `benchmark/`: canonical read-only benchmark runner and benchmark helpers.

Canonical implementations include:

- `lib/state_file.py`
- `lib/release_manifest.py`
- `diagnostics/doctor-observability.sh`
- `diagnostics/collect-diagnostics.sh`
- `runtime/runtime-transition.sh`
- `runtime/preflight-runtime.sh`
- `runtime/service-runner.sh`
- `runtime/monitor-runtime.sh`
- `runtime/wait-ready.sh`
- `runtime/validate_runtime.py`
- `lifecycle/update-transition.sh`
- `lifecycle/bootstrap-release.sh`
- `lifecycle/qualify-release.sh`
- `model/model-profiles.sh`
- `model/inspect_model.py`
- `model/prepare_config.py`

## Storage management

`scripts/manage-storage.sh` is the project-wide disk usage and cleanup entry point.
It inventories managed checkpoints, Docker usage, immutable releases, local benchmark
results, the Hugging Face cache, and the dedicated PLE swap file.

The default prune policy is deliberately conservative:

- never delete the active checkpoint or any managed model directory;
- never delete the manifest's active runtime image;
- retain both current and previous immutable releases;
- retain the PLE swap and Hugging Face cache;
- remove only stopped experiment containers, dangling images, stale build cache,
  inactive releases, and aged local benchmark results;
- remove known QSA experiment image tags only with `--experiments`.

Examples:

```bash
./scripts/manage-storage.sh status
./scripts/manage-storage.sh plan
./scripts/manage-storage.sh plan --experiments
./scripts/manage-storage.sh prune --dry-run --experiments
./scripts/manage-storage.sh prune --yes
```

Use `scripts/manage-models.sh` separately when an inactive managed checkpoint itself
should be removed.

## Benchmark layout

The canonical repository benchmark harness lives under `scripts/benchmark/`:

- `scripts/benchmark/run.py` is the canonical benchmark CLI.
- `scripts/benchmark/lib/` contains implementation helpers used by the CLI.
- `scripts/benchmark/common.py` is a local compatibility import used by the runner.
- top-level `bench/run.py` and `bench/common.py` are compatibility shims for older callers.
- `scripts/bench-prefill.py` stays at its upstream-derived path and is not the canonical benchmark harness for this fork.

## Dependency boundary policy

Canonical category code follows an explicit dependency direction:

| Category | May directly depend on |
|---|---|
| `lib/` | no other canonical category |
| `model/` | `lib/` |
| `runtime/` | `lib/`, `model/` |
| `lifecycle/` | `lib/`, `runtime/` |
| `diagnostics/` | `lib/`, `lifecycle/`, `runtime/` |
| `benchmark/` | no other canonical category; it measures the exposed runtime/API rather than importing orchestration |

Self-references inside a category are allowed. Stable top-level operator entry points are not treated as canonical-category dependencies because they are part of the public compatibility surface.

The layout tests scan canonical implementation files for explicit cross-category path references and fail when a reference points outside this allowlist. This is a guardrail rather than a full language-level import graph, so new dependency styles should extend the test instead of bypassing it.

## Layout rules

1. Do not relocate upstream-derived paths from `dolf3131/qwen3.8-flash-next-dgx-spark`.
2. Keep operator/service entry points stable.
3. Put repository-specific implementation under an explicit role directory.
4. Preserve older helper paths with small compatibility shims when removing them
   would break existing releases, tests, or automation.
5. Update internal references, tests, documentation, and CI in the same change.
6. When an operational workflow starts needing repeated ad-hoc commands, promote it to a reusable operator helper and document it in the same PR.
7. Do not combine layout refactors with unrelated runtime behavior changes.

## CI rule

Shell syntax and ShellCheck must recurse into script subdirectories. Python compilation must recurse through `scripts/` and `tests/`; canonical benchmark code is included under `scripts/benchmark/`.
