# Actual DGX H6 M1 memory-protection stop — 2026-10-14

## 2026-10-15 — Physical read-only forensic PASS; precise watchdog path classified

**Evidence class:** operator-pasted actual DGX console; source at audit
`2e61645c59dc005c474139bde1b3313ff62728b8`. The stopped
candidate originally ran `a30fe34b8c2fd3ad511d79876ac95ad69ac32523`.
These SHAs represent different things and must not be conflated.

- Source synchronization: clean branch, exact fast-forward head `2e61645...`.
- Exact journal/stop/Docker provenance: PASS; journal SHA256
  `f5c147acfcdbf2d23b1cbec26c8f1cfa1b753c7fbe285c522fc242d1f5a37a4f`;
  exact trial Docker ID `e526189f1093e95d81568d82eb10b8beaeb6227adca49029f241634769e6cbc7`;
  `failed_stopped`, Docker `exited`, `ExitCode=1`, `OOMKilled=False`.
- `H6_FORENSIC_VERDICT=CONFIRMED_WATCHDOG_MEMORY_PROTECTION_STOP`,
  `H6_FORENSIC_RC=0`, `H6_FORENSIC_PROTECT_LOG_PRESENT=True`,
  `H6_FORENSIC_STOP_REASON=memory-protection`,
  `H6_FORENSIC_STOP_AT=2026-10-14T14:28:55Z`.
- The five consecutive protective warnings (local KST clock) were:

  | KST 2026-10-14 | protect | noncma_available MiB | noncmafree MiB | swapfree MiB | swapgrowth MiB |
  |---|---|---:|---:|---:|---:|
  | 23:28:47 | 1/5 | 27809 | 1795 | 142999 | 3427 |
  | 23:28:49 | 2/5 | 28277 | 942 | 142999 | 3427 |
  | 23:28:51 | 3/5 | 28277 | 791 | 142999 | 3427 |
  | 23:28:53 | 4/5 | 28269 | 804 | 142999 | 3427 |
  | 23:28:55 | 5/5 | 28282 | 726 | 143000 | 3427 |

**Confirmed watchdog decision path (code + physical log):**
`noncmafree < 2 GiB` AND `swapgrowth >= 256 MiB`, repeated
5/5 at two-second intervals, with H6's legacy
`swap-available-gate=0GiB`. The `noncma_available < 10GiB`
branch did **not** fire (observed about 27–28 GiB), nor did
`swapfree < 8GiB`. `swapgrowth` is a host-wide delta since the
monitor started, **not per-process H6 swap attribution**.
This definitively identifies *why the watchdog decided to stop*,
NOT whether a genuine NVIDIA RM allocation failure or imminent physical
OOM also existed. No protection-policy relaxation is authorized.

**Fuller evidence archived on the physical host, not attached to GitHub:**
`/home/inlc/h6-m1-evidence-20261014.dvQmt6eq`. Operator copied
`active.json`, `trial.json`, `monitor.log`, `runtime-stop.env`,
`docker-inspect.json`, and `docker.log`. All six files passed
`sha256sum -c SHA256SUMS.txt`; original state assets remain untouched,
model not restarted, no deletion. This is one *on-host* archive, NOT
an off-host verified backup.

**Kernel evidence remains NOT_CAPTURED / NOT_VERIFIED.** The physical
`sudo -n journalctl` attempt failed because sudo required a password;
the empty/failed kernel attempt was not included in the SHA manifest.
Do **not** equate the absence of a kernel log with absence of NVRM/Xid
errors. The operator's attempted interval `14:18–14:45` corresponds
to UTC; the monitor prints `23:18–23:28` in KST. Query timestamps must
be interpreted in the host's timezone (or explicitly set UTC). The H6
journal stores `kernel_since` in local time. When recovering a kernel
window, use interactive sudo locally (never paste a password) and bound
the query to the actual experiment window, including earlier boots.
Retain the original failed attempt as history.

**Qualification:** `PHYSICAL_READONLY_PASS` for forensic stop identity,
`WATCHDOG_TRIGGER_PATH=LOW_FREE_AND_SWAP_GROWTH`;
`NVIDIA_RM_EVENTS=NOT_VERIFIED`, `HOST_STABILITY=INCONCLUSIVE`,
`API_READY=NOT_OBSERVED`, `INFERENCE=NOT_COMPLETED`,
`H6_FIRST_BENCHMARK=NOT_MEASURED`,
`RELAUNCH_AUTHORIZED=NO`, `RETIREMENT_AUTHORIZED=NO`.
Subsequent source-level changes/CI do not retroactively modify the
original physical run.


**Source:** operator-pasted real physical DGX Terminal A and Terminal B
console. This is a **selective transcript record**, not a full raw
monitor/kernel-log archive. Exact source Git HEAD:
`a30fe34b8c2fd3ad511d79876ac95ad69ac32523`.
Existing managed OrcaRouter original Docker and immutable release remained
the protected predecessor; no model/checkpoint deletion was authorized.

