# H38 MTP startup discriminator plan — 2026-10-07

Status: IMPLEMENTED / STATIC CI PENDING / LIVE NOT RUN

## Purpose

The first atomic managed-H38 migration reached the intended decoder-scope H38
candidate but memory protection stopped it before READY. Recovered monitor samples
showed high reclaimable non-CMA available memory, low immediately-free non-CMA
memory, and active swap growth. That signal collides with a known cold-load monitor
false-positive family.

That collision does **not** justify weakening the monitor. Canonical R22 evidence
already proves that a v0.29 PLE-mmap OrcaRouter runtime with the same 16 GiB KV
setting can reach READY and still record a strict NVIDIA RM
`_memdescAllocInternal / NV_ERR_NO_MEMORY` event.

The failed H38 candidate log also places the protection interval near a later
checkpoint-loading phase. Existing normal MTP startup evidence shows a second
safetensors loading pass followed by Qwen3.8 MTP speculator initialization. MTP
materialization is therefore a higher-information next variable than changing host
protection thresholds.

## Single-variable experiment

Runner:

`scripts/benchmark/run-h38-mtp-startup-discriminator.sh`

The runner requires the recovered post-protection managed state to remain unchanged:

- lifecycle transactions idle;
- managed service inactive;
- restored predecessor canonical container present but stopped;
- no rollback container;
- no active API on port 8888.

It never cold-starts the restored legacy runtime.

The isolated candidate preserves:

- image `vllm-orcarouter-v029-h38-decoder-scope:v1`;
- label `qwen38.h38scope=decoder-v1`;
- OrcaRouter checkpoint and served alias;
- PLE mmap;
- exact QSA;
- Marlin canonical order with decoder scope;
- 16 GiB KV;
- max model length 262144;
- max sequences 3;
- prefix cache disabled;
- standard 6 / 2 / 10 / 8 GiB monitor thresholds;
- 256 MiB swap-growth arm;
- five consecutive protection samples;
- `--protect`;
- strict kernel RM classification.

The only intended runtime variable is:

```text
production target: SPEC=mtp, k=2
discriminator:     SPEC=none
```

The experiment uses a distinct container, removes it on completion, and leaves the
managed predecessor in its original stopped state. It does not call `install.sh`,
`update-release.sh`, or mutate managed manifest/release pointers.

## Classification

- `VALID_CLEAN`: SPEC=none reaches exact model READY, Docker OOM is false,
  protection does not intervene, the kernel evidence window is valid, and no strict
  RM OOM appears. This supports MTP startup materialization as the next pressure
  discriminator. It does **not** qualify SPEC=none for production.
- `PROTECTED_STOP`: unchanged protection also stops SPEC=none. MTP is not
  sufficient to explain the startup event.
- `FUNCTIONAL_PASS_HOST_FAIL`: SPEC=none reaches READY but strict RM OOM occurs.
- `FUNCTIONAL_NOT_REACHED_HOST_FAIL`: strict RM OOM occurs before READY.
- anything else: INVALID / no causal claim.

Managed H38 promotion remains blocked until the original MTP k=2 managed target passes
migration FUNCTIONAL/HOST-STABILITY, determinism, performance, and managed
restart/attestation gates.
