# H38 MTP startup discriminator attempt 02 — 2026-10-08

Status: SETUP INVALID / NO CANDIDATE START / NO CAUSAL CLAIM

## Invocation

- branch: `feat/h38-managed-integration`
- exact checkout: `d5fa3dfe41ae6305a719201cea5798c9c6ae54cf`
- explicit evidence target:
  `/tmp/orcarouter-h38-mtp-none-attempt02-20261007T223234Z`
- runner return code: `1`

The runner emitted no discriminator banner, no harness error, and no evidence summary.
That proves it exited before `OUT_READY=1` and before candidate startup.

## Root cause

`assert_post_protection_baseline()` ended with:

```bash
docker inspect "${EXPERIMENT_CONTAINER}" >/dev/null 2>&1 &&
  fail "experiment container already exists: ${EXPERIMENT_CONTAINER}"
```

The experiment container being absent is the required clean baseline. In that state
`docker inspect` returns 1. Because the AND-list was the function's final command,
the function returned 1 even though every baseline condition was valid. The caller is
a simple command under top-level `set -e`, so the shell exited immediately and
silently before acquiring the experiment lock or creating the evidence directory.

## Correction

Both negative Docker-existence checks now use explicit conditionals:

```bash
if docker inspect ...; then
  fail ...
fi
```

The baseline function also ends with explicit `return 0`, making the success contract
independent of the status of its final predicate.

A regression assertion requires the explicit guards and successful return.

## Classification

- experiment lock: NOT REACHED
- evidence directory: NOT CREATED
- candidate start: NOT REACHED
- FUNCTIONAL: NOT REACHED
- HOST-STABILITY: NOT MEASURED
- protection: NOT EXERCISED
- strict RM window: NOT STARTED
- MTP causal claim: NONE

This attempt is harness-only evidence and does not change managed-H38 acceptance.
