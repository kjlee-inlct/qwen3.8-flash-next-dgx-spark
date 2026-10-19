# Physical DGX — mazinb R2 pinned download completed, reinstall M1 preflight PASS

**Date:** 2026-10-19. **Evidence source:** verbatim key lines and lossless
filename-range accounting from the owner's live DGX Wizard output provided
in conversation. The original terminal transcript, including 108
individual `verified ...` lines, remains in the conversation;
this file is a human-curated permanent receipt. It is **actual physical
DGX evidence**, not a source-only CI result. Its source Git SHA was
**not printed** in this terminal excerpt: do not invent one.

## Stage A: authorized model download and file validation

Wizard Models **3 → 12** completed an explicit owner-approved
checkpoint restore, isolated from protected installed OrcaRouter:

```text
MAZINB_RESTORE_DOWNLOAD=EXPLICITLY_APPROVED
Using containerized Hugging Face downloader
  image       : vllm-orcarouter-v029:v1
  workers     : 8
  xet highperf: 1
  missing     : 108 files
snapshot_download: repo=mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4 revision=f2c21eb3d2ff5f24c208ea7e3afba65e2e70f83f files=108 workers=8 dest=/download
hf_xet: available (high-performance mode)
Fetching 108 files: 100%|██████████| 108/108 [4:20:52<00:00, 144.93s/it]
done -> /home/inlc/Workspace/llm/qwen3.8-flash-next-dgx-spark/models/qwen3.8-flash-next-mazinb (174G), revision f2c21eb3d2ff5f24c208ea7e3afba65e2e70f83f
MAZINB_RESTORE_DOWNLOAD=COMPLETE_DOWNLOADER_VERIFIED
MAZINB_RESTORE_GPU_START=NOT_PERFORMED
✓ Checkpoint download verified. GPU/start NOT performed. Next use Benchmark M1 reinstall preflight.
```

The `108/108` progress counts files, not an exact byte fraction.
The output included **108 individually verified filenames**, with
the following *lossless* inventory by basename:

- 48 `experts-layerNN.safetensors` files, NN = `00` through `47`.
- 43 `ple-bf16-NN.safetensors` files, NN = `00` through `42`.
- 4 `model-bf16-NNNNN.safetensors`: `00001`, `00010`,
  `00011`, `00012`.
- 13 named auxiliary assets: `LICENSE`, `README.md`,
  `chat_template.jinja`, `config.json`,
  `generation_config.json`, `hf_quant_config.json`,
  `merges.txt`, `model.safetensors.index.json`,
  `preprocessor_config.json`, `tokenizer.json`,
  `tokenizer_config.json`, `video_preprocessor_config.json`,
  `vocab.json`.

The validated count is **48 + 43 + 4 + 13 = 108**.
This receipt documents the downloader's own post-transfer
size/hash validation success, not a separately archived
SHA256SUMS file or independently rerun hash command.
Do not infer checkpoint runtime readiness from file validation.

The Hugging Face downloader accepted optional login tokens
according to `scripts/download-weights.sh`, but this output
does not reveal whether the running process used a nonempty token.
It does show `hf_xet` high-performance mode and eight workers.

## Stage B: actual reinstall M1 read-only physical admission

After Stage A, owner entered Wizard **5 → 24 → 3**,
acknowledged the exact full predecessor Docker ID and
authenticated read-only `sudo` for kernel RM inspection.
The physical program produced:

```text
M1_PROTECTED_PREDECESSOR_ID=f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24
M1_PREFLIGHT=PASS_READ_ONLY
M1_OLD_DOCKER_ID=f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24
M1_IMMUTABLE_RELEASE=/home/inlc/.local/share/qwen38-spark/releases/ff67bab3c94d6992f61b9535836df97f03b9c022
M1_IMAGE_ID=sha256:dba5d8af279fb85901e6d8911f1a59ecc45b669b0948ab8d01d7c7d1c5815734
M1_CANDIDATE_START=NOT_PERFORMED
```

Installed manifest screen still `valid (phase=complete)`,
`Profile: orcarouter`, `Image: vllm-skinny-tp1:v1`,
`Runtime: NOT_PROBED`. The physical output does **not**
prove a newly created/stopped model Docker, watchdog arm,
API health, smoke inference, soak, or benchmark.

## Explicit remaining qualification gates

