# Actual DGX 134 local synthetic PASS and B1 selected-profile snapshot (2026-10-13)

**Evidence class: user-supplied physical-DGX terminal transcript, not independent host attestation.** Source command output does not include a reliable execution timestamp. No host command was initiated through GitHub.

## Exact-source local test

- User checked a clean repository and canonical HTTPS origin, then fetched and clean-fast-forwarded the feature branch from `1283b1a` to `b35d0f3d7840d00c55f4c633813e88ac367c6373`.
- Explicit SHA and clean-worktree assertions succeeded before the bounded verifier.
- `LOCAL_SYNTHETIC_ORIGIN=CANONICAL_GITHUB_REPOSITORY`, `LOCAL_SYNTHETIC_HEAD=b35d0f3d7840d00c55f4c633813e88ac367c6373`, `LOCAL_SYNTHETIC_SCOPE=DISPOSABLE_FIXTURES_ONLY`, `LOCAL_SYNTHETIC_HOST_COMMANDS=PATH_DENY_STUBS`.
- `BASH_SYNTAX=PASS`, `SHELLCHECK=SKIPPED_NOT_INSTALLED`, `LOCAL_SYNTHETIC_RESULT=PASS`.
- Eleven test modules passed: 19 uninstall, 7 ownership, 8 lock, 14 lifecycle, 17 switch, 8 selected-profile, 4 lifecycle snapshot, 10 D0 preflight, 22 D0 fake-host, 10 D0 receipt, 15 D0 external evidence = **134/134 PASS**.
- Same-source [GitHub CI #38320095401](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38320095401) SUCCESS 863/863 full and 134/134 selected, including ShellCheck. This does not replace the actual local evidence.

## Actual DGX B1 (normal operator HOME, read-only)

After the test run, the operator ran the selected-profile inspector and observed:

```text
MANIFEST_STATUS=VALID
INSTALL_PHASE=complete
SELECTED_PROFILE=orcarouter
RECORDED_PROFILE=orcarouter
EXPECTED_IMAGE=vllm-skinny-tp1:v1
MONITOR_PROTECT=1
MONITOR_ENABLED=1
MODEL_PATH_STATUS=MARKER_PRESENT_NOT_VERIFIED
PROFILE_SWITCH_STATE=IDLE
RUNTIME_TRANSITION_STATE=IDLE
UPDATE_STATE=IDLE
RELEASE_PROFILE_REFRESH_STATE=IDLE
STALE_TRANSACTION_ARTIFACTS=NONE
CONTAINER_STATE=EXITED
SERVICE_STATE=INACTIVE
RUNTIME_ATTESTATION=MISSING
RUNTIME_CONFIGURATION=NOT_APPLICABLE
PROFILE_STATUS_SUMMARY=CONTAINER_NOT_RUNNING
ACTUAL_SERVED_PROFILE=NOT_VERIFIED
HOST_HEALTH_QUALIFICATION=NOT_ESTABLISHED_BY_THIS_SNAPSHOT
```

The recorded OrcaRouter model and the container configuration aligned as strings. No model load, API readiness, live served identity, full Doctor, RM stability or restart was tested. Container EXITED / service INACTIVE are an **observed stopped baseline**, not an M1 PASS or a reason to auto-restart. Model marker presence is not proof of checkpoint integrity.

## New single-owner qualification policy

The DGX owner reports being its sole human user and accepting testing at any time. This removes conflicts with other human users but does not prove Docker exclusivity, data recoverability or permission for irreversible deletion. Bounded, reversible owner-approved tests on the one DGX can be considered after B2 read-only Doctor and backup/rollback review; a separate physical DGX is not a categorical precondition for **every** real runtime experiment.

Independently disposable-host D0 and destructive D1-D5 E2E remain NOT_QUALIFIED and NOT_RUN. Using the sole physical DGX cannot substitute for a recoverable disposable environment. Purges, swap removal, filesystem reinitialization and uncontrolled H38 memory experiments require separately scoped explicit approval plus verifiable recovery and stop conditions.

## Immediate next step on the already-tested checkout

Run the **full read-only lifecycle inspector** using the exact SHA from this evidence. The executable command belongs in the operator-facing `docs/DGX-STAGED-VALIDATION.md` runbook; keep benchmark evidence free of references to other script categories. No new Git sync is required to inspect the operator's existing checked-out SHA.

The inspector only collects state/Doctor; partial inspection exit code 3 must not trigger repair. Subsequent live OrcaRouter or H38 actions require separate decision after B2 review.

```text
ACTUAL_DGX_STAGE_A=PASS_134_AT_B35D0F3
ACTUAL_DGX_STAGE_B1=READONLY_COLLECTED
ACTUAL_DGX_STAGE_B2=NOT_RUN
CONTAINER_STATE=EXITED
SERVICE_STATE=INACTIVE
RUNTIME_ATTESTATION=MISSING
MONITOR_PROTECT=1
MONITOR_ENABLED=1
D0_INDEPENDENT_DISPOSABLE_ADMISSION=NOT_GRANTED
D1_D5_INDEPENDENT_E2E=NOT_RUN
M1_HOST_HEALTH=NOT_QUALIFIED
M2_DESTRUCTIVE_E2E=NOT_RUN
M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED
M4_H38=BLOCKED
CHECKPOINT_METADATA_ORDER_GATE=FAIL
HOST_STABILITY=INCONCLUSIVE
HOST_PROTECTION=UNCHANGED
PR_259=DRAFT_OPEN_UNMERGED
```


## CI failure and narrow documentation correction (2026-10-13)

Initial docs SHA `c280ef0e62a2b0fd39097c6d57c8a8a8ed2d7399`, [CI #38322282587](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38322282587), **FAILED 1 full Python test** (`test_script_layout.ScriptLayoutTests.test_canonical_category_dependencies_follow_allowed_directions`) because this benchmark Evidence contained a cross-category executable path. The remedy only relocates the command text to the existing operator runbook; it does **not** alter the DGX 134 PASS, B1 observations, any runtime code, protections or gate classification. The corrected documentation HEAD must have a separately verified successful CI before being called green.
