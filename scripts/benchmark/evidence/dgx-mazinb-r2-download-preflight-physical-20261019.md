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