1. **Next separate owner opt-in**, Wizard **5→24→4**:
   default-NO GPU approval; type full exact predecessor ID;
   type `START_RESTORED_MAZINB_16G`; fresh kernel RM
   authentication as required. Remain in Terminal A.
2. Only after exact new M1 journal and running watchdog,
   matching served API, 180-second protected soak, inference
   smoke and kernel RM PASS, expect
   `M1_READY_FOR_BENCH=http://127.0.0.1:18889`.
   This is a **future marker**, not contained in the observed
   physical transcript.
3. Terminal B obtains the **reinstall** benchmark lease,
   verifies historical + current resources, checks pinned
   `llama-benchy`, writes new evidence and SHA256.
   Terminal A `STOP` only after benchmark completes.
4. Do **not** delete/recreate archived old M1, A/B,
   installed OrcaRouter Docker/model, shared images,
   swap, systemd, or the newly restored checkpoint
   to circumvent errors. No persistent service exists
   merely because the isolated foreground API becomes ready.

Keep actual source HEAD clean and **unchanged between Terminal A
start and Terminal B post-admission**. The physical output
did not include a `git rev-parse HEAD` receipt.


## Stage C: ACTUAL physical owner-approved protected trial reached STARTED_UNQUALIFIED

**2026-10-19 operator console, later than the Stage A/B evidence above.**
The operator ran a read-only prestart check with:

```text
DGX_SOURCE_SHA=4612045c11ce47e52606794d63daede4cb35ac82
BENCHY=NOT_INSTALLED
BENCH_RESULT_DIR=READY
```

`git status --short` showed **no modified/untracked entries**.
The local DGX source is intentionally still pinned to this known
pre-download CI-successful commit, **not** the newer GitHub
documentation-only HEAD; do not run `git pull` during the trial.

The owner then explicitly selected Wizard **5 → 24 → 4**,
answered `y` to the default-NO new GPU session approval,
confirmed the full protected old Docker ID
`f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`,
typed `START_RESTORED_MAZINB_16G`, and the physical program printed:

```text
M1_CANDIDATE_STARTED_UNQUALIFIED=qwen38-mazinb-m1-20261019043708-479dfc86
```

This is **ACTUAL_DGX STARTED_UNQUALIFIED**, not `M1_READY_FOR_BENCH`
or a new benchmark. Per the executing controller source the marker
is printed after exact-ID creation/start and watchdog arm/heartbeat
admission; the owner's excerpt does not independently include the
new full container ID, watchdog logs, exact API identity, memory
telemetry, RM kernel audit, 180-second soak or inference smoke.
Those remain subject to actual live controller output.

**Benchmark tooling readiness:** `llama-benchy` was **not
on operator PATH**, while the result parent directory existed.
The new R2 benchmark script requires exactly
`0.4.1.dev1+ge9be34457`, must not install a benchmark package
implicitly, and must not run without exact
`M1_READY_FOR_BENCH`. A bounded, read-only search for an existing
isolated benchy environment is permitted from a separate terminal;
do not install packages or modify Git/live service during
ongoing protected GPU session. If no pinned benchy exists,
stop only the new candidate via the foreground controller's
explicit supported STOP after readiness or its protected failure
path, and prepare a properly pinned benchmark environment
**between** sessions. Never bypass the exclusive M1 benchmark lease.

Any earlier **NOT_EXECUTED** statements in this evidence file
refer to Stage B's earlier checkpoint; this Stage C is later.


## Stage D: ACTUAL physical M1 inference/soak READY — 2026-10-19

**Later operator-pasted continuation of the same protected R2 session**, while
Terminal A remains in the supervised foreground. On the locally executed
**clean Git HEAD `4612045c11ce47e52606794d63daede4cb35ac82`**, the M1 runtime
progressed beyond Stage C and printed:

```text
M1_CANDIDATE_STARTED_UNQUALIFIED=qwen38-mazinb-m1-20261019043708-479dfc86
M1_INFERENCE_SMOKE=PASS_NO_GENERATED_TEXT_PERSISTED
M1_READY_FOR_BENCH=http://127.0.0.1:18889
M1_SERVED_NAME=mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4
M1_EXACT_CONTAINER_ID=82b143c4adad9fd785aad38590ed6738de52a6a06b06a4a9bdc07118ceb40424
M1_TRIAL_RECORD=/home/inlc/.local/state/qwen38-spark/mazinb-m1-reinstall/active.json
M1_LLAMA_BENCHY=NOT_MEASURED; run pinned benchmark in Terminal B
Type STOP and Enter in this Wizard terminal to stop exact M1 candidate.
```

