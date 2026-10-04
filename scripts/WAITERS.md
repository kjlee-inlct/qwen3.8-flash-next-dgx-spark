# Runtime wait helpers

This document defines the stable operator-facing wait commands under `scripts/` and their canonical implementations under `scripts/runtime/`.

## `wait-ready.sh`

Stable entry point:

```text
scripts/wait-ready.sh
```

Canonical implementation:

```text
scripts/runtime/wait-ready.sh
```

Purpose: wait for a runtime to become usable.

The helper checks the named container, `/health`, and optionally the expected served-model identity from `/v1/models`. It exits early with diagnostics if the runtime stops or disappears instead of waiting for the full timeout.

Example:

```bash
./scripts/wait-ready.sh \
  --container qwen38-flash-next \
  --model orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4
```

Use this helper after starting/restarting a runtime instead of hand-written health polling loops.

## `wait-runtime-age.sh`

Stable entry point:

```text
scripts/wait-runtime-age.sh
```

Canonical implementation:

```text
scripts/runtime/wait-runtime-age.sh
```

Purpose: wait until one specific running container reaches a minimum runtime age before an age-conditioned experiment or maintenance action.

Default controls:

- container: `qwen38-flash-next`
- minimum age: `2700` seconds
- polling interval: `30` seconds
- progress report interval: `60` seconds

Example for the 45-minute OrcaRouter aged-predecessor gate:

```bash
./scripts/wait-runtime-age.sh \
  --container qwen38-flash-next \
  --min-age 2700
```

The helper pins both the initial Docker container ID and its `StartedAt` value. It deliberately fails if the container stops, disappears, or is replaced while waiting. It never silently transfers the age requirement to a new runtime.

Successful completion prints `WAIT_RUNTIME_AGE_READY` and exits zero. This means the same runtime observed at waiter start has reached the requested age; it does not imply runtime health or benchmark acceptance. Use `wait-ready.sh` separately when readiness is the condition being tested.

## Selection rule

Use the waiter that matches the condition:

| Condition | Helper |
|---|---|
| Container/API/model must become ready | `./scripts/wait-ready.sh` |
| The same running container must reach a minimum age | `./scripts/wait-runtime-age.sh` |

Do not replace these with repeated inline Python/shell polling in operational instructions. If another recurring wait condition appears, add a named helper and document its identity, success boundary, and replacement/failure behavior here.
