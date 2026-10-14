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

Operator ran `python3 .../scripts/runtime/mazinb-m1.py status` and listed the journal backup glob.

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
