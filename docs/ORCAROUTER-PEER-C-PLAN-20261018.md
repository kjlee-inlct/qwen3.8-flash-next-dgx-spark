# Official ARM64 OrcaRouter peer C — source-only plan and actual-DGX admission

**Date:** 2026-10-18. **Class:** official ARM64 Docker image installed and digest/OCI verified; **independent C runtime not created or launched; benchmark not measured**.
**Owner goal:** quickly obtain comparable model throughput and identify a usable, repeatably stable single-DGX-Spark runtime, without destroying A/B forensic evidence or the protected managed predecessor.

## Physical IMAGE VERIFIED after download-only approval — 2026-10-18

**This newer finding supersedes older `No such image` / `NOT_LOCAL`
findings on this page; earlier read-only absences remain historical.**

The operator explicitly approved the exact official ARM64 image pull
and digest verification only, then reported:

```text
PEER_C_IMAGE_OS=linux
PEER_C_IMAGE_ARCH=arm64
PEER_C_IMAGE_ID=sha256:d464f3b466fa9c45ddbff8a812e80564503b6879a9fd95c1a47514f3f0df5a4a
PEER_C_REPODIGEST=vllm/vllm-openai@sha256:3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e
PEER_C_VERIFY=PASS
PEER_C_PROTECTED_DOCKER=UNCHANGED
PEER_C_GPU_RUN=NOT_PERFORMED
PEER_C_MODEL_BENCHMARK=NOT_MEASURED
PEER_C_IMAGE_STAGE=VERIFIED
```

Pre/post Docker identity/status/image/Running/OOMKilled fields
were unchanged for original managed + A + B, all stopped.
Full historical receipt and artifact names:
[2026-10-18 actual owner image-pull evidence](../scripts/benchmark/evidence/dgx-orcarouter-peer-c-image-pull-20261018.md).

**New actionable gate**: run read-only C source preflight on the
qualified exact GitHub HEAD (and privately check the pinned image
history/Entrypoint/Cmd/Env without container execution), then
design/CI-qualify a fresh Wizard-owned C protected launcher.
An approved image pull does **not** approve Docker create/start,
GPU, a benchmark, service modification, KV24, deletion, or PR merge.
## Physical OCI Entrypoint & source-provenance evidence (2026-10-18, later observation)

The operator inspected the newly pinned ARM64 image on the **actual DGX**
without starting it, correcting the initial Go-template error
`map has no entry for key Cmd` with a safe JSON parser.
The output identified the same exact image ID/digest as the pull receipt:

```text
ENTRYPOINT=["vllm", "serve"]
CMD=NOT_SET
WORKDIR=/vllm-workspace
USER=NOT_SET
OCI_REVISION=unknown
CUDA_VERSION=13.0.1
FLASHINFER_VERSION=NOT_SET
VLLM_BUILD_COMMIT=unknown
VLLM_IMAGE_TAG=local/vllm-openai:dev
VLLM_VERSION=NOT_SET
IMAGE_INSPECTION=READ_ONLY_COMPLETE
```

The managed `serve.sh` shell syntax appends `/model` followed by
flags after the Docker image, which **would construct**
`vllm serve /model ...` for this Entrypoint.
This verifies argv **composition only**; it does **not** establish
supported options, package imports, Qwen4Exp loader/PLE, model READY
or stable host-RM allocations. No runnable C launch path is implemented
or authorized. `CMD=NOT_SET` is a legitimate absent default property,
not a Docker error. `FLASHINFER_VERSION=NOT_SET` is runtime-env absence
rather than evidence a package is missing. Exact embedded vLLM wheel
version/source cannot be attributed because OCI build and revision
labels say `unknown`.

The maintained C read-only preflight additionally checks the
`["vllm", "serve"]` Entrypoint, absent Cmd, working directory and
CUDA runtime Env. Successful metadata preflight explicitly reports
`WHEEL_SOURCE_UNATTESTED`; it does not confer GPU launch approval.
[Operator source metadata receipt](../scripts/benchmark/evidence/dgx-orcarouter-peer-c-image-pull-20261018.md).
## What is and is not evidenced

