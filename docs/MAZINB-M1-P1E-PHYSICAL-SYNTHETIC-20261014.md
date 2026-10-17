# DGX Spark P1e — physically executed synthetic journal model (2026-10-14)

## Source and scope

- Owner-supplied terminal capture from the real DGX; exact canonical source checkout `~/Workspace/llm/qwen3.8-flash-next-dgx-spark`.
- Exact verified source SHA `1594f301c6384ac0bbaebc3c65b1c01158ae5040`; fast-forward from `08f69be` and one registered Git worktree only.
- Invocations: `python3 -B scripts/runtime/m1-supervisor-journal-protocol.py plan`, `simulate`, and `python3 -B -m unittest discover -s tests -p 'test_m1_supervisor_journal_protocol.py' -v`.
- `plan` and `simulate` explicitly state `REAL_PERSISTENCE=NOT_IMPLEMENTED`, `REAL_FSYNC=NOT_PERFORMED`, `REAL_WORKER=NOT_IMPLEMENTED`, `HOST_IO=NONE`, `DOCKER_ACTION=NONE`, `SYSTEMD_ACTION=NONE`, `LINGER_CHANGE=NONE`.

## Actual DGX terminal outcome

```text
M1_P1E_MODE=PURE_IN_MEMORY_JOURNAL_MODEL
M1_P1E_RULE=INTENT_ACK_BEFORE_ACTION
M1_P1E_RULE=NO_AUTO_REPLAY_AFTER_UNCERTAIN_SHUTDOWN
M1_P1E_RULE=EXIT_PROVEN_RECORD_REQUIRES_EXACT_ID_MONITOR_AND_LEASE
M1_P1E_SECURITY=UNKEYED_HASH_IS_NOT_AUTHENTICATION
M1_P1E_SIMULATION=PASS_IN_MEMORY
M1_P1E_SIM_UNACKNOWLEDGED_FLUSH=BLOCKED
M1_P1E_SIM_STALE_REPLAY=BLOCKED
M1_P1E_SIM_IN_DOUBT_RESTART=RECONCILE_REQUIRED_NO_AUTO_REPLAY
M1_P1E_SIM_TORN_RECORD=BLOCKED
M1_P1E_SIM_UNKNOWN_SHUTDOWN=UNDETERMINED
Ran 11 tests in 0.027s
OK
```

**PHYSICAL_DGX_P1E_SYNTHETIC=PASS_IN_MEMORY / 11_OF_11_UNIT_TESTS_PASS.** The tested operation is a *pure synthetic program* physically run on the DGX. It did not test actual disk durability, fsync, Docker lifecycle, model/benchmark, persistent Journal or running supervisor.

## Priorities revised by the owner (same conversation)

The primary project outcome is **evaluate models, benchmark and preserve performance evidence, then selectively delete unneeded model/experiment assets to regain storage and memory**. Wizard should automate this operational lifecycle safely. Additional synthetic background-supervisor protocol layers are *not the current priority*. Focus next on a read-only current storage inventory, selecting a real model to test, collecting actual llama-benchy data, verifying an independent archive copy, then exact asset-specific reclaim review and explicit deletion authorization.

Retain the mazinb M1 raw benchmark results and the validated checksum copies, exact stopped Docker/journal evidence and all hybrid dependency ancestors until assessed. The 2026-10-13 105 GiB-free snapshot is historical, not current capacity. Removing model files frees disk space; releasing unified RAM/swap pressure also requires accurate runtime and cache attribution and should not be inferred from checkpoint deletion alone.

PR #261 and parent #259 remain Draft, unmerged; no Docker removal, user-service/linger modification, model deletion or actual background worker action was authorized by this P1e evidence.
