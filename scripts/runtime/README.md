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


## OrcaRouter v0.29 H38 runtime profiles

`orcarouter-v029.sh` also owns the validated H38 investigation/runtime profiles:

| Profile | Role | Canonical scope |
|---|---|---|
| `hybrid-h38-deterministic` | H38 production runtime | decoder-only |
| `hybrid-h38-decoder-scope` | explicit decoder A/B control | decoder-only |
| `hybrid-h38-all-scope` | fallback/regression control | all Marlin calls |

The production profile uses
`vllm-orcarouter-v029-h38-decoder-scope:v1`. The all-scope fallback keeps
`vllm-orcarouter-v029-h38-deterministic:v1` for regression continuity.

The canonical evidence is in `../benchmark/README.md`, with a concise summary
in `../../docs/H38-DETERMINISM.md`.

These H38 profiles are dedicated v0.29 runtime helpers and are not yet wired
into the transactional `install.sh` / systemd-managed `serve.sh` lifecycle.
Do not conflate H38 runtime qualification with managed-service qualification.


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
