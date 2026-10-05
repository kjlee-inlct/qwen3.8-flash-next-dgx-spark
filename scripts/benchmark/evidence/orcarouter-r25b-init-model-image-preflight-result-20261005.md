# OrcaRouter R25b — initialize_model marker image static preflight result — 2026-10-05

## Status

**PASS — IMAGE BUILT / STATIC PREFLIGHT PASS / MANAGED RUNTIME UNTOUCHED**

This result records only the diagnostic-image build and static preflight. No R25b model restart or live RM measurement occurred.

## Repository state

- branch: `docs/live-profile-switch-acceptance-20260930`
- tested head: `14aa187425fd5aa7d8845b5acae806f52bc91238`
- worktree: clean before build

## Base image

- image: `vllm-orcarouter-v029:v1`
- image id: `sha256:dba5d8af279fb85901e6d8911f1a59ecc45b669b0948ab8d01d7c7d1c5815734`
- stability label: `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`

## Diagnostic image

- image: `vllm-orcarouter-v029-r25-init-marker:v1`
- image id: `sha256:9abb228a5a4c232d20bf38e33a806f15d4bf62ff61128502349fdf39d70e3a9e`
- inherited stability label: `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`
- R25 label: `init-model-boundary-v1`

Image build validation reported:

- patch installation: `installed R25 initialize_model timing markers`
- image validation: `R25 initialize_model marker image validation passed`

The image adds only the two intended INFO markers around `initialize_model(...)`:

- `QWEN38_R25_INIT_MODEL_BEGIN`
- `QWEN38_R25_INIT_MODEL_END`

## Static preflight

Observed output:

```text
r25_marker_contract=PASS
R25B_IMAGE_PREFLIGHT=PASS
image=vllm-orcarouter-v029-r25-init-marker:v1
stability_label=v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla
r25_label=init-model-boundary-v1
model_restart=NO
managed_service_mutation=NO
persistent_vm_tuning=NO
```

Command return code: `0`.

## Managed-runtime non-mutation check

Before build/preflight:

- service: `active`
- container id: `9efdcdb49c4e999c06e73478102e9a5f6719fca9da03d6cc8322ce88a73a46ba`
- StartedAt: `2026-10-04T15:31:27.390211899Z`

After build/preflight:

- service: `active`
- container id: `9efdcdb49c4e999c06e73478102e9a5f6719fca9da03d6cc8322ce88a73a46ba`
- StartedAt: `2026-10-04T15:31:27.390211899Z`

The exact container id and start timestamp were unchanged. Therefore the diagnostic build/static-preflight step did not restart or replace the managed runtime.

## Conclusion

The R25b marker-only image is ready for the next gate. This result does **not** authorize reusing the preserved R24 container or evidence path.

A live R25b run must use:

1. a unique experiment container name;
2. a unique evidence directory;
3. the same R24/R22-matched H6 16 GiB runtime controls;
4. the established narrow RM trace only;
5. the two new userspace `initialize_model()` markers as the additional discriminator;
6. the same strict rule that any confirmed RM `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` in a valid run is HOST-STABILITY FAIL.

The live runner must have a separate preflight gate and must preserve/restore the managed OrcaRouter service.
