# ACTUAL_DGX — OrcaRouter Legacy A isolated wizard START — 2026-10-13 17:57 KST

**Evidence type:** physical operator-pasted terminal output;
**state:** Docker STARTED / model readiness & RM-stability **NOT QUALIFIED**.

## Exact source / execution

- GitHub commit `48c517357cef2182be986c298a86ddfa1f4c74b0`;
  clean detached worktree
  `~/Workspace/llm/qwen38-ab-trial-48c517357cef2182be986c298a86ddfa1f4c74b0`
- Source CI #38369045129 SUCCESS 955 Python tests and synthetic operator validations;
  CI is not real DGX readiness
- `./install.sh` invoked **without** `--dry-run`, under
  standard `operation.lock`, on the existing complete OrcaRouter
  installation
- Wizard: installed management `6` → A/B trial `2` Legacy A →
  confirmed protected original old Docker exact ID `f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`
  → explicitly answered `Y` to isolated trial create/start
- Operator saved full local wizard log as
  `/home/inlc/dgx-ab-legacy-start-20261013-175703.log`;
  log bytes not uploaded or read here

## Actual output fragment (verbatim)

```text
AB_TRIAL_STARTED=UNQUALIFIED
AB_TRIAL_VARIANT=legacy
AB_TRIAL_CONTAINER_ID=57eada965768b01eb412b10826ec4f0be9c4ed352abd87957c4ffbe932f27a56
AB_TRIAL_API=http://127.0.0.1:18888
AB_TRIAL_MONITOR_LOG=/home/inlc/.local/state/qwen38-spark/ab-trials/legacy-1791881886/monitor.log
AB_TRIAL_HOST_RM_QUALIFICATION=NOT_PERFORMED
AB_TRIAL_BENCHMARK=BLOCKED_UNTIL_API_AND_HOST_QUALIFIED
AB_WIZARD_RC=0
OLD_DOCKER_UNCHANGED=YES
INSTALL_MANIFEST_UNCHANGED=YES
AB_WIZARD_LOG=/home/inlc/dgx-ab-legacy-start-20261013-175703.log
```

The driver compared predecessor Docker
`Id|State.Status|Image|State.OOMKilled` and whole
`install.env` `sha256sum` before/after; both were identical.
This is a limited scoped preservation check. The new experimental
Docker ID is distinct from the protected predecessor. The
`AB_TRIAL_STARTED` result means only that the trial container
reached running state and the pinned watchdog wrote an initial
heartbeat under the source path. It does not assert sustained
model loading, watchdog liveness, API availability or host RM safety.

## Strict next gate and evidence requirements

Read-only observation of:

- Exact candidate+predecessor Docker inspect: status, Running, OOMKilled,
  exit code and pinned `Image`
- Trial watchdog `monitor/armed`, timestamp in
  `monitor/heartbeat`, actual monitor.log; stale heartbeat
  (more than about 10 seconds) is NOT_OK
- `docker logs` startup/traceback; actual
  `http://127.0.0.1:18888/health` HTTP 200 and
  `/v1/models` with exact OrcaRouter served model ID
- Host non-CMA `MemAvailable/MemFree/CmaFree`,
  SwapFree / nvidia-smi and NVIDIA RM kernel errors after 17:57
- A subsequent bounded physical observation window with no
  `NV_ERR_NO_MEMORY`, `_memdescAllocInternal` or Xid;
  absence in a partial journal excerpt cannot prove absence elsewhere

Any failure blocks Terminal B benchmark. If candidate is still
running but watchdog stale/host unstable, stop **through the wizard**
(menu 6→4; pinned candidate ID), preserve forensic container/log,
and recheck old predecessor. Only after real API and physical
host/RM stability approval may the pinned `llama-benchy`
be run with operation-lock wrapper, raw JSON+Markdown+SHA256
and verified off-host backup. The source-coded watchdog upper
runtime limit is **3600 s**, subject to its process liveness.
Do not assume it ran for that duration, or that a shell EXIT
trap handles `SIGKILL`/host reset. No deletion is authorized.
The original stopped managed container remains protected.
PR #259 Draft/Open/Unmerged.
