# Actual DGX peer C read-only admission — 2026-10-18

**Evidence class:** `ACTUAL_DGX_OPERATOR_TERMINAL` (not Github CI or external community).
**Scope:** Git-only fast forward; then Python read-only local image/managed-Docker guards. No C Docker create/start, GPU model load, API, benchmark, service restart, deletion or protection relaxation.

## Git checkout

Before operator change: local branch `feature/wizard-modular-phase1-20261014`,
local SHA `ad3855a0a64e25deed3b9c11d7b3168f06730d68`, working tree
clean by `git status --short`; remote branch SHA
`ff339c1eb9eb77cb774b50b3fcdc7fa009ecd74d`.
GitHub compare API independently verified ancestor fast-forward relationship
(30 commits ahead, 0 behind, merge base = original local SHA).
The operator ran `git fetch --no-tags`, tested exact FETCH_HEAD and
ancestor status, `git merge --ff-only FETCH_HEAD`, then verified exact SHA
and clean status. Terminal printed:

```text
Fast-forward
11 files changed, 1004 insertions(+), 1 deletion(-)
ff339c1eb9eb77cb774b50b3fcdc7fa009ecd74d docs(orcarouter): classify official C image entrypoint vs unattested vLLM wheel source
GIT_SYNC=PASS
```

At sync time GitHub's Push/PR CI on that SHA both completed with SUCCESS.

## C read-only preflight (executed on same DGX checkout)

Command: `python3 -B scripts/runtime/orcarouter-peer-c-readonly.py preflight`

```text
PEER_C_OPERATION=PLAN_ONLY_NO_HOST_INSPECTION
PEER_C_REGISTRY_TAG=vllm/vllm-openai:qwen38-flash-next-arm64-cu130
PEER_C_REGISTRY_MANIFEST_DIGEST=sha256:3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e
PEER_C_REGISTRY_PLATFORM=linux/arm64
PEER_C_EXPECTED_IMAGE_ID=sha256:d464f3b466fa9c45ddbff8a812e80564503b6879a9fd95c1a47514f3f0df5a4a
PEER_C_MODEL=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4
PEER_C_RUNTIME=OFFICIAL_ARM64_CPU_PLE_CANDIDATE_NOT_VALIDATED
PEER_C_EXISTING_AB_PRESERVE=MANDATORY
PEER_C_DESIRED_PORT=127.0.0.1:18891
PEER_C_KV_START_GIB=16
PEER_C_MODEL_START=NOT_IMPLEMENTED_OR_AUTHORIZED
PEER_C_IMAGE_PULL=NO_ACTION_BY_THIS_READ_ONLY_TOOL
PEER_C_BENCHMARK=NOT_MEASURED
PEER_C_HOST_ARCH=ARM64
PEER_C_LOCAL_IMAGE=PINNED_MATCH
PEER_C_RUNTIME_CONTRACT=ENTRYPOINT_SHAPE_MATCH_WHEEL_SOURCE_UNATTESTED
PEER_C_EMBEDDED_VLLM_COMMIT=NOT_ATTESTED_BY_OCI_METADATA
PEER_C_PROTECTED_OBJECTS=THREE_STOPPED_EXISTING_IDS
PEER_C_MANAGED_SERVICE=INACTIVE_OR_UNKNOWN
PEER_C_ROOT_DISK_FREE_GIB=417
PEER_C_ADMISSION=SOURCE_READ_ONLY_PREFLIGHT_PASS_NOT_LIVE_APPROVAL
PREFLIGHT_EXIT_CODE=0
```

**PASS interpretation:** on that actual checkout the pinned manifest
and image-config ID matched the earlier operator image pull; the
Entrypoint=(`vllm`,`serve`), absent Cmd, workdir and CUDA env agreed
with physically observed OCI metadata; managed plus two prior A/B
Docker objects were exactly the preserved IDs and in stopped state.
The helper made no Docker or service changes.

**Caveat:** `PEER_C_MANAGED_SERVICE=INACTIVE_OR_UNKNOWN` is the tool's
combined classification of systemctl exit code 3 *or* 4, and
does **not** independently attest that an installed service is inactive.
Do not reuse it as a standalone permission for a live trial.

**Live gate not passed:** the vLLM wheel commit remains unknown;
no new C container, host memory watchdog, model API, 180s soak or
benchmark was executed or admitted.

## Static compatibility gap found in same source review

- The installed official ARM64 image is `ENTRYPOINT=["vllm", "serve"]`
and has absent `Cmd`. This agrees only with the **argument shape**
formed by `scripts/serve.sh` (IMAGE `/model` followed by CLI flags).
- Existing `serve.sh` `TRIAL_CREATE_ONLY` admission is explicitly
allowlisted to `mazinb-m1`, `hybrid-h6-m1`, legacy A and v0.29 B.
An independent `orcarouter-peer-c` variant currently FAILS that
allowlist. A separate uniquely named, isolated create-only C is
**NOT IMPLEMENTED**.
- When `MODEL_PROFILE=orcarouter` selects a different VLLM_IMAGE than
`vllm-orcarouter-v029:v1`, `serve.sh` selects CPU PLE offload mode
and default `KV_MEMORY_FLAG=--kv-cache-memory`. Current *public* vLLM
engine-arguments docs describe `--kv-cache-memory-bytes`,
NOT this legacy spelling. A fixed 16GiB C allocation must only be
constructed after confirming the **specific installed image** CLI
parser; unknown vLLM version/commit means public docs are suggestive
but not byte-level proof of this image.
- Before writing any live launcher, reconcile the exact community
CLI options with the stock pinned image (loader, MP/TP1, MTP2,
prefix/async flags, KV16GiB, 0.0.0.0 container bind but only
127.0.0.1 host publish), then synthetic-test create-only, unique
name, pinned image/digest, exact protected IDs, watcher arm-before-start
and fail-closed host protection. No direct `docker run` bypass.

References: [`serve.sh`](../../serve.sh),
[C plan](../../../docs/ORCAROUTER-PEER-C-PLAN-20261018.md),
[image pull receipt](dgx-orcarouter-peer-c-image-pull-20261018.md),
[vLLM current engine arguments](https://docs.vllm.ai/en/stable/configuration/engine_args/).
