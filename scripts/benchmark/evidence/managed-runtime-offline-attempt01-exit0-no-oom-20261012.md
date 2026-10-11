# Managed runtime offline metadata Attempt 01 — exited / zero exit / no Docker OOM (2026-10-12)

## Actual DGX operator result and evidence limits

This is **actual user-provided DGX console output** from the guarded, no-restart offline metadata inspector. It is not a runtime success, model-validation, startup, or strict host-stability test. The original path `/tmp/managed-runtime-offline-attempt01-20261012.txt` was reported by the operator but its file bytes/SHA256 have **not** been independently retrieved.

- Checkout: `feat/h38-managed-integration` exact clean operator HEAD **`6ce45561640f4069d534cbe04f5064a39095a88a`**, fast-forward from `bbeceaf`.
- Inspector `scripts/lifecycle/inspect-readonly-runtime-offline.sh`, exact `QWEN38_OFFLINE_DIAGNOSTIC_TARGET_SHA`.
- Guard: `MANAGED_RUNTIME_OFFLINE_PREFLIGHT=BEGIN`; `scope=readonly_container_state_service_state_file_metadata_no_restart`; `gpu_or_model_launch=NO`; `install_uninstall_purge=NO`; `host_service_or_protection_mutation=NO`.
- All three checked read-only queries returned rc=0. Final `MANAGED_RUNTIME_OFFLINE=COLLECTED_READ_ONLY`, `offline_diagnostic_rc=0`, `MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED`, `H38_MODEL_GPU_RERUN=BLOCKED`.
- Result markers explicitly said `RUNTIME_ATTESTATION_VALIDITY=NOT_PROVEN` and `RUNTIME_STOP_REASON=NOT_YET_PROVEN`.

### Docker container state

```text
status=exited
exit_code=0
oom_killed=false
started=2026-10-07T07:35:45.800732164Z
finished=2026-10-07T13:08:34.847184942Z
state_error=""
OFFLINE_CHECK=container_state rc=0
```

Docker reports a **zero exit code**, **no Docker OOMKilled**, and no Docker state-error string. These observations **do not prove** an intentional operator stop, a protected monitor stop, error-free model operation, absence of prior NVIDIA RM failures, or kernel/driver health.

All timestamps below use **Asia/Seoul KST (UTC+09:00)**:

- Docker started at **2026-10-07 16:35:45.800732 KST**.
- Docker finished at **2026-10-07 22:08:34.847185 KST**.

### Port bindings: configuration is correct; stopped runtime mapping is empty

```text
port_bindings={"8888/tcp":[{"HostIp":"127.0.0.1","HostPort":"8888"}]}
runtime_port_map={}
OFFLINE_CHECK=container_declared_bindings rc=0
```

**Important correction of interpretation of prior Doctor FAIL:** `HostConfig.PortBindings` declares the **correct loopback** `127.0.0.1:8888` binding. Empty `NetworkSettings.Ports` / `docker port` on the exited runtime does **not** establish a configuration error or externally exposed port. Preserve the original Doctor `[FAIL] API port is not loopback-only: no published port` as an observed **running-port/readiness** failure; do not treat the configured host binding as wrong. The Doctor's fail/summary and its operational readiness gate are **not changed** by this clarification.

### Systemd service snapshot

```text
Result=success
ExecMainCode=1
ExecMainStatus=0
LoadState=loaded
ActiveState=inactive
SubState=dead
ActiveEnterTimestamp=Wed 2026-10-07 22:08:29 KST
InactiveEnterTimestamp=Wed 2026-10-07 22:18:17 KST
OFFLINE_CHECK=service_unit rc=0
```

`ExecMainCode=1` is the systemd **CLD_EXITED** process-exit classification, not the numeric process exit status; `ExecMainStatus=0` is the zero exit status. `Result=success` says the service did **not** record its unit result as failure. The managed unit was nevertheless **inactive/dead** during the operator check.

Docker finished **approximately 5.85 seconds after** the reported unit `ActiveEnterTimestamp`. Systemd entered `inactive` roughly **9 minutes 42 seconds after** the Docker `finished` timestamp. This timing is a **correlation** only: the event that requested container stop, the sequence of service startup hooks and eventual service deactivation, the presence/absence of previous protection events, and any transient attestation cleanup are **NOT PROVEN**. Do not infer a stable serving interval from these timestamps.

### Absent transient lifecycle state files

```text
state_file=runtime-commit.env status=ABSENT
state_file=runtime-stop.env status=ABSENT
state_file=monitor.pid status=ABSENT
```

These three files were **absent at observation time**. No evidence establishes when they disappeared, whether they were ever written, whether a protective stop was entered, or who removed them. The previous Doctor's runtime attestation check reported `missing or unsafe`; this newer metadata observation resolves **current existence** to `ABSENT`, **not historical provenance**. The missing stop marker makes a *currently retained* protected-stop marker absent; it does **not** rule out an earlier protective/managed stop if a cleanup path ran.

## Relationship to managed lifecycle acceptance

Prior actual DGX M1 read-only Attempt 01 had model/backend inventory `rc=0`, four profile/runtime/update/release-refresh states `idle` (`rc=0` each), but Doctor **five FAIL/two WARN**, `MANAGED_LIFECYCLE_READONLY=PARTIAL_CHECK_FAILURE`, `lifecycle_audit_rc=3`. This newer metadata audit passes **collection** only; it does not upgrade the Doctor or M1 live-host health. Historical strict H38 checkpoint `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `FUNCTIONAL=NOT_REACHED`, `HOST_STABILITY=INCONCLUSIVE`, `RM_MITIGATION=UNPROVEN`, `GPU_MODEL_RERUN=BLOCKED` persist.

```text
OFFLINE_METADATA_ATTEMPT01=COLLECTED_READ_ONLY
DOCKER_CONTAINER_STATE=EXITED
DOCKER_EXIT_CODE=0
DOCKER_OOM_KILLED=false
DOCKER_DECLARED_LOOPBACK_BINDING=CORRECT_127.0.0.1_8888
DOCKER_STOP_REQUEST_SOURCE=UNVERIFIED
SYSTEMD_SERVICE_RESULT=SUCCESS
SYSTEMD_SERVICE_STATE=INACTIVE_DEAD
RUNTIME_COMMIT_FILE=ABSENT
RUNTIME_STOP_FILE=ABSENT
MONITOR_PID_FILE=ABSENT
RUNTIME_STOP_REASON=NOT_YET_PROVEN
M1_HOST_HEALTH=NOT_QUALIFIED
MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED
GPU_MODEL_RERUN=BLOCKED
PR_259=DRAFT_OPEN
MERGE=BLOCKED
```

## Bounded next source and operator action

Inspect **only** a narrow, read-only `journalctl -u qwen38-flash-next.service` interval surrounding **2026-10-07 22:08 KST through 22:18 KST**. Look for service stop requests, reload/transition actions, runtime-commit removal conditions, monitor shutdown or unit timeout. Preserve errors and the possibility that journal access is incomplete. Do not infer who acted merely from `exit_code=0` and no Docker OOM. Review potentially sensitive journal messages before sharing them.

**No** `docker start/run/restart/rm`, `systemctl start/restart`, attestation fabrication, stop-marker/monitor state changes, `--refresh-profile-defaults`, checkpoint tensor reads, H38 GPU/model launch, image rebuild, destructive uninstall, host-protection relaxation, PR Ready or Merge.
