# OrcaRouter R25b — recovery + corrected live-harness preflight result — 2026-10-05

## Result

**PASS — ATTEMPT 01 PRESERVED / STALE PROBES CLEANED / CORRECTED PREFLIGHT PASS / ATTEMPT 02 AUTHORIZED**

This result follows the setup-invalid first live attempt documented in:

- `orcarouter-r25b-live-attempt01-probe-group-invalid-20261005.md`

No R25b measurement claim is made from attempt 01.

## Branch / repository state

- branch: `docs/live-profile-switch-acceptance-20260930`
- expected/actual head before this evidence-only commit: `ae6ffe1fde09bc966a7d5cee58a947a666da2d86`
- worktree: clean
- corrected probe-group transform implementation CI: #1077 SUCCESS

## Attempt-01 preservation

Partial attempt-01 evidence remained intact at:

`/tmp/orcarouter-hybrid-r25b-init-model-boundary-01-20261005`

Observed files included the candidate image/model identity, collector log/control files, allocator conditioning timestamps, predecessor-age data, original `probe-definitions.txt`, repository head, start timestamps, host page size, and managed-restoration artifacts.

The attempt-01 evidence was not deleted or reused.

## Experiment-container state

`qwen38-hybrid-r25b-init-marker` was absent before corrected preflight.

This confirms attempt 01 failed before candidate-container launch.

## Managed-runtime recovery

Managed service was active and immediately READY:

- service: `qwen38-flash-next.service`
- container: `qwen38-flash-next`
- exact served model: `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`
- `max_model_len=262144`
- managed container id: `22c78d93eef27e1777c760ff7bd0868824dddd61261fbd9f7a541f6a6fe58efc`
- managed `StartedAt`: `2026-10-05T02:54:12.603514562Z`

`wait-ready.sh` returned READY after 0 s.

## Failed-attempt stale probe cleanup

Tracefs:

`/sys/kernel/tracing`

Observed before cleanup:

- `r24_rm`: PRESENT
  - `nv_alloc_pages_entry`
  - `nv_alloc_pages_ret`
  - `nv_alloc_system_pages_entry`
  - `nv_alloc_system_pages_ret`
- `r25b_rm`: ABSENT

This directly matches the attempt-01 wrapper bug: the inherited R24 heredoc materialized the hard-coded `r24_rm` events while the wrapper validated `r25b_rm`.

Cleanup was restricted to the four expected RM events only. No unexpected event names were present.

Observed result:

- `stale_probe_cleanup=APPLIED`
- `stale_probe_cleanup=PASS`

## Corrected R25b preflight

Observed gates:

- `stale_probe_groups=NONE`
- `r25_marker_contract=PASS`
- `R25B_IMAGE_PREFLIGHT=PASS`
- image: `vllm-orcarouter-v029-r25-init-marker:v1`
- stability label: `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`
- diagnostic label: `qwen38.r25=init-model-boundary-v1`
- `r25b_probe_definition_contract=PASS`
- `R24_PREFLIGHT=PASS`
- `R25B_LIVE_PREFLIGHT=PASS`
- corrected preflight RC: `0`

Matched-control values:

- profile: `orcarouter-hybrid`
- candidate checkpoint: `models/qwen3.8-h6-modelopt-w4a16`
- candidate image: `vllm-orcarouter-v029-r25-init-marker:v1`
- KV bytes: `17179869184`
- predecessor age: `8585.831 s`
- minimum predecessor age: `2700 s`
- `predecessor_age_ok=1`
- RM probe target count: `2`
- experiment container: `qwen38-hybrid-r25b-init-marker`
- retry evidence: `/tmp/orcarouter-hybrid-r25b-init-model-boundary-02-20261005`
- preserved R24 evidence: `/tmp/orcarouter-hybrid-r24-kv16-rm-mitigation-01-20261004`

No model restart, managed-service mutation, or persistent VM tuning occurred during corrected preflight.

## Managed non-mutation closure

Before/after corrected preflight:

- container id before: `22c78d93eef27e1777c760ff7bd0868824dddd61261fbd9f7a541f6a6fe58efc`
- container id after: `22c78d93eef27e1777c760ff7bd0868824dddd61261fbd9f7a541f6a6fe58efc`
- `StartedAt` before: `2026-10-05T02:54:12.603514562Z`
- `StartedAt` after: `2026-10-05T02:54:12.603514562Z`

Final token:

`R25B_RECOVERY_AND_CORRECTED_PREFLIGHT=PASS`

## Classification

Attempt 01 remains:

**SETUP INVALID / NO MEASUREMENT CLAIM**

Recovery/corrected-preflight gate is:

**PASS**

Therefore exactly one corrected measured retry is authorized, using the preserved-control runner and the new evidence path:

`/tmp/orcarouter-hybrid-r25b-init-model-boundary-02-20261005`

The strict host-stability policy remains unchanged: any confirmed NVIDIA RM `_memdescAllocInternal` / `NV_ERR_NO_MEMORY` in a valid measured retry is HOST-STABILITY FAIL even if fallback recovers and the runtime reaches READY.

RM logical bytes remain activity volume rather than exact resident ownership; initialize-model overlap remains temporal localization rather than causal proof.
