# Isolated OrcaRouter A/B trial — experimental wizard mode

## ACTUAL_DGX Legacy A startup failed after Docker START — exited 137 (2026-10-13 ~18:16 KST)

Physical operator diagnostic after the first Legacy A isolated launch:
original protected managed container `f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`
still **exited, Running=false, OOMKilled=false, ExitCode=0**
at image ID `sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4`.
New A candidate `57eada965768b01eb412b10826ec4f0be9c4ed352abd87957c4ffbe932f27a56`
is **exited, Running=false, ExitCode=137, OOMKilled=false**.
The watchdog heartbeat was 1028 seconds old when read; its armed
file matched the exact candidate ID. Both `/health` and
`/v1/models` refused connections. Docker model logs show
vLLM `v0.1.dev20073+g8e685d198`, Legacy PLE offload worker,
16 GiB KV, two MTP speculation tokens, a **170.88 GiB
checkpoint on EXT4**, with ~38.68 GiB RAM available at
load start. Only initial 2/18 (GPU) and 1/18 (PLE) shard
progress was captured; no model READY, API, inference,
NVIDIA RM stability or benchmark success.

After termination, DGX shows ~118 GiB available and ~1 GiB
swap used, GPU idle, no matching RM/Xid strings in shown
kernel journal filter. These **post-exit** values cannot prove
lack of pressure during load. Monitor log tail includes many
copied Docker logs, which is strongly **consistent** with
the memory-protection path in `monitor-runtime.sh` (prints
`PROTECT stopping`, copies last 1000 container log lines,
then writes `monitor/runtime-stop.env` and invokes Docker
stop timeout 30 seconds); **NOT PROVEN** without early
`monitor.log` warnings and `runtime-stop.env`.
Exit 137 (SIGKILL) plus `OOMKilled=false` does not
establish container/kernel OOM or NVRM fault.

**NEXT GATE: READ-ONLY STOP REASON INVESTIGATION.**
Capture exact Docker StartedAt/FinishedAt; `monitor.log`
lines matching `WARNING memory margin`, `PROTECT stopping`,
`HEARTBEAT healthy`, `TRIAL WATCHDOG EXIT`;
`monitor/runtime-stop.env`; persisted trial records.
Do not start B, repeat A, weaken memory guards, clean up
images/models/containers, or benchmark until reason
is established. Previous old Docker is preserved;
OrcaRouter checkpoint no-delete is only for this test.
See [actual physical exit evidence](../scripts/benchmark/evidence/dgx-orcarouter-legacy-a-exit137-20261013.md).
PR #259 Draft/Open/Unmerged.


## ACTUAL_DGX OrcaRouter Legacy A isolated Docker START succeeded — NOT READY/NOT QUALIFIED (2026-10-13 17:57 KST)

The operator physically ran `./install.sh` using a clean detached worktree
at **exact source `48c517357cef2182be986c298a86ddfa1f4c74b0`**;
the wizard acquired its lifecycle lock, current installed OrcaRouter
management menu **6** → isolated A/B menu **2** (Legacy A) → entered
original exact old Docker ID → manually answered **Y** to isolated
Docker creation/start. Source CI #38369045129 had already succeeded
(955/955 tests + synthetic operator verification).
Actual DGX output **`AB_TRIAL_STARTED=UNQUALIFIED`**,
`AB_WIZARD_RC=0`, `OLD_DOCKER_UNCHANGED=YES`,
`INSTALL_MANIFEST_UNCHANGED=YES`:

- **New Legacy A experiment container exact ID:**
  `57eada965768b01eb412b10826ec4f0be9c4ed352abd87957c4ffbe932f27a56`,
  image `vllm-skinny-tp1:v1` (preflight image ID
  `sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4`).
- **Protected original managed Docker exact ID:**
  `f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`,
  unchanged according to post-command Docker status/image/OOMKilled comparison.
  Original `install.env` SHA256 unchanged by post-command comparison.
- Trial API `http://127.0.0.1:18888`; isolated monitor log
  `/home/inlc/.local/state/qwen38-spark/ab-trials/legacy-1791881886/monitor.log`.
  Wizard session log
  `/home/inlc/dgx-ab-legacy-start-20261013-175703.log`.