- External community reference https://arca.live/b/alpaca/181506470 *reports* using `vllm/vllm-openai:qwen38-flash-next-arm64-cu130` with one GB10, OrcaRouter NVFP4, CPU PLE offload, MP TP1, MTP k=2, KV24GiB. That is **third-party reported runtime**, not evidence from our DGX.
- Docker Hub explicitly publishes the `linux/arm64` manifest digest `sha256:3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e`, about 9.04GB compressed: https://hub.docker.com/layers/vllm/vllm-openai/qwen38-flash-next-arm64-cu130/images/sha256-3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e . Registry publication does **not** certify embedded vLLM Git revision or stable DGX runtime.
- Operator's actual DGX `docker image inspect vllm/vllm-openai@sha256:3b0e...` returned **`No such image`**. This proves only absence under that exact reference; a tag-only copy must be independently checked by `RepoDigests` and Docker image ID.
- Existing A (`vllm-skinny-tp1:v1`) and B (`vllm-orcarouter-v029:v1`) both had **actual protected stops**. B's Oct-13 monitor at 21:03:30 KST went `protect=5/5`, `noncmafree=1171MiB`, `swapgrowth=3207MiB`, `noncma_available=40702MiB`, exact ID `13abbb81...`; `OOMKilled=false`. Do not call this a proven NVIDIA RM OOM or current model READY.
- The OrcaRouter original and override JSON checked out on DGX matched the pasted third-party reference 7/7 in canonical values; this is only **config-value parity**, not actual installed wheel/weights/driver allocation equivalence.
- The only verified fresh five-profile protocol llama-benchy measurements so far are for `mazinb` (v0.29); OrcaRouter is `NOT_MEASURED`.

## Additional actual DGX Docker tag and storage read-only receipts — 2026-10-18

The owner independently inspected the **tag**, after earlier exact
`@sha256:` inspection returned `No such image`: 

```text
docker image inspect vllm/vllm-openai:qwen38-flash-next-arm64-cu130
Error response from daemon: No such image: vllm/vllm-openai:qwen38-flash-next-arm64-cu130

df -h "$(docker info --format '{{.DockerRootDir}}')"
/dev/nvme0n1p2  916G  451G  418G  52%  /

docker system df
Images          10  6  47.22GB  146.6kB (0%)
Containers       8  2   1.552GB   1.506GB (97%)
Local Volumes    3  3   34.16kB  0B (0%)
Build Cache    127  0   1.163MB  7.433kB
```

Interpretation: both the exact pinned image reference and the matching
human-readable tag were absent from local Docker at inspection.
Other aliases remain theoretically possible, not attested. Root Docker
storage has **418G filesystem free**, which gives substantial headroom
for a proposed image pull but is **not** a measured compressed+expanded
peak storage budget. `RECLAIMABLE` is **not** deletion approval.
Preserve all eight containers, especially old A/B and managed evidence;
no prune, image pull or service start was authorized by this inspection.

Following source-only C additions, Push and PR CI at HEAD `5a3c484d...`
each failed *one* of 1,300 unittest cases because
`tests/test_script_layout.py` treated a Markdown evidence-document
reference to `scripts/model/` as a runtime code dependency. **All nine
new C unit tests passed**. Source lint has since been corrected to
exclude Markdown evidence from executable dependency analysis; a fresh
full CI run must establish PASS before recommending an operator sync.
## Physical systemd-unit absence resolved (2026-10-18 read-only result)

The owner checked **both** `systemctl show` and
`systemctl --user show` for `qwen38-flash-next.service`.
Both returned `LoadState=not-found`, `ActiveState=inactive`,
`SubState=dead`, and empty `UnitFileState`.
This refines the earlier preflight `INACTIVE_OR_UNKNOWN`: the
**specific unit does not exist in either checked manager**; it
is not an installed-but-idle managed service. This is a neutral
fact for an independent C candidate, not evidence that the entire
host is quiescent. Do not reuse the legacy A/B service-install
precondition without an explicit independent C-specific admission.

