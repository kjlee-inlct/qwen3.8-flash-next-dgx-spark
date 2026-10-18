# Official ARM64 OrcaRouter peer C — source-only plan and actual-DGX admission

**Date:** 2026-10-18. **Class:** proposed, not installed, not launched, not measured.
**Owner goal:** quickly obtain comparable model throughput and identify a usable, repeatably stable single-DGX-Spark runtime, without destroying A/B forensic evidence or the protected managed predecessor.

## What is and is not evidenced

- External community reference https://arca.live/b/alpaca/181506470 *reports* using `vllm/vllm-openai:qwen38-flash-next-arm64-cu130` with one GB10, OrcaRouter NVFP4, CPU PLE offload, MP TP1, MTP k=2, KV24GiB. That is **third-party reported runtime**, not evidence from our DGX.
- Docker Hub explicitly publishes the `linux/arm64` manifest digest `sha256:3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e`, about 9.04GB compressed: https://hub.docker.com/layers/vllm/vllm-openai/qwen38-flash-next-arm64-cu130/images/sha256-3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e . Registry publication does **not** certify embedded vLLM Git revision or stable DGX runtime.
- Operator's actual DGX `docker image inspect vllm/vllm-openai@sha256:3b0e...` returned **`No such image`**. This proves only absence under that exact reference; a tag-only copy must be independently checked by `RepoDigests` and Docker image ID.
- Existing A (`vllm-skinny-tp1:v1`) and B (`vllm-orcarouter-v029:v1`) both had **actual protected stops**. B's Oct-13 monitor at 21:03:30 KST went `protect=5/5`, `noncmafree=1171MiB`, `swapgrowth=3207MiB`, `noncma_available=40702MiB`, exact ID `13abbb81...`; `OOMKilled=false`. Do not call this a proven NVIDIA RM OOM or current model READY.
- The OrcaRouter original and override JSON checked out on DGX matched the pasted third-party reference 7/7 in canonical values; this is only **config-value parity**, not actual installed wheel/weights/driver allocation equivalence.
- The only verified fresh five-profile protocol llama-benchy measurements so far are for `mazinb` (v0.29); OrcaRouter is `NOT_MEASURED`.

## Source-only implemented C preview

Use the current successful-CI Git SHA **after operator-specified repository synchronization**, not an unverified current branch checkout:

```bash
python3 -B scripts/runtime/orcarouter-peer-c-readonly.py plan
python3 -B scripts/runtime/orcarouter-peer-c-readonly.py preflight
```

These actions do not contact the model API, access GPU/weights, or create/start/stop/remove/pull Docker objects. `plan` is host-independent. `preflight` may only read exact pinned/tagged local image metadata and stopped Docker metadata, check ARM64 architecture, systemd active state and current disk-free metadata. A missing image yields `BLOCKED_IMAGE_NOT_INSTALLED`. Even a preflight PASS explicitly **does not** authorize a live trial.

Wizard: `./wizard.sh` -> Advanced / 연구 기록 -> official ARM64 C plan or read-only preflight. The installer-managed A/B wizard remains unchanged.

## Later independent C live design — not implemented or approved

1. Operator first reviews exact image/tag identity and root Docker storage headroom. A *separate explicit owner approval* is required before any **network Docker pull** of the published pinned image. Pinned reference: `vllm/vllm-openai@sha256:3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e`. After pull verify `linux/arm64` plus `RepoDigests` equals the expected manifest, not merely image `.Id` equality.
2. Independent C live launcher, **still to be implemented and CI/synthetic tested**, must be Wizard-owned and locked, use a unique never-reused Docker name such as `qwen38-orca-peer-c-<timestamp>-<nonce>`, never touch old managed/A/B IDs and names, use separate state and local-only 127.0.0.1:18891, no host-port exposure, no automatic restarts or `--rm`. It must create-only, capture exact new ID/labels, arm a watchdog *before* starting the exact candidate, then verify heartbeat. Do not translate this into a direct `docker run` bypass.
3. Candidate must use the **same pinned OrcaRouter checkpoint**, RO model source and checked override; `VLLM_PLE_CPU_OFFLOAD=1`, `VLLM_PLE_OFFLOAD_READY_TIMEOUT=1800`, MP TP1, MTP k2, 262144 configured max, concurrency 3, disabled prefix caching and async scheduling. **Start KV16GiB**, not external reporter's KV24. The official ARM64 vLLM CLI acceptability of legacy `--kv-cache-memory` and all model/PLE features must be established, not assumed from an image tag.
4. Bound to the existing unchanged memory-protection thresholds. Record exact Docker image ID, effective runtime flags and config mount identity, trial start, ready time, `/health`, `/v1/models` exact served model, RAM/non-CMA/swap, monitor heartbeat/protection samples, kernel NVRM/Xid/RM error window and 180s soak. Any strict RM OOM, watchdog stop or API mismatch fails live qualification. Preserve failed logs instead of claiming `0 tok/s`.
5. Only after explicit source/CI + real DGX READY and stable host gates: run pinned `eugr/llama-benchy` SHA `e9be344578cec17745066b220798b80a0d2686d3` as same model comparison workload, beginning PP512/TG128 and PP2048/TG128, 1 warmup and 3 measured each; capture raw JSON, version, image ID, source SHA, Markdown via maintained report converter, SHA256 and independent off-host backup. Do not run benchmark when the API is refused.
6. C success is not automatic production selection: repeat stable startup and bounded inference while preserving protected resources, then compare throughput/latency **and** strict host safety. Existing mazinb measured reference is useful for immediate fallback; do not delete the still-protected OrcaRouter model until explicit asset-specific disposition.

**STOP:** no live C launch command exists or is authorized by this document. PR #261/#259 remain Draft/Unmerged; no forced merge, Docker pull, GPU trial, model deletion, service restart or protection relaxation.
