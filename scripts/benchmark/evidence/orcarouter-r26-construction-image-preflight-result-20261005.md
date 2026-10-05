# OrcaRouter R26 — construction marker image static preflight result — 2026-10-05

## Status

**PASS — IMAGE BUILD / STATIC CONTRACT / MANAGED NON-MUTATION VERIFIED**

This is a static diagnostic-image gate only. No R26 model load, no R26 live RM measurement, and no managed runtime restart were performed.

## Repository state used on DGX Spark

- branch: `docs/live-profile-switch-acceptance-20260930`
- expected head: `35f11709715aa3b445b95442d7e81262cfcf8518`
- actual head: `35f11709715aa3b445b95442d7e81262cfcf8518`
- worktree: clean

The local branch fast-forwarded to the expected head before the build.

## Base diagnostic image

- tag: `vllm-orcarouter-v029-r25-init-marker:v1`
- image id: `sha256:9abb228a5a4c232d20bf38e33a806f15d4bf62ff61128502349fdf39d70e3a9e`

## R26 image build

Target:

- tag: `vllm-orcarouter-v029-r26-construction-marker:v1`
- image id: `sha256:568d0ac6917b324eef6c29e5f06b0a1ba182b5db043052b13296fe7d3c5428aa`
- created: `2026-10-05T16:44:02.087595123+09:00`
- build RC: `0`
- build log: `/tmp/r26-image-build-20261005-164401.log`

Build-time marker patch validation reported:

```text
installed R26 constructor and ModelOpt MoE timing markers
R26 construction marker image validation passed
```

Image labels:

```text
qwen38.stability-candidate=v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla
qwen38.r25=init-model-boundary-v1
qwen38.r26=construction-boundary-v1
```

## Static image contract

`check-orcarouter-r26-construction-image.sh` returned RC `0` and reported:

```text
r25_inherited_marker_contract=PASS
r26_model_constructor_contract=PASS
r26_modelopt_moe_contract=PASS
R26_IMAGE_PREFLIGHT=PASS
model_restart=NO
managed_service_mutation=NO
persistent_vm_tuning=NO
```

Static preflight log:

`/tmp/r26-image-preflight-20261005-164402.log`

The static contract therefore closes the following checks:

- inherited R25 `initialize_model()` boundary remains present and ordered correctly;
- R26 top-level `model_class(...)` constructor boundary is present and ordered correctly;
- R26 `ModelOptNvFp4FusedMoE.create_weights()` and packed `w13_weight` / `w2_weight` marker contracts are present;
- inherited stability label and R25 label are unchanged;
- R26 construction-boundary label is exact.

## Managed runtime non-mutation

Before build/static preflight:

```text
service=active
READY after 0s: qwen38-flash-next http://127.0.0.1:8888
managed_container_id=e5422a909bf4e9b8c84bfa1a864b9ddeedac4686de5c449eb6aaf0a645add2cd
managed_started_at=2026-10-05T05:42:55.476327457Z
served_model=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4
max_model_len=262144
```

After build/static preflight:

```text
service=active
managed_container_id=e5422a909bf4e9b8c84bfa1a864b9ddeedac4686de5c449eb6aaf0a645add2cd
managed_started_at=2026-10-05T05:42:55.476327457Z
served_model=orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4
max_model_len=262144
```

Both the exact Docker container ID and `StartedAt` are unchanged. The managed runtime therefore did not restart or get replaced during this gate. The post-gate `/health` request succeeded and `/v1/models` still exposed the exact expected OrcaRouter identity with `max_model_len=262144`.

## Final gate token

```text
R26_BUILD_RC=0
R26_STATIC_PREFLIGHT_RC=0
R26_BUILD_AND_STATIC_PREFLIGHT=PASS
```

## Classification

- repository/image static gate: **PASS**
- diagnostic image contract: **PASS**
- managed runtime non-mutation: **PASS**
- functional live classification: **NOT MEASURED IN THIS GATE**
- host-stability live classification: **NOT MEASURED IN THIS GATE**

No claim about RM activity, RM OOM count, functional live behavior, or host stability is made from this static gate.

## Next gate

R26 harness preflight is now authorized. It must remain preflight-only and must verify the inherited R24 matched-control configuration, unique R26 evidence/container names, exact `r26_rm` probe-definition transform, stale-probe absence, predecessor-age requirement, and no managed service mutation.

A live R26 measured run remains **not authorized** until the harness preflight is closed and recorded canonically.

PR #244 remains open. No merge is implied or authorized.