**Next C launcher gate (source-only, no live authorization):**
read-only enumerate other running model containers and port `18891`,
unfinished lifecycle state and swap/memory margin; reject collisions
and untrusted object identities. Separate C must be Wizard-locked,
unique-name create-only with `--restart no`, local-only host publish,
monitor arm-before-start exact ID, no `--rm`, no change to old objects.
Confirm actual official image CLI support for KV16GiB/CPU PLE/MTP
before any model-loaded start. No C start has been authorized.
[Actual DGX service evidence](../scripts/benchmark/evidence/dgx-orcarouter-peer-c-preflight-20261018.md).
## Actual DGX host-resource snapshot passed read-only inspection (2026-10-18)

The physical owner confirmed only running Docker containers are
`open-webui` and `portainer`; `ss` found no listener on planned
host TCP `18891`. `/swap-ple.img` (128 GiB, used 1020.3 MiB)
and `/swap.img` (16 GiB, unused) were active. From raw
`/proc/meminfo`, non-CMA **free** RAM was approximately **113.8 GiB**,
non-CMA **available** approximately **118.1 GiB**, and swap free
approximately **143.0 GiB**. The exact system/user managed service
was independently verified `LoadState=not-found` in both scopes.
[Actual host snapshot](../scripts/benchmark/evidence/dgx-orcarouter-peer-c-host-readonly-20261018.md).

A new strictly **read-only**
`python3 -B scripts/runtime/orcarouter-peer-c-readonly.py host-check`
action (Wizard Advanced option 5) makes these snapshot conditions
repeatable using only Docker ps, ss, swapon and `/proc/meminfo` reads.
It fails closed if a new running Docker container, port listener,
missing PLE swap, low non-CMA memory/swap or failed OS query appears.
**This helper and its tests are GitHub source-only until the owner
synchronizes a CI-passed SHA; it has NOT yet run on the physical DGX.**
`host-check` returning PASS would only establish a **dynamic
point-in-time observation, not permit Docker create/start or GPU**.
## ACTUAL DGX source-only C preflight PASS — 2026-10-18

Operator performed exact 30-commit safe Git fast-forward to
`ff339c1eb9eb77cb774b50b3fcdc7fa009ecd74d`,
then ran `scripts/runtime/orcarouter-peer-c-readonly.py preflight`.
Exit status 0 printed `PINNED_MATCH`,
`ENTRYPOINT_SHAPE_MATCH_WHEEL_SOURCE_UNATTESTED`,
`THREE_STOPPED_EXISTING_IDS` and
`SOURCE_READ_ONLY_PREFLIGHT_PASS_NOT_LIVE_APPROVAL`,
with 417GiB free. This establishes only static admission.
[Full physical read-only receipt and code-gap audit](../scripts/benchmark/evidence/dgx-orcarouter-peer-c-preflight-20261018.md).

**Current source blockers to a C start:**

- `serve.sh` create-only allowlist does not permit a `peer-c` variant;
do not bypass the protected Wizard through an unmanaged container.
- The non-v0.29 `orcarouter` image path chooses legacy
`--kv-cache-memory` with 16GiB value; current public vLLM docs
document `--kv-cache-memory-bytes`. The pinned official image
does not expose an embedded revision in its OCI metadata, so
prove the actual parser's accepted flags before any GPU execution.
- The preflight that passed on DGX prints
`PEER_C_MANAGED_SERVICE=INACTIVE_OR_UNKNOWN` for systemctl rc 3/4.
This is **ambiguous**, not an inactive-service proof and
not a live launch admission. Later source-only fix distinguishes
`INACTIVE` from `UNKNOWN_NOT_LIVE_APPROVED` and accurately reports
`PREFLIGHT_READ_ONLY_HOST_INSPECTION`; these changes are
unexecuted on DGX and require independent CI approval.

