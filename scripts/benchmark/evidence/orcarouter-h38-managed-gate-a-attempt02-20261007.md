# OrcaRouter H38 managed-service Gate A attempt 02 — 2026-10-07

Status: QUALIFICATION BLOCKED — TWO REMAINING NON-HERMETIC SETTINGS TEST CASES

## Provenance

- repository: `kjlee-inlct/qwen3.8-flash-next-dgx-spark`
- branch under qualification: `feat/h38-managed-integration`
- attempted target: `5e7c2023dda11b9de3dba3423acc06c2042948a7`
- installed profile: `orcarouter`
- pre-H38 managed image: `vllm-skinny-tp1:v1`
- installed current release before the attempt: `ff67bab3c94d6992f61b9535836df97f03b9c022`

## Baseline result

The pre-H38 managed runtime was active before qualification.

Baseline decode workload:

- mode: decode
- max tokens: 384
- repeats: 5
- status: PASS
- median decode throughput: `34.7488 tok/s`
- runtime image: `vllm-skinny-tp1:v1`
- managed KV cache: `17179869184` bytes
- served model: `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`

All lifecycle transaction guards were idle before the run.

## Qualification result

The exact target release staged successfully and entered release qualification.
The first host-isolation fix corrected five of the seven failures from attempt 01,
but two `SettingsTransitionTests` still failed:

```text
test_commit_removes_released_installer_owned_config ... FAIL
test_rollback_preserves_installer_owned_config ... FAIL

Ran 536 tests in 30.924s
FAILED (failures=2)
```

Both remaining tests construct their environment manually instead of using
`setup_state()`, so they bypassed the default fake lifecycle setup introduced
after attempt 01. They therefore still remained capable of observing the real
managed host resources during DGX-side release qualification.

## Classification boundary

This remains a qualification-harness isolation defect, not an H38 runtime result.

- `update-release` was not reached;
- the legacy manifest image was not migrated;
- managed H38 was not started;
- determinism/performance/restart/RM host-stability acceptance was not reached.

No managed-H38 PASS or FAIL classification is asserted from this attempt.

## Remediation

Commit `59bc690043f769445ac300ad23c57a1cc415f81c` applies
`setup_fake_resources()` to the two manually constructed owned-config test
fixtures.

Gate A must be restarted from the exact new qualified head after CI passes.
Attempt 02 remains immutable failure evidence.
