# DGX two-terminal operation — wizard-managed lifecycle, separate benchmark

## Priority update: OrcaRouter FIRST, permanent model keep (2026-10-13)

OrcaRouter is the **first** model in the future wizard-managed live and
performance sequence. Owner states **never delete OrcaRouter**, even
after benchmarks, in any model/image/Docker cleanup or full-purge plan.
Existing old stopped Docker ID and immutable release protection remains
a separate constraint. Do not run an actual wizard transition until the
old-ID-safe path is reviewed. The safe next Terminal A action is the
interactive `./install.sh --dry-run` with OrcaRouter selected; Terminal B
stays idle because no qualified running model API has been demonstrated.

New `scripts/benchmark/with-wizard-lock.sh -- COMMAND ARGS...` source
helper holds the **existing** same-UID wizard operation.lock with
nonblocking exclusive flock for the entire future benchmark child.
Exit 3 on a busy lock, exit 2 on an absent/unsafe lock. Does not create
a competing lock file, model, image, package, or host service.
This is SOURCE/CI isolation only; direct Docker/systemctl use remains
outside the advisory lock, and API identity/host stability/explicit
approval remain required. Future usage, ONLY after qualified M1:
`./scripts/benchmark/with-wizard-lock.sh -- llama-benchy ...`.
Do not benchmark today merely because wrapper CI passes.


**Owner operating rule (2026-10-13):** All model **installation,
selection/switching and uninstall** must go through the interactive
**terminal wizard**, not direct Docker or experimental runtime scripts.
Use **two terminals** for (A) management/storage preparation and
(B) benchmark/measurement. Two windows do **not** mean two concurrent
operations on a one-GPU Spark.

This supersedes any historical runbook implying that invoking a raw
experimental script is the preferred way to switch or install a model.
Existing experimental helpers are reference/diagnostic code and are
NOT an alternative production wizard entry point. Keep canonical project
goals and the five model-card identities unchanged; H38 is a runtime
variant, not another model.

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
