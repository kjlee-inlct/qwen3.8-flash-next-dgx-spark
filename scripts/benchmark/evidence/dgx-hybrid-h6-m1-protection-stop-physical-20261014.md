# Actual DGX H6 M1 memory-protection stop — 2026-10-14

## 2026-10-15 — Physical H6 monitor/Docker last-loading-window cross-check (7/7 archive PASS)

**Evidence type:** real owner-pasted **read-only** analysis of the
unchanged on-host `monitor.log` (270 lines, regex matches 17) and
`docker.log` (336 lines, regex matches 225). All seven archived files
passed `sha256sum -c SHA256SUMS.txt` again before inspection.
The operator's script displayed **only the last 35 regex matches** per
file, truncating lines to 400 characters. This is a selective transcript,
NOT full Docker traceback or proof that other unprinted log lines
contained no diagnostic errors.

**Cross-clock interpretation:** monitor timestamps are **KST (+09:00)**,
while vLLM's `docker.log` timestamps `10-14 14:28:46/58` are
**UTC as reconciled with the monitor/stop UTC marker**, thus
23:28:46/58 KST. The printed application log format itself has no
explicit timezone offset, so this mapping is corroborated by the
known stop/sequence, not independently certified by the log prefix.

| Actual H6 timeline (KST) | Observed contents |
|---|---|
| 23:18:04 | `monitor started`, `mode=protect`; `noncma-free=2GiB`, `free-gate=10GiB`, `swap-growth=256MiB`, `swap-available-gate=0GiB`, `swapfree=8GiB`. |
| 23:19:05–23:28:13 | Ten recorded healthy heartbeats (roughly 61 s intervals). |
| 23:28:13 | Last healthy heartbeat: non-CMA Available **42,581 MiB**, non-CMA Free **4,025 MiB**, SwapFree **143,030 MiB**. |
| 23:28:46 | `(Worker pid=486)` emitted **`Auto-prefetch is disabled`**: EXT4 is not recognized as NFS/Lustre and checkpoint size **173.59 GiB** exceeds 90% of reported available RAM **27.19 GiB**. This is an INFO message about prefetch admission, **not an OOM/CUDA error**. Second `Loading safetensors checkpoint shards: 0/81` pass is visible nearby. |
| 23:28:47 | `protect=1/5`; non-CMA Available **27,809 MiB**, Free **1,795 MiB**, swap-growth **3,427 MiB**, SwapFree **142,999 MiB**. |
| 23:28:49, :51, :53 | `protect=2/5,3/5,4/5`; non-CMA Free **942, 791, 804 MiB**. |
| 23:28:55 | `protect=5/5`; non-CMA Free **726 MiB**, non-CMA Available **28,282 MiB**, SwapFree **143,000 MiB**, swap-growth **3,427 MiB**. Monitor printed `PROTECT stopping qwen38-hybrid-h6-m1-20261014141803-69ef3492 gracefully`. |
| 23:28:55 | Exact-ID protected `runtime-stop.env` time `2026-10-14T14:28:55Z`. |
| 23:28:58 | vLLM `(APIServer pid=55)` logged `[shutdown] Process manager: send sigterm to process EngineCore` and a subsequent Python traceback. The excerpt does **not** include the traceback's terminal exception text; do not label it a spontaneous CUDA failure or independently prove its final exception from this excerpt. |
| 23:29:11.449–.484 | Existing 13-line kernel archive's Docker veth teardown events (about 16.5 s after 23:28:55). |

**Direct observed change:** From the 23:28:13 heartbeat to
23:28:47 warning (**34 seconds**), non-CMA Available decreased
**42,581 → 27,809 MiB** (**14,772 MiB**), while non-CMA Free
decreased **4,025 → 1,795 MiB** (**2,230 MiB**).
By 23:28:55, non-CMA Free was **726 MiB**; from 23:28:13
this is a total fall of **3,299 MiB**. The higher
`MemAvailable` is reclaimability estimation, not guaranteed
contiguous/unified GPU allocation headroom.

