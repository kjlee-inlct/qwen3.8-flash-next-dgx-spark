# Actual DGX selected profile-pair synthetic 70/70 — 2026-10-12

## Operator evidence and exact SHA

The operator supplied the complete command output for a guarded fast-forward
of the **actual single DGX Spark** feature checkout and the bounded
`verify-synthetic.sh` test runner.

- Source branch: `feat/h38-managed-integration`
- Prior local HEAD: `02e9c61d90c7f15484b0605dc872bbbb21ec253b`
- Validated local HEAD: **`d2e9a1dc2b9759bc60915f2a7cda7b0cfd9d4914`**
- Git log shows `Updating 02e9c61..d2e9a1d` and `Fast-forward`, not a reset.
- Command included pre-merge clean worktree and branch/remote origin checks,
  verified fetched origin tracking SHA before fast-forward, and verified
  both HEAD and clean worktree after the tests.
- The uploaded console output ends with
  `DGX_PROFILE_PAIR_SYNTHETIC_VALIDATION_COMPLETE`.
- The console is an operator-supplied transcript, **not** a detached,
  independently hashed logfile or remotely executed command by the assistant.

## Selected local synthetic results

| Actual-DGX selected module | Tests | Result |
|---|---:|---|
| `test_uninstall_wizard_preview.py` | 19 | PASS |
| `test_asset_ownership.py` | 7 | PASS |
| `test_operation_lock.py` | 8 | PASS |
| `test_lifecycle_integration.py` | 14 | PASS |
| `test_profile_switch_transition.py` | 10 | PASS |
| `test_selected_profile_readonly.py` | 8 | PASS |
| `test_managed_lifecycle_readonly_snapshot.py` | 4 | PASS |
| **TOTAL** | **70** | **PASS** |

Each module ended `OK`. In particular, the profile-switch test module
exercised all **12 directed ordered pairs** of the four supported profiles
with 3 simulated runtime identity branches per pair (attested commit,
pre-commit rollback, wrong container ID rejection followed by provable old
runtime recovery), plus same-profile/wrong-source refusal and earlier crash
and lock-recovery scenarios. These are subtest branches within ten unittest
methods, not 36 independently enumerated test methods.

Observed source markers:

```text
LOCAL_SYNTHETIC_SCOPE=DISPOSABLE_FIXTURES_ONLY
LOCAL_SYNTHETIC_HEAD=d2e9a1dc2b9759bc60915f2a7cda7b0cfd9d4914
LOCAL_SYNTHETIC_HOST_COMMANDS=PATH_DENY_STUBS
LOCAL_SYNTHETIC_LIVE_E2E=NOT_QUALIFIED
BASH_SYNTAX=PASS
SHELLCHECK=SKIPPED_NOT_INSTALLED
LOCAL_SYNTHETIC_RESULT=PASS
MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED
DGX_PROFILE_PAIR_SYNTHETIC_VALIDATION_COMPLETE
```

This exact source SHA also has independently recorded
[GitHub CI #38204845533](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38204845533)
**SUCCESS**, **796/796 full unit tests**, **70/70 selected synthetic**,
Bash syntax, ShellCheck, Python compilation and whitespace PASS.
**Local ShellCheck did not run because it was not installed**, so
GitHub CI's ShellCheck must not be attributed to the operator DGX.

## Boundaries, unchanged host gates

The synthetic runner uses disposable HOME/XDG/TMPDIR and PATH deny stubs;
that is **not an OS-level isolation or a physical-host lifecycle E2E**.
The transcript does not run live service Doctor or inspect live container
readiness, does not actually switch profiles, and does not start GPU models.
Prior independent historical observations showed selected `orcarouter`,
container EXITED and service INACTIVE following the Oct 7 protective abort
and restored-but-stopped predecessor. Those are **prior observations**,
not a current service snapshot from this log.

```text
DGX_LOCAL_SYNTHETIC=PASS
DGX_LOCAL_SYNTHETIC_SHA=d2e9a1dc2b9759bc60915f2a7cda7b0cfd9d4914
DGX_LOCAL_SYNTHETIC_TESTS=70_OF_70
DGX_LOCAL_SHELLCHECK=SKIPPED_NOT_INSTALLED
GITHUB_SOURCE_CI_38204845533=SUCCESS_796_OF_796
M1_HOST_HEALTH=NOT_QUALIFIED
M2_DESTRUCTIVE_E2E=NOT_RUN
M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED
M4_H38=BLOCKED
CHECKPOINT_METADATA_ORDER_GATE=FAIL
HOST_STABILITY=INCONCLUSIVE
HOST_PROTECTION=UNCHANGED
PR_259=DRAFT_OPEN_UNMERGED
MERGE=BLOCKED
```

No real-world uninstall, live profile switch, model restart, service action,
swap or protection change is authorized by this synthetic acceptance.
Independent disposable-host D0–D5 and real profile-pair E2E remain pending.
