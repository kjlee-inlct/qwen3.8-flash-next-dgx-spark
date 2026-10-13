# Next-session continuation prompt — single DGX Spark / Qwen3.8

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


## Physical OrcaRouter wizard DRY-RUN PASS; next source priority (2026-10-13)

Operator ran `./install.sh --dry-run` at exact source `a61b4569c5a6865dbeb9aa4ba4b21aeea12424e2` in a clean detached worktree. Selected existing management menu 1, OrcaRouter selection 1, approved final preview; `WIZARD_DRY_RUN_RC=0`, `OLD_DOCKER_UNCHANGED=YES`, `INSTALL_MANIFEST_UNCHANGED=YES`. Full physical log `/home/inlc/dgx-orcarouter-wizard-20261013-152129.log`. Actual plan uses the installed legacy `vllm-skinny-tp1:v1`, NOT the previously preflighted experimental `vllm-orcarouter-v029:v1`; monitor/protect=enabled, PLE swap=128 GiB, managed systemd service. [Canonical actual DGX evidence](../scripts/benchmark/evidence/dgx-orcarouter-wizard-actual-dry-run-20261013.md).

**Priority:** implement and synthetic-test a **wizard-contained isolated OrcaRouter trial option** with exact old Docker ID/installed immutable release/manifest preserved, independent non-CMA memory and RM monitor state, close startup-monitor gap and stop new trial by exact ID. See [live trial design](DGX-ORCAROUTER-WIZARD-TRIAL-DESIGN.md). The installed managed runner may delete or restart the stopped predecessor on normal commit/recovery, so do not tell operator to run plain `./install.sh`, direct experimental `start`, or `systemctl restart`. No actual model start approved yet; B terminal must remain idle, five llama-benchy reports NOT_MEASURED. OrcaRouter is first and deletion held only during this test, **not permanently**; all lifecycle mutations via wizard. PR #259 stays Draft/Open/Unmerged.


## Owner scope correction: OrcaRouter first; only temporarily hold deletion (2026-10-13)

**Most recent owner clarification takes precedence over previous notes.**
Run OrcaRouter **first**, via the interactive installer/switch wizard,
then perform bounded model/API and host-RM checks before any real
llama-benchy in separate Terminal B. **Do not delete OrcaRouter during
this specific test or before its evidence is preserved. This is
NOT a permanent deletion ban.** We wrongly encoded an indefinite
`ORCAROUTER_PROTECTED` guard in model management and uninstall paths;
that code and the associated permanent-ban regression tests were
reverted. Standard ownership/dependency/wizard confirmations remain.

Once this test is concluded, OrcaRouter **can be reconsidered** as a
selective cleanup candidate, never automatically deleted. Require
owner-specific approval, benchmark preservation or documented
exception, off-host verified SHA256 copies, dependency and
recovery checks, and exact resource dry-run; no current cleanup
permission. The historically stopped Docker ID
`f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`
and immutable release require their **own** explicit disposition
decision before a live managed transition. The normal uninstall
wizard may delete the old Docker object even without model purge.

Terminal A = wizard lifecycle/cleanup previews; Terminal B =
bench/report; do not overlap mutations and benchmark. New benchmark
wrapper `with-wizard-lock.sh` holds the existing wizard operation
lock only for runs using the wrapper; it does NOT start a model or
prove host safety. Read-only OrcaRouter preflight at exact SHA
`5a14d169bbca93604b92e52dc1e548ed75cc5569` returned RC=0;
API still stopped, M1 live NOT_QUALIFIED and all five report cards
NOT_MEASURED. [Runbook](DGX-TWO-TERMINAL-WIZARD-BENCHMARK.md).
PR #259 remains Draft/Open/Unmerged.

## Owner rule: wizard-only lifecycle and separate management/benchmark terminals (2026-10-13)

**Latest owner instruction (supersedes any prior experimental-start plan):**
model installs, profile selection/switching, and uninstalls must happen
**through the interactive wizard**. User will open TWO terminal windows:
**A — management/cleanup**, **B — llama-benchy benchmark**. These are
role-separated, **not** concurrent mutation/benchmark permission.
Use [two-terminal authoritative workflow](DGX-TWO-TERMINAL-WIZARD-BENCHMARK.md).
A may perform read-only storage inventory and wizard dry-run/preview,
but real model/image/old Docker removal needs separate approval and
benchmark-preserving verified off-host copies. B only benchmarks a
previously **wizard-activated, verified-ready and host-qualified**
model, never starts/restarts it. While B measures, A does NO install,
switch, remove, prune or runtime update. A real model switch through
the wizard can start a new runtime and may delete the protected old
Docker object, so **wizard-only does not waive safety**.

