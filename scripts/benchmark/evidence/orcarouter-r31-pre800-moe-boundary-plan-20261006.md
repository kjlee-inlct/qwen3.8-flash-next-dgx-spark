# OrcaRouter R31 — pre-800 / ModelOpt-MoE boundary plan — 2026-10-06

## Status

**READY — READ-ONLY POST-HOC ONLY — NO LIVE RUN AUTHORIZED**

R30 closed the 400 MiB request family exactly to the 48 R26 packed-w13 intervals and showed that each 400 MiB request has an immediately preceding 800 MiB RM request. The 800 MiB request occurs about 8.1 ms before W13 BEGIN and has mixed userspace placement.

R31 asks the smallest remaining userspace-boundary question: where is that preceding 800 MiB request relative to `QWEN38_R26_MODELOPT_MOE_BEGIN`?

## Input

Use only preserved R28 evidence:

`/tmp/orcarouter-hybrid-r28-unquant-linear-boundary-01-20261005`

Required files are the existing candidate container log, RM trace, host page size, and three wall/monotonic clock anchors.

## Classification

For each common R26 ModelOpt-MoE / w13 sequence with exactly one 400 MiB w13 request and an immediately preceding 800 MiB request, classify the 800 event as:

- `before_moe_begin`;
- `inside_moe_pre_w13`;
- `inside_w13`;
- `inside_moe_after_w13`;
- unexpected/outside.

Also report:

- 800 → MoE BEGIN timing;
- MoE BEGIN → W13 BEGIN timing;
- 800 → W13 BEGIN timing.

## Discriminators

Preferred strict outcomes:

- `R31_PRE800_STRICTLY_BEFORE_MODELOPT_MOE_BEGIN`
- `R31_PRE800_STRICTLY_INSIDE_MODELOPT_MOE_PRE_W13`
- `R31_PRE800_MIXED_ACROSS_MODELOPT_MOE_BEGIN`

Anything incomplete falls back to `R31_PRE800_BOUNDARY_PATTERN_NOT_EXACT`.

## Interpretation

If all 48 events are before MoE BEGIN, the 800 family belongs temporally to the preceding constructor phase rather than early `ModelOptNvFp4FusedMoE.create_weights()`. The next step should inspect the immediately preceding userspace/CUDA allocation boundary; do not modify w13 semantics on that basis.

If all 48 events lie between MoE BEGIN and W13 BEGIN, the target narrows to the early body of `ModelOptNvFp4FusedMoE.create_weights()` before the w13 assignment. Then source/AST inspection should identify the exact preceding allocation statement before any new live measurement.

If placement is mixed, userspace boundaries still do not define a single owner; the next step should move to a narrowly scoped lower-level allocation-transition discriminator rather than another model-prefix split.

RM logical bytes remain activity volume, not exact resident ownership. Marker alignment is temporal localization, not causal ownership.

H11 remains deferred. PR #244 remains open/unmerged.