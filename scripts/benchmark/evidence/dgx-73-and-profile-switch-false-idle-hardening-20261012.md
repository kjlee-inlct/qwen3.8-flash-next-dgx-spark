# Latest actual DGX 73/73 and fail-closed orphan-state synthetic CI — 2026-10-12

## Provenance and exact branches

The operator submitted the full console transcript for their actual single
DGX Spark. A guarded clean Git fast-forward updated
`feat/h38-managed-integration` from
`fb6e0ed4075ac5fa8a3142137d068eb98d65e4bf` to
**`e18c56aff008f717ad54ee787ab20c248e987e34`**, then ran the
isolated exact-SHA lifecycle verifier. Transcript began with fetch and
`Updating fb6e0ed..e18c56a` / `Fast-forward`, and ended with
`LOCAL_SYNTHETIC_RESULT=PASS`,
`LOCAL_SYNTHETIC_HEAD=e18c56aff008f717ad54ee787ab20c248e987e34`
and `DGX_PROFILE_RECOVERY_SYNTHETIC_VALIDATION_COMPLETE`.
The user-provided transcript does **not** carry an independent SHA256
or a hosted, independently executed run artifact.

The operator's local test counts are:

| Selected synthetic module | Passed |
|---|---:|
| `test_uninstall_wizard_preview.py` | 19 |
| `test_asset_ownership.py` | 7 |
| `test_operation_lock.py` | 8 |
| `test_lifecycle_integration.py` | 14 |
| `test_profile_switch_transition.py` | 13 |
| `test_selected_profile_readonly.py` | 8 |
| `test_managed_lifecycle_readonly_snapshot.py` | 4 |
| **TOTAL on actual DGX** | **73/73** |

Local markers: `LOCAL_SYNTHETIC_SCOPE=DISPOSABLE_FIXTURES_ONLY`,
`LOCAL_SYNTHETIC_HOST_COMMANDS=PATH_DENY_STUBS`,
`LOCAL_SYNTHETIC_LIVE_E2E=NOT_QUALIFIED`,
`BASH_SYNTAX=PASS`, **`SHELLCHECK=SKIPPED_NOT_INSTALLED`**,
`MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED`. These commands do
not attest a live running service or qualify model health.
At this exact SHA, [GitHub CI #38211338927](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38211338927)
separately completed **799/799 full Python tests and 73/73 selected
synthetic**, including ShellCheck in GitHub (not installed locally).

## Newly identified source safety boundary: false-idle after crash

After receipt of the operator evidence, source review found the
profile-switch Bash transaction controller sometimes treated dangling
symlinks or orphaned backup, candidate or staged temporary files as
an absent transition. In particular, previously `service-recover`
immediately returned success when the transaction file did not exist,
without checking residual candidate/backup files. Likewise
`rollback`, `recover` and `status` could report idle under
certain stranded or dangling-file conditions.

Commit [`7fd50c07`](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/commit/7fd50c07f76bf8b2b1df5f334cb9951d5c8849c5)
**changes production Bash fail-closed idle checks only**:

- Shared state-presence check treats both existing files and dangling
  symbolic links as **present**.
- No-state paths check orphan transaction `.tmp`, candidate/backup
  files and their `.tmp` files, plus the interrupted commit-complete
  temporary manifest. Both existing and dangling symlinks are treated
  as unsafe remnants.
- `rollback`, `recover`, `service-recover` and read-only
  `status` all refuse a misleading idle state when such remnants exist.
- Valid truly idle conditions still return success. Active transition
  phase semantics and live-model execution were not changed.

Three added `test_profile_switch_transition.py` unittest methods
cover valid empty idle, six orphan filename categories × four idle-like
actions, and dangling transaction/candidate symlinks × the four actions.
The profile-switch module grows from 13 to **16 methods**. New
source-commit [CI #38212223945](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38212223945)
completed **SUCCESS 802/802 full tests, 76/76 bounded synthetic tests**,
plus Bash syntax, ShellCheck, Python compile and whitespace PASS.
Selected module breakdown: 19 + 7 + 8 + 14 + **16** + 8 + 4
= **76 tests**. No on-DGX run of this new source has yet been
provided.

## Persistent gate separation

```text
ACTUAL_DGX_LOCAL_SYNTHETIC_SHA=e18c56aff008f717ad54ee787ab20c248e987e34
ACTUAL_DGX_LOCAL_SYNTHETIC=PASS_73_OF_73
ACTUAL_DGX_LOCAL_SHELLCHECK=SKIPPED_NOT_INSTALLED
GITHUB_NEW_SOURCE_CI_38212223945=SUCCESS_802_FULL_76_SYNTHETIC
GITHUB_NEW_SOURCE_ACTUAL_DGX_LOCAL_TEST=NOT_RUN
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

No real Docker/service restart or GPU model execution, profile switch,
swap adjustment, destructive asset deletion or monitor/protect changes.
A PATH-deny stub is not a privileged operating-system sandbox.
The previous protected H38 runtime abort and stopped original container
remain historical read-only observations, not replaced by this output.
M2 D0–D5 independent disposable-host live E2E and M3 real pairwise
service qualification remain NOT_RUN or NOT_QUALIFIED.
