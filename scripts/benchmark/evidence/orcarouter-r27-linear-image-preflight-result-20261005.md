# OrcaRouter R27 — W4A16-linear diagnostic image build / static preflight result — 2026-10-05

## Status

**PASS — MARKER-ONLY IMAGE BUILT — STATIC IMAGE CONTRACT PASS — MANAGED RUNTIME UNCHANGED — NO LIVE RUN AUTHORIZED YET**

This gate built the R27 marker-only diagnostic image from the already validated R26 image and ran only the static image checker. No R27 harness preflight and no model restart/live measured run occurred.

## Repository identity

The DGX command pinned the branch to:

`f3fb422edc13d056b08f34efa5f7b9ad24ded2f4`

The worktree was clean before the gate.

Repository CI for this head had already closed SUCCESS, including shell syntax, ShellCheck, Python compile, unit tests, and whitespace checks.

## Base image

Validated R26 base image:

- tag: `vllm-orcarouter-v029-r26-construction-marker:v1`
- image id: `sha256:568d0ac6917b324eef6c29e5f06b0a1ba182b5db043052b13296fe7d3c5428aa`
- stability label: `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`
- R26 label: `construction-boundary-v1`

## R27 image build

Built image:

- tag: `vllm-orcarouter-v029-r27-linear-marker:v1`
- image id: `sha256:e9e92c5cb98d443a8410f21345cb0e07c30c9e7c84516cedcc2a6dc213934119`
- created: `2026-10-05T18:46:17.204223912+09:00`
- stability label: `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`
- inherited R25 label: `init-model-boundary-v1`
- inherited R26 label: `construction-boundary-v1`
- R27 label: `w4a16-linear-boundary-v1`

Build validation emitted:

```text
installed R27 W4A16-linear and Qwen4Exp-layer timing markers
R27 residual-constructor marker image validation passed
R27_BUILD_RC=0
```

Local build log:

`/tmp/r27-image-build-20261005-184616.log`

## Static image preflight

The exact static checker reported:

```text
r26_inherited_constructor_contract=PASS
r26_inherited_modelopt_moe_contract=PASS
r27_w4a16_linear_contract=PASS
r27_qwen4_layer_contract=PASS
r27_ple_mmap_placeholder_contract=PASS
R27_IMAGE_PREFLIGHT=PASS
image=vllm-orcarouter-v029-r27-linear-marker:v1
stability_label=v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla
r25_label=init-model-boundary-v1
r26_label=construction-boundary-v1
r27_label=w4a16-linear-boundary-v1
model_restart=NO
managed_service_mutation=NO
persistent_vm_tuning=NO
R27_STATIC_PREFLIGHT_RC=0
```

Local static-preflight log:

`/tmp/r27-image-preflight-20261005-184617.log`

This closes the intended marker contracts before any model-load experiment:

1. inherited R26 top-level constructor markers remain present;
2. inherited R26 ModelOpt-MoE/w13/w2 markers remain present;
3. R27 `ModelOptNvFp4W4A16LinearMethod.create_weights()` markers are present;
4. the packed W4A16 `weight` sub-boundary markers are present;
5. the exact NVIDIA `Qwen4ExpDecoderLayer` construction markers are present;
6. the v0.29 PLE-mmap placeholder contract remains intact.

## Managed-runtime non-mutation

Before build/static preflight:

```text
service=active
managed_id=cd2d34ec90de03b74a8cb8dc76a2311dd4b90b88bd2700b35026016f9c05f911
managed_started=2026-10-05T08:55:17.15500875Z
served_model=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4
max_model_len=262144
readiness=READY after 0s
```

After build/static preflight:

```text
service=active
managed_id=cd2d34ec90de03b74a8cb8dc76a2311dd4b90b88bd2700b35026016f9c05f911
managed_started=2026-10-05T08:55:17.15500875Z
served_model=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4
max_model_len=262144
readiness=READY after 0s
```

The managed container ID and `StartedAt` are exactly unchanged. The exact served model identity and `max_model_len=262144` were revalidated after the gate.

Therefore:

```text
model_restart=NO
managed_service_mutation=NO
persistent_vm_tuning=NO
R27_BUILD_AND_STATIC_PREFLIGHT=PASS
```

## Closure

The R27 marker-only image is valid for the next gate.

The next authorized action is **R27 guarded harness preflight only**. That preflight may validate the inherited matched-control harness, exact four-probe transformation to `r27_rm`, stale-probe absence, predecessor/evidence prerequisites, and managed non-mutation, but it must not launch the candidate model.

A live R27 measurement remains unauthorized until the harness-preflight result is recorded canonically and closed PASS.

PR #244 remains open. No merge is implied or authorized.
