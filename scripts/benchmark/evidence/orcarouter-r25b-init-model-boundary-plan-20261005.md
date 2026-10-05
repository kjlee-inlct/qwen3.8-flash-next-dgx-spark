# OrcaRouter R25b — initialize_model RM-boundary discriminator — plan — 2026-10-05

## Status

**COMPLETED — VALID_MEASURED — FUNCTIONAL PASS / HOST-STABILITY FAIL — PRIMARY RM BURST LOCALIZED TO `initialize_model()` WITH SMALL PRECURSOR**

Canonical final result:

- `orcarouter-r25b-init-model-boundary-result-20261005.md`

R25 read-only localization showed that the R24 64 KiB NVIDIA RM episode is only about 3.218 seconds long even though checkpoint weight filling takes hundreds of seconds. R25b added exactly two userspace log boundaries around `initialize_model()` and then performed one corrected measured retry after attempt-01 setup invalidity was repaired.

The pinned vLLM v0.29 `BaseModelLoader.load_model()` order is:

1. enter the target device context;
2. `initialize_model(...)`;
3. `load_weights(...)`;
4. online-quant finalization when applicable;
5. `process_weights_after_loading(...)`.

## Question

Does the approximately 77 GiB 64 KiB `nv_alloc_pages` episode occur primarily inside `initialize_model()` before checkpoint weight filling begins?

**Answer: yes, with a small real precursor immediately before the marker.**

Attempt 02 measured:

- total RM order-4 activity: `77405.938 MiB`;
- before selected init: `559.688 MiB`;
- inside selected init: `76846.250 MiB`;
- after selected init: `0.000 MiB`;
- inside-init fraction: `99.276945%`;
- discriminator: `RM_ORDER4_STARTS_BEFORE_INITIALIZE_MODEL`.

The strict discriminator remains `STARTS_BEFORE` because the first RM activity precedes the marker by about `0.417859 s`, well beyond the `0.025 s` classification tolerance. But the primary approximately 75–77 GiB episode is now localized to the first `initialize_model()` / immediate model-construction interval rather than long checkpoint filling.

This remains temporal localization rather than causal proof below that boundary.

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

## Live runner

Repository additions:

- `scripts/benchmark/run-orcarouter-r25b-init-model-boundary.sh`;
- `scripts/benchmark/analyze-orcarouter-r25b-init-model-overlap.py`;
- `tests/test_orcarouter_r25b_init_model_overlap.py`.

The R25b runner does **not** edit the historical R24 runner. It creates an ephemeral `/tmp` copy and transforms only the R25b-local harness identity:

1. repository-root injection;
2. experiment container name → `qwen38-hybrid-r25b-init-marker`;
3. shell kprobe group variable → `r25b_rm`;
4. all exactly four hard-coded R24 kprobe definitions → `r25b_rm/...`.

The corrected transform requires exactly four replacements, rejects any remaining `r24_rm/` definition, requires exactly four resulting `r25b_rm/` definitions, and is covered by a regression test executing the exact embedded transform against the canonical R24 harness.

Attempt-02 evidence:

`/tmp/orcarouter-hybrid-r25b-init-model-boundary-02-20261005`

Attempt-01 setup-invalid evidence remains preserved:

`/tmp/orcarouter-hybrid-r25b-init-model-boundary-01-20261005`

Preserved R24 evidence remains:

`/tmp/orcarouter-hybrid-r24-kv16-rm-mitigation-01-20261004`

## Original live-harness preflight

Canonical result:

- `orcarouter-r25b-live-harness-preflight-result-20261005.md`

The original preflight passed and was non-mutating, but it did not materialize the probe definitions and therefore could not detect the inherited heredoc group mismatch later exposed by attempt 01.

## Live attempt 01 — setup invalid

Canonical result:

- `orcarouter-r25b-live-attempt01-probe-group-invalid-20261005.md`

Attempt 01 failed in `create_probes()` before candidate launch because the initial wrapper changed `GROUP="r24_rm"` to `GROUP="r25b_rm"`, while the inherited R24 probe-definition heredoc still created all four events under hard-coded `r24_rm/...` names.

Classification remains **SETUP INVALID / NO R25b MEASUREMENT CLAIM**.

## Recovery + corrected preflight

Canonical result:

