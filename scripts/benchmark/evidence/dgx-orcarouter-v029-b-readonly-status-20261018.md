# Actual DGX OrcaRouter v0.29 B current stopped state — 2026-10-18

## Follow-up physical B Docker and memory-monitor evidence (owner, 2026-10-18 inspection)

These outputs retrospectively inspect a 2026-10-13 stopped trial. They do NOT demonstrate a new GPU start on 2026-10-18. The shell paste included a garbled grep line, but the resulting read-only observations were present:

- Exact B ID: `13abbb81ca92cbf2f8256e96941a19102ce809ff1c9364ce6932b44a88ebf6a1`.
- Image ID: `sha256:dba5d8af279fb85901e6d8911f1a59ecc45b669b0948ab8d01d7c7d1c5815734`; state `exited`, `ExitCode=137`, **`OOMKilled=false`**.
- Start `2026-10-13T11:56:13.596597655Z` (20:56:13 KST); finish `2026-10-13T12:04:01.821891458Z` (21:04:01 KST).
- B monitor had recurrent transient `protect=0/5` low-free warnings/recovery from 20:58 through 21:02 KST, swap consumption initially 0–4 MiB.
- At 21:03:22, 24, 26, 28 and 30 KST, five consecutive `protect=1/5` to `5/5` samples were observed. `noncmafree` MiB: **1969 → 1508 → 1115 → 1210 → 1171**; `noncma_available` MiB: **41610 → 41387 → 40861 → 41028 → 40702**; `swapgrowth=3207MiB`, `swapfree` about 143230MiB.
- At 21:03:30 KST the monitor printed `PROTECT stopping qwen38-ab-v029 gracefully to preserve host stability`. `monitor/runtime-stop.env` reported `STOP_REASON=memory-protection`, `STOP_CONTAINER_NAME=qwen38-ab-v029` and the same exact Docker ID.

The container finished ~31.8 seconds after the protected-stop marker. These facts confirm a **watchdog protection stop** at low immediately-free non-CMA memory and considerable swap activity, despite high reclaimable non-CMA available memory. `ExitCode=137` with `OOMKilled=false` does NOT independently prove NVIDIA RM OOM or kernel/Docker OOM. The exact B kernel error window and model-loading phase logs are still missing; no inference/bench result was obtained.

The owner also inspected the exact published official ARM64 registry reference `vllm/vllm-openai@sha256:3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e` locally. Docker returned `No such image`. **Only that exact reference is proven absent**; a differently tagged same image is not excluded. C has not been pulled, started or benchmarked. Do not prune the existing A/B containers or relax monitoring.

---

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
