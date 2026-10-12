# Actual DGX Spark 76/76 isolated lifecycle synthetic acceptance and prepare orphan guard — 2026-10-12

## Evidence provenance and exact source

An operator-supplied DGX Spark terminal transcript documents a guarded source synchronization and isolated synthetic verifier execution. This is **operator-provided console evidence**, not an independently signed machine report or a live container/service acceptance.

- Repository: `kjlee-inlct/qwen3.8-flash-next-dgx-spark`
- Branch: `feat/h38-managed-integration`
- Previous DGX source SHA: `e18c56aff008f717ad54ee787ab20c248e987e34`
- Tested DGX source SHA: **`922062436b71353760c2323103e749ed6eaf6240`**
- Synchronization: expected-branch, exact-current-HEAD, clean worktree and origin URL guards; fetch followed by `git merge --ff-only`, then exact target verification
- Verifier: the pinned `verify-synthetic.sh` isolation runner against exact SHA `922062436b71353760c2323103e749ed6eaf6240`
- Explicit markers: `LOCAL_SYNTHETIC_SCOPE=DISPOSABLE_FIXTURES_ONLY`, `LOCAL_SYNTHETIC_HOST_COMMANDS=PATH_DENY_STUBS`, `LOCAL_SYNTHETIC_LIVE_E2E=NOT_QUALIFIED`, `LOCAL_SYNTHETIC_HEAD=922062436b71353760c2323103e749ed6eaf6240`
- Check results: `BASH_SYNTAX=PASS`, **`SHELLCHECK=SKIPPED_NOT_INSTALLED`**, `LOCAL_SYNTHETIC_RESULT=PASS`, `DGX_PROFILE_IDLE_SAFETY_SYNTHETIC_COMPLETE`; final clean tree and exact HEAD printed
- GitHub matching-source CI [#38212708550](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38212708550): **SUCCESS, 802/802 full Python, 76/76 selected synthetic**, Bash/ShellCheck/Python compilation/whitespace PASS

| Selected fixture module | Real DGX method results |
| --- | ---: |
| Uninstall Wizard | 19 PASS |
| Asset Ownership | 7 PASS |
| Operation Lock | 8 PASS |
| Lifecycle Integration | 14 PASS |
| Profile Switch Transition | 16 PASS |
| Selected Profile Readonly | 8 PASS |
| Managed Lifecycle Readonly Snapshot | 4 PASS |
| **Total** | **76/76 PASS** |

The profile-switch module covers the synthetic 12 directed pair cases but this is **not** 12 real live Docker/systemd transitions. The latest actual DGX *isolated synthetic* SHA is now `9220624`, superseding `e18c56a` (73/73) only as the **latest** operator-run test; the prior evidence remains historically valid.

## Subsequent source safety review and targeted change

A follow-up read of the same SHA showed that `recover`, `rollback`, `service-recover` and `status` refuse orphan backup, candidate, transaction `.tmp`, candidate/backup `.tmp`, and commit-complete staging; however `prepare` had checked only published state/backup/candidate and could overwrite or ignore orphan `.tmp` files from an interrupted transaction.

The follow-up patch reuses `assert_no_orphan_profile_switch_artifacts` inside `prepare` **before writing a new transaction**. One new `tests/test_profile_switch_transition.py` fixture method tests six stranded-file types plus a dangling transaction-stage symlink, asserting refusal, artifact preservation, unchanged manifest and absence of a new transaction. This is a new source change *after* DGX `9220624` 76/76. **Its own CI and DGX test results must be recorded separately; it is not included in the observed 76/76 run.**

## Qualification remains deliberately unchanged

```text
ACTUAL_DGX_SYNTHETIC_SHA=922062436b71353760c2323103e749ed6eaf6240
ACTUAL_DGX_SYNTHETIC=PASS_76_OF_76
ACTUAL_DGX_BASH_SYNTAX=PASS
ACTUAL_DGX_SHELLCHECK=SKIPPED_NOT_INSTALLED
ACTUAL_DGX_LIVE_E2E=NOT_QUALIFIED
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

The local verifier's PATH deny stubs are **not an OS-level sandbox**. No live H38 rerun, Docker/systemd lifecycle mutation, service restart, swap or protection change, actual profile-pair E2E or destructive host acceptance is evidenced. Independent D0–D5 host qualification remains NOT_RUN.

## CI correction history

First follow-up source-and-document commit `1da74d081dce72868c6204ef5957391edaab5e73` triggered [CI #38214784763](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38214784763): **FAILED** (803 Python methods executed, 2 documentation/layout assertions failed). The new `prepare` fixture method was not among the failures. Root causes: the established documentation test requires the original `Last synchronized: 2026-10-07` anchor, and benchmark evidence must not reference lifecycle-category paths. The corrective commit restores the original header anchor (without changing the dated new evidence) and references the verifier by basename rather than forbidden cross-category path. The layout tests remain enforced, not disabled. Retest outcome must be recorded separately.

## Corrected follow-up GitHub CI — confirmed

Corrective docs/evidence commit `51e85f6578ee0694a13964f700f30e854f17c020` was verified by [CI #38215072213](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38215072213): **SUCCESS, 803/803 full Python tests and 77/77 bounded synthetic tests** (including 17 profile-switch methods, with the new prepare-orphan test), Bash syntax, ShellCheck, Python compilation and whitespace PASS. First failed CI #38214784763 remains FAIL in the history; neither the first run nor this retest is a real DGX host acceptance. Actual DGX test remains `9220624` 76/76; the source after that run is GitHub-only qualified.
