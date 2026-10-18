# Actual DGX official ARM64 OrcaRouter C Docker image pull receipt — 2026-10-18

**Evidence:** ACTUAL_DGX_OPERATOR_TERMINAL, operator-supplied output.
**Operation scope:** expressly approved **Docker image download and digest verification only**; no container create/start/stop/remove, GPU inference, checkpoint edit, or benchmark.
**Recorded evidence root:** `/home/inlc/orcarouter-bench-evidence/peer-c-image-20261018T093728Z`.

## Verified pinned registry reference

```text
REF=vllm/vllm-openai@sha256:3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e
docker pull --platform linux/arm64 "$REF"
Digest: sha256:3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e
Status: Downloaded newer image for vllm/vllm-openai@sha256:3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e
PEER_C_IMAGE_OS=linux
PEER_C_IMAGE_ARCH=arm64
PEER_C_IMAGE_ID=sha256:d464f3b466fa9c45ddbff8a812e80564503b6879a9fd95c1a47514f3f0df5a4a
PEER_C_REPODIGEST=vllm/vllm-openai@sha256:3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e
PEER_C_VERIFY=PASS
```

Numerous pull layers printed `Already exists`. This only indicates layer cache reuse; the complete pinned image reference was **not locally resolvable** during earlier `docker image inspect` and became available after the approved pull. The **manifest digest** (`3b0e...`) is not the **local image config ID** (`d464...`). The Python verification in the operator terminal asserted OS=linux, architecture=arm64, digest member of `RepoDigests` and syntactically valid local image ID.

## Exact protected Docker identity before and after

| Name | Exact Docker ID | Image ID | State | Running | OOMKilled |
|---|---|---|---|---|---|
| `/qwen38-flash-next` | `f6bfee5a421743758974920064d59c1fb7586584cb3a96f83b5c3fafff6acd24` | `sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4` | exited | false | false |
| `/qwen38-ab-legacy` | `57eada965768b01eb412b10826ec4f0be9c4ed352abd87957c4ffbe932f27a56` | `sha256:01bdde6de42794bc7073fa7c0724d4b62375d4c32817fea902217fdc33b5cef4` | exited | false | false |
| `/qwen38-ab-v029` | `13abbb81ca92cbf2f8256e96941a19102ce809ff1c9364ce6932b44a88ebf6a1` | `sha256:dba5d8af279fb85901e6d8911f1a59ecc45b669b0948ab8d01d7c7d1c5815734` | exited | false | false |

All six columns were printed unchanged for these three named protected Docker objects in `protected-before.txt` and `protected-after.txt`; command returned without diff output, then printed:

```text
PEER_C_PROTECTED_DOCKER=UNCHANGED
PEER_C_GPU_RUN=NOT_PERFORMED
PEER_C_MODEL_BENCHMARK=NOT_MEASURED
PEER_C_IMAGE_STAGE=VERIFIED
EVIDENCE_DIR=/home/inlc/orcarouter-bench-evidence/peer-c-image-20261018T093728Z
```

The shell execution printed `=== EVIDENCE SHA256 ===` and passed the `sha256sum ... > SHA256SUMS.txt` step under `set -Eeuo pipefail`; the terminal **does not display** the actual SHA256SUMS content or its independent verification. Pasted heredoc text was partially garbled, but the output includes the complete expected identity and protected postcheck stages, with a final interactive prompt. Do not infer any unshown execution beyond that output.

## Follow-up physical image runtime-config metadata (owner read-only terminal, 2026-10-18)

The operator ran `docker image inspect` on the same exact pinned C
registry reference, parsed the JSON with Python after a first Docker
Go-template read failed because `.Config.Cmd` was not present.
Corrected **read-only** output is:

```text
IMAGE_ID=sha256:d464f3b466fa9c45ddbff8a812e80564503b6879a9fd95c1a47514f3f0df5a4a
OS=linux
ARCH=arm64
REPO_DIGESTS=["vllm/vllm-openai@sha256:3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e"]
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

**Source-level inference only:** the existing `scripts/serve.sh`
puts `/model` and CLI flags after the Docker IMAGE. For this entrypoint
it composes `vllm serve /model [flags]`, so the entrypoint/argv *shape*
matches; the internal vLLM wheel, supported flags, CPU PLE worker,
model architecture, compressed-tensors loader, MTP implementation
and safe memory allocations are **NOT PROVED**. `CMD=NOT_SET` here
is absence of an image default `Cmd` property, not a malformed image.
`FLASHINFER_VERSION=NOT_SET` means absent from the inspected runtime
Env whitelist, not that FlashInfer is uninstalled; OCI image build
history may report build arguments separately. `unknown` labels
cannot attest a commit. No Docker run/exec/copy or runtime import
was performed. The pasted multiline input was partly mangled but
the labeled Python output and interactive shell return were visible.
## Qualification remains blocked

- This is **IMAGE_PRESENT_VERIFIED_ONLY**, not embedded vLLM wheel/source attestation; image runtime/loader compatibility remains **UNQUALIFIED**.
- C candidate Docker has **not** been created or started. No health/model-ID response, protected 180-second host RM stability or C throughput exists.
- A/B preserved failures and the mazinb canonical measured result are unchanged.
- Next source/CI-verified entrypoint: `python3 -B scripts/runtime/orcarouter-peer-c-readonly.py preflight`; requires operator to explicitly synchronize qualified source first and capture git HEAD/status.
- No additional approval to mutate or launch a C Docker container, alter guards, change KV to 24GiB, delete model assets, prune, change services, merge PR or run inference has been given.
