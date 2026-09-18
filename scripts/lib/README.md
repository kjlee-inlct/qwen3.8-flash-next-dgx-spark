# Shared library helpers

This directory contains low-level reusable helpers shared across script categories.

## Responsibilities

- Parse and validate persistent state files as data, not executable shell input.
- Validate immutable release manifests and qualification markers.
- Provide lifecycle operation-lock semantics.

## Dependency direction

`lib/` is the lowest-level repository-specific script layer. Helpers here should depend only on the standard runtime/toolchain they need and must not import or source higher-level category implementations such as `runtime/`, `lifecycle/`, `model/`, `diagnostics/`, or `benchmark/`.

Higher-level categories may depend on `lib/`.

## Non-responsibilities

- Do not perform lifecycle orchestration.
- Do not start or stop runtime services/containers.
- Do not inspect/download models as a workflow.
- Do not produce operator-facing benchmark or diagnostic workflows.

## Canonical files

- `state_file.py`
- `release_manifest.py`
- `qualification_marker.py`
- `operation-lock.sh`
