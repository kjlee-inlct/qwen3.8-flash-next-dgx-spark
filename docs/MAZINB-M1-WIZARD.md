# mazinb M1: Wizard-owned isolated session — source implementation

## P1e in-memory write-ahead journal/crash protocol — SOURCE ONLY

Wizard Benchmark **16** uses `m1-supervisor-journal-protocol.py simulate`
to evaluate immutable prepared `STOP_INTENT` and `EXIT_PROVEN`
records against an injected, **in-memory** copy-on-write ledger.
An unacknowledged record cannot advance the synthetic durable snapshot.
A committed intent is bound to the exact Docker ID, predecessor ID,
owner token and one command nonce. On crash/recovery from that state
the only safe result is **`RECONCILE_REQUIRED_NO_AUTO_REPLAY`**,
not automatic reissue of STOP. An exit proof requires matching
candidate identity, an exited (not running) synthetic Docker state,
confirmed monitor termination, a free benchmark lease, exit code
and preserved shutdown cause. The journal chain uses SHA-256 for
synthetic corruption detection; **it is not authentication**.

**Not implemented:** real durable file persistence, fsync, directory
fsync, cross-process locks/CAS, trusted clock, authenticated IPC,
atomic nonce store, actual Docker inspect/stop, systemd worker,
on-host watchdog/Journal recovery, or restart handling. Commit
acknowledgements are injected booleans, not real durability proof.
CI/host simulation must not be mistaken for a worker qualification.
The existing physical `Linger=no` gate remains, with no permission
to enable lingering.
## P1d physically executed in-memory simulation (2026-10-14)

Operator executed the P1d `plan` and `simulate` commands at exact SHA
`08f69beda51a7ee8d610774e260aae21bed911b0` on the DGX, after
a clean Fast-forward sync and full SHA assertion. The simulation
returned `PASS_IN_MEMORY`, and rejected unapproved STOP,
`Linger=no`, nonce replay and expired synthetic requests.

**Qualification is physically executed synthetic protocol only.**
There is no actual STOP, IPC, kernel peer attestation, durable journal,
persistent replay ledger, user service or real background worker.
No Docker/managed model/GPU/linger mutation occurred.
[Exact DGX output](MAZINB-M1-P1D-PHYSICAL-SYNTHETIC-20261014.md).
## P1d in-memory control-command admission — SOURCE ONLY

Wizard Benchmark **15** runs `m1-supervisor-command-protocol.py simulate`,
a pure synthetic simulation of future VIEW_STATUS and REQUEST_STOP
authorization. `plan` describes the frozen request contract.

An injected immutable owner identity pins full candidate/predecessor
Docker IDs, owner token, systemd invocation ID, supervisor PID and start
ticks, and owner UID. A request must match the trusted identity, carry
a unique nonce and supported protocol version, and be neither future
nor expired (maximum 30,000 ms lifetime). Duplicate or exhausted
nonces fail closed. REQUEST_STOP requires a simulated explicit consent,
linger-enabled host gate, verified supervisor/watchdog and a free
benchmark lease. VIEW_STATUS never authorizes mutation.

**This is not authentication or an operating system peer check.** All
parameters are injected; the immutable in-memory nonce state is not
durably persisted or locked across concurrent requests. There is NO
IPC socket, SO_PEERCRED, systemd user unit, real persistent owner-token
storage, Docker start/stop, actual worker action or real operator STOP.
Before any production worker, implement peer credential validation,
atomic persistent replay protection and exact-ID watchdog/journal
reconciliation with separate approval and real DGX evidence.
On the single DGX, `Linger=no` remains verified and must not be
silently changed.
## Physically executed P1c in-memory simulation — VERIFIED (2026-10-14)

The operator synchronized the single canonical Git checkout to exact
`835be6f411abbb3e901992566d4459881853acf7` and invoked P1c
`plan` and `simulate` on the real DGX. Reported:
`PASS_IN_MEMORY`, `PASS_EXPLICIT_ACK`, `PASS_UNDETERMINED`
reconciliation, plus `BLOCKED` unauthorized STOP and PID reuse.

