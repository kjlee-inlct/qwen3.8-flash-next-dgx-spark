# Isolated OrcaRouter A/B trial — experimental wizard mode

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