## Exact stopped experiment

- Wizard main menu **5 → 20**, new user-approved isolated H6 trial,
  16-GiB KV, local API port 18890, no reboot-activated service.
- Approved prompt, full protected predecessor ID re-entry, and exact
  `START_HYBRID_H6_16G` typed by operator.
- `H6_CANDIDATE_STARTED_UNQUALIFIED=qwen38-hybrid-h6-m1-20261014141803-69ef3492`.
- **Experiment container exact ID:**
  `e526189f1093e95d81568d82eb10b8beaeb6227adca49029f241634769e6cbc7`.
- Original protected predecessor ID:
  `f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`.
- The next physical Wizard console lines were:
  ```text
  H6_EXACT_STOPPED_ID=e526189f1093e95d81568d82eb10b8beaeb6227adca49029f241634769e6cbc7
  H6_SESSION_BLOCKED=memory_protection_stop_marker
  ! H6 protected session failed/stopped; preserve Docker and forensic evidence.
  ```
- Independent read-only physical `hybrid-h6-m1.py status`:
  `H6_SESSION_PHASE=failed_stopped`, same pinned exact Docker ID,
  `H6_SESSION_RUNNING=False`; trial state directory
  `/home/inlc/.local/state/qwen38-spark/hybrid-h6-m1/qwen38-hybrid-h6-m1-20261014141803-69ef3492`.
- Independent read-only `docker inspect`: `Status=exited`,
  `Running=false`, `OOMKilled=false`, `ExitCode=1`.
  **This does not prove absence of NVIDIA RM/kernel OOM events.**

## Partial model-load details, not API READY

The pasted `monitor.log` tail was dominated by checkpoint-loading
progress because the protecting watchdog invokes `docker logs --tail 1000`
when it triggers. It is **not** the warning/trigger trajectory.

- A complete `81/81` safetensors shard pass finished.
- `Loading weights took 577.40 seconds` printed at 14:28:33 (log clock).
- GPU warning: native FP4 computation not supported; weight-only FP4
  compressed representation uses Marlin kernels. This is a warning,
  **not an established failure cause**.
- ModelOpt NVFP4 W4A16 format reported experimental, also **not an
  established fatal error**.
- Loader reported EXT4, checkpoint 173.59 GiB and `Available RAM:
  27.19 GiB` at 14:28:46. This is an instantaneous log observation,
  **not** the watchdog's non-CMA/MemFree/swap threshold snapshot.
- A **subsequent 81-shard loading pass** was observed starting and
  advancing to at least **9/81** according to the Docker log tail.
  The first `81/81` does NOT mean the entire model was ready.
- API traceback `KeyboardInterrupt: terminated` appeared following
  process termination; it must not be presumed to be the original fault.
- No `H6_READY_FOR_BENCH`, `H6_INFERENCE_SMOKE=PASS`, or measured
  llama-benchy output was provided.

Post-stop host snapshot: 121Gi RAM; 118Gi available; 143Gi swap,
approximately 142Gi free; `/swap-ple.img` 128G and `/swap.img` 16G.
**These are recovery-state values and do not establish the at-stop
threshold cause**. Full host/kernel/watchdog trajectory not yet provided.

## Current verdict and preservation rules

- `H6_TRIAL=PHYSICAL_STARTED_UNQUALIFIED_THEN_FAILED_STOPPED`
- `H6_STOP_TRIGGER=MEMORY_PROTECTION_MARKER_OBSERVED`
- `H6_PROTECT_THRESHOLD_CAUSE=NOT_YET_CLASSIFIED`
- `H6_KERNEL_RM_EVENTS=NOT_YET_CHECKED`
- `H6_API_READY=NOT_OBSERVED`
- `H6_FIRST_LLAMA_BENCHY=NOT_MEASURED`
- `H6_RETRY_AUTHORIZED=NO`, `H3_H4_H5_H6_DELETE=NO`.
- Archive the full original monitor log, stop marker, both JSON
  journals, Docker inspect/logs, exact image/source identity,
  RM kernel window and SHA256 checksums **outside** the deletion tree
  before proposing configuration changes or another H6 trial.
- Unlike mazinb M1, H6 currently uses the legacy unconditional
  256-MiB swap-growth path when non-CMA MemFree falls below 2 GiB,
  even with greater reclaimable available memory. This is a
  **source-level possibility**, NOT the demonstrated stop cause.
  Do not relax safety thresholds without actual five-warning
  sample values.
- New Wizard **Benchmark 5→21** performs **read-only** exact-Docker/
  journal/stop-marker validation and emits only critical watchdog
  warning/protection lines (avoiding embedded model log noise);
  kernel journal query is best-effort sudo noninteractive.
  Physically untested at this source revision.

## Operator verification (new source only, no launch)

```bash
bash wizard.sh --lang ko
# Main 5 → Benchmark 21 (read-only)
```

Any mismatch or absent stop evidence yields an invalid/incomplete
verdict; no automatic H6 reboot or cleanup.
