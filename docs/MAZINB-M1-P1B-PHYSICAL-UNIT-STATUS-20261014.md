# DGX Spark M1 Background P1b — physical reserved user-unit inventory (2026-10-14 KST)

## Provenance

- **Source:** owner-pasted output from the actual, single DGX Spark.
- **Canonical checkout:** `~/Workspace/llm/qwen3.8-flash-next-dgx-spark`.
- **Source and Git HEAD:** `e542f99fa711a61a1713fa0c10341f47934e7866`, branch `feature/wizard-modular-phase1-20261014`.
- **Command:** `python3 -B scripts/runtime/m1-background-probe.py unit-status` after a clean-worktree guard, Git fetch, fast-forward merge and full-SHA assertion.
- **Reserved unit name:** `qwen38-mazinb-m1-background.service`.

## Exact terminal result

```text
M1_BG_RESERVED_UNIT=qwen38-mazinb-m1-background.service
M1_BG_WORKER_IMPLEMENTED=NO
M1_BG_WORKER_IDENTITY_VERIFIED=NO
M1_BG_DOCKER_ACTION=NONE
M1_BG_USER_SERVICE_MUTATION=NONE
M1_BG_UNIT_STATUS=NOT_FOUND
M1_BG_UNIT_PRESENCE=ABSENT_RESERVED_UNIT_ONLY
```

**Classification: PHYSICAL_DGX_P1B_RESERVED_UNIT_INVENTORY=PASS_READ_ONLY_NOT_FOUND.**

This confirms that the *one reserved user unit* was reported missing by the implemented read-only systemctl query. It does **not** establish that all host units/processes or other model experiments are absent. There is no implemented background worker, verified PID, unit/session token, exact candidate Docker-ID binding or background start/stop protocol. The check is not a live supervisor functional qualification.

## Earlier physical admission remains blocked

The same DGX, at earlier source `56b51aa94a5db5b32ce0d8adc2397760bb026805`, independently returned `Linger=no`; its P1a probe returned `M1_BG_USER_LINGER=DISABLED`, `M1_BG_USER_MANAGER=AVAILABLE`, `M1_BG_HOST_PROBE=BLOCKED`, `M1_BG_BLOCK_REASON=USER_LINGER_DISABLED`.

**Do not enable lingering automatically.** Linger activation is a persistent owner-host policy change requiring separate explicit approval. No `systemctl start/stop`, `loginctl enable-linger`, Docker start/stop/remove, GPU inference or managed-service mutation occurred during these checks. `Linger=no` remains the operative logout-persistence gate.

## Follow-up boundaries

- Preserve the canonical single Git checkout; do not add per-operation worktrees.
- Keep original Foreground Wizard menu 9 and exact-ID stopped-journal reconciliation menu 10 unchanged.
- Model background worker, authorization, stop control, replay-resistant session identity, exact-ID monitor lifetime and lost-worker recovery need separate source implementation, synthetic safety tests, CI, read-only host inspection and expressly approved functional DGX validation.
- Do not assert HOST_STABILITY qualification or a successful background execution.
- Draft PR #261 is stacked on Draft PR #259, both unmerged.
