# OrcaRouter R25b — initialize_model RM-boundary discriminator — plan — 2026-10-05

## Status

**STATIC IMAGE PREFLIGHT PASS / LIVE RUNNER IMPLEMENTED — LIVE HARNESS PREFLIGHT NEXT**

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

## Completed build/static-preflight gate

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

The R25b runner does **not** edit the historical R24 runner. Instead it creates an ephemeral `/tmp` copy and changes only three harness-local identifiers:

1. repository-root injection so the temporary copy resolves the current checkout;
2. experiment container name → `qwen38-hybrid-r25b-init-marker`;
3. kprobe group name → `r25b_rm`.

The underlying R24 matched-control harness is otherwise reused unchanged. R25b sets its own diagnostic image and unique evidence directory:

`/tmp/orcarouter-hybrid-r25b-init-model-boundary-01-20261005`

The preserved R24 directory remains:

`/tmp/orcarouter-hybrid-r24-kv16-rm-mitigation-01-20261004`

and the R25b runner explicitly refuses to reuse that path or the R24 experiment container name.

Default invocation is safe: calling the R25b runner with no arguments performs `--preflight`. A live run additionally requires both explicit `run` mode and `ORCA_R25B_LIVE_ACK=YES`.

## Live preflight gate

The next action is **preflight only**:

`scripts/benchmark/run-orcarouter-r25b-init-model-boundary.sh --preflight`

This gate runs the marker-image contract plus the inherited R24 prerequisites, including:

- managed service/API healthy;
- installed managed profile is OrcaRouter;
- required H3/H4/H5/H6 checkpoints and H6 manifest valid;
- diagnostic image inherits the exact v0.29 stability label;
- predecessor runtime age meets the existing 2700 s minimum;
- direct RM probe targets are available;
- unique R25b experiment container does not already exist;
- unique R25b evidence path does not already exist;
- preserved R24 evidence path exists and is not reused.

A successful preflight must end in `R25B_LIVE_PREFLIGHT=PASS` and performs no model restart or managed-service mutation.

**Do not start the live run until this preflight is observed PASS.**

## Live-run boundary

When separately authorized after a PASS preflight, the live run preserves the R24 matched controls and strict host-stability policy while using the unique R25b container/evidence path.

The RM trace remains restricted to the already-closed boundaries:

- `nv_alloc_pages`;
- `nv_alloc_system_pages`;
- optional static NVIDIA Xid event if available.

No UVM, generic page allocation, scheduler, function graph, CUDA API blanket tracing, or broad Python profiling is added.

The post-run analyzer maps every valid begin/end marker pair onto the monotonic RM trace clock, selects the pair containing the most 64 KiB RM activity, and reports:

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

RM logical bytes remain activity volume, not exact resident ownership. Marker overlap remains temporal localization, not causal proof.

## Interpretation

- If nearly all order-4 RM activity lies inside `initialize_model()`: close the next layer to CUDA-side model/parameter/storage construction and design the next discriminator around construction/materialization shape.
- If substantial activity begins only after `INIT_MODEL_END`: instrument the smallest weight-loader boundary next.
- If the episode starts materially before `INIT_MODEL_BEGIN` or straddles both sides: quantify that portion before changing behavior.

H11 is potentially relevant only after initialization is implicated because it changes packed expert parameter construction. H12 remains lower priority for this host-stability question because it changes a later post-load wrapping/rename path.

## Validation

Validated implementation head before this documentation-only status stamp:

- `999a3176c7eb540c73527c9956f351a6795dd947`
- CI #1065: **SUCCESS**
- shell syntax: PASS
- ShellCheck: PASS
- Python compile: PASS
- full unit tests: PASS
- whitespace: PASS

PR #244 remains open. No merge is implied.