**This verifies synthetic program execution only.** No host PID,
systemd service, Docker, GPU, real watchdog or filesystem journal
was inspected or mutated by the scenario. `Linger=no` remains
independently confirmed; no permission to enable linger has been given.
Actual Background Worker and logout-persistent supervision are
still NOT_IMPLEMENTED / NOT_QUALIFIED.

[Exact physical synthetic transcript](MAZINB-M1-P1C-PHYSICAL-SYNTHETIC-20261014.md).
## P1c source-only supervisor protocol simulator — NOT A WORKER

Wizard Benchmark **14** and `scripts/runtime/m1-supervisor-protocol.py simulate`
exercise only in-memory synthetic values; `plan` prints the contract.
Neither command accesses Docker, systemd, host PID tables, persistent
journals, GPU, user-linger policy or the filesystem beyond loading Python
source. No background Worker, service unit, start or stop is implemented.

The pure transition protocol requires an immutable owner tuple of the
exact full trial and predecessor Docker IDs, owner token, unit identity,
supervisor PID **and its start ticks**, systemd invocation ID, matching
synthetic journal token/candidate and exact-ID watchdog arm.
State transitions are `CREATED → ARMED → RUNNING → STOP_REQUESTED →
STOPPED/FAILED_STOPPED`, and `SUPERVISOR_LOST → RECOVERY_REQUIRED →
STOPPED/FAILED_STOPPED`. Transitions accept **injected evidence only**;
they are not commands to start/stop anything.

Stop requires explicit approval, free benchmark lease, a live pinned
watchdog/heartbeat and supervised candidate. Finalization requires
synthetic exact-stop acknowledgement, proven Docker exit, ended
watchdog evidence and an available lease. Reconciliation after owner
loss must not infer STOP from a clean Docker exit; an unmarked exit
retains `UNDETERMINED`. PID reuse, token/invocation drift, stale
watchdogs, and illegal event replay fail closed.

**Qualification:** SOURCE_ONLY until source CI passes; no real user
service deployed and no DGX live, logout persistence or host stability
qualification performed. Independently observed `Linger=no` continues
to block actual durable background admission and no policy mutation
is authorized.
## Physical P1b user-unit status confirmed (2026-10-14) — NO WORKER

On the single canonical checkout, source SHA
`e542f99fa711a61a1713fa0c10341f47934e7866`, the owner ran the
read-only `unit-status` probe after an exact source-SHA assertion.
The reserved user unit `qwen38-mazinb-m1-background.service` was
**NOT_FOUND** (`M1_BG_UNIT_PRESENCE=ABSENT_RESERVED_UNIT_ONLY`).
The command also printed `M1_BG_WORKER_IMPLEMENTED=NO`,
`M1_BG_WORKER_IDENTITY_VERIFIED=NO`,
`M1_BG_DOCKER_ACTION=NONE`, and
`M1_BG_USER_SERVICE_MUTATION=NONE`.

**ACTUAL_DGX_READ_ONLY_UNIT_INVENTORY=PASS_NOT_FOUND** does not imply
a deployed Supervisor, a PID/unit ownership attestation, host stability,
or the absence of other system units and processes. Independent P1a
evidence remains `Linger=no`, so durable logout-independent background
admission is blocked. Do not silently enable lingering, change user
units or start a Docker model. Background start/stop remains UNIMPLEMENTED.

[Exact operator terminal result](MAZINB-M1-P1B-PHYSICAL-UNIT-STATUS-20261014.md)
## 2026-10-14 ACTUAL DGX P1a linger policy — READ_ONLY CONFIRMED

