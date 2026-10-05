# OrcaRouter R25b — initialize_model RM-boundary discriminator — plan — 2026-10-05

## Status

**LIVE ATTEMPT 01 SETUP INVALID — PROBE-GROUP FIX IMPLEMENTED — RETRY BLOCKED PENDING RECOVERY + CORRECTED PREFLIGHT**

R25 read-only localization showed that the R24 64 KiB NVIDIA RM episode is only about 3.218 seconds long even though checkpoint weight filling takes 522.10 seconds. `99.276945%` of traced order-4 activity falls between the existing `Loading model from scratch...` marker and `Loading weights took ...`, but the first approximately `559.688 MiB` begins about `0.395 s` before the existing model-load marker.

The pinned vLLM v0.29 `BaseModelLoader.load_model()` order is:

1. enter the target device context;
2. `initialize_model(...)`;
3. `load_weights(...)`;
4. online-quant finalization when applicable;
5. `process_weights_after_loading(...)`.

R25 therefore narrows the next question to model/parameter construction versus checkpoint filling. R25b adds exactly two userspace log boundaries around `initialize_model()` and otherwise preserves the R24 runtime/harness.

## Question

Does the approximately 77 GiB 64 KiB `nv_alloc_pages` episode occur primarily inside `initialize_model()` before checkpoint weight filling begins?

This is still a localization discriminator, not a mitigation test.

## Diagnostic image

Repository additions:

- `scripts/patch-v029-r25-init-model-markers.py`;
- `scripts/Dockerfile.v029-r25-init-model-markers`;
- `scripts/benchmark/check-orcarouter-r25b-init-model-image.sh`.

Image tag:

`vllm-orcarouter-v029-r25-init-marker:v1`

The image derives directly from `vllm-orcarouter-v029:v1`. It adds only these INFO markers in `BaseModelLoader.load_model()`:

- `QWEN38_R25_INIT_MODEL_BEGIN` immediately before entering the target-device `initialize_model(...)` block;
- `QWEN38_R25_INIT_MODEL_END` immediately after `initialize_model(...)` returns and before `load_weights(...)`.

It does not change checkpoint contents, parameter classes, quantization behavior, runtime flags, PLE mmap, exact QSA, KV size, host conditioning, allocator behavior, or post-load handling.

## Completed image/static gate

Canonical result:

- `orcarouter-r25b-init-model-image-preflight-result-20261005.md`

Observed diagnostic image:

- base image id: `sha256:dba5d8af279fb85901e6d8911f1a59ecc45b669b0948ab8d01d7c7d1c5815734`;
- diagnostic image id: `sha256:9abb228a5a4c232d20bf38e33a806f15d4bf62ff61128502349fdf39d70e3a9e`;
- inherited stability label: `v0.29+qsa-layer-type+ple-mmap+exact-qsa+fla`;
- diagnostic label: `qwen38.r25=init-model-boundary-v1`;
- marker/source contract: PASS;
- `R25B_IMAGE_PREFLIGHT=PASS`;
- model restart: NO;
- managed-service mutation: NO;
- persistent VM tuning: NO.

The managed container id and `StartedAt` timestamp were identical before and after the image build/static preflight, closing this gate as non-mutating.

## Live runner

Repository additions:

- `scripts/benchmark/run-orcarouter-r25b-init-model-boundary.sh`;
- `scripts/benchmark/analyze-orcarouter-r25b-init-model-overlap.py`;
- `tests/test_orcarouter_r25b_init_model_overlap.py`.

The R25b runner does **not** edit the historical R24 runner. Instead it creates an ephemeral `/tmp` copy and transforms only the R25b-local harness identity:

1. repository-root injection so the temporary copy resolves the current checkout;
2. experiment container name → `qwen38-hybrid-r25b-init-marker`;
3. shell kprobe group variable → `r25b_rm`;
4. all exactly four hard-coded R24 kprobe definitions → `r25b_rm/...`.

The transform now requires exactly four probe-definition replacements, rejects any remaining `r24_rm/` definition, and requires exactly four resulting `r25b_rm/` definitions. A regression test executes the exact embedded transform against the canonical R24 harness.

The corrected retry evidence directory is:

`/tmp/orcarouter-hybrid-r25b-init-model-boundary-02-20261005`

The failed attempt-01 directory is preserved and must not be reused:

`/tmp/orcarouter-hybrid-r25b-init-model-boundary-01-20261005`

The preserved R24 directory remains:

`/tmp/orcarouter-hybrid-r24-kv16-rm-mitigation-01-20261004`

The runner explicitly refuses to reuse the R24 path or container name. It also blocks preflight/live execution if stale `r24_rm` or `r25b_rm` kprobe groups are present.

