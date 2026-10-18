# Actual DGX OrcaRouter v0.29 B current stopped state — 2026-10-18

**Provenance:** `ACTUAL_DGX_OPERATOR_TERMINAL` pasted by the owner in the
2026-10-18 conversation. This is a **current read-only inspection of an
existing trial**, not evidence that the B model was started on this date.
The source checkout's last separately reported HEAD was
`ad3855a0a64e25deed3b9c11d7b3168f06730d68` with a clean
`git status --short`; the specific status-command transcript itself
**does not repeat** the git HEAD or Docker start/finish timestamps.

## Exact owner outputs

```text
AB_TRIAL_PHASE=stopped
AB_TRIAL_VARIANT=v029
AB_TRIAL_CONTAINER_ID=13abbb81ca92cbf2f8256e96941a19102ce809ff1c9364ce6932b44a88ebf6a1
AB_TRIAL_RUNNING=False
AB_TRIAL_DOCKER_STATUS=exited
AB_TRIAL_EXIT_CODE=137
AB_TRIAL_STOP_REASON=memory-protection
AB_TRIAL_MONITOR_LOG=/home/inlc/.local/state/qwen38-spark/ab-trials/v029-1791892573/monitor.log
AB_HOST_RM_STABILITY=REQUIRES_SEPARATE_PHYSICAL_QUALIFICATION
AB_BENCHMARK=NOT_MEASURED
Qwen runtime service status
  installed : no
  enabled   : no
  active    : no
NAMES        STATUS                 PORTS
open-webui   Up 2 weeks (healthy)   0.0.0.0:3000->8080/tcp, [::]:3000->8080/tcp
portainer    Up 2 weeks             8000/tcp, 9000/tcp, 0.0.0.0:9443->9443/tcp, [::]:9443->9443/tcp
```

Immediately before this read-only status, the owner attempted two
loopback checks of `http://127.0.0.1:18888`, both of which returned
`curl: (7) Failed to connect`. The maintained benchmark-lock wrapper
**acquired** its existing operation lock separately for qualification
and decode; neither wrapper attempt starts any model. The benchmark
client emitted two `status=fail` JSON documents with
`request failed: /health: <urlopen error [Errno 111] Connection refused>`
(starting 2026-10-18T08:29:57Z). This is
**NO_API / NO_PERFORMANCE_SAMPLES**, not a measured zero tok/s or
benchmarked inference failure of a running model. JSON paths and
SHA256SUMS content were not shown/independently verified.

## Interpretation and STOP contract

- `v029` is not currently READY/running. `stopped` journal state and
  `memory-protection` cause are reported by the maintained read-only
  status code, with an exited Docker object and exit code 137.
- `137` alone is **not evidence of kernel OOM, NVIDIA RM OOM, or
  Docker `OOMKilled=true`**. B's exact Docker `OOMKilled` flag,
  start/finish timestamp, monitor threshold trajectory, swap-growth
  record and kernel NVRM/RM window have **not** been pasted for this B.
- Service-manager `installed=no/enabled=no/active=no` is its reported
  observation; this alone does not establish absent checkpoints,
  installed manifests, immutable releases or protected historical Docker.
- The existing `qwen38-ab-v029` name and preserved evidence must not
  be overwritten. In current source, `check_candidates()` rejects
  trying to start another trial with the same existing variant name.
- **DO NOT** repeat the benchmark against 18888, restart the service,
  direct-start Docker, change monitor thresholds, force KV24, prune,
  remove this B container, or delete model assets. No new trial or
  change of image was authorized. The next gate is an actual read-only,
  bounded B-specific Docker/monitor/kernel timeline review, then a
  separately approved safe fresh-trial design and source qualification.
- Historical Legacy A protection-stop evidence remains independent;
  a 2026-10-18 view of stopped B is not a new 2026-10-18 GPU run.