On the original canonical Git checkout at source `56b51aa94a5db5b32ce0d8adc2397760bb026805`,
the operator ran `loginctl show-user "$(id -u)" --property=Linger`
and `python3 -B scripts/runtime/m1-background-probe.py probe`.
The physical DGX output was:

```text
Linger=no
M1_BG_USER_LINGER=DISABLED
M1_BG_USER_MANAGER=AVAILABLE
M1_BG_LINGER_POLICY_CHANGE=NOT_PERFORMED
M1_BG_SUPERVISOR_IMPLEMENTED=NO
M1_BG_DOCKER_ACTION=NONE
M1_BG_USER_SERVICE_MUTATION=NONE
M1_BG_AUTO_START=DISABLED
M1_BG_HOST_PROBE=BLOCKED
M1_BG_BLOCK_REASON=USER_LINGER_DISABLED
```

**PHYSICAL_P1A_HOST=CONFIRMED_LINGER_NO / BLOCKED_AS_DESIGNED**.
The source HEAD matched the fetched branch and retained the sole
canonical Git checkout. The operator did NOT authorize or perform
`loginctl enable-linger`. No Docker, service, GPU or managed
release mutation was performed. The earlier unknown/disabled combined
reason below is historical; `Linger=no` is now independently established.
## P1b preliminary unit visibility — READ ONLY / NO WORKER

Wizard Benchmark **13** and
`python3 -B scripts/runtime/m1-background-probe.py unit-status`
inspect only the reserved user unit
`qwen38-mazinb-m1-background.service` using read-only
`systemctl --user show` properties.

The method reports `M1_BG_UNIT_STATUS=NOT_FOUND` **only when**
the reserved unit is explicitly not found, inactive/dead with MainPID=0.
That does **not** prove there is no other process, system unit or
experimental worker. If a unit exists, has an unexpected property,
or user manager inspection fails, the probe reports BLOCKED or
BLOCKED_UNTRUSTED_PRESENT; a MainPID alone is never accepted
as worker identity. The worker, unit deployment, session-token
binding, stop protocol and real background launch remain unimplemented.
All existing Docker, host and user-service states are left unchanged.
## Physical DGX P1a host admission result — 2026-10-14 (owner output)

On the original single Git checkout, source `9df9d0823762b16a1316847b7804e178f8b1a494`,
the operator ran the `plan` and `probe` subcommands **read-only**.
Plan output confirmed `START=NOT_IMPLEMENTED`, `STOP=NOT_IMPLEMENTED`,
`AUTO_START=DISABLED`, `USER_LINGER_CHANGE=FORBIDDEN`.
Probe output included:

```text
M1_BG_SUPERVISOR_IMPLEMENTED=NO
M1_BG_DOCKER_ACTION=NONE
M1_BG_USER_SERVICE_MUTATION=NONE
M1_BG_AUTO_START=DISABLED
M1_BG_HOST_PROBE=BLOCKED
M1_BG_BLOCK_REASON=USER_LINGER_NOT_ENABLED_OR_UNKNOWN
```

**PHYSICAL_DGX_BG_P1A_READ_ONLY=BLOCKED_AS_DESIGNED.** The original
probe combined absent/disabled/unknown linger into one reason, so do
**not** infer the exact `Linger=no` response from this transcript alone.
No XDG runtime-dir/tool/user-manager problem was emitted; this is not a
substitute for a full user manager / session lifetime qualification.
No user linger setting or service was changed, and no Docker action occurred.

The next source revision distinguishes **DISABLED** (explicit `no`)
from **UNKNOWN** (failed/unrecognized response), while still blocking
background launch. The operator may perform read-only
`loginctl show-user "$(id -u)" -p Linger` and
`systemctl --user show -p Version` for independent confirmation.
Enabling lingering is a **persistent host-policy change** and requires
separate explicit operator authorization; do not turn it on as part
of an automated test or Wizard invocation.
## P1a background supervisor: read-only user-service host probe (2026-10-14)

