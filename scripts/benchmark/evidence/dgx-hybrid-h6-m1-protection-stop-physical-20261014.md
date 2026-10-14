# Actual DGX H6 M1 memory-protection stop — 2026-10-14

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
