# DGX two-terminal operation — wizard-managed lifecycle, separate benchmark

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


## OrcaRouter legacy / v0.29 A/B wizard plan staged (2026-10-13)

**Owner's new choice:** do not decide the final runtime image from source inspection alone. Benchmark **both** `vllm-skinny-tp1:v1` (legacy CPU-offload) and `vllm-orcarouter-v029:v1` (official vLLM v0.29 + PLE mmap/GB10 FLA/exact QSA) **sequentially** on the same OrcaRouter checkpoint/revision and a **16 GiB KV cache** starting point. These represent whole-runtime differences, not an image-only isolation. Measure actual load/READY, TTFT/TTFR, PP/TG, concurrency, failure rate and strict NVIDIA RM/non-CMA/swap stability with the same pinned `llama-benchy` workload, separate cold/warm repeats and preserved JSON/Markdown/SHA256/off-host backup. Prefer a stable image only **after** real qualification; both reports are NOT_MEASURED.

**Source implementation** at `394805e62999186afd56d085f279d87f4e4742af` (GitHub workflow pending at the time of documentation): A *newly provisioned DGX Spark OS with functional NVIDIA GPU/Docker* can use `./install.sh` to choose OrcaRouter baseline **v0.29** (provisional new-install default), or press **L** for Legacy; image builds locally if absent and the wizard handles pinned checkpoint download, compatible config, 128 GiB PLE swap, immutable release/service, monitor/protect (fresh OrcaRouter defaults enabled). The normalized equivalent CLI `--orcarouter-runtime legacy` reproduces L, only on fresh OrcaRouter installations. Missing OS/GPU driver/Docker/network prerequisites are **not** silently installed. Full real empty-host online installation has NOT_RUN.

**Existing protected DGX:** `./install.sh` → management menu **5** is a **read-only A/B plan preview**; **4 still cancels**. The installed legacy `vllm-skinny-tp1:v1` manifest/release and historical stopped Docker exact ID are never silently migrated or removed. The preview explicitly prints `WIZARD_ISOLATED_START=NOT_IMPLEMENTED`, no live API or RM acceptance, no benchmark. Actual dual-image isolated wizard launch/stop and exact-ID host safety is **NOT IMPLEMENTED**; never use direct experiment start or `systemctl restart` as a bypass. H38 is separately gated, not the fresh default. See [A/B comparison protocol](DGX-ORCAROUTER-AB-BENCHMARK.md) and [isolated trial design](DGX-ORCAROUTER-WIZARD-TRIAL-DESIGN.md). OrcaRouter checkpoint deletion is held **only for this test**; later review requires explicit approval and benchmark backups. PR #259 stays Draft/Open/Unmerged.


## Physical OrcaRouter wizard preview completed; both-terminal safety boundary (2026-10-13)

Real DGX `./install.sh --dry-run` on exact `a61b4569c5a6865dbeb9aa4ba4b21aeea12424e2` selected OrcaRouter in existing management, showed **legacy installed image** `vllm-skinny-tp1:v1` (different from independent experimental v0.29 image), enabled monitor/protect, immutable release systemd service; `WIZARD_DRY_RUN_RC=0` and protected old Docker/manifest unchanged. [Actual evidence](../scripts/benchmark/evidence/dgx-orcarouter-wizard-actual-dry-run-20261013.md). Terminal A wizard preview is now PASS. Terminal B remains **BENCHMARK_BLOCKED** because no live API or host/RM stability was verified. Next implement/test [safe opt-in isolated OrcaRouter run inside the wizard](DGX-ORCAROUTER-WIZARD-TRIAL-DESIGN.md), not direct experimental start and not a blind managed service restart. Separate approval required before any live startup or cleanup.


## Corrected owner scope — OrcaRouter FIRST and hold deletion ONLY for this test (2026-10-13)

The owner clarified that OrcaRouter is to be tested **first**;
the "do not delete OrcaRouter" rule applies **during this test to
avoid losing the model and benchmark opportunity**, NOT permanently.
Earlier permanent-retention language and a hard-coded model
delete refusal were overbroad and have been reversed. After the
test, OrcaRouter can be **considered** for cleanup but there is
no automatic permission: real benchmark evidence/raw JSON, MD
report, SHA256, verified separate backup, affected profile
dependencies, ownership, rollback identity and an approved
target-specific wizard plan are prerequisites. No deletions now.

Terminal A performs interactive wizard lifecycle and storage
preview. Terminal B performs benchmarks only after approved
wizard activation, real API identity and host/RM qualification.
No lifecycle mutation while B measures. New source helper
`scripts/benchmark/with-wizard-lock.sh -- COMMAND` acquires
the **existing** wizard operation lock for the entire child
and fails closed on absence/conflict (source/CI only, not
live admission). The currently stopped canonical Docker
predecessor and immutable release remain separately protected,
because the installed managed runner's commit can delete the
old object. The next safely admissible wizard step is
**OrcaRouter-focused interactive `./install.sh --dry-run`**.
Do not start a model or benchmark simply because a preflight
at exact SHA returned 0.

## Separation and operational ownership

| Stage | Terminal A — Wizard / storage | Terminal B — benchmark | Allowed concurrently? |
|---|---|---|---|
| A0: inspect | status, model registry, disk usage, deletion **previews** | inspect benchmark instructions, no API load | Read-only status operations |
| A1: lifecycle | **interactive** installer/model-switch wizard; remove wizard only with separate asset-specific authorization | **IDLE**, no bench or API load | **NO** |
| A2: admission | verify managed model identity, API health, host memory/RM and protection | bench preflight only, without launching any model | Read-only checks with stable service |
| B1: measured run | **read-only monitoring only**; never switch, install, remove, prune, update image/release | bounded pinned llama-benchy API workload, save raw JSON | Read-only monitoring + one measurement |
| B2: preserve | inspect target cleanup plan only | convert JSON to report, SHA256, verify an independent off-host backup | Only after benchmark has stopped |
| A3: optional cleanup | approved, narrowly scoped **wizard-facing** cleanup after backup, ownership and dependency review | **IDLE** | **NO** |

