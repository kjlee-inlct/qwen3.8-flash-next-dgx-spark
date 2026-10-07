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
- `collect-managed-readiness-evidence.sh`: read-only collector for lifecycle, service, monitor, Docker, and kernel evidence after a managed startup/readiness failure.
- `mazinb-kv-ab.sh`: guarded temporary mazinb 24 GiB vs 16 GiB KV-cache host-stability experiment with isolated monitor state and strict evidence classification.
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

The dedicated H38 profiles above remain the historical qualification surface.
The current H38 managed-integration feature branch also selects the decoder-scope
image for the managed `orcarouter` profile after an explicit
`--refresh-profile-defaults` migration. A pre-H38
`vllm-skinny-tp1:v1` manifest remains bootable after immutable code update so
the release cutover and runtime-default migration remain separate transactions.

That managed integration is implemented but live qualification is still
pending. Do not conflate the historical H38 runtime qualification with
installer/systemd managed-service qualification. See
`../benchmark/evidence/orcarouter-h38-managed-integration-plan-20261007.md`
for the acceptance gate.

## Temporary NVIDIA tuning runtimes

`nvidia-2x2.sh` launches a temporary, separately named container for one
controlled benchmark case. It does not modify installation state, runtime
attestation, or the managed service unit. It refuses to start if the
managed service or canonical container is still running.

Use `bash scripts/runtime/nvidia-2x2.sh plan` for the fixed controls and
A/B/C/D matrix. Operators must stop the managed service before a case and
restart it after the experiment series. Benchmark policy and result
interpretation remain documented under `../benchmark/README.md`.

## Current managed KV defaults and host-stability semantics

The managed profile registry is the source of truth for current runtime defaults.
As of the R23–R32 closure branch merge, both OrcaRouter and mazinb managed profiles
use a 16 GiB KV cache (`17179869184` bytes) as a resilience setting. Do not treat
that value as a proven fix for NVIDIA RM system-memory allocation failures.

The strict classification rule remains:

> Any confirmed `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` in a valid measured
> run is HOST-STABILITY FAIL, even if fallback recovers and the runtime reaches READY.

Therefore a managed mazinb run may be FUNCTIONAL PASS while still being
HOST-STABILITY FAIL. Current defaults describe the managed configuration; they do
not override the measured host-stability classification.

## mazinb KV host-stability A/B

The original 2026-10-02 managed mazinb activation used
`KV_MEM=25769803776` (24 GiB). That historical activation completed model loading,
compile, warmup, KV allocation, and CUDA graph capture, but the host emitted
`_memdescAllocInternal` / `NV_ERR_NO_MEMORY (0x51)` and the safety monitor then
performed a protected stop before managed readiness.

`mazinb-kv-ab.sh` preserves the controlled historical 24 GiB vs 16 GiB experiment
without changing the managed install manifest or runtime attestation:

| Case | KV cache | Purpose |
|---|---:|---|
| A | 24 GiB (`25769803776`) | historical 24 GiB control |
| B | 16 GiB (`17179869184`) | reduced-KV comparison matching the current managed resilience value |

All other runtime controls are pinned to the original failed mazinb attempt:
262144 maximum model length, MTP `k=2`, `MAXSEQS=3`, prefix cache off, index
sharing off, FlashInfer autotune off, exact QSA on, loopback-only API, no Docker
restart, and the same memory-monitor protection floors. Each case gets a separate
container name and separate `XDG_STATE_HOME`, so its monitor log and protected-stop
marker do not overwrite managed runtime state.

The helper remains useful for reproducing the historical A/B contrast, but it is
not the canonical description of the current managed profile. Check
`../model/model-profiles.sh` for current profile defaults before running or
interpreting a new experiment.

Run the reduced-KV B case first when reproducing the historical comparison:

```bash
sudo -v
bash scripts/runtime/mazinb-kv-ab.sh plan
bash scripts/runtime/mazinb-kv-ab.sh preflight
bash scripts/runtime/mazinb-kv-ab.sh run B \
  |& tee /tmp/mazinb-kv-b-20261002.txt
```

Use `|& tee`, not a stdout-only pipe, so startup/runtime diagnostics written to
stderr are retained with the case evidence.

`run` waits up to 1800 seconds for `/health`, validates that `/v1/models`
contains only the expected mazinb served-model ID, performs a 180-second soak,
stops the temporary runtime to release memory, then prints the case evidence.
A case is `FUNCTIONAL PASS / HOST-STABILITY PASS` only when readiness and model
identity pass, the full soak completes, no memory-protection stop occurs, no
kernel `NV_ERR_NO_MEMORY` is present in the case window, and Docker did not
report `OOMKilled=true`. A pre-ready application failure without host evidence
stays `HOST NOT CLASSIFIED`; it is not promoted to a host pass.

Interpret results conservatively:

- B fails with the same RM/protected-stop signature: reducing KV from 24 GiB to
  16 GiB is not sufficient.
- B passes the strict gate: this is controlled mitigation evidence only; compare
  with A if the experiment requires a matched contrast.
- B reaches READY but still records `NV_ERR_NO_MEMORY`: functional startup may
  have improved, but the strict host-stability result remains FAIL.

The helper intentionally does not restart the managed service. Experimental
containers and their evidence remain until explicitly cleaned:

```bash
bash scripts/runtime/mazinb-kv-ab.sh evidence B
bash scripts/runtime/mazinb-kv-ab.sh cleanup B
```

A successful 16 GiB temporary experiment is mitigation evidence, not proof that
the managed profile is host-stable. Managed acceptance requires the managed
lifecycle plus the strict RM kernel-evidence gate.

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

For an already-completed failure whose installer output predates the automatic diagnostic block, collect the retained evidence without restarting the model:

```bash
sudo -v
bash scripts/runtime/collect-managed-readiness-evidence.sh \
  --since '2026-10-02 18:00:00'
```

The collector does not start/stop services or containers. Its `--since` value is passed to `journalctl`; choose a window that includes the failed activation. Kernel RM/OOM lines are included only when a non-interactive sudo credential is available, which is why `sudo -v` is shown separately.
