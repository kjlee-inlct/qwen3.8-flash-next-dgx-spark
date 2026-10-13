# OrcaRouter wizard-based isolated trial — next implementation design

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


**2026-10-13 status: DESIGN/REVIEW ONLY. Live M1 NOT_QUALIFIED.**

## Driver for the next change

[Actual DGX wizard DRY-RUN PASS](../scripts/benchmark/evidence/dgx-orcarouter-wizard-actual-dry-run-20261013.md)
at exact source `a61b4569c5a6865dbeb9aa4ba4b21aeea12424e2`
successfully showed installed OrcaRouter, image
`vllm-skinny-tp1:v1`, monitor/protect=enabled and unchanged
original stopped Docker object/installer manifest. But it did
not start the model. The prior independent preflight used a
**different** v0.29 image, `vllm-orcarouter-v029:v1`.

Source review: normal installed managed `service-runner.sh` on
successful start executes `runtime-transition.sh commit`,
which `docker rm -f`s the rollback previous container.
Some recovery routes restart the stopped predecessor.
Blind `systemctl start/restart` and invoking a normal actual
`install.sh` as a workaround are not safe alternatives.

## Required wizard feature — no raw start/stop CLI as operator entry

Implement a **separate interactive option** in installed-setup
management, conceptually `Run isolated OrcaRouter trial`.
This is a future feature, not a current UI option and not
permission to execute a trial.

1. The wizard shows the **exact experiment image** (not silently
   substituting the installed immutable legacy image), checkpoint,
   served model alias, port, Docker name, context/sequence/KV
   constraints, NVIDIA GPU access, swap/monitor thresholds and
   proposed maximum observation window. Require explicit confirmation;
   preview/dry-run makes ZERO changes.
2. Fail closed unless manifest `PHASE=complete`, active profile
   `orcarouter`, installed immutable release verified and protected
   predecessor exact ID, stopped state, `OOMKilled=false`, image ID
   verified; no canonical/managed service running, no trial container
   present, no port conflict, and no active lifecycle transaction.
   Guard against stale/cross-owner/remote Docker contexts.
3. Before creating the trial container, arrange a **separate
   experiment-state home**, log destinations, per-ID stop reason
   and watchdog using current non-CMA `MemAvailable/MemFree/CmaFree`,
   `SwapFree` and strict NVIDIA RM event detection. The existing
   shared monitor's `--protect` writes a managed lifecycle
   `runtime-stop.env` if called with default XDG state: this
   is NOT acceptable. Close the existing experimental startup
   sleep/monitor-attachment gap or abort.
4. A source-verified trial launcher creates only a new
   `qwen38-orca-v029` experiment container. The manager's existing
   Docker object and manifest/release/current symlink remain
   untouched. Watchdog must match exact new ID on each stop
   action; automatically preserve failed container and logs,
   not remove/prune. Host safety/abort wins over API readiness.
5. Validate `/health`, `/v1/models` **actual served name**,
   minimal small inference, then independently complete a bounded
   host stability/RM monitor window. A functional health PASS
   without a clean host-RM observation is not stable.
6. Only after a separately owner-approved trial launch AND
   accepted M1 health/stability may Terminal B run
   a pinned, bounded llama-benchy workload, guarded by the
   existing wizard operation lock for its full duration.
   Terminal A cannot switch/update/delete during benchmark.
   Collect original JSON, Markdown, SHA256, exact IDs and
   independent off-host verified backup.
7. On normal exit or failure, stop only the new verified trial ID,
   preserve forensic logs, confirm its name/container lifecycle,
   and compare protected old Docker ID/state/image, immutable
   release/current, install manifest SHA256, protect/swap and
   other resources before/after. No automatic old Docker
   object restart or removal.
8. Add synthetic fake-host tests: two-terminal contention,
   explicit cancellation, missing image, old Docker drift,
   port occupied, absent state, monitor failure before
   launch, RM OOM, race while starting, ctrl-C, false READY,
   manifest drift, cleanup audit mismatch. Preserve the
   existing normal wizard settings/change feature separately.

**Restrictions:** no unapproved runtime restart, new container,
model switch, selective deletion, prune, swap/monitor disable,
image rebuild, model download or PR merge. A successful
source CI run is not an actual DGX qualification.

## Current host evidence and next bounded operator action

The wizard audit at SHA `a61b4569c5a6865dbeb9aa4ba4b21aeea12424e2`
returned `WIZARD_DRY_RUN_RC=0`, `OLD_DOCKER_UNCHANGED=YES`,
`INSTALL_MANIFEST_UNCHANGED=YES`, with log
`/home/inlc/dgx-orcarouter-wizard-20261013-152129.log`.
The earlier experimental v0.29 preflight was RC=0 and
not a launch. Both results are real DGX read-only evidence.

Next implementation priority is the safe **wizard trial option**,
not repeating S1–S4 storage audits. Until coded, synthetically
tested, independently host-qualified and owner-approved,
do NOT ask the operator to start from raw script. The
existing installed older image is not to be conflated
with the experiment image. All five reports NOT_MEASURED.