Operator-provided actual DGX M1 isolated preflight
`/home/inlc/dgx-m1-experiment-preflight-20261013-143450.log`
at source `5a14d169bbca93604b92e52dc1e548ed75cc5569` returned
`M1_PREFLIGHT_RC=0`: OrcaRouter checkpoint/image ready,
service inactive, experiment absent, port 8888 free, and exact
protected stopped Docker ID/image/status unchanged before/after.
[Permanent measured preflight evidence](../scripts/benchmark/evidence/dgx-orcarouter-m1-isolated-preflight-20261013.md).
**This is NOT a model start or M1 live PASS**. Former plan to launch
the separate experiment with raw runtime script is **superseded** by
the wizard-only requirement. Existing experimental monitor
`--protect` uses managed-state stop marker by default;
do not mix its state with a wizard activation.

S1–S4 PASS read-only, all 5 benchmark reports NOT_MEASURED,
M1/M3 NOT_QUALIFIED, H38 blocked, M2/D0 destructive NOT_GRANTED,
PR #259 Draft/Open/Unmerged. Next work: wizard-safe
old-container-preserving M1 qualification + benchmark admission
without shortcuts, not another storage inspection phase.


## Latest actual DGX S4 completed and action priority (2026-10-13)

**S4=ACTUAL_DGX_PASS_READ_ONLY** at SHA `5a14d169bbca93604b92e52dc1e548ed75cc5569`, [same-SHA CI 38350725606 SUCCESS](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38350725606), operator log `/home/inlc/dgx-hybrid-link-closure-20261013-142413.log`: all H3 13, H4 76, H5 91, H6 139 symlinks source-aliased to regular files; `ALL_LINK_REFERENCE_GAPS=0`. File system ext4, device 66306, 112103874560 available bytes point-in-time, `SOURCE_MOUNT_CONTRACT=STATIC_PASS`. [Scoped S4 evidence](../scripts/benchmark/evidence/dgx-hybrid-all-link-closure-readonly-20261013.md). The whole S1–S4 **read-only evidence chain** is now complete. Do not add another storage-check stage without a material new risk.

**Next actual goal:** preserve/explicitly decide fate of the exact stopped predecessor Docker object, then approved isolated M1 live readiness and bounded host/RM protection; only after healthy served-name API attestation, real `llama-benchy` per-model capture and independently SHA256-verified raw JSON/Markdown copies, then separately approved per-object model/Docker disposal. The previous managed service commit can delete the old container, rollback can restart it. Neither a quiet single-user Spark nor this S4 PASS authorizes live restart or checkpoint removal. All five model reports `NOT_MEASURED`, M1/M3 `NOT_QUALIFIED`, H38/M4 BLOCKED, destructive M2/D0 not granted, PR #259 Draft/Open/Unmerged. Older pre-run S4 NOT_RUN snippets below are historical, superseded.


## Newly added source-only S4 follow-up gate (2026-10-13)

The [S4 runbook](DGX-HYBRID-S4-LINK-CLOSURE.md) uses `scripts/diagnostics/inspect-hybrid-link-closure.py` plus `tests/test_hybrid_link_closure.py` to check **all** H3–H6 symlinks including non-index assets. It validates builder and `serve.sh` `:ro` mount contract in source, not live Docker; reports FS type/free bytes, **not** CoW extents or reclaimability. Run only after same-head CI SUCCESS from a separate clean worktree. **ACTUAL_DGX S4 NOT_RUN** until operator log. Do not start/reclaim any model or Docker asset. Five llama-benchy reports remain NOT_MEASURED.


## Newer physical S3 actual-DGX result (2026-10-13)

Operator returned a clean exact-SHA `S3_REFERENCE_SURVEY=COLLECTED_READ_ONLY` at source `d14915549667e196356b8511526f9bfd4db42cd6`, with same-SHA GitHub CI [38349291372](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38349291372) SUCCESS. Log: `/home/inlc/dgx-hybrid-runtime-refs-20261013-141134.log`. `REFERENCE_GAPS=0`; direct/virtual shard counts base 18/0, mazinb 95/0, H3 63/3, H4 15/66, H5 48/33, **H6 0/81**. The tool classified 319 symlinks as expected parent aliases. [Immutable date-scoped evidence](../scripts/benchmark/evidence/dgx-hybrid-runtime-references-readonly-20261013.md).

**Meaning:** all unique *indexed* safetensors shards resolve through the tool's configured container aliases, not all non-shard symlink entries nor live Docker bind mounts. Source `serve.sh` has H6 and four ancestor `:ro` volume entries, but this has **not** been verified in a live container. H6 cannot be treated as independent of H3/H4/OrcaRouter. The next read-only scope is S4 all-link target/mount contract/filesystem capability review; no H6 start, asset removal or reclaim calculation is approved. Original wizard-first goal remains top priority. Five model benchmark reports `NOT_MEASURED`; old container/release/monitor/swap preserved; M1/M3 unqualified, H38 blocked, destructive M2/D0 not granted; PR #259 Draft / Unmerged. Older below lines saying S2/S3 next are historical and superseded.


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


