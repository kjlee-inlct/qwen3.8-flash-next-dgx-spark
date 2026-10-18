# Actual DGX one-time CPU-only official peer C CLI probe — 2026-10-18

**Evidence class:** ACTUAL_DGX_OPERATOR_TERMINAL. **Authorization:** one disposable, CPU-only official-image CLI help/distribution query (no GPU, no model, no network, no checkpoint mounts, no existing Docker mutations). **Outcome:** package metadata captured, `vllm serve --help=all` **failed**, cannot assert any individual CLI argument is absent. Preserved old A/B unchanged.

## Operator commands and source provenance

```text
python3 -B scripts/runtime/orcarouter-peer-c-cli-probe.py plan
python3 -B scripts/runtime/orcarouter-peer-c-cli-probe.py run --approved-cpu-only
PEER_C_SOURCE_SHA=4873016f1d9fd864e6cce30c18fb96634b412fe3
PEER_C_PINNED_IMAGE=vllm/vllm-openai@sha256:3b0e188ffceb3d07e09c3cb5215433a0020eacf02d7f882ed3a8bfd15454477e
PEER_C_IMAGE_CONFIG_ID=sha256:d464f3b466fa9c45ddbff8a812e80564503b6879a9fd95c1a47514f3f0df5a4a
PEER_C_OPERATION=HOST_CHECK_READ_ONLY
PEER_C_RUNNING_DOCKER=ONLY_KNOWN_ADMIN_CONTAINERS
PEER_C_PORT_18891=NO_LISTENER_AT_CHECK
PEER_C_PLE_SWAP=PLE_SWAP_ACTIVE
PEER_C_NONCMA_FREE_KIB=119291328
PEER_C_NONCMA_AVAILABLE_KIB=123819800
PEER_C_SWAP_FREE_KIB=149950172
PEER_C_MEMORY_MARGIN=MINIMUM_STATIC_MARGIN_MET
PEER_C_HOST_CHECK=PASS_SNAPSHOT_NOT_LIVE_APPROVAL
PEER_C_PROBE_NAME=qwen38-peer-c-cpu-cli-20261018T115111Z-5e41d75a
PEER_C_EVIDENCE_DIR=/home/inlc/orcarouter-bench-evidence/peer-c-cli-20261018T115111Z-5e41d75a
```

This exact Git SHA had independently verified Push and PR CI SUCCESS before the operator ran it. The probe's one-time approval marker is at `/home/inlc/orcarouter-bench-evidence/peer-c-cli-approved-once-20261018.json`. **Do not rerun `run --approved-cpu-only` to seek a different CLI result; this approval has been consumed.**

## Package metadata captured from within isolated official ARM64 container

```text
PEER_C_CONTAINER_OPERATION=CLI_HELP_AND_DIST_METADATA_ONLY
PEER_C_CUDA_VISIBLE_DEVICES=-1
PEER_C_NVIDIA_VISIBLE_DEVICES=void
PEER_C_PACKAGE_VLLM=0.1.dev20073+g8e685d198
PEER_C_PACKAGE_TORCH=2.13.0+cu130
PEER_C_PACKAGE_TRANSFORMERS=5.15.1
PEER_C_PACKAGE_FLASHINFER_PYTHON=0.6.17
PEER_C_PACKAGE_COMPRESSED_TENSORS=0.17.0
```

This identifies the *installed distribution versions* (vLLM version string includes git-shaped suffix `g8e685d198`) but not a verified complete internal image-source diff, actual CUDA use, OrcaRouter checkpoint compatibility or CPU PLE loader viability. CLI probe had `--runtime runc --network none --read-only --pull=never`, no `--gpus` or model mounts, nonroot, memory/pid/cpu restrictions, and a new unique `--rm` container.

## Failed CLI parser/help invocation — interpretation

```text
PEER_C_HELP_EXIT_CODE=1
PEER_C_HELP_SHA256=01e500802ae39e3ffd269e0339325d7b7ade1e970cc06d0d05b308acabae4912
PEER_C_CLI_HELP=FAILED
PEER_C_PROTECTED_AFTER=UNCHANGED
PEER_C_DISPOSABLE_PROBE_REMOVED=YES
PEER_C_DOCKER_RUN_EXIT_CODE=13
PEER_C_CLI_PROBE=FAILED_REVIEW
CLI_PROBE_EXIT_CODE=2
```

The operator's terminal reported `PEER_C_FLAG_* = NOT_FOUND_IN_HELP` for every queried option, including both `--kv-cache-memory-bytes` and `--kv-cache-memory`. **These are not valid CLI option unsupported results** because the entire help command returned rc=1. Treat each as `NOT_EVALUATED_HELP_FAILED` until a *reliably successful* parser help or equivalent offline authoritative parser inspection exists. **The underlying failure traceback/error has not yet been pasted by the operator**; do not guess whether it is missing CUDA, missing write permissions, platform probing, import errors, vLLM CLI syntax, or any other cause.

Preserved on-host artifacts in the printed `PEER_C_EVIDENCE_DIR`:
- `raw.log` (may contain an extremely long `PEER_C_HELP_BASE64` line; **do not print all**).
- `vllm-serve-help-all.txt` (decoded actual stdout+stderr from failing CLI; primary root-cause evidence).
- `before-protected.json`, `after-protected.json`, `docker-argv-summary.json`, `SHA256SUMS.txt`.

The operator has not yet supplied the decoded CLI failure text or verified the local SHA256SUMS independently. Read the existing files only; never rerun the consumed one-time Docker probe without fresh approval.

## Product-facing next steps (Wizard-first P0)

The permanent product mission is operator-friendly **`./install.sh` and `./uninstall.sh` Wizards for install/switch/inspect/safe removal**, not an indefinite series of manual trial scripts. The peer C official image is a proposed *backend option* of the existing OrcaRouter model, not a new checkpoint family and **NOT** installable/qualified yet. Diagnose this one-shot help failure from preserved evidence via a read-only Wizard detail/report flow; then implement a reusable model+backend compatibility gate that unqualified backends block in normal Wizard install/switch screens. Only after exact image CLI, true model support, live host safety and explicit GPU approval may the backend become wizard-selectable for actual install/switch. Do not change production defaults or misrepresent success.