**Watchdog causal rule, source-identity checked:** GitHub
`scripts/runtime/monitor-runtime.sh` has identical Git blob
`017451b75b69da00bb10d9aec591a161a56862dc`
at the actual physical run commit
`a30fe34b8c2fd3ad511d79876ac95ad69ac32523`
and this documentation's parent
`ca1cb0c9e1855d8dac22d4247f7b28b43275e07a`.
The H6 controller `scripts/wizard/hybrid-h6-m1.py`
likewise is identical, blob
`19dd0823dc71d468890e334e4d484a34a1e1f56d`.
The monitor samples host `MemFree - CmaFree`,
`MemAvailable - CmaFree`, and **host-wide**
initial-minus-current `SwapFree`. Under the historical
H6 `swap-pressure-available-gib=0` behavior, consecutive
`noncmafree <2GiB && swapgrowth >=256MiB` triggers the
stop even with non-CMA Available >10GiB. Since SwapFree
was already approximately **3.4 GiB below** its initial
~146,426MiB level at the 23:28:13 heartbeat, this is an
**accumulated swap-activity arm** plus a subsequent
low-immediately-Free crossing, **not proof of an abrupt swap
spike at 23:28:47**. Host-wide swap consumption cannot be
attributed uniquely to H6.

**Source stop ordering:** the watchdog writes its
`PROTECT stopping` line, runs `docker logs --tail 1000`
(which accounts for application logs duplicated into
`monitor.log`), pins/rechecks the exact Docker ID, writes
`runtime-stop.env`, and issues
`docker stop --timeout 30`. In the preserved Docker log,
`[shutdown] ... SIGTERM` appears ~3s after the stop marker,
consistent with a watchdog-triggered graceful shutdown;
the precise Docker daemon invocation time is not
independently timestamped. Some later shard progress rows
(6/81→9/81) are printed **after** the API shutdown line
in the saved Docker stream; vLLM progress-bar updates /
concurrent stdout may be buffered or interleaved and
must not be used as proof that model loading persisted
after container termination. Previously observed
81/81 first-pass success does not mean H6 was READY.

**Final bounded attribution:**
`DIRECT_STOP=CONFIRMED_WATCHDOG_MEMORY_PROTECTION`;
`SECOND_SHARD_PASS_ACTIVE_AT_STOP=SUPPORTED_BY_LOG`;
`PREFETCH_INFO_MESSAGE=NOT_CAUSAL_ERROR_PROVEN`;
`API_SHUTDOWN_AFTER_WATCHDOG=OBSERVED`;
`KERNEL_13_LINES=DOCKER_VETH_ONLY_NO_RECORDED_RM_ERROR`;
`NVIDIA_RM_SAFETY=UNDETERMINED`;
`WAS_WATCHDOG_UNNECESSARY=UNDETERMINED`;
`H6_API_READY=NOT_OBSERVED`;
`H6_BENCHMARK=NOT_MEASURED`;
`OFF_HOST_BACKUP=NOT_VERIFIED`;
`H6_RELAUNCH_AUTHORIZED=NO`;
`WATCHDOG_RELAXATION_AUTHORIZED=NO`;
`DOCKER_CHECKPOINT_CLEANUP_AUTHORIZED=NO`.

**Next safe read-only discriminator:** inspect
`docker.log` lines ~235–336 *without regex truncation*,
especially the complete traceback tail (~255–328),
and `monitor.log` 13–25 (actual STOP and beginning of
copied Docker output), verifying checksums first.
Do not copy credentials. If additional physical diagnostics
are proposed, they must not start Docker, load GPU, delete
models or change protection policy.

## 2026-10-15 — Complete physical H6 kernel journal reviewed, all 13 lines

**Evidence class:** actual owner-pasted DGX stdout, from an unchanged
on-host `kernel-window.log`; the complete numbered output is transcribed
below. All **seven** files in the on-host evidence archive
`/home/inlc/h6-m1-evidence-20261014.dvQmt6eq` again passed
`sha256sum -c SHA256SUMS.txt` before `nl -ba -- kernel-window.log`.
This is the first **complete unfiltered 13-line kernel log review**
(previous reports relied on patterns and first/last lines). This
transcription in GitHub is a selective derived record; the physical
hash-pinned raw `kernel-window.log` remains on the owner host. No
off-host backup has been verified.