Default invocation remains safe: calling the R25b runner with no arguments performs `--preflight`. A live run additionally requires both explicit `run` mode and `ORCA_R25B_LIVE_ACK=YES`.

## Completed original live-harness preflight gate

Canonical result:

- `orcarouter-r25b-live-harness-preflight-result-20261005.md`

The original preflight passed and was non-mutating:

- `R25B_IMAGE_PREFLIGHT=PASS`;
- `R24_PREFLIGHT=PASS`;
- `R25B_LIVE_PREFLIGHT=PASS`;
- `R25B_PREFLIGHT_AND_NONMUTATION=PASS`;
- predecessor age: `40516.906 s` (minimum `2700 s`);
- `predecessor_age_ok=1`;
- RM probe target count: `2`;
- candidate image: `vllm-orcarouter-v029-r25-init-marker:v1`;
- KV bytes: `17179869184`;
- model restart during preflight: NO;
- managed-service mutation during preflight: NO;
- persistent VM tuning: NO.

That preflight did not materialize the probe definitions, so it could not detect the later heredoc group mismatch.

## Live attempt 01 — setup invalid

Canonical result:

- `orcarouter-r25b-live-attempt01-probe-group-invalid-20261005.md`

The first live invocation passed the preflight and explicit ACK gate, then failed in `create_probes()` with:

`ORCA_R24_ERROR: probe event not materialized: r25b_rm:nv_alloc_pages_entry`

Root cause: the initial wrapper changed `GROUP="r24_rm"` to `GROUP="r25b_rm"`, but the inherited R24 probe-definition heredoc still created all four events under hard-coded `r24_rm/...` names. Validation therefore searched for `r25b_rm/...` events that had not been created.

This failure occurred before candidate launch and produced **no R25b localization measurement**. Classification is **SETUP INVALID**.

Because cleanup used `GROUP=r25b_rm`, stale `r24_rm` probe events may remain. Managed restoration must also be verified explicitly on the DGX host. The partial attempt-01 evidence is preserved.

## Retry gate

A retry is **not** authorized yet. Before the retry:

1. verify the managed OrcaRouter service/API is restored and READY;
2. inspect and remove only the exact stale `r24_rm` / `r25b_rm` groups from the failed attempt if present;
3. preserve attempt-01 evidence unchanged;
4. pull the corrected wrapper and require green CI;
5. run corrected R25b `--preflight` using the new `-02` evidence path;
6. require `stale_probe_groups=NONE`, `r25b_probe_definition_contract=PASS`, and `R25B_LIVE_PREFLIGHT=PASS` before authorizing another live run.

## Live measured-run boundary after retry authorization

When the corrected retry gate passes, the live run must use the dedicated wrapper with both explicit controls:

- mode: `run`;
- environment acknowledgement: `ORCA_R25B_LIVE_ACK=YES`.

The RM trace remains restricted to:

- `nv_alloc_pages`;
- `nv_alloc_system_pages`;
- optional static NVIDIA Xid event if available.

No UVM, generic page allocation, scheduler, function graph, CUDA API blanket tracing, or broad Python profiling is added.

The post-run analyzer reports:

- clock-offset spread and classification tolerance;
- selected `INIT_MODEL_BEGIN` / `INIT_MODEL_END` markers;
- initialize-model duration;
- first/last RM order-4 activity;
- total, before-init, inside-init, and after-init RM activity;
- inside-init percentage;
- one discriminator:
  - `RM_ORDER4_WITHIN_INITIALIZE_MODEL`;
  - `RM_ORDER4_STARTS_BEFORE_INITIALIZE_MODEL`;
  - `RM_ORDER4_EXTENDS_AFTER_INITIALIZE_MODEL`;
  - `RM_ORDER4_STRADDLES_INITIALIZE_MODEL`.

RM logical bytes remain activity volume, not exact resident ownership. Marker overlap remains temporal localization rather than causal proof.

## Interpretation

- If nearly all order-4 RM activity lies inside `initialize_model()`: close the next layer to CUDA-side model/parameter/storage construction and design the next discriminator around construction/materialization shape.
- If substantial activity begins only after `INIT_MODEL_END`: instrument the smallest weight-loader boundary next.
- If the episode starts materially before `INIT_MODEL_BEGIN` or straddles both sides: quantify that portion before changing behavior.

H11 is potentially relevant only after initialization is implicated because it changes packed expert parameter construction. H12 remains lower priority for this host-stability question because it changes a later post-load wrapping/rename path.

## Validation

The previous authorized head `009c8d47595765ca5dcf366500dfdc8de8bd2257` passed CI #1072, but that CI did not include the newly discovered probe-definition fix.

The corrected retry must not proceed until the new fix/regression-test head is CI green.

PR #244 remains open. No merge is implied.
