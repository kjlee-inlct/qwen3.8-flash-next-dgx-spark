# OrcaRouter R25b — live-harness preflight result — 2026-10-05

## Status

**PASS — LIVE HARNESS PREFLIGHT / NON-MUTATION VERIFIED**

This result records the preflight-only validation of the R25b `initialize_model()` RM-boundary discriminator. No live candidate run was started by this step.

## Repository / runtime state

- repository head: `84cb923b022057c6997f54b374c83e7a25838011`
- managed service before preflight: `active`
- managed container ID before preflight: `9efdcdb49c4e999c06e73478102e9a5f6719fca9da03d6cc8322ce88a73a46ba`
- managed container `StartedAt` before preflight: `2026-10-04T15:31:27.390211899Z`

The same container ID and `StartedAt` were observed after preflight, proving that the preflight did not restart or replace the managed runtime.

## Diagnostic image gate

The marker-only image contract passed:

- `r25_marker_contract=PASS`
- `R25B_IMAGE_PREFLIGHT=PASS`
- image: `vllm-orcarouter-v029-r25-init-marker:v1`
- stability label: `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`
- R25 label: `init-model-boundary-v1`
- `model_restart=NO`
- `managed_service_mutation=NO`
- `persistent_vm_tuning=NO`

## Underlying matched-control harness gate

The reused R24 matched-control preflight also passed:

- profile: `orcarouter-hybrid`
- candidate checkpoint: `models/qwen3.8-h6-modelopt-w4a16`
- candidate image: `vllm-orcarouter-v029-r25-init-marker:v1`
- KV bytes: `17179869184`
- predecessor age: `40516.906 s`
- required predecessor age: `2700 s`
- `predecessor_age_ok=1`
- RM probe targets: `2`
- `model_restart=NO`
- `persistent_vm_tuning=NO`
- `R24_PREFLIGHT=PASS`

## R25b live gate

The dedicated wrapper reported:

- `R25B_LIVE_PREFLIGHT=PASS`
- experiment container: `qwen38-hybrid-r25b-init-marker`
- R25b evidence path: `/tmp/orcarouter-hybrid-r25b-init-model-boundary-01-20261005`
- preserved R24 evidence path: `/tmp/orcarouter-hybrid-r24-kv16-rm-mitigation-01-20261004`
- `model_restart=NO`
- `managed_service_mutation=NO`
- `persistent_vm_tuning=NO`

The outer verification also reported `R25B_PREFLIGHT_AND_NONMUTATION=PASS`.

## Conclusion

All static-image, matched-control, predecessor-age, RM-probe, unique-container/evidence, and managed-runtime non-mutation gates passed. A live R25b measurement is therefore authorized as the next experiment, provided the live invocation uses the dedicated wrapper and explicit `ORCA_R25B_LIVE_ACK=YES` gate.

This preflight does not itself establish where the RM burst falls relative to `QWEN38_R25_INIT_MODEL_BEGIN` / `END`; that requires the live measured run.

PR #244 remains open. No merge is implied.