```text
     1  2026-10-14T23:18:03.922217+09:00 lc-gx10-pc kernel: docker0: port 2(vethd3bc075) entered blocking state
     2  2026-10-14T23:18:03.922312+09:00 lc-gx10-pc kernel: docker0: port 2(vethd3bc075) entered disabled state
     3  2026-10-14T23:18:03.922341+09:00 lc-gx10-pc kernel: vethd3bc075: entered allmulticast mode
     4  2026-10-14T23:18:03.922359+09:00 lc-gx10-pc kernel: vethd3bc075: entered promiscuous mode
     5  2026-10-14T23:18:03.927209+09:00 lc-gx10-pc kernel: eth0: renamed from veth7a138b9
     6  2026-10-14T23:18:03.928208+09:00 lc-gx10-pc kernel: docker0: port 2(vethd3bc075) entered blocking state
     7  2026-10-14T23:18:03.928234+09:00 lc-gx10-pc kernel: docker0: port 2(vethd3bc075) entered forwarding state
     8  2026-10-14T23:29:11.449309+09:00 lc-gx10-pc kernel: veth7a138b9: renamed from eth0
     9  2026-10-14T23:29:11.467208+09:00 lc-gx10-pc kernel: docker0: port 2(vethd3bc075) entered disabled state
    10  2026-10-14T23:29:11.483621+09:00 lc-gx10-pc kernel: docker0: port 2(vethd3bc075) entered disabled state
    11  2026-10-14T23:29:11.483641+09:00 lc-gx10-pc kernel: vethd3bc075 (unregistering): left allmulticast mode
    12  2026-10-14T23:29:11.483665+09:00 lc-gx10-pc kernel: vethd3bc075 (unregistering): left promiscuous mode
    13  2026-10-14T23:29:11.483687+09:00 lc-gx10-pc kernel: docker0: port 2(vethd3bc075) entered disabled state
```

**Forensic interpretation, carefully bounded:**
- Rows **1–7**, `23:18:03.922–.928 KST`: `vethd3bc075`
  attached/configured and Docker bridge entered `forwarding`
  state. These correlate temporally with the H6 trial start;
  the kernel text does not itself include the Docker 64-hex ID,
  so **network-interface-to-H6 identity is not independently
  proved by the 13 lines alone**.
- Independent archived watchdog samples show five protective
  warnings at `23:28:47, :49, :51, :53, :55 KST`, ending at
  the confirmed `memory-protection` marker at
  `2026-10-14T14:28:55Z` = `23:28:55 KST`.
- Rows **8–13**, `23:29:11.449–.484 KST`: the same `veth`
  names reverse/disable/unregister. The first visible teardown
  event is **about 16.45 s** and last event **about 16.48 s**
  after the watchdog's second-resolution stop marker.
  This is consistent with subsequent container networking
  teardown; the exact runtime-stop command time and Docker
  cause are not independently supplied by the kernel events.
- **All thirteen rows are Docker bridge/veth networking events.**
  No recorded line describes NVIDIA, NVRM, Xid, GPU, GPU
  allocation failure, OOM or memory failure; the earlier
  expanded regex also matched **0/13**. There are no kernel
  entries between the two veth event clusters, approximately
  **11 min 7 s** apart: no *recorded* event is not proof of
  complete journal coverage or successful GPU allocation.
  The watchdog itself may have prevented an otherwise
  imminent failure. No claim that the watchdog was an
  unnecessary/false-positive stop is substantiated.