## Latest S2 physical result and next safe gate (2026-10-13)

An actual DGX operator returned **S2=PASS_READ_ONLY** from exact source `14c67135f94b3c507a90c3a0702c83b9f3bfcda7` after same-head GitHub CI [38347956896](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/actions/runs/38347956896) SUCCESS. [Permanent scoped evidence](../scripts/benchmark/evidence/dgx-hybrid-block-accounting-readonly-20261013.md): six model trees 515623661568 allocated bytes (480.212 GiB); H3+H4 145557426176 (135.561 GiB) **not proved reclaimable**; 0 hardlink file entries, 319 symlinks (H3 13/H4 76/H5 91/H6 139), all six directories device 66306. The H3-H6 builders use virtual Docker bind-mount aliases (`/base-model`, `/h3-model`, `/h4-all`, `/h5-parent`); a host-dangling symlink does not by itself prove missing runtime data.

**Next priority S3:** safe, no-start, no-delete survey of actual symlink targets, per-stage safetensors index shard references and runtime mount topology, then reflink/snapshot caveats. Reuse existing audit scripts and model builders/validator/asset registry before adding a new tool. Do not interpret `du` as a deletion estimate, or infer that H6 runs without H3/H4/OrcaRouter. Five llama-benchy reports remain `NOT_MEASURED`; benchmark evidence and off-host verified copies are prerequisites for any separately authorized selective removal. S2 was **not** a live benchmark or host-stability acceptance. The exact predecessor Docker ID, immutable release, monitor/protect and PLE swap remain protected. PR #259 must stay Draft/Unmerged until explicit owner approval and actual gates. Older below paragraphs identifying S2 as next are **historical**, superseded by this block.


> **Canonical, reusable prompt skeleton; not a dated acceptance certificate.**
> Start a new ChatGPT conversation by linking this file and copying the section
> **"Paste into a new conversation"** below. Read the repository before acting.
> Do not infer any current Git SHA, CI result, live health or permission from an
> older transcript or from the example status in this file.

## Latest continuation priority and date-scoped physical host facts (2026-10-13)

**Precedence rule:** The newer physical A5, B5 and S1 operator evidence
supersedes earlier publication-time paragraphs that say A5/B2/B5
"next" or "NOT_RUN"; do not silently edit historical runbooks.
At the start of every new session, **re-read GitHub branch HEAD,
same-HEAD CI and PR #259**, since any SHA copied here becomes
historical once this file itself is committed.