**VERDICT: actual single-DGX R2 isolated vLLM M1 passed controller-qualified
exact-model localhost API, 180-second protected soak, smoke inference and
pre-READY monitored safety checks.** Evidence classification is
`ACTUAL_DGX_READY_FOR_BENCH`, NOT yet a benchmark result or
boot-persistent managed service. The source controller implements (in
order) model identity API check, 36 five-second soak iterations,
watchdog/host and RM verification, inference smoke, journal
`ready_for_bench` then READY stdout. The transcript is evidence of
the latter marker, not independent telemetry capture or a long-term
host-stability result.

Protected old OrcaRouter:
`f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`.
New R2 isolated experimental Docker **exact ID** above must never
be confused with the protected original.

**Benchmark remains blocked by tooling until proven otherwise:**
earlier independent physical Terminal B probe found
`BENCHY=NOT_INSTALLED` on shell `PATH`, although
`BENCH_RESULT_DIR=READY`. Search for an existing,
unmodified, pinned version (no `pip install`, `git pull`,
container change or watchdog interference during the live
session). Even if found, use the strict reinstall-slot
exclusive benchmark lease/wrapper only while Terminal A
continues supervising and reporting `ready_for_bench`.
If no pinned benchy exists, use Terminal A's supported STOP
and prepare the tool between sessions. New measured JSON,
sha256, post-bench attestation and safe stop have **not**
been reported by the owner. Avoid claiming any.

**Earlier Stage B/C 'NOT_YET_READY' statuses are chronologically
superseded by this Stage D only; no historical records removed.**


## Stage E: ACTUAL R2 Terminal B benchmark admission passed but executable missing

**Later 2026-10-19 operator-pasted terminal B output**, against the
still-supervised Terminal A `READY_FOR_BENCH` session above:

```text
MAZINB_R2_BENCH_MODEL=mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4
MAZINB_R2_BENCH_API=http://127.0.0.1:18889/v1
MAZINB_R2_BENCH_BENCHY_VERSION=0.4.1.dev1+ge9be34457
MAZINB_R2_BENCH_SHAPE=PP512_2048_TG128_C1_DEPTH0_WARMUP1_RUNS3
MAZINB_R2_BENCH_READY=REQUIRES_LIVE_TERMINAL_A_M1_READY_FOR_BENCH
MAZINB_R2_BENCH=PLAN_ONLY_NO_API_OR_HOST_MUTATION
M1_BENCH_ADMISSION=PASS_SESSION_PINNED_READ_ONLY
M1_BENCH_CONTAINER_ID=82b143c4adad9fd785aad38590ed6738de52a6a06b06a4a9bdc07118ceb40424
M1_BENCH_API=http://127.0.0.1:18889
M1_BENCH_HOST_RM=NO_MATCHING_EVENTS_IN_CURRENT_WINDOW
BENCH_M1=ATTESTED_SHARED_LIFECYCLE_EXCLUSIVE_BENCH
BENCH_MODEL_START=NOT_PERFORMED_BY_WRAPPER
BENCH_READY_AND_HOST_SAFETY=EXTERNAL_PREREQUISITES
MAZINB_R2_BENCH=BLOCKED_PINNED_LLAMA_BENCHY_MISSING
M1_BENCH_ADMISSION=PASS_SESSION_PINNED_READ_ONLY
M1_BENCH_CONTAINER_ID=82b143c4adad9fd785aad38590ed6738de52a6a06b06a4a9bdc07118ceb40424
M1_BENCH_API=http://127.0.0.1:18889
M1_BENCH_HOST_RM=NO_MATCHING_EVENTS_IN_CURRENT_WINDOW
BENCH_COMMAND_RC=2
```

**Interpretation:** The strict reinstall-slot benchmark wrapper acquired
the shared lifecycle + exclusive benchmark locks. Both independent
**pre-admission and post-admission PASS** attested the exact new Docker,
local model API and absence of matching RM events in each queried
window. The payload refused to proceed because `llama-benchy`
was not found on the operator's `PATH`. `RC=2` is the
benchmark command's *missing-tool* status and not an inference,
watchdog, checkpoint or host instability failure.