- Physical evidence is the operator-pasted terminal output, not a
  retrieved monitor/API/kernel log. **No `/health`, `/v1/models`,
  watchdog recent heartbeat, long-running NVIDIA RM stability,
  inference or llama-benchy result has been verified**. Even if the
  initial container reported STARTED, it could subsequently exit or
  hit the 3600-second monitored runtime limit. All model benchmark
  results remain **NOT_MEASURED**.

**Immediate priority:** while the trial is present, collect read-only
exact-ID `docker inspect`, watchdog heartbeat/monitor tail,
Docker logs, API `/health` and served `/v1/models`, current
non-CMA memory and `journalctl -k --since '2026-10-13 17:57:00'`
NVRM/Xid/RM error evidence. A stale watchdog or strict RM failure
blocks benchmark; use **wizard management 6 → 4** to stop only the
candidate when necessary, not direct unmanaged `docker stop`.
Do NOT run B or llama-benchy yet, restart the managed service,
delete anything, or merge PR #259. The OrcaRouter no-delete instruction
is limited to this test. Record the **first actual** Legacy A trial as
DOCKER_STARTED_UNQUALIFIED, not model READY/host stable.
[Original operator-supplied physical startup evidence](../scripts/benchmark/evidence/dgx-orcarouter-legacy-a-actual-start-20261013.md).


## ACTUAL_DGX: both OrcaRouter images passed strict read-only A/B admission (2026-10-13 17:18 KST)

The owner ran existing installed wizard `./install.sh --dry-run` on
detached exact source `980e1001ed90ee0b08b14dfddcf26797909e10c0`,
management **6**, then variant preflight **6 (Legacy A)** and
**7 (v0.29 B)** with the same exact old stopped Docker identity.
Both returned **`AB_PREFLIGHT=PASS_READ_ONLY`, RC=0**:
Legacy `vllm-skinny-tp1:v1` image ID
`sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4`;
v0.29 `vllm-orcarouter-v029:v1` image ID
`sha256:dba5d8af279fb85901e6d8911f1a59ecc45b669b0948ab8d01d7c7d1c5815734`.
Both observed old ID
`f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`,
manifest digest
`68d56e776214d8df25bd98c632d9749e5e174c3b9f5c671b2db080035d582f0f`,
installed immutable release
`ff67bab3c94d6992f61b9535836df97f03b9c022`, candidate API
`127.0.0.1:18888`. A log path
`/home/inlc/dgx-ab-preflight-6-20261013-171811.log`;
owner-provided output ends before the B log filename was printed.
This is **real physical read-only admission**, *not* model startup,
API READY, strict NVIDIA RM window, benchmark or off-host backup.
[Canonical physical evidence](../scripts/benchmark/evidence/dgx-orcarouter-ab-readonly-both-20261013.md).
**No runtime launch is authorized by a preflight PASS.**
Existing manifest/release/predecessor preservation remains mandatory;
PR #259 Draft/Unmerged; both benchmarks NOT_MEASURED.


**Implementation state:** Source-based, guarded lifecycle; NOT qualified on
the real DGX. Menu `./install.sh` → 6 is distinct from menu 5
(read-only plan). Neither changes the installed manifest/release.
Menu 6 offers status, start Legacy, start v0.29, and stop **only**
the captured trial container ID. `./install.sh --dry-run` 6 always
returns plan-only, never creates a candidate.

For a real start the wizard requires manual confirmation and exact
64-digit *stopped* old Docker ID. It acquires the usual lifecycle
lock; refuses incomplete/unstable install manifest, any pending
lifecycle transaction, absent release, active managed service,
wrong old stopped object, unexpected non-CMA memory/swap, missing
checkpoint/compatible config/image or occupied 18888 endpoint.

It invokes the shared qualified `serve.sh` configuration in
`TRIAL_CREATE_ONLY=1` mode. This **only creates** a new
`qwen38-ab-legacy` or `qwen38-ab-v029` container, with labels
binding exact predecessor, variant and image. Candidate remains
`created`. A separate trial-state pinned memory watchdog is
spawned and must write its **armed file**, proving matching exact
Docker ID, *before* the wizard calls Docker START by exact ID.
The watcher observes non-CMA available/free/swap and on pressure
stops only the trial's exact ID; its stop journal/logs are
stored under `ab-trials/` instead of shared managed state.

