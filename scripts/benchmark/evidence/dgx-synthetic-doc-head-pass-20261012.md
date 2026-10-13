# DGX latest exact-SHA documentation-head synthetic verification — 2026-10-12

## Actual operator-supplied terminal evidence

The user provided terminal output after the prior fetch-only SHA mismatch
was corrected. The real DGX checkout performed a clean, exact-SHA
fast-forward from `d2e9a1dc2b9759bc60915f2a7cda7b0cfd9d4914`
to **`fb6e0ed4075ac5fa8a3142137d068eb98d65e4bf`**.
The resulting change was **five evidence/documentation files**:
`OPERATIONS.md`, `docs/CURRENT-STATUS.md`,
`docs/MANAGED-LIFECYCLE-ACCEPTANCE.md`, the benchmark evidence index
and a prior actual-DGX synthetic record; no runtime code was changed in
this fast-forward.

The operator invoked the exact-SHA isolated synthetic verifier. The
terminal output reports all seven selected modules `OK`:

| Module | Local count | Status |
|---|---:|---|
| `test_uninstall_wizard_preview.py` | 19 | PASS |
| `test_asset_ownership.py` | 7 | PASS |
| `test_operation_lock.py` | 8 | PASS |
| `test_lifecycle_integration.py` | 14 | PASS |
| `test_profile_switch_transition.py` | 10 | PASS |
| `test_selected_profile_readonly.py` | 8 | PASS |
| `test_managed_lifecycle_readonly_snapshot.py` | 4 | PASS |
| **Total** | **70** | **PASS** |

The terminal confirmed `LOCAL_SYNTHETIC_SCOPE=DISPOSABLE_FIXTURES_ONLY`,
`LOCAL_SYNTHETIC_HOST_COMMANDS=PATH_DENY_STUBS`,
`LOCAL_SYNTHETIC_HEAD=fb6e0ed4075ac5fa8a3142137d068eb98d65e4bf`,
`BASH_SYNTAX=PASS`, `SHELLCHECK=SKIPPED_NOT_INSTALLED`,
`LOCAL_SYNTHETIC_RESULT=PASS`,
`MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED`, and the
final `DGX_SYNTHETIC_VALIDATION_COMPLETE`, followed by
`HEAD=fb6e0ed4075ac5fa8a3142137d068eb98d65e4bf`.
Pre-run safety checks and post-run exact SHA and clean-worktree checks
completed without exiting early.

The console log is operator-provided; it was not independently signed,
hashed or executed from the GitHub connector. GitHub
[CI #38207710548](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38207710548)
independently passed **796/796 full Python tests and 70/70 synthetic
tests** at this exact SHA, including ShellCheck. **Local ShellCheck
was not executed**.

## Interpretation

```text
DGX_LOCAL_SYNTHETIC=PASS
DGX_LOCAL_SYNTHETIC_SHA=fb6e0ed4075ac5fa8a3142137d068eb98d65e4bf
DGX_LOCAL_SYNTHETIC_TESTS=70_OF_70
DGX_LOCAL_SHELLCHECK=SKIPPED_NOT_INSTALLED
GITHUB_38207710548=SUCCESS_796_FULL_70_SYNTHETIC
M1_HOST_HEALTH=NOT_QUALIFIED
M2_DESTRUCTIVE_E2E=NOT_RUN
M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED
M4_H38=BLOCKED
CHECKPOINT_METADATA_ORDER_GATE=FAIL
HOST_STABILITY=INCONCLUSIVE
HOST_PROTECTION=UNCHANGED
PR_259=DRAFT_OPEN_UNMERGED
```

No new running runtime, service state, GPU model, Docker image deletion,
protected memory or systemd interaction was verified or mutated. The
October 7 original protection abort and stopped-predecessor observation
remain **historical**, not a fresh service-state snapshot. PATH command
stubs are **not privileged host isolation**. Do not conflate this latest
local 70/70 with newer GitHub-only fault tests.
