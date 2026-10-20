## 2026-10-20 — ACTUAL DGX checkout/model symlink identity and local checkout SHA

New owner-pasted **read-only physical DGX** command output established:

- checked-out branch `feature/wizard-modular-phase1-20261014`;
- `git rev-parse HEAD=b0ef37f9b756a86cc3670691e98a0b0798984d51`;
- `git status --short` printed no entries (clean worktree at observation);
- `model` is **actually a symbolic link**, not merely an inferred
  `UNSAFE_SYMLINK`, with raw absolute link destination
  `/home/inlc/Workspace/llm/qwen3.8-flash-next-dgx-spark/models/qwen3.8-flash-next-orcarouter`;
- `stat -c` reported symbolic link, device `66306`, inode `12097904`
  (link entry only; destination inode/type/presence NOT_OBSERVED).

Live remote GitHub verification showed branch and Draft/Open/unmerged PR #261
at `97a7db92095ce34b622ee5c7140e6bf46953125b`, initially **18
commits ahead** of the physical checkout, **0 behind**, with both Push and PR
CI SUCCESS for that exact remote SHA. This is a GitHub-only comparison, not
physical code synchronization. The local `b0ef37f9` version predates the
dedicated `legacy_model_link_identity` source change; latest remote source
can represent the exact link as `legacy-model-link`, but a live destination
must also have independently verified model ownership. The target directory's
presence, managed registry attribution/fingerprint, and full project asset
inventory are NOT_OBSERVED. No fetch/pull, model deletion, Docker mutation,
plan receipt creation, GPU run, or M2 execution is evidenced by the new
read-only commands. A separate scoped sync review and further read-only
target/registry checks remain necessary; **menu 5 remains prohibited**.

## 2026-10-20 — ACTUAL DGX uninstall Wizard preflight, phase=complete baseline

Owner-pasted DGX Wizard output (operator session; latest visible local
observation before this handoff) shows `Manifest: valid (phase=complete)`,
`Profile: orcarouter`, `Image: vllm-skinny-tp1:v1`, and
`Runtime: NOT_PROBED`. Main Wizard displayed uninstall submenu
1–6, including SHA-bound full reset plan/apply/postcheck.
The operator selected **Uninstall -> 5** with no prior saved receipt;
the Wizard refused with `A saved exact plan receipt is required`.
No apply/mutation occurred.

Then the owner selected **Uninstall -> 4**, answered `y` to
the read-only receipt-generation prompt, and hit the exact
`checkout/model` path preflight block documented below.
The empty/unsuccessful plan receipt was removed by the Wizard;
subsequent `PLAN_NOT_FOUND` was observed. Owner exited with
`Ctrl-C`. **No destructive command is shown or inferred.**
The actual DGX `git rev-parse HEAD`, local
`checkout/model` file type and symlink destination, the exact
project asset inventory, and all image/container/runtime live
states after the prompt are **NOT_OBSERVED** in this output.
Do not infer host checkout HEAD from the separately verified
GitHub remote feature branch.
## 2026-10-20 — ACTUAL DGX full-reset plan blocked on legacy checkout/model

Owner selected Uninstall -> 4, entered `y` for read-only SHA
plan creation; engine returned
`resource_status_not_safely_present:model:/home/inlc/Workspace/llm/qwen3.8-flash-next-dgx-spark/model`.
The receipt was not created (`PLAN_NOT_FOUND` independently
observed). No delete operation was invoked. Actual `model` file
type/target has **not** been physically printed.

GitHub SOURCE_ONLY fix introduces exact `checkout/model` link-only
plan/application treatment with full target text/inode checks and
requires a live pointed-at model to also be within the enumerated
project model set; refuses foreign/untracked linked targets.
Read-only DGX `ls -ld model; readlink model; stat -c '%F %d %i' model`
is required to establish this specific host preflight result.
No DGX mutations, M2 acceptance or protected PR merge.

## 2026-10-20 — integrated full project uninstall engine, GitHub SOURCE_ONLY

Created `scripts/lifecycle/full-project-uninstall.py` with bounded
read-only SHA-bound plan, exact-ID/full-fingerprint `apply`, and
independent post-removal project-scoped verification. Added Wizard
uninstall options 4/5/6, dedicated vLLM/FlashInfer v0.29 cache
inventory, and standalone synthetic safety/teardown fixture cases.
Model weights, first/second/third mazinb R2 Docker, protected
OrcaRouter, owned services/proxy, PLE swap, local benchmark and
forensic files are all part of the eventual full-reset plan,
**not protected retention exceptions**.

Safeguards include managed unit marker validation, full Docker ID
and experiment labels, canonical project mount verification, image
ID identity, foreign image/volume/bind references, strict scoped
filesystem trees, no symlink following, transition refusal, lock
inheritance for managed service deletion, exact SHA receipt plus
typed consent, and no generic prune. Plan generation and fixture
testing do not mutate the DGX.

**Operational status: SOURCE_ONLY; no actual DGX command run; M2
destructive host E2E NOT_RUN/NOT_QUALIFIED.** The current physical
checkout is not assumed to match GitHub. CI outcome must be tied
to exact HEAD separately. PR #261 must remain Draft/unmerged.

## 2026-10-20 — ACTUAL DGX R2 Stage K: second/third named RM classification and Docker startup evidence

New operator-pasted physical evidence resolves the previously missing
**third named-journal detail**. Both second and third R2 named JSONs show
`phase=failed_stopped`, `exit_code=137` and
`detail=M1Error: NVIDIA RM memory allocation error`. The matching
full Docker IDs were independently label-checked and reported
`STATUS=exited RUNNING=false OOM=false EXIT=137`.
Two monitor extracts reported `STOP_MARKER=ABSENT_OR_UNSAFE`,
warnings consistently `protect=0/5`, and monitor termination only
after the Docker was no longer running. These outputs do not prove
how SIGKILL was delivered. Host kernel RM/oom lines remain
**NOT_OBSERVED**: both sudo journal queries required a password.

Third Docker showed 95/95 checkpoint shards, 79.42 GiB model
load, 16.0 GiB KV cache, finished CUDA graph capture and engine
initialization at 2026-10-20 07:24:54 KST; Docker finished
2026-10-20 07:25:14 KST. This is **not API READY** and no
third-run inference, smoke, 180s soak or new benchmark was demonstrated.
First R2 READY/smoke/soak PASS remains separately valid.

These are owner-provided DGX console observations, not assistant
host execution or proof of container-attributed kernel RM failures.
[Full exact logs and provenance (Stage K)](../scripts/benchmark/evidence/dgx-mazinb-r2-download-preflight-physical-20261019.md).
Owner's complete-uninstall scope now includes OrcaRouter, all R2
containers/model, swap, service/proxy and *local forensic journals
and archives*; generic `--purge-all` remains insufficient.
Do not launch a further GPU trial or destroy assets before the
exact-ID, shared-dependency and bounded source-only cleanup process
is implemented and separately approved. M2 remains NOT_RUN.

## 2026-10-20 — owner complete-reset scope explicitly includes protected OrcaRouter and R2 evidence

The owner confirmed that complete project removal MUST delete OrcaRouter,
all mazinb R2 experiment Docker and model assets, other project
NVIDIA/Hybrid checkpoints, project swap, service/proxy, state/releases,
and all locally retained forensic journals, private archives, and benchmark
results. No protected-project-asset exemption applies in complete mode.

Read-only inventory now additionally covers HOME/models, checkout/models,
external benchmark root, retirement archives, repo-local evidence, and
project-specific HF checkpoint caches. Synthetic exact-ID fixtures include
the OrcaRouter predecessor and all three known mazinb R2 trial Docker IDs.
These are inventory candidates, not hardcoded deletion IDs. External apps,
system swap, drivers and remote GitHub history remain outside local reset.
Complete destructive apply remains NOT_IMPLEMENTED; M2 remains NOT_RUN.
No physical DGX change was performed.

## 2026-10-20 — SOURCE_ONLY full-project uninstall inventory in Wizard; destructive M2 blocked

After reviewing the actual `uninstall.sh`, managed service/proxy/swap
helpers, cumulative ownership rules and retained R2 records, a separate
**read-only** full-project removal coverage module was added at
`scripts/lifecycle/uninstall-inventory.py`. Main Wizard **2. Uninstall**
now separates **1. Project asset inventory (read-only)**,
**2. Existing managed uninstaller (separate confirmation)** and
**3. Baseline-bound post-removal verification (read-only)**. The existing destructive
uninstall is unchanged; no blanket full-project deletion action was added.

Source scope: strict manifest and cumulative registry parsing; owned versus
unverified checkpoint/image reporting; project-model and state/release
enumeration including stopped R2 journals; project-named/labelled exact-ID
Docker containers and tagged images/volumes; systemd unit files plus
LoadState/ActiveState; PLE swap file plus exact fstab marker; and explicitly
excluded shared HF cache/system Docker and non-project resources.
The module never creates/stops/removes Docker, downloads models, changes
services/swap, or writes its own files. JSON plan + same-scope baseline
verification are available; **no observed residual within bounded scope**
is not a claim of complete OS factory restoration.

Synthetic tests `tests/test_uninstall_inventory.py` cover fail-closed
registry/manifest anomalies, Docker ID, resource provenance, unit/swap/volume
inventory, baseline residual detection, limited clean-postcheck and unknown
data. Documentation: [project uninstall coverage](PROJECT-UNINSTALL-COVERAGE.md).
Actual protected DGX was **NOT TOUCHED**; no physical pre/post removal
has been verified. **M2 destructive end-to-end remains NOT RUN**, and
historical five/17 exact-ID retirement code must never be reused for
new R2 trials. Complete project cleanup still needs per-asset ownership,
archive-before-retire, independent approvals and disposable-host acceptance.
PR #261 remains protected Draft (no Ready/Merge authorization).

## 2026-10-20 — SOURCE_ONLY mazinb R2 first-READY versus third-trial runtime file parity

GitHub read-only comparison of the physically reported source SHA for the
first successful R2 API/180-second soak/inference-smoke trial
(`4612045c11ce47e52606794d63daede4cb35ac82`) and the last
physically printed DGX checkout SHA during third-trial diagnosis
(`f24fa284ba51000ece317227df26ff32e6f24ecd`)
shows identical Git blob contents for:

- `scripts/runtime/mazinb-m1.py` — blob `60b2ebf1105ffcd47b373c16b57df8461ab30a8e`;
- `scripts/runtime/monitor-runtime.sh` — blob `017451b75b69da00bb10d9aec591a161a56862dc`;
- `scripts/serve.sh` — blob `b6cd92b1bd58160576624d9c645528fe80af450d`.

`scripts/wizard/benchmark-menu.sh` **did** change between those
commits (Wizard route/UI changes require separate review). The GitHub
compare places the third physical checkout 56 commits ahead of the first,
without changes to the three runtime files named above. This is
**GitHub SOURCE_ONLY file parity**, not an attestation of the exact
runtime checkout at second-trial launch, image binary, memory/swap
trajectory, model cache or driver state. The second trial's physical
source SHA was not captured. It reduces support for a direct regression
in those three files but does **not** establish a failure root cause.

The actual Stage J state still stands: third trial `failed_stopped`,
Docker exited with code 137 and `OOMKilled=false`; second trial's
host-wide RM classifier matched, but original kernel lines and third
named-journal `detail` remain **NOT_OBSERVED**. Next step remains
**read-only**, bounded exact-trial journal, monitor, Docker and kernel
correlation; no further GPU attempt or runtime/threshold change.
[Original physical evidence Stage H–J](../scripts/benchmark/evidence/dgx-mazinb-r2-download-preflight-physical-20261019.md).

## 2026-10-20 — ACTUAL DGX third mazinb R2 failed_stopped, exact Docker exited/retained; RM cause pending

**New owner-pasted physical DGX read-only evidence, superseding only
the older Stage I `M1_RUNNING=True` *point-in-time snapshot*.**
The third separately identified candidate
`qwen38-mazinb-m1-20261019221159-90ee9851`,
exact Docker ID
`bee2e3819b7c2fef595357b61ea23934dd8969215a7fe2b957678bbf98eb1dd8`,
now returned `M1_SESSION_PHASE=failed_stopped`,
`M1_RUNNING=False`, `M1_EXIT_CODE=137`,
`M1_DOCKER_REMOVED=NO`. Exact Docker inspect:
`STATUS=exited RUNNING=false OOM=false EXIT=137`.
Process inspection (`pgrep -af 'mazinb-m1.py|monitor-runtime.sh'`)
returned no supervisor/watchdog at that observation.
The script's identity-bound manual-stop guard appropriately
printed `STOP_NOT_PERFORMED_IDENTITY_OR_STATE_MISMATCH`
because the exact labeled candidate had
`Running=false` already. **No additional stop required.**

**Third trial monitor tail 2026-10-20 07:17:50–07:25:14 KST:**
recurrent `noncmafree` ~0.9–2.0 GiB, high but decreasing
`noncma_available` (low 17,240 MiB, 07:24:58),
cumulative `swapgrowth` up to 3,482 MiB
(07:23:12) and `swapfree` ≈142,945 MiB.
Lowest displayed `noncmafree=899MiB` (07:24:37)
occurred at a **different timestamp** from lowest
available. Warnings consistently show
`protect=0/5` and the final line at
07:25:14 was `container is no longer running;
monitor exiting`, with no `PROTECT stopping`
in the **provided 35-line tail**. Source policy
gates low-free + swap-growth protection on
`noncma_available<12GiB`; displayed available
was above that. Do **not** infer from this fragment
that the watchdog itself sent SIGKILL or that
no earlier stop event occurred. Docker exit 137
indicates SIGKILL; `OOMKilled=false` does not
disprove NVIDIA RM allocation failure or prove a
particular terminator. Third-trial failure
`detail`, full monitor record, kernel RM events
and Docker logs remain **NOT_OBSERVED**.

**Second R2 failed trial retained per-trial journal
independently read and validated** (do not consult
the rolling third-trial `active.json` for it):
`~/.local/state/qwen38-spark/mazinb-m1-reinstall/
qwen38-mazinb-m1-20261019065452-e70d6233.json`;
exact Docker ID
`68cd243882bf117dbccdfad577cfdec7a95063ee8f2a96dbe6bcf51cfd8554e7`,
`phase=failed_stopped`,
`detail=M1Error: NVIDIA RM memory allocation error`,
`exit_code=137`,
`kernel_since=2026-10-19 15:54:52`,
`started_at=2026-10-19T06:54:52.735564+00:00`,
`updated_at=2026-10-19T07:04:33.845050+00:00`.
The `kernel_since` parameter uses local host-wall-clock
time (KST). The code checks **host-wide**
`journalctl -k` for `NV_ERR_NO_MEMORY` or
`_memdescAllocInternal` after the recorded instant;
the actual kernel lines and attribution have **not
been provided**. `failed_stopped` is a protected
failure, not successful benchmark admission.

**Current objective is forensic attribution, not another
benchmark/reinstall or model change.** Both newer
failed trial Docker objects and exact per-trial
journals are preserved. First R2 trial still
independently proved `M1_READY_FOR_BENCH`,
180-second soak and inference smoke PASS and
stopped normally, **but R2 throughput remains
NOT_MEASURED** across all three trials.
Pinned `llama-benchy 0.4.1.dev1+ge9be34457`
has been installed on the actual host, no longer
a current blocker. Exact latest physically printed
checkout SHA was
`f24fa284ba51000ece317227df26ff32e6f24ecd`
(2026-10-20 first diagnosis), not the newer
GitHub documentation-only HEAD.

**Next safe order:** only read per-trial named
`qwen38-mazinb-m1-20261019221159-90ee9851.json`
to obtain actual third `detail/kernel_since`
and exact-ID `monitor/runtime-stop.env` if present;
capture **bounded** matching NVIDIA kernel lines
for both second and third exact time windows;
read only relevant tail of each
`monitor.log` and `docker logs` plus exact
Docker `FinishedAt/OOMKilled/ExitCode`.
Correlate timestamps and distinguish NVIDIA RM,
Linux OOM, watchdog protect, controller stop
and SSH/session failure **without inventing
causality**. No changes to watchdog/KV, swap,
cache, GPU runtime, Docker, systemd, protected
OrcaRouter or DGX source before forensic
classification. Never use `set -e`/`exit 1`
inside SSH read-only diagnostic copy/paste
where a mismatch would log out the operator.
Do not restart the model or measure benchmark
until a separately approved corrective action.

[Physical immutable evidence Stage I and
newer Stage J](../scripts/benchmark/evidence/dgx-mazinb-r2-download-preflight-physical-20261019.md).
The older Stage I running snapshot remains in history
but is no longer the latest known host state.

## 2026-10-20 — ACTUAL DGX unexpected active THIRD R2 candidate during RM forensic commands; SSH logout

Owner's DGX console, operating clean local HEAD
`f24fa284ba51000ece317227df26ff32e6f24ecd`,
attempted read-only postmortem on Stage H second
failed R2 Docker
`68cd243882bf117dbccdfad577cfdec7a95063ee8f2a96dbe6bcf51cfd8554e7`.
However the rolling `mazinb-m1-reinstall/active.json`
now identified a **THIRD** trial:
`M1_SESSION_PHASE=started_unqualified`,
`M1_SESSION_NAME=qwen38-mazinb-m1-20261019221159-90ee9851`,
`M1_CONTAINER_ID=bee2e3819b7c2fef595357b61ea23934dd8969215a7fe2b957678bbf98eb1dd8`,
`M1_RUNNING=True` (only at sampled instant).
The new trial name timestamp is 2026-10-20
07:11:59 Asia/Seoul. No user report of
approval/READY/new smoke/RM safety/STOP/benchmark
for this third trial was included. Do **not** assume
the controller is still running after SSH logout.

A pasted shell diagnostic matched active journal against
the **second trial** ID/name; mismatch correctly produced
`WRONG_TRIAL_RECORD`. Because the user's command ended
in `|| exit 1`, the subsequent `로그아웃` / SSH
disconnect may simply be the interactive shell exiting.
This log is **not** proof of DGX reboot/host crash.

**Immediate next step is safety, NOT a third benchmark or
new GPU start**: reconnect and inspect exact third
Docker ID status/labels, M1 current journal,
controller/watchdog process and monitor log *without
exit-on-error*, retain per-trial journal of second
failed R2 run for original kernel RM forensics.
If still supervised, stop via live Terminal A.
If orphaned, stop only after matching the third
Docker full ID/name/variant/predecessor labels.
Never touch old OrcaRouter or old A/B and M1
Docker, or run `git pull` while current M1
possibly active. No latest physical third-trial
post-SSH state has been supplied.
[Physical evidence Stage I](../scripts/benchmark/evidence/dgx-mazinb-r2-download-preflight-physical-20261019.md).

## 2026-10-19 — ACTUAL DGX second protected mazinb R2 trial stopped on NVIDIA RM error; benchy now installed

**Actual later physical user transcript** shows a *second*
separately owner-approved Wizard **5→24→4** isolated
mazinb M1 trial with candidate
`qwen38-mazinb-m1-20261019065452-e70d6233`;
new exact Docker ID
`68cd243882bf117dbccdfad577cfdec7a95063ee8f2a96dbe6bcf51cfd8554e7`.
The controller emitted
`M1_CANDIDATE_STARTED_UNQUALIFIED`, then
`M1_STOPPED_EXACT_ID=68cd243882bf117dbccdfad577cfdec7a95063ee8f2a96dbe6bcf51cfd8554e7`,
`M1_DOCKER_REMOVED=NO`, and
**`M1_BLOCKED=NVIDIA RM memory allocation error`**.
No `M1_READY_FOR_BENCH`/new inference smoke/180s
soak was emitted during this second trial, and no
model throughput result was generated.

Meanwhile, operator Terminal B **now has** the pinned
`llama-benchy 0.4.1.dev1+ge9be34457`
and PATH points to isolated user venv. This eliminates
the earlier missing-tool blocker, but benchmark wrapper
correctly **rejected failed trial** with
`M1_BLOCKED=M1 is not admitted for benchmark` and
`BENCH_M1=BLOCKED attestation_failed`.
No safety check was bypassed.

**Critical code-level limitation of error label:**
`scripts/runtime/mazinb-m1.py` verifies host-wide
`sudo -n journalctl -k --since <kernel_since>` and
fails if either `NV_ERR_NO_MEMORY` or
`_memdescAllocInternal` appears. The stdout proves
a matching message was detected in that time window,
but does not by itself link it to this candidate nor
distinguish VRAM allocation, RAM pressure, Xid or
a host-wide other-device event. Need actual matching
kernel timestamps/text + exact Docker state
`ExitCode`/`OOMKilled` + same trial `monitor.log` +
bounded model loading stderr + current retained journal.
**NO THIRD GPU RESTART** until root cause is classified.

The previous *first* R2 trial on the same DGX
**passed exact API, 180s soak and inference smoke** and
stopped cleanly (Docker
`82b143c4adad9fd785aad38590ed6738de52a6a06b06a4a9bdc07118ceb40424`).
That physical success must not be erased nor treated
as proof of reliability under the second load:
two separate episodes with different exact IDs.
Both stopped candidates intentionally retained;
original protected OrcaRouter/older M1 archives remain
untouched. New installed tool does not change these
classifications.

**Next safe action:** read-only failed session
`status --session-slot reinstall` (expect
`failed_stopped`, **not** normal `stopped`);
read per-trial logs and `journalctl -k` matching
RM lines since its `kernel_since`. Do not manually
mutate journal, disable monitor, adjust swap/KV/port,
delete Docker, upgrade source on DGX before collecting
forensics, or invoke a third trial.

[Physical Stage H evidence](../scripts/benchmark/evidence/dgx-mazinb-r2-download-preflight-physical-20261019.md).
This text was written to GitHub only, NOT on DGX.
Current local DGX SHA for second run **not printed**
in its pasted transcript; do not infer it from
remote HEAD. PR #261 Draft/unmerged.

## 2026-10-19 — ACTUAL DGX mazinb R2 protected exact-ID STOP completed, Docker preserved

**Owner's latest physical Wizard Terminal A output:** after a
successful isolated R2 vLLM API/model exact match, protected
180-second soak and real inference smoke, and separate
Terminal B safely refused to benchmark due to absent pinned
`llama-benchy`, the owner entered `STOP`. Program printed:

```text
M1_STOPPED_EXACT_ID=82b143c4adad9fd785aad38590ed6738de52a6a06b06a4a9bdc07118ceb40424
M1_DOCKER_REMOVED=NO
```

**Actual exact-ID stop PASS**, candidate intentionally
retained for forensic evidence, no model/container cleanup.
Earlier Terminal A reported
`M1_READY_FOR_BENCH=http://127.0.0.1:18889`,
`M1_INFERENCE_SMOKE=PASS_NO_GENERATED_TEXT_PERSISTED`
and exact served mazinb model; this functional success
stands. **R2 PP/TG/TTFT new measurements remain
NOT_MEASURED** because the required CLI was unavailable.
Old historical measured 2026-10-14 evidence remains
unchanged. No persistent managed systemd service
qualified.

Latest actual DGX checkout was clean
`4612045c11ce47e52606794d63daede4cb35ac82`;
newer remote GitHub documentation and tool-prep HEADs
were **not** used in this live trial. Although stdout
confirms exact stop, it does not display independent
journal `M1_SESSION_PHASE=stopped` and
`M1_RUNNING=False`. **Next operator read-only
verification:** `python3 -B scripts/runtime/mazinb-m1.py
status --session-slot reinstall`. Only after
confirmed stopped/no running candidate and clean
worktree, guarded fast-forward to successful remote
GitHub HEAD, then optional user-approved isolated
pinned `llama-benchy` install via Wizard
**5→24→5**; a *new* protected session must be
separately approved before actual benchmark.
Do not delete protected historical/OrcaRouter models,
Docker or old evidence.

[Latest permanent actual DGX Stage G receipt](../scripts/benchmark/evidence/dgx-mazinb-r2-download-preflight-physical-20261019.md).
PR #261 stays Draft/unmerged.

## 2026-10-19 — ACTUAL DGX R2 benchmark blocker pinned tool absent; sudo cache restored

Owner's actual DGX read-only file search for `llama-benchy`
under user local bin, uv tools, pipx venvs, and llm workspace
returned **no executable**. The later attempted
`BENCHY_PATH=/실제로/확인한/경로/llama-benchy` was
a copy of the assistant's example placeholder and **not
a discovered path**, so shell returned file not found.
First subsequent strict reinstall-slot benchmark wrapper was
blocked for `sudo -n` password cache expiration
(`M1_BLOCKED=... sudo: 암호가 필요합니다`). After `sudo -v`,
the entire exact-ID pre/post admission and kernel RM
check **PASSED**, but `MAZINB_R2_BENCH=
BLOCKED_PINNED_LLAMA_BENCHY_MISSING`,
`BENCH_COMMAND_RC=2`. **NO actual new PP/TG
measurements or new JSON**. Protected inference READY
evidence remains valid. Actual Terminal A STOP/expiry
has not yet been provided.

**GitHub source-only follow-up:** added
`scripts/wizard/llama-benchy-setup.sh`,
a default-NO/typed `INSTALL_PINNED_BENCHY`
user-scoped venv installer at pinned upstream
`e9be344578cec17745066b220798b80a0d2686d3`
with expected CLI version `0.4.1.dev1+ge9be34457`.
Wizard **5→24→5** exposes the plan and explicit
install after the experiment STOP. It refuses to install
while the lifecycle shared lock is held, project Docker
is active, or M1 localhost API port is listening,
never uses sudo or system package install, writes only
separate `~/.local/share/qwen38-benchmark-tools/`,
and records Python dependency freeze. Synthetic-only
tests added. **NOT EXECUTED on DGX**, final CI
and exact host compatibility still need confirmation.
No Git source sync during the live R2 session; later
clean worktree sync only after confirmed stopped.
Do not rerun placeholder `BENCHY_PATH` or start a new
GPU candidate without separate owner authorization.

[Physical Stage F receipt](../scripts/benchmark/evidence/dgx-mazinb-r2-download-preflight-physical-20261019.md).
PR #261 remains Draft and unmerged.

## 2026-10-19 — ACTUAL DGX R2 benchmark admission PASS twice, tool missing, NO throughput

**Physical Terminal B supplied by owner** against same
R2 `M1_READY_FOR_BENCH` isolated mazinb model,
exact new Docker
`82b143c4adad9fd785aad38590ed6738de52a6a06b06a4a9bdc07118ceb40424`,
`http://127.0.0.1:18889`. The
`--plan` action was no-API/no-host-mutation;
`scripts/wizard/m1-benchmark-lock.sh --session-slot reinstall`
acquired both shared lifecycle and exclusive bench lease,
then emitted:

```text
M1_BENCH_ADMISSION=PASS_SESSION_PINNED_READ_ONLY
M1_BENCH_HOST_RM=NO_MATCHING_EVENTS_IN_CURRENT_WINDOW
BENCH_M1=ATTESTED_SHARED_LIFECYCLE_EXCLUSIVE_BENCH
MAZINB_R2_BENCH=BLOCKED_PINNED_LLAMA_BENCHY_MISSING
M1_BENCH_ADMISSION=PASS_SESSION_PINNED_READ_ONLY
M1_BENCH_HOST_RM=NO_MATCHING_EVENTS_IN_CURRENT_WINDOW
BENCH_COMMAND_RC=2
```

The benchmark tool is not currently on operator PATH;
it requires the pinned version `0.4.1.dev1+ge9be34457`.
This is a **benchmark tooling gate block**, not a vLLM,
Docker/host-RM or inference failure. Both actual pre/post
model admission checks PASSED. No fresh throughput or
TTFT was measured; no result JSON or SHA256 output
was created by this refused payload.

**Next while Terminal A remains live:** bounded read-only
search for *existing* pinned `llama-benchy` in
known user tool/venv paths. Do not sync Git, install
packages, mutate service/cache or launch a second model.
If no matching executable exists, complete observed
model trial by the protected controller's `STOP`
or automatic expiry, then install/verify the
pinned benchmark tool **between** separately approved
GPU sessions. Keep archived 2026-10-14 M1 measured
numbers and all R2 API/soak/smoke evidence unchanged.

[Permanent physical evidence, Stage E](../scripts/benchmark/evidence/dgx-mazinb-r2-download-preflight-physical-20261019.md).
PR #261 remains Draft and unmerged; remote docs
have newer HEAD than the live clean DGX
`4612045c11ce47e52606794d63daede4cb35ac82`.

## 2026-10-19 — ACTUAL DGX mazinb R2 smoke/180s soak/API READY_FOR_BENCH

**Owner's later protected experiment console: actual physical DGX
evidence at clean local HEAD
`4612045c11ce47e52606794d63daede4cb35ac82`.**
The same separately approved isolated candidate
`qwen38-mazinb-m1-20261019043708-479dfc86`
now emitted `M1_INFERENCE_SMOKE=PASS_NO_GENERATED_TEXT_PERSISTED`,
`M1_READY_FOR_BENCH=http://127.0.0.1:18889`, exact
`M1_SERVED_NAME=mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4`,
and **unique new Docker ID**
`82b143c4adad9fd785aad38590ed6738de52a6a06b06a4a9bdc07118ceb40424`.
Active R2 trial journal:
`/home/inlc/.local/state/qwen38-spark/mazinb-m1-reinstall/active.json`.
Terminal A remains in interactive protected foreground and requested
manual STOP at conclusion.

The exact executing code places READY *after* exact-model API
health, 180s = 36×5s monitored soak, kernel RM/host/watchdog
revalidation and actual inference smoke; thus **R2 foreground
isolated inference readiness passed on physical DGX**. This
does NOT mean boot-persistent systemd operation, long-term
host-stability, or an actual throughput benchmark.

Terminal output explicitly said
`M1_LLAMA_BENCHY=NOT_MEASURED`. Prior Terminal B check
showed `BENCHY=NOT_INSTALLED` on PATH and
`BENCH_RESULT_DIR=READY`. Read-only search for an existing
pinned CLI is the safe next action; **no live package
installation, source sync or benchmark bypass**. Benchmark
requires pinned `0.4.1.dev1+ge9be34457` via strict
reinstall-slot exclusive benchmark lock, while Terminal A
keeps supervising. If tool absent, finish the live smoke
experiment with exact candidate STOP before setting up
benchmark tooling for another explicit session.
[Physical evidence Stage D](../scripts/benchmark/evidence/dgx-mazinb-r2-download-preflight-physical-20261019.md).

Earlier entry `STARTED_UNQUALIFIED` is preserved as a
chronological intermediate state superseded by this
**actual ready-for-benchmark result**. Original 2026-10-14
measured benchmark remains unchanged, and PR #261 is Draft.

## 2026-10-19 — ACTUAL DGX mazinb R2 first separately approved GPU trial STARTED_UNQUALIFIED

**Owner-pasted actual DGX console**, after R2 checkpoint restore
and read-only preflight: local clean source SHA
`4612045c11ce47e52606794d63daede4cb35ac82`,
`BENCHY=NOT_INSTALLED` (CLI absent on operator PATH), and
`BENCH_RESULT_DIR=READY`. User selected Wizard
**5→24→4**, explicitly approved GPU start with `y`,
typed protected exact OrcaRouter predecessor Docker ID
`f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`
and exact startup phrase `START_RESTORED_MAZINB_16G`.
The physical controller printed:

```text
M1_CANDIDATE_STARTED_UNQUALIFIED=qwen38-mazinb-m1-20261019043708-479dfc86
```

**Stage classification: ACTUAL_DGX STARTED_UNQUALIFIED ONLY**.
The marker is emitted by the controller after protected candidate
create/start and watchdog arm/initial heartbeat checks; operator
has not yet provided `M1_READY_FOR_BENCH`, 180s soak,
exact-model API/smoke or actual throughput output.
Do not claim full model READY or long-term service qualification.
The uninstalled/unavailable PATH `llama-benchy` blocks the
new R2 benchmark regardless of API readiness until the exact
pinned version and compatible CLI are verified. During live
Terminal A **do not `git pull`, install packages, rebuild
Docker images, stop services, delete data, or attempt a
bench without lease**. Read-only check for an *existing*
pin-matching benchy executable in a separate terminal is
safe; otherwise terminate the unique R2 candidate via
its watched/explicit `STOP` when safe and prepare
benchmark environment before a separately approved new run.

[Stage C appended to physical evidence receipt](../scripts/benchmark/evidence/dgx-mazinb-r2-download-preflight-physical-20261019.md).
Remote Draft PR HEAD is newer than physical DGX source;
**do not confuse docs commits with runtime source**.
The original 2026-10-14 measured mazinb benchmark remains
immutable.

## 2026-10-19 — ACTUAL DGX mazinb R2 checkpoint RESTORED and independent M1 preflight PASS

**Owner-pasted physical DGX Wizard evidence:** Models **3→12**
resumable HF download completed **108/108** selected files,
then post-transfer per-file `verified` printed for all 108
(48 expert safetensors + 43 BF16 PLE + 4 BF16 model
+ 13 aux/config/tokenizer files). Fixed checkpoint
`mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4`
at complete revision
`f2c21eb3d2ff5f24c208ea7e3afba65e2e70f83f`
was placed at
`/home/inlc/Workspace/llm/qwen3.8-flash-next-dgx-spark/models/qwen3.8-flash-next-mazinb`.
Downloader reported file progress `108/108 [4:20:52]`,
`hf_xet` available (high-performance), 8 workers,
temporary `vllm-orcarouter-v029:v1` downloader,
`done → ... (174G)`,
`MAZINB_RESTORE_DOWNLOAD=COMPLETE_DOWNLOADER_VERIFIED`
and `MAZINB_RESTORE_GPU_START=NOT_PERFORMED`.
It did **not** print whether HF authentication token was
actually present.

Owner immediately ran reinstalled **Benchmark 5→24→3**,
re-entered exact protected OrcaRouter Docker ID
`f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`,
authenticated read-only kernel RM inspection and received
`M1_PREFLIGHT=PASS_READ_ONLY`.
The immutable installed release was
`ff67bab3c94d6992f61b9535836df97f03b9c022`;
candidate experiment image ID
`sha256:dba5d8af279fb85901e6d8911f1a59ecc45b669b0948ab8d01d7c7d1c5815734`.
Output ended `M1_CANDIDATE_START=NOT_PERFORMED`.
Original installed OrcaRouter remains `phase=complete`,
runtime not probed by Wizard banner.

**Evidence classification:** physical **R2 model restore +
read-only launch admission PASS**; new R2 Docker startup,
monitor arm, 180-second soak, inference smoke, localhost
API READY, service operational qualification and
new benchmark measurements **NOT_YET_RUN**.
The physical transcript does not show local `git HEAD`
SHA; controller preflight source requires clean expected
branch but exact SHA must not be fabricated.
[Permanent human-curated physical evidence](../scripts/benchmark/evidence/dgx-mazinb-r2-download-preflight-physical-20261019.md).

**Next only after explicit fresh owner approval**:
Wizard **5→24→4**, confirm exact protected Docker ID,
type `START_RESTORED_MAZINB_16G`, remain in foreground
Terminal A. Only use separate Terminal B pinned benchmark
after the live controller prints `M1_READY_FOR_BENCH`.
Never run previous historical M1 action 5→9.
Do not fast-forward/modify local checkout during an
active trial/benchmark; source_sha is pinned across both.
Do not merge Draft PR #261 as a substitute for physical
live qualification.

## 2026-10-19 — catplusplus vLLM-first versus SGLang comparative source study (SOURCE ONLY)

**Owner says proceed** with source comparison while the 173.64-GiB
mazinb R2 checkpoint download is underway. No DGX commands,
weight/source-bundle downloads, Docker/GPU builds or model
runtime changes have been performed by this work.

**Verified external upstream GitHub PRs:**
`vllm-project/vllm#53896` Qwen3.8 model support **MERGED**
2026-08-31; `#54371` UVA PLE offload **MERGED**
2026-09-09; prior `#53899` CPU PLE **CLOSED UNMERGED**;
`#54129` PLE safetensors read-only mmap **CLOSED UNMERGED**.
Merged UVA offload uses pinned CPU memory accessible via CUDA
UVA and **does not remove physical RAM occupancy on the
single 128-decimal-GB unified-memory GB10**. Disk-backed
mmap was a separate, unmerged implementation. Neither
proves catplusplus mixed MXFP8 fused qkvz scale consumption
or installed `vllm-orcarouter-v029:v1` has the same patches.

**Publisher model card** claims `extra/packages/` includes
modified **both** vLLM and SGLang source trees and two
git-history bundles. Their actual per-file implementations,
bundle identities and GB10 kernel support have NOT been
inspected at fixed revision
`3251fd8afbd08f76368a9bfa71132d9aef364813`.
Production SGLang script is described, but this is not
GB10 proof; vLLM-first is a **review order**, not a runtime
decision.

**New source-only inspection tier:** Added
`scripts/model/inspect_catplusplus_engine_sources.py`
and Wizard **5→23→11** with strict pinned
`/extra/packages` Hub JSON subtree scope,
bounded API pagination/response limits/no redirect,
file/bundle existence counts with an explicit
`engine_impl=NOT_AUDITED` result. No source
bundles/files or weights are read, downloaded or
executed; actual DGX inventory **NOT_RUN** during
mazinb download. Offline safety/transport tests added.
A later bounded exact-path source file SHA/function audit
is required to compare fused QKVZ MXFP8 scales,
ModelOpt mixed NVFP4 and FP8 PLE by engine.

Authoritative [dual-engine source/GB10 report](CATPLUSPLUS-VLLM-SGLANG-COMPARISON.md).
**Live, engine, RAM, checkpoint, service and benchmark
qualification remains BLOCKED; catplusplus NOT_MEASURED.**
Keep PR #261 Draft and preserve mazinb in-progress
download; do not `git pull` the actively transferring
DGX checkout.

## 2026-10-19 — catplusplus preparation while mazinb R2 download underway (SOURCE ONLY)

Owner reports the previously authorized **mazinb 173.64-GiB R2
checkpoint download has STARTED**. This is operator status, not a
completion receipt; there is NO new actual mazinb API/benchmark
readiness evidence. Maintain the current pinned checkpoint transfer:
no simultaneous catplusplus weight download, Docker build, GPU,
systemd switch, source sync in its active checkout, cleanup,
swap mutation or eviction.

**Catplusplus work proceeds in GitHub source only** under Draft
PR #261, without touching DGX:
- Previous physical DGX Wizard 5→23→8 measured HEAD **307**
  (`resolve` → same HF host `/api/resolve-cache/`)
  and HEAD **200** (both fixed pinned `raw` files);
  new `scripts/model/audit_catplusplus_loader_source.py`
  uses a *single fixed pinned raw GET/no redirects* per
  `config.json` (≤256KiB) and
  `extra/inference/inference_qwen38_flash_next_sglang.sh`
  (≤128KiB). No arbitrary or package/weight fetch. Source
  declaration results from actual DGX GET: **NOT_YET_RUN**.
  Even PASS cannot attest SGLang wheel or GB10 residency.
- Added `scripts/model/catplusplus_admission_plan.py`
  (Wizard **5→23→9** pure source-only plan and **5→23→10**
  lock-aware *read-only* conservative full-repository/disk
  screen, no lock or directory creation). Current source
  download/engine/MXFP8/PLE/GPU/bench gates stay BLOCKED.
- Read-only capacity arithmetic based on actual pinned DGX
  metadata: root safetensors ≈174.8553 GiB vs 128 decimal
  GB unified RAM ≈119.2093 GiB. Even subtracting publisher
  estimated FP8 PLE 47.7 GiB yields ~127.1553 GiB in
  *stored bytes*, already above RAM before CUDA/KV/RM.
  This does not prove an actual GB10 residency number,
  but disallows "PLE offload alone => proven fit" reasoning.
- Full staged engineering guide:
  [single-GB10 install/serve/bench preparation](CATPLUSPLUS-SINGLE-GB10-INSTALL-SERVE-BENCH.md).
  Run original publisher scripts/bundles, drop caches, trust
  remote code or publish 0.0.0.0: **FORBIDDEN**.
  Actual SGLang mixed quant fused-qkvz scale, NVFP4 expert,
  FP8 PLE offload, image pin, peak GPU RM allocation and
  protected candidate controller are **UNQUALIFIED**.
  The existing catplusplus M1 preflight/live/bench options
  remain deliberately fail-closed.
- Tests added for pinned raw GET 2-file allowlist/size/no
  redirect and pure staged memory/lock planning.
  GitHub CI at final source HEAD must be checked separately.

**No catplusplus install, real model launch or benchmark has
been performed or approved by this source-only work**. Do not
run DGX code sync until the live mazinb download concludes
and its hashes are verified; after that do bounded
source 5→23→7 and design-time 9/10 without weights.

## 2026-10-19 — ACTUAL DGX mazinb R2 restore admission PASS twice; weights still absent

**Owner-supplied real DGX Wizard console** selected Models **3 → 11**
twice; both independent outputs ended with:
`MAZINB_RESTORE_PREFLIGHT=PASS_READ_ONLY_NO_WEIGHT_DOWNLOAD`
and `MAZINB_RESTORE_DOCKER_GPU_SERVICE_ACTION=NONE`.
The pinned repository was
`mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4`,
full revision `f2c21eb3d2ff5f24c208ea7e3afba65e2e70f83f`,
with Hub metadata + disk admission reporting **173.64 GiB** and
`Preflight passed` at the dedicated checkout model directory
`/home/inlc/Workspace/llm/qwen3.8-flash-next-dgx-spark/models/qwen3.8-flash-next-mazinb`.
The downloader's storage-space policy includes 20 GiB reserve.
The independent host-idle check on both invocations returned
`MANAGED_IDLE_SERVICE_ENABLED=0`, `API_ACCESS_MODE=local`,
three project systemd units `load=not-found active=inactive`,
`MANAGED_IDLE_MANAGED_PORTS=NO_LISTENERS`,
`MANAGED_IDLE_DOCKER=NO_RUNNING_QWEN38_CONTAINERS`,
`MANAGED_IDLE_AUDIT=PASS_NO_MANAGED_API_LISTENER_OR_BOOT_START`
and `MANAGED_IDLE_AUDIT_HOST_MUTATION=NONE`.
Installed manifest remained `phase=complete`, profile
`orcarouter`, image `vllm-skinny-tp1:v1`,
with runtime banner `NOT_PROBED`.

**Owner navigated Benchmark 5 → 24**, which displayed the
four restored-M1 menu actions, but performed **none**.
No 3→12 download was authorized or run in this transcript,
no 5→24→3 live preflight result, no GPU start, no fresh
model API/soak/benchmark. The current console output does
**not** attest an exact `git rev-parse HEAD`; continue to
require clean checked-out source before any destructive,
network-heavy or GPU operation.

**Next physical operation:** from Models **3 → 12** choose
explicit default-NO authorization and type
`RESTORE_MAZINB_PINNED` for pinned checkpoint download;
inspect completion and verify per-file hashes before opening
Benchmark 5 → 24 → 3. Never use legacy original M1 5→9,
do not reactivate managed systemd or delete evidence.
The measured historical mazinb result stays preserved
independently of R2; model restore does not yet qualify
a service or benchmark.

## 2026-10-19 — SOURCE mazinb pinned restore and isolated R2 live/bench path

The operator explicitly requested **mazinb reinstall → actually serve →
protected benchmark first**, before resuming catplusplus. This is a
new authorization to *prepare* the staged workflow, NOT evidence that
the DGX has downloaded the model, started a GPU or measured new results.

**Known physical predecessor:** DGX mazinb final read-only retirement
audit passed on exact SHA `5164042ed5d784fe3469ad0207e4d8ecf8d5869f`;
mazinb checkpoint absent, historic Docker archived and removed,
original benchmark JSON/SHA PASS; installed OrcaRouter profile remains
completed, service/boot disabled. Do **not** reactivate or replace the
installed service in order to run a benchmark.

**New source-only functionality:** Wizard Models **3 → 11**
read-only pinned metadata/disk/host-idle restore admission and **3 → 12**
explicit owner-approved ~174 GiB download, using
`scripts/wizard/mazinb-restore.sh`. Pinned source
`mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4`, full immutable
revision `f2c21eb3d2ff5f24c208ea7e3afba65e2e70f83f`.
Restore retains exclusive lifecycle lock, rechecks idle and leaves
OrcaRouter/old research artifacts untouched. The download helper
may briefly create a CPU-only downloader container; it does **not**
start a model, GPU or installed service. Old retired Hybrid
menu numbers 8-10 remain unavailable.

Wizard Benchmark **5 → 24** new `reinstall` session slot:
separate `mazinb-m1-reinstall` journal/benchmark lease, previous
`mazinb-m1` original audit/tombstone hash-pinned and never overwritten,
managed boot/service remains disabled and no project port/listener
or running Qwen Docker is admitted before create.
Old exact managed Docker immutable ID/image/release are protected.
Explicit separate GPU approval and Terminal-A foreground watchdog
are required. Localhost-only 18889, KV 16 GiB,
create-only→arm→start→READY→180s soak→inference smoke→strict RM safety.
**No persistent/background systemd service is claimed.**

Terminal B uses `m1-benchmark-lock.sh --session-slot reinstall`
plus `mazinb-reinstall-bench.sh --run` only after new physical
`M1_READY_FOR_BENCH`. The benchmark requires the historical
`llama-benchy 0.4.1.dev1+ge9be34457` version, fixed
PP512/2048 TG128 C1 warmup1/runs3, separate fresh JSON,
report and SHA256 and post-run admission. No performance
metrics until physical execution and independent evidence.
See [R2 operating guide](MAZINB-REINSTALL-R2-WIZARD.md).
**Current R2 physical install/download/live/bench: NOT_RUN**.
Synthetic source CI must pass at the exact final HEAD before DGX
action; PR #261 stays Draft.

## 2026-10-19 — ACTUAL DGX catplusplus redirect transport diagnosis (HEAD only)

**Operator-provided live DGX Wizard 5 → 23 → 8 output**
shows both pinned `resolve` text paths returned **HTTP 307**,
redirect `LOCATION_CLASS=HF_SAME_HOST`,
`LOCATION_ROUTE=API_RESOLVE_CACHE`; corresponding pinned
`raw` paths (`config.json`, SGLang launcher) returned
**HTTP 200** and `LOCATION_CLASS=NONE`. No redirect was
followed, no HTTP response body was read or parsed; no source
audit or model/download/GPU live admission occurred.
The terminal excerpt does not independently print a Git SHA.
The original `SOURCE_REDIRECT_BLOCKED` was consistent
with the strict `resolve` GET no-follow policy;
it is **not** proof that the pinned `raw` GET content
passes quantization declarations or is consumed by a GB10
engine. The approved source-level next step, after
the mazinb priority, is separately verifying bounded pinned
`raw` GET content with unchanged no-follow/size limits.
Catplusplus stays **NOT_MEASURED / LIVE_BLOCKED**.

## 2026-10-19 — catplusplus pinned Hub header-only redirect triage (SOURCE ONLY)

Physical DGX Wizard **5 → 23 → 7** previously returned
`CATPLUSPLUS_M1_BLOCKED=SOURCE_REDIRECT_BLOCKED`, with
neither redirect target/route nor which of the two files
established. Hugging Face `resolve` may redirect to same-Hub
cache routes or external data endpoints; no raw fallback
or target-host trust can be inferred without bounded evidence.

New Wizard **5 → 23 → 8** delegates to M1
`source-transport` and a dedicated constrained
`probe_transport()` to make four **HEAD only**
requests (`resolve`/`raw` for exactly the
two pinned tiny text file paths). No response bodies
are read, redirect following is disabled, and only
sanitized status, same-host/external-host classification
and bounded route class are displayed. No signed URL,
authentication tokens, redirect query strings,
weights, scripts or engine binaries are fetched.
Existing **5 → 23 → 7** GET source audit
retains its strict redirect-blocking behavior and
all catplusplus M1 GPU/load/memory/live admission
gates remain BLOCKED. New source-only tests
mock network transport and assert HEAD-only,
four fixed URLs, no-follow, no token disclosure
and independent live block. Current physical
HEAD diagnosis **NOT_YET_EXECUTED**; do not
claim the redirect resolved until real DGX output.

## 2026-10-19 — ACTUAL DGX mazinb final read-only retirement audit PASS

**Owner-pasted DGX terminal transcript (physical, not CI):**
[Permanent exact-key physical evidence](../scripts/benchmark/evidence/dgx-mazinb-retirement-audit-physical-20261019.md).
The owner synchronized the sole canonical checkout on
`feature/wizard-modular-phase1-20261014` from
`14a44f0` to **exact source SHA**
`5164042ed5d784fe3469ad0207e4d8ecf8d5869f` by
`git fetch` + `git merge --ff-only`, with expected branch and
clean-worktree gates; the shell printed `SOURCE_SYNC=VERIFIED`.
The preceding GitHub Push and PR CI both had success conclusions.

**Wizard 3 → 6** on that DGX returned
`MAZINB_RETIREMENT_AUDIT=PASS_READ_ONLY_DEDICATED_ARTIFACTS_ABSENT`
and `MAZINB_RETIREMENT_HOST_MUTATION=NONE`.
Specific independently observed read-only results:
- `MAZINB_DOCKER_EVIDENCE=ORIGINAL_AND_REPOSITORY_SHA256_PASS`,
  `MAZINB_DOCKER_JOURNAL=STOPPED_EXACT_ID`,
  `MAZINB_DOCKER_HYBRID_STAGES=POST_RETIREMENT_NOT_REQUIRED`.
- `MAZINB_AUDIT_ARCHIVE=PASS_EXACT_FIVE_INSPECT_AND_LOG_PAIRS_SHA256`
  and `MAZINB_AUDIT_ORIGINAL_AND_GITHUB_BENCHMARK=SHA256_PASS`.
  The private historical Docker evidence archive remains
  `/home/inlc/.local/state/qwen38-spark/retirement-archives/mazinb-docker-20261014T103718Z-7e238b9aeb`.
- `MAZINB_AUDIT_DOCKER=EXACT_FIVE_ABSENT_NO_OTHER_MAZINB`,
  protected predecessor ID
  `f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`
  is still present and the shared vLLM image is preserved.
- Dedicated system and user units both ABSENT, the three project
  shared runtime/proxy units `load=not-found active=inactive`,
  mazinb 18889 port and shared 8888/8000/8001 ports have NO_LISTENER,
  no known mazinb worker/watchdog processes.

**Wizard 3 → 5** after this independently confirmed
`MAZINB_DOCKER_RETIRE=BLOCKED_HISTORICAL_MARKER_REVIEW_REQUIRED`,
demonstrating the new no-repeat-delete protection physically; this
was not a second deletion. **Wizard 5 → 7** reported M1
`phase=stopped`, `Running=False`, `ExitCode=0`, historical
session `qwen38-mazinb-m1-20261014013811-16ced779`,
Docker ID `7af3966f3d0cae79f8277eaf9ad003fb04c1e15ea01f86574c2d8eeac396e7a1`,
`M1_DOCKER_REMOVED=YES_ARCHIVED` and the same archive path.
No Docker/service/GPU/weight/download action performed by these
read-only checks; all 2026-10-14 M1 benchmark observations remain
historical, not freshly measured or proof of a current live mazinb service.

**Closed:** prior post-retirement audit physical-run gap, old
H3-H6 false dependency and the repeated-retirement prevention
physical-check gap. **Still open:** catplusplus pinned-source
`SOURCE_REDIRECT_BLOCKED`, exact pinned loader/GB10 capacity,
checkpoint acquisition and separate approved model GPU launch.
mazinb checkpoint remains absent, as verified by prior physical
Wizard assets inventory; re-running mazinb requires separately
reviewed reinstallation and physical startup authorization.
PR #261 remains Draft/unmerged.

## 2026-10-19 — SOURCE fix for post-retirement mazinb audit after H3-H6 deletion

The actual DGX **3 → 5** historical cleanup attempt stopped in
`retire-mazinb-containers.py evidence()` because it still required
Hybrid H3-H6 directories, even though the 2026-10-14 physical Docker
retirement was already completed and those Hybrid checkpoints were
separately retired later.

**Distinct phase-specific contracts now enforced:**
- Historical *destructive* mazinb Docker retirement plan/apply still
  requires H3-H6 to exist, exact five stopped Docker IDs, prior source
  retirement and immutable benchmark/M1 provenance. No deletion
  protections were relaxed.
- Current *read-only* `verify-mazinb-retirement.py` archive check
  invokes shared benchmark/journal evidence with
  `require_hybrid_stages=False`; later removal of unrelated
  Hybrid stages no longer invalidates a historical mazinb archive.
  Exact benchmark original+repository SHA256, M1 journal,
  tombstone/ten Docker archive SHA256 files, Docker IDs,
  ports, dedicated units and processes remain fail-closed.
- Wizard **3 → 5** now detects an existing historical
  `retired-docker.json` marker, refuses any repeat cleanup
  and points operators to **3 → 6** for full read-only
  independent verification. Marker *presence* is not evidence
  of completion.

Host-free tests check both the non-relaxed destructive gate and
the later post-retirement audit exception, archive tampering rejection
and wizard refusal to call a deletion manager when a marker exists.
The new source fix needs exact-HEAD CI, DGX fast-forward and actual
**3 → 6** result before claiming physical post-retirement audit PASS.
No GPU/Docker/model files/service changes were performed.

## 2026-10-19 — ACTUAL DGX mazinb assets absent; historical retirement menu re-entry blocked

**Owner-supplied physical Wizard transcript**, not a source/CI simulation:
`./wizard.sh` **3 → 2** showed `mazinb`
`ACTIVE=no CHECKPOINT=absent CONTAINER=absent IMAGE=present`,
with expected checkpoint at
`models/qwen3.8-flash-next-mazinb` and shared image
`vllm-orcarouter-v029:v1`. OrcaRouter remained configured
active with `171G` checkpoint `present`, Docker `exited`
and image `present`; Hybrid H3-H6 checkpoints reported
`absent`, consistent with prior approved retirement.
The Wizard banner was
`Manifest: valid (phase=complete)`, configured
`orcarouter`, image `vllm-skinny-tp1:v1`,
`Runtime: NOT_PROBED`. This is an assets listing, **not**
a proof of a running backend or verified Docker image compatibility.

The operator entered **3 → 3** then supplied `6` at the
**profile-name** prompt; Wizard correctly rejected
`Unsupported or not-installable profile`. No switch occurred.
Next **3 → 5** attempted the *read-only pre-delete plan* for
historical mazinb Docker cleanup, which returned
`MAZINB_DOCKER_RETIRE=BLOCKED reason=hybrid dependency missing:
qwen3.8-hybrid-quant-layout`. This one-time legacy retirement
precondition expects H3/H6 still present, but they were subsequently
retired; the error does **not** contradict the verified 2026-10-14
mazinb Docker archive+deletion. **No Docker cleanup ran**.
At transcript end the operator had only opened **3 → 7**
candidate metadata menu, without executing an action.
**3 → 6** post-retirement audit and **5 → 7** M1 journal status
are still awaiting *current* physical output. The transcript lacks
an exact `git rev-parse HEAD` value, so no exact physical source
SHA is attested.

**Source-only UX/safety correction:** Wizard **3 → 5** now
detects a historical M1 `retired-docker.json` marker before
invoking the old one-time five-container plan, fails closed with
`BLOCKED_HISTORICAL_MARKER_REVIEW_REQUIRED` and points to
Wizard **3 → 6**. Marker existence alone is **not** proof of
a valid archive/retirement; the separate full read-only audit
remains mandatory. Synthetic Wizard regression checks there is
no call to the retirement manager when a marker is present.
The actual DGX has **not yet executed the corrected source**.

**Next gate:** collect physical **3 → 6** read-only retirement
audit, **5 → 7** M1 status, current Git HEAD and clean-worktree
proof. Do **not** select historical mazinb deletion actions,
managed model switching or M1 GPU start to bypass the absence
of a checkpoint. A new mazinb download and separate GPU
launch need explicitly scoped approval after source/host preflight;
archived M1 reports can already be analyzed without reinstallation.

## 2026-10-19 — ACTUAL DGX catplusplus pinned-source audit redirected and blocked

**Evidence: owner-pasted DGX Wizard transcript**, not GitHub CI or
a backend loader test. Wizard **5 → 23 → 7** on the host printed
`CATPLUSPLUS_M1_BLOCKED=SOURCE_REDIRECT_BLOCKED` followed by
`catplusplus M1 admission remains BLOCKED; no Docker/GPU/download action`.
The Wizard's displayed manifest was valid/complete, configured profile
`orcarouter`, image `vllm-skinny-tp1:v1`, runtime
`NOT_PROBED`. The transcript did **not** print a Git HEAD,
redirect HTTP response/location or file-specific request, and does not
establish that either pinned file was downloaded/parsed. The
read-only audit intentionally rejects HTTP redirects; the redirect
cause remains **UNDETERMINED** pending bounded transport diagnosis.
Do not bypass the allowlist or automatically follow an unverified
redirect; positive declarations and engine/GB10 compatibility remain
**NOT_ATTESTED**, catplusplus **NOT_MEASURED**.

The operator next prioritizes collecting mazinb runtime provenance
before returning to catplusplus. **Crucial existing physical
history:** mazinb's ~173.65 GiB source checkpoint and five stopped
trial Docker containers were already retired with preserved
SHA-verified M1 benchmark evidence on 2026-10-14. The historical
successful M1 is *not* evidence of currently installed mazinb
weights. Verify present host assets using Wizard **3 → 2** and
**3 → 6** before considering a *new* owner-approved download or
isolated M1 GPU run. Do not use managed model switching as a
shortcut: the last physically confirmed managed API/service state
had `SERVICE_ENABLED=0`, and actual current state must be rechecked.
The archive and [benchmark report](model-reports/mazinb.md)
can support static loader/benchmark comparison without
recreating a ~174 GiB checkpoint.

## 2026-10-18 — catplusplus M1 fused-qkvz declaration guard tightened (SOURCE ONLY)

Follow-up to the pinned two-file source audit: `scan_config` now
requires each declared fused `.linear_attn.in_proj_qkvz` quantized
layer to have explicit `quant_algo=MXFP8`. An NVFP4 or unspecified
algorithm no longer counts as a positive MXFP8 source declaration.
Wizard **5 → 23 → 7** now reports total, MXFP8 and non-MXFP8
fused alias counts and declared PLE dtype; offline negative fixtures
cover invalid qkvz algorithms. This is a conservative parser
correctness fix, **not pinned Hub source verification or a
real DGX result**. All engine/scale consumption, 128GB GB10 residency,
physical audit, weights, GPU start and M1 benchmark gates remain
unqualified; catplusplus stays **NOT_MEASURED**.
See [catplusplus M1 Wizard](CATPLUSPLUS-M1-WIZARD.md).

## 2026-10-18 — catplusplus real-path pinned source compatibility audit implemented (NOT DGX EXECUTED)

Progress beyond the previous source-only M1 lifecycle skeleton:
GitHub now has a maintained real-world read-only source
inspection path. Wizard **5 -> 23 -> 7** invokes
`scripts/runtime/catplusplus-m1.py source-audit`,
which delegates to
`scripts/model/audit_catplusplus_loader_source.py`.
This fetches (only if the owner physically selects that
menu) pinned **config.json** and the publisher's small
**SGLang launcher text**, checks quantization config
(ModelOpt MIXED_PRECISION, MXFP8 fused `in_proj_qkvz`
declarations, FP8 PLE dtype), PLE file-offload flags
and warns about `sudo`, `drop_caches`, public bind.
Read-only network requests cap the individual files
(256/128KiB), block redirects and do not pull model
weights, packages or bundles. Unit fixtures cover both
positive source declarations and missing/dangerous sources.

**IMPORTANT:** no physical DGX output for the new source
audit has been received. No actual backend loader/wheel
verified, no model downloaded, no 128GB capacity workaround
proven; GPU readiness/benchmark remains NOT_MEASURED.
The M1 live paths are still separately blocked, with
all old managed/A/B objects preserved. Positive source
declarations must not open the actual GPU start gate.

## 2026-10-18 — catplusplus M1 mazinb-parity lifecycle source scaffold; ALL LIVE GATES BLOCKED

The operator specified that catplusplus should follow the same **form**
as the first physical mazinb M1 benchmark: Wizard-owned independent
session, exact protected predecessor identities, lifecycle lock,
Docker create-only, exact-ID watchdog armed BEFORE start,
model API identity and functional smoke, protected post-ready
180-second soak, pinned llama-benchy Terminal-B admission and
PP512/TG128 + PP2048/TG128 C1 warmup1/runs3, exact-ID STOP,
archived raw evidence and SHA256.

**GitHub SOURCE ONLY now implemented:**
- `scripts/runtime/catplusplus-m1.py` exposes mazinb-compatible
action names `plan`, `status`, `preflight`, `run`,
`bench-admission`, `reconcile`. The 12-step lifecycle is a
**contract, not runnable implementation**. All live/bench
paths **fail closed** (rc2); no Docker/API/GPU/weight download.
Only read-only plan, journal status and no-journal reconcile
can return PASS without claiming actual candidate readiness.
- Wizard Benchmark **5 -> 23** gives its own seven-action
catplusplus sub-menu (the six mazinb-parity lifecycle checks plus
read-only pinned-source audit option **7**), alongside the existing
**5 -> 22 M0 plan**.
- Offline tests verify all 12 workflow markers, refused live
start, refused benchmark with even forged ready journal,
no-local-state side effects, symlink refusal and safe Wizard
nested navigation. No user data, services, releases or running
Docker objects are modified.
- Persistent runbook: [catplusplus M1 Wizard](CATPLUSPLUS-M1-WIZARD.md).

**Reason for rejecting an actual mazinb-style load TODAY:**
Actual DGX pinned catplusplus metadata shows root model
safetensors ~174.8553 GiB versus a single GB10 nominal
128GB unified memory. Neither exact mixed MXFP8 fused qkvz
scale consumer/ModelOpt NVFP4 loader nor file-offloaded FP8
PLE, peak RM/CPU/swap budget or exact pinned GB10 image
is currently qualified. The checkpoint was not downloaded,
and no owner approval for catplusplus download/GPU startup
was granted. Therefore catplusplus actual API
READY/inference/benchmark remains **NOT_MEASURED**.

Safety: do NOT inherit mazinb's known-good vLLM image
or systemd installed-service assumption. Existing three
managed/OrcaRouter A/B Docker protected objects remain intact.
Only after specific source/offload qualification and separate
download/GPU approvals may a full protected M1 controller
be implemented/executed on the physical DGX.
## 2026-10-18 — catplusplus M0 benchmark plan uploaded to GitHub: SOURCE ONLY / NOT_MEASURED

The operator suggested prioritizing catplusplus benchmark preparation
before additional OrcaRouter C attempts. The project remains
**P0 Wizard-first install/switch/inspect/safe-uninstall**.

Earlier ACTUAL DGX pinned L0 metadata for
`catplusplus/Qwen3.8-Flash-Next-uncensored-NVFP4-mixed`
revision `3251fd8afbd08f76368a9bfa71132d9aef364813`:
`TREE_METADATA_COMPLETE`, 17,448 entries, 96 `.safetensors`
files, complete repository 188,540,029,444 bytes (~175.59 GiB)
and root weights ~174.8553 GiB (rounded).
These weights exceed nominal 128 decimal GB unified RAM even
before KV cache, loader staging and safety reserve, so naive
fully-resident single-GB10 inference is not a safe next step.

**GitHub source-only M0 added:**
- `scripts/benchmark/catplusplus-plan.py plan [--json]`: purely
static pinned candidate plan with NO host/API/Docker/GPU/download
actions, correct baseline C1/PP512+2048/TG128/warmup1/repeats3,
empty `measurements` and `NOT_MEASURED` terminal status.
- Operator Wizard main **5 Benchmark -> 22 catplusplus M0 plan**
provides same read-only status and memory/loader blockers.
- Existing strict `llama-benchy-report.py` accepts optional
`--profile catplusplus` **only to convert future real JSON**;
this does NOT make the candidate model installable or prove READY.
- Synthetic tests for the M0 plan, menu and report identity/numeric
guards. New standalone
`docs/model-reports/catplusplus.md` explains source gates
and actual mazinb M1 benchmark reference without fake cat metrics.

**LIVE/INSTALL GATE REMAINS CLOSED:** no catplusplus weights
downloaded, no actual model/driver runtime qualified, no
MXFP8 qkvz+scale/ModelOpt mixed/FP8 PLE loader proof, no safe
partial memory-residency plan or GPU/RM watch, no catplusplus
API READY, no inference and **NO CATPLUSPLUS BENCHMARK**.
The previously owner-approved one-time C CPU CLI probe was
consumed and does not authorize catplusplus actions.
No new DGX/container/service changes, no Docker removal or
PR merge. A real downloaded model or GPU run still requires
new explicit owner authorization and independent host gates.

[M0 benchmark plan and comparison boundaries](model-reports/catplusplus.md).
[Last physical pinned metadata evidence](CATPLUSPLUS-METADATA-COMPATIBILITY.md).
## 2026-10-18 — ACTUAL DGX corrected OrcaRouter backend Wizard status now physically verified

Owner provided the **second actual DGX Wizard compatibility-screen output**
after the installed-vs-registry presentation fix. It now reports
`ORCAROUTER_MANIFEST_STATE=valid`,
`ORCAROUTER_CONFIGURED_PROFILE=orcarouter`,
`ORCAROUTER_CONFIGURED_IMAGE=vllm-skinny-tp1:v1`,
`ORCAROUTER_CONFIGURED_VARIANT=LEGACY_SKINNY_MANIFEST_IMAGE`,
`ORCAROUTER_LIVE_RUNTIME=NOT_PROBED`,
`ORCAROUTER_V029_BACKEND=REGISTRY_IMPLEMENTED_NOT_LIVE_ATTESTED_HERE`,
`ORCAROUTER_OFFICIAL_ARM64_C=BLOCKED_PRE_RUNTIME_DEVICE_INFERENCE_CPU_ONLY`,
`ORCAROUTER_OFFICIAL_ARM64_C_INSTALL_SWITCH=DISABLED_UNQUALIFIED`
and `WIZARD_MUTATION=NONE`.

The physical interactive view separately labels
`vllm-orcarouter-v029:v1` as the **registry default candidate**,
not as the installed image. It notes the deliberate GPU-hidden
CLI help failure and outstanding PLE/KV16GiB/MTP/READY qualification.
Thus the preceding source-only UI correction has now been
**actually seen and verified on DGX**. No exact
`git rev-parse HEAD` was provided for this particular screen;
do not claim the operator has synced to later GitHub commits.

**Not yet established:** any running vLLM/READY health, runtime
switch apply, model inference or benchmark. The screen is a
read-only manifest/candidate diagnostic and is not independent
fresh protected-Docker ID evidence. The permanent product
priority is still **easy Wizard install, runtime/backend switch,
inspect and safe uninstall**, not manual Docker probes.
[Physical second Wizard evidence](../scripts/benchmark/evidence/dgx-orcarouter-wizard-backend-status-20261018.md).
## 2026-10-18 — ACTUAL DGX OrcaRouter Wizard backend screen verified; installed image differs from registry default

The operator physically navigated `./wizard.sh`
`3 Model management -> 7 Candidate metadata ->
5 OrcaRouter backend qualification` and returned
to the parent submenu. The main banner reported
`Manifest: valid (phase=complete)`,
`Profile: orcarouter`, **`Image: vllm-skinny-tp1:v1`**,
**`Runtime: NOT_PROBED`**. The read-only C qualification
screen returned `WIZARD_MUTATION=NONE` and
`ORCAROUTER_OFFICIAL_ARM64_C_INSTALL_SWITCH=DISABLED_UNQUALIFIED`.
All CLI/help, PLE, KV, MTP, GPU runtime and benchmark
limitations remain. The terminal excerpt did not print
a Git HEAD or independently inspect active Docker IDs.

**P0 Wizard UX discrepancy discovered:** the C qualification
screen emphasized source registry
`vllm-orcarouter-v029:v1`, but the *physical installed
manifest* actually records `vllm-skinny-tp1:v1`.
The registry candidate must never be confused with
the currently installed manifest image or an actually
running/READY runtime.

**GitHub source correction (NOT YET physically verified):**
`scripts/wizard/candidate-metadata-menu.sh` now reads
the existing strict manifest status helper and renders
`ORCAROUTER_CONFIGURED_IMAGE`, exact
`ORCAROUTER_CONFIGURED_VARIANT`,
`ORCAROUTER_MANIFEST_STATE` and
`ORCAROUTER_LIVE_RUNTIME=NOT_PROBED` separately from
the v0.29 registry candidate. No `install.env` sourcing,
GPU, Docker mutation, model download/deletion, or
service changes. New synthetic tests exercise legacy,
v0.29, unknown, symlink/invalid and missing manifest cases.
No new C start authorization.

[Exact operator terminal receipt and follow-up source boundaries](../scripts/benchmark/evidence/dgx-orcarouter-wizard-backend-status-20261018.md).
## 2026-10-18 — SOURCE-ONLY P0 Wizard backend admission integrated; legacy menu contract restored

Continuing from physical DGX vLLM C CPU-only help failure
(`RuntimeError: Failed to infer device type` before CLI argument
printing), focus returns to **P0 easy Wizard install, profile
switch, diagnostics and safe uninstall**, NOT manual Docker trials.

CI on earlier head `714717c7d663bdc0c3c337bd6a8e71c4af17df48`
FAILED both Push and PR workflows, exactly two synthetic
retired-Hybrid menu tests (`8/9/10` must each return Invalid
selection). New Model management option 8 had improperly
revived retired slot 8. Source remediation keeps **8–10**
non-routable and moves the read-only OrcaRouter backend
qualification view to existing **Model management -> 7 Candidate
metadata -> 5 OrcaRouter qualification**. No Hybrid artifacts
or test protections are removed.

Additional new **source-only** operator integration:
- `scripts/backend/backends.sh` now distinguishes vLLM image
variants of existing OrcaRouter model: `v029` implemented,
`legacy` experimental fresh-install-only, `official-arm64-c`
**UNQUALIFIED/NOT_SELECTABLE**. This axis is distinct from the
vLLM vs SGLang backend axis and from model/checkpoint identity.
- Main `install.sh` Wizard model selection (both fresh install
and existing profile switch selection) explicitly displays
why official C cannot be selected: an intentionally GPU-hidden
CPU-only CLI probe died in device inference **before**
CLI flags could be assessed; real option, PLE/KV16GiB/MTP,
model READY and host-safety remain unverified.
- Typing `c`, `official-c`, `official-arm64-c` in Wizard,
or providing these as `--orcarouter-runtime` CLI arguments,
does **not** authorize/load/run C and is blocked by the
qualified runtime selector. Original v029/legacy contracts
and original default model/serving image are unchanged.
- Synthetic tests added to cover direct installer blocking,
candidate-menu nested navigation, and preserved invalid
retired menu numbers. No physical C start and no new
CPU-only Docker probe were performed by these commits.

**Current qualification:** GitHub source changes are NOT
DGX deployed/physically verified until exact-head CI PASS
and operator-controlled safe Git fast-forward. Prior actual
physical DGX state remains CLI-help failure with all protected
managed/A/B objects unchanged, disposable CPU probe removed.
**No approval for model GPU start, service changes, destructive
operations or PR merge.**

[C official runtime and wizard integration plan](ORCAROUTER-PEER-C-PLAN-20261018.md).
[Physical CPU CLI root-cause evidence](../scripts/benchmark/evidence/dgx-orcarouter-peer-c-cli-probe-20261018.md).
## 2026-10-18 — ACTUAL DGX saved vLLM traceback: CPU-only CLI died in DeviceConfig before flag help

The operator read the existing, already-consumed CPU-probe output
`/home/inlc/orcarouter-bench-evidence/peer-c-cli-20261018T115111Z-5e41d75a/vllm-serve-help-all.txt`
**without starting a new Docker container**. Exactly 34 saved
lines showed Triton `0 active driver(s)`, torch
`No CUDA runtime is found`, and Python traceback:
`vllm/entrypoints/cli/main.py` -> `serve.py` ->
`openai/cli_args.py` -> `AsyncEngineArgs.add_cli_args` ->
`EngineArgs.add_cli_args` -> `get_kwargs(VllmConfig)` ->
`_compute_kwargs` -> `default.default_factory()` ->
`vllm/config/device.py:56 __post_init__` ->
`RuntimeError: Failed to infer device type`.

**Confirmed failure point:** the CPU-only help invocation failed
when creating the CLI parser's device defaults **before printing
the options**. It is consistent with the explicitly GPU-hidden
`--runtime runc`, no GPU devices, `CUDA_VISIBLE_DEVICES=-1`,
`NVIDIA_VISIBLE_DEVICES=void` test environment. It does NOT
demonstrate unsupported `--kv-cache-memory-bytes`,
`--speculative-config` or any other CLI option, and does NOT
prove the image's GPU engine or OrcaRouter checkpoint incompatible.

Actual installed distributions remain
`vllm=0.1.dev20073+g8e685d198`,
`torch=2.13.0+cu130`, `transformers=5.15.1`,
`flashinfer-python=0.6.17`,
`compressed-tensors=0.17.0`. GPU, weight loading, model READY,
runtime memory stability and benchmark remain untested.

The saved-report code was extended **source-only** to classify the
exact device trace as
`DEVICE_INFERENCE_FAILED_IN_GPU_HIDDEN_PROBE`, while retaining
`NOT_EVALUATED_HELP_FAILED` for all CLI flags and
`BACKEND_WIZARD_INSTALL_SWITCH=NOT_QUALIFIED`.
The one-time CPU approval is consumed and no retry or GPU load
is authorized. Continue source/read-only diagnosis and the
**P0 Wizard-centered model install/switch lifecycle**, not
standalone trial scripts as a product replacement.
[Exact physical traceback evidence](../scripts/benchmark/evidence/dgx-orcarouter-peer-c-cli-probe-20261018.md).
## 2026-10-18 — ACTUAL DGX official ARM64 peer C CPU-only CLI probe FAILED; package inventory verified

Owner executed source SHA `4873016f1d9fd864e6cce30c18fb96634b412fe3`
via the explicitly approved one-time CPU-only disposable OCI
probe. Pre-Docker host-check passed, and after-run managed/A/B
objects were unchanged; new probe container auto-removed.
Evidence directory:
`/home/inlc/orcarouter-bench-evidence/peer-c-cli-20261018T115111Z-5e41d75a`.

**Physical verified packages:**
`vllm=0.1.dev20073+g8e685d198`,
`torch=2.13.0+cu130`, `transformers=5.15.1`,
`flashinfer-python=0.6.17`, `compressed-tensors=0.17.0`.
**Critical result:** the `vllm serve --help=all` invocation failed
(help exit 1; probe-container exit 13; host helper exit 2).
The physical output's all-`NOT_FOUND_IN_HELP` flags
are **not evidence those flags are unsupported** because
the help command did not succeed. The saved decoded
`vllm-serve-help-all.txt` is the source of the next root-cause
inspection and has not yet been pasted. No model loader, GPU,
API or performance sample was run.

**Approved action consumed:** do not rerun CPU Docker, alter
runtime flags, or initiate live C. New GitHub source adds a
`report` **read-only** action for already persisted CLI
stderr/stdout and repurposes Wizard Advanced option 6
to inspect saved failure rather than repeating the one-shot
probe; still requires CI-qualified source sync for DGX.

**P0 hierarchy:** normal easy Wizard checkpoint installation,
switching, diagnostics and safe removal remain the primary
product goal; official C is a candidate backend of existing
OrcaRouter and **not a newly verified selectable checkpoint**.
Keep C disabled from normal production selection until
real CLI/model/host proof is available. Do not reframe research
helpers or manual Docker commands as the primary deliverable.
[Complete physical probe receipt](../scripts/benchmark/evidence/dgx-orcarouter-peer-c-cli-probe-20261018.md).
## 2026-10-18 — Explicit approval: one-time CPU-only C image CLI/version probe (NOT EXECUTED)

Following physical DGX `host-check` PASS at source SHA
`c54248245376565c24c96893ba27f00032d6bffa`, the owner
explicitly approved a **single** CLI help/package metadata
inspection using the already installed official ARM64 C image.
This is **not** permission to run GPU or load OrcaRouter weights.

GitHub implements a new *source-only until DGX execution*
`scripts/runtime/orcarouter-peer-c-cli-probe.py` (`plan` and
`run --approved-cpu-only`), Wizard Advanced default-no option 6,
and synthetic offline tests.
The CPU probe uses exact image manifest/config IDs, Docker
`--pull=never --runtime runc --network none --read-only`, no GPU
devices, no model mounts, restricted non-root resources,
`vllm serve --help=all` and `importlib.metadata` packages.
Only a new randomly named disposable probe is auto-removed;
existing managed/A/B are exact-ID protected and untouched.
Evidence is collected to `$HOME/orcarouter-bench-evidence/`;
a one-time approval marker prevents accidental repeated execution.
No C container has yet been created under this authorization;
the tool requires a new CI-successful source sync on DGX.

**Persistent STOP boundaries:** do not claim the image's actual
CLI support or wheel/source revision before operator returns
the CPU-only probe output; even a parser-help PASS does not
prove model CPU PLE/KV/MTP runtime compatibility. No GPU start,
bench, service changes or cleanup of old containers authorized.
[Plan and approval receipt](ORCAROUTER-PEER-C-PLAN-20261018.md).
## 2026-10-18 — ACTUAL DGX NEW C host-check PASS (CI-qualified source; static only)

Owner safely fast-forwarded to exact Git HEAD
`c54248245376565c24c96893ba27f00032d6bffa`
(`GIT_SYNC=PASS`), then executed
`python3 -B scripts/runtime/orcarouter-peer-c-readonly.py host-check`
on the physical DGX.
Actual output: `PEER_C_OPERATION=HOST_CHECK_READ_ONLY`,
`PEER_C_RUNNING_DOCKER=ONLY_KNOWN_ADMIN_CONTAINERS`,
`PEER_C_PORT_18891=NO_LISTENER_AT_CHECK`,
`PEER_C_PLE_SWAP=PLE_SWAP_ACTIVE`,
`PEER_C_NONCMA_FREE_KIB=119329120`,
`PEER_C_NONCMA_AVAILABLE_KIB=123853516`,
`PEER_C_SWAP_FREE_KIB=149950172`,
`PEER_C_MEMORY_MARGIN=MINIMUM_STATIC_MARGIN_MET`,
`PEER_C_HOST_CHECK=PASS_SNAPSHOT_NOT_LIVE_APPROVAL`,
`HOST_CHECK_EXIT_CODE=0`.
Github CI on the exact DGX synchronized SHA was Push+PR SUCCESS.

**Scope:** only an independent read-only momentary host readiness
check passed. No C trial create/start, new services, model load,
host protected monitor arming, GPU execution, 180s soak or throughput
was performed. Existing managed/A/B identity/stop evidence remains
preserved; today's host snapshot does not replace the exact-ID check.

**Next source gate:** confirm the pinned official ARM64 image's
**actual** vLLM CLI/wheel and 16GiB KV/CPU PLE/MTP options, then
finish an independent uniquely named C create-only and protected
watchdog-before-start controller with synthetic CI tests. Any Docker
create/run or GPU model test needs separate owner approval.
[Physical host-check receipt](../scripts/benchmark/evidence/dgx-orcarouter-peer-c-host-readonly-20261018.md).
## 2026-10-18 — ACTUAL DGX peer C read-only host resources: free TCP port, swap and RAM

The owner ran `docker ps`, `ss -H -ltn '( sport = :18891 )'`,
`swapon --show` and a `/proc/meminfo` grep on the real DGX.
Only two Docker containers were currently running:
`open-webui` (id-prefix `9219d017e6ca`, exposed TCP 3000, healthy)
and `portainer` (id-prefix `360cc353a945`, exposed TCP 9443).
The `ss` check displayed **no listener** for C's planned TCP port
`18891` at that instant. `/swap-ple.img` was active at 128G with
`1020.3M` used, and `/swap.img` was active at 16G with 0 used.
Raw `/proc/meminfo`: `MemFree=119400264 kB`,
`MemAvailable=123921280 kB`, `CmaFree=69320 kB`,
`SwapTotal=150994936 kB`, `SwapFree=149950172 kB`.
So immediate **non-CMA free** was approximately **113.8 GiB**
and **non-CMA available** approximately **118.1 GiB**;
swap free was about **143.0 GiB**.

Interpretation: the *current* host snapshot is far above previous
low-free-RAM B protection samples, and no existing TCP listener
collides on port 18891. This is **NOT a port reservation, allocation
guarantee, GPU model compatibility result, proof other services are
absent, or authorization for live C start**. Existing A/B/managed
full exact IDs remain preserved per prior physical preflight.
No source deploy, host operation, Docker creation, model READY,
RAM-soak test or benchmark occurred in this inspection.

[Exact operator host resource and running-container evidence](../scripts/benchmark/evidence/dgx-orcarouter-peer-c-host-readonly-20261018.md).
## 2026-10-18 — ACTUAL DGX C systemd inventory: exact managed unit NOT_FOUND in system AND user managers

The owner ran `systemctl show qwen38-flash-next.service` and
`systemctl --user show qwen38-flash-next.service` with read-only
`--property=LoadState,ActiveState,SubState,UnitFileState`.
**Both** outputs were
`LoadState=not-found`, `ActiveState=inactive`, `SubState=dead`,
`UnitFileState=` (empty). Thus the exact named unit is
**not installed/recognized in either systemd scope** at inspection
time, **not** an installed stopped service. This resolves the
earlier `INACTIVE_OR_UNKNOWN` ambiguity to `NOT_FOUND` for this
specific physical observation, but does not rule out differently named
units or unmanaged processes.

An independent new C Wizard controller cannot inherit a requirement
that this actual unit be installed, nor claim a managed service
is healthy; it must independently guard port ownership, running
Docker objects and unfinished lifecycle state and arm the existing
memory-protection watchdog before starting the exact C candidate.
**No systemd change, C create/start, GPU execution or benchmark.**
[Read-only physical receipt](../scripts/benchmark/evidence/dgx-orcarouter-peer-c-preflight-20261018.md).
## 2026-10-18 — ACTUAL DGX C full preflight PASS (READ-ONLY); still no C model runtime

Operator successfully fast-forward synchronized DGX clean local branch
`feature/wizard-modular-phase1-20261014` from
`ad3855a0a64e25deed3b9c11d7b3168f06730d68` to
`ff339c1eb9eb77cb774b50b3fcdc7fa009ecd74d`
(`GIT_SYNC=PASS`). The same physical DGX executed
`python3 -B scripts/runtime/orcarouter-peer-c-readonly.py preflight`,
returning `PREFLIGHT_EXIT_CODE=0`,
`PEER_C_LOCAL_IMAGE=PINNED_MATCH`,
`PEER_C_RUNTIME_CONTRACT=ENTRYPOINT_SHAPE_MATCH_WHEEL_SOURCE_UNATTESTED`,
`PEER_C_PROTECTED_OBJECTS=THREE_STOPPED_EXISTING_IDS`,
`PEER_C_HOST_ARCH=ARM64`, `PEER_C_ROOT_DISK_FREE_GIB=417`,
`PEER_C_MANAGED_SERVICE=INACTIVE_OR_UNKNOWN`,
`PEER_C_ADMISSION=SOURCE_READ_ONLY_PREFLIGHT_PASS_NOT_LIVE_APPROVAL`.

**Important limits:** status `INACTIVE_OR_UNKNOWN` is only an ambiguous
combined result for systemctl exit codes 3 and 4; it cannot affirm
the systemd unit's existence/status. It also cannot attest exact
embedded vLLM wheel or flag compatibility, memory behavior, API READY,
or performance; **no C Docker create/start, GPU or bench** occurred.

Static code review: current `scripts/serve.sh` allows create-only
variants `mazinb-m1`, `hybrid-h6-m1` or old `legacy/v029`, **not C**.
When using a distinct image for OrcaRouter it selects CPU PLE but
default KV flag `--kv-cache-memory`; public vLLM docs instead expose
`--kv-cache-memory-bytes`. Specific pinned official image CLI parser
must be checked before writing a live C launcher. Do not use direct
`docker run` or reuse historical A/B container names to bypass this.

Read-only C helper source was later improved to label its true host
inspection and distinguish `INACTIVE` vs `UNKNOWN_NOT_LIVE_APPROVED`
rather than printing `PLAN_ONLY` and `INACTIVE_OR_UNKNOWN` on preflight;
the owner has **not** synchronized or run these later changes.
[Exact operator transcript and static blocker evidence](../scripts/benchmark/evidence/dgx-orcarouter-peer-c-preflight-20261018.md).
## 2026-10-18 — ACTUAL DGX peer C OCI ENTRYPOINT attested; vLLM embedded wheel remains unknown

The owner inspected local pinned official ARM64 image ID
`sha256:d464f3b466fa9c45ddbff8a812e80564503b6879a9fd95c1a47514f3f0df5a4a`
read-only. Output: `ENTRYPOINT=["vllm", "serve"]`,
`CMD=NOT_SET`, `WORKDIR=/vllm-workspace`,
`CUDA_VERSION=13.0.1`, `OCI_REVISION=unknown`,
`VLLM_BUILD_COMMIT=unknown`, `VLLM_IMAGE_TAG=local/vllm-openai:dev`,
`VLLM_VERSION=NOT_SET`, `FLASHINFER_VERSION=NOT_SET`.

Existing `serve.sh` appends `/model` and runtime flags after the
image, which produces the intended **argument shape**
`vllm serve /model ...`. It does not prove option acceptance,
Qwen4Exp/OrcaRouter/CPU PLE loader support or compatible
CUDA/allocator behavior, and no actual Docker start occurred.
The image is installed and SHA verified but its embedded vLLM
wheel/source is still **UNATTESTED**. Current new C
read-only preflight now inspects the actual Entrypoint, optional
Cmd, WorkingDir and CUDA_VERSION; this is a static gate only.
**No launch, API READY, memory/host qualification or C benchmark.**
[Actual OCI metadata receipt](../scripts/benchmark/evidence/dgx-orcarouter-peer-c-image-pull-20261018.md).
## 2026-10-18 — ACTUAL DGX official ARM64 peer C image pull VERIFIED, protected Docker unchanged

The operator explicitly authorized **only pinned image download and
identity verification**. On physical DGX, `docker pull --platform linux/arm64`
of `vllm/vllm-openai@sha256:3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e`
completed and live local `docker image inspect` produced
`PEER_C_VERIFY=PASS` with `OS=linux`, `Architecture=arm64`,
exact expected `RepoDigests` and distinct image ID
`sha256:d464f3b466fa9c45ddbff8a812e80564503b6879a9fd95c1a47514f3f0df5a4a`.
Source registry label information is not yet proof of actual embedded
wheel revision or runtime model compatibility.

The exact protected `qwen38-flash-next`, `qwen38-ab-legacy`,
`qwen38-ab-v029` container ID/image/status/running/OOMKilled metadata
were identical before and after the pull; `diff -u` passed and operator
printed `PEER_C_PROTECTED_DOCKER=UNCHANGED`.
Evidence root `/home/inlc/orcarouter-bench-evidence/peer-c-image-20261018T093728Z`
holds `pull.log`, JSON image inspect, verification output, pre/post
protected receipts and a `SHA256SUMS.txt` file. The owner's terminal
did not paste checksum contents nor attest post-run verification.

**Current gate:** `PEER_C_IMAGE_STAGE=VERIFIED`,
`PEER_C_MODEL_START=NOT_PERFORMED`,
`PEER_C_BENCHMARK=NOT_MEASURED`.
Run the independently developed **read-only** C preflight on a
known-clean, explicitly synchronized exact source SHA; check
image/guard/runtime metadata before designing live candidate.
**No live Docker create/start/exec, GPU, service, cleanup or
PR merge approval is implied by the download-only approval.**
[Exact actual DGX image receipt and protected postcheck](../scripts/benchmark/evidence/dgx-orcarouter-peer-c-image-pull-20261018.md).
[Peer C planning](ORCAROUTER-PEER-C-PLAN-20261018.md).
## 2026-10-18 — ACTUAL DGX OrcaRouter v0.29 B protection stop proven; official ARM64 C image NOT LOCAL

New owner physical **read-only observation** of the preserved Oct-13 B:
`qwen38-ab-v029` exact ID `13abbb81ca92cbf2f8256e96941a19102ce809ff1c9364ce6932b44a88ebf6a1`,
image `sha256:dba5d8af...`, Docker `exited`, `ExitCode=137`,
**`OOMKilled=false`**, 2026-10-13 20:56:13–21:04:01 KST.
Five monitor samples at 21:03:22–30 triggered `protect=1/5` →
`5/5`, low immediately-free non-CMA **1969 → 1171 MiB** and
`swapgrowth=3207MiB`, while `noncma_available` remained
approximately 40–42GiB. `STOP_REASON=memory-protection` and
`PROTECT stopping` occurred at **21:03:30 KST**. This is
a **confirmed watchdog stop**, *not* proof of NVIDIA RM or Docker OOM.
No actual B API READY or throughput was measured.

The same owner performed `docker image inspect` on the exact published
`linux/arm64` vLLM image manifest
`vllm/vllm-openai@sha256:3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e`,
and got **`No such image`**. This only proves that exact reference is
not local; an alias under a different tag still requires separate
`RepoDigests` inspection. **No C image pull, Docker start, GPU use,
or C performance measurement occurred.**

New GitHub **SOURCE_ONLY**
`scripts/runtime/orcarouter-peer-c-readonly.py` plus offline tests
and Advanced Wizard read-only plan/preflight entries identify the
official ARM64 digest and preserve existing managed/A/B objects.
`preflight` blocks if the pinned digest/tag is not locally attested.
This is a planner, **not a C GPU launch implementation or live approval**.
The operator's DGX was last shown on clean `ad3855a0...`; do not imply
new GitHub commits have been executed locally. PR #261 remains
Draft/Open/Unmerged. Real pinned Docker pull and C live startup still
require separate operator approval; keep KV=16GiB and protection unchanged.

[Actual B timeline and no-image evidence](../scripts/benchmark/evidence/dgx-orcarouter-v029-b-readonly-status-20261018.md).
[Independent C plan and gate](ORCAROUTER-PEER-C-PLAN-20261018.md).
## 2026-10-18 — ACTUAL DGX v0.29 B trial stopped from memory protection; benchmark had no API

The owner executed the maintained **read-only** OrcaRouter A/B trial
status, managed-service status and `docker ps`. The preserved
`v029` trial is `phase=stopped`, `Running=False`,
`DockerStatus=exited`, `ExitCode=137`,
`STOP_REASON=memory-protection`, exact Docker ID
`13abbb81ca92cbf2f8256e96941a19102ce809ff1c9364ce6932b44a88ebf6a1`.
This is the **current observation of an existing B trial**, **not**
a newly started 2026-10-18 GPU experiment. Its exact
`StartedAt`, `FinishedAt`, `OOMKilled`, monitor pressure
trajectory and strict kernel RM window were not provided.
Managed service command reported `installed=no enabled=no active=no`;
`docker ps` showed only unrelated `open-webui` and `portainer`
running. Neither service status nor an empty model-serving port proves
checkpoint/manifest or protected historical Docker absence.

The owner's loopback `18888` requests received connection refused.
Two invocations of the canonical lock-wrapped Python benchmark client
produced **error-only** JSON (qualification and decode), with
`/health` connection refused on 2026-10-18 at 08:29:57Z.
No throughput, TTFT, generation, READY or RM stability measurement was
obtained. `BENCHMARK_STATUS=NOT_MEASURED` for OrcaRouter remains.
The source's fail-closed same-variant Docker-name reservation blocks
reuse of existing `qwen38-ab-v029` without separate evidence-backed
resource disposition; **do not delete it to bypass admission**.
No trial restart, benchmark repeat, model-data cleanup or protection
relaxation is approved. Collect bounded read-only exact B monitor,
Docker and kernel window evidence next, then review any new candidate
through a distinct identity and owner-approved Wizard procedure.
[Exact owner terminal output, scope and STOP rules](../scripts/benchmark/evidence/dgx-orcarouter-v029-b-readonly-status-20261018.md).

## 2026-10-18 — ACTUAL DGX OrcaRouter full peer config parity 7/7 verified

The DGX operator pasted the output of the existing bounded,
read-only `inspect_orcarouter_mount_config_readonly.py` from
`~/Workspace/llm/qwen3.8-flash-next-dgx-spark`.
Current protected container postcheck `PASS_CURRENT_ONLY`;
managed/legacy RO bind sources match and original+override configs
are readable. The override equals the expected narrow
`qwen_sparse_attention -> full_attention` rewrite and retains
48 layers, 36 linear / 12 full, 2 CT groups / 301 targets /
753 ignores.

**New physical finding:** canonical SHA256 values for the FULL
operator-supplied community `config.json` and all six separately
reported subtrees (quant, CT groups, ignore list, text, **ordered**
layer types, vision) are **7/7 MATCH_REFERENCE_CANONICAL_VALUES**.
This closes *JSON-value parity with the supplied third-party reference*
as a remaining config-difference question; earlier count-only
conclusions are preserved as the preceding measurement.
**Not** proof of peer weight/tensor identity, actual runtime-selected
config, image source equivalence, READY/API success, protection
continuity or strict RM host-stability.

Provenance: `ACTUAL_DGX_OPERATOR_TERMINAL`, but the displayed
terminal portion does **not** include exact local HEAD, clean
worktree or exit status; those are `NOT_CAPTURED_IN_THIS_TRANSCRIPT`.
Do not attribute the run to GitHub HEAD `ad3855a0...` or its
successful PR CI without a separate local checkout receipt.
[Original and follow-up physical evidence](../scripts/benchmark/evidence/dgx-orcarouter-mounted-config-parity-20261018.md).
No weights, GPU or Docker mutation during this inspector run.

**Current active next gate:** exact provenance of official ARM64
CUDA13 vLLM wheel/commit and source-based 48 x 400MiB
`w13_weight` / 48 x 800MiB pre-create allocator comparison
against preserved R23–R32 source and memory evidence. Official
image still `NOT_PRESENT` in the last owner's local inspect;
no new image pull/container start, host mutation, protection
relaxation, KV24, or Draft PR merge is authorized.

## 2026-10-18 — OrcaRouter official ARM64 image registry provenance checked; embedded source still unattributed

GitHub PR #261 and #259 are **Draft / Open / Unmerged**. The
previous source HEAD `dacbdc21d31bd0d1a82169297b6726fd30b7ea53`
completed both exact-head Push CI #39104104591 and
PR CI #39104107142 **SUCCESS** (one validate job each).
This proves CI status for that exact revision only,
not the subsequent documentation commit or a physical DGX run.

Independent public Docker Hub registry review of the peer's
pinned `linux/arm64` image manifest
`sha256:3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e`
confirms CUDA 13.0.1 build metadata, Python 3.12 and FlashInfer
0.6.17 build arguments. But OCI/vLLM revision labels say
`unknown` / `local/vllm-openai:dev`; no immutable exact
wheel-source commit can be derived from those labels.
External deployments report
`vLLM 0.1.dev20073+g8e685d198`, but a public upstream
GitHub contents lookup for `8e685d198` returned 404.
**Official-image exact source and RM allocator differences:
NOT_ATTESTED / NOT_PROVED.** See
[the source-only image review](COMMUNITY-ORCAROUTER-SPARK-PLE-OFFLOAD-20261018.md#2026-10-18--official-arm64-cuda-13-image-provenance-source-only-evidence-and-blocker).

The already-implemented `inspect_orcarouter_mount_config_readonly.py`
digest comparison remains **NOT_RUN_ON_PHYSICAL_DGX**,
pending a clean checkout pinned to a newly CI-qualified exact HEAD
and the protected current-only postcheck.
Historical 2/301/753 + 36/12 shape evidence is counts-only;
no new Docker, checkpoint, PLE, GPU, KV or PR state mutation
was carried out. Default KV=16GiB, 24GiB future conditional
A/B only, strict RM error zero requirement unchanged.

## 2026-10-18 — ACTUAL_DGX OrcaRouter mounted original and override config verified, reference counts match

The physical DGX owner ran the protected Docker-mount-derived,
read-only `inspect_orcarouter_mount_config_readonly.py`
at exact HEAD `2812aa01fdc33d7d4b6b52cdc6e7a1ecec038948`,
with exact-head CI 2/2 SUCCESS. All current protected
image/container identity and RO mount checks **PASS**;
both protected stopped containers share the same
real on-host model root and config override source.
Original `config.json` and existing override are
bounded, readable regular files. **The earlier
`$HOME/models` guessed-path failure was NOT evidence
of checkpoint loss.**

`CONFIG_REWRITE=EXACT_EXPECTED_LAYER_TYPE_REWRITE`;
the original uses 48 layers (36 linear, 12
`qwen_sparse_attention`), the override uses 36
linear + 12 `full_attention`. CT declaration
shape in both: **2 groups / 301 targets / 753 ignored**,
matching the third-party OrcaRouter posted config
**counts only**. Neither the ordered 48 layer
positions nor all CT target/ignore values have
yet been compared to the posted config. The
operation read no weights and performed no Docker
mutation or GPU run.

**Important finding:** direct review of maintained
`scripts/serve.sh` confirms the peer's CUDA/PLE/
FlashInfer environment and resource/security flags
(32g shm, IPC host, memlock, privilege additions),
8192 batching, tool/reasoning parsers, TP=1/mp,
MTP2 and caching switches are all already
present. Raising KV from 16GiB to peer's 24GiB
remains contradicted by our physical stability
tests. The only prominent remaining unresolved
delta is the **official ARM64 CUDA13 image and
its embedded vLLM/allocator/PLE implementation**
(the owner previously confirmed NOT_PRESENT
locally). The new source-only extension performs
private SHA256 comparisons of the full community
pasted JSON and critical subtrees against the
current mounted override, emitting sanitized
MATCH/DIFFERENT/MISSING labels. This extra
comparison is **not yet physically measured**.
[New ACTUAL_DGX evidence](../scripts/benchmark/evidence/dgx-orcarouter-mounted-config-parity-20261018.md).

## 2026-10-18 — ACTUAL_DGX OrcaRouter read-only preflight stopped on guessed model path

The owner fast-forwarded local
`feature/wizard-modular-phase1-20261014` from
`1dddec7..28d5429` and obtained
`EXACT_HEAD_CI=SUCCESS_2_OF_2`.
The existing protected-container read-only postcheck
returned `PASS_CURRENT_ONLY`: both temp ID and
name absent, pinned image ID/size matches, both
managed and legacy exact stopped containers/nested
read-only model binds match. Both container
name-vs-ID `Mounts=ORDER_ONLY` (complete
record equality modulo order) and other fields
`MATCH`. Docker did no mutation/copy/GPU work.
The official peer-run image
`vllm/vllm-openai:qwen38-flash-next-arm64-cu130`
was reported **`OFFICIAL_IMAGE_LOCAL=NOT_PRESENT`**
by a read-only `docker image inspect`; no pull.
Next the older command assumed
`${QWEN38_MODEL_ROOT:-$HOME/models}/qwen3.8-flash-next-orcarouter/config.json`
and stopped at `STOP: Original config missing`
**before** running the maintained checkpoint inspector.

**This does not prove the original OrcaRouter checkpoint or
config was deleted.** The assumed default path was
not independently verified as the existing Docker
`/model` bind `Source`; actual current protected
Docker mounts are better provenance than a guessed
home directory. No model config comparison, safetensors
header read, image-source delta or benchmark was
performed in that physical run.

Follow-up is implemented SOURCE_ONLY as
`scripts/model/inspect_orcarouter_mount_config_readonly.py`:
it reuses the exact-ID current protected postcheck,
reads the existing protected `/model` directory
and nested `/model/config.json` bind sources from
Docker metadata and opens **only two bounded small
JSON configs**, never full model tensors or files.
It emits sanitized categories and CT/layer-type
counts without printing source paths, JSON or secrets,
and compares existing generated override to the
narrow `prepare_config.convert_layer_types` function.
It fails closed on changed identities, multiple/missing
or non-RO binds, differing managed/legacy source
directories, missing/invalid config files and
unreadable or unqualified data. Host execution of
the new code remains **NOT_OBSERVED**; no remote image,
model download or Docker mutation is authorized.
[OrcaRouter community comparator](COMMUNITY-ORCAROUTER-SPARK-PLE-OFFLOAD-20261018.md).

## 2026-10-18 — OrcaRouter-first recovery from community reference, flags mostly already matched

The owner specifically requested revisiting **OrcaRouter
startup stability** using the Arca single-Spark report,
rather than only extrapolating it to lychee888.
GitHub historical physical evidence shows a 16GiB
OrcaRouter run reached strict `PASS/PASS` (Oct 3),
while later 16GiB restarts could reach READY yet
emit strict NVIDIA RM `NV_ERR_NO_MEMORY` and fail
host-stability; Legacy A (Oct 13) was correctly
stopped by the protective monitor at 914MiB
non-CMA free with 13.77GiB swapgrowth before
checkpoint completion. v0.29 PLE-mmap R22
reached API READY but had one strict RM OOM;
mmap reduced later swap pressure yet did not
eliminate the early ~75GiB RM allocation burst.

Review of maintained `scripts/serve.sh` confirms
community options `mp`, legacy CPU PLE offload,
1800s PLE wait, TP1, MTP k=2, 262144 max context,
0.85 GPU utilization and max 3 sequences
are already configured. Local 16GiB KV remains
evidence-driven and **must not be raised to the
forum's 24GiB** without a separately qualified run.
Most meaningful unverified difference: the
community **official CUDA13 ARM64 vLLM image**
versus our custom legacy/v0.29 images, and
the author's separate `config.json` override.
TP1 uniproc/PLE worker hang workaround `mp`
is already in our stack
(https://github.com/vllm-project/vllm/issues/53960).
A recent vLLM image may have different
allocator/model/quantization semantics, but
this has **not been source-proved** or physically
measured here.

**Plan:** source-only image/config comparison and
read-only preflight first; a new isolated Wizard
trial needs separate explicit approval. Keep
protected monitors and 16GiB default; no image
pull/rebuild, Docker start/create/remove, checkpoint
download or GPU run now.
[Authoritative comparison](COMMUNITY-ORCAROUTER-SPARK-PLE-OFFLOAD-20261018.md).

## 2026-10-18 — EXTERNAL_ONLY OrcaRouter single-Spark CPU-offload reference; not lychee888 qualification

The operator supplied the **full third-party report and posted
config.json** from https://arca.live/b/alpaca/181506470.
Its author reports serving **orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4**
on one DGX Spark, TP=1, using
`vllm/vllm-openai:qwen38-flash-next-arm64-cu130`,
`VLLM_PLE_CPU_OFFLOAD=1`, MP executor,
24GiB KV, configured 262144 max context, concurrency 3 and
MTP=2. Author-reported memory 118.4/122GB (~97%);
mixed concurrency-3 output 52.4 tok/s on a short 12-request
benchmark. This is **external third-party user evidence**,
NOT our physical DGX evidence and NOT proof that a real
262K input or long-term stable benchmark passed.

We parsed the posted OrcaRouter config: Qwen4Exp,
`compressed-tensors` `mixed-precision`, 2 CT groups
(300 FP8 channel targets + 1 NVFP4 experts regex),
753 ignored entries, 2 explicitly ignored PLE projection
strings, **no direct PLE ngram target** and
**no `ple_embedding_dtype` declaration**. Thus it is
**NOT the lychee888 FP8 PLE / BF16 global-scale
checkpoint** and cannot clear the actual installed
`NATIVE_FP8_CONFIG_ONLY_SOURCE` dispatch blocker.

Single GB10 has shared system/GPU memory:
pinned CPU PLE offload still costs physical memory
and does not alone resolve lychee888's pinned index
`132279699754` bytes exceeding 128GB nominal.
External upstream file-backed alternatives
[#58439](https://github.com/vllm-project/vllm/pull/58439)
`checkpoint_mapped` and
[#58815](https://github.com/vllm-project/vllm/pull/58815)
`host_file_gather` are **OPEN/UNMERGED** as of
2026-10-18, potentially more relevant than
simple pinned-CPU offload but not part of our
installed image and NOT QUALIFIED for lychee888.
[Full external-evidence comparison](COMMUNITY-ORCAROUTER-SPARK-PLE-OFFLOAD-20261018.md).
No Docker/model download/GPU action is authorized;
current physical protected resources remain
`PASS_CURRENT_ONLY`, original historical
`FAIL_REVIEW` preserved.

## 2026-10-18 — SOURCE_ONLY compressed-tensors config_groups shape inventory for lychee888

The first actual DGX pinned model JSON L0 completed at
`b9114544eb35d7275740cf0ca2e9d010134f7cbb`:
index `total_size=132279699754` bytes, 223047 tensor
keys, 128 PLE shards, one global scale and
`compressed-tensors` `mixed-precision`.
The installed-image PLE selector remains known
only via prior physical SHA/AST evidence
`NATIVE_FP8_CONFIG_ONLY_SOURCE` with no
CT resolver runtime attestation.

The same existing metadata-only assessor was extended
with a **structural CT config-group inventory**:
group count, target-pattern count, PLE substring
mentions in group targets, ignored-target entries
and PLE substring mentions in ignore list.
These counts can help identify which fixed
checkpoint scheme declarations need source review.
**They are NOT runtime target matching.**
Actual CT matching may use layer class names,
regexes, fused remapping and ignored layers;
the installed image's `CompressedTensorsConfig`
implementation and prefix rules are **not
audited**, and a literal string mention alone
does not qualify FP8 PLE dispatch. Missing or
malformed structures are explicitly unknown
or fail-closed; no silent fallback to success.
The implementation is SOURCE_ONLY + synthetic tests.
The next operator command is the same pinned
JSON-only CLI at a successfully validated new HEAD.
No Docker/GPU/weight operations are authorized.

## 2026-10-18 — ACTUAL_DGX pinned lychee888 metadata L0 success and over-nominal index bytes

The operator on the physical DGX verified clean local
`b9114544eb35d7275740cf0ca2e9d010134f7cbb`
(exact-head two CI SUCCESS), then completed
`assess_lychee888_loader.py --json` with
`LYCHEE888_METADATA_COMMAND=COMPLETED`.
Pinned Hub revision:
`1b3c3cedc14fb3bee4294dea5e3515af74b8268a`.
`l0_verdict=INDEX_STRUCTURE_PASS_METADATA_ONLY`;
223,047 indexed keys, exactly 128 PLE weight shards
across ten FP8-PLE filenames, and one listed global
`weight_scale`; PLE config dtype `float8_e4m3fn`.
Pinned quant metadata
`quant_method=compressed-tensors` and
`format=mixed-precision` differs from the
repository NVIDIA `ModelOptMixedPrecisionConfig`
patch. Source dispatch `NATIVE_FP8_CONFIG_ONLY_SOURCE`
comes from an older independently captured physical
source SHA receipt, not a fresh Docker check.

New pinned index `metadata.total_size=132279699754`
bytes, exceeding nominal DGX Spark 128 GB unified
system memory by **4,279,699,754 bytes** under a
hypothetical untransformed full-residency comparison.
Runtime peak memory `NOT_MEASURED`;
this is not proof of OOM, nor proof of fit with
mmap/CPU offload/streaming. Global scale is
index-listed but its actual BF16 tensor dtype,
registration/load/consumption and backend dispatch
remain unverified.

Report `installed_loader_contract=BLOCKED_SOURCE_ONLY_UNQUALIFIED`,
`single_gb10_tp1=NOT_VERIFIED`, and
`SOURCE_ONLY_LOADER_UNQUALIFIED`. No model
download, Docker action or GPU run occurred.
Existing protected-current-state result remains
`PASS_CURRENT_ONLY`; historical one-shot
`FAIL_REVIEW` remains unclassified.
[Physical output](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

## 2026-10-18 — SOURCE_ONLY nominal unified memory screen for lychee888 index

The same standalone pinned metadata/source assessor now
screens `model.safetensors.index.json` `metadata.total_size`
against NVIDIA DGX Spark's **nominal 128 GB decimal
unified system memory** (128,000,000,000 bytes).
The model card reports ~123.25 GiB on disk and an
index tensor size of 132,279,699,754 bytes,
which **exceeds** the nominal memory capacity.
However those card claims and the model-index JSON
are **file-side metadata**, not a real pinned-host
`MemAvailable`, vLLM loaded tensor residency,
peak allocations, CPU/disk offload, mmap behavior,
or usable KV-cache/headroom measurement.
When the indexed `total_size` value is not present,
positive integral, and explicitly returned by the
pinned metadata source, the code fails closed with
`NOT_VERIFIED_INDEX_TOTAL_SIZE_MISSING`.
It never outputs `FIT` or `INSTALLABLE`, even when
index bytes are below nominal size.

One Spark **TP=1** still `NOT_VERIFIED`. This
source-only screen does not authorize checkpoint
download, disk-mmap or GPU experiments, and should
not be used to claim either measured OOM or
measured stable fit. Source: NVIDIA
https://docs.nvidia.com/dgx/dgx-spark/hardware.html;
model card:
https://huggingface.co/lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE.

## 2026-10-18 — SOURCE_ONLY lychee888 installed PLE native-FP8 versus compressed-tensors dispatch gate

The prior actual-DGX `PASS_CURRENT_ONLY` resource safeguard
and physical PLE source SHA remain valid; the historical
one-shot `FAIL_REVIEW` is preserved and not retroactively
explained. The existing independent metadata-vs-source
gate `scripts/model/assess_lychee888_loader.py` now
reports the **installed local Docker image ID**,
physical image-derived PLE Python file SHA256
`a71144c1d36e06f22a2da1b1ada900076597fe5e824a911e7ada86249a0993e7`
and actual static resolver classification
`NATIVE_FP8_CONFIG_ONLY_SOURCE`. It differentiates
pinned model `quant_method=compressed-tensors`,
`format=mixed-precision` from repository NVIDIA patch
`ModelOptMixedPrecisionConfig`, and explicitly
labels the vLLM runtime quant class as **expected but
not independently runtime-attested**.

**Static compatibility: `BLOCKED_SOURCE_ONLY_UNQUALIFIED`.**
The pinned lychee888 metadata has 128 PLE shards and
one index-listed global scale; the installed native
`Fp8Config` selector does **not** prove that a
`CompressedTensorsConfig` checkpoint can take the
FP8 path. Registering BF16 `weight_scale` and
multiplying by scale are only conditional **source
signatures**, not evidence that the scale tensor
was loaded or exercised. Its dtype routing is
`NOT_PROVEN_IN_INSTALLED_SOURCE`, and the CT
prefix/scheme resolution, expert quantization,
actual tensor header dtype and single GB10 TP=1
remain unverified. The source bytes are **not
archived**, so the new gate uses the preserved
ACTUAL_DGX SHA/AST receipt, not runtime execution.

New vLLM PLE documentation exposes explicit
`ple_embedding_dtype` / `CompressedTensorsConfig`
handling (external/reference-only); do **not**
attribute this new implementation to the measured
older installed image without identical-source evidence:
https://docs.vllm.ai/en/latest/api/vllm/models/qwen4_exp/common/ngram_embedding/

This update includes synthetic tests; **SOURCE_ONLY**
until pinned metadata-only CLI is run by an operator.
No image rebuild/patch, source reread, Docker mutation,
checkpoint download or GPU run is authorized.
[Actual source and protection evidence](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

## 2026-10-18 — ACTUAL_DGX order-insensitive PLE postcheck PASS_CURRENT_ONLY; historical failure retained

Operator fast-forwarded to clean exact local
`a24cd3a7ce48c7531cabbdfec0139327eefce18a`,
verified same-head GitHub CI `SUCCESS_2_OF_2` and
executed `inspect_ple_postcheck_readonly.py` on the
actual DGX. Current protected-state verdict:
**`PLE_POSTCHECK_CURRENT_STATIC_POSTCHECK=PASS_CURRENT_ONLY`**.
The one-time temp is **ABSENT_ID_AND_NAME**, installed
image SHA256/size match, both original protected
containers have exact expected identity, `EXITED`,
`ReadonlyRootfs=false` and nested RO model binds.
The managed `NAME_VS_ID_MOUNTS=ORDER_ONLY`
(all complete mount-record values identical, ordering
alone differs), historical A/B
`NAME_VS_ID_MOUNTS=IDENTICAL_ORDER`;
both `NAME_VS_ID_FIELDS=MATCH`. The command made
**no Docker mutation/copy and no GPU run**.

This confirms **current** matching protection
metadata and addresses the previous unqualified
raw `DIFFERENT_Mounts` ambiguity for this new
snapshot. It does **NOT** recover the initial physical
one-shot source probe's unrecorded pre/post field-level
differences. Preserve original `FAIL_REVIEW` as
historical `UNRECOVERABLE_WITHOUT_PRE_POST_FIELD_SNAPSHOTS`;
do not reinterpret it as `PASS` or proven damage.
Physical source-only image PLE SHA remains
`a71144c1d36e06f22a2da1b1ada900076597fe5e824a911e7ada86249a0993e7`,
with native `Fp8Config`-only selector and BF16
scale source signatures. lychee888 checkpoint
`compressed-tensors` routing and GB10 TP=1
remain **NOT_QUALIFIED**.
[Full actual-DGX evidence](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

## 2026-10-18 — ACTUAL_DGX legacy name-vs-ID Mounts raw difference; exact temp absent

At clean local SHA `4fa3a83f33be508736ea4d79f0ed97d24bc0be60`,
the owner verified exact-head CI `SUCCESS_2_OF_2`
and ran the seven-inspect **read-only** protected
postcheck on DGX. It reported
`PLE_POSTCHECK_TEMP_ABSENCE=ABSENT_ID_AND_NAME`,
`IMAGE=MATCH_PINNED_ID_AND_SIZE`, both protected
container exact name/ID/image matches, both `EXITED`,
`ROOTFS=READONLY_FALSE`, and
`MOUNT_TOPOLOGY=MODEL_CONFIG_NESTED_RO_BINDS`.
The **managed** container's whole name-vs-ID inspect
sections were `MATCH`; the **legacy** A/B object's
`NAME_VS_ID_FIELDS=DIFFERENT_Mounts`, so the script
returned `CURRENT_STATIC_POSTCHECK=STOP_REVIEW_REQUIRED`.

This is not evidence that a mount disappeared or that the
protected container was damaged. The older tool compared
`Mounts` as a **serialized ordered list**: order-only
reordering and a real mount-record drift are not
distinguished. The original one-time source probe's
`FAIL_REVIEW` remains in the record; lost before/after
field-level details cannot be recreated by reinspection.

A **SOURCE_ONLY** enhancement to
`scripts/model/inspect_ple_postcheck_readonly.py`
now classifies exact mount-record equality, reordering
only, and destination/type/RW/other mount metadata
differences without disclosing source paths. The next
physical action is ONLY this new read-only diagnosis
after exact-HEAD CI SUCCESS, not creating another
container or using an old mutation approval.
[ACTUAL_DGX transcript](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

## 2026-10-18 — SOURCE_ONLY postcheck differential diagnostic ready after physical probe partial result

After recording the actual physical installed-image PLE source
SHA256 and **`PLE_TEMP_PROTECTED_POSTCHECK=FAIL_REVIEW`**,
the branch adds the independent read-only
`scripts/model/inspect_ple_postcheck_readonly.py` and
offline synthetic tests. It requests only current Docker
metadata (7 `inspect` calls), checks actual temporary
object absence under both **exact ID and name**, protected
image ID/size, protected container IDs, stopped status,
rootfs flag, nested RO mounts and current same-time
name-vs-ID differences in the original fingerprint
fields. It emits only field CATEGORY labels, never bind
source paths, env, inspect JSON or credentials.

**Crucial:** the earlier entire-dictionary pre/post comparison
has no retained field-level receipts; the historical
`FAIL_REVIEW` root cause is **NOT_RECONSTRUCTIBLE**
from a new snapshot. Even if the current-state check
passes, original physical outcome remains
`SOURCE_CAPTURED_STATIC_ONLY, POSTCHECK_FAILED`.
This new script is SOURCE_ONLY until owner runs it;
no new Docker temp create/copy/removal or GPU use is
authorized. [Evidence](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

## 2026-10-18 — ACTUAL_DGX isolated PLE source SHA captured; protected postcheck FAIL_REVIEW

The owner's actual DGX ran the narrowly approved **single**
temporary created-only container source probe at exact clean
code SHA `f1bce18ef6ab444ced20f4efed2ba8ec42a250f0`
with verified `EXACT_HEAD_CI=SUCCESS_2_OF_2`.
Exact existing image SHA256 unchanged; Docker Engine 29.6.2;
created no-mount, unstarted temp
`eb91d18dd1a1b45a4cba233160165bbe43b7835afa21873686402b505aac9375`
(name `qwen38-ple-read-e7e7bac84a0b79e85020ff51`).
Generic Docker-copy transport succeeded and the actual
installed-image-derived PLE source path was
`/usr/local/lib/python3.12/dist-packages/vllm/models/qwen3_8_flash_next/nvidia/ple_layer.py`
with SHA256
`a71144c1d36e06f22a2da1b1ada900076597fe5e824a911e7ada86249a0993e7`.
Static AST labels:
`NATIVE_FP8_CONFIG_ONLY_SOURCE`;
BF16 global scale parameter registration `PRESENT`;
scale multiply `PRESENT`.
All are **source signatures**, not checkpoint loader or TP=1 proof.

Temp cleanup reported `EXACT_ID_REMOVED_VERIFIED`,
**but protected before/after fingerprint comparison reported
`FAIL_REVIEW`**. The script compared full `State`,
`HostConfig`, `Mounts` alongside immutable identity
without field-specific output. **Do not assert protected
resources were preserved unchanged**, or that they were
damaged; root cause remains UNCLASSIFIED pending read-only
physical identity/state inspection. The overall probe did
not reach `SOURCE_CAPTURED_STATIC_ONLY`; physical status
is **PARTIAL / POSTCHECK_FAILED**. No replay of the
already used one-temp approval, no destructive cleanup or
GPU work. Current installed source bytes were not archived,
but file SHA and static signatures were captured.
[Full physical transcript](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

## 2026-10-18 — owner approved exactly one isolated unstarted PLE source probe

The owner explicitly answered **허용** to creating one **new**
temporary container from the exact already-installed
`vllm-skinny-tp1:v1` image, never starting it, reading only
one bounded generic TAR and bounded PLE Python source files,
and removing **only that uniquely labeled newly created ID**.
The owner did **not** approve modifying/removing/restarting the
protected managed or A/B containers, executing GPU code,
downloading models, rebuilding images, Docker daemon upgrades
or protected Draft PR merger.

Source implementation is `scripts/model/probe_isolated_ple_source.py`
with synthetic tests `tests/test_isolated_ple_source_probe.py`.
The script defaults to read-only preview; execution requires
exact immutable image ID and `--approved-scope` literal.
It validates metadata, disk/inode reserve, no image-declared
volumes, zero mounts/network/GPU exposure, exact temp
identity/nonce/state, bounded TAR and source AST evidence,
exact-ID-only cleanup and postchecks. SIGINT/SIGTERM attempt
guarded cleanup, while SIGKILL/power-loss cannot be recovered
automatically. A cleanup identity mismatch is STOP, not force
deletion. All real Docker create/copy/remove steps remain
**ACTUAL_DGX NOT_RUN** until a clean exact successful CI
checkout and owner-terminal execution report are supplied.
The installed PLE source SHA and lychee888 loader/TP=1 remain
`NOT_CAPTURED`/`NOT_QUALIFIED` until that result.
[Scoped operator contract](LYCHEE888-ISOLATED-SOURCE-READ-PLAN.md).

## 2026-10-18 — ACTUAL_DGX isolated-source feasibility planner passed metadata only

The operator cleanly fast-forwarded the DGX branch to exact
`769332111dc4cdfa13e9817544b9166402985f66`
and **physically ran**
`python3 -B scripts/model/audit_installed_ple_image.py --plan-isolated-source`.
Output attests exact image SHA256
`01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4`,
20,629,141,958-byte declared image, **both existing
containers with `MODEL_CONFIG_NESTED_RO_BINDS`**,
`DECLARED_IMAGE_VOLUMES=NONE` and
`ISOLATED_CREATE_ONLY_FEASIBILITY=REVIEW_CANDIDATE_NOT_AUTHORIZED`.
Only three Docker metadata inspections occurred;
`DOCKER_CP_REQUESTS=0`, `DOCKER_MUTATION=NONE`,
`GPU_RUN=NOT_PERFORMED`, `SOURCE_BYTES_CAPTURED=NO`.
This is a **physical read-only preview result**, not
an installed PLE-source or loader/GPU acceptance.

A [separate unapproved source-access proposal](LYCHEE888-ISOLATED-SOURCE-READ-PLAN.md)
now describes a future uniquely owned, **created-but-never-
started, zero-mount** temporary container derived from the
exact installed image ID, one bounded generic copy and
bounded PLE-source inspection, plus strict exact-ID postcheck
and cleanup requirements. It explicitly does **not**
authorize or execute temporary container creation/removal.
Owner authorization, host disk/inode/operation isolation,
exact procedure review, and resource/rollback acceptance
remain **NOT_GRANTED / NOT_CHECKED**. Protected managed and
historical containers remain unchanged and both Draft
PR gates remain blocked.
[Physical output](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

## 2026-10-18 — SOURCE_ONLY isolated PLE source planning gate; no image bytes

The current working branch implements a **preview-only**
`python3 -B scripts/model/audit_installed_ple_image.py --plan-isolated-source`
diagnostic. It uses exactly three existing Docker inspect
requests and fails closed on mismatched immutable image ID,
unexpected protected/historical container state, missing
mount data, invalid image size, or ambiguous image
`Config.Volumes`. It reports only safe source-access
feasibility labels, never host bind source paths or raw
container config. It **does not** create, copy, start,
remove or change a container. A hypothetical mountless
create-only source-copy probe remains a separately reviewed,
**NOT_AUTHORIZED** future operation; volume declarations
are a STOP condition because Docker may create anonymous
volumes. Only SOURCE/CI tests exist for this mode until an
actual DGX run is supplied; it is NOT a physical
image-loader capture or a TP=1 admission.
[Maintained module](../scripts/model/audit_installed_ple_image.py).

External reference-only update: upstream vLLM
[PR #53899](https://github.com/vllm-project/vllm/pull/53899)
was closed without merge on 2026-09-21 and documents
CPU offload TP2/TP4 on GB200, not single GB10 TP=1.
[PR #54882](https://github.com/vllm-project/vllm/pull/54882)
merged on 2026-09-03 but resolves FP8 PLE under
`ModelOptMixedPrecisionConfig`, **not** proof that the
pinned lychee888 `compressed-tensors` `mixed-precision`
config selects that route. The exact vendor image source
SHA remains `NOT_CAPTURED`.

## 2026-10-17 — ACTUAL_DGX legacy same-image nested RO mounts; alternative cp blocked

Operator inspected historical stopped `qwen38-ab-legacy`
(`57eada965768b01eb412b10826ec4f0be9c4ed352abd87957c4ffbe932f27a56`)
on the DGX using **read-only Docker inspect**.
`Image` **exactly matched** the protected managed
`vllm-skinny-tp1:v1` image digest
`sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4`.
`State.Status=exited`, `HostConfig.ReadonlyRootfs=false`.
Its `Mounts` include `/model` and
`/model/config.json`, both bind and `RW=false`;
cache binds `/root/.cache/flashinfer` and
`/root/.cache/vllm` have `RW=true`.
This proves that the historical A/B container has the
**same nested read-only bind configuration** as the managed
container, so it is **not an established Docker-copy
workaround** for the diagnosed Docker 29.6.2 mount replay
bug. No `docker cp` against the legacy container was
performed or implied; no PLE source was captured.

Proceed to a **separately reviewed, bounded nonmutating**
image-origin source-access approach or independent
pinned-source analysis with explicit provenance; do not
bulk-export a ~20.63-GB image without an I/O/resource plan,
access the Docker layer store with unbounded root traversal,
restart Docker, create a fresh container, alter mounts or
touch checkpoint/GPU. The installed-source SHA, FP8 PLE
dispatch, BF16 scale and single-GB10 TP=1 gates remain
unqualified.
[Complete physical evidence](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

## 2026-10-17 — ACTUAL_DGX image size and legacy A/B alternate preview candidate

The owner ran read-only Docker image-size and container-inventory
commands. The pinned image ID remained
`sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4`,
declared image size `20,629,141,958` bytes (~19.21 GiB).
`docker ps -a --filter ancestor=vllm-skinny-tp1:v1`
returned two **stopped** containers:
historical `qwen38-ab-legacy`
(`57eada965768b01eb412b10826ec4f0be9c4ed352abd87957c4ffbe932f27a56`,
exit 137) and protected managed `qwen38-flash-next`
(`f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`,
exit 0), both displaying tag `vllm-skinny-tp1:v1`.
The `ancestor` filter **does not attest** the legacy
container's exact immutable image digest; its mount topology
and source provenance remain unverified.

**Current safe next step:** read-only `docker container inspect`
for **only** `qwen38-ab-legacy` and display its exact `Image`
digest, state, readonly-rootfs flag, and mount **destinations**
/ types / RW flags, never bind Source paths. Do not copy source
from or change the historical container before identity and
mount risk are evaluated. The 20.6-GB image is not a suitable
unreviewed bulk-save target. No GPU run, daemon restart,
image rebuild, model download or PR merge occurred.
[Physical transcript](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

## 2026-10-17 — ACTUAL_DGX 29.6.2 predates verified nested-bind docker cp fix

Read-only actual DGX `docker version` and `docker info`
reported `SERVER_VERSION=29.6.2`, `SERVER_API=1.55`,
and `STORAGE_DRIVER=overlay2`. Official Moby
`docker-v29.6.2` source still uses write-opening
`O_CREATE|O_WRONLY` and `root.Open` in mount replay.
The same source at `docker-v29.8.2` contains the
`O_EXCL` / `O_PATH` improvements; Docker
[29.8.2 release notes](https://docs.docker.com/engine/release-notes/29/)
list the nested bind `docker cp` fix.
Together with the previous **ACTUAL_DGX** nested RO bind topology
and `openat model/config.json: read-only file system`,
this narrows the Docker-copy failure to a **high-confidence
pre-fix daemon mount replay mechanism**, not PLE module absence.
The installed daemon binary's vendor-specific backport state and
internal stack are not independently attested; overlay2 usage alone
is not evidence of a corrupt Docker filesystem.

No Docker update, service restart, image rebuild, bind change,
container execution, checkpoint download or GPU run was performed.
Next: size-and-identity-only inventory of the installed image and
any existing same-image containers before proposing an image-source
extraction method. Physical source stays `NOT_CAPTURED` and
lychee888 remains `NOT_INSTALLABLE`.
[Detailed immutable physical transcript and source comparison](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

## 2026-10-17 — ACTUAL_DGX confirmed nested read-only model mounts at cee107d

Operator fast-forwarded the clean checkout to exact HEAD
`cee107d9e47b278d7dede40a8d401ea9c2ccea32`
and ran Wizard **3 → 7 → 4** on physical DGX.
The protected image/container immutable IDs matched previous
observations. `container_state=exited`,
`container_readonly_rootfs=FALSE`, and the new
`docker_cp_model_config_mount_topology=MODEL_CONFIG_NESTED_RO_BINDS`
**physically verified one nested pair of read-only binds**
at `/model` and `/model/config.json`.
The single `/etc/group` Docker-copy preflight still failed
`FILESYSTEM_READ_ONLY` with exit 1, 76-byte stderr and
`DOCKER_DAEMON_REPLY,FILESYSTEM`; all 24 PLE/GEMM copies
were deliberately skipped (`NOT_ATTEMPTED_PRECHECK_BLOCK`).
`DOCKER_MUTATION=NONE`, `GPU_RUN=NOT_PERFORMED`,
`PLE_IMAGE_AUDIT=INCONCLUSIVE`, source `NOT_CAPTURED`.

Coupled with the preceding exact Docker stderr
`openat model/config.json: read-only file system` for
an unrelated `/etc/group` copy, the protected container
topology now makes the known Docker nested-bind-mount
copy failure a **strong cause hypothesis**. An upstream
[Moby source fix](https://github.com/moby/moby/commit/7420e6240935b25644155447a3197a25af703d35)
for overlapping binds was found, but the installed Docker
Engine/server version and exact patch applicability remain
unverified. No inference of missing PLE source or host root
filesystem failure. **Physical next step:** read-only
Docker Server Version inspection, then evaluate an alternative
source-read route which does not modify the protected
container or Docker configuration.
[Full physical transcript](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

## 2026-10-17 — ACTUAL_DGX Docker copy openat model/config.json; nested readonly bind candidate

The owner captured the exact 76-byte-class Docker daemon error
from the same read-only generic copy control:
`Error response from daemon: openat model/config.json: read-only file system`
(exit 1). The directly supplied host checkout SHA was
`7c93e4db2efd37d0bdc4f2f40748b1fe23d5f360`
at this invocation. A request for `/etc/group` failed while accessing
an unrelated `model/config.json` path. Static project serve source
specifies nested read-only Docker bind mounts `/model:ro` and
`/model/config.json:ro` for config override. Moby's
[2026-09-17 nested bind mount Docker-copy fix](https://github.com/moby/moby/commit/7420e6240935b25644155447a3197a25af703d35)
is a directly relevant candidate mechanism, **not verified as the
installed daemon fault**. The physical container `Mounts` fields
and daemon version remain NOT_CAPTURED.

**SOURCE-only follow-up:** The existing PLE auditor now emits a
sanitized fixed-destination mount topology observation based solely on
existing `docker container inspect` records; it does not print
host bind-source paths. It retains the current fail-closed Docker-copy
preflight and is not a substitute for the next actual physical
Wizard **3 → 7 → 4** execution. This exact source change requires
its own HEAD CI result. Full physical stderr/provenance and
bounded next-gate details:
[lychee888 Docker-copy chronology](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).
No Docker/GPU/model mutation, PR merge or candidate admission.

## 2026-10-17 — ACTUAL_DGX early-stop verified; Docker copy read-only blocker persists

Owner supplied the next actual read-only Wizard **3 → 7 → 4**
output from the same pinned managed image/container IDs recorded in
the [chronological physical evidence](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).
`State.Status=exited` and **`HostConfig.ReadonlyRootfs=FALSE`**
were observed. The single generic `/etc/group` `docker cp`
failed with `FILESYSTEM_READ_ONLY`, exit 1, stderr 76 bytes,
sanitized signals `DOCKER_DAEMON_REPLY,FILESYSTEM`.
The revised auditor correctly reported `ple_candidates_checked=0`
and `NOT_ATTEMPTED_PRECHECK_BLOCK` for all targeted PLE/GEMM
copy requests; **24 downstream attempts were skipped**, not tested.
`PLE_IMAGE_AUDIT=INCONCLUSIVE`, `DOCKER_MUTATION=NONE`,
`GPU_RUN=NOT_PERFORMED`.

This is **ACTUAL_DGX proof of source-auditor fail-closed behavior**,
not proof that PLE/GEMM files are missing, Docker host root is
read-only, the image has a runtime-compatible FP8 loader, or
lychee888 TP=1 can load. Docker storage/mount/rootless/daemon
causality and exact Docker stderr remain unclassified. The
on-host checkout SHA was not supplied; GitHub HEAD/CI are
separate evidence. Next: one bounded, reviewed stderr probe on
an existing non-model file; no Docker mutation, rootfs repair,
service restart, model download, GPU load or protected PR merge.

## 2026-10-17 — ACTUAL_DGX Docker copy FILESYSTEM_READ_ONLY: 25 requests, source not attested

The owner reran read-only Wizard **3 → 7 → 4** on the existing
image `sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4`
and protected managed container
`f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`,
whose visible `container_state=exited`.
Each of the 12 PLE file candidates and 12 Skinny-GEMM
references failed Docker copy with `FILESYSTEM_READ_ONLY`;
the `/etc/group` non-model copy control failed the same way,
with `exit_code=1`, `stderr_bytes=76`, signals
`DOCKER_DAEMON_REPLY,FILESYSTEM`. All source files remained
`NOT_CAPTURED`, `GPU_RUN=NOT_PERFORMED`,
`DOCKER_MUTATION=NONE`, `PLE_IMAGE_AUDIT=INCONCLUSIVE`.
The **common Docker filesystem copy error** has priority over
additional PLE path guessing. Neither checkpoint incompatibility,
missing modules, host filesystem being read-only, nor container
rootfs configured readonly is proven. See
[the latest exact operator transcript](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

The independent inspector now reads
`container_readonly_rootfs` from existing
`HostConfig.ReadonlyRootfs` (TRUE/FALSE/UNKNOWN),
preflights only the bounded `/etc/group` Docker copy,
and aborts **before 24 targeted file attempts** when
`FILESYSTEM_READ_ONLY` or `CONTAINER_ROOTFS_READ_ONLY`
is returned. Target source statuses are explicit
`NOT_ATTEMPTED_PRECHECK_BLOCK`; this is not a loader
admission. Both protected Draft PRs are left unmerged;
no Docker mutation, image rebuild, GPU run or rootfs
remount is proposed. This new early-stop implementation
is SOURCE/CI-only until a new physical Wizard
**3 → 7 → 4** output is supplied. Its latest pre-handoff
implementation plus documentation at
`7c93e4db2efd37d0bdc4f2f40748b1fe23d5f360`
passed GitHub Actions `39035168973` (**SUCCESS**);
that result is synthetic/repository CI, NOT actual DGX
Docker-copy or PLE compatibility evidence.
The [physical evidence index](../scripts/benchmark/evidence/README.md)
now links the latest `FILESYSTEM_READ_ONLY` transcript.
See [lychee888 canonical analysis](LYCHEE888-WIZARD-INTEGRATION.md).

## 2026-10-17 — ACTUAL_DGX: all 25 Docker cp requests unclassified; prioritize shared copy transport

Physical owner ran read-only Wizard **3 → 7 → 4**. It verified local
Docker image SHA `01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4`
and protected managed container ID
`f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`.
Twelve PLE paths and twelve skinny-GEMM paths each returned
`COPY_FAILED_UNCLASSIFIED:12`; the generic tiny `/etc/group`
Docker-copy control also returned `COPY_FAILED_UNCLASSIFIED`.
`PLE_IMAGE_AUDIT=INCONCLUSIVE`, `DOCKER_MUTATION=NONE`,
`GPU_RUN=NOT_PERFORMED`. The exact reason, exit status and
container runtime state were not in this physical output. This
is **not proof of missing vLLM files or loader incompatibility**;
the shared Docker-copy access mechanism is the priority blocker.
See [the actual physical transcript](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

**GitHub SOURCE-only follow-on:** bounded, enumerated Docker
copy error categories and the generic non-model transport
control now also expose `container_state` (allowlist only),
`docker_cp_small_file_exit_code`,
`docker_cp_small_file_stderr_bytes`, and
`docker_cp_small_file_stderr_signals` (fixed keywords only).
No raw Docker stderr, host mount/source paths, credential data,
model files, Docker mutations, service restarts or GPU launches.
The same read-only Wizard **3 → 7 → 4** performs the check
after a clean branch sync. The new actual DGX result is
**NOT_CAPTURED** until the owner runs it; CI is only
synthetic verification. The lychee888 `compressed-tensors`
FP8-PLE source adapter, memory and single Spark TP=1 remain
unqualified; PR #261/#259 stay Draft and unmerged.

## 2026-10-17 — ACTUAL_DGX source copy inconclusive with pinned existing Docker IDs

New physical owner Wizard **3 → 7 → 4** output attested
existing local Docker image ID
`sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4`
and managed container ID
`f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`.
`PLE_DIAGNOSTIC_PLE_CANDIDATES_CHECKED=12`;
`PLE_DIAGNOSTIC_DOCKER_CP_REFERENCE_STATE=SKINNY_GEMM_REFERENCE_UNAVAILABLE`;
`PLE_DIAGNOSTIC_PLE_SOURCE_FILE=NOT_CAPTURED`;
`PLE_IMAGE_AUDIT=INCONCLUSIVE`;
`DOCKER_MUTATION=NONE`, `GPU_RUN=NOT_PERFORMED`.
This is **not proof the image lacks those files**, since the
previous inspector discarded Docker-copy error classifications.
Original log hash and exact on-host checkout SHA were not printed.
Preserve [second actual source-copy transcript](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

**Source-only follow-up:** the existing standalone auditor now
reports scrubbed categorical counts of `docker cp` failures
for PLE and GEMM source requests and probes a single tiny existing
`/etc/group` TAR read as a **transport control**; only its TAR
header is validated in memory, not file data displayed or written.
No Docker start/exec/create, image build/pull, source mount change,
weight download, GPU load or lifecycle mutation.
The operator route remains Wizard **3 → 7 → 4**.
The new classification/transport output is still
**NOT_CAPTURED on actual DGX**. The lychee888 source adapter,
memory and TP=1 runtime remain unqualified. The previously
attested OrcaRouter assets and managed container are protected;
Draft PR #261/#259 must not be merged without approval.

## 2026-10-17 — ACTUAL_DGX PLE source path unresolved; bounded Docker-copy differential added

Physical owner executed read-only Wizard **3 → 7 → 4** after the earlier
mount-safe source fix. The error changed from broad vLLM mount
blocking to `PLE_IMAGE_AUDIT=INCONCLUSIVE: No known PLE loader path
in existing matching container`, with `DOCKER_MUTATION=NONE` and
`GPU_RUN=NOT_PERFORMED`. The original checker attempted eight
fixed Python dist/site-package paths and did not print exact image ID,
matching container ID or `docker cp` failure details. Neither
source absence nor lychee888 incompatibility is established.
The exact chat transcript and interpretation limits are preserved
at [physical source-path evidence](../scripts/benchmark/evidence/dgx-lychee888-ple-path-inconclusive-20261017.md).

GitHub source remediation extends the fixed, bounded Python version
candidate list (12 paths) and adds **read-only existing-image**
`low_latency_gemm.py` sentinel checks after missing PLE paths.
The pinned `scripts/Dockerfile.skinny-gemm` requires that exact
nvidia low-latency GEMM module for image build. On a failed source
inspection the checker now prints validated image/container IDs,
candidate count, sentinel copy status and reference pathname,
while returning `INCONCLUSIVE`. The sentinel is a **package layout**
differential, not a PLE loader proof, new Docker image, or GPU trial.
The same Wizard menu **3 → 7 → 4** is retained, no extra operator
command or GPU activity is required. Updated synthetic tests cover
successful/missing sentinel separation and never admit lychee888
from the reference file alone.

This is **SOURCE/CI** only until a new physical DGX output arrives;
existing managed profile `orcarouter` and protected Docker assets
are untouched. Both Draft PR #261 and #259 remain unmerged.
See [lychee888 canonical analysis](LYCHEE888-WIZARD-INTEGRATION.md).
 
## 2026-10-16 — ACTUAL_DGX PLE image audit INCONCLUSIVE; safe mount-provenance SOURCE fix CI PASS

Operator ran the newly added Wizard **3 → 7 → 4** against their
existing DGX state and received
`PLE_IMAGE_AUDIT=INCONCLUSIVE: Mounted vLLM source could differ
from image layer`, `DOCKER_MUTATION=NONE`,
`GPU_RUN=NOT_PERFORMED`. This is a valid protective stop, **not**
an observed lychee888 GPU loader failure. The old checker blocked
all mounts under a broad Python/vLLM package prefix and did not
report whether the specific `ple_layer.py` path was shadowed.
See [physical mount-check evidence](../scripts/benchmark/evidence/dgx-lychee888-existing-ple-mount-audit-20261016.md).
The original exact image SHA256, conflicting Docker mount identity
and actual effective PLE source remain **NOT_CAPTURED**.

**Repository-only remediation:** `scripts/model/audit_installed_ple_image.py`
now distinguishes mounts covering the exact probed PLE pathname
from unrelated vLLM mounts. For an exact matching existing managed
container/image, it reads a covering host bind source with bounded,
symlink-resistant, identity-checked read-only operations (no Docker
`exec`, container start, image build or model data access), and
reports `source_origin=HOST_BIND_MOUNT_FILE_NOT_IMAGE_LAYER`,
mount destination and actual source SHA256. Unmounted sources still
use `docker cp` and carry separate provenance, while overlapping,
non-bind, unreadable, symlink or changed sources remain fail-closed.
The synthetic CI at commit `003851a34eca5098b83e8aa3dca27fedec7c6bae`,
Actions `38869439987`, **SUCCESS**; source-only, not physical.
Operator route stays Wizard **3 → 7 → 4** after clean fast-forward.
No lychee888 registry, installability, watchdog, image or running
host configuration was changed. Both protected Draft PRs remain
unmerged. See [lychee888 working analysis](LYCHEE888-WIZARD-INTEGRATION.md)
and [canonical module map](../scripts/README.md).

## 2026-10-16 — ACTUAL_DGX lychee888 compressed-tensors gate PASS; loader remains blocked

The owner fast-forwarded the clean DGX working checkout from
`99f04da` to `aea42fa` then used Wizard **3 → 7 → 3**.
The actual fixed-revision Hub JSON output returned
`INDEX_STRUCTURE_PASS_METADATA_ONLY` at
`1b3c3cedc14fb3bee4294dea5e3515af74b8268a`,
223,047 index keys, 128 FP8 PLE shards / ten files / one global
scale key, `float8_e4m3fn` PLE dtype, **`quant_method=compressed-tensors`**,
`format=mixed-precision`, and no top-level `quant_algo`.
`nvidia_patch_source_dispatch=NOT_APPLICABLE`;
`SOURCE_ONLY_LOADER_UNQUALIFIED`,
`MODEL_PAYLOAD_DOWNLOADED=NO` and `GPU_RUN=NOT_PERFORMED`.
This supersedes the new L1 source probe's prior `NOT_CAPTURED` status,
**not** the unverified actual-image loader and single-Spark TP=1 gates.
Exact owner-provided evidence is retained at
[lychee888 actual source-gate report](../scripts/benchmark/evidence/dgx-lychee888-fp8ple-source-gate-physical-20261016.md).

**SOURCE follow-on only:** The external dual-Spark PLE implementation
demonstrates FP8 table selection on explicit `ple_embedding_dtype`,
FP8 weight/BF16 global-scale registration and applying the global
scale during dequantization, but its externally maintained image and
TP=2 evidence do not qualify our installed `vllm-skinny-tp1:v1`
or actual GB10 TP=1 runtime. AGPL external source is referenced,
not copied. A bounded **read-only existing-image source inspector**
now operates through Wizard **3 → 7 → 4**:
`docker image inspect`, `docker container inspect` and
`docker cp` from an already-existing exact matching managed
container only. It cannot create/start/exec any container, build
images or touch GPU/model data, and fails closed if the source/image
identity is unavailable. Its output is explicitly static source
signatures only and `lychee888_tp1_loader=NOT_QUALIFIED`.
This new inspection procedure has **NOT** yet been executed on
the real DGX; CI/synthetic evidence is separate. The candidate
remains planned/disabled. PR #261 and #259 remain protected Draft
and no merge or physical GPU trial is authorized.

## 2026-10-16 — lychee888 pinned FP8-PLE source-only Wizard gate; CI PASS, physical probe pending

Added `scripts/model/assess_lychee888_loader.py` (independent standard-library
metadata/source inspector), its isolated offline synthetic tests and Wizard
Candidate metadata item **3 → 7 → 3**. The fixed
`lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE` immutable revision
is `1b3c3cedc14fb3bee4294dea5e3515af74b8268a`. The new gate
fetches revision-scoped Hub JSON, config and index only, validates
the 128 FP8 PLE shards / 10 files / global-scale key using the maintained
L0 module, and compares quantization method to the existing NVIDIA-only
`ModelOptMixedPrecisionConfig` / per-prefix FP8 patch conditions. It never
claims the NVIDIA image adapter works for lychee888's config; a successful
inspection verdict is explicitly `SOURCE_ONLY_LOADER_UNQUALIFIED`.
It does not download weights or execute Docker/GPU. The actual DGX pinned
Hub result for this new gate remains **NOT_CAPTURED**; the original
2026-10-13 lychee888 pinned Hub L0 PASS is preserved separately.

GitHub SOURCE CI at `2cfeb219ec4eb9b7367c808bbf1763fd7a6aa0a6`,
run `38864476668`, **SUCCESS** (new source gate, Wizard routing
and tests). The exact later documentation HEAD has its own CI.
The protected Draft PR #261/#259 remain unmerged; no model image build,
registration, managed-runtime modification, GPU load, memory-policy change
or model download was authorized. See
[lychee888 model compatibility](LYCHEE888-WIZARD-INTEGRATION.md).

## 2026-10-16 — ACTUAL DGX catplusplus pinned inventory and size reconciliation PASS

Owner re-ran the read-only Wizard **3 → 7 → 1** after the compact
pagination fix against immutable HF revision
`3251fd8afbd08f76368a9bfa71132d9aef364813`.
The physical-DGX terminal returned
`TREE_METADATA_COMPLETE`, `legacy_tree_reconciliation_complete=True`,
`GPU_RUN=NOT_PERFORMED`; pagination progress reached page 20 at
19,820 entries, with 17,448 **files** after directory filtering.
There were 96 `.safetensors` files and 96 index-referenced weight
filenames. These are Hub JSON metadata results, **not** local weight
installation, tensor header validation or GPU load.

**Definitive old-API accounting resolution:** old
`siblings[].size` = **68,586,923,924 bytes** = 63.876550574 GiB;
new full-tree-only files = **119,953,105,520 bytes** =
111.715035066 GiB; complete repository = **188,540,029,444 bytes** =
175.591585640 GiB = **188.540029444 decimal GB** (matches public
UI ~189 GB). Both `legacy_siblings_unknown_size_entries=0` and
`legacy_missing_size_recovered_tree_bytes=0`. The former shortfall
came from filenames missing from the sibling inventory rather than
unknown per-file byte sizes. Supersedes historical `NOT_CAPTURED`
and unresolved notes below; retain their dated provenance.

`root_safetensors_gib=174.8553` (~187.75 decimal GB)
is the **stored root weight data**. NVIDIA lists a single DGX Spark
with 128 decimal GB unified RAM (~119.21 GiB); therefore an
unchanged fully resident model load exceeds the entire system
capacity by ~55.65 GiB before runtime/KV/monitor overhead.
Memory mapping/offload/streaming are unqualified alternatives,
not license to launch. Candidate remains
`RESEARCH_ONLY / PROFILE_INSTALLABLE=0 / GPU_NOT_TESTED`;
lychee888's separate pinned L0 JSON PASS remains distinct.
See [full reconciled candidate record](CATPLUSPLUS-METADATA-COMPATIBILITY.md).
No Docker, weight download, GPU or host mutation was reported.

## 2026-10-16 — Actual DGX Hub pagination failure; compact metadata fix CI PASS

Owner synchronized the Wizard checkout at `22bcba4711ee423ffea062268f4b8de3366938e1`
and selected Model management **3 → 7 → 1** for the revision-pinned
catplusplus remote metadata summary. It failed before validation with
`CATPLUSPLUS_METADATA_FAIL: tree pagination repeated or exceeded 100 pages`.
The old implementation conflated a repeated URL with the 100-page limit
and used costly `expand=true` (documented at ~50 files/page). This
was a **physical host execution of read-only Hub JSON inspection**, NOT
physical model loading, READY or inference; 63.88 GiB vs ~189 GB remains
unresolved.

Source fix: `scripts/model/inspect_catplusplus_metadata.py` now uses
`recursive=true&expand=false&limit=1000`, enforces pinned-revision
pagination links, distinguishes repeated URLs/paths and empty-progress
pages, reports progress, and fails closed when the 256-page ceiling
is exceeded without claiming inventory completeness. Additional
synthetic/offline tests cover 105 unique pages, loops, missing progress,
unsafe links and the hard page limit. Source/CI at
`6858b4252d3e8768bd3c62a91508d7d4f614e176`, GitHub
Actions run `38859700597`, **SUCCESS**. The exact Hugging Face
model inventory still needs a new read-only DGX run via Wizard
**3 → 7 → 1**, without Docker, GPU or checkpoint download. The
status of PR #261 remains protected Draft; no merge was authorized.
See [catplusplus compatibility record](CATPLUSPLUS-METADATA-COMPATIBILITY.md).

## 2026-10-16 — Retired Hybrid research routes removed from active Wizard

Following the operator's request, the four completed Hybrid-only Model
management routes (former items 7–10 for H6 Phase-0, H3–H6 dependency
inspection, H6 launch admission and historical retirement guidance) have
been removed from the active terminal Wizard. The read-only candidate Hub
metadata submenu moved from item 11 to **item 7**. Historical Hybrid
inspection scripts and the retired retirement-menu module remain in Git
for reproducibility but are no longer imported by active Wizard routing.
Stale active-menu wording claiming the physically removed H3–H6 stages
must still be retained was corrected. The `orcarouter-hybrid` registry
record stays `retired` / `PROFILE_INSTALLABLE=0`; neither the registry's
historical identity nor the original local research evidence was deleted.

SOURCE + synthetic CI through commit `d78ad60e16719fc31cca5b94bde1bc0a11fbb3ef`:
GitHub Actions run `38857649562` **SUCCESS**, after updating assertions
that previously required the obsolete Hybrid menu. Regression tests now
verify the retired menu IDs cannot reach historical scripts and the
read-only source guards remain preserved. Stable general policy for
removing obsolete research-only menu routes is in
`docs/SESSION-HANDOFF-PROMPT.md`. No operator DGX source-sync,
Docker/model deletion, host mutation or new GPU trial is claimed by
these repository-only changes. PR #261/#259 remain protected Draft.

## 2026-10-16 — Candidate metadata Wizard integrated; source-only CI PASS

The canonical operator Wizard now exposes Model management item 11
(read-only candidate metadata), with catplusplus summary/full-JSON options
routed to the independent pinned Hub inspector. No candidate was made
installable. Error, cancellation, EOF and mock interpreter invocation
are covered by isolated synthetic Wizard tests. The catplusplus inspector
additionally reconciles old API `siblings[].size` subtotals with the
complete revision-pinned tree, separately accounting for legacy NULL sizes
and tree-only files, with four new offline validation tests.

GitHub PR #261 source/CI head `92dbb1ad8acf28bffe5fabdf5d003b87997e31be`:
Actions run `38856100612` **SUCCESS**, independently of any physical DGX
execution. Stable independent-module/Wizard-managed-operation rules were
recorded in `docs/SESSION-HANDOFF-PROMPT.md` (earlier CI run
`38855790439` SUCCESS). Both PR #261 and #259 remain protected Draft.
**Physical pinned full-tree API output remains NOT_CAPTURED.**
63.88 GiB versus ~189 GB is still only a source-level size discrepancy
hypothesis, not settled actual file accounting. No weights, GPU, Docker,
host state or protected assets were changed by these repository commits.

## 2026-10-16 — Candidate SOURCE metadata inspector added; Hub inventory and GPU unverified

A standalone standard-library catplusplus revision-pinned HF metadata tree
inspector and synthetic/offline tests were added. It reads only JSON (complete
paginated file tree, config, optional index) to distinguish legacy
siblings[].size subtotal from repository/weight file bytes. Historical
63.87655 GiB and public UI ~189 GB have **NOT** yet been reconciled by an
actual pinned full-tree output; model weights and GPU were not touched.
The current model card and config show ModelOpt MIXED_PRECISION, MXFP8
projections and NVFP4 experts, but current main-web config is not
independent pinned-revision validation. Source L1 found no qualified TP=1
FP8-PLE resolver in the current managed lychee888 path; the dual-DGX
external override is not a single-GB10 proof.
See [catplusplus investigation](CATPLUSPLUS-METADATA-COMPATIBILITY.md)
and [lychee888 plan](LYCHEE888-WIZARD-INTEGRATION.md). Both candidates
remain unapproved for real GPU trials or installation. Keep PR #261 and
#259 Draft/Unmerged. CI result for the latest fix must be checked on its
exact HEAD separately.

## 2026-10-16 — Physical managed-state retention audit PASS; cleanup closed

Owner fast-forwarded the DGX checkout through commit `9d84c39` and ran
`python3 -B scripts/storage/state-retention-audit.py` against
`/home/inlc/.local/state/qwen38-spark`. Physical output:
`STATE_DELETE_AUTHORIZED=NO`, `STATE_FILES_DELETED=0`; all inspected
top-level items had `links=0 boundaries=0`. Main measured allocated
sizes: `mazinb-m1=216.24 MiB` (research data),
`monitor.log=2.14 MiB` (managed lifecycle diagnostics),
`retirement-archives=1.69 MiB` including protected original
Hybrid Docker archive `1.40 MiB` and Mazinb archive `0.29 MiB`,
`hybrid-retirement-evidence=0.74 MiB`, and
`hybrid-h6-m1=0.10 MiB`. `ab-trials` and `analysis` are
each less than 0.2 MiB; 30 stability JSON and runtime
validation JSON entries are individually tiny.

**Operator disposition:** No further state-file deletion warranted.
Most allocated state space is the valuable Mazinb M1
benchmark history; Git has only sanitized Hybrid records,
not raw 17-container logs. Maintain install/ownership/lock/
recovery files, benchmark archives and historical evidence.
The `retirement-archives` parent size already includes its children;
do not double-count. Audit is classification only, not a
deletion approval. Close the immediate Hybrid/state cleanup
task and resume metadata-first model candidate evaluation.
Source CI for the audit + Wizard Storage item 5 at
`9d84c39ebd7ed6155199b6c1db4e58ae445dab0e`
completed successfully; real host audit above was separate.

## 2026-10-16 — Managed state retention review and next candidate metadata (read-only)

DGX owner has completed independent post-removal checks: retired Hybrid H3–H6
model directories absent, protected OrcaRouter directory present, and local
17-container private retirement archive SHA256 files still pass. Final
available bytes observed: `449058615296`. Do not remove original raw
Hybrid archive based merely on its Git-pinned checksums: Git retains
summaries and log hashes, **not the raw logs**. A distinct
`retirement-archives/mazinb-docker-20261014T103718Z-7e238b9aeb`
must remain untouched by Hybrid cleanup.

The owner inspected `~/.local/state/qwen38-spark`, which also includes
`install.env`, `asset-ownership.json`, `operation.lock`,
`config.vllm.json`, `monitor.log`, multiple `runtime-validation*.json`,
30 `stability-N.json` files, `ab-trials`, `analysis`,
`hybrid-h6-m1` and `hybrid-retirement-evidence`. These are **not all
disposable**: runtime and ownership files are protected, and raw evidence
archives contain non-Git-backed material. Historical Hybrid state and
stability results require separate duplicate/reference review, not blanket
deletion.

A small self-contained read-only classifier now lives in
`scripts/storage/state-retention-audit.py`, exposed under Wizard
Storage item 5, plus isolated synthetic tests. It reports
allocation-sized estimates, retention categories, symlinks and filesystem
boundary warnings **without exposing state-file contents or deleting
anything**. Its actual DGX output has NOT yet been collected. There is
currently no approved command for deleting these state folders.

Owner's real DGX remote metadata-only model inspection:
`lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE` revision
`1b3c3cedc14fb3bee4294dea5e3515af74b8268a`, reported
`remote_size_gib=123.24575388710946`, public, and separate MTP file marker;
`catplusplus/Qwen3.8-Flash-Next-uncensored-NVFP4-mixed` revision
`3251fd8afbd08f76368a9bfa71132d9aef364813`, reported
`remote_size_gib=63.87655057385564`, public. Both reported
`LOCAL_REQUIRED` with no tensor/layout qualification. Public
Hugging Face file-browser UI shows **189 GB** for the latter, differing
from the metadata-only inspector's 63.88 GiB; measurement scope is not
yet reconciled. **Do not budget download/physical storage based on
one of these numbers until exact file inventory and selective download
scope are verified**. No GPU launch or model-weight download occurred.

## 2026-10-16 — VERIFIED: Hybrid local retirement completed; Wizard guided cleanup modularized

**Physical DGX result, independently checked:** exactly 17 stopped Hybrid research Docker containers removed; all four H3/H4/H5/H6 checkpoint directories removed. Their names are recorded in the [immutable retirement evidence](../scripts/benchmark/evidence/dgx-hybrid-local-retirement-scope-20261015.md). 17-container raw-log+metadata private archive remains on DGX with 34/34 SHA256-verified files; its `SHA256SUMS` SHA256 is `79ac8fcce46cc7063a6f0952537151dd80fda2d63a3e2828ee594a705c0f6701`. Git contains sanitized 17-ID inventory, per-log digests/marker counts and H6 physical failure report; it does **not** contain raw logs or deleted weight blobs.

Actual model removal reported `available_bytes_before=303420813312`, `available_bytes_after=449058627584`, `available_bytes_delta=145637814272` (135.64 GiB). Independent filesystem check later returned `449058615296` available bytes. Earlier exact-17 Docker retirement measured `5099741184` additional available bytes. These are observed intervals, not an immutable per-object storage attribution. Post-delete check confirmed **all four Hybrid directories absent**, protected OrcaRouter original present, and the SHA256 archive remained checkable. Remaining Docker listing had eight non-target objects; `open-webui` and `portainer` were running. Managed OrcaRouter Docker was retained but was observed exited, **not proven READY**. No physical H6 inference/benchmark success occurred.

**Wizard improvement:** model-management item 10 now delegates to small dedicated `scripts/wizard/hybrid-retirement-menu.sh` (sourced by `scripts/wizard/menus.sh`). It exposes read-only stage status, archive verification, Docker reference inventory and guided evidence-first cleanup policy. This is **NOT** yet a generic automatic cleanup engine. Historical exact-17 and exact-H3-H6 scripts are pinned to the completed 2026-10-16 retirement and must not be reused for new experiments. Keep menus thin and implement generic discovery/approval/resume in independently testable modules. The operator explicitly prioritizes *finishing this small, safe Wizard improvement quickly* and then returning to other checkpoint candidates.

**Next candidate research (not GPU execution):** `lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE` is planned/not installable, and `catplusplus/Qwen3.8-Flash-Next-uncensored-NVFP4-mixed` is a research-only candidate. Begin with revision-pinned remote metadata and single-GB10 compatibility investigation, not a large download or GPU launch. See [lychee888 plan](LYCHEE888-WIZARD-INTEGRATION.md), [mission and model scope](PROJECT-MISSION-AND-MODEL-SCOPE.md), and [Hybrid final evidence](../scripts/benchmark/evidence/dgx-hybrid-local-retirement-scope-20261015.md).


## 2026-10-15 — DIRECTION CHANGE: multi-model validation + compact handoff

OPERATOR DECISION (not a physical GPU result): defer mazinb-centered Wizard completion. Maintain the wizard-first long-term mission, but improve common Wizard support incrementally while researching/validating `lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE` and new candidate `catplusplus/Qwen3.8-Flash-Next-uncensored-NVFP4-mixed`. Catplusplus is **research-only**, not registered, installed, benchmarked, or verified compatible. mazinb retains its historical real DGX READY and benchmark reference.

Hybrid H6 remains protected/stopped. Next decision is read-only assessment of the double 81-shard loading/memory behavior before deciding whether to retire Hybrid; do not infer success from absence of a kernel Xid. No new GPU run or asset deletion authorized. Preserve H7/H20 references, old managed OrcaRouter ID, H6 archive, and both Draft PR #261/#259. The older planned benchmark→retire→rebuild sequence is **deferred pending the explicit keep/retire decision**, not silently completed.

SESSION POLICY: stationary rules/history/evidence belong in canonical permanent docs. `docs/SESSION-HANDOFF-PROMPT.md` is a compact entrypoint with source-of-truth links, invariant guardrails and live delta only. Full previous handoff prose remains retrievable in Git history; do not copy that entire historical log into new conversation prompts.

## 2026-10-15 — Physical H6 Docker tail fully normalized: CR/LF counts and exception resolved

Actual DGX operator confirmed **all seven original H6 evidence
files SHA256 PASS** again and measured raw `docker.log`
delimiter counts: **244 LF, 97 CR, 336 Python
`splitlines()` logical lines**. This explains the
earlier `nl -ba` vs Python index discrepancy
without changing the evidence.
First shard pass **81/81**, 577.40s at
`docker.log` Python logical row 234 (~23:28:33 KST);
the next pass starts 0/81 at row 244 (~23:28:46),
reaches 5/81 before API shutdown row **255**
(23:28:58 KST), and prints 6/81–9/81
after the traceback in the captured output stream.
The single terminal traceback occupies rows **256–328**:
API was initializing EngineCore via AsyncMPClient /
ZeroMQ poll and vLLM `_interrupt_init` raised
`KeyboardInterrupt("terminated")` at row 327,
`KeyboardInterrupt: terminated` at row 328.
Previous watchdog stop was **23:28:55 KST**.
Worker progress after the API message may be
interleaved/buffered or genuine graceful-stop lag;
neither is a demonstrated post-exit GPU workload.
No independent CUDA/RM/OOM/ModelOpt crash is
evidenced by this terminal traceback. Root cause of
whether watchdog intervention was *necessary*
remains **INCONCLUSIVE**, notwithstanding definite
watchdog-triggered termination.
The prior docs/CI repair SHA `bedb80cf05fc115aa670e8aaab3c2274473e73bb`
passed **Push #38662904456 and PR #38662909227**;
this new commit needs independent CI verification.
No H6 READY/benchmark, off-host verified backup,
GPU rerun, guard weakening, deletion or PR merge.
[Permanent detailed evidence](../scripts/benchmark/evidence/dgx-hybrid-h6-m1-protection-stop-physical-20261014.md).

## 2026-10-15 — H6 interrupted vLLM initialization and CR-rendering caveat

Actual archived H6 owner terminal again verified **seven
SHA256 files PASS**. The shutdown traceback visibly ended
with vLLM `entry.py:_interrupt_init` raising
`KeyboardInterrupt("terminated")` and
`KeyboardInterrupt: terminated`, consistent with
the watchdog's pinned memory-protection stop
23:28:55 KST and subsequent vLLM EngineCore SIGTERM
message around 23:28:58. No independent GPU/RM OOM
cause is established. `nl -ba` printed numbered Docker
rows 235–240 followed by unnumbered shard progress bars;
because tqdm uses carriage returns, these shell line
numbers cannot safely be equated with the earlier Python
universal-newline **336 logical lines**. Next inspection,
if required, must use Python-indexed escaped output on
original `docker.log` without modifying archive files.
Confirmed source monitor path is
`scripts/runtime/monitor-runtime.sh`, identical Git blob
`017451b75b69da00bb10d9aec591a161a56862dc`
at the original H6 launch and later audit revisions.
Prior docs commit `cc5bdfa3...` had **both Push and PR
CI FAILED** solely on `test_script_layout` category
restriction: the physical evidence Markdown under
`scripts/benchmark/` included a forbidden literal
cross-category `runtime` path. The benchmark evidence
was corrected to retain the script name + hash without
the forbidden path. New head's CI is separate and cannot
be presumed passed. No GPU run, protection change,
Docker deletion, benchmark, PR merge or off-host backup
qualification. [Permanent analysis](../scripts/benchmark/evidence/dgx-hybrid-h6-m1-protection-stop-physical-20261014.md).

## 2026-10-15 — H6 terminal cross-check: watchdog stop during second shard pass

Actual operator read-only analysis, seven on-host SHA256 entries
PASS. `monitor.log`: 270 lines/17 selected regex matches.
`docker.log`: 336 lines/225 regex matches (only last 35 printed,
400 chars each; full traceback not yet reviewed). Last healthy
heartbeat at **23:28:13 KST** had non-CMA Available
**42,581 MiB**, Free **4,025 MiB**, SwapFree **143,030 MiB**.
At **23:28:46 KST** (`14:28:46` vLLM UTC timestamp), Worker
logged EXT4/checkpoint **173.59 GiB**/RAM **27.19 GiB**
auto-prefetch **disabled INFO**, with a new 0/81 checkpoint-shard
pass. At **23:28:47**, Available fell to **27,809 MiB**
(−14,772 MiB in 34s), Free **1,795 MiB**, and host-wide
swap-growth **3,427 MiB**; protection 1/5 to 5/5 ran
23:28:47–55 (last Free **726 MiB**), followed by
`PROTECT stopping` **23:28:55**. API Server shutdown
`send sigterm to EngineCore` at **23:28:58 KST**;
Docker veth teardown **23:29:11 KST**. Exact physical
source `a30fe34...` and audited head `ca1cb0c9...`
have **identical** monitor script blob
`017451b75b69da00bb10d9aec591a161a56862dc`
and H6 controller blob
`19dd0823dc71d468890e334e4d484a34a1e1f56d`.
Host-wide swap usage was already accumulated (~3.4GiB)
by last healthy heartbeat; crossing the 2GiB non-CMA
immediately-Free threshold armed the established legacy
swap-growth protection. Model loader INFO is not a
GPU allocation failure; truncated Python traceback
does not establish an independent model crash.
Watchdog **direct stop reason CONFIRMED**, necessity/false
positive and NVIDIA RM allocation safety **INCONCLUSIVE**;
no H6 READY/bench or independently verified off-host backup.
No GPU rerun, guard relaxation, deletion, or PR merge.
[Detailed forensic correlation](../scripts/benchmark/evidence/dgx-hybrid-h6-m1-protection-stop-physical-20261014.md).

## 2026-10-15 — H6 kernel all 13 physical lines reviewed: Docker veth only

Owner again confirmed **7/7 on-host SHA256 PASS** and pasted all
13 unfiltered saved kernel messages from H6 window. Rows 1–7 at
`23:18:03.922–.928 KST` are `docker0`/veth attach and
`forwarding`. A separate H6 watchdog stop marker is at
`23:28:55 KST`. Rows 8–13 at `23:29:11.449–.484 KST`
are the same interface rename/disable/unregister, **~16.45–16.48 s**
after the stop marker. Thus the logged kernel events are exclusively
Docker virtual-network lifecycle, and **no NVIDIA RM/Xid/GPU allocator/
OOM errors were recorded in these 13 lines**. The log itself has no
Docker container ID; interface-to-H6 association is temporal, not
independently ID-pinned by kernel text. No entries exist between the
two event clusters, which is NOT proof of complete event retention,
absence of silent GPU failures, or an unnecessary watchdog.
The established low non-CMA Free + host-wide swap-growth 5/5
protective stop stands; necessity/false-positive classification is
**INCONCLUSIVE**. No READY, inference, bench, off-host backup,
restart, threshold weakening, deletion, or merge authorized.
[Full 13-line transcript](../scripts/benchmark/evidence/dgx-hybrid-h6-m1-protection-stop-physical-20261014.md).

## 2026-10-15 — H6 archived kernel scan: 13 lines, zero broad RM/GPU/OOM matches

The operator rechecked all **seven** on-host SHA256 archive entries
and independently scanned the already saved `kernel-window.log`
**read-only**. `H6_KERNEL_LINES=13`, first timestamp
`2026-10-14T23:18:03.922217+09:00` (Docker veth blocking state),
last timestamp `2026-10-14T23:29:11.483687+09:00` (Docker veth
disabled state), spanning watchdog STOP at 23:28:55 KST.
`H6_KERNEL_BROAD_MATCHES=0` for
`nvidia|nvrm|xid|gpu|allocat|fail|error|fault|oom|out of memory|memory pressure|smmu|iommu|gsp|uvm|dma`
(case insensitive). These are **zero matches in 13 archived kernel
messages**, not proof that unlogged GPU allocation failures
could not happen or that memory protection was unnecessary.
The first/last records bracket the stop but do not prove the
kernel journal is complete. The other 11 raw lines have not been
pasted for unfiltered review. Confirmed watchdog cause remains
low non-CMA Free + >=256 MiB host-wide swap growth, 5/5 warnings.
`H6_ROOT_CAUSE_PROTECTION_NECESSITY=INCONCLUSIVE`;
`API_READY=NOT_OBSERVED`; `BENCHMARK=NOT_MEASURED`;
`OFF_HOST_BACKUP=NOT_VERIFIED`; no restart/tuning/deletion/merge.
[Detailed physical evidence](../scripts/benchmark/evidence/dgx-hybrid-h6-m1-protection-stop-physical-20261014.md).

## 2026-10-15 — H6 kernel window physically archived; selected RM/OOM strings absent

Owner-operated DGX evidence collection used interactive sudo and
verified a nonempty local kernel journal interval
**2026-10-14 23:18:03–23:29:55 KST** (stop was 23:28:55 KST).
The original six forensic evidence files and new
`kernel-window.log` passed all **seven** entries in the on-host
`SHA256SUMS.txt` check at
`/home/inlc/h6-m1-evidence-20261014.dvQmt6eq`.
The specified `NVRM|Xid|NV_ERR_NO_MEMORY|_memdescAllocInternal|oom-killer|out of memory`
grep emitted **zero matches**. This is a *captured-window limited
negative pattern search*, NOT proof of healthy NVIDIA RM or that
all kernel error text/coverage has been exhaustively reviewed.
The preceding `NOT_CAPTURED` statements below describe an earlier
failed `sudo -n` attempt, now superseded **for capture status only**.
Known H6 low-non-CMA-Free/swap-growth watchdog trigger remains
confirmed; false-positive versus necessary protection remains
`INCONCLUSIVE`. Original run source `a30fe34b...`; physical
read-only forensic audit source `2e61645c...`; follow-up source
hardening head `6936f8c9...` (CI PASS, **not yet physically
requalified by the new script**). No model restart, benchmark, deletion,
protection relaxation or off-host backup verification. PR #261 and
PR #259 remain Draft/unmerged.
[Full selective evidence](../scripts/benchmark/evidence/dgx-hybrid-h6-m1-protection-stop-physical-20261014.md).

## 2026-10-15 — H6 PHYSICAL read-only forensics: watchdog trigger confirmed; RM unresolved

At exact audit source `2e61645c59dc005c474139bde1b3313ff62728b8`
the operator ran `hybrid-h6-forensics-readonly.py --latest`.
Journal/stop marker/Docker exact ID matched and `RC=0` confirmed the
protected `failed_stopped` Docker object. Five actual watchdog warnings
(23:28:47–23:28:55 KST) confirm
`noncmafree < 2GiB && swapgrowth >= 256MiB`
with `noncma_available=27809–28282MiB`, `swapgrowth=3427MiB`,
final `noncmafree=726MiB`; H6 legacy swap-growth response was active.
The 10-GiB Available and 8-GiB SwapFree guards were not the trigger.
This identifies the watchdog decision, **not proof of NVIDIA RM health**.

Six raw trial/monitor/Docker files were copied into on-host directory
`/home/inlc/h6-m1-evidence-20261014.dvQmt6eq` and
`sha256sum -c` passed. No independent off-host backup verified.
`sudo -n` failed due to password requirement; NVIDIA RM/Xid kernel
window still NOT_CAPTURED. The attempted manual 14:18 interval was
UTC, whereas the host monitor uses KST 23:18; use the local H6 journal
`kernel_since` and actual stop time to bound a correct query.
No H6 READY, inference, or benchmark. No rerun, protection loosening,
deletion, or merge of Draft PRs #261/#259.
[Detailed physical evidence](../scripts/benchmark/evidence/dgx-hybrid-h6-m1-protection-stop-physical-20261014.md).

## 2026-10-14 — Actual H6 first GPU load MEMORY-PROTECTION STOP; benchmark NOT_MEASURED

The operator physically ran approved Wizard **Benchmark 5→20** at
exact `a30fe34b8c2fd3ad511d79876ac95ad69ac32523`.
A unique H6 isolated container
`qwen38-hybrid-h6-m1-20261014141803-69ef3492`, ID
`e526189f1093e95d81568d82eb10b8beaeb6227adca49029f241634769e6cbc7`,
reached **DOCKER_STARTED_UNQUALIFIED**, then Wizard emitted
`H6_EXACT_STOPPED_ID` and `H6_SESSION_BLOCKED=memory_protection_stop_marker`.
Read-only verification: journal `failed_stopped`, Docker `exited`,
`Running=false`, `OOMKilled=false`, `ExitCode=1`.
One 81/81 shard loading pass completed in 577.40 s, **then another
81-shard loading pass began** (at least 9/81 observed); READY was
NEVER observed. The post-stop host had 118Gi RAM available and 142Gi
swap free, but this **does not prove at-stop headroom**.
Full non-CMA/swap warning samples (especially `protect=5/5`),
exact monitor marker, and NVIDIA RM kernel events remain TO_BE_AUDITED.
Do not ascribe failure to the FP4/ModelOpt warnings or API
`KeyboardInterrupt` termination trace alone.
**No immediate rerun, benchmark, deletion or loosening watchdog
thresholds.** Historical H7/H20 model aliases and 16 stopped Docker
mount references remain protected; full H3–H6 retire blocked.

New **source-only** Wizard **Benchmark 5→21** forensics will display
bounded critical warnings plus independently pinned journal,
stop marker and exact stopped Docker ID; it does not mutate host.
[Permanent selective physical evidence](../scripts/benchmark/evidence/dgx-hybrid-h6-m1-protection-stop-physical-20261014.md).
CI and physical forensic check must pass separately before
any safe candidate configuration decision.

## 2026-10-14 — REAL DGX Wizard Benchmark 5→17/18/19: H6 preflight PASS

**Exact checkout:** `1de3ec0c9ae4cba5eb44fc66176d0c96b04371e6`
fast-forward from `e61f6b4` succeeded. Real DGX Wizard
**Benchmark 17** plan displayed `H6_PLAN=ISOLATED_16G_NO_BOOT`,
loopback port 18890, watchdog exact-ID before start;
**Benchmark 18** reported `H6_SESSION=ABSENT`.
**Benchmark 19**, with sudo kernel-journal read access, returned
`H6_PREFLIGHT=PASS_READ_ONLY`,
`H6_CANDIDATE_START=NOT_PERFORMED`.
Pinned existing old Docker ID
`f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`;
H6 runtime image
`sha256:dba5d8af279fb85901e6d8911f1a59ecc45b669b0948ab8d01d7c7d1c5815734`;
immutable release `ff67bab3c94d6992f61b9535836df97f03b9c022`.
The installed manifest remains OrcaRouter legacy image
`vllm-skinny-tp1:v1`, **not** the H6 isolated runtime image;
its identity was deliberately preserved.

**Result interpretation:** the actual host has sufficient
admission memory/swap/storage at this instant, H6 stage structure,
v0.29 image, sudo journal read and non-boot service policy pass
the *preflight*; **no new Docker container is created, no GPU model is
started, no READY/soak/inference, no llama-benchy numbers exist**.
Historical H7/H20 aliases and 16 old Docker mounts still prevent
H3–H6 cleanup. DO NOT run Wizard Benchmark 20 without separate
explicit operator approval for new GPU load.

**Follow-up source hardening:** check the running Git checkout is
clean and pin the exact 40-character HEAD before trial creation,
record the source SHA in the session journal, reject any source
drift during GPU load/soak/benchmark, and require that same pinned
source when admitting Terminal B. The new hardening is SOURCE_ONLY
until CI passes and its **new commit** is installed on DGX.
The observed physical preflight above belongs to prior source
`1de3ec0`; never claim the new source physically qualified yet.
Keep PR #261 Draft/unmerged and PR #259 unchanged.

## 2026-10-14 — Actual DGX H6 start-admission RC=3; isolated controller source-only

DGX checked exact commit `e61f6b4d44624e8ebb454eac3288d13e3904f370`:
Hybrid H3–H6 structural PASS, managed idle PASS, monitor=1,
protect=1, heartbeat=60, canonical predecessor stopped exact ID,
but `SERVICE_ENABLED=0` and `SERVICE_OWNED=0` block
**installer-managed profile switch**. The physical start-admission
`BLOCKED_PENDING_SAFE_CONTROLLER` result (RC=3) was expected.
A new Wizard Benchmark **17–20** isolated-H6 source controller
handles no-boot/no-service protected candidate create + exact-ID
watchdog-before-start + localhost port 18890 + 16-GiB KV and
forensic STOP; a separate Terminal-B benchmark lock adds
readiness/monitor/kernel RM admission. CI, physical preflight and
H6 live qualification must be recorded independently; **none yet
performed for this new controller at the time of authoring**.
H6 bench NOT_MEASURED; original H3–H6 full retire blocked by
2 preserved H7/H20 aliases and 16 old Docker trial mounts.
Canonical [runbook](HYBRID-BENCH-REBUILD-CYCLE.md).

## 2026-10-14 — DGX dependency audit PHYSICAL PASS (retirement BLOCKED)

At exact `443fd2bd01f0bd5314ee6a0dc66608d2059dfbf6`, operator
performed the new physical Hybrid reference audit.
`PROTECTED_PROFILE_REFERENCES=2` (H7 group metadata and H20
ModelOpt conversion both alias the existing H6 checkpoint);
`DOCKER_CONTAINERS_INSPECTED=24`;
`DOCKER_REFERENCING_CONTAINERS=16` all exited, including
`DOCKER_OTHER_ROOT_REVIEW_CONTAINERS=11` recorded with historical
`/home/inlc/models` mounts.
`HYBRID_REFERENCE_AUDIT=BLOCKED_KNOWN_REFERENCES`,
`HYBRID_DELETION_AUTHORIZED=NO`, RC=3 **EXPECTED**.
No models/services/containers changed; H6 first bench NOT_MEASURED.

**Independent startup issue identified in source:** DGX installed manifest
last reported `SERVICE_ENABLED=0`, while `install.sh` requires
`SERVICE_ENABLED=1` AND `SERVICE_OWNED=1` for a real managed
profile switch. The current shutdown state cannot safely be converted
into a qualified live H6 switch by blindly running
`install.sh --model orcarouter-hybrid`. Even restoring ownership
requires careful no-boot/no-accidental-start planning. A source-only
read-only Wizard **Models 3→9** admission checks this lifecycle
restriction plus protective monitor/heartbeat and exact stopped
predecessor, without any model start; physical check pending.
Implement a protected isolated H6 trial or explicitly reviewed
managed-service transition before 1st benchmark; **do not bypass
with docker run**.

## 2026-10-14 PHYSICAL DGX Hybrid Phase-0: STATIC PASS / RECLAIM BLOCKED

Operator executed exact source `8ca529ba62067cae10e7ccdfd457e890967a1133`
on the physical DGX. Host idle and pinned Hybrid H3→H6 runtime-only
manifest validation PASS. Available disk **298422198272 B**.
Allocated per directory: base **183535857664 B**, H3 **77543333888 B**,
H4 **68014092288 B**, H5 **44912640 B**, H6 **35475456 B**.
H3/H4/H5/H6 symlinks = 13/76/91/139; all five trees report zero
regular files with >1 hard link. **H7/H20 registered profiles alias H6;
16 exited Hybrid Docker experiments bind-mount H3/H4/H5/H6**
(5 at repo-root, 11 historical `/home/inlc/models` paths).
`PASS_STATIC_INVENTORY_ONLY` is not a deletion permit, runtime READY or
measured benchmark. First H6 benchmark NOT_MEASURED; full deletion
BLOCKED_KNOWN_REFERENCES. No asset or service removed.
Source-only Wizard **Models 3→8** read-only external dependency audit
added; physical execution of new audit NOT_RUN.
See [HYBRID-BENCH-REBUILD-CYCLE.md](HYBRID-BENCH-REBUILD-CYCLE.md).

## 2026-10-14 — SOURCE ONLY: Hybrid Phase-0 Wizard entry

Added Models **3→7** and `scripts/wizard/hybrid-phase0-readonly.sh`:
strict read-only managed idle, H6 runtime validation, metadata SHA256,
disk/link counts, Docker IDs and bind mounts. `PASS_STATIC_INVENTORY_ONLY`
is **not** live-start or retirement authorization. Physical Phase-0 at
this source revision: **NOT_RUN**. Full H7/H20/release reference closure
remains NOT_QUALIFIED. New host-free regression tests cover missing-root
rejection, non-mutation source contract and Wizard navigation. Also fixed
the mazinb Docker retirement Wizard's misplaced `else` to prevent a
misleading failure warning after successful cleanup.

## 2026-10-14 — NEXT: Hybrid H6 two-cycle benchmark / complete reclaim / rebuild

Physical DGX mazinb reclaim and full managed host idle PASS are complete.
The user requested **H6 benchmark → delete → verify absent → reinstall
from source → repeat benchmark → delete again**, preserving research
evidence and all unrelated Docker/shared assets.

**Canonical runbook:** [HYBRID-BENCH-REBUILD-CYCLE.md](HYBRID-BENCH-REBUILD-CYCLE.md).
It defines the first H6 reused-stage measurement, strict measured
JSON/report/SHA and off-host backup, full H6→H5→H4→H3 generated-stage
reclaim, independent absence/link/dependency/Docker/systemd checks,
forced pinned mazinb source reacquisition for true reconstruction when H3
is gone, full H3→H6 rebuild and matched benchmark, and final safe
reclaim/host idle. H7/H20, old experimental containers, OrcaRouter base
and images are **never broad-purged**.

**BLOCKERS before live/destructive steps:** Hybrid `NOT_MEASURED`;
past RM instability, modular Wizard live profile switch only preview;
no implemented full-chain dependency-gated Hybrid removal; physically
not qualified on clean new DGX. Current first action is ONLY Phase-0
read-only script in the runbook; actual hybrid launch/reclaim/rebuild
remain NOT_RUN. Do not use generic model `retire` or
`uninstall.sh --purge-all` as shortcuts.

## 2026-10-14 20:43 KST — PHYSICAL DGX MANAGED HOST IDLE: PASS (final)

**Evidence type: operator DGX terminal, not CI simulation.** The user fast-forwarded the
physical DGX source from `909b03f` to verified branch commit
`2a2c2220bbb70db6007934bd678bddd704c0f643`:
`SOURCE_UPDATE=PASS`. The standalone read-only shutdown preview
`bash install.sh --lang ko --manage-settings --shutdown-access --dry-run`
reached normalized **6/6 plan** with current `orcarouter` model profile,
`API access: local only: 127.0.0.1:8888`, service disabled (`--no-service`),
`--no-start`, and `DRY-RUN 완료` with no host resource mutation.

The operator then invoked `./wizard.sh` → **Runtime 4 → post-benchmark shutdown 6**,
explicitly approved the separate default-NO plan/commit questions, and reached
`Settings transaction prepared (start=0)`, systemd
`qwen38-flash-next.service` boot target link removed,
`Managed Qwen API access endpoints removed`,
`Managed Qwen runtime service removed`,
`Settings resources applied and verified with boot enable deferred until commit`,
`Settings transaction committed`, and transaction state applied/verified.
The managed install manifest remains `PHASE=complete`, `MODEL_PROFILE=orcarouter`,
but is now configured `API_ACCESS_MODE=local`, `SERVICE_ENABLED=0`.
**The profile shown in the manifest is configured identity, not evidence
of a running model.**

**Two independent physical host-idle checks passed**: once automatically after
Wizard shutdown and once directly after exiting Wizard using
`python3 -B scripts/diagnostics/verify-managed-idle.py`. Both output:

```text
MANAGED_IDLE_MODEL_PROFILE=orcarouter
MANAGED_IDLE_API_ACCESS_MODE=local
MANAGED_IDLE_SERVICE_ENABLED=0
MANAGED_IDLE_UNIT=qwen38-flash-next.service load=not-found active=inactive boot=
MANAGED_IDLE_UNIT=qwen38-openwebui-proxy.socket load=not-found active=inactive boot=
MANAGED_IDLE_UNIT=qwen38-openwebui-proxy.service load=not-found active=inactive boot=
MANAGED_IDLE_SYSTEMD=NO_RUNNING_OR_BOOT_ENABLED_UNITS
MANAGED_IDLE_MANAGED_PORTS=NO_LISTENERS
MANAGED_IDLE_DOCKER=NO_RUNNING_QWEN38_CONTAINERS
MANAGED_IDLE_AUDIT=PASS_NO_MANAGED_API_LISTENER_OR_BOOT_START
MANAGED_IDLE_AUDIT_HOST_MUTATION=NONE
```

**Scope of PASS:** the project-managed runtime and OpenWebUI systemd units,
boot-enable flags, configured backend/API/experiment port set, and running
`qwen38-*` Docker containers. This is not proof that every non-project
Docker or unrelated host service is stopped, nor proof of a physical reboot.
ma-zinb checkpoint (~173.65 GiB reclaimed), exact five trial containers
(~1.30 GiB reclaimed), and complete mazinb evidence archive were verified
in earlier physical stages. H3–H6, OrcaRouter model checkpoint, Docker images,
historic Docker objects not selected for reclaim, releases, benchmark payloads,
journals, and archives remain in place.

**Next workflow consequence:** newly installed or selected model must explicitly
restore the desired `API_ACCESS_MODE` and `SERVICE_ENABLED` through the
managed Wizard settings editor (Runtime **4 → 4**), only when wanted.
Do not manually toggle raw systemd units without updating managed state.
The older subsections below record historic intermediate states
(active proxy / unverified idle) and are **superseded by this physical PASS**.

## 2026-10-14: final model-benchmark cleanup must also close shared API/boot exposure

Owner's DGX after mazinb source+Docker retirement: `qwen38-flash-next.service`
is **installed=yes, enabled=yes, active=no**; the **shared** OpenWebUI
socket/service remain **installed/active** and listen on
`172.17.0.1:8000` and `10.221.50.65:8000`. Port 8888 has no
listener; dedicated mazinb M1 18889 has no listener. The old
`verify-mazinb-retirement.py` correctly passes its narrower
"mazinb-specific artifacts absent" contract, but **DOES NOT attest that
the overall managed API host is idle or reboot-safe**.

**Correct safety boundary:** Although the configured manifest is still
`MODEL_PROFILE=orcarouter`, no project model is currently being served.
Preserving a shared proxy install does not mean the proxy needs to
remain active. Worse, enabled runtime service can start on reboot.
Do not conflate preserved files/ownership with active network listeners,
and do not blindly `systemctl disable` without reconciling
`install.env`: the settings transaction verifies enabled/service
consistency.

**New Wizard flow:** Runtime/API/Ports/Service **4 → 6**,
"Post-benchmark API & boot shutdown". This delegates to the existing
`install.sh --manage-settings --shutdown-access` with an exact
completed-install manifest and a separate default-NO entry confirmation,
default-NO apply consent, final normalized plan review and
`START=0` (never starts the 171G vLLM model). It reuses
`settings-transition.sh` and its rollback semantics to set
`API_ACCESS_MODE=local`, `SERVICE_ENABLED=0` and release
installer-owned `qwen38-openwebui-proxy.socket/service` and
`qwen38-flash-next.service` managed systemd units. It preserves
model checkpoints, Docker containers, images, immutable releases,
benchmarks and private archived evidence. New CLI selector cannot be
used for fresh install, without `--manage-settings`, with `--yes`
or mixed with model/setting override flags.

Read-only preview:
`bash install.sh --lang ko --manage-settings --shutdown-access --dry-run`.
New Wizard **4 → 7** or
`python3 -B scripts/diagnostics/verify-managed-idle.py` verifies
completed manifest's local/no-boot policy, all three shared unit
ActiveState/UnitFileState, managed backend/proxy/old trial ports and
all running `qwen38-*` Docker containers, without modification.
It prints `MANAGED_IDLE_AUDIT=PASS_NO_MANAGED_API_LISTENER_OR_BOOT_START`
only when ALL layers are quiescent; missing/failed inspections block.

**Physical host shutdown: NOT_RUN.** The available real DGX evidence
only establishes active proxy and auto-boot while the user is idle.
Do not claim full teardown or report output of the new audit until the
operator syncs an exact passing CI SHA, previews the plan, explicitly
approves shutdown and obtains physical audit PASS. On subsequent
installs/benchmarks, the operator must deliberately re-enable service
and API access via the existing Wizard settings transaction.

## 2026-10-14 Wizard installed API / LAN port configuration restored (source)

**User finding:** prior installer supported setting Docker-app/LAN ports, but
modular `wizard.sh` hid those settings for already completed installations.
Verified code: fresh `install.sh` stage 5/6 still prompts for
`API_ACCESS_MODE=local|docker|lan`, `API_DOCKER_PORT`,
`API_LAN_ADDRESS`, `API_LAN_PORT`. Completed `install.sh` already
had a transactional **Edit runtime / API / service settings** path.
However the modular Wizard's top-level "Install/resume" blocks a
`PHASE=complete` install while its runtime menu initially exposed
only status/doctor/summary. This was a missing navigation route,
not a removed port capability.

**Source fix:** `wizard.sh` → **4 Runtime/Service → 4 API access /
Docker & LAN ports** now delegates directly to
`./install.sh --lang ko --manage-settings` (with the selected UI language).
The new `--manage-settings` option requires an existing strictly
parsed `PHASE=complete` manifest; blocks switches, forced `--yes`,
CLI setting overrides and fresh/resume mode. It directly opens the
existing installed-settings editor with current values, separate
**default-NO apply** consent, normalized plan and equivalent CLI,
and a last "Continue?" review. Only an accepted live edit delegates
to the existing rollback-capable `settings-transition.sh`; it does
not duplicate proxy/service mutation code. Direct preview supported:
`./install.sh --manage-settings --lang ko --dry-run`. Runtime menu
**5** shows `./scripts/manage-proxy.sh status` (read-only).
Run disposable-HOME CI and real DGX source/host preview before
claiming physical qualification.

**Physical host 2026-10-14 19:38 KST (older checkout `446de3a93494...`):**
the user's read-only mazinb post-retirement audit PASSED. The
shared `qwen38-flash-next.service` is loaded but inactive; the shared
OpenWebUI socket and proxy service are loaded/active. The listener
inventory shows `172.17.0.1:8000` for Docker apps,
`10.221.50.65:8000` for the LAN, neither on dedicated 8001,
and no active backend 8888 (because runtime is stopped).
Dedicated mazinb port 18889 and service, user unit and
worker processes were absent. The proxy is still active and is a
shared OrcaRouter component; do not delete it as mazinb debris.
This output documents actual current listener facts, not a test
that a future port-setting transaction has been applied.

> **2026-10-14 PHYSICAL MAZINB CHECKPOINT + FIVE DOCKER REMOVAL PASS; SERVICES/PROXY AUDIT PENDING.**
> Checkpoint recovered 186449989632 B (~173.65 GiB); Docker five-container
> archive PASS_10_FILES then `REMOVED_FIVE_VERIFIED`, 1397395456 B (~1.30 GiB)
> additionally recovered, all other Docker IDs unchanged. Known shared
> `qwen38-flash-next.service`, `qwen38-openwebui-proxy.socket/service`,
> and shared vLLM image MUST NOT be removed simply for mazinb.
> New Wizard Model 3→6 calls read-only `scripts/verify-mazinb-retirement.py`
> to audit system/user units, processes, M1 port 18889, shared proxy/runtime,
> benchmark SHA, retired Docker tombstone and 10 archived files.
> **ACTUAL DGX FULL SERVICE/PROXY AUDIT: NOT_RUN**. Exact details in
> [Benchmark before reclaim](BENCHMARK-BEFORE-RECLAIM.md).

> **2026-10-14 PHYSICAL MAZINB SOURCE RECLAIM PASS / FIVE DOCKER REMNANTS PENDING:**
> Physical Wizard 3→4 removed mazinb checkpoint and recovered
> `186449989632` bytes of disk availability. Five stopped mazinb
> Docker containers remain **by earlier explicit source-only scope**.
> New Wizard Models 3→5 archives their full logs/sanitized metadata
> before removing only those five exact stopped IDs. Shared Docker
> image/volumes, Hybrid, releases and M1 journal preserved.
> **New five-container cleanup PHYSICAL RUN: NOT_RUN**. CI is synthetic.
> See [physical run and scoped cleanup](BENCHMARK-BEFORE-RECLAIM.md).

> **2026-10-14 MAZINB CHECKPOINT RECLAIM PENDING PHYSICAL GATE:**
> v0.29 M1 actual benchmark is MEASURED; original/archived evidence was SHA-verified.
> New Wizard Model 3→4 and `manage-models.sh reclaim-mazinb --dry-run` provide
> a source-only, precise mazinb checkpoint removal with default-NO consent,
> exact phrase, archive/Hybrid/Docker/M1 journal checks and shared locks.
> All Docker objects, shared image, Hybrid H3-H6, logs and benchmark results
> are preserved. Stopped mazinb trial objects may no longer restart after
> model data removal. **REAL DGX REMOVAL AND BYTES RECLAIMED: NOT_RUN.**
> First verify new source SHA/CI, perform physical dry-run, and only apply
> if every gate passes. [Exact scope](BENCHMARK-BEFORE-RECLAIM.md).

> **2026-10-14 FRESH HYBRID H6 INSTALL ACCEPTANCE — SOURCE PATH PRESENT, E2E PENDING:**
> Operator requires one Wizard selection on a new DGX Spark to prepare
> the OrcaRouter + mazinb inputs, vLLM image and H3→H4→H5→H6 chain,
> then enter the managed runtime path automatically. Existing `install.sh`
> already contains this conditional flow; a disposable-HOME dry-run/CLI
> replay and source-contract regression were added. These are host-free
> tests, not proof of clean-host downloads, builds, inference or RM safety.
> Physical DGX installation/start requires separate approval and evidence.
> [Fresh-host Hybrid E2E acceptance gate](HYBRID-FRESH-INSTALL-ACCEPTANCE.md).
> OrcaRouter A/B benchmark is deferred; current priority remains
> actual other-model measurement → verified archive → targeted reclaim.

> **2026-10-14 PRIORITY: REAL MODEL BENCHMARK → ARCHIVE → TARGETED SPACE RECOVERY**
> User explicitly clarified the goal is to test models, preserve actual
> llama-benchy results, then recover memory/disk by selective removal;
> Wizard should make this lifecycle easier. Further pure P1f/P1g
> Supervisor simulation is DEFERRED as non-critical.
> Physical DGX at source `1594f30`: P1e in-memory journal simulation
> PASS and all **11/11** P1e standalone tests PASS; neither is a
> live Supervisor qualification. Sole canonical worktree clean.
> IMPORTANT: The former broad storage prune could erase stopped
> experiment containers and older benchmark files. Current source
> disables BOTH default deletion paths; they are preserved until
> exact-ID archive review, independent checksum verification and
> explicit per-target approval. Wizard 6→4 adds read-only archive SHA checks.
> No checkpoint/Docker cleanup is authorized; inspect actual up-to-date
> storage inventory and protect managed predecessor/dependency graph.
> [Benchmark/reclaim operating contract](BENCHMARK-BEFORE-RECLAIM.md).

> **2026-10-14 M1 P1e WRITE-AHEAD JOURNAL — PURE SYNTHETIC SOURCE ONLY:**
> Source commit `f715ee9c8e1877ea9da53ff3388d9caaf64cbc26`
> adds `m1-supervisor-journal-protocol.py`, adversarial unit tests
> and Wizard Benchmark **16** in-memory journal/crash simulation.
> Prepared STOP_INTENT is not 'durable' without an injected ack;
> acknowledged intent cannot be auto-replayed after interruption;
> independently proven candidate exit and stopped monitor are needed
> before an EXIT_PROVEN record, with unknown shutdown cause preserved.
> No actual file I/O, real fsync, authenticated IPC, concurrent durable
> CAS, replay ledger, user service, Docker or GPU action is implemented.
> All 'durable' snapshots/acks and watchdog evidence are simulated.
> **P1e has not yet been run on the physical DGX.** P1d actual
> in-memory simulation PASS is archived separately. Physical
> `Linger=no` remains confirmed and no change approved.
> [P1e design and limits](MAZINB-M1-WIZARD.md).

> **2026-10-14 ACTUAL DGX P1d COMMAND SIMULATION: PASS_IN_MEMORY**
> At exact source `08f69beda51a7ee8d610774e260aae21bed911b0`
> the operator ran the pure `m1-supervisor-command-protocol.py`
> plan/simulate on the physical DGX (one canonical Git worktree).
> P1d printed `PASS_IN_MEMORY`, and blocked default-NO STOP,
> `Linger=no`, nonce replay and expired requests. Real STOP was
> `NOT_PERFORMED`; real IPC, worker, OS peer attestation, Docker
> action, user service and linger mutation all remain absent.
> Source Push/PR CI for `08f69be` both SUCCESS, not a live
> background supervisor qualification. `Linger=no` stays confirmed.
> [Exact physical P1d evidence](MAZINB-M1-P1D-PHYSICAL-SYNTHETIC-20261014.md).

> **2026-10-14 M1 SUPERVISOR P1d — PURE SYNTHETIC CONTROL GATES ONLY:**
> Commit `5777ee4d2b63466b0db6a750a3a3f71e8bfb84df`
> adds `m1-supervisor-command-protocol.py`, adversarial unit tests
> and Wizard Benchmark **15** (memory-only command simulation).
> The mocked request includes owner token, exact Docker IDs, PID/start
> ticks, systemd invocation ID, UID, a bounded TTL and nonce history.
> Synthetic STOP requires explicit consent, linger gate, verified
> worker/watchdog and free benchmark lease. Default-NO, `Linger=no`,
> expired requests, nonce replay and owner drift reject admission.
> All peer UID, supervisor, linger, heartbeat and approval values are
> INJECTED INPUTS; no real kernel identity/authentication, IPC,
> persistent nonce store, background worker, Docker or systemd action.
> No physical DGX P1d execution yet; physical P1c IN_MEMORY_PASS and
> actual DGX `Linger=no` remain recorded above/below.
> Production real background lifecycle and logout persistence are
> NOT_IMPLEMENTED / NOT_QUALIFIED. New CI results need separate check.
> [Wizard P1d safety description](MAZINB-M1-WIZARD.md).

> **2026-10-14 ACTUAL DGX P1c PURE SYNTHETIC PROTOCOL: PASS_IN_MEMORY**
> At exact source `835be6f411abbb3e901992566d4459881853acf7`,
> the operator synced the sole canonical worktree and ran P1c
> `plan` and `simulate` physically on DGX.
> Output: `M1_P1C_SIMULATION=PASS_IN_MEMORY`,
> `SIM_STOP=PASS_EXPLICIT_ACK`, `SIM_RECOVERY=PASS_UNDETERMINED`,
> `SIM_UNAUTHORIZED_STOP=BLOCKED`, `SIM_PID_REUSE=BLOCKED`.
> The script also reported `WORKER_IMPLEMENTED=NO`,
> `HOST_INSPECTION=NONE`, `DOCKER_ACTION=NONE`,
> `USER_SERVICE_MUTATION=NONE`, `LINGER_CHANGE=NONE`.
> This proves only execution of an in-memory simulation on DGX.
> It does not qualify a real Worker, watchdog, Docker stop, host
> stability or logout persistence. `Linger=no` remains confirmed
> and no policy change has been approved.
> [Exact operator evidence](MAZINB-M1-P1C-PHYSICAL-SYNTHETIC-20261014.md).
> Source `835be6f` Push and PR CIs both SUCCESS.

> **2026-10-14 M1 BACKGROUND SUPERVISOR P1c — PURE SYNTHETIC SOURCE ONLY:**
> Commit `80501d2277945390ffc4c97ef79a10460ebdc073` adds
> `scripts/runtime/m1-supervisor-protocol.py` with in-memory
> exact-ID/session-token/PID-start-ticks/systemd-invocation binding,
> watchdog freshness, benchmark-lease and explicit STOP-approval gates.
> New Wizard Benchmark **14** runs `simulate` only; no host/Docker
> subprocesses, services, journals, GPU, linger or model actions.
> Synthetic STOP and supervisor-loss reconciliation are modeled, not
> performed. Prior physical DGX `Linger=no` and reserved unit
> `NOT_FOUND` remain the only actual background host observations.
> No real Background Worker, persistent journal/IPC, user unit or
> start/stop implementation has been built or qualified. SOURCE_CI
> result must be checked separately; no actual DGX P1c test yet.
> [Protocol guide](MAZINB-M1-WIZARD.md). Older source-only plans
> below must not be construed as real worker readiness.

> **2026-10-14 ACTUAL DGX P1b READ-ONLY USER UNIT INVENTORY: PASS_NOT_FOUND**
> At exact source `e542f99fa711a61a1713fa0c10341f47934e7866`,
> the owner fetched and fast-forwarded the single canonical checkout and
> ran `m1-background-probe.py unit-status` without mutation.
> The reserved `qwen38-mazinb-m1-background.service` returned
> `M1_BG_UNIT_STATUS=NOT_FOUND`, `ABSENT_RESERVED_UNIT_ONLY`.
> `M1_BG_WORKER_IMPLEMENTED=NO`, `M1_BG_WORKER_IDENTITY_VERIFIED=NO`,
> `M1_BG_DOCKER_ACTION=NONE`, `M1_BG_USER_SERVICE_MUTATION=NONE`.
> This proves only that specific reserved user unit was not found;
> no background worker/lifetime is qualified and no other process or
> unit inventory can be inferred. Earlier `Linger=no` remains confirmed.
> NO Docker/service/linger changes and no GPU startup were performed.
> [Exact physical evidence](MAZINB-M1-P1B-PHYSICAL-UNIT-STATUS-20261014.md); PR #261 Draft/unmerged.

> **2026-10-14 ACTUAL DGX USER SYSTEMD LINGER — CONFIRMED DISABLED:**
> Source `56b51aa94a5db5b32ce0d8adc2397760bb026805` and original canonical checkout verified.
> Physical `loginctl show-user ... --property=Linger` printed `Linger=no`.
> P1a printed `M1_BG_USER_LINGER=DISABLED`,
> `M1_BG_USER_MANAGER=AVAILABLE` and
> `M1_BG_BLOCK_REASON=USER_LINGER_DISABLED`; host probe BLOCKED.
> No Docker, user-service, linger, GPU or managed-release change.
> Prior reason `NOT_ENABLED_OR_UNKNOWN` is superseded by exact read-only
> evidence. Owner approval to modify persistent linger is **NOT GIVEN**.
> P1b source adds read-only reserved unit inventory only; no worker
> launch, stop, PID or exact-ID ownership qualification.
> See [physical evidence and P1b design](MAZINB-M1-WIZARD.md).

> **2026-10-14 ACTUAL DGX BACKGROUND P1a HOST PROBE: SAFELY BLOCKED**
> At source `9df9d0823762b16a1316847b7804e178f8b1a494` on
> the original Git checkout, operator executed read-only plan/probe.
> `M1_BG_HOST_PROBE=BLOCKED` with
> `M1_BG_BLOCK_REASON=USER_LINGER_NOT_ENABLED_OR_UNKNOWN`.
> No Docker/systemd user-service/linger mutation performed; background
> worker and start/stop remain NOT_IMPLEMENTED. This old combined
> reason does not by itself prove `Linger=no` rather than query failure.
> New source distinguishes DISABLED / UNKNOWN; read-only DGX recheck
> is necessary. Operator must explicitly authorize any persistent
> `loginctl enable-linger` change; do not silently change host policy.
> [Physical P1a evidence and safe next steps](MAZINB-M1-WIZARD.md).

> **2026-10-14 P1a BACKGROUND SUPERVISOR HOST PROBE — SOURCE ONLY:**
> Source commit `38560326631d612c45ee0d1cde19dd9da927e62d`
> adds Wizard Benchmark **11 plan** and **12 host probe**,
> backed by `scripts/runtime/m1-background-probe.py` and synthetic tests.
> User bus, loginctl linger, systemctl user manager, tool availability
> and XDG runtime-dir ownership/mode are inspected **read-only**.
> This does NOT enable lingering, install/start/stop systemd units,
> create Docker containers, launch a background worker or start models.
> `PASS_CAPABILITY_ONLY` is not detached lifecycle/host-stability proof.
> Background start/stop and independently owned PID/unit/session token
> remain **NOT_IMPLEMENTED / NOT_QUALIFIED**.
> Existing Wizard 5→9 Foreground and 5→10 exact-ID Journal recovery
> retain their prior implementation and safety gates.
> [Detailed safety design](MAZINB-M1-WIZARD.md) and
> [architecture](WIZARD-ARCHITECTURE.md).
> Older proposed Background notes below are historical snapshots.

> **2026-10-14 WORKSPACE / BENCHMARK EVIDENCE UPDATE:**
> All three remaining detached experiment worktrees were safely removed;
> `git worktree list` returned only the original canonical checkout
> on `feature/wizard-modular-phase1-20261014` at `2f1cc08`.
> The independent 36-KiB physical M1 benchmark output directory is
> preserved. DGX operator checked all three archived data SHA-256 values:
> `smoke.json` PASS, `mazinb.json` PASS, `mazinb-report.md` PASS.
> Local `SHA256SUMS` lists absolute paths (436 bytes), archival manifest
> lists relative paths (238 bytes); measured payload digests match.
> [Operator evidence](../scripts/benchmark/evidence/dgx-mazinb-m1-journal-reconcile-physical-20261014.md).
> Foreground-only M1 remains the qualified startup architecture;
> Background Supervisor is **DESIGN ONLY** and requires separate safety
> tests and DGX approval. No GPU/Docker changes in workspace cleanup.

> **2026-10-14 KST M1 PHYSICAL JOURNAL RECONCILIATION: PASS_RECORDED_STOPPED**
> Physical DGX operator ran Wizard Benchmark 5→10 on source
> `4776a6118decabc7cb511e4e60e7b157d3a57bec` and confirmed `y`.
> Reconciler printed `M1_RECONCILE=RECORDED_STOPPED`.
> Subsequent separate read-only status printed `phase=stopped`,
> `Running=False`, `ExitCode=0`, `M1_DOCKER_REMOVED=NO`.
> Two original JSON backup files were listed (0600; 1149 bytes each).
> Shutdown cause remains `UNDETERMINED`, HOST_STABILITY=INCONCLUSIVE.
> No Docker start/stop/delete is reported by the reconcile workflow.
> [Permanent operator evidence](../scripts/benchmark/evidence/dgx-mazinb-m1-journal-reconcile-physical-20261014.md).
> Source recovery is now **physically executed**; the older
> `RECOVERY_REQUIRED`/`NOT_RUN` paragraph below is the previous snapshot.
> Retain original canonical working directory:
> `~/Workspace/llm/qwen3.8-flash-next-dgx-spark`.
> Only audited, Git-registered clean temporary Worktrees may be removed;
> all model/Docker/swap/state/evidence assets remain protected.

> **2026-10-14 M1 SECOND ACTUAL GPU START:** DGX detached source SHA
> `67f45d506cd773b2c5066659ddcb946970cc5ff1` verified clean.
> Owner approved Wizard Benchmark 5 -> 9 and obtained
> `M1_CANDIDATE_STARTED_UNQUALIFIED=qwen38-mazinb-m1-20261014003622-035e91fd`.
> New M1-only swap-pressure availability gate is being physically
> exercised. No second-run exact Docker ID/READY/soak/smoke/strict
> RM outcome/llama-benchy metrics supplied yet. Preserve Terminal A.
> Source SHA mistakenly entered for old Docker ID at initial 5 -> 8
> was rejected (safe no-start); historical evidence submenu 9 was
> rejected (safe no-start). Eventually correct full old Docker ID
> acknowledged during live start. Historical A/B/managed preserved.
> Benchmark only after `M1_READY_FOR_BENCH` in separate Terminal B.

> **2026-10-14 M1 PHYSICAL FAILURE ROOT CAUSE CONFIRMED:** Actual new
> model `qwen38-mazinb-m1-20261013235416-edd777eb` stopped via
> `memory-protection`, exit 1, OOMKilled=false; reached 26/95 shards.
> Five consecutive samples at KST 08:59:10–18: non-CMA free
> 1192,1233,2045,1436,1496 MiB; non-CMA available 37.6–38.7 GiB;
> swap growth 279–411 MiB. Low free <2 GiB AND swap growth >256 MiB
> triggered despite high available memory and ~143 GiB swap-free.
> Filtered kernel RM/OOM result EMPTY (not exhaustive).
> Subsequent SOURCE-ONLY change: pinned M1-only swap-growth protection
> additionally needs available <12 GiB; primary 10 GiB available
> and 8 GiB swapfree guards unchanged, RM inspection still strict.
> Fix failure phase recorded as failed_stopped with failure cause;
> previous `phase=stopped` historical trial remains immutable.
> NEXT: source CI + exact DGX SHA, guard verification and
> explicit owner-supervised fresh M1/llama-benchy only if safe.
> No fresh runtime or performance numbers yet.

> **2026-10-14 ACTUAL DGX first M1 live started but MEMORY-PROTECTION STOPPED:**
> Exact source SHA `72982e0e1bb53cdf8bb66a641356eb4a7e743320`,
> operator approved Wizard 5 -> 9 and launched
> `qwen38-mazinb-m1-20261013235416-edd777eb`,
> exact Docker ID `1ebe723a279171794d7753cdbc3726e8c0db052c7cac02ec3060b8fc23c2700d`.
> Output `M1_STOPPED_EXACT_ID=...`, `M1_DOCKER_REMOVED=NO`,
> `M1_BLOCKED=candidate triggered memory-protection stop`.
> No READY/soak/inference/llama-benchy. Protective stop is confirmed;
> actual non-CMA/swap samples, OOMKilled and RM journal not yet supplied.
> HOLD new launch; request read-only candidate Docker/monitor/kernel
> evidence. Preserve historical A/B, managed Docker, M1 candidate and swap.
> See `scripts/benchmark/evidence/dgx-mazinb-m1-physical-readonly-preflight-20261014.md`.

> **2026-10-14 DGX M1 repeat READ_ONLY PASS:** A second physical
> Wizard 5 -> 8 transcript returned `M1_PREFLIGHT=PASS_READ_ONLY` and
> `M1_CANDIDATE_START=NOT_PERFORMED`, matching the previously recorded
> old Docker ID `f6bfee5a...ff6acd24`, immutable release `ff67bab3...`
> and image SHA256 `dba5d8af...`. The user then entered 5 -> 5 -> 0,
> which *cancelled* historical evidence selection without mutation.
> The second transcript did not print its git HEAD; do not assert it
> cryptographically establishes SHA 72982e0 until `git rev-parse HEAD`
> is checked. No new M1 live container, READY, smoke or bench has run.
> See `scripts/benchmark/evidence/dgx-mazinb-m1-physical-readonly-preflight-20261014.md`.

> **2026-10-14 M1 ACTUAL DGX READ-ONLY PREFLIGHT PASS:** Source
> `2dfa74dacedfe50fe1c28ca309939ed9d61b8123` in isolated
> worktree; Wizard Benchmark 6 plan (16 GiB / port 18889),
> 7 `M1_SESSION=ABSENT`, 8 returned `M1_PREFLIGHT=PASS_READ_ONLY`.
> Old Docker full ID
> `f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`,
> release `ff67bab3c94d6992f61b9535836df97f03b9c022`,
> M1 image ID `sha256:dba5d8af279fb85901e6d8911f1a59ecc45b669b0948ab8d01d7c7d1c5815734`.
> Candidate start NOT_PERFORMED. Subsequent source change isolates each
> new M1 HOME/vLLM/FlashInfer cache; needs updated SHA/CI physical check.
> New M1 GPU start, READY, RM stability and llama-benchy NOT_RUN.
> See `scripts/benchmark/evidence/dgx-mazinb-m1-physical-readonly-preflight-20261014.md`.

> **2026-10-14 mazinb M1 source implementation:** Added an isolated
> unique-name create-only `scripts/runtime/mazinb-m1.py` supervisor;
> Wizard Benchmark 6/7/8/9 = plan/status/read-only physical preflight/
> explicit opt-in new live start. A strict pinned-label watchdog is
> armed BEFORE start, post-ready 180s soak and strict RM monitoring are
> source-implemented; the M1 shared lifecycle + exclusive benchmark
> lock contract is source-implemented in `scripts/wizard/m1-benchmark-lock.sh`. **M1 ACTUAL DGX PREFLIGHT / LIVE READY /
> LLAMA-BENCHY remain NOT_RUN.** Old A/B and OrcaRouter protected.
> Controlled B (16 GiB) historical success does not erase the
> archived *managed* 16 GiB `NV_ERR_NO_MEMORY` HOST-STABILITY FAIL.
> See `docs/MAZINB-M1-WIZARD.md`.

> **2026-10-14 mazinb ACTUAL_DGX historical A/B evidence review:**
> The owner's Wizard 5 -> 5 -> 3 output shows A/24 GiB
> `STOP_REASON=memory-protection` after five low-memory samples
> (Docker exit 1, OOMKilled=false) and B/16 GiB healthy API
> `/health` + `/v1/models` HTTP 200 at 20:57:42 KST, about
> 180 s before orderly exit 0, with no displayed protect stop or
> filtered RM/OOM events. B exact served ID JSON and historical
> runner final RESULT line are not included in the pasted output;
> **no new model run, no llama-benchy, no cleanup**. Both old case
> objects must be preserved and a new isolated M1 candidate needs
> a unique name. See
> [physical A/B evidence review](../scripts/benchmark/evidence/dgx-mazinb-kv-ab-wizard-readonly-20261014.md).

> **2026-10-14 ACTUAL DGX mazinb status:** Wizard verified that both
> old KV trials still exist and are exited: A/24GiB exit 1, B/16GiB
> exit 0; both OOMKilled=false. These are historical observations,
> NOT new READY or bench results. Evidence submenu now supports
> 1=A, 2=B, 3=both; fresh-B admission explains old B name collision
> before asking for predecessor ID. No Docker/state cleanup performed.
> See `docs/MAZINB-EXECUTION-GATE.md`.

> **2026-10-14 DGX mazinb M0 follow-up:** Real read-only admission
> refused the existing historical `qwen38-mazinb-kv-a` container. It is
> NOT proven running or safe to remove. Wizard Benchmark now exposes
> read-only status/evidence A/B and an explicit reviewed-A exact-ID
> acknowledgement before allowing independent B *admission*.
> No cleanup, model launch, benchmark, or protected-object mutation.
> See `docs/MAZINB-EXECUTION-GATE.md`.

> **2026-10-14 mazinb timing/approval boundary:** Next DGX candidate is
> mazinb. The first additional gate is read-only exact Docker-ID admission
> (`scripts/wizard/mazinb-admission.sh`); M1 protected stay-READY lifecycle
> and real llama-benchy remain **NOT IMPLEMENTED / NOT MEASURED**.
> See [MAZINB-EXECUTION-GATE.md](MAZINB-EXECUTION-GATE.md).

> **2026-10-14 Wizard migration note (Phase 1, staged):** A separate
> modular `./wizard.sh` operator entry now exposes read-only inventory,
> diagnostics, preflight and safe preview paths. The installer-only refactor,
> live profile switch, protected benchmark controller and storage deletion
> are **NOT IMPLEMENTED** in this stage. See
> [WIZARD-ARCHITECTURE.md](WIZARD-ARCHITECTURE.md) for exact scope.

# Current project status

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


## ACTUAL DGX OrcaRouter installed-wizard preview PASS; live remains blocked (2026-10-13)

**Physical wizard output** from exact detached source `a61b4569c5a6865dbeb9aa4ba4b21aeea12424e2`: existing installed setup management → select/switch profile → OrcaRouter → 6/6 plan → Continue Y **under `--dry-run`**, `WIZARD_DRY_RUN_RC=0`. The manifest-selected OrcaRouter revision is `c1209bda15a6bbc4c68b585e93d40c0d85f50306`, image **`vllm-skinny-tp1:v1` (NOT the separate `vllm-orcarouter-v029:v1` experiment)**, monitor/protection enabled (available warn 6 GiB, non-CMA free 2/10 GiB gate, SwapFree 8 GiB, five samples, 60s heartbeat), 128 GiB PLE, managed systemd service, Docker/LAN API access. Before/after comparison confirmed identical protected predecessor `Id|State.Status|Image` and `install.env` SHA256. Operator log `/home/inlc/dgx-orcarouter-wizard-20261013-152129.log`. [Real DGX evidence](../scripts/benchmark/evidence/dgx-orcarouter-wizard-actual-dry-run-20261013.md).

This PASS confirms the **wizard preview**, NOT a running API, live M1, host stability, actual Docker mount or benchmark. Full wizard-managed start must protect the old exact stopped Docker predecessor: normal runtime transition `commit` deletes the predecessor. **Next feature:** [safe isolated OrcaRouter trial inside the wizard](DGX-ORCAROUTER-WIZARD-TRIAL-DESIGN.md), dedicated monitor state and exact-ID stop; DESIGN ONLY, no owner-authorized live run. OrcaRouter deletion is held only during this test; later cleanup needs benchmark backup and separate approval. Five reports NOT_MEASURED, PR #259 Draft.


## Latest owner scope correction — OrcaRouter deletion HOLD only during this test (2026-10-13)

**Corrected owner intent:** OrcaRouter remains the **first model** for
wizard-managed activation and llama-benchy. Its checkpoint must be
preserved **for the current OrcaRouter test and performance evidence
collection**, not forever. The earlier claim that OrcaRouter is a
permanent model keeper, and the hard-coded `ORCAROUTER_PROTECTED`
deletion bans, were an overinterpretation and are **withdrawn**.

After this test, OrcaRouter may be considered for future storage
reclamation **only as a separately approved candidate**, after actual
measurement (or explicitly documented unmeasured exception),
raw JSON/Markdown/SHA256 evidence and verified external backup,
other model dependencies, ownership and exact-ID recovery impacts
are reviewed. There is **no deletion authorization now**.
The historical stopped canonical Docker ID and installed immutable
release remain separately protected pending explicit disposition.
Actual model install/switch/uninstall must go through the wizard.
Terminal A manages/inspects; Terminal B measures a previously
qualified API; never overlap model lifecycle mutation with benchmarks.
Synthetic benchmark/wizard lock wrapper remains implemented.
[Current two-terminal policy](DGX-TWO-TERMINAL-WIZARD-BENCHMARK.md).

The actual DGX v0.29 OrcaRouter isolated **read-only** preflight at
`5a14d169bbca93604b92e52dc1e548ed75cc5569` returned RC=0,
weights/image ready, managed runtime inactive, experiment absent,
port 8888 free and canonical old Docker ID/image/exit/OOM unchanged.
No live model start or throughput resulted: all five reports
remain NOT_MEASURED; M1 live and host stability NOT_QUALIFIED.

## Wizard-only install/switch/uninstall + two terminals — latest owner requirement (2026-10-13)

The owner requires that model installation, profile switching, and
uninstallation use the **interactive wizard**, never manually via
experimental Docker/runtime scripts. TWO distinct terminals are used:
A=wizard/management/storage inspection and B=bench/reporting; a live
bench cannot overlap A's installation, switching, deletion or pruning.
See [two-terminal workflow and limitations](DGX-TWO-TERMINAL-WIZARD-BENCHMARK.md).
Existing install wizard supports profile selection/switch; uninstall
wizard supports preview and purge, but real uninstallation destroys the
canonical container, and a model switch may commit deletion of the
protected stopped predecessor. **No actual wizard install/switch/uninstall
yet approved**; do not use raw experiment start to bypass this.
Inactive intermediate model removal is not presently a wizard menu,
so treat that as an unmet UI feature rather than using low-level
remove/retire/prune without a separately approved exception.

**Actual DGX M1 read-only preflight PASS**: source
`5a14d169bbca93604b92e52dc1e548ed75cc5569` (same SHA
CI #38350725606 SUCCESS), operator log
`/home/inlc/dgx-m1-experiment-preflight-20261013-143450.log`,
RC 0; OrcaRouter weights and v0.29 image ready, managed inactive,
experiment absent, port 8888 free, exact stopped old Docker
ID/status/image/OOM unchanged before/after.
[Permanent M1 preflight evidence](../scripts/benchmark/evidence/dgx-orcarouter-m1-isolated-preflight-20261013.md).
This was read-only and **not** M1 live or measured performance.
Five benchmark profiles remain NOT_MEASURED. No host cleanup yet.


## Actual DGX S4 all-Hybrid-link closure PASS (2026-10-13) — benchmark next, no deletion

**ACTUAL_DGX** exact clean source `5a14d169bbca93604b92e52dc1e548ed75cc5569` with same-SHA CI [38350725606](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38350725606) SUCCESS: operator log `/home/inlc/dgx-hybrid-link-closure-20261013-142413.log` reports `S4_LINK_CLOSURE=COLLECTED_READ_ONLY`, `ALL_LINK_REFERENCE_GAPS=0`; all 319 H3/H4/H5/H6 symlinks resolved to regular files by the source's known Docker-virtual alias model (13/76/91/139). Static H6 source mount contract PASS; ext4/device 66306, available bytes 112103874560 (~104.404 GiB snapshot). [Permanent S4 evidence](../scripts/benchmark/evidence/dgx-hybrid-all-link-closure-readonly-20261013.md). **S1/S2/S3/S4 physical READ_ONLY checks complete**, not runtime acceptance or reclaim approval. Actual Docker mounts, CoW extents, payload correctness, M1 live, five llama-benchy reports still NOT_VERIFIED/NOT_MEASURED. **No more S-style inventory gates by default**; prioritize protected old-Docker-ID M1 isolation decision, safely monitored model readiness, then actual benchmark evidence before any selective cleanup. Old ID/release/swap/protect unchanged as far as this S4 log establishes; no destructive operation evidenced.


## S4 source-only all-link and H6 mount-contract audit ready (2026-10-13)

Added `inspect-hybrid-link-closure.py`, synthetic link-closure tests and [S4 read-only runbook](DGX-HYBRID-S4-LINK-CLOSURE.md). It reuses S3 exact-SHA and installation fingerprints, checks ALL H3–H6 symlink destinations, and verifies source-only H6 `:ro` bind-mount declarations; collects FS type/free bytes without claiming CoW/reflink extent uniqueness. **S4 ACTUAL_DGX NOT_RUN**; same-HEAD CI SUCCESS and operator output required. S3 actual PASS and benchmark/deletion safety gates remain unchanged.


## Actual DGX S3 link/index reference PASS — not runtime or reclaim clearance (2026-10-13)

Physical operator log `dgx-hybrid-runtime-refs-20261013-141134.log` at exact source `d14915549667e196356b8511526f9bfd4db42cd6`: `S3_REFERENCE_SURVEY=COLLECTED_READ_ONLY`, `REFERENCE_GAPS=0`, no model start or tensor payload read. Six-stage index counts (base/mazinb/H3/H4/H5/H6) show 18/95/66/81/81/81 unique shard names; H6's **81/81 shards use virtual link chains**, so H6 remains dependent on ancestors. All 319 H3-H6 symlinks had known parent alias categories, but only indexed shard references were resolved to files. Same-SHA CI #38349291372 was SUCCESS; physical results are separate. [New actual-DGX S3 evidence](../scripts/benchmark/evidence/dgx-hybrid-runtime-references-readonly-20261013.md). Source review of `scripts/serve.sh` shows H6 + four RO parent mounts; **actual Docker mounts/serving are NOT verified**. Follow-up S4 (all symlink targets, mount contract, filesystem capability) is NOT_RUN; five llama-benchy reports remain NOT_MEASURED, and model/Docker deletion remains blocked.


## Source-only S3 dependency inspection tool (2026-10-13)

Added `scripts/diagnostics/inspect-hybrid-runtime-references.py` and
[read-only S3 runbook](DGX-HYBRID-S3-REFERENCES.md). The tool recognizes only
builder-declared container aliases, reports each stage's link counts and unique
safetensors-index shard resolutions, checks exact clean checkout + installed
manifest/ownership/current pointer fingerprints before/after, and fails closed
for unknown references. It never loads weight tensors or starts/removes a
model. Static/synthetic tests are not actual DGX S3 evidence. **S3=NOT_RUN
on physical host** until the new commit's CI succeeds and the operator
returns the exact log. S2 PASS does not change deletion/benchmark gates.


## Actual DGX S2 block accounting PASS — no reclaim clearance (2026-10-13)

Operator-returned exact-SHA S2 at `14c67135f94b3c507a90c3a0702c83b9f3bfcda7` reported `RECLAIM_BLOCK_ACCOUNTING=COLLECTED_READ_ONLY`. Six model trees account for 515623661568 allocated bytes (480.212 GiB), with **zero multi-linked file entries** in this scope and **319 symlinks** (H3 13/H4 76/H5 91/H6 139). H3+H4 account for 145557426176 allocated bytes (135.561 GiB), **not** certified removable bytes. All six root directories have FS device 66306. Source-built symlinks can point to container-only mount aliases; host dangling resolution is not sufficient to declare breakage. The S2 runner did not enumerate actual target chains, safetensors index shard references or CoW shared extents. [Actual-DGX evidence](../scripts/benchmark/evidence/dgx-hybrid-block-accounting-readonly-20261013.md). Next read-only gate **S3 runtime-alias/index mapping NOT_RUN**; all five llama-benchy reports remain `NOT_MEASURED`; all model/Docker deletes remain blocked; M1/M3/M4/M2/D0 gates unchanged. Exact old Docker ID and installed immutable release remain protected.


This document is the canonical short-form status entry point for the repository.
Dated benchmark/evidence documents preserve what was known at the time of each run;
use this file plus `scripts/benchmark/evidence/README.md` when deciding what is true
**now**.

Last synchronized: 2026-10-07. The version on `main` is authoritative; do not encode a
specific "last documentation PR" or commit SHA here because the synchronization change
itself would make that marker stale as soon as it is merged.

Current-facing repository documentation (`README.md`, `OPERATIONS.md`,
`docs/ARCHITECTURE.md`, `scripts/model/README.md`, and
`scripts/runtime/README.md`) should agree with this status. Dated evidence remains
historical even when it contains then-current words such as `pending`, `next`, or
`current`.

## Actual DGX S1 storage inventory PASS (2026-10-13)

Exact DGX source 513623243c12c204378a0e22bb965ff47542f4f9, 8/8 read-only commands rc0, final RECLAIM_READONLY=COLLECTED. Root filesystem 105G free/88% full. OrcaRouter 171G active, mazinb 174G present, H3 73G and H4 64G intermediates, H5 43M/H6 34M. H6 registry explicitly depends on H5/H4/H3/OrcaRouter: nominal 137G combined H3/H4 directory sizes are NOT certified independently reclaimable and NOT approved for deletion. Docker image table 47.22GB with 0B reclaimable due references/shared layers, but 6.239GB stopped-container writable layers potentially reclaimable after evidence/archive approval. Open WebUI and Portainer are running and excluded. Actual proof: [S1 physical-DGX storage log](../scripts/benchmark/evidence/dgx-storage-pre-reclaim-readonly-20261013.md). Follow-up guarded exact-SHA filesystem block/hardlink audit ready. No benchmark run, deletion, GPU start or cleanup; five reports remain NOT_MEASURED; M1/M3 NOT_QUALIFIED, H38 BLOCKED, M2 NOT_RUN, D0 NOT_GRANTED.

## BENCHMARK BEFORE SELECTIVE RECLAIM — new operator preference (2026-10-13)

Some models/Docker assets may be considered for disk reclamation,
**but first preserve the per-model benchmark result and provenance**.
All five llama-benchy report templates remain NOT_MEASURED and no
real benchmark or deletion has yet been run.
[Read-only inventory / retain-before-delete gate](BENCHMARK-BEFORE-RECLAIM.md)
reuses existing storage/model managers, exact SHA, Docker reclaimable
accounting and dependency protection. The stopped old OrcaRouter
container ID, active checkpoint, swap and immutable releases remain
protected. Current observed disk headroom ~105 GiB is less than the
lychee888 model-card figure ~123.25 GiB before reserve.

## ACTUAL DGX B5 — legacy OrcaRouter read-only PASS (2026-10-13)

The operator returned `B5_READONLY=COLLECTED_READ_ONLY` at
exact source `c2a73179cc2319cac3b7402ac347cdc41572c1df`.
All **15/15 identity/read-only guards passed**: exact prior container
ID `f6bfee5a...`, installed immutable `ff67bab3...`,
Docker EXITED non-OOM, systemd INACTIVE/DEAD, monitor/protect=1,
active /swap-ple.img, no rollback object and unchanged real-host
state/source. MemAvailable ~118.2 GiB, SwapFree ~143.1 GiB,
CmaFree ~67.7 MiB, available disk 105 GiB (88% used).
[Scoped actual operator evidence](../scripts/benchmark/evidence/dgx-b5-legacy-orcarouter-prestart-readonly-20261013.md).
**B5 read-only PASS is NOT M1 startup authorization;** the exact
old Docker ID may be deleted by a managed-success path, and may
be restarted on generic rollback; separate owner decision and
STOP/recovery procedure remain required.
`lychee888` cannot be assumed to fit available disk based on
its published ~123.25 GiB checkpoint size. No model load or
throughput measurement occurred.

## External benchmark reference — llama-benchy model reports planned (2026-10-13)

Pinned external source [eugr/llama-benchy](https://github.com/eugr/llama-benchy)
at `e9be344578cec17745066b220798b80a0d2686d3` (MIT). Five [per-profile
model report placeholders](model-reports/README.md) are explicit
`NOT_MEASURED`; a strict offline JSON-to-Markdown conversion
script supports later traceable measured reports. Benchy sends API
requests and can fetch corpus/tokenizer data: **no automatic
bench install, model start or performance run** on the stopped
DGX. API/model readiness plus bounded strict RM health gate
must precede actual benchmarking.

## B5 legacy OrcaRouter prestart: operator-ready, physical run NOT_YET_OBSERVED (2026-10-13)

New [B5 exact-identity read-only runner and owner handoff](DGX-LEGACY-M1-B5-PRESTART.md)
verify source SHA, installed immutable release, full predecessor Docker
ID, stopped unit, unchanged monitor/protect and PLE swap, and
pre/post state hashes. **No model starts or host edits.** Earlier
A5 and lychee888 L0 actual-DGX results are PASS. B5 actual
operator output is still NOT_RUN; a B5 read-only PASS would
not authorize losing the old Docker ID or passing M1 host
stability.

## ACTUAL DGX A5 wizard previews PASS + lychee888 real L0 index JSON PASS (2026-10-13)

The operator ran the exact `f2674f0a60682a62f6218c7bfbfc5e9e5d24e4b8`
detached-worktree read-only wizard audit. **14/14 checks rc0**,
**60/60 scoped fixture tests**, four profile installer dry-run
plans, both uninstall previews; manifest and ownership file SHA256 and
immutable `current=ff67bab3` unchanged. The saved selected-profile
snapshot still reports stopped/EXITED OrcaRouter with no live
attestation and monitor/protect=1; **no runtime was started**.
The separate actual-network `lychee888` metadata probe resolved
Hub revision `1b3c3cedc14fb3bee4294dea5e3515af74b8268a`:
223,047 index keys / 128 PLE shards / 10 FP8 PLE files /
one global scale / `float8_e4m3fn`, verdict
`INDEX_STRUCTURE_PASS_METADATA_ONLY`. **L0_INDEX_JSON=PASS**
does NOT verify tensor dtype, weights, TP1 support or RM stability.
[Canonical physical-DGX A5+L0 operator evidence](../scripts/benchmark/evidence/dgx-a5-wizard-and-lychee-l0-result-20261013.md).
**M1 live NOT_QUALIFIED, M2 NOT_RUN, M3 live NOT_QUALIFIED,
M4 H38 BLOCKED, D0 NOT_GRANTED.** Old Docker ID survival on
managed service success remains a separate explicit safety gate.

## A5 real-DGX wizard preview gate — operator-ready, not yet run (2026-10-13)

A new [exact-SHA physical-DGX wizard dry-run script](DGX-WIZARD-A5-READONLY.md)
checks the installed profile and previews four installable model
targets plus default/full-purge **uninstall dry-run only**, then
executes isolated wizard fixtures. It verifies no change to
`install.env`, the asset ownership registry or the installed current
release pointer. Stage A5 is **ACTUAL_DGX_NOT_RUN** until a fresh
operator terminal log is received; GitHub CI alone is not A5.
The existing legacy runtime and old container remain untouched;
M1 LIVE NOT_QUALIFIED, H38/M4 BLOCKED and D0 NOT_GRANTED.

## Original fourth model lychee888: FP8-PLE separate compatibility path (2026-10-13)

The public checkpoint card claims a ~123.25 GiB OrcaRouter derivative
with FP8 E4M3 PLE and a single BF16 global scale; its author documents
a **dual-DGX** recipe using an FP8 PLE loader override, **not** proof of
single-GB10 TP=1 operation. Existing model registry has no lychee888
download defaults, image or runtime mapping; `serve.sh` has no case.
It is **planned / not selectable**. [Source-grounded staged integration
plan](LYCHEE888-WIZARD-INTEGRATION.md) defines metadata-only L0, source
L1, bounded future host L2 and final wizard admission L3. No model
download, runtime launch or actual DGX change is authorized by this plan.

## P0 model selection usability — retry and safe cancellation (2026-10-13)

The interactive installer now offers a **Cancel** entry for fresh install
and existing-profile switches and allows re-entry after invalid model
number/profile input. It preserves the previous profile until a valid
selection, and cancelling exits before a model/start/purge operation.
Existing `lychee888` remains displayed as planned/not selectable.
Synthetic wizard-integration tests cover invalid→valid, cancel and
manifest immutability; no new actual-DGX test has been run.

## lychee888 L0 metadata-only probe added (2026-10-13)

Candidate-only `scripts/model/inspect_lychee888_metadata.py` can now
inspect Hub revision JSON plus `config.json` and the safetensors
**index JSON only**, with no tensor download or model load.
Synthetic tests validate the 128-numbered PLE shard keys, 10 FP8
file references, one global scale in the final file, config dtype,
pinned SHA and fail-closed corruption cases. Successful execution
means `INDEX_STRUCTURE_PASS_METADATA_ONLY`, **not** verified
safetensors dtype, weights, TP1 runtime or strict RM stability.
Public model-card claims have **not** been promoted to measured
checkpoint evidence; actual remote L0 output still outstanding.
`lychee888` remains planned/not-installable and no DGX change
is approved by this source-only milestone.

## P0 wizard shared input: closed-input fail-closed regression (2026-10-13)

Code review of the existing terminal wizard found that EOF / interrupted
input could be treated as an empty/default answer when Bash `errexit`
was suppressed by conditional or AND/OR callers. The common reader now
exits with code 2 for EOF rather than treating it as a default-entered
answer, guarding default-yes confirmations and memory-monitor settings.
Normal newline-terminated Enter and explicit consent remain unchanged;
additional `test_wizard_ui.py` cases cover the failure modes.
Only branch/CI source and disposable-subprocess behavior are in scope;
there is **no actual DGX host action** and no M1/M2/M3/M4/D0 promotion.

## Primary P0 restored: original wizard goal and five tracked families

**The product is an easy interactive terminal wizard for first install, uninstall
and model/profile switch**, not primarily an H38 serving experiment.
**Original targets:** `orcarouter`, `nvidia`, `mazinb`, `lychee888`;
**later added:** generated `orcarouter-hybrid` H6. Exactly **3/4 original**
are registry-installable, plus Hybrid, for **4/5 tracked**; `lychee888`
remains planned/not-installable. H38 is an OrcaRouter runtime candidate,
not another user-selectable model. [Canonical objective, model identities
and acceptance](PROJECT-MISSION-AND-MODEL-SCOPE.md).

Work on safe wizard UX/feature parity, missing planned original-model
support and offline tests may proceed despite H38/M4 live blocking gates.
All real-host safety, strict RM, D0 destructive-host and PR promotion rules
remain unchanged. The prior B4 read-only observation does not imply live
installer, service or model-switch E2E completion.

## Physical DGX B4: exact image/container and memory pre-start snapshot (2026-10-13)

The operator completed a clean exact-SHA (`b35d0f3d7840d00c55f4c633813e88ac367c6373`) B4 **read-only** pre-start snapshot with `M1_PRESTART_READONLY=COLLECTED`. Immutable `current` still resolved to `ff67bab3`; legacy OrcaRouter `vllm-skinny-tp1:v1` image and retained Docker container matched; existing container ID `f6bfee5a4217...` was EXITED/exit0/non-OOM; rollback name absent; monitor/protect remained `1`; MemAvailable approximately **118.2 GiB**, SwapFree approximately **143.1 GiB**, PLE swap file active, systemd inactive/dead/success. This is **B4=COLLECTED_PRESTART_READONLY**, NOT a successful model start or strict RM host-stability measurement. [Exact operator B4 evidence and installed-release code review](../scripts/benchmark/evidence/dgx-b4-m1-prestart-readonly-20261013.md).

The installed `ff67bab3` legacy service restart is **not an in-place Docker restart**: the previous container is renamed to rollback and removed on successful candidate commit; general failure recovery may start an intentionally stopped predecessor. Thus it is only reversible in the managed logical sense, *not preserving the exact original container ID*. Preserve the existing Docker object if exact-ID retention is required; the B4 observation alone does not authorize a live start. Current release monitor logic also differs from the archived candidate's swap-growth trigger, so keep version-specific semantics separate. **M1 live NOT_QUALIFIED, M2 NOT_RUN, M3 NOT_QUALIFIED, M4/H38 BLOCKED, D0 NOT_GRANTED, PR #259 Draft/Open/Unmerged.**

## Physical DGX B3 completed: exited managed runtime and all state markers absent (2026-10-13)

On exact clean operator checkout `b35d0f3d7840d00c55f4c633813e88ac367c6373`, the **existing read-only runtime-offline collector completed all three probes rc=0** with final `MANAGED_RUNTIME_OFFLINE=COLLECTED_READ_ONLY`; the subsequent full service unit and eight state-marker existence checks also reached `IMMUTABLE_SERVICE_INSPECTION=COLLECTED_READ_ONLY`. Docker predecessor EXITED/ExitCode=0/OOMKilled=false, configured `127.0.0.1:8888` bind exists but running port map empty, systemd loaded/inactive/dead with `Result=success`, service unit runs immutable `current`, and `runtime-commit.env`, `runtime-stop.env`, `monitor.pid` plus four transition markers and the adoption marker are ABSENT. This **supersedes only the B3 partial collection status** documented later below, not the earlier B2 Doctor failures. [Complete operator evidence and installed-release safety review](../scripts/benchmark/evidence/dgx-b3-readonly-runtime-unit-complete-20261013.md).

The historical Oct 7 monitor-protected managed candidate abort / predecessor left stopped remains the best-supported lineage. Source of the **installed** immutable `ff67bab3` release confirms protected abort leaves a stopped predecessor, but **ordinary rollback/recover may start the predecessor** and its unit uses direct Docker-name `ExecStop` rather than newer attested stop helper. No blind legacy `systemctl restart` is authorized by B3. First review exact installed service identity, preflight, rollback/stop, container ownership and protection invariants; only then construct a bounded reversible legacy OrcaRouter M1 plan. **B3=COLLECTED_READ_ONLY; M1 NOT_QUALIFIED; M2 NOT_RUN; M3 NOT_QUALIFIED; M4 H38 BLOCKED; D0 NOT_GRANTED; PR #259 Draft/Unmerged.**

**Cross-session continuity:** [stable handoff prompt template](SESSION-HANDOFF-PROMPT.md); at the start of every session read this status and fresh GitHub CI/PR metadata. Do not freeze a feature HEAD in the template.

## Physical DGX stage B2: read-only Doctor collected, stopped baseline (2026-10-13)

Operator-supplied exact-SHA `b35d0f3d7840d00c55f4c633813e88ac367c6373` lifecycle inventory found **7 successful read-only sections** and Doctor **5 FAIL / 2 WARN** (`doctor_readonly rc=1`; final `PARTIAL_CHECK_FAILURE`). Manifest complete, OrcaRouter selected, four transaction states idle, 18 checkpoint shards complete and memory protection enabled. Container remained EXITED, systemd INACTIVE, attestation MISSING, monitor PID absent and health unreachable. Non-CMA available **118 GiB**, free **79,620 MiB**, swap free **143 GiB**, model filesystem free **104 GiB**. This is **B2=COLLECTED_PARTIAL**, not M1 live health. The missing published port was observed on an exited container; it is not on its own a host-bind configuration failure. [Full exact-source B2 operator evidence](../scripts/benchmark/evidence/dgx-b2-readonly-lifecycle-doctor-partial-20261013.md).

The existing October 7 managed candidate protected abort / stopped-predecessor lineage remains relevant, but a new healthy live runtime, an intentional current stop, and strict RM stability are **not** proven by B2. First review installed immutable release and service identity, rollback/stop bounds, and historical protection evidence; only then consider a reversible **legacy OrcaRouter** baseline using the existing managed service path with protection unchanged. Do not use a raw Docker start, rewrite attestation, silently refresh image defaults, or conflate this with H38. M1/M3 remain NOT_QUALIFIED, M2/D1-D5 NOT_RUN, H38/M4 BLOCKED, D0 NOT_GRANTED and PR #259 Draft/Unmerged.

## Actual DGX release-path and legacy service-unit interpretation (2026-10-13)

After B2, the operator inspected the already-verified DGX checkout `b35d0f3`. The immutable `current` release was `ff67bab3` with previous `a8aeca47`, but `install.env` retained a mutable checkout for `INSTALL_ROOT`. A one-off comparison printed `MISMATCH_STOP`; **this comparison is not a valid generic gate** because the installed `ff67bab3` release updater supports an explicit immutable `--runtime-root` service override and its runtime runner derives execution root from the installed script. The observed unit starts from immutable `current`; the B2 Doctor previously verified release integrity and unit path. The observed `ExecStop` was the legacy direct Docker-name stop, consistent with the exact installed release but not the latest feature branch's attestation-checked service stop. Output ended in a `systemctl` pager before state markers and completion marker; follow-up status is **PARTIAL_READONLY**, not an installation failure or new live qualification. [Dated physical-DGX evidence and source-level interpretation](../scripts/benchmark/evidence/dgx-b3-release-path-and-systemd-partial-20261013.md).

Use `--no-pager` and the existing read-only offline diagnostic for the remaining information. Do not alter the manifest or systemd unit just to force equality. Live M1 NOT_QUALIFIED, H38/M4 BLOCKED; PR #259 Draft/Open/Unmerged.

## Managed model profiles

| Profile | Registry status | Managed state | Current host-stability interpretation |
|---|---|---|---|
| `orcarouter` | stable/default/installable | primary managed profile; 16 GiB KV resilience default | stable project default; strict RM evidence remains authoritative for any new run |
| `nvidia` | experimental/installable | optional comparison path | not promoted to stable |
| `mazinb` | experimental/installable | live managed activation exercised; 16 GiB KV resilience value | managed readiness can pass while strict RM evidence still makes the run HOST-STABILITY FAIL |
| `orcarouter-hybrid` | experimental/installable/generated H6 | warm/reuse and managed round-trip functionally validated | FUNCTIONAL PASS / HOST-STABILITY FAIL under strict RM semantics |
| `lychee888` | planned/non-installable | no qualified managed path | not selectable |

Installability is an implementation property, not a qualification claim.

## Strict host-stability rule

FUNCTIONAL and HOST-STABILITY classifications are separate.

> Any confirmed NVIDIA RM `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` in a valid
> measured run is HOST-STABILITY FAIL, even when fallback recovers and the runtime
> reaches READY.

A 16 GiB KV cache is a resilience/default setting for the relevant managed profiles.
It is **not** a proven fix for the NVIDIA RM system-memory allocation mechanism.

## R9–R32 allocator/localization closure

The current engineering closure is indexed in
`scripts/benchmark/evidence/README.md`, ending at
`orcarouter-r23-r32-allocation-localization-closure-20261006.md`.

The supported chain is:

```text
first model construction / repeated decoder construction
  -> direct NVIDIA RM system-memory allocation
  -> 64 KiB / order-4 physical-page demand
  -> node0 Normal / Unmovable pressure with Movable fallback/pageblock stealing
  -> failed high-order acquisition
  -> rollback
  -> immediate order-0 fallback
  -> recoverable NV_ERR_NO_MEMORY
```

Important boundaries:

- R21/R22: common early physical-page burst is roughly 75 GiB over about five seconds;
  later PLE/swap pressure is separable from this burst.
- R23: the measured endpoint is direct NVIDIA RM system allocation through
  `nv_alloc_pages` / `nv_alloc_system_pages`; selected UVM allocation boundaries do
  not own the measured burst.
- R24: H6 W4A16 plus forced 16 GiB KV does not remove the structural burst.
- R25–R28: the burst localizes to first model construction, then predominantly to the
  Qwen4Exp decoder construction cadence rather than long checkpoint fill.
- R29/R29b: repeated `800 MiB -> 400 MiB` RM pairs form a strict adjacent cadence.
- R30: all 48 repeated 400 MiB events localize exactly to packed `w13_weight`
  construction.
- R31: each paired 800 MiB event occurs before ModelOpt-MoE create-weights begins.
- R32: exact-image source inspection finds no separate explicit direct pre-create
  model-weight allocation that can be promoted as the 800 MiB owner.

The best-supported interpretation for the 800 MiB family is therefore a discrete
lower/global CUDA/NVIDIA-RM backing/reservation growth event temporally induced by the
repeated decoder construction cycle. This is a mechanism-level inference, not proof of
the exact proprietary lower allocator call.

Do not restart model-prefix/Linear/attention/hyper-connection marker expansion for the
800 MiB ownership question unless a new actionable hypothesis invalidates the closure.

## H38 determinism track

The H38 decoder-only runtime is separately qualified through
`scripts/runtime/orcarouter-v029.sh` and summarized in `docs/H38-DETERMINISM.md`.

That historical qualification is **not** the same as transactional
installer/systemd managed-service qualification. The current H38 integration branch
implements the candidate `orcarouter` managed image/defaults, clean-host H38 image
construction, H38 runtime controls, preflight/doctor provenance checks, asset
inventory, and an atomic cross-release same-profile refresh transaction.

The earlier two-stage assumption — update immutable code, require the persisted
legacy CPU-offload runtime to become READY, then refresh the profile image — is
superseded. The matched PR-base-main control reproduced the same memory-protection
stop in that legacy intermediate state, so it is not a valid H38 discriminator.
The new `release-profile-refresh-transition.sh` path binds the qualified target
release and H38 candidate manifest before the single managed-service replacement.
The service runner writes target attestation while deferring runtime-transition commit,
so the previous rollback container remains available until the outer lifecycle commit.
Recovery therefore owns the release-pointer + manifest + runtime tuple rather than only
release and manifest state. Rollback is also identity-safe at the service boundary:
`ExecStop` stops only the attested container ID, a still-running restored predecessor
is reattached without replacement, and a safety-stopped predecessor is left stopped
instead of being cold-started merely to recover service state. Startup interruption
recovery also consumes the restored-runtime handoff inside the already-running target
runner, so changing `current` back to the previous release cannot cause a blind
systemd retry into an older runner before adoption completes.

This is **implementation state only**. The hardened atomic transaction now also
quiesces the candidate monitor before predecessor restoration, proves rollback topology
before mutation, restores the predecessor monitor from the restored release policy, and
uses a guarded post-migration follow-up runner. The latest implementation/test head
`acb69b83e28b593e434d2e5e51b7f9b4584b6aad` passed GitHub Actions
`37622310894`: shell syntax, ShellCheck, Python compilation, **581/581 unit tests**,
and whitespace all passed. Live managed H38 acceptance remains a separate gate. The guarded migration entry is
`scripts/benchmark/run-h38-managed-migration-gate.sh`; it requires an exact clean
target SHA and does not use the retired legacy-READY intermediate. After that gate
passes, `scripts/run-h38-managed-followup-gates.sh` binds the same migration evidence
baseline to managed-alias determinism, the >=90% decode-performance gate, a supported
managed-service replacement/restart, doctor/attestation checks, and one strict RM
follow-up window. The first live run through the new atomic transaction was executed on exact branch head
`05748a9c9a2b206a536b454dc5d662d7750913db`. It reached the H38 managed
candidate directly (PLE mmap, exact QSA, decoder-scope image) but memory protection
stopped the candidate during startup before READY. The guarded gate therefore recorded
`FUNCTIONAL=NOT_REACHED`, `HOST_STABILITY=INCONCLUSIVE`,
`kernel_window_rc=0`, `rm_oom_count=0`, and `protected_stop=1`. Recovery restored
the previous release + manifest + runtime tuple while preserving the safety-stopped
runtime instead of forcing a legacy cold restart. This is not a managed-H38 pass and
does not authorize the follow-up determinism/performance/restart gate. The terminal
summary did not retain the exact monitor threshold samples, so the gate now also extracts
the monitor start/warning/protection lines into a compact evidence file without changing
any protection threshold or strict RM classification rule.

The preserved trigger lines were subsequently recovered. Across the counted protection
window, non-CMA available rose from `27111 MiB` to `29909 MiB`, non-CMA free stayed
around `0.9-1.15 GiB`, swap growth increased from `654 MiB` to about `3.46 GiB`,
and swap-free remained above 139 GiB. The 10 GiB absolute available gate therefore did
not trigger; the stop came from the swap-growth arm while reclaimable available memory
was increasing. This matches the monitor condition family already known to create a
normal-cold-load false positive, but historical RM failures can also begin with high
available + low free. The current evidence is therefore classified as a **monitor
heuristic collision**, not a proof that the H38 candidate was safe to continue.

H38 must not be described as promoted into the managed runtime until
lifecycle/restart/doctor, managed-alias determinism, performance, and strict RM
host-stability gates in
`scripts/benchmark/evidence/orcarouter-h38-managed-integration-plan-20261007.md`
are recorded as passing.

## Memory monitor caveat

The current runtime monitor is CMA-aware and implements the repository's present
protection heuristic. In particular, low non-CMA free memory can become
protection-significant when non-CMA available is low or swap consumption since monitor
start increases by the configured gate (currently 256 MiB in the helper defaults).

This heuristic is **not a proven discriminator for RM failure**. Live Hybrid cold-load
evidence has shown that the 256 MiB swap-growth arm can produce a false-positive
protected stop during otherwise normal startup. The first atomic H38 managed attempt
reproduced the same signal family: low non-CMA free plus swap growth while non-CMA
available increased through the counted window, with `rm_oom_count=0`. Historical
PR #245 evidence also shows that real RM failures can occur while reclaimable available
memory is still initially high, so high available alone cannot suppress protection.
Treat the current state as a heuristic collision requiring a stronger discriminator,
not as justification to disable or simply raise the swap-growth gate. The next isolated
A/B keeps the protective monitor and H38 runtime identity unchanged but disables
speculative MTP only (`SPEC=none`) to test whether the later MTP materialization is what
crosses the protection boundary. The runner requires the recovered managed predecessor
to remain stopped, so it does not cold-start the legacy runtime merely to establish an
experiment baseline. This is a mechanism discriminator, not a production configuration. The isolated runner passed static CI on
`3d4eadcf2ce60c55b600d9e3ecd4143d061355de` in run `37633676272` with
**587/587 tests**. The first 2026-10-08 operator invocation was setup-invalid before
candidate start because the harness incorrectly equated manifest `INSTALL_ROOT` with
the immutable current-release root. The installer records the source repository root in
`INSTALL_ROOT`; immutable runtime identity is the separate verified release pointer.
The harness was corrected without changing runtime or protection policy. No live SPEC=none result has yet been recorded. A second 2026-10-08 invocation was
also setup-invalid before candidate start: the final negative Docker-existence guard
in the baseline function returned 1 in the required "container absent" state, and
top-level `set -e` exited silently. The harness now uses explicit conditional guards
and an explicit successful return. Attempt 03 then reached candidate creation but exposed a here-document control-flow
bug in the post-start identity validator: the intended shell `fail` line was consumed
as Python stdin, so exact candidate identity was not proven. That attempt is harness
invalid regardless of any later runtime outcome. The validator is now explicit
`if ! python3 ...; then fail; fi`, and `VALID_CLEAN` additionally requires a
persisted successful identity proof. Strict RM kernel evidence remains the classification
source of truth.

Attempt 03 also retained a useful non-gating diagnostic sequence: the launched
candidate reported `SPEC=none`, completed all 18 main checkpoint shards, and then
recorded four strict RM `_memdescAllocInternal / NV_ERR_NO_MEMORY` events. The first
RM event occurred before the monitor's first counted protection sample; protection
stopped the candidate only afterward. This materially weakens MTP materialization as
the sole cause and distinguishes this run from the earlier no-RM monitor-heuristic
collision. Because exact identity was not attested, one corrected rerun is still
required before rejecting MTP causation formally.

The corrected attempt 04 now provides the formal MTP-discriminator result. Exact
candidate identity passed (`identity_validated=1`), `SPEC=none` was confirmed, but
the unchanged monitor again stopped the candidate during early shard loading.
`rm_oom_count=0`, `protected_stop=1`, and the result is
`PROTECTED_STOP`: FUNCTIONAL NOT REACHED / HOST-STABILITY INCONCLUSIVE. non-CMA
available stayed about 40-45 GiB while low non-CMA free plus several GiB of swap growth
armed protection. Therefore MTP materialization is **not sufficient to explain the
managed-H38 protected-stop boundary**. The next step is offline/read-only trajectory
comparison against preserved strict-RM failures before any monitor-policy change.

## H38 allocator/protection observability — 2026-10-08

The valid MTP-off discriminator attempt 04 established that removing MTP
is insufficient to avoid the H38 protected-stop boundary. The exact
production-shape `SPEC=mtp k=2` allocator/protection attempt 01
also yielded a valid `PROTECTED_STOP` at `2026-10-08 11:06:47 KST`:
`FUNCTIONAL=NOT_REACHED`, `HOST-STABILITY=INCONCLUSIVE`,
`rm_oom_count=0`, `OOMKilled=false`, collector and kernel window valid.
The external memory protection policy was not changed. The managed
predecessor remains stopped.

The operator's **complete raw archive** was subsequently analyzed
offline; canonical result:
`scripts/benchmark/evidence/orcarouter-h38-allocator-protection-offline-analysis-20261008.md`.
The read-only analysis uses 502 pre-event 1 s fast samples and 101
pre-event 5 s slow samples, explicitly excluding 40/8 post-event samples.
The dominant Normal order-4+ collapse was
**-74,508.750 MiB** from `01:59:02.196334Z` to
`01:59:07.196252Z` (same window global MemFree
**-75,157.664 MiB**, node0 Normal free **-75,157.254 MiB**,
MemAvailable **-76,158.621 MiB**, SwapFree **0.000 MiB**).
Using the deliberately non-overlapping R21/R22 meminfo category set,
conventional resident growth was **+396.148 MiB**, giving an
approximate **+74,761.516 MiB core-unexplained physical-page loss**.
The identical-scale R21/R22 maxima were +75,174.387 and +75,138.043 MiB
over five seconds. This establishes a reproducible early-host-pressure
pattern but does **not** attribute exact NVIDIA RM/UVM page ownership
or authorize a safety threshold change.

The full timestamped phase log corrects an earlier summary: only
**14/18 shards were logged complete BEFORE the protection event**;
`15/18` was logged `6.95 s AFTER` protection had triggered.
The dominant physical-page burst occurs around the initial `0/18`
startup marker and before the first shard completion, not at shard 15.
The previous excerpt-only report is superseded by this full-history
phase correlation.

Original live runner exit-summary consistency was fixed and CI
`37718076547` succeeded with 596/596 tests; documentation
synchronization CI `37718270884` likewise passed 596/596.
A separate archived-evidence offline analyzer and regressions make
the full-history result reproducible. The analysis is read-only and
requires no new DGX experiment.
The full-history offline analyzer and synthetic regressions were committed
at `a9f4ec6658653b49cf908b567aea608e831313d6` and qualified by
GitHub Actions `37744164668` **SUCCESS, 599/599 unit tests**, shell syntax,
ShellCheck, Python compile and whitespace PASS.

The **R11/R23–R32-to-H38 mechanism transfer review** is now recorded at
`scripts/benchmark/evidence/orcarouter-h38-r23-r32-allocator-mechanism-transfer-20261008.md`.
R23 directly localized its historical same-scale burst to NVIDIA RM
`nv_alloc_pages` / `nv_alloc_system_pages`: 74,537.938 MiB logical
order-4 activity over a 75,083.652 MiB physical residual (99.273191%)
**in that R23 measurement**. H38's similar 74,761.516 MiB early
residual supports transfer of the **RM/backing-growth mechanism
hypothesis**, but **H38 did not capture its own RM call trace** and
the H38 physical residual is not driver-owned bytes. R30/R31 closed
the repeated 400 MiB (packed w13) and pre-MoE 800 MiB request
positions; R32's negative direct-allocation source check covered an
exact R28 image, not the H38 image. H38 carries H11/H12 patched
compressed-tensors semantics, so an exact-H38-image source check
requires separate evidence if a concrete mitigation warrants it.
The R23–R32 line of model-component prefix tracing stays closed;
**no new live R33 is authorized**.

The **exact-H38-installed-image source check has now been executed**
on the DGX Spark, using the guarded SHA
`1a4416581f4064baa110fc83947c442c360c4689` and the
`vllm-orcarouter-v029-h38-decoder-scope:v1` image
(`sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`).
Operator output closed `H38_EXACT_IMAGE_SOURCE_PREFLIGHT=PASS`,
`H38_EXACT_IMAGE_SOURCE_CONTRACT=PASS`, `source_check_rc=0`,
and `image_identity_unchanged=YES`.
Canonical DGX result:
`scripts/benchmark/evidence/orcarouter-h38-exact-image-source-contract-result-20261008.md`.
The original guarded preflight and static-check plan remains at
`scripts/benchmark/evidence/orcarouter-h38-exact-image-source-contract-plan-20261008.md`.

The H38 installed source retained both packed `torch.empty`
allocations under H11 `ModelWeightParameter`, H12 object-preserving
post-load rename, H38 Humming/Marlin controls and **the R32 precreate
source contract now replayed on the exact H38 image**.
The direct precreate allocation syntax count was **0** in both
inspected factory/routed scopes. This only rules out the checker's
specific explicit syntax, not indirect allocations. There was no
GPU/model load, managed-service replacement or protection change.
**This is a source-contract PASS only. RM mitigation is unproven;
the original H38 protected stop remains FUNCTIONAL NOT_REACHED /
HOST-STABILITY INCONCLUSIVE.** The checker CI `37747053983` and
docs CI `37747347746` both passed **606/606 tests**.
No R33 live trace or managed promotion is authorized.

## H38 CT deferred-w13 feasibility — 2026-10-08

The historical M1 branch `exp/m1-deferred-meta-w13`
(`4d72f8750e8a7beaec96a869e2dbfeaa7d4c747a`) is a
**ModelOpt/H6/R28 prototype**, not a tested H38 CT mitigation.
It defers the `ModelOptNvFp4FusedMoE.w13_weight` allocation with
`device="meta"` and native layerwise processing. The current H38
production image instead uses H11/H12
`CompressedTensorsW4A4Nvfp4MoEMethod` with
`w13_weight_packed` and post-load aliases. A direct M1 patch
transplant is invalid.

The implementation passed GitHub Actions `37778807130`:
**SUCCESS, 613/613 unit tests**, shell syntax, ShellCheck,
Python compilation and whitespace PASS.

**H38 CT Meta static prerequisites: VALID DGX SOURCE PASS.** The
operator ran the unmodified guarded checker at
`ac58309620ace2213df68ebf06b2c18b9592f394` on
`vllm-orcarouter-v029-h38-decoder-scope:v1` image ID
`sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`.
Both `H38_CT_META_STATIC_PREREQUISITES=PASS` and
`H38_CT_META_SOURCE_PREFLIGHT=PASS` were observed; image
identity unchanged, no model/GPU launch, service/protection change.
Canonical result:
`scripts/benchmark/evidence/orcarouter-h38-ct-meta-w13-source-prerequisites-result-20261009.md`.
Installed CT class `uses_meta_device` direct declaration was
**NO**; base-loader/layerwise wrapper/materialization functions were
`SOURCE_PRESENT`; original H11 packed `torch.empty` persists,
H12 aliases pass. **No actual CT meta patch/materialization or RM
reduction is established.** The checker and synchronization static
CI `37778807130` / `37779107553` passed **613/613** tests.

The metadata tool implementation was statically qualified at
`b476441899d07d04e9db3669ccd881f4351ef15e`: GitHub Actions
`37822913604` **SUCCESS, 620/620 unit tests**, shell syntax,
ShellCheck, Python compilation and whitespace PASS.
The production checkpoint metadata attempt 01 on
`551da2c603f2e83c6aedb4668e831e67dae82da6` was
**PREFLIGHT INVALID** before any shard result, due to Python
`No usable temporary directory`. Canonical record:
`scripts/benchmark/evidence/orcarouter-h38-checkpoint-metadata-order-attempt01-invalid-tempfile-20261009.md`.
The private `/tmp` 64 MiB `tmpfs` repair passed
static CI `37882840040` and `37883026595`,
**622/622 tests**.

**Attempt 02: VALID METADATA ANALYSIS / ORDER_GATE FAIL** on
`eadaaeefbc23abf428e880890537ca26ea162f9d`,
with the same pinned H38 image
`sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`.
The isolated tempdir worked. The index mapped **18 files: 17 numbered
`model-XXXXX-of-00017.safetensors` shards plus
`model-mtp.safetensors`**, 223,046 tensor keys, 221,186 routed keys,
all 48 routed layers. However, layers **0, 8, 11 were revisited**
and the maximum routed interval overlap was **3**.
The strict metadata-order gate is **FAIL**, not checkpoint
corruption or runtime materialization failure; canonical result:
`scripts/benchmark/evidence/orcarouter-h38-checkpoint-metadata-order-attempt02-gate-fail-20261009.md`.
Routed disk bytes total **72,981,184,512**; both theoretical
release-at-last-routed and release-at-last-layer-key scenarios
reported **6,448,748,544** bytes. These are **not**
observed runtime RAM/GPU peaks.

The outer runner previously misclassified a completed
`H38_CKPT_METADATA_ORDER_GATE=FAIL` as
`H38_CKPT_METADATA_PREFLIGHT=INVALID` because the
Docker command's non-zero exit was collapsed. The follow-up
classifier will preserve exit **3 = ORDER_GATE_FAIL**, while retaining
**2/infrastructure failure = INVALID**. Header-only diagnostics
will report the concrete first/last shard positions of the 0/8/11
revisits and separate numbered model files from auxiliary MTP.
The follow-up source/diagnostic commit
`51850e28230c760dadac8fd86268d949b7623345` passed
GitHub Actions `37883805274`: **SUCCESS / 624 of 624 tests**,
shell syntax, ShellCheck, Python compilation and whitespace PASS.
**Attempt 03: actual DGX revisit diagnostic observed**, running
`f875aa2ea141e004fe2c0b37174bd275d9df39a1` against the
unchanged H38 image and canonical OrcaRouter checkpoint.
`H38_CKPT_METADATA_ORDER_GATE=FAIL` and
`H38_CKPT_METADATA_PREFLIGHT=ORDER_GATE_FAIL` were correctly
reported; exit code **3**. The exact source and run spans are in
`scripts/benchmark/evidence/orcarouter-h38-checkpoint-metadata-order-attempt03-revisit-ownership-20261009.md`.
**Base-model layer 0** resides in numbered shard 1; the
second layer-0 run is actually the distinct **MTP module namespace**
(`mtp.layers.0`) in `model-mtp.safetensors`.
Independent **base-model layer 8** runs across numbered shards
4→5, and **layer 11** runs across numbered shards 5→6.
Base-only revisit diagnostic is **[8,11]**, so the strict
contiguous routed-layer condition fails even without the
MTP numeric-layer classifier collision.

Observed index: **17 numbered base-model shards plus
1 MTP file**, 223,046 keys, 221,186 routed keys, 48 routed
layers, maximum overlap **3**. Both hypothetical routed-byte
retention cases reported **6,448,748,544 bytes**; these
are on-disk metadata estimates and **not measured RSS/RM/GPU
peaks**. Image ID unchanged, no model/GPU launch.
The per-shard revisit attribution question is **closed** for
the tested assumed key-order model; **actual H38 installed loader
order and materialization lifecycle remain unverified**.
No new identical checkpoint recheck is authorized: next
engineering gate is exact-installed-loader source inspection,
not re-running unchanged metadata.

The full 18-file acceptance gate **cannot be overridden**
by omitting MTP. The actual H38 loader stream order, scales and
peak buffered-memory behavior remain unverified. No CT meta patch,
checkpoint contents modification, new GPU model test, R33,
monitor relaxation or managed promotion is authorized.


## H38 exact-installed weight-loader source-contract gate — 2026-10-09

The checkpoint Attempt 03 source/namespace attribution is **closed**
but exact H38 runtime loader order remains **unverified**. vLLM
**upstream v0.29.0 source** independently contains the default
index-filtered safetensors iterator, natural file sort,
`safe_open.keys()` and `get_tensor`; Qwen4Exp CausalLM and
ConditionalGeneration `load_weights()` pass
`orig_to_new_substr={"mtp.": None}` through `WeightsMapper`.
The mapper skips **model assignment** of MTP names, but source
order alone does **not** show that MTP data was excluded before
`get_tensor`. Native layerwise `load_numel` completion buffers
args and replays loaders through meta materialization; this source
structure does **not** prove safe CT-scale/packed-weight completion
for split routed layers 8 and 11.

Implementation commit `1e4aadaa029937a61007e225c173239079481a16`
passed GitHub Actions `37889474895`: **SUCCESS, 633/633
unit tests**, shell syntax, ShellCheck, Python compile and
whitespace PASS. This is **checker implementation CI only**,
not an actual image-source observation.

**Real DGX H38 installed-loader source inspection completed: PASS.**
The operator ran exact clean checkout
`b85f506a4f3f6e7a1272f6e5b37a137a5f57a5f9` against immutable
image ID
`sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`
in a no-network/no-GPU, read-only, UID 65534 runc inspector.
Observed `H38_LOADER_STATIC_CONTRACT=PASS`,
`H38_LOADER_SOURCE_PREFLIGHT=PASS`, unchanged image identity,
no checkpoint payload read or managed-service mutation. Eight
exact installed source SHA256 fingerprints and all observed
`SOURCE_PRESENT` conditions are in:
`scripts/benchmark/evidence/orcarouter-h38-installed-loader-source-contract-result-20261009.md`.

**Source proof only:** default indexed file selection, natural sorted
safetensors + `safe_open.keys()` + `get_tensor`, Qwen4Exp
`mtp.` name mapper, alternative loader routes, native layerwise
numel-based buffer/replay and H11/H12 CT aliases are present.
An `mtp.` model-mapping skip does **not** establish a pre-read
checkpoint payload skip. Actual selected H38 load format/strategy,
prefetch/multithread, EP filter, MTP model path and split
layer 8/11 packed-scale completion are **UNVERIFIED**.
The 18-file checkpoint `ORDER_GATE=FAIL` remains unmodified,
with 17 numbered base files + MTP, layer 8/11 base shard revisits
and no verified safe buffering bound. No CT meta patch,
RM reduction, functional or host stability qualification results.

The previously staged source-only checker is:

`scripts/benchmark/inspect-h38-installed-loader-source.py`,
`scripts/benchmark/check-h38-installed-loader-source.sh`, and
`tests/test_h38_installed_loader_source.py`.
It checks eight installed vLLM source files and fingerprints
their SHA256; exact H38 image ID, H11/H12/H38 labels, SHA, clean
checkout, no GPU/model/network, read-only inspector mount,
unprivileged runc and private 32 MiB `/tmp` are guarded.
Canonical protocol:
`scripts/benchmark/evidence/orcarouter-h38-installed-loader-source-contract-plan-20261009.md`.
**This is a staged source audit only**: no selected H38 config
path, runtime MTP I/O, buffer bound, memory reduction or stability
qualification has been measured. The 18-file checkpoint strict
contiguous-layer `ORDER_GATE=FAIL` remains authoritative.
No CT `device="meta"` patch or unchanged checkpoint replay is
justified.

## H38 preserved launch loader-config attestation — 2026-10-09

Exact H38 installed loader source check **PASS** does not attest
which loader settings were active during earlier protected candidate
launches. The valid **MTP SPEC=none Attempt 04** source
(`scripts/benchmark/evidence/orcarouter-h38-managed-mtp-startup-discriminator-attempt04-20261008.md`)
recorded an exact runtime identity match and **PROTECTED_STOP**,
`FUNCTIONAL=NOT_REACHED`, `HOST-STABILITY=INCONCLUSIVE`.
**Actual DGX Attempt 04 historical archive attestation completed:
PASS_ARCHIVED_LAUNCH_FLAGS_ONLY.** The operator ran the offline
parser at exact clean checkout
`1bc76cb12cc8df9d9512de0d0cd29e49120c1233`,
using the unchanged captured archive:
`/tmp/orcarouter-h38-mtp-none-attempt04-20261007T232026Z`.
Captured Docker image tag/ID, `candidate-inspect.json` command
versus `candidate-cmd.json`, H38 env lineage and model mount all
matched. The explicitly captured CLI was
**`--load-format safetensors`, executor `mp`, TP=1**.
`--safetensors-load-strategy`, model-loader extra config,
expert-parallel enable/disable, prefetch num threads/block size,
pipeline parallel size and `--speculative-config` were all
**NOT_EXPLICIT**, not inferred defaults. The **same archived
Attempt 04 startup log** contained the marker
`Auto-prefetch is disabled`. This is an observed startup message,
**not** a complete effective `LoadConfig` record.

Canonical operator result:
`scripts/benchmark/evidence/orcarouter-h38-preserved-loader-config-result-20261009.md`.
Source-only code quality CI: implementation
`0a71beb7fdd64ed06e9879c4349acb681e11f99f`,
GitHub Actions `37892699414` **SUCCESS, 641/641 tests**
(and documentation-sync CI `37892894955` **SUCCESS,
641/641 tests**). No Docker command/model/GPU work or host
protection change was performed by this archived-file analysis.

The guarded **read-only offline capture inspector** is:
`scripts/benchmark/inspect-h38-preserved-loader-config.py`,
guard `scripts/benchmark/check-h38-preserved-loader-config.sh`,
regression `tests/test_h38_preserved_loader_config.py`,
and canonical protocol
`scripts/benchmark/evidence/orcarouter-h38-preserved-loader-config-plan-20261009.md`.
It reads only preserved launch identity/CLI fields, redacts
secret environment and host paths, and prints `NOT_EXPLICIT`
for absent options — **never infers effective vLLM defaults**.
The same-archive prefetch marker **was observed** in
Attempt 04. The archived CLI and source checks **do not**
prove exact resolved `LoadConfig`, tensor delivery,
CT scale-completion or bounded buffers. Checkpoint
`ORDER_GATE=FAIL`, split base layers 8/11, and MTP
I/O ambiguity remain. CT Meta and runtime promotion stay blocked.

**PR #259 stays Draft/Open.** Managed migration and performance,
determinism, restart, promotion, and merge remain blocked. The
next useful work is code/evidence-level attribution of the **early
common ~75 GiB allocation burst**, not an unchanged live rerun,
compaction, drop-caches, sysctl or protection weakening.


## Historical evidence semantics

Dated evidence files are intentionally historical. Preserve their measured facts and
then-known decisions, including invalid attempts and superseded next-step plans.
When an older file contains words such as `current`, `pending`, `next`, or an old PR
merge instruction, read them in that dated context unless the file is explicitly marked
as a current index/closure.

Repository-facing current-state documents should point back here or to the evidence
index instead of duplicating volatile experiment-state text.

## Deferred mitigation work

The M1 mitigation prototype was intentionally excluded from PR #244 and is not part of
the R9–R32 canonical merge. Do not describe it as qualified or merged until its own
measurement/acceptance gates are completed.

## H38 CT layerwise-accounting source discriminator — 2026-10-09

The Draft PR #259 branch now stages a new exact-image, read-only AST CT packed/scale accounting inspector and guarded CPU-only wrapper:

- `scripts/benchmark/inspect-h38-ct-layerwise-accounting.py`
- `scripts/benchmark/check-h38-ct-layerwise-accounting.sh`
- `tests/test_h38_ct_layerwise_accounting.py`
- `scripts/benchmark/evidence/orcarouter-h38-ct-layerwise-accounting-source-plan-20261009.md`

The inspector pins the earlier verified H38 installed source digests and checks two packed H11 `ModelWeightParameter` registrations, six component scale registrations, H12 object aliases and the layerwise count/buffer/finalizer source anchors. The repository H11 patch supplies explicit packed `uint8` shape formulas. Upstream vLLM v0.29 per-invocation `get_numel_loaded` capping does not prove per-parameter lifetime deduplication or that all 512 experts and scales have arrived at a layerwise completion boundary.

**Status: STAGED / SYNTHETIC TESTS / NO NEW ACTUAL DGX RESULT YET.** Exact installed H38 tool execution and per-expert completeness, layer 8/11 shard-split finalization, subclass/alias materialization, effective iterator and simultaneous buffer peaks are still unverified. The earlier `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `FUNCTIONAL=NOT_REACHED`, `HOST-STABILITY=INCONCLUSIVE`, and `RM_MITIGATION=UNPROVEN` remain unchanged. H38 GPU/model rerun and PR #259 Ready/merge remain BLOCKED; no host protection modification is authorized.


## H38 CT accounting boundary — synthetic proof scope, 2026-10-09

The branch now also includes stronger installed-source AST shape/dtype checks (two packed ModelWeightParameter uint8 tensors, two float8 group scales and four float32 global/input scales; all eight symbolic size formulas), loadable-tensor exclusions, late size refresh, post-completion rejection, and meta parameter-class/attribute-preserving source markers.

A separate pure-stdlib synthetic suite demonstrates why a layerwise aggregate copied-element threshold does **not by itself prove unique per-parameter coverage**. In a toy model with eight names and only 20 total elements, repeating packed w13 copies can satisfy the aggregate target with missing scales (20 credited, 12 unique), or with a missing half of w13 (20 credited, 16 unique). A separate toy split-shard case leaves 16/20 elements and exposes the non-attention partial-finalizer branch. These are logical counterexamples, **not observations of real H38 repeated calls, unsafe postload or memory footprint**. Historical layer 8/11 shard revisits remain independently observed metadata-only facts.

Implementation and coverage:
- scripts/benchmark/inspect-h38-ct-layerwise-accounting.py
- scripts/benchmark/simulate-h38-ct-layerwise-completion.py
- tests/test_h38_ct_layerwise_accounting.py
- tests/test_h38_ct_layerwise_completion_cases.py
- scripts/benchmark/evidence/orcarouter-h38-ct-layerwise-accounting-source-plan-20261009.md

**Do not promote SOURCE_ONLY/SYNTHETIC into actual installed-image execution or model qualification.** The guarded exact H38 CPU-only inspector still requires an operator-side run and its output; real CT loader completeness and finite simultaneous buffer lifetime are UNVERIFIED. CHECKPOINT_METADATA_ORDER_GATE=FAIL; FUNCTIONAL=NOT_REACHED; HOST-STABILITY=INCONCLUSIVE; RM mitigation UNPROVEN; H38 model/GPU rerun BLOCKED; PR #259 DRAFT/OPEN and MERGE BLOCKED. All host memory protection stays unchanged.


## H38 RoutedExperts dispatch source prerequisite — 2026-10-09

The staged H38 CT source inspector now also requires the earlier installed-image SHA256 fingerprint of RoutedExperts (5206219da6b78315d6b35bee89fd0caa783681846affbf6917f430ef7f2481b5), alongside the existing CT, layerwise, meta and reload-utils fingerprints. Synthetic regression fixtures cover the exact inspected *source* contract, missing indexed-scale writes, missing nonlocal-expert skip, and the overloaded weight_loader concrete implementation.

Public upstream vLLM v0.29.0 RoutedExperts source shows explicit .copy_() in routed weight helpers, but indexed Tensor assignments for scalar/tensor input and global-scale helpers; scale dispatch can depend on GROUP/TENSOR tags, global/local expert remapping and nonlocal expert filtering. Exact TorchDispatchMode operations from these indexed assignments are **not certified by AST source**. In particular, it remains unjustified to treat every syntactic Tensor assignment as a CopyCounter count or to infer complete unique destination coverage for CT scales.

**State: SOURCE_ONLY CODE STAGED; exact H38 installed-source execution PENDING.** The bounded interpreter output is pending DGX operator evidence and can confirm only the exact source anchors and digests. No model/accelerator run, H38 image/source/checkpoint modification or host safety change was made. CT_COPYCOUNTER_SCALE_COVERAGE=UNVERIFIED; CT_WEIGHT_COMPLETENESS=UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE=FAIL; HOST-STABILITY=INCONCLUSIVE; PR #259 remains DRAFT/OPEN and MERGE BLOCKED. The separate source-plan result is recorded in scripts/benchmark/evidence/orcarouter-h38-ct-layerwise-accounting-source-plan-20261009.md.


## H38 installed-source Attempt 01 — checker wrapper mismatch, 2026-10-09

The DGX operator **executed** the exact clean source-only wrapper at Git HEAD b9db2c901676ebc974c22f5ee65b37bc6c208c72 against H38 image sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc. Preflight reached BEGIN; CT AST validation stopped with H38_CT_ACCOUNTING_SOURCE=INVALID reason=unsupported_CT_parameter_wrapper:PerTensorScaleParameter and source_check_rc=2. All five source SHA256 checks occur before the failing allocation AST, but the inspector did not complete validation or issue a PASS result.

**Classification: STATIC CHECKER CONTRACT INVALID / NOT MODEL DEFECT.** This is the first actual operator source-inspection attempt, not an H38 model/GPU run. The CT allocation AST checker previously allowed only ModelWeightParameter and torch.nn.Parameter and was incomplete for vLLM scale subclasses. The follow-up correction admits recognized PerTensorScaleParameter/GroupQuantScaleParameter only in appropriate scale classes while retaining shape/dtype/loader/source digest guards and negative regression tests. The original operator error did NOT specify which parameter was PerTensorScaleParameter or the tensor shape, and the correction is **not independently passed on the exact image yet**. Exact output is recorded in scripts/benchmark/evidence/orcarouter-h38-ct-layerwise-accounting-attempt01-invalid-20261009.md.

**Next gate:** after the corrected commit passes GitHub CI, rerun the guarded source-only image checker on the operator DGX from that exact clean SHA; preserve the full result. CT_SOURCE_CONTRACT=INVALID_ATTEMPT01; CT_SCALE_SOURCE_SEMANTICS=UNVERIFIED; CT_WEIGHT_COMPLETENESS=UNVERIFIED; COPYCOUNTER_SCALE_CREDIT=UNVERIFIED; FUNCTIONAL=NOT_REACHED; HOST_STABILITY=INCONCLUSIVE. Do not modify the H38 image, run the model/GPU, weaken host protection, or mark PR #259 Ready/Merge.


## H38 CT AST source-inspection fallback diagnostics — 2026-10-09

Following operator Attempt 01 (INVALID: unsupported PerTensorScaleParameter), the CI-qualified remediation now has a **fail-closed diagnostic fallback** for a later read-only exact-image AST run. If source-contract validation fails, the inspector first reports the original reason and returns code 2; it additionally re-verifies **all five installed-source SHA256 pins** and, only if those match, emits bounded syntax summaries of all eight expected CT packed/scale registrations. Each entry includes the registration name and line, constructor, initializer expression, symbolic torch.empty dimensions/dtype/device, source weight_loader argument and available keywords. These are **source expressions, not tensors or measured memory**.

This design minimizes blind repeated DGX runs that discover one unsupported constructor at a time. Diagnostics explicitly classify as PINNED_CT_SOURCE_SYNTAX_ONLY_NOT_A_PASS and cannot convert INVALID into PASS. If source hashes drift, no CT AST fallback output is qualified. The wrapper's GPU/no-network/no-pull/sandbox restrictions are unchanged.

**Execution status:** No DGX Attempt 02 result has been provided. Attempt 01 remains the only actual source-check execution observed: INVALID / inspector contract mismatch, not a model failure. Subsequent AST diagnostic code and synthetic tests are repository-side only pending any exact-image invocation. PR #259 remains Draft/Open, no H38 model/GPU run or host-protection change, no CT deferred-meta implementation, no Ready/Merge.


## H38 exact-image CT AST Attempt 02 — eight-parameter source closure pending PASS, 2026-10-10

The operator executed the guarded exact H38 source-only inspector on clean HEAD 88e8a0509676ddfa87780a556d26a82d6ac95a74 and pinned H38 image sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc. The wrapper began and the **SHA-pinned diagnostic fallback** enumerated exactly 8 expected registration sites with no missing names after an AST contract error:

- w13_weight_packed and w2_weight_packed: ModelWeightParameter / uint8.
- w13_weight_scale and w2_weight_scale: **ModelWeightParameter / float8_e4m3fn**, not the previous static checker's allowed torch.nn.Parameter or GroupQuantScaleParameter.
- w13_weight_global_scale and w2_weight_global_scale: PerTensorScaleParameter / float32.
- w13_input_global_scale and w2_input_global_scale: torch.nn.Parameter / float32; the constructor itself has no explicit weight_loader keyword (post-construction attribute paths NOT resolved by this output).
- All eight initializer torch.empty forms have no explicit device keyword, and symbolic shapes match the eight registered names in the operator source diagnostics.

Observed H38_CT_ACCOUNTING_SOURCE=INVALID reason=incorrect_CT_parameter_wrapper:w13_weight_scale:ModelWeightParameter; return code 2. The original failure is **AST CHECKER CLASS-EXPECTATION MISMATCH**, not observed model failure. The fallback checks all five installed source SHA256 digests before returning the diagnostic; neither the complete AST PASS nor the wrapper's final post-success image-identity check was reached.

Canonical immutable result: scripts/benchmark/evidence/orcarouter-h38-ct-layerwise-accounting-attempt02-invalid-20261010.md. The inspector/test source contract is corrected to the **eight exact observed constructor types** with retained shape/dtype/weight-loader and digest guards, not a permissive class-wide allowlist. Pending an independent source-only rerun, CT_SOURCE_CONTRACT remains INVALID_ATTEMPT02 / PASS_PENDING. CI tests are source/synthetic evidence only.

CopyCounter indexed scale write credit, per-expert unique coverage, live split-shard 8/11 finalization/buffer lifetime, peak memory, postload completeness, functional startup, and host stability remain UNVERIFIED. GPU_MODEL_RERUN=BLOCKED; HOST_PROTECTION=UNCHANGED; CT_META_PATCH=BLOCKED; PR_259=DRAFT_OPEN / MERGE=BLOCKED.


## H38 CT installed-image source audit — Attempt 03 PASS (2026-10-11)

**Current authoritative source-only disposition supersedes the earlier PENDING/INVALID status sections; historical Attempt 01/02 logs are retained unchanged.**

The DGX operator successfully fast-forwarded the clean branch to exact HEAD 5fa4265d394255744f8886b857804a28c433cf3f and executed the previously CI-qualified guarded H38 source-only inspector against pinned image sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc. The supplied complete console transcript reports H38_CT_ACCOUNTING_SOURCE=PASS_SOURCE_CONTRACT_ONLY, H38_CT_ACCOUNTING_PREFLIGHT=PASS_SOURCE_CONTRACT_ONLY, source_check_rc=0, image_identity_unchanged=YES; gpu_or_model_load=NO, checkpoint_payload_read=NO, host_protection_changed=NO, managed_service_mutation=NO and ct_meta_patch_implemented=NO. All five pinned installed source SHA256 values passed.

Static source confirmation is now established for eight CT parameter registrations (four ModelWeightParameter: two uint8 packed + two FP8 group scales; two PerTensorScaleParameter float32 global weight scales; two plain torch.nn.Parameter float32 input scales), symbolic shape/dtype/source keyword contracts, the H12 packed→weight same-object alias syntax, 21 Layerwise/CopyCounter/materialization AST anchors and 14 RoutedExperts write-path AST anchors. The two plain input-scale constructors do not explicitly accept a weight_loader keyword; this does NOT establish absence of post-construction setter attributes.

This **does not** establish real TorchDispatchMode credit for indexed scale assignment, all 512-expert unique loaded element coverage, complete shard 8/11 replay, finite peak buffer bounds, functioning H38 inference or host safety. Indexed assignment sites in source remain distinct from observed aten.copy_.default dispatch events. Earlier toy counterexamples remain hypothetical and were not reproduced on H38.

Canonical source result: scripts/benchmark/evidence/orcarouter-h38-ct-layerwise-accounting-attempt03-source-pass-20261011.md. Original operator /tmp logfile and its hash were not independently obtained; provenance is the supplied terminal transcript. This result belongs to the **old checked source HEAD** 5fa4265d394255744f8886b857804a28c433cf3f, not a later documentation-only commit.

Current gates: CT_INSTALLED_SOURCE_CONTRACT=PASS_SOURCE_CONTRACT_ONLY; CT_WEIGHT_COMPLETENESS=UNVERIFIED; CT_COPYCOUNTER_SCALE_CREDIT=UNVERIFIED; CT_SCALE_PARAMETER_SEMANTICS=UNVERIFIED; SHARD_8_11_COMPLETENESS=UNVERIFIED; PEAK_BUFFER_BYTES=UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE=FAIL; FUNCTIONAL=NOT_REACHED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; CT_META_IMPLEMENTATION=BLOCKED; GPU_MODEL_RERUN=BLOCKED; HOST_PROTECTION=UNCHANGED; PR_259=DRAFT_OPEN / MERGE=BLOCKED.

Next bounded plan: inspect post-construction attribute binding of input scales, then consider a strictly isolated, tiny synthetic CPU TorchDispatchMode witness for indexed writes **only if resource and service safety are validated**, followed by source-driven shard 8/11 ownership analysis. No automatic model startup, image rebuild, host resource relaxation, or PR Ready/Merge.


## H38 input-scale postconstruction loader attributes — source-only staging (2026-10-11)

After the real installed-image CT source audit **Attempt 03 PASS_SOURCE_CONTRACT_ONLY**, a separate, read-only **CT scale attribute provenance** inspector, guarded launcher and stdlib synthetic regression tests were staged in the GitHub PR #259 branch. This does not change or rescind the earlier qualified pinned-image CT registration/source result.

The narrow question is why w13_input_global_scale and w2_input_global_scale are constructed as plain torch.nn.Parameter without an explicit constructor weight_loader. Public upstream vLLM v0.29.0 source shows a later set_weight_attrs(variable, extra_weight_attrs) call and a TENSOR quant_method tag; the same upstream common helper sets attributes using setattr after an overwrite guard. A source expression in upstream does **not** by itself prove that the exact installed H38 image contains the same helper semantics or that its runtime assignment succeeds.

New repository tools:
- scripts/benchmark/inspect-h38-ct-scale-attr-provenance.py — stdlib-only AST reader, pins exact CT/RoutedExperts/layerwise installed-source hashes, captures the previously unpinned installed-image model_executor/utils.py helper digest, verifies both registered input-scale setter source sites, H11 extra attrs loader origin, RoutedExperts loader export and layerwise wrapper syntax. The utility digest is a new image-ID-guarded observation, NOT a preapproved SHA pin.
- scripts/benchmark/check-h38-ct-scale-attr-provenance.sh — immutable image-ID/label verification, clean exact HEAD requirement, unprivileged no-network/no-GPU/read-only limited runc; no model/checkpoint read, Docker image edit, managed service or host protection change.
- tests/test_h38_ct_scale_attr_provenance.py — synthetic AST success/fail-close regression only.
- Canonical stage plan: scripts/benchmark/evidence/orcarouter-h38-ct-scale-attr-source-plan-20261011.md.

**Current result is STAGED / not yet executed on DGX**; no PASS of this new attribute-site inspector has been claimed. The existing CT_INSTALLED_SOURCE_CONTRACT=PASS_SOURCE_CONTRACT_ONLY still applies only to the 2026-10-11 Attempt 03 source audit. A future attribute-site source PASS cannot establish effective runtime callback, actual aten.copy_ counting on indexed scales, expert-completeness, shard 8/11 buffer release, inference correctness or host memory stability. GPU_MODEL_RERUN=BLOCKED; HOST_PROTECTION=UNCHANGED; PR_259=DRAFT_OPEN; MERGE=BLOCKED.


## H38 input-scale postconstruction source audit — operator Attempt 01 PASS (2026-10-11)

**This newer confirmed result supersedes the preceding STAGED/PENDING entry for the attribute-site inspector, without enlarging its source-only qualification.** The operator fetched and fast-forwarded the clean branch to exact HEAD 1865521c2ff58add7bddeed6735c76803a3e3637 and executed scripts/benchmark/check-h38-ct-scale-attr-provenance.sh against the original, unchanged H38 pinned image sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc.

Reported verdict: H38_CT_SCALE_ATTR_SOURCE=PASS_SOURCE_SITES_ONLY; H38_CT_SCALE_ATTR_PREFLIGHT=PASS_SOURCE_SITES_ONLY; source_check_rc=0; image_identity_unchanged=YES; gpu_or_model_load=NO; checkpoint_payload_read=NO; managed_service_mutation=NO; host_protection_changed=NO; ct_meta_patch_implemented=NO.

Both CT input-scale registration→quant_method=TENSOR source update→postconstruction set_weight_attrs(variable, extra_weight_attrs) source sequences are verified: w13_input_global_scale registration line 183, TENSOR update 184, setter 187; w2_input_global_scale registration line 192, TENSOR update 193, setter 196. H11 extra_weight_attrs.get('weight_loader') and RoutedExperts loader export, layerwise original-loader reference/reassignment, and the helper guarded setattr source syntax also passed AST source checks.

The image-ID-guarded **newly observed** vllm/model_executor/utils.py source SHA256 is f208310647a012797e0b0e9631d3498135c7f9aef831e35e42e96eceb7623f89. This was NOT pre-pinned or independently preapproved before the run and must NOT be retroactively reported as preverified. The three other source SHA256 values (CT, RoutedExperts, layerwise) matched their earlier independently pinned values. The operator-reported logfile /tmp/h38-ct-scale-attrs-attempt01-20261011.txt was not independently materialized or hashed.

This is evidence that **source setter sites and helper code exist**, not evidence of the actual runtime value of a weight_loader attribute, a callback invocation, real scale copy counter credit, all 512 experts loaded, shard 8/11 ownership completion or finite peak memory. Canonical record: scripts/benchmark/evidence/orcarouter-h38-ct-scale-attr-attempt01-source-pass-20261011.md. The earlier source-audit Attempt 03 PASS_SOURCE_CONTRACT_ONLY remains a separate qualified result.

Current gates: CT_INSTALLED_SOURCE_CONTRACT=PASS_SOURCE_CONTRACT_ONLY; CT_SCALE_ATTR_SOURCE_SITES=PASS_SOURCE_SITES_ONLY; CT_EFFECTIVE_LOADER_RUNTIME=UNVERIFIED; CT_COPYCOUNTER_SCALE_CREDIT=UNVERIFIED; CT_WEIGHT_COMPLETENESS=UNVERIFIED; SHARD_8_11_COMPLETENESS=UNVERIFIED; PEAK_BUFFER_BYTES=UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE=FAIL; FUNCTIONAL=NOT_REACHED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; GPU_MODEL_RERUN=BLOCKED; CT_META_IMPLEMENTATION=BLOCKED; HOST_PROTECTION=UNCHANGED; PR_259=DRAFT_OPEN / MERGE=BLOCKED.

Next engineering decision is a separately provenance-labeled, tightly scoped tiny CPU-only PyTorch TorchDispatchMode indexed-assignment vs explicit copy_ experiment (only in a safe, bounded environment), followed by genuinely checkpoint-aware shard/expert source mapping. Neither requires or authorizes an H38 GPU/model run.


## Isolated external CPU TorchDispatchMode tiny write witness — 2026-10-11

A separate **assistant-side isolated Python environment** (NOT DGX/H38 image, NOT vLLM runtime) was used for a tiny CPU-only PyTorch 2.10.0+cpu experiment, without host or service mutation. Direct Tensor index assignment in this distinct runtime triggered torch.ops.aten.copy_.default under TorchDispatchMode for the tested synthetic scalar and row writes. A synthetic 3x2 tensor with writes to [0,1], row 1, row 2, then a second write to [0,1] credited 1+2+2+1=6 copied elements across four calls, even though only 5 of 6 destination elements were uniquely touched. Repeated writes can therefore satisfy a toy aggregate threshold without complete unique coverage.

**Critical provenance limitation:** this result was obtained on an external CPU PyTorch runtime with version 2.10.0+cpu, **not** in the pinned H38 vLLM v0.29 installation on DGX Spark. It does not prove actual H38 TorchDispatchMode events, loader callback counts, 512-expert completeness or wrong postload timing. It also shows that claiming indexed assignment can never be counted would be incorrect for at least this separate PyTorch stack. In H38, live scale CopyCounter credit and destination uniqueness remain UNVERIFIED, and no in-image torch CPU probe is approved yet.

Canonical, reproducible operations and scoped output: scripts/benchmark/evidence/h38-ct-copycounter-indexed-write-external-cpu-toy-20261011.md. The operator-installed CT source and input-scale attribute source PASS results remain separate and authoritative only for their syntax. PR #259 remains Draft/Open and merge blocked; H38 image/checkpoint/GPU/model/host protection unchanged. No new DGX execution is required merely to document this external synthetic observation.


## H38 CT expert/shard destination-map source gate — staged 2026-10-11

After the successful installed-image CT eight-parameter source Attempt 03 and input-scale attribute source Attempt 01, the next high-discrimination evidence target is **expert/shard destination identity**, not rerunning the same CT constructor/attribute checks. A new Python **stdlib AST-only** source inspector and protected runc wrapper were staged in PR #259:

- scripts/benchmark/inspect-h38-ct-expert-destination-source.py: requires the four previously qualified pinned H38 CT/RoutedExperts/Layerwise/meta SHA256 digests; emits source-branch predicates for get_expert_mapping/include_fused name matching, global-to-local expert mapping, nonlocal skip, conditional global scale, fused checkpoint handling, w13 first/second projection halves, w2 copies, grouped/tensor-scale dispatch and input-scale generic row vs ModelOpt-specific index-write branches. Also emits an eight-parameter source-conditioned destination hypothesis table.
- scripts/benchmark/check-h38-ct-expert-destination-source.sh: clean exact Git HEAD, fixed H38 image ID/H11-H12-H38 label gates, no network/no pull/no GPU, read-only unprivileged runc with CPU/memory/PID limits, and final image-ID comparison.
- tests/test_h38_ct_expert_destination_source.py: stdlib-only fake-source positive and negative tests for missing routing/callback, expert-id map, nonlocal skip, fused split, w1/w3 tensor-scale indices, input row write, separate ModelOpt path, projection-half displacement, and pinned digest failure.
- scripts/benchmark/evidence/orcarouter-h38-ct-expert-destination-source-plan-20261011.md: canonical planned source-only gate and evidence boundaries.

A critical conditional: the generic input-scale helper source writes param_data[expert_id] = loaded_weight while the per-tensor global-weight-scale helper has distinct w1/w3 indices; a ModelOpt-specific branch may instead write per-shard input cells. **This is only static control-flow syntax.** Actual H38 quant method, shape compatibility, input-scale equality checks, global/local expert resolution, TP slicing, checkpoint name mapping, occurrence count, and unique destination coverage remain UNVERIFIED. In particular, the existence of a generic row-write site is NOT proof of a repeated or successful row write in real H38.

**Status: SOURCE INSPECTOR/TINY TESTS STAGED; exact image execution PENDING.** A future H38_CT_EXPERT_DESTINATION_PREFLIGHT=PASS_SOURCE_BRANCHES_ONLY can qualify only those pinned source branch anchors, not actual loading, CopyCounter credit, layer 8/11 metadata order/buffer lifetime, functional startup or a finite memory peak. Existing CT_INSTALLED_SOURCE_CONTRACT=PASS_SOURCE_CONTRACT_ONLY; CT_SCALE_ATTR_SOURCE_SITES=PASS_SOURCE_SITES_ONLY; CT_WEIGHT_COMPLETENESS=UNVERIFIED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; GPU_MODEL_RERUN=BLOCKED; HOST_PROTECTION=UNCHANGED; CT_META_PATCH=BLOCKED; PR_259=DRAFT_OPEN; MERGE=BLOCKED.


## H38 CT Expert/Shard Destination — actual DGX operator Attempt 01 PASS (2026-10-11)

**This authoritative observation supersedes the earlier staged/PENDING expert-destination entry above, without extending its qualification to runtime loading.** On the clean exact Git checkout fd4221b5bdb2b95ad83f94255ee2740cea842c9e (fast-forwarded from 1865521) the operator executed the dedicated no-GPU/no-checkpoint/no-model guarded image-source audit. It reported H38_CT_EXPERT_DESTINATION_SOURCE=PASS_SOURCE_BRANCHES_ONLY; H38_CT_EXPERT_DESTINATION_PREFLIGHT=PASS_SOURCE_BRANCHES_ONLY; source_check_rc=0; image_identity_unchanged=YES; gpu_or_model_load=NO; checkpoint_payload_read=NO; managed_service_mutation=NO; host_protection_changed=NO; ct_meta_patch_implemented=NO.

All **29/29 AST source predicates** passed: 11 expert-name/global-to-local mapping, fused/full, callback/nonlocal/global-scale branches; 7 packed/group source destinations and w13 first/second halves; 11 input/TENSOR scale branches, including general full-row input assignment vs ModelOpt-specific per-index assignment and the compressed input-scale conflict-check source site. All four pre-pinned CT/RoutedExperts/layerwise/meta source SHA256 values matched the unmodified H38 image sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc.

**Source branching is not event coverage.** The installed image may take different branches depending on actual input/fused checkpoint naming, expert parallel mapping, optional global scale, model backend/quant method, TP dimensions and values. The output specifically retains real_checkpoint_name_to_parameter_matches, real_expert_id_mapping, real_copy_dispatch_numel, unique_real_destination_coverage, actual_input_scale_values_or_conflict, and layer_8_11_shard_revisit_or_buffer_lifetime as UNVERIFIED. No actual H38 torch import, model/GPU, checkpoint payload reading, memory peak, 512-expert copy trace or host stability test occurred.

**Separate conditional source risk**, not a model error observation: in the image-SHA-identical RoutedExperts source, the compressed input-scale conflict-check predicate can attempt Python boolean evaluation of param.data[expert_id] != 1. For a 2-element w13 input-scale row and if that branch is executed, this raises a potential ambiguous multi-element Tensor truth-value concern. The branch condition and exact H38 runtime shape/expert/method must be established before treating this as a defect. PR #259 source-crosscheck discussion comment 6105299781 retains that distinction.

Canonical newly observed evidence: scripts/benchmark/evidence/orcarouter-h38-ct-expert-destination-attempt01-source-pass-20261011.md. Operator console transcript is source; /tmp/h38-ct-expert-destination-attempt01-20261011.txt itself and its SHA256 have not been independently copied/hashed. The previous exact H38 CT registration Attempt 03 PASS_SOURCE_CONTRACT_ONLY and input-scale attribute Attempt 01 PASS_SOURCE_SITES_ONLY remain separate, successful bounded source-only gates.

Current gates: CT_INSTALLED_SOURCE_CONTRACT=PASS_SOURCE_CONTRACT_ONLY; CT_SCALE_ATTR_SOURCE_SITES=PASS_SOURCE_SITES_ONLY; CT_EXPERT_DESTINATION_SOURCE_BRANCHES=PASS_SOURCE_BRANCHES_ONLY; CT_REAL_DESTINATION_COVERAGE=UNVERIFIED; CT_COPYCOUNTER_SCALE_CREDIT=UNVERIFIED; SHARD_8_11_COMPLETENESS=UNVERIFIED; PEAK_BUFFER_BYTES=UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE=FAIL; FUNCTIONAL=NOT_REACHED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; GPU_MODEL_RERUN=BLOCKED; CT_META_PATCH=BLOCKED; HOST_PROTECTION=UNCHANGED; PR_259=DRAFT_OPEN; MERGE=BLOCKED.

Next bounded engineering gate: review existing checkpoint metadata-only inventory tooling and qualification before deriving a real key-to-expert/shard/parameter mapping. Design synthetic fixture coverage before any additional DGX action; do not assume source-only PASS proves actual coverage or justifies GPU/model loading.


## H38 OrcaRouter CT 48×512×9 checkpoint KEY mapping — index-only stage (2026-10-11)

**Next bounded gate after the exact-image Expert Destination source Attempt 01 PASS_SOURCE_BRANCHES_ONLY**: reconcile real checkpoint key names and shard owners with the six CT packed/group/global-weight-scale registration families identified in pinned H38 source. Do not repeat the prior 18-file safetensors full-header order scan: the previous validated header-only Attempt 03 already established 17 numbered base shards + 1 MTP, 223,046 indexed keys, 221,186 routed-classified keys including 2 in MTP, 48 base layers, and base layer 8 numbered shard 4→5 / layer 11 5→6, with strict ORDER_GATE=FAIL. This source/header provenance is documented in scripts/benchmark/evidence/orcarouter-h38-checkpoint-metadata-order-attempt03-revisit-ownership-20261009.md.

The new pure-stdlib scripts/benchmark/inspect-h38-ct-checkpoint-key-map.py reuses the existing metadata inspector's resolve_shards() shard/index guard, then reads **only model.safetensors.index.json** as JSON names→filenames. It does NOT call scan_checkpoint(), safetensors.safe_open(), read_header(), get_tensor(), torch or vLLM. The protected runner scripts/benchmark/check-h38-ct-checkpoint-key-map.sh mounts checkpoint and both inspectors read-only in immutable, image-ID-pinned unprivileged no-GPU/no-network/no-model runc with <=1GiB memory, <=1CPU, 64MiB private tmpfs, and clean exact Git HEAD guard. Tests/test_h38_ct_checkpoint_key_map.py provides 11 positive/fail-closed synthetic cases.

The source-driven **candidate** schema contains exactly nine names per expert: (gate_proj, up_proj, down_proj) × (weight, weight_scale, weight_global_scale) for a hypothesized 48 layers × 512 experts = 221,184 base routed keys. The earlier indexed routed count was 221,186 including 2 MTP classifier keys, but **the new 9-key grid has NOT yet been compared to the real index**. Code gates missing or unexpected names, semantic duplicate slots, expert-ID/layer bounds and reports per-shard splits without claiming real callbacks.

These 9 checkpoint name categories map conditionally to only **SIX** of the **EIGHT** H38 CT registration families: w13/w2_weight_packed, w13/w2_weight_scale and w13/w2_weight_global_scale. The two input-global-scale registrations w13_input_global_scale and w2_input_global_scale have **NO proved corresponding checkpoint key or initialization contract** under this schema. Even if the 9-key metadata grid passes, input scale data sourcing and actual loader results remain UNVERIFIED.

Canonical implementation/qualification and planned operator gate: scripts/benchmark/evidence/orcarouter-h38-ct-checkpoint-key-map-plan-20261011.md. The new real checkpoint **INDEX-ONLY** operator result is PENDING; do not claim that repo CI or old header-only metadata ORDER_GATE=FAIL is its result. A possible PASS_BASE_KEY_SCHEMA_ONLY concerns index names, not runtime element coverage; FAIL_KEY_SCHEMA is a classifier mismatch, not proof of corrupt checkpoint. The earlier ORDER_GATE=FAIL remains unchanged.

Gates remain CT_INSTALLED_SOURCE_CONTRACT=PASS_SOURCE_CONTRACT_ONLY; CT_SCALE_ATTR_SOURCE_SITES=PASS_SOURCE_SITES_ONLY; CT_EXPERT_DESTINATION_SOURCE_BRANCHES=PASS_SOURCE_BRANCHES_ONLY; CT_REAL_KEY_MAP=UNVERIFIED; CT_INPUT_SCALE_DATA_SOURCE=UNVERIFIED; CT_UNIQUE_DESTINATION_ELEMENT_COVERAGE=UNVERIFIED; CT_COPYCOUNTER_CREDIT=UNVERIFIED; LAYER_8_11_BUFFER_LIFETIME=UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE=FAIL; FUNCTIONAL=NOT_REACHED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; GPU_MODEL_RERUN=BLOCKED; HOST_PROTECTION=UNCHANGED; CT_META_PATCH=BLOCKED; PR_259=DRAFT_OPEN; MERGE=BLOCKED.


## H38 CT checkpoint key-map Attempt 01 — VALID KEY_SCHEMA_FAIL, not checkpoint fault (2026-10-11)

**This actual DGX observation supersedes the previously STAGED/PENDING index-only key-map record above, without changing prior source-only successes or the independent checkpoint ORDER_GATE=FAIL.** At exact clean operator checkout 1ed66b602c55534af432bba404b8eb0e6eb9db0e, fixed unmodified H38 image sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc, the safe index-only script returned H38_CKPT_CT_KEY_MAP_GATE=FAIL_KEY_SCHEMA, H38_CKPT_CT_KEY_MAP_PREFLIGHT=KEY_SCHEMA_FAIL, key_map_rc=3 and image_identity_unchanged=YES. It reported no tensor payload/header re-read, GPU or model execution.

Root cause is **a real checkpoint key naming mismatch against our analyzer's original assumption**, NOT observed missing packed checkpoint weights: actual keys are gate_proj/up_proj/down_proj.weight_packed; the analyzer originally required *.weight. Thus 73,728 (48 layers ×512 experts ×3 projections) packed-weight candidate keys were unclassified and also marked missing slots, showing incomplete_expert_grid_count=24,576 under the outdated schema. All four group/global scale categories had recognized counts (w13: 49,152 per scale family; w2: 24,576 per scale family). Total candidate base keys=221,184 and indexed total=223,046 across 18 shards; 31 keys have mtp. namespace. The observed index SHA256 is 188d5905df195dd2dca4dbf2f9c029bb79328d0c85fd9772d73f72d881561866. Crucially, indexed key names containing input_scale or input_global_scale=**0**, so the two input-global-scale CT parameter initialization/source questions remain UNVERIFIED, not "initialized".

13 (layer, expert) metadata key groups have multiple shard owners, including layer 8/expert 235 shards 4→5 and layer 11/expert 409 shards 5→6. The earlier per-shard counts in this incomplete parser covered only **3,072 recognized scale keys/layer**, not complete 4,608-key distributions. Neither key indices nor source branch ASTs establish live callback count, copied numel, destination completeness, shard buffer release or host safety.

The checker has been narrowly corrected to require the observed `weight_packed` suffix, and synthetic fail-closed tests now cover production-scale **hypothetical** 48×512×9 nine-slot grids, rejection of unsuffixed `weight`, scale omissions and unknown mappings. **Attempt 01 is permanently FAIL_KEY_SCHEMA**; real Attempt 02 against the new exact CI-qualified Git SHA is pending. Do not claim that new fixture PASS closes it. Canonical immutable result scripts/benchmark/evidence/orcarouter-h38-ct-checkpoint-key-map-attempt01-schema-fail-20261011.md. The original pre-correction operator /tmp log was not independently acquired or byte-hashed; provenance is the provided terminal transcript.

Current gates: CT_CHECKPOINT_KEY_MAP_ATTEMPT01=FAIL_KEY_SCHEMA; CT_INSTALLED_SOURCE_CONTRACT=PASS_SOURCE_CONTRACT_ONLY; CT_SCALE_ATTR_SOURCE_SITES=PASS_SOURCE_SITES_ONLY; CT_EXPERT_DESTINATION_BRANCHES=PASS_SOURCE_BRANCHES_ONLY; REAL_CHECKPOINT_CT_KEY_GRID=UNVERIFIED; CT_INPUT_SCALE_DATA_SOURCE=UNVERIFIED; CT_WEIGHT_COMPLETENESS=UNVERIFIED; CT_COPYCOUNTER_CREDIT=UNVERIFIED; LAYER_8_11_BUFFER_LIFETIME=UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE=FAIL; FUNCTIONAL=NOT_REACHED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; GPU_MODEL_RERUN=BLOCKED; HOST_PROTECTION=UNCHANGED; CT_META_PATCH=BLOCKED; PR_259=DRAFT_OPEN; MERGE=BLOCKED.


## H38 CT checkpoint key-map — real DGX Attempt 02 PASS_BASE_KEY_SCHEMA_ONLY (2026-10-11)

**This is the latest authoritative INDEX-ONLY key-name outcome, superseding earlier statements that Attempt 02 was PENDING.** The original Attempt 01 at source HEAD 1ed66b602c55534af432bba404b8eb0e6eb9db0e remains **FAIL_KEY_SCHEMA/rc3 as historical checker mismatch** (it incorrectly expected unsuffixed *.weight keys). The updated, CI-qualified checker was executed on clean exact HEAD **2426b9a9ac4234865176fc12c5e34a79d0bbfd1d** with the same immutable H38 image sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc, and the same checkpoint index SHA256 **188d5905df195dd2dca4dbf2f9c029bb79328d0c85fd9772d73f72d881561866**.

Actual operator output: H38_CKPT_CT_KEY_MAP_GATE=PASS_BASE_KEY_SCHEMA_ONLY; H38_CKPT_CT_KEY_MAP_PREFLIGHT=PASS_BASE_KEY_SCHEMA_ONLY; key_map_rc=0; image_identity_unchanged=YES; tensor_payload_read=NO; headers_reread=NO; model_or_gpu_load=NO; managed_service_mutation=NO; monitor_protection_changed=NO; meta_w13_patch_implemented=NO.

All **48 base routed layers × 512 experts × 9 index name slots = 221,184** are present under explicit gate_proj/up_proj/down_proj × weight_packed/weight_scale/weight_global_scale classifier: incomplete_expert_grid_count=0, missing_canonical_slot_count=0, no unclassified base routed key samples, no duplicate semantic slot samples and no out-of-range samples. Candidate CT key family counts: w13_weight_packed=49,152; w2_weight_packed=24,576; w13_weight_scale=49,152; w2_weight_scale=24,576; w13_weight_global_scale=49,152; w2_weight_global_scale=24,576. **These are checkpoint index names, not observed parameter callback/data loading.**

Full layer 8 index key file counts are shard4=2,119 and shard5=2,489 (4,608); layer 11 shard5=3,685 and shard6=923 (4,608). **13** candidate (layer, expert) pairs have indexed keys in multiple files; only **12** bounded samples were printed. Total index entries 223,046 across 18 files (17 numbered + 1 auxiliary MTP). The simple mtp. namespace count is **31**; that does not conflict with the previous independent analyzer's two MTP routed-classified keys, because the two counts use distinct predicates.

**Critical qualification:** There are **ZERO** checkpoint index key names containing 'input_scale' or 'input_global_scale'. This provides no evidence that the two registered H38 CT input-global-scale parameters have valid initialization or values. The passed 9-key index grid corresponds conditionally to only **6 of 8 CT registered parameter families**. Real global→local expert mapping, `weight_loader` callbacks, TorchDispatchMode/CopyCounter credit, unique copied destination elements, input scales, shard 8/11 runtime replay/buffer release and peak bytes all remain UNVERIFIED. The earlier strict CHECKPOINT_METADATA_ORDER_GATE remains **FAIL**, not corrected by index-name completeness.

Canonical genuine operator evidence: scripts/benchmark/evidence/orcarouter-h38-ct-checkpoint-key-map-attempt02-index-pass-20261011.md. The original /tmp logfile SHA256 is not independently established; provenance is the provided terminal transcript. Prior actual source-only gates (8 CT registrations, input-scale postconstruction source, 29 expert destination branch predicates) still have bounded SOURCE_ONLY PASS classifications. Prior external tiny PyTorch CPU toy is not H38 runtime qualification.

Current gates: CT_CHECKPOINT_KEY_MAP_ATTEMPT01=FAIL_KEY_SCHEMA [HISTORICAL]; CT_CHECKPOINT_KEY_MAP_ATTEMPT02=PASS_BASE_KEY_SCHEMA_ONLY; CT_INPUT_SCALE_DATA_SOURCE=UNVERIFIED; CT_EFFECTIVE_LOADER_CALLBACKS=UNVERIFIED; CT_UNIQUE_DESTINATION_ELEMENT_COVERAGE=UNVERIFIED; CT_COPYCOUNTER_SCALE_CREDIT=UNVERIFIED; CT_WEIGHT_COMPLETENESS=UNVERIFIED; SHARD_8_11_BUFFER_LIFETIME=UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE=FAIL; FUNCTIONAL=NOT_REACHED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; GPU_MODEL_RERUN=BLOCKED; HOST_PROTECTION=UNCHANGED; CT_META_PATCH=BLOCKED; PR_259=DRAFT_OPEN; MERGE=BLOCKED.

**Next:** avoid repeating a completed index grid audit. Trace installed H38 CT source handling of two input-global-scale parameters and whether defaults are deterministic vs value-load dependent; separately analyze the 13 cross-shard expert index ownership cases and any interaction with counted load completion using bounded source-only/synthetic evidence before planning additional DGX actions. No model/GPU, checkpoint tensor payload, host-defense relaxation, image rebuild, service change or PR Ready/Merge.


## H38 CT input-global-scale lifecycle / Layerwise numel-threshold — next source-only gate STAGED (2026-10-11)

After the genuine index-only checkpoint key-map Attempt 02 PASS_BASE_KEY_SCHEMA_ONLY (221,184/221,184 base routed keys and zero input_scale-substring names), the next question is **whether the two source-registered input-global-scale Parameters are initialized with effective values and whether cumulative loaded-numel is a safe proxy for unique destination-element completion**. Neither is resolved by the index key PASS.

Staged source-only tools: scripts/benchmark/inspect-h38-ct-input-scale-lifecycle.py, scripts/benchmark/check-h38-ct-input-scale-lifecycle.sh, tests/test_h38_ct_input_scale_lifecycle.py; canonical plan scripts/benchmark/evidence/orcarouter-h38-ct-input-scale-lifecycle-source-plan-20261011.md. They verify four already pinned installed-H38 CT/layerwise/meta/reload-utils source digests; use AST-only Python stdlib; check two plain torch.nn.Parameter(torch.empty(...)) constructor call sites, postconstructor set_weight_attrs, input-global-scale references in CT process_weights_after_loading, and Layerwise make_online_process_loader count-buffer-threshold syntax, with actual source line references and (if present) inverse-divide uses. Guarded read-only unprivileged runc image at exact clean Git HEAD, no network, GPU, model or checkpoint reading; image ID and H11/H12/H38 label gates unchanged.

**No installed-image run of this NEW source-lifecycle audit has occurred yet; repository code and synthetic tests are not a DGX PASS.** Public vLLM v0.29.0 CT has postload reciprocal use of w13/w2_input_global_scale, but public CT and exact installed-H38 CT hashes differ. A future verified source PASS may establish similar syntax in the actual installed image, not effective runtime values, safe defaults, completed CopyCounter events or successful model inference. The direct `torch.empty` allocations have **no explicit constructor fill values**; this is source syntax, not proof of reading undefined values in H38. The index source absence of input-scale keys remains independent actual DGX evidence.

**Layerwise accounting concern:** aggregate `info.load_numel` reaching `info.load_numel_total` is not a source guarantee of unique destination-element coverage if writes overlap or repeated callbacks occur. A bounded external CPU PyTorch synthetic witness established the logical possibility, not a real H38 event. Actual Layerwise closure/counter syntax is the scope of the new source gate, not a model load.

States unchanged: CT_CHECKPOINT_KEY_MAP_ATTEMPT02=PASS_BASE_KEY_SCHEMA_ONLY; CT_INPUT_SCALE_SOURCE_LIFECYCLE=STAGED_NOT_OBSERVED; CT_INPUT_SCALE_EFFECTIVE_VALUES=UNVERIFIED; CT_WEIGHT_COMPLETENESS=UNVERIFIED; CT_COPYCOUNTER_CREDIT=UNVERIFIED; CT_UNIQUE_DESTINATION_COVERAGE=UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE=FAIL; SHARD_8_11_BUFFER_LIFETIME=UNVERIFIED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; GPU_MODEL_RERUN=BLOCKED; HOST_PROTECTION=UNCHANGED; CT_META_PATCH=BLOCKED; PR_259=DRAFT_OPEN; MERGE=BLOCKED.

## H38 input-global-scale source lifecycle — actual DGX Attempt 01 PASS_SOURCE_ONLY (2026-10-11)

**This observed installed-image result supersedes the earlier STAGED/PENDING lifecycle source audit above**, without qualifying actual tensor values or real model loading. Operator ran exact clean checkout **5456809ab701dd38ef947afdc15bc88a32b22a13**, fixed H38 image sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc. Result: H38_CT_INPUT_SCALE_LIFECYCLE=PASS_SOURCE_ONLY; H38_CT_INPUT_SCALE_LIFECYCLE_PREFLIGHT=PASS_SOURCE_ONLY; source_check_rc=0; image_identity_unchanged=YES; gpu_or_model_load=NO; checkpoint_payload_read=NO; managed_service_mutation=NO; host_protection_changed=NO; ct_meta_patch_implemented=NO. Four previously pinned CT/layerwise/meta/reload-utils SHA256 files matched.

The exact installed H38 CT source has **w13_input_global_scale** torch.nn.Parameter(torch.empty(...)) constructor at line 179, registration at 183, set_weight_attrs at 187 and postload inverse division **1.0 / layer.w13_input_global_scale at line 238**. **w2_input_global_scale** analogously constructor at 189, registration 192, setter 196 and inverse division **1.0 / layer.w2_input_global_scale at 242**. Both constructors have **no explicit fill value and no explicit device**. Reported source_or_runtime_default_proven=NO means **the source inspector found no proven default**, not that every possible later initialization or alternate source has been excluded. effective_initial_value, actual_postload_invocation, checkpoint_load_event_for_this_parameter and effective_input_scale_values remain UNVERIFIED. Prior actual index-only checkpoint key-map Attempt02 showed zero input_scale-substring names among 223,046 indexed names; this does not establish that these parameters are invalid or uninitialized at runtime.

Installed Layerwise make_online_process_loader (line 149) passed **5/5 AST anchors**: buffer input arguments, get_numel_loaded(original_loader, bound_args), info.load_numel += num_loaded, threshold info.load_numel >= info.load_numel_total, and _layerwise_process invocation. This source supports the distinction between accumulated copy credit and unique Tensor destination coverage; it does **not** prove repeats, early completion or failed actual model loading.

Canonical independent observation scripts/benchmark/evidence/orcarouter-h38-ct-input-scale-lifecycle-attempt01-source-pass-20261011.md transcribes the supplied console output; the original /tmp/h38-ct-input-scale-lifecycle-attempt01-20261011.txt has not been separately byte-hashed. The earlier checkpoint key-map Attempt01 FAIL_KEY_SCHEMA stays historically immutable; Attempt02 PASS_BASE_KEY_SCHEMA_ONLY and CHECKPOINT_METADATA_ORDER_GATE=FAIL are independent.

Gate vector: CT_INPUT_SCALE_LIFECYCLE_SOURCE_ATTEMPT01=PASS_SOURCE_ONLY; CT_INPUT_SCALE_EFFECTIVE_VALUES=UNVERIFIED; CT_INPUT_SCALE_DEFAULT_GUARANTEE=UNVERIFIED; CT_INPUT_SCALE_ACTUAL_LOADER_EVENT=UNVERIFIED; CT_REAL_WEIGHT_COMPLETENESS=UNVERIFIED; CT_COPYCOUNTER_CREDIT=UNVERIFIED; CT_UNIQUE_DESTINATION_COVERAGE=UNVERIFIED; SHARD_8_11_BUFFER_LIFETIME=UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE=FAIL; FUNCTIONAL=NOT_REACHED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; GPU_MODEL_RERUN=BLOCKED; HOST_PROTECTION=UNCHANGED; CT_META_PATCH=BLOCKED; PR_259=DRAFT_OPEN; MERGE=BLOCKED.

**Next:** bounded source-only investigation of whether any deterministic default, alias or alternate-name loader write supplies both input scales *before* the postload inverse, retaining unresolved cases; separately prove whether counted numel can be connected to real per-expert unique destination events. No checkpoint payload, H38 torch/model/GPU, image rebuild, host protection/service mutation, CT meta patch or PR Ready/Merge.

## H38 CT input-global-scale counted-numel target — source-only inspector STAGED (2026-10-11)

The actual pinned H38 input-global-scale lifecycle source inspection **PASS_SOURCE_ONLY** and actual checkpoint-index 48×512×9 key-grid **PASS_BASE_KEY_SCHEMA_ONLY** are complete independent source/index checks, not a model-load qualification. Installed CT source has two torch.nn.Parameter(torch.empty(...)) input-global-scale registrations and CT postload reciprocal consumers; checkpoint index contains **zero input_scale-substring tensor key names**, while the Layerwise source has a counted-numel completion threshold. Their interaction is the next discriminator, not repeating those earlier PASS inspections.

**New code staged, NOT YET RUN on DGX:** scripts/benchmark/inspect-h38-ct-load-target-input-scale.py, scripts/benchmark/check-h38-ct-load-target-input-scale.sh, tests/test_h38_ct_load_target_input_scale.py. The stdlib-only AST gate requires four previously pinned CT/meta/reload-utils/layerwise source SHA256 values and verifies: skip-list SKIP_LOAD_TENSORS contents, registered input-global-scale shapes, get_layer_tensors(layer) parameter/buffer union, get_layer_size(layer) per-tensor numel and skip predicate, w13_num_shards = 2 if self.moe.is_act_and_mul else 1, Layerwise initialization/late refresh and accumulated >= threshold. The wrapper pins exact clean Git HEAD and original H38 image ID/labels, uses unprivileged no-network read-only runc limited to 512MiB/1CPU/64PIDs, no torch import, checkpoint, GPU/model or host changes. Canonical next-gate plan scripts/benchmark/evidence/orcarouter-h38-ct-input-scale-numel-target-source-plan-20261011.md.

**Illustrative source arithmetic ONLY** if actual num_experts=512, registrations exist when get_layer_size runs and input-global-scale names are not skipped: per-layer input-scale target contribution is 512×(w13_num_shards+1), hence 1,536 if w13_num_shards=2 or 1,024 if w13_num_shards=1. Across 48 independent layers this is 73,728 or 49,152 respectively. The real runtime layer's physical/local expert count and exact branch, input-scale callbacks, copied numel, initialization, unique destination coverage and any real threshold deficit are **UNVERIFIED**. Do not report these numbers as measured missing elements or a memory allocation peak.

Current gates: CT_INPUT_SCALE_LIFECYCLE_SOURCE_ATTEMPT01=PASS_SOURCE_ONLY; CT_CHECKPOINT_KEY_MAP_ATTEMPT02=PASS_BASE_KEY_SCHEMA_ONLY; CT_INPUT_SCALE_TARGET_SOURCE=STAGED_NOT_OBSERVED; CT_INPUT_SCALE_EFFECTIVE_VALUES=UNVERIFIED; CT_REAL_LOAD_NUMEL_DEFICIT=UNVERIFIED; CT_COPYCOUNTER_CREDIT=UNVERIFIED; CT_UNIQUE_DESTINATION_COVERAGE=UNVERIFIED; SHARD_8_11_BUFFER_LIFETIME=UNVERIFIED; CHECKPOINT_METADATA_ORDER_GATE=FAIL; FUNCTIONAL=NOT_REACHED; HOST_STABILITY=INCONCLUSIVE; RM_MITIGATION=UNPROVEN; GPU_MODEL_RERUN=BLOCKED; HOST_PROTECTION=UNCHANGED; CT_META_PATCH=BLOCKED; PR_259=DRAFT_OPEN; MERGE=BLOCKED. No image rebuild, checkpoint payload reads, H38 torch/model/GPU, managed service/host protection changes or PR Ready/Merge.

## H38 CT Input-scale numel-target contribution — real DGX source Attempt 01 PASS (2026-10-12)

**This actual, operator-supplied exact-image SOURCE-ONLY result supersedes the previous STAGED_NOT_OBSERVED status for this gate.** On clean DGX checkout **956ee0cd2db2a3ca607acd0516d6d35d62f09891**, unchanged fixed H38 image `sha256:412d407c76c55fe4411825f34ea3e843933d6d38780bedacb3e69688dc5e5cdc`, and all four previously pinned installed CT/layerwise/meta/utils SHA256 checks matching, the guarded inspector returned `H38_CT_INPUT_TARGET_GAP=PASS_SOURCE_POTENTIAL_ONLY`, `H38_CT_INPUT_TARGET_GAP_PREFLIGHT=PASS_SOURCE_POTENTIAL_ONLY`, `source_check_rc=0`, `image_identity_unchanged=YES`. It reported `gpu_or_model_load=NO`, `checkpoint_payload_read=NO`, `managed_service_mutation=NO`, `host_protection_changed=NO` and `ct_meta_patch_implemented=NO`.

All **9/9 source predicates** were true: registered parameter/buffer enumeration, no-None check, `get_layer_tensors` parameter/buffer union, `get_layer_size` `tensor.numel()` and SKIP exclusion, Layerwise initial/refresh count target, aggregated increment and `>=` completion predicate. The actual installed `SKIP_LOAD_TENSORS` literal does **not** include `w13_input_global_scale` or `w2_input_global_scale`. The registered source shapes are `(num_experts,w13_num_shards)` and `(num_experts,)` respectively. **Only if** they are registered at `get_layer_size` enumeration time do they contribute a potential `num_experts * (w13_num_shards+1)` elements to its count target. If there were 512 runtime registered expert rows and `is_act_and_mul` is true, the illustrative contribution is 1,536 per layer / 73,728 across 48 layers; otherwise 1,024 / 49,152. These are hypothetical arithmetic bounds under explicitly stated conditions, **NOT actual missing loader credits, source initialization values or measured memory**.

The prior actual input-scale reciprocal-consumer source `PASS_SOURCE_ONLY` and checkpoint-index `PASS_BASE_KEY_SCHEMA_ONLY` (221,184 base key names, 0 index keys containing `input_scale`) remain separate evidence. No actual runtime expert count, alternative input-scale writes/defaults, copied element uniqueness, `CopyCounter` credit, layer8/11 buffer lifetime or postload runtime invocation was established. The historical checkpoint index classifier Attempt01 `FAIL_KEY_SCHEMA` remains immutable; **`CHECKPOINT_METADATA_ORDER_GATE=FAIL`** remains FAIL. Canonical actual-console source evidence: `scripts/benchmark/evidence/orcarouter-h38-ct-input-scale-numel-target-attempt01-source-pass-20261012.md`; original user-reported `/tmp/h38-ct-input-target-gap-attempt01-20261011.txt` not independently byte-hashed.

Current gates: `CT_INPUT_SCALE_LOAD_TARGET_SOURCE_ATTEMPT01=PASS_SOURCE_POTENTIAL_ONLY`; `CT_INPUT_SCALE_LIFECYCLE_SOURCE_ATTEMPT01=PASS_SOURCE_ONLY`; `CT_CHECKPOINT_KEY_MAP_ATTEMPT02=PASS_BASE_KEY_SCHEMA_ONLY`; `CT_INPUT_SCALE_EFFECTIVE_VALUES=UNVERIFIED`; `CT_INPUT_SCALE_ALTERNATE_INITIALIZER=UNVERIFIED`; `CT_ACTUAL_LAYERWISE_TARGET_DEFICIT=UNVERIFIED`; `CT_COPYCOUNTER_CREDIT=UNVERIFIED`; `CT_UNIQUE_DESTINATION_COVERAGE=UNVERIFIED`; `SHARD_8_11_BUFFER_LIFETIME=UNVERIFIED`; `CHECKPOINT_METADATA_ORDER_GATE=FAIL`; `FUNCTIONAL=NOT_REACHED`; `HOST_STABILITY=INCONCLUSIVE`; `RM_MITIGATION=UNPROVEN`; `GPU_MODEL_RERUN=BLOCKED`; `HOST_PROTECTION=UNCHANGED`; `CT_META_PATCH=BLOCKED`; `PR_259=DRAFT_OPEN`; `MERGE=BLOCKED`.

**Next:** do not repeat prior key/source gate runs. Bound one more exact-source-only investigation of alternate initialization/alias/assignment and nuanced CopyCounter source credit; then formally decide whether H38 remains deferred while shifting engineering work to non-destructive installer/uninstaller/profile-switch acceptance. No H38 model/GPU, tensor payload, image rebuild, host/service protection relaxation, CT meta patch or PR Ready/Merge.

## Managed lifecycle acceptance — operator focus after H38 source-only closure (2026-10-12)

**Engineering focus shifts to the installer, uninstaller, and managed model-profile selector/transaction, without promoting H38 runtime.** Canonical acceptance matrix: `docs/MANAGED-LIFECYCLE-ACCEPTANCE.md`. Detailed operator steps remain in `OPERATIONS.md`; the matrix strictly separates simulation/CI from historical live runs, and from currently unqualified live/destructive scenarios.

Implemented (code paths exist): bilingual six-stage fresh install and completed-install management wizard, model registry/listing, selectable OrcaRouter/NVIDIA/mazinb/Hybrid H6 profiles, settings/default refresh, transactional profile switch and recovery, normal/purged uninstall wizard, persistent cumulative asset ownership and dependency-based refusal. `lychee888` remains non-installable. Existing independent test groups include `tests/test_installer_profile_manager.py`, `tests/test_model_profiles.py`, `tests/test_installer_plan_parity.py`, `tests/test_profile_switch_transition.py`, `tests/test_settings_transition.py`, `tests/test_asset_ownership.py`, `tests/test_release_profile_refresh_transition.py`, and `tests/test_operation_lock.py`. **Implementation is not a live all-path qualification.**

New `tests/test_uninstall_wizard_preview.py` runs the actual bilingual `uninstall.sh --dry-run` CLI against disposable HOME/XDG/manifests and verifies normal preserve, selected purge preview, full purge preview and byte-identical model/release/manifest state. A full purge preview without a cumulative registry correctly reports **no registry**; it does not fabricate an owned-asset list. These are synthetic **non-destructive** tests and do not confirm real uninstall would succeed or that live files can be safely deleted. Full live clean-host install→service→doctor→uninstall→reinstall→purge E2E remains NOT QUALIFIED. The historical Hybrid→OrcaRouter→Hybrid switch has a FUNCTIONAL PASS but strict HOST-STABILITY FAIL, not a blanket switch-all-pairs success. mazinb has live readiness but strict RM HOST-STABILITY FAIL; H38 managed runtime stays NOT_REACHED/INCONCLUSIVE and blocked.

The latest real fixed-image Input-scale load-target source Attempt01 `PASS_SOURCE_POTENTIAL_ONLY` already proved nine source predicates on original DGX SHA `956ee0cd2db2a3ca607acd0516d6d35d62f09891`. Do **not** repeat the same H38 source inspection to delay lifecycle work. H38 alternative input-scale default/alias and CopyCounter actual unique coverage remain UNVERIFIED; `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `GPU_MODEL_RERUN=BLOCKED`, `HOST_PROTECTION=UNCHANGED` and `PR_259=DRAFT_OPEN / MERGE=BLOCKED`. No H38 GPU/model, checkpoint payload, image rebuild, CT meta or service/protection change is authorized by lifecycle documentation/tests.

**Next admissible operator gate:** after a fresh CI-qualified exact HEAD, gather **read-only** live inventory via `./install.sh --list-models`, `./install.sh --list-backends`, the four transaction `status` paths and `./scripts/doctor.sh`; avoid real installer/uninstaller execution. This provides an operator state snapshot, not full E2E acceptance. Run destructive full purge only on an independent disposable target after a separate approval and safety preflight, never on the active single Spark.

## Lifecycle acceptance M1 implementation — synthetic wizard previews and read-only snapshot (2026-10-12)

**Latest focus:** staged `docs/MANAGED-LIFECYCLE-ACCEPTANCE.md` separates managed installer/uninstaller/model-switch implementation from CI/disposable-fixture verification, historical Hybrid↔OrcaRouter FUNCTIONAL PASS / strict HOST-STABILITY FAIL, and still-unqualified full live clean-host E2E. `lychee888` remains planned/non-installable. The H38 managed path remains BLOCKED and the independent strict checkpoint metadata ORDER_GATE stays FAIL.

New `tests/test_uninstall_wizard_preview.py` invokes the actual `uninstall.sh --dry-run` CLI in a disposable HOME/XDG with a realistic synthetic installed manifest and sentinel model/release data. Five cases check English/Korean normal-preserve previews, selected model/image/swap purge preview, full-purge preview, no mutation and no need for live Docker/sudo. Full-purge preview with **no** cumulative ownership registry correctly reports an absent registry, NOT an invented owned-asset list; an initial expectation error in the new test was corrected to that exact CLI behavior. **This is synthetic only: no real uninstall or removal was run.**

New `scripts/lifecycle/inspect-readonly-lifecycle.sh` plus `tests/test_managed_lifecycle_readonly_snapshot.py` stage a strictly bounded operator audit requiring a clean exact SHA, and run **only** the model/backend inventory commands, four transaction status queries, and read-only Doctor. Output `MANAGED_LIFECYCLE_READONLY=COLLECTED_READ_ONLY` means **snapshot collection**, never host-stability, full E2E or profile-switch success; individual exit codes and `PARTIAL_CHECK_FAILURE` are retained for issues. This new DGX on-host audit **has not yet been executed**. The uninstaller's `--dry-run` exits before real-operation transaction locks and destructive preflights, so it must not be used as evidence that real purge is eligible. No real purge or full live install is authorized.

Next after CI: operator runs exact-SHA read-only lifecycle snapshot on the existing Spark and returns complete stdout/exit; we then file immutable evidence and close **M1 at the snapshot/simulated level only**. Full M2 destructive install→uninstall→reinstall acceptance must run on a separate disposable host; M3 all-profile live switches remain PARTIAL, M4 H38 BLOCKED. Existing single Spark state/monitor/service must not be disrupted. PR #259 DRAFT_OPEN / MERGE BLOCKED until independent H38 conditions change.

## Managed lifecycle DGX read-only Attempt 01 — PARTIAL_CHECK_FAILURE / Doctor 5 FAIL + 2 WARN (2026-10-12)

**This actual operator DGX result supersedes the earlier "M1 snapshot not yet executed" description above.** On clean exact `feat/h38-managed-integration` HEAD `bbeceaf16c0c4bba4385c38cfead32e5dc243769`, the pinned `scripts/lifecycle/inspect-readonly-lifecycle.sh` reported `MANAGED_LIFECYCLE_READONLY=PARTIAL_CHECK_FAILURE`, `MANAGED_LIFECYCLE_LIVE_E2E=NOT_QUALIFIED`, `lifecycle_audit_rc=3` without host mutation, uninstall/install/purge, GPU or model launch.

**Read-only PASS:** installed and active OrcaRouter model/image; local mazinb + Hybrid H6 model/images installed but inactive; NVIDIA model/image absent (experimental/installable); lychee888 planned/non-installable. Backend vllm stable/installable, sglang planned/non-installable. **Four lifecycle states idle**, with each command rc=0: PROFILE_SWITCH_STATE, TRANSACTION_STATE, UPDATE_STATE and RELEASE_PROFILE_REFRESH_STATE. Doctor passed installation complete, current+previous immutable releases and qualification digest, ownership registry, 18-shard checkpoint/index/config, model mount/name/image consistency, enabled systemd unit, API access sockets, active PLE swap, memory/swap/disk margins and lack of recorded incomplete lifecycle transitions.

**Exactly 5 Doctor FAIL:** (1) `runtime-commit.env` missing **or unsafe**; (2) Docker runtime `exited`; (3) `docker port` returned **no published port**, so loopback-only API check failed; (4) enabled memory monitor `monitor.pid` missing; (5) loopback health endpoint unresponsive. **Exactly 2 WARN:** legacy OrcaRouter image selected, and systemd managed-service unit installed/enabled but **inactive**. Doctor `rc=1`. Several failures plausibly follow from the runtime's stopped/inactive state; their causal order, intentional protective stop vs startup failure, and old/new release provenance are **UNVERIFIED**. Do not recategorize the stopped runtime as a bad port binding, proven memory-protection trip or an H38 startup failure. Real current+previous immutable release ids `ff67bab3c94d6992f61b9535836df97f03b9c022` and `a8aeca47433dc4033b3f1f995eb59023467222ce` passed, respectively. Host point-in-time snapshot: non-CMA available 118 GiB, non-CMA free 80,045 MiB, swap free 143 GiB, model disk 104 GiB; **not an RM-host-stability qualification**.

Canonical actual operator-console evidence: `scripts/benchmark/evidence/managed-lifecycle-readonly-attempt01-doctor-partial-20261012.md`; user-reported `/tmp/managed-lifecycle-readonly-attempt01-20261012.txt` bytes and SHA256 not independently verified. M1 tests/CI `PASS` but **M1 host Doctor FAIL**; no M1 healthy/safe-live approval. M2 destructive install/uninstall/reinstall NOT RUN, M3 complete cross-profile E2E NOT QUALIFIED, M4 H38 managed BLOCKED. Strict H38 `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `FUNCTIONAL=NOT_REACHED`, `HOST_STABILITY=INCONCLUSIVE`, `GPU_MODEL_RERUN=BLOCKED`, `HOST_PROTECTION=UNCHANGED`, `PR_259=DRAFT_OPEN`, `MERGE=BLOCKED` unchanged.

**Next safe discriminator:** staged `scripts/lifecycle/inspect-readonly-runtime-offline.sh` and associated source-only guard tests ask for **stopped container ExitCode/OOMKilled/StartedAt/FinishedAt, declared Docker port bindings, systemd ActiveState/SubState/Result/ExecMainStatus and file type/existence for runtime-commit.env/runtime-stop.env/monitor.pid** on an exact clean CI-qualified SHA. It cannot restart/repair anything; it explicitly retains RUNTIME_STOP_REASON=NOT_YET_PROVEN. Do not start/restart the legacy runtime or H38, edit/delete attestation or stop-marker, force a transition commit, relax monitor, or run destructive purge to clear Doctor failures.

## Managed runtime offline metadata Attempt 01 — exit0, no Docker OOM, correct loopback binding (2026-10-12)

**Actual operator read-only DGX observation supersedes the earlier "offline probe not yet executed" statement.** On clean HEAD `6ce45561640f4069d534cbe04f5064a39095a88a`, `scripts/lifecycle/inspect-readonly-runtime-offline.sh` produced `MANAGED_RUNTIME_OFFLINE=COLLECTED_READ_ONLY`, `offline_diagnostic_rc=0`, `H38_MODEL_GPU_RERUN=BLOCKED`, no runtime/service/protection mutation. Its successful rc means **data collection only**, not healthy model or M1 live acceptance.

Actual Docker state: `exited`, `ExitCode=0`, `OOMKilled=false`, `State.Error=""`, started 2026-10-07 07:35:45.800732164 UTC (**16:35:45 KST**), finished 2026-10-07 13:08:34.847184942 UTC (**22:08:34 KST**). Docker `HostConfig.PortBindings` declared the **correct** loopback-only `8888/tcp → 127.0.0.1:8888`, while runtime `NetworkSettings.Ports={}` because stopped. Earlier Doctor's `no published port` remains a **readiness/active-port check failure**, NOT evidence of misconfigured HostConfig. Systemd `Result=success`, `ExecMainCode=1` (process-exited classification, **not process status 1**), `ExecMainStatus=0`, service `inactive/dead` with ActiveEnterTimestamp **2026-10-07 22:08:29 KST**, InactiveEnterTimestamp **22:18:17 KST**. Container finished ~5.85 seconds after unit active entry, unit became inactive ~9m42s after container finish. These temporal relations **do not identify** the stop requester or intent; `exit_code=0` and no Docker OOM do not prove a safe, intentional/protective, fully stable shutdown.

At this later probe `runtime-commit.env`, `runtime-stop.env`, and `monitor.pid` were **all ABSENT**; the prior Doctor's `missing or unsafe` attestation failure is now narrowed to **currently absent**, without proving historical file write/deletion reasons or whether a transient protective stop ever occurred. The earlier live Doctor **5 FAIL / 2 WARN** classification and `M1_HOST_HEALTH=NOT_QUALIFIED` stand. Strict H38 checkpoint `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `FUNCTIONAL=NOT_REACHED`, `HOST_STABILITY=INCONCLUSIVE`, `RM_MITIGATION=UNPROVEN`, `GPU_MODEL_RERUN=BLOCKED`, `HOST_PROTECTION=UNCHANGED`, `PR_259=DRAFT_OPEN`, `MERGE=BLOCKED` remain.

Immutable source-of-truth actual operator evidence: `scripts/benchmark/evidence/managed-runtime-offline-attempt01-exit0-no-oom-20261012.md`; original user-reported `/tmp/managed-runtime-offline-attempt01-20261012.txt` not separately byte-hashed.

**Next bounded read-only diagnostic:** `scripts/lifecycle/inspect-readonly-runtime-stop-journal.sh` (+ `tests/test_managed_runtime_stop_journal_readonly.py`) requires exact clean SHA, host timezone +0900 and gathers **at most 160** historical `qwen38-flash-next.service` journal lines within Oct 07 **21:55–22:25 KST** only. This journal diagnostic has **NOT yet run on the operator DGX**. It does not start/restart service/container or inspect checkpoint payload/GPU. Keep stop reason NOT_YET_CLASSIFIED if historical log access is unavailable or ambiguous. Do not change host service/monitor, regenerate attestation, run installer/update or restart H38 just to pass Doctor.

## Oct 07 managed-runtime stop: protection-triggered candidate abort CONFIRMED in actual service journal (2026-10-12)

**This actual DGX operator journal supersedes the earlier `RUNTIME_STOP_REASON=NOT_YET_PROVEN` for the managed transition sequence**, not the separate question of *which numeric monitor threshold fired*. Actual guard checkout **`efafe36fcc2e477e9d0cd110e4db275ba40dc489`**, October 7 service journal limited to **21:55–22:25 KST**, `RUNTIME_STOP_JOURNAL=COLLECTED_READ_ONLY`, `journal_audit_rc=0`, no host/service/protection/GPU/model mutation. The inspector's own `RUNTIME_STOP_CAUSE=NOT_YET_CLASSIFIED` is a deliberately static output marker; **human reading of the actual recorded messages supplies the following independent evidence classification**:

- Immediately before replacement, the **previous** managed vLLM answered HTTP 200 for `/health`, `/v1/models` and chat completions through about **22:08:29 KST**. This proves observed pre-transition endpoint responses, NOT the candidate's readiness or full functional correctness.
- **22:08:29.818**: `Managed service stop: no runtime attestation; preserving any canonical container.` Then `preflight-start`, transition recovery idle, **22:08:30.019** `Stopping current runtime container gracefully: qwen38-flash-next`; **22:08:35.049** transition prepared `previous=1`.
- **22:08:35.485**: new OrcaRouter candidate started with `executor=mp, PLE=mmap, SPEC=mtp k=2, qsa_exact_topk=1`; **memory monitor started (`protect=1`, pid 3127696)** and its log location announced `/home/inlc/.local/state/qwen38-spark/monitor.log`. These are startup assertions, not candidate READY.
- **22:08:35–22:17:26**: `candidate-validating`, readiness waiting through `540/1800 seconds`.
- **22:18:16.743**: exact journal `Candidate runtime was stopped by memory protection during startup; leaving managed runtime stopped.`; **22:18:17.125** `Previous runtime container restored but left stopped after memory protection.`; **22:18:17.125895** `Runtime transition aborted by memory protection (state=idle).` A following unit stop handler said no runtime attestation and preserved any canonical container.

**Thus the managed transition aborted due to a recorded memory-protection candidate stop, and previous runtime was purposefully restored-but-left-stopped.** This directly explains the earlier offline canonical-container `ExitCode=0`, Docker `OOMKilled=false`, systemd inactive/Result=success and the Doctor's unresponsive API; it does NOT prove the candidate's ExitCode or establish a true host/kernel OOM. The existing Docker `HostConfig.PortBindings` loopback `127.0.0.1:8888` was correctly configured and stopped runtime port publication absence remains a readiness failure, not a port-configuration bug.

**Still unknown:** which numeric `monitor-runtime` predicate fired (low non-CMA free + low available, low free + 256MiB-or-more swap growth, or critically low swap free); whether protection was a *false-positive* on normal cold load; actual NVIDIA RM host stability; historical marker cleanup. The current monitor source documents this heuristic but does not supply Oct07 exact samples/configuration. Original journal logfile `/tmp/managed-runtime-stop-journal-attempt01-20261012.txt` is only user-reported, not independently hashed. Canonical source-backed evidence: `scripts/benchmark/evidence/managed-runtime-stop-journal-attempt01-protected-abort-20261012.md`.

**One final strictly bounded optional clarification:** new `scripts/lifecycle/inspect-readonly-monitor-trigger.sh` and `tests/test_managed_monitor_trigger_readonly.py`, exact clean Git SHA, select Oct07 **22:08–22:19 KST** structured monitor numeric lines only (≤120 lines; local log must be regular and ≤64MiB). No service/GPU/host mutation; inspect numeric trigger without dumping embedded Docker prompts/tokens. The operator has **NOT YET** run this monitor-only probe. If log absent, too large, or inconclusive, **stop further recursive H38 diagnostics** and retain trigger UNKNOWN. Continue installer/uninstaller/model-switch M1–M3 **non-destructive** acceptance independently.

Gates: `MANAGED_TRANSITION_CANDIDATE_PROTECTION_ABORT=CONFIRMED_BY_JOURNAL`; `MANAGED_TRANSITION_PREVIOUS_RESTORED_STOPPED=CONFIRMED_BY_JOURNAL`; `MONITOR_TRIGGER_PREDICATE=UNVERIFIED`; `MONITOR_FALSE_POSITIVE=UNVERIFIED`; `M1_HOST_HEALTH=NOT_QUALIFIED`; `M2_DESTRUCTIVE_E2E=NOT_RUN`; `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`; `M4_H38=BLOCKED`; `CHECKPOINT_METADATA_ORDER_GATE=FAIL`; `HOST_STABILITY=INCONCLUSIVE`; `RM_MITIGATION=UNPROVEN`; `GPU_MODEL_RERUN=BLOCKED`; `HOST_PROTECTION=UNCHANGED`; `PR_259=DRAFT_OPEN`; `MERGE=BLOCKED`. No image rebuild, actual H38 model/GPU, host protection/service changes, synthetic success promoted to host readiness, attestation re-creation, PR Ready or Merge.

## Managed candidate memory-protection Oct07 numeric trigger — actual DGX source evidence VERIFIED (2026-10-12)

**This operator-recorded DGX monitor result supersedes the earlier `MONITOR_TRIGGER_PREDICATE=UNVERIFIED` and "numeric probe not yet run" status in historical sections above**, but it does not resolve **whether the monitor's heuristic was appropriately calibrated** for cold loading or guarantee actual NVIDIA RM host stability. The bounded read-only inspector ran on exact clean HEAD `7e4580bdca4054a788715bdf141e006bbb6b3f59`, selected **17** actual Oct07 monitor messages from a **2,242,582-byte** readable source file, and returned `MONITOR_TRIGGER_READONLY=COLLECTED_READ_ONLY`, `monitor_audit_rc=0`. No runtime/model/GPU, checkpoint payload, managed service, host-protection setting or local state was altered. Canonical source data: `scripts/benchmark/evidence/managed-monitor-trigger-attempt01-low-free-swap-growth-pass-20261012.md`; the original reported `/tmp/managed-monitor-trigger-attempt01-20261012.txt` was **not independently hashed**.

**Actual monitored threshold configuration, not assumed defaults:** At **2026-10-07 22:08:35 KST** the new OrcaRouter candidate monitor announced `mode=protect available-warn=6GiB noncma-free=2GiB free-gate=10GiB swap-growth=256MiB swapfree=8GiB`. It logged healthy heartbeats through **22:16:40** and then:
- **22:17:33**: non-CMA free **2,017 MiB < 2,048 MiB**, swapgrowth **17 MiB < 256 MiB**, non-CMA available **26,022 MiB > 10GiB**, swapfree **146,470 MiB > 8GiB** → `protect=0/5` (warning but no protection count).
- **22:17:35**: non-CMA free **1,151 MiB**, swapgrowth **654 MiB** → **`protect=1/5`**. Following ~2-second samples **22:17:37 (2/5)**, **22:17:39 (3/5)**, **22:17:41 (4/5)** and **22:17:43 (5/5)** kept non-CMA free below 2GiB and swapgrowth above 256MiB, while non-CMA available remained ~27–30GiB and swapfree ~140GiB.
- **22:17:43**: monitor explicitly logged `PROTECT stopping qwen38-flash-next gracefully to preserve host stability`. **The triggered branch is low immediate non-CMA free AND sustained swap consumption after monitor start** (consecutive=5), **not** the low-available threshold and **not** critically low SwapFree. The service journal subsequently recorded **22:18:16** the candidate protected abort and **22:18:17** restored-but-stopped old runtime and aborted transition `state=idle`.

This confirms **intended monitor policy logic ran on recorded counter values**, not that the policy's classification was necessarily right for cold-loading PLE/mmap/model behavior. Candidate `Ready`, kernel OOM, NVIDIA `NV_ERR_NO_MEMORY`, exact impact without protection, and false-positive vs correctly protective cutoff remain **UNVERIFIED**. Earlier Docker `ExitCode=0 OOMKilled=false` was the intentionally stopped **previous** canonical runtime, not evidence of candidate success.

**Lifecycle workstream handoff is NOW APPROPRIATE.** No further live H38 source/journal experiments for this issue are requested. Maintain `M1_HOST_HEALTH=NOT_QUALIFIED` from actual Doctor **5 FAIL/2 WARN**; the historical stopped state is explained, not repaired. Continue **M1 synthetic/CLI wizard and ownership-safe cancellation/recovery acceptance**, **M2 independent disposable-host destructive E2E design (NOT_RUN)** and **M3 profile-switch all-pairs simulation (NOT_QUALIFIED)**. H38 `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `FUNCTIONAL=NOT_REACHED`, `HOST_STABILITY=INCONCLUSIVE`, `RM_MITIGATION=UNPROVEN`, `GPU_MODEL_RERUN=BLOCKED`, `HOST_PROTECTION=UNCHANGED`, `CT_META_PATCH=BLOCKED`, `PR_259=DRAFT_OPEN`, `MERGE=BLOCKED`. Do **not** restart a candidate to fix Doctor, relax monitoring, create missing attestation or purge assets on the single active Spark.

New vector: `MONITOR_TRIGGER_SOURCE=PASS_ACTUAL_LOW_FREE_AND_SWAP_GROWTH`; `MONITOR_TRIGGER_CONSECUTIVE=5/5_CONFIRMED`; `MONITOR_POLICY_FALSE_POSITIVE=UNVERIFIED`; `MONITOR_REAL_HOST_OOM=UNVERIFIED`; `M1_HOST_HEALTH=NOT_QUALIFIED`; `GPU_MODEL_RERUN=BLOCKED`.


## Early swap-ownership refusal for destructive uninstall (2026-10-12)

**Safety contract:** `uninstall.sh --purge-swap` and `--purge-all` (which implies swap purge) now reject a manifest with `SWAP_OWNED!=1` **after dry-run preview but before** acquiring the operation lock, bootstrapping asset ownership, stopping Docker/systemd, or deleting any installer data. The former check was positioned after teardown and, for full purge, after owned asset removal; an unowned swap could therefore leave a partially uninstalled deployment before refusing. `--dry-run` remains preview-only and does not certify real purge eligibility.

`tests/test_uninstall_wizard_preview.py::test_unowned_swap_purge_fails_before_host_or_fixture_mutation` exercises the real CLI on disposable HOME/XDG state for selected swap and full purge with daemon-command denial stubs and byte-for-byte fixture preservation. This is a **synthetic fail-closed regression**, not an authorized live DGX uninstall. M2 destructive E2E remains NOT_RUN; M1 actual host Doctor remains NOT_QUALIFIED and H38 runtime remains BLOCKED. PR #259 remains Draft/Open, merge blocked.


## Uninstall final-consent cancellation is read-only before lock/bootstrap (2026-10-12)

The real `uninstall.sh` previously ran `asset_bootstrap_install` and destructive-eligibility preflights before asking the operator to enter `DELETE`. A declined confirmation could create/update `asset-ownership.json` despite no authorized uninstall. The `DELETE` consent check is now **before** `acquire_operation_lock` and cumulative-ownership registry writes, but **after** strict manifest parsing and early unowned-swap refusal. EOF is an explicit cancellation error. `--yes` bypasses only interactive consent; post-lock transaction guards and asset preflights remain mandatory. This is not a guarantee of rollback **after** destructive steps begin.

New `tests/test_uninstall_wizard_preview.py::test_cancel_or_eof_preserves_ownership_and_install_state` calls the real non-dry-run CLI with a disposable HOME/XDG fixture. English default, Korean selected purge, full purge refusal and full purge EOF must reject before host command execution and preserve fixture bytes without creating `asset-ownership.json` or `operation.lock`. External Docker/systemd/sudo/swapoff commands are denied by PATH stubs. Initial [CI 38186275070](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38186275070) SUCCESS (766/766 synthetic tests) at commit `2e86ed4fa75a28bd585ff932cffdd4c4afab59ef`; final CI for the extended pre-existing-registry fixture tracked in PR #259. No actual DGX state was touched. M1 host NOT_QUALIFIED; M2 destructive E2E NOT_RUN; M3 all-profile E2E NOT_QUALIFIED; M4 H38 BLOCKED; PR #259 Draft/Open, Merge BLOCKED.

Existing cumulative-registry preservation is additionally tested by `test_cancel_preserves_existing_ownership_registry_bytes`: a pre-existing valid `asset-ownership.json` must retain its exact bytes on operator cancellation, with an owned-model manifest that would otherwise trigger legacy bootstrap migration. No host-side daemon calls are allowed. A confirmed, actively executing uninstall still requires independent destructive E2E qualification.


## Preflight-staged ownership registry for approved uninstall (2026-10-12)

The approved real `uninstall.sh` previously bootstrapped the **canonical** cumulative ownership registry before `preflight-one`, `preflight-purge`, external-container references and unowned-service checks. A failure could leave an altered `asset-ownership.json` without any authorized teardown. The revised flow, under the existing operation lock, copies the registry into a private same-filesystem `.uninstall-preflight.*` directory, runs the **existing** legacy bootstrap and eligibility checks against that staged copy, and publishes it only if all checks succeed; on a handled failure, an EXIT trap deletes the staged directory. An unchanged original registry is not needlessly replaced. Symlink/non-regular canonical registry paths are rejected. The operation lock file may remain after refusal. A process killed without running EXIT traps may leave a private staging directory for later inspection; no claim of crash-atomicity is made.

The new `test_approved_purge_preflight_failure_preserves_cumulative_registry` uses the real CLI with `--yes` on disposable HOME/XDG synthetic owned base + retained unowned dependent, exercising both `--purge-model` and `--purge-all`. It asserts blocked deletion, identical canonical registry/manifest/model bytes, no external host mutator calls and no left-behind staging directory. The actual DGX was not touched; this is synthetic failure-preflight coverage, not destructive-install/uninstall E2E or proof of post-teardown recovery. M1 live Doctor still NOT_QUALIFIED; M2 destructive E2E NOT_RUN; M3 all-pairs NOT_QUALIFIED; M4 H38 BLOCKED. PR #259 Draft/Open, merge blocked.


An additional `test_external_container_image_refusal_preserves_registry` exercises a synthetic `IMAGE_OWNED=1` with an external Docker-container reference. Read-only Docker image inspection and `ps` are stubbed; `docker rm`, image deletion, sudo/systemctl/swapoff, real host data access and model load are not allowed. The installer-owned image is refused at the **external-container preflight**, and the canonical registry and fixture bytes remain unchanged. This expands synthetic eligibility refusal coverage without asserting successful destructive uninstall.


### Synthetic approved-uninstall preflight result — CI verified (2026-10-12)

Exact tested code HEAD `c332959df7676d3d87a69eb628b94fa5af862e41`: [GitHub Actions CI #38188708849](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38188708849) **SUCCESS, 769/769 Python unit tests**, Bash syntax PASS, ShellCheck PASS, Python compilation PASS, whitespace PASS. Earlier base staging code HEAD `6186294fda78d9fed5d5bac8f35029b52c4a2856`: [CI #38188545527](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38188545527) **SUCCESS, 768/768**. This evidence covers synthetic failure branches for retained dependent model and externally referenced image; it is **not** evidence of successful real deletion or crash-atomicity. No DGX host operations were executed. All M1 host-health, M2 destructive E2E, M3 all-pairs, M4 H38, and PR #259 merge blockers remain.


## Docker removal failure and partial-uninstall retry safety (2026-10-12)

Previously `uninstall.sh` ignored **every** `docker rm -f` failure with `|| true`, risking model/image/release deletion when the Docker daemon or authorization was broken and the managed container could still exist. Now arbitrary Docker errors are **fail-closed before asset purge**; only an exact Docker `No such container: <managed name>` message permits idempotent continuation. `PHASE=complete` remains when service/container removal fails, allowing an operator-directed retry. `asset-ownership.json` may already reflect the successful preflight; the service may already have been disabled or removed. Neither rollback of completed teardown nor crash-atomicity is claimed. Real managed host and H38 model remain untouched. New disposable synthetic fault-injection regressions cover service-remove failure, Docker-remove failure, retry-after-recovery and already-absent Docker container; final CI result to be recorded in PR #259. M1 live host NOT_QUALIFIED, M2 destructive E2E NOT_RUN, M3 profile all-pairs NOT_QUALIFIED, M4 H38 BLOCKED, PR Draft/Open, Merge BLOCKED.


### Post-teardown failure and safe retry: synthetic CI acceptance (2026-10-12)

**Evidence:** [CI #38189466067](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38189466067) **SUCCESS, 771/771** at `09527d81121ad6fe820400382a12eb9a443318b6`; [CI #38189596217](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38189596217) **SUCCESS, 772/772** at `69df950fc4a7f1c6038ab8aff9f5e3ee45dc80b7`, including Bash syntax, ShellCheck, Python compilation and whitespace checks.

A synthetic real-CLI sequence using only disposable HOME/XDG and command denial/stubs shows:
1. Managed service-removal fault => no Docker removal attempt, owned synthetic model intact, manifest `PHASE=complete`.
2. Service removal succeeds, Docker daemon removal fails => script exits nonzero **before** model/image/release purge, records no completed uninstall, owned model and release preserved; published registry retains ownership evidence.
3. After fault clearance, retry completes, removes the **synthetic owned model only**, retains release data and sets `PHASE=uninstalled`.
4. An exact Docker `No such container` diagnostic is idempotent; unowned model and release remain.
5. On `--purge-all`, after **synthetic model and image removal** a simulated swap-remove failure exits nonzero with remaining fake swap and release preserved, manifest still `PHASE=complete` and cumulative registry reflecting completed asset removal. On retry after fault clearance, the script tolerates the already absent owned model/image, removes only the fake swap and synthetic release/manifest, and completes.

This proves bounded **synthetic retry behavior**, NOT rollback of previously removed components, interruption/crash durability, actual systemd/Docker/PLE behavior, independent disposable-host install/remove/reinstall E2E, or single-DGX host qualification. Actual DGX was untouched. M1 actual host NOT_QUALIFIED; M2 destructive E2E NOT_RUN; M3 all-profile E2E NOT_QUALIFIED; M4 H38 BLOCKED. PR #259 remains Draft/Open, Ready/Merge BLOCKED.


## SIGKILL interrupted-uninstall preflight recovery (2026-10-12)

Under the lifecycle operation lock and before creating a staged ownership copy or doing any teardown, `uninstall.sh` now refuses existing `.uninstall-preflight.*` artifacts, including symlinks. A `SIGKILL` or power loss bypasses shell EXIT traps, so these private staging snapshots may survive. Do **not** automatically delete them or treat them as canonical ownership evidence. Inspect each exact stale path, verify ownership and contents, confirm no concurrent lifecycle operation, and handle its removal/quarantine only as a separately authorized maintenance action. No blanket wildcard deletion on the active DGX. This guard is fail-closed: the install manifest and canonical ownership registry remain authoritative, and model/image/swap removal cannot proceed while an unreviewed preflight snapshot exists. Synthetic SIGKILL crash tests and exact GitHub CI evidence are tracked in PR #259; actual power-loss durability is NOT_QUALIFIED. PR remains Draft/Open and merge blocked.


### Interrupted uninstall recovery procedure and validation boundaries (2026-10-12)

**Stop condition:** a `.uninstall-preflight.*` artifact, missing model ownership manifest, drifted registry fingerprint, interrupted model deletion, or a state/host mismatch is **not** permission to resume unattended `uninstall.sh --yes`. Leave all host protection and stopped runtime settings intact.

1. Preserve evidence before any repair: read the canonical `install.env`, `asset-ownership.json`, exact `.uninstall-preflight.*` entries, file owner/mode and applicable logs **without executing the staged file or running host mutators**. The canonical registry is the only ownership authority; staged snapshots are untrusted. Acquire or confirm exclusive lifecycle maintenance ownership before any later mutation.
2. Reconcile actual read-only service/container/swap state with the recorded manifest. `PHASE=complete` after a crash **does not** mean the service is still installed, container still exists, model remains complete or swap is intact. Never infer successful teardown from parent process exit status alone; child deletion commands may outlive a killed parent.
3. For a verified orphan staging directory, document its exact path and integrity, quarantine/clear **only that exact path** after operator review, and rerun preflight before resuming; never use broad `rm -rf` globs or follow symlinks. Unreviewed staging blocks the real uninstaller.
4. For a partially deleted model with a missing/drifted `.qwen38-model-manifest.json` or `.qwen38-hybrid-manifest.json`, keep the original cumulative registry and the surviving model data; **do not invent a marker or weaken preflight**. Recovery requires independent trusted backup/provenance verification, otherwise quarantine and a separately authorized reinstall on an isolated disposable host.
5. If a fully removed owned model is already absent but a dedicated swap/release remains, a repeat purge is eligible **only after** checking the original model path, ownership history, live host state, swap provenance and pending lifecycle artifacts. No automated or live sole-DGX destructive recovery is authorized by the synthetic tests.
6. Preserve an interruption evidence report (files/hashes, timeline, host-command results, whether child process survived, repair decision). Host power-loss filesystem ordering/fsync, SIGKILL of the whole process group, real teardown replay and install→remove→reinstall remain unverified separately.

Synthetic `test_sigkill_during_stage_requires_manual_stale_recovery`, `test_sigkill_partway_through_model_delete_requires_verified_recovery`, and `test_sigkill_at_swap_after_model_purge_can_resume` use the **real** CLI with disposable HOME/XDG, fake owned model/swap and PATH-denied Docker/sudo/systemctl/swapoff. Their SIGKILL is injected from a child stub and the stub must exit immediately rather than completing its own deletion after killing the parent. These tests do not simulate power loss or provide live-host authorization. Previous failing CI attempts due to a child-stub execution bug are retained as historical failures; the corrected commit and its CI outcome are recorded in PR #259. All M1 actual-host/M2 real-destructive/M3 all-profile/H38 gates remain blocked or unqualified; PR #259 remains Draft/Open, Ready/Merge BLOCKED.


## Guarded DGX code synchronization and synthetic-only local verification (2026-10-12)

The previous 775/775 GitHub Actions result was **CI**, not evidence that the operator's single DGX had fetched the latest branch or run any tests locally. To close this handoff gap without touching live host resources, `scripts/lifecycle/verify-synthetic.sh` now validates an explicitly supplied 40-character checkout SHA, clean Git worktree, exact `feat/h38-managed-integration` branch and matching `origin/feat/h38-managed-integration` tracking ref **without any Git mutation**. It then runs bounded Python synthetic lifecycle suites inside a disposable HOME/XDG_STATE_HOME/XDG_DATA_HOME/TMPDIR, with a first-in-PATH deny wrapper for Docker, sudo, systemctl, swapoff/swapon, mount/umount and nvidia-smi. Tests are restricted to installer/uninstaller preview, ownership, operation lock, lifecycle integration and non-mutating lifecycle snapshot tests; no actual install/uninstall, Docker, service change, runtime startup, model download or host Doctor is invoked. The test wrapper is itself exercised on GitHub Actions in `--ci` mode and refuses `--ci` outside `GITHUB_ACTIONS=true`.

**Operator sync procedure, not executed by ChatGPT:** on the actual DGX working checkout, require `git status --porcelain=v1 --untracked-files=all` empty and the expected feature branch already selected; `git fetch --prune origin`; confirm `origin/feat/h38-managed-integration` equals the **exact tested target SHA**; then `git merge --ff-only origin/feat/h38-managed-integration`, confirm HEAD and worktree, and invoke the new verifier with that SHA. No `git reset --hard`, stash/pop, force merge or automatic checkout switching. Sync/test modifies the local Git checkout and disposable test files only; no remote host access or DGX test was performed from ChatGPT. **Report DGX_LOCAL_SYNTHETIC=NOT_RUN until the operator supplies actual local output.** Keep `M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`, PR #259 Draft/Open; Ready/Merge BLOCKED.


### Verified safe Git sync and synthetic-only DGX test handoff (2026-10-12)

[CI #38192014751](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38192014751) **SUCCESS** for code commit `c915f805b7fe7abbc8a260379df69148ef5f54e6`: **780/780** full unit tests, Bash syntax, ShellCheck, Python compilation, whitespace, plus an actual execution of `scripts/lifecycle/verify-synthetic.sh` in the GitHub PR checkout with **48/48** bounded synthetic tests (16 uninstall wizard, 6 asset ownership, 8 operation lock, 14 lifecycle integration, 4 snapshot tests). The GitHub Actions checkout may be a PR merge SHA rather than the feature branch HEAD; the verifier checks the exact SHA **of the checkout it is given**. An earlier [CI #38191976973](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38191976973) failure was a missing-SHA message/test mismatch; corrected in `c915f80` with tests passing.

**DGX operator-only sync/test, not run by ChatGPT**: choose the latest verified GitHub branch head SHA as `TARGET`. Start on branch `feat/h38-managed-integration` with a clean worktree. Confirm remote `origin` points to the expected GitHub repository, fetch only the branch without tags, assert `origin/feat/h38-managed-integration` equals the pinned SHA, and fast-forward only with Git hooks disabled. Never reset/stash/force-overwrite local edits. Then run `bash scripts/lifecycle/verify-synthetic.sh "$TARGET"` to verify the exact local checkout. This tool **does not run fetch/merge**, Docker, service manager, install, uninstall, runtime/host Doctor or any model; it runs only the five synthetic test modules under disposable HOME/XDG/TMPDIR and intercepts host commands through PATH stubs. **PATH interception is not an OS-level sandbox**; tests are allowlisted after source review and GitHub CI qualification. If remote advanced beyond the pinned target or any preflight fails, stop without changing the checkout and reassess the SHA.

`DGX_LOCAL_SYNTHETIC=NOT_RUN` until the operator sends the **actual DGX output** (including exact SHA and `LOCAL_SYNTHETIC_RESULT=PASS`). `M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`, PR #259 Draft/Open and Ready/Merge BLOCKED.


## DGX-selected profile read-only snapshot and ordered operator verification (2026-10-12)

Operator-provided DGX log proves the earlier clean fast-forward through
`0e910a7e0ab6246228857cc9432c19b5787eb812` and the local **48/48
synthetic lifecycle tests PASS**, final `DGX_SYNTHETIC_VALIDATION_COMPLETE`.
The local command printed `SHELLCHECK=SKIPPED_NOT_INSTALLED` (ShellCheck
already passed GitHub CI), and did **not** qualify running model/runtime or
the destructive host E2E. This is historical exact-SHA local evidence only.

New `scripts/lifecycle/inspect-selected-profile.py` gives a compact,
read-only actual-host snapshot separately from the synthetic verifier:
strict `install-maintenance` manifest parsing reports selected model
profile/phase/repository/path/expected image/served name and monitor
protection; four strict transition status files and stale artifacts are
reported; read-only Docker inspect and systemctl show report runtime and
service observations. Docker/systemd probe errors remain UNKNOWN. A running
container with matching image/mount/served command is labeled
`MATCHED_NOT_READINESS`, **never actual serving/health qualified**.
Corrupt manifest or pending transition causes fail-closed nonzero exit.
Synthetic unit tests with temporary HOME/XDG and mocked host commands
verify stopped, missing, uninstalled, invalid, transition pending and
running-but-unqualified cases.

The expanded `inspect-readonly-lifecycle.sh` now prints selected-profile
snapshot **first**, before model inventory, other transitions and Doctor.
Operator sequencing: (1) safe exact-SHA Git synchronization, (2) actual
read-only selected-profile snapshot, (3) disposable synthetic tests, then
(4) optional comprehensive read-only Doctor. The disposable verifier
**must not be mistaken for an actual DGX runtime-status probe**.

Do not invoke install/uninstall, Docker mutation, systemd restart, model/GPU,
swap mutation, host monitor relaxation or H38. New actual-host snapshot
execution is **NOT_RUN** until its operator-provided DGX output is supplied.
M1 live host NOT_QUALIFIED, M2 destructive E2E NOT_RUN,
M3 model all-pairs NOT_QUALIFIED, M4 H38 BLOCKED; PR #259 Draft/Open,
Ready/Merge BLOCKED.


## DGX actual selected-profile and isolated test evidence (2026-10-12)

**Source:** operator-provided actual DGX transcript, fast-forward from `0e910a7`
to exact feature HEAD `87fb463984683f75435302eff5ffc3b3b9f941bf` with clean
post-test checkout and `DGX_PROFILE_AND_SYNTHETIC_VALIDATION_COMPLETE`.
`verify-synthetic.sh` reported `LOCAL_SYNTHETIC_RESULT=PASS` with **56/56**
disposable synthetic tests (16 uninstall, 6 ownership, 8 lock,
14 integration, 8 selected-profile snapshot, 4 read-only snapshot).
Local `BASH_SYNTAX=PASS`; `SHELLCHECK=SKIPPED_NOT_INSTALLED` (separately,
[GitHub CI #38194619518](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38194619518)
SUCCESS: 788/788 full unit tests and ShellCheck PASS). **DGX_LOCAL_SYNTHETIC=PASS at
this exact SHA only.**

Actual read-only DGX `inspect-selected-profile.py` reported:

| Observed field | Reported value / qualification |
|---|---|
| `MANIFEST_STATUS` / `INSTALL_PHASE` | `VALID` / `complete` |
| `SELECTED_PROFILE` | `orcarouter` (configuration intent) |
| `PROFILE_REPOSITORY` | `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4` |
| `EXPECTED_IMAGE` and `CONTAINER_IMAGE` | `vllm-skinny-tp1:v1` (legacy installed tag; H38 not active) |
| `MODEL_PATH_STATUS` | `MARKER_PRESENT_NOT_VERIFIED` (not checksum/integrity) |
| `MONITOR_PROTECT` / `MONITOR_ENABLED` | `1` / `1` (configured, not verified running protection) |
| `PROFILE_SWITCH_STATE`, `RUNTIME_TRANSITION_STATE`, `UPDATE_STATE`, `RELEASE_PROFILE_REFRESH_STATE` | all `IDLE` |
| `STALE_TRANSACTION_ARTIFACTS` | `NONE` (only the configured tracked subset) |
| `CONTAINER_STATE` / `SERVICE_STATE` | `EXITED` / `INACTIVE` |
| `RUNTIME_ATTESTATION` | `MISSING`; do not manufacture it |
| `PROFILE_STATUS_SUMMARY` | `CONTAINER_NOT_RUNNING` |
| `ACTUAL_SERVED_PROFILE` | `NOT_VERIFIED` |
| `HOST_HEALTH_QUALIFICATION` | `NOT_ESTABLISHED_BY_THIS_SNAPSHOT` |

**Interpretation and next priority:** Git code/tests are synchronized and the
selected profile is `orcarouter`, but the runtime is stopped. Its stop cause
is **NOT YET DETERMINED** by this newly submitted output: an exited container
plus inactive service does not prove OOM, a protection-triggered stop,
deliberate administrative shutdown or a runtime error. Runtime commit
attestation is absent; never reconstruct an attestation without verified
provenance. H38 code is not an installed/serving H38 model. Retain host
monitor/protection and all stopped services as observed: **NO restart, H38 GPU
rerun, swap cleanup, reinstall, profile-switch or uninstall**.

**Next existing read-only tool (no new script or additional Git pull is
required at verified SHA `87fb463...`):**
```bash
(
  set -Eeuo pipefail
  cd ~/Workspace/llm/qwen3.8-flash-next-dgx-spark
  TARGET=87fb463984683f75435302eff5ffc3b3b9f941bf
  test "$(git rev-parse HEAD)" = "$TARGET"
  test -z "$(git status --porcelain=v1 --untracked-files=all)"
  QWEN38_OFFLINE_DIAGNOSTIC_TARGET_SHA="$TARGET" \
    bash scripts/lifecycle/inspect-readonly-runtime-offline.sh
)
```
This existing exact-SHA helper reads `docker inspect` (container exit
code, OOMKilled, start/finish timestamp, state error, declared ports),
`systemctl show` (ActiveState/Result/ExecMainCode/ExecMainStatus/timestamps),
and `stat` file metadata for `runtime-commit.env`, `runtime-stop.env` and
`monitor.pid`. It prints `RUNTIME_STOP_REASON=NOT_YET_PROVEN`; the output
is **evidence for triage**, not authorization to restart or proof of cause.
Historical Oct-07 journal/monitor scripts are time-window bound, so only use
them after checking whether the observed `FinishedAt` falls in their
documented window. If the offline command returns 3, preserve its partial
results and do not reinterpret failure as stop-cause evidence.

**Gates:** `DGX_LOCAL_SYNTHETIC=PASS` at specified SHA, but
`M1_HOST_HEALTH=NOT_QUALIFIED`, `HOST_STABILITY=INCONCLUSIVE`,
`M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`,
`M4_H38=BLOCKED`, `HOST_PROTECTION=UNCHANGED`; PR #259 Draft/Open,
Ready/Merge BLOCKED.


## Reconciled DGX offline repeat versus previously resolved Oct 7 protection stop (2026-10-12)

The operator's latest **actual DGX** read-only `inspect-readonly-runtime-offline.sh`
run at a clean exact checkout `87fb463984683f75435302eff5ffc3b3b9f941bf`
completed all three queries (`rc=0`) and returned `MANAGED_RUNTIME_OFFLINE=COLLECTED_READ_ONLY`.
Docker `status=exited exit_code=0 oom_killed=false`, started **2026-10-07
16:35:45.800732 KST**, finished **22:08:34.847185 KST**; correct declared
loopback `127.0.0.1:8888` binding with no active port mapping while stopped.
Systemd `Result=success ExecMainCode=1 ExecMainStatus=0 inactive/dead`,
ActiveEnter **22:08:29 KST**, InactiveEnter **22:18:17 KST**.
`runtime-commit.env`, `runtime-stop.env`, and `monitor.pid` were **ABSENT**
at observation. The repeated values match the older exact-DGX
[offline Attempt 01](../scripts/benchmark/evidence/managed-runtime-offline-attempt01-exit0-no-oom-20261012.md)
recorded at a different checkout, not a new runtime or H38 test.

**Resolve chronology using existing historic evidence, not an additional
monitor experiment.** The already archived
[service journal](../scripts/benchmark/evidence/managed-runtime-stop-journal-attempt01-protected-abort-20261012.md)
explicitly records graceful stop of the **previous** container for candidate
handover **22:08:30**, candidate monitor/start at **22:08:35**, and candidate
abort by memory protection **22:18:16**, then **previous container restored
but left STOPPED 22:18:17**. The separately archived
[numeric monitor samples](../scripts/benchmark/evidence/managed-monitor-trigger-attempt01-low-free-swap-growth-pass-20261012.md)
confirm low non-CMA free memory **below 2 GiB** together with swap growth
**at least 256 MiB**, counted for **5 consecutive protection samples**
and `PROTECT stopping` at **22:17:43**. Thus the stopped canonical container's
`exit_code=0 oom_killed=false` correlates with the previous container's
handover/rollback, **not** with the candidate's unobserved Docker exit.
There is no candidate immutable ID or attestation proof in the new snippet;
no kernel OOM/NVIDIA RM failure, false positive, safe memory peak or
candidate READY may be inferred.

This reconciliation supersedes earlier **intermediate** lines stating the
Oct 7 *managed transition's* stop cause or protection threshold branch were
still wholly undetermined. The inspector itself intentionally emits the
literal `RUNTIME_STOP_REASON=NOT_YET_PROVEN` as a collection marker, and
must remain unchanged. The **managed-service protection-abort sequence
and numeric trigger branch are confirmed by earlier evidence**, while
ultimate kernel/driver/model root cause and protective-policy appropriateness
are still **UNVERIFIED**. No new H38 GPU rerun or additional journal hunt.

Canonical new [repeat cross-check evidence](../scripts/benchmark/evidence/managed-runtime-offline-repeat-crosscheck-20261012.md)
preserves source, timestamps and limits. `DGX_LOCAL_SYNTHETIC=PASS` only
for the earlier 56/56 locally run at `87fb463`; the new docs-only GitHub
HEAD has **not** been pulled/tested on the DGX. Maintain
`M1_HOST_HEALTH=NOT_QUALIFIED`,
`M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`,
`M4_H38=BLOCKED`, `HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`,
PR #259 **DRAFT/OPEN, Ready/Merge BLOCKED**. Primary next engineering
priority is **host-independent installer/uninstaller/profile-switch acceptance**,
then independent disposable-host E2E. Do not restart or mutate the sole DGX.


## Fail-closed uninstall plan, Docker dependency, and image absence (2026-10-12)

GitHub source-only hardening captures an ownership `plan-purge` during staged
preflight with an explicit successful producer exit; partially output
nonzero plans cannot authorize teardown. External `docker ps` must succeed,
not merely return zero results; `docker image inspect` must explicitly
report `No such image/object` to authorize an absent image. Unexpected
Docker command failures stop the purge, including at final image-forget.
Fixture regressions exercise failures before registry publication and retain
the preexisting canonical manifest/registry and unowned assets.

Final qualifying CI for the code at
[GitHub Actions #38196834096](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38196834096)
**SUCCESS 792/792 Python, 60/60 bounded synthetic tests**, plus Bash,
ShellCheck, Python compilation, whitespace. Two intermediate CI failures
were test-stub representation problems, preserved in
[specific evidence](../scripts/benchmark/evidence/managed-uninstall-fail-closed-purge-plan-docker-20261012.md).
The independent [disposable-host E2E plan](DISPOSABLE-LIFECYCLE-E2E-PLAN.md)
is an **acceptance plan, NOT an executed test**.

Current sole DGX checkout was last operator-observed at `87fb463...`, with
56/56 synthetic PASS and service/container intentionally stopped after the
Oct 7 protection-abort sequence; new source not locally synchronized/tested.
`M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`,
`M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`,
`HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`.
Never run destructive lifecycle gates on the sole DGX. PR #259 Draft/Open,
Ready/Merge BLOCKED.


## DGX local synthetic acceptance at exact uninstall-hardening SHA (2026-10-12)

An actual operator-provided DGX terminal log confirms a clean guarded
fast-forward `87fb463 → 02e9c61`, exact checkout
`02e9c61d90c7f15484b0605dc872bbbb21ec253b`, final SHA/worktree
checks, and `DGX_SYNTHETIC_VALIDATION_COMPLETE`. The isolated
`verify-synthetic.sh` tests passed **60/60**:
19 uninstall, 7 asset-ownership, 8 operation-lock, 14 lifecycle integration,
8 selected-profile-readonly and 4 full-readonly-snapshot tests.
`LOCAL_SYNTHETIC_RESULT=PASS`, `BASH_SYNTAX=PASS`,
`LOCAL_SYNTHETIC_SCOPE=DISPOSABLE_FIXTURES_ONLY`, and
`LOCAL_SYNTHETIC_HOST_COMMANDS=PATH_DENY_STUBS` were observed.
Local `SHELLCHECK=SKIPPED_NOT_INSTALLED`; separately
[CI #38197243631](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38197243631)
was **SUCCESS, 792/792 full tests**, **60/60 synthetic**, ShellCheck PASS.
This explicitly upgrades the earlier statement that the uninstall-hardening
code had not been synchronized/tested on the DGX.

See [actual DGX synthetic acceptance evidence](../scripts/benchmark/evidence/dgx-synthetic-uninstall-hardening-pass-20261012.md).
The DGX log **does not contain a new live service/Doctor inspection**;
the prior `orcarouter` selected profile and stopped runtime observation
remain historical, not a new readiness claim. Keep
`M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`,
`M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`,
`HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`,
PR #259 Draft/Open and Ready/Merge BLOCKED.

## Full ordered profile-switch pair matrix — synthetic CI (2026-10-12)

Four state-schema profiles (`orcarouter`, `nvidia`, `mazinb`,
`orcarouter-hybrid`) yield **12 distinct ordered profile switches**. The
synthetic transaction suite now checks all 12 for (1) uncommitted
activation recovering exact source manifest, (2) attested target runtime
finalizing target manifest, and (3) mismatched candidate container-ID
attestation refusing commit then allowing provable source rollback.
Same-profile and wrong-source prepares are also refused for all four
starting profiles. Existing interrupted-state and lock fixtures remain.

[CI #38204508012](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38204508012)
**SUCCESS, 796/796 full tests, 70/70 allowlisted synthetic tests** and
Bash, ShellCheck, Python compile and whitespace PASS. The exact-SHA local
synthetic runner now includes the mocked profile-switch test module
(**10 tests**). [Pair matrix evidence](../scripts/benchmark/evidence/managed-profile-switch-pair-matrix-synthetic-20261012.md)
records subtest coverage and evidence boundaries. It is **NOT** a true
Docker/systemd profile-switch E2E, and does not qualify M3.

The operator's last actual DGX synthetic run was **60/60 at `02e9c61`**;
this newer pair-matrix source has not been synchronized/run locally on
the DGX. Preserve the stopped runtime/protection, do not run live
profile switches or model starts. `M1_HOST_HEALTH=NOT_QUALIFIED`,
`M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`,
`M4_H38=BLOCKED`, `HOST_STABILITY=INCONCLUSIVE`,
`HOST_PROTECTION=UNCHANGED`; PR #259 Draft/Open and Merge BLOCKED.

## Actual DGX 70/70 directed profile-pair synthetic acceptance — 2026-10-12

The operator supplied a successful exact-SHA guarded DGX fast-forward
`02e9c61 → d2e9a1d` and `verify-synthetic.sh` output proving **70/70
selected synthetic tests PASS**, **Bash syntax PASS**, and final exact clean
checkout `d2e9a1dc2b9759bc60915f2a7cda7b0cfd9d4914`. Breakdown:
19 uninstall + 7 assets + 8 locks + 14 lifecycle integration +
**10 profile-switch transaction** + 8 selected-profile snapshot +
4 lifecycle snapshot. Profile-switch synthetic cases include all 12
ordered pair directions with successful target attestation, uncommitted
rollback, and incorrect container-ID rejection/rollback.

DGX `SHELLCHECK=SKIPPED_NOT_INSTALLED`. Separately
[CI #38204845533](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38204845533)
**SUCCESS**, 796/796 full unit tests, 70/70 selected synthetic and
ShellCheck/Bash/Python/whitespace PASS. The previous 60/60 actual-DGX
local synthetic acceptance at `02e9c61` is superseded as **latest**
local synthetic evidence. See the
[actual-DGX 70/70 evidence](../scripts/benchmark/evidence/dgx-profile-pair-synthetic-pass-20261012.md).

This proves neither physical Docker/systemd transition nor readiness,
M1 host health, M2 destructive E2E, M3 actual all-pair qualification or
M4 H38. Selected `orcarouter` and stopped runtime are **historical** read-only
observations, not updated by this test. The current single DGX host's
service/monitor/swap/protection remain untouched. `HOST_STABILITY=INCONCLUSIVE`,
`HOST_PROTECTION=UNCHANGED`; PR #259 DRAFT/OPEN and Ready/Merge BLOCKED.

## New actual DGX 70/70 confirmation and GitHub-only profile-switch drift gates — 2026-10-12

The user-supplied **actual DGX** terminal log confirms exact-SHA
fast-forward `d2e9a1d → fb6e0ed`, final clean checkout
`fb6e0ed4075ac5fa8a3142137d068eb98d65e4bf` and
`verify-synthetic.sh` **70/70 PASS** (7 allowlisted modules including
10 profile-switch tests). The on-host `BASH_SYNTAX=PASS`; local
`SHELLCHECK=SKIPPED_NOT_INSTALLED`. GitHub CI #38207710548 at this
same source had **796/796 full and 70/70 selected PASS**, including
CI ShellCheck, not on-host ShellCheck. This supersedes `d2e9a1d` as
**latest actual DGX locally tested SHA**, without changing host readiness
or previously observed runtime state.

Additionally, GitHub-only source commit `8538c83` added **3
disposable profile-switch fault regressions**: tampered backup SHA
refuses rollback while preserving state; tampered candidate SHA refuses
target commit and can roll back to a provable old runtime; removal of
runtime attestation after a recorded commit refuses finalization until
proof is restored. [CI #38210907792](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38210907792)
**SUCCESS, 799/799 full Python tests, 73/73 synthetic, ShellCheck PASS**.
These 3 cases have **not been run on the actual DGX**.

Evidence: [actual DGX console](../scripts/benchmark/evidence/dgx-synthetic-doc-head-pass-20261012.md)
and [manifest/attestation fault injection](../scripts/benchmark/evidence/managed-profile-switch-drift-attestation-synthetic-20261012.md).
Neither result qualifies live M1, real D0–D5 M2, all-pairs service M3 or
H38 M4. `HOST_STABILITY=INCONCLUSIVE`,
`HOST_PROTECTION=UNCHANGED`. No model/service/swap/GPU change. PR #259
must remain Draft/Open/Unmerged and Ready/Merge BLOCKED.

## Actual DGX 73/73 and fail-closed profile-switch orphan-state hardening — 2026-10-12

Operator-supplied real DGX output confirms a clean, exact guarded
fast-forward `fb6e0ed → e18c56a` and **73/73 local isolated synthetic
tests PASS**, including **13 profile-switch transaction tests**.
`BASH_SYNTAX=PASS`, local `SHELLCHECK=SKIPPED_NOT_INSTALLED`,
`LOCAL_SYNTHETIC_RESULT=PASS` and final
`DGX_PROFILE_RECOVERY_SYNTHETIC_VALIDATION_COMPLETE` were observed.
Latest actual DGX verified SHA is
`e18c56aff008f717ad54ee787ab20c248e987e34`.

Subsequent GitHub-source-only review found a **false-idle fail-open**:
a dangling transition file link or orphan backup/candidate/staging
artifact could be hidden by the no-state branch of `recover`,
`rollback`, `service-recover` or `status`. The new code refuses to
claim idle while any such file or link remains, preserving normal truly
idle behavior. Three new fixture unittest methods exercise the
dangling/orphan/valid-idle matrix. [Source CI #38212223945](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38212223945)
**SUCCESS 802/802 full Python, 76/76 synthetic**, plus Bash,
ShellCheck, compile and whitespace PASS. **This new source is not yet
executed locally on the DGX.**

[Evidence details](../scripts/benchmark/evidence/dgx-73-and-profile-switch-false-idle-hardening-20261012.md).
No live host E2E, Docker/systemd profile changes or H38 reruns.
`M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`,
`M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`,
`HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`,
PR #259 Draft/Open, Ready/Merge BLOCKED.


## New actual DGX 76/76 synthetic acceptance and prepare fail-closed check — 2026-10-12

A newly supplied DGX console transcript confirms exact guarded fast-forward `e18c56a → 9220624` and **76/76 local isolated synthetic methods PASS** on `922062436b71353760c2323103e749ed6eaf6240`, including 16 profile-switch methods. `BASH_SYNTAX=PASS`, local `SHELLCHECK=SKIPPED_NOT_INSTALLED`, clean exact HEAD and worktree, `LOCAL_SYNTHETIC_RESULT=PASS` and final `DGX_PROFILE_IDLE_SAFETY_SYNTHETIC_COMPLETE` were observed. The matching GitHub [CI #38212708550](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38212708550) passed 802/802 full and 76/76 synthetic tests plus ShellCheck. This **supersedes 73/73 as the latest actual DGX local synthetic**, not as any live host qualification.

A subsequent safety review found that `prepare` did not apply the existing orphan `.tmp` fail-closed check used by idle/recovery actions. The source now applies the shared guard before publishing a new transaction, with a new seven-scenario (six artifacts and one dangling symlink) fixture regression method. **The new source change was not part of the completed DGX 76/76 run.** [New-source CI #38215072213](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38215072213) **SUCCESS 803/803 full tests, 77/77 bounded synthetic (17 profile-switch), ShellCheck/Bash/compile/whitespace PASS** at `51e85f6578ee0694a13964f700f30e854f17c020`. This new source has not been tested on DGX.

[New DGX and source review evidence](../scripts/benchmark/evidence/dgx-76-and-prepare-orphan-guard-20261012.md). Actual Docker/systemd E2E, M1/M2/M3/M4 gates and host protection are unchanged: `M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`, `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`; PR #259 stays Draft/Open, Ready/Merge BLOCKED.


## Actual DGX 77/77 profile-switch prepare guard acceptance — 2026-10-12

New operator-provided console evidence confirms guarded fast-forward `9220624 → 1283b1a` and **77/77 isolated local synthetic tests PASS** on exact DGX checkout `1283b1a9252f1ff53d51659049ca42f9449e5ccd`, including **17/17 profile-switch tests** and the new `prepare` orphan-staging preservation regression. Exact final HEAD, `LOCAL_SYNTHETIC_RESULT=PASS` and `DGX_PREPARE_ORPHAN_SYNTHETIC_COMPLETE` were observed. Bash syntax PASS; **local ShellCheck SKIPPED_NOT_INSTALLED**, distinct from [GitHub CI #38215504822](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38215504822) **SUCCESS 803/803 full and 77/77 synthetic, ShellCheck PASS**.

[Canonical 77/77 operator evidence](../scripts/benchmark/evidence/dgx-77-prepare-orphan-synthetic-pass-20261012.md). This updates the latest *DGX-local isolated synthetic* source from `9220624` (76/76) to `1283b1a` (77/77), **not** any real Docker/systemd/model acceptance. `M1_HOST_HEALTH=NOT_QUALIFIED`, `M2_DESTRUCTIVE_E2E=NOT_RUN`, `M3_PROFILE_ALL_PAIRS=NOT_QUALIFIED`, `M4_H38=BLOCKED`, `CHECKPOINT_METADATA_ORDER_GATE=FAIL`, `HOST_STABILITY=INCONCLUSIVE`, `HOST_PROTECTION=UNCHANGED`. PR #259 remains Draft/Open/Unmerged and Ready/Merge BLOCKED; no protected DGX runtime mutation.


## Disposable D0 offline evidence precheck — code staged, not host-qualified (2026-10-12)

A new **offline-only** reviewer, `disposable-d0-preflight.py`, validates two
explicit operator-provided JSON files using Python stdlib only. It never reads
live Docker, systemd, host identity, Git or model state; it never runs commands
on any host. Required policy: exact SHA and repository, **nonempty protected
machine-id hash and Docker daemon denysets**, forbidden production roots.
Required inventory: separately identified disposable machine/daemon, clean
exact SHA + origin, owner disposable declaration, restore point, isolated
non-default Docker context without external users, nonoverlapping throwaway
model/log/work roots, bounded owned synthetic model, non-production service
unit, and no pending lifecycle transactions.

Run **only against an independently assembled, reviewed inventory**:
`python3 scripts/lifecycle/disposable-d0-preflight.py --policy <policy.json> --inventory <inventory.json>`.
No real protected machine IDs, daemon IDs, credentials or private mount
inventories belong in Git history or CI logs. Inputs are treated as
**untrusted assertions**: success prints
`D0_STATIC_REVIEW=READY_FOR_INDEPENDENT_REVIEW` but always
`D0_ADMISSION=NOT_GRANTED` and `D0_LIVE_E2E=NOT_AUTHORIZED`.
Any incomplete/mismatched evidence fails closed with exit 2. A passing
offline check is **not** permission for D1–D5; independent operator
attestation, read-only on-host cross-check and explicit disposable-host
authorization remain mandatory. Neither current DGX nor M1/M2/M3/M4
qualification is changed.


### D0 offline evidence policy CI acceptance (2026-10-12)

Source `7acd15cc5a2d8f5603bdb82b08b1cee49da7d18a` introduced a stdlib-only JSON D0 policy evaluator and nine fixture regressions. [GitHub CI #38217170909](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38217170909) **SUCCESS 812/812 full tests, 77/77 existing bounded synthetic**, Bash syntax, ShellCheck, Python compile, whitespace PASS. The D0 test methods are **not** yet in the bounded DGX verifier; latest DGX actual local run remains `1283b1a` **77/77**. A policy-consistent response is `D0_STATIC_REVIEW=READY_FOR_INDEPENDENT_REVIEW` with `D0_ADMISSION=NOT_GRANTED`; it is not live host attestation or D0 acceptance. [Permanent source/limitation evidence](../scripts/benchmark/evidence/disposable-d0-offline-preflight-ci-20261012.md). M1/M2/M3/M4 remain NOT_QUALIFIED/NOT_RUN/BLOCKED and PR #259 stays Draft/Open/Unmerged.


## D0 independent-host on-host read-only cross-check (source only; 2026-10-12)

A new conservative `disposable-d0-readonly-crosscheck.py` requires the
`--ack-independent-disposable-host` flag plus the existing strict
`--policy` and `--inventory` JSON. The **sole protected DGX is not a
permitted target**. It first validates the offline D0 policy and compares a
hashed real machine identity against the inventory and protected denyset
**before** any Docker/systemd calls. It then performs bounded read-only
Git HEAD/origin/worktree, candidate path realpath and mountpoint, Docker
context/daemon/empty-container, and dedicated disposable service-unit checks.

The collector does not probe without the explicit independent-host
acknowledgement, does not ask for sudo, does not modify files or host
configuration, and never installs/uninstalls or starts models. Its JSON
output excludes raw host identities, secrets, mounts and container IDs.
The output is `ON_HOST_READ_ONLY_ASSERTION_CROSSCHECK`, with
`d0_admission=NOT_GRANTED` and `d1_d5=NOT_AUTHORIZED` **even after
all observed fields match**. A missing daemon, unknown service response,
realpath/mount drift, protected identity or unclean Git state fails closed.

This cross-check **does not independently prove** owner consent, absence of
external Docker users, isolation of the underlying daemon, mount sources
outside the selected roots, or restoration/snapshot viability. Independent
D0 trust review and explicit authorization remain necessary. Current status:
**source and fixture tests only; not executed on any physical disposable
host or the protected DGX; M1–M4 and D1–D5 unchanged**.


## D0 independent-host read-only crosscheck — GitHub source CI (2026-10-12)

The new on-host read-only D0 cross-check source was implemented at `b6d3188`. Its first [CI #38218386709](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38218386709) **FAILED 1 of 824 full tests**, because a Docker-outage *fixture* used an `AssertionError` instead of subprocess-style `OSError`. The test fake was corrected without relaxing safety guards. [Source CI #38218663210](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38218663210) **SUCCESS 824/824 full Python, 77/77 existing bounded synthetic**, Bash/ShellCheck/Python compile/whitespace PASS at `b99b510e89cc08d99d683dcbf77c75bb55941b2c`.

The 12 new fixture cases cover protected host/daemon identities, clean Git source, path and mount drift, Docker outage/contamination and nonexclusive service refusal. No actual Docker/systemd on a disposable host was inspected; the collector is **not approved for the sole protected DGX**. Its on-host result always keeps `d0_admission=NOT_GRANTED` and `d1_d5=NOT_AUTHORIZED`, even when supplied host observations match. [Permanent evidence and trust limitations](../scripts/benchmark/evidence/d0-onhost-readonly-crosscheck-ci-20261012.md). Latest *actual DGX local* isolated synthetic remains 77/77 at `1283b1a`. D0 independent real-host review and D1–D5 remain NOT_RUN; M1/M2/M3/M4, strict host protections and PR #259 Draft/Open/Unmerged are unchanged.


## D0 parent-mount and Docker-endpoint fail-closed refinement (2026-10-12)

The source-only read-only host observer now rejects **non-root ancestor mounts** overlapping proposed disposable roots, Docker environment overrides, TCP/SSH and default/shared Unix socket endpoints, aliased/missing sockets, and refuses to use an implicit Docker context for daemon reads. Git command probes set `GIT_OPTIONAL_LOCKS=0` to avoid optional Git index refresh. The four trust-boundary fixture methods and one Git no-optional-locks method extend the read-only D0 module to **17/17 synthetic tests**.

[CI #38266470002](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38266470002) at `4dfc2aed238ce96be0b5f3970256b8a2ce8cadf8` **SUCCESS 828/828 full, 77/77 selected**, and [CI #38267015272](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38267015272) at `b65c0142340d90d681c8f82d05294bb72d813687` **SUCCESS 829/829 full, 77/77 selected** plus Bash/ShellCheck/Python compile/whitespace PASS. [Canonical source evidence](../scripts/benchmark/evidence/d0-parent-mount-docker-endpoint-guards-20261012.md) explains remaining host-attestation gaps. The latest *actual DGX-local* isolated result remains **77/77 at `1283b1a`**. This source has not been run on either actual DGX or independent disposable host. D0 `NOT_GRANTED`; D1–D5 `NOT_RUN`; M1/M2/M3/M4 unchanged; PR #259 Draft/Open/Unmerged, Ready/Merge BLOCKED.


## D0 read-only command environment and protected-socket refusal (2026-10-13)

Source `f4e83d2ae3f17d82c5f7702497138c3431072358` hardens the on-host D0 read-only observer against redirected Git/Systemd/DBus environment selectors; removes unpinned default Docker info/container commands from the allowlist; refuses arbitrary populated Docker environment overrides; and blocks context endpoints inside forbidden production roots or on/under non-root mountpoints. `GIT_OPTIONAL_LOCKS=0` remains enforced. Five new fixture methods confirm refusal before unintended host commands. [GitHub CI #38315552300](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38315552300) **SUCCESS 834/834 full Python, 77/77 existing selected synthetic, 22/22 D0 crosscheck fixtures, ShellCheck/Bash/Python compile/whitespace PASS**.

[Permanent D0 environment and socket-source evidence](../scripts/benchmark/evidence/d0-env-redirection-and-socket-boundaries-20261013.md) records provenance, safety rationale and remaining host-attestation gaps. The **latest actual DGX-local** isolated synthetic result remains **77/77 at `1283b1a`**, not the newer GitHub source. No actual independent disposable host observation or live D0 qualification occurred. `D0_LIVE_ADMISSION=NOT_GRANTED`, `D1_D5=NOT_RUN`, M1/M2/M3/M4 unchanged, and PR #259 Draft/Open/Unmerged with Ready/Merge BLOCKED.


## D0 exact-input digest receipts and offline consistency review (2026-10-13)

At source SHA `e41a34f06887f526d0a7ac7cb605d263c226f8f6`, the strict JSON reader hashes the **same bounded no-symlink file-descriptor bytes it parsed**, the read-only host collector emits `policy_sha256` and `inventory_sha256`, and the new `disposable-d0-receipt-review.py` compares its receipt to the exact supplied policy/inventory JSON. Mismatched files, invalid receipt schema, changed Git SHA and forged admission markers are refused. Consistent input is only `D0_RECEIPT_REVIEW=CONSISTENT_UNTRUSTED`; external attestation and replay freshness remain `NOT_VERIFIED`.

[Source CI #38316973840](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38316973840) **SUCCESS: 845/845 full Python, 77/77 bounded synthetic, Bash/ShellCheck/Python compile/whitespace PASS**. [Permanent fixture evidence](../scripts/benchmark/evidence/d0-receipt-input-binding-ci-20261013.md) and [receipt workflow/limitations](D0-RECEIPT-CHAIN.md) preserve provenance and non-admission semantics. The new 11 tests are **outside** the 77-case bounded DGX synthetic verifier; latest **actual DGX-local** synthetic remains **77/77 at `1283b1a`**. No actual disposable host observation occurred; D0 admission NOT_GRANTED, D1–D5 NOT_RUN, M1/M2/M3/M4 remain unqualified/blocked, PR #259 remains Draft/Open/Unmerged.


## D0 external owner/isolation/restore evidence-chain consistency (2026-10-13)

Source `a52ae7f2985ce0f415134b848b6caeb6aefec348` adds `disposable-d0-external-evidence-review.py`, a strictly offline, read-only and fail-closed review of the previous exact-input D0 receipt and **three separately provided artifacts** for independent-owner consent claims, Docker isolation claims and controlled restore-drill claims. It requires the exact policy, inventory, receipt SHA256, host/daemon identifiers and restore point to match; refused evidence includes missing/overlapping role IDs, altered/missing/empty/symlink proofs, overlapping proof digests, contradictory scopes and forged admission. The artifact contents and claimed reviewer actor IDs are **not authenticated or independently witnessed**; success only reports `STRUCTURALLY_CONSISTENT_UNTRUSTED` and always `D0_ADMISSION=NOT_GRANTED`, `D1_D5=NOT_AUTHORIZED`.

[Exact-source GitHub CI #38317915217](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38317915217) **SUCCESS: 860/860 full Python (15 new external proof methods), 77/77 existing bounded synthetic, Bash/ShellCheck/Python compile/whitespace PASS**. See [permanent evidence](../scripts/benchmark/evidence/d0-external-owner-isolation-restore-evidence-ci-20261013.md) and [external review schema and workflow](D0-EXTERNAL-EVIDENCE-REVIEW.md). The latest **actual DGX-local** fixture acceptance remains `1283b1a` 77/77, not this source; no actual independent disposable host D0 verification or D1–D5 has occurred. M1/M2/M3/M4 and PR #259 Draft/Open/Unmerged gates unchanged.


## DGX staged A/B validation recommendation — 2026-10-13

**Run A now when DGX is quiet**: after review and fast-forward-only Git synchronization to exact successful GitHub SHA, invoke the pre-existing local synthetic verifier, now extended to **134/134** offline fixtures (77 original plus 57 D0). It additionally checks the canonical repository origin and refuses Git environment redirection. After A PASS, B is **real HOME/XDG read-only selected-profile and optional Doctor/status observation**, not an M1 acceptance. **C** D0 admission and destructive D1–D5 belong on a separately owned disposable host only; **D** live H38 on the sole protected DGX remains blocked pending RM/metadata/stability/recovery and explicit approval. Source [CI #38319566009](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38319566009) PASS 863/863 full and 134/134 selected; latest actual DGX remains 77/77 at 1283b1a. [Safe DGX operator instructions](DGX-STAGED-VALIDATION.md); [source evidence](../scripts/benchmark/evidence/dgx-stage-a-expanded-synthetic-ci-20261013.md). D0 NOT_GRANTED, D1–D5 NOT_RUN, M1–M4 unchanged, PR #259 Draft/Open/Unmerged.


## Actual DGX 134/134 PASS and solo-owner test authorization boundary (2026-10-13)

User-supplied terminal evidence establishes **actual local 134/134 bounded synthetic PASS at exact b35d0f3d7840d00c55f4c633813e88ac367c6373** (Bash PASS; ShellCheck SKIPPED_NOT_INSTALLED). The immediately following real-HOME selected-profile snapshot showed a VALID complete OrcaRouter manifest, four transactions IDLE, no stale artifacts, monitor/protection both `1`, Docker container EXITED, service INACTIVE and runtime attestation MISSING. This is **A=PASS and B1=COLLECTED**, not M1 health or H38 acceptance. [Actual operator evidence](../scripts/benchmark/evidence/dgx-local-134-pass-readonly-snapshot-20261013.md).

The sole DGX owner reports testing can occur at any time without disrupting other human users. **Bounded, reversible, owner-approved live runtime tests on this one DGX may be considered after B2 full read-only Doctor and recovery review**; a second physical DGX is not mandatory for every runtime test. This revises the former blanket schedule restriction but does **not** approve deleting resources, assume Docker exclusivity, upgrade independent disposable D0 admission, run destructive D1-D5 on the only host, or launch H38 against the unresolved checkpoint/RM gates. Immediate B2: use the existing read-only lifecycle inspector at the **already checked out b35d0f3**; do not sync Git merely to run it. PR #259 remains Draft/Open/Unmerged; Ready/Merge BLOCKED.
