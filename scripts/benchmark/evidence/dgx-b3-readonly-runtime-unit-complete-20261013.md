# Actual DGX B3: complete read-only stopped-runtime and systemd collection — 2026-10-13

**Evidence type:** user-provided terminal output from one physical DGX Spark.
**Provenance:** local clean checkout asserted at
`b35d0f3d7840d00c55f4c633813e88ac367c6373`. This document is an
operator-log transcription/interpretation, not an independently collected archive.
**Mutation scope:** metadata reads only; no Docker start/stop, service restart,
model launch, GPU workload, install, uninstall, swap change or protection change.

## Exact collector and result

The user ran the pre-existing
`scripts/lifecycle/inspect-readonly-runtime-offline.sh` with
`QWEN38_OFFLINE_DIAGNOSTIC_TARGET_SHA=b35d0f3d7840d00c55f4c633813e88ac367c6373`,
with pager disabled, followed by `systemctl cat --no-pager` and
`stat` of named state-marker paths. Completion sentinels:

```text
MANAGED_RUNTIME_OFFLINE_PREFLIGHT=BEGIN
OFFLINE_CHECK=container_state rc=0
OFFLINE_CHECK=container_declared_bindings rc=0
OFFLINE_CHECK=service_unit rc=0
MANAGED_RUNTIME_OFFLINE=COLLECTED_READ_ONLY
OFFLINE_DIAGNOSTIC_RC=0
IMMUTABLE_SERVICE_INSPECTION=COLLECTED_READ_ONLY
```

### Container and service facts

```text
Docker name: qwen38-flash-next
Docker status: exited
Docker exit_code: 0
Docker oom_killed: false
Docker started: 2026-10-07T07:35:45.800732164Z
Docker finished: 2026-10-07T13:08:34.847184942Z
Docker state_error: ""
Configured port bindings: {"8888/tcp":[{"HostIp":"127.0.0.1","HostPort":"8888"}]}
Runtime port map: {}
Systemd LoadState: loaded
Systemd ActiveState: inactive
Systemd SubState: dead
Systemd Result: success
Systemd ExecMainCode: 1
Systemd ExecMainStatus: 0
Systemd ActiveEnterTimestamp: Wed 2026-10-07 22:08:29 KST
Systemd InactiveEnterTimestamp: Wed 2026-10-07 22:18:17 KST
```

Docker timestamps convert to **2026-10-07 16:35:45 KST** started and
**22:08:34 KST** finished. The Docker timestamps characterize the **retained
predecessor**, not the health or OOM status of the October 7 replacement candidate.
The empty live port map is expected while exited, not proof of a broken
loopback declaration. Likewise `Result=success` is not evidence of a
successful SERVING/READY or a live memory-stability acceptance.

### Actual unit and markers

```text
User=inlc
WorkingDirectory=/home/inlc/.local/share/qwen38-spark/current
ExecStart=/bin/bash /home/inlc/.local/share/qwen38-spark/current/scripts/service-runner.sh
ExecStop=-/usr/bin/docker stop --timeout 30 qwen38-flash-next
Restart=on-failure

runtime-adopt.env : ABSENT
runtime-stop.env : ABSENT
runtime-commit.env : ABSENT
monitor.pid : ABSENT
runtime-transition.env : ABSENT
profile-switch-transition.env : ABSENT
update-transition.env : ABSENT
release-profile-refresh-transition.env : ABSENT
```

The earlier partial collection established actual immutable
`current=ff67bab3c94d6992f61b9535836df97f03b9c022` and
`previous=a8aeca47433dc4033b3f1f995eb59023467222ce`, with
the canonical Manifest still pointing `INSTALL_ROOT` to the source checkout.
The actual installed `ff67bab3` release's updater uses
`manage-service.sh --runtime-root current`, so this discrepancy is **not**
by itself a release-alignment failure. Historical direct-Docker ExecStop is
consistent with that immutable release, though the feature branch implements
an identity-aware stop helper.

## Explanation and boundaries

The historic journal/monitor evidence from Oct 7 documented an attempted
managed replacement whose candidate monitor triggered **low non-CMA free +
swap-growth, five consecutive samples**, and a protected abort that left
the old predecessor stopped. The new exact metadata collection is **consistent**
with that history, but does not independently reobserve October 7's monitor
sampling or prove the currently missing stop-marker's root cause.

At installed release `ff67bab3`, source review finds:
- Managed `service-runner.sh` uses transactional candidate replacement and
  writes attestation after health and served-model identity validation.
- Its `abort-protected` restores the predecessor **stopped**.
- Its ordinary rollback and some recover paths can **start** the predecessor.
- The older service unit's `ExecStop` sends a Docker-name-based stop,
  unlike the feature branch's identity-checked helper.

Thus an apparently simple legacy `sudo systemctl restart` is not a
pure read-only test and can mutate container topology and reboot a
previously safety-stopped container on some failure paths. There is
no host test approval or live health evidence arising solely from this B3
collection.

```text
SOURCE_CLASS=ACTUAL_DGX_OPERATOR_PASTED
ACTUAL_DGX_CHECKOUT=b35d0f3d7840d00c55f4c633813e88ac367c6373
IMMUTABLE_RELEASE_CURRENT=ff67bab3c94d6992f61b9535836df97f03b9c022
B3_READONLY_RUNTIME_AND_UNIT=COLLECTED_READ_ONLY
B3_ALL_EIGHT_MARKERS=ABSENT
M1_LIVE_HEALTH=NOT_QUALIFIED
M2_DESTRUCTIVE_E2E=NOT_RUN
M3_LIVE_PROFILE_ALL_PAIRS=NOT_QUALIFIED
M4_H38=BLOCKED
D0_INDEPENDENT_DISPOSABLE=NOT_GRANTED
PR_259=DRAFT_OPEN_UNMERGED
```

## Next decision

Before a reversible legacy OrcaRouter M1 start: re-confirm live host protection,
exclusive relevant Docker object ownership, release image/manifest/container
identity and the installed release's exact `rollback`/`recover` side effects.
Specify bounded readiness sampling, independent strict RM event observation,
protection thresholds **unchanged**, STOP criteria, safe termination/rollback,
and what to do if an old stopped predecessor is present. No raw Docker start,
no blind systemd restart, no evidence fabrication, no H38 image/default refresh.
See `docs/DGX-STAGED-VALIDATION.md` and
`docs/SESSION-HANDOFF-PROMPT.md`.
