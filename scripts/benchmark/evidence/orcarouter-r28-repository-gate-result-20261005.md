# OrcaRouter R28 — repository implementation gate result — 2026-10-05

## Status

**CLOSED / PASS — R28 IMPLEMENTATION CI GREEN — STATIC DGX IMAGE GATE NEXT — NO LIVE RUN AUTHORIZED**

R28 follows the completed R27 H6 routing closure and narrows the next allocator discriminator to `UnquantizedLinearMethod.create_weights()` only.

## Repository contents

Implemented files:

- `scripts/patch-v029-r28-unquant-linear-markers.py`
- `scripts/Dockerfile.v029-r28-unquant-linear-markers`
- `scripts/benchmark/check-orcarouter-r28-unquant-linear-image.sh`
- `scripts/benchmark/analyze-orcarouter-r28-unquant-linear-overlap.py`
- `scripts/benchmark/run-orcarouter-r28-unquant-linear-boundary.sh`
- `tests/test_orcarouter_r28_unquant_linear_markers.py`
- `tests/test_orcarouter_r28_unquant_linear_overlap.py`
- `scripts/benchmark/evidence/orcarouter-r28-unquant-linear-boundary-plan-20261005.md`

## CI

Implementation head `496eaadb9fc56e268bcfcb080be6a45879709ba4` passed CI #1141.

The subsequent documentation-status head `225c9719aec6910de975c867d0a28c6549ae772b` also passed CI #1142 with **SUCCESS**.

Validated steps include:

- shell syntax: PASS;
- ShellCheck: PASS;
- Python compile: PASS;
- full unit tests: PASS;
- whitespace checks: PASS.

This evidence document was added after those checks and changes no R28 executable code or test semantics.

## Gate closure

Repository implementation is closed PASS. This result does not make a live functional or host-stability claim.

Next permitted action is DGX static work only:

1. fast-forward the branch to the current remote head;
2. verify that the checked-out head contains tested head `225c9719aec6910de975c867d0a28c6549ae772b` as an ancestor;
3. build `vllm-orcarouter-v029-r28-unquant-linear-marker:v1` from the already validated R27 image;
4. run `check-orcarouter-r28-unquant-linear-image.sh`;
5. prove managed container ID / StartedAt and exact OrcaRouter model identity unchanged;
6. run the guarded R28 harness in `--preflight` mode only;
7. canonicalize those gates before considering one live measurement.

No live R28 run is authorized by this document. H11 remains deferred.

PR #244 remains open. No merge is implied or authorized.
