# OrcaRouter R26 — live harness preflight result — 2026-10-05

## Status

**PASS — R26 LIVE HARNESS PREFLIGHT / MANAGED NON-MUTATION VERIFIED**

This gate is preflight-only. No R26 candidate model load, no R26 live RM measurement, and no managed runtime restart were performed.

## Repository state used on DGX Spark

- branch: `docs/live-profile-switch-acceptance-20260930`
- expected head: `80efd0e789493fd69ca6455ff794308f8723adff`
- actual head: `80efd0e789493fd69ca6455ff794308f8723adff`
- worktree: clean

## Diagnostic image

- tag: `vllm-orcarouter-v029-r26-construction-marker:v1`
- image id: `sha256:568d0ac6917b324eef6c29e5f06b0a1ba182b5db043052b13296fe7d3c5428aa`
- stability label: `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`
- inherited R25 label: `init-model-boundary-v1`
- R26 label: `construction-boundary-v1`

Static marker contracts were revalidated inside the harness preflight:

```text
r25_inherited_marker_contract=PASS
r26_model_constructor_contract=PASS
r26_modelopt_moe_contract=PASS
R26_IMAGE_PREFLIGHT=PASS
```

## Harness safety / transform contract

The preflight reported:

```text
stale_probe_groups=NONE
r26_probe_definition_contract=PASS
```

The transformed inherited R24 harness therefore has the exact `r26_rm` group contract and no stale `r24_rm`, `r25b_rm`, or `r26_rm` event group blocked the run.

Evidence/container identities remained unique:

- preserved R24 evidence: `/tmp/orcarouter-hybrid-r24-kv16-rm-mitigation-01-20261004`
- new R26 evidence: `/tmp/orcarouter-hybrid-r26-construction-boundary-01-20261005`
- experiment container: `qwen38-hybrid-r26-construction-marker`

## Matched-control preflight

The inherited R24 matched-control preflight passed with:

```text
profile=orcarouter-hybrid
candidate_checkpoint=/home/inlc/Workspace/llm/qwen3.8-flash-next-dgx-spark/models/qwen3.8-h6-modelopt-w4a16
candidate_image=vllm-orcarouter-v029-r26-construction-marker:v1
candidate_image_label=v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla
kv_bytes=17179869184
predecessor_age_s=9373.825
minimum_predecessor_age_s=2700
predecessor_age_ok=1
rm_probe_target_count=2
R24_PREFLIGHT=PASS
R26_LIVE_PREFLIGHT=PASS
```

The candidate therefore remains the H6 matched-control configuration with forced 16 GiB KV and the same narrow RM probe targets used by the validated R24/R25b sequence.

## Managed runtime non-mutation

Before harness preflight:

```text
service=active
READY after 0s: qwen38-flash-next http://127.0.0.1:8888
managed_container_id=e5422a909bf4e9b8c84bfa1a864b9ddeedac4686de5c449eb6aaf0a645add2cd
managed_started_at=2026-10-05T05:42:55.476327457Z
served_model=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4
max_model_len=262144
```

After harness preflight:

```text
service=active
managed_container_id=e5422a909bf4e9b8c84bfa1a864b9ddeedac4686de5c449eb6aaf0a645add2cd
managed_started_at=2026-10-05T05:42:55.476327457Z
READY after 0s: qwen38-flash-next http://127.0.0.1:8888
served_model=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4
max_model_len=262144
```

Both exact Docker container ID and `StartedAt` were unchanged.

The harness explicitly reported:

```text
model_restart=NO
managed_service_mutation=NO
persistent_vm_tuning=NO
```

## Final gate token

```text
R26_HARNESS_PREFLIGHT_RC=0
R26_HARNESS_PREFLIGHT_AND_NONMUTATION=PASS
```

Preflight log:

`/tmp/r26-harness-preflight-20261005-171908.log`

## Classification

- R26 image contract: **PASS**
- probe transform / stale-group gate: **PASS**
- inherited matched-control preflight: **PASS**
- predecessor-age gate: **PASS**
- managed runtime non-mutation: **PASS**
- functional live classification: **NOT MEASURED IN THIS GATE**
- host-stability live classification: **NOT MEASURED IN THIS GATE**

No live RM or OOM claim is made from this preflight.

## Next gate

Both R26 prerequisite gates are now closed:

1. image build/static preflight — PASS;
2. guarded harness preflight/non-mutation — PASS.

A single guarded R26 live measured run may now be authorized, using the existing R26 runner, exact candidate image, unique evidence path, narrow RM trace, and strict functional-versus-host-stability classification. Do not broaden tracing and do not apply H11 before the R26 localization result is known.

PR #244 remains open. No merge is implied or authorized.
