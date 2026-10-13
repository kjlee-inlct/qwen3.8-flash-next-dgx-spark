# OrcaRouter H38 managed-service Gate A attempt 01 — 2026-10-07

Status: QUALIFICATION BLOCKED — UNIT-TEST HOST-ISOLATION DEFECT

## Provenance

- repository: `kjlee-inlct/qwen3.8-flash-next-dgx-spark`
- branch under qualification: `feat/h38-managed-integration`
- attempted target: `a8af8a0f0b18a7854891b7b5af451f75d351e07a`
- installed profile: `orcarouter`
- pre-H38 managed image: `vllm-skinny-tp1:v1`
- installed current release before the attempt: `ff67bab3c94d6992f61b9535836df97f03b9c022`

## Baseline result

The pre-H38 managed runtime was active and healthy before qualification.

Baseline decode workload:

- mode: decode
- max tokens: 384
- repeats: 5
- status: PASS
- median decode throughput: `34.6357 tok/s`
- runtime image: `vllm-skinny-tp1:v1`
- managed KV cache: `17179869184` bytes
- served model: `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`

The target release staged successfully and the exact release manifest was verified.

## Blocking failure

The live qualification step stopped in the repository unit-test suite before
`update-release` was executed.

Result:

```text
Ran 536 tests in 29.707s
FAILED (failures=7)
```

All seven failures were in `tests/test_settings_transition.py`. The common failure was:

```text
FATAL: managed proxy resources exist but the live manifest does not own them
```

The affected tests used temporary HOME/XDG state and temporary manifests, but the
default lifecycle helpers still resolved to the real host's `manage-proxy.sh`,
`manage-service.sh`, `systemctl`, and `docker`. On the installed DGX host, the
real managed proxy/service/container existed; on the clean GitHub Actions runner they
did not. The unit-test fixture was therefore host-state-dependent.

This is a qualification-harness isolation defect, not an H38 runtime result.

## Classification boundary

This attempt does **not** establish any managed-H38 functional, determinism,
performance, restart, or host-stability result.

In particular:

- `update-release` was not reached;
- the legacy manifest image was not intentionally migrated to H38;
- the managed H38 runtime was not started by this attempt;
- the H38 determinism matrix was not run;
- the H38 performance comparison was not run;
- the strict NVIDIA RM host-stability gate was not reached.

The baseline legacy runtime result remains valid only as the pre-migration control.

## Remediation

Commit `d849c335593b8c87f4df7650e3a6d1b6301c24ad` changes the
`SettingsTransitionTests` fixture so external lifecycle dependencies are fake and
hermetic by default. The fake-resource setup is idempotent so tests that explicitly
exercise proxy/service resource transitions can reuse the same isolated harness.

Gate A must be restarted from the exact new qualified head after repository CI passes.
This attempt remains canonical failure evidence and must not be rewritten after retry.
