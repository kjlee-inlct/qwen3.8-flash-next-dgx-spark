# OrcaRouter R28 — unquantized Linear marker image preflight result — 2026-10-05

## Status

**CLOSED / PASS — STATIC MARKER IMAGE VALIDATED — MANAGED RUNTIME UNCHANGED — NO LIVE MEASUREMENT CLAIM**

Canonical plan:

- `scripts/benchmark/evidence/orcarouter-r28-unquant-linear-boundary-plan-20261005.md`

Repository head used on the DGX static gate:

`856ee0a34808e7cef5f0e32a3326bd7e57b72760`

The local branch fast-forwarded cleanly to that exact head and the working tree gate passed before static work.

## Managed baseline before static work

Managed service was active and READY immediately.

Exact served identity:

- model: `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`
- `max_model_len=262144`
- managed container ID: `9415187362d6f8b2d118d995aaa307b2c427c22d44d1548a78a166fe2c95812b`
- managed `StartedAt`: `2026-10-05T11:05:18.894715967Z`

Reserved R28 live resources were absent before the build:

- evidence path `/tmp/orcarouter-hybrid-r28-unquant-linear-boundary-01-20261005`: absent
- experiment container `qwen38-hybrid-r28-unquant-linear-marker`: absent

## Parent image

R27 parent image:

- image: `vllm-orcarouter-v029-r27-linear-marker:v1`
- image ID: `sha256:e9e92c5cb98d443a8410f21345cb0e07c30c9e7c84516cedcc2a6dc213934119`
- label: `qwen38.r27=w4a16-linear-boundary-v1`

## R28 build

Built:

`vllm-orcarouter-v029-r28-unquant-linear-marker:v1`

Build result:

- `R28_BUILD_RC=0`
- image ID: `sha256:54c1ae1ba05fc34ec10881db4e5a333895eebf5472a5d282fefa354fe39a762f`
- build-time patch message: `installed R28 UnquantizedLinearMethod timing markers`
- build-time validation: `R28 unquantized-linear marker image validation passed`
- build log: `/tmp/r28-image-build-20261005-211129.log`

## Static image contract

Static checker result:

- `r26_inherited_constructor_contract=PASS`
- `r26_inherited_modelopt_moe_contract=PASS`
- `r27_inherited_qwen4_layer_contract=PASS`
- `r28_unquant_linear_contract=PASS`
- `R28_IMAGE_PREFLIGHT=PASS`
- `R28_STATIC_PREFLIGHT_RC=0`

Validated labels:

- `qwen38.stability-candidate=v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`
- `qwen38.r25=init-model-boundary-v1`
- `qwen38.r26=construction-boundary-v1`
- `qwen38.r27=w4a16-linear-boundary-v1`
- `qwen38.r28=unquant-linear-boundary-v1`

Static checker explicitly reported:

- `model_restart=NO`
- `managed_service_mutation=NO`
- `persistent_vm_tuning=NO`

Static log:

`/tmp/r28-image-preflight-20261005-211130.log`

## Managed non-mutation closure

After the R28 image build and static checker:

- managed container ID remained exactly `9415187362d6f8b2d118d995aaa307b2c427c22d44d1548a78a166fe2c95812b`;
- managed `StartedAt` remained exactly `2026-10-05T11:05:18.894715967Z`;
- service remained active;
- exact OrcaRouter model identity remained READY immediately;
- `max_model_len` remained `262144`.

Therefore the static R28 gate did not restart or mutate the managed runtime.

## Classification

This is a static instrumentation gate only. It makes no FUNCTIONAL or HOST-STABILITY live-measurement claim.

The marker-only R28 image is accepted for the guarded harness preflight.
