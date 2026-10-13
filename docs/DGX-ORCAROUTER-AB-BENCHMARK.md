# OrcaRouter legacy vs v0.29 A/B — single DGX, wizard-first

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


**2026-10-13: source plan only, real A/B has NOT been executed.**

Both images must serve the same `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`
revision `c1209bda15a6bbc4c68b585e93d40c0d85f50306`.

| Treatment | Image | Runtime | PLE | KV starting limit |
| --- | --- | --- | --- | --- |
| A | `vllm-skinny-tp1:v1` | previous Flash Next skinny-GEMM | CPU offload | 16 GiB |
| B | `vllm-orcarouter-v029:v1` | official v0.29 with Spark PLE/FLA/QSA patches | mmap | 16 GiB |

This is a **whole-runtime** comparison, not image-only causal
attribution. The raw v0.29 experimental helper requests
24 GiB KV and MUST NOT be used directly for this comparison;
prior 24 GiB OrcaRouter runs had host RM OOM/protection issues.
Use a dedicated, qualified **wizard-isolated** launcher for
each image; that launcher is **NOT IMPLEMENTED** yet.

## Wizard user experience

- New DGX Spark OS with NVIDIA drivers, GPU-capable Docker,
  Git, Python3, curl, sudo, internet and sufficient storage:
  `./install.sh` → OrcaRouter 1 for provisional v0.29
  default, or enter `L` for Legacy. Image is built locally
  automatically if missing, model downloaded, config and
  128 GiB swap prepared, immutable release and service setup
  guided by wizard. No manual Docker build. Full empty-host
  online installation still requires physical end-to-end testing.
- Existing manifest: `./install.sh` → `5` for **A/B plan
  preview** only. Existing installed legacy image, stopped
  original Docker exact ID, release and manifest unchanged.
  Choice 4 is still Cancel; no A/B model startup in preview.
- Neither the provisional fresh default nor source test pass
  declares an operational winner. H38 decoder-specific image
  remains a separately gated experimental migration.

## Two-terminal sequential benchmark protocol

1. Terminal A snapshots exact old Docker ID/status/image,
   immutable release, installed manifest digest, monitor/protect,
   swap and free disk. A/B run never deletes or restarts the old
   container. Use two **distinct temporary trial container IDs**
   and isolated monitor state. Trial launch/stop via **wizard only**.
2. Run image A alone, confirm health + `/v1/models` actual
   OrcaRouter ID and bounded clean NVIDIA RM/non-CMA memory
   protection window. If instability arises, stop without
   running benchmark. Preserve failure evidence, not 0 tok/s.
3. Terminal B runs pinned `eugr/llama-benchy`
   `e9be344578cec17745066b220798b80a0d2686d3`
   under `scripts/benchmark/with-wizard-lock.sh`, same
   input prompts/context/output tokens/parallel requests,
   tokenization/sampling and limits. Record TTFR/TTFT,
   prompt processing, generation tok/s, throughput,
   error rate, load/ready time and host resources.
4. Stop only A's **new** trial ID, save raw JSON, Markdown,
   SHA256, service/container/host logs, exact image ID/command
   and verified independent off-host backup. Ensure memory/
   swap/GPU have settled before launching B.
5. Repeat B with identical workload. Optionally control
   cache/order effects via A→B→B→A and repeat cold/warm starts.
   Report functional and host stability verdict separately.
6. Only after both are actually stable compare metrics and
   select the preferred empty-DGX installer default.
   OrcaRouter deletion is held **during this test only**;
   afterward asset-specific cleanup still needs separate
   approval and complete backups.

Abort on strict `NV_ERR_NO_MEMORY`, `_memdescAllocInternal`,
old Docker ID drift, unexpected lifecycle transition, wrong
model/API identity, protection stop, or invalid memory monitor.
No direct `systemctl restart`, raw experiment `start`,
Docker prune, model deletion, H38 migration or PR merge.