**Updated precise labels:**
`KERNEL_CAPTURE=HASH_VERIFIED`;
`KERNEL_ALL_13_LINES_REVIEWED=YES`;
`KERNEL_EVENT_TYPE=DOCKER_VETH_ONLY`;
`KERNEL_RECORDED_RM_GPU_OOM_EVENTS=NONE_IN_CAPTURE`;
`WATCHDOG_MEMORY_PROTECTION_STOP=CONFIRMED`;
`WATCHDOG_NECESSITY=INCONCLUSIVE`;
`H6_READY=NOT_OBSERVED`;
`H6_BENCHMARK=NOT_MEASURED`;
`OFF_HOST_BACKUP=NOT_VERIFIED`;
`MODEL_RELAUNCH_AUTHORIZED=NO`;
`GUARD_WEAKENING_AUTHORIZED=NO`;
`CLEANUP_AUTHORIZED=NO`.

**Safe next analysis only:** correlate preexisting
`monitor.log` and `docker.log` event timestamps around
`23:28:47–23:29:11 KST`, and audit the existing protection
decision algorithm/source for a future separately reviewed
safe redesign. Do not restart H6, bypass/reduce the watchdog,
delete preserved Docker/checkpoints, modify H7/H20 dependencies,
or merge draft PR #261/#259. Even a proposed mitigation needs
independent safety gates and explicit owner permission before
physical GPU load.

## 2026-10-15 — Physical full-window kernel metadata and expanded pattern scan

**New actual DGX evidence:** after the seven-file on-host SHA256 audit
passed again (each `active.json`, `trial.json`, `monitor.log`,
`runtime-stop.env`, `docker-inspect.json`, `docker.log`, and
`kernel-window.log`: `성공`), the operator ran a **read-only**
Python scan of the already archived `kernel-window.log`. The resulting
physical console printed:

```text
H6_KERNEL_LINES=13
H6_KERNEL_FIRST=2026-10-14T23:18:03.922217+09:00 lc-gx10-pc kernel: docker0: port 2(vethd3bc075) entered blocking state
H6_KERNEL_LAST=2026-10-14T23:29:11.483687+09:00 lc-gx10-pc kernel: docker0: port 2(vethd3bc075) entered disabled state
H6_KERNEL_BROAD_MATCHES=0
H6_ANALYSIS_READ_ONLY=YES
```

The searched expression was
`nvidia|nvrm|xid|gpu|allocat|fail|error|fault|oom|out of memory|memory pressure|smmu|iommu|gsp|uvm|dma`
(case insensitive). The scanner searched **all 13 lines** but
reported only first/last and (if present) last 30 matches. There were
**zero hits**. The first and last timestamps bracket the
`2026-10-14 23:28:55 KST` watchdog stop, with the final kernel event
~16 seconds later; this validates time coverage by the extracted
records at its endpoints, but not continuity of kernel event
retention/delivery between those records. The **middle 11 full
lines have not been pasted**; do not claim to have reviewed their
unfiltered contents, boot completeness, or absence of silent RM
allocation errors.

**Evidence interpretation:** kernel journal `_TRANSPORT=kernel`
within 23:18:03–23:29:55 KST showed **no messages matching broad
GPU/RM/allocator/OOM indicators**. This strengthens the explanation
that the *observed* stop was the exact-ID protective watchdog using
`noncmafree < 2GiB` plus host-wide `swapgrowth >= 256MiB` on 5/5
samples, without a matching *logged* NVIDIA RM/Xid error.
It does **not** distinguish a harmless cold-load transient from a
protection event that prevented an imminent allocation failure.
The watchdog likely stopped before the later failure could happen,
so negative kernel matches cannot disprove an avoided failure.
Therefore: `H6_KERNEL_ARCHIVE=HASH_VERIFIED_13_LINES`,
`H6_KERNEL_BROAD_MATCHES=0`,
`NVIDIA_RM_FATAL_EVENT_IN_CAPTURE=NOT_OBSERVED_BY_PATTERN`,
`WATCHDOG_TRIGGER=CONFIRMED`,
`ROOT_CAUSE_PROTECTION_NECESSITY=INCONCLUSIVE`,
`RELAUNCH_AUTHORIZED=NO`,
`H6_BENCHMARK=NOT_MEASURED`,
`OFF_HOST_BACKUP=NOT_VERIFIED`.

