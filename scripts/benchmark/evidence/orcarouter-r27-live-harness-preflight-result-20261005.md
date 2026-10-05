# OrcaRouter R27 — guarded harness preflight result — 2026-10-05

## Status

**PASS — R27 HARNESS PREFLIGHT CLOSED — MANAGED RUNTIME UNCHANGED — SINGLE LIVE MEASURED RUN AUTHORIZED NEXT**

This gate executed only the guarded R27 harness preflight. It did not launch the R27 candidate model and did not create the R27 live evidence directory or experiment container.

## Repository / image identity

Repository head used on the DGX host:

`f359a6183233164bc4ec0b5d6febe68d5cc5dc5e`

Candidate diagnostic image:

- tag: `vllm-orcarouter-v029-r27-linear-marker:v1`
- image id: `sha256:e9e92c5cb98d443a8410f21345cb0e07c30c9e7c84516cedcc2a6dc213934119`
- stability label: `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`
- R25 label: `init-model-boundary-v1`
- R26 label: `construction-boundary-v1`
- R27 label: `w4a16-linear-boundary-v1`

## Preflight contract

The guarded runner reported:

```text
stale_probe_groups=NONE
r26_inherited_constructor_contract=PASS
r26_inherited_modelopt_moe_contract=PASS
r27_w4a16_linear_contract=PASS
r27_qwen4_layer_contract=PASS
r27_ple_mmap_placeholder_contract=PASS
R27_IMAGE_PREFLIGHT=PASS
r27_probe_definition_contract=PASS
R24_PREFLIGHT=PASS
R27_LIVE_PREFLIGHT=PASS
```

Matched-control values:

```text
profile=orcarouter-hybrid
candidate_checkpoint=/home/inlc/Workspace/llm/qwen3.8-flash-next-dgx-spark/models/qwen3.8-h6-modelopt-w4a16
candidate_image=vllm-orcarouter-v029-r27-linear-marker:v1
kv_bytes=17179869184
predecessor_age_s=3683.743
minimum_predecessor_age_s=2700
predecessor_age_ok=1
rm_probe_target_count=2
```

The R27 wrapper uses a transformed ephemeral copy of the validated R24 harness. The transform contract closed PASS with exactly four inherited `r24_rm/...` probe definitions rewritten to `r27_rm/...`; no historical R24 harness file was edited.

Preserved evidence prerequisites were present:

- R24: `/tmp/orcarouter-hybrid-r24-kv16-rm-mitigation-01-20261004`
- R26: `/tmp/orcarouter-hybrid-r26-construction-boundary-01-20261005`

Reserved new R27 live evidence path:

`/tmp/orcarouter-hybrid-r27-linear-boundary-01-20261005`

Reserved experiment container:

`qwen38-hybrid-r27-linear-marker`

Neither was created by preflight.

## Trace / stale-probe state

Before the guarded runner:

`stale_probe_groups_before=NONE`

The runner itself reported:

`stale_probe_groups=NONE`

After the preflight:

`stale_probe_groups_after=NONE`

Checked groups:

- `r24_rm`
- `r25b_rm`
- `r26_rm`
- `r27_rm`

## Managed-runtime non-mutation

Before preflight:

```text
service=active
managed_id=cd2d34ec90de03b74a8cb8dc76a2311dd4b90b88bd2700b35026016f9c05f911
managed_started=2026-10-05T08:55:17.15500875Z
served_model=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4
max_model_len=262144
readiness=READY after 0s
```

After preflight:

```text
service=active
managed_id=cd2d34ec90de03b74a8cb8dc76a2311dd4b90b88bd2700b35026016f9c05f911
managed_started=2026-10-05T08:55:17.15500875Z
served_model=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4
max_model_len=262144
readiness=READY after 0s
```

The managed container ID and `StartedAt` are exactly unchanged. Exact served identity and `max_model_len=262144` were revalidated after preflight.

Therefore:

```text
R27_HARNESS_PREFLIGHT_RC=0
R27_HARNESS_PREFLIGHT_GATE=PASS
model_restart=NO
managed_service_mutation=NO
persistent_vm_tuning=NO
```

Local preflight log:

`/tmp/r27-harness-preflight-20261005-185640.log`

## Closure / authorization

All prerequisite R27 gates are now closed PASS:

1. repository CI — PASS;
2. marker-only image build — PASS;
3. static image contract — PASS;
4. static managed non-mutation — PASS;
5. guarded harness preflight — PASS;
6. harness managed non-mutation — PASS.

The next authorized action is **one guarded R27 live measured run** using the existing R27 runner, exact diagnostic image, fresh default R27 evidence path, and explicit `ORCA_R27_LIVE_ACK=YES`.

This authorization is for one measurement only. Do not reuse or delete evidence if the run produces partial or failed evidence; classify and preserve it first.

Strict classification remains unchanged: any confirmed NVIDIA RM `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` in a valid measured run is **HOST-STABILITY FAIL**, regardless of functional recovery.

PR #244 remains open. No merge is implied or authorized.
