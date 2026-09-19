# Runtime helpers

This directory contains canonical managed-runtime transition, preflight, service-runner, monitoring, and runtime-validation implementation.

## Responsibilities

- Validate runtime prerequisites before start.
- Preserve/replace/rollback the managed container transactionally.
- Run the managed service lifecycle and commit runtime attestation only after validation.
- Monitor runtime resource safety and perform explicit runtime validation.
- Provide a reusable readiness wait that checks container state, health, and served-model identity.

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
- `wait-ready.sh`
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

## Readiness waiting

Use the stable operator entry point instead of hand-written polling loops:

```bash
./scripts/wait-ready.sh \
  --container qwen38-flash-next \
  --model orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

Experimental containers can use the same helper by changing `--container`. The waiter exits early if the container stops and prints recent logs; otherwise it waits for both `/health` and the expected `/v1/models` entry.
