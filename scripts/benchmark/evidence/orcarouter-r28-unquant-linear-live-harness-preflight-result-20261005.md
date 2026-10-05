# OrcaRouter R28 — unquantized Linear live-harness preflight result — 2026-10-05

## Status

**CLOSED / PASS — GUARDED HARNESS PREFLIGHT VALID — EXACTLY ONE R28 LIVE MEASUREMENT MAY BE AUTHORIZED**

Canonical predecessors:

- `scripts/benchmark/evidence/orcarouter-r28-unquant-linear-boundary-plan-20261005.md`
- `scripts/benchmark/evidence/orcarouter-r28-unquant-linear-image-preflight-result-20261005.md`

This preflight did not launch the candidate model and did not create live evidence.

## Preflight contracts

Before entering the inherited R24 matched-control preflight:

- `stale_probe_groups=NONE`
- `r26_inherited_constructor_contract=PASS`
- `r26_inherited_modelopt_moe_contract=PASS`
- `r27_inherited_qwen4_layer_contract=PASS`
- `r28_unquant_linear_contract=PASS`
- `R28_IMAGE_PREFLIGHT=PASS`
- `r28_probe_definition_contract=PASS`

Validated candidate image:

`vllm-orcarouter-v029-r28-unquant-linear-marker:v1`

Validated labels:

- stability: `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`
- R25: `init-model-boundary-v1`
- R26: `construction-boundary-v1`
- R27: `w4a16-linear-boundary-v1`
- R28: `unquant-linear-boundary-v1`

## Inherited R24 matched-control gate

The R24 H6/R22-matched preflight reported:

- profile: `orcarouter-hybrid`
- candidate checkpoint: `/home/inlc/Workspace/llm/qwen3.8-flash-next-dgx-spark/models/qwen3.8-h6-modelopt-w4a16`
- candidate image: `vllm-orcarouter-v029-r28-unquant-linear-marker:v1`
- candidate stability label: `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`
- forced KV bytes: `17179869184`
- predecessor age: `3989.048 s`
- minimum predecessor age: `2700 s`
- `predecessor_age_ok=1`
- RM probe target count: `2`
- `model_restart=NO`
- `persistent_vm_tuning=NO`
- `R24_PREFLIGHT=PASS`

R28 wrapper then reported:

`R28_LIVE_PREFLIGHT=PASS`

Reserved live identity:

- experiment container: `qwen38-hybrid-r28-unquant-linear-marker`
- evidence path: `/tmp/orcarouter-hybrid-r28-unquant-linear-boundary-01-20261005`
- preserved R24 evidence: `/tmp/orcarouter-hybrid-r24-kv16-rm-mitigation-01-20261004`
- preserved R26 evidence: `/tmp/orcarouter-hybrid-r26-construction-boundary-01-20261005`
- preserved R27 evidence: `/tmp/orcarouter-hybrid-r27-linear-boundary-01-20261005`
- managed served name: `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`

The wrapper remained explicitly non-mutating:

- `model_restart=NO`
- `managed_service_mutation=NO`
- `persistent_vm_tuning=NO`

Final harness preflight RC:

`R28_HARNESS_PREFLIGHT_RC=0`

Preflight log:

`/tmp/r28-harness-preflight-20261005-211147.log`

## Post-preflight freshness and managed non-mutation

Managed runtime remained unchanged across the entire static + harness-preflight sequence:

- container ID before: `9415187362d6f8b2d118d995aaa307b2c427c22d44d1548a78a166fe2c95812b`
- container ID after: `9415187362d6f8b2d118d995aaa307b2c427c22d44d1548a78a166fe2c95812b`
- `StartedAt` before: `2026-10-05T11:05:18.894715967Z`
- `StartedAt` after: `2026-10-05T11:05:18.894715967Z`
- service: active
- exact managed OrcaRouter: READY immediately
- `max_model_len=262144`

Freshness closure:

- `live_evidence_created=NO`
- `experiment_container_created=NO`
- `stale_r28_probe_group=NO`

Final combined gate:

`R28_STATIC_AND_HARNESS_PREFLIGHT=PASS`

## Authorization decision

All prerequisites in the R28 plan are now closed PASS. Therefore exactly **one** guarded R28 live measured run is authorized, using the existing R28 runner and the reserved fresh evidence path above.

The live run must retain the matched R24 controls and narrow direct-RM trace only. Do not broaden tracing and do not apply H11 before R28 closes.

A valid run remains subject to the strict classification policy: any confirmed NVIDIA RM `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` is **HOST-STABILITY FAIL**, even if fallback recovers and the runtime reaches READY. FUNCTIONAL and HOST-STABILITY results remain separate.

RM logical requested bytes remain activity volume, not exact resident ownership. R28 userspace marker overlap remains temporal localization, not causal proof.