Source now provides `scripts/runtime/m1-background-probe.py plan|probe` and
Wizard Benchmark **11** plan / **12** read-only host inspection.
The probe uses **only** `loginctl show-user ... -p Linger --value` and
`systemctl --user show -p Version --no-pager`, plus local tool/runtime-dir
metadata checks; it does **not** start, stop, enable, install or edit any
user unit, Docker container, swap or managed release.
`M1_BG_HOST_PROBE=PASS_CAPABILITY_ONLY` means only that user linger and
a current user manager appear available; it **does not qualify actual
terminal-detached worker behavior**. Failure is fail-closed, including
missing linger, inaccessible user manager, unsafe runtime-dir or missing
tools. Do not enable linger silently, introduce autorestart, or change
user unit configuration while probing.

**Background start, stop, logs, durable PID/unit/token ownership and
interactive attach are NOT IMPLEMENTED.** Existing Foreground
`mazinb-m1.py run` remains unchanged and continues to require
TTY + explicit Wizard approval. Live DGX background lifecycle is NOT_RUN.
Source synthetic tests and GitHub CI are separate qualification gates.
## Proposed next stage: background/foreground supervisor — DESIGN ONLY

**Status:** source design only; no background engine, automatic model boot,
physical GPU start, or systemd unit change has been performed or qualified.
The already-tested interactive `run` mode remains the only live start path.

### Safety contract and lifecycle

1. Keep the default `foreground` operator path intact. A new `background`
   path must require Wizard default-NO consent, exact full protected old
   Docker ID, immutable manifest/image/release checks, and an explicit
   independent physical validation gate. Do not simply append `&`,
   `nohup`, `setsid`, `disown`, or close the current TTY: `run` demands a
   live TTY and currently relies on interactive `STOP` input.
2. Background ownership must be an actual **supervised service** with
   independently checkable PID / start time / unique session token /
   exact Docker ID / matching journal and monitor identity. Evaluate
   `systemd --user` availability, user bus and **linger** policy before
   choosing it; refuse background start if terminal-detached lifetime
   cannot be demonstrated. Do not change linger or install system
   services without explicit operator authorization.
3. Worker startup must be acknowledged **before** creating or starting
   the trial Docker. Preserve create-only Docker object, dedicated HOME
   and model caches, per-session locks, exact-ID detached fail-closed
   watchdog **armed before Docker start**, and the same RM/host/180s
   soak/API checks as foreground.
4. `status` and `logs` must remain read-only. Expose distinct modes
   for worker-present, worker-missing, candidate-running, monitor-stale,
   shutdown-journal-incomplete; never assume worker status from PID alone.
5. A `stop` request must require explicit default-NO approval, pin the
   session/candidate identity, never stop an unknown/replaced Docker,
   respect the exclusive benchmark lease, and durably write the final
   journal and exact `ExitCode`. If stop confirmation fails, preserve
   active evidence and the bounded watchdog; do not alter predecessor.
6. A foreground terminal may display/tail **logs** of a background
   worker, but detaching or closing that viewer must not affect worker
   lifecycle. `attach` is observer-only unless a separately authenticated
   explicit stop operation is requested.
7. SIGTERM, SIGHUP, SIGKILL, worker crash, lost user bus, host reboot,
   memory-protection shutdown and partial two-record journal writes
   each need synthetic tests plus targeted DGX physical tests. On
   SIGKILL or power loss reconciliation remains **fail-closed**;
   the existing exact-ID `reconcile` is the documented recovery path.
8. Background worker must have a bounded lifetime, no unexpected
   automatic restart, no hidden model start on boot, and no launch of
   concurrent historical A/B/managed GPU workloads.

### Qualification stages

`SOURCE_REVIEW` → `LOCAL_SYNTHETIC` → `GITHUB_CI` →
`ACTUAL_DGX_READ_ONLY` → explicitly approved `ACTUAL_DGX_FUNCTIONAL` →
`HOST_STABILITY` → `ACTUAL_DGX_BENCHMARK` if a new run is warranted.
Do not promote the feature as physically qualified after CI alone.

