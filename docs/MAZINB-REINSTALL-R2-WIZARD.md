# mazinb R2 — pinned checkpoint restore and bounded isolated API benchmark

**Status: ACTUAL DGX restored 108/108 + protected R2 localhost API READY + 180-second monitored soak + inference smoke PASS on 2026-10-19; new llama-benchy measurements still NOT OBSERVED, permanent systemd service NOT QUALIFIED.**
This does **not** claim an installed long-running service or a new
benchmark result. It restores the 2026-10-14 measured *checkpoint
revision* without reusing or modifying the retired historical M1
Docker journal/tombstone or the managed OrcaRouter predecessor.

## 2026-10-19 — actual protected R2 benchmark admission passed; tool absent

Physical Terminal A passed API exact model, 180-second monitored
soak and `M1_INFERENCE_SMOKE=PASS_NO_GENERATED_TEXT_PERSISTED`
and showed `M1_READY_FOR_BENCH=127.0.0.1:18889`
(the actual API marker contains `http://`).
New unique Docker ID:
`82b143c4adad9fd785aad38590ed6738de52a6a06b06a4a9bdc07118ceb40424`.
Physical Terminal B `m1-benchmark-lock.sh --session-slot reinstall`
reported pre-admission PASS, safe exclusive lease acquisition,
`BLOCKED_PINNED_LLAMA_BENCHY_MISSING`, post-admission PASS,
`BENCH_COMMAND_RC=2`. No PP/TG/TTFT measurement exists yet.

A search under the user's local bin/uv/pipx and llm workspace
returned no `llama-benchy`. The operator accidentally copied
an illustrative `/실제로/확인한/경로/llama-benchy` placeholder;
that is **not** an executable file. `sudo -n` also refused an
expired read-only kernel audit credential on the first retry;
`sudo -v` restored pre/post host/RM checks on the next retry.
Neither error is a model or GPU inference fault.

### After Terminal A STOP/auto-expiry only — install pinned tool

Do **not** change the executing DGX Git HEAD while Terminal A
is live. End the supervised trial with `STOP` once it is
accepting input; otherwise record the automatic-stop or
failure result. Use Wizard **5→24→2** for R2 stopped status.
Retain the stopped exact Docker, trial journal and original
2026-10-14 evidence. Never broad-prune.

