# OrcaRouter legacy vs v0.29 A/B — single DGX, wizard-first

## 2026-10-13 17:59:36 KST — ACTUAL_DGX Legacy A protective stop CONFIRMED

The owner's second physical diagnostic resolved the first Legacy A
model-loading failure at source `48c517357cef2182be986c298a86ddfa1f4c74b0`.
**This is a verified MONITOR_MEMORY_PROTECTION stop, not an
unexplained exit 137 or proven NVIDIA RM OOM.**

- Candidate exact Docker ID
  `57eada965768b01eb412b10826ec4f0be9c4ed352abd87957c4ffbe932f27a56`;
  started **2026-10-13 08:58:06.343Z** (17:58:06 KST);
  monitor `mode=protect` started 17:58:07; at **17:59:36 KST**
  monitor emitted `protect=5/5`, then
  `PROTECT stopping qwen38-ab-legacy gracefully to preserve host stability`.
  `monitor/runtime-stop.env` explicitly contains
  `STOP_REASON=memory-protection`,
  exact `STOP_CONTAINER_ID`, timestamp
  `2026-10-13T08:59:36Z`.
  Docker finished **2026-10-13 09:00:10.252Z**
  (18:00:10 KST), **ExitCode=137**, **OOMKilled=false**.
  The ~34 s between stop request and final exit is consistent
  with Docker `stop --timeout 30` escalating to SIGKILL
  but the exact kill mechanism is not independently proven.
- Protection sequence includes recovery/reset at 17:59:18,
  then 17:59:27→36 five consecutive low-memory samples.
  Final margin **noncmafree=914MiB** (below 2 GiB)
  despite **noncma_available=23,163MiB** and
  `swapgrowth=14,096MiB` (~13.77 GiB, exceeds 256 MiB
  swap-activity gate). Thus warning/protect is triggered by
  low *immediately free* non-CMA with sustained swapping,
  **not** by the non-CMA available floor or swapfree<8GiB.
  Final `swapfree=132,391MiB`.
- Original old managed Docker
  `f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`
  remained exited clean (ExitCode 0), image unchanged.
  Real API `/health` and `/v1/models` refused;
  checkpoint loading incomplete, **no benchmark**.
  In shown kernel filter no NVRM/Xid/OOM matches,
  not a guarantee of complete hardware failure absence.
- **Stale recorded phase bug:** both
  `ab-trial.json` and per-run `record.json` retained
  `phase=started_unqualified` although the monitor already
  stopped A. The monitor operates asynchronously and
  cannot mutate the wizard's main journal. New code added
  actual Docker status, exit code and forensic STOP_REASON to
  read-only wizard status (6→1), and an exact-ID validated
  *already-exited* A reconciliation through wizard (6→4)
  that writes `phase=stopped` with `stop_reason` and
  `exit_code` **without another Docker stop or deletion**.
  Do not invoke the new reconciliation on the user's older
  worktree until the corrected SHA's CI is verified.
- **Next:** keep full Legacy logs/container,
  do not disable memory monitoring or change thresholds
  to force Legacy startup. After CI, reconcile A via
  wizard and repeat read-only v0.29 admission. Only then
  consider supervised B image loading as a *separate*
  real DGX test; no A throughput value can be reported.
  No benchmark, no cleanup, no PR merge. OrcaRouter
  checkpoint deletion hold is scoped to this test.
  [Canonical confirmed evidence](../scripts/benchmark/evidence/dgx-orcarouter-legacy-a-protection-confirmed-20261013.md).


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


## OrcaRouter A/B trial wizard implementation — SOURCE ONLY (2026-10-13)

**Progress since A/B preview:** A separate, experimental installed-setup
**menu 6** now offers **status / start Legacy / start v0.29 / stop**,
plus a plan-only response under `./install.sh --dry-run`.
A fresh DGX Spark OS with working NVIDIA driver/Docker/Git/Python/curl/sudo
still uses `./install.sh` to select v0.29 (default) or press
`L` (Legacy), automatically download pinned checkpoint and
locally build the selected runtime image if absent. These are
distinct workflows: neither is a pretext to change the existing
managed manifest, immutable release or stopped predecessor.

The A/B trial is **source-implemented but NOT ACTUAL_DGX
qualified**. Safety boundary: interactive choice and explicit
old Docker ID confirmation; shared lifecycle lock; complete
OrcaRouter manifest; service inactive; no conflicting lifecycle
transaction; protected predecessor exact 64-character ID,
`exited`, non-OOM and unchanged; original release and manifest
SHA retained; present pinned checkpoint/config/image; swap and
non-CMA memory margins; exclusive localhost trial API 18888.

