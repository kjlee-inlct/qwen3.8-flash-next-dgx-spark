# Profile-switch manifest and runtime-attestation fault injection — 2026-10-12

## Provenance

GitHub-only isolated fixture regressions added in commit
[`8538c83`](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/commit/8538c83cf36ae89d9815dd374fcf2836c97b7bf5).
The **production profile-switch implementation is unchanged**.
The Python tests invoke its Bash entry point against disposable HOME/XDG
manifests and a fake Docker identity-probe executable. This is not a
real service switch or destructive E2E acceptance.

## New crash, drift and missing-evidence boundaries

| Test | Injection | Required result |
|---|---|---|
| `test_modified_backup_manifest_refuses_rollback_and_preserves_transaction` | Change `UI_LANG=en` to `UI_LANG=ko` in an activated, SHA-recorded **backup**; fake predecessor Docker identity otherwise still matches | Rollback fails with backup digest mismatch; activated live bytes, candidate bytes, transaction state preserved for diagnosis |
| `test_candidate_drift_blocks_commit_before_rollback_recovery` | Change `UI_LANG` in SHA-recorded target **candidate** after activation, with otherwise valid fake target identity and runtime attestation | Target `runtime-committed` refused; activated state remains; fake-provable original container permits exact-source rollback |
| `test_missing_attestation_after_runtime_committed_blocks_finalization` | First mark valid target runtime committed, then remove the runtime commit file | `recover` refuses target finalization without current proof and retains manifest/backup/candidate/transaction; fixture restores valid attestation and `recover` finishes safely |

The selected profile-switch module rose from **10 to 13 unittest
methods**. Existing **12 directed pair × three transaction branch**
subtests remain intact. The exact-SHA synthetic verifier therefore
executes **19 uninstall + 7 asset + 8 lock + 14 lifecycle + 13 profile
switch + 8 selected-profile + 4 read-only snapshot = 73** methods.

[Source-commit CI #38210907792](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38210907792):
**SUCCESS; 799/799 full Python unittest suite, 73/73 selected synthetic
tests**, Bash syntax, ShellCheck, Python compile and whitespace PASS.
All results are GitHub CI only; **the last operator-observed real DGX
local synthetic run is 70/70 at `fb6e0ed`**, not this code commit.

## Continuing restrictions

The tests cover intentional single-process state-file corruption and
attestation loss under temporary fixtures, not real filesystem power
durability, Docker races, kernel memory pressure, actual service lock
identity or power-cut recovery. A block on missing proof is a safety
assertion, **not successful completion**. D0–D5 independent disposable
host acceptance remains NOT_RUN, actual M3 4-profile all-pairs remains
NOT_QUALIFIED, and M1/M4 remain blocked or unqualified.
No live test on the sole DGX is authorized. PR #259 stays Draft/Open.
