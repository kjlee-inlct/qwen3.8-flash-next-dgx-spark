# Actual DGX Spark 77/77 prepare-orphan isolated synthetic PASS — 2026-10-12

## Provenance

An operator-supplied DGX Spark console log of an exact-commit synchronization and bounded local synthetic test is the source of this record. It is **operator-provided evidence**, not a signed independent report and not a live managed runtime qualification.

- Repository: `kjlee-inlct/qwen3.8-flash-next-dgx-spark`
- Branch: `feat/h38-managed-integration`
- Previous verified local SHA: `922062436b71353760c2323103e749ed6eaf6240` (76/76 isolated synthetic)
- New **actual DGX locally tested SHA**: `1283b1a9252f1ff53d51659049ca42f9449e5ccd`
- Git synchronization: `9220624..1283b1a` recorded as `Fast-forward` with 10 files changed (167 insertions, 2 deletions)
- Preceding operator command employed branch, origin, clean worktree, exact-SHA and final marker guards; the transcript records the downstream successful completion marker and exact final HEAD
- Synthetic-only verifier: `verify-synthetic.sh` at the exact source SHA
- `LOCAL_SYNTHETIC_SCOPE=DISPOSABLE_FIXTURES_ONLY`
- `LOCAL_SYNTHETIC_HOST_COMMANDS=PATH_DENY_STUBS`
- `LOCAL_SYNTHETIC_LIVE_E2E=NOT_QUALIFIED`
- `BASH_SYNTAX=PASS`
- `SHELLCHECK=SKIPPED_NOT_INSTALLED` on DGX (not a local ShellCheck pass)

## Actual DGX results

| Selected fixture module | Passed methods |
| --- | ---: |
| Uninstall Wizard Preview | 19/19 |
| Asset Ownership | 7/7 |
| Operation Lock | 8/8 |
| Lifecycle Integration | 14/14 |
| Profile Switch Transition | **17/17** |
| Selected Profile Readonly | 8/8 |
| Managed Lifecycle Readonly Snapshot | 4/4 |
| **Total actual DGX isolated synthetic** | **77/77** |

The newly added `test_prepare_refuses_orphans_before_new_transaction` was included and passed. It checks fail-closed admission with residual profile-switch backup/candidate/temporary files and a dangling staged state link without allowing a fresh transaction to overwrite the artifacts. Other tests check the mocked 12 directed profile pair combinations, **not** 12 actual host profile changes.

The operator-provided terminal transcript ended with:

```text
LOCAL_SYNTHETIC_RESULT=PASS
LOCAL_SYNTHETIC_HEAD=1283b1a9252f1ff53d51659049ca42f9449e5ccd
MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED
DGX_PREPARE_ORPHAN_SYNTHETIC_COMPLETE
HEAD=1283b1a9252f1ff53d51659049ca42f9449e5ccd
```

Separately, the exact previously tested source [GitHub Actions CI #38215504822](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38215504822) completed **SUCCESS: 803/803 full Python tests, 77/77 selected isolated synthetic**, Bash syntax, ShellCheck, Python compile and whitespace PASS. The CI ShellCheck result does **not** imply local ShellCheck installation on the DGX.

## Scope and continuing gates

```text
ACTUAL_DGX_SYNTHETIC_SHA=1283b1a9252f1ff53d51659049ca42f9449e5ccd
ACTUAL_DGX_SYNTHETIC=PASS_77_OF_77
ACTUAL_DGX_PROFILE_SWITCH_FIXTURES=PASS_17_OF_17
ACTUAL_DGX_BASH_SYNTAX=PASS
ACTUAL_DGX_SHELLCHECK=SKIPPED_NOT_INSTALLED
GITHUB_CI_38215504822=SUCCESS_803_FULL_77_SYNTHETIC
DGX_LOCAL_LIVE_E2E=NOT_QUALIFIED
M1_HOST_HEALTH=NOT_QUALIFIED
M2_DESTRUCTIVE_E2E=NOT_RUN
M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED
M4_H38=BLOCKED
CHECKPOINT_METADATA_ORDER_GATE=FAIL
HOST_STABILITY=INCONCLUSIVE
HOST_PROTECTION=UNCHANGED
PR_259=DRAFT_OPEN_UNMERGED
READY_FOR_REVIEW=BLOCKED
MERGE=BLOCKED
```

No live Docker/systemd transition, model/GPU startup, checkpoint reload, service restart, swap/protection adjustment, destructive install or uninstall is included. PATH command-deny stubs are **not** an OS-level sandbox. The previous October 7 memory-protected H38 abort remains unresolved as to model/kernel/driver root cause; this synthetic success does not reopen that experiment or qualify the host.

Earlier [DGX 76 and prepare-guard source evidence](dgx-76-and-prepare-orphan-guard-20261012.md) remains historically valid. This new 77/77 actual-DGX evidence supersedes its **latest local synthetic checkout** statement only. This documentation commit is newer than the local tested source SHA and needs a separate GitHub CI result.
