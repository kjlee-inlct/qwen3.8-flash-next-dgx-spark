# DGX Spark M1 journal reconcile — physical operator evidence (2026-10-14)

## Provenance

- **Source:** actual operator-transcribed DGX Shell / Wizard results at 2026-10-14 ~13:40 KST.
- **Checked out commit:** `4776a6118decabc7cb511e4e60e7b157d3a57bec` (Draft PR #261).
- **Temporary worktree:** `~/Workspace/llm/qwen38-m1-reconcile-20261014`.
- **Canonical workspace (operator preference):** `~/Workspace/llm/qwen3.8-flash-next-dgx-spark`.
- **Action:** `./wizard.sh` main `5` (Benchmark) → `10` (Recover stopped M1 journal) → operator replied `y`.
- **Candidate:** `qwen38-mazinb-m1-20261014013811-16ced779`.
- **Exact Docker ID:** `7af3966f3d0cae79f8277eaf9ad003fb04c1e15ea01f86574c2d8eeac396e7a1`.

## Recovery command output

```text
M1_RECONCILE=RECORDED_STOPPED
M1_STOPPED_EXACT_ID=7af3966f3d0cae79f8277eaf9ad003fb04c1e15ea01f86574c2d8eeac396e7a1
M1_EXIT_CODE=0
M1_SHUTDOWN_CAUSE=UNDETERMINED
M1_DOCKER_START_STOP_REMOVE=NOT_PERFORMED
```

## Post-recovery read-only validation

Operator ran the M1 runtime controller's read-only `status` subcommand using `python3` and listed the journal backup glob.

```text
M1_SESSION_PHASE=stopped
M1_SESSION_NAME=qwen38-mazinb-m1-20261014013811-16ced779
M1_CONTAINER_ID=7af3966f3d0cae79f8277eaf9ad003fb04c1e15ea01f86574c2d8eeac396e7a1
M1_RUNNING=False
M1_EXIT_CODE=0
M1_STATE_DIR=/home/inlc/.local/state/qwen38-spark/mazinb-m1
M1_DOCKER_REMOVED=NO
```

Two distinct backups were listed (both owner-only mode `rw-------`, 1149 bytes, 2026-10-14 13:40 KST):

- `active.json.pre-reconcile-20261014T044002Z-a878cf7e7332.bak`
- `qwen38-mazinb-m1-20261014013811-16ced779.json.pre-reconcile-20261014T044002Z-a878cf7e7332.bak`

**Classification: PHYSICAL_M1_JOURNAL_RECONCILE=PASS_RECORDED_STOPPED.**

This confirms the reconcile command's success output and subsequent stopped status, but not independent backup-content hashes, a fresh post-recovery full predecessor inventory, or an independently established shutdown trigger. Termination cause stays `UNDETERMINED`; long-term `HOST_STABILITY=INCONCLUSIVE`. No new GPU run, benchmark or managed promotion was performed. Historical trial/model/Docker assets are to be preserved.

## Operator workspace follow-up

The operator requests no further per-operation worktree accumulation. Use `~/Workspace/llm/qwen3.8-flash-next-dgx-spark` as the routine working directory; after auditing `git worktree list --porcelain` and individual cleanliness, remove only Git-registered obsolete worktrees with `git worktree remove <exact-path>` and **never** `rm -rf` or force cleanup. Preserve all benchmark, checkpoint, Docker, release, swap and journal evidence.

## Follow-up physical evidence: canonical workspace and benchmark copy verification (2026-10-14)

The operator subsequently performed and supplied command output showing:

- All **three** remaining disposable Git worktrees were removed with
  `git worktree remove`, after verifying their expected detached commits
  and only deleting each narrowly checked Python `.pyc` cache (if present).
- `git worktree list` then reported **only** the original
  `~/Workspace/llm/qwen3.8-flash-next-dgx-spark` checkout,
  at `2f1cc08` on `feature/wizard-modular-phase1-20261014`.
- The separately retained **36 KiB** physical M1 output directory
  `~/Workspace/llm/qwen38-m1-bench-results/20261014T015805Z`
  contains `smoke.json`, `mazinb.json`, `mazinb-report.md`, and `SHA256SUMS`.
- The operator ran `sha256sum -c -` against the **GitHub archived hashes**.
  All three data files printed `성공` (SUCCESS):

```text
0e7f42ef99c91098572558bb909c589ae7c470b3cb60f32599e394553cf1fafd  smoke.json
377f5b5745aa16d454269490db408376d5f18d0289e576df8cd5a92a986fc23e  mazinb.json
b3e8f2d88ddfdc6894a3ed3678769f95a115ab4b665a7b3eb31ced1991bb298a  mazinb-report.md
```

The local `SHA256SUMS` is **436 bytes** and records absolute physical DGX
paths; the GitHub archival manifest is **238 bytes** and records relative
filenames. The manifests' byte representation differs but all three
payload digests have been independently checked against the published
GitHub manifest. The 36-KiB physical evidence folder remains **preserved**;
no checksum or folder deletion was performed as part of verification.

**Evidence gate:** WORKSPACE_WORKTREE_CLEANUP=PASS_OBSERVED and
MODEL_REPORT_PAYLOAD_SHA256=PASS_THREE_OF_THREE. No inference benchmark
or host stability was repeated by these read-only/checkout housekeeping steps.