**No benchmark generation was invoked; no new PP/TG throughput,
TTFT or raw JSON exists from this attempt.** A later terminal A
STOP/expiry status was not supplied at this stage. While the
bounded live session is still active, only a *scoped, read-only*
search for a previously installed exact-pinned CLI is recommended.
Do NOT `git pull`, install/up/downgrade packages, update PATH
globally, restart inference, bypass benchmark lease, or run a
new model. If no existing CLI is found, finish via watched
Terminal A `STOP` (unless it already ended), then provision and
qualify the tool before a *new separately authorized* GPU run.

Earlier stage D API/soak/smoke PASS still stands. This is
a **tooling-blocked benchmark attempt**, not a failed
mazinb inference trial.


## Stage F: path search empty; sudo expiry separately repaired, no new measurement

**Additional actual DGX Terminal B output** from the owner after Stage E:

1. Bounded `find` under `~/.local/bin`, uv tools, pipx venvs and
   `~/Workspace/llm` printed **no existing executable**. It is not
   proof that no `llama-benchy` executable exists anywhere else.
2. The user's variable `BENCHY_PATH="/실제로/확인한/경로/llama-benchy"`
   is an **unreplaced illustrative placeholder**, not an observed
   path. Execution produced
   `-bash: /실제로/확인한/경로/llama-benchy: 그런 파일이나 디렉터리가 없습니다`.
3. A subsequent wrapper invocation was blocked **before**
   acquiring an admitted benchmark lease:
   `M1_BLOCKED=command failed: sudo -n; rc=1; sudo: 암호가 필요합니다`
   and `BENCH_M1=BLOCKED attestation_failed`. This is **expired
   cached sudo authentication required for read-only kernel
   evidence**, not a GPU failure.
4. After the owner separately ran `sudo -v`, another strict
   wrapper invocation printed **M1_BENCH_ADMISSION=PASS...**
   both before and after the payload, matching unique R2 Docker
   `82b143c4adad9fd785aad38590ed6738de52a6a06b06a4a9bdc07118ceb40424`;
   the payload still refused with
   `MAZINB_R2_BENCH=BLOCKED_PINNED_LLAMA_BENCHY_MISSING`
   and `BENCH_COMMAND_RC=2`.

**No measured samples**, no R2 result file. Neither the owner nor
the project has yet provided an actual Terminal A `STOP` or
auto-expiry receipt.

**Source-only tool provisioning change:** a new
`scripts/wizard/llama-benchy-setup.sh` installer (Wizard
`5→24→5`) is written in GitHub and remains **NOT EXECUTED**.
Its `--plan` is mutation-free; `--install` requires default-NO
Wizard approval plus typed phrase `INSTALL_PINNED_BENCHY`,
an exclusive already-existing project lifecycle lock,
no running `qwen38-` Docker or M1 API port listener,
and installs the exact pinned Git source commit into an
owner-only user venv outside the active repository.
No system packages/GPU/Docker operations, and no checkout
synchronization while the R2 candidate is live. The script's
source CI and physical host compatibility must be separately
qualified before use. **It has not installed anything on DGX.**

Live session duration is bounded at 5400 seconds from startup:
owner-supplied experiment name timestamp ~`20261019T043708Z`
(13:37:08 KST), so automatic expiry *approximately*
15:07 KST in the absence of earlier STOP/abort. Only
physical terminal/journal output can confirm stop.

## Stage G: actual exact-ID STOP with Docker retained (2026-10-19)

**Later physical Wizard Terminal A transcript from owner**, after the
Stage D ready-for-benchmark result and Stage E/F tool-not-found
admission refusals:

```text
M1_INFERENCE_SMOKE=PASS_NO_GENERATED_TEXT_PERSISTED
M1_READY_FOR_BENCH=http://127.0.0.1:18889
M1_SERVED_NAME=mazinb/Qwen3.8-Flash-Next-Uncensored-NVFP4
M1_EXACT_CONTAINER_ID=82b143c4adad9fd785aad38590ed6738de52a6a06b06a4a9bdc07118ceb40424
M1_LLAMA_BENCHY=NOT_MEASURED; run pinned benchmark in Terminal B
Type STOP and Enter in this Wizard terminal to stop exact M1 candidate.
STOP
M1_STOPPED_EXACT_ID=82b143c4adad9fd785aad38590ed6738de52a6a06b06a4a9bdc07118ceb40424
M1_DOCKER_REMOVED=NO
```