**Working directory:** reuse the original canonical Git checkout;
new worktrees are exceptional and must have an agreed removal gate.
## Physical 2026-10-14 13:40 KST M1 journal reconciliation — VERIFIED

Using verified runtime SHA `4776a6118decabc7cb511e4e60e7b157d3a57bec`,
Wizard menu 5 → 10 returned `M1_RECONCILE=RECORDED_STOPPED`.
Operator's separate status check verified `M1_SESSION_PHASE=stopped`,
`M1_RUNNING=False`, and `M1_EXIT_CODE=0`. Two `0600` original
journal backups (1,149 bytes each) were observed. No Docker start/stop/
remove was performed. Shutdown cause remains `UNDETERMINED`.
**RECOVERY_PASS**, but NOT a long-term host-stability qualification.
[Physical operator evidence](../scripts/benchmark/evidence/dgx-mazinb-m1-journal-reconcile-physical-20261014.md).
The earlier SOURCE_ONLY/RECOVERY_NOT_RUN section below is historical.

## 2026-10-14 update: successful physical benchmark, orphaned shutdown journal

Unique M1 reached exact API READY, completed 180s soak, inference smoke,
and pinned llama-benchy on one DGX Spark (vLLM v0.29, KV 16 GiB).
[Unmodified measurements and checksums](model-reports/mazinb.md):
TG128 23.11 ± 1.05 tok/s at PP512, 22.54 ± 1.68 tok/s at PP2048.
The M1 Docker subsequently exited, code 0, OOMKilled false, with no
protective stop marker. Its `active.json` remained `phase=stopping` after
terminal closure. This does NOT establish an operator STOP signal or long-term
host stability. Historical NOT_REACHED/NOT_MEASURED statements below refer
to older pre-success snapshots.

Wizard Benchmark **menu 10** runs `mazinb-m1.py reconcile` only after
explicit approval, with no Docker start/stop/remove. It validates
correct active/per-trial JSON owner and immutable identity, stopped exact
Docker ID/labels/image/restart policy, unchanged inactive predecessor,
monitor arm/heartbeat/termination evidence, absence of live supervisor/
watchdog, and exclusive benchmark lease. Two immutable byte-level `.bak`
files are saved before journal replacement. Unknown termination is written
as `UNDETERMINED` and host stability as `INCONCLUSIVE`.

**Implementation is SOURCE_ONLY; physical DGX recovery NOT_RUN.**
Do not start another M1 before verifying and reconciling its prior journal.
Background supervision is still a separate, unimplemented stage.


**2026-10-14** · Target DGX Spark / Qwen3.8 Flash Next · Branch
`feature/wizard-modular-phase1-20261014` / Draft PR #261.

## Implementation status and non-negotiable limits

The code implements an **opt-in** isolated M1 path under root `wizard.sh` ->
**5 Benchmark** -> **6 plan / 7 status / 8 current-host read-only preflight /
9 experimental physical start**. Menu 9 defaults to **NO**, requires
the complete inspected managed-Docker 64-character ID, a second exact
`START_MAZINB_16G` phrase, and sudo kernel evidence access. There is
**no automatic model start** from this repository change or from CI.

The source implementation is **NOT ACTUAL_DGX_LIVE_QUALIFIED**.
The first real M1 startup (2026-10-14) reached 26/95 safetensors shards,
then five low non-CMA free / swapgrowth samples triggered a supervised
memory-protection stop. The object was retained, Docker OOMKilled=false,
and no model READY or llama-benchy has yet been measured. Newer source
mitigates high-available swapgrowth false positives only for pinned M1
while retaining existing managed/A-B monitor behavior. Verify exact
commit/CI and read-only preflight before a fresh owner-approved run.
**Actual DGX M1 read-only preflight PASS** on 2026-10-14 at source SHA
`2dfa74dacedfe50fe1c28ca309939ed9d61b8123`, with protected Docker
ID and immutable release/image. Live launch, READY and llama-benchy remain
NOT_RUN; the next cache-isolation commit needs its own Git SHA verification
and source CI before any opt-in GPU load. Failures must be
documented without deleting prior A/B, models, managed Docker or evidence.