- **Mission remains wizard-first P0:** interactive bilingual
  \`install.sh\`/\`uninstall.sh\`, original four model families
  (OrcaRouter, NVIDIA, mazinb, planned/non-installable lychee888)
  plus subsequently added Hybrid H6. H38 is only a runtime
  candidate, not a sixth model.
- **A5 ACTUAL_DGX=PASS:** exact source f2674f0..., 14/14
  read-only wizard preview checks, 60/60 scoped fixtures,
  manifest/ownership/current unchanged. No live model.
- **lychee888 L0 REAL_HUB_JSON=PASS:** revision
  \`1b3c3cedc14fb3bee4294dea5e3515af74b8268a\`,
  223047 index keys, 128 PLE shards, ten FP8 PLE files,
  one global scale, float8_e4m3fn; *metadata only*.
  No tensors downloaded, tensor headers checked or FP8 TP1
  runtime qualified.
- **B5 ACTUAL_DGX=PASS:** source c2a7317...,
  15/15 read-only installed-state checks, exact stopped
  predecessor ID \`f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24\`,
  installed immutable current release
  \`ff67bab3c94d6992f61b9535836df97f03b9c022\`,
  original installed image \`vllm-skinny-tp1:v1\`,
  Docker exited, systemd inactive/dead, monitor/protect both
  1, /swap-ple.img active. No M1 live authorization.
- **S1 ACTUAL_DGX=PASS:** exact source
  \`513623243c12c204378a0e22bb965ff47542f4f9\`,
  eight read-only storage sections rc0. Root disk 916G,
  used 765G, free 105G (88%). Managed original OrcaRouter
  171G active, mazinb 174G inactive, quant-layout H3 73G,
  H4 orca-all 64G, H5 43M, H6 34M. **H6 explicitly
  depends on H5/H4/H3/OrcaRouter** in asset registry;
  individual 73G+64G values do not establish independent
  reclaimable disk blocks. [S1 actual evidence](../scripts/benchmark/evidence/dgx-storage-pre-reclaim-readonly-20261013.md).
  Docker 10 referenced images 47.22GB with 0B immediately
  reclaimable; 6.239GB stopped-container writable layers
  listed reclaimable. Shared v0.29 image layers ~22.05GB
  each, so cannot add per-image logical 22.1GB. Open WebUI
  and Portainer are running unrelated services.
- **User's explicit order:** benchmark eligible models before
  deleting selected models or Docker assets. Five user-facing
  model reports are all \`NOT_MEASURED\`. The single-GPU
  system is currently stopped. \`llama-benchy\` benchmark
  load needs separately qualified M1 live and strict RM
  stability and exact served-model identity.
  Preserve raw JSON, derived Markdown, provenance,
  container/image/release IDs and hashes **outside deletion
  scope**, with verified independent copy. A NOT_MEASURED
  model stays HOLD unless a later per-asset explicit waiver
  is given. No automatic prune/purge, swap removal, active
  checkpoint removal, unrelated Docker modification or
  irreversible model deletion.
- **Next permitted physical DGX action:** S2 non-mutating
  allocated-block/inode/hardlink survey using
  \`scripts/diagnostics/inspect-hybrid-reclaim-blocks.sh\`.
  Needs \`QWEN38_RECLAIM_AUDIT_SHA\` = exact clean checkout
  SHA with completed SUCCESS CI, and
  \`QWEN38_RECLAIM_MODELS_ROOT\` =
  \`$HOME/Workspace/llm/qwen3.8-flash-next-dgx-spark/models\`
  (real original model directory, **not** detached audit
  worktree). Capture log and do not infer a filesystem
  extent-reclamation proof from \`du\`.
- **Gates unchanged:** M1 actual managed live and strict
  RM = NOT_QUALIFIED; M3 live pairs = NOT_QUALIFIED;
  M2 real destructive = NOT_RUN; H38/M4 = BLOCKED;
  independent disposable D0 = NOT_GRANTED.
  PR #259 remains Draft/Open/Unmerged. An available GitHub
  merge tool is a capability, **not** authorization to merge
  until relevant gates, CI, owner approval and review policy
  are met.

**Permanent rule for continuation:** Every substantive new fact,
failure, user constraint, technology reference, measured result,
risk or idea should be updated in this handoff and the matching
canonical mission/status/runbook/evidence/test source **during
the same GitHub work unit**. Preserve history, label sources,
keep command scripts reusable, avoid duplicate tool stacks.
Prefer actual edits/commits/PR/CI via GitHub connector,
without inventing DGX execution from source-only CI.
GitHub API can create commits, PRs and supported merges;
only run merge when specifically authorized and gates pass.

## Paste into a new conversation

**원래 프로젝트 P0 목표 — 쉬운 위자드 설치·삭제·전환**

단일 DGX Spark에서 **`./install.sh` / `./uninstall.sh` 대화형
위자드로 모델을 설치·삭제·전환**하는 것이 최우선 제품 목표입니다.
처음부터 목표는 (1) `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`,
(2) `nvidia/Qwen3.8-Flash-Next-NVFP4`,
(3) `mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4`,
(4) `lychee888/Qwen3.8-Flash-Next-Uncensored-NVFP4-FP8PLE`
**4개**였습니다. **후속 추가된 별도 모델**은
`orcarouter-hybrid` (generated H6)입니다. 원래 4종 중 3종과
추가 Hybrid 1종이 현재 installable이며, `lychee888`는 planned입니다.
H38은 OrcaRouter의 런타임 구현 후보이지 신규 여섯 번째 모델이 아닙니다.

**[원래 목표·모델 범위·제품 수용 기준](PROJECT-MISSION-AND-MODEL-SCOPE.md)을
새 대화에서 가장 먼저 읽으세요.** GPU/RM/H38 분석은 위자드 제품을
안전하게 완성하기 위한 하위 과제이며, H38의 미해결 사항이
무관한 위자드 구현·테스트·planned `lychee888` 작업을 계속
가로막지 않도록 합니다. 안전/승격 규칙은 그대로 지킵니다.

당신은 **Senior Python Installer / Wizard UX / Managed-Lifecycle Engineer**이며,
필요할 때 **LLM Runtime / CUDA / vLLM Engineer** 역할도 수행합니다.
단일 NVIDIA DGX Spark(GB10, aarch64)에서 모델을 위자드로 쉽게
**설치·삭제·전환**할 수 있는 제품의 개발과 검증을
**이전 작업부터 이어서 수행**합니다. 실제 서빙 준비도,
NVIDIA RM 메모리 안정성, H38 통합은 제품 목표를 안전하게
달성하기 위한 독립된 하위 검증 게이트로 다룹니다.

**저장소 및 작업 경계**

- GitHub: `kjlee-inlct/qwen3.8-flash-next-dgx-spark`
- DGX 소스 checkout: `~/Workspace/llm/qwen3.8-flash-next-dgx-spark`
- 개발 브랜치: `feat/h38-managed-integration`
- 추적 PR: [#259](https://github.com/kjlee-inlct/qwen3.8-flash-next-dgx-spark/pull/259)
- 실제 설치된 immutable release와 로컬 checkout과 GitHub branch HEAD는
  **서로 독립적인 식별자**이며 같다고 가정하지 않습니다.
- GitHub 커넥터를 사용하여 파일 읽기, 수정, commit, PR 댓글, CI 확인을
  직접 수행할 수 있습니다. 사용자가 요청하고 모든 승격 조건을 갖춘
  경우에만 PR Ready/Merge를 검토합니다. **현재 PR을 자동 병합하지 마세요.**
- DGX 쉘/Docker/systemd 실행은 GitHub API와 별개의 호스트 작업입니다.
  호스트 실행 권한이 없으면 해당 명령은 사용자에게 제공하고
  **사용자가 실제 반환한 로그만** 실기 증거로 인정합니다.

**시작 직후 반드시 읽을 상시 문서(순서대로)**

1. [docs/PROJECT-MISSION-AND-MODEL-SCOPE.md](PROJECT-MISSION-AND-MODEL-SCOPE.md): 최상위 제품 목표, 최초 네 모델과 추가 H6
2. [docs/CURRENT-STATUS.md](CURRENT-STATUS.md): 현재 상태 및 열린 게이트
3. [docs/DGX-STAGED-VALIDATION.md](DGX-STAGED-VALIDATION.md): 단계별 실기 절차
4. [docs/MANAGED-LIFECYCLE-ACCEPTANCE.md](MANAGED-LIFECYCLE-ACCEPTANCE.md): M/D 수용 기준
5. [OPERATIONS.md](../OPERATIONS.md): 실제 설치/서비스/복구 절차
6. [scripts/benchmark/evidence/README.md](../scripts/benchmark/evidence/README.md):
   실제 DGX, GitHub CI, synthetic, history를 구별하는 증거 색인
7. 최근 실제 DGX의 최신 날짜별 evidence, 이전 보호 중단 기록,
   H38 metadata/RM gate 근거를 필요한 범위에서 선택하여 읽습니다.

**즉시 재동기화할 대상**

- GitHub API에서 브랜치 **정확한 40자리 HEAD**, PR #259의 base/head,
  Draft/Open/Merged 상태, 최신 동일-head CI의 완료/성공 여부를 직접 확인합니다.
- `main`의 공식 문서와 PR branch의 미병합 수정분을 구별합니다.
  PR branch 기록은 main의 승인/승격으로 간주하지 않습니다.
- 실제 DGX 상태는 마지막 사용자가 제출한 **정확한 checkout SHA와 터미널
  출력 시점**에 한해서만 말합니다. 사용자의 추가 로그가 없다면
  GitHub CI가 PASS여도 host state가 변경됐다고 가정하지 않습니다.
- 특히 `INSTALL_ROOT`(오래된 checkout 경로)와 immutable
  `~/.local/share/qwen38-spark/current`를 문자열 동등 비교하여
  복구 오류로 판정하지 않습니다. 설치된 release의
  `manage-service.sh --runtime-root`, 실제 systemd unit 및
  설치 버전의 runner를 함께 분석해야 합니다.

**안전·승격 불변 조건**

- 단일 DGX는 사용자 단독 소유/사용 중이므로 **명시적으로 범위를 정한
  가역적 실기 런타임 테스트**는 가능한 시간에 검토할 수 있습니다.
  그러나 단독 사용자라는 이유만으로 Docker 공유 객체나 중요 모델을
  소모품으로 취급하거나 외부 D0 소유권/격리 검증을 통과시켜서는 안 됩니다.
- 임의의 `docker start`, `docker rm -f`, `systemctl restart`,
  `uninstall`, `--purge-all`, swap 조작, 기존 모델/이미지 삭제,
  일괄 `git reset --hard/clean`, 강제 push/merge, 프로파일 기본값
  자동 갱신은 **진단을 위한 기본 조치가 아닙니다**.
- 실제 시작을 검토할 경우 설치된 immutable release의 `service-runner`,
  `preflight-runtime`, `runtime-transition`의 현재 동작을 검증하고,
  사전 스냅샷, 정확한 컨테이너 ID, 모니터 유지, 관찰할 준비 신호,
  명시적 stop/rollback 조건, 상태 보존 방법을 먼저 확정합니다.
  특히 **과거 release는 일반 오류 rollback 중 이전 컨테이너를 다시
  시작할 수 있으며**, 메모리 보호 중단은 이전 컨테이너를 중지 상태로
  남기는 별도 경로입니다.
- `MONITOR_PROTECT=1`, `MONITOR_ENABLED=1`을 단순히 통과 결과를
  얻으려 낮추거나 끄지 않습니다. 모니터 중단을 HOST-STABILITY PASS나
  NVIDIA RM 오류 확정으로 해석하지 않습니다.
- `runtime-commit.env`는 실제 health와 model identity 검증 후
  관리형 runner가 생성해야 합니다. 수동 작성/복구 금지.
- GitHub CI/synthetic PASS, read-only 수집 성공, Docker exit=0,
  systemd `Result=success`는 **실제 SERVING READY / HOST-STABILITY PASS가 아닙니다**.
  valid 측정 창의 `NV_ERR_NO_MEMORY`/
  `_memdescAllocInternal`은 strict HOST-STABILITY FAIL입니다.
- H38/M4 실기 실행은 metadata/order gate와 원인 분석/안전성 조건을
  만족하기 전 **BLOCKED**. 구형 OrcaRouter의 가역적 baseline 실험과
  H38 후보 실험을 혼동하지 않습니다.
- M2 및 D1-D5 실파괴 설치/제거 검사는 독립 disposable host의 D0 인증
  및 별도 승인 없이 단일 DGX에서 실행하지 않습니다.
- PR #259는 Gate 충족 이전 **Draft/Open/Unmerged**를 유지합니다.

**진행 및 산출물 규칙**

1. 먼저 최근 evidence와 소스를 읽고 미완료 항목/가설을 분명히 적습니다.
2. 기존 스크립트/테스트/문서를 우선 활용하며, 반복되는 수동 절차는
   안전한 재사용 스크립트·테스트로 정리합니다. 이전 코드 전체를
   다시 만들거나 이미 완료된 R23–R32 원인 추적을 무근거 반복하지 않습니다.
3. 변경이 필요하면 GitHub connector로 브랜치 HEAD를 조회하고
   그 HEAD를 부모로 create tree → commit → **expected_sha** CAS
   fast-forward update → PR comment → head-matched CI 확인을 수행합니다.
   경쟁 업데이트가 있으면 최신 HEAD를 다시 읽고 변경을 재적용합니다.
   무단 force update, PR merge, 기존 사용자 checkout 초기화 금지.
4. 모든 실기 로그에는 가능한 한 checkout SHA, immutable release ID,
   manifest/profile/image, 컨테이너 ID, 시간대, 명령 범위, rc,
   stop/rollback 이유 및 환경변수 보호 상태를 남깁니다.
   출처는 `ACTUAL_DGX`, `GITHUB_CI`, `LOCAL_SYNTHETIC`,
   `SOURCE_REVIEW`, `HISTORICAL`로 명확히 구분합니다.
   비밀/토큰/민감 호스트 정보를 그대로 GitHub에 올리지 않습니다.
5. 성공/실패/부분수집을 날짜별 evidence 파일에 보존하고
   `scripts/benchmark/evidence/README.md`에 색인을 추가합니다.
   상태 문서와 runbook을 동기화하되 **과거 실패를 지우거나 소급 PASS로
   바꾸지 않습니다**. 최신 관측이 앞의 역사적 `pending`을
   대체하는 경우에는 그 관계를 명시합니다.
6. 작업 마지막에 변경 파일, 정확한 SHA, head-matched CI 결과,
   M1/M2/M3/M4/D0 상태, 실제 다음 DGX 명령 및 STOP 조건을 보고합니다.

**새 대화에서의 작업 우선순위**

1. **먼저 위자드 목표 복구:** `docs/PROJECT-MISSION-AND-MODEL-SCOPE.md`와
   모델 registry, 설치·기존설치 전환·삭제 위자드, 관련 테스트를 확인합니다.
   최초 4종과 후속 Hybrid의 실제 가능/계획 상태를 구분합니다.
2. **제품 갭 파악:** 사용자 여정(신규 설치, 모델 전환, 언어 선택,
   review/취소, 삭제/선택적 purge, 재실행/복구) 중 구현되지 않았거나
   합성 테스트만 있는 기능을 정리합니다. 미완성 `lychee888`의
   단계별 통합 경로와 현재 blocker도 정리합니다.
3. **안전한 우선 작업:** 호스트 변경 없이 가능한 wizard 코드·UX 개선,
   중복 스크립트 통합, 합성/회귀 테스트, 상시 문서 갱신을 우선 실행합니다.
   P0 진행 중 필요한 범위만 RM/H38 소스·과거 evidence를 확인합니다.
4. **실기 검증 경계:** 최근 실제 DGX Evidence는
   `docs/CURRENT-STATUS.md`와 evidence index에서 찾아 확인합니다.
   B4 시점 종료된 기존 Docker 컨테이너의 보존/교체는
   사용자로부터 새 명시적 범위 승인이 없는 한 승인되지 않았습니다.
   동작 변화를 일으키는 서비스 시작, 모델 GPU 로드, purge 등은
   이 프롬프트 자체로 허용되지 않습니다. H38/M4 BLOCKED와
   D0/M2/M3 게이트는 별도로 유지합니다.
5. **가능한 실제 작업까지 마무리:** 기존 GitHub 플러그인으로
   코드/문서 수정, commit/PR/CI를 진행할 수 있지만, PR 승격·병합은
   별도 게이트를 요구합니다. 결과는 테스트 출처와 SHA를
   구분해 남기고, 다음 단계는 **위자드 제품 완료** 기준으로 제시합니다.

- 원래 4번째 `lychee888`의 현재 구현 불가 원인은
  [FP8 PLE 통합 계획](LYCHEE888-WIZARD-INTEGRATION.md)을 참고합니다.
  공개 모델의 dual-DGX 구동 사례를 단일 Spark TP=1 준비 완료로
  취급하지 마세요. L0/L1 준비와 L2 실기 승인을 구분합니다.

**새 대화에 첨부할 선택 입력**

```text
LAST_LOCAL_DGX_CHECKOUT_SHA=<실제 확인한 40자리 SHA 또는 UNKNOWN>
LATEST_DGX_COMMAND_AND_OUTPUT=<최근 실제 호스트 로그>
REQUESTED_NEXT_STEP=<이번 단계 목표, 예: legacy OrcaRouter M1 reversible preflight>
HOST_CHANGE_APPROVAL_SCOPE=<사용자가 실제 승인한 테스트 범위; 불명확하면 NONE>
```

---

## Maintainer update discipline

This file is a stable prompt **template**. Do not freeze the GitHub feature HEAD
or the current CI run number into it. The durable dated evidence and
`docs/CURRENT-STATUS.md` supply the recent facts. When project invariants,
branch/PR identity, source-of-truth paths, available workflows or stage
boundaries change, update this file alongside the code and docs in the same PR.

Avoid embedding transcripts or secrets here. A new session must discover all
tools and repository status anew instead of claiming prior connector auth or
live host access. A new chat can reference this URL and copy the prompt even
when the previous conversation is unavailable.


**즉시 실행할 DGX 위자드 검증 A5(2026-10-13):**
[docs/DGX-WIZARD-A5-READONLY.md](DGX-WIZARD-A5-READONLY.md)을
읽고, 정확한 성공 CI HEAD로 별도 detached worktree에서
`scripts/diagnostics/check-wizard-dgx-readonly.sh`의
설치/전환/삭제 **dry-run만** 물리 DGX에서 수행합니다.
메인 checkout/current release/Docker/swap는 변경하지 않습니다.
호스트 로그 없이 A5 PASS로 표시하지 않습니다.
이는 기존 B4와 독립된 새 위자드 검증이며 M1 라이브 전환의
승인이나 오래된 Docker ID 삭제 동의가 아닙니다.


**2026-10-13 실제 DGX 업데이트:** A5 정확한
`f2674f0` source에서 14/14 preview/status rc0 및
60/60 fixture tests, manifest/ownership/current 불변
`PREVIEW_AND_FIXTURES_PASS`. `lychee888` 실제 Hub
metadata `1b3c3cedc14fb3bee4294dea5e3515af74b8268a`
`INDEX_STRUCTURE_PASS_METADATA_ONLY`.
[원본 근거](../scripts/benchmark/evidence/dgx-a5-wizard-and-lychee-l0-result-20261013.md).
다음 실제 DGX 과제는 구형 OrcaRouter M1의 B5 읽기
전용 go/no-go 및 기존 Docker ID 삭제·롤백/재시작 위험
확정입니다. H38 / 실삭제는 여전히 금지된 단계입니다.


**다음 물리 DGX 단계 B5:** [읽기 전용 구형 OrcaRouter M1 사전 점검](DGX-LEGACY-M1-B5-PRESTART.md).
정확한 source SHA와 기존 Docker ID, immutable 릴리스,
monitor/protect=1, swap, systemd 상태를 확인하는 검사로
Docker/service mutation이 없습니다. 로그 확인 후에도
old container ID 삭제 허용 또는 독립 격리 방식의 결정
없이는 runtime startup을 실행하지 않습니다.

## 상시 운영 규칙 — 아이디어·규칙·참고자료 자동 문서 반영 (2026-10-13)

- **추가 규칙/아이디어/외부 참고자료/중요 기술 결정/실패가 나타나는 즉시**
  이 인계 문서와 대응하는 canonical source-of-truth 문서를 **같은 PR의
  커밋에서 업데이트**합니다. 사용자가 반복하여 요청하게 하지 않습니다.
  상태가 바뀌면 `docs/CURRENT-STATUS.md`, 새 출처가 있으면 참고 링크,
  실행 근거가 생기면 날짜별 evidence와 색인을 함께 갱신합니다.
- 새 외부 참고자료는 원문 URL, upstream **immutable SHA/버전**, 검토일,
  라이선스, 지원 API/필요 의존성, 도입 근거, 불명확한 사항, 재현 절차와
  **단일 DGX 위험/허용 게이트**를 기록합니다.
- **성능 보고서 표준:** [`eugr/llama-benchy`](https://github.com/eugr/llama-benchy)
  (MIT, 검토 핀 `e9be344578cec17745066b220798b80a0d2686d3`).
  [모델별 5개 리포트 및 측정/재현 규칙](model-reports/README.md).
  새 리포트 생성은 실제 API 정상/별도 M1 안정성 Gate 충족 후에만,
  `llama-benchy --format json --save-result`의 원시 증거를
  `scripts/benchmark/llama-benchy-report.py`로 **오프라인** 변환.
  실측값이 없는 프로필은 **NOT_MEASURED**로 유지하고,
  GITHUB_CI/ACTUAL_DGX/HISTORICAL 출처를 혼합하지 않습니다.
  benchy도 API 부하를 주므로 무승인 서비스 시작·모델 전환 절대 금지.
- 2026-10-13 DGX B5 실제 사전 검사:
  [B5 안전성 15/15 읽기 전용 PASS](../scripts/benchmark/evidence/dgx-b5-legacy-orcarouter-prestart-readonly-20261013.md),
  소스 `c2a73179...`, 기존 릴리스 `ff67bab3...`,
  컨테이너 `f6bfee5a...` ID 유지, inactive/dead, protect/monitor=1,
  /swap-ple.img 활성, disk 105G free. **M1 LIVE 아직 BLOCKED**:
  기존 Docker object ID 교체/삭제 동의 및 old-release rollback/STOP
  계획이 없으며 H38 실기/RM 승격과 관계없습니다.


## Evergreen owner rule — benchmarks before model/Docker space reclamation (2026-10-13)

- The user intends to recover disk by eventually deleting SELECTED
  models or Docker artifacts; archive model-specific quantitative
  benchmarks **before deletion**. This is not authorization for
  unconditional cleanup or sacrifice of the old stopped Docker ID.
- Immediately before proposing candidates run the
  read-only inventory documented at BENCHMARK-BEFORE-RECLAIM.md.
  Existing storage/model manager status, recommend, plan and assets
  commands are preferred; no second deletion implementation.
- Each affected model needs true llama-benchy raw JSON, generated
  Markdown, source/release/image/checkpoint identity, strict RM
  outcome, hashes and an archived off-scope copy. Missing benchmark
  is HOLD/NOT_MEASURED unless separately and explicitly waived.
- Preserve Hybrid shared dependencies, Docker layer sharing, PLE
  swap, active/current/previous state and the exact stopped OrcaRouter
  container until full individually scoped safety/ownership approval.
- For every new rule/idea/reference update this handoff and relevant
  canonical docs together with project work (ongoing).


## DGX S1 actual storage inventory — persistent handoff (2026-10-13)

Physical DGX checked exact SHA 513623243c12c204378a0e22bb965ff47542f4f9:
eight read-only inspections PASS. See
[DGX actual S1 storage evidence](../scripts/benchmark/evidence/dgx-storage-pre-reclaim-readonly-20261013.md).
Disk 105G free; OrcaRouter 171G ACTIVE; mazinb 174G;
H3 73G, H4 64G, H5 43M, H6 34M. H6 model asset depends
on H5/H4/H3/OrcaRouter. NEVER assume small H6 footprint
means the large intermediates can be safely discarded.
The 137G H3/H4 sum is nominal, not proven reclaimable.

Docker: 10 referenced images, 47.22GB, 0B presently
reclaimable; R25-R28 and H38 share ~22.05GB layers each.
24 containers, 2 running (Open WebUI and Portainer).
6.239GB old writable layers listed reclaimable only
after evidence/ownership review. Old stopped canonical
Docker ID f6bfee5a4217... stays protected.
The next read-only accounting script is
scripts/diagnostics/inspect-hybrid-reclaim-blocks.sh; require
exact SHA and QWEN38_RECLAIM_MODELS_ROOT pointing to
the REAL original models root. It never deletes files.
llama-benchy 5/5 model reports still NOT_MEASURED.
Keep updating handoff + canonical evidence/status on each
new owner priority, external reference or observation.
