# DGX Spark P1c — physically executed, pure synthetic supervisor protocol (2026-10-14)

## Provenance and classification

- **Source:** actual DGX terminal transcript pasted by the owner.
- **Canonical checkout:** `/home/inlc/Workspace/llm/qwen3.8-flash-next-dgx-spark` (the sole registered Git worktree).
- **Exact Git source:** `835be6f411abbb3e901992566d4459881853acf7`, checked using a full SHA comparison after `git fetch` and `git merge --ff-only`.
- **Invocations:** `python3 -B scripts/runtime/m1-supervisor-protocol.py plan` and `python3 -B scripts/runtime/m1-supervisor-protocol.py simulate`.
- **Nature of experiment:** Python in-memory state-transition simulation executed on physical DGX. No real background worker or service was created or managed; no actual Docker, GPU, journal, monitor or host-supervisor transition was tested.

## Physical terminal results (exact output fields)

```text
=== P1c Protocol Plan ===
M1_P1C_MODE=PURE_SYNTHETIC_PROTOCOL
M1_P1C_WORKER_IMPLEMENTED=NO
M1_P1C_HOST_INSPECTION=NONE
M1_P1C_DOCKER_ACTION=NONE
M1_P1C_USER_SERVICE_MUTATION=NONE
M1_P1C_LINGER_CHANGE=NONE
M1_P1C_PROTOCOL=OWNER_TOKEN_PID_START_INVOCATION_EXACT_DOCKER_WATCHDOG
M1_P1C_TRANSITIONS=ARM_OBSERVED,RUNNING_OBSERVED,REQUEST_STOP,STOP_VERIFIED,SUPERVISOR_LOST,RECONCILE_STOPPED
M1_P1C_HOST_STABILITY=NOT_QUALIFIED
=== P1c Pure Synthetic Simulation ===
M1_P1C_MODE=PURE_SYNTHETIC_PROTOCOL
M1_P1C_WORKER_IMPLEMENTED=NO
M1_P1C_HOST_INSPECTION=NONE
M1_P1C_DOCKER_ACTION=NONE
M1_P1C_USER_SERVICE_MUTATION=NONE
M1_P1C_LINGER_CHANGE=NONE
M1_P1C_SIMULATION=PASS_IN_MEMORY
M1_P1C_SIM_STOP=PASS_EXPLICIT_ACK
M1_P1C_SIM_RECOVERY=PASS_UNDETERMINED
M1_P1C_SIM_UNAUTHORIZED_STOP=BLOCKED
M1_P1C_SIM_PID_REUSE=BLOCKED
=== Workspace ===
835be6f (HEAD -> feature/wizard-modular-phase1-20261014, origin/feature/wizard-modular-phase1-20261014) docs(handoff): preserve P1c synthetic supervisor gate and physical exclusions
/home/inlc/Workspace/llm/qwen3.8-flash-next-dgx-spark  835be6f [feature/wizard-modular-phase1-20261014]
```

## Evidence interpretation

**PHYSICAL_DGX_P1C_SYNTHETIC=PASS_IN_MEMORY.** This is legitimate proof that the current code executed its synthetic plan and scenario on the DGX. It does **not** prove the safety of an actual background session, daemon, persistent owner-token issuance, real PID start-time identity, `systemd --user` invocation, actual watchdog heartbeats, exact Docker stop, or a persisted journal.

Source CI for commit `835be6f411abbb3e901992566d4459881853acf7` independently completed with **Push SUCCESS and PR SUCCESS**. CI proves synthetic/source checks, not physical runtime behavior.

Previously established physical host constraints remain: `Linger=no`, `M1_BG_USER_LINGER=DISABLED`, user manager available while logged in, `M1_BG_HOST_PROBE=BLOCKED` with `USER_LINGER_DISABLED`; reserved background unit `NOT_FOUND`. The owner has **not** approved a persistent linger-policy change.

## Next P1d prerequisites

Design durable worker identity, a versioned authenticated command protocol, one-shot default-deny operator STOP authorization, tamper/replay resistance, per-session audit/journal and independent fail-closed watchdog ownership. Test all edges with synthetic mocks including missing/changed Docker ID, monitor stale, user manager unavailable, SIGKILL, service disappearance, benchmark lease and interrupted journal commits, before any separately authorized DGX physical worker trial.

No background worker/start/stop or host policy mutation is authorized by this record. The original protected Docker, models, historical A/B evidence, M1 journal backups and benchmark output remain protected.