An M1 candidate is uniquely named
`qwen38-mazinb-m1-YYYYMMDDHHMMSS-8hex`, does NOT reuse either old
`qwen38-mazinb-kv-a` / `qwen38-mazinb-kv-b` and does not reuse
`qwen38-flash-next`. It runs on loopback **127.0.0.1:18889**, with
`vllm-orcarouter-v029:v1`, KV pool **16 GiB**, `MAXLEN=262144`,
MTP k=2, `MAXSEQS=3`, exact QSA, restart policy `no`.
Fresh attempts are independently named; all previous containers and
record JSON files remain preserved. The subsequent source hardening gives
each candidate a unique per-trial HOME for vLLM and FlashInfer host caches
rather than touching the user's existing canonical/experiment cache files.

See [physical M1 preflight evidence](../scripts/benchmark/evidence/dgx-mazinb-m1-physical-readonly-preflight-20261014.md).

## Safety contract — inspect code before first physical attempt

1. `preflight` validates strictly parsed managed manifest, completed
   OrcaRouter, monitor/protect ON, exact unchanged stopped old Docker
   and immutable image, immutable release, inactive systemd, idle
   lifecycle transaction, present mazinb checkpoint+image+swap, unique
   loopback port, no other *running* mazinb historical/M1 trial and
   sudo-available kernel log, then revalidates old identity.
2. The model is provisioned with `TRIAL_CREATE_ONLY=1`; the helper
   enforces a unique name and mazinb-specific Docker provenance labels
   and uses `docker create`, not `docker run`.
3. The independent exact-ID `monitor-runtime.sh` is detached,
   **armed before Docker start**, writes arm/heartbeat/stop evidence and
   protects memory. A monitor *catchable* exit stops only the exact
   labeled candidate. Its hard TTL is **7200 s**; process/host SIGKILL
   and power loss remain inherent unattended-recovery limitations
   requiring physical verification.
4. The foreground M1 supervisor holds a **shared lifecycle lock**
   for its entire session; lifecycle mutation commands require
   **exclusive** lock and cannot overlap. A separate B-terminal
   benchmark uses the explicit `m1-benchmark-lock.sh`
   shared-lifecycle / exclusive-benchmark pair after independent
   source-level `bench-admission` identity and current-host checks.
5. The M1-only `--swap-pressure-available-gib 12` requires an exact-ID
   `mazinb|m1` Docker provenance. It adds a 12-GiB non-CMA available
   margin condition to the 256-MiB swapgrowth protect path. Existing
   primary 10-GiB free gate, 8-GiB SwapFree, 2-GiB free warning,
   strict RM and exact-ID protection stay active. Managed and historical
   A/B monitor policy is unchanged. Source mitigation NOT live qualified.
6. Before READY: strict `/health` HTTP 200, *exact one* expected
   `/v1/models` ID and **180-second post-ready soak**. Any sampled
   `NV_ERR_NO_MEMORY` / `_memdescAllocInternal`, stale watchdog
   heartbeat, triggered protection, identity drift, stop or failing
   sudo kernel collection fails closed and stops only the new candidate.
7. After READY: Terminal A remains supervising, repeatedly checking
   Docker/monitor/kernel/immutable managed identity. **Type STOP**
   to end. STOP is deferred if Terminal B holds the benchmark lock.
   Session ends automatically no later than **5400 s of post-start
   supervision**, under the 7200-second watchdog maximum.
