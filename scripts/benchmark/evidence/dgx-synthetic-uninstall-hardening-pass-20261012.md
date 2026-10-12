# DGX synthetic lifecycle verification — actual operator pass (2026-10-12)

## Provenance and scope

Actual DGX Spark terminal transcript provided by the operator after the guarded
Git synchronization and synthetic-only verifier. The original transcript is
available in the conversation attachment, but its bytes were **not**
independently retrieved or SHA256-hashed inside GitHub. This record transcribes
the operator-provided output; it is **not** a managed-runtime startup, service
Doctor, full installation/removal, or destructive E2E test.

- Repository: `kjlee-inlct/qwen3.8-flash-next-dgx-spark`.
- Branch: `feat/h38-managed-integration`.
- Exact DGX checkout: `02e9c61d90c7f15484b0605dc872bbbb21ec253b`.
- Previous DGX checkout: `87fb463984683f75435302eff5ffc3b3b9f941bf`.
- Git output: `Updating 87fb463..02e9c61`, `Fast-forward`;
  no reset, dirty worktree, or branch switch.
- Operator command performed **exact-SHA verification before/after**
  the synthetic verifier and printed `DGX_SYNTHETIC_VALIDATION_COMPLETE`.
- Runner reports `LOCAL_SYNTHETIC_SCOPE=DISPOSABLE_FIXTURES_ONLY`,
  `LOCAL_SYNTHETIC_HOST_COMMANDS=PATH_DENY_STUBS`, `BASH_SYNTAX=PASS`,
  `SHELLCHECK=SKIPPED_NOT_INSTALLED` (ShellCheck was independently PASS in
  GitHub CI at this same SHA), and
  `LOCAL_SYNTHETIC_LIVE_E2E=NOT_QUALIFIED`.

## Executed test modules and outcomes

| Synthetic module | Passed | Failed |
|---|---:|---:|
| `test_uninstall_wizard_preview.py` | 19 | 0 |
| `test_asset_ownership.py` | 7 | 0 |
| `test_operation_lock.py` | 8 | 0 |
| `test_lifecycle_integration.py` | 14 | 0 |
| `test_selected_profile_readonly.py` | 8 | 0 |
| `test_managed_lifecycle_readonly_snapshot.py` | 4 | 0 |
| **TOTAL** | **60** | **0** |

All suites ended with `OK`. New fail-closed coverage explicitly exercised
nonzero partial ownership-plan output, partial external-container listing,
Docker image-inspection daemon failure, and retained/owned asset recovery.
The transcript reports:

```text
LOCAL_SYNTHETIC_RESULT=PASS
LOCAL_SYNTHETIC_HEAD=02e9c61d90c7f15484b0605dc872bbbb21ec253b
MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED
DGX_SYNTHETIC_VALIDATION_COMPLETE
```

**Separation of evidence:**
[GitHub Actions #38197243631](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38197243631)
previously reported **SUCCESS** at this exact feature-branch source with
**792/792 full Python tests** and **60/60 allowlisted synthetic tests**, plus
Bash syntax, ShellCheck, Python compile and whitespace PASS.
The **DGX result is narrower**: exact clean checkout, Bash syntax and
60 selected synthetic tests; no local ShellCheck installation. Neither
CI nor local synthetic execution tests host-level Docker teardown.

## Non-qualification and next priority

This operator output does **not** re-inspect the actual selected profile,
Docker container/service state or monitor status. Prior real read-only
observation found `SELECTED_PROFILE=orcarouter`,
`CONTAINER_STATE=EXITED`, `SERVICE_STATE=INACTIVE`, consistent with
the archived October 7 protected candidate abort and stopped predecessor
rollback. The new tests did not start or change them.

```text
DGX_LOCAL_SYNTHETIC=PASS
DGX_LOCAL_SYNTHETIC_SHA=02e9c61d90c7f15484b0605dc872bbbb21ec253b
DGX_LOCAL_SYNTHETIC_TESTS=60_OF_60
DGX_LOCAL_SHELLCHECK=SKIPPED_NOT_INSTALLED
CI_SHELLCHECK=PASS
M1_HOST_HEALTH=NOT_QUALIFIED
M2_DESTRUCTIVE_E2E=NOT_RUN
M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED
M4_H38=BLOCKED
CHECKPOINT_METADATA_ORDER_GATE=FAIL
HOST_STABILITY=INCONCLUSIVE
HOST_PROTECTION=UNCHANGED
PR_259=DRAFT_OPEN
MERGE=BLOCKED
```

Maintain strict host protection. The next substantive acceptance work is
isolated profile-switch/install/uninstall fault-injection coverage and the
D0–D5 plan on an **independent disposable host**. No active Spark
install/uninstall, container restart, swap/protection adjustment or
model/GPU rerun is authorized by this result. PATH deny stubs are **not**
privileged sandbox enforcement, and cannot substitute for actual isolation.