**Next source-only milestone:** design/CI-qualify a separate C
create-only/lock/watchdog-arm-before-start controller with all
old Docker exact-ID guards and no cleanup of evidence;
then independently request approval for the live GPU phase.
## Source-only implemented C preview

Use the current successful-CI Git SHA **after operator-specified repository synchronization**, not an unverified current branch checkout:

```bash
python3 -B scripts/runtime/orcarouter-peer-c-readonly.py plan
python3 -B scripts/runtime/orcarouter-peer-c-readonly.py preflight
```

These actions do not contact the model API, access GPU/weights, or create/start/stop/remove/pull Docker objects. `plan` is host-independent. `preflight` may only read exact pinned/tagged local image metadata and stopped Docker metadata, check ARM64 architecture, systemd active state and current disk-free metadata. A missing image yields `BLOCKED_IMAGE_NOT_INSTALLED`. Even a preflight PASS explicitly **does not** authorize a live trial.

Wizard: `./wizard.sh` -> Advanced / 연구 기록 -> official ARM64 C plan or read-only preflight. The installer-managed A/B wizard remains unchanged.

## Later independent C live design — not implemented or approved

1. **Completed, download-only-approved 2026-10-18:** the operator downloaded the pinned official ARM64 image `vllm/vllm-openai@sha256:3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e` and verified OS/arch, RepoDigest and image config ID, and preserved A/B IDs. This approval **does not** extend to any C create/start/GPU trial.
2. Independent C live launcher, **still to be implemented and CI/synthetic tested**, must be Wizard-owned and locked, use a unique never-reused Docker name such as `qwen38-orca-peer-c-<timestamp>-<nonce>`, never touch old managed/A/B IDs and names, use separate state and local-only 127.0.0.1:18891, no host-port exposure, no automatic restarts or `--rm`. It must create-only, capture exact new ID/labels, arm a watchdog *before* starting the exact candidate, then verify heartbeat. Do not translate this into a direct `docker run` bypass.
3. Candidate must use the **same pinned OrcaRouter checkpoint**, RO model source and checked override; `VLLM_PLE_CPU_OFFLOAD=1`, `VLLM_PLE_OFFLOAD_READY_TIMEOUT=1800`, MP TP1, MTP k2, 262144 configured max, concurrency 3, disabled prefix caching and async scheduling. **Start KV16GiB**, not external reporter's KV24. The official ARM64 vLLM CLI acceptability of legacy `--kv-cache-memory` and all model/PLE features must be established, not assumed from an image tag.
4. Bound to the existing unchanged memory-protection thresholds. Record exact Docker image ID, effective runtime flags and config mount identity, trial start, ready time, `/health`, `/v1/models` exact served model, RAM/non-CMA/swap, monitor heartbeat/protection samples, kernel NVRM/Xid/RM error window and 180s soak. Any strict RM OOM, watchdog stop or API mismatch fails live qualification. Preserve failed logs instead of claiming `0 tok/s`.
5. Only after explicit source/CI + real DGX READY and stable host gates: run pinned `eugr/llama-benchy` SHA `e9be344578cec17745066b220798b80a0d2686d3` as same model comparison workload, beginning PP512/TG128 and PP2048/TG128, 1 warmup and 3 measured each; capture raw JSON, version, image ID, source SHA, Markdown via maintained report converter, SHA256 and independent off-host backup. Do not run benchmark when the API is refused.
6. C success is not automatic production selection: repeat stable startup and bounded inference while preserving protected resources, then compare throughput/latency **and** strict host safety. Existing mazinb measured reference is useful for immediate fallback; do not delete the still-protected OrcaRouter model until explicit asset-specific disposition.

**STOP:** no live C launch command exists or is authorized by this document. PR #261/#259 remain Draft/Unmerged; no forced merge, Docker pull, GPU trial, model deletion, service restart or protection relaxation.
