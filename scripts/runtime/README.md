# Runtime helpers

This directory contains canonical managed-runtime transition, preflight, service-runner, monitoring, and runtime-validation implementation.

## Responsibilities

- Validate runtime prerequisites before start.
- Preserve/replace/rollback the managed container transactionally.
- Run the managed service lifecycle and commit runtime attestation only after validation.
- Monitor runtime resource safety and perform explicit runtime validation.
- Provide a reusable readiness wait that checks container state, health, and served-model identity.
- Provide read-only exact-host preflights for runtime/driver instrumentation and blocked profile-switch legs without mutating lifecycle state.

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
- `check-h6-r9-rmsys-probes.sh`: read-only R9 exact-host RM/sysmem probe and trace-filter preflight; it starts no model.
- `check-mazinb-switch-preflight.sh`: read-only Hybrid -> mazinb asset/lifecycle preflight; it performs no profile-switch mutation.
- `orcarouter-v029.sh`: dedicated OrcaRouter v0.29 investigation/runtime launcher, including the validated H38 profiles.
- `orcarouter-stock-skinny.sh`: guarded stock/skinny OrcaRouter comparison launcher.
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

## Managed readiness failure diagnostics

The systemd installer path waits for a replacement runtime to become healthy, expose the expected served-model identity, and write a matching runtime-commit attestation. If the managed service becomes inactive before that boundary, or the 30-minute readiness window expires, `scripts/manage-service.sh` prints failure context before returning an error.

The diagnostic block includes:

- systemd `ActiveState`, `SubState`, `Result`, `ExecMainCode`, and `ExecMainStatus`;
- the recent managed-service journal;
- the recent runtime memory-monitor log, including protection warnings/stops when present;
- Docker container status, exit code, `OOMKilled`, engine error, and start/finish timestamps; and
- a recent timestamped container-log tail.

This output is evidence collection, not a host-stability classification by itself. In particular, a service that becomes `inactive` during startup can be consistent with the intentional memory-protection path because `service-runner.sh` exits successfully after a matching protected stop. Confirm the monitor/journal evidence before classifying the event as memory protection, runtime failure, or another lifecycle stop.