The wizard then waits for a watchdog heartbeat, rechecks old ID,
and returns `STARTED_UNQUALIFIED`. It never declares real
API/model readiness or NVIDIA RM safety based on mere Docker
start. On failure, it attempts to stop **the new exact ID only**,
preserving forensic Docker container, logs and state. Stop
leaves Docker object intact and verifies original old identity,
manifest checksum and immutable release. Same named trial cannot
be overwritten: reusing a stopped candidate requires an
explicit later evidence-backed disposition; no implicit prune.

The trial exposes localhost `127.0.0.1:18888` so it does not
occupy or route the managed API 8888. Terminal B can only
benchmark after actual model identity/API health, fresh monitor,
strict NVIDIA RM and host soak verdict (a source CI cannot
supply this). User must use pinned `llama-benchy`, retain
raw JSON+Markdown+SHA256 and verified off-host backups before
cleanup. No model/Docker deletion approved. OrcaRouter no-delete
hold applies **only for this test**, not permanently.

## Legacy → v0.29 handoff without model/Docker cleanup

Wizard stops A by its exact Docker ID and leaves the `qwen38-ab-legacy` container stopped, plus its per-run `record.json` and monitor logs. The next B trial may create only `qwen38-ab-v029`, provided A is cleanly stopped with matching provenance labels. An old B name may not be replaced, and a still-running or unknown A is fatal. No automatic deletion, prune or loss of prior evidence is part of the transition.

## Read-only host preflight from the same wizard

For first physical validation, run `./install.sh --dry-run` → existing installed management **6** → **6** (Legacy) or **7** (v0.29). Enter the already observed exact stopped predecessor Docker 64-character ID. The preflight validates installation/release/manifest, absent active managed service/transactions/other running trials, pinned image and checkpoint, endpoint 18888 and non-CMA/swap margins. It prints `AB_PREFLIGHT=PASS_READ_ONLY` with image SHA and manifest SHA; no Docker create/start, swap/config edits, monitor launch or benchmark. A PASS is admission only, **not** GPU/RM stability or model/API readiness.

## Watchdog exit and maximum trial time (2026-10-13 hardening)

For pinned A/B candidates, the monitor's catchable EXIT/SIGTERM/SIGINT path
verifies the **exact candidate Docker ID and trial ownership label** and, if
still running, stops **only that trial container ID**. The watchdog also
stops the candidate after **3600 seconds maximum** through the same
protected exit path. It never removes the container or touches the old
managed predecessor. Tests exercise exit-time protection and watchdog
ID mismatch; **SIGKILL, kernel/host resets and Docker-daemon outages
cannot be fully handled by a shell exit trap**, so source CI alone
must not be promoted to proven host safety. Actual DGX isolated trial
and RM stability remain NOT_PERFORMED pending operator qualification.

## Confirmed physical Legacy A protection stop and state reconciliation

The actual 2026-10-13 Legacy A launch ended after the watchdog detected
`noncmafree=914MiB` (below 2 GiB), **swapgrowth=14,096MiB**, and
five consecutive protection samples at 17:59:36 KST. The monitor wrote
`STOP_REASON=memory-protection` for the exact Legacy trial Docker ID.
The container subsequently exited with code 137 / OOMKilled=false
at 18:00:10 KST. This is a watchdog stop, **not a proven NVRM OOM**.
See [actual confirmed evidence](../scripts/benchmark/evidence/dgx-orcarouter-legacy-a-protection-confirmed-20261013.md).

The watchdog terminates independently of the wizard and so cannot
update the original wizard's `ab-trial.json`: it may still show
`phase=started_unqualified` even though the trial exited.
New wizard status (menu 6→1) reports the **actual Docker status,
exit code, forensic STOP_REASON** and reconciliation-needed flag
without changing state. Once evidence is preserved, wizard
**menu 6→4** can reconcile a *previously exited* protected A
as `stopped` **without Docker stop**, after strict exact-ID,
release and manifest safety checks; it captures the protected
stop reason and exit code and preserves original trial evidence.
Then, and only after another independent read-only B admission
and explicit approval, B may be trial-started.