No Docker start/stop, checkpoint deletion, threshold change,
new H6 load or benchmark was performed by this audit. The precise
container, monitor, original raw evidence, H7/H20 aliases and
historical mounts remain protected. A next **read-only** action is to
review the 13 original kernel lines completely (not just regex
matches), together with existing timestamped Docker log and
monitor progression. This requires no new GPU run and no change
to safety thresholds.

## 2026-10-15 — Physical kernel-window capture complete; known RM/OOM strings not found

**Operator-provided physical DGX console** (not a GitHub CI result): after
the earlier noninteractive sudo failure, the operator used **interactive
`sudo -v`**, then ran
`journalctl _TRANSPORT=kernel --since ... --until ... --no-pager
--quiet --output=short-iso-precise`. The bounds were computed rather
than guessed: `kernel_since` from archived `active.json`, and the UTC
`UPDATED_AT` in `runtime-stop.env` plus 60 seconds converted to the
host-local time zone. Actual printed bounds:
`2026-10-14 23:18:03` to `2026-10-14 23:29:55` (KST).
The watchdog stop at `2026-10-14 23:28:55` KST falls inside.

- Original evidence archive:
  `/home/inlc/h6-m1-evidence-20261014.dvQmt6eq`.
- Existing six archived files were reverified using
  `sha256sum -c SHA256SUMS.txt` **before** kernel collection: six PASS.
- New **nonempty** `kernel-window.log` saved inside the same on-host
  archive. The operator added its checksum to `SHA256SUMS.txt`,
  reran `sha256sum -c`, and observed all **seven** PASS.
  Individual file digests and the raw kernel text were **not** pasted
  into chat or GitHub; do not fabricate them.
- `grep -Ein 'NVRM|Xid|NV_ERR_NO_MEMORY|_memdescAllocInternal|oom-killer|out of memory'
  kernel-window.log` printed **no matching lines**. Thus the result
  is `KERNEL_WINDOW_CAPTURED_HASH_VERIFIED` and
  `SELECTED_NVRM_XID_OOM_PATTERNS=ZERO_MATCHES_IN_CAPTURE`,
  **not** `NVIDIA_RM_ERRORS_ABSENT`. Journal completeness across
  the time window, potentially different fault text, and other
  device-allocation failures have **not** been independently reviewed.
- The operator printed `H6_MODEL_RESTARTED=NO`; no Docker/model
  start, stop, delete, source change, or watchdog tuning occurred
  during evidence capture.

**Important qualification:** previous lines below saying
`NOT_CAPTURED` refer to the *earlier failed `sudo -n` attempt* and are
historical, superseded with respect to archive presence only.
`WATCHDOG_TRIGGER_PATH=LOW_FREE_AND_SWAP_GROWTH` remains physically
supported by monitor events, but **false-positive versus necessary
protection is UNRESOLVED**. The high non-CMA MemAvailable (~27–28 GiB)
and large host-wide swap-growth (~3.4 GiB) cannot prove a GPU memory
allocation succeeded or that host memory was safe at every point.
`API_READY=NOT_OBSERVED`,
`INFERENCE_SMOKE=NOT_COMPLETED`,
`BENCHMARK=NOT_MEASURED`,
`OFF_HOST_BACKUP=NOT_VERIFIED`,
`RELAUNCH_AUTHORIZED=NO`,
`RETIREMENT_AUTHORIZED=NO`.
Do not touch the stopped H6 trial, historical Docker references,
H7/H20 dependencies, or PR #261/#259 merge status.

**Next read-only discriminator:** review non-sensitive metadata about
the captured kernel file (line count, first/last timestamps, boot IDs
or journal retention where available), and perform a broader *inspection*
of full log text for `nvidia`, `alloc`, `fail`, `fault`, `memory`,
`gpu`, `iomm` / `smmu`, not a claim of zero errors solely because
the selected six patterns had no hits. Independent off-host backup
with reverified hashes remains a separate prerequisite for later
checkpoint retirement.

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
