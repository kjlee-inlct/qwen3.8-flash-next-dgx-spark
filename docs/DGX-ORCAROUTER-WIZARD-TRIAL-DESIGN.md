# OrcaRouter wizard-based isolated trial — next implementation design

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