Launch uses a new `qwen38-ab-legacy` or `qwen38-ab-v029`
container with immutable predecessor/variant labels, initially
**docker create, not start**; a separately persisted state
watchdog must be **armed to that exact Docker ID** before the
trial can be started. The watchdog uses its own stop journal and
non-CMA/swap monitoring. Failure/stop targets only the exact new
trial ID; Docker container/logs are preserved for evidence.
After stopping A, B can start only if A is cleanly stopped with
proper provenance. Neither trial changes installed image,
manifest, service, old Docker object or release pointer.
Ref: [isolated trial source runbook](DGX-ORCAROUTER-AB-ISOLATED-TRIAL.md).

**Crucial:** A successful GitHub Python/ShellCheck CI tests
source and synthetic mocks, NOT actual GPU load, model READY,
NVIDIA RM correctness, stability or benchmark. No actual
model start, pause or deletion has been performed in this chat.
The host's earlier read-only OrcaRouter wizard dry-run remains
the only verified physical wizard event. A/B results,
raw llama-benchy JSON/Markdown/SHA256 and off-host backup
remain **NOT_MEASURED/NOT_CAPTURED**. Before live use,
conduct an owner-approved exact-SHA read-only menu 6 preview,
check all host prerequisites and watchdog behavior; any
physical launch is a separate explicit operator decision.
OrcaRouter deletion HOLD applies **only during this test**,
not permanently. PR #259 remains Draft/Open/Unmerged.


**2026-10-13: source plan only, real A/B has NOT been executed.**

Both images must serve the same `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`
revision `c1209bda15a6bbc4c68b585e93d40c0d85f50306`.

| Treatment | Image | Runtime | PLE | KV starting limit |
| --- | --- | --- | --- | --- |
| A | `vllm-skinny-tp1:v1` | previous Flash Next skinny-GEMM | CPU offload | 16 GiB |
| B | `vllm-orcarouter-v029:v1` | official v0.29 with Spark PLE/FLA/QSA patches | mmap | 16 GiB |

This is a **whole-runtime** comparison, not image-only causal
attribution. The raw v0.29 experimental helper requests
24 GiB KV and MUST NOT be used directly for this comparison;
prior 24 GiB OrcaRouter runs had host RM OOM/protection issues.
Use a dedicated, qualified **wizard-isolated** launcher for
each image; that launcher is **NOT IMPLEMENTED** yet.

## Wizard user experience

- New DGX Spark OS with NVIDIA drivers, GPU-capable Docker,
  Git, Python3, curl, sudo, internet and sufficient storage:
  `./install.sh` → OrcaRouter 1 for provisional v0.29
  default, or enter `L` for Legacy. Image is built locally
  automatically if missing, model downloaded, config and
  128 GiB swap prepared, immutable release and service setup
  guided by wizard. No manual Docker build. Full empty-host
  online installation still requires physical end-to-end testing.
- Existing manifest: `./install.sh` → `5` for **A/B plan
  preview** only. Existing installed legacy image, stopped
  original Docker exact ID, release and manifest unchanged.
  Choice 4 is still Cancel; no A/B model startup in preview.
- Neither the provisional fresh default nor source test pass
  declares an operational winner. H38 decoder-specific image
  remains a separately gated experimental migration.

## Two-terminal sequential benchmark protocol

1. Terminal A snapshots exact old Docker ID/status/image,
   immutable release, installed manifest digest, monitor/protect,
   swap and free disk. A/B run never deletes or restarts the old
   container. Use two **distinct temporary trial container IDs**
   and isolated monitor state. Trial launch/stop via **wizard only**.
2. Run image A alone, confirm health + `/v1/models` actual
   OrcaRouter ID and bounded clean NVIDIA RM/non-CMA memory
   protection window. If instability arises, stop without
   running benchmark. Preserve failure evidence, not 0 tok/s.
3. Terminal B runs pinned `eugr/llama-benchy`
   `e9be344578cec17745066b220798b80a0d2686d3`
   under `scripts/benchmark/with-wizard-lock.sh`, same
   input prompts/context/output tokens/parallel requests,
   tokenization/sampling and limits. Record TTFR/TTFT,
   prompt processing, generation tok/s, throughput,
   error rate, load/ready time and host resources.
4. Stop only A's **new** trial ID, save raw JSON, Markdown,
   SHA256, service/container/host logs, exact image ID/command
   and verified independent off-host backup. Ensure memory/
   swap/GPU have settled before launching B.
5. Repeat B with identical workload. Optionally control
   cache/order effects via A→B→B→A and repeat cold/warm starts.
   Report functional and host stability verdict separately.
6. Only after both are actually stable compare metrics and
   select the preferred empty-DGX installer default.
   OrcaRouter deletion is held **during this test only**;
   afterward asset-specific cleanup still needs separate
   approval and complete backups.

Abort on strict `NV_ERR_NO_MEMORY`, `_memdescAllocInternal`,
old Docker ID drift, unexpected lifecycle transition, wrong
model/API identity, protection stop, or invalid memory monitor.
No direct `systemctl restart`, raw experiment `start`,
Docker prune, model deletion, H38 migration or PR merge.