8. On normal STOP/error/interactive SIGHUP or SIGTERM, only the
   **exact pinned candidate ID** may be stopped. No `docker rm`,
   `docker image rm`, `docker system prune`, swap changes or
   protected managed service actions are implemented. Records are
   preserved under `~/.local/state/qwen38-spark/mazinb-m1/`.

**Limitations:** The Python supervisor and detached watchdog are
not equivalent to a boot-persistent independent systemd service.
If *both* are SIGKILLed, the host resets or Docker becomes unreachable,
the process-local guarantee cannot apply. A later separate recovery
implementation must classify orphan/stale sessions and enforce a
reboot-safe policy before declaring unattended operation qualified.
Do not treat M1 as proof of strict host stability without **physical**
qualification and complete NVIDIA RM inspection.

## Actual DGX read-only sequence — operator terminal A only

Verify the source tree SHA and run *only* the root Wizard.
In the Benchmark submenu choose **6** to review the plan,
**7** to inspect preserved active M1 state and **8** for the exact
managed predecessor ID/read-only M1 preflight. **Do not select 9**
until the verified preflight and owner-authorized physical window.

When the owner *does* explicitly select **9**, the prompt describes
real GPU load, defaults to NO and requires exact predecessor identity
and typed start phrase. Terminal A must remain connected and supervises
the candidate until it displays `M1_READY_FOR_BENCH`. No other
lifecycle, model-switch, uninstall, swap, prune or cleanup actions
may run during this session.

## Terminal B — after actual M1 READY only

Do not infer benchmark eligibility from historical 2026-10-02 trial B.
The B-terminal execution wrapper is:

```bash
bash scripts/wizard/m1-benchmark-lock.sh -- COMMAND [ARGS...]
```

`COMMAND` must be the separately verified pinned `llama-benchy`
invocation against `http://127.0.0.1:18889` for the exact
`mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4` ID. No unverified
upstream CLI flags are asserted in this document. The wrapper checks
the active session and revalidates it after the command. Terminal A
rejects voluntary STOP while B holds its exclusive benchmark lock.
The physical approval for any benchmark is separate from merely
starting M1; raw JSON/Markdown, SHA256, memory and kernel evidence,
source/model/image hashes and verified off-host backup remain mandatory.

## Historical warning — controlled vs managed B

The older source
`scripts/benchmark/evidence/mazinb-kv-ab-20261002.md`
explicitly states historical *isolated* 16 GiB B achieved
**FUNCTIONAL PASS / HOST-STABILITY PASS**, with API identity and
180-second soak. It also says a subsequent **managed** 16 GiB run
was **FUNCTIONAL PASS / HOST-STABILITY FAIL** after a startup
`NV_ERR_NO_MEMORY` event. This controlled-run success is *not*
a universal 16 GiB host stability guarantee. Strict RM policy
must remain on during M1.

## Acceptance ledger

| Gate | Current classification |
| --- | --- |
| New names/create-only labels/source controller | SOURCE IMPLEMENTED, CI validation required |
| Safe default NO / two-step live approval | SOURCE IMPLEMENTED |
| Foreground shared lifecycle lock / benchmark exclusive lock | SOURCE IMPLEMENTED |
| Exact-ID detached watchdog with bounded TTL | SOURCE IMPLEMENTED; boot-persistent guarantee NOT_PROVEN |
| Actual DGX M1 read-only preflight | PASS_READ_ONLY twice; second HEAD not included in pasted preflight, later live run exact SHA 72982e0 verified |
| Actual DGX initial new M1 start | STARTED, stopped by memory protection at 26/95 shards; Docker OOM=false |
| Actual DGX new M1 exact API READY | NOT_REACHED, source-only M1 swapgrowth mitigation pending physical recheck |
| Actual DGX fresh 180s soak / strict RM stability | NOT_RUN |
| Pinned llama-benchy JSON/report/SHA256/off-host backup | NOT_MEASURED / NOT_VERIFIED |
| A/B historical and managed Docker removal | FORBIDDEN / NOT_PERFORMED |
