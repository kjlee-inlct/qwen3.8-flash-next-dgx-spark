# mazinb R2 — pinned checkpoint restore and bounded isolated API benchmark

**Status: SOURCE IMPLEMENTED / physical DGX restore+live+bench NOT EXECUTED.**
This does **not** claim an installed long-running service or a new
benchmark result. It restores the 2026-10-14 measured *checkpoint
revision* without reusing or modifying the retired historical M1
Docker journal/tombstone or the managed OrcaRouter predecessor.

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

`MAZINB_RESTORE_DOWNLOAD=COMPLETE_DOWNLOADER_VERIFIED` is
the expected source result, not independently observed on DGX yet.

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

- DGX source current HEAD and clean worktree after these new commits
- R2 restore preflight and disk space, actual ~174 GiB checkpoint bytes
- Real new R2 Docker create/arm/GPU load, API READY, 180 s soak
- New benchmark version/CLI availability, raw JSON, PP/TG/TTFT numbers
- 24/7 persistent installed mazinb systemd service or reboot behavior

Do **not** merge Draft PR #261 based solely on synthetic CI.
Catplusplus is a later, separately approved track and does not
inherit mazinb's runtime qualification.
