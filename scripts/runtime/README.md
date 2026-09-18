# Runtime helpers

This directory contains canonical managed-runtime transition, preflight, service-runner, monitoring, and runtime-validation implementation.

## Responsibilities

- Validate runtime prerequisites before start.
- Preserve/replace/rollback the managed container transactionally.
- Run the managed service lifecycle and commit runtime attestation only after validation.
- Monitor runtime resource safety and perform explicit runtime validation.

## Dependencies

- May use strict state parsing and shared helpers from `../lib/`.
- May consume model/profile/config state prepared by installation and `../model/`.
- May expose state for lifecycle and diagnostics layers to inspect.

## Non-responsibilities

- Do not decide which immutable release is qualified/current; that belongs to `../lifecycle/` and release management.
- Do not implement model-download or checkpoint-rewrite workflows.
- Do not own benchmark policy or support-bundle presentation.

## Canonical files

- `preflight-runtime.sh`
- `runtime-transition.sh`
- `service-runner.sh`
- `monitor-runtime.sh`
- `validate_runtime.py`
- `nvidia-2x2.sh`: guarded temporary launcher for the NVIDIA INDEX_SHARE x AUTOTUNE benchmark matrix.

Top-level runtime helper paths in `scripts/` are stable operator or compatibility entry points and should remain thin where a canonical implementation exists.


## Temporary NVIDIA tuning runtimes

`nvidia-2x2.sh` launches a temporary, separately named container for one
controlled benchmark case. It does not modify installation state, runtime
attestation, or the managed service unit. It refuses to start if the
managed service or canonical container is still running.

Use `bash scripts/runtime/nvidia-2x2.sh plan` for the fixed controls and
A/B/C/D matrix. Operators must stop the managed service before a case and
restart it after the experiment series. Benchmark policy and result
interpretation remain documented under `../benchmark/README.md`.