After the trial **has physically stopped**, source sync to an
exactly verified successful remote branch HEAD is a separate
operation; only then can new Wizard **5→24→5** be used.
It shows a read-only tool plan before an explicit default-NO
installation approval. The setup script asks for typed
`INSTALL_PINNED_BENCHY`, refuses if any project lifecycle
shared/exclusive lock or running project Docker/M1 API port
is detected, and installs pinned
[eugr/llama-benchy](https://github.com/eugr/llama-benchy/tree/e9be344578cec17745066b220798b80a0d2686d3)
at `e9be344578cec17745066b220798b80a0d2686d3`
to a dedicated user-owned venv **outside** the project
checkout and managed install root:
`~/.local/share/qwen38-benchmark-tools/llama-benchy-e9be34457`.
Expected CLI version is `0.4.1.dev1+ge9be34457`.
The installer verifies all required flags and records a
dependency freeze with SHA256; dependency versions are
not independently hash-locked by the source SHA.
No sudo, implicit system packages, Docker, GPU or model changes.
If `venv`/pip/git/dependency fetch fails, it **blocks** and
retains the partial user-only directory for manual review.

Exact command-line counterpart after STOP, when the verified
new source is checked out:

```bash
bash scripts/wizard/llama-benchy-setup.sh --plan
# Only after checking the plan and with separate explicit owner approval:
QWEN38_BENCHY_SETUP_APPROVED=1 \
  bash scripts/wizard/llama-benchy-setup.sh --install
```

Before a *new* independently approved protected GPU trial:
```bash
export PATH="$HOME/.local/share/qwen38-benchmark-tools/llama-benchy-e9be34457/bin:$PATH"
llama-benchy --version
llama-benchy --help
```

Then repeat the R2 physical preflight and separate Wizard
**5→24→4** GPU start. On a new actual `M1_READY_FOR_BENCH`,
and only while the foreground watchdog remains alive,
run the standard **Terminal B** lease+payload under the
same exact clean Git HEAD. Since RM attestation uses
`sudo -n` during postcheck, obtain a fresh `sudo -v`
in Terminal B before beginning; do not weaken RM/monitor
gates or share credentials in transcripts.

Remember: `llama-benchy` can download its default
Project Gutenberg prompt corpus on first run and may
reuse `~/.cache/llama-benchy`. This is an external
network/corpus provenance dependency distinct from
the pinned benchmark executable and local tokenizer;
retain evidence if it changes.

**New bench setup code is SOURCE-ONLY until CI+physical
validation; its existence does NOT prove the user has
installed or executed it.**

## Why a separate R2

The 2026-10-19 actual DGX audit at
[the physical evidence](../scripts/benchmark/evidence/dgx-mazinb-retirement-audit-physical-20261019.md)
proved that the original ~174 GiB mazinb source checkpoint and five
stopped historical mazinb Docker objects were already removed, while
the original benchmark JSON/report, SHA256 and M1 retirement receipt
were preserved. The installed OrcaRouter profile's service was disabled
and project-managed API/boot exposure was physically absent.
The older M1 launcher required `SERVICE_ENABLED=1`, and its
`mazinb-m1/active.json` refers to a retired Docker object.
Reusing this old journal or blindly starting systemd would be unsafe.

**R2 new state root:** `~/.local/state/qwen38-spark/mazinb-m1-reinstall`.
The historic `mazinb-m1/active.json`, `retired-docker.json`,
benchmark evidence and original Docker archive are unchanged.
The new controller hash-pins both historical files, the immutable
project source HEAD, predecessor Docker ID/image, installed manifest
and release. It requires `SERVICE_ENABLED=0` and `SERVICE_OWNED=0`,
managed system/user API ports and boot units idle; it fails closed on
unverified host/container state. The old original M1 CLI defaults
and historical state root remain unchanged.

## Stage 1 — download admission (NO weights, no GPU)

Run the **exact CI-passed GitHub HEAD** from a clean, canonical checkout,
then `./wizard.sh` -> **3 Models -> 11 restore preflight**.
This calls `scripts/wizard/mazinb-restore.sh preflight`.
It verifies installed OrcaRouter manifest + model root, managed
host idle, symlink/partial-manifest provenance, pinned Hub metadata,
revision equality and available disk **plus 20 GiB reserve**.
It does not change models, services or containers. It may fetch
small JSON metadata through HTTPS; it does not download weights.

**Pinned mazinb Hugging Face checkpoint SHA:**
`f2c21eb3d2ff5f24c208ea7e3afba65e2e70f83f`.
The full revision replaces the older short `f2c21eb` selector.

Do not proceed if `MAZINB_RESTORE_PREFLIGHT=PASS_READ_ONLY_NO_WEIGHT_DOWNLOAD`
is missing. Do not repair a failed disk check by deleting protected
Docker/models/evidence or editing the existing manifest.

## Stage 2 — approved large checkpoint restore

Wizard **3 -> 12 Restore pinned mazinb checkpoint** repeats the
preflight, defaults to **NO**, and requires exact
`RESTORE_MAZINB_PINNED`. The approved apply retains an exclusive
shared lifecycle lock during the large, resumable download,
rechecking managed host idle under that lock. It writes only the
dedicated `models/qwen3.8-flash-next-mazinb` checkpoint.
The existing pinned `download-weights.sh` verifies per-file
size/hash against HF metadata and writes its local manifest.
The downloader may launch a **temporary CPU-only** Docker helper
using the already-installed v0.29 image for Hugging Face transfers;
this is **not a GPU/inference model start**. A fallback may
download via curl. An interruption leaves scoped partial
files for subsequent vetted resume; no automatic cleanup/purge.

**Actual 2026-10-19 DGX result:** `MAZINB_RESTORE_DOWNLOAD=COMPLETE_DOWNLOADER_VERIFIED`, 108/108 files verified individually, `hf_xet` high-performance, 8 workers, saved checkpoint reported as `174G`. New Wizard **5→24→3** returned `M1_PREFLIGHT=PASS_READ_ONLY` with protected OrcaRouter exact Docker identity and installed release pinned. No GPU/API attempt yet. [See physical evidence](../scripts/benchmark/evidence/dgx-mazinb-r2-download-preflight-physical-20261019.md).

## Stage 3 — protected foreground localhost API

Wizard **5 Benchmark -> 24 restored mazinb M1**:
1. Plan — no host changes
2. R2 status — read-only
3. R2 physical preflight — read-only, asks exact old Docker ID
4. **New isolated GPU start** — *separate default-NO approval*,
   exact old Docker ID, and typed `START_RESTORED_MAZINB_16G`.

The controller creates one new, uniquely named trial Docker
object only, pins its immutable ID and pre-arms the monitor
**before** Docker start. vLLM is served only on
`http://127.0.0.1:18889`, KV cache **16 GiB**;
it must pass exact model API identity, smoke generation,
180-second protected soak and strict NVIDIA RM kernel check
before printing `M1_READY_FOR_BENCH`. The terminal must remain
connected until explicit `STOP` or bounded automatic termination.
The managed OrcaRouter predecessor, release, old trial Docker
archive, shared images and systemd state are protected.
**Foreground service != background/systemd boot-persistent service**;
no user linger or auto-start is enabled by R2.

M1 live start is NOT qualified by code/CI. A real physical
preflight PASS and a new explicit owner GPU approval remain
mandatory after the checkpoint is installed.

## Stage 4 — separately admitted pinned Terminal B performance benchmark

Only if the **new R2** Terminal A prints `M1_READY_FOR_BENCH`
and keeps supervising the exact candidate, open a *separate*
interactive Terminal B in the same canonical checkout:

```bash
cd "$HOME/Workspace/llm/qwen3.8-flash-next-dgx-spark" || exit 1
bash scripts/wizard/mazinb-reinstall-bench.sh --plan
bash scripts/wizard/m1-benchmark-lock.sh --session-slot reinstall -- \
  bash scripts/wizard/mazinb-reinstall-bench.sh --run
```

The protected wrapper takes a shared lifecycle lock and an
exclusive **R2-specific** benchmark lease, rechecks exact Docker ID,
fresh watchdog heartbeat, exact API/model, host memory/RM before
and after benchmark, and defers Terminal A STOP until the lease
releases. The payload requires already installed
`llama-benchy 0.4.1.dev1+ge9be34457`; it does **not**
automatically install or upgrade benchmark tools. If unavailable
or its CLI is incompatible, benchmark stays BLOCKED rather than
measuring with an unpinned tool.

Fixed comparability dimensions:
`PP=512,2048`, `TG=128`, `depth=0`, `concurrency=1`,
`warmup-runs=1`, `runs=3`, `latency-mode=generation`,
no prefix caching in vLLM. New output folder
`~/Workspace/llm/qwen38-m1-bench-results/mazinb-r2-<UTC>-<unique>`
contains raw `mazinb.json`, new `mazinb-report.md`,
and verified `SHA256SUMS`. Off-host backup and host/kernel
evidence are separate requirements; no upload/backup is implied.
Never overwrite the archived 2026-10-14 original results.

After the wrapper completes and **post-run admission passes**,
enter `STOP` in Terminal A to stop only the new exact candidate.
Keep stopped Docker/journal for forensic evidence; no automatic
retirement, image cleanup, proxy/service switch or profile change.

## Explicitly not yet proven

- Exact local DGX source SHA (not printed in supplied physical output; preflight checks clean expected branch)
- Real new R2 Docker create/arm/GPU load, API READY, 180 s soak
- New benchmark version/CLI availability, raw JSON, PP/TG/TTFT numbers
- 24/7 persistent installed mazinb systemd service or reboot behavior

Do **not** merge Draft PR #261 based solely on synthetic CI.
Catplusplus is a later, separately approved track and does not
inherit mazinb's runtime qualification.

## 2026-10-19 actual execution checkpoint (supersedes former source-only stage status)

Physical restore and R2 read-only launch preflight are now PASS, with **no new M1 GPU start**. The next operator action is Wizard **5→24→4** only with independent default-NO approval, 64-character protected Docker ID acknowledgement, and exact `START_RESTORED_MAZINB_16G`. Before starting a potentially costly 90-minute protected session, check that Terminal B has the pinned `llama-benchy 0.4.1.dev1+ge9be34457` and an existing non-symlinked `~/Workspace/llm/qwen38-m1-bench-results` directory. Do not auto-install tools while the experiment is live. **Do not fast-forward/update the DGX checkout during Terminal A or B**: the controller pins source SHA across both. Original M1 history and old managed resources stay immutable. For exact evidence see [DGX checkpoint+admission receipt](../scripts/benchmark/evidence/dgx-mazinb-r2-download-preflight-physical-20261019.md).
