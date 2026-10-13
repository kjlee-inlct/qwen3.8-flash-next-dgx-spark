# DGX two-terminal operation — wizard-managed lifecycle, separate benchmark

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
