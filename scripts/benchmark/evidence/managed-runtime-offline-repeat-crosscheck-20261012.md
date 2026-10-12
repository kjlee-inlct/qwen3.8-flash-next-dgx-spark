# Managed runtime offline snapshot repeat — October 12, 2026

## Provenance and exact limits

The operator pasted a second **actual DGX Spark** read-only offline runtime inspection,
executed against a clean checkout of `feat/h38-managed-integration` at
`87fb463984683f75435302eff5ffc3b3b9f941bf`. The operator log shows
`MANAGED_RUNTIME_OFFLINE_PREFLIGHT=BEGIN`, three `OFFLINE_CHECK` entries with
`rc=0`, `MANAGED_RUNTIME_OFFLINE=COLLECTED_READ_ONLY`, and the terminal reached
`=== 3. Completed read-only inspection ===`. The console excerpt is the supplied
source; no original log file was retrieved or independently hashed.

This is **repeat observation of existing stopped-host metadata**, not another
H38 model attempt or a new service/protection intervention. It was conducted on
the operator's older checked-out code SHA, not the newer docs-only branch HEAD.
The source inspector emits `RUNTIME_STOP_REASON=NOT_YET_PROVEN` as a
**non-interpreting collection marker**. The interpretation below is an
evidence cross-check, not a change to its generic literal output.

### Current operator observations

| Observed property | Exact result |
|---|---|
| Docker status | `exited` |
| Docker start | `2026-10-07T07:35:45.800732164Z` = 16:35:45.800732 KST |
| Docker finish | `2026-10-07T13:08:34.847184942Z` = **22:08:34.847185 KST** |
| Exit / Docker OOM / state error | `exit_code=0`, `oom_killed=false`, `state_error=""` |
| Declared binding | `8888/tcp` → `127.0.0.1:8888`; stopped runtime `runtime_port_map={}` |
| systemd | `Result=success`, `ExecMainCode=1`, `ExecMainStatus=0`, `LoadState=loaded`, `ActiveState=inactive`, `SubState=dead` |
| Service active/inactive | **22:08:29 KST / 22:18:17 KST**, 2026-10-07 |
| Transient state metadata | `runtime-commit.env`, `runtime-stop.env`, `monitor.pid` all **ABSENT** |
| Final collection markers | `RUNTIME_ATTESTATION_VALIDITY=NOT_PROVEN`, `RUNTIME_STOP_REASON=NOT_YET_PROVEN`, `H38_MODEL_GPU_RERUN=BLOCKED`, `MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED` |

All recorded Docker/systemd results, start/finish timestamps and file-existence
statuses **match** the earlier
[offline metadata Attempt 01](managed-runtime-offline-attempt01-exit0-no-oom-20261012.md)
taken at another clean checkout (`6ce45561640f4069d534cbe04f5064a39095a88a`).
Thus this is **confirmation of persisted stopped state**, not an independent
repeat of a running-model health or GPU/allocator experiment. The correct
declared loopback binding does not imply an active port or serving API.

## Cross-evidence timeline: this is not the candidate's Docker exit

The existing bounded actual-DGX
[service unit journal](managed-runtime-stop-journal-attempt01-protected-abort-20261012.md)
reports:

1. **22:08:30 KST** — `Stopping current runtime container gracefully`
   during managed candidate transition. The Docker snapshot's finish
   **22:08:34.847** and zero exit are consistent with the **predecessor
   container** being stopped for handover.
2. **22:08:35 KST** — transition prepared with `previous=1`; candidate
   runtime and memory monitor started with protection enabled.
3. **22:17:43 KST** — separate
   [actual monitor numeric samples](managed-monitor-trigger-attempt01-low-free-swap-growth-pass-20261012.md)
   reach `protect=5/5`; log states `PROTECT stopping qwen38-flash-next
   gracefully to preserve host stability`.
4. **22:18:16–17 KST** — managed service records
   `Candidate runtime was stopped by memory protection during startup`,
   `Previous runtime container restored but left stopped after memory protection`,
   and `Runtime transition aborted by memory protection (state=idle)`.
   The returned systemd `InactiveEnterTimestamp=22:18:17` agrees with
   that protection-abort/rollback sequence.

**Resolved at the recorded application/managed-service level:**
`MANAGED_CANDIDATE_PROTECTION_ABORT=CONFIRMED_BY_EARLIER_SERVICE_JOURNAL`;
`PREVIOUS_RUNTIME_GRACEFULLY_STOPPED_FOR_TRANSITION=CONFIRMED`;
`PREVIOUS_RUNTIME_RESTORED_STOPPED=CONFIRMED`.
The numerical protection-branch evidence identifies **low non-CMA free
memory plus growth in swap usage**, with five consecutive samples. It
does not demonstrate a kernel OOM, a proven NVIDIA RM cause, an actual
host instability, or whether the protection was appropriately tuned.

**Identity limitation:** the current snippet does not supply an immutable
candidate container ID/exit code or a complete rollback identity chain.
The `exit_code=0` and `oom_killed=false` belong to the **currently
inspected canonical container, consistent with the restored predecessor**;
they **must not** be applied to the stopped H38 candidate or presented as
evidence of its clean startup. The absent runtime attestation and stop marker
cannot disprove the already archived protection event.

## Acceptance and next action

```text
DGX_LOCAL_SYNTHETIC=PASS_AT_87fb463_56_OF_56
REPEATED_OFFLINE_METADATA=COLLECTED_READ_ONLY
LIVE_SELECTED_PROFILE=orcarouter_IN_INSTALL_MANIFEST
PRESENT_CONTAINER=EXITED
MANAGED_CANDIDATE_PROTECTION_ABORT=CONFIRMED_HISTORICAL_JOURNAL
MONITOR_TRIGGER=LOW_NONCMA_FREE_PLUS_SWAP_GROWTH_5_OF_5
STOPPED_PREDECESSOR_RESTORED=CONFIRMED_HISTORICAL_JOURNAL
CANDIDATE_KERNEL_OOM_OR_NVIDIA_RM_CAUSE=UNVERIFIED
RUNTIME_ATTESTATION=ABSENT
M1_HOST_HEALTH=NOT_QUALIFIED
M2_DESTRUCTIVE_E2E=NOT_RUN
M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED
M4_H38=BLOCKED
HOST_STABILITY=INCONCLUSIVE
HOST_PROTECTION=UNCHANGED
PR_259=DRAFT_OPEN
MERGE=BLOCKED
```

Do **not** repeat live H38/monitor runs, query additional broad histories,
restart the old service/container, fabricate runtime commit, change swap or
host-protection configuration, or promote the stopped runtime to qualified.
The same historic Oct 7 events are already resolved as far as the manager
stop/rollback and trigger branch are concerned. Return priority to
**host-independent lifecycle acceptance and independent disposable-host
destructive E2E planning**. The single production DGX remains untouched.
