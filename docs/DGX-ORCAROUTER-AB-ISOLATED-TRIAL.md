# Isolated OrcaRouter A/B trial — experimental wizard mode

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