**ACTUAL DGX exact-ID stop is CONFIRMED** for only the newly
created R2 trial candidate; the candidate Docker was **NOT removed**,
as the evidence journal and stopped-object forensics must be
preserved. This output does NOT independently print journal
`M1_SESSION_PHASE=stopped` or `M1_RUNNING=False`: run
the read-only session-status command as a separate confirmation
before any source fast-forward or package installation.
Do not infer external systemd/boot-persistent status from the
isolated foreground trial. Original protected OrcaRouter
predecessor
`f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24`
and prior M1 evidence remain out of scope and untouched
by the R2 exact-ID stop.

No new benchmark result was generated because the
pinned `llama-benchy` executable was missing. **Final trial
classification:** `FUNCTIONAL_API_AND_SMOKE_PASS`,
`MONITORED_SOAK_PASS`, `PROTECTED_EXACT_ID_STOP_PASS`,
`BENCHMARK_NOT_MEASURED_TOOL_MISSING`. Further action:
observe stopped journal, sync Git only after stop/clean
repo, install strict pinned benchmark tool separately,
and obtain a new explicit GPU approval for another trial.


## Stage H: second separately approved R2 trial protective NVIDIA RM fail-closed (2026-10-19)

**Actual physical DGX terminal output pasted by owner**, later than
Stage G's first successful API/soak/smoke + STOP. A new isolated,
separately owner-approved Wizard **5→24→4** trial was attempted
after the first Docker had stopped; its selected source HEAD
was not printed in this second-trial excerpt. New Wizard
menu included **5 Pinned llama-benchy setup**. Operator's
new trial output:

```text
Approve NEW GPU-heavy isolated mazinb live session? / 새 GPU 실행 승인? [y/N]: y
M1_PROTECTED_PREDECESSOR_ID=f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24
Type START_RESTORED_MAZINB_16G exactly []: START_RESTORED_MAZINB_16G
M1_CANDIDATE_STARTED_UNQUALIFIED=qwen38-mazinb-m1-20261019065452-e70d6233
M1_STOPPED_EXACT_ID=68cd243882bf117dbccdfad577cfdec7a95063ee8f2a96dbe6bcf51cfd8554e7
M1_DOCKER_REMOVED=NO
M1_BLOCKED=NVIDIA RM memory allocation error
```

**New unique failing candidate:** Docker exact ID
`68cd243882bf117dbccdfad577cfdec7a95063ee8f2a96dbe6bcf51cfd8554e7`,
**not** the earlier successful/stopped
`82b143c4adad9fd785aad38590ed6738de52a6a06b06a4a9bdc07118ceb40424`.
The new container was stopped by exact ID, preserved for
forensic examination, and **did not reach** API READY,
smoke or 180-second soak. No second-trial benchmark.

Operator Terminal B independently confirmed exact required
pinned `llama-benchy 0.4.1.dev1+ge9be34457`
was now present and runnable after user PATH setup.
But the protected wrapper rejected the attempt:

```text
M1_BLOCKED=M1 is not admitted for benchmark
BENCH_M1=BLOCKED attestation_failed
```

This is **correct fail-closed admission**, not a missing-tool
condition. The reporter's `M1_BLOCKED=NVIDIA RM memory
allocation error` is issued by `verify_host` when
`sudo -n journalctl -k --since <record.kernel_since>`
contains `NV_ERR_NO_MEMORY` or
`_memdescAllocInternal`. This is a **host-wide**
kernel log time-window scan, not a container-specific
kernel error attribution. The matching lines/timestamps,
Docker OOMKilled/exit code, actual unified memory and
swap pressure, loading-phase Docker/monitor traces, and
trial journal have **not been furnished** yet. Do not
state the second Docker caused the RM error solely from
the classifier label. The stdout does show exact-ID
stop, but no independent after-stop `M1_RUNNING=False`
status yet.

**Next: no third GPU attempt.** Obtain read-only evidence
from the exact stopped new Docker, state
`~/.local/state/qwen38-spark/mazinb-m1-reinstall/active.json`
(phase may be `failed_stopped`),
`qwen38-mazinb-m1-20261019065452-e70d6233/monitor.log`,
and the **host kernel RM log since journal
`kernel_since`**. Capture exact matching RM lines with
timestamps, avoid disabling watchdog or changing
swap/KV, thresholds, Docker state, image or source.
Keep both stopped M1 Docker objects and historical A/B
forensics untouched. The previous first-trial functionality
PASS and new second-trial RM FAIL are **separate physical
events**; no new PP/TG measurement for either trial.