If cleanup of individual inactive models/images is not offered in the
wizard, **do not bypass it using low-level remove/retire/prune actions**.
Treat it as a wizard feature gap to implement/test before use, or obtain
a separately documented exception from the owner. A normal uninstall
wizard is a whole-managed-install lifecycle operation, NOT automatically
a safe way to delete an inactive intermediate H3/H4 checkpoint.

**Important current hazard:** the installed normal uninstall flow
removes the canonical Docker container object, even with no model purge.
Model switching can start a replacement runtime and commit a deletion
of the historical stopped predecessor. Thus an interactive wizard is
not itself permission to run those destructive paths. The protected
stopped predecessor ID and immutable release still need an explicit
disposition/isolation decision.

## Starting point — use read-only commands, NOT a model launch

Source checkout: `~/Workspace/llm/qwen3.8-flash-next-dgx-spark`.

### Terminal A (관리 / 정리 / 위자드)

From the project's original checkout, these commands display
information; they do not install, switch, delete or start a model:

~~~bash
cd ~/Workspace/llm/qwen3.8-flash-next-dgx-spark

./install.sh --list-models
./install.sh --list-backends
./scripts/manage-storage.sh status
./scripts/manage-storage.sh plan
./scripts/manage-models.sh assets
./uninstall.sh --dry-run
~~~

`./install.sh --dry-run` can also preview the interactive
wizard's plan; it should NOT be mistaken for a live model activation.
Use the default interactive `./install.sh` for future real model
install or switch **only after approval**, with a reviewed final plan;
use the default interactive `./uninstall.sh` for real uninstall
only after explicit destructive authorization, impact review and backup.
Never use `--yes` to skip an approval barrier. Do not execute
low-level `manage-models ... remove/retire` or
`manage-storage ... prune` as a way around the wizard.

### Terminal B (벤치마크 / 리포트)

Before live M1 approval, this terminal may inspect benchmark code and
write a plan, but **must NOT start models or invent speed results**.
After the wizard completes an owner-approved and separately
host-qualified activation, read-only status and loopback API checks:

~~~bash
cd ~/Workspace/llm/qwen3.8-flash-next-dgx-spark

./scripts/manage-service.sh status
curl -fsS --max-time 5 http://127.0.0.1:8888/health
curl -fsS --max-time 5 http://127.0.0.1:8888/v1/models
~~~

The API currently has **no newly qualified live M1**, so failed
readiness checks are expected and mean **do not run benchmark**.
Do not issue `./install.sh` or call any experimental
runtime `start` from Terminal B. The bench is only an
OpenAI-compatible API client on a *previously healthy* runtime.
`--model` and served name must come from **actual**
`/v1/models` output, not an assumed profile alias.
`eugr/llama-benchy` remains pinned to commit
`e9be344578cec17745066b220798b80a0d2686d3`, and
its installation/download needs prior operator approval.
Use the planned bounded `pp128 tg32 depth0 concurrency1` smoke
and then explicitly gated larger cases, not an automatic sweep.

Before a future measured run, ensure the bench window cannot overlap a
lifecycle mutation. The installer/uninstaller use a **flock** operation
lock, but the upstream bench client is not automatically protected by
that same lock. Merely opening two terminals offers no locking or
scheduling guarantee. A future benchmark admission/wrapper should
hold the same nonblocking operation lock for the **whole** workload,
check model/image/served-name identity before and after, and abort if
the managed runtime or host protection state changes. Do not claim that
this benchmark lock has already been implemented.

Preserve true upstream raw JSON, generated Markdown, SHA256, model
revision, image digest, served name, exact project source/release SHA,
prompt/workload settings, host/RM trace, and a SHA256-verified
**independent off-host copy**. Do not copy files from a model directory
scheduled for deletion as the only backup. Failed/unavailable profiles
remain NOT_MEASURED, not 0 tok/s. Nvidia and lychee888 local checkpoints
were absent in the latest actual DGX inventory.

## Hard safety gates and status as of 2026-10-13

- S1/S2/S3/S4 actual DGX read-only filesystem/link checks: PASS.
- Experimental M1 OrcaRouter v0.29 read-only preflight at source
  `5a14d169bbca93604b92e52dc1e548ed75cc5569`:
  RC=0, checkpoint/image ready, service inactive, canonical stopped,
  experiment container absent, port 8888 free, exact old Docker
  ID/status/image preserved. **No model start**.
- Full wizard install/profile switch/uninstall live end-to-end:
  NOT_QUALIFIED. The current installed old container and immutable
  release must not be deleted, restarted or replaced without approval.
- Independent old-Docker-safe M1 activation via **wizard** needs a
  designed/tested isolation path; don't work around it by starting an
  experiment container manually. Existing standalone runtime memory
  monitor could write the **managed** stop-reason state when given
  an experimental container name. Avoid mixed state.
- M1 live functional/host stability NOT_QUALIFIED; M3 live switching
  NOT_QUALIFIED, M4/H38 BLOCKED, actual destructive M2/D0 not approved.
- **All five model reports NOT_MEASURED**. No model/Docker deletion
  or storage reclaim approved; no hypothetical released bytes.
- PR #259 is Draft / Open / Unmerged. Preserve old snapshot, owner
  rules, S1–S4 evidence, and terminal-role policy in every handoff.

Never turn a read-only preflight PASS or wizard dry-run PASS into runtime
READY, host-stability PASS, model-benchmark data or deletion consent.