- `orcarouter-r25b-recovery-corrected-preflight-result-20261005.md`

Recovery verified exact managed OrcaRouter readiness, found the stale `r24_rm` group with exactly the expected four RM events, removed only those known events, and then passed the corrected preflight:

- `stale_probe_cleanup=APPLIED`;
- `stale_probe_cleanup=PASS`;
- `stale_probe_groups=NONE`;
- `r25_marker_contract=PASS`;
- `R25B_IMAGE_PREFLIGHT=PASS`;
- `r25b_probe_definition_contract=PASS`;
- `R24_PREFLIGHT=PASS`;
- `R25B_LIVE_PREFLIGHT=PASS`;
- `R25B_RECOVERY_AND_CORRECTED_PREFLIGHT=PASS`.

The managed container id and `StartedAt` remained unchanged across the corrected preflight.

## Attempt 02 — completed measured retry

Final result:

- `orcarouter-r25b-init-model-boundary-result-20261005.md`

The R24-matched measurement was valid:

- `run_valid=1`;
- `functional_class=PASS`;
- `host_stability_class=FAIL`;
- `rm_oom_count=3`;
- `event_snapshot_count=3`;
- `ORCA_R24_RESULT=VALID_RM_OOM`;
- `ORCA_R25B_RESULT=VALID_MEASURED`;
- final command RC `0`.

The common burst remained unchanged relative to R22:

- largest 5 s residual: `+77870.578 MiB`;
- candidate/R22 ratio: `103.636687%`;
- band: `BURST_UNCHANGED`;
- 64 KiB/order-4 calls: `526`;
- total order-4 RM activity: `77405.938 MiB`.

Exact selected initialization alignment:

- clock-offset spread: `6.176949 ms`;
- classification tolerance: `0.025000 s`;
- selected init duration: `3.161066 s`;
- RM episode duration: `3.468940 s`;
- before init: `559.688 MiB`;
- inside init: `76846.250 MiB`;
- after init: `0.000 MiB`;
- inside-init fraction: `99.276945%`;
- discriminator: `RM_ORDER4_STARTS_BEFORE_INITIALIZE_MODEL`.

The candidate log has two initialization marker pairs. The full traced order-4 episode ends before the first selected `INIT_MODEL_END`; it therefore does not extend into the first 601.96 s weight-fill interval or the later second init/69.95 s load interval.

Managed restoration closed PASS:

- `managed_restore_ready_rc=0`;
- exact managed OrcaRouter READY after `880 s`;
- restored model id `orcarouter/Qwen3.8-Flash-Next-Uncensored-NVFP4`;
- restored `max_model_len=262144`;
- managed service active after restoration.

## Interpretation / closure

R25b closes the current phase question as:

`small pre-init precursor (~560 MiB) -> first initialize_model() (~76.85 GiB RM order-4 activity) -> no remaining order-4 activity after init -> long checkpoint filling continues separately`

The approximately `559.688 MiB` precursor is real and should remain a separate side observation because it starts about `0.418 s` before `INIT_MODEL_BEGIN`, well outside the 25 ms tolerance.

The primary approximately 75–77 GiB direct-RM burst is now localized to the first `initialize_model()` / model-construction interval. This materially implicates constructor/parameter/storage materialization rather than checkpoint filling or post-load wrapping.

H11 is therefore now relevant as a hypothesis, but changing H11 behavior should follow one more observational boundary split inside `initialize_model()` rather than precede it. H12 remains lower priority because all traced order-4 activity is finished before post-load processing.

## Next engineering direction

Do not repeat H6 and do not broaden tracing.

The next discriminator should add only a few stable markers inside the first `initialize_model()` path to separate:

1. model-class resolution/import and constructor entry;
2. top-level model/module construction;
3. routed-expert / packed expert parameter construction or storage materialization;
4. constructor return.

Keep the approximately 560 MiB pre-init precursor separate from the main 76.8 GiB burst.

## Validation

The corrected implementation head `ae6ffe1fde09bc966a7d5cee58a947a666da2d86` passed CI #1077. The pre-attempt documentation head `42b2e3bb97a0631993e0dac430710142dac87a3c` passed CI #1079. The final result/documentation head must remain green before starting the next discriminator.

PR #244 remains open. No merge is implied.
